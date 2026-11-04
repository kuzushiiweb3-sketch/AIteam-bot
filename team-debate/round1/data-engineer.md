# Round 1: Data engineer. How the bot sees the market

**In plain English (for Paul):**
- The bot should read the blockchain itself, through a fast paid "live stream" of every Pump.fun and PumpSwap transaction, and decode it with Pump.fun's own published decoding files. Third-party "new coin" feeds are too slow, too opaque, or may miss coins that graduate in new ways.
- A second, separate stream from a different company watches only the migrations (graduations) and our open coins. A third, free outside feed (PumpPortal) acts as a tripwire. If any one of them sees a graduation the others did not, an alarm goes off.
- Every few minutes the bot also checks its migration list against a full on-chain record. That gives a "coverage %" number, so blind spots get measured instead of guessed.
- Expected cost: about **$150 a month** while paper trading, or about **$270** if the cheaper stream provider turns out to cap our data. Prices still need checking. An optional **$499/month** upgrade buys replay-after-outage once real money is at stake.

**Jargon used once:** *RPC* = a paid server you ask for blockchain data. *Websocket / gRPC stream* = a connection where the server pushes new data to us as it happens (gRPC is a faster, more compact format). *Geyser / Yellowstone* = the standard plug-in that lets a Solana node stream raw data over gRPC. *Slot* = one block, roughly 0.2–0.4 s (re-measure after the Alpenglow upgrade). *Commitment* = how settled a block is: "processed" = just seen, "confirmed" = voted on. *IDL* = a program's published "decoding file". *Event* = a structured record a program writes inside a transaction. *CPI* = one program calling another inside the same transaction. *Decoder* = our code that turns raw bytes into events.

Tags: **[DOC]** = VERIFIED-DOC (I read the primary source this session), **[SEARCH]** = VERIFIED-SEARCH (seen only in search results), **[UNV]** = UNVERIFIED. Host notes: WebFetch worked only on `raw.githubusercontent.com`. `docs.shyft.to` failed to resolve, so I stopped trying other hosts. Teammates had already found `helius.dev`, `pumpportal.fun`, `solana.com` and `docs.birdeye.so` blocked, and I did not retry them.

---

## 1. How a migration shows up on chain today

| Step | What happens on chain | What we must decode |
|---|---|---|
| 1. Curve completes | The last buy empties the bonding curve. The curve is complete when `complete == true` and `real_token_reserves == 0` [DOC P1]. The completing buy can be `buy`, `buy_v2`, `buy_exact_sol_in`, `buy_exact_quote_in_v2/v3` or `buy_v3` on the Pump program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` [DOC P2]. **It can also be a hop inside PumpSwap's `multi_hop_swap`.** In that case PumpSwap calls Pump's `multi_hop_curve_swap` internally, and only PumpSwap may call it [DOC P5] | `TradeEvent`, then `CompleteEvent` (fields: user, mint, bonding_curve, timestamp, quote_mint) [DOC P2] |
| 1b. **Synthetic migration** (new) | A `buy_v3`, `buy_exact_quote_in_v3` or multi-hop curve hop that asks for more than the curve has left no longer fails. It buys the rest of the curve, then keeps buying "against the pool before the pool exists". Mayhem-mode coins are excluded [DOC P3, P4] | A third event, `PostCompleteBuyEvent` (base_out, quote_in, fees, pool reserves before and after). **The pool opens at a price this buyer already moved** [DOC P3] |
| 2. Migration | Someone calls `migrate` or `migrate_v2` ("Migrates liquidity to pump_amm if the bonding curve is complete"). Neither takes arguments [DOC P2]. It is **permissionless and idempotent: anyone can migrate a completed curve** [DOC P1]. Both versions list the PumpSwap program `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA`, the pool accounts, and the global `withdraw_authority` (`39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg`) as required accounts [DOC P1, P2]. Migration fee: 15,000,001 lamports [DOC P1] | `CompletePumpAmmMigrationEvent` (user, mint, mint_amount, sol_amount, pool_migration_fee, bonding_curve, timestamp, **pool**, quote_mint) [DOC P2]. PumpSwap's `CreatePoolEvent` (index, base_mint, **quote_mint**, pool, lp_mint, coin_creator, is_mayhem_mode…) [DOC P6]. That `migrate` emits `CreatePoolEvent` internally is my inference from the account list [UNV: test D2] |
| 3. Pool trading | PumpSwap `BuyEvent` / `SellEvent`. These carry pool reserves, every fee, `ix_name` and `virtual_quote_reserves`, which can be negative [DOC P6, P7] | Feeds the fill simulator and the exits |

**Five traps that create blind spots** (a feed or decoder that falls into any of them will miss migrations):
1. **Watching Pump's own migration wallet as the signer.** Migration is permissionless, so any wallet (or a sniper bot) can sign it [DOC P1]. Instead, match on the event, or on the `withdraw_authority` account that every migrate transaction must include.
2. **Reading only top-level instructions.** A multi-hop completion is an internal call under PumpSwap [DOC P5].
3. **Reading only the text logs.** Solana cuts each transaction's logs off at 10,000 bytes ("Log truncated") [SEARCH S1]. One parser library had to add a fallback that decodes `migrate_v2` events from the internal event calls when logs were cut [SEARCH S2]. The `event_authority` and `program` accounts in the IDL [DOC P2] are the standard sign that a program emits its events as internal calls [UNV inference: test D5]. **We decode those internal calls, never logs alone.**
4. **Matching instruction names instead of events.** New versions keep arriving: `buy_v3`, `sell_v3`, `migrate_v2`, `multi_hop_swap`, and the v2/legacy versions still work [DOC P4]. We decode by event type and treat any unknown instruction or event as an alarm. Unknowns are never skipped silently.
5. **Acting on "processed" data.** Since Alpenglow (live Oct 21 2026), one slot can briefly hold more than one candidate block. "Confirmed" and "finalized" now mean the same near-instant state [SEARCH S3]. **The bot may pre-arm checks on processed data, but it only buys on confirmed data.**

Also: the quote side is no longer always SOL. Since Oct 13 a coin can be paired with another Pump coin, and USDC is announced [DOC P8]. The feed must carry `quote_mint` everywhere.

**Migration of record** = a successful, confirmed transaction containing `CompletePumpAmmMigrationEvent` from the Pump program, whose `pool` matches the canonical (index 0) PumpSwap pool. The canonical check is in chain-forensics check #1. `CompleteEvent` alone means "about to migrate: pre-arm the checks".

## 2. Options compared

| Option | Latency | Catches EVERY migration (synthetic, multi-hop, new versions)? | $/month | Reliability / failure modes | Build difficulty |
|---|---|---|---|---|---|
| **A. Standard RPC websocket `logsSubscribe`** | Roughly 1 slot, plus a second call to fetch the full transaction [UNV] | **No.** `mentions` accepts only one address [SEARCH S4]. Logs can be cut off (trap 3) | $0–49 | Silent drops, no replay, 10-minute idle timeout on Helius [SEARCH S4] | Low, but fragile |
| **B. Helius Enhanced WSS `transactionSubscribe`** | Slot-level. Now runs on LaserStream, which Helius says is up to 200 ms faster [SEARCH S5] | Yes, if we decode the full transaction ourselves. It filters by included or required accounts | Developer plan **$49**, open to Developer since Apr 7 2026. Streaming metered at **20 credits/MB** [SEARCH S5, S6] | No replay after a disconnect. Metered, so a full firehose could eat the 10M monthly credits (test D4) | Medium |
| **C. Yellowstone gRPC, flat-rate third party** (Chainstack, Solana Tracker, Shyft, NodeFlare) | Slot-level, processed or confirmed [DOC Y1] | **Yes.** It gives full transactions including internal calls. Filters: `account_include`, `account_required`, `failed`, plus a slot stream and `ping`, and an optional `from_slot` [DOC Y1] | Chainstack Growth $49 + add-on **$49** (2 streams) [SEARCH S7]. Solana Tracker **€200** flat [SEARCH S8]. Shyft says it is unmetered, price not seen [SEARCH S8] | One provider, one region. Whether `from_slot` replay works depends on the provider [UNV, D10] | Medium (we write the decoders) |
| **D. Helius LaserStream gRPC** | Slot-level, low (vendor claim) | Yes (same as C) | **$499** (Business; mainnet needs Business or Professional) [SEARCH S6, S9] | **Best:** replays the last ~216,000 slots (~24 h) after an outage [SEARCH S9] | Medium |
| E. Shred streams (Jito ShredStream, Shyft RabbitStream) | Earliest: before the block is even executed | No. It carries no execution results or events, so a failed transaction looks the same as a successful one [UNV] | Varies | Bad-data risk for buy decisions | High. **Rejected for v1** |
| F. **PumpPortal** websocket | Seconds? [UNV] | Unknown. A third party parses the data, and nobody has shown it handles `buy_v3`/`migrate_v2`/multi-hop [UNV, D9]. `subscribeMigration` exists from memory only [UNV]. Documented: `subscribeNewToken`, `subscribeTokenTrade`, `subscribeAccountTrade` [SEARCH S10] | Curve data free. **PumpSwap data: 0.01 SOL per 10,000 messages**, with an API key and a 0.02 SOL minimum [SEARCH S11] | A third-party black box with no slot guarantees | Very low. **Good as a tripwire, not as the main feed** |
| G. Bitquery streams (GraphQL / Kafka / CoreCast gRPC) | Vendor claims under 300 ms on gRPC and under 400–500 ms on Kafka [SEARCH S12] | Says it detects Pump→PumpSwap migrations [SEARCH S12]. Not tested on new versions [UNV] | Not published (sales quote). Pro about $69 per quant-tester [SEARCH S12] | Vendor parsing lag after Pump updates [UNV] | Low |
| H. Birdeye websocket (`SUBSCRIBE_NEW_PAIR`) | Seconds [UNV] | A generic "new pair" feed, not migration-aware | Websocket needs the Business package (second-hand source), price not seen [SEARCH S13] | Aggregated, opaque | Low |
| I. DEX Screener API | Seconds to minutes. **Polling only, no stream** | No | Free. 60 requests/min on token profiles [SEARCH S14] | Not usable as a trading feed | Very low. Display only |
| J. Helius webhooks | Seconds [UNV] | Depends on the filter | 1 credit per event. Gives up after 3 failed tries [SEARCH, see social-intel G] | Gives up after failures | Low. **Rejected** for the trigger path |
| K. Our own node with Geyser | Lowest | Yes | Dedicated nodes from **$1,800–2,900/mo** [SEARCH S8, S15] | Our own operations burden | Very high. **Rejected** |

## 3. Recommendation: three independent eyes, plus an audit

1. **Primary: flat-rate Yellowstone gRPC (option C), with a full firehose.** It streams every successful transaction that touches the Pump *or* PumpSwap program (`account_include` both), at processed commitment, together with the slot-status stream, so we know the moment each slot becomes confirmed. Our decoders are generated from the official IDLs [DOC P2, P6], pinned by version and checksum. This one stream feeds everything: migrations, pre-arm signals, creator history (chain-forensics #13), the quant-tester's recorder and exits. Start with Chainstack (≈$98/mo). If test D4 shows bandwidth caps or filter limits, switch to Solana Tracker (€200 flat).
2. **Backup: Helius Developer plan ($49), a different company and a different method (option B).** Two *narrow* subscriptions: (a) transactions that **require** the `withdraw_authority` account. That should be exactly the migration transactions, and very little data [UNV: D1, D2]. (b) The pools we hold or watch, updated on the fly. The same plan is the second RPC for the risk-manager's exit price checks and chain-forensics' `funded-by` lookups.
3. **Tripwire: PumpPortal migration feed, about $0.** A different decoder written by someone else. If it reports a migration that our decoder did not, our decoder is probably broken.
4. **Audit every 5 minutes:** ask Helius `getTransactionsForAddress` for every transaction that includes `withdraw_authority`. It costs 10 credits per 100 transactions [SEARCH S16], so pennies a month. Any migration missing from our record becomes a **coverage-gap alarm**, and the coverage % feeds the quant-tester's "Coverage" metric. This audit also fills gaps after an outage.
5. **Every arrival is time-stamped per feed and de-duplicated by transaction signature.** So we always know which feed was fastest and which one missed.

**Upgrade path:** once real money is at scale, replace the primary with Helius LaserStream ($499) for its 24-hour replay [SEARCH S9]. Keep Chainstack as the backup. During paper trading, the audit (step 4) does the gap repair much more cheaply.

## 4. Detecting that a feed is silent, behind, or wrong

| Check | Rule (placeholder values; the risk-manager owns the final numbers) | Action |
|---|---|---|
| Heartbeat | gRPC `ping` every 10 s [DOC Y1]. Websocket ping every 30 s (Helius drops idle connections after 10 min [SEARCH S4]). No message of any kind for 3 s = **stale** | Reconnect with backoff. Request `from_slot` replay if the provider supports it. Run the audit at once |
| Slot lag | Every second, compare the feed's newest confirmed slot with `getSlot(confirmed)` from the *other* provider. More than 5 slots behind = **behind**. More than 25 slots, or stale for 5 s = **down** (matches risk-manager `feed_stale_sec` 5) | Behind: no new buys. Down: switch decisions to the backup. Exits keep running on the freshest source |
| Event-rate floor | Pump and PumpSwap are never quiet for long [UNV]. Fewer events per 10 s than 10% of the trailing 1-hour median = **silent while connected** | Treat as down |
| Cross-feed agreement | Every migration should reach both primary and backup within 2 s | A primary miss raises a coverage alarm. A backup-only miss suggests the `withdraw_authority` changed: run D1 |
| Expected follow-up | Every `CompleteEvent` should be followed by a migration within N slots. If not, derive the canonical pool address and read it by RPC | If the pool exists, we missed the event: raise a coverage alarm |
| Decoder health | Unknown event or instruction type, a decode error, or a field out of range (for example negative reserves where they are not allowed) | Store the raw bytes. Alarm. Pause new buys until a human clears it |
| **Program-change watch** | Subscribe to the Pump and PumpSwap program-data accounts. An upgrade rewrites them [UNV: D7]. Re-hash the IDLs on `raw.githubusercontent.com/pump-fun/pump-public-docs` every hour (that host works today) | Mark decoders "unverified" and pause new buys. Resume once the new IDL is in and the three feeds agree on the next 5 migrations |

**Store raw transaction bytes** (compressed) next to every decoded event. When Pump changes a program and our decoder breaks, we re-decode afterwards and lose no data. Estimated at tens of GB a month [UNV, D4].

## 5. Historical data for backtesting

The quant-tester owns this. My additions:

| Source | What | Cost | Note |
|---|---|---|---|
| Our recorder (primary firehose) | Every event plus raw bytes from day 1 | $0 extra | The trusted source |
| Helius `getTransactionsForAddress` | Full migration list for any period, via the `withdraw_authority` address. Full transactions of chosen pools | 10 credits per 100 transactions, up to 1,000 per call [SEARCH S16]. 90 days ≈ 27k migrations ≈ under 3k credits [UNV estimate] | Rebuilds the complete coin list with **dead coins included**. That cures survivorship bias. Re-decoded with our own decoders |
| Dune (one month) | Decoded event tables | ~$75 one-off (quant-tester) | Cross-check only |
| Bitquery archive | Pump and PumpSwap trades | Pro ~$69 (quant-tester) | Optional |
| LaserStream replay | Last 24 h only | Comes with the $499 plan | Repairs outages; it is not a history source |
| Old Faithful | Every block since the first one | Free download, heavy compute | Last resort |

## 6. Open risks
- **Decoder breakage** is certain to happen eventually. Pump changed instructions, events and fee flows several times in 2026 [DOC P8]. The mitigations are in section 4 (program watch, raw bytes, three-way agreement, pause on unknowns).
- **The `withdraw_authority` filter depends on one global setting.** If Pump's admin changes it, backup filter (a) and the audit go blind. The primary firehose and test D1 cover this.
- **Metered streaming (Helius, Alchemy) can surprise on cost** during meme manias. Use a flat-rate primary and keep Helius narrow.
- **Synthetic-migration pools open at a price already moved** by the completing buyer. Strategy and quant teams must read `PostCompleteBuyEvent`, not only the pool's first trade.
- **Sniper-triggered migrations:** since anyone can migrate, a bot may complete the curve, migrate and buy the pool in one transaction [UNV inference from P1/P3]. Our "first chance to buy" may come after that bot. Measure it in D2.
- **Post-Alpenglow timing** (slot length, processed-to-confirmed delay, dropped candidate blocks) is unmeasured. Every latency number above is a guess until D6 runs.
- **Volume is an estimate.** Daily Pump and PumpSwap transaction counts are not verified (search found only about 1M/day from 2025 press) [UNV]. Both bandwidth and the Helius cost depend on it.

## 7. Tests to run once allowed (read-only, nothing signed)

| # | Test | Domain(s) needed |
|---|---|---|
| D1 | Read the Pump Global account `4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf` [DOC P1]. Confirm `withdraw_authority` is still `39azUY…` and `enable_migrate` is true | `mainnet.helius-rpc.com` or `api.mainnet-beta.solana.com` |
| D2 | Fetch 7 days of transactions that include `39azUY…`. Check that each one has `CompletePumpAmmMigrationEvent` and `CreatePoolEvent`. Count the signers that are not Pump's own. Count same-transaction complete+migrate+buy. Measure the slots from `CompleteEvent` to migration. Count synthetic migrations | `mainnet.helius-rpc.com`, `www.helius.dev` |
| D3 | Run all feeds side by side for 72 h: per-migration arrival time, coverage %, disagreements | Chainstack endpoint (`*.core.chainstack.com`, exact host from the dashboard [UNV]), `mainnet.helius-rpc.com` (wss), `pumpportal.fun` (wss `/api/data`) |
| D4 | Measure 1 h of full Pump + PumpSwap firehose: MB/hour, then monthly Helius credits against flat-rate. Also raw-byte storage per day | gRPC provider host, `mainnet.helius-rpc.com` |
| D5 | Of 10,000 Pump transactions, what share hit "Log truncated"? Confirm events always appear as internal event calls | RPC host |
| D6 | Post-Alpenglow: slot length, processed-to-confirmed delay, number of dropped candidate blocks per day (`SLOT_DEAD` [DOC Y1]) | gRPC provider host |
| D7 | Read the Pump and PumpSwap program accounts, then their program-data address, last deploy slot and upgrade authority | RPC host |
| D8 | Disconnect the primary for 60 s, reconnect with `from_slot`. Is the gap filled? | gRPC provider host, Helius LaserStream trial host (from `www.helius.dev` docs) |
| D9 | PumpPortal: does `subscribeMigration` exist? Message fields, latency, synthetic-migration coverage, connection limits | `pumpportal.fun` |
| D10 | Confirm prices and limits on the live pricing pages | `www.helius.dev/pricing`, `chainstack.com/pricing`, `docs.solanatracker.io`, `shyft.to`, `pumpportal.fun/data-api/pump-swap`, `docs.birdeye.so`, `bitquery.io/pricing`, `docs.shyft.to` |

## Sources
- P1 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_PROGRAM_README.md
- P2 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json (instructions `migrate`, `migrate_v2`, `multi_hop_curve_swap`, `buy_v3`; events list)
- P3 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- P4 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/TRADE_V3.md
- P5 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/MULTI_HOP_SWAP.md
- P6 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (`create_pool`, `CreatePoolEvent`, `BuyEvent`)
- P7 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md (via quant-tester)
- P8 [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md
- Y1 [DOC] https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/yellowstone-grpc-proto/proto/geyser.proto
- S1 [SEARCH] https://docs.rs/solana-program-runtime/2.0.6/src/solana_program_runtime/log_collector.rs.html
- S2 [SEARCH] https://github.com/0xfnzero/sol-parser-sdk/releases/tag/v0.7.12
- S3 [SEARCH] https://solana.com/upgrades/alpenglow · https://docs.chainstack.com/docs/solana-alpenglow-consensus
- S4 [SEARCH] https://solana.com/docs/rpc/websocket/logssubscribe · https://www.helius.dev/docs/api-reference/rpc/websocket/logssubscribe
- S5 [SEARCH] https://www.helius.dev/blog/laserstream-websockets
- S6 [SEARCH] https://www.helius.dev/pricing · https://www.helius.dev/docs/billing/plans · https://chainstack.com/helius-rpc-provider-a-practical-overview/
- S7 [SEARCH] https://chainstack.com/yellowstone-grpc-more-streams-same-price/ · https://chainstack.com/marketplace/yellowstone-grpc-geyser-plugin/ · https://chainstack.com/pricing/
- S8 [SEARCH] https://www.solanatracker.io/yellowstone-grpc · https://www.shyft.to/solana-yellowstone-grpc · https://shyft.to/solana-dedicated-grpc-nodes · https://nodeflare.app/yellowstone
- S9 [SEARCH] https://www.helius.dev/docs/laserstream/historical-replay · https://www.helius.dev/docs/laserstream.md
- S10 [SEARCH] https://github.com/TrustPump/Pump-Fun-API (unofficial mirror of PumpPortal's readme)
- S11 [SEARCH] https://pumpportal.fun/data-api/pump-swap
- S12 [SEARCH] https://www.bitquery.io/products/pumpswap-api · https://www.bitquery.io/products/corecast · https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/
- S13 [SEARCH] https://docs.birdeye.so/docs/subscribe_new_pair · https://gist.github.com/Klaudioz/67bbc2430528615eef34447486ec36b0
- S14 [SEARCH] https://docs.dexscreener.com/api/reference
- S15 [SEARCH] https://rpcfast.com/blog/best-solana-grpc-providers · https://www.alchemy.com/overviews/solana-rpc (Triton ~$0.08/GB, Alchemy ~$75/TB, QuickNode included on Scale $499 since Jun 2026)
- S16 [SEARCH] https://www.helius.dev/docs/billing/credits.md · https://www.helius.dev/docs/rpc/migrate-to-gettransactionsforaddress
