"""The ONE shared JSON-RPC client for Phase 0. Read-only by construction.

Safety rules enforced here (red-team: start reading at `ALLOWED_METHODS` and `_check_call`):
  1. Hard allowlist of read-only methods per provider. Anything else -- including every method
     that sends, simulates or airdrops -- is refused with RpcRefused BEFORE any network activity
     and before the budget is touched. There is no "raw" or batch call path.
  2. Hard host list. A provider can only point at the hosts below; Helius Sender and every other
     host are impossible to POST to through this module.
  3. The Helius key is read only from the environment variable HELIUS_API_KEY, registered with the
     redactor, kept in a private attribute, and only ever placed into the URL at send time.
     Every error message is redacted; no exception from the transport is chained.
  4. Budget (p0.budget) is charged before each attempt; rate limits (p0.ratelimit) before each
     attempt; every attempt has a timeout; 429 / 5xx / provider "try again" errors back off
     exponentially and honour Retry-After.

The allowlist is test-plan section 1 rule 1, plus four extras that only read node state:
getHealth, getVersion, getBlockTime and getEpochInfo.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .budget import Budget, BudgetExceeded
from .net import NetError, Transport, urllib_transport
from .ratelimit import RateLimiter
from .redact import REDACTOR, redact

KEY_ENV_VAR = "HELIUS_API_KEY"

# ---- the allowlist -------------------------------------------------------------------------
SOLANA_READ_METHODS = frozenset({
    "getAccountInfo", "getMultipleAccounts", "getProgramAccounts", "getSignaturesForAddress",
    "getTransaction", "getBlock", "getSlot", "getBlockHeight", "getBlockTime", "getLatestBlockhash",
    "isBlockhashValid", "getRecentPerformanceSamples", "getRecentPrioritizationFees",
    "getMinimumBalanceForRentExemption", "getTokenSupply", "getTokenLargestAccounts",
    "getHealth", "getVersion", "getEpochInfo",
})
HELIUS_ONLY_METHODS = frozenset({"getTransactionsForAddress", "getTokenAccounts"})
JITO_METHODS = frozenset({"getTipAccounts"})

DAS_METHODS = frozenset({"getTokenAccounts"})


@dataclass(frozen=True)
class Provider:
    name: str
    host: str
    paths: tuple            # allowed URL paths; the first is the default
    methods: frozenset
    rate_per_s: float
    das_rate_per_s: float = 0.0
    needs_key: bool = False


PROVIDERS = {
    # Helius free plan limit is 10 req/s, DAS 2 req/s [VERIFIED-SEARCH, test-plan s.1 rule 4]; we use 8 and 1.5.
    "helius": Provider("helius", "mainnet.helius-rpc.com", ("/",),
                       SOLANA_READ_METHODS | HELIUS_ONLY_METHODS, 8.0, 1.5, True),
    # Public RPC limits are about 100 requests / 10 s per IP and 40 / 10 s per method
    # [UNVERIFIED from memory; confirm on solana.com docs]. 3/s keeps well under both.
    "public": Provider("public", "api.mainnet-beta.solana.com", ("/",), SOLANA_READ_METHODS, 3.0),
    # Jito block engine: only getTipAccounts. Both paths are UNVERIFIED until docs.jito.wtf is read (A19).
    "jito": Provider("jito", "mainnet.block-engine.jito.wtf", ("/api/v1/getTipAccounts", "/api/v1/bundles"),
                     JITO_METHODS, 1.0),
}
ALLOWED_HOSTS = frozenset(p.host for p in PROVIDERS.values())

# JSON-RPC error codes that mean "try again shortly" (node behind, rate limited, not yet available).
RETRYABLE_RPC_CODES = frozenset({-32005, -32004, -32014, -32016, -32429, 429})


class RpcRefused(RuntimeError):
    """The call was refused locally. Nothing was sent and no budget was used."""


class RpcError(RuntimeError):
    def __init__(self, provider: str, method: str, message: str, code: Optional[int] = None,
                 http_status: Optional[int] = None) -> None:
        self.provider, self.method, self.code, self.http_status = provider, method, code, http_status
        self.message = redact(message)
        super().__init__(f"{provider}.{method} failed: {self.message}"
                         + (f" (code {code})" if code is not None else "")
                         + (f" (HTTP {http_status})" if http_status else ""))


class HostBlocked(RuntimeError):
    def __init__(self, host: str, detail: str) -> None:
        self.host = host
        super().__init__(f"BLOCKED: {host} ({redact(detail)})")


class MissingKey(RuntimeError):
    pass


def load_helius_key(environ: Optional[dict] = None) -> Optional[str]:
    """Read HELIUS_API_KEY from the environment. Never printed. Returns None if absent or malformed."""
    env = os.environ if environ is None else environ
    raw = env.get(KEY_ENV_VAR)
    if raw is None:
        return None
    key = raw.strip()
    if not key or len(key) < 8 or len(key) > 256 or any(c.isspace() for c in key) \
            or any(c in key for c in "&?#/\"'<>"):
        return None
    REDACTOR.register(key)
    return key


def _check_call(provider: Provider, method: str, params: Any, path: Optional[str]) -> None:
    """Raise RpcRefused unless this exact call is allowed. Pure function, no side effects."""
    if not isinstance(method, str) or method not in provider.methods:
        raise RpcRefused(f"method {method!r} is not on the read-only allowlist for {provider.name}")
    if path is not None and path not in provider.paths:
        raise RpcRefused(f"path {path!r} is not allowed for {provider.name}")
    if params is not None and not isinstance(params, (list, dict)):
        raise RpcRefused("params must be a JSON list or object")
    plist = params if isinstance(params, list) else []
    cfg = plist[1] if len(plist) > 1 and isinstance(plist[1], dict) else {}
    if method == "getProgramAccounts":
        ds = cfg.get("dataSlice")
        if not isinstance(ds, dict) or int(ds.get("length", 10**9)) > 512:
            raise RpcRefused("getProgramAccounts must carry a dataSlice of at most 512 bytes")
    if method == "getMultipleAccounts":
        if not plist or not isinstance(plist[0], list) or len(plist[0]) > 100:
            raise RpcRefused("getMultipleAccounts takes at most 100 addresses")
    if method == "getSignaturesForAddress":
        if int(cfg.get("limit", 1000)) > 1000:
            raise RpcRefused("getSignaturesForAddress limit is at most 1000")
    if method in ("getTransaction", "getBlock"):
        if cfg.get("maxSupportedTransactionVersion") != 0:
            raise RpcRefused(f"{method} must set maxSupportedTransactionVersion: 0")
    if method == "getBlock":
        if cfg.get("transactionDetails") not in ("full", "signatures", "accounts", "none"):
            raise RpcRefused("getBlock must set transactionDetails explicitly")
        if cfg.get("rewards") is not False:
            raise RpcRefused("getBlock must set rewards: false")


Recorder = Callable[[dict], None]


@dataclass
class CallMeta:
    latency_s: float
    attempts: int
    bytes: int
    http_status: int
    sha256: str
    context_slot: Optional[int] = None


@dataclass
class RpcClient:
    provider: Provider
    budget: Budget
    api_key: Optional[str] = field(default=None, repr=False)
    transport: Transport = urllib_transport
    timeout_s: float = 30.0
    max_retries: int = 5
    backoff_base_s: float = 0.5
    backoff_cap_s: float = 30.0
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = lambda: time.monotonic_ns() / 1e9     # intervals from monotonic_ns (TS-12)
    recorder: Optional[Recorder] = None
    limiter: Optional[RateLimiter] = None
    das_limiter: Optional[RateLimiter] = None
    _id: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        if self.provider.host not in ALLOWED_HOSTS or PROVIDERS.get(self.provider.name) != self.provider:
            raise RpcRefused(f"provider {self.provider.name!r} / host {self.provider.host!r} is not allowed")
        if self.provider.needs_key and not self.api_key:
            raise MissingKey(f"{KEY_ENV_VAR} is not set (value is never shown); {self.provider.host} needs it")
        if self.api_key:
            REDACTOR.register(self.api_key)
        if self.limiter is None:
            self.limiter = RateLimiter(self.provider.rate_per_s, clock=self.clock, sleep=self.sleep)
        if self.das_limiter is None and self.provider.das_rate_per_s:
            self.das_limiter = RateLimiter(self.provider.das_rate_per_s, clock=self.clock, sleep=self.sleep)

    def __repr__(self) -> str:  # never show the key
        return f"RpcClient(provider={self.provider.name}, host={self.provider.host})"

    def _url(self, path: str) -> str:
        url = f"https://{self.provider.host}{path}"
        if self.api_key:
            url += ("&" if "?" in url else "?") + "api-key=" + self.api_key
        return url

    def _backoff(self, attempt: int, retry_after: Optional[str]) -> float:
        if retry_after:
            try:
                return min(self.backoff_cap_s, max(0.0, float(retry_after)))
            except ValueError:
                pass
        return min(self.backoff_cap_s, self.backoff_base_s * (2 ** attempt)) * (0.75 + 0.5 * random.random())

    def call(self, method: str, params: Any = None, *, row: str, path: Optional[str] = None,
             max_bytes: int = 50 * 1024 * 1024, timeout_s: Optional[float] = None) -> Any:
        return self.call_meta(method, params, row=row, path=path, max_bytes=max_bytes, timeout_s=timeout_s)[0]

    def call_meta(self, method: str, params: Any = None, *, row: str, path: Optional[str] = None,
                  max_bytes: int = 50 * 1024 * 1024, timeout_s: Optional[float] = None) -> "tuple[Any, CallMeta]":
        _check_call(self.provider, method, params, path)          # refuse first; nothing sent
        use_path = path or self.provider.paths[0]
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method,
                           "params": params if params is not None else []}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self.budget.charge(self.provider.name, method, row)    # may raise BudgetExceeded
            self.limiter.acquire()
            if method in DAS_METHODS and self.das_limiter is not None:
                self.das_limiter.acquire()
            t0 = self.clock()
            try:
                status, rheaders, data = self.transport("POST", self._url(use_path), body, headers,
                                                        timeout_s or self.timeout_s, max_bytes)
            except NetError as e:
                if e.kind == "blocked":
                    raise HostBlocked(self.provider.host, e.message) from None
                if e.kind in ("tls", "too_large"):
                    raise RpcError(self.provider.name, method, e.message) from None
                last_err = RpcError(self.provider.name, method, e.message)
                self.sleep(self._backoff(attempt, None))
                continue
            latency = self.clock() - t0
            if status == 429 or status >= 500:
                last_err = RpcError(self.provider.name, method, f"HTTP {status}", http_status=status)
                self.sleep(self._backoff(attempt, rheaders.get("retry-after")))
                continue
            if status != 200:
                snippet = data[:300].decode("utf-8", "replace")
                raise RpcError(self.provider.name, method, f"unexpected HTTP status: {snippet}",
                               http_status=status)
            try:
                obj = json.loads(data)
            except ValueError:
                last_err = RpcError(self.provider.name, method, "response was not JSON")
                self.sleep(self._backoff(attempt, None))
                continue
            if isinstance(obj, dict) and obj.get("error"):
                err = obj["error"]
                code = err.get("code") if isinstance(err, dict) else None
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                if code in RETRYABLE_RPC_CODES or "rate limit" in str(msg).lower():
                    last_err = RpcError(self.provider.name, method, str(msg), code=code)
                    self.sleep(self._backoff(attempt, rheaders.get("retry-after")))
                    continue
                raise RpcError(self.provider.name, method, str(msg), code=code)
            result = obj.get("result") if isinstance(obj, dict) else None
            ctx_slot = None
            if isinstance(result, dict) and isinstance(result.get("context"), dict):
                ctx_slot = result["context"].get("slot")
            meta = CallMeta(latency, attempt + 1, len(data), status, hashlib.sha256(data).hexdigest(), ctx_slot)
            if self.recorder is not None:
                self.recorder({
                    "row": row, "provider": self.provider.name, "host": self.provider.host,
                    "path": use_path, "method": method, "params": REDACTOR.redact_obj(params),
                    "context_slot": ctx_slot, "latency_ms": round(latency * 1000, 1),
                    "attempts": attempt + 1, "bytes": len(data), "sha256": meta.sha256,
                    "raw": REDACTOR.redact(data.decode("utf-8", "replace")),
                })
            return result, meta
        assert last_err is not None
        raise last_err


__all__ = ["RpcClient", "RpcRefused", "RpcError", "HostBlocked", "MissingKey", "BudgetExceeded",
           "PROVIDERS", "SOLANA_READ_METHODS", "ALLOWED_HOSTS", "load_helius_key", "KEY_ENV_VAR"]
