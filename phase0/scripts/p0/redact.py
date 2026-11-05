"""Secret redaction. Every log line, error message and file write passes through here.

The Helius key travels in the URL query (`?api-key=...`). This module:
  * remembers registered secret values (the key and its URL-encoded form) and replaces them;
  * also replaces any `api-key=<value>` / `api_key=<value>` it sees, even for unregistered values;
  * offers `assert_clean()` so writers can refuse to write anything that still holds a secret.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

MASK = "[REDACTED]"
_KEY_PARAM_RE = re.compile(r"(?i)(api[-_]?key=)([^&\s\"'<>\\]+)")


class SecretLeak(RuntimeError):
    """Raised when text that is about to be written or printed still contains a secret."""


class Redactor:
    def __init__(self) -> None:
        self._secrets: list[str] = []

    def register(self, secret: str | None) -> None:
        if not secret or len(secret) < 4:
            return
        for variant in {secret, urllib.parse.quote(secret, safe=""), urllib.parse.quote_plus(secret)}:
            if variant not in self._secrets:
                self._secrets.append(variant)
        # Longest first, so a longer variant is never half-replaced by a shorter one.
        self._secrets.sort(key=len, reverse=True)

    def clear(self) -> None:
        self._secrets.clear()

    def redact(self, text: Any) -> str:
        if not isinstance(text, str):
            text = str(text)
        for s in self._secrets:
            if s in text:
                text = text.replace(s, MASK)
        return _KEY_PARAM_RE.sub(lambda m: m.group(1) + MASK if m.group(2) != MASK else m.group(0), text)

    def redact_obj(self, obj: Any) -> Any:
        """Deep copy of a JSON-like object with every string redacted."""
        if isinstance(obj, str):
            return self.redact(obj)
        if isinstance(obj, dict):
            return {self.redact(k): self.redact_obj(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.redact_obj(v) for v in obj]
        return obj

    def contains_secret(self, text: str) -> bool:
        if any(s in text for s in self._secrets):
            return True
        for m in _KEY_PARAM_RE.finditer(text):
            if m.group(2) != MASK:
                return True
        return False

    def assert_clean(self, text: str, where: str = "output") -> None:
        if self.contains_secret(text):
            # Never include the text itself in the message.
            raise SecretLeak(f"refusing to write {where}: it still contains a secret value")


# One process-wide redactor. p0.rpc registers the key here when it is loaded.
REDACTOR = Redactor()


def redact(text: Any) -> str:
    return REDACTOR.redact(text)


def log(*parts: Any) -> None:
    """The only print() used by the scripts. Redacts before printing."""
    print(REDACTOR.redact(" ".join(str(p) for p in parts)), flush=True)
