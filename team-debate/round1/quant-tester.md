# Round 1: Quant Tester. How we prove a rule works before real money

**In plain English (for Paul):**
- Your rules get three tests before any real SOL is used. First a **backtest**: we replay old trades and ask what the rule would have done. Then **paper trading**: the bot runs on the live market but only pretends to buy. Then a tiny **canary**: real money at a size too small to hurt.
- The pretend trades are charged every real cost: network fees, tips, the exchange fee, the price moving against us while our order travels, and orders that fail.
- A rule goes live only when you flip the switch, and only after it passes a written checklist. Every rule edit restarts the clock.
- New rule ideas run as **shadows** beside the current rule on the same coins, so you can compare them fairly.

Source tags look like `[VD S3]`. **VD** means VERIFIED-DOC (I read the primary source this session). **VS** means VERIFIED-SEARCH (seen only in search results). **UNV** means UNVERIFIED. The numbered sources are at the bottom. Shell network was blocked. WebFetch worked only for `raw.githubusercontent.com`. `docs.dune.com` failed to resolve, so I did not try other hosts.

---

## 1. Where historical trade data comes from

**Survivorship bias** means testing only on coins that are still alive, which makes every rule look better than it is. Rugged and dead coins must stay in the data. So our list of coins must come from the on-chain migration events themselves, never from a provider's "token list".

| Option | What it gives | Cost per month | Complete? Dead coins kept? | Has pool reserves (needed for real slippage)? | Freshness | Build difficulty |
|---|---|---|---|---|---|---|
| **A. Our own recorder** (stores every Pump/PumpSwap event from the live feed) | Every trade, migration and fee event, plus what our bot knew and decided at each moment | No extra cost. It reuses the live feed the data-feed agent picks | Complete going forward, if gaps are detected (see risks). No history before the day it starts | **Yes.** Every PumpSwap `BuyEvent`/`SellEvent` carries `pool_base_token_reserves`, `pool_quote_token_reserves`, `virtual_quote_reserves`, every fee amount and `ix_name` [VD S1]. The curve's `TradeEvent` carries the virtual and real reserves [VD S2] | Real time | Medium. Needs storage and alarms for gaps and failed decoding |
| **B. Dune** (SQL over decoded chain data) | `dex_solana` base trades include `pumpdotfun` and `pumpswap` models [VD S3]. The PumpSwap model starts 2025‑02‑20 and has `block_slot`, `tx_index` and `fee_tier` [VD S4] | Analyst about $75, Plus about $399. The free plan lost query access for many users on 2026‑09‑10 [VS S5, S6] | It is raw chain data, so dead coins are included [UNV: test T1]. **Possible gap:** the trade model never mentions the new v2 trade instructions, and it matches transfers in a way the "fees kept in pool" change may break [VD S4, S7] | Not in the curated table [VD S4]. The decoded event table `pump_amm_evt_buyevent` exists [VD S4]. Whether it includes the new fields is not known [UNV: T2] | Curated Solana tables lag 3–7 h [VS S8]. That is fine for backtests and useless for live trading | Low. SQL plus export |
| **C. Bitquery** (GraphQL API and Parquet archive) | Protocols labelled `pump` (curve) and `pump_amm` (PumpSwap). History older than about 30 days comes from an archive [VS S9] | Pro is about $69 (the cheapest plan licensed for commercial use, billed yearly). Usage is metered in points [VS S10] | Claims full history [VS S9]. Not tested [UNV: T3] | Unclear [UNV] | Real time and archive | Low to medium |
| **D. Birdeye** (prices, candles, trades) | Price candles and recent trades | $39–$199 for 1.5M–15M compute units. Historical endpoints cost extra units per call [VS S11] | Unknown whether dead coins stay listed [UNV: T4] | **No.** Candles (open, high, low, close prices) cannot reproduce slippage | Real time | Low |
| **E. Old Faithful raw archive** plus our own decoder | Every Solana block since the first one, as files. A new epoch appears within about 4 epochs of closing [VS S12] | The download may be free [UNV]. Storage and compute are large [UNV] | Most complete option | Yes, after we decode it ourselves | Days behind | **Very high** |
| *Rejected:* Google BigQuery public Solana data | Reported as stopped or lagging for months [VS S13] | Billed per query | Not reliable | Partly | Stale | Medium |
| *Rejected:* Flipside | Its query website shut 2025‑07‑01. The data moved to Snowflake [VS S14] | A free trial, then Snowflake bills you | Unknown | Unknown | Unknown | Medium |
| *Rejected:* Codex | Solana data starts 2024‑03‑20, and sub-minute candles are kept only 24 h [VS S15] | Free tier, then pay as you go | n/a | No | Real time | Low |

**Data choice: A plus a short B.** The recorder (A) starts on day 1 and becomes the trusted data. Buy one month of Dune Analyst (about $75), pull about 60–90 days of raw PumpSwap and curve events, then cancel. Before any Dune result counts, check it against our recorder on the days both cover (T1, T2). Use Birdeye only for charts, never to judge fills. A 24-hour replay service (for example Helius LaserStream, which needs a $499+/month plan [VS S16]) can repair recorder outages only if the data-feed agent already pays for it.

**Pump's programs keep changing, and this hits backtests directly.** Since September 30 (the doc gives no year; 2026 is my inference), pool quote reserves = vault balance + `virtual_quote_reserves`, and that number can be **negative** [VD S17]. v2 trades keep fees inside the pool [VD S7]. A buy that finishes the curve now spans both the curve and the new pool and emits `PostCompleteBuyEvent` [VD S18]. Fee rates depend on market-cap tiers read from an on-chain fee config [VD S19]. So the recorded data tags every event with the **program version in force at the time**, and results are reported separately for each version.

## 2. Backtest design: no peeking at the future

**Look-ahead bias** means a test accidentally uses information that did not exist yet at decision time.

1. **One event tape.** Every event goes into a single list ordered by (slot, transaction index, instruction index). A slot is one Solana block, about 0.4 s [UNV]. The bot's **real decision code** reads this tape through the same input it uses live. There is no separate backtest copy of the rules.
2. **Two timestamps on everything.** Each item records when it happened on-chain and when *we* learned it. The replay releases an item only at the time we learned it. Off-chain data (holder counts, social posts, AI scores, token info) can only be backtested from the day the recorder started saving it. Fetching it now from an API would give today's values, which is look-ahead.
3. **AI can also see the future.** An AI model trained after a coin pumped may "remember" that it pumped. Research calls this parametric look-ahead bias [VS S20, S21]. So AI judgments in a backtest must come from outputs saved live at the time. Re-running the AI on old coins is allowed only with the name and ticker hidden, and it must be labelled "contaminated".
4. **Two ways to replay, compared:**

| | Event-tape replay (**chosen**) | Candle backtest (Birdeye-style) |
|---|---|---|
| Accuracy | Exact pool state at each slot | 1-minute guesses. Slippage and failures are invisible |
| Cost | Our storage only | API units |
| Speed | 30 days of replay in minutes [UNV] | Fast |
| Build effort | Medium. It reuses the bot's own code | Low, but the code is separate and drifts from the bot |

5. **Walk-forward testing with a locked holdout.** Tune on weeks 1–3, test on week 4, then move the window forward one week. The newest 2 weeks are a **locked holdout**. A rule version may look at it once. After that look, those 2 weeks count as used for that version.

## 3. Paper trading: fills charged at real cost

**One code path.** Paper and live share everything: data in, features, rules, risk checks, position sizing, and building the exact transaction. They differ only at the last step, where paper sends the trade to the fill simulator and live sends it to the signer and sender.

**Three ways to price a paper fill, compared.** Local math on recorded pool reserves is **chosen**: it costs nothing, it uses the exact formula, and it can include delay. Asking an aggregator for a quote (for example Jupiter) is rejected. That quote is at decision time, not at landing time, it costs API calls, and it may route through a different exchange. The RPC check `simulateTransaction` is exact against the current chain state but misses the price moving while the order travels. It is worth adding as a pre-live bug check once Paul approves the build.

| Cost charged on every paper trade | How it is modelled |
|---|---|
| Network base fee | 5,000 lamports per signature, **charged even when the trade fails** [VS S22]. 1 SOL = 1 billion lamports |
| Priority fee | Compute-unit price × compute-unit limit ÷ 1,000,000 [VS S22]. It uses the same fee estimate the live sender would choose at that moment |
| Jito tip (an extra payment to get into a block fast) | At least 1,000 lamports, or 5,000 through Helius [VS S23]. A bundle (a group of transactions sent together) that fails does not land and costs nothing [VS S24] |
| Exchange fee | PumpSwap 20 bps to the liquidity providers plus 5 bps protocol fee [VD S25], plus the coin-creator fee for the market-cap tier, all read from the live on-chain fee config [VD S19]. **Never a hard-coded 0.25%.** (1 bp = 0.01%.) |
| Slippage and price impact | Constant-product math on the *effective* quote reserves (vault balance + signed `virtual_quote_reserves`) [VD S17]. Example: a 0.5 SOL buy into a pool with 80 SOL moves the price by about 0.6% before fees (my arithmetic; the pool size is only an illustration) |
| Delay | The fill uses the pool **as it was at the landing slot**. Landing slot = decision slot + our measured processing delay + a modelled 2‑slot sending delay. That starting guess is conservative and gets corrected in the canary [UNV]. Real trades by others in that gap move the price against us |
| Failed trades | (a) **Fixed rule:** if the price at landing broke our slippage limit, the trade fails, fees are paid, and no position opens. That matches reality, where about 80% of failures in 2024 were slippage errors [VS S26]. (b) **Random drops** at a set rate, starting at 10% [UNV]. Bots fail far more often than people: 58% against 6% in a 2025 study [VS S26] |
| Token account deposit | 0.00203928 SOL per new token account (an account that holds one coin), returned when it is closed [VS S27]. Counted as locked cash, and as a real cost if never closed |
| Exits | Same model. If the developer dumps before our sell lands, we get the post-dump price |
| Coins priced in other tokens | Curves can now be priced in tokens other than SOL (`quote_mint`) [VD S2]. Profit is always converted to SOL at that moment |

Two honest limits. Paper size is capped at 1% of pool reserves, and larger trades are flagged "unrealistic" because the simulator does not push our own trade into the pool for other traders. The simulator must also pass test T6, matching real past trades to the lamport, before any paper number is trusted.

## 4. The numbers Paul sees (every number is after all costs)

| Metric | Plain-English meaning | Why it matters |
|---|---|---|
| P&L after all fees | SOL gained or lost once every fee, tip and slippage is paid | The only number that counts |
| Win rate | Share of trades that made money | Meme coins often win under 40% and still profit [UNV]. Read it next to the averages below |
| Average win / average loss | Typical SOL gained on winners, and typical SOL lost on losers | Shows whether the winners pay for the losers |
| Profit factor | Total won ÷ total lost. Above 1.0 means profitable | A quick health check |
| Expectancy per trade | Average SOL made or lost per trade. "Each trade is worth +0.012 SOL" | The core go-live number |
| Max drawdown | The biggest fall from a high point to a later low, in SOL and % | How much pain to expect |
| Fee drag | Share of gross profit eaten by costs | If over 50%, the rule is feeding the network, not you |
| Luck check | Profit with the 3 best trades removed | Shows whether a few lucky trades carried everything |
| Missed-coin rate | Coins the rule *should* have bought (re-checked later on the tape) that the bot missed or reached too late | Catches blind spots and outages |
| Coverage | Share of all migrations on-chain that the recorder saw | Catches data gaps |
| Time to entry | Seconds from migration to our (pretend) fill. Typical and slowest 10% | Shows whether we are too slow |
| Failed-trade rate and fees lost | How many orders failed and what they cost | |
| Paper-vs-live fill gap | During the canary: how much worse real fills were than paper predicted | Shows whether the simulator is honest |
| Breakdown by rule and reason | All of the above per rule, per rule version and per rejection reason ("killed: dev wallet over 10%") | This is how you refine rules |

A warning built into the screen: rejection-regret views ("coins rule X rejected that later went 3x") come from hindsight. They suggest new ideas to test. They never edit a rule on their own.

## 5. Go-live gate (a ladder, and only Paul flips each step)

**Three gate styles, compared.** "Paper for 30 days" ignores how many trades happened. A sequential test checks constantly and stops early when the evidence is strong; it is faster but easier to misuse. A **fixed checklist plus a resampling test (chosen)** is simple and hard to fool. The resampling test (statistically, a bootstrap) means re-drawing the trade list thousands of times to see how far luck alone could move the result.

**Steps:** Backtest → Paper → Canary (tiny real money) → Normal size. A rule version must pass **all** of these to move from Paper to Canary:
1. At least **200 closed paper trades over at least 21 days**, including at least one quiet week and one busy week. The 2026 graduation rate swung between 0.26% and 6.7% [VS S28].
2. Expectancy after costs is above 0 with 90% confidence on the resampling test. Example: if each trade's result swings by ±60% (one standard deviation), 200 trades only prove an edge above about **+7% per trade**. Small edges cannot be proven quickly (my arithmetic; the ±60% figure is an assumption).
3. The luck check is not negative.
4. Max drawdown is under **25%** of the paper bankroll. This is a placeholder; Paul sets it.
5. Paper results fall inside the backtest's range for the same weeks. If paper is much worse, the backtest is lying.
6. Missed-coin rate is under 5%, and no data-integrity alarm is open.
7. **Trial counter.** Every rule variant ever tested counts as a trial. More than 20 trials means 95% confidence is needed instead. Trying many variants makes a lucky winner likely [VS S29, S30].

**Canary:** a tiny fixed size (for example 0.05 SOL per trade), a daily loss cap and at least 50 live trades. If the fill gap is worse than the simulator's margin, the rule goes back to paper and the simulator is recalibrated. Two failures in a row send it back automatically: the drawdown cap, or a fill gap above the limit. **Any rule edit is a new version, and its clock restarts.**

## 6. Rule-refining loop: champion and shadows

| | **Shadow rules (chosen)** | Split by coin | Split by time (week A, then week B) |
|---|---|---|---|
| How | Every version judges every coin. Only the current rule ("champion") trades; the others paper-trade beside it | Each coin goes to A or B at random | A runs one week, B the next |
| Fairness | Best: both see the same coins at the same moment, so the comparison is paired | Good, but needs twice the coins | Poor: the market itself changes |
| Cost | CPU, plus AI calls if a shadow uses AI. Limit: 3 AI-using shadows [UNV cost] | Same | Same |

A challenger replaces the champion only if it beats the champion on coins where the two disagreed. That needs at least 100 such coins and 90% confidence on the resampling test. The new champion then still goes through the gate. Before any shadow starts, a new idea is replayed on the last 30 days of tape in minutes, to drop bad ideas cheaply.

## 7. Recommendation
1. Start the event recorder on day 1. It is the trusted data, and paper trading needs it anyway.
2. Buy one month of Dune (about $75) for the first backtests, checked against the recorder.
3. Use one event-tape replay engine for both backtest and paper. It runs the bot's real code and a fill simulator that reads true pool reserves, the fee config, delay and failures.
4. Go live in steps: Paper → Canary → Normal, using the gate in section 5. Paul flips every step.
5. Use shadow rules for every refinement.

## 8. Open risks
- **An optimistic simulator** is the most common way these projects lose money. Mitigation: T6, plus the canary measuring the fill gap.
- **Dune may lag Pump's program changes** (v2 trades, synthetic migration, negative virtual reserves) and so miss or mis-size trades [UNV: T2].
- **Fat tails.** A handful of huge winners decides the result, so small samples lie. Mitigation: the luck check and the 200-trade minimum.
- **Our own size moves thin pools.** Mitigation: the 1% cap.
- **Decoder breakage** on the next Pump update. Unknown instruction names must raise an alarm and pause trading. They must never be skipped silently.
- **Paper and live code drifting apart.** An automated test must prove both modes build an identical transaction.

## 9. Tests to run once allowed

| # | Test | Domain(s) needed |
|---|---|---|
| T1 | Count migrations per day in Dune and in our recorder over 14 days. They must match within 0.5%. Also spot-check 20 rugged coins | `dune.com`, `api.dune.com`, `docs.dune.com` |
| T2 | For txs with `ix_name` like `%v2` in `pumpdotfun_solana.pump_amm_evt_buyevent`, check they appear in `dex_solana.trades` with correct amounts. Confirm `virtual_quote_reserves` is signed | `dune.com`, `api.dune.com` |
| T3 | Pull the full trade history of a coin that rugged 60+ days ago | `graphql.bitquery.io`, `bitquery.io/pricing` |
| T4 | Ask Birdeye for candles of a coin that died 60+ days ago | `public-api.birdeye.so`, `docs.birdeye.so` |
| T5 | Read the PumpSwap global config and fee-config accounts and compare them with the published tiers | the chosen RPC host (e.g. `api.mainnet-beta.solana.com`), `github.com/pump-fun` |
| T6 | Recompute 500 real recorded PumpSwap trades from the reserves before each trade plus the fee config. The output must equal the on-chain amount to the lamport | RPC host as in T5 |
| T7 | Measure slot time and our detect-to-decision delay (read-only) | RPC host, plus the data-feed provider |
| T8 | Confirm today's minimum Jito tip | `docs.jito.wtf` (blocked this session) |
| T9 | Check BigQuery freshness, cost-checked first: `bq query --dry_run 'SELECT MAX(block_timestamp) …crypto_solana_mainnet_us…'` | `bigquery.googleapis.com` |
| T10 | Measure Old Faithful epoch size and download speed | `files.old-faithful.net`, `docs.old-faithful.net` |
| T11 | Confirm Dune and Bitquery prices on their live pricing pages | `dune.com/pricing`, `bitquery.io/pricing` |

## Sources
S1 PumpSwap IDL https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json ·
S2 Pump IDL https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json ·
S3 https://raw.githubusercontent.com/duneanalytics/spellbook/main/dbt_subprojects/solana/models/_sector/dex/dex_solana_base_trades.sql ·
S4 https://raw.githubusercontent.com/duneanalytics/spellbook/main/dbt_subprojects/solana/models/_sector/dex/pumpswap/pumpswap_solana_base_trades_backfill.sql ·
S5 https://cryptobriefing.com/dune-free-plan-view-only-access/ ·
S6 https://obolcryptocoin.com/companies/dune/ ·
S7 https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md ·
S8 https://docs.dune.com/data-catalog/data-freshness.md (seen in search only) ·
S9 https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/pump-swap-api/ ·
S10 https://bitquery.io/pricing ·
S11 https://docs.birdeye.so/docs/pricing ·
S12 https://docs.old-faithful.net/ ·
S13 https://discuss.google.dev/t/public-solana-bigquery-dataset-crypto-solana-mainnet-us-stopped-updating-on-march-31-2025/185629 ·
S14 https://x.com/flipsidecrypto/status/1937114061575168275 ·
S15 https://docs.codex.io/extra/faq.md ·
S16 https://www.helius.dev/docs/laserstream/laserstream-vs-dedicated-nodes.md ·
S17 https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md ·
S18 https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md ·
S19 https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md ·
S20 https://arxiv.org/abs/2605.24564 ·
S21 https://arxiv.org/abs/2603.11838 ·
S22 https://solana.com/docs/core/fees/fee-structure ·
S23 https://www.helius.dev/docs/sending-transactions/send-bundle.md and https://www.alchemy.com/docs/chains/solana/solana-jito-bundles-and-transactions.md ·
S24 https://docs.getblock.io/guides/how-to-optimize-solana-transactions-with-jito-bundles ·
S25 https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md ·
S26 https://arxiv.org/html/2504.18055v1 and https://fxstreet.com/cryptocurrencies/news/solana-failed-transactions-exceed-70-as-meme-coin-frenzy-attracts-bots-202403210927 ·
S27 https://www.helius.dev/docs/rpc/guides/getminimumbalanceforrentexemption.md ·
S28 https://www.theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives and https://www.dextools.io/news/pump-fun-graduation-collapse-solana-fees-2026 ·
S29 https://papers.ssrn.com/abstract=2326253 ·
S30 https://papers.ssrn.com/abstract=2460551
