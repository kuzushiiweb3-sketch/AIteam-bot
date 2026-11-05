"""Clock helpers for timing rows (docs/tech-stack.md v1.1 s.5k, TS-12).

* Intervals use time.monotonic_ns() (never wall-clock differences).
* clock_sync_status() records whether the host clock was NTP-synchronised, so wall-clock times in
  results can be judged. It only reads local state; it never changes the clock.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time


def now_ns() -> int:
    return time.monotonic_ns()


def seconds_since(t0_ns: int) -> float:
    return (time.monotonic_ns() - t0_ns) / 1e9


def clock_sync_status() -> dict:
    out = {"checked_unix": int(time.time()), "synchronized": None, "method": None, "detail": ""}
    tdc = shutil.which("timedatectl")
    if tdc:
        try:
            r = subprocess.run([tdc, "show", "--property=NTPSynchronized", "--value"], capture_output=True,
                               text=True, timeout=5, check=False)
            val = (r.stdout or "").strip().lower()
            if val in ("yes", "no"):
                out.update(synchronized=(val == "yes"), method="timedatectl NTPSynchronized")
                return out
            out["detail"] = (r.stderr or "").strip()[:200]
        except (OSError, subprocess.SubprocessError) as e:
            out["detail"] = str(e)[:200]
    if os.path.exists("/run/systemd/timesync/synchronized"):
        out.update(synchronized=True, method="/run/systemd/timesync/synchronized exists")
        return out
    out["method"] = "unknown (no timedatectl answer, no timesyncd flag file)"
    return out
