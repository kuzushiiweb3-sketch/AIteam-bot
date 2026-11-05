"""Phase 0 read-only test helpers (Python standard library only).

Nothing in this package signs, sends or simulates a transaction. Every network call goes
through p0.rpc.RpcClient (JSON-RPC, hard method allowlist) or p0.http_get.HttpGetClient
(plain GET, hard host allowlist). See phase0/scripts/README.md.
"""

__all__ = []
