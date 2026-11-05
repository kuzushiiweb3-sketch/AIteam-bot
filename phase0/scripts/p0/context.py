"""Run context shared by every tier-A row: clients, store, budget, helpers and options."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

from .http_get import HttpGetClient
from .redact import log
from .rpc import PROVIDERS, MissingKey, RpcClient
from .store import Store
from .txparse import Tx, normalize


class NeedRow(RuntimeError):
    """A row needs another row's artifacts first."""

    def __init__(self, row: str) -> None:
        self.row = row
        super().__init__(f"needs row {row} to have run first")


@dataclass
class Options:
    quick: bool = False
    public_fallback: bool = False
    a18_minutes: float = 10.0
    t6_stop_after_calibration: bool = False
    a20_url_template: Optional[str] = None
    verbose: bool = False


@dataclass
class Ctx:
    store: Store
    budget: Any
    helius: Optional[RpcClient]
    public: Optional[RpcClient]
    jito: Optional[RpcClient]
    get: HttpGetClient
    opts: Options = field(default_factory=Options)
    row: str = "_none"
    hosts_used: set = field(default_factory=set)
    provider_used: set = field(default_factory=set)
    blocked_hosts: set = field(default_factory=set)

    # ---- small helpers ---------------------------------------------------------------------
    def log(self, *parts: Any) -> None:
        log(f"[{self.row}]", *parts)

    def dur(self, full_s: float, quick_s: float) -> float:
        return quick_s if self.opts.quick else full_s

    def n(self, full: int, quick: int) -> int:
        return quick if self.opts.quick else full

    def artifacts(self, row: str) -> Any:
        a = self.store.load_artifacts(row)
        if a is None:
            raise NeedRow(row)
        return a

    def rpc(self, fallback_ok: bool = True) -> RpcClient:
        if self.helius is not None:
            return self.helius
        if fallback_ok and self.opts.public_fallback and self.public is not None:
            return self.public
        raise MissingKey("HELIUS_API_KEY is not set (value is never shown). Add it to the environment, "
                         "or re-run with --public-fallback for rows that allow api.mainnet-beta.solana.com")

    def call(self, method: str, params: Any = None, client: Optional[RpcClient] = None, **kw) -> Any:
        c = client or self.rpc()
        self.hosts_used.add(c.provider.host)
        self.provider_used.add(c.provider.name)
        return c.call(method, params, row=self.row, **kw)

    def call_meta(self, method: str, params: Any = None, client: Optional[RpcClient] = None, **kw):
        c = client or self.rpc()
        self.hosts_used.add(c.provider.host)
        self.provider_used.add(c.provider.name)
        return c.call_meta(method, params, row=self.row, **kw)

    def http_get(self, url: str, **kw):
        from .net import host_of
        self.hosts_used.add(host_of(url))
        return self.get.get(url, row=self.row, **kw)

    # ---- chain helpers ----------------------------------------------------------------------
    def get_tx_raw(self, sig: str, encoding: str = "base64") -> Optional[dict]:
        kind = "tx-" + encoding
        cached = self.store.cache_get(kind, sig)
        if cached is not None:
            return cached.get("result")
        res = self.call("getTransaction", [sig, {"encoding": encoding, "maxSupportedTransactionVersion": 0,
                                                 "commitment": "finalized"}])
        if res is not None:
            self.store.cache_put(kind, sig, {"result": res, "fetched_by": self.row,
                                             "provider": next(iter(self.provider_used), "?")})
        return res

    def get_tx(self, sig: str, encoding: str = "base64") -> Optional[Tx]:
        res = self.get_tx_raw(sig, encoding)
        if res is None:
            return None
        return normalize(res, sig)

    def signatures(self, address: str, *, max_total: int = 1000, before: Optional[str] = None,
                   until: Optional[str] = None, stop_before_time: Optional[int] = None,
                   stop_before_slot: Optional[int] = None, page: int = 1000,
                   commitment: str = "finalized") -> Iterator[dict]:
        """Newest-first signature entries for an address, paging with `before`."""
        got = 0
        cursor = before
        while got < max_total:
            cfg: dict = {"limit": min(page, max_total - got), "commitment": commitment}
            if cursor:
                cfg["before"] = cursor
            if until:
                cfg["until"] = until
            batch = self.call("getSignaturesForAddress", [address, cfg]) or []
            if not batch:
                return
            for e in batch:
                if stop_before_time is not None and e.get("blockTime") is not None and e["blockTime"] < stop_before_time:
                    return
                if stop_before_slot is not None and e.get("slot") is not None and e["slot"] < stop_before_slot:
                    return
                got += 1
                yield e
                if got >= max_total:
                    return
            if len(batch) < cfg["limit"]:
                return
            cursor = batch[-1]["signature"]

    def multiple_accounts(self, addresses: list, encoding: str = "base64", data_slice: Optional[dict] = None,
                          client: Optional[RpcClient] = None) -> dict:
        out: dict = {}
        for i in range(0, len(addresses), 100):
            chunk = addresses[i:i + 100]
            cfg: dict = {"encoding": encoding, "commitment": "confirmed"}
            if data_slice:
                cfg["dataSlice"] = data_slice
            res = self.call("getMultipleAccounts", [chunk, cfg], client=client) or {}
            for a, v in zip(chunk, res.get("value") or []):
                out[a] = v
        return out

    def account(self, address: str, encoding: str = "base64", data_slice: Optional[dict] = None,
                client: Optional[RpcClient] = None) -> Optional[dict]:
        cfg: dict = {"encoding": encoding, "commitment": "confirmed"}
        if data_slice:
            cfg["dataSlice"] = data_slice
        res = self.call("getAccountInfo", [address, cfg], client=client) or {}
        return res.get("value")

    def now(self) -> int:
        return int(time.time())


def build_clients(budget, recorder, api_key: Optional[str], transport=None) -> "tuple[Optional[RpcClient], RpcClient, RpcClient]":
    kw = {"recorder": recorder}
    if transport is not None:
        kw["transport"] = transport
    helius = RpcClient(PROVIDERS["helius"], budget, api_key=api_key, **kw) if api_key else None
    public = RpcClient(PROVIDERS["public"], budget, **kw)
    jito = RpcClient(PROVIDERS["jito"], budget, **kw)
    return helius, public, jito
