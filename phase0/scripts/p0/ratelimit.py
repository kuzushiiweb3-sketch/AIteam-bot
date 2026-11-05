"""A small token-bucket rate limiter (thread-safe, injectable clock for tests)."""

from __future__ import annotations

import threading
import time
from typing import Callable


class RateLimiter:
    def __init__(self, rate_per_s: float, burst: float = 1.0,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if rate_per_s <= 0:
            raise ValueError("rate must be positive")
        self.rate = float(rate_per_s)
        self.capacity = max(1.0, float(burst))
        self.tokens = self.capacity
        self.clock = clock
        self.sleep = sleep
        self.last = clock()
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """Block until one request may go. Returns the seconds waited."""
        waited = 0.0
        while True:
            with self._lock:
                now = self.clock()
                self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
                self.last = now
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return waited
                need = (1.0 - self.tokens) / self.rate
            self.sleep(need)
            waited += need
