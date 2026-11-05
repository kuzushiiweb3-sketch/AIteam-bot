"""Test helpers: an IDL-driven Borsh ENCODER (the mirror of p0.borsh), a transaction builder that
produces getTransaction-shaped results, and a scripted fake transport.

Everything built here is labelled "synthetic" (docs/tech-stack.md s.8). Real-data anchors are:
  * tests/fixtures/feeconfig_sdk_rows.json + data/feeconfig_mainnet_2026-09-08.b64 (Pump's SDK capture)
  * the documented PDAs (test-plan s.2, fee-model s.4)
  * fee-model.md s.5 worked example
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any

from p0.b58 import b58decode, b58encode, pubkey_bytes
from p0.borsh import _INTS, _defined_name
from p0.net import NetError
from p0.txparse import EVENT_PREFIX

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


# ---- Borsh encoder -------------------------------------------------------------------------------
def enc(dec, t: Any, v: Any) -> bytes:
    if isinstance(t, str):
        if t in _INTS:
            n, signed = _INTS[t]
            return int(v).to_bytes(n, "little", signed=signed)
        if t == "bool":
            return b"\x01" if v else b"\x00"
        if t == "pubkey":
            return pubkey_bytes(v)
        if t == "string":
            raw = v.encode("utf-8")
            return len(raw).to_bytes(4, "little") + raw
        if t == "bytes":
            raw = bytes.fromhex(v)
            return len(raw).to_bytes(4, "little") + raw
        raise ValueError(t)
    if "vec" in t:
        return len(v).to_bytes(4, "little") + b"".join(enc(dec, t["vec"], x) for x in v)
    if "option" in t:
        return b"\x00" if v is None else b"\x01" + enc(dec, t["option"], v)
    if "array" in t:
        inner, n = t["array"]
        if inner == "u8":
            return bytes.fromhex(v)
        return b"".join(enc(dec, inner, x) for x in v)
    if "defined" in t:
        return enc_named(dec, _defined_name(t), v)
    raise ValueError(t)


def default_for(dec, t: Any) -> Any:
    if isinstance(t, str):
        return {"bool": False, "pubkey": "11111111111111111111111111111111", "string": "", "bytes": ""}.get(t, 0)
    if "vec" in t:
        return []
    if "option" in t:
        return None
    if "array" in t:
        inner, n = t["array"]
        return "00" * n if inner == "u8" else [default_for(dec, inner) for _ in range(n)]
    if "defined" in t:
        ty = dec.types[_defined_name(t)]["type"]
        if ty["kind"] == "enum":
            return ty["variants"][0]["name"]
        fs = ty["fields"]
        if fs and not isinstance(fs[0], dict):
            vals = [default_for(dec, f) for f in fs]
            return vals[0] if len(vals) == 1 else vals
        return {f["name"]: default_for(dec, f["type"]) for f in fs}
    raise ValueError(t)


def enc_named(dec, name: str, v: Any) -> bytes:
    ty = dec.types[name]["type"]
    if ty["kind"] == "enum":
        names = [x["name"] for x in ty["variants"]]
        return bytes([names.index(v)])
    fs = ty["fields"]
    if fs and not isinstance(fs[0], dict):
        vals = v if isinstance(v, list) and len(fs) > 1 else [v]
        return b"".join(enc(dec, f, x) for f, x in zip(fs, vals))
    return b"".join(enc(dec, f["type"], v.get(f["name"], default_for(dec, f["type"]))) for f in fs)


def struct_bytes(dec, name: str, values: dict) -> bytes:
    return enc_named(dec, name, values)


def account_bytes(dec, name: str, values: dict) -> bytes:
    return dec.account_disc[name] + struct_bytes(dec, name, values)


def event_cpi_data(dec, name: str, values: dict) -> bytes:
    return EVENT_PREFIX + dec.event_disc[name] + struct_bytes(dec, name, values)


def ix_data(dec, name: str, args: dict) -> bytes:
    ix = dec.ix_by_name[name]
    return bytes(ix["discriminator"]) + b"".join(enc(dec, a["type"], args.get(a["name"], default_for(dec, a["type"])))
                                                 for a in ix["args"])


# ---- transactions ---------------------------------------------------------------------------------
def compact_u16(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def wire_message(keys: list, header: tuple, instructions: list, version="legacy", lookups=()) -> bytes:
    """instructions: [(program_index, [account indexes], data bytes)]"""
    m = bytearray()
    if version != "legacy":
        m.append(0x80 | int(version))
    m += bytes(header)
    m += compact_u16(len(keys)) + b"".join(pubkey_bytes(k) for k in keys)
    m += bytes(32)                                       # recent blockhash (zeros)
    m += compact_u16(len(instructions))
    for prog, accs, data in instructions:
        m.append(prog)
        m += compact_u16(len(accs)) + bytes(accs)
        m += compact_u16(len(data)) + data
    if version != "legacy":
        m += compact_u16(len(lookups))
        for table, w, r in lookups:
            m += pubkey_bytes(table) + compact_u16(len(w)) + bytes(w) + compact_u16(len(r)) + bytes(r)
    return bytes(m)


def wire_tx(num_sigs: int, message: bytes) -> bytes:
    return compact_u16(num_sigs) + bytes(64) * num_sigs + message


class TxBuilder:
    """Collects keys and instructions, then emits a getTransaction(base64)-shaped result."""

    def __init__(self, signer: str, slot: int = 1000, block_time: int = 1_760_000_000) -> None:
        self.keys = [signer]
        self.top = []          # (program, [accounts], data)
        self.inner = {}        # top index -> [(program, [accounts], data, stack_height)]
        self.slot, self.block_time = slot, block_time
        self.err = None
        self.fee = 5000
        self.logs = []
        self.pre_tok, self.post_tok = [], []
        self.pre_bal, self.post_bal = None, None

    def k(self, addr: str) -> int:
        if addr not in self.keys:
            self.keys.append(addr)
        return self.keys.index(addr)

    def add(self, program: str, accounts: list, data: bytes) -> int:
        self.top.append((program, accounts, data))
        return len(self.top) - 1

    def add_inner(self, top_index: int, program: str, accounts: list, data: bytes, stack_height: int = 2) -> None:
        self.inner.setdefault(top_index, []).append((program, accounts, data, stack_height))

    def token_balance(self, account: str, mint: str, owner: str, pre: int, post: int,
                      program: str = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA") -> None:
        idx = self.k(account)
        for lst, amt in ((self.pre_tok, pre), (self.post_tok, post)):
            if amt is not None:
                lst.append({"accountIndex": idx, "mint": mint, "owner": owner, "programId": program,
                            "uiTokenAmount": {"amount": str(amt), "decimals": 6}})

    def result(self) -> dict:
        for prog, accs, _ in self.top:
            self.k(prog)
            for a in accs:
                self.k(a)
        for lst in self.inner.values():
            for prog, accs, _, _ in lst:
                self.k(prog)
                for a in accs:
                    self.k(a)
        ixs = [(self.keys.index(p), [self.keys.index(a) for a in accs], d) for p, accs, d in self.top]
        msg = wire_message(self.keys, (1, 0, 0), ixs, version=0)
        raw = wire_tx(1, msg)
        inner = [{"index": ti, "instructions": [{"programIdIndex": self.keys.index(p), "accounts": [self.keys.index(a) for a in accs],
                                                 "data": b58encode(d), "stackHeight": h} for p, accs, d, h in lst]}
                 for ti, lst in sorted(self.inner.items())]
        n = len(self.keys)
        return {"slot": self.slot, "blockTime": self.block_time, "version": 0,
                "transaction": [base64.b64encode(raw).decode(), "base64"],
                "meta": {"err": self.err, "fee": self.fee, "innerInstructions": inner, "logMessages": self.logs,
                         "preBalances": self.pre_bal or [0] * n, "postBalances": self.post_bal or [0] * n,
                         "preTokenBalances": self.pre_tok, "postTokenBalances": self.post_tok,
                         "loadedAddresses": {"writable": [], "readonly": []}, "computeUnitsConsumed": 50_000}}


# ---- fake transport ------------------------------------------------------------------------------------
class FakeTransport:
    """Scripted responses. `handler(method, params, url) -> (status, headers, body_bytes)` or raise NetError."""

    def __init__(self, handler=None) -> None:
        self.calls = []
        self.handler = handler

    def __call__(self, method, url, body, headers, timeout_s, max_bytes):
        payload = json.loads(body) if body else None
        self.calls.append({"http_method": method, "url": url, "payload": payload, "timeout": timeout_s})
        if self.handler is None:
            return 200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": "ok"}).encode()
        rpc_method = payload.get("method") if isinstance(payload, dict) else None
        params = payload.get("params") if isinstance(payload, dict) else None
        return self.handler(rpc_method, params, url)


def ok(result: Any) -> tuple:
    return 200, {}, json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()


def blocked(host: str):
    raise NetError("blocked", host, "Tunnel connection failed: 403 Forbidden")


def account_value(data: bytes, owner: str, space: int | None = None) -> dict:
    return {"data": [base64.b64encode(data).decode(), "base64"], "owner": owner, "lamports": 1, "executable": False,
            "rentEpoch": 0, "space": len(data) if space is None else space}


def load_fixture(name: str) -> Any:
    with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as f:
        return json.load(f)


__all__ = ["enc", "struct_bytes", "account_bytes", "event_cpi_data", "ix_data", "TxBuilder", "FakeTransport", "ok",
           "blocked", "account_value", "load_fixture", "b58decode"]
