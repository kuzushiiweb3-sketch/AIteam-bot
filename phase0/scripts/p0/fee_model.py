"""PumpSwap fee and price maths, exactly as docs/fee-model.md section 3 (v1.1) writes it.

REVIEW NOTES
  * Integers only. No float is used anywhere in this file.
  * Every function is pure: inputs in, numbers out. No network, no files.
  * Where fee-model.md leaves a question open for calibration (FC7), the choice is an explicit
    field of `Semantics`, so the calibration step can test each candidate and the scoring step
    uses exactly one frozen choice. Nothing is tuned silently.
  * REFEREE ONLY. docs/tech-stack.md v1.1 s.5k: the T6 / A09 verdict comes from the Rust `fees` crate,
    run offline over the fixtures A09 saves. This Python module is the reviewer-readable referee; the
    Rust crate and this module must agree on every saved T6 fixture (a differential test).

Sources: docs/fee-model.md s.2a-s.3 and s.7, which cite Pump's SDK 2.1.0 (fees.ts, util.ts, buy.ts,
sell.ts) [VERIFIED-DOC there]. Re-checked against the SDK source in this session.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

MODEL_VERSION = "fee-model-v1.1/py-1"

BPS = 10_000
U64_MAX = 2 ** 64 - 1
MAYHEM_SUPPLY = 10 ** 15                       # SDK PUMP_AMM_TOTAL_TOKEN_SUPPLY [VERIFIED-DOC util.ts]
DEFAULT_PUBKEY = "11111111111111111111111111111111"
SOL_LIKE_QUOTES = (DEFAULT_PUBKEY, "So11111111111111111111111111111111111111112",
                   "9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP")
STABLE_QUOTES = ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",)
BASE_FEE_PER_SIGNATURE = 5_000                 # [VERIFIED-DOC fee-structure.mdx via fee-model s.2]
MICRO_LAMPORTS_PER_LAMPORT = 1_000_000


class QuoteRefused(ValueError):
    """fee-model s.6 rule 9: refuse to quote (a class-A alarm in the live system)."""


# ---- inputs -------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Fees:
    lp: int
    protocol: int
    creator: int

    @property
    def total(self) -> int:
        return self.lp + self.protocol + self.creator


@dataclass(frozen=True)
class FeeTier:
    threshold: int          # market cap, lamports (u128 on chain)
    fees: Fees


@dataclass(frozen=True)
class FeeSchedule:
    flat_fees: Fees
    fee_tiers: tuple
    stable_fee_tiers: tuple = ()
    exotic_flat_fees: Fees = Fees(0, 0, 0)

    @staticmethod
    def from_account(decoded: dict) -> "FeeSchedule":
        def f(d: dict) -> Fees:
            return Fees(int(d["lp_fee_bps"]), int(d["protocol_fee_bps"]), int(d["creator_fee_bps"]))

        def tiers(lst) -> tuple:
            return tuple(FeeTier(int(t["market_cap_lamports_threshold"]), f(t["fees"])) for t in (lst or []))

        exotic = decoded.get("exotic_flat_fees") or {"lp_fee_bps": 0, "protocol_fee_bps": 0, "creator_fee_bps": 0}
        return FeeSchedule(f(decoded["flat_fees"]), tiers(decoded["fee_tiers"]),
                           tiers(decoded.get("stable_fee_tiers")), f(exotic))


@dataclass(frozen=True)
class PoolState:
    """Pool state at one instant (all values from the same slot). vqr is SIGNED."""
    q_vault: int                    # raw quote vault amount (includes fees waiting in buckets)
    vqr: int                        # Pool.virtual_quote_reserves (i128)
    b: int                          # base vault amount
    protocol_fees: Optional[int] = 0   # Pool.protocol_fees bucket; None = unknown (events do not carry it)
    creator_fees: Optional[int] = 0    # Pool.creator_fees bucket; None = unknown
    supply: int = 0                 # base mint supply (ignored for mayhem pools)
    is_mayhem: bool = False
    quote_mint: str = SOL_LIKE_QUOTES[1]
    canonical: bool = True
    coin_creator: str = "x"         # DEFAULT_PUBKEY means "no creator": creator fee 0
    creator_fee_bps: int = 0        # Pool.creator_fee_bps (per-pool rate)

    @property
    def q(self) -> int:
        """Effective quote reserves Q = Q_vault + vqr; the program guarantees 0 <= Q < 2^64."""
        q = self.q_vault + self.vqr
        if q < 0 or q > U64_MAX:
            raise QuoteRefused(f"effective quote reserve {q} out of range")
        return q

    @property
    def buckets_known(self) -> bool:
        return self.protocol_fees is not None and self.creator_fees is not None

    @property
    def q_real(self) -> Optional[int]:
        """What sells can be paid from; None when the fee buckets are unknown."""
        if not self.buckets_known:
            return None
        return self.q_vault - self.protocol_fees - self.creator_fees

    @property
    def sigma(self) -> Optional[int]:
        """Boost reserve = Q - Q_real (0 on unboosted pools) [fee-model v1.1 s.3]."""
        qr = self.q_real
        return None if qr is None else self.q - qr

    def check(self) -> None:
        """fee-model v1.1 s.3: refuse to quote if Q == 0, B == 0, sigma < 0 or Q_real < 0.

        sigma and Q_real are only checked when both fee buckets are known (from the Pool account).
        """
        if self.q == 0 or self.b == 0:
            raise QuoteRefused("Q or B is zero")
        if self.buckets_known and (self.q_real < 0 or self.sigma < 0):
            raise QuoteRefused(f"sigma {self.sigma} or Q_real {self.q_real} is negative")


@dataclass(frozen=True)
class Semantics:
    """Open questions from fee-model s.7 Step 1 (FC7). Each field is one candidate answer."""
    exact_in_net: str = "shave"            # "shave" (net = min(net0, X - fees)) | "whole_budget" (net = X - fees)
    buyback_basis: str = "protocol_fee"    # bb = rounding(base * bb_bps / 10000), base = "protocol_fee" | "amount"
    buyback_rounding: str = "floor"        # "floor" | "ceil"
    event_protocol_fee: str = "total"      # event.protocol_fee is "total" (includes buyback) | "net_of_buyback"
    protocol_bucket: str = "pr_minus_bb"   # v2: Pool.protocol_fees grows by "pr_minus_bb" | "pr"
    no_creator_event_bps: str = "zero"     # when coin_creator is the default key, event creator bps is "zero" | "tier"
    event_reserves: str = "pre"            # event pool_*_token_reserves are "pre" | "post" trade (FC7 q.1)
    event_quote_kind: str = "raw"          # event pool_quote_token_reserves is the "raw" vault | "effective" Q (FC7 q.1)
    event_vqr: str = "pre"                 # event virtual_quote_reserves is "pre" | "post" trade (FC7 q.2)

    def key(self) -> str:
        return "|".join(f"{k}={v}" for k, v in sorted(self.__dict__.items()))


SEMANTICS_CHOICES = {
    "exact_in_net": ("shave", "whole_budget"),
    "buyback_basis": ("protocol_fee", "amount"),
    "buyback_rounding": ("floor", "ceil"),
    "event_protocol_fee": ("total", "net_of_buyback"),
    "protocol_bucket": ("pr_minus_bb", "pr"),
    "no_creator_event_bps": ("zero", "tier"),
    "event_reserves": ("pre", "post"),
    "event_quote_kind": ("raw", "effective"),
    "event_vqr": ("pre", "post"),
}


def all_semantics() -> "list[Semantics]":
    combos = [Semantics()]
    for name, values in SEMANTICS_CHOICES.items():
        combos = [replace(s, **{name: v}) for s in combos for v in values]
    return combos


# ---- arithmetic --------------------------------------------------------------------------------
def ceil_div(a: int, b: int) -> int:
    if b <= 0:
        raise QuoteRefused("division by a non-positive number")
    return (a + b - 1) // b


def fee(amount: int, bps: int) -> int:
    """Every fee rounds UP [VERIFIED-DOC util.ts fee()]."""
    return ceil_div(amount * bps, BPS)


def market_cap(q: int, b: int, supply: int) -> int:
    if b == 0:
        raise QuoteRefused("base reserve is zero")
    return q * supply // b


def tier(tiers: tuple, m: int) -> Fees:
    """[VERIFIED-DOC fees.ts calculateFeeTier = Rust calculate_fee_tier]"""
    if not tiers:
        raise QuoteRefused("fee tiers cannot be empty")
    if m < tiers[0].threshold:
        return tiers[0].fees
    for t in reversed(tiers):
        if m >= t.threshold:
            return t.fees
    return tiers[0].fees


def tier_index(tiers: tuple, m: int) -> int:
    if m < tiers[0].threshold:
        return 0
    for i in range(len(tiers) - 1, -1, -1):
        if m >= tiers[i].threshold:
            return i
    return 0


def pool_market_cap(state: PoolState) -> int:
    supply = MAYHEM_SUPPLY if state.is_mayhem else state.supply
    return market_cap(state.q, state.b, supply)


def schedule_rates(state: PoolState, sched: FeeSchedule, creator_fee_configurable: bool) -> Fees:
    """The schedule's rates BEFORE the no-creator rule [VERIFIED-DOC fees.ts computeFeesBps/feesForQuoteMint]."""
    m = pool_market_cap(state)
    if not state.canonical:
        r = sched.flat_fees
    elif state.quote_mint in SOL_LIKE_QUOTES:
        r = tier(sched.fee_tiers, m)
    elif state.quote_mint in STABLE_QUOTES:
        r = tier(sched.stable_fee_tiers or sched.fee_tiers, m)
    else:
        ex = sched.exotic_flat_fees
        r = sched.flat_fees if (ex.lp == 0 and ex.protocol == 0 and ex.creator == 0) else ex
    if creator_fee_configurable and state.creator_fee_bps > 0:
        r = Fees(r.lp, r.protocol, state.creator_fee_bps)
    return r


def rates(state: PoolState, sched: FeeSchedule, creator_fee_configurable: bool) -> Fees:
    """Rates actually charged: the creator rate is 0 when Pool.coin_creator is the default key."""
    r = schedule_rates(state, sched, creator_fee_configurable)
    if state.coin_creator == DEFAULT_PUBKEY:
        r = Fees(r.lp, r.protocol, 0)
    return r


def buyback_fee(protocol_fee: int, amount: int, bb_bps: int, sem: Semantics) -> int:
    base = protocol_fee if sem.buyback_basis == "protocol_fee" else amount
    num = base * bb_bps
    return ceil_div(num, BPS) if sem.buyback_rounding == "ceil" else num // BPS


# ---- the three trade shapes -------------------------------------------------------------------
def buy_exact_out(state: PoolState, b: int, r: Fees) -> dict:
    """buy / buy_v2 (base_amount_out = b) [VERIFIED-DOC buy.ts buyBaseInput]"""
    state.check()
    q, bb = state.q, state.b
    if b >= bb:
        return {"fail": 6016}
    q_in = ceil_div(q * b, bb - b)
    lp, pr, cr = fee(q_in, r.lp), fee(q_in, r.protocol), fee(q_in, r.creator)
    return {"q_in": q_in, "lp": lp, "pr": pr, "cr": cr, "b_out": b,
            "quote_amount_in_with_lp_fee": q_in + lp, "pay": q_in + lp + pr + cr}


def buy_exact_in(state: PoolState, x: int, r: Fees, sem: Semantics) -> dict:
    """buy_exact_quote_in(_v2) (spendable_quote_in = x) [VERIFIED-DOC buy.ts exactQuoteInFees/buyQuoteInput]"""
    state.check()
    q, bb = state.q, state.b
    net0 = x * BPS // (BPS + r.total)
    if net0 <= 0:
        return {"fail": "budget_does_not_cover_fees"}
    lp, pr, cr = fee(net0, r.lp), fee(net0, r.protocol), fee(net0, r.creator)
    net = min(net0, x - lp - pr - cr) if sem.exact_in_net == "shave" else x - lp - pr - cr
    if net <= 1:
        return {"fail": "budget_does_not_cover_fees"}
    b_out = bb * (net - 1) // (q + net - 1)
    return {"q_in": net, "lp": lp, "pr": pr, "cr": cr, "b_out": b_out, "net0": net0,
            "quote_amount_in_with_lp_fee": net + lp, "pay": net + lp + pr + cr}


def sell_exact_in(state: PoolState, b: int, r: Fees) -> dict:
    """sell / sell_v2 (base_amount_in = b) [VERIFIED-DOC sell.ts sellBaseInput/sellAmounts]

    The 6063 line (payout capped at Q_real) is only decided when the buckets are known; otherwise
    `fails_6063` is None ("not decidable from this state").
    """
    state.check()
    q, bb = state.q, state.b
    q_out = q * b // (bb + b)
    lp, pr, cr = fee(q_out, r.lp), fee(q_out, r.protocol), fee(q_out, r.creator)
    leaves = q_out - lp
    receive = q_out - lp - pr - cr
    return {"q_out": q_out, "lp": lp, "pr": pr, "cr": cr, "leaves": leaves, "receive": receive, "base_in": b,
            "quote_amount_out_without_lp_fee": leaves,
            "fails_6063": None if state.q_real is None else state.q_real < leaves}


def predict(ix_name: str, args: dict, state: PoolState, r: Fees, sem: Semantics) -> dict:
    """Predicted outcome of one PumpSwap trade instruction, including the fail-or-succeed line."""
    if ix_name in ("buy", "buy_v2"):
        p = buy_exact_out(state, int(args["base_amount_out"]), r)
        if "fail" not in p and p["pay"] > int(args["max_quote_amount_in"]):
            p["fail"] = 6004
        return p
    if ix_name in ("buy_exact_quote_in", "buy_exact_quote_in_v2"):
        p = buy_exact_in(state, int(args["spendable_quote_in"]), r, sem)
        if "fail" not in p and p["b_out"] < int(args["min_base_amount_out"]):
            p["fail"] = 6040
        return p
    if ix_name in ("sell", "sell_v2"):
        p = sell_exact_in(state, int(args["base_amount_in"]), r)
        if p["fails_6063"]:
            p["fail"] = 6063
        elif p["receive"] < int(args["min_quote_amount_out"]):
            p["fail"] = 6004
        return p
    raise QuoteRefused(f"unknown instruction {ix_name}")


# ---- state updates (fee-model s.3 "state update after our own (or any) trade") ------------------
def _add(bucket: Optional[int], amount: int) -> Optional[int]:
    return None if bucket is None else bucket + amount


def post_state(state: PoolState, ix_name: str, p: dict, bb: int, sem: Semantics) -> PoolState:
    v2 = ix_name.endswith("_v2")
    is_buy = ix_name.startswith("buy")
    pr, cr, lp = p["pr"], p["cr"], p["lp"]
    kept_protocol = (pr - bb) if sem.protocol_bucket == "pr_minus_bb" else pr
    if is_buy:
        q_in = p["q_in"]
        b_new = state.b - p["b_out"]
        if v2:
            q_vault = state.q_vault + q_in + lp + kept_protocol + cr
            vqr = state.vqr - kept_protocol - cr
            return replace(state, q_vault=q_vault, vqr=vqr, b=b_new,
                           protocol_fees=_add(state.protocol_fees, kept_protocol),
                           creator_fees=_add(state.creator_fees, cr))
        return replace(state, q_vault=state.q_vault + q_in + lp, b=b_new)
    # sell
    b_new = state.b + p["base_in"]
    if v2:
        paid_out = pr - kept_protocol          # the buyback slice (or 0 if the bucket keeps all of pr)
        return replace(state, q_vault=state.q_vault - (p["receive"] + paid_out), vqr=state.vqr - kept_protocol - cr,
                       b=b_new, protocol_fees=_add(state.protocol_fees, kept_protocol),
                       creator_fees=_add(state.creator_fees, cr))
    return replace(state, q_vault=state.q_vault - p["leaves"], b=b_new)


def vault_deltas(ix_name: str, p: dict, bb: int, sem: Semantics) -> dict:
    """Expected change of the two pool vaults and of everyone else's quote accounts (P4 witness)."""
    v2 = ix_name.endswith("_v2")
    pr, cr, lp = p["pr"], p["cr"], p["lp"]
    kept_protocol = (pr - bb) if sem.protocol_bucket == "pr_minus_bb" else pr
    if ix_name.startswith("buy"):
        if v2:
            return {"quote_vault": p["q_in"] + lp + kept_protocol + cr, "base_vault": -p["b_out"],
                    "user_quote": -p["pay"], "fee_recipients": pr - kept_protocol}
        return {"quote_vault": p["q_in"] + lp, "base_vault": -p["b_out"], "user_quote": -p["pay"],
                "fee_recipients": pr + cr}
    if v2:
        return {"quote_vault": -(p["receive"] + (pr - kept_protocol)), "base_vault": p["base_in"],
                "user_quote": p["receive"], "fee_recipients": pr - kept_protocol}
    return {"quote_vault": -p["leaves"], "base_vault": p["base_in"], "user_quote": p["receive"],
            "fee_recipients": pr + cr}


def sweep(state: PoolState, amount: int, bucket: int) -> PoolState:
    """sweep_protocol_fee (bucket 0) / sweep_creator_fee (bucket 1): Q unchanged."""
    if bucket == 0:
        return replace(state, q_vault=state.q_vault - amount, vqr=state.vqr + amount,
                       protocol_fees=_add(state.protocol_fees, -amount))
    return replace(state, q_vault=state.q_vault - amount, vqr=state.vqr + amount,
                   creator_fees=_add(state.creator_fees, -amount))


# ---- network fee (fee-model s.2c; check P6) ---------------------------------------------------
def priority_fee(cu_price_micro_lamports: int, cu_limit: int) -> int:
    """ceil(price x requested limit / 1e6) [VERIFIED-DOC agave compute_budget_limits.rs get_prioritization_fee]"""
    return ceil_div(cu_price_micro_lamports * cu_limit, MICRO_LAMPORTS_PER_LAMPORT) if cu_price_micro_lamports else 0


def network_fee(signatures: int, cu_price_micro_lamports: int, cu_limit: int) -> int:
    return BASE_FEE_PER_SIGNATURE * signatures + priority_fee(cu_price_micro_lamports, cu_limit)
