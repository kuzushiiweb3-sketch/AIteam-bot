# Round 3: Lead architect's rulings

## 0. In plain English (for Paul)
- **Every open argument is now settled.** For each one I list the options, who wanted what, my decision and the reason. I ruled by your priorities, in order: no losses to bugs, bad data, slowness or security mistakes; no blind spots; low running cost; clear logs.
- **Selling can no longer freeze while you sleep.** If the guard computer dies, it restarts itself. If it can't, a second, deliberately simpler "sell-only" computer takes over within about 30 seconds without a human. Pre-signed emergency sells are **banned**, because a stolen copy could be used against us.
- **We won't race other bots at graduation.** We buy after Pump's 5-minute BOOST buying ends, and only when the quick sellers have left. If other careful bots crowd that same moment, a rule fixed today sends us back to paper trading.
- **The money, in one table:** about **$275 a month** in bills (range $213–604). A trade costs about 3.2–4.9% of the bet in fees and price impact. With a 25 SOL wallet and 0.25 SOL bets, the bot must earn about **7–10% per trade** to pay its own bills. With 50 SOL and 0.5 SOL bets, it needs about **6–7%**. No rule has shown that yet. The default stays paper.

**Tags.** [VERIFIED-DOC] = primary source read this session or by a teammate this session (URL given). [VERIFIED-SEARCH] = search results only. [UNVERIFIED] = inference or judgment, with the test that would settle it. [DERIVED] = arithmetic on tagged inputs. Teammates' files are cited as RSK-R, SEC-R, EXE-R, DAT-R, CHN-R, QNT-R, AI-R, SOC-R (`team-debate/round2/<role>-response.md`), RT-A (`red-team-attacks.md`) and RT-R (`red-team-recheck.md`). I used 4 web searches this round (sources at the bottom). The shell network is still blocked, so I ran no live tests.

**How I ruled.** Paul's four priorities, in order. When two options were equally safe, I chose the cheaper one. When they were also equally cheap, I chose the one that is simpler to log and explain. When a choice depends on a number nobody has measured, I picked the safe default and named the test that can overturn it.

---

## 1. The six rulings the coordinator asked for by name

### R1. The guard host as a single point of failure (SEC-3, NEW-1, C2)
**Options.**
- (a) **Security (SEC-R):** cold standby. Paul clicks "launch standby" if the guard dies.
- (b) **Risk (RSK-R):** fully automatic standby, plus pre-signed emergency sells held by an outside watchdog.
- (c) **Red-team (RT-R NEW-1):** a process supervisor, EC2 auto-recovery, a 60 s outside heartbeat that alerts Paul, and a minimal sell-only safe mode. The cold standby is only for loss of a data centre.

**Ruling: four automatic layers, none of which needs Paul.**

| Layer | What happens | Target time | Can it buy? |
|---|---|---|---|
| 0. Supervisor | The guard runs under a process supervisor with a watchdog ping. On a crash it restarts, reads the chain and its journal, and re-arms every exit first | Under 10 s | Yes, after reconciliation passes |
| 1. Crash loop → safe mode | 3 restarts in 10 minutes switch the host to the **safe-mode seller** (below) instead of the full guard | Under 60 s | No |
| 2. Hardware loss | EC2 auto-recovery restarts the same instance on new hardware, with the same disk and identity [UNVERIFIED for t4g; test G1] | Minutes | Yes, after reconciliation |
| 3. Warm standby | A second small instance in another Frankfurt zone runs **only the safe-mode seller**. Both instances write a heartbeat to a shared lease record inside the guard's AWS account (outbound calls only, no open ports). If the guard's heartbeat is older than 20 s, the standby takes the lease and manages exits | Under 30 s | **Never** |
| 4. Outside watchdog | Both instances push a heartbeat every 15 s to a dead-man's-switch alert service on a third provider. If both go silent for 60 s, Paul's phone gets a plain-English alert | Under 90 s | n/a |

**The safe-mode seller is deliberately different code.** It is a small, separately tested program that only: reads our held positions from the chain, prices them from its own Helius stream, and sells on the hard stop, the trailing stop, the time exit, Pump's "selling reopened" moment, or Paul's FLATTEN lever. It has no buy code. This answers red-team's sharpest point (NEW-1): the likeliest failure is a bug in our own guard, and a standby running the same code would share it.

**Why automatic takeover is safe here.** The usual danger with two live guards is double trading. The standby can only sell. A sell "of my current balance" limits itself: once the tokens are gone, a second sell fails and costs only its network fee (EXE-R EXE-1) [VERIFIED-SEARCH via EXE-R]. So the worst case of both guards acting at once is one wasted fee or an earlier exit than planned, never a lost position and never an extra buy.

**After a takeover**, buys stay paused until Paul taps "resume" on a one-line incident note. Takeovers should be rare, and missed trades cost nothing (priority 1 beats missed trades).

**Drill (pass marks fixed now, paper mode, 3 open positions):**
1. Kill the guard process at random, 20 times. Positions are back under management within 10 s at p95, and any exit that was due completes within 60 s.
2. Stop the guard instance, 10 times. The standby holds the lease within 30 s at p95, and due exits complete within 60 s.
3. Feed the guard an intent that crashes it. Safe mode is running within 60 s.
4. Kill both instances. Paul's phone alert arrives within 90 s.

**What's left: ACCEPTED RISK.** A Frankfurt-wide AWS or KMS outage stops both instances. KMS publishes a 99.999% monthly uptime target, about 26 s a month [VERIFIED-SEARCH aws.amazon.com/kms/sla via SEC-R]. Exposure is capped at 3% of the bankroll (3 positions × 1%). If test S2 shows that Ed25519 keys support multi-Region replicas, the standby moves to a second region.

### R2. Sell-path auto-adoption after a mandatory Pump change (SEC-6, NEW-7, SEAM-3)
**Options.**
- (a) **Security (SEC-R):** the tolerant allowlist accepts *added* instructions. A *mandatory* new account still needs an IDL review and Paul's OK.
- (b) **Red-team (NEW-7):** auto-adopt for sells only, if the new accounts are seed-derived addresses or fixed program IDs.
- (c) Do nothing: sells fail until a human reviews.

Pump made two new accounts mandatory on Sep 1 2025, and integrations broke [VERIFIED-SEARCH t.me/s/pump_tech_updates/29 via RT-A].

**Ruling: (b), with tighter checks. Sells auto-adopt within minutes. Buys always wait for review.** A new sell layout is adopted only if **all** of these hold:
1. **Source.** The new IDL comes from Pump's official repository (`github.com/pump-fun/pump-public-docs`, main branch), and at least one of these is true: our current sell fails with an account error, or the program's on-chain deploy slot has changed.
2. **Only additions.** The diff only *adds* accounts to sell instructions. It adds no new instruction arguments, removes nothing, and adds no new signer.
3. **Every added account is predictable.** It is either an address derived from seeds written in the IDL, using only constants and accounts already in the instruction, or a fixed address or program ID written in the IDL.
4. **Simulation agrees.** A read-only simulation of the new sell against current mainnet state succeeds. It shows tokens leaving only our token account, and SOL arriving only in our wrapped-SOL account or wallet. The only other balances that change are the pool vaults and Pump's fee accounts named in the IDL. (In live operation this is a read-only RPC call. Nothing is signed for it. During design work we replay history instead.)
5. **Two providers agree.** Two of our three RPC providers derive the same addresses.

If all pass, the guard and the safe-mode seller use the new layout for sells, alert Paul and the team, and the team reviews it within 24 h. If any check fails, the guard keeps trying the old layout, alerts, and a human reviews. A **new Pump program ID** is never auto-adopted.

**Why.** A missed sell costs more than a bad one (RSK-R). Sells already can't steal, because the guard pins every output to our own accounts (SEC-R). Check 4 is the strongest guard against a hostile or mistaken diff, because the simulation shows the exact balance changes. Buys stay strict: buying is where theft-by-trade lives (SEC-R).

**Drill (RC8, pass marks fixed):** replay the Sep 1 2025 change. The rule must adopt it. It must also refuse five made-up hostile diffs: an added writable account that isn't derived from seeds, an added signer, a changed output account, a new program ID, and a removed account.

### R3. The guard refusing honest sells on a stale quote (NEW-2, NEW-3)
**The problem.** The guard checks the bot's lowest acceptable price ("min-out") against its own RPC quote. In a crash its RPC may lag, so its quote is too high and the bot's honest min-out looks "too loose".

**Options.**
- (a) **Security (SEC-R):** the guard's own quote rules.
- (b) **Red-team (NEW-2):** use the freshest slot-stamped state from any source, accept min-out down to `max(catastrophic floor, freshest quote × (1 − m_emergency))`, and never refuse two sells in a row on price alone.

**Ruling: the guard owns min-out for sells, and it computes it from the freshest state it can check itself.**
1. A SELL intent from the bot names the coin, the reason and a *suggested* min-out with the slot of the state it used.
2. The guard prices from its own sources. Those are its own Helius stream of held pools (C9) and a fallback poll on a second company's RPC. If the bot's state is newer by slot, the guard immediately re-reads both of its providers (about 1 slot). It never takes the bot's numbers on trust, because a hacked bot host could feed fake low prices to set up a sandwich.
3. min-out = the guard's freshest quote × (1 − m), where m is execution's margin (1–5% normally, 3–15% in emergencies) (EXE-R EXE-3).
4. **The guard never refuses two sells in a row on price.** After one disagreement it sends on its own fresh numbers. If the price has already fallen further, that sell fails on-chain, which costs only base and priority fees, and the 2-block chase re-quotes it (EXE-R §1a).
5. **The re-quote interval is the larger of 2 slots and the measured guard loop p99 plus 1 slot** (NEW-3). The loop is bot → tunnel → guard quote → KMS → send. KMS timing is test S1 / RC9. Price-triggered exits fire from the guard's own stream, so they skip the bot-to-guard hop entirely.

**Why.** This keeps the theft bound (a fake price can't loosen min-out) and removes the freeze (a disagreement causes at most one slot of delay, never a refusal). **Test RC2 (pass mark):** over 50 recorded crashes, the guard's own stream lags the bot's Chainstack stream by 2 slots or less at p95. If not, the guard gets a second stream before any canary.

### R4. Pre-signed emergency sells versus the durable-nonce ban (C1, NEW-5, NEW-6)
**Options.**
- (a) **Risk (RSK-R):** "pre-signed emergency sells" (PSES). The guard keeps two signed whole-balance sells per position, with lowest prices of 50% and 10% of value. They sit on durable nonces (a stamp that keeps a signed transaction valid until used), and an outside watchdog holds copies.
- (b) **Security (SEC-R):** durable nonces refused.
- (c) **Execution (EXE-R):** rolling 30 s "exit tickets" (signed sells on a normal expiry, refreshed every ~20 s, only while a position is near a stop).

**Ruling: durable nonces stay banned in v1. Exit tickets are allowed, but only as cover for short signer blips. PSES is rejected.**

**Why PSES is rejected (priority 1, security mistakes):**
- **A copy is a weapon.** With a 10% min-out, whoever holds a copy can push the price down first and then fire it, taking up to ~90% of the position (NEW-5) [DERIVED].
- **More places to steal from.** Copies held on a third provider are a new target.
- **Old copies come back to life.** A durable-nonce transaction never expires, so re-buying the same coin can revive an old copy.
- **The feature is going away.** Solana plans to remove durable nonces about 6 months after a replacement ships [VERIFIED-SEARCH solana.com/upgrades/durable-nonce-deprecation via RT-R].
- **Most of the need is gone.** R1 now covers a dead guard automatically.

**Exit tickets are low risk.** They live only in the guard's memory and are never copied off the host. They expire within about 30 s, carry a tight min-out, and pay only into our own accounts. If the guard host is hacked, the attacker has signing anyway, so tickets add nothing to the theft risk. They fail in a fast crash (NEW-6), so they count only as **cover for signer blips**, never as crash protection.

**What would reopen PSES.** All of these must hold: the 60-day paper drill log shows guard-and-standby downtime above 60 s more than twice; durable nonces are still supported; and the design follows red-team's narrow version (one rung, min-out of at least 50% of value at signing, nonce advanced on every close, copies only on the guard host). Even then, Paul decides.

### R5. Crowding at the BOOST cliff (NEW-11, NEW-12), with a kill rule fixed now
**Options.**
- (a) **The specialists:** enter after BOOST ends, on events (RSK-R, CHN-R, DAT-R, QNT-R).
- (b) **Red-team:** the same moment is public on-chain (`boost_vault_remaining` [VERIFIED-DOC pump_amm.json via RT-R]), and bots know the 5-minute window [VERIFIED-SEARCH htx via RT-R]. It may become the next crowded race. Patient insiders can wait and sell into the careful buyers.

**Ruling: enter on state, add random jitter, measure crowding on every entry, and kill on a rule written today.**
1. **Entry on state, not on the clock.** The rules in §3 (C14) use BOOST state, net flow and the sellers' remaining tokens. When a condition first becomes true, the bot waits a **random 0–15 slots (0–3 s)**, re-checks the condition, then sends. The decision is minute-scale, so jitter costs almost nothing, and it stops us being a fixed pattern others can trade against.
2. **The crowding measure (fixed now).**
   - *Calm baseline:* rival buy transactions (landed plus failed, excluding BOOST's own and ours) per slot, and their median priority fee per compute unit, in this pool over the window from 70 s to 10 s before our trigger.
   - *Crowded entry:* in our landing slot ±2 slots, rival buys ≥ max(3, 3 × the baseline rate × 5 slots), **or** the median rival priority fee ≥ 3 × the baseline median.
   - *Arrival penalty:* our fill price against the pool price 10 s before the trigger.
3. **Kill rule.** Over any rolling 14 days with at least 50 entries, if **crowded entries exceed 30%**, *or* **the median arrival penalty exceeds 1.5%**, the rule goes back to paper (if it is in canary or live) or fails its gate (if it is in paper). At 20% crowded, an early warning goes into Paul's daily summary.
4. **The "insiders held through BOOST" variant is dropped** from the entry family. It rewards exactly the patient insider red-team describes. The forensics rule keeps only "overhang below 3%".
5. **BOOST may change or stop (NEW-12).** The engine branches on `boost_enabled` in GlobalConfig and on whether this pool shows BOOST events (`toggle_boost` exists [VERIFIED-DOC pump_amm.json via RT-R]). A coin with no BOOST is a different market. It is traded on paper only, as its own group. BOOST switched off globally counts as a market-structure change: buys pause in canary or live, and quant's fast re-validation applies (QNT-R §1d). The BOOST amount is read from events, never assumed to be 17.6 SOL. A July-era search found no BOOST change reported since launch [VERIFIED-SEARCH kucoin, theblock; search on 2026-11-05].

### R6. One joint cost and break-even table (NEW-10, PREMISE-7, C4, C5, SEAM-7)
**Options.**
- (a) **Risk:** $150 a month of bills, 600 trades a month.
- (b) **Quant:** $300 a month.
- (c) **Security:** a daily buy cap of about 6 trades.
- (d) **Red-team:** a bottom-up $225–360. That sum left out the bot's own server.

**Ruling: one bottom-up table, below, including the bot host and the guard pair. The daily buy cap is set so it doesn't starve the strategy, and the theft risk it bounds is stated plainly.**

**6a. Monthly bills (USD)**

| Item | Starts in phase | Low | Expected | High | Tag |
|---|---|---|---|---|---|
| Chainstack Growth + Yellowstone gRPC add-on (2 streams) | 1 | 98 | 98 | 215 if D4 forces a switch to Solana Tracker (€200) | [VERIFIED-SEARCH chainstack.com/pricing, /products/yellowstone-grpc; DAT-R] |
| Helius Developer (10M credits) | 1 (free tier in 0) | 49 | 49 | 49 | [VERIFIED-SEARCH helius.dev/docs/billing/plans] |
| Helius autoscale overage ($5 per 1M, capped at 5M) | 3 | 0 | 0 | 25 | [VERIFIED-SEARCH via DAT-R] |
| Bot host (recorder, decoders, strategy, paper, research) | 1 | 24 | 48 | 120 | low/expected [UNVERIFIED shared-CPU tiers]; high [VERIFIED-SEARCH spendark: 4 vCPU/16 GB general-purpose $120–126, US regions] |
| Recorder disk (200 GB) + archive storage | 1 | 10 | 15 | 30 | [UNVERIFIED; DAT-R] |
| Guard + sell-only standby + KMS + alarms (AWS Frankfurt) | 3 | 22 | 25 | 35 | t4g.small ~$14 [VERIFIED-SEARCH via SEC-R]; standby and alarms [UNVERIFIED]; KMS ~$1 [VERIFIED-SEARCH via SEC-R] |
| AI (Anthropic API) | 1 (reader only) / 2 | 10 | 40 | 75 = Console hard cap | [DERIVED from AI-R §1c] |
| Social (X counts and sample) | only if S1 passes | 0 | 0 | 45 (= $1.50/day cap) | [DERIVED from SOC-R] |
| Alert and dead-man's-switch service | 3 | 0 | 0 | 10 | [UNVERIFIED] |
| **Total, Phases 1–2 (recorder + research)** | | **191** | **250** | **534** | [DERIVED] |
| **Total, Phase 3 onward (adds the guard pair and autoscale)** | | **213** | **275** | **604** | [DERIVED] |

- **One-offs:** X history test S1 $10–20 (only with Paul's yes). Dune ~$75 (skipped by default, QNT-R §2).
- **Not counted:** Paul's own Claude subscription for the design team.

**Flagged as able to blow up, and the cap on each:**

| Risk | Cap |
|---|---|
| Helius metered credits | Local meter plus the $25 autoscale cap |
| AI | Console spend limit plus 3,000 label calls a day |
| X | Daily cap of $1.50 |
| Storage | Disk alarms at 70/85/95% plus archiving |
| Chainstack throttling our data | +$117 if we must switch providers |
| Second firehose for redundancy (~$200) | Not adopted (DAT-2 accepted risk) |
| LaserStream $499, a racing stack ~$2,000+ | Rejected unless the reopen rule passes (C15) |

**6b. Cost per trade** (one buy and one sell; SOL ≈ $100 [VERIFIED-SEARCH mexc via EXE-R]; 85 SOL pool; the fee and transaction numbers are the settled EXE-R §1b/§1c table; 30% crash exits is an [UNVERIFIED] mix assumption)

| Stake | Pump fee (2 × 1.25%) | Price impact (≈ 2 × size ÷ 85) | Network + tips, calm / crash | Sandwich allowance (crash) | **Total calm** | **Total crash** | **Blended (70/30)** |
|---|---|---|---|---|---|---|---|
| 0.25 SOL | 2.50% | 0.59% | 0.13% / 1.64% | 0.2% | **3.22% ($0.81)** | **4.93% ($1.23)** | **3.73% ($0.93)** |
| 0.5 SOL | 2.50% | 1.18% | 0.07% / 0.82% | 0.2% | **3.75% ($1.87)** | **4.70% ($2.35)** | **4.04% ($2.02)** |
| 1.0 SOL* | 2.50% | 2.35% | 0.03% / 0.41% | 0.2% | **4.88% ($4.88)** | **5.46% ($5.46)** | **5.05% ($5.05)** |

\*1.0 SOL is allowed only with a bankroll of at least 100 SOL **and** a pool of at least 100 SOL (1% caps, C7). Above ~0.6 SOL, our own price impact makes bigger bets *dearer* per SOL [DERIVED].

**6c. The daily buy cap, the bills and the break-even gain** (expected bills $275 a month; "break-even" = blended per-trade cost + bills ÷ turnover)

| Stake | Trades a day (live, after the cap) | Bills share of turnover | **Break-even gain per trade** |
|---|---|---|---|
| 0.25 SOL (25 SOL bankroll) | 3 | 12.2% | **16.0%** |
| 0.25 | 6 (security's 1.5 SOL/day example) | 6.1% | **9.8%** |
| 0.25 | 10 | 3.7% | **7.4%** |
| 0.25 | 20 | 1.8% | **5.6%** |
| 0.5 SOL (50 SOL bankroll) | 6 | 3.1% | **7.1%** |
| 0.5 | 10 | 1.8% | **5.9%** |
| 0.5 | 20 | 0.9% | **5.0%** |

At 10 trades a day, the low ($213) and high ($604) bill cases give break-evens of 6.6% / 11.8% at 0.25 SOL, and 5.5% / 8.1% at 0.5 SOL [DERIVED].

**Decisions from this table:**
1. **The daily buy cap is 10% of the bankroll per rolling 24 h, in SOL** (10 buys at the floor). It is enforced on the guard host and can only be loosened there, with a 10-minute delay. At a 25 SOL bankroll that is 2.5 SOL a day. Security's 1.5 SOL example would force a ~10% break-even and starve the strategy. **The honest cost:** if the bot host is hacked, the worst day loses about 10% of the bankroll (bought attacker coins), not 6%. That is a question for Paul (Q8 in QUESTIONS_FOR_PAUL.md); the default is 10%.
2. **The hot wallet** holds at most the daily cap + open exposure (3%) + fee and exit reserves. That is about 3.3 SOL at a 25 SOL bankroll. The guard sweeps anything above that to Paul's cold address. **Losses that drain the hot wallet need Paul to top it up**, which is a natural circuit breaker.
3. **Two different bars.** The trade-level gate (Gate v2) asks: does a trade beat its own per-trade costs? The desk-level check, before live, asks: does profit at the *capped* trade count beat the bills? Both are reported. Bills are mostly research costs that exist whether or not we trade.
4. **Paid extras stay off until they earn** (X, Haiku labels at scale, a second firehose, LaserStream).

**6d. Helius credit budget, including the guard (SEAM-7, DAT-5)** [DERIVED from DAT-R, CHN-R, RSK-R; credits per method UNVERIFIED until P12/D15]

| Consumer | API key | Normal (M/month) | Worst (M/month) |
|---|---|---|---|
| Migration backup stream, slot heads, canonical-pool follow-up | bot | 0.03 | 0.05 |
| Silent-feed probe | bot | 0.09 | 0.9 |
| Migration audit | bot | 0.09 | 0.1 |
| Forensics (hard cap 100k/day) | forensics | 0.6 | 3.0 |
| Backfill after outages | bot | 0 | 1.0 |
| Block capture around migrations (prefer Chainstack's RPC allowance, G4) | bot | 0 | 1.0 |
| Guard stream of held pools | guard | 0.03 | 0.3 |
| **Guard fallback poll reserve (untouchable)** | guard | 0 | 2.6 |
| **Total** | | **≈ 0.85** | **≈ 8.95** |

- **Margin:** 10M are included [VERIFIED-SEARCH helius.dev], and autoscale at a $25 cap adds 5M.
- **The meter's rules:**
  - At 6M used, the optional consumers stop: block capture, backfill and the `funded-by` accuracy checks.
  - The guard reserve is never spent by anything else.
  - The guard's healthy-time cross-check poll runs on Chainstack's RPC, a different company, so it uses no Helius credits.
  - **Without autoscale** (if Paul says no), the optional consumers stop at 5M and the forensics cap drops to 60k/day.
- **This ends the 2.5M-versus-4M disagreement:** forensics is bounded at 3M by its own daily cap.

---

## 2. The 17 contradictions (C1–C17)

| # | Topic | Options and who argued them | **Ruling** | Why (priorities) |
|---|---|---|---|---|
| C1 | Emergency sells when the guard or KMS is down | Risk: PSES on durable nonces. Security: ban. Execution: 30 s exit tickets | **Ban durable nonces. Exit tickets for signer blips only. R1's automatic layers** (see R4) | P1: a stolen copy can be used against us; R1 covers the need |
| C2 | Guard standby | Security: cold, Paul clicks. Risk: automatic | **Automatic, sell-only safe-mode standby; buys resume only on Paul's tap** (see R1) | P1: nothing waits for a sleeping human; sell-only makes double action harmless |
| C3 | Bankroll for 0.25 SOL bets | Risk: 1% cap → ≥25 SOL. Execution: 0.5% → 50 SOL | **Live needs at least 25 SOL (1% per trade). Sizing ideas (RSK-E1, RSK-E3) act only at ≥50 SOL; below that, RSK-E1 is tested as a skip filter.** Paul decides the bankroll; default paper | P1: ruin is ~0 at ≤1% per trade even for a losing rule (RSK-R §1.2 [DERIVED]). The 50 SOL figure buys room to size, not safety |
| C4 | Trades per month | Risk/quant: 600. Security: cap ≈ 6/day | **Cap = 10% of bankroll per 24 h (10 floor-size buys). Paper isn't capped for research power; the constrained paper bot runs with the live caps** (R6) | P1 and P3: a 6/day cap pushes break-even to ~10% and starves the test |
| C5 | Monthly bills | Risk $150, quant $300, red-team $225–360 | **$275 expected ($213–604), bottom-up, including the server** (R6) | Honesty: the earlier sums missed the bot host |
| C6 | Take-profit below 0.5 SOL | Risk: one step (sell ½). Execution: no ladder | **Incumbent: no ladder below 0.5 SOL. Risk's one step is contestant #2 in the exit tournament** | P3/P4: cheaper (~0.12% less [DERIVED RSK-R]) and simpler to log. The tournament (~200 paired coins a day) settles it within weeks. I depart from red-team's suggestion only on which rule is the *default*; both get tested |
| C7 | Max share of the pool | Risk 1%, execution 1.5% | **1% until the canary measures our real impact** | P1: the impact maths is unverified (negative virtual reserves, fees kept in the vault) |
| C8 | Slot time | Execution 200 ms; data 0.2–0.4 s; security/risk 350 ms | **Execution is right: 200 ms target, ~218 ms measured** [VERIFIED-SEARCH solanacompass via RT-R]. Every timer is written in **slots** and measured live (D6). Blockhash life ≈ 150 slots ≈ 33 s [UNVERIFIED, X3] | P1: timers in slots survive further speed changes |
| C9 | Where the exit data sources run | Data: A = Chainstack gRPC, B = Helius WSS. Security: guard has "two RPCs, no feeds" | **The guard subscribes outbound to its own Helius stream** (`transactionSubscribe` and `accountSubscribe` on held pools, both vaults, GlobalConfig) with its own API key. Fallback poll on Chainstack's RPC, then the public RPC. Chainstack gRPC stays on the bot host | P1: price and flow exits survive a dead or hacked bot host; two companies feed the guard directly |
| C10 | Where insider exits run | Risk/forensics: in the guard. Security: minimal guard | **The bot host computes insider-flow, taint and cluster exits and sends SELL intents. The guard always honours a SELL intent (with its own min-out) but never depends on them.** The guard runs price stops, trailing stop, time exit and pool-level `EXIT_SELL_PRESSURE` from its own stream | P1: the guard stays small and auditable. A hacked bot host can withhold advisory exits (ACCEPTED; the guard's stops still bound the loss) |
| C11 | Seeing plain token transfers | Forensics: Helius `transactionSubscribe` (≤50k addresses). Data: Chainstack `token_accounts` + Helius mint `programSubscribe` | **Both, at different layers.** (1) Held coins (≤3): Helius `programSubscribe` on both token programs filtered by mint. Account updates show every holder's balance change, plain transfers included. (2) Candidates: wallet-based watch of insider wallets' token accounts. Test F2/D13 picks Chainstack (`token_accounts`, cuckoo filter) or Helius `transactionSubscribe`. (3) The Token-2022 program goes into the firehose only if D11's bandwidth fits | P2: no blind spot on held coins. SOL funding of side wallets stays an RPC lookup (ACCEPTED gap) |
| C12 | "Still positive with the top 5% removed" | Quant: report only. Others: hard pass | **Hard for filters and exits. For entries: at least 20 tail wins, and top-3-removed ≥ 0** (red-team's split) | P1: filters and exits must help typical trades, not ride luck. Entry rules in meme coins legitimately rely on rare big winners, but we need enough of them to trust the rate |
| C13 | Dump label | Four teams, four labels | **Frozen now, one per purpose (§4)** | P4: one label per question stops after-the-fact label shopping |
| C14 | Default entry rule | Risk: BOOST over + 180 s + net flow. Forensics: Rule C. Quant: flipper < 20%. Data: fast group ≤ 25%. Execution: auction cooled | **Paper incumbent = risk's rule** (needs no insider ledger, so it can run from day 1). **Primary challenger = the merged "sellers exhausted" rule.** The other three are named variants in one trial family (§4, NEW-15) | P1/P2: the simplest working rule runs first; the rest compete under one error budget |
| C15 | Reopening the race | Data +5 pts; execution +10%; risk +5% on ≥300 coins without the top 5%; quant's four-condition rule | **Quant's four conditions + risk's sample (≥300 post-BOOST graduates for the rule, ≥1,000 for the lateness curve) + the top-5%-removed test.** Racing also needs Paul's OK for a separate racing wallet (local key, 1–2 bets, treated as already lost) | P1: racing brings a riskier key setup, so it gets the strictest bar |
| C16 | PumpPortal key | Data: never. Security: Paul may create a ≤0.05 SOL prepaid wallet | **Never create a PumpPortal key.** Keyless channels only, or drop PumpPortal | P1: the key comes with a wallet key someone else generated. PumpPortal is only the fourth audit, so its value is low |
| C17 | Metadata scope | AI: all ~30k launches a day. Social: fetch at 20% of the curve | **Free create-event fields (name, ticker, URI, creator) for every launch. The metadata file is fetched once at 20% of the curve, through one sandboxed gateway with size and time limits. Image hash for every fetched file.** Fetch time is stored next to creation time | P2/P3: the wave detector needs every launch's name, which is free. Fetching 30k files a day is costly and unsafe. Attacker-written text never reaches the AI unfiltered |

---

## 3. The other new attacks (NEW-1 to NEW-18)

| ID | Ruling | Status |
|---|---|---|
| NEW-1 | R1 (four layers, sell-only safe-mode standby, drills) | **FIXED**; region-wide outage ACCEPTED (≤3% exposure) |
| NEW-2 | R3 (guard owns min-out from its freshest own state; never refuses twice; chase) | **FIXED**; RC2 confirms |
| NEW-3 | R3 point 5 (re-quote interval from measured loop p99; price exits from the guard's own stream) | **FIXED**; S1/RC9 measure |
| NEW-4 | C9 + C10 | **FIXED**; withheld advisory exits ACCEPTED |
| NEW-5 | R4 (PSES rejected) | **FIXED by rejection** |
| NEW-6 | R4 (exit tickets = signer-blip cover only) | **ACCEPTED** with that limited role |
| NEW-7 | R2 (sells-only auto-adopt with simulation; buys reviewed) | **FIXED**; RC8 drill |
| NEW-8 | Decoders keep a list of **allowed lengths per account type and version**. A shorter, older layout is legal and its missing trailing fields read as 0 [VERIFIED-DOC PUMP_SWAP_README via RT-R]. An unknown length is a shape alarm. Events keep exact lengths per discriminator and version. **`virtual_quote_reserves` is decoded as a live signed value and price uses vault + virtual** [VERIFIED-DOC NEGATIVE_VIRTUAL_QUOTE_RESERVES.md via RT-R]. The dormant-field alarm no longer covers it. The two-witness check (DAT-R) validates the result on every trade | **FIXED**; RC3/RC4 measure |
| NEW-9 | **Alarm severity classes.** *A (money safety):* decoder shape, two-witness failure, admin change, program upgrade, unknown wallet outflow, unexplained SOL gap > 0.001. Buys pause; resume after the team's review, regenerated decoders, then 1,000 clean *market-wide* trades (minutes, not days) and 30 quiet minutes. In live phases Paul also taps resume. *B (data health):* feed behind or stale, coverage miss. Buys pause and auto-resume after 60 s healthy. *C (info):* budget thresholds, a single refused intent. Daily digest only. Every new monitor runs log-only for 7 days first (RC5). Target: on average no more than one phone alert a week in calm periods | **FIXED**; RC5 calibrates |
| NEW-10 | R6 | **FIXED** |
| NEW-11 | R5 (state + jitter + crowding measure + kill rule) | **FIXED** (kill rule fixed now); RC1 measures |
| NEW-12 | R5 point 5 (branch on BOOST state; no-BOOST coins paper only; global off = market-structure change) | **FIXED** |
| NEW-13 | Before any canary, risk re-runs the ruin simulation by **resampling whole days** of the recorded null. If ruin (a 50% fall) exceeds 1% at 1% per trade, the drawdown and daily limits are tightened before Gate 3→4 | **FIXED** (Phase 2 deliverable) |
| NEW-14 | Trial families with fixed error budgets that reset only on fresh data (§4) | **FIXED** |
| NEW-15 | One "sellers exhausted" family: a primary rule plus named variants, one pass mark (§4) | **FIXED** |
| NEW-16 | Q2/D11/RC6 first. The 8 Jito tip accounts are **not** streamed by default. Tips are captured by fetching full blocks for the 20 slots after each migration and around each paper order, on whichever provider's included allowance has room (G4). The Token-2022 stream is added only if D11 fits | **FIXED** (design); measured in Phase 0 |
| NEW-17 | **Control path.** The levers (RUN / PAUSE BUYS / STOP / KILL) live in one parameter inside the guard's own AWS account. The guard reads it outbound every 2 s. Paul changes it in the AWS console, which is protected by a hardware security key. Tightening takes effect at once; loosening waits 10 minutes and alerts. The bot host can request PAUSE only, never loosen. A CloudTrail alarm fires on any `Sign` call from a role other than the guard or standby roles. The tripwire's credential can only `DisableKey`, and re-enabling needs Paul. **ACCEPTED:** a stolen tripwire credential can freeze exits (a denial of service, not theft); positions wait, ≤3% exposure, alert fires. Whoever controls the AWS account controls the key, so the root login stays with Paul alone, with hardware MFA | **FIXED** + ACCEPTED residual |
| NEW-18 | QUESTIONS_FOR_PAUL Q4–Q6: bankroll, tuition budget, canary. Default: paper only | **QUESTION for Paul** |

---

## 4. The rules for honest testing (C13, NEW-14, NEW-15), frozen today

### 4a. Labels, one per purpose (C13). Changing one creates a new version and costs a trial ticket.

| Label | Definition | Used by |
|---|---|---|
| `DUMP60` | Within 60 min of the decision, the price falls to ≤ −50% of the decision price **before** it ever reaches +50% | AI labels, the wave detector, forensic vetoes, CHN-A's AUC |
| `INSIDER_DUMP` | A `DUMP60` where ≥40% of the SOL sold between the decision and the low came from the insider set *as it stood at decision time* | CHN-A, RSK-E1 |
| `RUG` | ≤ −80% within 60 min, with half the drop inside 3 slots | Stop calibration, gap study (R1 test) |
| `FAST_DUMP` | ≥ −30% within 60 s | Exit-warning tests (DAT-E3), the crash replays (EXE-E2, RC2) |

### 4b. Trial families and error budgets (NEW-14)
**The fix for "the counter fills up in two months":** budgets are counted **per family, per fresh data window**. Data that a family has used for a test is spent for that family. A new 4-week window of data no family test has touched gets a fresh budget. On top of that, a rule must pass **three independent stages**: a research test on the tape, then Gate v2 on forward paper trades, then the canary. That keeps false discoveries rare without freezing research.

| Family | Tickets per window | Error budget (one-sided) | Confidence each ticket needs |
|---|---|---|---|
| F1 Entry ("sellers exhausted") | Primary rule 5%; 3 named variants share 5% | 10% | Primary 95%; each variant ≈ 98.3% |
| F2 Exits (tournament) | Best challenger vs incumbent 5%; 2 per-type promotions at 2.5% each | 10% | 95% / 97.5% |
| F3 Regime (thermometer) | 1 | 10% | 90% |
| F4 Filters and features | 7: CHN-A taint, CHN-B crew, wave (SOC-E1 + AI-E1), KOL bait, losers' tape, RSK-E1 as a filter, X spread shape | 10% | ≈ 98.6% each |
| F5 AI desk rules | Each AI rule entering shadow in a quarter (≤60) shares 5% | 5% | ≥ 99.9% each. Separately, the placebo comparison decides whether the desk exists at all (AI-R E2: Fisher one-sided p < 0.05) |
| F6 Race reopen | 1 | 5% | 95%, plus C15's conditions |
| Reserve | 2 spare tickets per family per window | taken from the family's budget | The family's smallest per-ticket share |

Gate v2 (QNT-R §1c) stays as written, applied to the single champion on fresh forward paper data (one ticket, 90%), **plus** the pessimistic view above 0.

**Gate power, stated plainly for Paul (QNT-4).** Suppose a trade's result swings by ±100% (one standard deviation). Then 200 trades can only prove an edge of about 15% per trade. A realistic 5–8% edge needs about 600–1,800 trades [DERIVED, QNT-R §1c]. **Ruling:** the expectancy test counts the **unconstrained paper twin**, which takes every qualifying entry and has no position cap. Drawdown, caps and operations are judged on the constrained bot that copies live limits. The desk-level economics use the constrained count. This makes the gate reachable in months rather than a year, without changing which coins count.

### 4c. The merged entry family (NEW-15): one pass mark for all of it
- **Incumbent (paper default):** BOOST over (vault at 0, or no BOOST event for 30 s) + 180 s settle + net SOL flow over the last 60 s ≥ −2% of the pool + jitter (RSK-R).
- **Primary challenger:** BOOST over **and** the fast group (the completing buyer, block 0–3 buyers, and everyone they passed tokens to) plus the insider set together hold ≤25% of their peak (DAT-E1 + CHN-C + QNT-E2) + jitter.
- **Named variants:**
  1. flipper clock below 20% of peak overhang (QNT-E2);
  2. Rule C: insider overhang below 3% + no new low for N blocks + organic net buying positive (CHN-C, without "held through BOOST");
  3. auction cooled (EXE-E1).
- **One pass mark (Stage B, after costs, last-in-block fills, base view):**
  - Fit on the first 300 post-BOOST graduates and test on the next ≥300, walking forward.
  - The rule's mean net per trade beats **both** the incumbent and the null at the same timing by **≥ 3 points**, with the day-block bootstrap lower bound above 0 at the family confidence.
  - The pessimistic view is above 0.
  - It has ≥20 tail wins and stays ≥ 0 with the top 3 trades removed (C12).
  - It qualifies on ≥5 entries a day or ≥30% of graduates.
  - It passes the crowding check (R5).
  - **Kill** if it is under +1 point against the incumbent at 2,000 graduates, or if the crowding kill fires.

---

## 5. The remaining "partly fixed / still open / not OK" items

| ID | Final ruling | Status |
|---|---|---|
| SEC-3 | R1 | **FIXED**; region outage ACCEPTED |
| PREMISE-2 | Only data can close it. The research queue in DESIGN.md §3 runs the top 5 first, with kill tests fixed in advance; the stop rule ends the spending if none passes | **OPEN by nature**, managed by the stop rule |
| SEAM-3 | R1 + R2 + R3 | **FIXED**; Pump's own sell switch ACCEPTED (EXE-5) |
| SEC-6 | R2 | **FIXED** |
| DAT-1 | NEW-8 ruling | **FIXED** |
| PREMISE-3 / QNT-1 | Losing Jito bundles never appear on-chain, so the 20% contested-landing figure is a guess. **ACCEPTED** with three limits: (1) by design we enter only on calm slots, which shrinks the exposure; (2) the pessimistic view must stay above 0; (3) the canary's "paper filled / live failed" gap must be ≤2 points per trade before live | **ACCEPTED**, measured by the canary |
| PREMISE-5 | Change classes and the fast path (QNT-R §1d), plus the BOOST branch (R5), plus a stop-rule clause: if two market-structure changes reset our clock before any rule finishes Gate v2, we pause and report | **FIXED** (process); pace of change ACCEPTED |
| PREMISE-7 | R6 | **FIXED** (honest table); the desk may still be unable to pay its bills, which the stop rule handles |
| SEAM-6 / DAT-3, CHN-2 | C11; test F2/D13 picks the provider; fallback Helius `transactionSubscribe` | **FIXED** (design); SOL-funding blind spot ACCEPTED |
| RSK-3 | Cluster insider flow (CHN-R) + the pool-level `EXIT_SELL_PRESSURE` backstop on the guard. F1 measures how dumpers got their tokens | **FIXED**; exchange-funded unlinked insiders ACCEPTED |
| CHN-5 | §4a | **FIXED** |
| QNT-4 | C12 + §4b (stated power, unconstrained twin) | **FIXED** |
| SEAM-7 / DAT-5 | R6 §6d | **FIXED** |
| RSK-8 | C9 | **FIXED** |

---

## 6. Ledger: every attack and its final state
All 81 Round 2a attacks plus the 18 new ones. "Fixed" means fixed in the design; every fix still needs its test or drill to pass in the build.

| Group | IDs | Final state |
|---|---|---|
| Premise | PREMISE-1, 4, 6 | FIXED (no race + shadow racer; baselines; AI cut to labels) |
| | PREMISE-2 | OPEN by nature → research queue + stop rule |
| | PREMISE-3 | ACCEPTED, measured by canary (§5) |
| | PREMISE-5, 7 | FIXED (§5, R6) |
| Seams | SEAM-1, 2, 4, 5, 8, 9, 10, 11, 12, 13 | FIXED (as in RT-R §1b; SEAM-9 strengthened by §4b; SEAM-12 needs test S7) |
| | SEAM-3, 6, 7 | FIXED by R1–R3, C11, R6 (residuals ACCEPTED as stated) |
| Data | DAT-1, 3, 4, 5, 6, 8, 9 | FIXED |
| | DAT-2 | ACCEPTED (degraded mode never buys; second firehose not worth $200 yet) |
| | DAT-7 | FIXED (C16); Paul confirms in Q9 |
| Forensics | CHN-1, 2, 3, 5, 6, 7 | FIXED |
| | CHN-4 | FIXED (cost); evasion ACCEPTED |
| Execution | EXE-1, 2, 3, 4, 6, 7, 8, 9 | FIXED |
| | EXE-5 | ACCEPTED: no bot beats Pump's sell switch; small size + "first out when it reopens" + Paul's manual-route question (Q7) |
| Risk | RSK-1, 2, 4, 5, 6, 7, 8 | FIXED (RSK-1 extended by R5) |
| | RSK-3 | FIXED + ACCEPTED residual (§5) |
| Quant | QNT-1 | ACCEPTED, measured by canary (with PREMISE-3) |
| | QNT-2, 3, 4, 5, 6, 7 | FIXED |
| | QNT-8 | ACCEPTED (stated to Paul in DESIGN.md risks) |
| AI | AI-1 to AI-6 | FIXED |
| Social | SOC-1, 2, 4, 5, 6 | FIXED |
| | SOC-3 | ACCEPTED (X data optional; missing = neutral) |
| Security | SEC-1, 2, 4, 5, 7, 8 | FIXED (SEC-8 latency still needs S1) |
| | SEC-3, 6 | FIXED by R1, R2 |
| New | NEW-1 to NEW-17 | As in §3 |
| | NEW-18 | QUESTION for Paul (Q4–Q6) |

Nothing has been silently dropped. Every accepted risk appears, with its size, in DESIGN.md §6.

---

## 7. Edge ideas: the final ranking
I adopt red-team's top five and its ratings (RT-R §4), with three changes:
1. **BOOST-cliff exit dropped.** The exit tournament no longer includes it, because our entries come after BOOST. That saves a ticket.
2. **"Held through BOOST" dropped** from the entry family (R5).
3. **SEC-E2 and AI-E3 adopted as tools, not edges.** KMS signing and the rule-change reader cost little and reduce losses.

| Rank | Idea | Role | Rating |
|---|---|---|---|
| 1 | Exit tournament (RSK-E2) with EXE-E2's chase and DAT-E3/CHN-A insider exits as contestants | Acts on every trade | STRONG |
| 2 | "Sellers exhausted" entry family (DAT-E1 + CHN-C + QNT-E2; EXE-E1 variant) | The entry | PLAUSIBLE, highest priority |
| 3 | Market thermometer (QNT-E3) | Whether to trade at all; silent-change alarm | PLAUSIBLE |
| 4 | Taint-tracked overhang (CHN-A) | Shared feature for 1, 2 and RSK-E1 | PLAUSIBLE |
| 5 | Theme-wave position (SOC-E1 + AI-E1), code-only first | The only off-chain input; recorded from day 1 | PLAUSIBLE |
| 6–9 | RSK-E1 sizing (filter below 50 SOL), CHN-B crew fingerprints, AI-E2 research desk with placebo, RSK-E3 grow-on-proof | Secondary | PLAUSIBLE |
| 10–15 | QNT-E1 losers' tape, SEC-E1, DAT-E2, SOC-E2 KOL bait, SOC-E3 X shape, AI-E3 as an edge | Test only if nearly free | WEAK |
| — | EXE-E3 (sell into BOOST) | Doesn't fit an after-BOOST entry | DEAD |

**Recorded from day 1 because it can't be backfilled honestly:**
- failed transactions;
- tips (block capture);
- each transaction's position in its block;
- our receive times;
- lookup tables used;
- create-event metadata;
- fetch times.

---

## 8. Tests to run once allowed (new this round; read-only)
| # | Test | Domain(s) |
|---|---|---|
| G1 | Does EC2 auto-recovery work for t4g instances in eu-central-1, and how fast? (docs, then a sandbox instance) | `docs.aws.amazon.com`, `ec2.eu-central-1.amazonaws.com` |
| G2 | Latency and conditional-write behaviour of the lease record and the lever parameter, read every 2 s from the guard | `dynamodb.eu-central-1.amazonaws.com`, `ssm.eu-central-1.amazonaws.com` |
| G3 | Helius `transactionSubscribe` on ≤3 pool addresses against the Chainstack gRPC stream: delay per update in a busy hour (extends RC2) | `mainnet.helius-rpc.com`, Chainstack gRPC host |
| G4 | Chainstack Growth's included RPC request allowance, and the cost of `getBlock` there (for block capture and the guard's cross-check poll) | `chainstack.com`, `docs.chainstack.com` |
| G5 | Can one Helius account hold separate API keys (bot / forensics / guard) with per-key limits? | `www.helius.dev` |
| G6 | Pick the dead-man's-switch alert service; confirm it accepts outbound heartbeats and sends phone push | vendor host to be chosen [UNVERIFIED] |
| G7 | The bot host's Frankfurt price and terms (trading bots allowed) for 2 candidate providers (not Hetzner, SEC R1) | e.g. `www.vultr.com`, `www.digitalocean.com` |
| G8 | Helius autoscaling setting and cap behaviour (confirms DAT-R's reading) | `www.helius.dev/docs/billing` |

All earlier tests (P1–P15, D1–D16, T1–T11, X1–X8, Q1–Q6, R1–R10, S1–S8, F1–F7, A1–A10, RC1–RC9) still stand. QUESTIONS_FOR_PAUL.md consolidates their domains.

## Sources (new this round)
- [VERIFIED-SEARCH] Chainstack Yellowstone add-on $49 for 2 streams, Growth plan required, Growth $49/month: https://chainstack.com/products/yellowstone-grpc/ ; https://chainstack.com/yellowstone-grpc-more-streams-same-price/ ; https://chainstack.com/pricing/ ; https://toolradar.com/tools/chainstack/pricing
- [VERIFIED-SEARCH] Helius Developer $49, 10M credits (effective Apr 7 2026); aggregator figures conflict and were ignored: https://helius.dev/docs/billing/plans ; https://www.helius.dev/docs/billing/plans.md ; https://costbench.com/software/blockchain-nodes/helius-rpc/hidden-costs/
- [VERIFIED-SEARCH] No BOOST change reported since the Jul 21 2026 launch (search 2026-11-05; absence is weak evidence): https://www.kucoin.com/news/flash/pump-fun-launches-boost-mode-to-reinject-dead-liquidity-into-token-market ; https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives ; https://onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering
- [VERIFIED-SEARCH] 4 vCPU / 16 GB general-purpose servers ≈ $120–126/month (US regions; Frankfurt not confirmed): https://spendark.com/compare/g-4vcpu-16gb-vs-voc-g-4c-16gb/ ; https://spendark.com/instances/voc-g-4c-16gb/
- Every other fact is cited from the round 1 and round 2 files named in the text, with their original tags.
