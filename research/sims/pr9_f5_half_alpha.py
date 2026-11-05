#!/usr/bin/env python3
"""PR-9 follow-up: the F5 single-rule ticket (56 day blocks, ~5 trades a day) failed at
alpha 0.0833% under the worst left tail (0.110%). v1.1 therefore scores F5 at alpha/2 =
0.04167% (B = max(10,000, ceil(100/alpha)) = 240,000). This checks that the false-pass rate
at that setting is <= 0.0833%. Offline only."""
import json, sys
from multiprocessing import Pool
sys.path.insert(0, "/home/user/aiteam-bot/research/sims")
from pr9_bootstrap_false_pass import run_cell, cp_upper, _check_t
if __name__ == "__main__":
    _check_t()
    a = 0.0008333 / 2
    cells = [("LS", 1.7, 5, 8.0, 56, [a], 100000, 500, 240000, 7001 + i) for i in range(4)]
    cells += [("LS", 2.2, 5, 8.0, 56, [a], 100000, 500, 240000, 7101)]
    with Pool(4) as p:
        res = p.map(run_cell, cells)
    json.dump(res, open("/home/user/aiteam-bot/research/sims/pr9_f5_results.json", "w"), indent=1)
    k = sum(r["fpTC1"][str(a)] for r in res[:4]); n = sum(r["reps_v11"] for r in res[:4])
    print("LS a=1.7 lam=5 n=56, scored at alpha/2: false passes %d of %d = %.4f%% [95%% upper %.4f%%] vs target 0.0833%%"
          % (k, n, 100 * k / n, 100 * cp_upper(k, n)))
    r = res[4]; k2 = r["fpTC1"][str(a)]
    print("LS a=2.2 lam=5 n=56: %d of %d = %.4f%% [upper %.4f%%]" % (k2, r["reps_v11"], 100 * k2 / r["reps_v11"], 100 * cp_upper(k2, r["reps_v11"])))
