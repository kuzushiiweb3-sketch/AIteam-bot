"""Read-only HTTP GET client for keyless rows (docs pages, Jito tip floor, Sender ping, prices).

* GET only. There is no POST/PUT method in this module.
* Hard host allowlist (List 1 hosts, plus two hosts the test plan names that are not on a list yet,
  marked below). Some hosts are further limited to specific paths.
* Rate limited per host, timeouts on every call, retries with back-off on 429 / 5xx.
* Requests are counted in the shared budget ledger (0 credits; these are not Helius calls).
"""

from __future__ import annotations

import hashlib
import random
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, Optional

from .budget import Budget
from .net import NetError, Transport, urllib_transport
from .ratelimit import RateLimiter
from .redact import REDACTOR, redact
from .rpc import HostBlocked

# host -> allowed path prefixes (None = any path on that host)
GET_HOSTS: dict = {
    "bundles.jito.wtf": ("/api/v1/bundles/tip_floor", "/api/"),
    "explorer.jito.wtf": None,
    "docs.jito.wtf": None,
    "www.helius.dev": None,
    "docs.helius.dev": None,
    "sender.helius-rpc.com": ("/ping",),          # latency only; never anything else on Sender
    "chainstack.com": None,
    "docs.chainstack.com": None,
    "api.coingecko.com": ("/api/v3/simple/price",),
    "raw.githubusercontent.com": None,
    "registry.npmjs.org": None,
    "pumpportal.fun": None,
    "solana.com": None,
    "docs.anza.xyz": None,
    "www.bankofcanada.ca": ("/valet/",),          # NOT on any list yet (test-plan s.5 note); A28 only
}
PER_HOST_RATE = {"sender.helius-rpc.com": 2.0}
DEFAULT_RATE = 1.0


class GetRefused(RuntimeError):
    pass


@dataclass
class GetResult:
    url: str
    status: int
    headers: dict
    body: bytes
    latency_s: float
    sha256: str

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def check_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise GetRefused("only https URLs are allowed")
    host = parts.hostname or ""
    if host not in GET_HOSTS:
        raise GetRefused(f"host {host!r} is not on the GET allowlist")
    prefixes = GET_HOSTS[host]
    if prefixes is not None and not any((parts.path or "/").startswith(p) for p in prefixes):
        raise GetRefused(f"path {parts.path!r} is not allowed on {host}")
    if parts.username or parts.password:
        raise GetRefused("credentials in URLs are not allowed")
    return host


@dataclass
class HttpGetClient:
    budget: Budget
    transport: Transport = urllib_transport
    timeout_s: float = 20.0
    max_retries: int = 3
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = lambda: time.monotonic_ns() / 1e9     # intervals from monotonic_ns (TS-12)
    recorder: Optional[Callable[[dict], None]] = None
    _limiters: dict = field(default_factory=dict, repr=False)

    def _limiter(self, host: str) -> RateLimiter:
        if host not in self._limiters:
            self._limiters[host] = RateLimiter(PER_HOST_RATE.get(host, DEFAULT_RATE), clock=self.clock, sleep=self.sleep)
        return self._limiters[host]

    def get(self, url: str, *, row: str, max_bytes: int = 10 * 1024 * 1024, record: bool = True,
            accept: str = "*/*") -> GetResult:
        host = check_url(url)
        last: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self.budget.charge("get:" + host, "GET", row)
            self._limiter(host).acquire()
            t0 = self.clock()
            try:
                status, headers, body = self.transport("GET", url, None, {"Accept": accept}, self.timeout_s, max_bytes)
            except NetError as e:
                if e.kind == "blocked":
                    raise HostBlocked(host, e.message) from None
                last = RuntimeError(f"GET {host} failed: {e.message}")
                self.sleep(min(20.0, 0.5 * 2 ** attempt) * (0.75 + 0.5 * random.random()))
                continue
            latency = self.clock() - t0
            if status == 429 or status >= 500:
                last = RuntimeError(f"GET {host} returned HTTP {status}")
                self.sleep(min(30.0, 1.0 * 2 ** attempt))
                continue
            res = GetResult(redact(url), status, headers, body, latency, hashlib.sha256(body).hexdigest())
            if self.recorder is not None and record:
                self.recorder({"row": row, "provider": "get", "host": host, "method": "GET",
                               "url": redact(url), "status": status, "latency_ms": round(latency * 1000, 1),
                               "bytes": len(body), "sha256": res.sha256,
                               "raw": REDACTOR.redact(body.decode("utf-8", "replace"))})
            return res
        assert last is not None
        raise last
