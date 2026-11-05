"""Registry of tier-A rows (phase0/test-plan.md section 4), in the plan's run order (section 3):
keyless rows first, then A01-A09 (the Gate 0 -> 1 core), then the rest.
A20 is keyless but needs A04's create transactions, so it runs after A22.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from p0 import t6

from . import core, keyless, live, trades

HELIUS = "mainnet.helius-rpc.com"
PUBLIC = "api.mainnet-beta.solana.com"


@dataclass(frozen=True)
class Row:
    row: str
    tests: str
    question: str
    run: Optional[Callable] = None
    needs_key: bool = True
    hosts: tuple = (HELIUS,)
    public_fallback: bool = False
    deferred: Optional[str] = None
    env_var: str = "HELIUS_API_KEY"
    prereqs: tuple = field(default_factory=tuple)


ROWS = [
    # ---- keyless (can start as soon as List 1 is allowed) ----
    Row("A18", "X1, EXE-r1.3, QT-T8", "Jito tip floor for 7 days; does a failed bundle pay nothing?", keyless.a18,
        needs_key=False, hosts=("bundles.jito.wtf", "docs.jito.wtf"), env_var="none"),
    Row("A19", "Q5, SEC-S7, X4, EXE-r1.4", "Official tip accounts; how Sender's protection works", keyless.a19,
        needs_key=False, hosts=("mainnet.block-engine.jito.wtf", "sender.helius-rpc.com", "docs.jito.wtf", "www.helius.dev"),
        env_var="none"),
    Row("A23", "D9, D14, EXE-r1.6", "Keyless PumpPortal migration feed: complete?", None, needs_key=False,
        hosts=("pumpportal.fun",), env_var="none",
        deferred="Rust probe, later (websocket wss://pumpportal.fun/api/data, 24 h; crates/feed/examples/)"),
    Row("A24", "D15, P12, R8, G5, G8, PX-2", "What does each Helius method cost?", keyless.a24, needs_key=False,
        hosts=("www.helius.dev",), env_var="none"),
    Row("A26", "PX-1, PX-2, D10", "Are Helius and Chainstack prices as budgeted? $49 = 1 or 2 streams?", keyless.a26,
        needs_key=False, hosts=("chainstack.com", "docs.chainstack.com", "www.helius.dev"), env_var="none"),
    Row("A27", "G4 (docs), D13 (docs)", "Chainstack Growth allowance, getBlock cost, Yellowstone filters", keyless.a27,
        needs_key=False, hosts=("docs.chainstack.com",), env_var="none"),
    Row("A28", "PX-11, EXE-r1.8", "SOL price and exchange rates", keyless.a28, needs_key=False,
        hosts=("api.coingecko.com",), env_var="none"),
    # ---- Gate 0 -> 1 core ----
    Row("A01", "D1, FC3 (Global part)", "Are Pump's migration settings unchanged?", core.a01, public_fallback=True,
        hosts=(HELIUS, PUBLIC)),
    Row("A02", "D7, SEC-r1.4 (Pump part)", "Program upgrade baseline", core.a02, public_fallback=True, hosts=(HELIUS, PUBLIC)),
    Row("A03", "D2, CF-T3, P1 (one-tx share), PR-1 audit", "How does a migration look; does the authority key catch every one?",
        core.a03),
    Row("A04", "D5, AR-T1 (TS-6)", "Are events always inner event calls? How often are logs cut off?", core.a04),
    Row("A05", "CF-T1, D16, R9, FC5", "What kind of token is a Pump coin today?", core.a05, prereqs=("A04",)),
    Row("A06", "CF-T4", "Is the migrated pool canonical, and is its LP burned?", core.a06, prereqs=("A03",)),
    Row("A07", "RC4, RC3", "How many pool layouts exist? Is virtual_quote_reserves live and signed?", core.a07,
        prereqs=("A03",)),
    Row("A08", "QT-T5, FC1, FC2, FC3, FC4, FC8, EXE-r1.2", "Do live fee settings, pool sizes and deposits match fee-model?",
        core.a08, public_fallback=True, hosts=(HELIUS, PUBLIC), prereqs=("A03", "A04")),
    Row("A09", "QT-T6 = T6 (Gate 0->1), FC6, FC7, D12, X6, Q1, RSK-r1.3, FM-3/4/5", "Do our fee and price maths reproduce real trades to the lamport?",
        t6.run, prereqs=("A03", "A08")),
    # ---- the rest ----
    Row("A10", "P6, SEC-S4 (mainnet part)", "Can a payout account be owned by someone other than the signer?", trades.a10,
        prereqs=("A04",)),
    Row("A11", "X2, Q4, FC9, EXE-r1.2", "Compute use; what failed buys look like; priority fees", trades.a11, prereqs=("A04",)),
    Row("A12", "D6 (lite), QT-T7, EXE-r1.2", "Slot length; processed vs confirmed", live.a12, public_fallback=True,
        hosts=(HELIUS, PUBLIC)),
    Row("A13", "RC2 (lite), RSK-r1.2", "Freshness of exit-price sources", None,
        deferred="Rust probe, later (websocket accountSubscribe vs polls; crates/feed/examples/)"),
    Row("A14", "X3", "How long does a blockhash stay usable?", live.a14, public_fallback=True, hosts=(HELIUS, PUBLIC)),
    Row("A15", "RC8", "Would the sells-only auto-adopt rule adopt the Sep 2025 change and refuse 5 hostile diffs?", None,
        hosts=("github.com",),
        deferred="Not JSON-RPC: needs `git clone` of github.com/pump-fun/pump-public-docs and the R2 IDL-diff checker "
                 "(its own TODO item); the 5 replayed sells can then use this client"),
    Row("A16", "R2, F4, X7", "What does BOOST look like on chain?", trades.a16, prereqs=("A03",)),
    Row("A17", "P4, X1 (winning tips)", "What do winners tip at migration?", trades.a17, prereqs=("A03", "A19")),
    Row("A21", "F5", "Do launch crews reuse lookup tables?", trades.a21, prereqs=("A16",)),
    Row("A22", "A8 (step 1), SOC-S3 (host part)", "Where does coin metadata live? (no fetching)", trades.a22,
        prereqs=("A04",)),
    Row("A20", "CF-T11", "How often are create transactions bundled?", keyless.a20, needs_key=False,
        hosts=("bundles.jito.wtf",), env_var="none", prereqs=("A04",)),
    Row("A25", "CF-T2, F6", "What do forensics lookups cost, and how fast are they?", trades.a25, prereqs=("A03",)),
    Row("A29", "P1 (pilot)", "Price per block in blocks 0-20", trades.a29, prereqs=("A03",)),
    Row("A30", "RC1 + X5 (pilot)", "Crowding at the end of BOOST; failures in the first 5 min", trades.a30,
        prereqs=("A16",)),
    Row("A31", "F1 + P5 (pilot)", "How do dumping insiders get their tokens?", trades.a31, prereqs=("A03",)),
    Row("A32", "F3 (our own lookup)", "What does our own funding lookup cost?", trades.a32, prereqs=("A16",)),
]

BY_ID = {r.row: r for r in ROWS}
