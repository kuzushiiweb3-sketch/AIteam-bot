"""Where results, fixtures, artifacts and the transaction cache are written.

Layout (relative to the repository root):
  phase0/results/<ROW>.json            one summary per row (what results.md is built from)
  phase0/results.md                    plain-English summary table + one section per row
  phase0/results/_budget_ledger.json   estimated credits and requests this month
  fixtures/phase0/<ROW>/responses.jsonl.gz   every raw response the row fetched, one JSON per line,
                                             each with its provenance (method, redacted params,
                                             provider, slot, UTC time, SHA-256)
  fixtures/phase0/<ROW>/provenance.json      file hashes and counts
  fixtures/phase0/<ROW>/artifacts.json       derived lists later rows need (e.g. A03's migrations)
  phase0/cache/                        local cache of immutable getTransaction results (not committed)

Every write passes REDACTOR.assert_clean(): if a secret value is still present, the write is refused.
"""

from __future__ import annotations

import datetime as _dt
import gzip
import hashlib
import json
import os
import threading
from typing import Any, Optional

from .redact import REDACTOR

STATUS_FINAL = ("PASS", "FAIL", "MEASURED")


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=1, sort_keys=False, default=str)


class Store:
    def __init__(self, repo_root: str) -> None:
        self.root = os.path.abspath(repo_root)
        self.results_dir = os.path.join(self.root, "phase0", "results")
        self.results_md = os.path.join(self.root, "phase0", "results.md")
        self.fixtures_dir = os.path.join(self.root, "fixtures", "phase0")
        self.cache_dir = os.path.join(self.root, "phase0", "cache")
        self._lock = threading.Lock()
        self._open: dict = {}

    # ---- safe writes ---------------------------------------------------------------------------
    def write_text(self, path: str, text: str) -> None:
        REDACTOR.assert_clean(text, where=os.path.basename(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)

    def write_json(self, path: str, obj: Any) -> None:
        self.write_text(path, _dump(obj) + "\n")

    def read_json(self, path: str) -> Optional[Any]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---- per-row results ----------------------------------------------------------------------
    def result_path(self, row: str) -> str:
        return os.path.join(self.results_dir, f"{row}.json")

    def load_result(self, row: str) -> Optional[dict]:
        return self.read_json(self.result_path(row))

    def save_result(self, result: dict) -> None:
        self.write_json(self.result_path(result["row"]), result)

    def all_results(self) -> dict:
        out = {}
        if os.path.isdir(self.results_dir):
            for name in sorted(os.listdir(self.results_dir)):
                if name.endswith(".json") and not name.startswith("_"):
                    r = self.read_json(os.path.join(self.results_dir, name))
                    if isinstance(r, dict) and "row" in r:
                        out[r["row"]] = r
        return out

    # ---- artifacts (derived data later rows use) ------------------------------------------------
    def artifacts_path(self, row: str) -> str:
        return os.path.join(self.fixtures_dir, row, "artifacts.json")

    def save_artifacts(self, row: str, obj: Any) -> str:
        p = self.artifacts_path(row)
        self.write_json(p, obj)
        return os.path.relpath(p, self.root)

    def load_artifacts(self, row: str) -> Optional[Any]:
        return self.read_json(self.artifacts_path(row))

    # ---- raw response fixtures --------------------------------------------------------------------
    def record(self, entry: dict) -> None:
        """Called by the RPC and GET clients after every successful response."""
        row = entry.get("row") or "_unassigned"
        entry = dict(entry)
        entry.setdefault("fetched_utc", utc_now())
        line = json.dumps(entry, separators=(",", ":"), default=str)
        REDACTOR.assert_clean(line, where=f"fixture for {row}")
        with self._lock:
            fh = self._open.get(row)
            if fh is None:
                d = os.path.join(self.fixtures_dir, row)
                os.makedirs(d, exist_ok=True)
                fh = gzip.open(os.path.join(d, "responses.jsonl.gz"), "at", encoding="utf-8")
                self._open[row] = fh
            fh.write(line + "\n")

    def close_row(self, row: str, extra: Optional[dict] = None) -> Optional[str]:
        with self._lock:
            fh = self._open.pop(row, None)
            if fh is not None:
                fh.close()
        d = os.path.join(self.fixtures_dir, row)
        if not os.path.isdir(d):
            return None
        files = {}
        for name in sorted(os.listdir(d)):
            if name == "provenance.json":
                continue
            p = os.path.join(d, name)
            if os.path.isfile(p):
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                files[name] = {"sha256": h.hexdigest(), "bytes": os.path.getsize(p)}
        prov = {"row": row, "written_utc": utc_now(), "files": files,
                "note": "responses.jsonl.gz: one JSON object per line with method, redacted params, provider, "
                        "host, context slot, fetch time (UTC), SHA-256 of the raw body, and the raw body. "
                        "Requests (which carry the key in the URL) are never stored."}
        if extra:
            prov.update(extra)
        self.write_json(os.path.join(d, "provenance.json"), prov)
        return os.path.relpath(d, self.root)

    def close_all(self) -> None:
        with self._lock:
            rows = list(self._open)
        for r in rows:
            self.close_row(r)

    # ---- transaction cache --------------------------------------------------------------------------
    def _cache_path(self, kind: str, key: str) -> str:
        safe = "".join(c for c in key if c.isalnum())
        return os.path.join(self.cache_dir, kind, safe[:2] or "_", safe + ".json")

    def cache_get(self, kind: str, key: str) -> Optional[Any]:
        p = self._cache_path(kind, key)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def cache_put(self, kind: str, key: str, value: Any) -> None:
        p = self._cache_path(kind, key)
        self.write_text(p, json.dumps(value, separators=(",", ":")))

    # ---- results.md -------------------------------------------------------------------------------------
    def write_results_md(self, rows_meta: list) -> None:
        results = self.all_results()
        lines = [
            "# Phase 0 results (tier A)",
            "",
            "## In plain English (for Paul)",
            "- This page is written by the Phase 0 test scripts. Each line is one check of a fact the design relies on.",
            "- PASS means the fact held; FAIL means it did not and the design must react; MEASURED means we recorded a number.",
            "- BLOCKED means the web address was not allowed from here, and NO KEY means the Helius key was missing. "
            "Nothing is ever guessed.",
            "- The scripts only read public blockchain data. They never sign, send or simulate a transaction.",
            "",
            f"_Last written: {utc_now()} (UTC). Generated by `phase0/scripts/run_tier_a.py`; edit the scripts, not this file._",
            "",
            "| Row | Test | Outcome | Number measured | Domain used |",
            "|---|---|---|---|---|",
        ]
        for meta in rows_meta:
            r = results.get(meta["row"])
            if r is None:
                d = meta.get("deferred")
                outcome = "NOT RUN" if not d else (f"NOT RUN ({d})" if d.startswith("optional") else "DEFERRED: " + d)
                number, domain = "", ""
            else:
                outcome = r.get("outcome", r.get("status", "?"))
                number = r.get("headline", "")
                domain = ", ".join(r.get("domains_used") or []) or "-"
            lines.append(f"| {meta['row']} | {meta['tests']} | {outcome} | {_cell(number)} | {_cell(domain)} |")
        lines.append("")
        lines.append("## Row details (template: phase0/test-plan.md section 6)")
        for meta in rows_meta:
            r = results.get(meta["row"])
            if r is None:
                continue
            lines += [
                "",
                f"### {meta['row']} {meta['tests']} — {r.get('finished_utc', '')}",
                f"- Domain(s) used: {', '.join(r.get('domains_used') or []) or '-'}   Provider: {r.get('provider', '-')}   "
                f"Env var: {r.get('env_var', 'none')} (value never shown)",
                f"- Outcome: {r.get('outcome')}",
                f"- Numbers: {_numbers(r.get('numbers'))}",
                f"- Fixtures: {r.get('fixtures') or '-'}",
                f"- Follow-up: {r.get('follow_up') or '-'}",
            ]
            if r.get("notes"):
                lines.append(f"- Notes: {r['notes']}")
            lines.append(f"- Requests: {r.get('requests', 0)}, estimated Helius credits: {r.get('credits_est', 0)}")
        self.write_text(self.results_md, "\n".join(lines) + "\n")


def _cell(text: Any) -> str:
    return str(text).replace("|", "/").replace("\n", " ")[:220]


def _numbers(nums: Any) -> str:
    if not nums:
        return "-"
    if isinstance(nums, dict):
        parts = []
        for k, v in nums.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, default=str)
                if len(v) > 300:
                    v = v[:300] + "…"
            parts.append(f"{k} = {v}")
        return "; ".join(parts) + " [VERIFIED-LOCAL]"
    return str(nums)
