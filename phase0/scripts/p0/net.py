"""The one place that opens network connections (urllib, standard library only).

* TLS is always verified. If SSL_CERT_FILE / REQUESTS_CA_BUNDLE points at a CA bundle (as in
  this cloud session's proxy setup), that bundle is used; verification is never switched off.
* The proxy from HTTPS_PROXY is honoured by urllib automatically.
* Errors are turned into NetError with a redacted message and NO chained exception, so a
  traceback can never print a URL that holds the key.
* A refused proxy tunnel ("Tunnel connection failed: 403") or an unresolvable host is
  classified as kind="blocked": the domain is not allowed in this environment.
"""

from __future__ import annotations

import gzip
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Tuple

from .redact import redact

DEFAULT_MAX_BYTES = 50 * 1024 * 1024
USER_AGENT = "aiteam-bot-phase0/1.0 (read-only research; python-urllib)"

Response = Tuple[int, dict, bytes]
Transport = Callable[[str, str, "bytes | None", dict, float, int], Response]


class NetError(Exception):
    """kind: blocked | dns | timeout | connection | tls | too_large | other"""

    def __init__(self, kind: str, host: str, message: str) -> None:
        self.kind = kind
        self.host = host
        self.message = redact(message)
        super().__init__(f"{kind} error talking to {host}: {self.message}")


def host_of(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def _ssl_context() -> ssl.SSLContext:
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        path = os.environ.get(var)
        if path and os.path.isfile(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


_OPENER = None


def _opener() -> urllib.request.OpenerDirector:
    global _OPENER
    if _OPENER is None:
        _OPENER = urllib.request.build_opener(
            urllib.request.ProxyHandler(),            # reads HTTPS_PROXY / NO_PROXY
            urllib.request.HTTPSHandler(context=_ssl_context()),
        )
    return _OPENER


def classify(reason: object, host: str) -> NetError:
    text = str(reason)
    low = text.lower()
    if "tunnel connection failed" in low or "403 forbidden" in low or "407" in low:
        return NetError("blocked", host, text)
    if isinstance(reason, socket.gaierror) or "name or service not known" in low \
            or "nodename nor servname" in low or "getaddrinfo" in low or "temporary failure in name resolution" in low:
        return NetError("blocked", host, "host name did not resolve (" + text + ")")
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in low:
        return NetError("timeout", host, text)
    if isinstance(reason, ssl.SSLError) or "certificate" in low or "ssl" in low:
        return NetError("tls", host, text)
    if isinstance(reason, (ConnectionError, OSError)):
        return NetError("connection", host, text)
    return NetError("other", host, text)


def urllib_transport(method: str, url: str, body: "bytes | None", headers: dict,
                     timeout_s: float, max_bytes: int = DEFAULT_MAX_BYTES) -> Response:
    """Do one HTTP request. Returns (status, headers, body). Raises NetError (already redacted)."""
    host = host_of(url)
    if not url.startswith("https://"):
        raise NetError("other", host, "only https URLs are allowed")
    hdrs = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=body, method=method, headers=hdrs)
    err: NetError | None = None
    status, rheaders, data = 0, {}, b""
    try:
        with _opener().open(req, timeout=timeout_s) as resp:
            status = resp.status
            rheaders = {k.lower(): v for k, v in resp.headers.items()}
            data = resp.read(max_bytes + 1)
    except urllib.error.HTTPError as e:      # an HTTP status from the server: not a network failure
        status = e.code
        rheaders = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        try:
            data = e.read(64 * 1024)
        except Exception:                     # noqa: BLE001 - best effort body read
            data = b""
        if status in (403, 407) and "tunnel" in str(e.reason).lower():
            err = NetError("blocked", host, str(e.reason))
    except urllib.error.URLError as e:
        err = classify(e.reason, host)
    except (socket.timeout, TimeoutError) as e:
        err = NetError("timeout", host, str(e))
    except (ConnectionError, OSError) as e:
        err = classify(e, host)
    # Raised outside the except blocks, so no original exception (which may hold the URL) is chained.
    if err is not None:
        raise err
    if len(data) > max_bytes:
        raise NetError("too_large", host, f"response larger than {max_bytes} bytes")
    if rheaders.get("content-encoding", "").lower() == "gzip" and data:
        try:
            data = gzip.decompress(data)
        except OSError:
            raise NetError("other", host, "bad gzip body") from None
        if len(data) > max_bytes * 8:
            raise NetError("too_large", host, "decompressed response too large")
    return status, rheaders, data
