"""Turn a getTransaction result (encoding "json" or "base64") into one plain structure.

Nothing here touches the network. Everything is decoded from the saved response.

Key facts used (tags):
  * Message layout (legacy and v0), compact-u16 lengths, address-table lookups, and the full
    account list = static keys + meta.loadedAddresses.writable + .readonly   [UNVERIFIED from memory
    of the Solana wire format; the offline tests round-trip it and A03/A04 confirm on real data]
  * meta.innerInstructions entries carry base58 `data` and `stackHeight`     [UNVERIFIED; A04 confirms]
  * an ABSENT or null innerInstructions is recorded as no_inner_ix (TS-6 F4): it means "events can't be
    seen", never "there were no events". An empty list [] means there really were no inner instructions.
  * Anchor self-CPI events start with the 8-byte prefix e445a52e51cb9a1d     [DERIVED, test-plan s.2]
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Any, Optional

from .b58 import b58decode, b58encode

EVENT_PREFIX = bytes.fromhex("e445a52e51cb9a1d")
COMPUTE_BUDGET = "ComputeBudget111111111111111111111111111111"
SYSTEM_PROGRAM = "11111111111111111111111111111111"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
TOKEN_PROGRAMS = (TOKEN_PROGRAM, TOKEN_2022_PROGRAM)
# Precompiles whose signatures are charged like transaction signatures (data[0] = count).
PRECOMPILES = ("Ed25519SigVerify111111111111111111111111111", "KeccakSecp256k11111111111111111111111111111",
               "Secp256r1SigVerify1111111111111111111111111")


@dataclass
class Ix:
    program: str
    accounts: list
    data: bytes
    top_index: int
    inner_index: Optional[int]     # None for the top-level instruction itself
    stack_height: Optional[int]


@dataclass
class Tx:
    signature: str
    slot: Optional[int]
    block_time: Optional[int]
    err: Any
    fee: Optional[int]
    cu_consumed: Optional[int]
    logs: list
    account_keys: list
    num_required_signatures: int
    num_readonly_signed: int
    num_readonly_unsigned: int
    num_static_keys: int
    instructions: list                 # top-level Ix
    inner: dict                        # top_index -> [Ix]
    pre_balances: list
    post_balances: list
    pre_token_balances: list
    post_token_balances: list
    lookups: list                      # [(table, [writable idx], [readonly idx])]
    loaded_writable: list
    loaded_readonly: list
    version: Any
    raw_encoding: str
    signatures: list = field(default_factory=list)
    no_inner_ix: bool = False          # meta.innerInstructions absent or null: "can't see events" (TS-6 F4)

    @property
    def success(self) -> bool:
        return self.err is None

    @property
    def signers(self) -> list:
        return self.account_keys[: self.num_required_signatures]

    def is_writable(self, idx: int) -> bool:
        h = self.num_required_signatures
        if idx < h:
            return idx < h - self.num_readonly_signed
        if idx < self.num_static_keys:
            return idx < self.num_static_keys - self.num_readonly_unsigned
        return idx < self.num_static_keys + len(self.loaded_writable)

    def flat(self, top_index: int) -> list:
        """The top-level instruction followed by its inner instructions, in order."""
        return [self.instructions[top_index]] + list(self.inner.get(top_index, []))

    def all_ixs(self) -> list:
        out = []
        for i in range(len(self.instructions)):
            out.extend(self.flat(i))
        return out

    @property
    def log_truncated(self) -> bool:
        return any("Log truncated" in (line or "") for line in self.logs)


# ---- wire-format parsing (base64 encoding) ---------------------------------------------------
def _compact_u16(buf: bytes, off: int) -> "tuple[int, int]":
    val = 0
    shift = 0
    for i in range(3):
        if off >= len(buf):
            raise ValueError("compact-u16 runs past the end")
        b = buf[off]
        off += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, off
        shift += 7
    raise ValueError("compact-u16 too long")


def parse_wire_transaction(raw: bytes) -> dict:
    off = 0
    nsig, off = _compact_u16(raw, off)
    sigs = []
    for _ in range(nsig):
        sigs.append(b58encode(raw[off:off + 64]))
        off += 64
    version: Any = "legacy"
    if raw[off] & 0x80:
        version = raw[off] & 0x7F
        off += 1
    header = (raw[off], raw[off + 1], raw[off + 2])
    off += 3
    nkeys, off = _compact_u16(raw, off)
    keys = []
    for _ in range(nkeys):
        keys.append(b58encode(raw[off:off + 32]))
        off += 32
    blockhash = b58encode(raw[off:off + 32])
    off += 32
    nix, off = _compact_u16(raw, off)
    ixs = []
    for _ in range(nix):
        prog = raw[off]
        off += 1
        nacc, off = _compact_u16(raw, off)
        accs = list(raw[off:off + nacc])
        off += nacc
        dlen, off = _compact_u16(raw, off)
        data = raw[off:off + dlen]
        off += dlen
        ixs.append({"programIdIndex": prog, "accounts": accs, "data": data})
    lookups = []
    if version != "legacy":
        nl, off = _compact_u16(raw, off)
        for _ in range(nl):
            table = b58encode(raw[off:off + 32])
            off += 32
            nw, off = _compact_u16(raw, off)
            w = list(raw[off:off + nw])
            off += nw
            nr, off = _compact_u16(raw, off)
            r = list(raw[off:off + nr])
            off += nr
            lookups.append((table, w, r))
    if off != len(raw):
        raise ValueError(f"{len(raw) - off} unexpected trailing bytes in transaction")
    return {"signatures": sigs, "version": version, "header": header, "keys": keys,
            "blockhash": blockhash, "instructions": ixs, "lookups": lookups}


def _ix_data(d: Any) -> bytes:
    if isinstance(d, (bytes, bytearray)):
        return bytes(d)
    if isinstance(d, str):
        return b58decode(d)
    raise ValueError("unknown instruction data form")


def normalize(result: dict, signature: Optional[str] = None) -> Tx:
    if not isinstance(result, dict):
        raise ValueError("getTransaction returned no transaction")
    meta = result.get("meta") or {}
    txf = result.get("transaction")
    if isinstance(txf, list) and len(txf) == 2 and txf[1] == "base64":
        w = parse_wire_transaction(base64.b64decode(txf[0]))
        header = w["header"]
        static = w["keys"]
        top_raw = w["instructions"]
        lookups = w["lookups"]
        version = w["version"]
        sigs = w["signatures"]
        encoding = "base64"
    elif isinstance(txf, dict):
        msg = txf["message"]
        h = msg["header"]
        header = (h["numRequiredSignatures"], h["numReadonlySignedAccounts"], h["numReadonlyUnsignedAccounts"])
        static = [k if isinstance(k, str) else k["pubkey"] for k in msg["accountKeys"]]
        top_raw = [{"programIdIndex": i["programIdIndex"], "accounts": i["accounts"], "data": i["data"]}
                   for i in msg["instructions"]]
        lookups = [(lk["accountKey"], lk["writableIndexes"], lk["readonlyIndexes"])
                   for lk in (msg.get("addressTableLookups") or [])]
        version = result.get("version", "legacy")
        sigs = txf.get("signatures", [])
        encoding = "json"
    else:
        raise ValueError("unsupported transaction encoding (use json or base64)")
    loaded = meta.get("loadedAddresses") or {}
    lw, lr = list(loaded.get("writable") or []), list(loaded.get("readonly") or [])
    keys = list(static) + lw + lr

    def key(i: int) -> str:
        return keys[i] if 0 <= i < len(keys) else f"<missing:{i}>"

    tops = []
    for n, ix in enumerate(top_raw):
        tops.append(Ix(key(ix["programIdIndex"]), [key(a) for a in ix["accounts"]], _ix_data(ix["data"]), n, None, 1))
    inner: dict = {}
    no_inner = meta.get("innerInstructions") is None
    for group in meta.get("innerInstructions") or []:
        ti = group["index"]
        lst = []
        for j, ix in enumerate(group.get("instructions", [])):
            lst.append(Ix(key(ix["programIdIndex"]), [key(a) for a in ix.get("accounts", [])],
                          _ix_data(ix.get("data", "")), ti, j, ix.get("stackHeight")))
        inner[ti] = lst
    return Tx(
        signature=signature or (sigs[0] if sigs else ""), slot=result.get("slot"), block_time=result.get("blockTime"),
        err=meta.get("err"), fee=meta.get("fee"), cu_consumed=meta.get("computeUnitsConsumed"),
        logs=list(meta.get("logMessages") or []), account_keys=keys, num_required_signatures=header[0],
        num_readonly_signed=header[1], num_readonly_unsigned=header[2], num_static_keys=len(static),
        instructions=tops, inner=inner, pre_balances=list(meta.get("preBalances") or []),
        post_balances=list(meta.get("postBalances") or []),
        pre_token_balances=list(meta.get("preTokenBalances") or []),
        post_token_balances=list(meta.get("postTokenBalances") or []),
        lookups=lookups, loaded_writable=lw, loaded_readonly=lr, version=version, raw_encoding=encoding,
        signatures=list(sigs), no_inner_ix=no_inner)


# ---- helpers over a normalized Tx -------------------------------------------------------------
def children(flat: list, pos: int) -> list:
    """Instructions invoked (directly or deeper) by flat[pos], using stackHeight."""
    base = flat[pos].stack_height or 1
    out = []
    for ix in flat[pos + 1:]:
        h = ix.stack_height
        if h is None:
            break
        if h <= base:
            break
        out.append(ix)
    return out


def compute_budget(tx: Tx) -> dict:
    out = {"cu_limit": None, "cu_price_micro_lamports": None, "heap": None, "loaded_data_limit": None}
    for ix in tx.instructions:
        if ix.program != COMPUTE_BUDGET or not ix.data:
            continue
        tag = ix.data[0]
        if tag == 2 and len(ix.data) >= 5:
            out["cu_limit"] = int.from_bytes(ix.data[1:5], "little")
        elif tag == 3 and len(ix.data) >= 9:
            out["cu_price_micro_lamports"] = int.from_bytes(ix.data[1:9], "little")
        elif tag == 1 and len(ix.data) >= 5:
            out["heap"] = int.from_bytes(ix.data[1:5], "little")
        elif tag == 4 and len(ix.data) >= 5:
            out["loaded_data_limit"] = int.from_bytes(ix.data[1:5], "little")
    return out


def precompile_signatures(tx: Tx) -> int:
    return sum(ix.data[0] for ix in tx.instructions if ix.program in PRECOMPILES and ix.data)


def system_transfers(tx: Tx) -> list:
    """[(from, to, lamports, top_index)] for System Program Transfer instructions (top-level and inner)."""
    out = []
    for ix in tx.all_ixs():
        if ix.program == SYSTEM_PROGRAM and len(ix.data) >= 12 and int.from_bytes(ix.data[:4], "little") == 2 \
                and len(ix.accounts) >= 2:
            out.append((ix.accounts[0], ix.accounts[1], int.from_bytes(ix.data[4:12], "little"), ix.top_index))
    return out


def token_ops(tx: Tx) -> list:
    """Token / Token-2022 transfers and burns: dicts with kind, accounts, amount."""
    out = []
    for ix in tx.all_ixs():
        if ix.program not in TOKEN_PROGRAMS or not ix.data:
            continue
        tag, a = ix.data[0], ix.accounts
        amt = int.from_bytes(ix.data[1:9], "little") if len(ix.data) >= 9 else None
        if tag == 3 and len(a) >= 3:
            out.append({"kind": "transfer", "source": a[0], "dest": a[1], "owner": a[2], "amount": amt, "program": ix.program})
        elif tag == 12 and len(a) >= 4:
            out.append({"kind": "transferChecked", "source": a[0], "mint": a[1], "dest": a[2], "owner": a[3], "amount": amt, "program": ix.program})
        elif tag == 8 and len(a) >= 3:
            out.append({"kind": "burn", "account": a[0], "mint": a[1], "owner": a[2], "amount": amt, "program": ix.program})
        elif tag == 15 and len(a) >= 3:
            out.append({"kind": "burnChecked", "account": a[0], "mint": a[1], "owner": a[2], "amount": amt, "program": ix.program})
        elif tag == 17 and len(a) >= 1:
            out.append({"kind": "syncNative", "account": a[0], "program": ix.program})
    return out


def token_balance_map(entries: list, keys: list) -> dict:
    """account address -> {mint, owner, amount(int), program}"""
    out = {}
    for e in entries:
        idx = e.get("accountIndex")
        if idx is None or idx >= len(keys):
            continue
        ui = e.get("uiTokenAmount") or {}
        try:
            amt = int(ui.get("amount"))
        except (TypeError, ValueError):
            continue
        out[keys[idx]] = {"mint": e.get("mint"), "owner": e.get("owner"), "amount": amt,
                          "program": e.get("programId")}
    return out


def token_deltas(tx: Tx) -> dict:
    """account -> (mint, owner, post - pre). Accounts created or closed in the tx count from/to 0."""
    pre = token_balance_map(tx.pre_token_balances, tx.account_keys)
    post = token_balance_map(tx.post_token_balances, tx.account_keys)
    out = {}
    for acct in set(pre) | set(post):
        p = pre.get(acct, {})
        q = post.get(acct, {})
        out[acct] = (q.get("mint") or p.get("mint"), q.get("owner") or p.get("owner"),
                     q.get("amount", 0) - p.get("amount", 0), acct in pre, acct in post)
    return out


def lamport_delta(tx: Tx, address: str) -> Optional[int]:
    try:
        i = tx.account_keys.index(address)
    except ValueError:
        return None
    if i >= len(tx.pre_balances) or i >= len(tx.post_balances):
        return None
    return tx.post_balances[i] - tx.pre_balances[i]


def per_instruction_compute(tx: Tx) -> dict:
    """top-level index -> compute units consumed, from 'Program X consumed N of M' log lines at depth 1."""
    out: dict = {}
    top = -1
    depth = 0
    for line in tx.logs:
        if not line.startswith("Program "):
            continue
        parts = line.split()
        if len(parts) < 3 or parts[1] in ("log:", "data:", "return:", "consumption:"):
            continue
        if len(parts) >= 4 and parts[2] == "invoke":
            try:
                depth = int(parts[3].strip("[]"))
            except ValueError:
                continue
            if depth == 1:
                top += 1
        elif len(parts) >= 6 and parts[2] == "consumed" and depth == 1:
            try:
                out[top] = int(parts[3])
            except ValueError:
                pass
        elif parts[2] == "success" or parts[2].startswith("failed"):
            depth = max(0, depth - 1)
    return out


def program_data_logs(tx: Tx) -> list:
    """Base64 payloads of 'Program data:' log lines (the log-based event path)."""
    out = []
    for line in tx.logs:
        if line.startswith("Program data: "):
            try:
                out.append(base64.b64decode(line[len("Program data: "):].strip()))
            except (ValueError, TypeError):
                out.append(b"")
    return out
