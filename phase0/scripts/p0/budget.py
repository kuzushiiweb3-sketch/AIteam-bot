"""Request and credit budget with a hard stop well below the Helius free plan.

Numbers come from phase0/test-plan.md:
  * free plan = 1,000,000 credits a month, 10 requests/s, DAS 2 requests/s   [VERIFIED-SEARCH, test-plan section 1 rule 4]
  * all of tier A is about 90,000 calls = 100-150k credits (10-15% of the month) [DERIVED, test-plan section 3]
  * per-row call estimates (A16 ~20k, A29 ~15k, A04 ~10k, A13 ~11k, A30 ~8k, A31 ~6k, others < 3k) [DERIVED, section 3]

Credit prices per method are ESTIMATES until row A24 reads the billing page. Search results
(2026-11-05) say standard and archival calls cost 1 credit, DAS 10, getTransactionsForAddress
"starts at 10" and is metered by results [VERIFIED-SEARCH helius.dev/docs/billing/credits.md].
getProgramAccounts' price was not visible, so it is charged at a conservative 10 here, and
getBlock at a conservative 10. Over-estimating makes the hard stop trigger early, never late.

The ledger is saved to disk, per UTC month, so the cap holds across separate runs.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import threading
from typing import Callable

FREE_PLAN_MONTHLY_CREDITS = 1_000_000
DEFAULT_MONTHLY_CAP = 150_000          # the test plan's upper estimate for all of tier A (15% of the month)
ABSOLUTE_CEILING = 500_000             # no option can raise the cap above half the free month

HELIUS_CREDITS_PER_CALL = {            # estimates; see module docstring
    "getProgramAccounts": 10,
    "getBlock": 10,
    "getTokenAccounts": 10,            # DAS
    "getTransactionsForAddress": 100,  # metered by results; 100 is a deliberately high guess
}
DEFAULT_CREDITS_PER_CALL = 1

# Per-row request caps (all providers together): test-plan section 3 estimate x 1.25, rounded.
ROW_CALL_CAPS = {
    "A16": 25_000, "A29": 19_000, "A04": 12_500, "A13": 14_000, "A30": 10_000, "A31": 7_500,
    "A09": 5_000,  # "under 3k" in the plan; T6 tops up thin strata, so it gets a little more room
    "A12": 7_000,  # its own spec: getSlot x 2 commitments, 5 times a second for 10 minutes = 6,000 calls
    "A18": 11_500,  # keyless GET once a minute for 7 days = 10,080 requests (no credits)
}
DEFAULT_ROW_CALL_CAP = 3_750


class BudgetExceeded(RuntimeError):
    """Raised BEFORE a request is made that would cross a cap."""


def credits_for(provider: str, method: str) -> int:
    if provider != "helius":
        return 0
    return HELIUS_CREDITS_PER_CALL.get(method, DEFAULT_CREDITS_PER_CALL)


def _month(now: _dt.datetime) -> str:
    return now.strftime("%Y-%m")


class Budget:
    def __init__(self, ledger_path: str | None, monthly_cap: int = DEFAULT_MONTHLY_CAP,
                 now_fn: Callable[[], _dt.datetime] | None = None,
                 row_caps: dict | None = None, default_row_cap: int = DEFAULT_ROW_CALL_CAP) -> None:
        if monthly_cap > ABSOLUTE_CEILING:
            raise ValueError(f"monthly cap {monthly_cap} is above the absolute ceiling {ABSOLUTE_CEILING}")
        if monthly_cap <= 0:
            raise ValueError("monthly cap must be positive")
        self.cap = monthly_cap
        self.path = ledger_path
        self.now_fn = now_fn or (lambda: _dt.datetime.now(_dt.timezone.utc))
        self.row_caps = dict(ROW_CALL_CAPS if row_caps is None else row_caps)
        self.default_row_cap = default_row_cap
        self._lock = threading.Lock()
        self._unsaved = 0
        self.data = self._load()

    # ---- persistence -------------------------------------------------------------------
    def _empty(self) -> dict:
        return {"month": _month(self.now_fn()), "credits_est": 0, "requests": {}, "by_method": {},
                "by_row": {}, "note": "Estimated Helius credits. Compare with the Helius dashboard."}

    def _load(self) -> dict:
        if self.path and os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("month") == _month(self.now_fn()):
                return data
        return self._empty()

    def save(self) -> None:
        if not self.path:
            return
        with self._lock:
            tmp = self.path + ".tmp"
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1, sort_keys=True)
            os.replace(tmp, self.path)
            self._unsaved = 0

    # ---- the check -----------------------------------------------------------------------
    def row_cap(self, row: str) -> int:
        return self.row_caps.get(row, self.default_row_cap)

    def remaining_credits(self) -> int:
        return self.cap - self.data["credits_est"]

    def row_calls(self, row: str) -> int:
        return self.data["by_row"].get(row, 0)

    def charge(self, provider: str, method: str, row: str) -> int:
        """Reserve one request. Raises BudgetExceeded before anything is sent."""
        cost = credits_for(provider, method)
        with self._lock:
            if self.data.get("month") != _month(self.now_fn()):
                self.data = self._empty()
            if self.data["credits_est"] + cost > self.cap:
                raise BudgetExceeded(
                    f"monthly credit cap reached ({self.data['credits_est']} + {cost} > {self.cap}); "
                    "nothing was sent")
            used = self.data["by_row"].get(row, 0)
            if used + 1 > self.row_cap(row):
                raise BudgetExceeded(f"row {row} request cap reached ({self.row_cap(row)}); nothing was sent")
            self.data["credits_est"] += cost
            self.data["requests"][provider] = self.data["requests"].get(provider, 0) + 1
            key = f"{provider}:{method}"
            self.data["by_method"][key] = self.data["by_method"].get(key, 0) + 1
            self.data["by_row"][row] = used + 1
            self._unsaved += 1
            should_save = self._unsaved >= 50
        if should_save:
            self.save()
        return cost
