"""Keyless rows: A18, A19, A20, A24, A26, A27, A28. They need no Helius key, only the List 1 hosts.

Documentation rows (A24, A26, A27 and the doc parts of A18/A19) SAVE the pages and pull out candidate lines,
but a session must still read them; their outcome is "REVIEW", never a guessed PASS.
Every URL marked [UNVERIFIED path] may 404; a 404 is recorded as such.
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time

from p0.redact import REDACTOR
from p0.rpc import HostBlocked, RpcError
from p0.store import utc_now


def _pct(vals, q):
    if not vals:
        return None
    v = sorted(vals)
    return v[min(len(v) - 1, int(round(q * (len(v) - 1))))]


def save_pages(ctx, urls: list, keywords: list) -> dict:
    """Fetch documentation pages, save them under fixtures/phase0/<row>/pages/, extract matching lines."""
    d = os.path.join(ctx.store.fixtures_dir, ctx.row, "pages")
    os.makedirs(d, exist_ok=True)
    out = {}
    blocked = []
    for url in urls:
        try:
            r = ctx.http_get(url, max_bytes=8 * 1024 * 1024)
        except HostBlocked as e:
            out[url] = {"status": "BLOCKED: " + e.host}
            blocked.append(e.host)
            continue
        except Exception as e:  # noqa: BLE001
            out[url] = {"status": "ERROR: " + str(e)}
            continue
        text = r.text()
        slug = re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[1])[:120]
        ctx.store.write_text(os.path.join(d, slug + ".txt"), text)
        lines = [ln.strip() for ln in text.splitlines() if any(k.lower() in ln.lower() for k in keywords)]
        out[url] = {"status": r.status, "bytes": len(r.body), "sha256": r.sha256, "file": f"pages/{slug}.txt",
                    "matching_lines": lines[:40]}
    if blocked and len(set(blocked)) == len({u.split('/')[2] for u in urls}):
        raise HostBlocked(", ".join(sorted(set(blocked))), "every documentation host was refused")
    return out


# ---- A18 -------------------------------------------------------------------------------------------
TIP_FLOOR = "https://bundles.jito.wtf/api/v1/bundles/tip_floor"


def a18(ctx) -> dict:
    d = os.path.join(ctx.store.fixtures_dir, "A18")
    os.makedirs(d, exist_ok=True)
    log_path = os.path.join(d, "tip_floor_polls.jsonl")
    end = time.time() + ctx.opts.a18_minutes * 60
    n = 0
    while True:
        try:
            r = ctx.http_get(TIP_FLOOR, record=False)
            rec = {"utc": utc_now(), "unix": int(time.time()), "status": r.status, "body": r.text()[:4000]}
        except HostBlocked:
            raise
        except Exception as e:  # noqa: BLE001
            rec = {"utc": utc_now(), "unix": int(time.time()), "status": "error", "error": str(e)}
        with open(log_path, "a", encoding="utf-8") as f:
            line = json.dumps(rec)
            REDACTOR.assert_clean(line, where="A18 log")
            f.write(line + "\n")
        n += 1
        if time.time() + 60 > end:
            break
        time.sleep(60)
    polls = []
    with open(log_path, "r", encoding="utf-8") as f:
        for ln in f:
            try:
                polls.append(json.loads(ln))
            except ValueError:
                pass
    ok_polls = [p for p in polls if p.get("status") == 200]
    ts = sorted(p["unix"] for p in ok_polls)
    span_min = (ts[-1] - ts[0]) / 60 if len(ts) > 1 else 0
    gaps = sum(max(0, round((b - a) / 60) - 1) for a, b in zip(ts, ts[1:]))
    expected = span_min + 1
    gap_share = gaps / expected if expected else None
    latest = None
    if ok_polls:
        try:
            latest = json.loads(ok_polls[-1]["body"])
        except ValueError:
            latest = ok_polls[-1]["body"][:300]
    docs = save_pages(ctx, ["https://docs.jito.wtf/", "https://docs.jito.wtf/lowlatencytxnsend/"],
                      ["tip", "minimum", "lamports", "fail", "rate limit"])
    seven_days = span_min >= 7 * 24 * 60
    outcome = ("PASS" if gap_share is not None and gap_share < 0.01 else "FAIL") if seven_days else \
        f"INCOMPLETE: {round(span_min / 60, 1)} h of 168 h logged (re-run A18 with --a18-minutes, or in the background)"
    return {"outcome": outcome + "; docs saved for REVIEW (minimum tip, no-fee-on-failure)",
            "headline": f"{len(ok_polls)} polls over {round(span_min / 60, 2)} h, gap share {round(gap_share, 4) if gap_share is not None else None}",
            "numbers": {"polls_this_run": n, "polls_total_ok": len(ok_polls), "span_hours": round(span_min / 60, 2),
                        "gap_minutes": gaps, "gap_share": gap_share, "latest_tip_floor": latest, "docs": docs},
            "notes": "The poll log is cumulative across runs: fixtures/phase0/A18/tip_floor_polls.jsonl."}


# ---- A19 -------------------------------------------------------------------------------------------
def a19(ctx) -> dict:
    tips, path_used, errors = None, None, {}
    for path in ctx.jito.provider.paths:
        try:
            res = ctx.call("getTipAccounts", [], client=ctx.jito, path=path)
            if isinstance(res, list) and res:
                tips, path_used = res, path
                break
        except HostBlocked:
            raise
        except RpcError as e:
            errors[path] = str(e)
    pings = []
    try:
        for _ in range(ctx.n(100, 5)):
            r = ctx.http_get("https://sender.helius-rpc.com/ping", record=False)
            if r.status == 200:
                pings.append(r.latency_s)
    except HostBlocked as e:
        errors["sender.helius-rpc.com"] = str(e)
    docs = save_pages(ctx, ["https://docs.jito.wtf/lowlatencytxnsend/",
                            "https://www.helius.dev/docs/sending-transactions/sender.md",      # [UNVERIFIED path]
                            "https://docs.helius.dev/sending-transactions/sender"],            # [UNVERIFIED path]
                      ["tip", "minimum", "mev", "region", "swqos", "lamports"])
    ctx.store.save_artifacts(ctx.row, {"tip_accounts": tips or [], "path": path_used, "fetched_utc": utc_now(),
                                       "source": f"https://mainnet.block-engine.jito.wtf{path_used}" if path_used else None})
    out = "MEASURED" if tips else "FAIL"
    return {"outcome": out + "; Sender docs saved for REVIEW",
            "headline": f"{len(tips or [])} Jito tip accounts via {path_used}; Sender ping p50 "
                        f"{round(statistics.median(pings) * 1000, 1) if pings else None} ms",
            "numbers": {"tip_accounts": tips, "jito_path": path_used, "errors": errors,
                        "sender_ping_ms_p50": round(statistics.median(pings) * 1000, 1) if pings else None,
                        "sender_ping_ms_p95": round(_pct(pings, 0.95) * 1000, 1) if pings else None,
                        "pings": len(pings), "docs": docs},
            "follow_up": "Pin the tip-account list in config (with this URL and date)."}


# ---- A20 -------------------------------------------------------------------------------------------
def a20(ctx) -> dict:
    tpl = ctx.opts.a20_url_template
    if not tpl:
        return {"outcome": "SKIPPED: Jito's bundle-by-transaction lookup endpoint is UNVERIFIED. Read the pages A19 saved "
                           "(docs.jito.wtf), then re-run with --a20-url-template 'https://bundles.jito.wtf/...{signature}'",
                "headline": "not run (no verified endpoint)"}
    a04 = ctx.artifacts("A04")
    sigs = [c["sig"] for c in a04.get("creates", [])][: ctx.n(50, 3)]
    hits = 0
    statuses = {}
    for s in sigs:
        r = ctx.http_get(tpl.replace("{signature}", s))
        statuses[r.status] = statuses.get(r.status, 0) + 1
        body = r.text().strip()
        if r.status == 200 and body not in ("", "[]", "null", "{}"):
            hits += 1
    return {"outcome": "MEASURED", "headline": f"{hits}/{len(sigs)} creates found in a bundle",
            "numbers": {"creates": len(sigs), "bundled": hits, "http_statuses": statuses}}


# ---- A24 / A26 / A27 -------------------------------------------------------------------------------
HELIUS_CONSUMERS = ["getSignaturesForAddress", "getTransaction", "getBlock", "getTransactionsForAddress",
                    "getMultipleAccounts", "getProgramAccounts", "DAS", "funded-by", "websocket", "accountSubscribe",
                    "programSubscribe", "Enhanced", "autoscal", "credit", "rate limit", "requests per second"]


def a24(ctx) -> dict:
    docs = save_pages(ctx, ["https://www.helius.dev/docs/billing/credits.md",
                            "https://www.helius.dev/docs/billing/plans.md",
                            "https://www.helius.dev/docs/billing/rate-limits.md",             # [UNVERIFIED path]
                            "https://www.helius.dev/docs/billing/autoscaling.md",             # [UNVERIFIED path]
                            "https://www.helius.dev/pricing"], HELIUS_CONSUMERS)
    return {"outcome": "REVIEW: pages saved; a session must read them and price every rulings s.6d line",
            "headline": f"{sum(1 for v in docs.values() if v.get('status') == 200)}/{len(docs)} pages fetched",
            "numbers": {"pages": docs},
            "follow_up": "Fill the credits table in docs/costs.md and update p0/budget.py HELIUS_CREDITS_PER_CALL."}


def a26(ctx) -> dict:
    docs = save_pages(ctx, ["https://chainstack.com/pricing/", "https://chainstack.com/products/yellowstone-grpc/",  # [UNVERIFIED path]
                            "https://docs.chainstack.com/changelog", "https://www.helius.dev/pricing",
                            "https://www.helius.dev/docs/billing/plans.md"],
                      ["$", "stream", "grpc", "yellowstone", "add-on", "credits", "per month"])
    return {"outcome": "REVIEW: pages saved; check costs.md U1-U4 (is the $49 add-on 1 stream or 2?)",
            "headline": f"{sum(1 for v in docs.values() if v.get('status') == 200)}/{len(docs)} pages fetched",
            "numbers": {"pages": docs}}


def a27(ctx) -> dict:
    docs = save_pages(ctx, ["https://docs.chainstack.com/docs/request-units",                         # [UNVERIFIED path]
                            "https://docs.chainstack.com/docs/limits",                                # [UNVERIFIED path]
                            "https://docs.chainstack.com/docs/yellowstone-grpc-geyser-plugin"],       # [UNVERIFIED path]
                      ["request unit", "rps", "requests per second", "filter", "token_accounts", "cuckoo",
                       "account_include", "getBlock", "limit"])
    return {"outcome": "REVIEW: pages saved; set the C02 plan from them",
            "headline": f"{sum(1 for v in docs.values() if v.get('status') == 200)}/{len(docs)} pages fetched",
            "numbers": {"pages": docs}}


# ---- A28 -------------------------------------------------------------------------------------------
def a28(ctx) -> dict:
    nums = {}
    r = ctx.http_get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd,cad")
    try:
        nums["coingecko"] = json.loads(r.text())
    except ValueError:
        nums["coingecko"] = {"status": r.status}
    try:
        b = ctx.http_get("https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?recent=1")   # [UNVERIFIED path]
        try:
            obs = json.loads(b.text()).get("observations") or []
            nums["bank_of_canada_usdcad"] = obs[-1] if obs else {"status": b.status}
        except ValueError:
            nums["bank_of_canada_usdcad"] = {"status": b.status}
    except HostBlocked as e:
        nums["bank_of_canada_usdcad"] = "BLOCKED: " + e.host + " (not on any list yet; test-plan s.5)"
    sol = (nums.get("coingecko") or {}).get("solana") or {}
    return {"outcome": "MEASURED", "headline": f"SOL = ${sol.get('usd')} USD / ${sol.get('cad')} CAD",
            "numbers": nums, "follow_up": "Record monthly in docs/costs.md."}
