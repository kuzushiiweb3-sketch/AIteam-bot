# Round 2b: Risk manager response to the red team

## 0. In plain English (for Paul)
- **The red team was right: 0.05 SOL bets can't pay their costs.** At that size, fees and monthly bills eat 9–16% of every trade. The cheapest bet size is about 0.25–0.5 SOL, where all costs fall to about 4.5–5%. Each bet still stays at or under 1% of the wallet, so trading with real money needs a wallet of at least about 25 SOL. With less, the bot stays on paper.
- **Ruin stays very unlikely.** In our simulation, betting 1% per trade never lost half the wallet in 300 trades, even with a losing strategy. The "stop everything" loss limit now grows with bet size. A losing strategy usually trips it, and a good one rarely trips it by bad luck.
- **No race at graduation, and no fixed 5-minute wait.** The bot waits until Pump.fun's automatic BOOST buying has ended *and* the selling after it has calmed down. Paper "shadows" test every other timing.
- **Our own switches no longer stop selling.** STOP halts buying only. A proposed backup, a "pre-signed emergency sell", would let a small outside watchdog sell even if the main program or the signing service is down. If Pump.fun itself switches selling off, no bot can sell; small bets are the only defence.
- **Three edge ideas:** bet less on coins that insiders could crash hardest; pick exit rules by testing them on every graduating coin, not just ours; and grow bets only after the data proves the edge.

Tags: [VERIFIED-DOC] primary source read this session, [VERIFIED-SEARCH] search results only, [UNVERIFIED] inference (with a test), [DERIVED] my arithmetic or simulation. Host note: `onchaindivers.substack.com` failed to resolve (not allowed in this session).

---

## 1. Answers to attacks

### 1.1 Break-even and the new minimum size (SEAM-1, PREMISE-7, SEC-8, EXE-2): FIXED
Inputs [DERIVED, inputs UNVERIFIED until tests]:
- SOL ≈ $100; the pool's SOL side holds 80 SOL.
- Pump's pool fee is 1.25% each way (the highest published tier, as SEAM-4 asks) [VERIFIED-SEARCH, EXE §1].
- A calm transaction costs 0.000305 SOL. An urgent sell costs 0.002 SOL (Helius Sender Max needs a tip of at least 0.001 SOL [VERIFIED-SEARCH helius, via red team]).
- Price impact is about 2 × size ÷ pool, for the buy and the sell together.
- The last sell closes the token account, so its deposit comes back [VERIFIED-SEARCH, QNT S27].
- Signing costs nothing extra on KMS [VERIFIED-SEARCH, SEC §2].
- Monthly bills are $150, spread over 600 trades.

| Size (SOL) | Pool fee | Impact | Tx fees, calm (3 tx) | Tx fees, crash (buy + 2 urgent sells) | Bills share | **Total calm / crash** |
|---|---|---|---|---|---|---|
| 0.05 | 2.5% | 0.1% | 1.8% | 8.6% | 5.0% | **9.5% / 16.3%** |
| 0.10 | 2.5% | 0.3% | 0.9% | 4.3% | 2.5% | **6.2% / 9.6%** |
| **0.25** | 2.5% | 0.6% | 0.4% | 1.7% | 1.0% | **4.5% / 5.9%** |
| **0.50** | 2.5% | 1.3% | 0.2% | 0.9% | 0.5% | **4.4% / 5.1%** |
| 1.00 | 2.5% | 2.5% | 0.1% | 0.4% | 0.3% | **5.3% / 5.7%** |
| 2.00 | 2.5% | 5.0% | <0.1% | 0.2% | 0.1% | **7.7% / 7.8%** |

- **Rule of thumb [DERIVED]:** the cheapest size ≈ √(fixed cost per trade × pool SOL ÷ 2). That is 0.35–0.65 SOL for an 80 SOL pool across the bill scenarios ($150–400 a month, 300–600 trades).
- **The cost floor:** even at the cheapest size, about 4.5% is unavoidable, and it is almost all Pump's fee plus our own price impact.
- **So every entry rule needs a gross edge above ~5% per trade.** This matches the quant-tester's hurdle table (5.4% at 0.25 SOL with $300 bills) and the execution engineer's table.

**Changes:**
1. **Floor.** `min_trade_sol` = 0.25 (bounds 0.1–1). It is recomputed from measured costs as the smallest size where fixed costs are ≤ 2% of the stake (transaction fees at their 75th percentile, plus the share of bills).
2. **Target size.** `target_trade_sol` = the √ rule. It is capped by `max_pool_share_pct` = 1% of the pool's SOL. Execution's 1.5% is allowed once the canary has measured our real impact.
3. **Floor and caps must both pass.** If the floor is more than 1% of the bankroll, the bot doesn't trade live. That means **a bankroll of at least 25 SOL**. Between 25 and 50 SOL, it trades at the floor (0.5–1% per trade). **This is a question for Paul (bankroll); the safe default is paper only.**
4. **Shrinking never makes a bet smaller than the floor.** If conviction or Kelly would cut a bet below the floor, the bot **skips the trade**.
5. **The canary is a paid measurement, not an earner.** It runs 0.1 SOL × 50 trades on a fixed budget (default 1 SOL, including fees). Its only job is to measure the gap between paper fills and real fills. Profit is judged by applying that gap to paper results at the target size, and paper always runs at the target size (this matches quant's response).
6. **Take-profit tranches.** Below 0.5 SOL there is one take-profit step: sell ½ at TP1 and let the rest ride the trailing stop. Each extra sell adds about 0.12% at 0.25 SOL [DERIVED]. Execution asks for no ladder at all below 0.5 SOL; I accept their rule above 0.5 SOL. Take-profit sells pay calm fees. Only emergency exits pay urgent fees.
7. **Fixed fees.** The last sell closes the token account in the same transaction. One permanent wrapped-SOL account removes the deposit on each trade (EXE-7). Signing must cost ≤ 0.1% of the stake per signature: Turnkey's pay-as-you-go plan (≈ 0.4% at 0.25 SOL) fails, and KMS passes [VERIFIED-SEARCH prices, SEC].
8. **Bills (PREMISE-7).** Bills stay at or under 2% of turnover only if turnover is at least 50 × bills. For $150, that is 75 SOL a month, for example 300 trades × 0.25 SOL. Paid extras stay off until they earn more than they cost.

### 1.2 Risk of ruin at the new size [DERIVED simulation, illustration only, not data]
- **Set-up:** 300 trades, 4,000 runs per row.
- **Made-up trade mix (fat-tailed):** 8% near-total losses, 50% stop-outs at −25% to −45%, 25% roughly flat, 15% wins of +30% to +150%, and 2% wins of 3× to 10×. The swing per trade is ±89%.
- **Edges tested:** the mix is shifted to an average of −5%, 0 or +5% per trade.

| Bet per trade | Chance of a 25% fall from peak (edge −5% / 0 / +5%) | Chance of a 50% fall (ruin) | How often a drawdown stop set at 20 × the bet trips |
|---|---|---|---|
| 0.5% | 0.2% / 0% / 0% | 0% / 0% / 0% | 66% / 26% / 3% (stop at 10%) |
| 1% | 38% / 7% / 0.4% | 0% / 0% / 0% | 62% / 21% / 2% (stop at 20%) |
| 2% | 92% / 62% / 20% | 23% / 3% / 0.05% | 51% / 13% / 1% (stop at 40%) |

- **Ruin is about 0 at ≤ 1% per trade, even for a losing strategy.** `max_trade_pct` stays 1%, and anything above 2% needs Paul's second confirmation (unchanged).
- **FIXED: the Round 1 drawdown stop was mis-set.** A fixed 10% stop with 1% bets tripped in 46% of the runs of a *winning* (+5%) strategy [DERIVED].
  - New default: `max_drawdown_pct` = 20 × the bet % actually used. The bounds are 2–30%, and it is never above Paul's own maximum loss.
  - `daily_loss_limit_pct` = 6 × the bet %. At a 0.5% bet that is 3%, the same as in Round 1.
- **Kelly can now only shrink bets** (Kelly is the formula for the "best" bet share given known odds).
  - For this mix with a +5% edge, full Kelly is 7.4% and quarter Kelly is 1.85%. Both are above the 1% cap.
  - With a ±89% swing, proving a +5% edge needs about 860 trades, and a +10% edge about 210 (90% confidence, one-sided) [DERIVED]. Quant's table gives the same picture.
  - So Kelly's real job is to **cut** size when the measured edge fades.

### 1.3 "Can we still sell?" (SEAM-3, RSK-6, SEC-3/4/6, EXE-5, SEAM-13)
The security engineer now proposes AWS KMS as the signer, behind our own guard on a separate host, with three levers (PAUSE BUYS / STOP / KILL). The execution engineer proposes an IDL-built sell path and rolling 30-second "exit tickets". I adopt both. That leaves one hole: **if the guard host dies at 3 a.m., positions sit unmanaged until Paul clicks "launch standby".** The table shows how each way of blocking a sell is handled.

| What can block a sell | Fix | Status |
|---|---|---|
| 1. The signer (KMS) or the guard host is down | **Pre-signed emergency sells (PSES), proposed.** While signing works, the guard keeps two signed "sell my whole balance" transactions for each position (lowest accepted price, "min-out": 50% and 10% of the value at signing). Each uses a **durable nonce**, a stored stamp that keeps a signed transaction valid until it is used. The outside watchdog (third provider) holds copies but **no key**. It sends one if the guard has been silent for more than 30 s while its own price read shows a stop crossed. The guard also uses them if KMS is down. A leaked copy can only sell our coin into our own wallet at or above min-out. The pair is re-signed whenever the position changes or the price moves ±25%. A failed nonce transaction still uses up its nonce [VERIFIED-SEARCH solana.com durable-nonces], so each rung has its own nonce account (refundable deposit ≈ 0.0015 SOL [UNVERIFIED]). **Caveat:** Solana plans to retire durable nonces, with no date set [VERIFIED-SEARCH solana.com/upgrades/durable-nonce-deprecation]. Security's current rules refuse durable nonces; see challenge C1. | Proposed; QUESTION to security |
| 2. Paul's STOP revokes signing | Adopt security's levers. PAUSE BUYS and STOP leave sells running. KILL cuts everything and first shows Paul which positions will be stuck. | FIXED |
| 3. The program allowlist refuses sells after a Pump update | Adopt execution's fixed sell template under a sell-only rule. Tokens may leave only our own account, for a mint in the buy journal. SOL may go only back to our own account. No other transfers. The builder is generated from the pinned IDL. Extra Pump accounts don't break it; a new Pump program ID raises a one-click review for Paul. | FIXED (with security and execution) |
| 4. Pump turns selling off (error 6021) or breaks bots for hours | No bot can beat a global switch. Small size and the 3% total-exposure cap are the defence. The guard keeps a prepared sell and alerts within 10 s. The manual-exit drill is P10. | ACCEPTED RISK + QUESTION (does Paul want an emergency manual route?) |
| 5. The 7-day package cooldown blocks an urgent SDK fix | The guard runs no npm SDK. Its builder reads the pinned IDL file, and any change is a reviewed diff plus Paul's one-line OK (adopted from security). | FIXED |
| SEAM-13: L4 freezes Paul's manual sell | L4/KILL fires only when value leaves to an address that isn't on the approved list (security's rule). A sell we didn't send, if it pays into our own account, is reconciled with no freeze. | FIXED |

**Drill (paper, local; together with security's S8 drill):** with 3 open positions, cut each path in turn and record time-to-flat. **Pass:** flat within 60 s for paths 1–3 and 5, with no help from Paul. For path 4, the alert must arrive within 10 s.

### 1.4 The remaining attacks, and teammates' challenges to me
| ID | Answer | What changed |
|---|---|---|
| **RSK-1 / SEAM-2** | FIXED | The fixed 300 s delay is gone. Entry is **event-based**: no buy before BOOST ends + `post_boost_settle_sec` (180 s), *and* net SOL flow over the last 60 s ≥ −2% of the pool (the post-BOOST selling has slowed). BOOST buys on a schedule spread over 5 minutes, not in response to price [VERIFIED-SEARCH kucoin]. Each buy is a `boost_buy_and_burn` signed by the global `boost_authority`, and it emits `BoostBuyAndBurnEvent` with `boost_vault_remaining`. An admin can switch BOOST off (`toggle_boost`) [VERIFIED-DOC pump_amm.json; data-engineer found this first]. So "BOOST ended" means the vault reaches 0, or no BOOST event for 30 s. The schedule itself is set off-chain (no field in the IDL), so test R2 measures it. Shadows run quant's grid (60/300/330/600/900 s plus event-based), and P2 sets the live default. Any position still open when BOOST ends gets `EXIT_BOOST_CLIFF`: 20 s before the end, the trail tightens to 8%. |
| **RSK-2** | FIXED | `EXIT_LIQ_DRAIN` is deleted. The red team's maths is right: a 25% fall in the SOL side means a −43.75% price, which comes after the −35% stop. The replacement is `EXIT_SELL_PRESSURE`, which ignores who is selling: net SOL outflow ≥ 6% of the pool's SOL within a rolling 20 s (≈ −12% price [DERIVED]), with ≥ 60% of it from ≤ 3 wallets. Calibrated by P5. |
| **RSK-3** | FIXED, by adopting chain-forensics' design | `EXIT_DEV_SELL` and `EXIT_WHALE_DUMP` are replaced by forensics' `EXIT_INSIDER_FLOW`: the insider set (creator plus linked wallets) sells ≥ 3% of supply within 120 s, or ≥ 30% of what it held when we entered. Tokens passed on by plain transfer are "tainted", so those wallets count as insiders. A plain `Transfer` instruction doesn't name the coin. Data-engineer's held-coin `programSubscribe`, filtered on the mint, sees every holder's balance change anyway. `create_v2` coins use Token-2022 [VERIFIED-DOC SELL.md], which deprecates plain `Transfer` [VERIFIED-SEARCH solana.com]; whether it is still accepted is test R9. `WARN_INSIDER_TRANSFER` tightens the trail to 10%. Residual: insiders who bought through unlinked wallets; `EXIT_SELL_PRESSURE` is the backstop. |
| **RSK-4** | FIXED (process) | −35% is a paper placeholder only. Shadow stops run at −20/−35/−50% plus a "too long in loss" exit (quant's grid). A rule fixed in advance picks the live stop: the best null-strategy expectancy after costs, using the gap study (R1); ties go to the tighter stop. |
| **RSK-5** | FIXED | Only mints in the buy-intent journal are adopted. Unknown tokens are never sold or closed (they may carry transfer hooks) and go into a daily digest. Only SOL and journal mints are reconciled. An unexplained SOL gap above 0.001 SOL → L1 + alert. |
| **RSK-7** | FIXED | An emergency exit is one transaction for the whole balance, with min-out computed from the pool maths. The pool-share cap keeps its own impact at about 1–2%. |
| **RSK-8 / DAT-4** | FIXED (adopting data-engineer's sources and rule) | Source A is Chainstack (gRPC), and source B is Helius (websocket), a different company. Fallback is `getMultipleAccounts`, then a public RPC. In fallback, 1 read triggers. A breach seen only on "processed" (not yet settled) data *arms* the sell. The sell is sent when the block confirms, source B agrees, or the breach is **catastrophic**: −50% from entry, or −25% within one block (my number). min-out comes from the latest confirmed state. The settings are `feed_fallback_sec` 1.5 and `feed_stale_sec` 5 → L1 (data's proposal, adopted). |
| **SEAM-7** | FIXED | The guard polls every 5 s while healthy and every 1 s when stale: ≈ 0.5M credits a month normally, 2.6M worst [DERIVED]. This sits inside data-engineer's untouchable 2.6M exit reserve, with a capped autoscale. Credits per call are [UNVERIFIED] (R8). |
| **SEAM-8** | FIXED | The guard's journal (kilobytes a day) gets reserved space on the system disk. The recorder has its own volume (data-engineer). A failed write never crashes the guard: it keeps running from memory and the chain, goes to L1 and alerts. |
| **SEAM-11 / EXE-3** | FIXED (adopting execution's model) | The 3/8/15/30% ladder is retired. min-out = the pool-maths quote × (1 − m), where m = 1–5% normally and 3–15% in emergencies, re-quoted every 2 blocks. The 30% figure becomes a cumulative chase **alert**. **Amendment:** after the alert, the chase continues; it stops only on 6021, a frozen account or an unknown error. A missed sell costs more than a bad one. |
| **EXE-1 / EXE-2** | FIXED (agree) | Sells are rebuilt at once, for the current balance. Each position locks a 0.01 SOL exit reserve (execution), so `fee_reserve_sol` = 0.02 + 0.01 per open position. |
| **PREMISE-3** | FIXED (risk part) | Size-ups and Kelly never use paper results. The canary reports "paper filled, live failed" coins separately. Quant owns the competition-aware fill model. |
| **PREMISE-4 / PREMISE-5** | FIXED | The null baseline gets the full exit set *and* a "time exit only" version, so entries and exits are judged separately. On a market-structure change (quant's fast path), canary or live size drops to the floor until the fast path passes. If quant's silent-change alarm fires, size is halved. |
| **Challenges to me** | ACCEPTED | **Security:** every theft-bounding limit lives on the guard host and can only be loosened there, with the 10-minute delay. **Quant C2:** the defaults are shadows, not adoptions. **Execution:** the 0.25 SOL floor, single-shot emergency sells and the margin model (amended as above). **Forensics:** `EXIT_INSIDER_FLOW`. **Data:** BOOST events in place of a clock, and faster feed-stale timers. |

---

## 2. The big fork: race at graduation? Risk position: **no, not in v1**
1. **Our failed buys pile up on the winners (PREMISE-3).** Paper results on contested coins are the least trustworthy numbers we will have. They are the likeliest way to switch on real money for an edge that isn't real.
2. **Racing is priced in the worst currency.** It needs contested tips. The top 5% of Jito tips run up to 0.005 SOL [VERIFIED-SEARCH, EXE §3], which is 2% of a 0.25 SOL stake per attempt, and execution estimates catching up costs about $2,000 a month in infrastructure [UNVERIFIED, EXE response]. It also needs wide buy slippage, which feeds sandwich bots. And the pool opens at a price the completing buyer has already moved [VERIFIED-DOC SYNTHETIC_MIGRATION.md].
3. **The tail risk is highest in the first minutes.** Launch snipers sell 85% within 5 minutes [VERIFIED-SEARCH pineanalytics, launches not migrations], and the BOOST cliff arrives at minute 5. Gap study R1 splits stop slippage by minute since migration to measure this.
4. **Speed money buys more on exits.** Each block saved on a dump is real money (one 2%-of-supply chunk ≈ −17% [DERIVED, RSK-3]).

**What would change my mind:** quant's pre-written RACE rule passes. On top of that, risk adds: the graduation-entry null strategy, filled at our *measured* latency with competition-aware landing, has expectancy above +5% after costs on ≥ 300 post-BOOST coins, *with the top 5% of trades removed*. Only then would a Phase-2 canary run at the floor size. Until then, a paper-only "race shadow" logs what we're missing.

---

## 3. Challenges to other areas (3)
- **C1 → security-engineer: allow durable nonces for one purpose only, or say in writing that positions wait.** Your design is sound for theft, but a dead guard host waits for Paul's click, and a KMS outage means "positions wait". Proposal: the guard may sign durable-nonce transactions **only** for PSES. A PSES must sell a journal mint, from our own token account, with SOL coming back to our own account, a min-out of at least 10% of value, one tip ≤ 0.003 SOL to a listed tip account, and nothing else. Every other durable nonce stays refused. The worst case if one leaks is an early sale at or above min-out. If you refuse, the lead must write "unmanaged positions until Paul wakes" into DESIGN.md as an accepted risk, with its size: up to 3% of the bankroll.
- **C2 → execution-engineer: the chase never gives up, and the drill uses one target.** (a) The 30% chase limit is an alert, not a stop (see SEAM-11). (b) Allow one take-profit step between 0.25 and 0.5 SOL (+0.12%). (c) Your exit tickets and my PSES share one "time-to-flat" target in the paper drill: p95 under 60 s across signer blip, guard crash and STOP. (d) Report realised versus quoted price per send path in the canary, and drop any path that leaks more than 0.5% on average.
- **C3 → data-engineer: an exit testbed, and no single point of failure in the holder watch.** (a) Keep every pool's full trade stream for ≥ 60 minutes after migration for **every** graduate, not just held coins. Edge E2 depends on it, and your disk alarm at 70% must never drop this (drop other raw bytes first). (b) The held-coin holder watch (`programSubscribe` on the mint) is on Helius only. Give it a second path for when Helius is down, for example Yellowstone's `token_accounts` filter [VD geyser.proto, via quant]. Measure its delay to the guard (target < 1 s).

---

## 4. Edge hunt
### E1. Bet by how far a coin *can* fall, not by how sure we are ("overhang-scaled sizing")
- **Idea:** Round 1 rejected "volatility-scaled" sizing because stops gap. This version scales instead to the **structural worst case**: the price drop if the insider set dumped everything it still holds. Forensics measures this "overhang" from its holder ledger. In a constant-product pool, selling H tokens into a pool holding T tokens leaves the price at (T ÷ (T + H))² of where it was [DERIVED from the PumpSwap formula, VERIFIED-DOC PUMP_SWAP_README via Round 1]. Size = min(caps, risk unit ÷ worst-case drop), and coins below the floor are skipped.
- **Example** (50 SOL bankroll, risk unit 0.2 SOL):

  | Insiders hold, as a multiple of pool tokens | Worst-case drop | Bet |
  |---|---|---|
  | 0.15× | −24% | 0.5 SOL (the 1% cap binds) |
  | 0.5× | −56% | 0.36 SOL |
  | 1× | −75% | 0.27 SOL |
  | 2× | −89% | skipped (0.225 is below the floor) |
- **Why we'd win:** retail bots use one fixed size per snipe, so their rugs cost them full size. Our losses shrink exactly on the coins most able to crash, with **no** change to which coins we pick. Fixed-size rivals can't get this without an insider ledger.
- **Cost:** $0. It reuses forensics' overhang number. It needs only a pool-maths line in the sizing code.
- **How a rival copies it:** the idea is easy; the honest insider ledger behind it is the hard part (forensics E1). Moat: weeks.
- **Kill test (on the recorder tape, fixed in advance):**
  - Use the same entries (null strategy and champion) on ≥ 300 post-BOOST graduates, with the same average SOL deployed.
  - Pre-check: overhang at entry has a rank correlation of at least 0.2 with the realised loss.
  - **Pass:** return per SOL deployed improves by at least 1.5 points per trade *and* max drawdown falls by at least 20%.
  - **Kill:** the improvement is under 0.5 points.

### E2. Choose exits by testing them on every graduate, per coin type ("exit tournament")
- **Idea:** the exit guard paper-runs 6 rival exit sets on a paper entry into **every** canonical graduate:
  - the current ladder;
  - trail only;
  - burst-sell take-profit: sell a step in the slot after a buy burst of ≥ 1.5% of the pool's SOL, which is execution's BOOST-buy idea generalised to any buyer who ignores price;
  - insider-flow exits;
  - the BOOST-cliff exit;
  - a "too long in loss" exit.

  The winner is promoted **per coin type** (overhang low/high × entry window) after a paired test with a correction for the number of trials.
- **Why we'd win:** rival tools offer user-set take-profit levels, trailing stops and "Dev Sell" exits [VERIFIED-SEARCH datawallet GMGN guide; megateway Axiom guide, weak]. Those are fixed guesses. GMGN even suggests 30–35% slippage on automated orders and 50% or more on new tokens [VERIFIED-SEARCH datawallet], which is a sandwich tax on every exit. Our exits are picked from data and re-picked within weeks after each Pump change. Exits tested on the same entries are paired, so they need far fewer samples. Quant notes this is "the cheapest statistical power we have".
  - At an assumed 0.8 correlation between the two rules on the same coin, the swing of the difference is about ±56%.
  - With 200 graduates a day, a 2-point exit improvement is provable in about 18 days.
  - On our own ~10 trades a day, the same proof would take about a year [DERIVED, using quant's 80%-power formula].
- **Cost:** CPU and recorder storage (C3a). No API calls.
- **How a rival copies it:** any team with a full recorder could. Most retail setups have none.
- **Kill test:** after 6 weeks, the promoted exit must beat the incumbent by at least 2 points per trade at 90% confidence (corrected for contestants × coin types) on the held-out weeks. **Kill** the tournament if no contestant beats the incumbent by at least 1 point.

### E3. Grow bets only on proven edge; cut them on the first sign of decay
- **Idea:** bets step up from the floor, 1× → 2× → 4×. Each step needs the 90% lower bound of live expectancy after costs above 0, plus the luck check (still positive with the top 5% of trades removed). A decay alarm steps the bet down one level. The alarm is a CUSUM (a running-sum detector that notices when the average shifts). It watches the champion's **unconstrained paper twin**, which trades every coin that passes its filters with no position caps, plus quant's "market thermometer" (the null strategy over all graduates).
- **Why we'd win:** Pump changed market structure about 4 times in 15 weeks (PREMISE-5). Fixed-size bots lose most in the weeks after their edge dies.
  - On our own trades alone, a detector tuned to false-alarm only about once per 4 runs of 300 trades needs a median of ~90 trades to notice an edge flip from +5% to −5%. That is about 9 days at 10 trades a day [DERIVED simulation].
  - A twin with 3–10× more trades a day cuts that to days [DERIVED, assuming the detection count in trades stays similar].
  - Losing less is a real edge.
- **Cost:** $0, just arithmetic on logs we already keep. The trade-off is slower growth and some false step-downs.
- **How a rival copies it:** the concept is trivial. It needs honest null and twin bookkeeping, which most setups lack.
- **Kill test:** replay at least 90 days of tape across at least 2 market-structure changes.
  - **Pass:** max drawdown falls by at least 25% and total profit falls by no more than 10%, compared with fixed size.
  - Also, in a synthetic test, an injected edge flip must be caught within 60 live trades in at least 75% of runs.
  - **Kill:** drawdown improves by less than 10%, or profit falls by more than 20%.

---

## 5. Revised recommendation
- **Size:** the floor is 0.25 SOL (recomputed from measured costs) and the target is √(fixed cost × pool ÷ 2). The caps are 1% of the bankroll and 1% of the pool's SOL. Skip any trade where the floor and the caps can't both be met. Below a ~25 SOL bankroll, run paper only, plus an optional fixed-budget canary. Size within the caps by overhang (E1) once its kill test passes.
- **Limits scale with the bet:** drawdown stop = 20 × the bet %, daily loss limit = 6 × the bet %, and both stay at or under Paul's own maximum. Kelly and conviction only shrink bets. Bets grow in steps only on live proof and shrink on decay alarms (E3).
- **Exits:** delete the pool-drain exit. Add `EXIT_SELL_PRESSURE`, `EXIT_INSIDER_FLOW` and `EXIT_BOOST_CLIFF`, each logging its reason code. The hard stop comes from the gap study. Use execution's margin-and-chase sells, which never give up. Emergency exits are one transaction. Exits are chosen by the tournament on every graduate (E2).
- **Selling can't be switched off by us:** PAUSE BUYS and STOP keep sells running. Use a sell-only template built from the IDL, and L4/KILL only when value leaves to an unlisted address. The PSES watchdog backstop is pending security's ruling. Drill all five paths with a 60 s time-to-flat target.
- **Entry timing:** no race at graduation in v1. Enter when BOOST has ended, the settle time has passed and the selling has calmed, with quant's shadow grid running alongside. A pre-written RACE rule plus the risk test in §2 can overturn this.

**New or changed settings** (all Paul-editable; tightening applies at once, loosening waits 10 min on the guard host):

| Setting | Default | Bounds |
|---|---|---|
| `min_trade_sol` | 0.25 | 0.1–1 |
| `target_trade_sol` | √ rule | at or under the caps |
| `max_pool_share_pct` | 1% | 0.1–3% |
| `max_drawdown_pct` | 20 × bet % | 2–30% |
| `daily_loss_limit_pct` | 6 × bet % | 0.5–10% |
| `post_boost_settle_sec` / `boost_end_quiet_sec` | 180 / 30 | 0–1800 / 5–120 |
| `catastrophic_breach_pct` / `catastrophic_block_drop_pct` | −50% / −25% | −20% to −90% / −10% to −60% |
| `feed_fallback_sec` / `feed_stale_sec` | 1.5 / 5 | 0.5–10 / 2–60 |
| `entry_netflow_min_pct` | −2% per 60 s | −10% to +5% |
| `sell_pressure_pct` / `sell_pressure_window_sec` | 6% / 20 | 2–20% / 5–120 |
| `insider_flow_pct` / `insider_flow_window_sec` / `insider_flow_share` | 3% / 120 / 30% | 0.5–10% / 30–600 / 10–80% |
| `boost_cliff_trail_pct` | 8% | 3–20% |
| `tp_single_step_below_sol` | 0.5 | 0.25–2 |
| `exit_reserve_per_position_sol` | 0.01 | at least 0.005 |
| `chase_alert_pct` | 30% | 10–60% |
| `canary_budget_sol` | 1.0 | 0.2–5 |

The old `liq_drain_pct`, `dev_sell_pct`, `whale_dump_pct`, `sell_slippage_ladder` and `post_migration_buy_delay_sec` are removed or become shadows.

## Tests to run once allowed (read-only; nothing signs or sends)
| # | Test | Domain(s) |
|---|---|---|
| R1 | Gap study by minute since migration (0–1, 1–5, 5–15, 15+): the share of −20/−35/−50% stops that filled below −50% | `mainnet.helius-rpc.com` or `api.mainnet-beta.solana.com`; the gRPC provider host |
| R2 | BOOST schedule on 50 graduates: the spacing and size of `BoostBuyAndBurnEvent`s, whether `boost_vault_remaining` always reaches 0, and net flow ±2 min around the last one | same |
| R3–R5 | Kill tests for E1, E2, E3 on the recorder tape (local), with history from `dune.com` / `api.dune.com` | as listed |
| R6 | The five-path sell drill with 3 paper positions (local, no network) | none |
| R7 | PSES on devnet, only after Paul approves a build: a sell-only durable-nonce transaction is accepted by our guard's rules and every other one is refused; a failed rung uses up its nonce | `api.devnet.solana.com`, `solana.com/docs/core/transactions/durable-nonces`, `solana.com/upgrades/durable-nonce-deprecation` |
| R8 | Credits per `getMultipleAccounts` call and per websocket `accountSubscribe` | `www.helius.dev/docs/billing/credits` |
| R9 | Do `create_v2` (Token-2022) mints still accept plain `Transfer`? Count plain versus checked transfers on 100 coins | RPC host |
| R10 | Read `onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering` for the BOOST schedule details | `onchaindivers.substack.com` (blocked this session) |

## Sources
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md (no BOOST mention; `create_v2`; mandatory sell accounts)
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/SELL.md (Token-2022 for `create_v2` coins; 26 accounts incl. fee program)
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (`boost_buy_and_burn`, `BoostBuyAndBurnEvent.boost_vault_remaining`, `GlobalConfig.boost_authority` / `boost_enabled`, `toggle_boost`; no schedule field)
- [VERIFIED-DOC, via red team] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- [VERIFIED-SEARCH] BOOST TWAP over 5 min, 17.6 SOL: https://www.kucoin.com/blog/pump-fun-boost-mode-explained ; https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives ; https://ourcryptotalk.com/news/pump-fun-boost-mode-dead-liquidity ; https://onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering (search only)
- [VERIFIED-SEARCH] Durable nonces (failed transactions still advance the nonce): https://solana.com/docs/core/transactions/durable-nonces ; https://docs.anza.xyz/implemented-proposals/durable-tx-nonces
- [VERIFIED-SEARCH] Durable nonce deprecation, in development, no date: https://solana.com/upgrades/durable-nonce-deprecation
- [VERIFIED-SEARCH] Token-2022 deprecates `Transfer`: https://solana.com/docs/tokens/basics/transfer-tokens (seen via translated pages)
- [VERIFIED-SEARCH] GMGN Dev Sell, trailing TP, suggested 30–50% slippage: https://www.datawallet.com/zh/隐蔽性/gmgn-explained ; Axiom TP levels (weak): https://megateway.pages.dev/academy/axiom-trading-bot-guide
- [VERIFIED-SEARCH] No published first-hour median data for graduates found (search, 2026-11-04)
- Teammates' figures cited as "EXE / SEC / QNT / CHN" come from `team-debate/round1/*.md` and `team-debate/round2/*-response.md`.
