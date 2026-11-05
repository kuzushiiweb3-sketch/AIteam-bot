# Pre-registration v1.0: labels, kill tests, pass marks and trial families (FROZEN 2026-11-05)

## In plain English (for Paul)
- This file says, **before any data exists**, exactly how every idea will be judged. It defines what counts as a "dump", a "rug" or a "crowded entry", the number each idea must reach to pass, the number that kills it, how many coins and days it needs, and which days stay locked away for the final check.
- Writing it first stops us fooling ourselves, because we can't move the goalposts after seeing the results. A later change may only make a test **harder**. Any other change counts as a brand-new test that needs brand-new data.
- It also fixes the stop rules (week 4 and month 3), the rule for whether we ever race other bots, the "crowding" rule that sends us back to paper, and the placebo test that switches off the AI research desk if its ideas do no better than random ones.
- Nothing in this file trades. It is a rulebook for honest scoring. Expect most ideas to fail it; that is what it is for.

**At a glance: what each top idea must show** (the details are in §8).

| Idea | Passes if… | Dies if… | Earliest verdict |
|---|---|---|---|
| 1. Exit tournament | A rival exit set beats today's exits by **≥ 2 points per trade** on locked weeks | No rival exit set beats today's exits by even 1 point | Day 42 |
| 2. "Sellers exhausted" entry | It beats today's entry and buy-every-graduate by **≥ 3 points per trade** after all costs, and isn't crowded | It is under +1 point at 2,000 graduates, or the entry moment is crowded | Day 28 (final by day 42) |
| 3. Market thermometer | Good and bad 6-hour spells persist, and trading only in warm spells adds ≥ 3 points per trade or cuts the worst fall by ≥ 25% | The spells don't persist (correlation under 0.10) | Screen day 28, verdict about day 84 |
| 4. Following insider tokens | It finds hidden insider holdings and predicts insider dumps better | Under 10% of dumped tokens moved by plain transfer | Day 14 |
| 5. Copycat-wave position | Hot waves beat cold ones by ≥ 8 points, or leaders dump ≥ 8 points less than copies | Both gaps under 4 points, or they point the wrong way | Day 28 |

---

## 1. Status and how to read this file

| Item | Value |
|---|---|
| Version | **v1.0** |
| Frozen | **2026-11-05 (UTC)**, by quant-tester, in Phase 0 |
| Data that existed when this was written | **None.** Phase 1 recording has not started, and the shell network in this environment is blocked |
| Proof of the freeze date | The git commit that first adds this file. At Gate 0 → 1 the lead architect records that commit hash and this file's SHA-256 in `phase0/results.md` |
| Red-team sign-off | Pending. It is part of the Gate 0 → 1 review. Red-team may tighten anything (§15); it may not loosen anything |
| Precedence | On *how tests are scored*, this file overrides DESIGN.md and the round files. Where it is stricter than DESIGN.md or the rulings, the text says **TIGHTER**. It never loosens them |
| Inputs | DESIGN.md §3, §7, §8; `team-debate/round3/rulings.md` §4, R5, C12, C15; QNT-R, RSK-R, CHN-R, DAT-R, EXE-R, SOC-R and AI-R (the `team-debate/round2/*-response.md` files); RT-R (`red-team-recheck.md`) |

**Tags.**
- [VERIFIED-DOC]: primary source read this session. This session I re-downloaded `idl/pump_amm.json`, `idl/pump.json`, `README.md` and `docs/SYNTHETIC_MIGRATION.md` from `raw.githubusercontent.com/pump-fun/pump-public-docs/main/`.
- [VERIFIED-SEARCH]: seen in search results, cited through the round files.
- [UNVERIFIED]: an inference, with the test that settles it.
- [DERIVED]: arithmetic.
- **[FROZEN]**: a choice this file fixes. It is not a fact about the world.
- **[NEW]**: a detail that the design or the rulings left open, fixed here for the first time.

**Naming clash.** "F1–F6" are the trial *families* (rulings §4b). Chain-forensics' Phase 0 test F1 is always written **"test F1 (forensics)"**.

**Words used below.** A *ticket* is one pre-registered hypothesis test. *α* (alpha) is the false-pass risk we allow that ticket. A *holdout* is data kept locked until the test's scheduled look. A *look* is the moment a test is scored. *LB* is the one-sided lower confidence bound.

---

## 2. Shared machinery (frozen; every test uses it)

### 2.1 Clock, days and data health
- **Every window is counted in slots**, at the fixed conversion **1 s = 5 slots** [FROZEN]. That is Solana's 200 ms target [VERIFIED-SEARCH solanacompass, via rulings C8]. About 218 ms per slot has been measured, so "60 min" (18,000 slots) is really about 65 minutes of wall time. The conversion is never changed after the fact.
  - Slot distance is the difference of slot numbers, with skipped slots included.
  - If the network changes its slot target, that counts as a market-structure change (§12).
- **Conversions used in this file:**

  | Seconds | 10 | 20 | 30 | 60 | 70 | 120 | 180 | 300 | 330 | 600 | 900 | 1,800 | 3,600 | 6 h | 14,400 (240 min) |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | Slots | 50 | 100 | 150 | 300 | 350 | 600 | 900 | 1,500 | 1,650 | 3,000 | 4,500 | 9,000 | 18,000 | 108,000 | 72,000 |

- **Day:** a UTC calendar day, taken from the block time of the decision slot.
- **Green day:** a recorded day that meets all three of these:
  1. coverage ≥ 99.5% (§3.6);
  2. total stream gap ≤ 60 s;
  3. two-witness mismatches < 0.1% of trades.

  Any other day is a **red day**. Red days are excluded from every test and every minimum sample.
- **Green days are numbered 0, 1, 2, …** in order. "Day 0" is the first green day of Phase 1 recording. **Every "day N" in this file means green day N.**
- **Pool-day exclusion.** A pool with a reserve-continuity break on a day is dropped for that day, from the rule and from the baselines alike. **If more than 2% of a test's coins are excluded for data health, the test cannot pass at that look.** It may still be killed, or it waits for cleaner data where this file allows waiting.

### 2.2 The universe of coins
- **U0, a canonical SOL graduate.** The coin must have all four of these:
  1. a `CreateEvent` from the Pump program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`;
  2. a `CompleteEvent` for its bonding curve;
  3. a `CompletePumpAmmMigrationEvent` and a PumpSwap (`pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`) `CreatePoolEvent` whose `pool` equals the canonical pool address derived from Pump's published seeds;
  4. `quote_mint` = wrapped SOL and `is_mayhem_mode` = false.

  [VERIFIED-DOC: program IDs, event and field names, pump.json / pump_amm.json]
- **Graduation slot g:** the slot of that `CreatePoolEvent`. That is when the pool opens. Under synthetic migration the pool opens "at the price where the [completing] buy stopped" [VERIFIED-DOC SYNTHETIC_MIGRATION.md]. Every pool-side measure starts from that state.
- **HARD_SAFE:** mint authority null and freeze authority null at creation (test T1), plus the canonical pool above. LP burn (test T4) and the Token-2022 extension list (test T1) are recorded, but they don't exclude any coin until those tests set the rule (§16).
- **U1 = U0 ∩ HARD_SAFE.** The rules, the null and the random baseline all draw from U1.
- **U1-PB** (the main research universe): U1 coins with BOOST_SEEN that reach BOOST_OVER (§3.1).
- **NB group:** U1 coins labelled NO_BOOST. This group is paper-only and reported separately. It is never pooled with U1-PB (rulings R5.5).
- **Cashback and holder-reward coins** are included and flagged (`is_cashback_coin`, `is_holder_reward`).
- **Dead and rugged coins are always included.** No coin is ever removed because of its outcome.
- **Rejected in v1 and counted in the exclusion report:** non-SOL quotes, Mayhem coins and non-canonical pools.

### 2.3 Price
- **Effective quote reserve:** Q_eff = the pool's quote-vault amount + `Pool.virtual_quote_reserves`, read as a **signed** value [VERIFIED-DOC README, "Negative Virtual Quote Reserves"].
- **Base reserve:** B = the pool's base-vault amount.
- **Price:** P = Q_eff ÷ B (SOL per token, decimals applied).
- **P_end(s)** is the price after the last *successful* transaction in slot s, in block order. Failed transactions never move the price.
- **Two witnesses.**
  1. The vault post-token-balances.
  2. The reserves carried by the event.

  Whether event reserves are taken before or after the trade is test PR3. Until PR3 is run, witness 1 is the one used. A mismatch excludes that pool-day.

### 2.4 What we knew at the time (no look-ahead)
1. **Replays order every message by our recorded local receive time**, not by slot. A condition becomes true at the message that makes it true. The decision time is that message's receive time plus the engine latency (fallback **50 ms**; S2 in §16).
2. **Forensic links count only from their recorded `known_at` time.** Examples are funding lookups and taint.
3. **Histories use only coins whose 60-minute window ended before the decision.** These are the hold-time book, the wave history, creator history and the thermometer.
4. **Distribution-based thresholds use only earlier data.** These are the deciles and medians, over the trailing windows named where each is used.
5. **A transaction seen at "processed" that is later dropped by a fork stays in the replay** at the time we saw it, because we would have seen it. It is excluded from outcome prices.
6. **Labels may use hindsight; features may not.**
7. **Sealed results.** A ticket's metric on its holdout days is computed only at its scheduled look. Before then, dashboards and Paul's daily summary show only:
   - baselines;
   - the paper incumbent;
   - data health;
   - tickets that have finished.

   Shadow rules whose tickets are still open stay hidden.

### 2.5 Paper fills (the simulator, from QNT-R §1a)
- **Earliest arrival** = decision slot + d.
  - Fallback until test T7/D6: **d uniform on {2, 3, 4} slots when the decision slot is calm, and on {4, …, 10} when it is hot** (S1).
  - **Hot** means **≥ 3 rival same-direction transactions** (K = 3), landed or failed, in this pool in that slot.
- **Rival:** any landed or failed transaction that calls a PumpSwap trade instruction on this pool, excluding our own and BOOST's `boost_buy_and_burn`. The trade instructions are `buy`, `buy_v2`, `buy_exact_quote_in`, `buy_exact_quote_in_v2`, `sell`, `sell_v2`, and `multi_hop_swap` with this pool in its route [VERIFIED-DOC pump_amm.json].
- **Seat rule:**
  - In a calm slot we land, unless a seeded residual drop of **10%** hits us (S3; only the canary can replace this value).
  - In a contested slot we land only if our bid beats the threshold for the view (table below). A bid is the lamports paid above the base fee: priority fee plus tip.
  - If we lose, we retry in the next slot at a fresh price.
- **Position in the block:** after every same-direction trade in that slot and before every opposite-direction trade. This is the worst case, and it is used in the base and pessimistic views.
- **Price limits:**
  - **Buys:** max-in = quote × (1 + m), with m = clamp(2 × swing2, 1%, 5%). Here swing2 = |P_end(s) ÷ P_end(s − 2) − 1|.
  - **Sells:** min-out = latest quote × (1 − m). Normal m = clamp(2 × swing2, 1%, 5%). **Emergency** m = clamp(3 × swing2, 3%, 15%). An emergency is a hard stop, sell pressure, insider flow, or a FAST_DUMP in progress.
  - When a limit breaks, the transaction fails. It still pays its base and priority fees.
  - Sells re-quote every **3 slots** (S7) and never give up. A 30% cumulative chase is only an alert.
- **Patience on buys:** 10 slots after the earliest arrival. After that the coin is logged as **MISSED_AUCTION**, together with what that coin did next.
- **Bid fallbacks** (S6, until execution's sender policy is frozen in `docs/fee-model.md`):

  | Order | Priority fee | Tip | Cap |
  |---|---|---|---|
  | Buy, or a calm sell | The p75 priority fee per compute unit of this pool's landed same-direction transactions over the last 150 slots | None | 0.0005 SOL in total |
  | Emergency sell | The p90 of the same | 0.001 SOL | 0.002 SOL priority |

  The 0.001 SOL tip is Helius Sender's minimum [VERIFIED-SEARCH, via RSK-R].
- **Three views:**

  | View | To land in a contested slot | Extra rule | Use |
  |---|---|---|---|
  | Optimistic | Beat the lowest winning bid; placed by bid | | Shown only; never decides anything |
  | **Base** | Beat the median winning bid; worst position | | **The number every pass mark uses** |
  | **Pessimistic** | Beat the top winning bid; worst position | A buy is counted as missed if there are **≥ 5 rival buys in slots L−1…L+1** | Must stay **> 0** wherever this file says so |

- **Jitter:** every simulated entry (rules and baselines) waits a seeded **J ∈ {0, …, 15} slots** after its trigger. It then re-checks the condition. If the condition is still true it sends; if not, it waits for the next true slot and draws a new J (rulings R5.1).
- **Seeds** (so replays reproduce exactly): SHA-256 of the UTF-8 string `"<rule_version_id>|<mint>|<purpose>"`. The first 8 bytes are read as a big-endian unsigned integer. Purposes are `jitter`, `drop`, `rand-<i>` and `tiebreak`.

### 2.6 Costs and the net result of a trade
- **Stake:** **0.25 SOL** for every research test and every paper result [FROZEN, the live floor]. A 0.5 SOL row is reported for information only.
- **Net result of trade i:** **net_i = 100 × (S_i − B_i − N_i) ÷ B_i**, in "points" (percentage points of the stake). Its parts:
  - **B_i:** the SOL paid into the buy, including every Pump fee as charged.
  - **S_i:** the SOL received from all sells, after Pump fees.
  - **N_i:** base, priority and tip fees for every attempt (landed, or landed but failed), plus the sandwich allowance, plus any token-account rent not recovered. Rent is assumed recovered, because the last sell closes the account (RSK-R). One permanent wrapped-SOL account is assumed, so wrapped-SOL costs 0 (RSK-R).
- **Pump fee:** until T6 passes, the fallback is the higher of 1.25% per side [VERIFIED-SEARCH, 3 sources via rulings §6b] and the sum of every fee rate recorded on the latest same-direction trade in that pool. The recorded rates are `lp`, `protocol`, `coin_creator`, `buyback`, `cashback` and `holder_rewards` bps [VERIFIED-DOC pump_amm.json]. Until T6 passes, results carry the label "fee model unproven" (S4).
- **Sandwich allowance:** **0.2%** of position value on every emergency sell (S8, rulings §6b).
- **Mean net per trade:** the plain average of net_i. Every pass mark uses it **after per-trade costs only** (the *trade bar*).
- **Desk bar** (bills included; reported at Gate v2, required at Gate 4 → 5):
  - Bills are **USD 250 a month** in Phases 1–2 and **USD 275** from Phase 3 [DERIVED, rulings R6].
  - They are shared over the *constrained* bot's trades that month, at the day's SOL/USD, against a 0.25 SOL stake.

### 2.7 Statistics toolkit
- **Block:** one green UTC day if the holdout has ≥ 14 days. Otherwise a 6-hour block (00, 06, 12 and 18 UTC), and then the holdout needs **≥ 28 blocks**. Trades on the same day move together, which is why whole days are resampled (QNT-4).
- **Bootstrap:** a percentile block bootstrap.
  - Resamples: B = max(10,000, ⌈100 ÷ α⌉).
  - Seed: the string `"20261105|<test id>"`.
  - The mean is computed as the ratio of sums (Σ net ÷ Σ trades over the resampled blocks).
  - Comparisons of two rules resample the same blocks for both.
  - Paired tests (same coin, same entry) resample blocks of per-coin differences.
- **Heavy-tail check** (an "m-out-of-n" re-draw, QNT-R §1b): draw m = ⌈n^(2/3)⌉ blocks, where n is the number of blocks.
  - T* = √m · (θ*_m − θ̂).
  - LB_m = θ̂ − Q_{1−α}(T*) ÷ √n.
  - **The reported LB is the smaller of the ordinary LB and LB_m.**
- **"A beats B by ≥ X at confidence 1 − α"** always means **two things together:** the point estimate of (A − B) ≥ X, **and** the LB at that confidence > 0.
- **"Holds in both halves":** split the holdout days in order (an odd middle day goes to the second half). The point estimate must have the required sign in each half.
- **Several conditions that must all hold:** each is tested at the ticket's full α. No split is needed, because all of them must pass together. **A pass that can come through either of two paths:** the ticket's α is split equally between the paths.
- **Inconclusive means not passed.** A test is never extended unless this file names the extension. A retest is a new version: a new ticket on fresh data (§15).
- **Prediction tests (AUC):**
  - Model: logistic regression with an L2 penalty, C = 1.0, and no tuning.
  - Features are rank-transformed using research-period quantiles. A missing value becomes the research median plus a "missing" flag. Constant features are dropped.
  - The model is fitted once, on research data. ΔAUC is measured on the holdout.
  - The LB comes from the block bootstrap of holdout coins, with the fitted models held fixed.
  - **BASE-F**, the $0 baseline feature set: f01, f03, f05, f06, f10, f13 and f15 (Appendix B).
- **Correlations:** Spearman (rank) correlation.
- **Smallest provable edge:** every result also reports (z_{1−α} + 0.84) × sd ÷ √n. That is the edge the sample could detect 80% of the time (QNT-R §1c).

---

## 3. Labels (frozen; changing one creates a new version and costs a ticket)
Notation:
- s0 = the decision slot; P0 = P_end(s0).
- The **outcome window** is (s0, s0 + 18,000].
- **P_low** is the lowest P_end in the outcome window, and **t_low** is the first slot where it occurs.

### 3.1 Coin and BOOST labels
| Label | Exact computation |
|---|---|
| `GRADUATE` | The coin is in U0 (§2.2) |
| `BOOST_SEEN` | An `InitBoostEvent` or a `BoostBuyAndBurnEvent` for this pool [VERIFIED-DOC event names] occurs within **600 slots of g** (S9) |
| `NO_BOOST` | U1 coin and not BOOST_SEEN. `can_boost` is ignored until test PR1 confirms what it means (S10) |
| `BOOST_OVER(t)` | BOOST_SEEN **and** either (a) the latest `BoostBuyAndBurnEvent` for the pool at or before t has `boost_vault_remaining` = 0, or (b) no BOOST event for the pool in [t − 150, t] while t ≥ (first BOOST event slot + 150). This is the "vault at 0, or no BOOST event for 30 s" rule (rulings §4c) |
| `t_bend` | The first slot at which BOOST_OVER becomes true |
| `ARMED` | The first slot where curve progress, 1 − `real_token_reserves` ÷ `Global.initial_real_token_reserves`, reaches ≥ 50%, or completion if that comes first [NEW; FROZEN as the snapshot point for tests] |
| `HARD_SAFE` | See §2.2 |

### 3.2 Outcome labels (rulings §4a, made exact)
| Label | Exact computation | Used by |
|---|---|---|
| **`DUMP60`** | Let t_dn = the first slot with P_end ≤ 0.5 × P0, and t_up = the first slot with P_end ≥ 1.5 × P0, both in the outcome window. DUMP60 = 1 if t_dn exists **and** (t_up doesn't exist **or** t_dn comes before t_up). If both fall in the same slot, block order decides; if block order is unknown, it counts as a dump [FROZEN] | Wave test, vetoes, AI labels |
| **`INSIDER_DUMP`** | DUMP60 = 1 **and** the insider share of selling ≥ 0.40. Insider share = (SOL from `SellEvent.quote_amount_out` on this pool by wallets in the insider set **as it stood at s0**) ÷ (all `quote_amount_out` on this pool), over (s0, t_low]. Wallets tainted after s0 don't count (a report-only variant counts them) | CHN-A, RSK-E1 |
| **`RUG`** | P_low ≤ 0.2 × P0, **and** some slot a in (s0, t_low] has P_end(a − 1) − P_end(a + 2) ≥ 0.5 × (P0 − P_low). That is, half the drop happens inside 3 slots | Stop calibration, gap study |
| **`FAST_DUMP` (decision form)** | Some t in (s0, s0 + 300] has P_end(t) ≤ 0.7 × P0 | Exit-warning tests (DAT-E3) |
| **`FAST_DUMP` (event form)** | During a held position: the first slot r where P_end(r) ≤ 0.7 × max{P_end(u) : u ∈ [r − 300, r]}. The crash starts at the slot of that maximum. One event per position | Crash replays (V1), RC2 |
| `TAIL_WIN` | A closed trade with net ≥ **+100 points** (the stake at least doubled after costs) [NEW; FROZEN] | C12 tail rule, Gate v2 |
| `FALSE_EXIT` | An exit fires at slot f, price P_f. It is false if, within (f, f + 18,000], the price reaches ≥ 1.3 × P_f **before** it reaches ≤ 0.7 × P_f | CHN-A condition 3, DAT-E3 |
| `R30` | The net result of a 0.25 SOL null entry at N-PB (§4.1) sold by one normal chase sell starting exactly 9,000 slots after the entry landed, with no other exits (base view) | Wave test |

### 3.3 Wallet sets and holdings
- **Holdings.** A wallet's holding is the sum of its token accounts for the mint, by owner, from post-token-balances.
  - Not counted: the pool base vault, the bonding-curve token account, burned tokens and the Mayhem vault.
  - Any other program-owned account is logged as `UNCLASSIFIED_PDA` and not counted.
  - **Supply S(t)** = mint supply minus recorded burns (S11).
- **Plain transfer.** In a successful transaction with **no** Pump or PumpSwap trade instruction for this mint, an owner's balance of the mint falls and another owner's rises. Every such receiver joins the sender's set at that slot. Program-owned receivers never join; they are logged.
- **INSIDER SET v1** (CHN-R §1a). Each member carries a join slot and the reason it joined.

  | Part | Who |
  |---|---|
  | **I0** | The create signer (`CreateEvent.user`) and the `creator` field |
  | **I1** | Every wallet with a successful curve buy (`TradeEvent.is_buy` = true) in creation slot c to c + 2 |
  | **I2** | A *material* wallet that shares a direct funder with an I0 or I1 wallet, or that funded, or was funded by, I0. Its join time is the lookup's `known_at` |
  | **I3** | Taint: any wallet that received the mint by plain transfer from I0–I3, over any number of hops |

  Notes on I2:
  - *Material* wallets are the top 25 holders at the ARMED snapshot plus all I1 wallets.
  - A wallet's *funder* is the sender of the first SOL it ever received.
  - A **common funder** never creates a link. A funder is common if it is on the versioned common-funder list, **or** it funded ≥ 50 distinct wallets in our lookups over the previous 7 green days (S13).
  - If test F1 (forensics) drops taint, the set becomes I0–I2 (S17).
- **Overhang.**
  - Naive overhang O_n(t) = holdings of I0 + I1 ÷ S(t).
  - **Tainted overhang O_t(t)** = holdings of I0–I3 ÷ S(t).
- **FAST GROUP F(t)** (DAT-R E1). Members are:
  - the completing buyer (`CompleteEvent.user`, plus `PostCompleteBuyEvent.user` if present);
  - every wallet with a successful pool buy in slots [g, g + 3], excluding BOOST;
  - every wallet that received the mint from F by plain transfer (any hops), joining at the transfer slot.
- **The "sellers" set U(t) = F(t) ∪ insider set(t).**
  - H_U(t) = total holdings of U at the end of slot t, counting membership as of t.
  - **Peak_U(t) = the maximum of H_U(u) for u in [g, t].**
  - Transfers inside the set don't change H_U.
- **FLIPPER** (for variant 1 of the entry family). Hold-time book, built walk-forward:
  - For wallet w and a finished coin c, hold(w, c) = (the first slot where w's balance of c is ≤ 50% of its peak) − (w's first buy slot). If that never happens within 18,000 slots of g, hold(w, c) counts as ≥ 18,000.
  - A **flipper** is a wallet with a median hold < 1,500 slots over ≥ 5 finished coins.
  - **Flipper overhang FO(t)** = holdings of (flippers ∪ pool buyers in [g, g + 3] ∪ the completing buyer).

### 3.4 Entry-moment labels (rulings R5, made exact)
Here T is a rule's trigger slot (its first-true slot) and L is the simulated landing slot.

| Label | Exact computation |
|---|---|
| `CALM` / `HOT` slot | HOT if there are ≥ 3 rival same-direction transactions in the pool in that slot |
| Baseline rate λ | Rival **buys** (landed + failed, excluding BOOST and ours) in this pool over (T − 350, T − 50], divided by 300 slots |
| Baseline fee f0 | The median priority fee per compute unit of those rival buys. If there were fewer than 3, f0 is the median over all recorded Pump/PumpSwap landed transactions in the same window. If that is 0 too, the fee condition below is false |
| **`CROWDED_ENTRY`** | With R5 = rival buys in [L − 2, L + 2]: R5 ≥ max(3, 3 × λ × 5), **or** (R5 ≥ 2 **and** the median rival priority fee per compute unit in [L − 2, L + 2] ≥ 3 × f0). The "R5 ≥ 2" floor on the fee leg is [NEW; FROZEN] |
| **`ARRIVAL_PENALTY`** | Our execution price ÷ P_end(T − 50) − 1. The execution price is the pool-side quote in, excluding Pump fees, divided by the tokens received |
| `time_to_entry` | L − T, in slots (reported) |

### 3.5 Waves (SOC-E1 + AI-E1, code-only version v1)
- **norm(s):** apply Unicode NFKC, lower-case, then keep only Unicode letter characters. Digits, spaces, punctuation and emoji are removed.
- **Match:** two launches match if norm(ticker) is equal with length ≥ 2, **or** norm(name) is equal with length ≥ 3 [FROZEN; fuzzy and embedding matching is a separate, reserve-ticket variant].
- **The wave W(c, s)** of coin c at decision slot s: every launch that matches c and was created between (c's creation − 108,000 slots) and s, with c itself included.
- **Rank:** 1 + the number of members created before c.
- **Size:** |W|.
- **Heat(c, s):** the number of distinct funders behind the creators of the members created in [s − 18,000, s].
  - A creator with no known funder (`known_at` ≤ s) counts as its own funder.
  - Creators that share a known funder count once.
- **Leader:** rank 1–2 in a wave of size ≥ 3. **Follower:** rank ≥ 4 in a wave of size ≥ 3.
- **Growth:** (launches in the last 18,000 slots + 1) ÷ ((launches in the 90,000 slots before that) ÷ 5 + 1).
- **Prior graduates:** the count and mean R30 of the wave's earlier U1-PB members whose R30 was finished before s.

### 3.6 Health and operations labels
| Label | Exact computation |
|---|---|
| Coverage | Daily audit: `getSignaturesForAddress` on 20 random pools plus every held pool, across the four audit keys. Coverage = audit signatures the recorder also holds ÷ audit signatures. Green requires ≥ 99.5% |
| Per-pool completeness | Pool-days with no reserve-continuity break ÷ all pool-days. Required ≥ 99.5% |
| `MISSED_COIN` | A U0 graduate in the migration audit that the live engine didn't register within **150 slots** of g. The rate is missed ÷ audited |
| `MISSED_AUCTION` | A qualifying entry that didn't fill within its patience window (reported, never hidden) |
| Quiet / busy week | Let M = the median daily U0 count over all green days to date. A run of 7 consecutive green days is **quiet** if its mean daily count ≤ 0.85 × M, and **busy** if it is ≥ 1.15 × M [NEW; FROZEN] |
| Regime id | The tuple (Pump program deploy slot, PumpSwap deploy slot, IDL hash, FeeConfig hash, `boost_enabled`). A new tuple starts a new regime, classified in §12 |
| Mint-hash half | Take SHA-256 of the UTF-8 base58 mint string. **R-half** (research) if the first byte is < 128, otherwise **C-half** (check) |

---

## 4. Entries and exits used by the tests

### 4.1 Entries
- **E_inc, the incumbent and paper default** (RSK-R; rulings §4c):
  - trigger at the first slot t ≥ t_bend + 900 where **NF60(t) ≥ −2%**;
  - NF60(t) = (Σ `quote_amount_in` of buys − Σ `quote_amount_out` of sells over (t − 300, t], all wallets) ÷ Q_eff(t);
  - then jitter, then send;
  - **timeout:** no trigger by t_bend + 9,000 means `SKIP entry_timeout` [NEW; FROZEN].
- **N-PB, the post-BOOST null timing:** buy at t_bend + 900, plus jitter, with no condition.
- **N_D, the null "at the same timing" as a rule:** buy at t_bend + D, where D is the median of (rule trigger − t_bend) over the rule's fit sample, fixed when the fit ends.
- **Lateness points** (for the race study, §11):
  - landing at g + {0, 1, 2, 3, 5, 8, 10, 15, 20} slots;
  - g + {150, 300, 600, 1,500, 1,650, 3,000, 4,500};
  - **EVT**, the first slot after t_bend where NF60 > 0.

### 4.2 Exit sets (the five tournament contestants)
**Order of priority when several exits fire:** hard stop > sell pressure > insider flow > trailing stop > time exits > take-profit. "Entry" means our execution price.

| Set | Rules |
|---|---|
| **X0, the incumbent** | **Hard stop:** sell all when P ≤ entry × (1 − h). h = 0.35 until the gap study sets h* (S12); acts at once. **Trailing stop:** arms at P ≥ 1.25 × entry and trails 20% below the peak, tightening to 15% once the peak is ≥ 2.5 × entry. It fires on 2 consecutive slots with a trade whose P_end is at or below the trail. **Dead coin:** at entry + 4,500 slots, if |P ÷ entry − 1| < 10% and pool volume over the last 1,500 slots < 2% of Q_eff, sell all. **Max hold:** sell all at entry + 72,000 slots. **`EXIT_SELL_PRESSURE`:** sell all when net SOL outflow ≥ 6% of Q_eff within a rolling 100 slots and the top 3 sellers supply ≥ 60% of gross SOL sold in that window. No take-profit below 0.5 SOL (rulings C6) |
| **X1** | X0 + **one take-profit step:** sell 50% the first time P ≥ 1.5 × entry |
| **X2** | X0 + **sell into a buy burst:** sell 50% once, in the slot after a slot whose rival buy SOL ≥ 1.5% of Q_eff (at that slot's start), provided P ≥ 1.10 × entry |
| **X3** | X0 + **insider exits:** `EXIT_INSIDER_FLOW` sells all when the insider set's holdings fall by ≥ 3% of supply within a rolling 600 slots, **or** fall to ≤ 70% of their level at entry. `WARN_INSIDER_TRANSFER` (an insider plain-transfers to a wallet outside the set) tightens the trail to 10%, arming it at once from the current price if it isn't armed yet |
| **X4** | X0 + **too long in loss:** sell all if P ≤ 0.90 × entry continuously for 3,000 slots |

**Gap study (sets h*).** On day 14, using days 0–13: h* is whichever of {20%, 35%, 50%} gives B-NULL (N-PB entries, X0) the highest mean net per trade in the base view. If two are within 0.5 points, the tighter stop wins.
- Tests whose holdout starts on or after day 14 use h*.
- Tests whose holdout starts before day 14 use h = 35%.

---

## 5. Baselines (every report shows all of them, after all costs)
| Baseline | Exact definition |
|---|---|
| **B-NULL: buy every graduate after BOOST** | Every U1-PB coin, 0.25 SOL at N-PB, X0 exits, all three fill views. Also reported for every lateness point and at N_D |
| B-NULL-T (time exit only) | The same entries, sold at entry + 9,000 slots with no other exit. This separates the entry effect from the exit effect (RSK-R) |
| **B-RAND: random** | 1,000 draws. Each draw takes, per green day, the same number of trades as the rule, chosen uniformly without replacement from that day's U1-PB coins (seed `rand-<i>`). Each random trade enters at t_bend + a delay drawn from the rule's same-day delays, and uses the rule's exits. **A rule must beat the draws' 90th-percentile mean** |
| **B-ZERO: do nothing** | 0 points per trade on the trade bar. On the desk bar, minus the bills |
| NB group | B-NULL computed on NO_BOOST coins, at g + 1,500 + 900 slots. Reported only |

---

## 6. Data calendar: which days are research and which are locked holdout
Any day not listed as a test's holdout is research data for that test. Whatever a test has used as holdout is spent for its family (§7).

| Test | Research (fit or screen) days | Locked holdout days | Look(s) | Minimum sample (holdout unless stated) |
|---|---|---|---|---|
| Lateness curve + race memo (F6) | — | 0–20 | Day 21, or the first later day the minimums are met (cap day 41) | ≥ 14 days, ≥ 1,000 U0, ≥ 300 U1-PB |
| Gap study (sets h*) | 0–13 | — | Day 14 | — |
| Test F1 (forensics) | 0–13 | — | Day 14, or once 200 INSIDER_DUMP coins exist (cap day 27) | ≥ 200 INSIDER_DUMP |
| Idea 4, CHN-A (F4) | 0–6 | 7–13 | Day 14 (extended equally until ≥ 1,000 U1-PB in total; cap day 27) | ≥ 1,000 graduates, ≥ 14 days, ≥ 100 INSIDER_DUMP in the holdout |
| Idea 2, entry family (F1) | 0–13 (fit; also the screen) | 14 onward | Days 28, 35 and 42 | Fit ≥ 300 U1-PB (if short, the fit and all looks shift later); holdout ≥ 300 / 1,000 / 2,000 U1-PB at the three looks |
| Idea 5, waves (F4) | 0–6 (AUC training only) | Gaps: 0–27. AUC: 7–13, 14–20, 21–27 | Day 28 | ≥ 1,000 U1-PB, ≥ 100 leaders, ≥ 100 followers |
| Idea 1, exit tournament (F2) | 0–27 | 28–41 | Day 42 (extended day by day to ≥ 2,000 paired coins; cap day 83) | ≥ 14 days, ≥ 2,000 paired coins; ≥ 500 per coin type |
| Crash-chase sub-test (V1) | — | 0–41 | Day 42 | 200 FAST_DUMP events (one per coin) |
| Idea 3, thermometer Stage A (F3) | 0–27 (0–41 if inconclusive) | — | Day 28 (or 42) | ≥ 100 usable block pairs |
| Idea 3, thermometer Stage B (F3) | — | The 56 green days after Stage A ends | At the end | ≥ 200 champion trades |
| AI desk rules (F5) | R-half, every day up to the night of the proposal | C-half, the green days after each proposal | Each rule at +14 days (desk score) and +56 days (its own ticket); the desk verdict at 60 + 60 rules | §14 |
| Gate v2 | — | Forward paper after the champion's version freeze | The first day its minimums are met (one look per attempt) | §9 |

**Week 4 = day 28.** **Month 3 = day 90**, or calendar day 105 after Day 0 if that comes first.

---

## 7. Trial families and error budgets (rulings §4b, with one-sided α)
| Family | Ticket | α | Confidence | Notes |
|---|---|---|---|---|
| **F1 Entry** | Primary rule | 5%, split over the looks as 1% / 1.5% / 2.5% | 99% / 98.5% / 97.5% per look | **TIGHTER:** the looks are split (rulings: 95% once) |
| | Variant 1 (flipper clock), Variant 2 (Rule C), Variant 3 (auction cooled) | 1.667% each, split 0.333% / 0.5% / 0.833% | 99.67% / 99.5% / 99.17% | |
| **F2 Exits** | Best challenger vs X0 | 5% | 95% | One look |
| | Per-type promotion, T-low (O_t at entry < 5%) and T-high (≥ 5%) | 2.5% each | 97.5% | O_t is replaced by I0–I2 overhang if taint is dropped |
| **F3 Regime** | Thermometer Stage B | 10%, split **5% for the expectancy path + 5% for the drawdown path** | 95% each | **TIGHTER** (rulings: one path at 90%), because a pass can come from either path |
| **F4 Filters and features** | 7 tickets: CHN-A taint, CHN-B crew, waves, KOL bait, losers' tape, RSK-E1 as a filter, X spread shape | 1.4286% each | 98.57% | The wave ticket splits 0.714% per path |
| **F5 AI desk** | Each AI rule entering shadow (≤ 60 per 90 green days) | 0.0833% | 99.917% | The desk's existence is decided by §14 (Fisher one-sided p < 0.05) |
| **F6 Race reopen** | 1 | 5% | 95% | Plus C15's conditions (§11) |
| **V Validations** [NEW] | V1 crash chase | 5% | 95% | Doesn't promote a trading rule, so it doesn't share an edge budget |
| **Gate v2** | Each champion attempt | Attempt k = 1–3: 10%; k = 4–10: 5%; k > 10: 1%. A champion without a passed research ticket starts one tier stricter | 90% / 95% / 99% | **TIGHTER** than QNT-R's 20/50 tiers. k counts every attempt since 2026-11-05 |

**The ledger rule** (this settles how "reserve tickets come from the family's budget" works):
1. Each family has one ledger per **family window**. A window is ≥ 28 green days that no earlier test of that family used as holdout.
2. A ticket's α is fixed when it is registered, before any of its holdout is read. **The registered α in one window may never add up to more than the family's budget.**
3. Named tickets are registered now, at the values above. A **reserve ticket** (2 per family per window) takes the family's smallest named share. It may be registered only if the ledger has room, either because a named ticket in that window was retired unrun or was never scheduled there. Otherwise it waits for a fresh window.
4. A ticket that is retired before its holdout is read returns its α to the ledger.
5. Holdout data a family has used is spent for that family. Other families may still use the same days.
6. A rule must pass **three independent stages:** its research ticket, then Gate v2 on forward paper, then the canary (Phase 4, with Paul's OK).

---

## 8. The top-5 edge tests
Every test uses U1-PB coins, 0.25 SOL stakes, the base view and per-trade costs, unless it says otherwise. "Kill" ends the idea. "Not passed" (between pass and kill) means no promotion, and a retest is a new version on fresh data.

### 8.1 Idea 1: Exit tournament (family F2), rated STRONG
- **Hypothesis.** On identical entries, at least one challenger (X1–X4) earns a higher mean net per trade than X0.
- **Rule.** Every U1-PB coin gets one simulated entry at N-PB. All five exit sets (§4.2) run on **the same entry fill**, so the comparison is paired. A coin whose entry misses its auction is dropped from all five equally.
- **Primary metric.** d = net(Xk) − net(X0) per coin, averaged over coins.
- **Selection** (research days 0–27 only):
  - the overall best challenger is the one with the highest point estimate of d;
  - the best challenger for T-low and for T-high is chosen separately, the same way.
- **Pass, main ticket** (α 5%), on holdout days 28–41. All of these:
  - the selected challenger beats X0 by **≥ 2.0 points at 95%**;
  - the pessimistic-view d > 0;
  - **mean d with the top 5% of d values removed ≥ 0** (a hard condition for exits, C12);
  - it holds in both halves.
- **Pass, per-type tickets** (α 2.5% each): the same conditions on that type's holdout coins (≥ 500 paired coins).
- **Kill.** Every challenger's point d on the holdout is < +1.0. X0 then stays the exit, and the tournament ends as an edge claim.
- **Minimum sample.** ≥ 2,000 paired coins in research and ≥ 2,000 in a holdout of ≥ 14 days. The holdout is extended day by day if short (cap day 83). Below 1,000 at the cap, the test cannot pass.
- **Week-4 screen.** On days 0–27, the best challenger's point d ≥ +1.0.
- **Crash-chase sub-test V1** (family V, α 5%; EXE-E2):
  - **Sample:** the first 200 FAST_DUMP events (one per coin) on X0 tournament positions, days 0–41.
  - **Compared:** the chase (§2.5) against one-shot sells at 20% and at 30% slippage. A one-shot that fails is resent every 3 slots at the same tolerance.
  - **One-shot cost:** a one-shot sell pays a sandwich allowance of **1.0%** (S8, from EXE-E2(a)'s pass threshold, until P14 measures it).
  - **Metric:** median of (chase proceeds − the better one-shot's proceeds) ÷ the position value at the crash start, after attempt fees.
  - **Pass:** median ≥ +1.5% and LB > 0 at 95%.
  - **Kill (of the exit edge claim):** median < 0. The chase stays as the safety design whatever happens. A kill only removes the edge claim and sends execution to re-tune the emergency margin, retested on 200 fresh events.

### 8.2 Idea 2: "Sellers exhausted" entry family (family F1), rated PLAUSIBLE, highest priority
- **Hypothesis.** Entering after BOOST, once the fast group and the insiders have sold ≥ 75% of their peak holdings, earns more per trade than E_inc and than the null at the same timing.
- **Primary challenger, E_pri** (DAT-E1 + CHN-C + QNT-E2):
  - trigger at the first t ≥ t_bend where **H_U(t) ≤ 0.25 × Peak_U(t)**;
  - if Peak_U(t) < 2% of S(t), the condition counts as met [NEW; FROZEN degenerate case];
  - then jitter; timeout at t_bend + 9,000.
- **Variants** (same jitter and timeout; each is its own ticket):
  1. **Flipper clock (QNT-E2):** BOOST_OVER and FO(t) ≤ 0.20 × max FO over [g, t], with the same 2% floor. The hold-time book is walk-forward from day 0.
  2. **Rule C (CHN-C, without "held through BOOST"):** BOOST_OVER, and O_t(t) < 3%, and the minimum P_end over [g, t] occurred at or before t − 150, and **organic** net flow over (t − 300, t] > 0. Organic means wallets outside I0–I3 and outside F.
  3. **Auction cooled (EXE-E1):** BOOST_OVER, and over (t − 10, t] there is ≤ 1 failed rival buy, and the largest priority fee per compute unit of this pool's landed transactions is ≤ the p75 across all recorded Pump/PumpSwap landed transactions over (t − 1,500, t]. This uses priority fees instead of tips, because tips are captured only near migrations (NEW-16).
- **Fit.** Days 0–13 (≥ 300 U1-PB coins). The fit only fixes D for N_D. Every threshold is already frozen above.
- **Primary metric.** The rule's mean net per trade, against E_inc and against N_D.
- **Pass** (at each look, at that look's α). **All** of these:
  1. the rule beats **E_inc by ≥ 3.0 points** and beats **N_D by ≥ 3.0 points** (§2.7 convention: point estimate plus LB > 0);
  2. the rule's own LB > 0;
  3. the pessimistic-view mean > 0;
  4. there are ≥ 20 TAIL_WINs, and the mean with the top 3 trades removed is ≥ 0 (C12, the entry version);
  5. it qualifies on ≥ 5 entries per green day **or** on ≥ 30% of U1-PB coins;
  6. the crowding check passes over the holdout entries: with ≥ 50 entries, CROWDED share ≤ 30% **and** median ARRIVAL_PENALTY ≤ 1.5%;
  7. excluded coins ≤ 2%.
- **Kill.**
  - At look 3, (rule − E_inc) < +1.0 point.
  - **Early futility:** at look 2, (rule − E_inc) ≤ 0.
  - At any look, the crowding condition fails with ≥ 50 entries (CROWDED > 30% or penalty > 1.5%).
- **Minimum sample.** Looks happen at day 28 (≥ 300 holdout U1-PB coins), day 35 (≥ 1,000) and day 42 (≥ 2,000). If a count is short on that day, the look moves to the first day the count is met. Every look needs ≥ 14 holdout days.
- **Insider set used:** I0–I3, or I0–I2 if test F1 (forensics) drops taint. Test F1 resolves before day 14.
- **Week-4 screen.** On fit days 0–13, the primary or any variant has a point estimate of (rule − E_inc) ≥ +1.0 and qualifies under condition 5, **and** look 1 didn't kill it.

### 8.3 Idea 3: Market thermometer (family F3), rated PLAUSIBLE
- **Hypothesis.** Post-BOOST graduates have good and bad spells that persist from one 6-hour block to the next. Trading only in warm spells raises the mean net per trade, or lowers the worst drawdown.
- **Stage A, the screen** (days 0–27).
  - **Blocks:** 6-hour blocks (00, 06, 12 and 18 UTC). r_b = the mean net of B-NULL trades decided in block b. A block is usable if it has ≥ 10 such trades.
  - **Metric:** ρ1 = the Spearman correlation of r_b with r_{b+1}, over consecutive usable pairs (≥ 100 pairs).
  - **Pass:** ρ1 ≥ 0.25. **Kill:** ρ1 < 0.10.
  - **In between, or fewer than 100 pairs:** extend once to days 0–41, then pass at ≥ 0.25 or kill.
- **Temperature, frozen.**
  - Temp(t) = the mean net of B-NULL trades **whose exits completed** in (t − 108,000, t].
  - **Warm(t)** = Temp(t) ≥ the median of hourly Temp samples over the trailing 14 green days.
  - If there are fewer than 10 such trades, or less than 14 days of history, Warm = true (neutral, meaning trade as usual).
- **Stage B, the ticket.** It uses the 56 green days after Stage A ends.
  - The champion is the current paper champion. If none has passed, it is E_inc + X0.
  - "Gated" means the champion's entries are taken only when Warm(T).
  - **Expectancy path** (α 5%): gated beats ungated by **≥ 3.0 points per trade at 95%**.
  - **Drawdown path** (α 5%), on the constrained bot (25 SOL notional, live caps; §9 G6). All three:
    - DD_gated ≤ 0.75 × DD_ungated (point estimate);
    - total P&L gated ≥ total P&L ungated (point estimate);
    - the 95% upper bound of DD_gated ÷ DD_ungated < 1.0, from a moving-block bootstrap with 3-day blocks.
  - **Yardsticks:** whichever path passes must also beat two free gates on the same metric (point estimate):
    - (a) warm when U0 graduations in the trailing 6 h are ≥ their trailing 14-day hourly median;
    - (b) warm when SOL/USD now is ≥ SOL/USD 24 h ago.
- **Kill.** The Stage A kill, or neither path passing at the end of Stage B.
- **Minimum sample.** Stage A: ≥ 100 usable block pairs. Stage B: 56 green days and ≥ 200 champion trades. If Stage A runs to day 41, Stage B ends after month 3 and so can only finish if the stop rule (§13) doesn't fire first.
- **Week-4 screen.** Stage A passes on days 0–27.
- **Side use:** the silent-change alarm (§12).

### 8.4 Idea 4: Taint-tracked insider overhang, CHN-A (family F4), rated PLAUSIBLE
- **Hypothesis.** Following insider tokens through plain transfers finds holdings that snapshot views miss. That extra holding predicts insider dumps and gives earlier exits.
- **Decision slot.** d2 = g + 1,500. d1 = g is reported only.
- **Early kill, test F1 (forensics),** on ≥ 200 INSIDER_DUMP coins from days 0–13. Compute (tokens sold by I3 wallets) ÷ (tokens sold by I0–I3 wallets) over (s0, t_low], pooled across coins. **If this is < 10%, taint is dropped**: the ticket is retired unrun, its α goes back to the ledger, and the insider set becomes I0–I2 everywhere (S17).
- **Pass** (α 1.4286%). All three on the holdout days 7–13:
  1. **Extra holding:** O_t(d2) − O_n(d2) ≥ 3 points of supply on ≥ 15% of U1-PB coins.
  2. **Better prediction:** for INSIDER_DUMP at d2, **ΔAUC = AUC(BASE-F + O_t + (O_t − O_n)) − AUC(BASE-F) ≥ 0.03**, with LB > 0 at 98.57%. The models are fitted on days 0–6, and the holdout uses 6-hour blocks.
  3. **Earlier exits:** on the X3 tournament positions on the holdout days, `EXIT_INSIDER_FLOW` fires before X0's hard stop (or fires when the hard stop never does) on ≥ 30% of the INSIDER_DUMP positions. At most 20% of its firings are FALSE_EXIT. This needs ≥ 100 INSIDER_DUMP positions.
- **Kill.** Test F1's early kill, or any of conditions 1–3 failing at the look.
- **Minimum sample.** ≥ 1,000 U1-PB coins over ≥ 14 days, split equally between research and holdout. If short, both halves extend equally (cap day 27).
- **Week-4 screen.** The full test passes.

### 8.5 Idea 5: Theme-wave position (family F4), rated PLAUSIBLE, code-only
- **Hypothesis.** A graduate's place in its copycat wave predicts its 30-minute return, or its dump risk.
- **Decision slot.** N-PB. The features come from §3.5.
- **Path A** (α 0.714%):
  - rank U1-PB coins by Heat at the decision (ties broken by wave size, then by seed `tiebreak`);
  - **the hottest third beats the coldest third by ≥ 8.0 points in mean R30**, with LB > 0 at 99.29%;
  - it holds in both halves (days 0–13 and 14–27).
- **Path B** (α 0.714%):
  - in waves of size ≥ 3, **the followers' DUMP60 rate minus the leaders' rate ≥ 8.0 points**, with LB > 0 at 99.29%;
  - it holds in both halves.
- **Prediction condition** (required with either path):
  - wave features are Heat, size, rank, growth, prior-graduate count and prior-graduate mean R30;
  - **ΔAUC(BASE-F + wave features vs BASE-F) ≥ 0.02 on DUMP60, in ≥ 2 of the 3 walk-forward test weeks;**
  - the weeks are trained on days 0–6 and tested on 7–13; trained on 0–13 and tested on 14–20; trained on 0–20 and tested on 21–27.
- **Kill.** Both gaps (A and B) < 4.0 points, **or** either gap points the wrong way: Path A gap < 0, or followers dumping less than leaders.
- **Minimum sample.** ≥ 1,000 U1-PB coins over ≥ 14 days (we use 28, **TIGHTER**), and ≥ 100 leaders and ≥ 100 followers.
- **Claude labels add-on.** This is a reserve F4 ticket, run only if the wave ticket passes. On the next fresh F4 window, Haiku labels must add **≥ 0.01 AUC** over the free version, with LB > 0. If they don't, Haiku is never used for waves.
- **Week-4 screen.** The full test passes on day 28.

---

## 9. Gate v2: paper → canary (exactly; every item is required)
**Data used:**
- **The twin:** the champion's frozen version on forward paper, after its freeze time. The unconstrained twin takes every qualifying entry.
- **The constrained bot:** it applies the live caps on a 25 SOL notional bankroll:
  - 0.25 SOL bets;
  - ≤ 3 open positions and ≤ 3% exposure;
  - a buy cap of 10% per rolling 24 h;
  - a daily loss limit of 6%;
  - a drawdown stop at 20%.

  When too many entries arrive, the earliest landing wins.

| # | Condition |
|---|---|
| G1 Sample | The twin has ≥ 200 closed trades over ≥ 21 green days. The constrained bot has ≥ 50 closed trades (**TIGHTER**). The period contains one quiet and one busy week (§3.6). If both haven't appeared after 42 days, the replacement condition is: a positive point-estimate mean in both the lower and the upper half of days ranked by U0 count |
| G2 Expectancy | The twin's mean net per trade (base view) has **LB > 0** at the attempt's confidence (§7: 90% / 95% / 99%) |
| G3 Pessimistic | The twin's mean net in the pessimistic view is > 0 |
| G4 Baselines | The twin's mean is > B-NULL at N_D on the same days (D = the twin's median delay), > the 90th percentile of B-RAND, and > 0 |
| G5 Luck | The mean with the top 3 trades removed is ≥ 0. If the mean with the top 5% removed is < 0, the rule is *tail-dependent*. It then needs ≥ 20 TAIL_WINs, and its tail-win rate must lie inside the 90% interval of its research-stage rate. For a filter or exit change, the top-5%-removed mean must be ≥ 0 (C12) |
| G6 Drawdown | The constrained bot's maximum drawdown is < 20% of the notional, or Paul's own limit if he sets a lower one |
| G7 Consistency | (a) Replaying the same days from the archive gives the same enter-or-skip decision on ≥ 97% of U1-PB coins, and the mean nets differ by ≤ 1.0 point. (b) The twin's mean lies inside the two-sided 90% interval of the rule's research-holdout estimate. For the incumbent, that is its replay on the 28 green days before the gate. Below the interval fails. Above it puts the gate on hold until red-team writes an explanation |
| G8 Data health | Every day counted is green. Coverage ≥ 99.5%. Per-pool completeness ≥ 99.5%. **MISSED_COIN rate ≤ 1%** (**TIGHTER** than 5%). Two-witness mismatches < 0.1%, each explained. No open class-A alarm. **T6 passed** (if not, the gate cannot pass) |
| G9 Crowding | Over the period (≥ 50 twin entries): CROWDED share ≤ 30% and median ARRIVAL_PENALTY ≤ 1.5%, and the rolling kill (§10) never fired |
| G10 Regimes | Trade counts are shown per regime. If the period spans more than one regime, the newest has ≥ 50 twin trades and a positive base-view point estimate. A regime with < 50 trades can never pass on its own |
| G11 Ruin | The clustered ruin simulation (NEW-13) resamples whole recorded days. The chance of a 50% fall within 300 trades at the configured bet must be ≤ 1%. If it isn't, the limits are tightened and G6 is re-checked |

- **One look per attempt.** The look happens on the first day G1 is met. A failed attempt spends its data. A re-attempt needs ≥ 21 *new* green days, and k goes up by 1.
- **The desk bar** (mean net after the bills share, at the constrained count) is reported at Gate v2. It is required at Gate 4 → 5.
- **Outside Gate v2:** Gate 3 → 4 also needs the drills, the reviewed signing code and **Paul's explicit written OK** (DESIGN.md §7). Those are not covered here.

---

## 10. The crowding kill rule (rulings R5; frozen)
- **Scope:** every entry rule, in research, paper, canary and live.
- **Entries counted:**
  - in research and paper, the twin's entries;
  - in canary or live, the real entries, or the twin's if there are fewer than 50 real ones.
- **Measure:** CROWDED_ENTRY and ARRIVAL_PENALTY (§3.4), on every entry.
- **Kill:** over any rolling 14 green days with ≥ 50 entries, **CROWDED share > 30%, or median ARRIVAL_PENALTY > 1.5%**. Then:
  - in paper, the rule fails its gate;
  - in canary or live, it goes back to paper at once;
  - in research, the ticket is killed.
- **Early warning:** a CROWDED share ≥ 20% goes into Paul's daily summary.
- **Checked:** daily, after the UTC day closes.
- **Coming back** after a crowding kill needs a new version (new ticket, fresh data). There is no automatic return.

---

## 11. The race / no-race decision rule (QNT-R §2 + rulings C15; family F6)
- **Data:** the lateness curve (§4.1 points), on days 0–20. It needs ≥ 1,000 U0 coins, ≥ 300 U1-PB coins and ≥ 14 days.
  - Each point simulates a 0.25 SOL buy landing at that slot, in the worst position, starting after any synthetic-migration buyer.
  - Each runs under three exit rules: H5 (hold 1,500 slots), H30 (hold 9,000 slots) and X0 (h = 35%).
  - The results are paired by coin.
- **Seat price s_k:** the p75 winning bid (priority fee + tip, where captured) among landed buys at slot g + k, for k = 0–5.
- **Assumptions until measured:**
  - k_ours = **3 slots** (S18; replaced by the T7/D6 median);
  - k_race = **1 slot** (an assumption; it can't be measured without racing);
  - racing cost = **USD 2,000 a month** over 300 constrained trades (S19).
- **G** = net(k_race) − net(k_ours) − s_{k_race} ÷ stake − (racing cost per trade ÷ stake), in points.
- **RACE only if all six hold:**
  1. G > 0 with LB > 0 at **95%** (X0 exits).
  2. Entry at k_race is profitable on its own in the pessimistic view (point estimate > 0).
  3. G > 0 (point estimate) in both halves of the days and under ≥ 2 of the 3 exit rules.
  4. G stays > 0 when counting only coins where our *capped* bid would have won that slot. Coins we would have lost can't rescue it.
  5. G stays > 0 with the top 5% of trades removed (C15).
  6. **Paul explicitly OKs a separate racing wallet** (a local key, 1–2 bets, treated as already lost; Q12 default "never").
- **RACE-LITE:** condition 1 fails, but net(slot 3) − net(slot 10) ≥ 3.0 points (point estimate, X0 exits, both halves). Only cheap speed is then allowed (≤ USD 25 a month, no change to keys).
- **DON'T RACE** in every other case. This is the default. The shadow racer keeps logging.
- **Reopening** needs a fresh F6 window (≥ 28 new green days), at most once per window.
- **The memo goes to the lead and Paul on day 21**, or on the first later day the minimums are met.

---

## 12. Regime changes and clock resets (QNT-R §1d, made exact)
| Class | Examples | Effect |
|---|---|---|
| Decoding only | New instruction names with the same economics, new event fields that stay at 0 | No reset. Paper counts again only after the new decoder matches 500 post-change trades exactly (the T6 method) |
| Fee or parameter | Fee tiers, protocol fee, BOOST size | Re-priced from the tape; no reset |
| Market structure | Migration mechanics, BOOST on or off, new quote coins, reward programs, the graduation threshold, selling switched off, a change in the network's slot target, a silent-change alarm, a new bot cohort | Open tickets: holdout days before and after the change are never pooled. If a ticket's minimums were met before the change, it is scored on the pre-change days. Otherwise it is **voided unread** (its α goes back to the ledger) and restarts with the same version on post-change data |
| Unclear | Anything else | Treated as market structure |

- **Fast re-validation.** This applies only to an *unchanged* champion that passed Gate v2 earlier. It needs ≥ 7 green days and ≥ 80 twin trades in the new regime, and all three of:
  - (a) mean net > 0 in the base and the pessimistic views;
  - (b) the 90% LB of (new − old) > −5.0 points;
  - (c) the 90% *upper* bound of (B-NULL new − B-NULL old, old = the prior 28 green days) ≥ 0.
- **Silent-change alarm** (from day 30). Either of these, on 3 consecutive green days:
  - B-NULL's daily mean is outside the trailing 30-green-day mean ± 2 standard deviations;
  - the daily median count of rival buys per U1-PB coin over [t_bend, t_bend + 900] is above 2 × its trailing 30-day median (a new bot cohort).

---

## 13. Stop rules (DESIGN.md §8, made exact)
1. **Week 4 (day 28).**
   - **Condition 1:** B-NULL (U1-PB, X0 with h = 35%, base view, days 0–27) has a mean net **< −10.0 points at every one** of these timings: g + 1,500, g + 1,650, g + 3,000, g + 4,500, t_bend, t_bend + 900 and EVT.
   - **Condition 2:** none of the five week-4 screens (§8.1–8.5) passes.
   - **If both hold:** we recommend **recorder-only mode**. That is about USD 160 a month (range 130–210), with the AI desk off and no paper bot or canary. Free research replays keep running.
   - **Default if Paul doesn't answer:** recorder-only for at most 56 more green days, then a full stop, unless some idea passes its screen on days 28–83.
   - The verdict also reports the six "what has to be true" items (DESIGN.md §3).
2. **Month 3** (day 90, or calendar day 105, whichever comes first). If **no rule has passed Gate v2**, we **stop every paid service**, the recorder included unless Paul chooses to keep it, and write the final report. **Default: full stop.** There is no extension unless Paul says so.
3. **Moving goalposts.** If two market-structure changes (§12) reset our clocks before any rule passes Gate v2, we pause and report. We continue only with Paul's yes.
4. **Live.** The drawdown stop sends us back to paper, and only Paul can resume. If it trips twice, live trading ends unless Paul re-approves after a written review.
5. **Budget.** If cumulative research spending since Phase 1 reaches the research ceiling, we stop whatever the results. The ceiling is Q3, default **USD 750**. It is separate from the CAD 1,000 a month cap Paul approved.

---

## 14. The nightly AI desk placebo protocol (AI-R E2 + QNT-R C3; family F5)
1. **Start:** day 14, in Phase 2, once Paul's Anthropic key and spend limit exist.
2. **Nightly pack** (built at 02:00 UTC, after green day d closes):
   - **R-half coins only**, from days ≤ d;
   - per-coin features (Appendix B) and outcomes, near misses and rejects;
   - the R-half forward results of the AI's *own* past rules.

   Names and addresses are replaced by salted hashes. The AI never sees C-half coins, placebo rules or placebo results. Seeing R-half coins from other families' holdout days is allowed, because desk rules are scored only here and can't join another family's ticket.
3. **AI rules:** Opus 5.5 in batch, or Fable 5.1 once it joins, proposes **≤ 3 rules a night**, with at most 20 per 30 green days and **60 per 90 green days**.
   - Each rule is written in the grammar of Appendix B.
   - Code checks the grammar. Rules that are invalid or duplicated (in canonical form) are rejected and not counted.
   - A refusal, a timeout or invalid output means zero rules that night, never a default rule.
4. **Placebo:** for each accepted AI rule with k conditions, code writes **one random rule with k conditions**, drawn from the same grammar:
   - features are drawn uniformly without replacement from the catalogue;
   - the comparison sign is chosen uniformly;
   - the threshold is chosen uniformly from the same decile grid;
   - the seed is SHA-256(`"placebo|<date>|<i>"`);
   - duplicates are re-drawn.

   The two arms are always equal in size.
5. **Forward scoring for each rule** (AI and placebo the same way):
   - **Data:** the C-half U1-PB coins on the 14 green days after the proposal night where the champion (E_inc if none) enters. K = coins where the rule is true; J = coins where it is false.
   - **Success** means both: mean net(K) > mean net(K ∪ J) (it beats the champion on the coins where they disagree), **and** mean net(K) > B-NULL's mean on the same C-half days.
   - If |K| < 20 or |J| < 5, the rule counts as **not a success**, in both arms.
6. **Desk verdict:**
   - It is taken once 60 AI and 60 placebo rules have been scored.
   - **The desk stays only if** (AI success share − placebo success share) ≥ **15 points** **and** a Fisher exact test gives one-sided p < 0.05.
   - **Futility:** at 30 + 30, if the AI share ≤ the placebo share, the desk switches off.
   - The desk also switches off if the month-3 stop fires or the AI spend cap is reached.
   - Once it is off, only the weekly summary remains.
7. **A single rule's own ticket** (F5, α 0.0833%). It is scored once, at +56 green days of forward C-half data, on mean net(K) − mean net(K ∪ J): LB > 0 at 99.917%, plus the pessimistic view > 0.
   - An AI rule that passes may go to Gate v2 as a champion candidate.
   - **Placebo rules are never promoted.** A placebo rule that passes its ticket is logged as a false-discovery alarm and reported to the team and Paul.

---

## 15. How this file may be amended
1. **What is frozen:** everything above the amendment log at the end. That text is never edited or deleted.
2. **Three classes of amendment.** Each is appended to the log, dated in UTC and numbered A-1, A-2 and so on.

   | Class | What it covers | Effect |
   |---|---|---|
   | **(a) Tightening** | Only makes a pass harder or a kill easier: a higher pass mark, a higher confidence, a bigger sample, an extra required condition, a stricter data-health rule | Applies to every look not yet run. **No clock restart** |
   | **(b) Clarification** | Changes no number and no computed result. Red-team must agree it changes nothing | No restart. If there is any doubt, it is treated as class (c) |
   | **(c) Anything else** | A loosening, or any change to a label, metric, rule, split, universe, cost or family | The item becomes a **new version**. It is a new ticket charged to its family's ledger, and **its clock restarts on the amendment date**: only green days after that count as its holdout. The old version's result stays on record, shown next to the new one |

3. **Who can amend:**
   - Any agent may propose an amendment. Quant-tester writes it, red-team signs it, and the lead records it.
   - Paul may tighten anything at any time.
   - If Paul chooses to proceed without a pass, the record says **"gate overridden by Paul"**. It never says "passed".
4. **Each log entry records:** the date, the sections affected, the old text, the new text, the class, the reason, red-team's sign-off, and whether any affected holdout had already been read.
5. **Substitutions are not amendments.** The fallback values in §16 are replaced by their named test results through the substitution log. A substitution must be applied **before** the affected test's holdout is read. If its result arrives later, that test keeps the fallback.
6. **Code follows this file.** An ambiguity found while coding is settled before any holdout is read, as a class (b) clarification. If it can't be settled, red-team picks the stricter reading.
7. **Never allowed:** changing a result after its look, re-running a failed ticket on the same holdout, or reading a sealed holdout early. Breaking this voids the affected ticket and spends its α.

---

## 16. Fallback values and the tests that replace them
These are the only numbers a Phase 0 or Phase 2 measurement may replace, and only through §15.5.

| # | Value | Fallback now | Replaced by (test, domain) |
|---|---|---|---|
| S1 | Our arrival delay | U{2,3,4} slots calm, U{4..10} hot [UNVERIFIED] | T7/D6, the measured decode → decide → send distribution (gRPC host, `mainnet.helius-rpc.com`) |
| S2 | Engine decision latency | 50 ms | T7/D6 |
| S3 | Residual drop in calm slots | 10% | The canary only (Phase 4) |
| S4 | Pump fee | The higher of 1.25% per side and the latest recorded same-pool rates | The shared fee module after T6 (500 trades, ≥ 50 crossing a tier, ≥ 50 v2) |
| S5 | Base fee per signature | 5,000 lamports [UNVERIFIED] | `docs/fee-model.md` (`docs.anza.xyz`, `solana.com`) |
| S6 | Our bids | §2.5 table | Execution's sender policy in `docs/fee-model.md` |
| S7 | Sell re-quote interval | 3 slots | max(2, guard loop p99 + 1) from S1/RC9 (`kms.eu-central-1.amazonaws.com`) |
| S8 | Sandwich allowance | 0.2% on a chase emergency sell; 1.0% on a one-shot 20–30% sell | P14, the sandwich rate by implied tolerance (gRPC host or `dune.com`) |
| S9 | NO_BOOST window | 600 slots | RC1/PR5: max(600, the p99.9 delay from g to the first BOOST event + 50) |
| S10 | `can_boost` field | Ignored | PR1 (it must agree with BOOST events on ≥ 99.9% of 300 pools) |
| S11 | Supply | Mint supply minus recorded burns | PR2 (`base_supply` used if it matches on 100 pools) |
| S12 | Hard stop h | 35% | Gap study on day 14 (§4.2) |
| S13 | Common funders | ≥ 50 distinct wallets funded in 7 green days | The union of that rule and chain-forensics' versioned list |
| S14 | Allowed Token-2022 extensions | Recorded, not used to exclude | T1 (`api.mainnet-beta.solana.com`) |
| S15 | LP burn | Recorded, not used to exclude | T4 (same) |
| S16 | SOL/USD | Pyth SOL/USD on-chain feed every 60 s [UNVERIFIED account]; CoinGecko hourly if unavailable | PR4 (`api.mainnet-beta.solana.com`, `api.coingecko.com`) |
| S17 | Taint in the insider set | I0–I3 | Test F1 (forensics); under 10% means I0–I2 |
| S18 | k_ours (race study) | 3 slots | The T7/D6 median |
| S19 | Racing cost | USD 2,000 a month over 300 trades | Execution's racing-stack quote, if written before day 21 |
| S20 | Position in the block | Worst position (base and pessimistic views) | Q3 changes only the optimistic "by bid" view |

---

## Appendix A. Fields the recorder MUST capture
"Can't backfill" marks data that can't be rebuilt honestly later, so it must be recorded from day 1 (rulings §7).

| # | Field(s) | Source | Used by | Can't backfill? |
|---|---|---|---|---|
| A1 | Every Pump and PumpSwap transaction, **landed and failed**: signature, slot, **position in the block** (Yellowstone `index`, checked by Q3), block time, err plus the program error code | Main gRPC stream (`failed` filter on) | All tests; rivals, crowding, auction cooled | **Yes** (failed transactions, position) |
| A2 | **Our local receive time** per message (UTC ns, clock disciplined), a monotonic timestamp, the provider and stream id, the commitment at receipt, and the final status (confirmed, finalized or dropped) | Recorder | §2.4 replay order; fork handling; T7/D6 | **Yes** |
| A3 | Fee payer and all signers; `meta.fee`; compute units consumed; ComputeBudget unit limit and **unit price** (micro-lamports per CU) | Stream | Bids, the seat price, CROWDED f0, auction cooled | |
| A4 | All top-level and inner instructions: program id, account keys, **raw data** (the args of failed trades, e.g. `base_amount_out`, `max_quote_amount_in`, `spendable_quote_in`, `min_base_amount_out`, `base_amount_in`, `min_quote_amount_out` [VERIFIED-DOC pump_amm.json]) | Stream | Rival direction and size; losers' tape; plain-transfer detection | |
| A5 | Address lookup tables used: the table address and the resolved writable and read-only lists | Stream | CHN-B | **Yes** |
| A6 | Pre/post lamport balances; **pre/post token balances** (account index, mint, owner, token program, amount, decimals) | Stream | Holdings, taint, overhang, fast group, witness 1 | |
| A7 | Log messages including the "Program data:" event payloads; **raw transaction bytes** kept for re-decoding | Stream | Every event below; decoder re-runs | |
| A8 | Decoded **pump** events with every field: `CreateEvent` (name, symbol, uri, mint, user, creator, token_program, is_mayhem_mode, quote_mint, virtual_quote_reserves, is_holder_reward, …), `TradeEvent` (is_buy, sol_amount, token_amount, user, reserves, fee bps, ix_name, …), `CompleteEvent`, `PostCompleteBuyEvent` (user, base_out, quote_in, reserves before and after), `CompletePumpAmmMigrationEvent` (pool, mint_amount, sol_amount, pool_migration_fee), `SetParamsEvent`, `AdminCtoEvent` [VERIFIED-DOC pump.json] | Decoder | Universe, I0/I1, fast group, ARMED | |
| A9 | Decoded **PumpSwap** events with every field: `CreatePoolEvent`; `BuyEvent` / `SellEvent` (pool, user, base_amount_out/in, quote_amount_in/out, user_quote_amount_in/out, max_quote_amount_in, min_base_amount_out, min_quote_amount_out, pool reserves, `virtual_quote_reserves`, lp/protocol/coin_creator/cashback/buyback fee bps and amounts, holder_rewards_bps, holder_rewards, `base_supply`, `can_boost`, ix_name); `InitBoostEvent`; `BoostBuyAndBurnEvent` (quote_amount_in_used, base_amount_burned, `boost_vault_remaining`, reserves); `DisableEvent`; `UpdateFeeConfigEvent`; `CreateConfigEvent`; `UpdateAdminEvent`; `SetBoostAuthorityEvent`; `AdminCtoPoolEvent`; `ExtendAccountEvent` [VERIFIED-DOC pump_amm.json]. Plus the decoder version id | Decoder | Price, BOOST labels, fees (S4), witness 2, regimes | |
| A10 | Account states, each change with its slot: PumpSwap `GlobalConfig` (`boost_enabled`, `disable_flags`, fee bps, mayhem, cashback, buyback); `FeeConfig` (`flat_fees`, `fee_tiers`); Pump `Global` (`initial_real_token_reserves`, …); each canonical `Pool` (`virtual_quote_reserves`, flags, **account byte length**, RC4); `BondingCurve` at completion (`post_complete_base_out`, `post_complete_quote_in`); program deploy slots; IDL hash | Stream + RPC | Q_eff, ARMED, regime id, BOOST switch-off | |
| A11 | Mint facts at creation and at ARMED: token program, mint authority, freeze authority, decimals, supply, Token-2022 extension list | RPC / decoder | HARD_SAFE, S(t) | |
| A12 | Per slot: slot, parent, block time, leader, skipped flag, transaction count. **Full blocks** for the 20 slots after each migration and for ±5 slots around each paper order (Jito tip transfers: tip account, lamports, bundle position) | RPC `getBlock` (G4) | Seat price, tips, Q3 | **Yes** (tips) |
| A13 | Coin metadata: the create-event fields for every launch. At 20% of the curve, through the sandboxed fetcher: fetch start and end time, HTTP status, bytes, SHA-256, description text, image URL, image SHA-256 and perceptual hash, links. Failures are recorded too | Decoder + fetcher | Waves (§3.5), the Claude add-on, CHN-B | **Yes** (fetch times; mutable metadata) |
| A14 | Forensic lookups: wallet, funder, funding signature and slot, amount, **lookup start and `known_at` time**, provider, credits used. The ARMED snapshot (slot, top 25 holders with balances). Holder-scan reconciliations | Helius RPC (forensics key) | I2, Heat, common funders, §2.4 | **Yes** (`known_at`) |
| A15 | Derived per slot: Pump and PumpSwap landed and failed counts; priority fee per CU p50, p75 and p90 | Computed from A1/A3 | f0, auction cooled, S6 | |
| A16 | SOL/USD every 60 s with its source; the daily U0 count | RPC or CoinGecko; recorder | Yardstick (b), the desk bar, quiet and busy weeks | |
| A17 | Health: stream gaps per provider (start and end slot and time); the daily audit per pool; reserve-continuity breaks; two-witness mismatches; alarms (class, start, end); regime-id changes; the green or red day flag | Monitors | §2.1, G8, §12 | **Yes** |
| A18 | Research and paper outputs: one decision line per coin × rule version (reason code plus numbers); version hashes; seeds; T, J, earliest arrival, L, or the miss reason; fills per view; exit codes and slots; net per view; the twin and constrained ledgers | Engine and simulator | Every metric; G7 | |
| A19 | AI desk: pack hash, prompt hash, model id, timestamps, raw output, refusals, grammar-check result, rules in canonical form, placebo rules with seeds, scores | Desk | §14 | |

---

## Appendix B. AI desk grammar and feature catalogue (frozen v1)
- **Grammar.**
  - `RULE := COND [AND COND] [AND COND]` (one to three conditions).
  - `COND := feature (< | ≥) threshold`.
  - The threshold is one of the feature's {q10, q20, …, q90} deciles. They are computed over R-half U1-PB coins at E_inc triggers in the trailing 14 green days, and the numeric value is fixed into the rule when it is proposed.
  - **Meaning:** "take E_inc's entry only when RULE is true" (an entry filter; exits are X0).
- **Features, all measured at the decision slot T:**

| ID | Feature | ID | Feature |
|---|---|---|---|
| f01 | Slots since g | f15 | Creator's (I0) earlier launches, point-in-time |
| f02 | T − t_bend | f16 | Creator's earlier U0 graduates |
| f03 | Q_eff (SOL) | f17 | P(T) ÷ P(g) − 1 |
| f04 | NF60 | f18 | P(T) ÷ P(T − 300) − 1 |
| f05 | Net flow over (T − 1,500, T] ÷ Q_eff | f19 | Largest fall from the peak over [g, T] |
| f06 | Distinct buyers over (T − 1,500, T] | f20 | BOOST SOL used (Σ `quote_amount_in_used`) |
| f07 | Distinct sellers over (T − 1,500, T] | f21 | Slots from creation to completion |
| f08 | Failed rival buys over (T − 1,500, T] | f22 | Wave Heat |
| f09 | The pool's median priority fee per CU ÷ the network p50, over (T − 1,500, T] | f23 | Wave rank |
| f10 | O_n (naive overhang) | f24 | Wave size |
| f11 | O_t (tainted overhang) | f25 | Temp(T) |
| f12 | H_U ÷ Peak_U | f26 | U0 graduations in the trailing 6 h |
| f13 | Top-10 holder share | f27 | SOL/USD change over 24 h |
| f14 | Holder count | f28 | FO ÷ its peak (from day 14) |

---

## Tests to run once allowed (new in this file; all read-only)
| # | Test | Expected result → what we use | Domain(s) |
|---|---|---|---|
| PR1 | On 300 new pools, compare `can_boost` in the first `BuyEvent`/`SellEvent` with whether BOOST events follow | Agreement ≥ 99.9% → use it; otherwise keep ignoring it (S10) | Chainstack gRPC host, `api.mainnet-beta.solana.com` |
| PR2 | `base_supply` against mint supply on 100 pools, at 3 times each | Exact match → use `base_supply` (S11) | `api.mainnet-beta.solana.com` |
| PR3 | Are the pool reserves in `BuyEvent`/`SellEvent` before or after the trade? 200 trades against vault post-balances | Settles witness 2 (§2.3) | `api.mainnet-beta.solana.com` |
| PR4 | Read the Pyth SOL/USD account every 60 s for 1 h and compare with CoinGecko | Within 0.5% → Pyth is the primary source (S16) | `api.mainnet-beta.solana.com`, `api.coingecko.com` |
| PR5 | Distribution of the delay from g to the first BOOST event on 300 pools (part of RC1) | Sets the S9 window | Chainstack gRPC host |
| PR6 | Daily U0 count for 14 days (= Q6), to check the minimum samples can be met on schedule | If fewer than 72 a day, the §6 minimums push the looks later; the file still applies unchanged | Recorder; `dune.com` |
| PR7 | Time from ARMED to completed I2 lookups (`known_at`) on 200 coins | Shows how often I2 is known before decisions | `mainnet.helius-rpc.com` |

Earlier tests this file depends on, unchanged: T1, T4, T6, T7/D6, Q2/RC6, Q3, Q4, Q5, RC1, RC4, G4, P14, S1/RC9 and test F1 (forensics). Their domains are in QUESTIONS_FOR_PAUL.md, List 1.

## Sources
- [VERIFIED-DOC, re-downloaded this session] Pump program IDL: event and field names, `CreateEvent`, `TradeEvent`, `CompleteEvent`, `PostCompleteBuyEvent`, `CompletePumpAmmMigrationEvent`, `Global.initial_real_token_reserves`. https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json
- [VERIFIED-DOC, this session] PumpSwap IDL: `BuyEvent`/`SellEvent` fields, `InitBoostEvent`, `BoostBuyAndBurnEvent.boost_vault_remaining`, `GlobalConfig.boost_enabled`, trade-instruction arguments, `can_boost`, `base_supply`. https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json
- [VERIFIED-DOC, this session] Signed `virtual_quote_reserves` and effective quote reserves. https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md
- [VERIFIED-DOC, this session] Synthetic migration: the pool opens where the completing buy stopped; event order. https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- [VERIFIED-SEARCH, via the round files] 200 ms slots (rulings C8); Pump fee of 1.25% per side (rulings §6b); BOOST amount not confirmed as fixed (rulings R5.5); heavy-tail bootstrap and the number of trials (QNT-R sources: Athreya 1987 via russell-davidson.research.mcgill.ca; Cornea-Madeira & Davidson 2015; Bailey et al., SSRN 2326253 and 2460551).
- Every threshold and pass mark comes from DESIGN.md §3/§7/§8 and `team-debate/round3/rulings.md` §4/R5/C12/C15, unless it is marked [NEW] or TIGHTER here.

---

## Substitution log (append-only)
*(none yet)*

## Amendment log (append-only; nothing above this line is ever edited)
- **v1.0, 2026-11-05 (UTC):** frozen by quant-tester before any data existed. No amendments.
