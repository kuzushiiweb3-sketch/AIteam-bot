#!/usr/bin/env python3
"""PR-2 offline simulation (red-team phase 0 review, test PR-T3, second half).

In plain English: we invent rules that have NO edge (their true average result is exactly
break-even, the hardest case for the tests), push them through the whole pipeline
(research ticket, then the Gate v2 paper exam, with the retry rules of v1.0 or v1.1), and
count how often one reaches the paper-to-canary gate (Gate 3 -> 4) by day 90.

Two questions are answered:
  A. PER RULE (red-team's test): a no-edge rule enters at day 0; share that reaches Gate 3->4
     by day 90.
  B. PER PROGRAMME (extra stress, harsher than asked): every candidate the calendar allows
     before day 90 is a no-edge rule at the same time; share of simulated programmes in
     which at least one reaches Gate 3->4 by day 90.

Offline only: no network, no data, nothing signed or sent. Requires numpy.
Usage: python3 pr2_null_champion.py [quick]
"""
import math
import sys
import json
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, "/home/user/aiteam-bot/research/sims")
from pr9_bootstrap_false_pass import t_ppf, draw_trades, cp_upper, _check_t  # noqa: E402

TAIL_CUT = -100.0
B_BOOT = 10000
GATE_DAYS = 21
LAM_GATE = 10      # twin trades per green day on forward paper (>= 200 in 21 days)
LAM_RES = 20       # the candidate combination's trades per green day on its research holdout
LAST_DAY = 90      # a look on day <= 90 counts


# ------------------------------------------------------------------ lower bound on one sample
def lower_bound(rng, S, N, alpha, rule, delta=0.0):
    """S, N: 1-D day sums and counts. rule 'v10' = min(P, M); 'v11' = min(P, M, T) - delta."""
    n = S.shape[0]
    th = S.sum() / N.sum()
    if rule == "v11":
        z = S - th * N
        se = math.sqrt(n / (n - 1.0) * float((z * z).sum())) / N.sum()
        lt = th - t_ppf(1 - alpha, n - 1) * se - delta
        if lt <= 0:
            return lt
    elif th <= 0:
        return th
    idx = rng.integers(0, n, size=(B_BOOT, n))
    tb = S[idx].sum(1) / N[idx].sum(1)
    m = int(math.ceil(n ** (2.0 / 3.0)))
    idm = rng.integers(0, n, size=(B_BOOT, m))
    tm = math.sqrt(m) * (S[idm].sum(1) / np.maximum(N[idm].sum(1), 1) - th)
    k = max(1, int(math.floor(alpha * B_BOOT)))
    kk = int(math.ceil((1 - alpha) * B_BOOT))
    lp = np.partition(tb, k - 1)[k - 1]
    lm = th - np.partition(tm, kk - 1)[kk - 1] / math.sqrt(n)
    if rule == "v11":
        return min(lp, lm, lt)
    return min(lp, lm)


def sample(rng, kind, a, mean, lam, days, u):
    """Trades on the given day indices of one world. u = that world's shared day effects."""
    nd = len(days)
    N = rng.poisson(lam, size=nd)
    x = draw_trades(rng, kind, a, int(N.sum())) + mean
    did = np.repeat(np.arange(nd), N)
    y = x + u[np.asarray(days)][did] + rng.standard_t(3, size=nd)[did] * 0.0
    S = np.bincount(did, weights=y, minlength=nd)
    k_adv = int((y <= TAIL_CUT).sum())
    s_adv = float(y[y <= TAIL_CUT].sum())
    top3 = float(np.sort(y)[-3:].sum()) if y.size >= 3 else float(y.sum())
    return S, N.astype(float), k_adv, s_adv, top3


def tc1_delta(k_ref, n_ref, s_ref, k_h, n_h):
    """Tail completion +1 (v1.1 rule): phantom give-ups the holdout 'should' have seen."""
    k_exp = math.ceil((k_ref + 1.0) / (n_ref + 1.0) * n_h - 1e-12)
    phantom = max(0, k_exp - k_h)
    size = abs(s_ref / k_ref) if k_ref > 0 else abs(TAIL_CUT)
    return phantom * size / n_h


def research_test(rng, kind, a, mean, u, days, alpha, rule):
    """Returns True if the candidate's own mean passes (LB > 0) on these holdout days."""
    S, N, k, s, _ = sample(rng, kind, a, mean, LAM_RES, days, u)
    delta = 0.0
    if rule == "v11":
        # reference tail rate: an equal-sized research sample from the days before the holdout
        ref_days = [max(0, d - len(days)) for d in days]
        _, Nr, kr, sr, _ = sample(rng, kind, a, mean, LAM_RES, ref_days, u)
        delta = tc1_delta(kr, Nr.sum(), sr, k, N.sum())
    return lower_bound(rng, S, N, alpha, rule, delta) > 0


def gate_test(rng, kind, a, mean, u, start, alpha, rule):
    days = list(range(start, start + GATE_DAYS))
    S, N, k, s, top3 = sample(rng, kind, a, mean, LAM_GATE, days, u)
    delta = 0.0
    if rule == "v11":
        ref_days = [max(0, d - GATE_DAYS) for d in days]
        _, Nr, kr, sr, _ = sample(rng, kind, a, mean, LAM_GATE, ref_days, u)
        delta = tc1_delta(kr, Nr.sum(), sr, k, N.sum())
    g2 = lower_bound(rng, S, N, alpha, rule, delta) > 0
    g5 = (S.sum() - top3) / max(N.sum() - 3, 1) >= 0
    return g2 and g5


# ------------------------------------------------------------------ calendars
# Each research candidate: (name, family, [(look_day, holdout_days, alpha), ...]).
# A candidate that passes at a look may start Gate v2 on that day (version frozen and pushed).
def rng_days(a, b):
    return list(range(a, b + 1))


def v11_candidates():
    c = [("INC-1", "F0", [(28, rng_days(14, 27), 0.05)])]
    c.append(("F1-P", "F1", [(35, rng_days(14, 34), 0.02), (42, rng_days(14, 41), 0.03)]))
    for i in (1, 2, 3):
        c.append(("F1-V%d" % i, "F1", [(35, rng_days(14, 34), 0.00667), (42, rng_days(14, 41), 0.01)]))
    c.append(("F2-main", "F2", [(42, rng_days(28, 41), 0.05)]))
    c.append(("F2-Tlow", "F2", [(42, rng_days(28, 41), 0.025)]))
    c.append(("F2-Thigh", "F2", [(42, rng_days(28, 41), 0.025)]))
    for i in range(7):
        c.append(("F4-%d" % i, "F4", [(28, rng_days(14, 27), 0.014286)]))
    # second family windows (new versions / reserve tickets), fresh days only, full budgets
    c.append(("F1w2-P", "F1", [(63, rng_days(42, 62), 0.05)]))
    for i in (1, 2, 3):
        c.append(("F1w2-V%d" % i, "F1", [(63, rng_days(42, 62), 0.01667)]))
    c.append(("F2w2-main", "F2", [(56, rng_days(42, 55), 0.05)]))
    c.append(("F2w2-T1", "F2", [(56, rng_days(42, 55), 0.025)]))
    c.append(("F2w2-T2", "F2", [(56, rng_days(42, 55), 0.025)]))
    for i in range(7):
        c.append(("F4w2-%d" % i, "F4", [(42, rng_days(28, 41), 0.014286)]))
    return c


def step_alpha(schedule, step):
    return schedule[min(step, len(schedule) - 1)]


# ------------------------------------------------------------------ one world
def world_v11(rng, kind, a, mean, tau, schedule, only=None):
    """only: restrict to one candidate name (question A). Returns 1 if a false champion
    reaches Gate 3->4 by day 90."""
    u = tau * rng.standard_t(3, size=200) / math.sqrt(3.0)
    passes = []  # (day, name, family)
    for name, fam, looks in v11_candidates():
        if only is not None and name != only:
            continue
        for day, hold, alpha in looks:
            if research_test(rng, kind, a, mean, u, hold, alpha, "v11"):
                passes.append((day, name, fam))
                break
    # combinations: an entry winner (F1) with an exit (F2) or filter (F4) winner; both must pass
    if only is None:
        f1 = [p for p in passes if p[2] == "F1"]
        other = [p for p in passes if p[2] in ("F2", "F4")]
        for p in f1:
            for q in other:
                passes.append((max(p[0], q[0]), p[1] + "+" + q[1], "COMBO"))
    starts = sorted(set(p[0] for p in passes if p[0] + GATE_DAYS <= LAST_DAY))
    for step, sday in enumerate(starts):
        group = [p for p in passes if p[0] == sday]
        alpha = step_alpha(schedule, step) / len(group)   # same-day starts split the step
        for _ in group:
            if gate_test(rng, kind, a, mean, u, sday, alpha, "v11"):
                return 1
    return 0


def world_v10(rng, kind, a, mean, tau, only=None):
    """v1.0 as written: tiers by attempt count k (1-3: 10%, 4-10: 5%, >10: 1%); a champion
    without a passed research ticket starts one tier stricter; the same version may re-attempt
    after 21 new green days; parallel attempts allowed at their own tier; LB = min(P, M)."""
    u = tau * rng.standard_t(3, size=200) / math.sqrt(3.0)
    queue = []  # (start_day, name, tested)
    if only in (None, "INC-1"):
        queue.append((28, "INC", False))   # paper incumbent: forward paper from about day 28
    for name, fam, looks in v11_candidates():
        if name == "INC-1" or (only is not None and name != only):
            continue
        if "w2" in name:
            continue  # v1.0 lets the same version re-try instead of needing new versions
        for day, hold, alpha in looks:
            if research_test(rng, kind, a, mean, u, hold, alpha, "v10"):
                queue.append((day, name, True))
                break
    k = 0
    events = sorted(queue)
    while events:
        sday, name, tested = events.pop(0)
        if sday + GATE_DAYS > LAST_DAY:
            continue
        k += 1
        tier = 0 if k <= 3 else (1 if k <= 10 else 2)
        if not tested:
            tier = min(tier + 1, 2)
        alpha = (0.10, 0.05, 0.01)[tier]
        if gate_test(rng, kind, a, mean, u, sday, alpha, "v10"):
            return 1
        events.append((sday + GATE_DAYS, name, tested))  # same version re-attempts
        events.sort()
    return 0


def run(args):
    policy, kind, a, mean, tau, schedule, only, reps, seed = args
    rng = np.random.default_rng(seed)
    t0 = time.time()
    hits = 0
    for _ in range(reps):
        if policy == "v10":
            hits += world_v10(rng, kind, a, mean, tau, only)
        else:
            hits += world_v11(rng, kind, a, mean, tau, schedule, only)
    return dict(policy=policy, kind=kind, a=a, mean=mean, tau=tau, schedule=schedule, only=only,
                reps=reps, hits=hits, rate=hits / reps, upper95=cp_upper(hits, reps),
                secs=round(time.time() - t0, 1))


def main():
    _check_t()
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    R = 1000 if quick else 10000
    jobs = []
    seed = 902
    sched_rt = [0.10, 0.05, 0.01]          # red-team's recommended alpha-spending (10/5/1, then 1)
    sched_t = [0.05, 0.025, 0.01]          # tighter alternative
    for kind, a in (("RS", 2.2), ("SYM", 3.0)):
        # A. per rule: the incumbent route and the research route (F1 primary) on their own
        for only in ("INC-1", "F1-P", "F2-main"):
            seed += 1; jobs.append(("v10", kind, a, 0.0, 8.0, None, only, R, seed))
            seed += 1; jobs.append(("v11", kind, a, 0.0, 8.0, sched_rt, only, R, seed))
        # B. per programme, every candidate a no-edge rule at once
        seed += 1; jobs.append(("v10", kind, a, 0.0, 8.0, None, None, R, seed))
        for sch in (sched_rt, sched_t):
            seed += 1; jobs.append(("v11", kind, a, 0.0, 8.0, sch, None, R, seed))
            seed += 1; jobs.append(("v11", kind, a, 0.0, 0.0, sch, None, R, seed))  # no shared days
    # B'. realistic no-edge: true mean = -3 points (roughly the round-trip fees)
    seed += 1; jobs.append(("v11", "RS", 2.2, -3.0, 8.0, sched_rt, None, R, seed))
    seed += 1; jobs.append(("v10", "RS", 2.2, -3.0, 8.0, None, None, R, seed))
    with Pool(4) as pool:
        res = pool.map(run, jobs)
    out = "/home/user/aiteam-bot/research/sims/pr2_results%s" % ("_quick" if quick else "")
    with open(out + ".json", "w") as f:
        json.dump(res, f, indent=1)
    lines = ["policy  trades  true-mean  shared-day-sd  Gate-v2 schedule      scope        rate %   [95% upper]   secs"]
    for r in res:
        sch = "v1.0 tiers" if r["schedule"] is None else "/".join("%g" % (100 * x) for x in r["schedule"]) + "%"
        scope = ("rule " + r["only"]) if r["only"] else "programme"
        lines.append("%-6s  %-6s  %6.1f     %5.1f          %-20s  %-12s %6.3f   [%6.3f]   %5.1f" % (
            r["policy"], "%s%.1f" % (r["kind"], r["a"]), r["mean"], r["tau"], sch, scope,
            100 * r["rate"], 100 * r["upper95"], r["secs"]))
    txt = "\n".join(lines)
    print(txt)
    with open(out + ".txt", "w") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()
