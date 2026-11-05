"""Program-derived addresses (PDAs) and associated token accounts, standard library only.

A PDA is sha256(seeds || bump || program_id || "ProgramDerivedAddress"), taking the first bump
from 255 down whose hash is NOT a point on the Ed25519 curve. The curve test below is plain
field arithmetic (it mirrors curve25519-dalek's CompressedEdwardsY::decompress().is_some(),
which Solana uses). It involves no keys and cannot sign anything.
"""

from __future__ import annotations

import hashlib

from .b58 import b58encode, pubkey_bytes

_P = 2 ** 255 - 19
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
PDA_MARKER = b"ProgramDerivedAddress"
MAX_SEED_LEN = 32
MAX_SEEDS = 16

ATA_PROGRAM = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


def is_on_curve(b32: bytes) -> bool:
    if len(b32) != 32:
        raise ValueError("need 32 bytes")
    y = int.from_bytes(b32, "little") & ((1 << 255) - 1)
    y %= _P
    yy = y * y % _P
    u = (yy - 1) % _P
    v = (_D * yy + 1) % _P
    if v == 0:
        return u == 0
    x2 = u * pow(v, _P - 2, _P) % _P
    if x2 == 0:
        return True
    return pow(x2, (_P - 1) // 2, _P) == 1


def _seed_bytes(seed) -> bytes:
    if isinstance(seed, bytes):
        return seed
    if isinstance(seed, str):
        # a base58 address (32 bytes) or, failing that, a UTF-8 literal
        try:
            return pubkey_bytes(seed)
        except ValueError:
            return seed.encode("utf-8")
    raise TypeError("seed must be bytes or str")


def create_program_address(seeds: list, program_id: str) -> bytes:
    if len(seeds) > MAX_SEEDS:
        raise ValueError("too many seeds")
    h = hashlib.sha256()
    for s in seeds:
        if len(s) > MAX_SEED_LEN:
            raise ValueError("seed too long")
        h.update(s)
    h.update(pubkey_bytes(program_id))
    h.update(PDA_MARKER)
    out = h.digest()
    if is_on_curve(out):
        raise ValueError("on curve")
    return out


def find_program_address(seeds: list, program_id: str) -> "tuple[str, int]":
    raw = [_seed_bytes(s) for s in seeds]
    for bump in range(255, -1, -1):
        try:
            addr = create_program_address(raw + [bytes([bump])], program_id)
        except ValueError as e:
            if str(e) == "on curve":
                continue
            raise
        return b58encode(addr), bump
    raise ValueError("no viable bump")


def lit(text: str) -> bytes:
    """A literal UTF-8 seed (use this, not a str, when the text could look like base58)."""
    return text.encode("utf-8")


def ata(owner: str, mint: str, token_program: str = TOKEN_PROGRAM) -> str:
    return find_program_address([pubkey_bytes(owner), pubkey_bytes(token_program), pubkey_bytes(mint)], ATA_PROGRAM)[0]
