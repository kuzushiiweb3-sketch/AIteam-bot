# Round 1: Risk Manager proposal

## In plain English (for Paul)
- **Small bets first.** The bot starts with tiny, fixed bets. It only moves to bigger bets after 100+ real trades show the rules make money. Even then it bets a quarter of what the maths says, and never more than 1% of the wallet on one coin.
- **Every coin gets automatic exits:** a hard stop, a trailing stop, a three-step take-profit, a "dead coin" timer, and an emergency exit if the pool drains or the developer sells. **Honest warning:** if a coin collapses within one block (about a third of a second), no stop can save that trade. The small bet size is the real protection.
- **A separate "exit guard" program handles selling.** It keeps running when buying is switched off. If it crashes it restarts within seconds, the bot can't buy until it's back, and you get a phone alert.
- **You control every limit.** Each one below is a setting you can change and comes with a safe starting value. Every sale records the reason it happened.

---

## 1. Position sizing (how much to buy)

**Kelly in plain English.** Kelly is a formula for the share of your wallet to bet when you know your odds. If you bet too little you grow slowly. If you bet too much you go broke, even with a winning system. For trades it is: **bet share = W ÷ L − (1 − W) ÷ G**. Here W is the win rate, G is the average gain on a winner and L is the average loss on a loser, both written as fractions. *(Standard Kelly maths, derived here. [UNVERIFIED]: the primary page en.wikipedia.org was blocked. Confirm with any textbook.)*

**Why we use only a fraction of it.** Here is a worked example.
- With a 35% win rate, +80% average win and −30% average loss, Kelly says bet **35% of the wallet**.
- Change only the average loss to −40% (a few rugs) and Kelly drops to **6%**.
- Then lower the win rate to 30% and Kelly says **don't trade at all**.

Small errors in our estimates swing the answer wildly. After 100 trades a 35% win rate is still only known to about **±5 points** (one standard error, √(0.35×0.65/100) ≈ 0.048, derived). Betting half of Kelly keeps about **75% of the growth**, and betting twice Kelly gives **zero growth** [VERIFIED-SEARCH: ryanoconnellfinance.com/kelly-criterion; consistent with the standard growth formula, derived]. Meme-coin results are "fat-tailed": a few huge wins, many losses and some total losses. That makes the estimates even shakier.

| | A. Fixed SOL per trade | B. Fixed % of wallet | C. Volatility-scaled ("risk X% to the stop") | D. Fractional Kelly × conviction |
|---|---|---|---|---|
| How it works | e.g. always 0.05 SOL | e.g. always 0.5% of wallet | size = risk budget ÷ stop distance | ¼ of Kelly from our own stats, scaled by the conviction score |
| Data needed first | none | none | price history per coin (fresh coins have little) | 100+ closed live trades |
| Safe if our guesses are wrong? | yes | yes | **no**: it assumes the stop holds, but in a crash the loss is near 100%, not the stop distance | only with the fraction plus hard caps |
| Shrinks after losses / grows with edge | no / no | yes / slowly | yes / no | yes / yes |
| Build difficulty | trivial | trivial | medium | medium-high |
| Speed, cost per month, cost per trade | **the same for all four**: a few lines of arithmetic, no API calls, $0 [UNVERIFIED, inference] |

**Recommendation: compute several sizes and buy the smallest.**
1. **Phase 1 base size:** 0.5% of the bankroll or 0.05 SOL, whichever is smaller. This applies to all paper trades and the first 100 live trades.
2. **Kelly size** switches on only after `kelly_min_trades` (100) closed live trades, and only if the "pessimistic Kelly" is above zero. Pessimistic means three things:
   - Use the win rate minus one standard error.
   - Cap the biggest winners at the 90th percentile, so one lucky coin can't inflate the estimate.
   - Count every rug and crash in the average loss.

   The size is 0.25 × pessimistic Kelly × the conviction multiplier. It is recomputed daily over the last 200 trades. If it falls to zero or below, the bot drops back to Phase 1 size automatically and alerts Paul.
3. **Hard caps that always win:**
   - max % of bankroll per trade
   - max SOL per trade
   - max 1% of the pool's SOL side (about 1% price impact)
   - room left under the total-exposure limit
   - wallet balance minus the fee reserve
4. **Conviction** is a score from 0 to 100 given by the strategy/AI layer.
   - Below the minimum score, the bot doesn't trade.
   - Above it, the multiplier is 0.5, 0.75 or 1.0 by score band.
   - **Conviction can always shrink a bet. It can only grow one after the logs prove the high-conviction band really earns more**, with at least 30 trades per band.
   - The AI can never override a cap.

   **Paper trades never feed Kelly**, because paper fills look better than real ones. They only decide whether to go live.

---

## 2. Exit rules (each one is a setting and writes a reason code)

When several rules fire at once, they apply in this priority order: **kill-switch flatten > hard stop > liquidity/dev exit > trailing stop > time exit > take-profit.** All the rules that fired are logged.

| Rule | Safe default | Reason code |
|---|---|---|
| Hard stop | sell everything at −35% from the average buy price. Acts immediately, no confirmation wait | `EXIT_HARD_STOP` |
| Trailing stop (a stop that follows the price up) | turns on at +25%. Sells if the price falls 20% from its peak. Tightens to 15% after +150%. The fall must show on 2 consecutive price reads, so one odd trade (a "wick") can't trigger it | `EXIT_TRAIL` |
| Take-profit ladder (sell in parts) | sell ⅓ at +50% and ⅓ at +100%. The last ⅓ rides the trailing stop. By rung 2 about 1.17× the stake is back | `EXIT_TP1`, `EXIT_TP2` |
| Dead-coin timer | after 15 min, if the price has moved less than ±10% and volume is low, sell everything | `EXIT_TIME_DEAD` |
| Max hold | 240 min | `EXIT_TIME_MAX` |
| Pool draining | the pool's SOL side falls 25% below its level at buy time: sell everything | `EXIT_LIQ_DRAIN` |
| Dev / insider dump | the creator wallet sells more than 0.5% of supply, or any single wallet sells more than 2% of supply in one go: sell everything | `EXIT_DEV_SELL`, `EXIT_WHALE_DUMP` |
| Missed stop after restart | if a stop level was crossed while the exit guard was down, sell on restart | `EXIT_MISSED_ON_RESTART` |
| Kill switch | see §4 | `EXIT_KILL_FLATTEN` |

**How sells are sent.**
- **Slippage ladder:** slippage is how much worse than the quoted price we accept. Each retry is logged: 3%, then 8%, then 15%, then a 30% cap.
- **Chunked sells:** no single sell is more than 1% of the pool's SOL side.
- **Sandwich risk:** a wide slippage limit makes us an easy target for "sandwich" bots. They extracted roughly $370M–$500M on Solana in the 16 months to May 2025 [VERIFIED-SEARCH: solanacompass.com Accelerate-25]. Emergency sells should therefore go through whichever protected send path the execution specialist picks. For reference, Jupiter's own stop-loss orders default to 20% slippage [VERIFIED-SEARCH: developers.jup.ag/docs/trigger, fetch blocked].

**Honest limits.**
- Solana produces a slot (one block opportunity) every ~350 ms since Aug 2026. The docs still say 400 ms [VERIFIED-SEARCH: thedefiant.io; docs.rs solana-clock].
- After graduation, the pool's LP tokens are burned and liquidity can't be removed by hand. That blocks the classic "pull the pool" rug on the main pool [VERIFIED-SEARCH: blofin.com academy]. Creators can still dump their own coins [VERIFIED-SEARCH: emergentmind.com/topics/pump-fun].
- PumpSwap is a constant-product pool [VERIFIED-DOC: PUMP_SWAP_README.md]. So one sale of tokens equal to half the pool's token reserve cuts the price by about **56%**, and a sale equal to the whole reserve by about **75%**. *(Derived maths, [UNVERIFIED] until checked against the official SDK quote.)*
- Our stop fires at the next price we see, so **a −35% stop can fill at −70%.** Paper trading must fill stops at the first real price after the trigger, never at the stop level.

**Reading the pool correctly.** Price and liquidity must use PumpSwap's *effective quote reserves*: the vault balance plus `virtual_quote_reserves`, a signed number that can be negative [VERIFIED-DOC: NEGATIVE_VIRTUAL_QUOTE_RESERVES.md]. The two Pump.fun docs disagree on whether non-zero values are live yet. PUMP_SWAP_README says "0 on all pools today", while the negative-reserves doc says "from Sep 30". Design for both. If decoding fails, the bot pauses buys and the exit guard falls back to an aggregator quote.

**BOOST.** Since July 2026, Pump.fun spends about 20% of migration liquidity (17.6 SOL on SOL pairs) buying the coin back over the first 5 minutes after graduation [VERIFIED-SEARCH: kucoin.com BOOST explainer, cryptobriefing.com]. That is artificial buying with a cliff at minute 5. The safe default is `post_migration_buy_delay_sec = 300`, and shadow logs show what earlier entries would have done. I'm flagging this to the strategist.

**Alternatives compared.**
- **Trailing stop:**
  - (a) fixed %: simple and predictable, but gets shaken out in wild coins.
  - (b) ATR / "chandelier" style: the stop sits a multiple of recent average price swing below the peak [VERIFIED-SEARCH: stockcharts chandelier-exit]. It adapts to each coin, but fresh coins have almost no history, so the first minutes are noise.
  - (c) stepped fixed %, tightening as profit grows.

  **Pick (c) now.** Run (b) as a *shadow exit*: the exit guard also logs what 2–3 alternative rule sets *would* have done, with no money involved. That makes refining rules easy.
- **Take-profit:**
  - a single target: wins a lot or nothing
  - **a ladder (pick):** locks in gains and lowers regret
  - trailing stop only: gives back a lot on reversals

---

## 3. Portfolio limits, 4. Kill switch

**Principle: "Buys need every light green. Sells need just one red light."** Any doubt blocks buying. A false sell costs only missed upside, while a missed sell costs real money. **The AI can make an exit happen sooner, never later**: it may tighten stops or say "sell now", but it can never loosen or cancel an exit.

| Level | What happens | Exits? |
|---|---|---|
| L1 PAUSE BUYS | no new buys | keep running normally |
| L2 WIND DOWN | L1, plus trailing stops tighten to 10% and everything is sold within 30 min | yes |
| L3 FLATTEN | sell everything now, in chunks, using the slippage ladder | yes |
| L4 FREEZE ALL | no transactions at all. Only for "the bot itself is misbehaving" (for example a sell loop or unknown transactions) | **stopped**: Paul is alerted at once |

| Trigger (automatic unless noted) | Level | Who un-pauses |
|---|---|---|
| Paul's button: dashboard, Telegram command or a flag file on the server | any | Paul |
| Daily loss limit hit (realized losses plus the current value of open positions) | L1 | auto at day reset |
| Max drawdown from the wallet's peak value hit | L1 + alert | **Paul only** |
| Losing streak of N trades | L1 for the cooldown | auto |
| Both price feeds stale for more than 5 s, or sources disagree by more than 5% | L1 | auto after 60 s healthy |
| Send/RPC failure rate above 30% over the last 10 transactions | L1 | auto when healthy |
| Exit guard heartbeat older than 5 s | L1 | auto |
| Exit guard crash loop (3 restarts in 10 min) | L1 + "safe mode" exits only + alert | Paul |
| Wallet on-chain balance ≠ the bot's ledger | L1 + alert | Paul |
| Any transaction from the wallet the bot didn't send | **L4** + alert | Paul |
| Fee reserve below its minimum | L1 | auto when topped up |
| Settings file invalid | L1. Exits keep the last good settings | Paul |

The buy side reads the kill switch before **every** buy and **fails closed**: if it can't read the switch, it doesn't buy.

---

## 5. The always-on exit guard

**What it is.** A separate, small program. It has no AI, no scanner and no heavy libraries. Its only jobs are to watch open positions and sell.

**How it works.**
- **Positions:** it learns positions from an append-only journal *and* from the wallet's actual on-chain token balances. The chain is the truth. The buy side writes its intent to the journal **before** sending a buy.
- **Its own price feed:** it reads the pool accounts directly through two different RPC providers. (RPC is the server you ask for blockchain data.) It uses live updates plus a 1-second poll as backup. An aggregator price is only a sanity check.
- **Its own send path:** a primary sender plus a backup RPC, with a priority-fee cap.
- **Fee reserve:** a fixed SOL reserve that buys can never touch, so sells can always pay their fees.

**Interlock.** The guard writes a heartbeat ("I'm alive, last price for each position at time T") every second. The buy side won't buy if the heartbeat is more than 5 s old. **No exit guard means no new buys.**

**If it crashes:**
1. **Restart.** A process supervisor restarts it within seconds. Linux systemd offers a watchdog: the program must keep pinging, or it is treated as failed [VERIFIED-SEARCH: man7.org sd_watchdog_enabled(3)]. Whether a missed watchdog ping triggers `Restart=` is [UNVERIFIED]; the man7.org page was blocked.
2. **Reconcile on restart:**
   - Re-read the wallet and match it to the journal.
   - Check the status of any sell signature sent before the crash (each one is logged *before* sending). This avoids double-selling.
   - Before every sell, sell only what is actually held.
   - Restore trailing peaks; they are saved to the journal at every new peak.
   - Fire any stop that was crossed while the guard was down.
   - Adopt "orphan" tokens (held but missing from the journal), apply tight default exits to them, and send an alert.
3. **Crash loop** (3 restarts in 10 min): L1 pause, safe mode (hard stop and trailing stop only), and a phone alert.
4. **Outside watchdog:** a tiny monitor on a *different* provider pings the guard. It alerts Paul if the guard has been down more than 30 s while positions are open. This is the same idea as an exchange "dead man's switch" [VERIFIED-SEARCH: blog.bitmex.com]. It **does not hold the key**, so it alerts but doesn't trade.
5. **Total outage** (all RPCs down): nothing on-chain is possible for anyone. The alert includes manual-exit steps. Whether Paul gets an emergency manual-sell route is a question for Paul (see open risks).
6. **Paper mode:** a crash is simulated honestly. Missed time is filled at the real later price.

| Option | Speed | Cost/month | Cost/trade | Reliability | Build |
|---|---|---|---|---|---|
| A. Exits inside the main bot | fast | $0 extra | $0 | **poor**: one crash or a slow AI call blocks exits | easy |
| **B. Separate guard + supervisor + buy interlock + outside watchdog (pick)** | fast (local decision, latency set by the feed) | ≈ $0 extra on the server. The 2nd RPC is costed by infra [UNVERIFIED] | $0 | good | medium |
| C. B + hot standby guard in a 2nd region with a leader lock | fast | +1 server [UNVERIFIED cost] | $0 | best uptime | hard. The key sits on 2 machines and double-sells are possible. **Phase 3, only if the bankroll grows** |
| D. Backstop resting stop orders (Jupiter Trigger V2, now with trailing stops) | runs on Jupiter's side | API key needed | Jupiter fee [UNVERIFIED] | survives *our* outage | medium. Tokens sit in Jupiter's vault, an extra transaction is needed before our own sells, and support for fresh tokens is unknown [VERIFIED-SEARCH: developers.jup.ag/changelog/2026-07]. **Evaluate later, not by default** |

---

## 6. Every limit as a setting you control

**Tightening a limit takes effect at once. Loosening one waits 10 minutes.** Every change is logged with its before and after values. The dashboard refuses values outside the hard bounds, which stops typos (for example 50 instead of 0.5).

| Setting | Safe default | Hard bounds | What it does |
|---|---|---|---|
| `paper_mode` | **ON** | Paul only | no real trades |
| `bankroll_sol` | Paul sets it | ≤ wallet balance | money the bot may use. Keep everything else in a different wallet |
| `base_trade_pct` / `max_trade_sol` | 0.5% / 0.05 SOL | 0.1–2% / 0.01–1 | Phase 1 size |
| `max_trade_pct` | 1% | 0.1–5% (above 2% needs a 2nd confirm) | cap per trade, even with Kelly |
| `kelly_enabled` / `kelly_fraction` / `kelly_min_trades` | OFF / 0.25 / 100 | – / 0.05–0.5 / ≥50 | Kelly phase |
| `conviction_min` / `conviction_can_upsize` | 60 / OFF | 0–100 / – | conviction gate |
| `max_pool_share_pct` / `min_pool_sol` | 1% / 40 SOL | 0.1–3% / ≥10 | liquidity caps |
| `max_open_positions` / `max_exposure_pct` | 3 / 3% | 1–10 / 0.5–20% | portfolio |
| `max_buys_per_hour` / `per_day` | 4 / 20 | 1–30 / 1–200 | pace |
| `reentry_cooldown_min` / `allow_average_down` | 60 / OFF | ≥0 / – | no revenge buys |
| `daily_loss_limit_pct` / `day_reset_utc` | 3% / 00:00 | 0.5–10% | daily stop |
| `max_drawdown_pct` | 10% | 2–30% | drawdown stop. Only Paul resets it |
| `loss_streak_n` / `cooldown_min` | 4 / 60 | 2–10 / 10–1440 | cool-down |
| `fee_reserve_sol` | 0.05 | ≥0.01 | SOL kept for sell fees [UNVERIFIED size; measure fees in paper] |
| `hard_stop_pct` | −35% | −10 to −80% | hard stop |
| `trail_start_pct` / `trail_pct` / `trail_tight_pct` | +25% / 20% / 15% | – / 5–50% | trailing stop |
| `tp_ladder` | ⅓ @ +50%, ⅓ @ +100% | any | take-profits |
| `dead_coin_min` / `max_hold_min` | 15 / 240 | 3–120 / 10–1440 | time exits |
| `liq_drain_pct` / `dev_sell_pct` / `whale_dump_pct` | 25% / 0.5% / 2% | 5–80% / 0–5% / 0.5–10% | emergency exits |
| `post_migration_buy_delay_sec` | 300 | 0–1800 | skip the BOOST window |
| `sell_slippage_ladder` / `max_sell_slippage` | 3/8/15% / 30% | cap ≤50% | sell retries |
| `feed_stale_sec` / `price_disagree_pct` | 5 / 5% | 1–60 / 1–20% | data health |
| `heartbeat_stale_sec` / `crash_loop_n` | 5 / 3 per 10 min | 2–30 / 2–10 | exit guard health |
| `rpc_fail_pause_pct` | 30% | 5–80% | send health |

**Recommendation.**
- Sizing: "smallest of" sizing with fixed tiny bets first and quarter-Kelly only once it's earned.
- Exits: stepped trailing stop plus a ⅓-⅓ take-profit ladder plus hard, time and liquidity exits, with shadow logs of alternative exits.
- Kill switch: 4 levels.
- Exit guard: option B.
- Limits: everything in the table above.

## 7. Open risks
1. **Gap risk is real and unmeasured.** A big holder can crash the price in a single block. Bet size, not the stop, is the protection. The test below measures how often it happens.
2. **Sells may fail when everyone sells.** Congestion and sandwich bots hit exactly then. This depends on the execution specialist's send path.
3. **Kelly estimates drift.** The meme market changes from month to month, and an edge can vanish. Hence the rolling window and the automatic fall-back to Phase 1 size.
4. **Pump.fun changes its programs often:** signed reserves, BOOST, holder-reward coins [VERIFIED-DOC: pump-public-docs README]. A wrong pool decode means wrong stops. Mitigations: cross-checks, pause buys on any decode error, and a pinned decoder version.
5. **Meme coins crash together.** The exposure cap and max-positions cap are the only defence.
6. **Signing key.** The exit guard must always be able to sign, so key security is the security specialist's issue. **Question for Paul:** do you want an emergency manual-sell route? That would mean the trading wallet can be opened in a wallet app, which is a security trade-off.
7. **Default values are placeholders** until Paul's own rules arrive (QUESTIONS_FOR_PAUL).

## 8. Tests to run once allowed (read-only, no transactions)
1. **Gap study.** For 1,000 graduated coins, find the biggest one-slot price drops and the share of −35% stops that would have filled below −50%. Needs `api.mainnet-beta.solana.com` plus the chosen history provider (for example `mainnet.helius-rpc.com`).
2. **Exit-feed speed.** Measure pool-account update delay from two RPC providers. Same domains as test 1.
3. **Constant-product maths.** Compare the 56%/75% figures and buy price impact against the official PumpSwap SDK quote functions. Needs `registry.npmjs.org` and `raw.githubusercontent.com`. Local maths only.
4. **Jupiter Trigger V2.** Check vault custody, fees and support for fresh PumpSwap tokens. Needs `developers.jup.ag`, which was blocked this session.
5. **systemd watchdog.** Check whether a missed watchdog ping triggers a restart. Needs `www.man7.org`, which was blocked; alternatively test it in a local container.
6. **Crash drills in paper mode.** Hard-kill the exit guard with open paper positions. Check that restart, reconciliation, missed-stop sells and the buy interlock all work.

*Hosts that failed this session: developers.jup.ag, www.man7.org, en.wikipedia.org, theblock.co.*

**Sources:**
- https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md
- https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md
- https://ryanoconnellfinance.com/kelly-criterion/
- https://thedefiant.io/news/blockchains/solana-activates-350-millisecond-slots-on-mainnet
- https://blofin.com/academy/education/pumpfun/pumpswap-canonical-pool-ownership
- https://www.emergentmind.com/topics/pump-fun
- https://www.kucoin.com/blog/pump-fun-boost-mode-explained
- https://solanacompass.com/learn/accelerate-25/scale-or-die-at-accelerate-2025-the-state-of-solana-mev
- https://developers.jup.ag/changelog/2026-07
- https://blog.bitmex.com/api_announcement/dead-mans-switch-enabled-for-api-keys-with-order-cancel-permissions
- https://www.man7.org/linux/man-pages/man3/sd_watchdog_enabled.3.html
- https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-overlays/chandelier-exit
