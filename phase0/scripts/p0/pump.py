"""Pump.fun / PumpSwap constants and decoders, driven by the pinned IDLs in phase0/scripts/idl/.

All addresses below are from the pinned IDLs or phase0/test-plan.md section 2 [VERIFIED-DOC there].
The offline tests re-derive Global, GlobalConfig and both FeeConfig addresses as PDAs from the
IDL seeds, so a typo here fails a test.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .b58 import pubkey_bytes
from .borsh import IdlDecoder, ShapeError
from .pda import find_program_address, lit
from .txparse import EVENT_PREFIX, Ix, Tx, children

PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
PUMP_FEES_PROGRAM = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
PUMP_GLOBAL = "4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf"
WITHDRAW_AUTHORITY = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"
PUMPSWAP_GLOBAL_CONFIG = "ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw"
PUMPSWAP_FEE_CONFIG = "5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx"
CURVE_FEE_CONFIG = "8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt"
WSOL_MINT = "So11111111111111111111111111111111111111112"
WSOL_2022_MINT = "9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_PUBKEY = "11111111111111111111111111111111"
SOL_LIKE_QUOTES = (DEFAULT_PUBKEY, WSOL_MINT, WSOL_2022_MINT)   # [VERIFIED-DOC SDK fees.spec.ts]
STABLE_QUOTES = (USDC_MINT,)
BPF_UPGRADEABLE_LOADER = "BPFLoaderUpgradeab1e11111111111111111111111"
PROGRAMS = {"pump": PUMP_PROGRAM, "pump_amm": PUMPSWAP_PROGRAM, "pump_fees": PUMP_FEES_PROGRAM}

# Expected values for A01 [VERIFIED-DOC via DAT R1, test-plan A01]
EXPECTED_POOL_MIGRATION_FEE = 15_000_001

# SIMD-0437 gates [VERIFIED-DOC agave feature-set/src/lib.rs, fetched 2026-11-05, sha256 576a28d1...95c4]
RENT_GATES = {
    "4a6f7o7iTcA8hRDCrPLkSatnt5Ykxiu36wo5p1Tt12wC": 6333,
    "61BtM7BkDEE8Yq5fskEVAQT9mYA8qCejJWoLe5apqg81": 5080,
    "rntCigrTppP5JdZz7K8TyN9sMzLdAcXp8SejYpVpX6D": 2575,
    "rntD7invRBswCAdKtRsh1G4psKjrPdS3BKqtnA78C7N": 1322,
    "rntTjNZ9boq8owDxjGVFHPfWNQPDaKiM5JcjxmDGg47": 696,
    "rnt8ZQpz2HYhX3DkYBDGjJS1a36mYq69oXka7JrhEdi": 6960,   # the revert gate
}
LAMPORTS_PER_BYTE_STEPS = (6960, 6333, 5080, 2575, 1322, 696)

IDL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "idl")

# Trade instructions (by program; buy_v2's discriminator is the same in both programs).
AMM_BUYS = ("buy", "buy_v2", "buy_exact_quote_in", "buy_exact_quote_in_v2")
AMM_SELLS = ("sell", "sell_v2")
AMM_TRADES = AMM_BUYS + AMM_SELLS
AMM_V2 = ("buy_v2", "buy_exact_quote_in_v2", "sell_v2")
CURVE_TRADES = ("buy", "buy_v2", "buy_v3", "buy_exact_sol_in", "buy_exact_quote_in_v2", "buy_exact_quote_in_v3",
                "sell", "sell_v2", "sell_v3")
MIGRATE_IXS = ("migrate", "migrate_v2")
CREATE_IXS = ("create", "create_v2")


class IdlPinError(RuntimeError):
    pass


_DECODERS: dict = {}


def load_decoders(idl_dir: str = IDL_DIR) -> dict:
    """{'pump': IdlDecoder, 'pump_amm': ..., 'pump_fees': ...}; refuses if a hash differs from PINNED.json."""
    key = os.path.abspath(idl_dir)
    if key in _DECODERS:
        return _DECODERS[key]
    with open(os.path.join(idl_dir, "PINNED.json"), "r", encoding="utf-8") as f:
        pins = json.load(f)["files"]
    out = {}
    for fname, pin in pins.items():
        path = os.path.join(idl_dir, fname)
        with open(path, "rb") as f:
            raw = f.read()
        got = hashlib.sha256(raw).hexdigest()
        if got != pin["sha256"]:
            raise IdlPinError(f"{fname}: sha256 {got} does not match the pinned {pin['sha256']}")
        idl = json.loads(raw)
        if idl.get("address") != pin["program"]:
            raise IdlPinError(f"{fname}: address {idl.get('address')} != pinned {pin['program']}")
        out[fname[:-5]] = IdlDecoder(idl)
    _DECODERS[key] = out
    return out


def decoder_for_program(program: str) -> Optional[IdlDecoder]:
    d = load_decoders()
    for name, pid in PROGRAMS.items():
        if program == pid:
            return d[name]
    return None


# ---- PDAs --------------------------------------------------------------------------------
def pool_authority(base_mint: str) -> str:
    return find_program_address([lit("pool-authority"), pubkey_bytes(base_mint)], PUMP_PROGRAM)[0]


def canonical_pool_address(base_mint: str, quote_mint: str = WSOL_MINT, index: int = 0) -> str:
    if quote_mint == DEFAULT_PUBKEY:
        quote_mint = WSOL_MINT       # SDK canonicalPoolQuoteMint: the curve's zero quote mint means WSOL
    creator = pool_authority(base_mint)
    return find_program_address([lit("pool"), index.to_bytes(2, "little"), pubkey_bytes(creator),
                                 pubkey_bytes(base_mint), pubkey_bytes(quote_mint)], PUMPSWAP_PROGRAM)[0]


def bonding_curve_address(mint: str) -> str:
    return find_program_address([lit("bonding-curve"), pubkey_bytes(mint)], PUMP_PROGRAM)[0]


def user_volume_accumulator(user: str) -> str:
    return find_program_address([lit("user_volume_accumulator"), pubkey_bytes(user)], PUMPSWAP_PROGRAM)[0]


def is_canonical_pool(pool: dict) -> bool:
    return pool.get("creator") == pool_authority(pool["base_mint"])


# ---- account decoders --------------------------------------------------------------------
def b64data(account: dict) -> bytes:
    data = account.get("data")
    if isinstance(data, list) and len(data) == 2 and data[1] == "base64":
        return base64.b64decode(data[0])
    raise ShapeError("account data is not base64-encoded")


def decode_global(data: bytes) -> dict:
    return load_decoders()["pump"].decode_account(data, expect="Global", lenient=True)


def decode_pool(data: bytes) -> dict:
    return load_decoders()["pump_amm"].decode_account(data, expect="Pool", lenient=True)


def decode_global_config(data: bytes) -> dict:
    return load_decoders()["pump_amm"].decode_account(data, expect="GlobalConfig", lenient=True)


def decode_fee_config(data: bytes) -> dict:
    return load_decoders()["pump_amm"].decode_account(data, expect="FeeConfig", lenient=True)


def decode_bonding_curve(data: bytes) -> dict:
    return load_decoders()["pump"].decode_account(data, expect="BondingCurve", lenient=True)


def pool_allowed_lengths() -> "list[int]":
    """Every field boundary from `coin_creator` onward, plus the padded 300 bytes.

    Pump docs: older pools are shorter and missing trailing fields read as 0; accounts may be
    padded to 300 bytes [VERIFIED-DOC PUMP_SWAP_README via docs/fee-model.md s.4].
    """
    offs = load_decoders()["pump_amm"].field_offsets("Pool")
    ends = [o + s for (name, o, s) in offs]
    start = next(o + s for (name, o, s) in offs if name == "coin_creator")
    return sorted({e for e in ends if e >= start} | {300})


# ---- events and trades in a transaction ---------------------------------------------------
# ---- events: red-team TS-6 rules F1, F2, F4 (docs/tech-stack.md v1.1 s.5b) ----------------------
FAILED_TX_EVENT = "FAILED_TX_EVENT"     # F1: event inside a transaction whose meta.err is set
EVENT_PROVENANCE = "EVENT_PROVENANCE"   # F2: event-shaped call that is not a proper self-call
NO_INNER_IX = "NO_INNER_IX"             # F4: meta.innerInstructions absent or null

_EVENT_AUTHORITY: dict = {}


def event_authority(program: str) -> str:
    """The program's `event_authority` PDA, seeds ["__event_authority"] [VERIFIED-DOC IDLs]."""
    if program not in _EVENT_AUTHORITY:
        _EVENT_AUTHORITY[program] = find_program_address([lit("__event_authority")], program)[0]
    return _EVENT_AUTHORITY[program]


@dataclass
class Event:
    program: str
    name: str
    fields: dict
    top_index: int
    inner_index: Optional[int]
    stack_height: Optional[int]
    flag: Optional[str] = None           # None = usable; else FAILED_TX_EVENT or EVENT_PROVENANCE
    reason: str = ""


@dataclass
class ProgramIx:
    program: str
    name: str
    args: dict
    accounts: list
    ix: Ix
    events: list                         # usable events (successful tx, provenance checked)
    failed_events: list = field(default_factory=list)   # F1: same events from a failed tx, tagged
    flagged_events: list = field(default_factory=list)  # F2: provenance failures under this instruction


@dataclass
class Scan:
    pixs: list                           # every Pump / PumpSwap / Pump Fees instruction, top-level or CPI
    events: list                         # usable events only (empty for a failed tx or a NO_INNER_IX tx)
    failed_events: list                  # F1
    provenance_flags: list               # F2 (orphans and wrong-authority calls)
    no_inner_ix: bool                    # F4
    success: bool

    def counts(self) -> dict:
        return {FAILED_TX_EVENT: len(self.failed_events), EVENT_PROVENANCE: len(self.provenance_flags),
                NO_INNER_IX: int(self.no_inner_ix)}


def _decode_event(ix: Ix) -> Event:
    dec = decoder_for_program(ix.program)
    try:
        ev = dec.decode_event(ix.data[8:]) if dec else None
    except ShapeError as e:
        return Event(ix.program, "_SHAPE_ERROR", {"error": str(e), "disc": ix.data[8:16].hex()},
                     ix.top_index, ix.inner_index, ix.stack_height)
    if ev is None:
        return Event(ix.program, "_UNKNOWN_EVENT", {"disc": ix.data[8:16].hex()},
                     ix.top_index, ix.inner_index, ix.stack_height)
    return Event(ix.program, ev["_name"], ev, ix.top_index, ix.inner_index, ix.stack_height)


def _is_event_call(ix: Ix) -> bool:
    return ix.data[:8] == EVENT_PREFIX and ix.program in PROGRAMS.values()


def scan(tx: Tx) -> Scan:
    """Decode every Pump-family instruction and event in a transaction, applying F1, F2 and F4.

    F2 (provenance): an event counts only if (a) it is an inner instruction of the emitting program,
    (b) its parent is an instruction of the SAME program exactly one stack level up, and (c) its first
    account is that program's event_authority PDA. Without stackHeight data, the parent is accepted only
    when it is the top-level instruction of the same program and no other instruction of that program
    appears in the same top-level group (otherwise the parent is ambiguous -> EVENT_PROVENANCE).
    """
    cached = getattr(tx, "_p0_scan", None)
    if cached is not None:
        return cached
    pixs, usable, failed, flags = [], [], [], []
    claimed: set = set()
    for ti in range(len(tx.instructions)):
        flat = tx.flat(ti)
        inner = tx.inner.get(ti, [])
        has_heights = all(k.stack_height is not None for k in inner)
        for pos, ix in enumerate(flat):
            if ix.program not in PROGRAMS.values() or _is_event_call(ix):
                continue
            dec = decoder_for_program(ix.program)
            try:
                args = dec.decode_instruction(ix.data) if dec else None
            except ShapeError as e:
                args = {"_name": "_SHAPE_ERROR", "error": str(e)}
            name = args["_name"] if args else "_UNKNOWN_IX:" + ix.data[:8].hex()
            pix = ProgramIx(ix.program, name, args or {}, ix.accounts, ix, [])
            auth = event_authority(ix.program)
            if has_heights:
                base = ix.stack_height or 1
                for k in children(flat, pos):
                    if not _is_event_call(k) or k.stack_height != base + 1:
                        continue
                    claimed.add((ti, k.inner_index))
                    ev = _decode_event(k)
                    if k.program != ix.program:
                        ev.flag, ev.reason = EVENT_PROVENANCE, "event-shaped call under another program's instruction"
                    elif not k.accounts or k.accounts[0] != auth:
                        ev.flag, ev.reason = EVENT_PROVENANCE, "first account is not the program's event_authority"
                    (pix.flagged_events if ev.flag else pix.events).append(ev)
            elif pos == 0:
                same = [k for k in inner if k.program == ix.program and not _is_event_call(k)]
                for k in inner:
                    if not _is_event_call(k):
                        continue
                    claimed.add((ti, k.inner_index))
                    ev = _decode_event(k)
                    if k.program != ix.program:
                        ev.flag, ev.reason = EVENT_PROVENANCE, "no stackHeight; event under another program"
                    elif same:
                        ev.flag, ev.reason = EVENT_PROVENANCE, "no stackHeight; parent ambiguous"
                    elif not k.accounts or k.accounts[0] != auth:
                        ev.flag, ev.reason = EVENT_PROVENANCE, "first account is not the program's event_authority"
                    (pix.flagged_events if ev.flag else pix.events).append(ev)
            if not tx.success:                              # F1
                for ev in pix.events:
                    ev.flag, ev.reason = FAILED_TX_EVENT, "transaction failed (meta.err is set)"
                pix.failed_events, pix.events = pix.events, []
                failed.extend(pix.failed_events)
            usable.extend(pix.events)
            flags.extend(pix.flagged_events)
            pixs.append(pix)
        for k in inner:                                     # event-shaped calls nobody legitimately emitted
            if _is_event_call(k) and (ti, k.inner_index) not in claimed:
                ev = _decode_event(k)
                ev.flag, ev.reason = EVENT_PROVENANCE, "event-shaped call with no same-program parent"
                flags.append(ev)
        top = tx.instructions[ti]
        if _is_event_call(top):
            ev = _decode_event(top)
            ev.flag, ev.reason = EVENT_PROVENANCE, "event-shaped TOP-level instruction"
            flags.append(ev)
    res = Scan(pixs, usable if tx.success else [], failed, flags, tx.no_inner_ix, tx.success)
    try:
        tx._p0_scan = res                                   # type: ignore[attr-defined]
    except AttributeError:
        pass
    return res


def events_in_tx(tx: Tx) -> "list[Event]":
    """Usable events only. Empty for a failed transaction (F1) or one without inner instructions (F4)."""
    return scan(tx).events


def event_flags(tx: Tx) -> dict:
    return scan(tx).counts()


def program_instructions(tx: Tx, programs: tuple = (PUMP_PROGRAM, PUMPSWAP_PROGRAM)) -> "list[ProgramIx]":
    """Every instruction (top-level or CPI) of the given programs. For a FAILED transaction the
    instructions (arguments, accounts) are returned, but `events` is always empty (F1)."""
    return [p for p in scan(tx).pixs if p.program in programs]


def named_accounts(pix: ProgramIx) -> dict:
    """Map the IDL account names of an instruction to the addresses actually passed."""
    dec = decoder_for_program(pix.program)
    if dec is None or pix.name not in dec.ix_by_name:
        return {}
    names = [a["name"] for a in dec.ix_by_name[pix.name]["accounts"]]
    return {n: pix.accounts[i] for i, n in enumerate(names) if i < len(pix.accounts)}


def amm_trades(tx: Tx) -> "list[ProgramIx]":
    """PumpSwap trades that changed state: successful transactions only (F1). Use program_instructions()
    for the ARGUMENTS of failed trades."""
    if not tx.success:
        return []
    return [p for p in program_instructions(tx, (PUMPSWAP_PROGRAM,)) if p.name in AMM_TRADES]


def trade_event(pix: ProgramIx) -> Optional[Event]:
    want = "BuyEvent" if pix.name in AMM_BUYS else "SellEvent" if pix.name in AMM_SELLS else "TradeEvent"
    for e in pix.events:
        if e.name == want:
            return e
    return None
