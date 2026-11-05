#!/usr/bin/env python3
"""PR-9 offline simulation (red-team phase 0 review, test PR-T3, first half).

In plain English: we invent trading results where the TRUE average is exactly zero
(no edge), with the ugly features real meme-coin results have (rare huge winners or
rare huge losers, and days that move together). Then we score them with the
preregistration's lower-bound recipe and count how often a no-edge rule would
"pass" (lower bound above zero). That count must not exceed the stated alpha.

Offline only. Reads no data, touches no network, signs and sends nothing.
Requires: python3 standard library + numpy (scipy is not installed, so the Student-t
quantile is computed here and checked against printed table values at start-up).

Lower bounds compared (all on day blocks, ratio-of-sums mean):
  P   percentile block bootstrap LB (the alpha-quantile of the resampled means)
  M   m-out-of-n LB, m = ceil(n^(2/3)), LB_m = th - Q_{1-a}(sqrt(m)(th*_m - th))/sqrt(n)
  T   cluster-t LB: th - t_{n-1,1-a} * sqrt(n/(n-1) * sum_j (S_j - th N_j)^2) / sum_j N_j
  v1.0 rule  = min(P, M)
  v1.1 rule  = min(P, M, T)
A false pass is LB > 0.

Usage: python3 pr9_bootstrap_false_pass.py [quick]
"""
import math
import sys
import time
import json
from multiprocessing import Pool

import numpy as np

# ---------------------------------------------------------------- Student t quantile
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 500, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > FPMIN else FPMIN)
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = d if abs(d) > FPMIN else FPMIN
        c = 1.0 + aa / c; c = c if abs(c) > FPMIN else FPMIN
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = d if abs(d) > FPMIN else FPMIN
        c = 1.0 + aa / c; c = c if abs(c) > FPMIN else FPMIN
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    bt = math.exp(lbt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    x = df / (df + t * t)
    tail = 0.5 * _betai(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def t_ppf(p, df):
    """Upper quantile helper: returns t with P(T <= t) = p, for p > 0.5."""
    lo, hi = 0.0, 1e4
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _check_t():
    # Printed table values (any standard t table): t_{0.95,13}=1.771, t_{0.99,20}=2.528,
    # t_{0.995,13}=3.012, t_{0.975,27}=2.052, t_{0.999,55}=3.245 (approx)
    for p, df, ref in [(0.95, 13, 1.7709), (0.99, 20, 2.5280), (0.995, 13, 3.0123), (0.975, 27, 2.0518)]:
        got = t_ppf(p, df)
        assert abs(got - ref) < 2e-3, (p, df, got, ref)


# ---------------------------------------------------------------- scenarios
# Per-trade net results in points (percent of stake). Every scenario is centred so that
# the TRUE per-trade mean is exactly 0 (analytic mean subtracted).
LOSS_P, LOSS_LO, LOSS_HI = 0.72, -45.0, -3.0
WIN_XM = 20.0


def _rs_mean(a):
    return LOSS_P * 0.5 * (LOSS_LO + LOSS_HI) + (1 - LOSS_P) * WIN_XM * a / (a - 1.0)


def draw_trades(rng, kind, a, size):
    if kind == "SYM":
        return 30.0 * rng.standard_t(3, size)
    u = rng.random(size)
    loss = rng.uniform(LOSS_LO, LOSS_HI, size)
    win = WIN_XM * (1.0 - rng.random(size)) ** (-1.0 / a)
    x = np.where(u < LOSS_P, loss, win) - _rs_mean(a)
    return x if kind == "RS" else -x  # LS = mirror image (left-skewed, e.g. exit differences)


def simulate_day_sums(rng, kind, a, lam, tau, n, reps, tail_cut=-100.0):
    """Simulates 2n days per replicate: days 0..n-1 are the RESEARCH days, n..2n-1 the HOLDOUT.
    Returns holdout S, N (reps, n) and, for the tail-completion rule, per replicate:
    k_h (holdout trades <= tail_cut), n_h, k_r, n_r, mean size of research trades <= tail_cut."""
    D = 2 * n
    N2 = rng.poisson(lam, size=(reps, D))
    tot = int(N2.sum())
    x = draw_trades(rng, kind, a, tot)
    day_id = np.repeat(np.arange(reps * D), N2.ravel())
    # day effect (whole day shifts together; heavy-tailed t3 scaled to sd tau)
    u = tau * rng.standard_t(3, size=reps * D) / math.sqrt(3.0)
    y = x + u[day_id]
    S2 = np.bincount(day_id, weights=y, minlength=reps * D).reshape(reps, D)
    adv = (y <= tail_cut)
    K2 = np.bincount(day_id, weights=adv.astype(float), minlength=reps * D).reshape(reps, D)
    A2 = np.bincount(day_id, weights=np.where(adv, y, 0.0), minlength=reps * D).reshape(reps, D)
    S, N = S2[:, n:], N2[:, n:]
    k_h = K2[:, n:].sum(1); n_h = N.sum(1)
    k_r = K2[:, :n].sum(1); n_r = N2[:, :n].sum(1)
    a_r = A2[:, :n].sum(1)
    mean_adv_r = np.where(k_r > 0, a_r / np.maximum(k_r, 1), 0.0)
    # Tail completion (v1.1 rule TC): phantom give-ups = max(0, ceil(f_r * n_h) - k_h),
    # each of the research mean size; the LB is lowered by their total / n_h.
    k_exp = np.ceil(k_r / np.maximum(n_r, 1) * n_h - 1e-12)
    phantom = np.maximum(0.0, k_exp - k_h)
    delta = phantom * np.abs(mean_adv_r) / n_h
    # TC+1 (the v1.1 rule as frozen): research frequency (k_r + 1) / (n_r + 1); size = research
    # mean adverse value, or the tail cut itself if research saw none.
    k_exp1 = np.ceil((k_r + 1.0) / (n_r + 1.0) * n_h - 1e-12)
    phantom1 = np.maximum(0.0, k_exp1 - k_h)
    size1 = np.where(k_r > 0, np.abs(mean_adv_r), abs(tail_cut))
    delta1 = phantom1 * size1 / n_h
    return S, N, delta, delta1


# ---------------------------------------------------------------- lower bounds
def lb_t(S, N, alphas):
    n = S.shape[1]
    th = S.sum(1) / N.sum(1)
    z = S - th[:, None] * N
    se = np.sqrt(n / (n - 1.0) * (z * z).sum(1)) / N.sum(1)
    return th, {a: th - t_ppf(1 - a, n - 1) * se for a in alphas}


def lb_boot(rng, s, nn, th, alphas, B):
    """Percentile and m-out-of-n LBs for one replicate (s, nn are length-n arrays)."""
    n = s.shape[0]
    idx = rng.integers(0, n, size=(B, n))
    tb = s[idx].sum(1) / nn[idx].sum(1)
    m = int(math.ceil(n ** (2.0 / 3.0)))
    idm = rng.integers(0, n, size=(B, m))
    nm = nn[idm].sum(1)
    nm = np.where(nm == 0, 1, nm)  # guard (never happens at lam >= 10)
    tm = math.sqrt(m) * (s[idm].sum(1) / nm - th)
    tb.sort(); tm.sort()
    outP, outM = {}, {}
    for a in alphas:
        k = max(1, int(math.floor(a * B)))          # k-th smallest (1-indexed)
        outP[a] = tb[k - 1]
        kk = int(math.ceil((1 - a) * B))            # ceil((1-a)B)-th smallest
        outM[a] = th - tm[kk - 1] / math.sqrt(n)
    return outP, outM


# ---------------------------------------------------------------- one cell
def run_cell(args):
    kind, a, lam, tau, n, alphas, reps_v11, reps_v10, B, seed = args
    rng = np.random.default_rng(seed)
    t0 = time.time()
    amax = max(alphas)
    fp11 = {x: 0 for x in alphas}
    fp10 = {x: 0 for x in alphas}
    fpT = {x: 0 for x in alphas}
    fpP = {x: 0 for x in alphas}
    fpTC = {x: 0 for x in alphas}
    fpTC1 = {x: 0 for x in alphas}
    done = 0
    chunk = 5000
    v10_seen = 0
    while done < reps_v11:
        r = min(chunk, reps_v11 - done)
        S, N, delta, delta1 = simulate_day_sums(rng, kind, a, lam, tau, n, r)
        th, LT = lb_t(S, N, alphas)
        for x in alphas:
            fpT[x] += int((LT[x] > 0).sum())
        for i in range(r):
            need11 = LT[amax][i] > 0
            in10 = v10_seen < reps_v10
            if in10:
                v10_seen += 1
            need10 = in10 and th[i] > 0
            if not (need11 or need10):
                continue
            P, M = lb_boot(rng, S[i], N[i], th[i], alphas, B)
            for x in alphas:
                if need11:
                    lb = min(P[x], M[x], LT[x][i])
                    if lb > 0:
                        fp11[x] += 1
                    if lb - delta[i] > 0:
                        fpTC[x] += 1
                    if lb - delta1[i] > 0:
                        fpTC1[x] += 1
                if need10:
                    if min(P[x], M[x]) > 0:
                        fp10[x] += 1
                    if P[x] > 0:
                        fpP[x] += 1
        done += r
    return dict(kind=kind, a=a, lam=lam, tau=tau, n=n, B=B, reps_v11=reps_v11, reps_v10=reps_v10,
                fp11={str(x): fp11[x] for x in alphas}, fp10={str(x): fp10[x] for x in alphas},
                fpT={str(x): fpT[x] for x in alphas}, fpP={str(x): fpP[x] for x in alphas}, fpTC={str(x): fpTC[x] for x in alphas}, fpTC1={str(x): fpTC1[x] for x in alphas},
                secs=round(time.time() - t0, 1))


def cp_upper(k, n, conf=0.95):
    """One-sided Clopper-Pearson upper bound for a binomial rate (bisection, log-space, stdlib only)."""
    if k >= n:
        return 1.0
    target = 1 - conf
    lo, hi = k / n, 1.0
    lg = math.lgamma
    for _ in range(80):
        p = 0.5 * (lo + hi)
        lp, lq = math.log(p), math.log1p(-p)
        mx, terms = -1e300, []
        for j in range(0, k + 1):
            t = lg(n + 1) - lg(j + 1) - lg(n - j + 1) + j * lp + (n - j) * lq
            terms.append(t)
            mx = max(mx, t)
        cdf = math.exp(mx) * sum(math.exp(t - mx) for t in terms)
        if cdf > target:
            lo = p
        else:
            hi = p
    return 0.5 * (lo + hi)


def main():
    _check_t()
    quick = len(sys.argv) > 1 and sys.argv[1] == "quick"
    alphas = [0.10, 0.05, 0.03, 0.025, 0.02, 0.014286, 0.01, 0.00714, 0.00667, 0.005]
    shapes = [("RS", 2.2), ("RS", 1.7), ("LS", 2.2), ("LS", 1.7), ("SYM", 3.0)]
    lams = [10, 70]
    ns = [14, 21, 28]
    reps11, reps10 = (4000, 2000) if quick else (40000, 10000)
    B = 20000  # >= max(10,000, ceil(100/alpha)) for every alpha >= 0.5% in the list
    cells = []
    seed = 20261105
    for kind, a in shapes:
        for lam in lams:
            for n in ns:
                seed += 1
                cells.append((kind, a, lam, 8.0, n, alphas, reps11, reps10, B, seed))
    for n in ns:  # strong day clustering
        for kind in ("RS", "LS"):
            seed += 1
            cells.append((kind, 2.2, 70, 20.0, n, alphas, reps11, reps10, B, seed))
    # F2 size: >= 2,000 paired coins over 14 days (lam 140), left-skewed exit differences
    for a in (2.2, 1.7):
        seed += 1
        cells.append(("LS", a, 140, 8.0, 14, alphas, reps11, reps10, B, seed))
    # F3 Stage B size: 56 days, ~200 champion trades (lam 4), alpha 5% (and 2.5%)
    for kind, a in (("LS", 2.2), ("LS", 1.7), ("SYM", 3.0), ("RS", 2.2)):
        seed += 1
        cells.append((kind, a, 4, 8.0, 56, [0.05, 0.025], reps11, reps10, B, seed))
    # F5 single AI rule: 56 days, few trades a day, alpha 0.0833% (B = 120,000)
    for kind, a in (("LS", 2.2), ("LS", 1.7), ("SYM", 3.0)):
        seed += 1
        cells.append((kind, a, 5, 8.0, 56, [0.000833], 10 * reps11, reps10 // 5, 120000, seed))
    with Pool(4) as pool:
        res = pool.map(run_cell, cells)
    out = "/home/user/aiteam-bot/research/sims/pr9_results%s.json" % ("_quick" if quick else "")
    with open(out, "w") as f:
        json.dump(res, f, indent=1)
    lines = []
    P = lines.append
    P("PER SCENARIO (false-pass %, true mean = 0). Columns per alpha: v1.0 | v1.1 | v1.1+TC | v1.1+TC+1")
    for r in res:
        name = "%s a=%.1f lam=%d tau=%g n=%d" % (r["kind"], r["a"], r["lam"], r["tau"], r["n"])
        cols = []
        for x in sorted((float(k) for k in r["fp11"]), reverse=True):
            k = str(x)
            cols.append("a=%g%%: %.3f | %.3f | %.3f | %.3f" % (100 * x, 100 * r["fp10"][k] / r["reps_v10"],
                        100 * r["fp11"][k] / r["reps_v11"], 100 * r["fpTC"][k] / r["reps_v11"],
                        100 * r["fpTC1"][k] / r["reps_v11"]))
        P("%-34s %s" % (name, "   ".join(cols)))
    P("")
    P("WORST CASE over scenarios, by (blocks n, alpha). Rates in %; [ ] = one-sided 95% Clopper-Pearson upper bound")
    P("  n    alpha   | v1.0 min(P,M)       | min(P,M,T)          | min(P,M,T) + TC     | v1.1 = min(P,M,T)+TC+1 | worst scenario for v1.1")
    worst = {}
    for r in res:
        name = "%s a=%.1f lam=%d tau=%g" % (r["kind"], r["a"], r["lam"], r["tau"])
        for k in r["fp11"]:
            x = float(k)
            key = (r["n"], x)
            w = worst.setdefault(key, {"v10": (-1, 0, 1, ""), "v11": (-1, 0, 1, ""), "tc": (-1, 0, 1, ""),
                                       "tc1": (-1, 0, 1, "")})
            for tag, cnt, tot in (("v10", r["fp10"][k], r["reps_v10"]), ("v11", r["fp11"][k], r["reps_v11"]),
                                  ("tc", r["fpTC"][k], r["reps_v11"]), ("tc1", r["fpTC1"][k], r["reps_v11"])):
                if cnt / tot > w[tag][0]:
                    w[tag] = (cnt / tot, cnt, tot, name)
    for key in sorted(worst, key=lambda z: (z[0], -z[1])):
        w = worst[key]
        def f(t):
            rate, cnt, tot, _ = w[t]
            return "%7.3f [%7.3f]%s" % (100 * rate, 100 * cp_upper(cnt, tot), "*" if rate > key[1] else " ")
        P("%3d  %8.4f  | %s | %s | %s | %s    | %s" % (key[0], 100 * key[1], f("v10"), f("v11"), f("tc"), f("tc1"),
                                                  w["tc1"][3]))
    P("(* = point estimate above the stated alpha)")
    P("seconds per cell: %s" % [r["secs"] for r in res])
    txt = "\n".join(lines)
    print(txt)
    with open(out.replace(".json", ".txt"), "w") as f:
        f.write(txt + "\n")


if __name__ == "__main__":
    main()
