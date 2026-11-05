"""Rows built on transaction history: A10, A11, A16, A17, A21, A22, A25, A29, A30, A31, A32.

Red-team TS-6: only SUCCESSFUL transactions are decoded as trades. Failed ones are used for
fee / failure statistics and their instruction ARGUMENTS only; any events inside them are ignored
(A11 counts how often they appear).
"""

from __future__ import annotations

import statistics
import time
import urllib.parse

from p0 import pump
from p0.txparse import EVENT_PREFIX, compute_budget, normalize, per_instruction_compute, system_transfers, \
    token_balance_map, token_deltas
from p0.t6 import custom_error


def _pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


def _price(ev: dict) -> "float | None":
    """Report-only float price (SOL per token, 6-decimal coins), from event reserves. Never used in decisions."""
    b = int(ev.get("pool_base_token_reserves") or 0)
    q = int(ev.get("pool_quote_token_reserves") or 0) + int(ev.get("virtual_quote_reserves") or 0)
    return (q / 1e9) / (b / 1e6) if b else None


def early_tape(ctx, mig: dict, seconds: int, max_pages: int, max_txs: int, include_failed: bool = False) -> "list | None":
    """Signature entries of a pool from its migration slot to +seconds (oldest first), or None if too busy."""
    entries = []
    for e in ctx.signatures(mig["pool"], max_total=1000 * max_pages, stop_before_slot=mig["slot"]):
        entries.append(e)
    if len(entries) >= 1000 * max_pages:
        return None
    t0 = mig.get("block_time") or 0
    out = [e for e in entries if (e.get("blockTime") or 0) <= t0 + seconds and (include_failed or e.get("err") is None)]
    out.sort(key=lambda e: (e.get("slot") or 0))
    return out[:max_txs]


def _recent_migrations(ctx, min_age_s: int, n: int) -> list:
    a03 = ctx.artifacts("A03")
    now = ctx.now()
    ms = [m for m in a03.get("migrations", []) if m.get("pool") and m.get("block_time") and now - m["block_time"] >= min_age_s]
    ms.sort(key=lambda m: -m["block_time"])        # youngest first: fewer pages to read back to the start
    return ms[:n]


# ---- A10 -------------------------------------------------------------------------------------------
def a10(ctx) -> dict:
    a04 = ctx.artifacts("A04")
    sigs = sorted({s["sig"] for s in a04.get("amm_samples", [])})
    target = ctx.n(1000, 30)
    n = mism_base = mism_quote = user_ne_signer = 0
    examples = []
    for sig in sigs:
        if n >= target:
            break
        tx = ctx.get_tx(sig, encoding="json")
        if tx is None or not tx.success:
            continue
        pre = token_balance_map(tx.pre_token_balances, tx.account_keys)
        post = token_balance_map(tx.post_token_balances, tx.account_keys)
        for p in pump.amm_trades(tx):
            na = pump.named_accounts(p)
            user = na.get("user")
            for side, acct in (("base", na.get("user_base_token_account")), ("quote", na.get("user_quote_token_account"))):
                owner = (post.get(acct) or pre.get(acct) or {}).get("owner")
                if owner and owner != user:
                    if side == "base":
                        mism_base += 1
                    else:
                        mism_quote += 1
                    if len(examples) < 20:
                        examples.append({"sig": sig, "side": side, "account": acct, "owner": owner, "user": user})
            if tx.signers and user != tx.signers[0]:
                user_ne_signer += 1
            n += 1
    return {"outcome": "MEASURED", "headline": f"{mism_base + mism_quote} of {n} trades pay out to an account the user does not own",
            "numbers": {"trades": n, "base_owner_differs": mism_base, "quote_owner_differs": mism_quote,
                        "user_is_not_fee_payer": user_ne_signer, "examples": examples},
            "follow_up": "Any count > 0 confirms the guard's output pinning is the only defence (already the design)."}


# ---- A11 -------------------------------------------------------------------------------------------
def a11(ctx) -> dict:
    a04 = ctx.artifacts("A04")
    cu: dict = {}
    sigs = sorted({s["sig"] for s in a04.get("amm_samples", [])})[: ctx.n(1200, 40)]
    a09 = ctx.store.load_artifacts("A09") or {}
    sigs += [k.split("#")[0] for k in (a09.get("test_keys") or [])][: ctx.n(500, 10)]
    for sig in sorted(set(sigs)):
        tx = ctx.get_tx(sig, encoding="json") or ctx.get_tx(sig)
        if tx is None or not tx.success:
            continue
        per = per_instruction_compute(tx)
        for p in pump.program_instructions(tx):
            if p.ix.inner_index is None and p.ix.top_index in per:
                key = ("curve:" if p.program == pump.PUMP_PROGRAM else "pool:") + p.name
                cu.setdefault(key, []).append(per[p.ix.top_index])
    cu_stats = {k: {"n": len(v), "p50": _pct(v, 0.5), "p99": _pct(v, 0.99), "max": max(v),
                    "proposed_limit": int(_pct(v, 0.99) * 1.2)} for k, v in sorted(cu.items()) if v}
    # failure share and error codes on PumpSwap (from signature entries: no tx fetch needed)
    codes: dict = {}
    total = failed = 0
    failed_6004 = []
    for e in ctx.signatures(pump.PUMPSWAP_PROGRAM, max_total=ctx.n(5000, 300)):
        total += 1
        if e.get("err") is None:
            continue
        failed += 1
        err = e["err"]
        code = None
        if isinstance(err, dict) and "InstructionError" in err:
            d = err["InstructionError"][1] if len(err["InstructionError"]) > 1 else None
            code = d.get("Custom") if isinstance(d, dict) else str(d)
        codes[str(code)] = codes.get(str(code), 0) + 1
        if code == 6004 and len(failed_6004) < ctx.n(100, 5):
            failed_6004.append(e["signature"])
    decoded_failed, events_in_failed, args = 0, 0, []
    for sig in failed_6004:
        tx = ctx.get_tx(sig)
        if tx is None:
            continue
        trades = [p for p in pump.program_instructions(tx, (pump.PUMPSWAP_PROGRAM,)) if p.name in pump.AMM_TRADES]
        if any(ix.data[:8] == EVENT_PREFIX for ix in tx.all_ixs()):
            events_in_failed += 1             # TS-6 evidence; never used as a trade
        if trades:
            decoded_failed += 1
            p = trades[0]
            if len(args) < 30:
                args.append({"sig": sig, "ix": p.name, "args": {k: v for k, v in p.args.items() if not k.startswith("_")}})
    # FC9: v2 trades on mayhem pools
    pools = sorted({s["pool"] for s in a04.get("amm_samples", []) if s.get("ix", "").endswith("_v2") and s.get("pool")})[: ctx.n(500, 20)]
    acc = ctx.multiple_accounts(pools)
    mayhem_v2 = 0
    mayhem_pools = set()
    for p, a in acc.items():
        if a:
            try:
                if pump.decode_pool(pump.b64data(a)).get("is_mayhem_mode"):
                    mayhem_pools.add(p)
            except Exception:  # noqa: BLE001
                pass
    for s in a04.get("amm_samples", []):
        if s.get("pool") in mayhem_pools and s.get("ix", "").endswith("_v2"):
            mayhem_v2 += 1
    # priority fees every 60 s for an hour
    pf = []
    hot_pool = (a04.get("amm_samples") or [{}])[0].get("pool")
    end = time.time() + ctx.dur(3600, 120)
    while time.time() < end:
        res = ctx.call("getRecentPrioritizationFees", [[pump.PUMPSWAP_PROGRAM] + ([hot_pool] if hot_pool else [])]) or []
        vals = [r.get("prioritizationFee", 0) for r in res]
        pf.append({"t": int(time.time()), "n": len(vals), "p50": _pct(vals, 0.5), "p90": _pct(vals, 0.9), "max": max(vals) if vals else None})
        time.sleep(60 if not ctx.opts.quick else 20)
    share = round(failed / total, 4) if total else None
    return {"outcome": "MEASURED",
            "headline": f"compute p99 by type recorded ({len(cu_stats)} types); PumpSwap failure share {share}; "
                        f"6004 decodable {decoded_failed}/{len(failed_6004)}; v2 on mayhem pools {mayhem_v2}",
            "numbers": {"compute": cu_stats, "pumpswap_sig_entries": total, "failed": failed, "failure_share": share,
                        "error_codes": codes, "failed_6004_sampled": len(failed_6004), "failed_6004_decodable": decoded_failed,
                        "failed_6004_with_event_cpis": events_in_failed, "failed_args_examples": args,
                        "v2_trades_on_mayhem_pools": mayhem_v2, "priority_fee_polls": pf},
            "follow_up": "Proposed compute limit per type = p99 x 1.2. If < 95% of failed buys decode, the losers'-tape "
                         "idea (QNT-E1) loses its price-limit feature."}


# ---- A16 -------------------------------------------------------------------------------------------
def a16(ctx) -> dict:
    migs = _recent_migrations(ctx, min_age_s=900, n=ctx.n(50, 3))
    per_pool, tapes = [], {}
    for m in migs:
        tape = early_tape(ctx, m, 600, max_pages=ctx.n(15, 2), max_txs=ctx.n(400, 40))
        if tape is None:
            per_pool.append({"pool": m["pool"], "skipped": "too many transactions to page back to the start"})
            continue
        boosts, inits, flow = [], [], []
        for e in tape:
            tx = ctx.get_tx(e["signature"])
            if tx is None or not tx.success:
                continue
            for ev in pump.events_in_tx(tx):
                f = ev.fields
                if f.get("pool") != m["pool"]:
                    continue
                if ev.name == "BoostBuyAndBurnEvent":
                    boosts.append({"t": f.get("timestamp"), "slot": tx.slot, "used": f.get("quote_amount_in_used"),
                                   "burned": f.get("base_amount_burned"), "remaining": f.get("boost_vault_remaining"),
                                   "authority": f.get("authority"), "sig": tx.signature})
                elif ev.name == "InitBoostEvent":
                    inits.append({"t": f.get("timestamp"), "vqr": f.get("virtual_quote_reserves"), "sig": tx.signature})
                elif ev.name in ("BuyEvent", "SellEvent"):
                    q = int(f.get("user_quote_amount_in") or f.get("user_quote_amount_out") or 0)
                    flow.append((f.get("timestamp"), q if ev.name == "BuyEvent" else -q))
        tapes[m["pool"]] = [e["signature"] for e in tape]
        rec = {"pool": m["pool"], "txs_first_10min": len(tape), "boost_events": len(boosts), "init_boost": len(inits)}
        if boosts:
            ts = [b["t"] for b in boosts if b["t"]]
            rec.update(total_used_lamports=sum(int(b["used"] or 0) for b in boosts),
                       spacing_s_p50=_pct([b - a for a, b in zip(ts, ts[1:])], 0.5),
                       duration_s=(max(ts) - min(ts)) if ts else None,
                       vault_reaches_zero=any(int(b["remaining"] or 0) == 0 for b in boosts),
                       authorities=sorted({b["authority"] for b in boosts}),
                       burned_every_time=all(int(b["burned"] or 0) > 0 for b in boosts))
            last = max(ts) if ts else None
            if last:
                rec["net_flow_2min_before_last"] = sum(q for t, q in flow if t and last - 120 <= t < last)
                rec["net_flow_2min_after_last"] = sum(q for t, q in flow if t and last <= t <= last + 120)
                rec["last_boost_t"] = last
        per_pool.append(rec)
    with_boost = sum(1 for r in per_pool if r.get("boost_events"))
    described = sum(1 for r in per_pool if "skipped" not in r)
    gc = (ctx.store.load_artifacts("A08") or {}).get("global_config") or {}
    ctx.store.save_artifacts(ctx.row, {"per_pool": per_pool, "tapes": tapes,
                                       "migrations": {m["pool"]: m for m in migs}})
    ok = described == len(migs) and migs
    return {"outcome": "PASS" if ok else "INCOMPLETE: " + f"{len(migs) - described} pools too busy to page back",
            "headline": f"{with_boost}/{described} graduates show BOOST; boost_enabled={gc.get('boost_enabled')}",
            "numbers": {"graduates": len(migs), "described": described, "with_boost": with_boost,
                        "without_boost_group": described - with_boost, "per_pool": per_pool[:60]},
            "follow_up": "Graduates without BOOST are their own group (rulings R5)."}


# ---- A17 -------------------------------------------------------------------------------------------
def a17(ctx) -> dict:
    tips = set((ctx.store.load_artifacts("A19") or {}).get("tip_accounts") or [])
    migs = _recent_migrations(ctx, min_age_s=300, n=ctx.n(30, 2))
    by_off: dict = {0: [], 1: [], 2: [], 3: []}
    buys: dict = {0: [], 1: [], 2: [], 3: []}
    for m in migs:
        for off in range(4):
            blk = ctx.call("getBlock", [m["slot"] + off, {"encoding": "base64", "transactionDetails": "full",
                                                          "maxSupportedTransactionVersion": 0, "rewards": False,
                                                          "commitment": "finalized"}], max_bytes=200 * 1024 * 1024)
            if not blk:
                continue
            nb = 0
            for t in blk.get("transactions") or []:
                tx = normalize(dict(t, slot=m["slot"] + off, blockTime=blk.get("blockTime")))
                for frm, to, lam, _ in system_transfers(tx):
                    if to in tips:
                        by_off[off].append(lam)
                if tx.success:
                    nb += sum(1 for p in pump.amm_trades(tx) if p.name in pump.AMM_BUYS and pump.named_accounts(p).get("pool") == m["pool"])
            buys[off].append(nb)
    stats = {f"+{k}": {"tips": len(v), "p50": _pct(v, 0.5), "p75": _pct(v, 0.75), "p95": _pct(v, 0.95)} for k, v in by_off.items()}
    comp = {f"+{k}": {"p50": _pct(v, 0.5), "max": max(v) if v else None} for k, v in buys.items()}
    return {"outcome": "MEASURED" if tips else "MEASURED (no tip account list: run A19 first)",
            "headline": f"tip p50/p95 at +0: {stats['+0']['p50']}/{stats['+0']['p95']} lamports over {len(migs)} migrations",
            "numbers": {"migrations": len(migs), "tips_by_slot_offset": stats, "landed_buys_on_new_pool": comp,
                        "tip_accounts_known": len(tips)},
            "notes": "30 migrations by default (the plan's fallback when getBlock is costly). Bundle membership needs "
                     "the A20 endpoint, which is not verified yet.",
            "follow_up": "Feeds the race/no-race memo (rulings C15)."}


# ---- A21 -------------------------------------------------------------------------------------------
def a21(ctx) -> dict:
    a16 = ctx.artifacts("A16")
    a04 = ctx.store.load_artifacts("A04") or {}
    use: dict = {}
    for pool, sigs in (a16.get("tapes") or {}).items():
        for s in sigs[:60]:
            tx = ctx.get_tx(s)
            if tx is None or not tx.success:
                continue
            for table, _, _ in tx.lookups:
                use.setdefault(table, set()).add(pool)
    for rec in a04.get("lookups", []):
        for table in rec["tables"]:
            for mint in rec["mints"]:
                use.setdefault(table, set()).add(mint)
    reused = {t: len(v) for t, v in use.items() if len(v) >= 5}
    top = sorted(reused.items(), key=lambda kv: -kv[1])[:300]
    accts = ctx.multiple_accounts([t for t, _ in top], encoding="jsonParsed")
    auth = {t: (((accts.get(t) or {}).get("data") or {}).get("parsed") or {}).get("info", {}).get("authority") for t, _ in top}
    keep = any(c >= 5 for c in reused.values())
    return {"outcome": "MEASURED", "headline": f"{len(use)} tables seen; {len(reused)} used across >= 5 launches",
            "numbers": {"tables_seen": len(use), "reused_ge_5": len(reused), "top": top[:20],
                        "authorities": dict(list(auth.items())[:20])},
            "follow_up": "CHN-B keeps the lookup-table feature" if keep else "CHN-B drops the lookup-table feature (proposal rule)"}


# ---- A22 -------------------------------------------------------------------------------------------
def a22(ctx) -> dict:
    a04 = ctx.artifacts("A04")
    uris = [c.get("uri") for c in a04.get("creates", []) if c.get("uri")]
    target = ctx.n(1000, 20)
    if len(uris) < target:
        for e in ctx.signatures(pump.PUMP_PROGRAM, max_total=ctx.n(3000, 50)):
            if len(uris) >= target:
                break
            if e.get("err") is not None:
                continue
            tx = ctx.get_tx(e["signature"], encoding="json")
            for ev in pump.events_in_tx(tx) if tx else []:
                if ev.name == "CreateEvent" and ev.fields.get("uri"):
                    uris.append(ev.fields["uri"])
    hosts: dict = {}
    for u in uris[:target]:
        h = urllib.parse.urlsplit(u).hostname or ("(scheme " + urllib.parse.urlsplit(u).scheme + ")")
        hosts[h] = hosts.get(h, 0) + 1
    ranked = sorted(hosts.items(), key=lambda kv: -kv[1])
    return {"outcome": "PASS" if ranked else "FAIL", "headline": f"{len(uris[:target])} URIs; top hosts {ranked[:5]}",
            "numbers": {"uris": len(uris[:target]), "hosts": ranked[:50]},
            "follow_up": "Add the top hosts to List 2 (QUESTIONS_FOR_PAUL.md). No URI was fetched."}


# ---- A25 -------------------------------------------------------------------------------------------
def a25(ctx) -> dict:
    a03 = ctx.artifacts("A03")
    mints = [m["mint"] for m in a03.get("migrations", []) if m.get("mint")][: ctx.n(50, 2)]
    lat: dict = {"getTokenLargestAccounts": [], "getMultipleAccounts": [], "getSignaturesForAddress": [], "das_page": []}
    calls_per_coin, credits_per_coin, das_pages = [], [], []
    for mint in mints:
        before_calls = ctx.budget.row_calls(ctx.row)
        before_cr = ctx.budget.data["credits_est"]
        res, meta = ctx.call_meta("getTokenLargestAccounts", [mint, {"commitment": "confirmed"}])
        lat["getTokenLargestAccounts"].append(meta.latency_s)
        holders = [t["address"] for t in ((res or {}).get("value") or [])[:20]]
        res2, meta2 = ctx.call_meta("getMultipleAccounts", [holders, {"encoding": "jsonParsed", "commitment": "confirmed"}])
        lat["getMultipleAccounts"].append(meta2.latency_s)
        owners = [(((v or {}).get("data") or {}).get("parsed") or {}).get("info", {}).get("owner") for v in (res2 or {}).get("value") or []]
        if owners and owners[0]:
            _, meta3 = ctx.call_meta("getSignaturesForAddress", [owners[0], {"limit": 100}])
            lat["getSignaturesForAddress"].append(meta3.latency_s)
        cursor, pages = None, 0
        while pages < 10:
            params = {"mint": mint, "limit": 1000}
            if cursor:
                params["cursor"] = cursor
            r, m4 = ctx.call_meta("getTokenAccounts", params)
            lat["das_page"].append(m4.latency_s)
            pages += 1
            cursor = (r or {}).get("cursor")
            if not cursor or not (r or {}).get("token_accounts"):
                break
        das_pages.append(pages)
        calls_per_coin.append(ctx.budget.row_calls(ctx.row) - before_calls)
        credits_per_coin.append(ctx.budget.data["credits_est"] - before_cr)
    p = {k: {"p50_s": round(_pct(v, 0.5), 3) if v else None, "p95_s": round(_pct(v, 0.95), 3) if v else None} for k, v in lat.items()}
    per_grad = statistics.median(credits_per_coin) if credits_per_coin else None
    fits = per_grad is not None and per_grad * 300 <= 100_000
    return {"outcome": ("PASS" if fits else "FAIL") + " (credits are our estimate; confirm with the dashboard)",
            "headline": f"median {per_grad} est. credits and {statistics.median(calls_per_coin) if calls_per_coin else None} calls per graduate",
            "numbers": {"coins": len(mints), "latency": p, "calls_per_coin_p50": statistics.median(calls_per_coin) if calls_per_coin else None,
                        "est_credits_per_coin_p50": per_grad, "das_pages_p50": statistics.median(das_pages) if das_pages else None,
                        "daily_at_300_graduates": per_grad * 300 if per_grad is not None else None},
            "follow_up": None if fits else "Narrow the scan to top holders",
            "notes": "Paul can read the real credits used from the Helius dashboard before/after this row."}


# ---- A29 -------------------------------------------------------------------------------------------
def a29(ctx) -> dict:
    migs = _recent_migrations(ctx, min_age_s=300, n=ctx.n(100, 3))
    paths, moves = {}, []
    for m in migs:
        entries = []
        for e in ctx.signatures(m["pool"], max_total=1000 * ctx.n(15, 2), stop_before_slot=m["slot"]):
            entries.append(e)
        sel = sorted([e for e in entries if e.get("err") is None and (e.get("slot") or 0) <= m["slot"] + 20],
                     key=lambda e: e["slot"])[: ctx.n(300, 30)]
        per_slot: dict = {}
        for e in sel:
            tx = ctx.get_tx(e["signature"])
            if tx is None or not tx.success:
                continue
            for p in pump.amm_trades(tx):
                if pump.named_accounts(p).get("pool") != m["pool"]:
                    continue
                ev = pump.trade_event(p)
                if ev:
                    pr = _price(ev.fields)
                    if pr:
                        per_slot[tx.slot - m["slot"]] = pr
        if per_slot:
            first = per_slot[min(per_slot)]
            path = {k: round(v / first - 1, 4) for k, v in sorted(per_slot.items())}
            paths[m["pool"]] = {"synthetic": m.get("synthetic"), "path": path}
            moves.append(max(abs(x) for x in path.values()))
    ctx.store.save_artifacts(ctx.row, {"paths": paths})
    return {"outcome": "MEASURED", "headline": f"{len(paths)} pools; median max move in blocks 0-20: {_pct(moves, 0.5)}",
            "numbers": {"pools": len(paths), "max_move_p50": _pct(moves, 0.5), "max_move_p90": _pct(moves, 0.9),
                        "synthetic_pools": sum(1 for v in paths.values() if v["synthetic"])},
            "notes": "Pilot only. Prices are report-only floats from event reserves (pre/post semantics per FC7 unknown).",
            "follow_up": "Sizes D03."}


# ---- A30 -------------------------------------------------------------------------------------------
def a30(ctx) -> dict:
    a16 = ctx.artifacts("A16")
    tips = set((ctx.store.load_artifacts("A19") or {}).get("tip_accounts") or [])
    boosted = [r for r in a16.get("per_pool", []) if r.get("last_boost_t")][: ctx.n(20, 2)]
    migs = a16.get("migrations", {})
    out, tip_vals = [], []
    blocks_left = ctx.n(5, 1)
    for r in boosted:
        m = migs.get(r["pool"])
        if not m:
            continue
        lo, hi = r["last_boost_t"] - 60, r["last_boost_t"] + 180
        entries = [e for e in ctx.signatures(r["pool"], max_total=1000 * ctx.n(15, 2), stop_before_slot=m["slot"])
                   if e.get("blockTime") and lo <= e["blockTime"] <= hi][: ctx.n(600, 40)]
        per_slot: dict = {}
        for e in entries:
            tx = ctx.get_tx(e["signature"])
            if tx is None:
                continue
            buys = [p for p in pump.program_instructions(tx, (pump.PUMPSWAP_PROGRAM,))
                    if p.name in pump.AMM_BUYS and pump.named_accounts(p).get("pool") == r["pool"]]
            if not buys:
                continue
            s = per_slot.setdefault(tx.slot, {"landed": 0, "failed": 0, "cu_price": []})
            s["landed" if tx.success else "failed"] += 1           # failed: instruction args only (TS-6)
            cb = compute_budget(tx)
            if cb["cu_price_micro_lamports"]:
                s["cu_price"].append(cb["cu_price_micro_lamports"])
        busiest = sorted(per_slot, key=lambda k: -(per_slot[k]["landed"] + per_slot[k]["failed"]))[:1]
        for slot in busiest:
            if blocks_left <= 0 or not tips:
                break
            blocks_left -= 1
            blk = ctx.call("getBlock", [slot, {"encoding": "base64", "transactionDetails": "full",
                                               "maxSupportedTransactionVersion": 0, "rewards": False,
                                               "commitment": "finalized"}], max_bytes=200 * 1024 * 1024)
            for t in (blk or {}).get("transactions") or []:
                tx = normalize(dict(t, slot=slot))
                tip_vals += [lam for _, to, lam, _ in system_transfers(tx) if to in tips]
        landed = sum(v["landed"] for v in per_slot.values())
        failed = sum(v["failed"] for v in per_slot.values())
        out.append({"pool": r["pool"], "slots": len(per_slot), "landed_buys": landed, "failed_buys": failed,
                    "fail_share": round(failed / (landed + failed), 3) if landed + failed else None,
                    "cu_price_p50": _pct([x for v in per_slot.values() for x in v["cu_price"]], 0.5)})
    return {"outcome": "MEASURED", "headline": f"{len(out)} boosted graduates; median fail share "
                                               f"{_pct([o['fail_share'] for o in out if o['fail_share'] is not None], 0.5)}",
            "numbers": {"pools": out, "tips_in_busiest_blocks": {"n": len(tip_vals), "p50": _pct(tip_vals, 0.5),
                                                                  "p95": _pct(tip_vals, 0.95)}},
            "notes": "Pilot only. Failed buys are counted from instruction arguments, never from events (TS-6).",
            "follow_up": "Sizes D02."}


# ---- A31 -------------------------------------------------------------------------------------------
def a31(ctx) -> dict:
    migs = _recent_migrations(ctx, min_age_s=3600, n=ctx.n(40, 3))
    fallen = []
    for m in migs:
        entries = [e for e in ctx.signatures(m["pool"], max_total=1000 * ctx.n(10, 2), stop_before_slot=m["slot"])
                   if e.get("err") is None and e.get("blockTime") and e["blockTime"] <= m["block_time"] + 3600]
        if not entries:
            continue
        minute: dict = {}
        for e in entries:
            k = (e["blockTime"] - m["block_time"]) // 60
            if k not in minute or e["slot"] > minute[k]["slot"]:
                minute[k] = e
        prices = {}
        for k, e in sorted(minute.items()):
            tx = ctx.get_tx(e["signature"])
            for p in pump.amm_trades(tx) if tx and tx.success else []:
                ev = pump.trade_event(p)
                if ev and pump.named_accounts(p).get("pool") == m["pool"]:
                    prices[k] = _price(ev.fields)
        prices = {k: v for k, v in prices.items() if v}
        if len(prices) < 3:
            continue
        early = [v for k, v in prices.items() if k <= 10]
        peak = max(early) if early else None
        if not peak:
            continue
        trough_k = min((k for k in prices if prices[k] == min(prices.values())))
        if min(prices.values()) <= 0.5 * peak:
            fallen.append({"m": m, "entries": entries, "trough_minute": trough_k, "drop": round(1 - min(prices.values()) / peak, 3)})
        if len(fallen) >= ctx.n(20, 2):
            break
    results = []
    for f in fallen:
        m = f["m"]
        sellers: dict = {}
        window = [e for e in f["entries"] if (e["blockTime"] - m["block_time"]) // 60 <= f["trough_minute"]][: ctx.n(100, 15)]
        for e in window:
            tx = ctx.get_tx(e["signature"])
            for p in pump.amm_trades(tx) if tx and tx.success else []:
                ev = pump.trade_event(p)
                if ev and ev.name == "SellEvent" and ev.fields.get("pool") == m["pool"]:
                    u = ev.fields.get("user")
                    sellers[u] = sellers.get(u, 0) + int(ev.fields.get("base_amount_in") or 0)
        for wallet, sold in sorted(sellers.items(), key=lambda kv: -kv[1])[:3]:
            bought = transferred = 0
            for e in ctx.signatures(wallet, max_total=ctx.n(100, 10)):
                if e.get("err") is not None:
                    continue
                tx = ctx.get_tx(e["signature"])
                if tx is None:
                    continue
                inflow = sum(d[2] for a, d in token_deltas(tx).items() if d[0] == m["mint"] and d[1] == wallet and d[2] > 0)
                if not inflow:
                    continue
                is_buy = any(ev.name in ("BuyEvent", "TradeEvent") and ev.fields.get("user") == wallet
                             for ev in pump.events_in_tx(tx))
                if is_buy:
                    bought += inflow
                else:
                    transferred += inflow
            results.append({"pool": m["pool"], "wallet": wallet, "sold": sold, "in_by_buy": bought, "in_by_transfer": transferred})
    tot_t = sum(r["in_by_transfer"] for r in results)
    tot = tot_t + sum(r["in_by_buy"] for r in results)
    share = round(tot_t / tot, 4) if tot else None
    return {"outcome": "MEASURED", "headline": f"{len(fallen)} coins fell >= 50%; share of dumpers' tokens that arrived by transfer: {share}",
            "numbers": {"coins": len(fallen), "sellers": len(results), "transfer_share": share, "rows": results[:60]},
            "notes": "Pilot only; one hop. The fixed early kill (< 10% by plain transfer) is applied on 200 coins in D06.",
            "follow_up": "Feeds D06."}


# ---- A32 -------------------------------------------------------------------------------------------
def a32(ctx) -> dict:
    a16 = ctx.artifacts("A16")
    wallets = []
    for pool, sigs in (a16.get("tapes") or {}).items():
        for s in sigs[:40]:
            tx = ctx.get_tx(s)
            if tx is None or not tx.success:
                continue
            for ev in pump.events_in_tx(tx):
                if ev.name == "BuyEvent" and ev.fields.get("user") and ev.fields["user"] not in wallets:
                    wallets.append(ev.fields["user"])
    wallets = wallets[: ctx.n(200, 5)]
    rows = []
    for w in wallets:
        calls0 = ctx.budget.row_calls(ctx.row)
        t0 = time.monotonic()
        oldest = None
        n = 0
        for e in ctx.signatures(w, max_total=1000 * ctx.n(5, 1)):
            oldest = e
            n += 1
        funder = None
        if oldest:
            tx = ctx.get_tx(oldest["signature"])
            for frm, to, lam, _ in system_transfers(tx) if tx else []:
                if to == w and frm != w:
                    funder = frm
                    break
        complete = n < 1000 * ctx.n(5, 1)
        rows.append({"wallet": w, "calls": ctx.budget.row_calls(ctx.row) - calls0, "seconds": round(time.monotonic() - t0, 3),
                     "funder": funder, "history_complete": complete})
    calls = [r["calls"] for r in rows]
    secs = [r["seconds"] for r in rows]
    med = statistics.median(calls) if calls else None
    p95 = _pct(secs, 0.95)
    ok = med is not None and med <= 5 and p95 is not None and p95 <= 2
    return {"outcome": "PASS" if ok else ("FAIL" if rows else "MEASURED"),
            "headline": f"median {med} calls (~credits) per lookup, p95 {p95} s; funder found for "
                        f"{sum(1 for r in rows if r['funder'])}/{len(rows)}",
            "numbers": {"wallets": len(rows), "calls_p50": med, "seconds_p95": p95,
                        "funder_found": sum(1 for r in rows if r["funder"]),
                        "history_capped": sum(1 for r in rows if not r["history_complete"])},
            "notes": "Pass mark is a proposal: median <= 5 credits and p95 <= 2 s."}
