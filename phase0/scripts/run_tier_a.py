#!/usr/bin/env python3
"""Run every tier-A Phase 0 test (phase0/test-plan.md rows A01-A32) and write the results.

    python3 phase0/scripts/run_tier_a.py              # everything, in the plan's order (resumable)
    python3 phase0/scripts/run_tier_a.py --preflight  # check the key and every host; writes nothing
    python3 phase0/scripts/run_tier_a.py --only A01,A03 --quick

Read-only. It never signs, sends or simulates a transaction (see p0/rpc.py's allowlist).
The Helius key is read ONLY from the environment variable HELIUS_API_KEY and is never printed or saved.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from p0 import budget as budget_mod  # noqa: E402
from p0 import t6  # noqa: E402
from p0.budget import Budget, BudgetExceeded  # noqa: E402
from p0.clock import clock_sync_status  # noqa: E402
from p0.context import Ctx, NeedRow, Options, build_clients  # noqa: E402
from p0.http_get import GetRefused, HttpGetClient  # noqa: E402
from p0.pump import load_decoders  # noqa: E402
from p0.redact import REDACTOR, log, redact  # noqa: E402
from p0.rpc import KEY_ENV_VAR, HostBlocked, MissingKey, RpcError, RpcRefused, load_helius_key  # noqa: E402
from p0.store import Store, utc_now  # noqa: E402
from tier_a import BY_ID, ROWS  # noqa: E402

SCRIPT_VERSION = "phase0-tierA/1.0"
FINAL_PREFIXES = ("PASS", "FAIL", "MEASURED", "PARTIAL", "REVIEW", "DEFERRED")

PROBE_GET = {
    "bundles.jito.wtf": "https://bundles.jito.wtf/api/v1/bundles/tip_floor",
    "sender.helius-rpc.com": "https://sender.helius-rpc.com/ping",
    "api.coingecko.com": "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
}


def parse_args(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="comma-separated row ids, e.g. A01,A03")
    ap.add_argument("--quick", action="store_true", help="small samples and short durations (never a pass mark)")
    ap.add_argument("--rerun", action="store_true", help="re-run rows that already have a final result")
    ap.add_argument("--with-optional", action="store_true", help="also run optional rows (TS-T3)")
    ap.add_argument("--preflight", action="store_true", help="check the key and hosts, print, write nothing")
    ap.add_argument("--list", action="store_true", help="list rows and their current outcome")
    ap.add_argument("--public-fallback", action="store_true",
                    help="rows that allow it use api.mainnet-beta.solana.com when HELIUS_API_KEY is missing")
    ap.add_argument("--max-credits", type=int, default=budget_mod.DEFAULT_MONTHLY_CAP,
                    help=f"monthly estimated-credit cap (default {budget_mod.DEFAULT_MONTHLY_CAP}, "
                         f"hard ceiling {budget_mod.ABSOLUTE_CEILING})")
    ap.add_argument("--row-cap", action="append", default=[], help="override one row's request cap: ROW=N")
    ap.add_argument("--a18-minutes", type=float, default=10.0, help="minutes of tip-floor polling this run (7 days = 10080)")
    ap.add_argument("--a20-url-template", help="verified Jito bundle-lookup URL with {signature}")
    ap.add_argument("--t6-freeze", action="store_true", help="write phase0/scripts/t6_freeze.json (Step 0) and exit")
    ap.add_argument("--t6-stop-after-calibration", action="store_true")
    ap.add_argument("--force", action="store_true", help="with --t6-freeze: replace an existing freeze")
    return ap.parse_args(argv)


def selected_rows(args):
    if not args.only:
        return [r for r in ROWS if not r.optional or args.with_optional]
    ids = [x.strip().upper() for x in args.only.split(",") if x.strip()]
    unknown = [i for i in ids if i not in BY_ID]
    if unknown:
        raise SystemExit(f"unknown row(s): {', '.join(unknown)}")
    return [r for r in ROWS if r.row in ids]


def hosts_for(rows) -> list:
    out = []
    for r in rows:
        if r.deferred:
            continue
        for h in r.hosts:
            if h not in out:
                out.append(h)
    return out


def preflight(ctx: Ctx, rows, have_key: bool) -> dict:
    """One cheap read per host. Returns host -> 'ok' | 'BLOCKED' | 'error: ...' | 'skipped: ...'."""
    status = {}
    for h in hosts_for(rows):
        try:
            if h == "mainnet.helius-rpc.com":
                if not have_key:
                    status[h] = "skipped: no key"
                    continue
                ctx.helius.call("getHealth", [], row="_preflight")
            elif h == "api.mainnet-beta.solana.com":
                ctx.public.call("getHealth", [], row="_preflight")
            elif h == "mainnet.block-engine.jito.wtf":
                ctx.jito.call("getTipAccounts", [], row="_preflight")
            else:
                ctx.get.get(PROBE_GET.get(h, f"https://{h}/"), row="_preflight", record=False)
            status[h] = "ok"
        except HostBlocked:
            status[h] = "BLOCKED"
        except (RpcError, RpcRefused, GetRefused, BudgetExceeded) as e:
            status[h] = "reachable, but: " + redact(e)[:160]
        except Exception as e:  # noqa: BLE001
            status[h] = "error: " + redact(e)[:160]
    return status


def print_preflight(status: dict, have_key: bool) -> None:
    log("=" * 78)
    log(f"{KEY_ENV_VAR}: " + ("present (value never shown)" if have_key else
                              "MISSING. Rows that need Helius will be marked 'NO KEY'. Ask Paul to add it "
                              "(QUESTIONS_FOR_PAUL.md, Setup checklist step 2)."))
    blocked = [h for h, s in status.items() if s == "BLOCKED"]
    for h, s in status.items():
        log(f"  {h:<34} {s}")
    if blocked:
        log("BLOCKED domains (not allowed in this environment's network settings): " + ", ".join(blocked))
        log("Ask Paul to add them (QUESTIONS_FOR_PAUL.md, List 1). Rows that need them are recorded as BLOCKED; nothing is guessed.")
    log("=" * 78)


def run_row(ctx: Ctx, row, have_key: bool, status: dict, args) -> dict:
    started = utc_now()
    base = {"row": row.row, "tests": row.tests, "question": row.question, "env_var": row.env_var,
            "started_utc": started, "quick_mode": bool(args.quick), "script_version": SCRIPT_VERSION}
    if row.deferred:
        return dict(base, outcome="DEFERRED: " + row.deferred, headline="", finished_utc=utc_now())
    primary_blocked = [h for h in row.hosts if status.get(h) == "BLOCKED"]
    if row.needs_key and not have_key:
        if not (row.public_fallback and args.public_fallback and status.get("api.mainnet-beta.solana.com") == "ok"):
            return dict(base, outcome=f"NO KEY: {KEY_ENV_VAR} is not set (value never shown)", headline="",
                        finished_utc=utc_now(), domains_used=[])
    elif primary_blocked and len(primary_blocked) == len(row.hosts):
        return dict(base, outcome="BLOCKED: " + ", ".join(primary_blocked), headline="", finished_utc=utc_now(),
                    domains_used=[])
    ctx.row = row.row
    ctx.hosts_used, ctx.provider_used = set(), set()
    calls0 = ctx.budget.row_calls(row.row)
    credits0 = ctx.budget.data["credits_est"]
    out: dict
    try:
        out = row.run(ctx) or {}
    except HostBlocked as e:
        out = {"outcome": f"BLOCKED: {e.host}", "headline": "the domain was refused; nothing was guessed"}
    except MissingKey as e:
        out = {"outcome": "NO KEY: " + redact(e)}
    except NeedRow as e:
        out = {"outcome": f"SKIPPED: needs row {e.row} to have run first"}
    except BudgetExceeded as e:
        out = {"outcome": "STOPPED: " + redact(e), "follow_up": "Raise the cap only within the free plan (see README)."}
    except RpcRefused as e:
        out = {"outcome": "ERROR (refused locally, nothing sent): " + redact(e)}
    except RpcError as e:
        out = {"outcome": "ERROR: " + redact(e)}
    except Exception as e:  # noqa: BLE001 - never crash the whole run on one row
        log(redact(traceback.format_exc()))
        out = {"outcome": f"ERROR: {type(e).__name__}: {redact(e)}"}
    fixtures = ctx.store.close_row(row.row)
    res = dict(base)
    res.update(out)
    if args.quick and not str(res.get("outcome", "")).startswith(("NO KEY", "BLOCKED", "SKIPPED", "DEFERRED")):
        res["outcome"] = "QUICK MODE (not a pass mark): " + str(res.get("outcome"))
    prov = dict(res.get("provenance") or {})
    prov.setdefault("clock_sync", clock_sync_status())
    prov.setdefault("interval_clock", "time.monotonic_ns")
    res["provenance"] = prov
    res.update(finished_utc=utc_now(), domains_used=sorted(ctx.hosts_used),
               provider=", ".join(sorted(ctx.provider_used)) or "-",
               fixtures=res.get("fixtures") or fixtures,
               requests=ctx.budget.row_calls(row.row) - calls0,
               credits_est=ctx.budget.data["credits_est"] - credits0)
    return res


def is_final(prev: dict, args) -> bool:
    if not prev or args.rerun:
        return False
    if prev.get("quick_mode") and not args.quick:
        return False
    return str(prev.get("outcome", "")).startswith(FINAL_PREFIXES)


def main(argv=None, *, repo: str = REPO, transport=None, environ=None) -> int:
    """`transport` and `environ` exist only so the offline tests can run the whole runner with no network."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    store = Store(repo)
    rows = selected_rows(args)
    rows_meta = [{"row": r.row, "tests": r.tests,
                  "deferred": r.deferred or ("optional: run with --with-optional or --only " + r.row if r.optional else None)}
                 for r in ROWS]
    if args.list:
        res = store.all_results()
        for r in ROWS:
            log(f"{r.row}  {r.tests:<40} {(res.get(r.row) or {}).get('outcome', 'DEFERRED: ' + r.deferred if r.deferred else 'NOT RUN')}")
        return 0
    if args.t6_freeze:
        if os.path.exists(t6.FREEZE_PATH) and not args.force:
            log("t6_freeze.json already exists; use --force to replace it (this voids the old freeze).")
            return 1
        fr = t6.make_freeze(secrets.token_hex(16), utc_now())
        store.write_json(t6.FREEZE_PATH, fr)
        log(f"Wrote {os.path.relpath(t6.FREEZE_PATH, repo)}: seed {fr['seed']}, t6_select.py sha256 {fr['selection_sha256']}")
        log("Record both in docs/preregistration.md and commit BEFORE running A09.")
        return 0
    load_decoders()                                       # refuses to start if a pinned IDL hash differs
    env = os.environ if environ is None else environ
    key = load_helius_key(env)
    have_key = key is not None
    if env.get(KEY_ENV_VAR) and not have_key:
        log(f"{KEY_ENV_VAR} is set but looks malformed (value not shown); treating it as missing.")
    for spec in args.row_cap:
        r_id, _, n = spec.partition("=")
        budget_mod.ROW_CALL_CAPS[r_id.strip().upper()] = int(n)
    ledger = None if args.preflight else os.path.join(store.results_dir, "_budget_ledger.json")
    budget = Budget(ledger, monthly_cap=args.max_credits)
    recorder = None if args.preflight else store.record
    helius, public, jito = build_clients(budget, recorder, key, transport)
    getc = HttpGetClient(budget, recorder=recorder) if transport is None else \
        HttpGetClient(budget, recorder=recorder, transport=transport)
    opts = Options(quick=args.quick, public_fallback=args.public_fallback, a18_minutes=args.a18_minutes,
                   t6_stop_after_calibration=args.t6_stop_after_calibration, a20_url_template=args.a20_url_template)
    ctx = Ctx(store=store, budget=budget, helius=helius, public=public, jito=jito, get=getc, opts=opts)
    status = preflight(ctx, rows, have_key)
    print_preflight(status, have_key)
    if args.preflight:
        log("Preflight only: nothing was written.")
        return 0
    stopped = False
    for row in rows:
        prev = store.load_result(row.row)
        if is_final(prev, args):
            log(f"[{row.row}] already done ({prev.get('outcome')}); use --rerun to repeat")
            continue
        if stopped:
            continue
        log(f"[{row.row}] {row.question}")
        t0 = time.time()
        res = run_row(ctx, row, have_key, status, args)
        store.save_result(res)
        budget.save()
        store.write_results_md(rows_meta)
        log(f"[{row.row}] {res.get('outcome')}  ({round(time.time() - t0, 1)} s, {res.get('requests', 0)} requests, "
            f"~{res.get('credits_est', 0)} credits)")
        if str(res.get("outcome", "")).startswith("STOPPED: monthly"):
            log("Monthly credit cap reached: stopping the run. Nothing past the cap was sent.")
            stopped = True
    store.close_all()
    budget.save()
    store.write_results_md(rows_meta)
    log(f"Results: phase0/results.md and phase0/results/<row>.json. Estimated credits this month: "
        f"{budget.data['credits_est']} of the {budget.cap} cap.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Interrupted. Finished rows are saved; re-run the same command to continue.")
        sys.exit(130)
