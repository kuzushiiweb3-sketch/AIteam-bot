"""Live polling rows over HTTP JSON-RPC: A12 (slot time, processed vs confirmed) and A14 (blockhash life).

A12's websocket leg (slotSubscribe for 1 h) is a Rust probe for crates/feed/examples/, later.
"""

from __future__ import annotations

import statistics
import time


def _pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


def a12(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    samples = ctx.call("getRecentPerformanceSamples", [60], client=client) or []
    slot_ms = [s["samplePeriodSecs"] * 1000 / s["numSlots"] for s in samples if s.get("numSlots")]
    gaps, polls = [], 0
    end = time.time() + ctx.dur(600, 20)
    target_interval = 0.2            # 5 polls a second if the rate limit allows (2 calls per poll)
    while time.time() < end:
        t0 = time.time()
        p = ctx.call("getSlot", [{"commitment": "processed"}], client=client)
        c = ctx.call("getSlot", [{"commitment": "confirmed"}], client=client)
        if isinstance(p, int) and isinstance(c, int):
            gaps.append(p - c)
        polls += 1
        rest = target_interval - (time.time() - t0)
        if rest > 0:
            time.sleep(rest)
    duration = ctx.dur(600, 20)
    med = statistics.median(slot_ms) if slot_ms else None
    flag = med is not None and med > 300
    return {"outcome": "PARTIAL: HTTP legs measured; slotSubscribe leg is a Rust probe, later",
            "headline": f"median slot {round(med, 1) if med else None} ms; processed-confirmed gap p50/p95 {_pct(gaps, 0.5)}/{_pct(gaps, 0.95)} slots",
            "numbers": {"slot_ms_p50": round(med, 1) if med else None, "slot_ms_p95": round(_pct(slot_ms, 0.95), 1) if slot_ms else None,
                        "samples": len(slot_ms), "gap_p50": _pct(gaps, 0.5), "gap_p95": _pct(gaps, 0.95),
                        "gap_max": max(gaps) if gaps else None, "polls": polls,
                        "achieved_polls_per_s": round(polls / duration, 2), "median_slot_over_300ms": flag},
            "notes": "The plan asks for 5 polls a second; with 2 calls per poll and the 8 requests/s cap, the achieved "
                     "rate is shown above.",
            "follow_up": "Re-derive every slot-based timer from the median." + (" FLAG: median slot > 300 ms." if flag else "")}


def a14(ctx) -> dict:
    client = ctx.rpc(fallback_ok=True)
    held = []                 # (blockhash, height at fetch, lastValidBlockHeight)
    checks = {100: [], 130: [], 140: [], 150: [], 155: []}
    windows = []
    end = time.time() + ctx.dur(3600, 120)
    while time.time() < end:
        lb = (ctx.call("getLatestBlockhash", [{"commitment": "confirmed"}], client=client) or {}).get("value") or {}
        h = ctx.call("getBlockHeight", [{"commitment": "confirmed"}], client=client)
        if lb.get("blockhash") and isinstance(h, int):
            held.append((lb["blockhash"], h, lb.get("lastValidBlockHeight")))
            if lb.get("lastValidBlockHeight"):
                windows.append(lb["lastValidBlockHeight"] - h)
            for bh, h0, _ in held:
                age = h - h0
                for target in checks:
                    if abs(age - target) <= 5 and not any(x[0] == bh for x in checks[target]):
                        v = (ctx.call("isBlockhashValid", [bh, {"commitment": "confirmed"}], client=client) or {}).get("value")
                        checks[target].append((bh, age, v))
        time.sleep(10 if not ctx.opts.quick else 5)
    valid_at = {k: {"checked": len(v), "valid": sum(1 for x in v if x[2])} for k, v in checks.items()}
    still_valid = [x[1] for v in checks.values() for x in v if x[2]]
    return {"outcome": "MEASURED",
            "headline": f"lastValidBlockHeight - height p50 {_pct(windows, 0.5)} blocks; oldest age still valid {max(still_valid) if still_valid else None}",
            "numbers": {"window_blocks_p50": _pct(windows, 0.5), "window_blocks_min": min(windows) if windows else None,
                        "validity_by_age": valid_at, "polls": len(held)},
            "follow_up": "Set the exit-ticket expiry below the measured window, with a margin."}
