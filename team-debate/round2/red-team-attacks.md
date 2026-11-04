# Round 2a: Red-team attacks on all 8 Round 1 proposals

## In plain English (for Paul)
- The design is careful about many small dangers, but the biggest money risks sit **between** the proposals. One example: the safety rules that stop a hacker can also stop the bot from selling in a crash. Another: the default "wait 5 minutes before buying" means buying at the exact moment Pump.fun's own automatic buying stops.
- **The team has not yet named a single edge of its own.** As written, the design is a slower, more expensive version of the filters that free trading apps already show every trader. It loses the race at graduation by roughly 3–10 blocks, and nobody has measured what that costs per trade.
- At the proposed starting bet (0.05 SOL, about $5), fees, tips, signing charges and monthly bills eat **15–40% of each trade** before the coin moves at all. Small bets are safe, but at this size the desk can't pay for itself.
- None of this means "stop". It means every specialist must answer the numbered attacks below with a fix or a data test before anything is adopted. The ten most dangerous attacks are listed first.

**How to read this file.** Each attack has an ID (for example EXE-3) so specialists can answer by number. **Severity** is the money at risk: *Critical* = the whole hot wallet or every open position at once; *High* = a big share of a position on many trades, or it makes the strategy unprofitable; *Medium* = losses on some trades, blind spots, or more than $50/month wasted; *Low* = a nuisance. **Likelihood:** *Certain* (follows from the proposals' own numbers), *Likely* (has happened before, or will under normal conditions), *Possible*, *Unlikely*.

**Tags:** [VERIFIED-DOC] = I read the primary source this session. [VERIFIED-SEARCH] = seen only in search results. [UNVERIFIED] = inference, with the test that would confirm it. [DERIVED] = my arithmetic on numbers from the proposals. Sources are listed at the bottom. Host notes: WebFetch worked on `raw.githubusercontent.com`. The shell network is blocked, so no live tests were run.

---

## TOP 10 (most money at risk first)

| # | ID | Attack in one line | Severity / Likelihood |
|---|---|---|---|
| 1 | SEC-1 | A hacked server can empty the whole hot wallet in one trade: the approved list includes Jupiter, which can pay a swap's output to *any* token account, and the hosted wallet's rules cannot see transfers made inside other programs. | Critical / Possible |
| 2 | SEAM-3 | Five separate things can cut the exit guard off from selling in a crash: a hosted-signer outage, Paul's STOP button, the program allowlist after a Pump update, Pump's own sell switch, and the 7-day package cooldown. All open positions would be stuck. | Critical / Likely |
| 3 | PREMISE-2 | No proposal names an edge. Every filter is one that free trading apps already show, and the bot applies them later and pays more. | High / Likely |
| 4 | RSK-1 | The default 300-second wait buys exactly when BOOST's 17.6 SOL of automatic buying ends, which is the moment its artificial support disappears. | High / Likely |
| 5 | PREMISE-3 | **Adverse selection:** we win the trades nobody else wanted and lose the auctions on the hot ones. Paper mode treats failures as random, so it will show profit that doesn't exist. | High / Likely |
| 6 | SEAM-1 + SEC-8 + PREMISE-7 | At 0.05 SOL a trade, fixed costs per trade (tips, priority fees, Turnkey's $0.10 per signature, a 0.002 SOL account deposit) plus about $300–500 a month in bills need a **15–40% gain per trade** just to break even. | High / Certain |
| 7 | PREMISE-1 | At graduation we arrive about **3–10 blocks (0.8–2.5 s) after the leaders**, because of the confirmed-only rule, gate reads, a Jupiter cross-check, remote signing and a capped tip. The cost per trade has never been measured. | High / Certain if we enter at graduation |
| 8 | RSK-2 / RSK-3 | The dump exits are blind or useless. "Pool drain 25%" can only fire after the −35% hard stop. A dev who moves tokens to fresh wallets and sells in 1.9% chunks triggers no exit. | High / Likely |
| 9 | EXE-1 / EXE-2 / EXE-3 | Sell mechanics in a crash contradict each other. A rebuilt sell waits for the old trade to expire (30–60 s). The 2% retry budget can't pay one "urgent" tip. Slippage of 20–30% sent over many paths invites sandwich bots. | High / Likely in crashes |
| 10 | DAT-1 | **Silent decoding errors:** Pump adds fields to the end of its data (it did this for `virtual_quote_reserves`) and has pushed breaking changes without notice. An old decoder keeps running and prices pools wrongly, without any error. | High / Possible |

**Next five:** SEAM-7 (the Helius credit budget runs out, and with it the exit guard's second RPC), SEAM-8 (a full disk kills the exit journal), SEAM-4 (quant and execution assume fees about 5× apart), RSK-5 (spam airdrops trigger orphan sells and permanent pauses), SEC-5 (the package cooldown versus urgent Pump SDK fixes).

---

## A. PREMISE: will this beat the bots already trading graduated coins?

**PREMISE-1 (High / Certain if we enter at graduation). We lose the speed race at graduation, and nobody has priced it.**
Since synthetic migration, the buy that completes the curve also buys the first pool-priced tokens "against the pool before the pool exists", and the pool "opens at the price where the buy stopped" [VERIFIED-DOC SYNTHETIC_MIGRATION.md]. Migration is permissionless [VERIFIED-DOC PUMP_PROGRAM_README.md], so a sniper can complete, migrate and buy in one transaction (data-engineer already flags this). Our path, using the proposals' own numbers:

| Step | Leader bot | Our design (proposal) | Our extra delay |
|---|---|---|---|
| Learn the curve is complete | Shreds or a co-located node, same block | gRPC at processed, then **buy only on confirmed** (DAT trap 5) | +1–2 blocks [UNVERIFIED post-Alpenglow, D6] |
| Pool opens | Already bought inside the completing transaction | Wait for `CompletePumpAmmMigrationEvent` | 0–1 block |
| Safety gate | Pre-computed | Gate reads, "< 0.5 s" (CHN T2) | 0–0.5 s |
| Price cross-check | None | Jupiter `/build` web call (EXE §7) | 50–200 ms [UNVERIFIED] |
| Sign | Local key, < 1 ms | Hosted signer (SEC §2) | 50–250 ms [VERIFIED-SEARCH, anecdote] |
| Land | Top tips, many paths | Jito bundle only. Tip capped at 0.5% of trade = **0.00025 SOL at 0.05 SOL** (EXE §7) | 1–2+ blocks, and often loses the auction |
| **Total** | 0 | | **≈ 0.8–2.5 s ≈ 3–10 blocks** at 0.2–0.35 s per block [DERIVED] |

The snipers we arrive behind sell fast. Pine Analytics found first-block sniper wallets on Pump launches sell 85% within 5 minutes, 90% in one or two swaps [VERIFIED-SEARCH pineanalytics]. That data is about launches, not migrations [UNVERIFIED for migrations]. The cost per trade is unknown. Illustration only [DERIVED, UNVERIFIED]: if a contested coin rises 2% per block for its first 10 blocks, arriving 5 blocks late costs ~10%, which is more than double the 3.5–4% fee round trip.
**Demand:** (a) Test P1 (below) measures the median and the slowest-10% price change per block for blocks 0–20 after pool open on 500 post-BOOST graduations. (b) Every specialist states whether their area competes at graduation or not. **If entry is not at graduation (the risk-manager's 300 s default), the team must stop justifying entry-side speed spend** and say which decision each dollar of speed buys (I expect exits only).

**PREMISE-2 (High / Likely). There is no edge yet. The design is a slower copy.**
The design has top-10 holders, dev %, bundle and sniper share, creator history, KOL wallets, a trailing stop and a take-profit ladder. Retail apps (GMGN, Axiom, Photon) show these same columns on their "migrated" lists, and many copy bots act on them [UNVERIFIED: test P15]. Commercial APIs sell sniper/insider/bundler scores [VERIFIED-SEARCH docs.solanatracker.io/guides/sniper-detection]. Paul's mandate asks for an edge "of our own" and "why we would win". **Not one Round 1 file says what we will know or do that they don't.** "Better decisions" is a claim, not a test.
**Demand:** every Round 2b edge idea must state (1) the information or action the competition lacks, (2) why they can't copy it within a month, (3) a kill test on the recorder tape with a pass/fail number decided *before* the test runs.

**PREMISE-3 (High / Likely). Adverse selection: we get the fills nobody else wanted.**
Our buys land when the auction is quiet (nobody wants the coin) and fail when it's hot: the tip is capped, buy slippage is capped at 3% (EXE §4), and Jito bundles only land on Jito leaders. So **failure is correlated with the coins that would have won.** The execution engineer's 70%/90% landing assumption and the quant-tester's "random drops at 10%" are independent of outcome. Paper mode will therefore keep the winners we would really have missed.
**Demand:** (a) The fill simulator decides landing from competition, meaning the tips paid and the number of competing buys in our landing blocks (test P4), not a coin flip. (b) In the canary, report P&L on "paper filled, live failed" coins separately. (c) The quant gate adds: "paper P&L stays above zero when every coin that had more than N competing buys in its first 3 blocks is counted as missed."

**PREMISE-4 (High / Likely). There is no baseline to beat.**
Before any filter counts, we need the **null strategy**: buy *every* canonical graduate at the chosen entry time, with the risk-manager's exits, after all costs. We also need a random-entry baseline and "do nothing". If the null loses 10% per trade, a filter that "improves" it to −4% is still a loser. No proposal includes this.
**Demand:** quant-tester adds the null and random baselines to every report. A rule must beat **both** the null *and* zero.

**PREMISE-5 (High / Likely). Pump changes the market faster than we can prove an edge.**
Since July 2026: BOOST (Jul 21) [VERIFIED-SEARCH kucoin, theblock], negative virtual reserves (Sep 30), depth-2 Pump-coin quotes (Oct 13), v3 instructions with synthetic migration and fees kept in the pool, and holder-reward coins [VERIFIED-DOC pump-public-docs README]. That is at least 4 market-structure changes in about 15 weeks. The go-live path is 200 paper trades over 21+ days, then 50 canary trades, then 100 live trades before Kelly. Realistically that is 2–4 months, and results are "reported separately for each program version" (QNT §1). **Proof will usually straddle a regime change, and per-version samples will be too small.**
**Demand:** quant-tester classifies changes as *decoding-only* (no clock reset) or *market-structure* (clock reset or fast re-validation), with a written fast path.

**PREMISE-6 (Medium / Likely). "AI project", but no AI in the money path.**
This is the honest choice, and I support it. The danger is the opposite: inflating the AI's role to fit the label. The only live AI job, the Haiku "vibe score", has no evidence behind it (AI §7) and no cheap baseline.
**Demand:** the vibe score must beat a $0 baseline (name/ticker features, description length, link presence) on the same coins. The AI's measurable job should be **offline research on the tape** (finding features), with every proposal counted as a trial (see SEAM-9).

**PREMISE-7 (High / Certain). The desk can't pay its own bills at the proposed size.**
Monthly fixed costs from the proposals: data $150–270, RugCheck $40, social $50–65, AI $31–93, hosting $5–30, Dune $75 (one-off). That is **≈ $280–500/month**. At 20 trades/day × 0.05 SOL × ~$100/SOL, turnover is ≈ $3,000/month, so **fixed costs alone are 9–17% of turnover**, before per-trade costs (SEAM-1) [DERIVED].
**Demand:** a break-even table for Paul: the bet size and trade count at which monthly costs fall under 2% of turnover. Paid services stay switched off in paper mode until their value is shown (RugCheck, social, Sonnet second look).

---

## B. SEAMS: one proposal's assumption is another's unknown

**SEAM-1 (High / Certain). Bet size × fees × the take-profit ladder.**
Risk sets Phase 1 at 0.05 SOL with a ladder (buy + TP1 + TP2 + final = 4 transactions on a winner). Execution's fixed cost per transaction is priority + tip = 0.0003 SOL normal and 0.003 SOL hot. Helius Sender Max needs a ≥0.001 SOL tip plus a priority fee [VERIFIED-SEARCH helius.dev/docs/sending-transactions/sender].

| 0.05 SOL position [DERIVED] | Fixed tx costs | PumpSwap fee (~1.25% × 2) | Total before price moves |
|---|---|---|---|
| Winner, normal, 4 tx | 0.0012 SOL = 2.4% | ~2.5% | **~5%** |
| Winner, hot, 4 tx | 0.012 SOL = 24% | ~2.5% | **~26.5%** |
| Loser, hot, Sender Max sell | 0.005 SOL = 10% | ~2.5% | **~12.5%** |
| Add: token-account deposit if not closed | 0.00204 SOL = **4%** [VERIFIED-SEARCH, QNT S27] | | |
| Add: Turnkey at $0.10/signature (SEC-8) | 4 sigs ≈ $0.40 = **8%** of a $5 stake | | |

**Demand:** risk and execution agree on a **minimum position size** where fixed costs are ≤1% of the stake, or no ladder below that size. The last sell must close the token account in the same transaction.

**SEAM-2 (High / Likely). The 300 s delay × BOOST × speed spend.** See RSK-1. Data and execution are designing for milliseconds while risk's default enters at minute 5. One of them is wrong for entries.

**SEAM-3 (Critical / Likely). The exit guard assumes it can always sign and send. Five proposals can each stop it.**
1. The hosted signer is down. Privy logged "wallet actions and transaction finality delayed due to repeat issue with an upstream provider", and IsDown counts 8 Privy outages since Feb 2026 [VERIFIED-SEARCH isdown.app]. Risk-manager §5 has no plan for "signer unavailable".
2. Paul's STOP "pauses the bot *and* revokes the server's signing access" (SEC §3.8), so it also kills sells.
3. The program allowlist is "updated by hand after Paul reviews the change" (SEC §3.1). A Pump update that adds a program or account layout makes the signer refuse **sells too**.
4. Pump's admin can globally disable PumpSwap operations [VERIFIED-DOC PUMP_SWAP_README.md]. On Aug 28 2025 a Pump change broke bot selling for hours, and traders were told to sell via Pump's website only [VERIFIED-SEARCH protos.com]. With a hosted wallet, Paul has no wallet app to sell from Pump's website [UNVERIFIED: test P10].
5. The 7-day package cooldown (SEC §5) versus a breaking SDK change. On Sep 1, new accounts became mandatory with a fixed deadline [VERIFIED-DOC FEE_PROGRAM_README.md], and Pump's dev channel reports integrations broke over new required accounts [VERIFIED-SEARCH t.me/s/pump_tech_updates].

**Demand:** a single "can we still sell?" design owned by risk and security together. It needs: a **sell-only credential** that STOP does not revoke; sell rules that are narrower than buy rules but survive Pump updates (sell a mint we hold, to our own account, through PumpSwap or the curve); a minimal instruction builder generated from the IDL, so selling does not depend on an npm release; and a **tested manual exit** for when bots can't sell. Drill: in paper mode, cut each of the five paths in turn with open positions and record time-to-flat.

**SEAM-4 (Medium / Certain). Quant and execution use different fee models.**
Quant-tester charges "PumpSwap 20 bps LP + 5 bps protocol plus the creator fee for the tier" (QNT §3). Execution charges "1.25% (0.93% protocol, 0.30% creator, 0.02% LP)" (EXE §1). The PumpSwap README's 20/5 bps is the global config [VERIFIED-DOC]. The fee program's tier table applies to canonical pools, but **its tier values are in an image not present in the text** [VERIFIED-DOC FEE_PROGRAM_README.md]. Search reports of Project Ascend conflict on thresholds [VERIFIED-SEARCH mexc, solanafloor]. Fresh graduates sit near the 420 SOL tier boundary [UNVERIFIED], so the tier can change during a hold.
**Demand:** one shared fee module, proven by T6 (match 500 real trades to the lamport), including trades that cross a tier boundary. Until then, paper uses the higher figure.

**SEAM-5 (High / Likely). Forensics' "free time" between complete and pool-open may be zero.**
Chain-forensics §1 calls that gap "free time to finish checks". Data-engineer §6 says a bot can complete, migrate and buy in one transaction. **Demand:** D2/T3 report the gap distribution, including the share at 0 blocks. The gate must work when the gap is 0: everything heavy is pre-armed, and only cheap reads happen at the gate.

**SEAM-6 (High / Likely). Forensics and exits need to see token transfers. The firehose doesn't carry them.**
The primary stream takes transactions that touch Pump or PumpSwap (`account_include` both programs, DAT §3). A dev moving tokens to fresh wallets with a plain token transfer doesn't touch either program, so it is **invisible**. The same applies to SOL funding of sybil wallets, and to sales on any other venue. Chain-forensics #8 ("transfers do not show in trade events") and risk's `EXIT_DEV_SELL` both depend on it.
**Demand:** a per-mint subscription for candidates and held coins (the token mint plus top holders' token accounts). Watch Chainstack's limit of 50 accounts per stream and 5 filters [VERIFIED-SEARCH docs.chainstack.com]. Test P5 measures how real dumpers got their tokens.

**SEAM-7 (High / Likely). The Helius credit budget is double-booked.**
The Helius Developer plan (10M credits/month) carries: the backup stream (20 credits/MB, DAT), the exit guard's second-RPC 1 s poll (3 positions × 86,400 calls/day ≈ 7.8M/month unbatched, 2.6M batched) [DERIVED], the 1 s slot-lag `getSlot` check (≈ 2.6M/month) [DERIVED], forensics (1–5M, CHN §3), `funded-by` lookups, the audit, and social's KOL webhooks (~150k). That totals ≈ 7–16M+. When credits run out, the **exit guard's second price source dies**.
**Demand:** one credit budget table covering every consumer, and the exit guard's sources must never sit on a plan that can run dry.

**SEAM-8 (High / Likely). A full disk kills the exit journal.**
Data stores raw bytes, "tens of GB a month" (DAT §4). Security's VPS option is about $5–6 [VERIFIED-SEARCH serverspace.us], and such plans typically include 25–80 GB of disk [UNVERIFIED]. Risk's exit guard writes its journal, peaks and heartbeat to disk. Disk full means journal writes fail, then a crash loop, then L1, while positions are open.
**Demand:** the recorder and the exit guard use separate disks (or the recorder sits on a separate host), with a disk-space alarm and a test with a full disk.

**SEAM-9 (Medium / Likely). The AI reviewers × the trial counter.**
Opus nightly and Fable weekly "suggest rule changes" (AI §1). That is about 35 proposals a month, each a trial, which pushes past the quant-tester's ">20 trials → 95% confidence" in weeks. The reviewers see outcomes, so proposals tested on the same weeks are look-ahead.
**Demand:** AI proposals are scored only on data **after** the proposal date, and every one increments the trial counter, adopted or not.

**SEAM-10 (Medium / Likely). Social's 30-minute window × entry at minute 5 × AI pre-scoring at 50% of the curve.**
Social needs "3 independent clusters within 30 minutes" (SOC §2), but entry is at 300 s. At minute 5 most fresh coins have few organic posts, so social is mostly "unknown" at decision time [UNVERIFIED: test P13]. Synthetic migration lets one buy finish the curve with no size limit [VERIFIED-DOC README], so a coin can jump from below 50% to complete before Haiku (p95 ~20 s) returns.
**Demand:** measure the share of graduates with a usable social and AI score at entry time. If it is low, these inputs can't affect entry and must be costed as research only.

**SEAM-11 (High / Likely). The two slippage ladders disagree and both invite sandwiches.** See EXE-3. Risk uses 3/8/15/30%. Execution uses 5% normal and up to 20% emergency.

**SEAM-12 (Medium / Likely). The signer allowlist × the multi-sender.**
Security allows transfers only to "known Jito tip accounts up to a tip cap" (SEC §3.3). Execution also uses Helius Sender and Nozomi, which have their own tip requirements [VERIFIED-SEARCH helius docs, nozomi docs]. If those tip recipients aren't allowlisted, **every Sender/Nozomi sell is refused**. **Demand:** a joint list of tip recipients per sender, tested against the policy.

**SEAM-13 (Medium / Possible). The kill switch L4 × Paul's manual sell.**
"Any transaction from the wallet the bot didn't send → L4 FREEZE ALL" (RSK §4). Paul's emergency manual sell (SEC §9) *is* such a transaction, so it freezes the exit guard for every other position. **Demand:** L4 freezes buys and non-sell transactions; selling held mints stays allowed unless Paul chooses otherwise.

---

## C. Attacks by area

### DATA (data-engineer)

**DAT-1 (High / Possible). Silent decoder corruption.** Pump appends fields to accounts and events (`virtual_quote_reserves`, `holder_rewards`, `buyback_fee_recipient`) [VERIFIED-DOC README, PUMP_SWAP_TRADE_V2.md], and has pushed breaking changes without notice [VERIFIED-SEARCH protos.com]. A decoder that ignores trailing bytes **keeps running with no error** and prices pools from the vault balance, which is wrong when virtual reserves are negative [VERIFIED-DOC NEGATIVE_VIRTUAL_QUOTE_RESERVES.md]. The program-data watch (DAT §4) is good, but it has two gaps. (a) Its resume rule ("the three feeds agree on the next 5 migrations") proves we *see* migrations, not that we *decode prices and fees* correctly. (b) Changes made by admin configuration (`update_fee_config`, `set_params`, a field that was always 0 starting to carry values) need no program upgrade, so nothing alarms [VERIFIED-DOC PUMP_SWAP_README.md, PUMP_PROGRAM_README.md].
**Demand:** assert the exact byte length per discriminator and version, and treat unexpected trailing bytes as an alarm. Subscribe to the fee-config and global-config accounts, and pause buys on any change until it is reviewed. Continuously compare our computed price against each real trade's executed amounts (the T6 check run live); any drift above 0.5% raises an alarm and is part of the resume rule.

**DAT-2 (High / Possible). One primary provider in one region.** Chainstack logged a Solana "degraded performance" incident lasting 1 day 1 hour (May 5 2026) and a "London cluster down" incident [VERIFIED-SEARCH isdown.app, pingoru.io]. The backup carries only migrations and held pools, so when the primary dies, pre-arm, forensics, creator history and the recorder all go dark.
**Demand:** a written degraded mode: which checks fail closed, whether exits keep a full-quality feed, and how recorder gaps are repaired and flagged in backtests.

**DAT-3 (High / Likely). The firehose is blind to non-Pump transactions.** See SEAM-6.

**DAT-4 (Medium / Likely). Confirmed-only buys versus processed exits.** Buying only on confirmed data costs blocks at entry (PREMISE-1). Exits on "the freshest source" (DAT §4) during Alpenglow's brief multi-candidate blocks [VERIFIED-SEARCH, DAT S3] can fire on a block that is later dropped, causing a phantom crash and a needless sell.
**Demand:** an exit trigger on processed data needs a second source or confirmation within N ms. Measure dropped candidate blocks (D6).

**DAT-5 (High / Likely). Credits.** See SEAM-7.

**DAT-6 (Medium / Possible). The backup and the audit share one dependency.** Both use the global `withdraw_authority`, which Pump's authority can change with `set_params` [VERIFIED-DOC PUMP_PROGRAM_README.md]. The "independent" eyes go blind together. **Demand:** an audit keyed differently, for example derive the canonical pool from every `CompleteEvent` and check that it exists N blocks later (DAT §4 already half-proposes this, so make it the audit).

**DAT-7 (Medium / Possible). The PumpPortal tripwire may need a funded PumpPortal wallet.** PumpSwap data costs 0.01 SOL per 10,000 messages with an API key [VERIFIED-SEARCH, DAT S11]. If PumpPortal's API key comes with a wallet whose key PumpPortal generates [UNVERIFIED], that breaks the "no keys" rule. **Demand:** confirm D9 and how the key is handled before adopting.

**DAT-8 (High / Likely). Disk.** See SEAM-8.

**DAT-9 (Low / Possible). The event-rate floor can cause false "down" alarms in quiet hours** (it rests on "never quiet for long", which is unverified) and push decisions onto the narrow backup for no reason. **Demand:** calibrate the floor from 7 days of recorder data.

### CHAIN FORENSICS (chain-forensics)

**CHN-1 (High / Likely).** The gate window may be zero. See SEAM-5.

**CHN-2 (High / Likely). Top-20 holders only, plus an unchecked exclusion list.** `getTokenLargestAccounts` returns 20 accounts [VERIFIED-SEARCH CHN S9], and splitting supply over 50 wallets defeats the check. The exclusions (pool vault, curve, burn, Mayhem agent) miss BOOST/buyback accounts, creator and holder-reward vaults, and Pump fee accounts [UNVERIFIED which hold tokens]. Missing ones inflate concentration (false rejects), and wrong ones hide insiders.
**Demand:** build the holder map from the stream plus per-mint transfers (SEAM-6), and measure a full holder scan's cost for candidates only (T2).

**CHN-3 (Medium / Likely). Bundle detection misses most modern bundles.** The Jito lookup only finds Jito bundles. Bundler tools spread buys across blocks and senders [VERIFIED-SEARCH CHN S23]. Slot-0 rules flag legitimate snipers [VERIFIED-SEARCH CHN S20].
**Demand:** use the outcome-relevant measure, "share of supply still held at migration by wallets that bought in the first N blocks", and report its catch rate on labelled rugs (T10).

**CHN-4 (Medium / Likely). Funding-source checks are cheap to evade and not cheap to run.** Exchange-funded or multi-hop wallets and bought aged wallets get through, and Helius `funded-by` returns the immediate funder only [VERIFIED-SEARCH CHN S11]. At 40–150 credits × pre-armed coins it lands in SEAM-7. **Demand:** a credit cost per check in the budget table, and a catch rate from T10 before it can veto.

**CHN-5 (High / Likely). The reliable checks catch only fakes, and the checks that matter are unproven.** By the proposal's own table, #1–#6 almost always pass on genuine coins, and rugs are "driven mainly by liquidity manipulation and social dynamics" [VERIFIED-SEARCH CHN S22]. The catch rate of #7–#14 is unknown, and the outcome label ("−90% within 1 h"?) isn't fixed.
**Demand:** fix the rug/dump label *before* T10. Report each check's catch rate and false-alarm rate against the null baseline (PREMISE-4).

**CHN-6 (Medium / Possible). Mayhem coins and depth-2 quotes.** Identifying the Mayhem agent wallet is unverified (T9), and coins quoted in another Pump coin inherit that coin's rug risk [VERIFIED-DOC README Oct 13]. **Demand:** in v1, REJECT Mayhem coins and any non-SOL quote mint (not WARN) until there is data.

**CHN-7 (Low / Likely). Creator-history and recycled-wallet databases** are evaded by a new wallet per launch, and admin-set creators confuse them [VERIFIED-DOC CHN S4]. That's fine as a minor input. **Demand:** never weight these as positive evidence ("clean history").

### EXECUTION (execution-engineer)

**EXE-1 (High / Likely). The sell retry ladder contradicts the no-rebuild rule.** "Only after expiry do we build a new one" (EXE §4), but a blockhash lives about 150 blocks, roughly 30–60 s [UNVERIFIED post-Alpenglow], while the ladder wants "4 attempts in about 20 s" with new slippage, which needs a new transaction. For sells, a double send limits itself: the second fails because the tokens are already gone, and costs only the fee.
**Demand:** separate rules. Buys keep the no-rebuild rule. Sells rebuild immediately as "sell the current balance". A paper drill shows time-to-exit in a simulated crash.

**EXE-2 (High / Certain). The retry budget can't pay one urgent send.** "Never spend more than 2% of position value on retry fees". At 0.05 SOL that is 0.001 SOL, which equals **one** Sender Max minimum tip with no priority fee left. On a ⅓ take-profit tranche, 2% is 0.00034 SOL, below the Max minimum [DERIVED; VERIFIED-SEARCH helius]. **Demand:** fee floors in absolute SOL for sells, and the position-size floor from SEAM-1.

**EXE-3 (High / Likely). Wide slippage sent over many paths invites sandwiches.** `jitodontfront` is a Jito block-engine rule [VERIFIED-SEARCH solana.com/docs/defi/mev-protection]. Helius Sender also fans out to SWQoS, Harmonic and Rakurai [VERIFIED-SEARCH helius], and whether those honour the marker is unknown [UNVERIFIED]. Sandwiches concentrate on low-liquidity Pump/PumpSwap tokens [VERIFIED-SEARCH mirror.xyz MEV monitor]. A 20–30% slippage sell offers a sandwich bot up to 20–30% of the position.
**Demand:** set emergency min-out from pool maths (expected impact + a margin), not a fixed 20–30%. Measure realised versus quoted price per send path in the canary, and drop any path that leaks.

**EXE-4 (Medium / Likely). The Jupiter cross-check may block every fresh trade or be quietly skipped.** How soon Jupiter can route brand-new pools is unknown (EXE §8). The free tier allows 1 request/s [VERIFIED-SEARCH EXE]. Either all fresh-pool buys are blocked, or someone bypasses the check under pressure. If it ever applies to sells, it's dangerous.
**Demand:** the independent check runs locally (the SDK quote against our own maths on the same block), and it never gates sells.

**EXE-5 (Critical / Likely).** Pump's sell switch and unannounced breaking changes. See SEAM-3 point 4. Marking a position "stuck" is not an exit plan.

**EXE-6 (High / Likely).** The capped Jito tip loses contested auctions, which is the adverse selection in PREMISE-3. **Demand:** test P4 records the winning tips in migration blocks, and the cap is set from data, knowing that a low cap means "we only trade unwanted coins".

**EXE-7 (Medium / Certain). The cost table leaves things out.** It omits the token-account deposit (4% of a 0.05 SOL stake if never closed), wrapping and unwrapping SOL (v2 SOL pools need a wrapped-SOL account) [VERIFIED-DOC PUMP_SWAP_TRADE_V2.md], fees on failed attempts, and BOOST effects. Cashback-coin pools reject v2 (error 6079), so the v1 path must exist [VERIFIED-DOC same]. **Demand:** add these to the table and to the simulator.

**EXE-8 (Medium / Possible). Fee-tier boundary.** See SEAM-4. Quote at the exact market cap the program uses, and test trades that cross a tier.

**EXE-9 (Medium / Likely). Landing rates rest on 2024 data** and pre-Alpenglow blogs (EXE §3). **Demand:** no landing number enters the go-live gate until it is measured (P4).

### RISK (risk-manager)

**RSK-1 (High / Likely). `post_migration_buy_delay_sec = 300` buys into the BOOST cliff.** BOOST buys 17.6 SOL over 5 minutes after migration and burns it [VERIFIED-SEARCH kucoin, blofin]. Fast actors front-run this predictable buying, and one reverse-engineering puts the take at about 2–4 SOL per coin [VERIFIED-SEARCH onchaindivers, single source]. Those actors are sellers as the buying ends. A search snippet without a traceable source says the median graduate loses 57% of liquidity between minute 5 and minute 30 [UNVERIFIED]. The default skips the artificial support and then buys the moment it stops.
**Demand:** test P2 compares entries at 60, 300, 330, 600 and 900 s (and "never") on 500 post-BOOST graduations, with net flow plotted around minute 5. The default comes from that data.

**RSK-2 (High / Certain). `EXIT_LIQ_DRAIN` can never fire first.** In a constant-product pool, price ∝ SOL-side². A 25% fall in the SOL side means a −43.75% price, while the −35% hard stop fires at about a 19.4% SOL-side fall [DERIVED]. LP tokens are burned [VERIFIED-DOC PUMP_PROGRAM_README.md], so liquidity can't be pulled any other way. It is dead code that gives false comfort.
**Demand:** replace it with sell-pressure triggers, such as net SOL outflow over the last N blocks, or a cluster's cumulative sells.

**RSK-3 (High / Likely). The dev/whale exits are easy to dodge.** If the dev moves tokens to fresh wallets (invisible, SEAM-6) and sells in 1.9% chunks, neither `EXIT_DEV_SELL` nor `EXIT_WHALE_DUMP` (>2% in one go) fires. If the pool holds roughly 20% of supply at migration [UNVERIFIED], each 2% chunk is about 10% of the pool's tokens, so about −17% in price per chunk [DERIVED].
**Demand:** use rolling-window net sells per *cluster* (from CHN #10 and #14), not per wallet per transaction. Test P5 measures real dump patterns.

**RSK-4 (Medium / Likely). The −35% hard stop is uncalibrated.** On coins that swing ±40% in minutes, noise stops us out, and gaps fill it at −70% (RSK §2). **Demand:** set the stop from the gap study (RSK test 1) and the null baseline's swing distribution, not a round number.

**RSK-5 (Medium / Likely). Spam airdrops trigger orphan sells and permanent pauses.** "Adopt orphan tokens … apply tight default exits" means the guard will try to sell scam tokens sent to the wallet. Those can carry transfer hooks or need unknown routes, so the signer refuses them or fees are wasted. "Wallet balance ≠ ledger → L1, Paul only" turns every airdrop into a buy pause. Address-poisoning spam is widespread [VERIFIED-SEARCH SEC, solscan].
**Demand:** adopt only mints in the buy-intent journal, and alert on everything else. Reconcile SOL and tracked mints only.

**RSK-6 (Critical / Possible).** L4 and STOP kill exits. See SEAM-3 and SEAM-13.

**RSK-7 (Medium / Likely). Chunked emergency sells are slower than one sell.** "No single sell is more than 1% of the pool's SOL side" means several transactions in sequence during a crash, each waiting to land. **Demand:** size positions so one sell's impact is acceptable, and in an emergency sell all at once with a computed min-out.

**RSK-8 (Medium / Likely). The exit feed falls back to slow polling exactly when it matters.** Live updates plus a 1 s backup poll is the right shape. But in a crash, live streams lag or drop first. The fallback poll is then 3–5 blocks stale, and "2 consecutive reads" for the trailing stop makes about 2 s. Nobody has said which provider carries the live updates (if it is the same Chainstack stream, it isn't independent). **Demand:** name the exit guard's two live sources (different companies from each other). In fallback mode the trailing stop needs only 1 read. Measure the delay of both in a busy hour (RSK test 2).

### QUANT (quant-tester)

**QNT-1 (High / Likely).** Fill failures are modelled as independent of outcome. See PREMISE-3.

**QNT-2 (High / Likely). Order within a block is unspecified.** "Fill at the pool as it was at the landing block": before or after the other trades in that block? Snipers with higher tips go first. **Demand:** by default, our trade goes **last** among same-block trades in the same direction, with a sampled position as the alternative view.

**QNT-3 (Medium / Certain).** Fee model conflict. See SEAM-4.

**QNT-4 (High / Likely). Fat tails make the 200-trade gate weaker than stated.** "±60% swing → proves edges above +7%" uses an assumed spread. At a spread of ±150% (plausible for meme coins [UNVERIFIED]), 200 trades prove only edges above **~17% per trade** (1.645 × 1.5 ÷ √200) [DERIVED]. A bootstrap also understates tail risk on small samples.
**Demand:** compute the spread from the recorder, report the edge size the gate can actually detect, and add "still positive with the top 5% of trades removed".

**QNT-5 (Medium / Likely). Dune history straddles regime changes** (PREMISE-5), and per-version reporting shrinks every sample. **Demand:** state the sample size per regime for every backtest result.

**QNT-6 (Medium / Likely). Shadows versus the champion compares paper with live.** In canary and live phases the champion's fills are real and the shadows' are paper. **Demand:** the champion also runs a paper twin, and challengers are compared paper-to-paper.

**QNT-7 (Medium / Likely). "Coverage" checks migrations, not trades.** The recorder could drop trade messages inside the stream while the migration counts still match. **Demand:** a per-pool completeness sample (recorder trades against `getSignaturesForAddress` on 20 random pools a day).

**QNT-8 (Low / Likely). The locked holdout is the newest data.** In a fast-changing market that is also the most relevant data. That's a real tension, not a bug. **Demand:** state it to Paul, and allow a one-time "fresh regime" holdout after each market-structure change.

### AI (ai-strategist)

**AI-1 (Medium / Likely). Shadow-to-gate after 2–4 weeks is underpowered.** About 20 paper buys a day, split into high and low score bands, gives about 140–280 per band, which only detects large differences given fat tails (QNT-4). **Demand:** a power calculation *before* shadowing, plus the $0 baseline (PREMISE-6).

**AI-2 (Medium / Likely). `INJECTION_BAIT` rejects a whole narrative.** Auto-rejecting metadata containing "AI agent" blocks the AI-agent meme category, a common theme [UNVERIFIED share]. **Demand:** flag injection *patterns* (instructions, role tags, "ignore previous"), not topic words, and log the false-reject rate.

**AI-3 (Medium / Likely). Coins that complete in one jump have no score.** See SEAM-10. Once the score gates entry, these are skipped, and they may be the most-wanted coins. **Demand:** measure their share and outcome before gating.

**AI-4 (Medium / Likely).** The reviewers are an overfitting engine. See SEAM-9.

**AI-5 (Medium / Possible). Score noise.** Haiku 5.5 rejects temperature settings (AI §7). If the same coin's score varies about as much as the band width, the gate is a coin flip. **Demand:** run test 3 (repeatability) before any gating, and use the median of 3 calls if needed (and cost it).

**AI-6 (Low / Possible). The volume assumption.** Pre-scoring at 50% of the curve covers more coins than graduate, and the count is unknown. **Demand:** count coins reaching 50% per day from the recorder, and put a hard daily cap on calls.

### SOCIAL (social-intel)

**SOC-1 (Medium / Likely).** Social can't weigh in at minute 5. See SEAM-10.

**SOC-2 (Medium / Certain). The prepaid cap runs out mid-month.** $0.02 × 100 coins/day ≈ $60/month, already above the ~$50 cap, before the "posted 5+ CAs in 24 h" check on each author, which needs extra timeline calls per author [UNVERIFIED cost]. After that, social is "unknown" for the rest of the month. **Demand:** a cost model that includes author-history calls, and a stated behaviour when the cap is hit.

**SOC-3 (Medium / Possible). X is actively shutting down third-party readers.** X sent cease-and-desist letters to Nitter and XCancel in Aug 2026, and both went offline [VERIFIED-SEARCH techcrunch]. **Demand:** keep the second provider configured, and plan for a v1 with no X data at all.

**SOC-4 (Medium / Likely). KOL wallets are crowded copy trades.** Thousands of copy bots watch the same labelled wallets, so we'd be last in line. Pump.fun itself bought the Kolscan label source [VERIFIED-SEARCH dlnews]. KOLs use second wallets and plain transfers to hide sells [VERIFIED-SEARCH reddit, weak]. **Demand:** measure the KOL signal *after our real delay*, and test it as a contrarian signal too.

**SOC-5 (Medium / Likely). The confirm logic rewards paid campaigns.** Paid KOL waves look like "several independent clusters". In one report on 1,500+ KOL promotions, 80% were down 70% after a week [VERIFIED-SEARCH SOC]. **Demand:** a burst of KOL posts within minutes counts as a **negative** feature unless the KOLs' wallets bought.

**SOC-6 (Low / Likely). Helius webhooks for KOL wallets** give up after 3 failed tries [VERIFIED-SEARCH SOC], which data-engineer rejected for the same reason. **Demand:** use the gRPC stream for watched wallets.

### SECURITY (security-engineer)

**SEC-1 (Critical / Possible). Allowlisting Jupiter, plus "free" token accounts, opens a one-transaction drain.** Jupiter's swap API takes a `destinationTokenAccount` that can belong to someone else, which is how its payments feature works [VERIFIED-SEARCH docs.jup.ag, hub.jup.ag]. Turnkey's transfer rules see only top-level transfers [VERIFIED-SEARCH SEC]. The PumpSwap IDL places **no constraint** tying `user_base_token_account` to the signer [VERIFIED-DOC pump_amm.json]; whether the program itself enforces it is [UNVERIFIED: test P6]. With an allowlisted swap program, a hacked server can sell everything or swap all SOL with the output sent to the attacker.
**Demand:** the hosted policy itself pins the output account (if Turnkey or Privy can't express that, they don't qualify). Jupiter is not allowlisted for live trading unless its output is pinned. P6 settles the PumpSwap question.

**SEC-2 (Critical / Possible). Our own signer guard is bypassable if it runs on the bot's server.** SEC §8 puts "our own signer guard" on the same Frankfurt VPS. If the server holds the hosted-wallet API key, the attacker calls the vendor directly and skips the daily caps, the output check and the refusal list, because hosted engines judge one transaction at a time (SEC §3.2).
**Demand:** the vendor credential lives **only** on a separate guard host (different provider account), and the bot can only ask the guard.

**SEC-3 (Critical / Likely).** A hosted-signer outage stops sells, and the manual route is unproven. See SEAM-3 point 1 and test P10.

**SEC-4 (Critical / Possible).** STOP revokes the sell path. See SEAM-3 point 2. **Demand:** two credentials, so STOP revokes the buy-capable one first and the sell-only one by a separate, deliberate action.

**SEC-5 (High / Likely). The 7-day cooldown versus urgent Pump SDK changes.** Mandatory account changes arrive on fixed dates [VERIFIED-DOC FEE_PROGRAM_README.md], and breaking changes arrive without notice [VERIFIED-SEARCH protos]. Under pressure the team will either be unable to trade for 7 days or will bypass the control. The Dec 2024 web3.js backdoor shows what a 5-hour window costs [VERIFIED-SEARCH SEC]. **Demand:** a pre-written emergency path: build instructions from the IDL with no SDK dependency, or vendor the SDK and review the diff, with Paul's one-line approval.

**SEC-6 (Critical / Likely).** The allowlist update blocks sells. See SEAM-3 point 3.

**SEC-7 (Medium / Possible). Address lookup tables.** Routes use on-chain address lists. The guard must resolve them at signing time from a trusted RPC; a lying RPC returns a fake list [UNVERIFIED risk]. **Demand:** resolve them from two providers and refuse on any mismatch.

**SEC-8 (High / Certain). Turnkey's signing cost at our bet size.** $0.10 per signature after 25 free [VERIFIED-SEARCH turnkey.com/pricing]. That is 4 signatures on a winner plus retries, so $0.40–0.80 a trade, or 8–16% of a $5 stake [DERIVED]. **Demand:** fold it into SEAM-1. At Phase 1 size, Turnkey is ruled out on cost unless Pro ($99 + $0.05) is cheaper, or Privy and KMS pass the policy tests.

---

## D. Choices the team must compare again (each against 2 real alternatives)

| Decision | A | B | C | What decides it |
|---|---|---|---|---|
| Entry timing | Race at graduation (needs PREMISE-1 spend) | Fixed delay (300 s default) | Event-based (after BOOST ends, on net-flow or holder conditions), with no speed race | Tests P1, P2, null baseline |
| Who holds the signing credential | Hosted policy wallet, key on the bot server | Hosted policy wallet, key only on a separate guard host | KMS plus our own guard on a separate host | SEC-1, SEC-2, P8, cost per trade (SEC-8) |
| Exit send path | Jito only, with `jitodontfront` | Helius Sender (fan-out) | Both, chosen by measured leak and landing per path | EXE-3, canary slippage per path |
| Bet size in Phase 1 | 0.05 SOL with ladder | Fixed-cost floor (≤1% fixed cost), no ladder | Paper only until an edge is shown | SEAM-1, PREMISE-7 |

---

## E. Tests to run once allowed (read-only; nothing signs, sends or simulates)

| # | Test | Domain(s) |
|---|---|---|
| P1 | Price change per block for blocks 0–20 after pool open on 500 post-BOOST graduations; the share completed and migrated in one transaction | `mainnet.helius-rpc.com` or `api.mainnet-beta.solana.com`, gRPC provider host |
| P2 | BOOST study: price, net flow and liquidity from t = 0 to 30 min; entries at 60, 300, 330, 600 and 900 s against the null baseline | Same as P1, plus `dune.com` |
| P3 | Null and random baselines over 60–90 days, after all costs | `dune.com`, `api.dune.com` |
| P4 | Winning Jito tips and the count of competing buys in migration blocks; landing as a function of competition | `bundles.jito.wtf`, `explorer.jito.wtf`, RPC host |
| P5 | For 200 dumps: did the dumping wallets get tokens by buying or by plain transfer, and what were the chunk sizes and timing? | RPC host |
| P6 | Of 1,000 historical PumpSwap buys and sells, how many have `user_base_token_account` owned by someone other than the signer? (If any, the program allows it.) | RPC host |
| P7 | Jupiter `destinationTokenAccount` behaviour on current Swap V2 docs | `developers.jup.ag`, `dev.jup.ag` |
| P8 | Can Turnkey or Privy policies pin an instruction's output account, or only programs and top-level recipients? | `docs.turnkey.com`, `docs.privy.io` |
| P9 | 12-month incident history for the signer and stream vendors | `status.privy.io`, Turnkey status page (URL from `www.turnkey.com`), `status.chainstack.com`, `status.helius.dev` [UNVERIFIED hosts] |
| P10 | Manual exit drill: can Paul sell a PumpSwap token from the hosted wallet's dashboard? (Docs now; devnet only after Paul approves a build) | `docs.turnkey.com`, `docs.privy.io` |
| P11 | Disk growth per day of the recorder (from D4) against the chosen VPS plan's disk | Provider pricing pages |
| P12 | Credit cost of every Helius consumer in SEAM-7 | `www.helius.dev/docs/billing/credits` |
| P13 | Number of non-team posts mentioning the CA at t = 300 s for 200 graduations | `api.twitterapi.io`, `api.x.com` |
| P14 | Sandwich rate and loss on PumpSwap sells by slippage setting | `dune.com` |
| P15 | Which filters GMGN, Axiom and Photon already show on migrated coins | `gmgn.ai`, `axiom.trade`, `photon-sol.tinyastro.io` [UNVERIFIED host] |

---

## Sources
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_PROGRAM_README.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (first 100K characters read)
- [VERIFIED-SEARCH] BOOST: https://www.kucoin.com/blog/pump-fun-boost-mode-explained ; https://blofin.com/en/academy/education/pumpfun/pump-fun-boost-mode-explained ; https://www.theblock.co/news/defi/2026-07-29-pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives-409815 ; https://onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering
- [VERIFIED-SEARCH] Project Ascend fees: https://www.mexc.com/news/82737 ; https://solanafloor.com/news/pump-funs-new-creator-fee-model-pays-2m-24-hours
- [VERIFIED-SEARCH] Aug 28 2025 sell outage: https://protos.com/axiom-traders-panic-as-pump-fun-temporarily-bans-selling-memecoins/
- [VERIFIED-SEARCH] Pump dev updates (integrations broke on new accounts): https://t.me/s/pump_tech_updates/29
- [VERIFIED-SEARCH] Sandwiches concentrate on Pump/PumpSwap tokens: https://mirror.xyz/0x7c855e1bF411Ab5975235bC8C74E032615073044/mwh7Bkqp_nmsOkW6T7ee4tqXyXYgaRwLQd8zi38HbcY
- [VERIFIED-SEARCH] jitodontfront: https://solana.com/docs/defi/mev-protection
- [VERIFIED-SEARCH] Helius Sender requirements: https://www.helius.dev/docs/sending-transactions/sender
- [VERIFIED-SEARCH] Jupiter destinationTokenAccount: https://docs.jup.ag/docs/apis/swap-api ; https://hub.jup.ag/docs/swap-api/payments-through-swap
- [VERIFIED-SEARCH] Privy incidents: https://isdown.app/status/privy-io/incidents/656889-wallet-actions-and-transaction-finality-delayed ; https://isdown.app/status/privy-io/outage-history
- [VERIFIED-SEARCH] Chainstack incidents and limits: https://isdown.app/status/chainstack/incidents/541754-solana-mainnet-down-in-london-cluster ; https://pingoru.io/providers/chainstack/incidents/3419497 ; https://docs.chainstack.com/docs/yellowstone-grpc-geyser-plugin.md ; https://docs.chainstack.com/changelog/chainstack-updates-june-10-2026
- [VERIFIED-SEARCH] Solana halts: https://www.theblock.co/amp/post/276237/solana-network-restarts-after-outage-that-lasted-five-hours (2024, 5 h) ; https://dropthe.org/coin/solana-outage-january-2026-what-broke-and-whats-next/ (Jan 2026, low-confidence source)
- [VERIFIED-SEARCH] Sniper behaviour: https://pineanalytics.substack.com/p/exit-liquidity-machines ; https://beincrypto.com/pump-fun-meme-coin-snipers-systematic-problem
- [VERIFIED-SEARCH] Sniper/bundler scores sold commercially: https://docs.solanatracker.io/guides/sniper-detection
- [VERIFIED-SEARCH] X action on scrapers: https://techcrunch.com/2026/09/15/nitter-and-xcancel-are-dead-again-after-xs-latest-legal-actions
- [VERIFIED-SEARCH] KOL tracking: https://www.dlnews.com/articles/defi/memecoin-kols-bag-millions-as-pump-fun-buys-kolscan-tracker/ ; https://reddit.sentinel-team.org/posts/1pjc21s/snapshots/2025-12-11T00%3A41%3A04.568627Z (weak)
- Proposal references (EXE §n, RSK §n, etc.) point to `team-debate/round1/<role>.md`.
