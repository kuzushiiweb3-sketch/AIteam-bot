"""Offline unit tests. Importing this package switches networking OFF for the whole test run.

Any attempt to open a socket raises, so a test that forgets to inject a fake transport fails loudly
instead of reaching the internet (docs/tech-stack.md s.8: tests pass with networking switched off).
"""

import os
import socket
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


class NetworkDisabled(RuntimeError):
    pass


def _refuse(*_a, **_k):
    raise NetworkDisabled("network access is disabled in the offline unit tests")


socket.socket.connect = _refuse            # type: ignore[assignment]
socket.socket.connect_ex = _refuse         # type: ignore[assignment]
socket.create_connection = _refuse         # type: ignore[assignment]
socket.getaddrinfo = _refuse               # type: ignore[assignment]
