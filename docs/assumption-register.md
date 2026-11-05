# Assumption register (Phase 0 deliverable)

## In plain English (for Paul)
- This lists all **80 facts and numbers the design relies on**, numbered A-001 to A-080 and sorted with the most important first. For each one it gives how sure we are, where it came from, what goes wrong if it is false, and which test settles it.
- **Only 6 of the 80 come from reading a primary source, and 41 are still unproven.** That is normal before the Phase 0 network tests. It is also why nothing trades yet.
- The **30 "High" items** could cost money or leave the bot blind if they are wrong. No gate opens while a High item it depends on is unsettled (table in §3).
- When a test runs, we update the row's tag, date and result here. If a High item turns out to be false, we pause the affected part, red-team reviews it, and you hear about it in the daily summary.

**Tags.** [VERIFIED-DOC] = the primary source (official docs, IDL or pricing page) was read. [VERIFIED-SEARCH] = seen only in search results or secondary pages. [UNVERIFIED] = estimate or inference, with the test that settles it. [DERIVED] = our arithmetic on tagged inputs. **The tag shown is the tag of the claim's weakest part.** For example, a vendor price that was seen in search but whose sufficiency for our use is unproven is tagged UNVERIFIED. All dates are 2026. "11-04" means the Round 1–2 files; "11-05" means Round 3 or a re-check today (12 web searches; vendor pages blocked from fetching, see `docs/costs.md` §1).

---

## 1. Counts

| Impact | Rows | VERIFIED-DOC | VERIFIED-SEARCH | DERIVED | UNVERIFIED |
|---|---|---|---|---|---|
| **High** (money loss, theft, a blind spot, or the whole strategy) | 30 | 4 | 5 | 1 | 20 |
| **Medium** (a cost or timeline shift, a weaker edge, a fallback needed) | 31 | 1 | 8 | 5 | 17 |
| **Low** (small cost, or only affects a rejected alternative) | 19 | 1 | 14 | 0 | 4 |
| **Total** | **80** | **6** | **27** | **6** | **41** |

## 2. Test ID key
Test IDs come from the debate files. Some IDs repeat across files, so prefixes are added where needed.

| ID | Where defined |
|---|---|
| P1–P15 | Red-team attacks, `team-debate/round2/red-team-attacks.md` |
| D1–D10 / D11–D16 | Data-engineer, round 1 / round 2 response |
| **QT-T1–T11** | Quant-tester round 1 (the "T6" and "T7" in DESIGN.md) |
| **CF-T1–T11** | Chain-forensics round 1 (the "T1/T4" in DESIGN.md) |
| Q1–Q6, X1–X8, R1–R10, F1–F7 | Quant, execution, risk and forensics round 2 responses |
| **SEC-S1–S8** | Security round 2 (the "S1/S2/S3" key-vault tests in DESIGN.md) |
| **SOC-S1–S8** | Social round 2 (the "X history test S1" in DESIGN.md) |
| A1–A10 | AI-strategist round 2 (not the A-0xx numbers used in this file) |
| RC1–RC9 | Red-team re-check, `team-debate/round2/red-team-recheck.md` |
| G1–G8 | Lead-architect rulings §8 |
| **PX-1–PX-12** | **New:** price checks, defined in `docs/costs.md` §11 |
| DRILL-R1 | The four guard-failure drills (rulings R1) |
| DRILL-SELL5 | "Five ways of blocking a sell, flat within 60 s" plus the "selling disabled" alert (Gate 3→4) |
| RUIN | Ruin simulation re-run on whole recorded days (NEW-13, Phase 2) |
| PREREG | The pre-registered kill tests and pass marks (`docs/preregistration.md`, to be frozen in Phase 0) |
| GATE-v2 / CANARY | Paper gate (Gate 3→4) / canary gate (Gate 4→5) |
| PAUL | Only Paul can answer it |

---

## 3. Which gate needs which rows settled

| Gate | Rows that must be settled (or have a named fallback chosen) |
|---|---|
| **0 → 1** (provider tests, T6, prices) | A-001–A-007, A-009, A-011–A-013, A-021, A-022, A-035–A-037, A-046, A-047, A-048, A-051, A-052, A-062–A-067 |
| **1 → 2** (recorder health) | A-020, A-021, A-031, A-048, A-056, A-057, A-058 |
| **2 → 3** (research done) | A-023–A-027, A-029, A-034, A-042–A-045 |
| **3 → 4** (paper → canary) | A-008, A-010, A-014–A-019, A-030, A-033, A-039, A-040, A-053–A-055 |
| **4 → 5** (canary → live) | A-028, A-030, A-038, A-041 |

---

## 4. The register

### 4a. HIGH impact (A-001 to A-030)

| ID | Claim | Tag (checked) | Source | If wrong, what breaks | Settled by |
|---|---|---|---|---|---|
| A-001 | PumpSwap charges **1.25% per side** on a freshly graduated canonical pool (market cap under 420 SOL): 0.93% protocol, 0.30% creator, 0.02% LP. The admin can change it through the on-chain `feeConfig` | VERIFIED-DOC (11-05: the tier image docs/fees.png was read, and the mainnet fee-account capture in Pump SDK 2.1.0 was decoded; see docs/fee-model.md) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md ; https://trojan.com/blog/how-pump-fun-works ; https://blofin.com/academy/education/pumpfun/pumpswap-canonical-pool-ownership | Every cost per trade, break-even figure and paper profit is off. A higher real fee could turn every rule negative | QT-T5, Q1, QT-T6 |
| A-002 | Our fee and price maths reproduce every real trade **to the last lamport**. Reserves = vault balance + virtual quote reserves, minus the protocol and creator fees kept in the vault | UNVERIFIED (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md | Paper fills, the guard's price check and sell min-out are all wrong. Gate 0→1 fails | QT-T6 (500 trades), X6, D12 |
| A-003 | `virtual_quote_reserves` is a live **signed** value (it can be negative), and price uses vault + virtual | VERIFIED-DOC (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md | Quotes are mispriced and sells carry the wrong minimum price | RC3 |
| A-004 | Pool accounts come in several legal byte lengths. Older, shorter layouts are valid, and their missing trailing fields read as 0 | VERIFIED-DOC (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md | The decoder rejects good pools (a blind spot) or misreads fields | RC4 |
| A-005 | Pump's published IDLs (program description files) match the programs actually deployed | UNVERIFIED (the repository itself is VERIFIED-DOC) (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json ; https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json | Decoders and the guard's transaction builder are wrong: failed trades, or misread trades | D7, QT-T6, Phase 1 two-witness check (< 0.1% mismatch) |
| A-006 | Pump's trade events always appear as internal event calls inside the transaction, so we never rely on logs, which can be cut short | UNVERIFIED (11-04) | `team-debate/round1/data-engineer.md` (D5) ; https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_PROGRAM_README.md | Trades go silently missing (bad data, blind spots) | D5 |
| A-007 | Program upgrades and admin-setting changes are detectable from the chain (deploy slot, upgrade authority, GlobalConfig and feeConfig account changes) | UNVERIFIED (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md ; `team-debate/round2/data-engineer-response.md` | We keep buying through a rule change with stale decoders | D7, RC5 |
| A-008 | Pump changes its programs about **once every 4 weeks** | VERIFIED-DOC (README changelog) (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md | If faster: research clocks keep resetting, stop-rule clause 3 fires, and decoders break more often | D7 monitor tally over Phases 1–2; RC8 |
| A-009 | On Sep 1 2025 Pump made two new accounts mandatory and integrations broke. Our "sells-only auto-adopt" rule (R2) would have adopted that change safely and refused hostile diffs | UNVERIFIED (the event itself is VERIFIED-SEARCH) (11-05) | https://t.me/s/pump_tech_updates/29 ; `team-debate/round3/rulings.md` R2 | Sells fail during the next mandatory change, or a hostile layout gets adopted | RC8 |
| A-010 | Pump can switch selling off, as it did in Aug 2025. No bot can beat that | VERIFIED-SEARCH (11-04) | https://protos.com/axiom-traders-panic-as-pump-fun-temporarily-bans-selling-memecoins/ | Accepted risk. If it happens more often or for longer, more than 3% of the bankroll is stuck | DRILL-SELL5 (alert within 10 s), SEC-S8 |
| A-011 | PumpSwap **may** accept a payout account owned by someone other than the signer. So the guard's pinning of every payout to our own accounts is the defence | UNVERIFIED (worst case assumed) (11-04) | `team-debate/round2/red-team-attacks.md` P6 ; https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md | If the program allows it and the guard's pinning had a bug: theft through a trade | P6, SEC-S4 |
| A-012 | New coins (`create_v2`) are Token-2022 with **no mint or freeze authority** and only metadata extensions (no transfer hook, no permanent delegate). Legacy coins also have no authorities | UNVERIFIED (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/COIN_CREATION.md ; https://spl.solana.com/token-2022 | A coin could be frozen or clawed back, and we could not sell | CF-T1, D16, R9 |
| A-013 | The canonical PumpSwap pool is index 0, and its LP tokens are burned, so liquidity can't be pulled | UNVERIFIED (11-04) | https://blofin.com/academy/education/pumpfun/pumpswap-canonical-pool-ownership ; https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md | A rug by liquidity withdrawal, or a fake pool passes the check | CF-T4 |
| A-014 | AWS KMS signs with **Ed25519** (Solana's key type, since Nov 2025), and its output is a valid Solana signature | VERIFIED-SEARCH (11-04) | https://aws.amazon.com/about-aws/whats-new/2025/11/aws-kms-edwards-curve-digital-signature-algorithm/ ; https://docs.aws.amazon.com/cli/latest/reference/kms/sign.html | The signer design must change (another vault, or a hosted wallet) before Phase 4 | SEC-S1 / RC9, SEC-S2 |
| A-015 | A KMS signature is fast enough at p99 for the guard's loop (tunnel → quote → KMS → send) to stay within about 2–3 slots | UNVERIFIED (one forum post says ECC signing in KMS can be slow) (11-04) | https://repost.aws/questions/QUPEubdAqrSnSLm-38Vjyqpw/kms-signing-performance-with-asymmetric-ecc-nist-p256-key-is-slow | The re-quote interval grows, and crash sells slip further | SEC-S1 / RC9 |
| A-016 | An IAM policy can give the tripwire **only** `kms:DisableKey` on one key, and the guard reaches KMS through its machine role with no secret on disk | UNVERIFIED (11-04) | `team-debate/round2/security-engineer-response.md` (S3) | The tripwire credential could do more than freeze, or a secret sits on disk | SEC-S3 |
| A-017 | The guard's lease record and lever parameter (inside its own AWS account) support safe conditional writes and reliable reads every 2 s from Frankfurt | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` R1, NEW-17, G2 | Two guards act at once, or a lever change is late | G2 |
| A-018 | A "sell my current balance" transaction limits itself. Once the tokens are gone, a second copy fails and costs only the network fee | VERIFIED-SEARCH (via the execution engineer) (11-04) | `team-debate/round2/execution-engineer-response.md` (EXE-1) | Automatic standby takeover could cause double action. This is what makes the sell-only standby safe | DRILL-R1 (drills 2 and 4) |
| A-019 | The guard's own Helius stream of held pools lags the bot's Chainstack stream by **2 slots or less at p95** during crashes | UNVERIFIED (11-05) | `team-debate/round2/red-team-recheck.md` (NEW-2) ; `team-debate/round3/rulings.md` R3 | The guard's exits fire late. It would then need a second stream before any canary | RC2, G3 |
| A-020 | For held coins, a Helius `programSubscribe` on both token programs, filtered by mint, shows every holder's balance change, including plain transfers | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` C11 ; `team-debate/round2/chain-forensics-response.md` | A blind spot on the coins we hold: insider exits fire late | F2, D13 |
| A-021 | Chainstack's Yellowstone stream delivers **every** Pump and PumpSwap transaction, **including failed ones**, with its slot | UNVERIFIED (the stream filters are VERIFIED-DOC; Chainstack's support for them is VERIFIED-SEARCH) (11-05) | https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/yellowstone-grpc-proto/proto/geyser.proto ; https://chainstack.com/products/yellowstone-grpc/ | Blind spots. Competition-aware paper fills become impossible | D3, D4, X5, Phase 1 coverage ≥ 99.5% |
| A-022 | Chainstack's flat-rate plan carries the full firehose **without throttling** | UNVERIFIED (11-05) | `team-debate/round2/data-engineer-response.md` ; https://chainstack.com/yellowstone-grpc-more-streams-same-price/ | Lost coverage, or a switch to Solana Tracker (+$126 to +$175 a month, `docs/costs.md` F4) | D4, RC6, Q2, D11 |
| A-023 | Buying every graduate after BOOST loses **no more than ~5 points per trade** after all costs (the first "what has to be true" item) | UNVERIFIED (11-05) | DESIGN.md §3b ; `team-debate/round2/red-team-recheck.md` | No rule is likely to clear costs, and the week-4 stop checkpoint fires | P2, P3 (baselines, Phase 2) |
| A-024 | The end of BOOST is **not already crowded** by other careful bots (crowded entries ≤ 30%, median arrival penalty ≤ 1.5%) | UNVERIFIED (bots are known to watch the 5-minute window [VERIFIED-SEARCH]) (11-05) | https://www.htx.com/news/443626/ ; `team-debate/round3/rulings.md` R5 | Idea 2 dies and live trading goes back to paper | RC1; R5 crowding kill |
| A-025 | BOOST is visible on the chain: `BoostBuyAndBurnEvent.boost_vault_remaining`, `GlobalConfig.boost_enabled` and the `toggle_boost` instruction | VERIFIED-DOC (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json | The entry rule can't tell when BOOST has ended | R2 |
| A-026 | BOOST buys about **17.6 SOL** of each new graduate over about 5 minutes, then stops. The amount is read from events, never assumed | VERIFIED-SEARCH (amount not confirmed as fixed) (11-05) | https://www.kucoin.com/blog/pump-fun-boost-mode-explained ; https://onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering | Entry timing and the BOOST study are built on the wrong pattern | R2, F4, X7, R10 |
| A-027 | Stop-losses don't slip too far. The share of −20/−35/−50% stops that fill below −50%, by minute since migration, is small enough for stops to mean something | UNVERIFIED (11-04) | `team-debate/round2/risk-manager-response.md` (R1 gap study) | Losses per trade exceed the plan, and the ruin simulation is wrong | R1 |
| A-028 | Paper fills match real fills within about 2 points per trade. The "20% contested landing" figure is a guess, because losing Jito bundles never appear on the chain | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` §5 (PREMISE-3, QNT-1) | Paper shows a profit that doesn't exist | CANARY (gap ≤ 2 points per trade) |
| A-029 | The chance of ruin (a 50% fall) is about 0 at 1% per trade, even with a losing rule | DERIVED (illustration) (11-04) | `team-debate/round2/risk-manager-response.md` §1.2 | The drawdown and daily limits are too loose | RUIN (whole-day resampling, Phase 2) |
| A-030 | Together, the edges reach **≥ +5–6% net per trade** on 5–10 trades a day (exit tournament ≥ 2 points, plus an entry feature that passes) | UNVERIFIED (hypothesis) (11-05) | DESIGN.md §3b ; `team-debate/round3/rulings.md` §4 | The desk can't pay its bills, and the stop rule ends the spending | PREREG kill tests; GATE-v2 |

### 4b. MEDIUM impact (A-031 to A-061)

| ID | Claim | Tag (checked) | Source | If wrong, what breaks | Settled by |
|---|---|---|---|---|---|
| A-031 | About **200 graduates a day** (plausible range 80–2,000), from about 30,000 launches a day | DERIVED (the launch count is VERIFIED-SEARCH; the graduation rate swings from 0.26% to 6.7%) (11-04) | https://madeonsol.com/blog/pump-fun-first-3-minutes-graduation-math ; https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex ; https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives | Fewer: the exit tournament and the gates take longer. More: bandwidth and AI costs rise (both capped) | Q6, QT-T1 |
| A-032 | A slot lasts about **200 ms** (target), about 218 ms measured | VERIFIED-SEARCH (11-04) | https://solanacompass.com/news/solanas-200ms-slot-time-is-live-on-mainnet-at-epoch-1053-completing-simd-0525 ; https://solanacompass.com/news/solanas-first-full-epoch-at-the-200ms-slot-time-target-averaged-2183ms-and-lasted-262-hours | Time budgets shift. Timers are written in slots, so the logic still holds | D6, QT-T7 |
| A-033 | A transaction's built-in expiry (blockhash) lasts about **150 slots ≈ 30–33 s** | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` C8 | Exit tickets and retries expire earlier or later than planned | X3 |
| A-034 | With our setup we would arrive **3–8 blocks (0.6–1.8 s)** after graduation, and catching up would cost about $2,000+ a month | UNVERIFIED (11-04) | `team-debate/round2/execution-engineer-response.md` | If we are actually closer, the no-race decision leaves money on the table. That is a missed chance, not a loss | QT-T7, P4, D3; the race memo (around day 21) |
| A-035 | Synthetic migration: the bot that completes the bonding curve can buy pool-priced tokens in the same transaction | VERIFIED-DOC (11-04) | https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/SYNTHETIC_MIGRATION.md | The "don't race" thesis weakens (a missed chance, not a loss) | D2, P1 |
| A-036 | A fresh pool holds about **85 SOL** (80–85) | UNVERIFIED (11-04) | `team-debate/round2/execution-engineer-response.md` §1b | If smaller: price impact rises and the 1%-of-pool cap bites sooner | CF-T4, D2 |
| A-037 | Round-trip price impact ≈ 2 × bet ÷ pool SOL | DERIVED (constant-product maths) (11-05) | `team-debate/round3/rulings.md` 6b | Per-trade cost and size caps are off | QT-T6 |
| A-038 | Network fees + tips per round trip ≈ **0.13% calm / 1.64% crash** at 0.25 SOL | DERIVED (from EXE-R's assumed priority fees and tips) (11-04) | `team-debate/round2/execution-engineer-response.md` §1b–1c | Per-trade cost is off by up to ~1.5 points | X1, X2, P4 |
| A-039 | The Jito minimum tip is 1,000 lamports, a failed bundle costs nothing, and the `jitodontfront` marker works | UNVERIFIED (the minimum tip is VERIFIED-SEARCH; "failed costs nothing" is inference) (11-04) | https://quicknode.com/docs/solana/getTipFloor ; `team-debate/round1/execution-engineer.md` | Buy costs rise, or we can be front-run | X1, QT-T8, Q5 |
| A-040 | Helius Sender needs a tip of ≥ 0.000005 SOL (SWQoS-only) or ≥ 0.001 SOL (Max), has an `mev-protect` option, uses no credits, and allows 50 tx/s | VERIFIED-SEARCH (11-04) | https://www.helius.dev/docs/sending-transactions/sender ; https://www.helius.dev/docs/sending-transactions/sender-swqos-only | Sell cost or sell path changes | X4, SEC-S7 |
| A-041 | With a tight min-out and protected senders, sandwich bots take **≤ 0.2%** of a crash sell | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` 6b | Crash exits cost more than planned | P14; CANARY (≤ 0.5% leak per path) |
| A-042 | Exits split about **70% calm / 30% crash** | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` 6b | The blended cost moves anywhere between 3.2% and 4.9% | R1 gap study; exit-tournament logs |
| A-043 | Proving a realistic 5–8% edge needs **600–1,800 trades** (one trade's result swings about ±100%) | DERIVED (11-04) | `team-debate/round2/quant-tester-response.md` §1c | If results swing more, the paper phase runs longer and costs more | Swing measured on the P3 baselines |
| A-044 | The primary entry rule finds **≥ 5 qualifying entries a day** | UNVERIFIED (11-04) | `team-debate/round2/red-team-recheck.md` (NEW-10) | The rule fails its gate on volume, and the desk can't pay its bills | RC7 |
| A-045 | Insiders move a real share (≥ 10%) of their dumped tokens to fresh wallets by plain transfer | UNVERIFIED (11-04) | `team-debate/round2/chain-forensics-response.md` (F1) | Idea 4's "follow the tokens" part is dropped (cheap early kill) | F1, P5 |
| A-046 | Chainstack supports `token_accounts` and cuckoo-filter watches for wallets' token accounts | UNVERIFIED (11-04) | https://docs.chainstack.com/changelog/chainstack-updates-june-10-2026.md | The candidate watch uses Helius `transactionSubscribe` instead, which costs credits | D13, F2 |
| A-047 | Yellowstone's `index` equals the transaction's position in the block | UNVERIFIED (11-04) | `team-debate/round2/quant-tester-response.md` (Q3) | The "placed last in the block" paper rule needs `getBlock` calls (credits) | Q3, D12 |
| A-048 | Helius credit use fits: about 0.85M a month normally, 8.95M at worst, against 10M included | DERIVED (credits per method are UNVERIFIED) (11-05) | `team-debate/round3/rulings.md` 6d | The guard's reserve is threatened, and autoscale or stricter caps are needed | P12, D15, R8, F3 |
| A-049 | One Helius account can hold separate keys (bot, forensics, guard) with per-key limits | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` G5 | Guard key separation needs a second account (+$0–49) | G5 |
| A-050 | Helius autoscaling can be capped (e.g. at $25) and stops at the cap | VERIFIED-SEARCH (third-party: capped on Developer) (11-05) | https://apis.io/plans/helius/helius-plans-pricing/ ; https://www.helius.dev/docs/billing/autoscaling | An uncapped overage | G8, PX-2 |
| A-051 | Chainstack Growth's included **20M request units** cover block capture around migrations and the guard's cross-check poll | UNVERIFIED (the 20M figure is VERIFIED-SEARCH) (11-05) | https://coinsaga.com/news/technology/chainstack-solana-rpc-review-2026-free-plan-and-features/ | That work moves to Helius credits, or we pay a Chainstack overage | G4, PX-1 |
| A-052 | Chainstack's Yellowstone add-on is **$49 for 2 streams** (Growth plan required) | VERIFIED-SEARCH (**sources conflict**: one says $49 buys 1 stream; the next tiers are $149 for 5–7 and $449 for 25) (11-05) | https://chainstack.com/learn/compare/best-yellowstone-grpc-providers-solana-2026/ ; https://chainstack.com/yellowstone-grpc-more-streams-same-price/ ; https://www.solanatracker.io/yellowstone-grpc | +$100 a month (the data line goes from $98 to $198) | PX-1, D10 |
| A-053 | KMS targets 99.999% monthly uptime per region (about 26 s a month) | VERIFIED-SEARCH (11-04) | https://aws.amazon.com/kms/sla | More downtime. Positions wait (≤ 3% exposure) | SEC-S6 |
| A-054 | EC2 auto-recovery works for t4g instances in Frankfurt (eu-central-1) | UNVERIFIED (11-05) | `team-debate/round3/rulings.md` G1 | Layer 2 of the guard's failover is missing. The standby (layer 3) still covers | G1 |
| A-055 | A dead-man's-switch service exists that accepts outbound heartbeats, alerts a phone, and costs $0–17 a month | UNVERIFIED (free tiers are VERIFIED-SEARCH: Healthchecks.io 20 checks, Better Stack 10 heartbeats; native phone push not confirmed) (11-05) | https://betterstack.com/community/comparisons/better-stack-vs-healthchecks-io/ ; https://hyperping.com/blog/healthchecks-io-alternatives | Paul's "both guards silent" alert needs another app (e.g. a push relay) | G6, PX-10 |
| A-056 | Data-feed outages happen. Chainstack had a 25-hour Solana degradation (May 2026) and a London cluster outage | VERIFIED-SEARCH (11-04) | https://pingoru.io/providers/chainstack/incidents/3419497 ; https://isdown.app/status/chainstack/incidents/541754-solana-mainnet-down-in-london-cluster | If more frequent: more missed trades and recorder gaps (degraded mode never buys) | P9, SEC-S6 |
| A-057 | Recorded data grows by **15–135 GB a month**, so a 200 GB disk plus an archive is enough | UNVERIFIED (11-04) | `team-debate/round2/data-engineer-response.md` (DAT-8) | Disk alarms fire, and a bigger disk or archive costs +$10–30 a month | D4, P11 |
| A-058 | A shared 4 vCPU / 8 GB server (~$48 a month) can run the recorder, decoders, paper bot and research. A dedicated 4 vCPU / 16 GB server costs $86–126 | UNVERIFIED (the 16 GB prices are VERIFIED-SEARCH, default regions, not Frankfurt) (11-05) | https://www.digitalocean.com/pricing/droplets ; https://getdeploying.com/digitalocean-vs-vultr ; https://spendark.com/compare/g-4vcpu-16gb-vs-voc-g-4c-16gb/ | The recorder falls behind (blind spots) until we upgrade (+$38–78 a month) | D4, A9, G7, PX-6 |
| A-059 | SOL ≈ **$100** (about $101 on Oct 27 2026) | VERIFIED-SEARCH (11-05; no dated November quote found) | https://www.mexc.com/news/82737 ; search 2026-11-05 (a snippet attributed to 24/7 Wall St, Oct 27 2026) | Dollar values of per-trade costs and the bankroll shift. Bills are in USD and don't change | PX-11 |
| A-060 | **1.42 CAD per USD** (Oct 14 2026). July–August 2026 was 1.40–1.41 | VERIFIED-SEARCH (11-05; no November quote found) | https://30rates.com/ (Round 3) ; https://pluang.com/en/tools/currency-converter/usd-cad | If the USD strengthens past ~1.433, the Phase 3 high case exceeds CAD $1,000 (`docs/costs.md` F1) | PX-11 (monthly) |
| A-061 | Paul's CAD $1,000 budget is the **vendors' sticker price** (sales tax and card foreign-exchange fees not included) | UNVERIFIED (question) (11-05) | `docs/costs.md` §4c | If tax and fees are inside the budget, the usable sticker budget falls to about CAD $850–930 | PAUL, PX-12 |

### 4c. LOW impact (A-062 to A-080)

| ID | Claim | Tag (checked) | Source | If wrong, what breaks | Settled by |
|---|---|---|---|---|---|
| A-062 | Helius Developer costs **$49 a month** for 10M credits and 50 requests/s. Extra credits are **$5 per million** | VERIFIED-SEARCH (11-05; one source mentions a Sep 2026 pricing refresh) | https://www.helius.dev/pricing ; https://www.helius.dev/docs/billing/plans | A small cost shift | PX-2 |
| A-063 | Solana Tracker's standalone Yellowstone gRPC costs **€200 a month flat**, with no data caps and 25 connections (the fallback if Chainstack throttles) | VERIFIED-SEARCH (11-05) | https://docs.solanatracker.io/pricing ; https://www.solanatracker.io/yellowstone-grpc | The fallback costs more | PX-3 |
| A-064 | AWS t4g.small costs about **$0.019 an hour in Frankfurt** (~$14 a month) | VERIFIED-SEARCH (11-05; aggregator) | https://www.devzero.io/instances/aws/t4g.small ; https://aws-pricing.com/t4g.small.html | A small cost shift | PX-4 |
| A-065 | AWS KMS costs **$1 per key per month** plus **$0.15 per 10,000** asymmetric sign requests, with no free tier for asymmetric requests | VERIFIED-SEARCH (11-05; one source lists $0.03 for ECC, which is lower) | https://aws.amazon.com/kms/pricing/ ; https://cloudburn.io/blog/aws-kms-pricing | Negligible: a few cents a month | PX-5 |
| A-066 | AWS charges about $0.005 an hour (~$3.65 a month) for each public IPv4 address | UNVERIFIED (from memory) (11-05) | https://aws.amazon.com/vpc/pricing/ (to check) | The guard line moves ±$7 | PX-4 |
| A-067 | Block storage costs about **$0.10 per GB-month** (NVMe), or about $0.025 on HDD tiers | VERIFIED-SEARCH (11-05; aggregators disagree) | https://getdeploying.com/digitalocean-vs-vultr ; https://ployz.dev/blog/vultr-pricing | The disk line moves ±$15 | PX-7 |
| A-068 | Claude prices: Haiku 5.5 $0.10 / $0.50 and Opus 5.5 $4 / $20 per million input / output tokens. Batch is 50% off. A 1-hour cache write costs 2× the input price | VERIFIED-DOC (Anthropic API reference, cached 2026-10-06), matched by VERIFIED-SEARCH (11-05) | https://platform.claude.com/docs/en/about-claude/pricing ; https://costgoat.com/pricing/claude-api | The AI line shifts. It is capped by the Console limit anyway | PX-8, A5 |
| A-069 | A label call uses ~2,500 cached + 1,500 new + 500 output tokens. Haiku takes about 6 s to start answering | UNVERIFIED (the token counts are estimates; latency is VERIFIED-SEARCH) (11-04) | `team-debate/round2/ai-strategist-response.md` §1c ; https://www.edenai.co/models/claude-haiku-5-5 | The AI line shifts (capped). AI is never in the trade path | A1, A5 |
| A-070 | X API pay-per-use: $0.005 per post read; counts requests about $0.005 (recent) and $0.010 (full archive); 3M reads a month cap | VERIFIED-SEARCH (11-05; the official page shows $0.005 per post read) | https://docs.x.com/x-api/getting-started/pricing ; https://www.outstand.so/blog/x-api-pricing | The optional X test costs more than $10–20 | SOC-S1, PX-9 |
| A-071 | Few non-team X posts exist at our entry time (about 5 minutes after graduation) | UNVERIFIED (11-04) | `team-debate/round2/red-team-attacks.md` (P13) | If many exist, paid X data might be worth testing sooner | P13 |
| A-072 | Hetzner has banned crypto use (2022), so the bot host avoids it | VERIFIED-SEARCH (11-04) | https://www.hivelocity.net/blog/cloud-tos-crypto-when-your-validator-is-not-welcome/ | One host candidate is lost needlessly | G7 (read the chosen provider's terms) |
| A-073 | Privy had 8 outages since Feb 2026, and Turnkey costs $0.10 per signature (both rejected as signers) | VERIFIED-SEARCH (11-04) | https://isdown.app/status/privy-io/outage-history ; https://www.turnkey.com/pricing | Only the comparison changes | SEC-S6 |
| A-074 | Solana plans to remove durable nonces about 6 months after a replacement ships | VERIFIED-SEARCH (11-04) | https://solana.com/upgrades/durable-nonce-deprecation | None. They are banned in v1 anyway | Re-check only if PSES is ever reopened |
| A-075 | Retail trading-app users often accept 30–50% slippage | VERIFIED-SEARCH (11-04) | https://www.datawallet.com/crypto/gmgn-explained | One of the "exit cheaper" arguments weakens | P14, X8 |
| A-076 | **1.12 USD per EUR** (Oct 30 2026) | VERIFIED-SEARCH (11-05) | https://30rates.com/eur-usd-forecast-tomorrow-this-week ; https://www.poundsterlinglive.com/history/EUR-USD-2026 | The Solana Tracker fallback's dollar cost moves | PX-11 |
| A-077 | The base fee is 5,000 lamports per signature, and the priority fee is charged on the **requested** compute limit | VERIFIED-DOC (11-05: Solana source code; see docs/fee-model.md) | https://solana.com/docs/core/fees/fee-structure | A small per-trade shift | X2 |
| A-078 | Helius `funded-by` costs 100 credits a call. Our own funding lookup costs about 3 | UNVERIFIED (the 100 is VERIFIED-SEARCH; our ~3 is an estimate) (11-04) | https://www.helius.dev/docs/wallet-api/funded-by | The forensics credit cap bites sooner | F3, CF-T5 |
| A-079 | Validators running Jito's client produce most blocks (88–95% of stake) | VERIFIED-SEARCH (11-04; figures vary) | https://rpcfast.com/blog/jito-explained-bundles-tips-mev-solana | Bundle-only buys land less often (missed buys, not losses) | X1, P4 |
| A-080 | Rejected alternatives cost: LaserStream needs the $499 Business plan; bloXroute about $300; our own node $1,800+; a second firehose about $200 (Shyft $199) | VERIFIED-SEARCH (11-04) | https://www.helius.dev/docs/laserstream.md ; https://www.trustradius.com/products/bloxroute-labs/pricing ; https://www.shyft.to/solana-yellowstone-grpc | Only the decision table's comparison changes | D10 |

---

## 5. Rules for keeping this register
1. **One row per fact.** A new fact gets the next number (A-081 onward). Rows are never deleted; superseded rows are marked "SUPERSEDED by A-0xx".
2. **When a test runs**, add "Result (date, test): …" to the row, change the tag, and update `docs/costs.md` if the fact is a price.
3. **A High row found false** → buys pause (if any part of the bot is running), the affected design section is reviewed by red-team, and Paul is told in the daily summary in plain English. Gates stay shut until it is resolved.
4. **Prices are re-checked monthly** (PX tests) and before every gate.

## Tests to run once allowed
Every test named above is already defined, with its domain, in the round files (`team-debate/round1/`, `team-debate/round2/`, `team-debate/round3/rulings.md` §8). QUESTIONS_FOR_PAUL.md has the consolidated domain list. The new price checks (PX-1 to PX-12), with their exact domains, are in `docs/costs.md` §11.
