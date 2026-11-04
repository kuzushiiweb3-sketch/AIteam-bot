# Round 2b: Execution engineer response (buying, selling, landing, costs)

**In plain English (for Paul):**
- **We should not race other bots at the moment a coin graduates.** At best we would arrive 3–8 blocks (about 0.6–1.8 s) behind the leaders. Catching up would cost about $2,000 a month plus large tips, which adds 8–17% to every 0.5 SOL trade. The plan is to buy after that first scramble has calmed down, when fees are tiny and our trades nearly always get through. We spend money on speed only for **selling**, and that is almost free.
- **Selling in a crash is redesigned.** We no longer accept a fixed 20–30% worse price. Every block or two we re-price the sell from the pool's real numbers and allow only a small margin. A sandwich bot can then take at most that margin (about 1–5%), never 30%.
- **Fees are settled with the quant team in one table:** Pump.fun's pool fee is **1.25% each way** on a freshly graduated coin, so 2.5% for a buy plus a sell, before anything else. A full buy and sell costs about **3.1% of the position at 0.1 SOL and 3.7% at 0.5 SOL in calm conditions, and 4.5–6.8% when we must get out of a crash fast.**
- **At the proposed 0.05 SOL bet, a crash exit eats about 11% of the stake.** I propose a minimum real-money position of **0.25 SOL**. Smaller sizes stay in paper trading (or a tiny "measurement-only" test).
- Paper trading will now **assume we lose the busy auctions**, instead of treating failures as random luck. This stops it from showing profits on hot coins we could never really have bought.

**Tags:** [VERIFIED-DOC] = primary source read this session; [VERIFIED-SEARCH] = search results only; [UNVERIFIED] = estimate or inference, with the test that would settle it. **Host notes:** WebFetch worked on `raw.githubusercontent.com` (3 Pump docs re-read today). I did not retry hosts that failed in Round 1 (`helius.dev`, `developers.jup.ag`, `docs.jito.wtf`). I used 9 web searches. No live tests were possible.

**Three new facts since Round 1:**
1. Slots are now **~200 ms** (measured ~222 ms) since Oct 9 2026, and a transaction's built-in expiry ("blockhash") lasts **~30 s** [VERIFIED-SEARCH solanacompass, kucoin]. Whether Alpenglow is live on mainnet: sources conflict [VERIFIED-SEARCH]. We measure it with `getRecentPerformanceSamples`.
2. In v2 PumpSwap trades, protocol and creator fees **stay inside the pool's SOL vault** until someone sweeps them, recorded in `Pool.protocol_fees` / `Pool.creator_fees` [VERIFIED-DOC PUMP_SWAP_TRADE_V2.md]. So a price computed from the raw vault balance may overstate the pool [UNVERIFIED; test T6 settles it]. The README does not say whether the user's token accounts must belong to the signer [VERIFIED-DOC].
3. Helius Sender has a `mev-protect=true` option that avoids validators linked to sandwiching. SWQoS-only mode (sends through validators' "staked" fast lane only) needs a tip of ≥0.000005 SOL. Max mode needs ≥0.001 SOL. Every Sender transaction must carry a tip and a priority-fee instruction [VERIFIED-SEARCH helius.dev/docs/sending-transactions/sender-swqos-only, /trading/overview].

---

## 1. Answers to attacks

| ID | Verdict | What changed / why |
|---|---|---|
| **EXE-1** retry ladder vs no-rebuild | **FIXED** | Separate rules. **Buys are one-shot:** the same signed buy is re-broadcast and never rebuilt. It carries a **"short fuse"**: we sign with a slightly older blockhash, so it can only land within ~10 blocks (≈2 s) [UNVERIFIED technique, test X3]. A late buy then can't fill into a changed market. **Sells rebuild every 2 blocks** as "sell my current balance". A double send limits itself: once the tokens are gone, the second sell fails and costs only its fee. Take-profit tranches (partial sells) are not urgent, so they keep the no-rebuild rule; with 30 s blockhashes that wait is short. An emergency "sell all" always overrides a tranche that is still in flight. |
| **EXE-2** retry budget too small | **FIXED** | The budget is set in absolute SOL, not as a percentage. Each open position locks a **0.01 SOL exit reserve** inside risk's fee reserve; buys can't touch it. Tips are instructions *inside* the transaction, so a sell that fails on-chain pays only base + priority fee and no tip. A Jito bundle that fails pays nothing [UNVERIFIED inference from bundle atomicity; test X1]. So retries mostly burn priority fees. If the reserve runs out, the bot keeps retrying at calm fees every 10 s and alerts Paul. It never just stops. |
| **EXE-3** wide slippage over many paths | **FIXED** | Slippage percentages are replaced by a **margin over the pool-maths quote**. min-out = quote at the latest block × (1 − m). Normal m = clamp(2 × the 2-block price swing, 1%, 5%); emergency m = clamp(3 × swing, 3%, 15%). In a crash we **chase the price down by re-quoting every 2 blocks**, never by widening the margin, so a sandwich can take at most m. Each sell is **one signed transaction** sent to Jito bundle-only (with the `jitodontfront` anti-front-run marker) **and** to Helius SWQoS-only with `mev-protect=true`. One signature means it lands at most once. Sender Max, which fans out to paths we can't vet, is used only after 2 failed protected attempts. The canary measures realised vs quoted price per path and drops any path that leaks. |
| **EXE-4** Jupiter cross-check | **FIXED** | Jupiter is removed from the live path completely (see SEC-1). The independent check is now **local**: our own constant-product maths vs the official SDK's quote function, on the same block's pool state. A gap over 0.1% means a bug, and **buys** pause. The check **never gates sells**. Jupiter becomes a read-only daily audit. |
| **EXE-5** Pump's sell switch | **ACCEPTED RISK** + mitigations | Nobody can sell through PumpSwap while Pump disables it (`DisabledSell` 6021) [VERIFIED-DOC pump_amm.json]. The protections: (1) the risk team's per-coin size cap; (2) a subscription to PumpSwap's global config account: any flag change pauses buys and alerts Paul at once; (3) **"first out when the door reopens"**: the exit guard keeps a sell pre-built and re-priced every 2 blocks, and sends it in the first block after the flag flips back; (4) security's tested manual exit (P10). "Stuck" now means "waiting to fire", not "given up". |
| **EXE-6** capped tip loses auctions | **FIXED by design** (see §2) | We don't enter contested auctions. The tip cap comes from P4 data. Paper counts contested coins as **missed** (PREMISE-3 below). |
| **EXE-7** missing costs | **FIXED** | Added to the table in §1c: token-account deposit (the final sell closes the account in the same transaction, so the deposit comes back), wrapped-SOL handling (one **persistent** wSOL account instead of wrapping and unwrapping on every trade), fees on failed attempts, signing fees, and the v1 path for cashback pools (error 6079) [VERIFIED-DOC PUMP_SWAP_TRADE_V2.md]. The `buyback_fee_recipient` account "must exist", so the builder adds an idempotent create step (it does nothing if the account already exists) [VERIFIED-DOC same]. |
| **EXE-8** fee-tier boundary | **FIXED** | One shared fee module (table §1b). It computes market cap with the program's own formula, `quoteReserve × baseMintSupply ÷ baseReserve`, at quote time, and uses the first tier when below the first threshold [VERIFIED-DOC FEE_PROGRAM_README.md]. BOOST alone lifts a fresh pool from about 380–410 SOL of market cap to about 600 SOL [UNVERIFIED arithmetic: 85 SOL pool + 17.6 SOL of buying], so the tier really does change during a hold. Paper charges 1.25% until T6 passes. |
| **EXE-9** landing rates from 2024 | **FIXED** | No landing number enters the go-live gate until P4 and the canary measure it. Paper uses the competition model below, not 70%/90%. |
| **SEAM-1** bet size × fixed costs | **FIXED (proposal) / QUESTION for Paul via lead-architect** | Live minimum position **0.25 SOL**: fixed costs are then 0.14% calm and 1.6% in a crash exit. **No take-profit ladder below 0.5 SOL.** Maximum position = **1.5% of the pool's SOL reserve** (≈1.3 SOL in an 85 SOL pool), so one emergency sell's own price impact stays ≤ ~2–3% (this also answers RSK-7: no chunked sells). The signer must cost ≤$0.01 per signature. Turnkey pay-as-you-go at $0.10 [VERIFIED-SEARCH, SEC] adds 1.6% per 4-signature trade at 0.25 SOL. Paul's question is the bankroll: 0.25 SOL at risk's "0.5% of bankroll" implies a 50 SOL bankroll. At a smaller bankroll, stay in paper or raise the per-trade share. |
| **SEAM-3** can we still sell? (execution part) | **FIXED for my part; security/risk own the rest** | (a) The sell path **does not depend on the npm SDK**: a small sell builder is generated from the pinned IDL JSON, reviewable in minutes (answers point 5 / SEC-5). (b) A **fixed sell template** for a sell-only credential that STOP does not revoke. Allowed contents: compute-budget ×2, idempotent create of the buyback ATA, PumpSwap `sell`/`sell_v2` with *our* accounts pinned, close-account to the hot wallet, and one tip ≤0.003 SOL to a listed tip account. (c) **Rolling "exit tickets"**: while a position is near a stop, the guard keeps one *signed* sell, refreshed every ~20 s. It can only pay into our own accounts, has a tight min-out and expires in ≤30 s. That carries us through short signer blips (Privy's incidents were mostly "delays" [VERIFIED-SEARCH isdown]), not long outages. Security must approve it (§3). (d) The paper drill cuts each of the 5 paths in turn and reports time-to-flat (p50/p95) and SOL lost against the price at the trigger. |
| **SEAM-4** fee models 5× apart | **FIXED** | One table, §1b. |
| **SEAM-11** two slippage ladders | **FIXED (needs risk to adopt)** | Risk's 3/8/15/30% and my 5/20% both become the margin model in EXE-3. Risk's 30% survives only as a **cumulative chase limit**: the most we will follow the price down before alerting Paul, never the slippage of a single transaction. |
| **SEAM-12** tip recipients vs allowlist | **FIXED (list for security)** | Tip recipients per sender: Jito's 8 tip accounts (from `getTipAccounts`, pinned), Helius Sender's tip accounts and Nozomi's (copied from their official docs at build time, never from memory). Cap: one tip per transaction, ≤0.003 SOL. |
| **SEAM-7** credits (send side) | **ACCEPTED** | Sender uses no Helius credits [VERIFIED-SEARCH R1], so the exit's send path never runs dry. Its reads are data-engineer's to budget. |
| **SEC-1** Jupiter can pay output to anyone | **FIXED** | **Jupiter is never signed in v1.** Route A builds every PumpSwap trade with `user_base_token_account` = our token account for that coin and `user_quote_token_account` = our persistent wSOL account. The signer guard checks those two accounts, `user`, and `pool` = the canonical pool PDA **by name from the pinned IDL**. A program allowlist alone is not enough. Non-PumpSwap liquidity is not traded in v1. A held coin whose only liquidity has moved elsewhere is ACCEPTED RISK until a Jupiter exit with the output pinned passes P7. |
| **PREMISE-1** we lose the race | **ACCEPTED, and we stop racing** | See §2. Execution does **not** compete at graduation. Speed money goes to exits only. |
| **PREMISE-3** adverse selection | **FIXED (simulator spec)** | See §1d. |

### 1a. Sell procedure, start to finish (replaces Round 1 §4)
1. **Trigger.** Quote from the latest processed block. Set min-out with the margin m.
2. **Send.** One signed transaction to Jito bundle-only (dontfront) plus Helius SWQoS-only (mev-protect).
3. **Every 2 blocks (~0.4 s), if it hasn't landed:** re-quote, rebuild "sell current balance", and step the fee. Priority fee: 0.0001 → 0.0003 → 0.001 → 0.002 SOL. Jito tip: p50 → p75 → p95 of the live tip floor. After 2 failed protected attempts, add Sender Max (0.001 SOL tip).
4. **Target: flat within 15 blocks (~3 s)** in 95% of paper crash drills [UNVERIFIED target].
5. **Stop and alert, but keep a pre-built sell ready, only on:** 6021 `DisabledSell`, a frozen account, a transfer-hook or fee mint (security screens these out before buying), or an unknown error code.
6. **The wallet's on-chain balance is the truth** after every attempt.

### 1b. ONE fee table (agreed basis for quant-tester's simulator and my cost table)
| Item | Quant R1 | Exec R1 | **Settled: both use this** | Tag |
|---|---|---|---|---|
| PumpSwap fee, **canonical** pool, market cap < 420 SOL | 20 bps LP + 5 bps protocol + creator tier | 1.25% (0.93 protocol / 0.30 creator / 0.02 LP) | **1.25% per side.** Only the total matters for P&L. Sources disagree on the split | Total consistent across [VERIFIED-SEARCH trojan, blofin, solanafloor]. The official tier table is an image we couldn't read [VERIFIED-DOC FEE_PROGRAM_README] |
| Canonical, 420–1,470 SOL | — | 1.20% | 1.20% *after* T6. Until then 1.25% | [VERIFIED-SEARCH benzinga, blofin] |
| Higher tiers | — | falling to 0.30% above ~98,000 SOL | Read live from `feeConfig` | [VERIFIED-SEARCH solanafloor] |
| Non-canonical pools | (the 20 + 5 bps global config is the fallback) | — | `feeConfig.flatFees` (≈0.30%). **Not traded in v1** | [VERIFIED-DOC FEE_PROGRAM_README; VERIFIED-SEARCH blofin] |
| Where fees go (v2) | — | — | LP fee → reserves. Protocol + creator fees → stay in the quote vault (recorded) until swept. Buyback fee = part of the protocol fee. **Pricing must subtract unswept fees if the program does** | [VERIFIED-DOC TRADE_V2]; subtraction [UNVERIFIED, T6] |
| Base fee | 5,000 lamports/signature | same | Same. Paid by landed failures. $0 if a bundle isn't included | [VERIFIED-SEARCH solana.com] |
| Priority fee | CU price × limit | same | `ceil(price × requested limit ÷ 1e6)`, charged on the **requested** limit. Paper uses the same limit the builder requests | [VERIFIED-SEARCH solana.com fee-structure] |
| Tips | Jito ≥1,000; Helius ≥5,000 lamports | Jito ≥1,000; Max ≥0.001 SOL | Jito ≥1,000 lamports; Sender SWQoS-only ≥0.000005 SOL; Max ≥0.001 SOL. Paid only if the transaction succeeds | [VERIFIED-SEARCH helius]; "only if success" [UNVERIFIED] |
| Token-account deposit | 0.00203928 SOL | ~0.002 | 0.00203928 SOL, refunded when the final sell closes the account | [VERIFIED-SEARCH QNT S27] |
| API fee | — | 0 (route A) | 0 | design |
| Signing fee | — | — | Whatever security picks. Must be ≤$0.01/signature | [VERIFIED-SEARCH SEC] |
| Same-block ordering | — | — | **Last** among same-direction trades in our landing block (QNT-2) | design |

### 1c. Cost per trade, one buy + one sell (SOL; USD at ~$100/SOL [VERIFIED-SEARCH mexc ≈$101.7 on Oct 15 2026])
**Assumptions [UNVERIFIED]:** pool holds 85 SOL; first fee tier.
- **Calm buy** (Jito bundle-only): base 0.000005 + priority 0.00002 + tip 0.0001 = **0.000125 SOL**. The priority fee is low because we request a tight compute limit; the scheduler ranks by fee per unit of cost [VERIFIED-SEARCH solana.com].
- **Calm sell** (Jito + SWQoS-only): base 0.000005 + priority 0.0001 + tips 0.000105 = **0.00021 SOL**.
- **Crash sell:** 2 failed-but-landed attempts at 0.001005 each + 1 success at 0.002005 ≈ **0.004 SOL**.
- **Price impact vs mid price:** ≈ 2 × size ÷ 85.

| | 0.05 SOL (risk Phase 1) | 0.1 SOL | 0.5 SOL | 2 SOL |
|---|---|---|---|---|
| Fixed tx costs, calm | 0.00034 | 0.00034 | 0.00034 | 0.00034 |
| PumpSwap fee 2 × 1.25% | 0.00125 | 0.0025 | 0.0125 | 0.05 |
| Price impact | 0.00006 | 0.00024 | 0.0059 | 0.094 |
| **Total, calm** | **0.0016 (3.3%) $0.16** | **0.0031 (3.1%) $0.31** | **0.0187 (3.7%) $1.87** | **0.144 (7.2%) $14.44** |
| **Total, crash exit** (fixed 0.0041) | **0.0054 (10.8%) $0.54** | **0.0068 (6.8%) $0.68** | **0.0225 (4.5%) $2.25** | **≥0.148 (≥7.4%) $14.82**; more, since a crash shrinks the pool |
| If the account is left open | +4.1% | +2.0% | +0.4% | +0.1% |
| If Turnkey pay-as-you-go (2–4 signatures) | +4–8% | +2–4% | +0.4–0.8% | +0.1–0.2% |
| Take-profit ladder (+2 calm sells) | +0.8% | +0.4% | +0.08% | ~0 |
| Pessimistic sandwich (2% margin × 10% hit rate) [UNVERIFIED, P14] | +0.2% of sell | same | same | same |
| If we raced at graduation (not proposed) | contested tip 0.005–0.05 SOL [UNVERIFIED, P4] = +10–100% | +5–50% | +1–10% | +0.25–2.5% |

**Reading:** the floor is ~3% per round trip, and 2.5 points of it is Pump's fee, which no route avoids. Fixed costs only matter below ~0.25 SOL or in a crash. Above ~1.3 SOL, our own price impact dominates.

### 1d. Paper fill model, now competition-aware (PREMISE-3, QNT-1, QNT-2)
1. **Landing block** = trigger block + our measured detect → decide → sign → send delay. Until measured: 3–8 blocks for entries, with a long tail [UNVERIFIED]. Short fuse: if not landed within 10 blocks, the buy expires and counts as a **miss**.
2. **Bundle-only buys** land only in blocks led by a Jito-running validator. The leader schedule and client type are recorded per slot.
3. **Competition:** in the landing block, count the trades on this pool, **including failed ones**, and their fee per compute unit and Jito tips. We go after every same-direction trade (QNT-2). If ≥3 competing buys outbid our tip cap, landing probability = p_contested (start at 20%); otherwise p_calm (start at 95%) [UNVERIFIED; canary calibrates].
4. Apply min-out **after** that ordering. Failures are charged per the §1b fee rules.
5. Every report shows P&L three ways: as simulated; **counting every contested coin as missed**; and in the canary, "paper filled, live failed" coins separately.

---

## 2. The big fork: race at graduation or not?

**Answer: no.** The honest numbers:

| | Leaders | **Us, Tier 0 (proposed)** | Us, Tier 1 (paid speed) |
|---|---|---|---|
| What it is | Complete, migrate and buy in **one transaction** (synthetic migration allows a buy with no size limit [VERIFIED-DOC README]). Shreds, co-location | Frankfurt/Amsterdam VPS, data team's gRPC at processed, pre-armed checks, hosted signer, Jito + Sender (free) | + Helius Professional/LaserStream **$999/mo** + Shreds **$800–1,000/mo per IP** [VERIFIED-SEARCH helius.dev/docs/billing/plans] + bare metal ~$300 [UNVERIFIED] + local or KMS signing |
| Where we land after pool open | block 0 (they *are* the opening trade) | **3–8 blocks behind ≈ 0.6–1.8 s** (gRPC ~1–2 blocks, signing 50–250 ms, landing 1–2 blocks, +1–2 if confirmed-only) [UNVERIFIED, T7/P4] | 1–3 blocks behind. Shreds give a 50–200 ms head start [VERIFIED-SEARCH rpcfast, vendor blog] |
| Extra $/month | $5,000+ [UNVERIFIED] | ≈ $0 | ≈ $2,100–2,300 |
| Extra per trade (600 trades/mo, 0.5 SOL position) | — | ~0.0003 SOL (tips only) | infra $3.5–3.8 + contested tips $0.5–5 = **+8–17% of the position** |
| Win rate in contested first-3-block auctions | ~all | **<10%** [UNVERIFIED estimate] | 20–40% [UNVERIFIED estimate] |

**Why not:**
- Migration is a one-block race [VERIFIED-SEARCH rpcfast]. A small set of MEV-driven actors pays most of the tips on PumpSwap and Pump.fun [VERIFIED-SEARCH pineanalytics].
- First-block launch snipers sell 85% within 5 minutes (data from launches, not migrations) [VERIFIED-SEARCH pine, via red-team].
- Even a 100% win rate pays only if blocks 1–3 beat a calm entry by **more than ~10% per trade, net**. Racing at 5+ SOL would cut infra to under 1% per trade, but in an 85 SOL pool that size costs ~12% in round-trip impact.

**What would change my mind:** test P1/E1 (below) shows entries in blocks 1–3 beat the cooled entry by >10% net per trade on the null baseline. Meanwhile a **shadow racer** in paper mode logs the block we would have reached, so the cost of not racing is measured, not guessed.

---

## 3. Challenges to other areas (3)

1. **Risk-manager.** Adopt the margin-and-chase sell model in place of the 3/8/15/30% ladder (SEAM-11). Set the live minimum position at 0.25 SOL, no ladder below 0.5 SOL, and a maximum of 1.5% of the pool's SOL reserve. Replace chunked emergency sells with one sell at a computed min-out (RSK-7). Fund the 0.01 SOL exit reserve per position from the fee reserve.
2. **Security-engineer.**
   - The signer must meet **p99 ≤150 ms and ≤$0.01 per signature**. At our size this rules out Turnkey pay-as-you-go.
   - The guard must pin PumpSwap accounts **by name** (`user`, `user_base_token_account`, `user_quote_token_account`, `pool`), not only check programs.
   - Approve or reject, in writing: (a) the fixed sell template under a sell-only credential that STOP does not revoke, and (b) rolling exit tickets. A stolen ticket can only sell our coin into our own account at a tight min-out within 30 s; the worst case is an early exit plus at most margin m.
3. **Data-engineer + quant-tester.**
   - The recorder must keep **failed** PumpSwap transactions on watched pools (Yellowstone has a `failed` filter [VERIFIED-DOC, DAT Y1]), each slot's leader and its client type, and Jito tip transfers. Without these the competition-aware fill model (§1d) can't be built, and PREMISE-3 stays open.
   - T6 must explicitly test the v2 "fees kept in the vault" accounting and a trade that crosses the 420 SOL tier.

---

## 4. Edge hunt

**E1. "Let the auction clear, then buy cheaply" (timing and cost, not speed).**
- *What rivals lack:* an on-chain **"auction cooled" signal** from our own recorder. It uses failed buys, Jito tips and compute-unit prices in the pool's last N blocks; retail apps don't show failed transactions. Racers pay big tips to buy at a price the completing buy has already pushed up, then dump. Retail-app traders pay app fees of roughly 1% per side [UNVERIFIED; test X8].
- *Why we'd win:* we buy after the racers' selling, at calm fees (~0.0003 SOL per round trip vs 0.005–0.05 SOL for racers), with near-certain landing. A round trip costs ~3.1–3.7% against roughly 5–6% for app traders on the same coin [UNVERIFIED]. Losing less is an edge.
- *Cost:* $0. It's a rule plus recorder fields.
- *Copying:* the idea is easy to copy. If the "cooled" moment gets crowded, our own competition metric shows it, and we still pay calm fees or skip.
- *Kill test (pre-registered):* 500 post-BOOST canonical graduations on the tape, all with the same exits and the §1b/§1c costs. Compare: (i) a cooled entry, at the first block where the last 10 blocks show ≤1 failed buy and a max tip ≤ the network p75; (ii) fixed entries at 60/300/330/600 s; (iii) block-1 entry with racing costs; (iv) the null baseline. **PASS** if (i) beats the best of (ii) by **≥1.0% per trade** and beats zero, with a 90% bootstrap confidence interval above zero, and still holds with the top 5% of trades removed. Otherwise **KILL**.

**E2. Crash exits without the sandwich tax.**
- *What rivals lack:* re-quoting every 2 blocks with a tight min-out, a pre-built (or pre-signed) sell ready to fire, and two protected send paths. Typical stop orders use fixed wide slippage; Jupiter's trigger orders default to 20% [VERIFIED-SEARCH, RSK §2].
- *Why we'd win:* a wide-slippage sell can lose up to the tolerance to a sandwich, or wait. Ours can lose at most m, and it fires 1–2 blocks sooner because only signing remains.
- *Cost:* ≈0.004 SOL per crash exit (1.6% at 0.25 SOL). $0 per month.
- *Copying:* a skilled bot can copy it. App users can't set this up.
- *Kill test:*
  - (a) P14 on the tape or Dune: sandwich rate and loss on PumpSwap sells, grouped by **implied tolerance** = (quote − min_out) ÷ quote, decoded from instruction data. **PASS** if sells at ≤3% tolerance lose <0.2% on average while sells at ≥15% lose ≥1%.
  - (b) Replay 200 recorded crashes (−30% within 20 blocks) with our measured latency and landing model. Compare the chase against one-shot 20% and 30% slippage sells. **PASS** if the chase's median proceeds beat the one-shot by ≥1.5% of the position after attempt fees. **KILL** if the price runs away faster than we re-quote.

**E3. Sell into scheduled buying (BOOST).**
- *What rivals lack:* attention to the timing of protocol-scheduled buy flow. BOOST buys ~17.6 SOL over 5 minutes after migration as a TWAP (time-spread buying), and burns the tokens [VERIFIED-SEARCH kucoin, cryptobriefing]. Most exits fire on price alone.
- *Why we'd win:* if BOOST's buy times are predictable, a non-urgent exit (take-profit, time exit) placed in the first block **after** a BOOST buy sells at a briefly higher price into a deeper pool. One 0.5 SOL tranche into ~90 SOL lifts the price ~1.1% [UNVERIFIED arithmetic].
- *Cost:* $0.
- *Copying:* easy once noticed. Fast actors already front-run BOOST [VERIFIED-SEARCH onchaindivers, single source], so the bump may already be gone.
- *Kill test:* identify BOOST transactions on the tape. **PASS** only if (1) ≥80% of the next BOOST buys are predictable within ±2 blocks; (2) the mean price is higher in the 1–3 blocks after a BOOST buy than in the block before; and (3) in simulation, "first block after a BOOST buy" beats "the trigger block" by **≥0.5% per exit** after costs, with a wait of ≤5 blocks. Otherwise **KILL**. The same machinery serves "first out when sells reopen" (EXE-5).

---

## 5. Revised recommendation
1. **Don't race at graduation in v1.** Entries happen after the auction clears (E1). Speed money goes only to exits, and that is nearly free: Jito, Helius Sender and Nozomi charge per transaction, not per month. Execution infrastructure costs **≈$0–25/month**.
2. **Route:** direct PumpSwap instructions from our own **IDL-generated builder**, with our own token accounts pinned. The npm SDK serves only as a local quote cross-check for buys. **Jupiter is never signed in v1.**
3. **Landing:** buys go Jito bundle-only, one shot, short fuse, buy margin ≤3%. Sells are one signed transaction sent to Jito (dontfront) and Helius SWQoS-only (mev-protect), re-quoted every 2 blocks with a tight margin (≤15%), escalating to Sender Max after 2 failures, with a 0.01 SOL exit reserve per position.
4. **Costs (settled with quant):** 1.25% per side. A round trip costs 3.1–3.7% calm and 4.5–6.8% in a crash at 0.1–0.5 SOL. Live minimum position 0.25 SOL, maximum 1.5% of the pool. The final sell closes the token account. The signer costs ≤$0.01 per signature.
5. **Paper:** competition-aware landing, our trade last in its block, fees from the shared module, P&L shown three ways. No landing rate enters the go-live gate until measured.

## Tests to run once allowed (read-only)
| # | Test | Domain |
|---|---|---|
| X1 | Poll the tip floor for 7 days. Confirm that a failed or uncled bundle pays nothing. Collect winning tips in migration blocks (= P4) | `bundles.jito.wtf`, `docs.jito.wtf`, `explorer.jito.wtf` |
| X2 | Compute units actually used by `buy_v2`, `sell_v2` and `buy_exact_quote_in_v2` across 200 transactions (sets the tight limit) | RPC host (`mainnet.helius-rpc.com` or `api.mainnet-beta.solana.com`) |
| X3 | Short fuse: `getLatestBlockhash` and `getBlockHeight` sampling. How reliably is a blockhash ~140 blocks old still accepted? Read-only check of `lastValidBlockHeight` versus current height | RPC host |
| X4 | Does `mev-protect` work in Max mode? Get Sender's tip-account list and regional endpoints | `www.helius.dev/docs` |
| X5 | Share of failed transactions per block on pools in their first 5 minutes (feeds §1d) | gRPC provider (`failed` filter), RPC host |
| X6 | Is the raw vault balance minus `protocol_fees` and `creator_fees` the reserve the program actually prices with? (part of T6) | RPC host |
| X7 | BOOST transaction identification and timing regularity (E3) | RPC host, `dune.com` |
| X8 | Per-trade fees of retail trading apps (for E1's comparison) | `gmgn.ai`, `axiom.trade`, `photon-sol.tinyastro.io` [UNVERIFIED host] |

## Sources
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/FEE_PROGRAM_README.md · https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/PUMP_SWAP_TRADE_V2.md · https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md (all re-read 2026-11-04)
- [VERIFIED-SEARCH] Helius Sender tiers and mev-protect: https://www.helius.dev/docs/sending-transactions/sender-swqos-only · https://www.helius.dev/docs/trading/overview
- [VERIFIED-SEARCH] Fee tiers: https://trojan.com/blog/how-pump-fun-works · https://blofin.com/academy/education/pumpfun/pumpswap-canonical-pool-ownership · https://blofin.com/academy/education/pumpfun/pumpswap-canonical-vs-non-canonical-pools · https://www.benzinga.com/content/47482176/new-pump-fun-fee-structure-pays-creators-more-than-twitch-generates-2-1m-in-24-hours · https://solanafloor.com/news/pump-funs-new-creator-fee-model-pays-2m-24-hours
- [VERIFIED-SEARCH] 200 ms slots, 30 s blockhash: https://solanacompass.com/news/solanas-200ms-slot-time-is-live-on-mainnet-at-epoch-1053-completing-simd-0525 · https://www.kucoin.com/news/flash/solana-doubles-block-speed-to-200ms-eyes-alpenglow-upgrade
- [VERIFIED-SEARCH] Priority fee and scheduler ranking: https://solana.com/docs/core/fees/fee-structure.md · https://solana.com/docs/core/fees/compute-budget.md
- [VERIFIED-SEARCH] Tip floor endpoint and an Apr 2026 snapshot (p95 0.00089 SOL): https://quicknode.com/docs/solana/getTipFloor · https://dev.to/sai_93caeceb4f6a4d9969910/jito-bundle-tip-calculator-closed-form-break-even-for-solana-mev-defense-3c1b
- [VERIFIED-SEARCH] Migration race and ShredStream head start (vendor blogs): https://rpcfast.com/blog/how-to-launches-snipe-pump · https://rpcfast.com/blog/complete-stack-competitive-solana-sniper-bots · https://pineanalytics.substack.com/p/jitos-role-in-solana-deep-dive
- [VERIFIED-SEARCH] Helius plan and Shreds prices: https://www.helius.dev/docs/billing/plans · https://www.helius.dev/pricing
- [VERIFIED-SEARCH] BOOST: https://www.kucoin.com/blog/pump-fun-boost-mode-explained · https://cryptobriefing.com/pump-fun-launches-boost-mode-to-recycle-dead-liquidity-through-token-burns/ · https://onchaindivers.substack.com/p/the-176-sol-ghost-reverse-engineering
- [VERIFIED-SEARCH] SOL price (≈$101.7, Oct 15 2026): https://www.mexc.com/hu-HU/price/SOL
- Round 1 sources for jitodontfront, Sender credits, the Jito minimum tip and the PumpSwap IDL are in `team-debate/round1/execution-engineer.md`.
