"""Rows A01-A08: Pump settings, program upgrades, migrations (+ independent audit), events, token kind,
canonical pools, pool layouts, and live fee settings. All read-only.

Red-team TS-6: failed transactions are counted, never decoded as trades or migrations.
Red-team PR-1: A03 adds an audit that does not depend on our event decoder (account snapshots).
"""

from __future__ import annotations

import base64
import gzip
import json
import os
import statistics
import urllib.parse

from p0 import pump
from p0.b58 import b58encode
from p0.pda import ata
from p0.store import utc_now
from p0.txparse import EVENT_PREFIX, program_data_logs, token_deltas, token_ops

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CAPTURE = os.path.join(DATA_DIR, "feeconfig_mainnet_2026-09-08.b64")
DANGEROUS_EXTENSIONS = ("transferHook", "permanentDelegate", "transferFeeConfig", "defaultAccountState",
                        "nonTransferable", "pausableConfig", "confidentialTransferMint", "mintCloseAuthority",
                        "scaledUiAmountConfig", "interestBearingConfig")
SAFE_EXTENSIONS = ("metadataPointer", "tokenMetadata")


def _pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


# ---- A01 -------------------------------------------------------------------------------------------
def a01(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    acct = ctx.account(pump.PUMP_GLOBAL, client=client)
    if acct is None:
        return {"outcome": "FAIL", "headline": "Pump Global account not found",
                "follow_up": "Check the address against the IDL; log ADMIN_CHANGE"}
    data = pump.b64data(acct)
    g = pump.decode_global(data)
    tail = data[g["_consumed"]:]
    checks = {
        "owner_is_pump": acct.get("owner") == pump.PUMP_PROGRAM,
        "withdraw_authority": g.get("withdraw_authority") == pump.WITHDRAW_AUTHORITY,
        "enable_migrate": g.get("enable_migrate") is True,
        "pool_migration_fee": g.get("pool_migration_fee") == pump.EXPECTED_POOL_MIGRATION_FEE,
        "every_field_decodes": not g["_missing"],
        "trailing_bytes_zero": all(b == 0 for b in tail),
    }
    ok = all(checks.values())
    nums = {"data_len": len(data), "decoded_len": g["_consumed"], "trailing_bytes": len(tail),
            "withdraw_authority": g.get("withdraw_authority"), "enable_migrate": g.get("enable_migrate"),
            "pool_migration_fee": g.get("pool_migration_fee"),
            "initial_virtual_token_reserves": g.get("initial_virtual_token_reserves"),
            "initial_virtual_sol_reserves": g.get("initial_virtual_sol_reserves"),
            "initial_real_token_reserves": g.get("initial_real_token_reserves"),
            "token_total_supply": g.get("token_total_supply"),
            "initial_virtual_quote_reserves": g.get("initial_virtual_quote_reserves"),
            "buyback_basis_points": g.get("buyback_basis_points"), "checks": checks,
            "context_slot": None}
    ctx.store.save_artifacts(ctx.row, {"global": g, "fetched_utc": utc_now()})
    return {"outcome": "PASS" if ok else "FAIL",
            "headline": f"authority {'ok' if checks['withdraw_authority'] else 'CHANGED'}, enable_migrate={g.get('enable_migrate')}, "
                        f"fee={g.get('pool_migration_fee')}, {len(data)} bytes",
            "numbers": nums,
            "follow_up": None if ok else "Re-point the backup filter and audit to the new authority, re-run A03, log ADMIN_CHANGE"}


# ---- A02 -------------------------------------------------------------------------------------------
def a02(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    dec = pump.load_decoders()
    out = {}
    ok_all = True
    for name, pid in pump.PROGRAMS.items():
        acct = ctx.account(pid, client=client)
        rec = {"idl_address_matches": dec[name].address == pid}
        if acct is None:
            rec["error"] = "program account not found"
            ok_all = False
            out[name] = rec
            continue
        data = pump.b64data(acct)
        rec["owner"] = acct.get("owner")
        rec["executable"] = acct.get("executable")
        if acct.get("owner") != pump.BPF_UPGRADEABLE_LOADER or len(data) < 36 or int.from_bytes(data[:4], "little") != 2:
            rec["error"] = "not an upgradeable-loader Program account"
            ok_all = False
            out[name] = rec
            continue
        pdata = b58encode(data[4:36])
        rec["program_data"] = pdata
        pd = ctx.account(pdata, data_slice={"offset": 0, "length": 45}, client=client)
        raw = pump.b64data(pd) if pd else b""
        if len(raw) < 13 or int.from_bytes(raw[:4], "little") != 3:
            rec["error"] = "ProgramData header did not decode"
            ok_all = False
        else:
            rec["last_deploy_slot"] = int.from_bytes(raw[4:12], "little")
            rec["upgrade_authority"] = b58encode(raw[13:45]) if raw[12] == 1 and len(raw) >= 45 else None
            rec["programdata_len"] = (pd or {}).get("space")
        ok_all = ok_all and rec["idl_address_matches"]
        out[name] = rec
    ctx.store.save_artifacts(ctx.row, {"regime_tag": "v0", "programs": out, "fetched_utc": utc_now()})
    return {"outcome": "PASS" if ok_all else "FAIL",
            "headline": "; ".join(f"{n}: deploy slot {r.get('last_deploy_slot')}" for n, r in out.items()),
            "numbers": out, "notes": "Saved as regime tag v0 (fixtures/phase0/A02/artifacts.json).",
            "follow_up": None if ok_all else "Decode the loader account bytes by hand; try the public RPC"}


# ---- A03 -------------------------------------------------------------------------------------------
def _gpa_keys(ctx, program: str, filters: list, timeout_s: float = 180.0) -> list:
    res = ctx.call("getProgramAccounts", [program, {"encoding": "base64", "commitment": "confirmed",
                                                    "dataSlice": {"offset": 0, "length": 0},
                                                    "filters": filters, "withContext": True}],
                   max_bytes=600 * 1024 * 1024, timeout_s=timeout_s)
    value = res.get("value") if isinstance(res, dict) else res
    out = []
    for e in value or []:
        out.append((e["pubkey"], (e.get("account") or {}).get("space")))
    slot = res.get("context", {}).get("slot") if isinstance(res, dict) else None
    return out, slot


def snapshot(ctx) -> dict:
    """Independent audit snapshot: every PumpSwap Pool account and every completed bonding curve.

    Uses only account owners, 8-byte discriminators (from the pinned IDLs) and one flag byte, so it does
    not depend on our event or instruction decoders (red-team PR-1).
    """
    amm = pump.load_decoders()["pump_amm"]
    pumpd = pump.load_decoders()["pump"]
    pool_disc = b58encode(amm.account_disc["Pool"])
    curve_disc = b58encode(pumpd.account_disc["BondingCurve"])
    complete_off = next(o for (n, o, s) in pumpd.field_offsets("BondingCurve") if n == "complete")
    snap = {"utc": utc_now(), "unix": ctx.now(), "pools": None, "complete_curves": None, "errors": {}}
    try:
        pools, slot = _gpa_keys(ctx, pump.PUMPSWAP_PROGRAM, [{"memcmp": {"offset": 0, "bytes": pool_disc}}])
        snap["pools"] = {k: sp for k, sp in pools}
        snap["pools_slot"] = slot
    except Exception as e:  # noqa: BLE001 - recorded, never hidden
        snap["errors"]["pools"] = str(e)
    try:
        curves, slot = _gpa_keys(ctx, pump.PUMP_PROGRAM, [{"memcmp": {"offset": 0, "bytes": curve_disc}},
                                                          {"memcmp": {"offset": complete_off, "bytes": b58encode(b"\x01")}}])
        snap["complete_curves"] = sorted(k for k, _ in curves)
        snap["curves_slot"] = slot
    except Exception as e:  # noqa: BLE001
        snap["errors"]["complete_curves"] = str(e)
    return snap


def _snap_dir(ctx) -> str:
    return os.path.join(ctx.store.fixtures_dir, "A03", "snapshots")


def save_snapshot(ctx, snap: dict) -> str:
    d = _snap_dir(ctx)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, snap["utc"].replace(":", "") + ".json.gz")
    text = json.dumps(snap)
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(text)
    return p


def previous_snapshot(ctx, min_age_s: int) -> "dict | None":
    d = _snap_dir(ctx)
    if not os.path.isdir(d):
        return None
    best = None
    for name in sorted(os.listdir(d)):
        with gzip.open(os.path.join(d, name), "rt", encoding="utf-8") as f:
            s = json.load(f)
        if ctx.now() - s.get("unix", 0) >= min_age_s and s.get("pools") is not None:
            best = s
    return best


def a03(ctx) -> dict:
    window_s = int(ctx.dur(7 * 86400, 6 * 3600))
    since = ctx.now() - window_s
    entries = list(ctx.signatures(pump.WITHDRAW_AUTHORITY, max_total=ctx.n(20_000, 400), stop_before_time=since))
    migrations, failed, odd = [], 0, []
    counts = {"txs": len(entries), "successful": 0, "failed": 0, "with_migration_event": 0, "with_create_pool_event": 0,
              "with_both_events": 0, "synthetic_post_complete_buy": 0, "complete_in_same_tx": 0,
              "complete_migrate_buy_same_tx": 0, "migrate_ix": 0, "migrate_v2_ix": 0, "unknown_pump_ix": 0,
              "migration_without_create_pool": 0, "create_pool_without_migration": 0}
    signer_counts: dict = {}
    unknown_names: dict = {}
    for e in entries:
        tx = ctx.get_tx(e["signature"])
        if tx is None:
            continue
        if not tx.success:
            failed += 1
            counts["failed"] += 1
            continue                         # TS-6: nothing inside a failed tx is counted as a migration
        counts["successful"] += 1
        evs = pump.events_in_tx(tx)
        names = [ev.name for ev in evs]
        pixs = pump.program_instructions(tx, (pump.PUMP_PROGRAM, pump.PUMPSWAP_PROGRAM))
        ixn = [p.name for p in pixs]
        for p in pixs:
            if p.name.startswith("_UNKNOWN_IX"):
                counts["unknown_pump_ix"] += 1
                unknown_names[p.name] = unknown_names.get(p.name, 0) + 1
        mig = [ev for ev in evs if ev.name == "CompletePumpAmmMigrationEvent"]
        cpe = [ev for ev in evs if ev.name == "CreatePoolEvent" and ev.program == pump.PUMPSWAP_PROGRAM]
        has_mig_ix = any(n in pump.MIGRATE_IXS for n in ixn)
        counts["migrate_ix"] += ixn.count("migrate")
        counts["migrate_v2_ix"] += ixn.count("migrate_v2")
        if not mig and not has_mig_ix and not cpe:
            continue                         # some other transaction touching the authority
        counts["with_migration_event"] += bool(mig)
        counts["with_create_pool_event"] += bool(cpe)
        counts["with_both_events"] += bool(mig and cpe)
        if mig and not cpe:
            counts["migration_without_create_pool"] += 1
        if cpe and not mig:
            counts["create_pool_without_migration"] += 1
        if (has_mig_ix and not mig) or (mig and not has_mig_ix):
            odd.append({"sig": tx.signature, "ix": ixn, "events": names})
        synthetic = "PostCompleteBuyEvent" in names
        complete_same = "CompleteEvent" in names
        buy_same = any(n in pump.CURVE_TRADES for n in ixn)
        counts["synthetic_post_complete_buy"] += synthetic
        counts["complete_in_same_tx"] += complete_same
        counts["complete_migrate_buy_same_tx"] += bool(complete_same and has_mig_ix and buy_same)
        signer = tx.signers[0] if tx.signers else None
        signer_counts[signer] = signer_counts.get(signer, 0) + 1
        f = mig[0].fields if mig else {}
        c = cpe[0].fields if cpe else {}
        migrations.append({
            "sig": tx.signature, "slot": tx.slot, "block_time": tx.block_time, "pool": f.get("pool") or c.get("pool"),
            "mint": f.get("mint") or c.get("base_mint"), "bonding_curve": f.get("bonding_curve"),
            "quote_mint": f.get("quote_mint") or c.get("quote_mint"), "migrate_ix": [n for n in ixn if n in pump.MIGRATE_IXS],
            "synthetic": synthetic, "complete_same_tx": complete_same, "signer": signer,
            "authority_in_keys": pump.WITHDRAW_AUTHORITY in tx.account_keys,
            "create_pool": {k: c.get(k) for k in ("pool_base_amount", "pool_quote_amount", "lp_mint", "lp_token_amount_out",
                                                    "is_mayhem_mode", "coin_creator", "index", "creator")} if c else None,
            "mint_amount": f.get("mint_amount"), "sol_amount": f.get("sol_amount"),
            "pool_migration_fee": f.get("pool_migration_fee"),
        })
    # slots from CompleteEvent to migration, for migrations whose CompleteEvent is in an earlier tx
    lags = []
    for m in [m for m in migrations if not m["complete_same_tx"] and m.get("bonding_curve")][: ctx.n(100, 5)]:
        for e in ctx.signatures(m["bonding_curve"], max_total=20, before=m["sig"]):
            if e.get("err") is not None:
                continue
            tx = ctx.get_tx(e["signature"])
            if tx and any(ev.name == "CompleteEvent" and ev.fields.get("mint") == m["mint"] for ev in pump.events_in_tx(tx)):
                lags.append(m["slot"] - tx.slot)
                break
    n_mig = len(migrations)
    both_ok = counts["with_both_events"] == n_mig and n_mig > 0
    # ---- independent audit (PR-1) ----
    snap = snapshot(ctx)
    save_snapshot(ctx, snap)
    prev = previous_snapshot(ctx, min_age_s=int(ctx.dur(20 * 3600, 600)))
    audit = {"snapshot_errors": snap["errors"], "pools_now": len(snap["pools"] or {}),
             "complete_curves_now": len(snap["complete_curves"] or [])}
    new_canonical = []
    audit_ok = None
    if prev is None or snap["pools"] is None:
        audit["status"] = "PENDING: needs a second snapshot at least 20 h after this one (re-run A03 tomorrow)"
    else:
        known_pools = {m["pool"] for m in migrations if m.get("pool")}
        new_pools = sorted(set(snap["pools"]) - set(prev["pools"]))
        acc = ctx.multiple_accounts(new_pools)
        misses = []
        for p in new_pools:
            a = acc.get(p)
            if not a:
                continue
            try:
                pl = pump.decode_pool(pump.b64data(a))
            except Exception:  # noqa: BLE001
                misses.append({"pool": p, "class": "undecodable_pool"})
                continue
            if not pump.is_canonical_pool(pl):
                continue
            new_canonical.append(p)
            if p not in known_pools:
                misses.append({"pool": p, "class": f"quote={pl['quote_mint']} mayhem={pl.get('is_mayhem_mode')}"})
        curve_misses = []
        new_curves = sorted(set(snap["complete_curves"] or []) - set(prev.get("complete_curves") or []))
        sample = new_curves[: ctx.n(50, 5)]
        for cv in sample:
            mint = None
            for e in ctx.signatures(cv, max_total=5):
                tx = ctx.get_tx(e["signature"]) if e.get("err") is None else None
                if not tx:
                    continue
                for pix in pump.program_instructions(tx, (pump.PUMP_PROGRAM,)):
                    na = pump.named_accounts(pix)
                    if na.get("bonding_curve") == cv:
                        mint = na.get("mint") or na.get("base_mint")
                        break
                if mint:
                    break
            if mint is None:
                curve_misses.append({"curve": cv, "class": "mint_not_found"})
                continue
            pool = pump.canonical_pool_address(mint)
            if pool not in known_pools:
                exists = ctx.account(pool, data_slice={"offset": 0, "length": 0})
                if exists is not None:
                    curve_misses.append({"curve": cv, "mint": mint, "pool": pool, "class": "pool_exists_not_seen"})
        audit.update(status="DONE", interval_hours=round((snap["unix"] - prev["unix"]) / 3600, 1),
                     new_pools=len(new_pools), new_canonical_pools=len(new_canonical), pool_misses=misses[:100],
                     n_pool_misses=len(misses), new_complete_curves=len(new_curves), curves_sampled=len(sample),
                     curve_misses=curve_misses)
        audit_ok = not misses and not curve_misses
    ctx.store.save_artifacts(ctx.row, {"window_s": window_s, "migrations": migrations, "counts": counts, "odd": odd,
                                       "audit": audit, "audit_new_canonical_pools": new_canonical,
                                       "signers": signer_counts, "unknown_ix": unknown_names})
    nums = dict(counts)
    nums.update(migrations=n_mig, per_day=round(n_mig / (window_s / 86400), 1), distinct_signers=len(signer_counts),
                lag_slots_p50=_pct(lags, 0.5), lag_slots_p95=_pct(lags, 0.95), lag_samples=len(lags),
                synthetic_share=round(counts["synthetic_post_complete_buy"] / n_mig, 4) if n_mig else None,
                audit=audit)
    if not both_ok or audit_ok is False or counts["unknown_pump_ix"]:
        outcome = "FAIL"
    elif audit_ok is None:
        outcome = "INCOMPLETE: events check " + ("holds" if both_ok else "fails") + "; " + audit["status"]
    else:
        outcome = "PASS"
    return {"outcome": outcome,
            "headline": f"{n_mig} migrations in {window_s // 3600} h; both events in {counts['with_both_events']}; "
                        f"migrate {counts['migrate_ix']} / migrate_v2 {counts['migrate_v2_ix']}; audit: {audit.get('status')}",
            "numbers": nums,
            "follow_up": None if outcome == "PASS" else
            "If any migration lacks the authority or an event: make 'CompleteEvent -> derived pool' (DAT-6 key 2) the primary "
            "audit and re-run. If the audit is pending: re-run A03 after 20 h.",
            "notes": "Plan deviation: the '50 random CompleteEvents from Pump-program signatures' cross-check is done "
                     "through account snapshots (new PumpSwap Pool accounts and newly completed curves, diffed >= 20 h "
                     "apart), because ~1 Pump transaction in 10,000+ completes a curve and sampling signatures would cost "
                     "far more than the row budget. This is also red-team PR-1's independent audit."}


# ---- A04 -------------------------------------------------------------------------------------------
def a04(ctx) -> dict:
    n_each = ctx.n(5000, 150)
    stats = {"txs": 0, "successful": 0, "failed": 0, "log_truncated": 0, "trades": 0, "trades_with_event": 0,
             "trades_missing_event": 0, "failed_with_inner_events": 0, "failed_with_inner_instructions": 0,
             "program_data_log_lines": 0, "unknown_events": 0, "event_shape_errors": 0, "unknown_ix": 0,
             "event_prefix_cpis": 0}
    by_ix: dict = {}
    missing = []
    creates, amm_samples, lookups = [], [], []
    for program in (pump.PUMP_PROGRAM, pump.PUMPSWAP_PROGRAM):
        for e in ctx.signatures(program, max_total=n_each, commitment="finalized"):
            tx = ctx.get_tx(e["signature"], encoding="json")
            if tx is None:
                continue
            stats["txs"] += 1
            stats["log_truncated"] += tx.log_truncated
            stats["program_data_log_lines"] += len(program_data_logs(tx))
            if not tx.success:
                stats["failed"] += 1
                if any(tx.inner.values()):
                    stats["failed_with_inner_instructions"] += 1
                if any(ix.data[:8] == EVENT_PREFIX for ix in tx.all_ixs()):
                    stats["failed_with_inner_events"] += 1          # TS-6 / AR-T1 evidence; never used as trades
                continue
            stats["successful"] += 1
            for ev in pump.events_in_tx(tx):
                stats["event_prefix_cpis"] += 1
                if ev.name == "_UNKNOWN_EVENT":
                    stats["unknown_events"] += 1
                elif ev.name == "_SHAPE_ERROR":
                    stats["event_shape_errors"] += 1
                elif ev.name == "CreateEvent":
                    f = ev.fields
                    ixn = [p.name for p in pump.program_instructions(tx, (pump.PUMP_PROGRAM,))]
                    creates.append({"sig": tx.signature, "mint": f.get("mint"), "uri": f.get("uri"),
                                    "token_program": f.get("token_program"), "creator": f.get("creator"),
                                    "ix": [n for n in ixn if n in pump.CREATE_IXS], "buy_in_same_tx": any(n in pump.CURVE_TRADES for n in ixn),
                                    "is_mayhem_mode": f.get("is_mayhem_mode"), "slot": tx.slot})
            for p in pump.program_instructions(tx):
                if p.name.startswith("_UNKNOWN_IX"):
                    stats["unknown_ix"] += 1
                    continue
                is_trade = (p.program == pump.PUMP_PROGRAM and p.name in pump.CURVE_TRADES) or \
                           (p.program == pump.PUMPSWAP_PROGRAM and p.name in pump.AMM_TRADES)
                if not is_trade:
                    continue
                key = ("pump:" if p.program == pump.PUMP_PROGRAM else "amm:") + p.name
                by_ix.setdefault(key, [0, 0])
                by_ix[key][0] += 1
                stats["trades"] += 1
                ev = pump.trade_event(p)
                if ev is not None:
                    stats["trades_with_event"] += 1
                    by_ix[key][1] += 1
                else:
                    stats["trades_missing_event"] += 1
                    if len(missing) < 200:
                        missing.append({"sig": tx.signature, "ix": key, "top": p.ix.top_index, "inner": p.ix.inner_index})
                if p.program == pump.PUMPSWAP_PROGRAM and ev is not None and len(amm_samples) < 3000:
                    na = pump.named_accounts(p)
                    amm_samples.append({"sig": tx.signature, "ix": p.name, "pool": na.get("pool"), "user": na.get("user"),
                                        "signer": tx.signers[0] if tx.signers else None,
                                        "base_mint": na.get("base_mint")})
            if tx.lookups:
                mints = {ev.fields.get("mint") or ev.fields.get("base_mint") for ev in pump.events_in_tx(tx)
                         if ev.name in ("TradeEvent", "CreateEvent")}
                lookups.append({"sig": tx.signature, "tables": [t for t, _, _ in tx.lookups], "mints": sorted(m for m in mints if m)})
    ctx.store.save_artifacts(ctx.row, {"stats": stats, "by_ix": by_ix, "missing": missing, "creates": creates,
                                       "amm_samples": amm_samples, "lookups": lookups})
    ok = stats["trades"] > 0 and stats["trades_missing_event"] == 0
    share = round(stats["log_truncated"] / stats["txs"], 5) if stats["txs"] else None
    nums = dict(stats)
    nums.update(log_truncated_share=share, by_ix={k: f"{v[1]}/{v[0]}" for k, v in sorted(by_ix.items())})
    return {"outcome": "PASS" if ok else "FAIL",
            "headline": f"{stats['trades_with_event']}/{stats['trades']} trades carry their inner event; "
                        f"log truncated in {stats['log_truncated']}/{stats['txs']}; failed txs with inner events: "
                        f"{stats['failed_with_inner_events']}/{stats['failed']}",
            "numbers": nums,
            "follow_up": None if ok else "Add a 'Program data:' log fallback decoder with its own alarm",
            "notes": "failed_with_inner_events answers red-team TS-6/AR-T1 (do failed txs carry inner-instruction events?). "
                     "Failed txs are never decoded as trades."}


# ---- A05 -------------------------------------------------------------------------------------------
def _mint_info(acct: dict) -> dict:
    parsed = ((acct or {}).get("data") or {}).get("parsed") or {}
    info = parsed.get("info") or {}
    exts = [x.get("extension") for x in info.get("extensions") or []]
    return {"owner_program": (acct or {}).get("owner"), "mint_authority": info.get("mintAuthority"),
            "freeze_authority": info.get("freezeAuthority"), "extensions": exts, "decimals": info.get("decimals"),
            "space": (acct or {}).get("space")}


def a05(ctx) -> dict:
    a04 = ctx.artifacts("A04")
    creates = a04.get("creates", [])
    v2 = [c["mint"] for c in creates if "create_v2" in c["ix"] and c.get("mint")][: ctx.n(100, 10)]
    v1 = [c["mint"] for c in creates if "create" in c["ix"] and c.get("mint")][: ctx.n(20, 3)]
    infos = ctx.multiple_accounts(v2 + v1, encoding="jsonParsed")
    rows = {m: _mint_info(infos.get(m)) for m in v2 + v1}
    auth_null = all(r["mint_authority"] is None and r["freeze_authority"] is None for r in rows.values()) and bool(rows)
    bad_ext = {m: [x for x in r["extensions"] if x in DANGEROUS_EXTENSIONS] for m, r in rows.items()}
    bad_ext = {m: v for m, v in bad_ext.items() if v}
    ext_seen: dict = {}
    for r in rows.values():
        for x in r["extensions"]:
            ext_seen[x] = ext_seen.get(x, 0) + 1
    progs = {"create_v2": {}, "create": {}}
    for m in v2:
        p = rows[m]["owner_program"]
        progs["create_v2"][p] = progs["create_v2"].get(p, 0) + 1
    for m in v1:
        p = rows[m]["owner_program"]
        progs["create"][p] = progs["create"].get(p, 0) + 1
    # graduates' token programs
    a03 = ctx.store.load_artifacts("A03") or {}
    grads = [m["mint"] for m in a03.get("migrations", []) if m.get("mint")][: ctx.n(300, 10)]
    ginfo = ctx.multiple_accounts(grads, encoding="jsonParsed")
    grad_progs: dict = {}
    for m in grads:
        p = ((ginfo.get(m) or {}).get("owner"))
        grad_progs[p] = grad_progs.get(p, 0) + 1
    # holders' token-account sizes and plain transfer vs transferChecked, on graduated coins
    sizes, transfer_kinds = [], {"transfer": 0, "transferChecked": 0}
    for mint in grads[: ctx.n(10, 2)]:
        top = (ctx.call("getTokenLargestAccounts", [mint, {"commitment": "confirmed"}]) or {}).get("value") or []
        holders = [t["address"] for t in top[:5]]
        acc = ctx.multiple_accounts(holders, data_slice={"offset": 0, "length": 0})
        sizes += [(acc.get(h) or {}).get("space") for h in holders if acc.get(h)]
        for h in holders:
            for e in ctx.signatures(h, max_total=ctx.n(20, 3)):
                if e.get("err") is not None:
                    continue
                tx = ctx.get_tx(e["signature"])
                for o in token_ops(tx) if tx else []:
                    if o["kind"] in transfer_kinds and h in (o.get("source"), o.get("dest")):
                        transfer_kinds[o["kind"]] += 1
    sizes = [s for s in sizes if s is not None]
    size_counts: dict = {}
    for s in sizes:
        size_counts[s] = size_counts.get(s, 0) + 1
    ok = auth_null and not bad_ext
    return {"outcome": "PASS" if ok else "FAIL",
            "headline": f"{len(rows)} mints: authorities null={auth_null}; risky extensions on {len(bad_ext)}; "
                        f"token-account sizes {size_counts}",
            "numbers": {"create_v2_token_program": progs["create_v2"], "create_token_program": progs["create"],
                        "graduates_token_program": grad_progs, "extensions_seen": ext_seen, "risky_extensions": bad_ext,
                        "authorities_null_all": auth_null, "holder_account_sizes": size_counts,
                        "transfer_kinds_on_top_holders": transfer_kinds},
            "follow_up": None if ok else "Add a coin-safety veto before Phase 3 (fee-model FC5)"}


# ---- A06 -------------------------------------------------------------------------------------------
def a06(ctx) -> dict:
    a03 = ctx.artifacts("A03")
    migs = [m for m in a03.get("migrations", []) if m.get("pool") and m.get("mint")][: ctx.n(20, 3)]
    rows, ok_n = [], 0
    pools = ctx.multiple_accounts([m["pool"] for m in migs])
    for m in migs:
        rec = {"sig": m["sig"], "pool": m["pool"]}
        derived = pump.canonical_pool_address(m["mint"], m.get("quote_mint") or pump.WSOL_MINT)
        rec["derived_equal"] = derived == m["pool"]
        a = pools.get(m["pool"])
        if not a:
            rec["error"] = "pool account missing"
            rows.append(rec)
            continue
        pl = pump.decode_pool(pump.b64data(a))
        rec.update(index=pl.get("index"), canonical_creator=pump.is_canonical_pool(pl), lp_mint=pl.get("lp_mint"),
                   lp_supply_field=pl.get("lp_supply"), layout_len=pl["_len"])
        sup = (ctx.call("getTokenSupply", [pl["lp_mint"], {"commitment": "confirmed"}]) or {}).get("value") or {}
        rec["lp_mint_supply_now"] = int(sup.get("amount", 0)) if sup else None
        top = (ctx.call("getTokenLargestAccounts", [pl["lp_mint"], {"commitment": "confirmed"}]) or {}).get("value") or []
        rec["lp_top_holder_amounts"] = [int(t.get("amount", 0)) for t in top[:3]]
        tx = ctx.get_tx(m["sig"])
        burns = [o for o in token_ops(tx) if o["kind"] in ("burn", "burnChecked") and o.get("mint") == pl["lp_mint"]] if tx else []
        rec["lp_burned_in_migration_tx"] = sum(o["amount"] or 0 for o in burns)
        rec["ok"] = rec["derived_equal"] and pl.get("index") == 0 and rec["canonical_creator"] and bool(burns)
        ok_n += rec["ok"]
        rows.append(rec)
    ok = ok_n == len(migs) and migs
    return {"outcome": "PASS" if ok else "FAIL", "headline": f"{ok_n}/{len(migs)} canonical, index 0, LP burned in the migration tx",
            "numbers": {"checked": len(migs), "ok": ok_n, "rows": rows},
            "follow_up": None if ok else "Learn and pin the creator used for migrated pools (DAT-6), then re-derive"}


# ---- A07 -------------------------------------------------------------------------------------------
def a07(ctx) -> dict:
    allowed = pump.pool_allowed_lengths()
    d = _snap_dir(ctx)
    latest = None
    if os.path.isdir(d):
        names = sorted(os.listdir(d))
        if names:
            with gzip.open(os.path.join(d, names[-1]), "rt", encoding="utf-8") as f:
                latest = json.load(f)
    if latest is None or latest.get("pools") is None:
        snap = snapshot(ctx)
        save_snapshot(ctx, snap)
        latest = snap
    lengths: dict = {}
    missing_space = 0
    for k, sp in (latest.get("pools") or {}).items():
        if sp is None:
            missing_space += 1
        else:
            lengths[sp] = lengths.get(sp, 0) + 1
    if missing_space and not lengths:
        amm = pump.load_decoders()["pump_amm"]
        disc = b58encode(amm.account_disc["Pool"])
        for n in allowed:
            keys, _ = _gpa_keys(ctx, pump.PUMPSWAP_PROGRAM, [{"memcmp": {"offset": 0, "bytes": disc}}, {"dataSize": n}])
            lengths[n] = len(keys)
    unknown = {n: c for n, c in lengths.items() if n not in allowed}
    # decode a few accounts of each length exactly
    decode_ok = True
    by_len_keys: dict = {}
    for k, sp in (latest.get("pools") or {}).items():
        if sp is not None and len(by_len_keys.setdefault(sp, [])) < 3:
            by_len_keys[sp].append(k)
    samples = ctx.multiple_accounts([k for ks in by_len_keys.values() for k in ks])
    decode_notes = {}
    for sp, ks in by_len_keys.items():
        for k in ks:
            a = samples.get(k)
            if not a:
                continue
            try:
                pl = pump.decode_pool(pump.b64data(a))
                tail = pump.b64data(a)[pl["_consumed"]:]
                if any(tail):
                    decode_ok = False
                    decode_notes[k] = "non-zero bytes after the last IDL field"
            except Exception as e:  # noqa: BLE001
                decode_ok = False
                decode_notes[k] = str(e)
    # RC3: virtual_quote_reserves on recent pools, by age since migration
    a03 = ctx.store.load_artifacts("A03") or {}
    migs = [m for m in a03.get("migrations", []) if m.get("pool")][: ctx.n(200, 10)]
    accs = ctx.multiple_accounts([m["pool"] for m in migs])
    now = ctx.now()
    buckets = {"age_lt_10min": [], "age_ge_10min": []}
    for m in migs:
        a = accs.get(m["pool"])
        if not a:
            continue
        pl = pump.decode_pool(pump.b64data(a))
        age = now - (m.get("block_time") or now)
        buckets["age_lt_10min" if age < 600 else "age_ge_10min"].append(int(pl.get("virtual_quote_reserves") or 0))
    vqr = {k: {"n": len(v), "negative": sum(x < 0 for x in v), "zero": sum(x == 0 for x in v),
               "positive": sum(x > 0 for x in v), "min": min(v) if v else None, "max": max(v) if v else None}
           for k, v in buckets.items()}
    ok = bool(lengths) and not unknown and decode_ok
    return {"outcome": "PASS" if ok else "FAIL",
            "headline": f"pool lengths {dict(sorted(lengths.items()))}; unknown {unknown or 'none'}; vqr {vqr}",
            "numbers": {"lengths": lengths, "allowed_lengths": allowed, "unknown_lengths": unknown,
                        "decode_ok": decode_ok, "decode_notes": decode_notes, "vqr": vqr,
                        "snapshot_utc": latest.get("utc")},
            "follow_up": None if ok else "Add a reviewed version entry for each new length",
            "notes": "Counts only accounts with the Pool discriminator (an unfiltered program scan would also return "
                     "every UserVolumeAccumulator and could be very large). 'During BOOST' pools are only present if "
                     "A03 found migrations under 10 minutes old at read time."}


# ---- A08 -------------------------------------------------------------------------------------------
def _feature(acct: "dict | None") -> dict:
    if acct is None:
        return {"exists": False}
    raw = pump.b64data(acct)
    if not raw:
        return {"exists": True, "activated_at": None}
    if raw[0] == 1 and len(raw) >= 9:
        return {"exists": True, "activated_at": int.from_bytes(raw[1:9], "little")}
    return {"exists": True, "activated_at": None, "pending": True}


def a08(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    with open(CAPTURE, "r", encoding="ascii") as f:
        cap = base64.b64decode(f.read().strip())
    live_acct = ctx.account(pump.PUMPSWAP_FEE_CONFIG, client=client)
    live = pump.b64data(live_acct) if live_acct else b""
    cap_d = pump.decode_fee_config(cap)
    live_d = pump.decode_fee_config(live) if live else None

    def view(d):
        return {k: d.get(k) for k in ("bump", "admin", "flat_fees", "fee_tiers", "stable_fee_tiers", "exotic_flat_fees")}
    same_bytes = live == cap
    same_values = live_d is not None and view(live_d) == view(cap_d)
    diffs = []
    if live_d is not None and not same_values:
        for k in ("bump", "admin", "flat_fees", "fee_tiers", "stable_fee_tiers", "exotic_flat_fees"):
            if live_d.get(k) != cap_d.get(k):
                diffs.append(k)
    gc_acct = ctx.account(pump.PUMPSWAP_GLOBAL_CONFIG, client=client)
    gc = pump.decode_global_config(pump.b64data(gc_acct)) if gc_acct else {}
    flags = int(gc.get("disable_flags") or 0)
    buy_disabled, sell_disabled = bool(flags & (1 << 3)), bool(flags & (1 << 4))
    curve_acct = ctx.account(pump.CURVE_FEE_CONFIG, client=client)
    curve = pump.decode_fee_config(pump.b64data(curve_acct)) if curve_acct else None
    rent = {n: ctx.call("getMinimumBalanceForRentExemption", [n], client=client) for n in (165, 170)}
    lpb = {n: (v // (128 + n) if v else None) for n, v in rent.items()}
    gates = {k: _feature(v) for k, v in ctx.multiple_accounts(list(pump.RENT_GATES), client=client).items()}
    # opening pool sizes from A03's CreatePoolEvents (exact), and today's vault balances of the 50 freshest pools
    a03 = ctx.store.load_artifacts("A03") or {}
    migs = sorted([m for m in a03.get("migrations", []) if m.get("pool")], key=lambda m: -(m.get("slot") or 0))[: ctx.n(50, 5)]
    opening = [(m["create_pool"] or {}).get("pool_quote_amount") for m in migs if m.get("create_pool")]
    opening_base = [(m["create_pool"] or {}).get("pool_base_amount") for m in migs if m.get("create_pool")]
    # user_volume_accumulator size for 3 wallets
    a04 = ctx.store.load_artifacts("A04") or {}
    users = []
    for s in a04.get("amm_samples", []):
        if s.get("user") and s["user"] not in users:
            users.append(s["user"])
        if len(users) >= 3:
            break
    uva = ctx.multiple_accounts([pump.user_volume_accumulator(u) for u in users], data_slice={"offset": 0, "length": 0}, client=client)
    uva_sizes = {k: ((v or {}).get("space"), (v or {}).get("lamports")) for k, v in uva.items()}
    tips = (ctx.store.load_artifacts("A19") or {}).get("tip_accounts") or []
    ok = bool(live) and same_values and not buy_disabled and not sell_disabled
    ctx.store.save_artifacts(ctx.row, {"fee_config": live_d or cap_d, "fee_config_source": "live" if live_d else "capture",
                                       "global_config": gc, "curve_fee_config": curve, "rent": rent, "tip_accounts": tips,
                                       "fetched_utc": utc_now()})
    return {"outcome": "PASS" if ok else "FAIL",
            "headline": f"FeeConfig {'identical to' if same_bytes else ('same values as' if same_values else 'DIFFERS from')} the "
                        f"2026-09-08 capture; buy/sell disabled={buy_disabled}/{sell_disabled}; boost_enabled={gc.get('boost_enabled')}; "
                        f"rent 165B={rent.get(165)}",
            "numbers": {"fee_config_len": len(live), "same_bytes": same_bytes, "same_values": same_values, "diff_fields": diffs,
                        "global_config": {k: gc.get(k) for k in ("disable_flags", "boost_enabled", "buyback_basis_points",
                                                                 "creator_fee_configurable", "max_configurable_creator_fee_bps",
                                                                 "lp_fee_basis_points", "protocol_fee_basis_points",
                                                                 "coin_creator_fee_basis_points", "admin", "is_cashback_enabled",
                                                                 "mayhem_mode_enabled")},
                        "buyback_fee_recipients": gc.get("buyback_fee_recipients"),
                        "curve_fee_config_tiers": len((curve or {}).get("fee_tiers") or []),
                        "curve_flat_fees": (curve or {}).get("flat_fees"),
                        "rent": rent, "implied_lamports_per_byte": lpb, "rent_gates": gates,
                        "opening_quote_lamports_p50": statistics.median(opening) if opening else None,
                        "opening_base_raw_p50": statistics.median(opening_base) if opening_base else None,
                        "opening_samples": len(opening), "user_volume_accumulator": uva_sizes,
                        "tip_accounts_known": len(tips)},
            "follow_up": None if ok else "Update docs/fee-model.md and the fee module, bump the version, BEFORE A09"}
