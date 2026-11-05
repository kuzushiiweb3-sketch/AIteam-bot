# DESIGN: AI-assisted trading desk for graduated Pump.fun coins

**Status: approved by Paul on 2026-11-05.** Monthly running-cost budget: CAD $1,000 (about USD $700). Real money still needs Paul's separate, explicit OK at Phases 4 and 5.

## In plain English (for Paul)
- We are building a bot that watches every Pump.fun coin, waits until a freshly graduated coin's quick sellers have left, buys small, and sells fast when insiders start dumping. It trades on **paper (pretend money) by default, forever**, until you personally switch real money on.
- We **won't try to be first in**. The fastest bots sit next to the validators, and we can't beat them cheaply. We aim to choose better *when* to get in, and to get out faster and cheaper than app users.
- **Honest odds:** about a 1 in 4 chance that any rule proves itself on paper within about 3 months of data. The chance it then also pays its bills with real money is lower. What is near-certain is that the desk will lose less to bugs, theft and fees than most retail bots.
- **Cost:** about **$275 a month** once fully running (range $213–604), and about $250 a month during research. Real money needs at least **25 SOL** plus a loss budget you accept. A stop rule ends the spending if no edge appears.

**Tags used here.** [VERIFIED-DOC] = we read the primary source this session. [VERIFIED-SEARCH] = seen in search results only. [UNVERIFIED] = our estimate or judgment; the test that settles it is named. [DERIVED] = our arithmetic on tagged inputs. The detailed evidence, with URLs, is in `team-debate/round1/`, `team-debate/round2/` and `team-debate/round3/rulings.md`.

---

## 1. One-page summary

**What we're building.** A trading desk with three parts:
1. A **data recorder** that sees every Pump.fun and PumpSwap transaction, including the failed ones.
2. A **strategy engine** whose rules are plain code, never an AI's opinion.
3. A small, separate **guard computer** that does all the signing and selling, under strict limits.

AI is used for research (proposing and testing rules overnight) and for reading Pump.fun's rule changes. AI is never in the buy, sell or sizing path.

**How it intends to win.** "We won't be first in. We aim to choose better when to get in, and to get out faster." Concretely:
- **Better timing.** Pump's BOOST feature buys about 17.6 SOL of each new graduate over its first 5 minutes, then stops [VERIFIED-SEARCH kucoin; amount not confirmed as fixed]. The early snipers sell into that buying. We keep an exact, live ledger of how many tokens the fast wallets and the insiders still hold, *including tokens they quietly moved to fresh wallets*. We buy only once that pile is nearly gone.
- **Better exits.** Exit rules are chosen by testing them on *every* graduating coin (about 200 a day), not just ours. Sells are re-priced every 2 blocks with a tight margin, so sandwich bots can take at most a few percent. App users often accept 30–50% slippage [VERIFIED-SEARCH, datawallet GMGN guide].
- **Knowing when not to trade.** A "market thermometer" tracks how a buy-every-graduate strategy is doing right now, and keeps us out in bad weather.
- **Losing less.** Strict safety, tiny bets (1% of the bankroll each) and cost discipline. Losing less is a real edge.

**All of these are hypotheses.** None is proven. Each has a pass/fail test written down *before* the data exists.

**Honest odds (team judgment, [UNVERIFIED]).**
- About **1 in 4** that some rule passes the paper-trading gate within ~3 months.
- Perhaps **1 in 8 to 1 in 10** that it also survives a real-money test, the next Pump.fun change, and pays its own bills.
- The likeliest single outcome is "no edge found", and the stop rule (§8) handles that cheaply.

**What it costs.**
- About **$250 a month** while recording and researching. About **$275 a month** once the paper bot and guard are running. The range is $213–604; every line that can grow has a hard cap.
- A round trip (buy and sell) costs about **3.2% of the bet in calm conditions and 4.9% in a crash** at 0.25 SOL [DERIVED].
- To pay its bills too, the bot must earn about **7.4% per trade** (25 SOL wallet, 10 trades a day) or **5.9%** (50 SOL wallet, 0.5 SOL bets).

**What happens next.**
1. You approve this design (or not) and set a monthly budget (QUESTIONS_FOR_PAUL.md).
2. **Phase 0:** you allow some web domains and create a few read-only data accounts. We run the network tests we couldn't run here.
3. **Phase 1:** a recorder runs for 14–21 days, and nothing trades.
4. Research, then a paper bot. Real money only if a rule passes every gate **and** you say yes.

---

## 2. The architecture, in plain English

### 2a. The picture
```
                SOLANA BLOCKCHAIN  (Pump.fun curve + PumpSwap pools)
                   |                        |                       |
     Chainstack live stream          Helius (narrow streams,     Public RPC
     (every Pump/PumpSwap tx,        audits; a separate key      (last-resort
      failed tx, admin settings)      for the guard)              fallback)
                   |                        |   \                    |
   +---------------v------------------------v-+  \                   |
   |  BOT HOST  (rented server, account A)    |   \                  |
   |  1 Recorder ---> own disk ---> archive    |    \                 |
   |  2 Decoders (built from Pump's own files, |     \                |
   |    every trade checked two ways)          |      \               |
   |  3 Forensics / coin state (dossier per    |       \              |
   |    coin, insider ledger, holder map,      |        \             |
   |    theme waves)                           |         \            |
   |  4 Strategy engine (rules as code)        |          \           |
   |  5 Paper simulator (realistic fills,      |           \          |
   |    shadows, baselines)                    |            \         |
   |  6 Research loop (backtests; nightly AI   |             \        |
   |    research desk with a placebo)          |              \       |
   |  7 Dashboard + logs (private, login-only) |               \      |
   +--------------------|----------------------+                \     |
                        |  requests only ("BUY coin X, max 0.25  \    |
                        |  SOL"; "SELL ALL coin X, reason Y")     \   |
                        v  one-way encrypted tunnel                v  v
   +------------------------------------------------------------------+
   | GUARD HOST  (separate AWS account B, Frankfurt, no open ports)   |
   |  8 Signer guard: builds every transaction itself from Pump's     |
   |    official files, fixes every payout to OUR accounts, enforces  |
   |    caps, checks the price, refuses everything else               |
   |  9 Exit guard: its own live view of the pools we hold; stop-loss,|
   |    trailing stop, time exit, sell-pressure exit; re-prices sells |
   |    every 2 blocks                                                |
   |      -> AWS KMS key vault (the key never leaves it)              |
   |      -> senders: Jito + Helius Sender (protected paths)          |
   +------------------------------------------------------------------+
   | STANDBY (account B, second Frankfurt zone): sell-only            |
   |   "safe-mode seller" that takes over automatically in ~30 s      |
   +------------------------------------------------------------------+
  10 WATCHDOG (third provider): heartbeat "dead man's switch" -> your
     phone; on-chain tripwire on the hot wallet -> disable key + alert
```

### 2b. The ten parts
1. **Recorder.** Saves every Pump.fun and PumpSwap transaction, *including failed ones*, with its position in the block, the fees and tips paid, and the time we received it. It also saves each new coin's name, ticker and link. All of it goes onto its own disk, so a full disk can never stop the selling side. History we didn't record can't be rebuilt honestly later, so recording starts first.
2. **Decoders.** Turn raw blockchain bytes into "who bought what, at what price".
   - They are generated from Pump.fun's own published description files, called IDLs [VERIFIED-DOC github.com/pump-fun/pump-public-docs].
   - **Every trade is checked two ways.** Pump's own receipt must match the blockchain's balance record down to the last unit.
   - Any mismatch, unknown data shape or admin settings change pauses new buys at once. Selling continues.
3. **Forensics and coin state.** A running file ("dossier") on every coin from the moment it is created. It holds:
   - who created it;
   - who bought in the first blocks;
   - which wallets share a funder;
   - **where insiders' tokens went**, including plain transfers to fresh wallets;
   - how much they still hold (the "insider overhang");
   - which "theme wave" of copycat coins it belongs to.

   All of this is prepared in advance, so the buy decision needs **no network calls** and takes milliseconds.
4. **Strategy engine.** Rules written as plain code, with settings you can read. It decides "buy now", "skip" or "sell". Every decision writes one log line with the reason code and the numbers behind it, for example `SKIP insider_overhang 18.4% > 15%`.
5. **Paper simulator.** Pretends to trade with realistic fills:
   - We land only if our bid would have beaten the bots that actually got into that block.
   - We are placed last in the block.
   - Every fee is charged.

   Every result is shown next to three yardsticks: "buy every graduate", "buy at random" and "do nothing". A "paper twin" trades every coin the rules allow, with no position limits, so we get enough trades for honest statistics.
6. **Research loop.**
   - Backtests on the recorded data.
   - An **exit tournament** that tries rival exit rules on every graduate.
   - A **nightly AI research desk**: Claude proposes up to 3 new rules a night in a small fixed rule language, and code also writes 3 *random* rules as a placebo. Rules are judged only on data from after they were proposed. If the AI's rules don't beat the random ones, the desk is switched off.
   - A **rule-change reader**: when Pump.fun changes something, code pauses buys and the AI explains which of our assumptions just broke.
7. **Dashboard and logs.** A private page (login-protected, no public address) showing positions, every buy and reject with its reason, costs, alarms and the daily plain-English summary.
8. **Signer guard (on the separate guard host).** The bot can only *ask*: "buy coin X for at most 0.25 SOL" or "sell all of coin X". The guard:
   - builds the transaction itself;
   - fixes every payout to our own accounts;
   - re-checks that the pool is the genuine one;
   - checks the price against its own data;
   - enforces every limit: per trade, per day, open positions, fees.

   It refuses everything else. The signing key lives in Amazon's key vault (AWS KMS) and never leaves it. A hacked bot server can therefore lose at most about one day's buying limit, never the wallet.
9. **Exit guard (same host).** Its own live view of the pools we hold, from a different data company than the bot uses. It runs the stop-loss, trailing stop, time exit and sell-pressure exit itself, so selling works even if the bot server is dead or hacked. In a crash it re-prices the sell every 2 blocks and keeps chasing. It never gives up except on Pump's own "selling disabled" switch, and then it fires the moment selling reopens. The bot's smarter exits (insiders moving tokens) arrive as sell requests, which the guard always honours.
10. **Watchdog.**
    - A **sell-only standby** in a second data centre takes over automatically in about 30 s if the guard goes silent. It runs deliberately simpler code, so one bug can't take both down.
    - An outside "dead man's switch" texts your phone if both are silent for 60 s.
    - An on-chain **tripwire** watches the hot wallet. If value ever leaves to an address not on our list, it disables the key and alerts you.

### 2c. Your three levers (from Phase 3)
| Lever | What it does | Selling? |
|---|---|---|
| **PAUSE BUYS** | No new buys | Keeps running |
| **STOP** | Buying is revoked on the guard host itself; the bot can't undo it | Keeps running |
| **KILL** | Disables the signing key entirely, for when the guard itself may be hacked. Shows you first which positions will be stuck | Stops |

You pull them in the AWS console, protected by a hardware security key. Tightening works at once. Loosening waits 10 minutes and alerts you.

### 2d. Money layout (only if you ever go live)
- Your **cold wallet** (your own hardware wallet) holds the bankroll.
- The **hot wallet** (the KMS key) holds only one day's buying limit plus open positions plus fees: about 3.3 SOL at a 25 SOL bankroll.
- The guard sweeps anything extra back to your cold address, which only you can change.
- If losses drain the hot wallet, it stops until *you* top it up.
- We never move funds. You do.

---

## 3. How we plan to beat other bots

### 3a. The thesis
- **Where we cannot win: entry speed.** Since Pump's "synthetic migration", the bot that completes the bonding curve can buy pool-priced tokens inside the same transaction [VERIFIED-DOC SYNTHETIC_MIGRATION.md]. With our setup we would arrive about 3–8 blocks (0.6–1.8 s) later [UNVERIFIED, test T7/P4]. Catching up would cost about $2,000+ a month and still lose (EXE-R) [UNVERIFIED]. So we don't race. A paper "shadow racer" logs what that costs us, and a rule fixed in advance reopens the question only if data demands it.
- **Where we can win:**
  1. **Seeing more precisely.** Our insider ledger follows tokens through plain transfers that snapshot-based trading apps miss.
  2. **Deciding better.** Entry is timed to the moment the forced sellers are done. Exits are chosen from data on every coin. The thermometer decides whether to trade at all.
  3. **Exiting faster and cheaper than app users.** Sells are triggered from a live stream, built in advance, protected from sandwich bots, and use a tight margin.
- **Why rivals don't already do this.** Snipers compete on speed and ignore post-BOOST timing. Retail apps show one coin at a time from snapshots. Copy bots follow the same public wallets and become exit liquidity. None of our ideas is a deep secret: a capable team could copy any of them in weeks. Our moat is discipline (honest paper fills, baselines, tests fixed in advance) and our own recorded history.
- **The risk to this thesis (red-team, NEW-11).** The end of BOOST is public on the blockchain. Other careful bots may crowd that exact moment. So we add a random delay of 0–3 s, measure crowding on every entry, and a rule fixed today sends us back to paper if crowding appears (§3c, idea 2).

### 3b. The ranked edge ideas. **Every one is a hypothesis until data proves it after all costs.**
All five top ideas use the recorded data and cost almost nothing extra. Pass marks are fixed now and can't be changed after the data arrives (rulings §4).

| Rank | Idea (team source) | Why we might win | Kill test and pass mark (fixed in advance) |
|---|---|---|---|
| **1** | **Exit tournament** (risk RSK-E2, with execution's crash chase and forensics' insider exits as contestants) | Rival apps use fixed, user-set exits. We test 5 exit sets *side by side on the same coins*, every graduate, ~200 a day. That gives the most statistical power we have, and it needs no race | After 6 weeks, on held-out weeks: the best challenger beats the incumbent (stop-loss + trailing stop + time exit) by **≥ 2 points per trade** at 95% confidence. **Kill** if no challenger beats it by ≥ 1 point. Sub-test for the crash chase: over 200 replayed crashes, the chase beats one-shot 20–30% slippage sells by ≥ 1.5% of the position after fees |
| **2** | **"Sellers exhausted" entry** (data DAT-E1 + forensics CHN-C + quant QNT-E2; execution EXE-E1 as a variant) | We buy after the racers have sold, at calm fees, with near-certain landing. The rule needs our exact ledger of what the fast wallets and insiders still hold | Primary rule: "BOOST over **and** fast group + insiders hold ≤ 25% of their peak", plus 0–3 s random delay. Fit on 300 post-BOOST graduates, test on the next ≥ 300. **Pass:** beats both the simple default rule and buy-every-graduate by **≥ 3 points per trade** after all costs, the lower confidence bound is above 0, the pessimistic fill view is above 0, it has ≥ 20 big wins and stays ≥ 0 without the top 3 trades, ≥ 5 entries a day, and the crowding check passes. **Kill:** under +1 point at 2,000 graduates. **Crowding kill:** over any 14 days with ≥ 50 entries, more than 30% of entries crowded, or a median arrival penalty above 1.5% → back to paper |
| **3** | **Market thermometer** (quant QNT-E3) | Hundreds of coins a day tell us whether *this week* is good or bad for graduates. It costs $0, comes free with the baseline, and doubles as an alarm for unannounced Pump changes | Stage A: the 6-hour results of buy-every-graduate are correlated with the next 6 hours at ≥ 0.25 (**kill** below 0.10). Stage B, after 8 weeks: trading only in "warm" periods adds ≥ 3 points per trade **or** cuts the worst drawdown by ≥ 25% without lowering total profit (90% confidence), **and** beats two free yardsticks: a daily graduation count and SOL's 24-hour price trend |
| **4** | **Insider overhang that follows the tokens** (forensics CHN-A) | Apps show an insider % from snapshots. We follow tokens through plain transfers to fresh wallets. Used in entries, exits and sizing | Early kill (test F1): if under 10% of dumped tokens arrived by plain transfer, the "follow" part is dropped. **Pass** (≥ 14 days, ≥ 1,000 graduates): followed overhang exceeds the naive figure by ≥ 3 points of supply on ≥ 15% of graduates; it improves dump prediction (AUC) by ≥ 0.03 on a held-out week; and the insider-flow exit fires before the hard stop on ≥ 30% of insider dumps, with ≤ 20% false alarms |
| **5** | **Theme-wave position** (social SOC-E1 + AI AI-E1), code-only first | When a meme goes viral, dozens of copycat coins launch within hours. We see the whole wave from every launch, before graduation. Leaders may hold attention while late copies become exit liquidity. It is the only off-chain idea in the top 5, and it must be recorded from day 1 | ≥ 1,000 graduates over ≥ 14 days. **Pass:** the hottest third of waves beats the coldest third by ≥ 8 points in 30-minute return after costs (confidence range above 0, holds in both halves), **or** leaders dump at least 8 points less often than followers; **and** wave features improve prediction (AUC) by ≥ 0.02 in 2 of 3 weeks. **Kill:** both gaps under 4 points, or the sign flips. Claude labels are added only if they add ≥ 0.01 AUC over the free version |

**The rest, tested only after the top 5 or when nearly free:**

| Idea | Rating | Note |
|---|---|---|
| Size by insiders' worst-case dump (RSK-E1) | Plausible | Below a 50 SOL bankroll it can only act as a skip filter |
| Crew fingerprints (CHN-B) | Plausible | Recognise repeat scam crews by their tools. Lookup tables and tips are recorded from day 1; tested at day 30 against a shuffle placebo |
| Overnight AI research desk (AI-E2) | Plausible (process) | Killed if its rules don't beat random rules by 15 points (60 vs 60 rules) |
| Grow bets only on proof (RSK-E3) | Plausible (risk control) | Only meaningful above 50 SOL |
| Losers' tape (QNT-E1, failed buys as unmet demand) | Weak | Must beat a simple momentum yardstick |
| First to work after a Pump update (SEC-E1) | Weak | Only ~5 events to test |
| Blind-spot coins (DAT-E2) | Weak | Non-SOL quotes are rejected in v1 |
| KOL side-wallet bait detector (SOC-E2) | Weak | Fewer than 50 events in 60 days kills it |
| Shape of organic spread on X (SOC-E3) | Weak | One-off $10–20 test, only with your yes |
| Sell into BOOST's buys (EXE-E3) | Dead | We enter after BOOST |

**What has to be true for any of this to work** (red-team's checklist, measured in the first 2–4 weeks of recording):
1. Buy-every-graduate after BOOST loses no more than ~5 points per trade after all costs.
2. At least one on-chain feature passes its first screen and the crowding check.
3. The exit tournament wins ≥ 2 points per trade.
4. Together that makes ≥ +5–6% net per trade on 5–10 trades a day.
5. Pump leaves BOOST and migration alone for 6–8 weeks at a time.
6. Real fills match paper fills within 1–2 points.

If several fail, the stop rule ends the spending.

---

## 4. Decision table

| # | Decision | Chosen | Alternatives rejected, and why |
|---|---|---|---|
| 1 | **Entry timing** | Event-based, after BOOST ends, when the quick sellers are out, plus a 0–3 s random delay. A shadow racer logs what we miss | **Race at graduation:** we'd be 3–8 blocks late, it needs ~$2,000+/month, and it needs a riskier key setup. **Fixed 5-minute wait:** buys exactly when BOOST's support stops |
| 2 | **Main data feed** | Chainstack Yellowstone gRPC stream, $98/month, every Pump/PumpSwap transaction including failed ones [VERIFIED-SEARCH chainstack.com] | **Helius LaserStream** $499 buys tens of ms we don't need. **Solana Tracker** €200 (kept as the switch if Chainstack throttles us). **Own node** $1,800+. **PumpPortal / Bitquery / Birdeye:** someone else's decoder, slower, a black box |
| 3 | **Second data company** | Helius Developer $49: narrow streams, audits, and the guard's own stream on a separate key [VERIFIED-SEARCH helius.dev] | **A second full stream** (~$200): only worth it once missed trades cost more. **Public RPC only:** no stream, rate-limited |
| 4 | **Decoding** | Our own decoders generated from Pump's official files, with allowed lengths per version and two-witness checks | **Pump's npm SDK** in the money path: supply-chain risk and release delays. **Third-party parsed feeds:** lag after Pump changes, and silent errors |
| 5 | **Signing** | AWS KMS key vault (Ed25519), ~$1/month, reached only by the guard's machine role | **Turnkey:** $0.10 a signature = 4–12% of a small bet. **Privy:** free and exportable, but 8 outages since Feb 2026 [VERIFIED-SEARCH isdown.app]. **Key file on a server:** one hack loses everything |
| 6 | **Where code runs** | Two machines on two separate provider accounts. The bot host can't sign; the guard host has no open ports | **One machine:** the guard could be bypassed (SEC-2). **Home computer:** unreliable, unsafe |
| 7 | **Who builds transactions** | The bot sends requests; the guard builds every transaction and pins our accounts | **Bot builds, guard checks:** a hacked bot could route payouts to an attacker (SEC-1). **Jupiter routes:** can pay out to any account |
| 8 | **Sending** | One signed sell to Jito (anti-front-run marker) and Helius Sender (MEV-protected), escalating to Sender Max only after 2 failures | **Sender Max fan-out only:** paths we can't vet. **bloXroute** ~$300/month: not worth it at our size |
| 9 | **Sell price protection** | Margin over the pool's own maths (1–5%, up to 15% in emergencies), re-priced every 2 blocks, never gives up | **Fixed 20–30% slippage:** invites sandwich bots to take up to 30%. **A 3/8/15/30% ladder:** same problem |
| 10 | **If the guard dies** | Supervisor restart → safe mode → automatic sell-only standby → phone alert. Durable-nonce emergency sells banned | **Pre-signed emergency sells:** a stolen copy can be used against us, and the feature is being retired. **Cold standby, Paul clicks:** positions wait until you wake |
| 11 | **After a Pump.fun update** | Sells adopt a new layout automatically only if strict checks pass (only predictable added accounts, simulation shows payouts to us). Buys pause until reviewed | **Everything waits for a human:** we can't sell in a crisis. **Everything automatic:** a bad diff could reach buys |
| 12 | **Bet size** | 0.25 SOL minimum, ≤ 1% of the bankroll, ≤ 1% of the pool. So live needs ≥ 25 SOL | **0.05 SOL:** fees and bills eat 9–16% of every trade. **0.5% of bankroll:** needs 50 SOL for the same bet |
| 13 | **Exits** | Chosen by the tournament on every graduate. The guard runs price and flow exits itself; insider exits come from the bot as requests | **A fixed take-profit ladder:** a guess, and costly at small size. **All exits inside the guard:** too big to audit |
| 14 | **Paper fills** | Competition-aware: we must outbid the real winners, we land last in the block, three views (optimistic / base / pessimistic) | **Random "10% of orders fail":** keeps the winners we'd really miss, and shows profit that doesn't exist |
| 15 | **AI's role** | Labels only (in shadow), the offline research desk with a placebo, and the rule-change reader. A refusal or timeout means "no decision", never "buy" | **AI decides trades:** ~6 s just to start answering (about 30 blocks) and untestable taste. **No AI:** loses the research desk and the change reader, which are cheap |
| 16 | **Social data** | $0: the wave detector and the influencer-wallet watch run on our own stream. X (Twitter) only after a $10–20 test passes | **Paid X from day 1** ($50–65/month): few posts exist at entry time, and paid hype looks real. **LunarCrush / Kaito:** don't cover minute-old coins |
| 17 | **Safety checks on coins** | Our own zero-network-call dossier and insider ledger | **RugCheck / GoPlus / Birdeye scores:** cached, opaque, seconds late. **Helius `funded-by`:** 100 credits a call; our own lookup costs ~3 |
| 18 | **History for testing** | Our own recorder, plus Helius for the full list of past migrations, dead coins included | **Dune** ($75): its tables may lack failed transactions and tips. **Bitquery:** another decoder to trust |
| 19 | **Statistics** | Tests fixed in advance, day-by-day resampling, trial families with error budgets, a paper twin, forward-only scoring | **One global trial counter:** blocks everything within 2 months. **Trade-by-trade statistics:** overstate confidence |
| 20 | **Control levers** | PAUSE / STOP / KILL in the guard's own AWS account, with a hardware security key | **Levers through the bot server:** can be blocked or faked. **One STOP that also stops selling:** strands positions |
| 21 | **Coin metadata** | Name, ticker and creator for all ~30k daily launches; the full metadata file fetched once at 20% of the curve, through a sandboxed fetcher | **Fetch all 30k files:** costly and unsafe (attacker-written content). **Fetch none:** no wave detector |
| 22 | **PumpPortal** | Keyless tripwire only, or not at all | **A PumpPortal key:** it comes with a wallet key someone else generated |

---

## 5. Costs

### 5a. Monthly bills (USD)
| Item | From phase | Low | Expected | High |
|---|---|---|---|---|
| Chainstack Growth + Yellowstone stream add-on | 1 | 98 | 98 | 215 (if we must switch to Solana Tracker) |
| Helius Developer | 1 | 49 | 49 | 49 |
| Helius extra credits (autoscale, capped) | 3 | 0 | 0 | 25 |
| Bot host server | 1 | 24 | 48 | 120 |
| Recorder disk + archive | 1 | 10 | 15 | 30 |
| Guard + standby + key vault + alarms (AWS) | 3 | 22 | 25 | 35 |
| AI (Claude API), capped by your Console limit | 1–2 | 10 | 40 | 75 |
| X (Twitter) data, only if its test passes and you agree | — | 0 | 0 | 45 |
| Alert service | 3 | 0 | 0 | 10 |
| **Phases 1–2 total (recording + research)** | | **191** | **250** | **534** |
| **Phase 3+ total (paper bot, canary, live)** | | **213** | **275** | **604** |

- **Phase 0** costs $0–110: free tiers, plus perhaps one month of Chainstack for the bandwidth tests.
- **One-offs:** the X history test is $10–20, and only with your yes.
- **Cost tags.** Chainstack and Helius prices are [VERIFIED-SEARCH]. Server, disk and alert prices are [UNVERIFIED] until test G7. The AI line is [DERIVED].
- **What can blow up, and the cap on it:** Helius credits (our meter + a $25 cap), AI (your Console limit + 3,000 calls a day), X ($1.50 a day), storage (disk alarms + archive), Chainstack throttling (+$117 to switch). We have **rejected** LaserStream ($499), a second full stream (~$200) and racing infrastructure (~$2,000+) unless data proves them.

### 5b. Cost per trade (one buy + one sell)
SOL ≈ $100 [VERIFIED-SEARCH mexc, Oct 2026]. Pool ≈ 85 SOL. Pump's fee is 1.25% per side [VERIFIED-SEARCH, 3 sources; the official tier table is an image, VERIFIED-DOC FEE_PROGRAM_README].

| Bet | Calm exit | Crash exit | Typical mix (70% calm / 30% crash, [UNVERIFIED]) |
|---|---|---|---|
| **0.25 SOL** (the floor) | 3.22% = $0.81 | 4.93% = $1.23 | 3.73% = $0.93 |
| **0.5 SOL** | 3.75% = $1.87 | 4.70% = $2.35 | 4.04% = $2.02 |
| 1.0 SOL (only with ≥ 100 SOL bankroll and ≥ 100 SOL pool) | 4.88% | 5.46% | 5.05% |

About 2.5 points of every trade is Pump.fun's own fee, which no route avoids. Above ~0.6 SOL our own price impact makes bigger bets *dearer* per SOL.

### 5c. Break-even gain per trade (per-trade cost + share of $275 bills)
| Bankroll → bet | 3 trades/day | 6/day | **10/day** | 20/day |
|---|---|---|---|---|
| 25 SOL → 0.25 SOL | 16.0% | 9.8% | **7.4%** | 5.6% |
| 50 SOL → 0.5 SOL | 10.2% | 7.1% | **5.9%** | 5.0% |

The daily buying limit is 10% of the bankroll (10 floor-size buys), so it doesn't starve the strategy. **Two bars:**
- **The trade bar.** A rule must beat its own per-trade costs (about 3.7–4.0%) with confidence before it can go near real money.
- **The desk bar.** Before live, profit at the capped trade count must also beat the bills.

The bills are mostly research costs that exist whether or not we trade.

### 5d. What real money could cost you (the "tuition budget")
At 25 SOL:
- the drawdown stop halts live trading after a 20% fall: **5 SOL**;
- plus the optional canary: **1 SOL**;
- plus bills: **~$275 a month**.

Separately, theft is bounded by the hot wallet (~3.3 SOL), and only if the guard itself is hacked. The risk-manager's simulation shows almost no chance of losing half the wallet at 1% per trade, even with a losing rule [DERIVED, illustration; to be re-run on recorded days, NEW-13].

---

## 6. Known risks, ranked

| # | Risk | Mitigation | Status |
|---|---|---|---|
| 1 | **There is no edge.** The likeliest outcome | Cheap research first; tests fixed in advance; the stop rule (§8) | Accepted |
| 2 | **Pump.fun changes the rules** (BOOST off, new mandatory accounts, fees). About one change every 4 weeks recently [VERIFIED-DOC README changelog] | Buys pause on any change; sells auto-adopt only under strict checks; no-BOOST coins are paper-only; a fast re-validation path; the AI change reader | Mitigated; the pace is accepted |
| 3 | **Pump.fun switches selling off** (it happened in Aug 2025 [VERIFIED-SEARCH protos.com]) | No bot can beat it. Small bets, ≤ 3% total exposure, an instant alert, and "first out when it reopens" | **Accepted** (up to 3% of bankroll) |
| 4 | **A bug in our own guard** | A separate minimal safe-mode seller on the standby; kill drills with fixed pass marks; supervisor restarts | Mitigated; shared-bug residual accepted |
| 5 | **Hot-wallet theft if the guard host is hacked** | Separate AWS account, hardware-key login, no open ports, small hot wallet, tripwire, alarm on any unexpected signing | **Accepted, bounded** (~3.3 SOL at 25 SOL) |
| 6 | **A hacked bot server makes us buy attacker coins** | The guard's daily limit, pace limits and pool checks | **Accepted, bounded** (≤ 10% of bankroll in a day; Q8) |
| 7 | **Crowding at BOOST's end** | Random delay, crowding measured on every entry, the kill rule | Mitigated |
| 8 | **Paper looks better than real** (we lose the auctions on hot coins) | Competition-aware fills; the pessimistic view must stay positive; the canary measures the gap | Accepted until measured |
| 9 | **Blind spots**: insiders who buy through unrelated, exchange-funded wallets; SOL funding of side wallets | Pool-level sell-pressure exit as a backstop; reported coverage % | Accepted |
| 10 | **Silent decoder errors** | Two-witness check on every trade, allowed lengths per version, admin-change alarm, raw bytes kept for re-decoding | Mitigated |
| 11 | **A false discovery** (a rule looks good by luck) | Trial families with error budgets, forward-only scoring, the paper twin, the canary, three independent stages | Mitigated |
| 12 | **Bills overrun** | A hard cap on every metered line; daily cost in your summary | Mitigated |
| 13 | **Frankfurt-wide AWS or key-vault outage** | ~26 s/month uptime target [VERIFIED-SEARCH]; second-region copy if test S2 allows | **Accepted** (≤ 3% exposure) |
| 14 | **Data-feed outage** (Chainstack had a 25-hour degradation in May 2026 [VERIFIED-SEARCH isdown]) | Degraded mode never buys; exits use two other companies; gaps are flagged and excluded from tests | Accepted (missed trades only) |
| 15 | **Alarm fatigue** | Three severity classes, 7 days log-only calibration, at most ~1 phone alert a week in calm periods | Mitigated |
| 16 | **Solana network halt** | Positions wait; small exposure | Accepted |
| 17 | **Testing on slightly old data** (the newest 2 weeks are locked as a holdout) | A one-time "fresh regime" holdout after each market change | Accepted |
| 18 | **Terms-of-service risk** on X and Pump's website data | Optional, research only, terms read first; missing data counts as neutral | Accepted |

---

## 7. Phased build plan
Every phase ends at a gate. Nothing moves forward until every item passes. **Real money appears only in Phases 4–5, and only by your explicit action.** Phases 0–3 contain no signing of real transactions. Until you approve this design, the team writes only read-only tools (CLAUDE.md rule 2).

### Phase 0: Setup and the network tests (about 1–2 weeks, mostly waiting on accounts)
- **What we do:** run the read-only tests we couldn't run in this environment (consolidated list in QUESTIONS_FOR_PAUL.md). Re-check every price. Write the test plans down and freeze them, dated.
- **Deliverables:**

| File | Contents |
|---|---|
| `phase0/results.md` | Each test, its result, and its domain |
| `docs/assumption-register.md` | ~50 numbered facts the design relies on |
| `docs/preregistration.md` | Frozen labels, every kill test, the trial families |
| `docs/fee-model.md` | The one shared fee model |
| `docs/costs.md` | Re-verified price table |

- **Key tests:**

| Test | Question it answers |
|---|---|
| D13/F2 | Can Chainstack watch wallets' token accounts? |
| D4/RC6/Q2 | Stream bandwidth |
| D1/D2 | How migrations look today |
| T1/T4 | Coin authorities, LP burn |
| P6 | Does PumpSwap check who owns the payout account? |
| RC3/RC4 | Pool layouts, negative virtual reserves |
| T6 (on 500 historical trades) | Do our fee and price maths match the chain to the last unit? |
| RC8 | Replay of the Sep 2025 forced change against the auto-adopt rule |
| D15/P12/G4/G5/G8 | Credit and request costs |

- **What you do:**
  - approve the design;
  - set the budget;
  - allow the domains;
  - create a free Helius key and a Chainstack account, and later an Anthropic key with a spend limit (Setup checklist).

  About an hour.
- **Gate 0 → 1:**
  - the provider tests pass, or a named fallback is chosen;
  - T6 matches 500 historical trades to the last unit (≥ 50 crossing a fee tier, ≥ 50 v2 trades);
  - prices are re-verified;
  - the pre-registration file is frozen and dated.

### Phase 1: Recorder and decoders, plus 14–21 days of data (about 3–4 weeks)
- **What we build** (all read-only):

| Folder | Contents |
|---|---|
| `recorder/` | Full stream, failed transactions, block position, receive times, tip capture around migrations, create-event metadata, its own disk with 70/85/95% alarms and an archive |
| `decoders/` | IDL-generated; allowed lengths per version; two-witness check; reserve-continuity check |
| `monitors/` | Admin and program changes, silent-feed probe, coverage audits with four independent keys, credit meter |
| `fees/` | The shared fee module |
| `reports/daily/YYYY-MM-DD.md` | Your plain-English daily summary: coins seen, coverage %, alarms, costs |

- **What you do:** rent the bot server (we give click-by-click steps and a public login key; you never see a private key) and upgrade Helius to Developer ($49). Then nothing; read the daily summary if you like.
- **Gate 1 → 2:**
  - ≥ 14 days recorded (target 21);
  - coverage ≥ 99.5% against the audits;
  - per-pool completeness ≥ 99.5%;
  - two-witness mismatches < 0.1% of trades, each explained;
  - alarm rates calibrated (7 days log-only);
  - the disk-full drill passed;
  - credits inside budget.

### Phase 2: Research and backtests (weeks 3–8; overlaps Phase 3)
- **What we build:**

| Folder | Contents |
|---|---|
| `research/baselines/` | Buy-every-graduate, random, do-nothing, after all costs |
| `research/lateness-curve/` and the **race / no-race memo** (around day 21) | Decided by the pre-written rule |
| `research/boost-study/` | BOOST schedule, net flow and crowding around its end (R2, RC1) |
| `research/gap-study/` | How far stop-losses slip, by minute since migration; sets the stop grid |
| `research/edges/<idea>/` | Stage A screens for the top 5 ideas; the exit tournament starts |
| `sim/` | The competition-aware paper simulator |
| `research/ruin/` | The ruin simulation re-run on whole recorded days |
| Nightly AI desk with placebo | Starts once 14 days of tape exist |

- **What you do:** nothing required. At the **week-4 checkpoint** we send a one-page verdict (continue / recorder-only / stop). The default in §8 applies if you don't answer.
- **Gate 2 → 3:**
  - baselines computed;
  - the race memo delivered;
  - the BOOST and gap studies done;
  - the simulator validated on history;
  - the week-4 stop checkpoint not triggered;
  - the clustered ruin simulation done;
  - red-team has signed off the paper-bot design.

### Phase 3: The paper bot (from about week 5; at least 21 days and 200 closed trades)
- **What we build:**

| Folder | Contents |
|---|---|
| `strategy/` | Rules as data plus the engine; reason codes on every decision |
| `guard/` | Signer guard and exit guard in **paper mode**: they build transactions but never sign |
| `safe-seller/` | The standby |
| `watchdog/` | Heartbeat and tripwire design |
| `dashboard/` | Private page |
| `ops/runbooks/` | Click-by-click lever and incident steps for you |

  The guard runs on its real separate host, so the drills are real. No key exists yet.
- **What you do:**
  - create the separate AWS account with a hardware security key (steps provided);
  - set Helius autoscaling to a $25 cap (if you agree);
  - install the alert app;
  - do one 10-minute lever drill with us.
- **Gate 3 → 4 (paper → canary). All required:**
  1. Gate v2:
     - ≥ 200 closed trades over ≥ 21 days, including a quiet week and a busy week;
     - expectancy after costs above 0 with 90% confidence on forward paper data (the unconstrained twin);
     - the pessimistic view above 0;
     - beats buy-every-graduate, random and zero;
     - the luck check;
     - drawdown under your limit;
     - paper matches the backtest's range;
     - data health ≥ 99.5%.
  2. The crowding check passes.
  3. **All drills pass:**
     - five ways of blocking a sell, each flat within 60 s with no human;
     - guard kill, standby takeover, disk full;
     - the "selling disabled" alert within 10 s;
     - the Pump-change replay;
     - the lever drill with you.
  4. The signing code is built (only after you approve this design), reviewed by security and red-team, and the key-vault tests (S1, S3) pass.
  5. **Your explicit written OK** for the canary, with its budget. Default: no canary; we stay on paper.

### Phase 4: Optional canary (only with your explicit OK; about 2–4 weeks)
- **What it is:** about 50 real trades at 0.1 SOL, with a fixed budget (default 1 SOL including fees). It is a **paid measurement, not an earner**. Its only job is to measure the gap between paper fills and real fills, and how much each sending path leaks. It does **not** need the 25 SOL bankroll.
- **What you do:**
  - create the key in the key vault by following our steps;
  - send the canary budget to the hot wallet from *your* wallet (we never move funds);
  - read the weekly canary report.
- **Gate 4 → 5. All required:**
  - ≥ 50 canary trades;
  - the "paper filled / real failed" gap ≤ 2 points per trade, and the rule still passes with that gap applied;
  - each sending path leaks ≤ 0.5% (leaky paths are dropped);
  - no unexplained wallet movement;
  - real time-to-flat within the drill target;
  - projected profit at the capped trade count beats the bills;
  - **your explicit OK, a bankroll of ≥ 25 SOL, and a tuition budget set.**

### Phase 5: Live at the floor size
- 0.25 SOL bets at 1% of the bankroll, inside every cap.
- Bets grow only in proven steps (1× → 2× → 4×), and only with ≥ 50 SOL.
- **Automatic demotion to paper** on any of: the drawdown stop (20% of the bankroll at the floor; only you can resume), the crowding kill, the decay alarm, or a Pump.fun market-structure change (fast re-validation first).
- **What you do:** top up the hot wallet when asked, and read the weekly report.

**Rough calendar (if accounts are ready quickly) [UNVERIFIED]:** recording from week 2, research from week 3, the paper bot from week 5, the earliest canary decision around weeks 9–12, the earliest live decision around months 3–4. Realistic edges of 5–8% per trade need about 600–1,800 trades to prove [DERIVED], so the paper phase may run longer.

---

## 8. The stop rule: when we conclude there is no edge and stop spending
These checkpoints are fixed now. Each sends you a one-page verdict.

1. **Week 4 of recorded data.** If buy-every-graduate after BOOST loses more than 10% per trade at *every* entry time we test, **and** none of the top-5 ideas passes its first screen, we recommend **recorder-only mode**: about **$160 a month** (range $130–210, depending on whether Helius can drop to its free plan), with the AI desk off and no paper bot or canary. **Default if you don't answer:** recorder-only for at most 8 more weeks, then a full stop unless an idea passes its screen on the new data.
2. **About 3 months of recorded data.** If no rule has passed Gate v2 on paper, we **stop every paid service** (the recorder too, unless you choose to keep it) and write a final report of what we learned. **Default: full stop.**
3. **Pump.fun keeps moving the goalposts.** If two market-structure changes reset our clock before any rule finishes Gate v2, we pause and report. We continue only if you agree.
4. **Live.** The drawdown stop sends us back to paper, and only you can resume. **If it trips twice, live trading ends** unless you re-approve after a written review.
5. **Your budget.** If cumulative research spending reaches your research ceiling (Q3; default about 3 months of expected bills, ~$750), we stop whatever the results.

---

## 9. Settings you can change (the main ones; all logged)
| Setting | Default | Notes |
|---|---|---|
| Minimum bet | 0.25 SOL | Recomputed from measured costs |
| Max bet | 1% of bankroll, 1% of pool SOL | Above 2% needs your second confirmation |
| Max open positions / total exposure | 3 / 3% | |
| Daily buying limit | 10% of bankroll per 24 h | Theft bound if the bot server is hacked |
| Drawdown stop | 20 × bet % (20% at 1% bets) | Never above your maximum loss |
| Daily loss limit | 6 × bet % | |
| Entry | BOOST over + 180 s settle + net flow ≥ −2% per 60 s + 0–3 s random delay | Paper default until a challenger wins |
| Stop-loss | Chosen from −20/−35/−50% by the gap study | Rule fixed in advance |
| Take-profit below 0.5 SOL | None (one-step version under test) | |

Tightening takes effect at once. Loosening waits 10 minutes on the guard host and alerts you.

---

## 10. Words used here
| Word | Meaning |
|---|---|
| **Graduate / migrate** | A coin leaves Pump.fun's bonding curve and gets a PumpSwap pool |
| **BOOST** | Pump's automatic buying of each new graduate for about 5 minutes |
| **Block / slot** | Solana's ~0.2-second time step |
| **Slippage / min-out** | The worst price we accept on a trade |
| **Sandwich** | A bot buys just before our sell and sells right after it, to take part of our price |
| **IDL** | A program's published description of its instructions and data |
| **KMS** | Amazon's key vault; it signs without ever revealing the key |
| **Paper twin** | A pretend copy of the strategy that takes every allowed trade |
| **Null / buy-every-graduate** | The simplest yardstick any rule must beat |
| **Canary** | A small, capped real-money measurement run |
| **AUC** | A 0.5–1 score of how well a number separates winners from losers; 0.5 is a coin flip |

## Tests to run once allowed
Every read-only test from rounds 1–3 still stands, with its domain, in the round files. **QUESTIONS_FOR_PAUL.md** has the single consolidated domain list. New in round 3: tests G1–G8 (`team-debate/round3/rulings.md` §8).

## Sources (most load-bearing; full lists in the round files)
- [VERIFIED-DOC] Pump.fun public docs, IDLs and change notes: https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md ; .../idl/pump_amm.json ; .../docs/SYNTHETIC_MIGRATION.md ; .../docs/FEE_PROGRAM_README.md ; .../docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md ; .../docs/PUMP_SWAP_README.md
- [VERIFIED-SEARCH] Chainstack Yellowstone pricing: https://chainstack.com/products/yellowstone-grpc/ ; https://chainstack.com/pricing/
- [VERIFIED-SEARCH] Helius plans: https://helius.dev/docs/billing/plans
- [VERIFIED-SEARCH] BOOST: https://www.kucoin.com/blog/pump-fun-boost-mode-explained ; https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives
- [VERIFIED-SEARCH] 200 ms slots: https://solanacompass.com/news/solanas-200ms-slot-time-is-live-on-mainnet-at-epoch-1053-completing-simd-0525
- [VERIFIED-SEARCH] Aug 2025 sell outage: https://protos.com/axiom-traders-panic-as-pump-fun-temporarily-bans-selling-memecoins/
- [VERIFIED-SEARCH] AWS KMS Ed25519 and SLA: https://docs.aws.amazon.com/cli/latest/reference/kms/sign.html ; https://aws.amazon.com/kms/sla
- [VERIFIED-SEARCH] Durable nonce deprecation: https://solana.com/upgrades/durable-nonce-deprecation
- [VERIFIED-SEARCH] Server prices (US regions): https://spendark.com/compare/g-4vcpu-16gb-vs-voc-g-4c-16gb/
