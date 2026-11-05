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
from dataclasses import dataclass
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
@dataclass
class Event:
    program: str
    name: str
    fields: dict
    top_index: int
    inner_index: Optional[int]
    stack_height: Optional[int]


def events_in_tx(tx: Tx) -> "list[Event]":
    out = []
    for ix in tx.all_ixs():
        if ix.data[:8] != EVENT_PREFIX:
            continue
        dec = decoder_for_program(ix.program)
        if dec is None:
            continue
        try:
            ev = dec.decode_event(ix.data[8:])
        except ShapeError as e:
            out.append(Event(ix.program, "_SHAPE_ERROR", {"error": str(e), "disc": ix.data[8:16].hex()},
                             ix.top_index, ix.inner_index, ix.stack_height))
            continue
        if ev is None:
            out.append(Event(ix.program, "_UNKNOWN_EVENT", {"disc": ix.data[8:16].hex()},
                             ix.top_index, ix.inner_index, ix.stack_height))
            continue
        out.append(Event(ix.program, ev["_name"], ev, ix.top_index, ix.inner_index, ix.stack_height))
    return out


@dataclass
class ProgramIx:
    program: str
    name: str
    args: dict
    accounts: list
    ix: Ix
    events: list            # events emitted by this instruction (self-CPI children of the same program)


def program_instructions(tx: Tx, programs: tuple = (PUMP_PROGRAM, PUMPSWAP_PROGRAM)) -> "list[ProgramIx]":
    """Every instruction (top-level or CPI) of the given programs, each with its own events."""
    out = []
    for ti in range(len(tx.instructions)):
        flat = tx.flat(ti)
        has_heights = all(k.stack_height is not None for k in tx.inner.get(ti, []))
        for pos, ix in enumerate(flat):
            if ix.program not in programs or ix.data[:8] == EVENT_PREFIX:
                continue
            dec = decoder_for_program(ix.program)
            try:
                args = dec.decode_instruction(ix.data) if dec else None
            except ShapeError as e:
                args = {"_name": "_SHAPE_ERROR", "error": str(e)}
            name = args["_name"] if args else "_UNKNOWN_IX:" + ix.data[:8].hex()
            evs = []
            if has_heights:
                kids = children(flat, pos)
                base = ix.stack_height or 1
                for k in kids:
                    if k.program == ix.program and k.data[:8] == EVENT_PREFIX and (k.stack_height in (None, base + 1)):
                        evs.append(k)
            else:
                # no stackHeight information: take same-program event CPIs up to the next same-program ix
                for k in flat[pos + 1:]:
                    if k.program == ix.program and k.data[:8] != EVENT_PREFIX:
                        break
                    if k.program == ix.program and k.data[:8] == EVENT_PREFIX:
                        evs.append(k)
            decoded = []
            for k in evs:
                try:
                    ev = dec.decode_event(k.data[8:]) if dec else None
                except ShapeError as e:
                    ev = {"_name": "_SHAPE_ERROR", "error": str(e)}
                decoded.append(Event(k.program, ev["_name"] if ev else "_UNKNOWN_EVENT", ev or {},
                                     k.top_index, k.inner_index, k.stack_height))
            out.append(ProgramIx(ix.program, name, args or {}, ix.accounts, ix, decoded))
    return out


def named_accounts(pix: ProgramIx) -> dict:
    """Map the IDL account names of an instruction to the addresses actually passed."""
    dec = decoder_for_program(pix.program)
    if dec is None or pix.name not in dec.ix_by_name:
        return {}
    names = [a["name"] for a in dec.ix_by_name[pix.name]["accounts"]]
    return {n: pix.accounts[i] for i, n in enumerate(names) if i < len(pix.accounts)}


def amm_trades(tx: Tx) -> "list[ProgramIx]":
    return [p for p in program_instructions(tx, (PUMPSWAP_PROGRAM,)) if p.name in AMM_TRADES]


def trade_event(pix: ProgramIx) -> Optional[Event]:
    want = "BuyEvent" if pix.name in AMM_BUYS else "SellEvent" if pix.name in AMM_SELLS else "TradeEvent"
    for e in pix.events:
        if e.name == want:
            return e
    return None
