"""A small IDL-driven Borsh decoder for Anchor IDLs (spec 0.1.0). Read-only, integers exact.

Supported types (everything the three pinned Pump IDLs use): bool, u8/i8 ... u128/i128, pubkey,
string, bytes, vec<T>, option<T>, [T; N], defined structs (named or tuple fields) and enums.

Lenient decoding (`decode_struct(..., lenient=True)`): if the data ends exactly on a field
boundary, the remaining fields are reported in `_missing` (Pump docs: older, shorter Pool layouts
read missing trailing fields as 0). If data ends in the middle of a field, that is a shape error.
Extra bytes after the last field are reported as `_extra_bytes` (a newer layout than our IDL).
"""

from __future__ import annotations

import struct
from typing import Any

from .b58 import b58encode

_INTS = {"u8": (1, False), "i8": (1, True), "u16": (2, False), "i16": (2, True), "u32": (4, False),
         "i32": (4, True), "u64": (8, False), "i64": (8, True), "u128": (16, False), "i128": (16, True)}


class ShapeError(ValueError):
    """The bytes do not match the IDL layout (cut short mid-field, bad tag, bad length)."""


class Truncated(ShapeError):
    pass


def _defined_name(t: dict) -> str:
    d = t["defined"]
    return d["name"] if isinstance(d, dict) else d


class IdlDecoder:
    def __init__(self, idl: dict) -> None:
        self.idl = idl
        self.address = idl.get("address")
        self.types = {t["name"]: t for t in idl.get("types", [])}
        self.accounts = {bytes(a["discriminator"]): a["name"] for a in idl.get("accounts", [])}
        self.events = {bytes(e["discriminator"]): e["name"] for e in idl.get("events", [])}
        self.instructions = {bytes(i["discriminator"]): i for i in idl.get("instructions", [])}
        self.ix_by_name = {i["name"]: i for i in idl.get("instructions", [])}
        self.account_disc = {a["name"]: bytes(a["discriminator"]) for a in idl.get("accounts", [])}
        self.event_disc = {e["name"]: bytes(e["discriminator"]) for e in idl.get("events", [])}

    # ---- primitives --------------------------------------------------------------------------
    def decode(self, t: Any, buf: bytes, off: int) -> "tuple[Any, int]":
        if isinstance(t, str):
            if t in _INTS:
                n, signed = _INTS[t]
                if off + n > len(buf):
                    raise Truncated(f"need {n} bytes for {t} at {off}, have {len(buf) - off}")
                return int.from_bytes(buf[off:off + n], "little", signed=signed), off + n
            if t == "bool":
                if off + 1 > len(buf):
                    raise Truncated(f"need 1 byte for bool at {off}")
                b = buf[off]
                if b > 1:
                    raise ShapeError(f"bool byte {b} at {off}")
                return bool(b), off + 1
            if t == "pubkey":
                if off + 32 > len(buf):
                    raise Truncated(f"need 32 bytes for pubkey at {off}")
                return b58encode(buf[off:off + 32]), off + 32
            if t in ("string", "bytes"):
                n, off = self.decode("u32", buf, off)
                if off + n > len(buf):
                    raise Truncated(f"{t} of length {n} at {off} runs past the end")
                raw = buf[off:off + n]
                return (raw.decode("utf-8", "replace") if t == "string" else raw.hex()), off + n
            if t in ("f32", "f64"):
                n = 4 if t == "f32" else 8
                return struct.unpack_from("<f" if n == 4 else "<d", buf, off)[0], off + n
            raise ShapeError(f"unsupported primitive {t}")
        if "vec" in t:
            n, off = self.decode("u32", buf, off)
            if n > 1_000_000:
                raise ShapeError(f"vec length {n} is implausible")
            out = []
            for _ in range(n):
                v, off = self.decode(t["vec"], buf, off)
                out.append(v)
            return out, off
        if "option" in t:
            tag, off = self.decode("u8", buf, off)
            if tag == 0:
                return None, off
            if tag != 1:
                raise ShapeError(f"option tag {tag} at {off - 1}")
            return self.decode(t["option"], buf, off)
        if "array" in t:
            inner, n = t["array"]
            if inner == "u8":
                if off + n > len(buf):
                    raise Truncated(f"need {n} bytes for [u8;{n}] at {off}")
                return buf[off:off + n].hex(), off + n
            out = []
            for _ in range(n):
                v, off = self.decode(inner, buf, off)
                out.append(v)
            return out, off
        if "defined" in t:
            return self.decode_named(_defined_name(t), buf, off)
        raise ShapeError(f"unsupported type {t}")

    def decode_named(self, name: str, buf: bytes, off: int) -> "tuple[Any, int]":
        td = self.types.get(name)
        if td is None:
            raise ShapeError(f"type {name} not in IDL")
        ty = td["type"]
        if ty["kind"] == "struct":
            fields = ty.get("fields", [])
            if fields and not isinstance(fields[0], dict):      # tuple struct
                vals = []
                for f in fields:
                    v, off = self.decode(f, buf, off)
                    vals.append(v)
                return (vals[0] if len(vals) == 1 else vals), off
            out = {}
            for f in fields:
                out[f["name"]], off = self.decode(f["type"], buf, off)
            return out, off
        if ty["kind"] == "enum":
            idx, off = self.decode("u8", buf, off)
            variants = ty["variants"]
            if idx >= len(variants):
                raise ShapeError(f"enum {name} variant {idx} out of range")
            var = variants[idx]
            if not var.get("fields"):
                return var["name"], off
            vals = {}
            for i, f in enumerate(var["fields"]):
                key = f["name"] if isinstance(f, dict) else str(i)
                vals[key], off = self.decode(f["type"] if isinstance(f, dict) else f, buf, off)
            return {var["name"]: vals}, off
        raise ShapeError(f"unsupported type kind {ty['kind']}")

    # ---- structs with lenient tails ---------------------------------------------------------
    def decode_struct(self, name: str, buf: bytes, off: int = 0, lenient: bool = False) -> dict:
        ty = self.types[name]["type"]
        out: dict = {}
        missing = []
        fields = ty["fields"]
        for i, f in enumerate(fields):
            if lenient and off == len(buf):
                missing = [g["name"] for g in fields[i:]]
                break
            out[f["name"]], off = self.decode(f["type"], buf, off)
        out["_missing"] = missing
        out["_consumed"] = off
        out["_extra_bytes"] = len(buf) - off
        return out

    def field_offsets(self, name: str) -> "list[tuple[str, int, int]]":
        """(field, offset after the 8-byte discriminator, size) for fixed-size structs."""
        res = []
        off = 8
        for f in self.types[name]["type"]["fields"]:
            size = self.fixed_size(f["type"])
            res.append((f["name"], off, size))
            off += size
        return res

    def fixed_size(self, t: Any) -> int:
        if isinstance(t, str):
            if t in _INTS:
                return _INTS[t][0]
            if t == "bool":
                return 1
            if t == "pubkey":
                return 32
            raise ShapeError(f"{t} is not fixed size")
        if "array" in t:
            return self.fixed_size(t["array"][0]) * t["array"][1]
        if "defined" in t:
            ty = self.types[_defined_name(t)]["type"]
            if ty["kind"] == "struct":
                fs = ty["fields"]
                return sum(self.fixed_size(f["type"] if isinstance(f, dict) else f) for f in fs)
            if ty["kind"] == "enum" and not any(v.get("fields") for v in ty["variants"]):
                return 1
        raise ShapeError(f"{t} is not fixed size")

    # ---- accounts / events / instructions ---------------------------------------------------
    def decode_account(self, data: bytes, expect: str | None = None, lenient: bool = False) -> dict:
        disc = bytes(data[:8])
        name = self.accounts.get(disc)
        if name is None:
            raise ShapeError(f"unknown account discriminator {disc.hex()}")
        if expect and name != expect:
            raise ShapeError(f"expected account {expect}, got {name}")
        out = self.decode_struct(name, data, 8, lenient=lenient)
        out["_name"] = name
        out["_len"] = len(data)
        return out

    def decode_event(self, data: bytes) -> "dict | None":
        """data = event discriminator (8 bytes) + fields. Returns None if the discriminator is unknown."""
        name = self.events.get(bytes(data[:8]))
        if name is None:
            return None
        out = self.decode_struct(name, data, 8, lenient=True)
        out["_name"] = name
        return out

    def decode_instruction(self, data: bytes) -> "dict | None":
        ix = self.instructions.get(bytes(data[:8]))
        if ix is None:
            return None
        off = 8
        args: dict = {"_name": ix["name"], "_missing": []}
        for i, a in enumerate(ix["args"]):
            if off == len(data):
                # Anchor allows trailing Option args to be omitted by older clients
                args["_missing"] = [b["name"] for b in ix["args"][i:]]
                break
            args[a["name"]], off = self.decode(a["type"], data, off)
        args["_extra_bytes"] = len(data) - off
        return args
