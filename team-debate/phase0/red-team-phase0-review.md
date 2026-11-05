# Red-team Phase 0 review: preregistration, fee model, costs, assumption register, tech stack

## In plain English (for Paul)
- I attacked the five Phase 0 rulebooks the team wrote before any data exists. The most important is the "pre-registration", which fixes in advance how every trading idea will be judged.
- It is careful, and most of its arithmetic is right. But I found ways a lucky rule could still get through, mainly by **re-trying the final paper exam**, by **designing spare tests after peeking at the data**, and because the bot **can't see coins it misses**. Those must be fixed before recording starts (Gate 0→1). No data exists yet, so fixing them now costs nothing.
- All five documents get **"sign off with fixes"**. None is rejected. The fee maths in particular checks out: I re-derived it from Pump's own code and on-chain data, and it matched to the last unit.

**Reviewer:** red-team. **Date:** 2026-11-05. **Files reviewed:** `docs/preregistration.md` v1.0 (SHA-256 `072a774fadb65861ba6004f4d0d76846e1b7b226faf2fc331d82ae717e7698e1`; I recomputed it, and it matches the frozen hash), `docs/fee-model.md` v1.0, `docs/costs.md`, `docs/assumption-register.md`, `docs/tech-stack.md`.

**Tags.** [VERIFIED-DOC] = primary source read this session (URL given). [VERIFIED-SEARCH] = search results only. [UNVERIFIED] = inference; the test that settles it is named. [DERIVED] = arithmetic.

**Sources fetched this session** (raw.githubusercontent.com works from the shell): `https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/` `README.md`, `docs/SYNTHETIC_MIGRATION.md`, `idl/pump.json`, `idl/pump_amm.json` [VERIFIED-DOC].

**How to read severities.** Critical = could lose real money or certify a fake edge. High = a likely false pass or a large blind spot. Medium = biases results or wastes weeks or money. Low = a clarification or consistency fix. "BLOCKS" = must be fixed before Gate 0→1.

---

## Verdicts at a glance
| Document | Verdict | Blocking findings |
|---|---|---|
| `docs/preregistration.md` | **SIGN OFF WITH FIXES.** v1.0 is not signed as it stands. I sign v1.1 once the blocking fixes are in | PR-1, PR-2, PR-3, PR-4, PR-5 |
| `docs/fee-model.md` | **SIGN OFF WITH FIXES** | FM-3, FM-4, FM-5 (T6 definition); FM-1 and FM-2 block the Phase 3 guard design |
| `docs/costs.md` | **SIGN OFF WITH FIXES** | None for Gate 0→1, but C01/D4 must measure data volume (CO-7e) before the disk is bought; CO-2, CO-3 and CO-4 before Phase 3 |
| `docs/assumption-register.md` | **SIGN OFF WITH FIXES** | AR-1 (seven missing High rows) |
| `docs/tech-stack.md` | **SIGN OFF WITH FIXES** | TS-1, TS-2, TS-6, TS-8 block its adoption (the recorder is built on it in Phase 1) |

## Top 10 findings (most money or most self-deception first)
| # | ID | Finding | Severity | Blocks Gate 0→1? |
|---|---|---|---|---|
| 1 | PR-2 | Gate v2 (the last edge test before real money) can be passed by re-trying: same-version re-attempts, parallel attempts, and untested champions allowed. That gives a 27% false pass in 3 tries | High | Yes |
| 2 | PR-1 / AR-1.1 | The bot can't see coins it misses. U0 and the coverage audit come from our own decoder, so a new migration path shrinks the universe silently | High | Yes |
| 3 | PR-3 / TS-1 | Sealed holdouts are honour-system. Spare (reserve) tickets can be designed after other families have read their data. Registration dates are forgeable | High | Yes |
| 4 | FM-1 | "Sell all + close account" in one transaction lets 1 token of dust make our crash sell fail | High (live) | No; blocks the Phase 3 guard |
| 5 | TS-6 | Events inside failed transactions could become fake trades and prices, if failed transactions carry inner instructions | High (data) | Yes (adoption) |
| 6 | PR-5 | The thermometer can pass with no skill: Stage A look-ahead, and a drawdown path any trade-thinning filter passes when the champion loses money | High | Yes |
| 7 | PR-4 | Test F1 (forensics) peeks at CHN-A's holdout, then may retire it and get its α back | High | Yes |
| 8 | FM-2 | Boosted pools price in virtual SOL that sellers can't be paid (error 6063). The leftover after BOOST is unmeasured | Medium-High | No; blocks Phase 3 |
| 9 | PR-6 | The week-4 stop almost can't fire (best-of-N point-estimate screens), so about 2 months of bills are spent on nothing | Medium-High | No |
| 10 | TS-2 | Flushing to disk after every frame on network storage makes the recorder fall behind, causing gaps we can't backfill | Medium-High | Yes (adoption) |

### Seams between documents (where one file assumes something another doesn't deliver)
- **Fee fallback.** The preregistration's fee fallback ≠ the fee model's (PR-14b / FM-7). Paper results would depend on which module loads.
- **Exit timing.** The preregistration simulates exits on the bot's clock. DESIGN runs them on the guard's separate feed (PR-13 ↔ A-019).
- **Rent and dust.** The fee model's "rent costs 0" assumes the close happens inside the sell. That is the FM-1 trap (FM-1 ↔ A-018).
- **T6 and the gate.** T6 needs recorder data. The recorder needs Gate 0→1. Gate 0→1 needs T6 (FM-5).
- **Money stop and statistics.** The research ceiling (costs F8) arrives before the preregistration's month-3 verdicts (PR-18 / CO-9).
- **AI spend cap.** One Anthropic cap covers the safety-relevant change reader and the optional desk (CO-3 ↔ TS-8b).
- **Recorder-only mode.** Dropping Helius stops the `known_at` lookups that later tests need (CO-5).

---

## 1. `docs/preregistration.md` (v1.0)

### What is sound (checked, no change needed)
- The α arithmetic adds up. F1: 1 + 1.5 + 2.5 = 5% for the primary, and 3 × 1.667% for the variants, so 10% in total, matching rulings §4b. F2: 5 + 2.5 + 2.5 = 10%. F4: 7 × 1.4286% = 10%, with waves at 2 × 0.714%. F5: 5% ÷ 60 = 0.0833% [DERIVED].
- Splitting α across the three F1 looks (Bonferroni) is valid whatever the correlation between looks. "All conditions at full α" is a valid intersection-union test. "Either path, α split" is a valid Bonferroni.
- The m-out-of-n lower-bound formula is the standard one. Seeds, ratio-of-sums means and paired resampling are all well specified.
- Labels may use hindsight and features may not; `known_at` is used for funding links; histories use finished coins only. These are the right rules.
- The race rule is safely biased towards "don't race": a racing cost of USD 2,000 a month over 300 trades is about 27 points per trade on a USD 25 stake [DERIVED].
- The F3 split (5% + 5%) really is tighter than two 90% paths.

### Findings

**PR-1. The bot can't see the coins it misses, so "no blind spots" is untested during research. Severity: High. BLOCKS.**
- U0 is built from our own decoded events (`CompletePumpAmmMigrationEvent` + `CreatePoolEvent`).
  - Pump already has two migration instructions, `migrate` and `migrate_v2`, and four trade generations [VERIFIED-DOC pump.json instruction list].
  - If Pump adds a third migration path our decoder doesn't know, U0 shrinks silently. Every ticket, and B-NULL, then runs on a biased universe.
- The green-day coverage audit samples "20 random pools", drawn from pools *we already know*. A pool we never saw can't be sampled.
- MISSED_COIN (≤ 1%) is checked only at Gate v2 (G8). It isn't part of the green-day test, so no research ticket checks it.
- **Fix demanded:**
  1. An **independent migration audit**. From a provider other than the main stream, list every new account owned by PumpSwap with the `Pool` discriminator, plus every bonding curve that turns `complete`. U0 is reconciled against it daily.
  2. A **green day also requires MISSED_COIN ≤ 1%** against that audit.
  3. **Misses are classified** by migration instruction, quote mint, mayhem flag and token program. Any instruction name outside the frozen list, or ≥ 3 misses of one class in 7 days, makes the day red.
  4. Of the 20 audited pools, 5 are drawn from the independent audit, not from our recorder.
- **On the "≤ 1%" bar itself (flagged for review):** 1% is acceptable only for *random* misses. A *systematic* 1% (one migration path) is not acceptable, hence point 3.

**PR-2. Gate v2 can be passed by re-trying. Severity: High (the last statistical gate before real money). BLOCKS.**
- The tiers allow attempts 1–3 at 90% each.
  - The same rule version may re-attempt after 21 new days.
  - Several champions may attempt at once on the same days.
  - A null champion tried 3 times passes at least once with probability 1 − 0.9³ = **27%** [DERIVED].
- §7 rule 6 says a rule must pass its research ticket first. But §7's Gate v2 row says "a champion without a passed research ticket starts one tier stricter", which lets an untested rule go straight to Gate v2. **These contradict each other.** The rulings (§4b) say Gate v2 applies "to the single champion".
- The canary measures fills, not edge (50 trades at 0.1 SOL). So Gate v2 really is the last test of whether the edge exists.
- **Fix demanded:**
  1. **One attempt per rule version.** A re-attempt must be a new version with its own research ticket.
  2. **Parallel attempts** on overlapping days split the current tier's α equally.
  3. **Every champion needs a passed research ticket**, with one exception: the frozen incumbent E_inc + X0 gets one attempt, at 95%. A combination (an entry winner plus an exit winner) counts only if both parts passed. The twin that is tested must run the combination.
  4. *Recommended (a tightening):* α-spending across attempts: 10% / 5% / 1%, then 1%.
- **Test that proves the fix:** a pure offline simulation of 10,000 null champions under the final rules should show ≤ 1% reaching Gate 3→4 by day 90.

**PR-3. Sealed holdouts are honour-system, and spare (reserve) tickets can be designed after the data has been seen. Severity: High. BLOCKS.**
- The ledger says a ticket's α is fixed "before any of its holdout is read". But:
  - a "family window" is only "≥ 28 green days that no earlier test *of that family* used as holdout";
  - other families may read the same days (§7 rule 5);
  - dashboards show B-NULL and the incumbent on every day (§2.4.7);
  - the AI desk sees R-half coins from other families' holdouts.
- **Concrete leak:** F2's research days 0–27 contain F1's holdout (days 14–27) and the F4 wave holdout (days 0–27). The exit researchers see per-coin outcomes on exactly those days, and could then register a reserve F1 or F4 ticket shaped by them.
- Every agent here is an AI working across sessions. One "run it on all days" research script would read a sealed holdout by accident.
- **Fix demanded:**
  1. **Reserve tickets and new-version tickets use only fresh days.** Their holdout is only green days that start *after* the registration commit is pushed.
  2. **Technical sealing.** One scoring tool computes ticket metrics. Every run is logged append-only with the days it touched. An unscheduled run on a sealed holdout voids the ticket and spends its α. Research tools refuse rule-vs-baseline metrics on sealed days.
  3. **Proof of registration** is the push to GitHub (server-side time), plus the SHA-256 copied into Paul's daily summary, which is an outside timestamp. A local git commit date can be set to anything.

**PR-4. "Retire it unrun and get the α back" works even after peeking. Severity: High. BLOCKS.**
- Test F1 (forensics) uses days 0–13. That includes CHN-A's holdout, days 7–13.
- It reads insider-selling outcomes on those days. Then it either retires CHN-A (α returned) or runs it on the very days it just looked at. That is an early look with a free cancel option.
- **Fix demanded:**
  1. Test F1 (forensics) uses days 0–6 only, or CHN-A's holdout moves to fresh days ≥ 14 (preferred, see PR-8c).
  2. **General rule:** α returns only if no data from the ticket's holdout days entered the decision to retire it. Otherwise retiring spends the α.

**PR-5. The market thermometer can pass without any forecasting skill. Severity: High (a false pass also blocks the week-4 stop). BLOCKS.**
- **(a) Look-ahead in Stage A.**
  - The problem:
    - r_b averages B-NULL trades *decided* in block b, but they exit up to 72,000 slots (4 h) later, inside block b+1. So r_b and r_{b+1} share market hours, which pushes ρ1 up mechanically.
    - The tradable signal Temp(t) uses only *completed* exits. That is a different, lagged quantity.
    - There are 4 fixed blocks a day, so a time-of-day pattern looks like "persistence".
  - **Fix demanded:**
    - the Stage A metric = Spearman correlation of Temp at block start (completed exits only) with the mean net of trades decided in the next block;
    - remove the research-period mean per block-of-day first;
    - also report the lag-4 (same time yesterday) correlation as a seasonality check.
- **(b) Loophole in the drawdown path.**
  - The problem:
    - If the champion loses money (E_inc + X0 is expected to), *any* filter that trades less loses less. So "total P&L gated ≥ ungated" and "DD_gated ≤ 0.75 × DD_ungated" both pass for a coin-flip gate.
    - The constrained bot's 20% drawdown stop also caps DD_ungated.
    - The two free yardsticks only need to be beaten on a point estimate, which luck alone does often.
  - **Fix demanded:**
    - the drawdown path counts only if the ungated champion's base-view mean > 0;
    - add a **random-gate placebo**: 1,000 draws with the same warm fraction, and the thermometer must beat their 90th percentile, mirroring B-RAND;
    - measure drawdown with the drawdown stop switched off in both arms (notional, report-only).
- **(c) The champion must be frozen when Stage B starts**, not "the current champion". If it was selected on days that overlap Stage B (for example the tournament holdout, days 28–41), only Stage B days after its selection count.
- **(d) Power.**
  - At about 200 champion trades and a per-trade spread of 40–100 points, the smallest gated-minus-ungated gain the sample can prove is about 10 points or more. The pass mark is 3 [DERIVED from §2.7's own formula].
  - **Fix demanded:** say so in the at-a-glance table.
- **(e) Stage B timing (flagged for review).**
  - The problem:
    - Stage B ends on day 84 at the earliest, or day 98 if Stage A extends. The month-3 stop is day 90.
    - A thermometer-gated champion would still need 21 days of Gate v2.
    - So the thermometer can't affect real money before the stop rule unless Paul extends.
  - **Fix demanded:**
    - state this plainly;
    - keep Stage B as a $0 by-product of B-NULL;
    - give it no extra compute or AI spend.

**PR-6. The week-4 stop almost can't fire. Severity: Medium-High (about 2 months of bills, roughly USD 500, spent on nothing).**
- The stop needs **both** conditions: B-NULL < −10 at all 7 timings, **and** no screen passing.
- But the screens are point estimates on research data, and they take the best of several:
  - idea 1: the best of 4 challengers needs ≥ +1.0;
  - idea 2: the primary or any of 3 variants needs ≥ +1.0.
- A take-profit exit and a no-take-profit exit differ by more than a point in one direction or the other on almost any tape. So "best of 4 ≥ +1" is near-certain whether or not anything can make money. A 1-point improvement on a −15-point baseline is not an edge.
- **Fix demanded** (class (a): it makes a stop easier). A screen passes only if:
  1. the point estimate ≥ the stated screen mark;
  2. the LB > 0 at 80% on research days;
  3. B-NULL at its best tested timing plus the screen's gain > −3 points, which shows a plausible path to profit.

**PR-7. The AI desk's placebo is too weak a yardstick, and its statistics assume independence. Severity: Medium (cost, and a misleading "AI beats random" headline).**
- **(a) Random signs.**
  - The problem: the placebo picks each feature's sign at random, so half its rules point the wrong way. An AI that only learns the sign of an obvious feature (net flow, say) beats it by 15 points without finding any edge.
  - **Fix demanded:**
    - add a **$0 code-search arm**: a greedy best-feature-and-sign search on the same R-half pack, with the same grammar and the same number of rules per night;
    - the desk survives only if it also beats that arm by ≥ 10 points.
- **(b) Near-duplicate rules.**
  - The problem: rules on the same feature at neighbouring deciles succeed or fail together. Fisher's exact test treats all 120 rules as independent. Placebo and AI rules are also scored on the same windows.
  - **Fix demanded:** cluster rules by (feature set, signs), and use a paired permutation test by proposal night, with clusters as units.
- **(c) Timing.**
  - The problem:
    - 60 rules at ≤ 20 per 30 green days, starting on day 14, means the verdict lands around day 118. That is after the month-3 stop (day 90).
    - The first rule's own ticket (+56 days) ends around day 70, so its Gate v2 ends around day 91 or later [DERIVED].
  - **Fix demanded:**
    - state that the desk can't produce a live candidate before the stop;
    - run it at the minimum night rate unless Paul extends the project.
- **(d) Seed re-rolling.**
  - The problem: `rule_version_id` feeds the jitter and drop seeds, so renaming a version re-rolls the luck.
  - **Fix demanded:** the version id is the SHA-256 of the canonical rule text, fixed at registration.

**PR-8. Idea 4 (CHN-A) gives "taint" credit it may not have earned, and its exit test is nearly built in. Severity: Medium.**
- **(a) Wrong yardstick.**
  - The problem: O_n = I0 + I1 but O_t = I0–I3, so the "extra" includes I2 (shared-funder links). Trading apps already show funder clusters [UNVERIFIED; check GMGN and Axiom holder views]. The claimed edge is *following plain transfers* (I3).
  - **Fix demanded:** O_n = I0–I2, so that O_t − O_n is I3 only. Keep I0 + I1 as a reported variant.
- **(b) Condition 3 is nearly circular.**
  - The problem:
    - INSIDER_DUMP is *defined* by insider selling, and EXIT_INSIDER_FLOW *fires* on insider selling. So "fires before the hard stop on ≥ 30%" comes almost for free.
    - The 20% FALSE_EXIT cap is loose: most post-graduation coins fall 30% before they rise 30%, so even random exits rarely count as false.
  - **Fix demanded:**
    - a random-time placebo exit on the same positions, with a matched number of firings;
    - insider-flow FALSE_EXIT rate ≤ the placebo's − 10 points;
    - net points saved against X0 > 0 across all positions, not only the dumps.
- **(c) The holdout is too short.**
  - The problem: the holdout is 7 days, so 28 six-hour blocks. Blocks on the same day move together, which is the very reason day blocks were chosen. So the 98.57% LB is too narrow.
  - **Fix demanded:** every ticket with an LB needs a holdout of ≥ 14 days (day blocks). CHN-A's holdout becomes days 14–27, which also fixes PR-4.

**PR-9. A bootstrap with only 14 day-blocks gives over-confident bounds. Severity: Medium.**
- The problem:
  - A percentile bootstrap with 14 clusters understates the spread (by about √((n−1)/n), worse with skew).
  - It is weakest in exactly the far tails this file uses: 99%, 99.5% and 99.917%.
  - The m-out-of-n check helps with heavy tails, not with small n.
- **Fix demanded:**
  - the reported LB = the smallest of: the percentile LB, the m-out-of-n LB, and a cluster-t LB (day means, t on n − 1 degrees of freedom);
  - any α ≤ 1% needs ≥ 21 blocks.
- **Test before Gate 0→1** (offline, no network): simulate heavy-tailed, day-clustered null data at 14, 21 and 28 blocks, and show the false-pass rate ≤ the stated α for each α used.

**PR-10. Outcome-based "regime changes" can rescue or cancel tickets. Severity: Medium.**
- The problem:
  - The silent-change alarm (B-NULL outside ±2 sd for 3 days) and "a new bot cohort" are triggered by *results*.
  - §12 then scores tickets on the pre-change days only, if their minimums were met, or voids them with α returned.
  - So a bad spell can shield a lucky early result from bad data, or hand out a free re-roll.
- **Fix demanded:**
  - only verifiable on-chain changes can split or void tickets: program upgrades, config or IDL hash changes, the BOOST toggle, new migration or trade instructions, and the slot target;
  - outcome alarms pause paper and live entries and are reported, but tickets keep running over all days;
  - the class of each change is logged within 24 h of its slot.

**PR-11. The crash-chase test (V1) starts with a head start for the chase. Severity: Medium (it could hide a safety problem in the "never give up" sell).**
- The problem:
  - One-shot sells are charged a 1.0% sandwich allowance and the chase 0.2% (S8). That is a built-in 0.8-point lead against a 1.5-point pass mark.
  - The 1.0% is EXE-E2(a)'s *pass threshold*, not a measurement.
- **Fix demanded:**
  - V1 is scored with equal allowances, and the S8 version is shown beside it. The pass needs ≥ +1.5% with equal allowances.
  - Family V gets its own ledger: tickets are registered before data and their α is fixed.
  - State that a V result can never promote a rule or change a trading parameter.

**PR-12. The "common funder" rule (S13) hides the busiest scam crews. Severity: Medium (an unsafe fallback).**
- The problem: a funder that seeds ≥ 50 wallets in 7 days becomes "common" and creates no links. A busy crew that funds many dev and bundle wallets crosses 50 quickly, so the worst actors drop out of I2.
- **Fix demanded:**
  - "common" = on the versioned exchange or service list only;
  - a high-volume funder that isn't on the list is tagged `crew_suspect` and still links, unless its funded coins dump no more often than the population (checked point-in-time);
  - report how many I2 links the rule removes.

**PR-13. Paper exits run on the bot's clock, but real exits run on the guard's feed. Severity: Medium (a seam).**
- The problem: DESIGN §2b-9 gives the exit guard a different data company (Helius). The simulator has a single receive-time clock, the main stream's (A2). So paper exits are as fast as the bot's feed, not the guard's.
- **Fix demanded:**
  - record the guard-feed receive times on test pools from day 1;
  - simulated exits decide on those times;
  - fallback until measured: +2 slots on every exit decision.
- **Related fallback (S1, decision-to-landing delay U{2,3,4}):** this is plausible but optimistic for the path bot → tunnel → guard → KMS → Jito/Sender. Every pass must also hold in the pessimistic view with S1 doubled.

**PR-14. Several fallbacks are optimistic or don't match `docs/fee-model.md`. Severity: Low-Medium.**
- **(a) Sandwich charge.** S8 charges nothing for sandwiches on normal sells and on buys, although the margin m can reach 5%.
  - **Fix:** the pessimistic view charges 0.1 × m on every trade sent outside a bundle, until P14 measures it.
- **(b) Fee fallback. Severity: Medium (a bias, not just caution).** The pre-T6 fallback is defined twice:
  - §2.6 here: max(1.25%, the sum of all recorded rates, *including* buyback, cashback and holder rewards).
  - fee-model §6.2: max(model, 125 bps).
  - Why the sum is wrong:
    - Buyback sits inside the protocol fee (fee-model §2a).
    - On holder-reward coins the creator fee *is* the holder reward ("the creator fee … is set aside for the coin's holders" [VERIFIED-DOC README, Holder Rewards]).
    - So the sum double-counts, and only on some coin types. A filter that merely avoids holder-reward or cashback coins would then look like an edge.
  - **Fix:** use one definition, fee-model's.
- **(c) Tips.** S6 charges no tip on buys and calm sells. The fee model's sender plan pays a 100,000-lamport Jito tip on calm buys (bundle-only needs a tip).
  - **Fix:** use one table, the fee model's §2c, and say which one the simulator loads.
- **(d) Re-quote interval.** S7 = 3 slots; fee-model and DESIGN #9 say every 2 blocks. Keep 3 as the paper value (it is more conservative), and say so in both files.

**PR-15. Clarifications (class (b); no number changes). Severity: Low.**
1. **Supply.**
   - The problem: S(t) = "mint supply minus recorded burns". An SPL or Token-2022 burn already lowers the mint's supply, so reading supply live and also subtracting burns counts them twice. That inflates every overhang. BOOST burns about 3.5% of supply in the fee-model's example [DERIVED from its 964.51M figure].
   - **Fix:** S(t) = the live mint supply at t.
2. **Jitter seed.** "Draws a new J" reuses the same seed string, so the new J equals the old one. Add a counter: `jitter-<n>`.
3. **ARMED.** It must use the coin's own `initial_real_token_reserves` at creation, not today's `Global`, because `set_params` can change it [VERIFIED-DOC pump.json `set_params` args].
4. **"Contested slot"** means HOT. Say so.
5. **Rivals.** These must include PumpSwap trades reached by CPI, including Pump's own `multi_hop_curve_swap` [VERIFIED-DOC pump.json] and third-party routers, not only top-level instructions.
6. **CHN-A decision slot.** Condition 3 uses the tournament entry as s0, not d2. Say so.
7. **Slot timing.** Conditions on P_end(s) can only be known once slot s is complete. Define the decision time as the receipt of the slot's last message plus 50 ms, or evaluate the conditions on running state.

**PR-16. Dropping whole red days may skip the stressful days. Severity: Low-Medium.**
- The problem: feeds degrade under load, which is when crashes and fee wars happen.
- **Fix demanded:**
  - report the red-day share and the mean U0 count on red days against green days;
  - if red days are > 10% of days, or their U0 count is > 1.3 × the green days' count, the gate is marked "stress days missing", and G1 can't be met;
  - trades whose holding window overlaps a stream gap are dropped from the rule and the baselines alike.

**PR-17. Gate v2 doesn't require the constrained bot to make money. Severity: Low.**
- The problem: the constrained bot picks the earliest landings, which may be a systematically different set of trades.
- **Fix demanded:** the constrained bot's base-view point estimate > 0, reported beside the twin's.

**PR-18. The budget ceiling stops the work before the statistics finish. Severity: Low (honesty).**
- The problem: the USD 750 research ceiling is reached around weeks 11–12 (costs.md F8), before day 90. So realistically one Gate v2 attempt finishes, perhaps two.
- **Fix demanded:** add a "will the verdict arrive before the money stop?" column to the at-a-glance table.

**PR-19. The regime rules haven't been tried against Pump's real change history. Severity: Medium.**
- §12 lists "new quote coins" as market structure. Pump's README shows "Depth 2 Pump Coin Quotes" on Oct 13, and at least three changes between Sep 30 and Oct 13 [VERIFIED-DOC README]. v1 rejects non-SOL quotes, yet by §12's wording that change would still have reset every clock.
- At that pace, stop rule 3 ("two resets, then pause") could fire within weeks.
- **Fix demanded** (class (b), added to v1.1):
  - a dry-run table classifying each of the last 6 README changes under §12;
  - the class keyed to whether the change touches U1-PB's trading path (SOL-quoted canonical pools and their rival flow).
  - If the dry run shows more than one market-structure reset per 6 weeks, report it to the lead before day 0.

### Answers on the spots the author flagged
| Flagged spot | Red-team view |
|---|---|
| Reserve tickets as a ledger | Sound bookkeeping. Unsafe without prospective-only holdouts and technical sealing (PR-3), and with α returned after peeking (PR-4) |
| α splits for repeated looks | The F1 split is correct. The Gate v2 repeated *attempts* are the real gap (PR-2) |
| Gate v2 confidence tiers | Tighter than QNT-R, but they allow re-tries of the same version, parallel attempts and the incumbent loophole (PR-2) |
| Missed-coin bar ≤ 1% | The right number, measured wrongly: it needs an independent audit, a daily check and classes (PR-1) |
| New family V | Fine as an idea. It needs a ledger, equal allowances in V1, and a "never promotes a rule" clause (PR-11) |
| Thermometer Stage B timing | Can't reach real money before the month-3 stop. Stage A also has look-ahead and the drawdown path has a loophole (PR-5) |

### Verdict: preregistration
**SIGN OFF WITH FIXES.** The structure is good, and better than most published trading research. But v1.0 has five holes that would let a lucky rule through or hide blind spots (PR-1 to PR-5). Because no data exists yet, the fixes go into **v1.1** with no clock restart. I sign v1.1 once PR-1 to PR-5 are in and PR-6 to PR-17 are either in or answered in writing. PR-9's simulation test must be run (offline) before Gate 0→1.

---

## 2. `docs/fee-model.md` (v1.0)

### What I checked independently, and it holds
- **Pump's SDK source matches.** I downloaded `@pump-fun/pump-swap-sdk` 2.1.0 from `registry.npmjs.org` and read it without running it. The fee model's pseudo-code matches it on four points:
  - rounding: `fee()` rounds up, sell output rounds down, buy input is a ceiling division;
  - the exact-SOL-in "shave", with fees on the pre-shave net and the "− 1";
  - tier selection from **pre-trade** effective reserves and **live** mint supply, with 10¹⁵ for mayhem pools;
  - creator fee = 0 when `coin_creator` is the default key, and the 6063 real-reserve check (`Q_real < q_out − lp`) [VERIFIED-DOC `src/sdk/fees.ts`, `util.ts`, `buy.ts`, `sell.ts`].
- **The tier table matches the chain capture.** I decoded the 4,073-byte mainnet capture in `src/__tests__/feeConfigMainnetFixture.ts` (slot 445186127) myself:
  - flat fees 25/5/0, and 25 tiers;
  - tier 0 = 2/93/30, tier 1 from 420 SOL = 20/5/95, down to tier 24 at 98,240 SOL = 20/5/5, with 28 bps at tier 15;
  - every row matches §2a [VERIFIED-DOC].
- **The layouts match.** Every `Pool` and `GlobalConfig` offset in §4 matches my own offset calculation from `idl/pump_amm.json`. Pool = 287 bytes; `virtual_quote_reserves` i128 @245; `buyback_basis_points` @899; `boost_enabled` @939. The `disable_flags` bits 3 = buy and 4 = sell are in the IDL field docs [VERIFIED-DOC].
- **The worked example recomputes exactly.** My own integer recomputation of §5 at 0.25 SOL gives 599,275,881,600 tokens, gross 245,487,362, received 242,418,768 and a total cost of 7,916,232 lamports = **3.17%**. The 0.1 SOL figure (3.03%) and the 0.5 SOL figure (3.66%) match too [DERIVED].
- **The v2 bookkeeping is consistent.** The vault, `vqr` and bucket update rules (§3) keep effective reserves the same for v1 and v2, which I checked by algebra [DERIVED].

### Findings

**FM-1. "Sell all and close the account in the same transaction" lets anyone make our crash sell fail. Severity: High (live only). Does not block Gate 0→1; it BLOCKS the Phase 3 guard design and the cost assumption.**
- §2d puts the account close inside the final sell, which is why round-trip rent is 0.
- The trap:
  - A PumpSwap sell sells a *fixed* `base_amount_in` [VERIFIED-DOC pump_amm.json args].
  - Anyone can send tokens to any existing token account without permission.
  - Closing an account that isn't empty fails, and the whole transaction is undone [UNVERIFIED for Token-2022 here; standard SPL behaviour, test FM-T1].
  - So 1 raw token of dust sent between building and landing makes the "sell all + close" fail. An attacker watching our wallet can repeat it every 2–3 slots for 5,000 lamports a time. Holder-reward payouts may do the same by accident if they arrive in the coin [UNVERIFIED].
- **Fix demanded:**
  - an emergency or chase sell **never** contains a close;
  - closing is a separate clean-up transaction after we are flat;
  - paper shows the rent as "locked" until that clean-up, which costs one more base fee of 5,000 lamports per trade [DERIVED].
- **Test FM-T1:** find mainnet transactions that failed with a non-zero-balance close error on Token-2022 accounts.

**FM-2. Boosted pools can show a price that sellers can't actually be paid. Severity: Medium-High.**
- How it works:
  - `PoolCannotBoost` ("no virtual reserves") shows that BOOST runs on virtual quote reserves [VERIFIED-DOC pump_amm.json error 6065].
  - Error 6063 says "effective = real + virtual is pricing-only; payout is capped at real_vault" [VERIFIED-DOC].
- If any boost reserve is left after BOOST ends, the quoted price includes SOL that can't be paid out. A crowded exit could then hit 6063 for the last sellers. The "never give up" chase would keep paying fees on sells that are certain to fail.
- §2e marks the boost mechanics [UNVERIFIED: FC7].
- **Fix demanded:**
  1. Add to FC7 a measurement of the boost-reserve share of `Q` at t_bend, t_bend + 900 and t_bend + 9,000, on 100 pools.
  2. The guard checks `Q_real ≥ q_out − lp` *before* sending, and raises a class-A alarm instead of paying for a certain failure.
  3. Risk adds `Q_real ÷ Q` as a skip and exit feature.
  4. The simulator applies 6063 (it already plans to).

**FM-3. T6 tests the amounts but not the fail-or-succeed line, which is what decides whether a sell lands. Severity: Medium. BLOCKS Gate 0→1 (it is part of the T6 definition).**
- Every T6 check is on *successful* trades.
- **Fix demanded:** add a stratum of ≥ 50 failed trades with 6004, 6040 or 6063, and ≥ 50 successful trades whose limit was within 0.5% of the amount actually paid. The model must predict each fail or succeed correctly: 100%.

**FM-4. T6 continuity (P5) skips the hard cases. Severity: Medium. BLOCKS (T6 definition).**
- Many trades share a slot, and rivals use `multi_hop_swap` (also excluded from the gate).
- **Fix demanded:** P5 must include ≥ 50 same-slot pairs ordered by the transaction index, ≥ 30 pairs with a multi-hop trade between them, and ≥ 30 pairs with a `boost_buy_and_burn` between them. Otherwise the "worst position in the block" convention and state rebuilding are never validated.

**FM-5. T6 and Gate 0→1 can deadlock. Severity: Medium (process). BLOCKS (it must be settled before the gate).**
- §7 says a stratum that 14 days of history can't fill "waits for the recorder". But the recorder is Phase 1, which begins only after Gate 0→1, and DESIGN puts T6 in Gate 0→1.
- **Fix demanded:**
  - **T6a** (history, at Gate 0→1) covers the strata history can fill;
  - **T6b** (recorder data) must pass before any holdout day's paper result counts. Prereg G8 already blocks Gate v2 without it.
  - The 500-trade sample is drawn from the independent migration audit of PR-1, not from pools our decoder already recognised.

**FM-6. The "changes without a program upgrade" watch list has gaps. Severity: Medium.**
- These admin instructions exist in today's IDLs and aren't named in §8 [VERIFIED-DOC pump.json, pump_amm.json, pump_fees.json]:
  - **Pump `set_virtual_quote_reserves`.** Changes the curve's starting SOL, so the opening pool size and tier change.
  - **Pump `set_max_curve_depth` and the quote-mint whitelist** (`add_quote_mint`, `remove_quote_mint`, `initialize_quote_control`, `add_quote_control_mint`, `set_quote_control_mint_reserves`). New quote types, and multi-hop rival flow through our SOL pools.
  - **`toggle_create_v2`, `toggle_mayhem_mode`, `set_mayhem_virtual_params`, `update_holder_reward_config`.** Which coin types exist.
  - **`admin_update_token_incentives` (both programs).** Trading rewards invite wash volume; `BuyEvent` carries `track_volume` and `current_sol_volume` [VERIFIED-DOC]. Wash volume distorts NF60, rival counts and the crowding labels. This is a *market-structure* change, not a fee change.
  - **`update_global_authority`, `admin_set_idl_authority`.** Who controls the program and the on-chain IDL.
  - **Not admin instructions, but watch them:** each program's **upgrade authority** (the ProgramData account), and each held coin's **Token-2022 extension data**. An extension authority could switch on a transfer fee or hook mid-hold.
- **Fix demanded:**
  - name these items;
  - define the monitor as "a diff of every byte" of Pump `Global`, PumpSwap `GlobalConfig`, both FeeConfigs, the incentive accounts and the three ProgramData accounts;
  - route incentive changes to prereg §12 as market structure.

**FM-7. The two pre-T6 fee fallbacks disagree. Severity: Medium.** The same problem as PR-14(b): it biases results by coin type. **Fix:** one definition, here, and prereg §2.6 points to it.

**FM-8. The "crash cost" table leaves out the biggest crash cost. Severity: Low-Medium (honesty).**
- §0 and §5 say a crash round trip costs 3.4–6.2% "on top of the market move". But the further fall while the chase runs (arrival delay, plus the margin of up to 15%) is a real execution loss, and it isn't in the table.
- So "crash costs are lower than DESIGN" mustn't be used to loosen anything.
- **Fix:** add the line "excludes chase slippage, which the simulator adds", and report measured chase slippage after V1.

**FM-9. Small definitions. Severity: Low.**
1. **m in whole numbers.** m must be defined in integer basis points (swing2 computed from integers, rounding stated), because "floats never in quoting" otherwise has a gap.
2. **"SOL-like" quotes.** These include the Token-2022 native mint and the default key [VERIFIED-DOC SDK `fees.ts` `SOL_LIKE_QUOTE_MINTS`], but prereg U0 says "wrapped SOL". Make them agree, and list Token-2022-native-quoted pools in the exclusion report.
3. **Priority-fee formula (P6).** It must use the *effective* compute limit when a transaction has no `SetComputeUnitLimit` (the runtime's per-instruction defaults). Many rival transactions omit it.
4. **The 500-trade sample** needs a defined population: all U0 pools in the window, taken from the audit.

### Verdict: fee model
**SIGN OFF WITH FIXES.** The maths is right. I re-derived it from Pump's SDK and the on-chain capture, and it is the strongest of the five documents. Before Gate 0→1, FM-3, FM-4 and FM-5 must be added to the T6 definition, and FM-6 and FM-7 fixed. FM-1 and FM-2 must be closed before any guard code (Phase 3).

## 3. `docs/costs.md`

### What I checked, and it holds
- **Every total adds up** [DERIVED]:
  - Phase 1: 186 / 230 / 513. Phase 2: 191 / 260 / 608. Phase 3: 218 / 295 / 698. Recorder-only: 132 / 171 / 371.
  - The bridge from $295 to $698 is +$403, from eight items (175 + 78 + 15 + 13 + 17 + 45 + 25 + 35).
  - USD 698 × 1.42 = CAD 991. The crossing rate is 1,000 ÷ 698 = 1.433.
  - The tax and card multipliers are 1.05 × 1.025 = 1.076 and 1.15 × 1.025 = 1.179.
- **The break-even table recomputes.** At 0.25 SOL and 10 trades a day: 3.73% + 295 ÷ (300 × $25) = 7.66%, so 7.7%. The SOL $70 / $150 cases give 9.35% / 6.35% [DERIVED].
- Flags F1, F3 and F8 are exactly the right worries, and are honestly stated.

### Findings

**CO-1. Cost per trade disagrees with `docs/fee-model.md`. Severity: Low-Medium.**
- §6 still uses DESIGN's 3.22% / 4.93% and tags Pump's fee VERIFIED-SEARCH. Its new 0.1 SOL row (3.07% / 7.04%) contradicts the fee model's 3.03% / 6.15%.
- Paul is being shown two different numbers.
- **Fix:**
  - quote the fee model's §0 as the exact figures;
  - keep DESIGN's as a labelled "conservative planning envelope";
  - note that chase slippage is not included (FM-8).

**CO-2. The standby's "no public IPv4" low case probably doesn't exist. Severity: Medium.**
- A machine with no public IPv4 address needs one of two things:
  - **a NAT gateway**, at about $0.045–0.052 an hour, so about **$33–38 a month** plus data [VERIFIED-SEARCH cloudburn.io, cloudpipelines.pages.dev]. That is ten times the $3.65 the low case saves;
  - **IPv6-only exit**, which works only if Jito, Helius Sender, the RPCs and KMS all have IPv6 endpoints [UNVERIFIED].
- **Fix:**
  - the low case uses 2 IPv4 addresses (L6 low becomes about $31);
  - add test PX-4b (IPv6 reachability of every endpoint the guard and standby use).

**CO-3. One Anthropic spend limit covers both the safety reader and the optional jobs. Severity: Medium.**
- Labels and the AI desk can use up the Console cap. The rule-change reader then goes silent too, at the very moment Pump changes something.
- Haiku 5.5 has thinking **on by default** [VERIFIED-DOC brief]. So label outputs can be several times the 500 tokens in A-069, and the L7 line may be low.
- **Fix:**
  - separate workspaces or keys, each with its own limit. The change reader gets a small dedicated limit;
  - label calls run with thinking off or at minimal effort;
  - recompute L7 including thinking tokens.

**CO-4. An AWS Budgets *action* could kill selling. Severity: Medium (safety).**
- AWS Budgets can do more than alert: it can apply policies or stop instances [UNVERIFIED in detail; PX-4].
- An auto-stop on the guard or standby would end all selling.
- **Fix:** C-11 states "alert only; no Budgets action may ever be attached to the guard account's compute or KMS". Paul's click-by-click steps must say so.

**CO-5. Recorder-only mode quietly breaks later tests. Severity: Medium.**
- Dropping Helius to its free plan stops or shrinks the `known_at` funding lookups (A14, "can't backfill").
- The stop rule's default lets an idea revive on days 28–83. Ideas that depend on I2 (forensics, the insider ledger, wave Heat) then can't be tested honestly on recorder-only data.
- **Fix:** say which lookups continue in recorder-only mode, and at what credit cost. Otherwise state that I2 ideas can't revive from it.

**CO-6. The recorder-only high case isn't built like the other high cases. Severity: Low.**
- It uses the $48 server, not $126, and does not keep Chainstack Growth.
- **Fix:** itemise it and state the assumption.

**CO-7. Missing or under-sized cost lines. Severity: Medium.**
- **(a) The independent migration audit (PR-1).** Program-account scans or a narrow second stream cost credits.
- **(b) The on-chain tripwire's feed.** A webhook or a third provider. It is unpriced.
- **(c) Research compute bursts.** B-RAND uses 1,000 full re-simulations per gate, and bootstraps up to 120,000 resamples.
- **(d) Archive egress** if we ever need to restore or re-decode.
- **(e) Data volume (A-057) may be 2–3× low.**
  - My rough estimate: 5–15M Pump and PumpSwap transactions a day, including failed ones, at about 4 KB each, is 20–60 GB a day raw, or roughly 4–12 GB a day compressed [UNVERIFIED; settled by C01/D4].
  - On that estimate L5 climbs to about $40–80 by month 3.
- **Fix:** add each line, even at $0 expected with a high, and tie L5 to C01's measured MB per hour.

**CO-8. Review of the proposed budget guard C-12. Severity: Low. Adopt with these conditions:**
1. The projection includes term plans and one-offs.
2. The 90% pause applies **only** to optional research jobs that are billed by usage. It never applies to the recorder, monitors, coverage audits, the change reader, the guard or the standby.
3. CAD uses the day's rate (PX-11) and shows the sticker price and the F2 tax-and-card multiplier side by side.
4. No automatic plan downgrades, ever.

**CO-9. The money stop beats the statistics. Severity: Low (honesty).**
- F8 is right. With the USD 750 ceiling, at most one Gate v2 attempt finishes (see PR-18).
- Paul's Q3 answer decides whether the month-3 checkpoint can ever be reached.
- Put this in plain words at the top of the file.

### Verdict: costs
**SIGN OFF WITH FIXES.** The arithmetic is correct and the flags are honest. Not blocking for Gate 0→1, except that CO-7(e) must be measured (C01/D4) before the recorder's disk is bought. CO-2, CO-3 and CO-4 must be fixed before Phase 3 spending starts.

## 4. `docs/assumption-register.md`

### What holds
- The structure is good: impact, tag, source, "if wrong", the settling test, and the gate.
- Every **High** row is assigned to a gate.
- The rule "weakest part sets the tag" is the right one.

### Findings

**AR-1. Seven High-impact assumptions are missing. Severity: High. BLOCKS Gate 0→1** (the register is a Gate 0→1 deliverable, and the gate table must cover these). Add each row with its test:
1. **Every graduation goes through a migration path our decoder knows, and an independent audit sees the ones it doesn't.**
   - `migrate` and `migrate_v2` both exist [VERIFIED-DOC pump.json].
   - Settled by PR-1's audit. Gate 0→1 (design) and 1→2 (measured).
2. **No unpayable boost reserve remains after BOOST ends** (FM-2). FC7 extension. Gate 2→3.
3. **Dust sent to our token account can't block a sell** (FM-1). FM-T1. Gate 3→4.
4. **BOOST stays switched on through the research window (≥ 8 weeks).**
   - U1-PB and idea 2 depend on it.
   - A-025 and A-026 cover only visibility and amount; DESIGN §3 "what has to be true" #5 has no row.
   - Settled by the `boost_enabled` monitor. Gates 2→3 and 3→4.
5. **Events inside failed transactions are never applied as trades** (TS-6).
   - Whether failed transactions carry inner-instruction events is [UNVERIFIED]. A search didn't settle it [VERIFIED-SEARCH, no answer: docs.metamask.io getTransaction].
   - Test AR-T1. Gate 0→1.
6. **The day-block bootstrap gives honest error rates with 14–28 blocks** (PR-9). Offline simulation. Gate 0→1.
7. **Sealed holdouts stay sealed** (PR-3, TS-1). The access-log audit at each look. Gate 1→2.

**AR-2. Two rows are rated too low. Severity: Medium.**
- **A-057 (data volume) and A-058 (server capacity) are Medium**, but if either is wrong the recorder falls behind or drops raw bytes. That is a blind spot plus lost "can't backfill" data, which is High by the register's own definition.
- **A-057's range (15–135 GB a month) may be 2–3× too low** (CO-7e).
- **Fix:** raise both to High and settle them by C01/D4 at Gate 0→1.

**AR-3. A-002 is worded wrongly, in a High row. Severity: Medium.**
- The problem: "Reserves = vault balance + virtual quote reserves, minus the protocol and creator fees kept in the vault" subtracts the kept fees twice. `virtual_quote_reserves` already nets them out (fee-model §3; PUMP_SWAP_TRADE_V2).
- **Fix:**
  - **pricing reserve** Q = vault + vqr;
  - **payout reserve** Q_real = vault − protocol_fees − creator_fees.
  - A wrong sentence in the register is how a wrong line of code gets written.

**AR-4. Three rows are wrongly tagged. Severity: Low-Medium.**
- **A-008** ("Pump changes about once every 4 weeks") is not VERIFIED-DOC. It is **DERIVED** from a changelog whose two dated entries are 13 days apart, with at least three changes in that span [VERIFIED-DOC README]. The pace may be faster. Link it to prereg stop rule 3 (PR-19).
- **A-018** ("a sell of my current balance limits itself") is tagged VERIFIED-SEARCH "via the execution engineer". A teammate's claim is not a search result. **UNVERIFIED**; test: decode failed sells with an insufficient-balance error. It also depends on FM-1.
- **A-002 / A-005**, after T6a: record which parts are settled by history and which wait for T6b (FM-5).

**AR-5. The counts are out of date. Severity: Low.**
- A-001 and A-077 were upgraded to VERIFIED-DOC today, but §1 still counts them as before.
- My recount:
  - High: VERIFIED-DOC 5 (A-001, A-003, A-004, A-008, A-025), VERIFIED-SEARCH 4;
  - Low: VERIFIED-DOC 2 (A-068, A-077), VERIFIED-SEARCH 13;
  - totals: **8 VERIFIED-DOC, 25 VERIFIED-SEARCH**, 6 DERIVED, 41 UNVERIFIED.
- The plain-English line "only 6 of the 80" should say 8, or 7 once A-008 is re-tagged.

**AR-6. Some Medium and Low rows have no gate. Severity: Low.**
- A-031, A-068, A-069 and A-078 belong at Gate 1→2 (sample schedule, AI cost, funder-lookup credits).
- A-049, A-050 and A-079 belong at Gate 3→4 (separate guard key, autoscale cap, Jito leader share for bundle-only buys).

**AR-7. Smaller wording and scope fixes. Severity: Low.**
- **A-041** covers sandwiches on crash sells only. Extend it to buys and calm sells, where the margin can reach 5% (PR-14a).
- **A-033:** a blockhash expires after about 150 *blocks* (block height), not slots. With skipped slots that is longer in wall time [UNVERIFIED; X3]. Exit-ticket expiry logic should count blocks.

**AR-8. Medium rows to add. Severity: Medium.**
1. Pump's trading-reward programs (`admin_update_token_incentives`; `BuyEvent.track_volume` [VERIFIED-DOC]) don't create enough wash volume to distort flow and crowding features (FM-6).
2. Pump-coin-quoted chains (depth 2) don't push unseen multi-hop flow through our SOL pools (PR-15.5).
3. The Anthropic spend limit is shared between jobs (CO-3).
4. The standby has a way out to the internet without IPv4, at a known cost (CO-2).
5. The archive is write-once and the bot host can't delete it (TS-9).

### Verdict: assumption register
**SIGN OFF WITH FIXES.** AR-1 blocks: the seven missing High rows must be added and gated before Gate 0→1. AR-2 and AR-3 should be fixed at the same time. The rest can follow.

## 5. `docs/tech-stack.md` (PROPOSED)

### What holds
- **Rust for the money maths and the recorder, Python for research only, the TypeScript SDK as a test-only referee.** That is the right split, for the reasons §3 gives.
- Banning `solana-client`, `solana-sdk`, Anchor and `carbon-*` from production is good.
- Dispatching on program first and discriminator second is good. I agree the `buy_v2` collision is real.
- Raw frames kept beside Parquet, re-decoding that never overwrites, the 7-day cooldowns, and fixture-only `make test` are all good.

### Answers to the attacks the author expected (§4, §11)
| # | Expected attack | Red-team view |
|---|---|---|
| §4.1 | Rust slows us down | Accepted, with the fallback. But the fallback (TypeScript recorder) puts npm on a production host, against §0's own rule. It needs security review before use (TS-10) |
| §4.2 | Two fee models | A text scan for "bps" is easy to dodge. Rule: Python never computes `net_i` or any fill. It reads nets that `desk-sim` wrote, checked against the run's output hash (TS-1) |
| §4.3 | Huge Solana dependency trees | Accepted as answered |
| §4.4 | Yellowstone client churn | Partly answered. There is no emergency lane (TS-4) |
| §4.5 | The referee pulls in npm | Accepted, with one addition. `@pump-fun/pump-sdk` drags in `@pump-fun/agent-payments-sdk` (§1), an odd dependency for a quoting library. The referee runs in a throwaway container: network off after install, no secrets, outputs only vector files |
| §4.6 / §11.3 | Same language for guard and seller | Rust is fine. **Spec diversity matters more than language diversity** (TS-7). Go isn't required |
| §4.7 | No 128-bit integers in Parquet | Accepted (STK-2) |
| §4.8 / §11.4 | Research starves the recorder | Only partly. CPU and memory limits don't cover disk input/output (TS-2, TS-11) |
| §11.5 | The Rust 1.100 cooldown setting name | `check_cooldown.py` covers it until then. Accepted |
| §11.6 | Codama's event support | Accepted, test-only |
| §11.7 | `cargo vet` audit sources | Choose them before Phase 3. The guard workspace needs every crate "safe-to-deploy" by a named audit or our own review |

### Findings

**TS-1. Sealing and scoring need code, not good intentions. Severity: High. BLOCKS adoption** (this implements PR-3).
- The problem:
  - Python "may explore freely" over every Parquet partition, including sealed holdouts.
  - The statistics (bootstrap, LB, pass or fail) sit in Python's numpy/scipy, while pass marks are said to come "only through desk-sim". Which program actually decides a pass isn't stated.
- **Fix demanded:**
  1. **One frozen scorer.** A single module computes every ticket verdict, bootstrap included. Its hash goes into the preregistration. It is tested against known-answer cases and PR-9's simulation.
  2. **A sealed-partition guard.** A thin DuckDB/Polars wrapper refuses partitions listed in `sealed.json` unless the scorer calls it at a scheduled look. Every access is logged append-only.
  3. **Python never computes `net_i`.** It reads nets written by `desk-sim`, checked by hash.

**TS-2. A disk flush after every frame can make the recorder fall behind. Severity: Medium-High (a blind spot). BLOCKS adoption.**
- The problem:
  - "Append, fsync" for every frame at firehose rates (thousands of messages a second) on network block storage, where each fsync takes milliseconds [UNVERIFIED], will lag.
  - Yellowstone servers drop slow clients, which makes gaps we can't backfill.
  - STK-1 tests CPU on 1 vCPU, not disk-flush speed on the real volume.
- **Fix demanded:**
  - group commits: fsync every ≤ 50 ms or every ≤ 1 MB, with the most data a crash could lose stated;
  - STK-1 is re-run on the actual disk type and on the busiest hour of the first 7 days, plus a synthetic 10× burst;
  - record the server's flow-control and drop behaviour.

**TS-3. "Every byte is decoded" needs one more rule. Severity: Medium.**
- The monitors' silent-feed probe is right. It must compare in near real time against an independent count, for example a once-a-minute signature count for the PumpSwap program from another provider. Comparing only against our own decoder isn't enough.
- **Fix:** state it, together with PR-1's audit.

**TS-4. There is no emergency path when the gRPC client must change now. Severity: Medium.**
- The problem: major versions went from 13 to 17 in six weeks. If Chainstack changes its server and our pinned client breaks, a 7-day cooldown plus monthly upgrades means about a week blind, with data we can't backfill.
- **Fix demanded:**
  - a written fast lane for the recorder's client crate, mirroring SEC-5:
    - exact version;
    - full diff review;
    - replay and reconnect tests passing;
    - red-team sign-off within 24 h;
  - meanwhile a second recorder on the previous provider (Solana Tracker trial) or the TS-10 fallback.

**TS-5. Check the IDL against a second source. Severity: Low.** The pinned GitHub IDLs are the only source. Anchor programs can also store their IDL on chain. Compare its hash with the GitHub copy in Phase 0 (a second witness for A-005); `admin_set_idl_authority` exists [VERIFIED-DOC pump.json]. Then watch both.

**TS-6. Events inside failed transactions must never become trades. Severity: High (bad data). BLOCKS adoption.**
- The problem:
  - Decoders read events from inner instructions. Whether failed transactions carry inner instructions in their metadata is [UNVERIFIED].
  - If they do, an attacker can make a real CPI trade, fail the transaction on purpose, and leave a perfect-looking `BuyEvent` behind. Fake prices for any decoder that doesn't check `meta.err`.
  - Failed transactions are recorded on purpose (rival bids, losers' tape), so they are in our tape.
- **Fix demanded:**
  - a decoder rule: events from a failed transaction are tagged `FAILED_TX_EVENT` and never change state, price, holdings or labels;
  - a hostile fixture with a failed transaction containing a full `BuyEvent`;
  - test AR-T1.

**TS-7. The safe-mode seller needs a different *method*, not just different code. Severity: Medium.** (This answers the §5j question.)
- The problem: "byte-identical sell instructions" and "min-outs within 1 lamport" force the seller to re-implement the full fee model. If the specification (IDL, fee tiers, golden vectors) is wrong, both are wrong together. Differential tests catch only where two implementations drift apart.
- **Fix demanded:**
  1. The seller computes a *conservative* min-out from the constant-product maths, minus a fixed fee ceiling (for example 3% per side, or the maximum row of the live FeeConfig), minus its margin. It never uses tier logic.
  2. The differential test becomes "seller min-out ≤ guard min-out, and both ≤ what the chain actually paid out" (from T6 data).
  3. The seller reads pool state from a different provider than the guard.
  4. It uses blocking input/output with minimal dependencies (no shared async or TLS stack versions with the guard, where practical).
- **Verdict:** Rust is acceptable. Go is not required, and it would bring `solana-go` (a single main maintainer [UNVERIFIED]) into the guard account.

**TS-8. Build scripts run code, and the AI desk key sits with research. Severity: Medium-High (supply chain). BLOCKS adoption.**
- **(a) Builds.**
  - The problem: build scripts and macros run at compile time. Builds must not happen on any host that holds secrets: the bot host keeps the provider API keys and, later, the tunnel credentials.
  - **Fix:** build in a secret-free environment, record binary hashes (`cargo auditable` ✓), and have the bot host run only prebuilt, hash-checked binaries.
- **(b) The AI desk key.**
  - The problem: §9 says the Python research user has "no access to any secret". But the AI desk and the change reader need the Anthropic key.
  - **Fix:**
    - run the desk as its own user with its own minimal environment (`anthropic` plus the standard library only, with no polars, duckdb or scipy);
    - give it its own key and spend limit (CO-3).
- **(c) Small fix:** `pyarrow 26.0.x` isn't an exact pin.

**TS-9. The archive must be impossible to delete from the bot host. Severity: Medium.**
- The problem: the recorded history is the project's one asset that can't be replaced. If the bot host's object-storage credentials can delete or overwrite, a hacked host or a bad script wipes it.
- **Fix:**
  - put-only credentials;
  - provider-side versioning or object lock;
  - a monthly restore test.

**TS-10. The TypeScript recorder fallback needs its own review. Severity: Low.** It would put npm and native add-ons on a production host. If it is triggered, it runs as its own user with no secrets other than the stream key, under the strict pnpm settings in §9, after a security and red-team review.

**TS-11. Research reads can starve the recorder's disk. Severity: Low-Medium.**
- The problem: CPU and memory limits don't cover disk input/output.
- **Fix:**
  - Parquet and research reads live on a different volume from the recorder's raw segments;
  - give research a low cgroup io weight;
  - an alarm on recorder fsync latency.

**TS-12. Receive times need a disciplined clock. Severity: Low.** Replays order everything by our receive time. Run chrony, put the measured clock offset into control frames, and order by the monotonic clock within a connection.

### Verdict: tech stack
**SIGN OFF WITH FIXES.** The language split and the storage choice are right, and better argued than most. **Before it is adopted:** TS-1, TS-2, TS-6 and TS-8. TS-7 sets the conditions for the Phase 3 seller.

## What Gate 0→1 now needs from this review (checklist for the lead)
1. **Preregistration v1.1** with PR-1 to PR-5 in it. PR-6 to PR-19 either in it or answered in writing. A new SHA-256, pushed to GitHub, with the hash copied into Paul's daily summary (PR-3.3).
2. **The T6 definition** extended by FM-3 and FM-4, and split into T6a and T6b (FM-5).
3. **The assumption register** with AR-1's seven High rows added and gated.
4. **Two offline simulations** run and reported. Neither needs the network:
   - PR-9: false-pass rate of the bootstrap at 14, 21 and 28 day-blocks;
   - PR-2: share of null champions reaching Gate 3→4 by day 90.
5. **The tech stack** adopted only with TS-1, TS-2, TS-6 and TS-8 in it.
6. **Red-team re-check** of the revised files. I will mark each finding fixed, partly fixed or open.

## Tests to run once allowed (all read-only; none signs, sends or simulates a transaction)
| # | Test | Expected result → what we do | Domain(s) |
|---|---|---|---|
| AR-T1 | `getTransaction` on 20 failed PumpSwap and Pump trades: does `meta.innerInstructions` contain event self-calls? | If yes, TS-6's rule is mandatory and the hostile fixture uses a real example. If no, keep the rule anyway (cheap) | `api.mainnet-beta.solana.com` or `mainnet.helius-rpc.com` |
| FM-T1 | Find failed transactions whose close-account step failed because the account still held tokens, on Token-2022 accounts; confirm the whole transaction was undone | Confirms FM-1 → no close inside any sell | same RPC hosts |
| FM-T2 (FC7 extension) | On 100 boosted pools: the boost-reserve part of `virtual_quote_reserves` and `Q_real ÷ Q` at t_bend, t_bend + 900 and t_bend + 9,000 | If a reserve remains after BOOST, risk adds a `Q_real ÷ Q` skip and exit | Chainstack gRPC host; RPC hosts |
| PR-T1 | Independent migration audit: list PumpSwap-owned accounts with the `Pool` discriminator created over 24 h (from a provider other than the main stream), plus bonding curves that turned `complete`; diff with U0 | Measures MISSED_COIN and its classes (PR-1). Also measures the credit cost (CO-7a) | `mainnet.helius-rpc.com`, `api.mainnet-beta.solana.com` |
| PR-T2 | Check whether GMGN and Axiom holder views already show funder clusters (I2-like) | Sets the right yardstick for CHN-A (PR-8a) | `gmgn.ai`, `axiom.trade` |
| CO-T1 (PX-4b) | IPv6 reachability (AAAA records and a TLS handshake over IPv6) of the Jito block engine, Helius Sender, the RPC providers and AWS KMS in eu-central-1 | Decides whether the standby can run without IPv4 (CO-2) | Jito block-engine host, Helius Sender host, `kms.eu-central-1.amazonaws.com` (exact hostnames from execution) |
| CO-T2 (= C01/D4) | 24 h of firehose capture: MB per hour raw and compressed, including the busiest hour | Settles A-057 and the L5 line (CO-7e, AR-2) | Chainstack gRPC host |
| TS-T1 (STK-1 extended) | Recorder throughput with group-commit fsync on the real block-storage type, on the busiest captured hour plus a synthetic 10× burst | No lag over 1 slot at p99 (TS-2) | Chainstack gRPC host, then offline |
| TS-T2 | Read Pump's on-chain Anchor IDL accounts and compare their hashes with the GitHub IDLs | A second witness for A-005 (TS-5) | RPC hosts |
| PR-T3 (offline) | The PR-9 bootstrap simulation and the PR-2 null-champion simulation | Must show false-pass rates ≤ the stated α | none |

## Sources
- [VERIFIED-DOC] Pump public docs, fetched 2026-11-05 through the shell from `raw.githubusercontent.com`:
  - https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md
  - https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
  - https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json (instructions incl. `migrate`, `migrate_v2`, `multi_hop_curve_swap`, `set_params`, `set_virtual_quote_reserves`, `set_max_curve_depth`, quote-mint control)
  - https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (BuyEvent/SellEvent fields, errors 6063/6065/6077/6079/6080, `Pool` and `GlobalConfig` layouts, `disable_flags` bits)
  - https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_fees.json
- [VERIFIED-DOC] Pump's SDK, read only (never run): https://registry.npmjs.org/@pump-fun/pump-swap-sdk/-/pump-swap-sdk-2.1.0.tgz. Files: `src/sdk/fees.ts`, `util.ts`, `buy.ts`, `sell.ts`, `src/__tests__/boost.spec.ts`, `src/__tests__/feeConfigMainnetFixture.ts` (decoded independently).
- [VERIFIED-SEARCH] NAT gateway pricing: https://cloudburn.io/blog/aws-nat-gateway-pricing ; https://cloudpipelines.pages.dev/guides/aws-nat-gateway-pricing-2026/
- [VERIFIED-SEARCH, inconclusive] Failed transactions' inner instructions: https://docs.metamask.io/services/reference/solana/json-rpc-methods/gettransaction.md ; https://solana.com/docs/core/transactions/transaction-introspection
- Team files: `DESIGN.md`; `team-debate/round3/rulings.md` §4b–4c; the five reviewed documents.
- Web searches used: 2 of the allowed ~6.
