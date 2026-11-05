"""Rows added by docs/tech-stack.md v1.1 s.12: AR-T1 (failed transactions and events), TS-T2 (on-chain IDL
accounts as a second witness of the GitHub pin), TS-T3 (optional: the silent-feed probe's window and cost).
All read-only.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import zlib

from p0 import pump
from p0.b58 import b58decode, b58encode, pubkey_bytes
from p0.budget import FREE_PLAN_MONTHLY_CREDITS
from p0.clock import clock_sync_status, now_ns
from p0.pda import create_with_seed, find_program_address
from p0.redact import REDACTOR
from p0.txparse import EVENT_PREFIX, program_data_logs

PROGRAM_METADATA = "ProgM6JCCvbYkfKqJYHePx4xxSUSqJp7rh8Lyv7nk7S"     # [VERIFIED-DOC tech-stack v1.1 s.1]
MAX_IDL_BYTES = 20 * 1024 * 1024


def _pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


def _fail_index(tx):
    err = tx.err
    if isinstance(err, dict) and "InstructionError" in err:
        ie = err["InstructionError"]
        detail = ie[1] if len(ie) > 1 else None
        code = detail.get("Custom") if isinstance(detail, dict) else detail
        return ie[0], code
    return None, (json.dumps(err) if err is not None else None)


# ---- AR-T1 -----------------------------------------------------------------------------------------
def ar_t1(ctx) -> dict:
    """Do RPC responses for FAILED Pump / PumpSwap trades carry inner event self-calls and 'Program data:' logs?"""
    target = ctx.n(20, 3)
    picked, summary = [], {}
    for label, program, names in (("pumpswap", pump.PUMPSWAP_PROGRAM, pump.AMM_TRADES),
                                  ("pump", pump.PUMP_PROGRAM, pump.CURVE_TRADES)):
        cands = []
        for e in ctx.signatures(program, max_total=ctx.n(6000, 400)):
            if e.get("err") is None:
                continue
            tx = ctx.get_tx(e["signature"], encoding="json")
            if tx is None:
                continue
            trades = [p for p in pump.program_instructions(tx, (program,)) if p.name in names]
            if not trades:
                continue
            fidx, code = _fail_index(tx)
            ttop = trades[0].ix.top_index
            pos = None if fidx is None else ("after_trade" if fidx > ttop else "at_trade" if fidx == ttop else "before_trade")
            sc = pump.scan(tx)
            cands.append({"sig": tx.signature, "program": label, "trade_ix": [p.name for p in trades],
                          "trade_top_index": ttop, "trade_is_cpi": trades[0].ix.inner_index is not None,
                          "fail_index": fidx, "error": code, "position": pos,
                          "inner_instructions_returned": not tx.no_inner_ix,
                          "inner_instruction_count": sum(len(v) for v in tx.inner.values()),
                          "event_self_calls": sum(1 for ix in tx.all_ixs() if ix.data[:8] == EVENT_PREFIX
                                                  and ix.program in pump.PROGRAMS.values()),
                          "FAILED_TX_EVENT": len(sc.failed_events),
                          "program_data_log_lines": len(program_data_logs(tx)),
                          "log_truncated": tx.log_truncated})
            after = [c for c in cands if c["position"] == "after_trade"]
            if len(cands) >= 4 * target and len(after) >= target // 2:
                break
        after = [c for c in cands if c["position"] == "after_trade"][: max(1, target // 2)]
        rest = [c for c in cands if c not in after][: target - len(after)]
        chosen = after + rest
        picked += chosen
        summary[label] = {"failed_trades": len(chosen), "scanned_candidates": len(cands),
                          "failures_after_the_trade": sum(1 for c in chosen if c["position"] == "after_trade"),
                          "with_event_self_calls": sum(1 for c in chosen if c["event_self_calls"]),
                          "with_program_data_logs": sum(1 for c in chosen if c["program_data_log_lines"]),
                          "inner_instructions_not_returned": sum(1 for c in chosen if not c["inner_instructions_returned"])}
    d = os.path.join(ctx.store.fixtures_dir, "AR-T1")
    os.makedirs(d, exist_ok=True)
    with gzip.open(os.path.join(d, "failed_trades.jsonl.gz"), "wt", encoding="utf-8") as f:
        for c in picked:
            raw = ctx.store.cache_get("tx-json", c["sig"])
            line = json.dumps({"summary": c, "raw_tx": raw}, separators=(",", ":"))
            REDACTOR.assert_clean(line, where="AR-T1 fixtures")
            f.write(line + "\n")
    ctx.store.save_artifacts(ctx.row, {"failed_trades": picked, "summary": summary})
    any_events = any(s["with_event_self_calls"] for s in summary.values())
    return {"outcome": "MEASURED",
            "headline": "; ".join(f"{k}: events in {v['with_event_self_calls']}/{v['failed_trades']}, Program data in "
                                  f"{v['with_program_data_logs']}, failed after the trade {v['failures_after_the_trade']}"
                                  for k, v in summary.items()),
            "numbers": summary,
            "follow_up": ("Events ARE returned for failed transactions: replace the synthetic hostile fixture "
                          "failed_tx_full_buyevent with a real one from fixtures/phase0/AR-T1/." if any_events else
                          "No events returned for failed transactions here; the F1 rule stays anyway (cheap)."),
            "notes": "Measured, not pass/fail. Repeat on 5 of them through the Chainstack stream in C01."}


# ---- TS-T2 -----------------------------------------------------------------------------------------
def canonical_sha256(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _inflate(data: bytes, kind: str) -> bytes:
    d = zlib.decompressobj(wbits=31 if kind == "gzip" else 15)
    out = d.decompress(data, MAX_IDL_BYTES)
    if d.unconsumed_tail:
        raise ValueError("IDL larger than the size cap")
    return out


def anchor_idl_address(program: str) -> str:
    """Anchor legacy IDL account: create_with_seed(find_program_address([], P), "anchor:idl", P)."""
    base = find_program_address([], program)[0]
    return create_with_seed(base, "anchor:idl", program)


def program_metadata_idl_addresses(program: str) -> dict:
    """Canonical Program Metadata 'idl' PDA, seeds [program, seed] [VERIFIED-DOC program-metadata README].
    Whether the seed is the bare 'idl' or the 16-byte zero-padded buffer is [UNVERIFIED]; both are derived."""
    pk = pubkey_bytes(program)
    return {"seed_bare": find_program_address([pk, b"idl"], PROGRAM_METADATA)[0],
            "seed_padded16": find_program_address([pk, b"idl" + bytes(13)], PROGRAM_METADATA)[0]}


def decode_anchor_idl_account(raw: bytes) -> dict:
    """8-byte tag, authority (32), data_len (u32), zlib JSON [VERIFIED-DOC anchor lang/src/idl.rs via tech-stack]."""
    if len(raw) < 44:
        raise ValueError("account shorter than the Anchor IDL header")
    n = int.from_bytes(raw[40:44], "little")
    body = raw[44:44 + n]
    if len(body) != n:
        raise ValueError("data_len runs past the end of the account")
    return {"authority": b58encode(raw[8:40]), "data_len": n, "json": json.loads(_inflate(body, "zlib"))}


def decode_program_metadata_account(raw: bytes) -> dict:
    """96-byte header [VERIFIED-DOC solana-program/program-metadata program/src/state/header.rs]."""
    if len(raw) < 96:
        raise ValueError("account shorter than the 96-byte Program Metadata header")
    auth = raw[33:65]
    h = {"discriminator": raw[0], "program": b58encode(raw[1:33]),
         "authority": None if not any(auth) else b58encode(auth), "mutable": raw[65], "canonical": raw[66],
         "seed": raw[67:83].rstrip(b"\0").decode("utf-8", "replace"), "encoding": raw[83], "compression": raw[84],
         "format": raw[85], "data_source": raw[86], "data_length": int.from_bytes(raw[87:91], "little")}
    data = raw[96:96 + h["data_length"]]
    if h["data_source"] != 0:
        h["source_text"] = data.decode("utf-8", "replace")[:500]          # a URL or external pointer
        return h
    if h["encoding"] == 2:
        data = b58decode(data.decode("ascii"))
    elif h["encoding"] == 3:
        data = base64.b64decode(data)
    if h["compression"] == 1:
        data = _inflate(data, "gzip")
    elif h["compression"] == 2:
        data = _inflate(data, "zlib")
    if h["format"] == 1:
        h["json"] = json.loads(data)
    else:
        h["raw_text"] = data.decode("utf-8", "replace")[:500]
    return h


def pinned_idl_hashes() -> dict:
    out = {}
    for name, dec in pump.load_decoders().items():
        out[name] = canonical_sha256(dec.idl)
    return out


def ts_t2(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    pinned = pinned_idl_hashes()
    rows, verdicts = {}, {}
    for name, pid in pump.PROGRAMS.items():
        anchor = anchor_idl_address(pid)
        pmd = program_metadata_idl_addresses(pid)
        accts = ctx.multiple_accounts([anchor] + list(pmd.values()), client=client)
        rec = {"anchor_idl_address": anchor, "program_metadata_addresses": pmd, "pinned_canonical_sha256": pinned[name]}
        found = []
        a = accts.get(anchor)
        if a:
            try:
                d = decode_anchor_idl_account(pump.b64data(a))
                h = canonical_sha256(d["json"])
                rec["anchor"] = {"authority": d["authority"], "canonical_sha256": h, "matches_pin": h == pinned[name],
                                 "owner": a.get("owner"), "metadata": d["json"].get("metadata")}
                found.append(h == pinned[name])
            except Exception as e:  # noqa: BLE001 - recorded
                rec["anchor"] = {"present": True, "decode_error": str(e)}
        else:
            rec["anchor"] = {"present": False}
        for label, addr in pmd.items():
            v = accts.get(addr)
            if not v:
                rec[f"program_metadata_{label}"] = {"present": False}
                continue
            try:
                d = decode_program_metadata_account(pump.b64data(v))
                if "json" in d:
                    h = canonical_sha256(d.pop("json"))
                    d.update(canonical_sha256=h, matches_pin=h == pinned[name])
                    found.append(h == pinned[name])
                rec[f"program_metadata_{label}"] = d
            except Exception as e:  # noqa: BLE001
                rec[f"program_metadata_{label}"] = {"present": True, "decode_error": str(e)}
        verdicts[name] = "absent" if not found else ("match" if all(found) else "MISMATCH")
        rows[name] = rec
    mism = [k for k, v in verdicts.items() if v == "MISMATCH"]
    return {"outcome": "MEASURED" + (f": MISMATCH on {', '.join(mism)} (alarm; review which copy is right)" if mism else ""),
            "headline": ", ".join(f"{k}: {v}" for k, v in verdicts.items()),
            "numbers": {"verdicts": verdicts, "programs": rows},
            "notes": "A second witness for the GitHub IDL pin (A-005). 'absent' is recorded; the ProgramData deploy slot "
                     "(A02) then stays the second witness. A mismatch can also be a format difference (an older IDL spec), "
                     "so a human compares the two before acting.",
            "follow_up": "Watch both accounts hourly alongside the ProgramData deploy slot (tech-stack s.5e)."}


# ---- TS-T3 (optional) --------------------------------------------------------------------------------
def ts_t3(ctx) -> dict:
    sync = clock_sync_status()
    per = {"pumpswap": {"full_slots": [], "pages_for_60s": [], "calls": 0},
           "pump": {"full_slots": [], "pages_for_60s": [], "calls": 0}}
    credits0 = ctx.budget.data["credits_est"]
    duration_ns = int(ctx.dur(3600, 120) * 1e9)
    start = now_ns()
    while now_ns() - start < duration_ns:
        t_poll = now_ns()
        for label, program in (("pumpswap", pump.PUMPSWAP_PROGRAM), ("pump", pump.PUMP_PROGRAM)):
            page = ctx.call("getSignaturesForAddress", [program, {"limit": 1000, "commitment": "confirmed"}]) or []
            per[label]["calls"] += 1
            if not page:
                continue
            slots = [e["slot"] for e in page if e.get("slot") is not None]
            newest, oldest = max(slots), min(slots)
            per[label]["full_slots"].append(newest - oldest)        # the oldest slot of a full page may be cut
            depth, cursor_oldest, cursor = 1, oldest, page[-1]["signature"]
            while newest - cursor_oldest < 150 and depth < 10:      # ~60 s of slots at ~400 ms
                more = ctx.call("getSignaturesForAddress", [program, {"limit": 1000, "commitment": "confirmed",
                                                                      "before": cursor}]) or []
                per[label]["calls"] += 1
                if not more:
                    break
                depth += 1
                cursor_oldest = min(e["slot"] for e in more if e.get("slot") is not None)
                cursor = more[-1]["signature"]
            per[label]["pages_for_60s"].append(depth)
        rest = 60e9 - (now_ns() - t_poll) if not ctx.opts.quick else 20e9 - (now_ns() - t_poll)
        if rest > 0 and now_ns() - start + rest < duration_ns:
            import time
            time.sleep(rest / 1e9)
        elif now_ns() - start + max(rest, 0) >= duration_ns:
            break
    minutes = max(1e-9, (now_ns() - start) / 6e10)
    calls = sum(v["calls"] for v in per.values())
    credits = ctx.budget.data["credits_est"] - credits0
    month_calls = calls / minutes * 43_200
    month_credits = credits / minutes * 43_200
    share = month_credits / FREE_PLAN_MONTHLY_CREDITS
    summary = {k: {"full_slots_p50": _pct(v["full_slots"], 0.5), "full_slots_min": min(v["full_slots"]) if v["full_slots"] else None,
                   "pages_for_60s_p50": _pct(v["pages_for_60s"], 0.5), "pages_for_60s_max": max(v["pages_for_60s"]) if v["pages_for_60s"] else None,
                   "calls": v["calls"]} for k, v in per.items()}
    return {"outcome": "MEASURED", "headline": f"probe ≈ {round(month_calls)} calls / {round(month_credits)} est. credits a month "
                                               f"({round(share * 100, 2)}% of the free plan)",
            "numbers": {"per_program": summary, "calls": calls, "est_credits": credits,
                        "projected_monthly_calls": round(month_calls), "projected_monthly_credits_est": round(month_credits),
                        "share_of_free_plan": round(share, 4)},
            "provenance": {"interval_clock": "time.monotonic_ns", "clock_sync_before": sync, "clock_sync_after": clock_sync_status()},
            "notes": "Credits are our estimate (1 per call until A24 prices it). The overlap with the Chainstack tape is a tier C step.",
            "follow_up": "The probe stays if it costs <= 5% of the monthly credit budget (CO-7a)."}
