# Round 2b: Data engineer response to the red team

## 0. In plain English (for Paul)
- **We will not race at the moment a coin graduates.** The fastest bots are inside the graduation transaction itself. Getting close would cost $500–3,000+ a month and still lose. Our data budget (about **$147 a month**, plus about $15 for a separate disk) pays for seeing *every* coin and *every* trade *correctly*. That is what our edge ideas need.
- The red team's worst data attack is right: Pump.fun can quietly change its data, and an old decoder would misprice coins without any error. The fix: every trade is now checked two ways, Pump's own receipt against the blockchain's own balance record, down to the last unit. Any mismatch stops new buys at once.
- Our edge ideas rely on being *exact*, not first. Let the snipers race, measure exactly how many tokens they still hold (including tokens moved to fresh wallets), and buy only when that pile is gone. Also, catch insiders moving tokens *before* the price falls. Each idea has a pass/fail test fixed in advance.
- Two small things for Paul later: turn on Helius "autoscaling" with a $25 cap, so the safety system never runs out of data credits. And never create a PumpPortal account key (it comes with a wallet key).

**Tags:** [DOC] = VERIFIED-DOC (I read the primary source this session; URL in Sources). [SEARCH] = VERIFIED-SEARCH. [UNV] = UNVERIFIED (the test that settles it is named). [DERIVED] = my arithmetic on tagged inputs. Round 1 references look like "R1 §3". Host notes: WebFetch worked on `raw.githubusercontent.com`. The shell network is blocked, so no live tests ran. I used 10 web searches.

---

## 1. Answers to attacks

### DAT-1 Silent decoder corruption: FIXED
1. **Exact-length decoding.** In the current PumpSwap IDL, `BuyEvent` has exactly one variable-length field (`ix_name`, a string), and `SellEvent` has none [DOC pump_amm.json]. So every decoder must use up *every* byte: the fixed size plus the string length. If a byte is left over or missing, that is a `DECODER_SHAPE` alarm: store the raw bytes and pause new buys. Accounts (Pool, GlobalConfig, BondingCurve) get the same rule.
2. **Two witnesses on every trade.** For each `BuyEvent`/`SellEvent` and curve `TradeEvent`, we compare three things. (a) The event's amounts. (b) The pool vaults' before and after token balances in the transaction record, which the validator writes, not Pump's code. (c) Our own fee and price maths. They must agree to the lamport (±1 for rounding), not within 0.5%. A shifted field fails (a)=(b) at once. A fee or formula change fails (c). This is the T6 check running live on every trade. It also settles on day 1 whether the event's reserves are before or after the trade, which the docs don't say [DOC PUMP_SWAP_README].
3. **Watch admin settings, not just upgrades.** Add the fee program `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` to the firehose [DOC pump_amm.json]. Stream account changes for Pump Global `4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf` [DOC R1 P1], PumpSwap GlobalConfig `ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw` [DOC PUMP_SWAP_README] and the `fee_config` addresses (seed `"fee_config"`) [DOC]. Several admin instructions change behaviour with no upgrade. PumpSwap: `update_fee_config`, `disable`, `update_admin`, `toggle_boost`, `toggle_mayhem_mode`, `toggle_cashback_enabled`, `update_buyback_config`, `update_creator_fee_config`, `set_reserved_fee_recipients`, `set_boost_authority`, `admin_update_token_incentives` [DOC pump_amm.json]. Pump: `set_params` and `update_global_authority` [DOC]. If any of these appears, or any watched account is written, raise `ADMIN_CHANGE`: log the before and after values and pause new buys until someone reviews it. Exits keep running.
4. **Dormant-field monitor.** For each decoded field, keep the range of values seen in the last 7 days. `virtual_quote_reserves` "is 0 on all pools today" [DOC PUMP_SWAP_README]. If a field like that turns non-zero, raise `FIELD_ACTIVATED`, and pause buys if the field affects price.
5. **New resume rule** (replaces "5 migrations agree"). All of these must hold: a human has reviewed the change, decoders are regenerated from the new IDL and their hashes pinned, all feeds agree on the next 5 migrations, the next **1,000 trades in a row** pass the two-witness check, and there have been no shape alarms for 30 minutes.

### DAT-2 One provider, one region: degraded mode FIXED; a hot standby is an ACCEPTED RISK until stakes are bigger
| Primary state | New buys | Exits | Pre-arm / forensics | Recorder |
|---|---|---|---|---|
| Behind (more than 5 slots) | Blocked | Helius becomes the lead source | Marked stale, no vetoes lifted | Gap logged |
| Down (stale for 5 s) | Blocked, armed candidates cancelled | Helius live updates, plus a 1 s poll on whichever provider is healthy, plus the public RPC as a third path | Off: fails closed | Gap logged (start and end slot). Backfill job runs |
| Both down | Blocked | Poll only. Risk-manager's L1 | Off | Gap logged |

Gaps are repaired with Helius `getTransactionsForAddress` over the gap's slots for Pump, PumpSwap and `withdraw_authority` [SEARCH R1 S16]. A repaired window is flagged "repaired". An unrepaired window is **excluded** from backtests, and every report states the share of its time window affected [DERIVED rule].
**Why a standby is an accepted risk:** in degraded mode we never buy, and exits keep two sources at two other companies. So a primary outage costs missed trades and recorder gaps, not losses. A second flat-rate firehose from another company costs about $200 a month (Shyft Build $199, Solana Tracker €200 flat [SEARCH]). Add it once the trades we would miss during outages are worth more than that. Chainstack's $49 add-on now allows 2 streams [SEARCH chainstack June 2026].

### DAT-3 / SEAM-6 The firehose can't see plain token transfers: FIXED in the design (bandwidth to be measured)
The current Yellowstone filter can match **wallets through their token balances**. When `token_accounts = BALANCE_CHANGED` is set, `account_include` "also match[es] against owners of pre/post token balances" [DOC geyser.proto]. `cuckoo_account_include` lets one filter carry a large set of wallets [DOC]. Whether Chainstack's server supports these new fields is [UNV: D13].
- **Watched wallets** (the dev, the `creator`, early-buyer clusters, the fast group of wallets from E1): a filter that includes those wallets with token-balance matching on. It catches every token move they make, plain transfers included, on any venue. Every new wallet that receives their tokens shows up in the same transaction's balances, so it **joins the watch list automatically**.
- **Every holder of a held coin** (5 or fewer coins): Helius standard `programSubscribe` on the token program, filtered on "first 32 bytes = mint". It sees every balance change of every holder. Helius allows 1,000 subscriptions per connection, metered at 20 credits/MB [SEARCH]. This is also exit source B.
- **Candidates, at full coverage:** add the Token-2022 program to the firehose and keep only the coins we track. That gives a complete holder ledger for every coin at zero credits, if the bandwidth fits (D11). It assumes `create_v2` coins are Token-2022, which Pump's docs don't state [UNV: D16]. Older plain-token coins get the wallet watch only.
- **Not covered:** SOL funding of sybil wallets. Every plain SOL transfer on the chain is far too much data. It stays an RPC lookup (`funded-by`), costed under SEAM-7.

### DAT-4 Confirmed-only buys vs exits on unconfirmed data: FIXED
- Entries: we don't race (section 2), so waiting for confirmed data costs nothing that matters. Alpenglow targets 100–150 ms finality [SEARCH anza/alchemy, targets, not live measurements]. So the wait is probably under one slot, not the 1–2 blocks PREMISE-1 assumed (test D6).
- Exits: an unconfirmed ("processed") breach *arms* the sell. It is **sent** when any of these is true: (a) the triggering block confirms, (b) source B shows the same breach, or (c) a catastrophic breach (the risk-manager sets the number). **The worst price we accept is always computed from the latest *confirmed* pool state, never from an unconfirmed one.** A phantom block therefore can't widen our slippage and hand a sandwich bot room (EXE-3). The worst a phantom can do is an early exit at the real price.
- Helius's standard websocket updates "deliver updates in a random order" [SEARCH helius blog]. Every update is ordered by its slot, and older ones are dropped.

### DAT-5 / SEAM-7 Credits double-booked: FIXED
Helius Developer: 10M credits/month. Extra credits cost $5 per 1M. Autoscaling is capped at 50M a month and its default limit is 0, meaning off [SEARCH helius billing].

| Consumer (Helius) | How | Credits/month [DERIVED; sizes UNV] |
|---|---|---|
| Backup: migrations | Enhanced WSS, transactions that *require* `withdraw_authority` | ~5k (300/day × ~20 KB) |
| Slot heads for the lag check | `slotSubscribe`. **Replaces the 1 s `getSlot` poll (~2.6M)** | ~15k |
| Exit source B | Pool-vault `accountSubscribe` + mint `programSubscribe`, held coins only | 30k–300k |
| Exit fallback poll | `getMultipleAccounts` 1/s, **only while a live source is silent** | ~0 normally; **2.6M reserved** |
| Silent-feed probe (DAT-9) | `getSignaturesForAddress` limit 1, Pump + PumpSwap, every 60 s | 0.09–0.9M (cost per call UNV, P12) |
| Migration audit | `getTransactionsForAddress(withdraw_authority)` every 5 min | ~90k |
| Canonical-pool follow-up (DAT-6) | `getAccountInfo` per `CompleteEvent` | ~10k |
| Migration-window blocks (PREMISE-3) | `getBlock` × 11 per migration | 0.1–1M (optional) |
| Forensics + `funded-by` | per chain-forensics, smaller once holders come from the stream | 0.6–2.5M |
| Backfill reserve | after outages | 1M |
| **Total** | | **≈1–5M normal; ≤ ~8.5M worst case** |

Rules: a local meter counts credits per consumer, using the published price per method. At 6M used, the optional consumers stop (block capture, `funded-by`, backfill). **The 2.6M exit reserve can't be touched.** Paul turns on autoscaling with a 5M (**$25**) cap, so the plan can never cut off the exit guard. KOL wallets move to the gRPC stream (SOC-6), which saves ~150k.

### DAT-6 The backup and the audit share one key: FIXED (four keys now)
1. `withdraw_authority`: the backup stream and the 5-minute audit.
2. **From the events:** for every `CompleteEvent` (from any feed), work out the canonical pool address (seeds `["pool", index 0, creator, base_mint, quote_mint]` [DOC PUMP_SWAP_README]) and read it 10 slots later. Which Pump-owned address acts as the "creator" for migrated pools is learned from the first migrations and then pinned [UNV: D2]. A `CreatePoolEvent` with index 0 and no matching migration event raises an alarm: Pump may have added a new migration path.
3. **Global settings watch:** `set_params` can change `withdraw_authority` and `enable_migrate` [DOC PUMP_PROGRAM_README]. A change raises an alarm, and the filters are re-pointed after review.
4. PumpPortal's keyless tripwire, a decoder written by someone else (DAT-7).

### DAT-7 PumpPortal key: FIXED (only the keyless parts are allowed)
PumpPortal's Data API is free (rate-limited) [SEARCH]. PumpSwap data needs a key and costs 0.01 SOL per 10,000 messages [SEARCH R1 S11]. A community tool's PumpPortal `create_wallet` returns an apiKey together with a **privateKey** [SEARCH lobehub]. So keys come bundled with a wallet that PumpPortal generates [UNV, but likely]. **Rule: we never create a PumpPortal key.** The tripwire uses only keyless channels (`subscribeNewToken`, plus `subscribeMigration` if D9 shows it exists without a key). If no keyless migration channel exists, PumpPortal is dropped. Keys 1–3 stay.

### DAT-8 / SEAM-8 A full disk: FIXED
The recorder writes to **its own disk volume** (about 200 GB, ~$10–20/month [UNV]). The exit guard's journal stays on the system disk, with space reserved for it. Raw data is stored compressed and in binary form, without logs (events come from the internal event calls). The estimate is 15–135 GB a month [UNV: D4]. Recent days stay on the disk; older days move to cheap object storage and are checked before the local copy is deleted. Alarms: at 70% full, drop raw bytes for coins we don't track. At 85%, keep decoded events only. At 95%, the recorder stops and logs the gap. **The recorder can never block the exit guard.** Drill: fill the recorder's disk in paper mode with positions open, and confirm exits are unaffected.

### DAT-9 False "down" alarms in quiet hours: FIXED
The event-rate floor is set separately for each hour of the week from 7 days of tape, and it only logs (no action) during those first 7 days. "Silent while connected" now needs **two** signals: a low event rate **and** the probe showing that the other provider has seen newer Pump transactions (more than 10 slots newer) than we have. A truly quiet hour shows nothing newer anywhere, so it can't trip the alarm.

### PREMISE and SEAM attacks that touch data or speed
- **PREMISE-1 / SEAM-2 (the speed race):** see section 2. My position: no race. One correction: waiting for confirmed data likely costs about 150 ms after Alpenglow, not 1–2 blocks [SEARCH target; D6]. The conclusion doesn't change.
- **PREMISE-2 (no edge):** see section 4.
- **PREMISE-3 / QNT-2 (adverse selection, order within a block): FIXED on the data side.** The recorder now also keeps **failed** transactions (Yellowstone `failed` filter [DOC geyser.proto]), because failed buys show us the losers of an auction. For every transaction it stores the slot, `index` (its position in the block is UNV, D12), signer, priority fee, compute used and any Jito tip inside it. For each migration it also fetches the full block plus the next 10 blocks (`getBlock`), which catches tips paid in separate bundle transactions. That feeds P1 and P4.
- **PREMISE-5 (regime changes): FIXED on the data side.** Every event is tagged with the program's last deploy slot, the IDL hash and the decoder version. The DAT-1 admin diff helps label a change as "decoding only" or "market structure".
- **PREMISE-7 (bills): ACCEPTED.** Data costs a fixed $147 + ~$15 a month and doesn't grow with bet size. Cutting the second set of eyes saves $49 and breaks priority 1, so the fix is bet size (SEAM-1).
- **SEAM-5 (zero gap):** the recorder measures the gap from `CompleteEvent` to migration, including the share inside the same transaction. The design assumes the gap is 0: all pre-arm data comes from the firehose before the curve completes.
- **SEAM-10 (scores too late):** the recorder logs the curve progress per coin per slot and flags coins that jump more than 20% in one transaction (synthetic completions). The ai-strategist and social-intel use that share.
- **QNT-7 (missed trades): FIXED, at zero credits.** **Reserve continuity:** for each pool, the vault balances after trade N must equal those before trade N+1. A jump means we missed a transaction touching that vault, or someone sent tokens straight to it. Either way it raises an alarm. The quant-tester's daily check of 20 random pools stays as an outside cross-check.
- **RSK-8 (name the exit sources): FIXED.** Source A: Chainstack gRPC (PumpSwap trade events plus pool-vault account updates). Source B: Helius WSS (vault `accountSubscribe` and mint `programSubscribe`). Fallback poll: `getMultipleAccounts` on the healthy provider, with the public RPC as a third path. In fallback mode one read is enough to trigger.

---

## 2. The big fork: my position is **don't race at graduation**
| Setup | Lands, in blocks after the leader | Extra $/month | Source |
|---|---|---|---|
| Leader: the buy that completes the curve also buys pool-priced tokens in the same transaction | 0 | n/a | [DOC SYNTHETIC_MIGRATION] |
| Professional sniper: shreds (raw block pieces), a server next to the validators, a local key, top tips | 0–1 | $1,000–3,000+ | [SEARCH R1 S8/S15; UNV] |
| Us, cheapest possible race: flat gRPC on unconfirmed data, a local key | +1–3 (0.2–1.2 s) | $0 over the $98 feed | [UNV: D3, D6] |
| Us as designed: confirmed data, hosted signer (50–250 ms [SEARCH]), Jito only | +2–5 | $0 | [DERIVED] |
| + Helius LaserStream (mainnet needs Business, $499) | saves tens of ms (vendor claim), still +1–3 | +$499 | [SEARCH] |
| + paid shreds (Jito's free ShredStream **shut down Sep 5 2026**; paid replacements) | +1–2, on not-yet-executed data | unknown, likely hundreds or more | [SEARCH chainstack, orbitflare] |
| + our own node | +1–2 | +$1,800–2,900 | [SEARCH R1] |

Block length is 0.2–0.4 s. Alchemy describes Alpenglow as using 400 ms blocks [SEARCH], while a teammate saw 200 ms [UNV]. D6 settles it.
**Numbers:** every dollar beyond the $98 feed buys at most about one block, and never block 0. To come close we'd pay $500–3,000 a month against a turnover of about $3,000 a month (red team). That is 17–100% of turnover [DERIVED]. And blocks +1 to +3 are described as "the first wave of retail and slower bots" [SEARCH rpcfast vendor guide]. That is the worst of both worlds: sniper prices, retail fills and adverse selection.
**What the $98 does buy:** complete, slot-level data. We need that anyway for coverage (priority 2), for the recorder, and for exits. A sell that sees a dump in the next slot instead of on a 1 s poll saves 2–5 slots (0.4–2 s) in a crash. Entries move to events that unfold over seconds to minutes (BOOST ending, snipers selling out). There, our ~0.5 s delay is under 1% of a 60 s decision window [DERIVED].
**Reopen rule (fixed now, before any test):** run P1 and P4 on 300 or more post-BOOST graduations. A buy landing at block +3 pays the 75th-percentile winning tip in those blocks, fills last in its block, and counts as missed when more than N competing buys came first (PREMISE-3). If that buy beats the best delayed rule by at least 5 percentage points net per trade, with a confidence interval above 0, the race comes back on the table. Otherwise speed spend for entries stays at **$0**.

---

## 3. Challenges to other areas (3)
1. **To risk-manager:** drop the 300 s clock (RSK-1). The chain reports BOOST directly: `BoostBuyAndBurnEvent` carries `boost_vault_remaining`, and `GlobalConfig` has `boost_enabled` [DOC pump_amm.json]. Make entries depend on events we compute live (BOOST money left, the snipers' remaining tokens from E1, net SOL flow), not on a guess about time. Also, `feed_stale_sec = 5` means 12–25 slots, far too slow for exits. I propose 1.5 s to switch to the fallback poll and 5 s to trigger L1 (you own the numbers).
2. **To chain-forensics:** take holder concentration from the stream's holder ledger (DAT-3), and use `getTokenLargestAccounts` (only the top 20) as a cross-check. Learn the accounts to exclude from the events, rather than from a hand-made list: `BuyEvent` names `protocol_fee_recipient` and `coin_creator`, and `BoostBuyAndBurnEvent` names `authority` and `pool` [DOC]. Design the gate for a gap of 0 (SEAM-5).
3. **To quant-tester and execution-engineer:** (a) Tell me *now* every field the fill simulator needs. Anything not recorded from day 1 can only be backfilled through costly `getBlock` calls. (b) Replace the Jupiter cross-check (EXE-4) with the two-witness check plus the SDK quote compared against our own maths on the same slot. That keeps the independent check local, and it never blocks sells. (c) Split results by regime tag (deploy slot + IDL hash), not by calendar date.

---

## 4. Edge hunt
**E1. Let the racers go first: an exact clock of what the fast wallets still hold.**
*What we know that others don't:* slot by slot, the exact number of tokens still held by the fast group at graduation. That group is (i) the completing buyer, whose pool-priced tokens and cost come from `PostCompleteBuyEvent` [DOC SYNTHETIC_MIGRATION], (ii) the wallets that buy in pool blocks 0–3, and (iii) **any wallet they pass tokens to** (DAT-3). It also includes BOOST money remaining [DOC]. Retail screens show sniper share from top-holder snapshots [UNV: P15], and a sniper who moves tokens to a fresh wallet vanishes from them. *Why we'd win:* snipers compete on speed and ignore this. Retail can't see transfers live. We buy after the racers have sold, at a lower price. *Cost:* $0 in new data, if D11 fits. *Copying:* any team with a recorder could copy it within weeks. The protection is thin: our labelling quality plus our history. *Kill test:* fit on 300 post-BOOST graduations, test on the next 300. The rule is "enter at the first slot where the fast group holds 25% or less of its peak", fixed before the test. Compare it with the plain buy-every-graduate baseline (null) at 60/300/600 s, using the same exits, all costs and last-in-block fills. **PASS** if the test set's mean net is at least the best null + 3 percentage points per trade, the bootstrap 95% confidence interval is above 0, it stays positive without the top 5% of trades, and at least 30% of graduations trigger it. Otherwise **KILL**.

**E2. Blind-spot pockets: coins the crowd's tools misread.**
*What:* synthetic migrations, curves completed through multi-hop swaps, coins quoted in something other than SOL, and the first 72 h after each Pump change (more than 4 changes in 15 weeks [DOC README]). Outside decoders lag behind. One parser library needed a fix for `migrate_v2` when logs were cut off [SEARCH R1 S2], and Dune's model lacks the v2 instructions (quant-tester R1, [DOC]). If trackers miss or misprice a coin, fewer bots compete for it. *Why we'd win:* our decoders are generated from the IDL and proven by the two-witness check within minutes of a change. *Cost:* $0. For comparison we poll DEX Screener's free API (60 requests/min [SEARCH R1 S14]). *Copying:* any team that decodes directly. The window reopens with every Pump change. *Kill test:* for each group of coins, measure the distinct buyers and the known-bot share in the first 120 s, DEX Screener's listing delay and its price error against our numbers, and the null strategy's net. **PASS** if some group of 50 or more graduations has a bot share at least 30% lower **and** a null net at least 3 percentage points better than standard graduations, repeated in a second period. Otherwise **KILL**. Paper only. CHN-6 rejects non-SOL quotes for live trading in v1.

**E3. Exit on the warning signs, before the price moves.**
*What:* plain transfers from dev or insider groups to fresh wallets, and selling that speeds up among the fast group. Our ledger sees both before the dump hits the price, while price-based trailing stops react afterwards. *Why we'd win:* we see the transfer itself. Charts don't show it. *Cost:* the Helius held-coin stream, 30k–300k credits/month, already in the budget. *Copying:* moderately hard. It needs complete transfer tracking plus grouping of related wallets. *Kill test:* on 200 or more dumps from the tape (a fall of 30% or more within 60 s), the warning rule must fire at least 2 s before the first −10% on at least 40% of dumps. It may raise at most 1 false alarm for every 2 true ones. Compared with a price-only trailing stop delayed by 2 s, the simulated exits must save at least 3 percentage points per dumped position, after paying for the false exits. Otherwise **KILL**.

---

## 5. Revised recommendation
1. **Primary:** Chainstack Growth + the Yellowstone add-on (**$98**, 2 streams [SEARCH]). Stream 1 carries Pump + PumpSwap + the fee program, including failed transactions (+ Token-2022 if D11 fits). Stream 2 carries the admin and settings accounts plus the wallet and mint watch lists. Decoders are strict: exact byte counts, the two-witness check, reserve continuity, and the dormant-field monitor.
2. **Backup:** Helius Developer (**$49**), kept narrow: migrations, slot heads and exit source B. A local credit meter holds back an exit reserve that can't be spent elsewhere, and Paul sets the autoscaling cap ($25).
3. **Coverage audits** use four independent keys plus a silent-feed probe. PumpPortal is used without any key, or not at all.
4. **No speed spend for entries.** LaserStream, shreds, a co-located server and our own node are all rejected. They come back only if the pre-set reopen rule passes. Data total: **≈ $147/month + ~$15 disk**.
5. The **recorder** runs on its own disk. It stores competition data, full blocks around each migration, and regime tags, and it feeds E1–E3 from day 1.

## Tests to run once allowed (new; D1–D10 from R1 still stand)
| # | Test | Domain(s) |
|---|---|---|
| D11 | MB/hour of a Token-2022-program transaction stream, and the share that touches Pump coins | Chainstack gRPC host (from the dashboard) |
| D12 | On 1,000 trades: event reserves before or after the trade, compared with vault balance changes; whether `index` is the position in the block | `mainnet.helius-rpc.com`, gRPC host |
| D13 | Does Chainstack support `token_accounts`, `cuckoo_account_include`, and what are its current filter and account limits | `docs.chainstack.com`, gRPC host |
| D14 | PumpPortal's keyless channels, and whether `subscribeMigration` needs a key | `pumpportal.fun` |
| D15 | Helius credit cost per method (`getSignaturesForAddress`, `getBlock`, `getTransactionsForAddress`), the autoscaling settings | `www.helius.dev/docs/billing` |
| D16 | Is `create_v2` Token-2022, and what share of graduates are legacy plain-token coins | `mainnet.helius-rpc.com` |

## Sources
- [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (instructions, events, `BuyEvent`/`SellEvent` fields, Boost events, fee program)
- [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md (GlobalConfig address, `disable`, pool seeds, `virtual_quote_reserves` 0 today)
- [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_PROGRAM_README.md (`set_params` scope)
- [DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md · https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md · https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md
- [DOC] https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/yellowstone-grpc-proto/proto/geyser.proto (`failed`, `index`, `token_accounts`, `cuckoo_account_include`, SlotStatus)
- [SEARCH] Helius autoscaling and extra credits: https://www.helius.dev/docs/billing/autoscaling · https://www.helius.dev/docs/billing/additional-credits.md
- [SEARCH] Helius WSS metering, 1,000 subscriptions per connection, random order; LaserStream on Business since Apr 7 2026: https://www.helius.dev/blog/laserstream-websockets · https://www.helius.dev/docs/billing/plans.md
- [SEARCH] Chainstack 2 streams for $49 (Jun 2026), older filter limits: https://docs.chainstack.com/changelog/chainstack-updates-june-10-2026.md · https://github.com/chainstack/dev-portal/pull/72.patch
- [SEARCH] Shyft and Solana Tracker flat prices: https://www.shyft.to/solana-yellowstone-grpc · https://www.solanatracker.io/yellowstone-grpc
- [SEARCH] PumpPortal Data API free; `create_wallet` returns a privateKey: https://github.com/TrustPump/Pump-Fun-API · https://lobehub.com/mcp/pump-portal-pump-portal-mcp-server
- [SEARCH] Alpenglow targets (400 ms blocks, 100–150 ms finality, simulated): https://alchemy.com/blog/solana-alpenglow · https://www.anza.xyz/blog/alpenglow-a-new-consensus-for-solana
- [SEARCH] Jito ShredStream shut down Sep 5 2026: https://chainstack.com/how-to-improve-solana-rpc-latency-with-shredstream/ · https://orbitflare.com/blog/developers/jito-shredstreams-last-slot
- [SEARCH] "first wave of retail and slower bots" (vendor guide): https://rpcfast.com/blog/how-to-launches-snipe-pump
