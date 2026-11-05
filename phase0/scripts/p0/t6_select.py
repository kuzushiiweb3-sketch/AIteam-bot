"""T6 Step 0: the FROZEN part — pass criteria, strata and the seeded selection rules.

docs/fee-model.md s.7 Step 0: "commit the selection script and its random seed, the model version,
and the pass criteria, dated, before looking at any trade". The SHA-256 of THIS FILE is written to
phase0/scripts/t6_freeze.json by `run_tier_a.py --t6-freeze`. Row A09 refuses to fetch anything if
the file's hash or the seed no longer match the freeze (check P7).

Every random choice is "sort by SHA-256(seed | purpose | item)". That ordering depends only on the
seed and the item, never on fetch order, timing or any scored outcome.

T6_SPEC holds fee-model.md s.7 (v1.0) and, separately marked, red-team's FM-3 / FM-4 / FM-5 additions
(team-debate/phase0/red-team-phase0-review.md), which fee-model.md v1.1 is expected to adopt. When
v1.1 is final: edit T6_SPEC to match it, then re-freeze with a new seed (the old freeze becomes void).
"""

from __future__ import annotations

import hashlib

T6_SPEC = {
    "spec_source": "docs/fee-model.md s.7 v1.0 (2026-11-05) + red-team FM-3/FM-4/FM-5 proposals (pending v1.1)",
    "calibration_trades": 50,          # Step 1: not scored
    "calibration_max": 150,            # extra calibration trades allowed if a semantics dimension is not exercised
    "test_trades": 500,                # Step 2
    "min_pools": 100,
    "min_days": 7,
    "strata": {                        # Step 2 minimum strata (one trade can count in several)
        "tier_cross": 50,              # pre and post market cap in different tiers, or pre within +-1% of a threshold
        "v2": 50,
        "v1": 50,
        "v1_buy_sol": 25,
        "sell": 100,
        "buy": 100,
        "buy_exact_in": 50,
        "vqr_negative": 30,
        "can_boost": 30,
        "tier_ge_2": 20,
    },
    "tier_cross_sides_of_lamports": 420_000_000_000,   # both sides of 420 SOL must be represented
    "p4_min_trades": 400,
    "p5_min_pairs": 200,
    "p6_min_txs": 100,
    "p6_min_failed": 30,
    # ---- red-team additions (reported as their own checks until fee-model v1.1 freezes them) ----
    "fm3_min_failed_trades": 50,       # failed with 6004 / 6040 / 6063; fail-or-succeed predicted 100%
    "fm3_min_near_limit": 50,          # successes whose limit was within 0.5% of the amount paid
    "fm3_near_limit_bps": 50,
    "fm4_min_same_slot_pairs": 50,     # ordered by position in the block
    "fm4_min_multihop_between": 30,
    "fm4_min_boost_between": 30,
    "fm5_universe": "independent audit (PR-1) when available, else the withdraw-authority scan, labelled",
    # ---- sampling sizes (part of the frozen script) ----
    "sig_pages_per_pool": 2,
    "trades_per_pool_first_pass": 6,
    "failed_per_pool": 2,
    "pair_fraction": 0.5,              # half of the sampled trades also fetch their next state change (P5)
    "topup_passes": 2,
    "topup_trades_per_pool": 6,
}


def h(seed: str, purpose: str, item: str) -> str:
    return hashlib.sha256(f"{seed}|{purpose}|{item}".encode("utf-8")).hexdigest()


def order(seed: str, purpose: str, items: list) -> list:
    return sorted(items, key=lambda x: h(seed, purpose, str(x)))


def pick(seed: str, purpose: str, items: list, k: int) -> list:
    return order(seed, purpose, items)[:max(0, k)]


def take_pair(seed: str, sig: str, fraction: float) -> bool:
    return int(h(seed, "pair", sig)[:8], 16) / 0xFFFFFFFF < fraction


def assign(seed: str, trades: list, n_cal: int) -> "tuple[list, list]":
    """Split the sampled trade keys into calibration (first n_cal by seed) and test (the rest, by seed)."""
    ordered = order(seed, "assign", trades)
    return ordered[:n_cal], ordered[n_cal:]


def strata_of(tr: dict) -> list:
    """Which strata a decoded trade belongs to. Uses decoded event fields only (never a score)."""
    out = []
    name = tr["ix_name"]
    if name.endswith("_v2"):
        out.append("v2")
    else:
        out.append("v1")
        if name.startswith("buy"):
            out.append("v1_buy_sol")
    out.append("buy" if name.startswith("buy") else "sell")
    if name.startswith("buy_exact_quote_in"):
        out.append("buy_exact_in")
    if tr.get("vqr_event", 0) < 0:
        out.append("vqr_negative")
    if tr.get("can_boost"):
        out.append("can_boost")
    if tr.get("tier_pre", 0) >= 2:
        out.append("tier_ge_2")
    if tr.get("tier_cross"):
        out.append("tier_cross")
    return out


def short_strata(counts: dict) -> dict:
    return {k: v - counts.get(k, 0) for k, v in T6_SPEC["strata"].items() if counts.get(k, 0) < v}
