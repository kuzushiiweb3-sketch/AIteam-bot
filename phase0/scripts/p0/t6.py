"""Row A09 = test T6 (the Gate 0 -> 1 test): docs/fee-model.md s.7, step by step.

  Step 0  freeze:       t6_freeze.json must exist and match t6_select.py's SHA-256 and seed (else nothing is fetched)
  Step 1  calibration:  50 trades (up to 150), every candidate answer to the FC7 questions (fee_model.Semantics)
                        is tried; exactly one family of answers must reproduce all of them, or we stop
  Step 2  test set:     500 different trades, seeded, from canonical SOL non-mayhem pools, >= 100 pools, >= 7 days
  Step 3  score:        P1-P7 with no tolerance, plus red-team FM-3 (fail-or-succeed) and FM-4 (hard continuity
                        cases), reported separately until fee-model v1.1 freezes them

Red-team TS-6: a FAILED transaction is never decoded as a trade. Failed transactions are used only for
the network-fee check (P6) and the fail-or-succeed check (FM-3, where the instruction ARGUMENTS of the
failed trade are compared with the model's prediction; any events inside it are ignored).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from typing import Any, Optional

from . import fee_model as fm
from . import pump
from . import t6_select as sel
from .redact import REDACTOR
from .t6_select import T6_SPEC
from .txparse import (Tx, compute_budget, lamport_delta, precompile_signatures, system_transfers, token_deltas,
                      token_ops)

FREEZE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "t6_freeze.json")
SELECT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t6_select.py")
STOP = "STOP"


def file_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def make_freeze(seed: str, utc: str) -> dict:
    return {"seed": seed, "selection_module": "phase0/scripts/p0/t6_select.py",
            "selection_sha256": file_sha256(SELECT_PATH), "model_version": fm.MODEL_VERSION,
            "pass_criteria": T6_SPEC, "frozen_utc": utc,
            "note": "fee-model.md s.7 Step 0. Record this file (seed + hash + date) in docs/preregistration.md and "
                    "commit it BEFORE row A09 runs. Changing t6_select.py voids it (P7)."}


def check_freeze() -> "tuple[Optional[dict], str]":
    if not os.path.exists(FREEZE_PATH):
        return None, "Step 0 freeze missing: run `run_tier_a.py --t6-freeze`, record it in docs/preregistration.md, commit, then run A09"
    with open(FREEZE_PATH, "r", encoding="utf-8") as f:
        fr = json.load(f)
    if not fr.get("seed"):
        return None, "freeze file has no seed"
    if fr.get("selection_sha256") != file_sha256(SELECT_PATH):
        return None, "P7: t6_select.py changed since the freeze; re-freeze with a NEW seed and commit before running"
    if fr.get("pass_criteria") != json.loads(json.dumps(T6_SPEC)):
        return None, "P7: pass criteria changed since the freeze; re-freeze with a NEW seed"
    return fr, "ok"


# ---- decoding a trade from a successful transaction -------------------------------------------------
def i(v: Any) -> int:
    return int(v) if v is not None else 0


def decode_trades(tx: Tx, pool: str) -> list:
    """Successful single-pool PumpSwap trades in a tx (TS-6: returns [] for a failed tx)."""
    if not tx.success:
        return []
    out = []
    trades = [p for p in pump.amm_trades(tx) if pump.named_accounts(p).get("pool") == pool]
    for k, p in enumerate(trades):
        ev = pump.trade_event(p)
        if ev is None:
            continue
        acc = pump.named_accounts(p)
        out.append({"key": f"{tx.signature}#{k}", "sig": tx.signature, "slot": tx.slot, "block_time": tx.block_time,
                    "pool": pool, "ix_name": p.name, "args": {a: v for a, v in p.args.items() if not a.startswith("_")},
                    "ev": {a: v for a, v in ev.fields.items() if not a.startswith("_")}, "ev_missing": ev.fields.get("_missing", []),
                    "accounts": acc, "all_accounts": list(p.accounts), "single": len(trades) == 1,
                    "trade_top_index": p.ix.top_index, "trade_inner_index": p.ix.inner_index})
    return out


def other_pool_activity(tx: Tx, pool: str) -> dict:
    """Non-trade PumpSwap activity on the pool in this tx (sweeps, BOOST, multi-hop, deposits)."""
    kinds: dict = {}
    for p in pump.program_instructions(tx, (pump.PUMPSWAP_PROGRAM,)):
        acc = pump.named_accounts(p)
        touches = acc.get("pool") == pool or pool in p.accounts
        if touches and p.name not in pump.AMM_TRADES:
            kinds.setdefault(p.name, []).append(p)
    return kinds


# ---- state reconstruction under one set of semantics ----------------------------------------------------
def pre_state(tr: dict, sem: fm.Semantics, pool_info: dict) -> fm.PoolState:
    ev, name = tr["ev"], tr["ix_name"]
    v2, is_buy = name.endswith("_v2"), name.startswith("buy")
    lp, pr_ev, cr, bb = i(ev.get("lp_fee")), i(ev.get("protocol_fee")), i(ev.get("coin_creator_fee")), i(ev.get("buyback_fee"))
    pr_total = pr_ev if sem.event_protocol_fee == "total" else pr_ev + bb
    kept = (pr_total - bb) if sem.protocol_bucket == "pr_minus_bb" else pr_total
    vqr_ev = i(ev.get("virtual_quote_reserves"))
    vqr_pre = vqr_ev if (sem.event_vqr == "pre" or not v2) else vqr_ev + kept + cr
    bx, qx = i(ev.get("pool_base_token_reserves")), i(ev.get("pool_quote_token_reserves"))
    if sem.event_reserves == "post":
        if is_buy:
            bx += i(ev.get("base_amount_out"))
            q_in = i(ev.get("quote_amount_in"))
            if sem.event_quote_kind == "raw":
                qx -= q_in + lp + ((kept + cr) if v2 else 0)
            else:
                qx -= q_in + lp
        else:
            bx -= i(ev.get("base_amount_in"))
            if sem.event_quote_kind == "raw":
                qx += (i(ev.get("user_quote_amount_out")) + (pr_total - kept)) if v2 else i(ev.get("quote_amount_out_without_lp_fee"))
            else:
                qx += i(ev.get("quote_amount_out")) - lp
    q_vault = qx if sem.event_quote_kind == "raw" else qx - vqr_pre
    creator_after = i(ev.get("creator_fee_unclaimed"))
    return fm.PoolState(q_vault=q_vault, vqr=vqr_pre, b=bx, protocol_fees=0,
                        creator_fees=creator_after - (cr if v2 else 0), supply=i(ev.get("base_supply")),
                        is_mayhem=bool(pool_info.get("is_mayhem_mode")), quote_mint=pool_info.get("quote_mint", pump.WSOL_MINT),
                        canonical=True, coin_creator=ev.get("coin_creator") or fm.DEFAULT_PUBKEY,
                        creator_fee_bps=i(pool_info.get("creator_fee_bps")))


def trade_amount(name: str, p: dict) -> int:
    return p["q_in"] if name.startswith("buy") else p["q_out"]


def score_trade(tr: dict, sem: fm.Semantics, sched: fm.FeeSchedule, gcfg: dict, pool_info: dict,
                tx: Optional[Tx] = None, want_p4: bool = False) -> dict:
    ev, name, args = tr["ev"], tr["ix_name"], tr["args"]
    res: dict = {"key": tr["key"], "mism": []}
    try:
        st = pre_state(tr, sem, pool_info)
        sr = fm.schedule_rates(st, sched, bool(gcfg.get("creator_fee_configurable")))
        r = fm.rates(st, sched, bool(gcfg.get("creator_fee_configurable")))
        p = fm.predict(name, args, st, r, sem)
    except (fm.QuoteRefused, KeyError, ValueError) as e:
        res.update(P1=False, P2=False, P3=False, error=str(e))
        return res
    no_creator = st.coin_creator == fm.DEFAULT_PUBKEY
    exp_cbps = sr.creator if (no_creator and sem.no_creator_event_bps == "tier") else r.creator
    got = (i(ev.get("lp_fee_basis_points")), i(ev.get("protocol_fee_basis_points")), i(ev.get("coin_creator_fee_basis_points")))
    res["P1"] = got == (r.lp, r.protocol, exp_cbps)
    if not res["P1"]:
        res["mism"].append(("bps", [r.lp, r.protocol, exp_cbps], list(got)))
    if "fail" in p:
        res.update(P2=False, P3=False, predicted_fail=p["fail"])
        res["mism"].append(("predicted_fail", p["fail"], "success"))
        return res
    bb_bps = i(ev.get("buyback_fee_basis_points"))
    bb = 0 if st.is_mayhem else fm.buyback_fee(p["pr"], trade_amount(name, p), bb_bps, sem)
    pr_exp = p["pr"] if sem.event_protocol_fee == "total" else p["pr"] - bb
    p2 = [("lp_fee", p["lp"]), ("protocol_fee", pr_exp), ("coin_creator_fee", p["cr"]), ("buyback_fee", bb)]
    res["P2"] = True
    for f, v in p2:
        if i(ev.get(f)) != v:
            res["P2"] = False
            res["mism"].append((f, v, i(ev.get(f))))
    if name.startswith("buy"):
        p3 = [("base_amount_out", p["b_out"]), ("quote_amount_in", p["q_in"]),
              ("quote_amount_in_with_lp_fee", p["quote_amount_in_with_lp_fee"]), ("user_quote_amount_in", p["pay"])]
    else:
        p3 = [("base_amount_in", p["base_in"]), ("quote_amount_out", p["q_out"]),
              ("quote_amount_out_without_lp_fee", p["leaves"]), ("user_quote_amount_out", p["receive"])]
    res["P3"] = True
    for f, v in p3:
        if i(ev.get(f)) != v:
            res["P3"] = False
            res["mism"].append((f, v, i(ev.get(f))))
    res["pred"] = {k: v for k, v in p.items() if isinstance(v, int)}
    res["bb"] = bb
    res["state"] = st.__dict__.copy()
    if want_p4 and tx is not None and tr.get("single"):
        res["P4"] = balance_witness(tr, tx, p, bb, sem)
    return res


def balance_witness(tr: dict, tx: Tx, p: dict, bb: int, sem: fm.Semantics) -> Optional[dict]:
    """P4 on a tx with exactly one PumpSwap trade on this pool. None = not witnessable."""
    acc = tr["accounts"]
    bv, qv, uq = acc.get("pool_base_token_account"), acc.get("pool_quote_token_account"), acc.get("user_quote_token_account")
    d = token_deltas(tx)
    if bv not in d or qv not in d:
        return None
    exp = fm.vault_deltas(tr["ix_name"], p, bb, sem)
    out = {"base_vault": d[bv][2] == exp["base_vault"], "quote_vault": d[qv][2] == exp["quote_vault"]}
    # user side: only if the user's quote account exists before and after and nothing else touched it
    ops_outside = [o for o in token_ops(tx) if uq in (o.get("source"), o.get("dest"), o.get("account"))]
    if uq in d and d[uq][3] and d[uq][4] and not any(o["kind"] == "syncNative" for o in ops_outside) \
            and not any(t[1] == uq for t in system_transfers(tx)):
        out["user_quote"] = d[uq][2] == exp["user_quote"]
    quote_mint = d[qv][0]
    skip = {bv, qv, uq, acc.get("user_base_token_account")}
    fee_sum = sum(d[a][2] for a in set(tr["all_accounts"]) if a in d and a not in skip and d[a][0] == quote_mint)
    out["fee_recipients"] = fee_sum == exp["fee_recipients"]
    out["ok"] = all(v for k, v in out.items())
    return out


def network_fee_check(tx: Tx, tip_accounts: set) -> Optional[dict]:
    cb = compute_budget(tx)
    price = cb["cu_price_micro_lamports"] or 0
    if price and cb["cu_limit"] is None:
        return None          # default-limit rule not modelled here: excluded, and counted
    sigs = tx.num_required_signatures + precompile_signatures(tx)
    exp = fm.network_fee(sigs, price, cb["cu_limit"] or 0)
    out = {"sig": tx.signature, "failed": not tx.success, "expected": exp, "observed": tx.fee, "ok": tx.fee == exp}
    if not tx.success:
        tips = [t for t in system_transfers(tx) if t[1] in tip_accounts]
        if tips:
            out["tip_unchanged"] = all(lamport_delta(tx, t[1]) == 0 for t in tips)
            out["ok"] = out["ok"] and out["tip_unchanged"]
    return out


def custom_error(tx: Tx) -> Optional[int]:
    err = tx.err
    if isinstance(err, dict) and "InstructionError" in err:
        detail = err["InstructionError"][1] if len(err["InstructionError"]) > 1 else None
        if isinstance(detail, dict) and "Custom" in detail:
            return int(detail["Custom"])
    return None


# ---- tier helpers for strata (proxies from event fields; never from scores) ------------------------------
def tier_proxies(tr: dict, sched: fm.FeeSchedule) -> None:
    ev = tr["ev"]
    q = i(ev.get("pool_quote_token_reserves")) + i(ev.get("virtual_quote_reserves"))
    b = i(ev.get("pool_base_token_reserves"))
    s = i(ev.get("base_supply")) or 10 ** 15
    tiers = sched.fee_tiers
    if not b or not tiers:
        return
    m_pre = q * s // b
    if tr["ix_name"].startswith("buy"):
        q2, b2 = q + i(ev.get("quote_amount_in")) + i(ev.get("lp_fee")), b - i(ev.get("base_amount_out"))
    else:
        q2, b2 = q - (i(ev.get("quote_amount_out")) - i(ev.get("lp_fee"))), b + i(ev.get("base_amount_in"))
    m_post = q2 * s // b2 if b2 > 0 else m_pre
    t_pre, t_post = fm.tier_index(tiers, m_pre), fm.tier_index(tiers, m_post)
    near = any(t.threshold > 0 and abs(m_pre - t.threshold) * 100 <= t.threshold for t in tiers)
    tr.update(vqr_event=i(ev.get("virtual_quote_reserves")), can_boost=bool(ev.get("can_boost")),
              tier_pre=t_pre, tier_cross=(t_pre != t_post) or near, mcap_pre=m_pre)


# ---- the row ----------------------------------------------------------------------------------------------
def run(ctx) -> dict:
    fr, why = check_freeze()
    if fr is None:
        return {"outcome": "SKIPPED: " + why, "headline": "nothing fetched (freeze first)",
                "follow_up": "Freeze per fee-model.md s.7 Step 0, then re-run A09."}
    seed = fr["seed"]
    a03 = ctx.artifacts("A03")
    a08 = ctx.artifacts("A08")
    sched = fm.FeeSchedule.from_account(a08["fee_config"])
    gcfg = a08["global_config"]
    tips = set(a08.get("tip_accounts") or [])
    universe = a03.get("audit_new_canonical_pools") or []
    universe_src = "independent audit (PR-1 / FM-5)"
    if not universe:
        universe = [m["pool"] for m in a03.get("migrations", []) if m.get("pool")]
        universe_src = "withdraw-authority scan (independent audit not available yet; FM-5 not met)"
    universe = sorted(set(universe))
    times = [m["block_time"] for m in a03.get("migrations", []) if m.get("block_time")]
    window_start = min(times) if times else 0

    # admin change points inside the window (FeeConfig / GlobalConfig have no reliable per-trade history)
    change_slots = admin_changes(ctx, [a08["fee_config"].get("admin"), gcfg.get("admin")],
                                 [pump.PUMPSWAP_FEE_CONFIG, pump.PUMPSWAP_GLOBAL_CONFIG], window_start)
    min_slot = max(change_slots) + 1 if change_slots else 0

    # pool accounts: keep canonical, SOL-like, non-mayhem, non-cashback
    pools = {}
    excluded = {"non_canonical": 0, "non_sol": 0, "mayhem": 0, "cashback": 0, "missing": 0}
    accts = ctx.multiple_accounts(universe)
    for addr in universe:
        a = accts.get(addr)
        if not a:
            excluded["missing"] += 1
            continue
        try:
            pl = pump.decode_pool(pump.b64data(a))
        except Exception:  # noqa: BLE001
            excluded["missing"] += 1
            continue
        if not pump.is_canonical_pool(pl):
            excluded["non_canonical"] += 1
        elif pl["quote_mint"] not in fm.SOL_LIKE_QUOTES:
            excluded["non_sol"] += 1
        elif pl.get("is_mayhem_mode"):
            excluded["mayhem"] += 1
        elif pl.get("is_cashback_coin"):
            excluded["cashback"] += 1
        else:
            pools[addr] = pl
    order = sel.order(seed, "pool", list(pools))

    trades: dict = {}          # key -> trade record
    txs: dict = {}             # sig -> Tx
    sigmaps: dict = {}         # pool -> newest-first list of signature entries
    pairs: list = []           # (key_a, sig_b, kind)
    failed_sigs: list = []
    used_pools: set = set()
    counts: dict = {}

    def fetch(sig: str) -> Optional[Tx]:
        if sig not in txs:
            t = ctx.get_tx(sig)
            if t is None:
                return None
            txs[sig] = t
        return txs[sig]

    def add_trades_from(pool: str, sigs: list, want: Optional[dict]) -> int:
        added = 0
        for s in sigs:
            tx = fetch(s)
            if tx is None or (tx.slot or 0) < min_slot:
                continue
            for tr in decode_trades(tx, pool):
                if tr["key"] in trades:
                    continue
                tier_proxies(tr, sched)
                st = sel.strata_of(tr)
                if want is not None and not any(k in want for k in st):
                    continue
                tr["strata"] = st
                trades[tr["key"]] = tr
                for k in st:
                    counts[k] = counts.get(k, 0) + 1
                used_pools.add(pool)
                added += 1
        return added

    budget_reserve = 150
    for pass_no in range(1 + T6_SPEC["topup_passes"]):
        want = None if pass_no == 0 else sel.short_strata(counts)
        if pass_no > 0 and not want and len(trades) >= T6_SPEC["test_trades"] + T6_SPEC["calibration_trades"]:
            break
        for pool in order:
            if ctx.budget.row_cap(ctx.row) - ctx.budget.row_calls(ctx.row) < budget_reserve:
                break
            if pass_no == 0 and len(trades) >= (T6_SPEC["test_trades"] + T6_SPEC["calibration_trades"]) * 1.3 \
                    and len(used_pools) >= T6_SPEC["min_pools"]:
                break
            if pool not in sigmaps:
                sigmaps[pool] = list(ctx.signatures(pool, max_total=1000 * T6_SPEC["sig_pages_per_pool"],
                                                    stop_before_slot=min_slot or None))
            entries = sigmaps[pool]
            ok = [e["signature"] for e in entries if e.get("err") is None]
            bad = [e["signature"] for e in entries if e.get("err") is not None]
            k = T6_SPEC["trades_per_pool_first_pass"] if pass_no == 0 else T6_SPEC["topup_trades_per_pool"]
            already = {t["sig"] for t in trades.values() if t["pool"] == pool}
            chosen = [s for s in sel.order(seed, f"trade{pass_no}", ok) if s not in already][:k]
            add_trades_from(pool, chosen, want)
            if pass_no == 0:
                for s in sel.pick(seed, "failed", bad, T6_SPEC["failed_per_pool"]):
                    failed_sigs.append((pool, s))
                    fetch(s)
                # P5 / FM-4 pairs: the next newer state change after a sampled trade
                pos = {e["signature"]: n for n, e in enumerate(entries)}
                for s in chosen:
                    if s in pos and sel.take_pair(seed, s, T6_SPEC["pair_fraction"]):
                        j = pos[s] - 1
                        while j >= 0 and entries[j].get("err") is not None:
                            j -= 1
                        if j >= 0:
                            pairs.append((pool, s, entries[j]["signature"]))
                            fetch(entries[j]["signature"])
        if pass_no == 0 and not sel.short_strata(counts) and len(used_pools) >= T6_SPEC["min_pools"]:
            break

    keys = sorted(trades)
    cal_keys, test_keys = sel.assign(seed, keys, T6_SPEC["calibration_trades"])
    test_keys = test_keys[:T6_SPEC["test_trades"]]

    # ---- Step 1: calibration ----
    cal = calibrate(cal_keys, test_keys, trades, txs, pools, sched, gcfg, seed)
    result_numbers: dict = {"universe": universe_src, "pools_eligible": len(pools), "pools_used": len(used_pools),
                            "excluded_pools": excluded, "admin_change_slots": change_slots,
                            "trades_sampled": len(trades), "calibration": cal["summary"]}
    artifacts = {"seed": seed, "freeze": fr, "model_version": fm.MODEL_VERSION, "calibration_keys": cal_keys,
                 "test_keys": test_keys, "pairs": pairs, "failed": failed_sigs, "calibration": cal}
    save_trade_fixtures(ctx, trades, txs)
    if cal["chosen"] is None or ctx.opts.t6_stop_after_calibration:
        ctx.store.save_artifacts(ctx.row, artifacts)
        return {"outcome": "INCOMPLETE: calibration " + cal["summary"]["verdict"], "numbers": result_numbers,
                "headline": cal["summary"]["verdict"],
                "follow_up": "Read calibration mismatches in fixtures/phase0/A09/artifacts.json; fix the model, bump "
                             "MODEL_VERSION, re-freeze with a new seed, and re-run on a fresh sample."}
    sem = cal["chosen"]

    # ---- Step 3: score ----
    sc = score_all(test_keys, trades, txs, pools, sched, gcfg, sem, pairs, failed_sigs, tips, ctx)
    days = 0.0
    bts = [trades[k]["block_time"] for k in test_keys if trades[k].get("block_time")]
    if bts:
        days = (max(bts) - min(bts)) / 86400
    test_counts: dict = {}
    for k in test_keys:
        for s in trades[k]["strata"]:
            test_counts[s] = test_counts.get(s, 0) + 1
    short = sel.short_strata(test_counts)
    sides = {"below_420": sum(1 for k in test_keys if "tier_cross" in trades[k]["strata"]
                              and trades[k].get("mcap_pre", 0) < T6_SPEC["tier_cross_sides_of_lamports"]),
             "at_or_above_420": sum(1 for k in test_keys if "tier_cross" in trades[k]["strata"]
                                    and trades[k].get("mcap_pre", 0) >= T6_SPEC["tier_cross_sides_of_lamports"])}
    pools_in_test = len({trades[k]["pool"] for k in test_keys})
    p7 = (not short and len(test_keys) >= T6_SPEC["test_trades"] and pools_in_test >= T6_SPEC["min_pools"]
          and days >= T6_SPEC["min_days"] and sides["below_420"] > 0 and sides["at_or_above_420"] > 0)
    sc["P7"] = {"ok": p7, "test_trades": len(test_keys), "pools": pools_in_test, "days": round(days, 2),
                "strata": test_counts, "short_strata": short, "tier_cross_sides": sides,
                "freeze_sha256_ok": True}
    core = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]
    core_ok = all(sc[p]["ok"] for p in core)
    result_numbers.update({p: {k: v for k, v in sc[p].items() if k != "mismatches"} for p in core + ["FM3", "FM4"]})
    artifacts["scores"] = sc
    artifacts["semantics"] = sem.__dict__
    ctx.store.save_artifacts(ctx.row, artifacts)
    if core_ok:
        outcome = "PASS"
    elif all(sc[p]["ok"] for p in core if p != "P7") and short:
        outcome = "INCOMPLETE: T6a checks hold; strata " + ", ".join(sorted(short)) + " need recorder data (T6b, FM-5)"
    else:
        outcome = "FAIL"
    head = (f"P1 {sc['P1']['passed']}/{sc['P1']['n']}, P2 {sc['P2']['passed']}/{sc['P2']['n']}, "
            f"P3 {sc['P3']['passed']}/{sc['P3']['n']}, P4 {sc['P4']['passed']}/{sc['P4']['n']}, "
            f"P5 {sc['P5']['passed']}/{sc['P5']['n']}, P6 {sc['P6']['passed']}/{sc['P6']['n']}")
    return {"outcome": outcome, "headline": head, "numbers": result_numbers,
            "follow_up": ("Gate 0->1 fee check passed; red-team signs off." if outcome == "PASS" else
                          "Record every mismatch (artifacts.json), fix the model, bump the version, re-freeze, "
                          "and re-run on a FRESH 500 (never re-score the same sample).")}


def admin_changes(ctx, admins: list, watched: list, window_start: int) -> list:
    slots = []
    for admin in [a for a in admins if a]:
        for e in ctx.signatures(admin, max_total=300, stop_before_time=window_start or None):
            if e.get("err") is not None:
                continue
            tx = ctx.get_tx(e["signature"])
            if tx is None:
                continue
            for idx, k in enumerate(tx.account_keys):
                if k in watched and tx.is_writable(idx):
                    slots.append(tx.slot)
    return sorted(set(s for s in slots if s))


def calibrate(cal_keys: list, test_keys: list, trades: dict, txs: dict, pools: dict, sched, gcfg, seed: str) -> dict:
    combos = fm.all_semantics()
    full: list = []
    best = (-1, None)
    per_combo = {}
    for sem in combos:
        good = 0
        for k in cal_keys:
            tr = trades[k]
            r = score_trade(tr, sem, sched, gcfg, pools[tr["pool"]], txs.get(tr["sig"]), want_p4=True)
            p4 = r.get("P4")
            if r.get("P1") and r.get("P2") and r.get("P3") and (p4 is None or p4.get("ok")):
                good += 1
        per_combo[sem.key()] = good
        if good == len(cal_keys) and cal_keys:
            full.append(sem)
        if good > best[0]:
            best = (good, sem)
    summary = {"trades": len(cal_keys), "combinations_tried": len(combos), "combinations_fitting_all": len(full)}
    chosen = None
    if not cal_keys:
        summary["verdict"] = "no calibration trades sampled"
    elif not full:
        summary["verdict"] = f"no candidate semantics reproduces all {len(cal_keys)} trades (best {best[0]})"
        bs = best[1]
        summary["best_semantics"] = bs.__dict__ if bs else None
        summary["best_mismatches"] = [score_trade(trades[k], bs, sched, gcfg, pools[trades[k]["pool"]],
                                                  txs.get(trades[k]["sig"]), True)["mism"] for k in cal_keys][:50]
    else:
        # Several families may fit if a question is never exercised. Accept only if they predict the test
        # set identically (this compares predictions with each other, never with the chain).
        def preds(sem):
            out = []
            for k in test_keys:
                tr = trades[k]
                r = score_trade(tr, sem, sched, gcfg, pools[tr["pool"]])
                out.append((r.get("pred"), r.get("bb"), r.get("P1")))
            return out
        ref = preds(full[0])
        same = all(preds(s) == ref for s in full[1:])
        if same:
            chosen = full[0]
            undetermined = [n for n in fm.SEMANTICS_CHOICES if len({getattr(s, n) for s in full}) > 1]
            summary["verdict"] = "unique" if len(full) == 1 else "equivalent on the test set"
            summary["undetermined_dimensions"] = undetermined
            summary["chosen"] = chosen.__dict__
        else:
            summary["verdict"] = f"ambiguous: {len(full)} families fit and they disagree on the test set"
            summary["fitting"] = [s.__dict__ for s in full[:20]]
    return {"chosen": chosen, "summary": summary}


def score_all(test_keys, trades, txs, pools, sched, gcfg, sem, pairs, failed_sigs, tips, ctx) -> dict:
    out: dict = {p: {"n": 0, "passed": 0, "mismatches": []} for p in ("P1", "P2", "P3", "P4", "P5", "P6", "FM3", "FM4")}
    near_limit = 0
    for k in test_keys:
        tr = trades[k]
        r = score_trade(tr, sem, sched, gcfg, pools[tr["pool"]], txs.get(tr["sig"]), want_p4=True)
        for p in ("P1", "P2", "P3"):
            out[p]["n"] += 1
            if r.get(p):
                out[p]["passed"] += 1
            elif len(out[p]["mismatches"]) < 200:
                out[p]["mismatches"].append({"key": k, "mism": r.get("mism"), "error": r.get("error")})
        p4 = r.get("P4")
        if p4 is not None:
            out["P4"]["n"] += 1
            if p4["ok"]:
                out["P4"]["passed"] += 1
            elif len(out["P4"]["mismatches"]) < 200:
                out["P4"]["mismatches"].append({"key": k, "detail": p4})
        # FM-3 near-limit successes: the model must predict success
        if r.get("pred") and _near_limit(tr, r["pred"]):
            near_limit += 1
            out["FM3"]["n"] += 1
            if "predicted_fail" not in r:
                out["FM3"]["passed"] += 1
    # P5 continuity (pairs in different slots, nothing in between) and FM-4 hard cases
    fm4 = {"same_slot": 0, "same_slot_ok": 0, "boost_between": 0, "multihop_between": 0}
    for pool, sa, sb in pairs:
        ta, tb = txs.get(sa), txs.get(sb)
        if ta is None or tb is None:
            continue
        a_tr, b_tr = decode_trades(ta, pool), decode_trades(tb, pool)
        if len(a_tr) != 1 or len(b_tr) != 1 or other_pool_activity(ta, pool) or other_pool_activity(tb, pool):
            continue
        same_slot = ta.slot == tb.slot
        ok = continuity(a_tr[0], b_tr[0], sem, sched, gcfg, pools[pool])
        if ok is None:
            continue
        if same_slot:
            fm4["same_slot"] += 1
            fm4["same_slot_ok"] += int(ok)
            continue   # same-slot pairs need block order (FM-4); reported, not counted in P5
        out["P5"]["n"] += 1
        if ok:
            out["P5"]["passed"] += 1
        elif len(out["P5"]["mismatches"]) < 200:
            out["P5"]["mismatches"].append({"a": sa, "b": sb})
    # P6 network fees on every fetched tx we looked at (successful trades and sampled failures)
    p6_sigs = sorted({trades[k]["sig"] for k in test_keys} | {s for _, s in failed_sigs})
    excluded_default_limit = 0
    failed_n = 0
    for s in p6_sigs:
        tx = txs.get(s)
        if tx is None:
            continue
        r = network_fee_check(tx, tips)
        if r is None:
            excluded_default_limit += 1
            continue
        out["P6"]["n"] += 1
        failed_n += int(r["failed"])
        if r["ok"]:
            out["P6"]["passed"] += 1
        elif len(out["P6"]["mismatches"]) < 200:
            out["P6"]["mismatches"].append(r)
    # FM-3 failed trades: compare the model's fail prediction using the previous state change's post-state
    fm3_failed = {"n": 0, "ok": 0, "not_evaluable": 0}
    for pool, s in failed_sigs:
        tx = txs.get(s)
        code = custom_error(tx) if tx else None
        if code not in (6004, 6040, 6063):
            continue
        res = fail_prediction(ctx, tx, pool, code, sem, sched, gcfg, pools[pool])
        if res is None:
            fm3_failed["not_evaluable"] += 1
            continue
        fm3_failed["n"] += 1
        fm3_failed["ok"] += int(res)
    for p in ("P1", "P2", "P3"):
        out[p]["ok"] = out[p]["n"] >= T6_SPEC["test_trades"] and out[p]["passed"] == out[p]["n"]
    out["P4"]["ok"] = out["P4"]["n"] >= T6_SPEC["p4_min_trades"] and out["P4"]["passed"] == out["P4"]["n"]
    out["P5"]["ok"] = out["P5"]["n"] >= T6_SPEC["p5_min_pairs"] and out["P5"]["passed"] == out["P5"]["n"]
    out["P6"].update(failed=failed_n, excluded_default_limit=excluded_default_limit)
    out["P6"]["ok"] = (out["P6"]["n"] >= T6_SPEC["p6_min_txs"] and failed_n >= T6_SPEC["p6_min_failed"]
                       and out["P6"]["passed"] == out["P6"]["n"])
    out["FM3"].update(failed_trades=fm3_failed, near_limit=near_limit)
    out["FM3"]["ok"] = (fm3_failed["n"] >= T6_SPEC["fm3_min_failed_trades"] and fm3_failed["ok"] == fm3_failed["n"]
                        and near_limit >= T6_SPEC["fm3_min_near_limit"] and out["FM3"]["passed"] == out["FM3"]["n"])
    out["FM4"].update(fm4)
    out["FM4"]["note"] = ("same-slot pairs are checked in both orders only; block-position ordering (getBlock), "
                          "multi-hop-between and boost-between pairs await fee-model v1.1's definition")
    out["FM4"]["ok"] = False
    return out


def _near_limit(tr: dict, pred: dict) -> bool:
    bps = T6_SPEC["fm3_near_limit_bps"]
    a, n = tr["args"], tr["ix_name"]
    if n in ("buy", "buy_v2") and pred.get("pay"):
        lim = i(a.get("max_quote_amount_in"))
        return lim >= pred["pay"] and (lim - pred["pay"]) * 10_000 <= bps * pred["pay"]
    if n.startswith("buy_exact_quote_in") and pred.get("b_out"):
        lim = i(a.get("min_base_amount_out"))
        return pred["b_out"] >= lim and (pred["b_out"] - lim) * 10_000 <= bps * pred["b_out"]
    if n.startswith("sell") and pred.get("receive"):
        lim = i(a.get("min_quote_amount_out"))
        return pred["receive"] >= lim and (pred["receive"] - lim) * 10_000 <= bps * pred["receive"]
    return False


def continuity(a: dict, b: dict, sem, sched, gcfg, pool_info) -> Optional[bool]:
    try:
        sa = pre_state(a, sem, pool_info)
        r = fm.rates(sa, sched, bool(gcfg.get("creator_fee_configurable")))
        p = fm.predict(a["ix_name"], a["args"], sa, r, sem)
        if "fail" in p:
            return False
        bb = 0 if sa.is_mayhem else fm.buyback_fee(p["pr"], trade_amount(a["ix_name"], p), i(a["ev"].get("buyback_fee_basis_points")), sem)
        post = fm.post_state(sa, a["ix_name"], p, bb, sem)
        sb = pre_state(b, sem, pool_info)
    except (fm.QuoteRefused, KeyError, ValueError):
        return None
    return (post.q_vault, post.b, post.vqr, post.creator_fees) == (sb.q_vault, sb.b, sb.vqr, sb.creator_fees)


def fail_prediction(ctx, tx: Tx, pool: str, code: int, sem, sched, gcfg, pool_info) -> Optional[bool]:
    """FM-3: rebuild the pre-state from the previous successful single-trade tx in an EARLIER slot."""
    if code == 6063:
        return None      # needs the protocol fee bucket, which events do not carry: recorder data (T6b)
    ptr = [p for p in pump.program_instructions(tx, (pump.PUMPSWAP_PROGRAM,))
           if p.name in pump.AMM_TRADES and pump.named_accounts(p).get("pool") == pool]
    if len(ptr) != 1:
        return None
    entries = list(ctx.signatures(pool, max_total=50, before=tx.signature))
    prev = next((e for e in entries if e.get("err") is None), None)
    if prev is None or prev.get("slot") == tx.slot:
        return None
    if any(e.get("slot") == tx.slot and e.get("err") is None for e in entries):
        return None
    ptx = ctx.get_tx(prev["signature"])
    if ptx is None:
        return None
    ptr_prev = decode_trades(ptx, pool)
    if len(ptr_prev) != 1 or other_pool_activity(ptx, pool):
        return None
    try:
        sa = pre_state(ptr_prev[0], sem, pool_info)
        r = fm.rates(sa, sched, bool(gcfg.get("creator_fee_configurable")))
        p = fm.predict(ptr_prev[0]["ix_name"], ptr_prev[0]["args"], sa, r, sem)
        bb = 0 if sa.is_mayhem else fm.buyback_fee(p["pr"], trade_amount(ptr_prev[0]["ix_name"], p),
                                                   i(ptr_prev[0]["ev"].get("buyback_fee_basis_points")), sem)
        post = fm.post_state(sa, ptr_prev[0]["ix_name"], p, bb, sem)
        args = {a: v for a, v in ptr[0].args.items() if not a.startswith("_")}
        r2 = fm.rates(post, sched, bool(gcfg.get("creator_fee_configurable")))
        pred = fm.predict(ptr[0].name, args, post, r2, sem)
    except (fm.QuoteRefused, KeyError, ValueError):
        return None
    return pred.get("fail") == code


def save_trade_fixtures(ctx, trades: dict, txs: dict) -> None:
    """fixtures/phase0/A09/t6_trades.jsonl.gz: decoded trade + the raw getTransaction result it came from."""
    d = os.path.join(ctx.store.fixtures_dir, "A09")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "t6_trades.jsonl.gz")
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for k in sorted(trades):
            tr = trades[k]
            raw = ctx.store.cache_get("tx-base64", tr["sig"])
            line = json.dumps({"trade": tr, "raw_tx": raw}, default=str, separators=(",", ":"))
            REDACTOR.assert_clean(line, where="t6 fixtures")
            f.write(line + "\n")
