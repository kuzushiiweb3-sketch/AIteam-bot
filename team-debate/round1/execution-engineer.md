# Round 1: Execution engineer (buying and selling fast and cheap)

**In plain English (for Paul):**
- Every buy and later sell of a freshly graduated coin costs roughly **3.5–4% of the position** (0.1–0.5 SOL), and **more than 7% at 2 SOL** in a fresh pool. Most of that is Pump.fun's own 1.25% pool fee each way, which no route avoids. The bot's rules must expect at least that much gain before a trade can make money.
- I recommend **building trades ourselves with Pump.fun's official toolkit** (no middleman fee). Jupiter's free "build" service checks every price and acts as a backup route. Jupiter's all-in-one service and PumpPortal both add 1–2% per round trip, and PumpPortal's fastest option holds your wallet key, so I reject them for the main path.
- Buys go out as **Jito "bundles"**: if the price moved too far, the trade simply doesn't happen and costs nothing. Sells use a **multi-path sender (Helius Sender)**, because a sell must get through. Every trade carries a strict "worst price I accept" limit, which is also the main defence against sandwich bots (bots that trade just before and just after you to skim money off your trade).
- Paper mode must charge every fee, add realistic delay, use the price *when the trade would actually land*, and sometimes fail. Otherwise it will show profits that don't exist.

Host notes: WebFetch failed (host not allowed) for developers.jup.ag, www.helius.dev, solana.com, pumpportal.fun, pump.fun and intercom.help. raw.githubusercontent.com worked. No live tests were possible.

## 1. Key facts this design rests on
- Pump.fun coins graduate to **PumpSwap** by default since March 2025 [VERIFIED-SEARCH https://www.theblock.co/post/347360]. PumpSwap program `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` [VERIFIED-DOC https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md].
- PumpSwap trades have built-in price limits: `buy_exact_quote_in_v2(spendable_quote_in, min_base_amount_out)`, `sell_v2(base_amount_in, min_quote_amount_out)`. The v1 versions still work [VERIFIED-DOC https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md]. A blocked trade fails with error 6004 `ExceededSlippage`. Pump's admin can switch buys and sells off (6020 `DisabledBuy`, 6021 `DisabledSell`) [VERIFIED-DOC https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json].
- **Fees are dynamic and admin-changeable.** Official pools ("canonical" pools, the ones Pump.fun creates at graduation) use market-cap tiers read from an on-chain `feeConfig` account; the admin can change fee settings [VERIFIED-DOC https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md]. Tier values: 0–420 SOL market cap = **1.25%** (0.93% protocol, 0.30% creator, 0.02% LP); 420–1,470 SOL = 1.20%; above 98,000 SOL = 0.30% [VERIFIED-SEARCH https://pump.fun/docs/fees, https://docs.darkfibre.dev/platforms/pumpswap/]. **Never hard-code fees. Read `feeConfig` before every quote.**
- Solana network fee: 5,000 lamports (0.000005 SOL) per signature, charged even when a trade fails. Priority fee = compute units × price, paid entirely to the validator [VERIFIED-SEARCH https://solana.com/docs/core/fees/fee-structure].
- The **Alpenglow** upgrade went live on Oct 21 2026 (target finality ~150 ms) [VERIFIED-SEARCH https://solanacompass.com/news/solana-alpenglow-is-live-on-mainnet-as-anza-retires-towerbft-at-slot-459653000]. One search summary (quoting Galaxy) said slot time fell to 200 ms on Oct 9 [UNVERIFIED; confirm with `getRecentPerformanceSamples`]. **Every landing-time number in blogs predates this. Re-measure everything.**

## 2. Routing: who builds the trade
| Option | Speed | $/month | $/trade (API fee, round trip) | Reliability / failure modes | Build difficulty |
|---|---|---|---|---|---|
| **A. Direct PumpSwap via official `@pump-fun/pump-swap-sdk` 2.1.0** [VERIFIED-DOC README] | Fastest: we quote from the pool balances ourselves, with no extra web request | $0 (needs RPC, counted by data team) | **0%** | Breaks when Pump changes its programs (it does, often: fee accounts became mandatory Sep 1, v2 trades, negative reserves) [VERIFIED-DOC README]. Only covers PumpSwap pools | Medium (SDK does the maths; we must track SDK releases) |
| **B. Jupiter Swap V2 `/build`** (returns trade steps; we sign and send) | One extra web request (~50–200 ms) [UNVERIFIED] | Free: 1 request/s with key; Developer ~$25/mo for 10 requests/s [VERIFIED-SEARCH https://developers.jup.ag/docs/portal/rate-limits, https://comparedge.com/tools/jupiter-aggregator/pricing] | **0%** Jupiter fee on /build [VERIFIED-SEARCH https://developers.jup.ag/docs/swap/migration/metis-to-build] | Jupiter maintains the Pump code. Unknown delay before brand-new pools become routable [UNVERIFIED]. Exact-input trades only | Low–medium |
| C. Jupiter Swap V2 `/order`+`/execute` (Jupiter builds and lands the trade; Ultra API is deprecated in favour of this) [VERIFIED-SEARCH https://developers.jup.ag/docs/ultra] | Claims 50–400 ms landing [VERIFIED-SEARCH https://developers.jup.ag/blog/ultra-v3] | Same as B | **1.0%** (0.50% each way on tokens <24 h old; 0.10% older) [VERIFIED-SEARCH https://dev.jup.ag/docs/swap/v2/fees.md] | High, but a black box. Claims private landing and sandwich protection (vendor claim) [VERIFIED-SEARCH https://www.theblock.co/post/375184] | Lowest |
| D. PumpPortal Local / Lightning | Lightning fast to build | API key | **1.0% Local / 2.0% Lightning** [VERIFIED-SEARCH https://pumpportal.fun/fees] | Third party in the money path. Lightning signs for you, so PumpPortal holds the key [UNVERIFIED, confirm on docs] | Very low |
| E. Solana Tracker swap API | Similar to D | — | 1.0% (0.5% each way) [VERIFIED-SEARCH https://docs.solanatracker.io/swap-api] | Third party | Very low |

Raydium and Meteora pools only matter when a coin later gains liquidity there. Route B covers them automatically, so we write no custom Raydium or Meteora code.

## 3. Landing: who carries the trade to the network
| Sender | Speed / landing | $/month | $/trade (per transaction) | Reliability notes | Build |
|---|---|---|---|---|---|
| Public RPC `sendTransaction` | Worst under load; can be silently dropped | $0 | base + priority only | Not acceptable for live trading | Trivial |
| **Jito block engine (bundle-only)** | Lands only when a Jito validator is the block producer (most of stake, figures vary 88–95%) [VERIFIED-SEARCH https://rpcfast.com/blog/jito-explained-bundles-tips-mev-solana] | $0 (≈5 requests/s per IP, unofficial) [VERIFIED-SEARCH https://raw.githubusercontent.com/api-evangelist/jito/refs/heads/main/rate-limits/jito-rate-limits.yml] | Tip ≥1,000 lamports. Market median tip about 0.00001–0.0001 SOL, top 5% about 0.00015–0.005 SOL (2025–26 snapshots) [VERIFIED-SEARCH https://quicknode.com/docs/solana/getTipFloor, https://oanor.com/api/jito-api/openapi.json] | **All-or-nothing: a bundle that would fail is not included, so it costs nothing** [VERIFIED-SEARCH https://docs.jito.wtf/lowlatencytxnsend/; the "no fee" part is my inference, test it]. Supports `jitodontfront` anti-front-running marker [VERIFIED-SEARCH https://solana.com/docs/defi/mev-protection] | Medium |
| **Helius Sender** | Sends to Jito, staked connections (SWQoS, validators' fast lane for staked senders), Harmonic and Rakurai at once [VERIFIED-SEARCH https://www.helius.dev/docs/sending-transactions/sender] | $0 extra, no credits used, 50 tx/s [VERIFIED-SEARCH same] | Max mode: tip ≥ **0.001 SOL**. SWQoS-only mode: ≥0.000005 SOL. Priority fee required [VERIFIED-SEARCH same] | Best landing odds of the options found. Failed trades that land still pay base + priority fee | Low |
| Nozomi (Temporal) | Tip-ranked queue | ? | Tip ≥0.001 SOL, charged only if it lands [VERIFIED-SEARCH https://dashboard.nozomi.temporal.xyz/docs/nozomi/tipping-and-faq] | Good alternative / second path | Low |
| bloXroute Trader API | Fast relay network | ~$300/mo (old third-party listing; pricing changed Mar 2026) [VERIFIED-SEARCH https://www.trustradius.com/products/bloxroute-labs/pricing, https://docs.bloxroute.com/getting-started/pricing] | tip + fees | Too expensive for our size | Medium |
| 0slot | — | — | Could not verify [UNVERIFIED] | — | — |

**Realistic landing rate in a hot launch:** I found no 2026 measurement. 2024 data showed 58–75% of non-vote transactions failing, mostly bots. Over 80% of launch-time failures were "slippage exceeded" [VERIFIED-SEARCH https://cointelegraph.com/news/solana-struggling-record-seventy-five-percent-trasnactions-fail-memecoin-mania, https://www.gearbrain.com/amp/why-solana-transactions-fail-causes-fixes-2676651475]. Until we measure it, paper mode assumes **70% of first attempts succeed in hot moments and 90% in calm ones** [UNVERIFIED].

## 4. Slippage control and failed sells
- **Max price on every trade:** buys use "spend exactly X SOL, receive at least Y tokens" (`min_base_amount_out`), and sells use `min_quote_amount_out`. The allowed slippage is set by pool depth and recent price swings. Hard caps: **3% for buys** (beyond that, skip the trade; never chase), 5% for normal sells, up to 20% for emergency exits [UNVERIFIED starting values; Paul to confirm].
- **Stale quotes:** each quote records the slot (block) it was read at. If it is more than about 2 slots old when we sign, re-quote. Rebroadcast the *same* signed trade until it lands or its blockhash (the trade's built-in expiry stamp) expires. **Only after expiry do we build a new one.** This prevents double buys and double sells.
- **Partial fills:** one AMM swap fills completely or not at all. Partial exposure comes from "did it land?" uncertainty and chunked sells. So the **wallet's on-chain token balance is the source of truth** after every attempt, never the API's reply.
- **Sell retry ladder:** re-quote, then raise the fee one step and the slippage one step, up to 4 attempts in about 20 s. Then back off to one try every 60 s, and alert Paul. Never spend more than 2% of position value on retry fees. If the coin is too big for the pool, split the sell into chunks. Stop and mark the position "stuck" (never loop) on `DisabledSell` (6021), a frozen account or a token transfer fee/hook. Sells go via Helius Sender, plus Jito with `jitodontfront`.
- **Sandwich defence:** the slippage cap limits loss to at most the tolerance. Use `jitodontfront` on Jito sends, use no senders that sell order flow, and keep size under 1% of the pool's SOL reserve.

## 5. Cost per trade (one buy + one sell), recommended route (A/B + Jito/Helius)
Assumptions [UNVERIFIED]: SOL ≈ $100 (last seen $104 on Oct 14 2026 [VERIFIED-SEARCH https://30rates.com/solana]). Fresh pool holds ~80 SOL. The 1.25% fee tier applies. Per transaction: priority fee 0.0001 SOL normal / 0.001 hot; tip 0.0002 normal / 0.002 hot.

| Cost item (SOL) | 0.1 SOL | 0.5 SOL | 2 SOL |
|---|---|---|---|
| Network base fee (2 × 0.000005) | 0.00001 | 0.00001 | 0.00001 |
| Priority fee, 2 tx (normal / hot) | 0.0002 / 0.002 | 0.0002 / 0.002 | 0.0002 / 0.002 |
| Tip, 2 tx (normal / hot) | 0.0004 / 0.004 | 0.0004 / 0.004 | 0.0004 / 0.004 |
| PumpSwap fee (1.25% × 2) | 0.0025 | 0.0125 | 0.05 |
| API fee (route A/B) | 0 | 0 | 0 |
| Price impact, both sides (≈ 2 × size ÷ 80) | 0.00025 | 0.00625 | 0.10 |
| **Total, normal** | **0.0034 (3.4%) ≈ $0.34** | **0.0194 (3.9%) ≈ $1.94** | **0.151 (7.5%) ≈ $15.06** |
| **Total, hot** | **0.0088 (8.8%) ≈ $0.88** | **0.0248 (5.0%) ≈ $2.48** | **0.156 (7.8%) ≈ $15.60** |
| Extra if Jupiter /order or PumpPortal Local | +0.001 | +0.005 | +0.02 |
| Extra if PumpPortal Lightning | +0.002 | +0.01 | +0.04 |

Not included: price movement during the delay, sandwich loss (at most the tolerance), fees on failed attempts, and ~0.002 SOL token-account deposit (refunded when closed) [UNVERIFIED]. **Conclusion:** at 0.1 SOL, fixed fees bite in hot moments. At 2 SOL, a fresh pool is too shallow. **Position size must scale with pool depth.**

## 6. What paper mode must simulate
1. **Delay**: decision → quote → send → land, drawn from measured timings. Until measured, assume 0.4–2 s with a long tail in hot moments.
2. **Fill at the price when the trade lands**: replay the real on-chain pool balances at that slot and apply PumpSwap's maths, using the live fee tier.
3. **All costs**: base fee, priority fee, tip, DEX fee tier, the route's API fee, account deposit.
4. **Failures**: dropped (retry after delay); landed but reverted on slippage (charge base + priority; free if Jito bundle); slippage rejection = missed buy; sell retry ladder; "stuck" coins.
5. **Sandwich loss** up to the tolerance, with some probability.
6. **API limits** (429 "too many requests") and an outage of each provider.
7. Report **optimistic and pessimistic P&L side by side**. Calibrate later by comparing against real swaps of similar size by other wallets (read-only).

## 7. Recommendation
- **Route:** A (official Pump SDK, 0% API fee, fastest) as primary. B (Jupiter /build, 0% fee) provides an independent quote on every trade: if A and B disagree by more than 1%, **don't trade** (bad-data guard). B is also the fallback for non-PumpSwap liquidity or SDK breakage. Reject C, D and E (1–2% extra per round trip; D's Lightning option holds keys).
- **Landing:** buys go through Jito bundle-only with `jitodontfront` and a tip from the live tip floor (median to 75th percentile), capped at 0.5% of trade value. Sells go via Helius Sender (SWQoS-only when calm, Max when urgent), plus Jito. Nozomi is the spare path. Execution infrastructure cost: **≈ $0–25/month**. The real cost is per trade (table above).

## 8. Open risks
- Pump program and fee changes break direct code (mitigation: official SDK, fee read on-chain, A-vs-B cross-check, auto-pause on unknown errors).
- Pump admin can disable sells. A coin can then be impossible to exit; the position size limit is the only protection.
- Post-Alpenglow timing is unknown. Blog landing numbers are stale.
- Jupiter's delay before routing brand-new pools is unknown.
- The 3.5–8% round-trip cost may make many strategies unprofitable. The strategy and risk teams must use these numbers.

## 9. Tests to run once allowed (read-only; nothing signed or sent)
1. `api.jup.ag`: GET `/swap/v2/build` and `/swap/v2/order` quotes for 20 coins 0–120 s after migration. Does a route exist, how long does it take, and what `feeBps` comes back (expect 50)? Docs: `developers.jup.ag`, pricing: `portal.jup.ag`.
2. RPC (`api.mainnet-beta.solana.com` or `mainnet.helius-rpc.com`): read the PumpSwap `feeConfig` and GlobalConfig accounts (live fee tiers); read the vault balances of 20 freshly migrated pools (check the ~80 SOL depth); `getTransaction` on 200 PumpSwap swaps (compute units used, failure share, error 6004 frequency); `getRecentPrioritizationFees` for the PumpSwap program; `getRecentPerformanceSamples` (post-Alpenglow slot time); `getMinimumBalanceForRentExemption` (account deposit).
3. `bundles.jito.wtf/api/v1/bundles/tip_floor`: poll once a minute for 7 days. Docs: `docs.jito.wtf` (confirm the minimum tip, bundle-only "no fee on failure", and rate limits).
4. `www.helius.dev` / `docs.helius.dev`: confirm Sender tips and limits. `sender.helius-rpc.com/ping` for latency only.
5. `use.temporal.xyz`, `dashboard.nozomi.temporal.xyz`: tip percentiles and pricing.
6. `pumpportal.fun`: fees page and whether Lightning holds the private key. `pump.fun/docs/fees`: full tier table.
7. `docs.bloxroute.com`: current pricing. 0slot: domain unknown, needs a search.
8. `api.coingecko.com` or `api.jup.ag/price/v3`: SOL price for USD figures.
9. `dune.com`: 2026 failed-transaction and sandwich statistics on PumpSwap.
