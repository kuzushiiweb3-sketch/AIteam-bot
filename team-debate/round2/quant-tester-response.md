# Round 2b: Quant tester response. Honest paper fills, a data-decided speed fork, three testable edges

## 0. In plain English (for Paul)
- The red team found a real flaw in my paper trading. It treated our failed orders as random bad luck. In real life we lose the race on the coins everyone wants, and those are often the winners. Now a pretend order only "gets in" if it would have beaten the bots that actually got into that coin in that block, paying what they paid. If it would have been outbid, the trade counts as missed, the same as in real life.
- Every result now sits next to three yardsticks: "buy every graduated coin", "buy random coins" and "do nothing". A rule counts only if it beats all three after every fee and after our share of the monthly bills.
- Should we race other bots at the moment of graduation? A 2–3 week study on our own recorded data decides it before any money goes on speed. The study measures what each block of lateness costs us and what the winning bots paid to be early.
- **We have no proven edge yet.** We have three ideas we can test. Each one has a pass/fail number written down before its test runs, so we can't fool ourselves afterwards.

Tags: **[VD]** = VERIFIED-DOC (I read the primary source this session). **[VS]** = VERIFIED-SEARCH (seen only in search results). **[UNV]** = UNVERIFIED, with the test that would confirm it. **[DERIVED]** = my own arithmetic on tagged inputs. Host notes: WebFetch worked on `raw.githubusercontent.com`. The shell network was blocked, so I ran no live tests. I used 7 web searches.

---

## 1. Answers to the attacks

### 1a. How paper mode now handles lost races (QNT-1, PREMISE-3, EXE-6, EXE-9). **FIXED**
A Solana block (a "slot") is a small auction for space. Bots bid with a **priority fee** (paid to the validator) and a **Jito tip** (a payment for a fast lane). The fill simulator now settles every paper order, buy or sell, in six steps:

1. **Earliest arrival.** Decision slot + our measured delay (decode, decide, sign, send), drawn from real timings including the slow tail. Until those timings exist I assume 2–4 slots when calm and 4–10 when hot [UNV; T7/D6 and the canary replace it].
2. **Was the slot contested?** The recorder lists the other transactions that traded the same pool in the same direction in that slot. It counts those that landed and those that landed but failed (for example error 6004 "slippage exceeded" [VD in Round 1 by execution, EXE §1]), and it reads what each winner bid.
3. **Did we win a seat?** In a calm slot (fewer than K = 3 rivals to start), we land unless a residual random drop hits us (10% until measured). In a contested slot we land only if our bid beats the marginal winner's. That bid is the same tip and priority fee, cap included, that the live sender would choose. If we lose, we try the next slot, and by then the price has moved.
4. **Where in the block (QNT-2)?** By default we sit after every same-direction trade in that slot and before every opposite-direction trade. That is our worst possible position. A "ranked by bid" position is shown as a second view [UNV: real ordering inside a block is only roughly by bid].
5. **Did our price limit hold?** We compute the fill from the pool's reserves at exactly that position, using the shared fee module (SEAM-4). If the limit breaks, the order fails. A failed Jito bundle costs nothing [VS Round 1 S24]. A normal transaction still pays its base fee and priority fee.
6. **Gave up?** After the patience window (10 slots for buys to start with; sells keep retrying on the sell ladder), the buy is logged as **"missed: lost auction"** next to what that coin did afterwards. The winners we lose stay visible on Paul's screen.

Failure is now tied to outcome, because hot coins have many rivals and high bids. Sells use the same machinery. In a crash many sellers compete, so our stop slips blocks and fills lower, which keeps stop-loss results honest (RSK-4).

| View | How contested slots are settled | Use |
|---|---|---|
| Optimistic | We land if we beat the lowest winning bid | Upper bound only. Never used for decisions |
| **Base** | We must beat the median winner, and we take the worst position in the block | The main number |
| **Pessimistic** | We must beat the top winner, **and** every coin with ≥ 5 rival buys in the 3 slots around our landing counts as missed (the red team's test c) | Must stay above zero to pass the gate |

**Honest limits.** Jito bundles that lose never appear on chain. We see the winners' bids but not how many bots tried. That is enough to price a seat, but it can't tell us whether we would actually land. Only real orders can show that. So the canary reports **"paper filled / live failed"** and **"paper failed / live filled"** coins separately, each with its P&L (PREMISE-3b). If the coins that paper filled but live missed earned more on paper than the coins live did fill (90% confidence), adverse selection is confirmed. Then K and the bid percentile are refit, and the rule goes back to paper. No landing rate taken from a blog enters the gate (EXE-9).

### 1b. Every other attack touching testing honesty

| Attack | Verdict | What changed |
|---|---|---|
| **QNT-3 / SEAM-4 / EXE-8** fees 5× apart | **FIXED, jointly with execution** | One fee module, owned by execution, used by quoting, paper, backtest and sizing. My Round 1 "20 + 5 bps" is PumpSwap's global setting. Canonical graduated pools use a market-cap tier table instead, and its values exist only in an image [VD FEE_PROGRAM_README]. **The chain settles the dispute:** every PumpSwap `BuyEvent`/`SellEvent` records the rates actually charged: `lp_fee_basis_points`, `protocol_fee_basis_points`, `coin_creator_fee_basis_points`, plus the buyback, cashback and holder-reward rates [VD pump_amm.json]. The tier is chosen by the program's own formula, market cap = quote reserve × base supply ÷ base reserve, and non-canonical pools pay `flatFees` [VD FEE_PROGRAM_README]. T6 now passes only if the module reproduces the recorded rate *and* amount on 500 trades, including ≥ 50 that cross a tier boundary and ≥ 50 v2 trades. The same check then runs on every live trade (DAT-1). Until T6 passes, paper charges the higher of the two models (1.25% per side at the low tier [VS EXE §1]) and labels results "fee model unproven" |
| **QNT-4** fat tails | **FIXED** (one demand modified) | The gate uses the spread measured on our own trades and shows the **smallest edge the sample can prove** (table in 1c). Confidence intervals come from re-drawing whole days, not single trades, because trades on the same day move together. A smaller-sample re-draw check ("m-out-of-n") is added, because the ordinary re-draw test is unreliable when a few huge outcomes dominate [VS Athreya 1987 via russell-davidson; Cornea-Madeira & Davidson 2015]. **"Still positive with the top 5% removed"**: I keep it as a report, not an automatic kill. A genuinely lopsided meme strategy, one with rare big winners, always fails it. A failure therefore labels the rule *tail-dependent*. A tail-dependent rule needs ≥ 20 tail wins in its sample, and its tail-win rate in paper must sit inside the range of the full-population backtest. The luck check (top 3 trades removed ≥ 0) stays a hard rule |
| **QNT-5** sample per regime | **FIXED** | Every result row shows trades and days for each program regime. A regime with < 50 trades is marked "thin" and cannot pass a gate on its own |
| **QNT-6** shadows vs live champion | **FIXED** | In canary and live, the champion also runs a paper twin. Challengers are compared paper to paper. Live vs twin gives the fill gap |
| **QNT-7** trades missing inside the stream | **FIXED** | Every day: 20 random pools plus every held pool, recorder vs `getSignaturesForAddress`, which should include failed transactions [UNV, check alongside Q4]. An alarm sounds below 99.5% matched. The credits go into the joint budget table (SEAM-7) |
| **QNT-8** newest data is locked | **ACCEPTED RISK**, stated to Paul | Locking the newest 2 weeks means tuning on slightly stale data, and that is the price of honesty. After a market-structure change, the unchanged champion meets the new regime's data out of sample anyway (1d) |
| **PREMISE-1** speed race unpriced | **QUESTION, settled by data** | Section 2. No money on speed before the fork memo |
| **PREMISE-2** no named edge | **ACCEPTED: true today** | Section 4 gives three hypotheses with kill numbers fixed in advance. None counts as an edge until its Stage B passes |
| **PREMISE-4** no baseline | **FIXED** | Every report shows four lines. *Rule.* *Null*: buy every canonical SOL-quoted graduate at the same entry time, with the same exits, size and costs. *Random*: the same number of trades per day, drawn 1,000 times from graduates that pass only the hard safety checks; the rule must beat the 90th-percentile draw. *Do nothing*: zero minus bills. A rule must beat the null, random and zero |
| **PREMISE-6** AI with no baseline | **FIXED** | The vibe score must beat a $0 feature score (name, ticker, description length, links) on the same coins. A power calculation runs before shadowing starts (AI-1) |
| **PREMISE-7 / SEAM-1 / SEC-8 / EXE-7** costs left out | **FIXED in the simulator** | Newly charged: setting up and refunding the wrapped-SOL account, the token-account deposit (unless the last sell closes the account), fees on failed attempts, the signer's per-signature fee if the chosen vendor charges one (Turnkey $0.10 [VS red team]), and the v1 trade path for cashback coins. P&L is shown two ways: after per-trade costs, and after monthly bills shared out per trade (table below). **Paper runs at the size we would really trade**, not only at 0.05 SOL |
| **SEAM-9 / AI-4** AI as an overfitting engine | **FIXED** | Every AI proposal counts as a trial, adopted or not, and is scored only on data from after its proposal date. See challenge C3 |
| **SEAM-10 / AI-3** inputs missing at decision time | **FIXED** (new metric) | **Input availability:** for each input (social, AI score, RugCheck, holder scan), the share of decisions where it existed at decision time. Below 50%, the input is research only |
| **RSK-1 / RSK-4 / CHN-5** uncalibrated defaults | **FIXED** (test design) | The entry-time study is part of Section 2. Stops are set from the null's swing and one-slot gap distributions in the same replay. The rug label is written down *before* T10 runs: "≤ −80% from the entry price within 60 min, with half of the drop inside 3 slots". This is a starting definition. Chain-forensics may change it before the test, never after |

**Hurdle: the gain a trade needs before it makes anything** [DERIVED. Inputs: execution §5 per-transaction costs (calm 0.000305 SOL, hot 0.003005 SOL) [UNV], 1.25% pool fee per side [VS], an 80 SOL pool, $300/month of bills (red team range $280–500), 600 trades a month, SOL ≈ $100 [UNV]]:

| Stake | Bills per trade | Network + tips, 2 tx (calm / hot) | Pool fee, both sides | Price impact | **Hurdle, calm / hot** |
|---|---|---|---|---|---|
| 0.05 SOL | 10% | 1.2% / 12% | 2.5% | 0.1% | **≈ 14% / 25%** |
| 0.25 SOL | 2% | 0.24% / 2.4% | 2.5% | 0.6% | **≈ 5.4% / 7.5%** |
| 0.5 SOL | 1% | 0.12% / 1.2% | 2.5% | 1.25% | **≈ 4.9% / 6.0%** |

At 0.05 SOL the bills alone need a 10% gain per trade, so Phase 1 size can prove safety but cannot prove profit.

### 1c. Gate v2: Paper to Canary (replaces Round 1 §5; every item must pass, and Paul flips the switch)
1. At least 200 closed trades over at least 21 days, including one quiet week and one busy week, with each regime's count shown.
2. Expectancy after per-trade costs is above 0 with 90% confidence, using the day-based re-draw. The bar rises to 95% above 20 trials and 99% above 50 [VS: the false-discovery risk grows fast with the number of trials, Bailey et al. SSRN 2326253 and 2460551].
3. The pessimistic view's expectancy is above 0.
4. The rule beats the null and the 90th-percentile random draw on the same days. It also beats zero after bills at the intended size.
5. Luck check: removing the top 3 trades leaves it ≥ 0. Tail-dependent rules must also meet the tail rule (QNT-4).
6. Max drawdown is under 25%. This is a placeholder; Paul sets the real number.
7. Paper results fall inside the backtest's range for the same weeks.
8. Data health: coverage ≥ 99.5%, per-pool completeness ≥ 99.5%, missed-coin rate < 5%, no open alarm, and the fee module has passed T6.

**What a sample can prove.** The smallest edge per trade that we would detect 80% of the time at 90% confidence is 2.12 × spread ÷ √trades [DERIVED]. The real spread gets measured; these rows are illustrations [UNV]:

| Per-trade spread (one std. dev.) | 200 trades | 500 | 1,000 | 3,000 |
|---|---|---|---|---|
| ±60% | 9.0% | 5.7% | 4.0% | 2.3% |
| ±100% | 15.0% | 9.5% | 6.7% | 3.9% |
| ±150% | 22.5% | 14.2% | 10.1% | 5.8% |

Read together with the hurdle table: at our trade rate, **only large edges can be proven within weeks.** That is why research runs on *every* graduation (hundreds a day), while the gate judges only our own trades.

Canary to Normal is unchanged from Round 1, with the "paper filled / live failed" report from 1a added.

### 1d. When Pump changes the market (PREMISE-5). **FIXED**

| Class | Examples | Effect on the clock |
|---|---|---|
| Decoding only | new instruction names with the same economics (`buy_v3`), new event fields that stay zero, IDL renames | **No reset.** The new decoder must pass T6 on 500 trades made after the change before paper results count again |
| Fee or parameter | tier values, protocol fee, BOOST size | **Re-price, don't reset.** Fills come from the tape, so past trades are recomputed with the new fees. If the rule still passes, the clock keeps running |
| Market structure | migration mechanics (synthetic migration), BOOST added or removed, new quote coins, reward programs, graduation threshold, a sell switch-off | **Fast re-validation** (below) |
| Unclear | anything else | Treated as market structure |

**Fast path.** It applies only to an *unchanged* champion that passed the gate before. Paper keeps running, and risk-manager decides whether canary or live pauses or halves its size. The rule passes again after ≥ 7 days and ≥ 80 trades in the new regime if three things hold. (a) Expectancy is above 0 in both the base and pessimistic views. (b) It is "not clearly worse": the 90% lower bound of (new − old) is above −5 points per trade. (c) The null, measured on every graduation, has not dropped significantly. A retuned rule is a new version with a full clock. Honest cost: the fast path accepts more risk than proving everything again, which is why it covers only a rule that has passed before.
**Silent-change alarm.** If the null's daily result leaves its 30-day band for 3 days in a row, we treat it as an unannounced market-structure change. A new cohort of bots counts too.

---

## 2. The big fork: race at graduation or not?

**The question:** for the coins we would want, does arriving early earn more than it costs to win the early seat?

**Step 1. The lateness curve (recorder only, no money).** For every canonical SOL graduation, replay a fixed 0.25 SOL buy landing at different points:
- slots 0, 1, 2, 3, 5, 8, 10, 15 and 20 after the pool opens, starting from the pool state *after* any synthetic-migration buyer [VD by red team, PREMISE-1];
- 30, 60, 120, 300, 330, 600 and 900 s after the pool opens;
- one event-based entry: BOOST finished and net flow positive.

Each entry takes the worst position in its block and goes through the fee module. Each one exits under three exit rules fixed in advance (hold 5 min, hold 30 min, risk's default ladder), with competition-aware sells. Output: average net P&L at each entry point, for the null and for two fixed filters (hard safety only; hard safety plus low early-buyer concentration).

**Step 2. Price a seat.** For slots 0–5 we record:
- how many rivals there were (landed plus failed);
- the winners' bids;
- the share of pools completed, migrated and bought in one transaction (red team P1).

"Seat price at slot k" is the 75th-percentile winning bid. One vendor blog claims buys in the first pool slot get the floor price, while buys one or two slots later meet the first retail wave [VS rpcfast, weak]. That claim is exactly what this step measures.

**Step 3. Where we would land.** Our arrival without racing (k_ours) comes from measured latency (T7/D6). Arrival with racing (k_race = 0–2) can only be *assumed*. It is charged at the seat price plus the extra infrastructure (for example LaserStream at $499+/month [VS Round 1 S16]).

**Decision rule, written before any data:**
- **RACE** only if all four hold:
  1. Gain(k_race vs k_ours) minus the seat price, the extra per-trade costs and the extra monthly cost per trade is above 0, with 90% confidence.
  2. Entry at k_race is profitable on its own after all costs, in the pessimistic view.
  3. Both halves of the period and at least 2 of the 3 exit rules show it.
  4. It is still true when we count only the slots where our *capped* bid would have won. Coins we would have lost can't rescue the result.
- **RACE-LITE**: the curve falls steeply between slots 3 and 10, but slots 0–2 fail condition 1. Then we pay only for cheap speed (local decoding, decisions on "processed" data behind a confirmation guard, local quotes), not for co-location or top tips.
- **DON'T RACE** (the default): otherwise. Entry becomes time-based or event-based at the best point on the curve, which also settles the 300 s question (RSK-1). Speed money goes to exits only.

**Sample and timing.** At least 1,000 graduations over at least 14 days. The daily count is unknown today. One day in January 2026 saw 269 [VS]. Under BOOST the rate rose to 4.7–6.7% of roughly 30,000 daily launches in late July [VS theblock, solanacompass]. That suggests roughly 100–2,000 a day [UNV], and the recorder counts it from day 1. Each coin is compared with itself at different entry times (a "paired" test), so the noise is far smaller than for a trade-level edge. If the paired spread is ±30 points, 1,000 graduations prove a lateness cost of about 2 points per trade (2.12 × 0.3 ÷ √1,000) [DERIVED; spread UNV]. **Timeline:** recorder on day 1, curve on day 14, fork memo to the lead and Paul around day 21. Paper trading starts sooner with a non-racing entry, because paper needs no speed spending.
**What the study can't tell us:** whether paying the seat price really lands us. Only the canary can show that, and only when Paul flips it.
**Dune is now optional.** The fork needs post-BOOST data that includes failed transactions and tips. Dune's curated tables may not carry them correctly (T2). The safe, cheaper default is to skip Dune and use the recorder.

---

## 3. Challenges to other areas (3)

**C1 → data-engineer: record the losers, the tips and the order inside each block.** Without all three, QNT-1 and QNT-2 can't be fixed and the fork can't be measured.
- (a) Include failed transactions for Pump and PumpSwap. `failed` is an option of the Yellowstone transaction filter [VD geyser.proto].
- (b) Capture Jito tips. They usually sit in a separate *last* transaction of the bundle that touches no Pump program [VS docs.rs jito-bundle, getblock guide], so our current filter never sees them. One way is to add the 8 tip accounts [VS] to the subscription. If D4 shows that is too much data, fetch full blocks for the 20 slots after each migration and around each paper order instead.
- (c) Store each transaction's position in its block and our local receive time for each message. Yellowstone transaction updates carry an `index` field, but its meaning is undocumented [VD field exists; UNV meaning, test Q3].
- Also: Yellowstone now has a `token_accounts` option that matches the owners of token balances. That may answer SEAM-6, the invisible transfers [VD geyser.proto].

**C2 → risk-manager: test the defaults, don't adopt them yet.** Do not adopt `post_migration_buy_delay_sec = 300` or the −35% stop as defaults. From paper day 1, run a grid fixed in advance as shadows on the same coins:
- entries at 60, 300, 330, 600 and 900 s, plus event-based;
- stops at −20, −35 and −50%;
- the ladder vs a trailing stop only.

Each grid counts as one trial family, corrected once. Exit variants compared on identical entries are the cheapest statistical power we have. Paper must also run at the intended live size (0.25–0.5 SOL), because the hurdle table shows bills dominate at 0.05 SOL.

**C3 → ai-strategist: split the coins with a hash.** Split coins into two halves by a hash of the mint address. The nightly and weekly AI reviewers only ever see the "research half". Their proposals are judged on the "check half" of the same weeks and on later data. Each proposal states its kill number before it is tested, and at most 4 proposals a week enter shadow. That gives an honest test within days instead of weeks, and it stops the reviewers from fitting noise (SEAM-9).

---

## 4. Edge hunt: three ideas from the testing seat

**Shared method.** Every idea runs in two stages:
- **Stage A** is a cheap screen on *every* graduation. It uses a low-noise outcome: the 10-minute forward price change, clipped at ±100%. A rank correlation from 1,500 graduations has a standard error of about 0.026, so a correlation of 0.10 is about 4 standard errors [DERIVED].
- **Stage B** is a trading rule that goes through paper and Gate v2.

Kill numbers are fixed here, now. The research order is fixed too, and each step counts as one trial family:
1. data checks (T1, T6, Q1–Q4, QNT-7);
2. the lateness curve and entry time (Section 2);
3. E3, the thermometer;
4. the exit grid;
5. E1, the losers' tape;
6. E2, the flipper clock;
7. the AI vibe score vs its $0 baseline.

**E1. The losers' tape: who tried to buy and failed.**
- *What we'd know that others don't:* unmet demand. Failed buys still land on chain with an error code, and their requested amounts can be decoded from the raw transaction [UNV, Q4]. Successful buys reveal urgency: every `BuyEvent` records the buyer's own price limit (`min_base_amount_out`, `max_quote_amount_in`) next to what they actually got [VD pump_amm.json]. Two measures:
  - U = failed-buy SOL ÷ landed-buy SOL in the first 20 slots;
  - urgency = the median price tolerance of the early buyers.
- *Why we'd win:* trade APIs and charting apps show successful swaps. I found no tool showing failed-buy demand [UNV, P15]. It needs a firehose that keeps failed transactions, which most users filter out. A serious team could copy it within weeks, so we test it fast and expect it to fade.
- *Cost:* storage only, perhaps $0–10/month [UNV, D4], plus about 2 days of analysis.
- *Test:* Stage A uses ≥ 1,500 graduations over ≥ 14 days: the rank correlation of U and of urgency with the 10-minute return from t = 60 s. The direction isn't assumed in advance. High unmet demand might mean chasers keep buying, or it might mean snipers dump on them, and either way it is usable (enter or avoid).
  - **Pass:** |ρ| ≥ 0.10 with the same sign in both 7-day halves.
  - **Kill:** |ρ| < 0.05, or the sign flips.
  - **Stage B:** null plus a U filter vs the null, walk-forward, ≥ 300 rule trades. Pass: ≥ 3 points per trade better with 90% confidence, and above zero in the pessimistic view. Kill: less than 1 point better after 4 weeks.

**E2. The flipper clock: enter when the forced sellers are done.**
- *What we'd know:* a hold-time book built from our own tape. For each wallet it records the typical hold time across past graduations. It is built walk-forward, using only coins that finished before the current one, so there is no look-ahead. At each graduation, the "overhang" is the tokens held by fast flippers (median hold < 5 min over ≥ 5 coins) and by wallets that front-ran BOOST's buying. Live, we track how much of the overhang has already been sold. Entry: BOOST has ended and less than 20% of the peak overhang remains.
- *Why we'd win:* vendors sell static "sniper %" labels [VS solanatracker]. This is a live clock of *future forced selling*, which is what kills late buyers. First-block snipers on launches sell 85% within 5 minutes [VS Pine Analytics, via red team; launches, not migrations]. It also replaces the 300 s guess (RSK-1) with "enter when the sellers are actually out". The book improves every day it runs, so starting early is a modest moat. Anyone with a recorder could build one.
- *Cost:* compute and storage, perhaps $0–20/month [UNV], and 14 days of warm-up before the labels mean anything.
- *Test:* 14 days of warm-up, then ≥ 21 days of test.
  - **Stage A:** correlation between the overhang remaining at time t (60–900 s) and the next 10-minute return. Pass: |ρ| ≥ 0.10 in both halves.
  - **Stage B:** flipper-clock entry vs the best fixed-time entry from Section 2, on the *same* coins (paired, so powerful). Pass: ≥ +3 points per trade with 90% confidence, positive in the pessimistic view, over ≥ 1,000 graduations. **Kill:** less than +1 point, or a confidence interval that includes zero at 2,000 graduations.

**E3. The market thermometer: trade the weather, not just the coin.**
- *What we'd know:* the null strategy's cost-adjusted result over the last 24–72 h, computed on every graduation (hundreds a day) instead of our ~20 trades. Hypothesis: good and bad periods last for days. If so, trading only when the thermometer reads warm improves expectancy and, more reliably, cuts drawdown. Losing less is a real edge.
- *Why we'd win:* it needs our full-population replay with real fills and costs, which chart-reading and copy bots don't compute. It is a decisions edge, not a speed edge. It is also the silent-change alarm from 1d.
- *Cost:* $0. It comes free with PREMISE-4.
- *Test:* needs ≥ 6 weeks.
  - **Stage A:** autocorrelation of the null's 6-hour results (about 168 blocks, standard error ≈ 0.08 [DERIVED]). Pass ≥ 0.25. **Kill** < 0.10.
  - **Stage B:** gated vs ungated champion on the same days. Pass: ≥ +3 points per trade, or ≥ 25% lower max drawdown without lower total P&L, at 90% confidence using the day-based re-draw. **Kill:** neither after 8 weeks.

---

## 5. Revised recommendation
1. **The recorder starts on day 1 and now keeps failed transactions, Jito tips, the order inside each block and our receive times (C1).** One shared fee module, owned by execution and checked by T6 against the fee rates the chain records on every trade.
2. **Fill simulator v2 decides landings from real competition.** It takes the worst position in the block and shows optimistic, base and pessimistic views side by side. Base must pass the gate, and pessimistic must stay above zero. The canary reports coins that paper filled but live missed, separately.
3. **Every report carries the null, random and do-nothing baselines,** the sample size per regime, the measured spread and the smallest provable edge. Gate v2 (1c) and the regime fast path (1d) replace Round 1 §5.
4. **The fork memo around day 21 decides "race / race-lite / don't race"** from the lateness curve and the seat prices. Until then, no money goes on speed and Dune stays unbought.
5. **Research follows a fixed queue with kill numbers fixed in advance** (E3, E1, E2 plus the exit and entry grids). Every variant, including every AI proposal, adds to the trial counter. AI reviewers see only the research half of the coins.

---

## Tests to run once allowed (new; all read-only)
| # | Test | Domain(s) |
|---|---|---|
| Q1 | From 1 day of recorded `BuyEvent`/`SellEvent`s, plot the charged fee rates against pool market cap, and compare them with the `feeConfig` account | gRPC provider host; RPC host (e.g. `api.mainnet-beta.solana.com`) |
| Q2 | Data volume per hour of (a) failed Pump/PumpSwap transactions and (b) transactions touching the 8 Jito tip accounts (extends D4) | gRPC provider host |
| Q3 | Does Yellowstone's `index` equal the position in the block? Compare with `getBlock` order on 100 transactions | gRPC host, RPC host |
| Q4 | On 100 failed PumpSwap buys (error 6004), can `getTransaction` give the requested amount and price limit? Is any event emitted? | RPC host |
| Q5 | Official Jito tip-account list (`getTipAccounts`) | `mainnet.block-engine.jito.wtf`, `docs.jito.wtf` |
| Q6 | Daily canonical graduation count for 14 days, cross-checked with a public dashboard | recorder; `dune.com` |

## Sources
- [VD] PumpSwap IDL, `BuyEvent`/`SellEvent` field lists (fee bps fields, `min_base_amount_out`, `max_quote_amount_in`, `virtual_quote_reserves`, `base_supply`): https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json
- [VD] Fee program (tiers in an image only, `poolMarketCap`, canonical-only tiers, `flatFees` otherwise): https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md
- [VD] Yellowstone filter (`failed`, `account_required`, `token_accounts`, `index`): https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/yellowstone-grpc-proto/proto/geyser.proto
- [VS] Graduation rates and BOOST: https://theblock.co/news/defi/2026-07-29-pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives-409815 ; launch counts: https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex
- [VS] Jito tip in a separate last transaction: https://docs.rs/crate/jito-bundle/latest/source/README.md ; https://docs.getblock.io/guides/how-to-optimize-solana-transactions-with-jito-bundles ; tip-floor snapshots only: https://raw.githubusercontent.com/api-evangelist/jito/refs/heads/main/json-schema/jito-tip-floor-schema.json ; https://www.quicknode.com/pt/docs/solana/lil-jit-jito-bundles
- [VS] Overfitting and number of trials: https://papers.ssrn.com/abstract=2326253 ; https://papers.ssrn.com/abstract=2460551
- [VS] Bootstrap with heavy tails: https://russell-davidson.research.mcgill.ca/articles/stable.pdf ; https://ideas.repec.org/a/cup/etheor/v31y2015i03p449-470_00.html
- [VS] Migration timing (vendor blog, weak): https://rpcfast.com/blog/how-to-launches-snipe-pump
- Round 1 sources (S16, S24 etc.) are in `team-debate/round1/quant-tester.md`. Attack IDs refer to `team-debate/round2/red-team-attacks.md`.
