# The shared fee and price model

## In plain English (for Paul)
- This is the one rulebook for "what does a trade really cost, and what price do we really get". The paper simulator, the backtests, the strategy and the guard all use it, so they can never disagree.
- On a freshly graduated coin, Pump.fun takes **1.25% each way**, falling to **1.20%** once the coin is worth about 420 SOL. We read this from Pump's own files and the live on-chain setting, and we watch dozens of settings Pump can change without warning.
- A full buy and sell costs about **3.0–3.7% of the bet in calm conditions** (0.1–0.5 SOL) and about **3.4–6.2% in a crash**, on top of the market's own fall. The extra fall while a crash sell keeps retrying is added on top by the simulator.
- Before paper results count, our maths must reproduce real past trades to the last unit **and predict exactly which trades fail**. This test (T6) now has two parts: T6a on past data before recording starts, and T6b on our own recordings before any "final exam" result counts.
- Version 1.1 fixes two traps found by red-team: a sell never also closes the coin account (a stranger could block it with 1 token of dust), and on "boosted" pools the bot checks the pool can really pay before it sells.

**Status:** fee-model **v1.1**, 2026-11-05 (v1.0 the same day, revised after red-team's Phase 0 review, `team-debate/phase0/red-team-phase0-review.md` §2; the changes are listed in §12). Owner: execution-engineer. Consumers: `sim/`, `research/`, `strategy/`, `guard/`, `fees/` (DESIGN §7). This is a specification, not code. It contains no signing or sending logic.

**Tags.**
- **[VERIFIED-DOC]**: primary source read this session, with its URL (full list in §11).
- **[VERIFIED-SEARCH]**: seen in search results only.
- **[UNVERIFIED]**: our inference, with the test that settles it.
- **[DERIVED]**: our arithmetic on tagged inputs.

**What changed since DESIGN §5b:**
- The fee tier table is now read from Pump's own image (`docs/fees.png`) **and** from a byte capture of the live mainnet fee account that ships with Pump's official SDK. I decoded the bytes myself and they match (§2a).
- Token-account rent is **no longer a fixed 0.00203928 SOL**: Solana is cutting rent in steps (SIMD-0437, §2d).
- New pump coins are Token-2022 coins.

---

## 0. The answer in one table

One buy plus one sell, the buy at a **calm, fresh-graduate pool** (85 SOL effective quote reserve, 206.9M tokens, fee tier 0 = 1.25%/side). SOL = $100 [VERIFIED-SEARCH, DESIGN §5b, mexc, Oct 2026]. Full workings are in §5.

| Stake | Calm exit (price unchanged) | Crash exit (price −30%, escalated sell) | DESIGN §5b said (calm / crash) |
|---|---|---|---|
| **0.1 SOL** | 0.00304 SOL = **3.04%** = $0.30 | 0.00616 SOL = **6.16%** = $0.62 | 3.1% / 6.8% (EXE-R §1c) |
| **0.25 SOL** | 0.00792 SOL = **3.17%** = $0.79 | 0.00971 SOL = **3.89%** = $0.97 | 3.22% / 4.93% |
| **0.5 SOL** | 0.01829 SOL = **3.66%** = $1.83 | 0.01707 SOL = **3.41%** = $1.71 | 3.75% / 4.70% |

- These costs come **on top of** the market move. The −30% fall itself is the trade's result, not a cost.
- **Included since v1.1:** the separate clean-up transaction that closes the empty coin account after the sell (6,000 lamports; §6 rule 11, FM-1).
- **Excluded: chase slippage.** In a crash, the price can keep falling while the sell retries (arrival delay, plus a margin of up to 15%). That is a real execution loss. It is not in this table; the simulator adds it from the replayed tape (§6 rule 14, FM-8).
- The crash column is lower than DESIGN's because, after a fall, the sell is worth less, so the percentage fees on the sell are smaller. DESIGN §5b charged every sell-side cost at the full stake. **This must never be used to loosen any limit, margin or stop** (FM-8): it leaves out chase slippage, which can be larger than the whole difference.
- DESIGN's figures stay a valid **conservative planning envelope**. The simulator uses this document's exact per-trade maths instead (§9).

---

## 1. Sources read this session (2026-11-05)
- **Pump.fun's official docs and IDLs** (`github.com/pump-fun/pump-public-docs`, main branch), fetched through `raw.githubusercontent.com`: README, PUMP_SWAP_README, FEE_PROGRAM_README **and its tier image `docs/fees.png` (read as an image)**, NEGATIVE_VIRTUAL_QUOTE_RESERVES, VIRTUAL_QUOTE_RESERVES_FEE_ADJUSTMENT, PUMP_SWAP_TRADE_V2, SWEEP_FEES, FEE_RECIPIENTS, SYNTHETIC_MIGRATION, HOLDER_REWARDS_README, PUMP_SWAP_CREATOR_FEE_README, MULTI_HOP_SWAP, FAQ, and the IDLs `pump_amm.json`, `pump_fees.json`, `pump.json`.
- **Pump's official SDK source**, `@pump-fun/pump-swap-sdk` 2.1.0, the version the README names. It was downloaded from `registry.npmjs.org`, its sha512 matched the registry's published hash, and it was only read, never run. Files read: `src/sdk/fees.ts`, `util.ts`, `buy.ts`, `sell.ts`, `multiHop.ts`, `offlinePumpAmm.ts`, and the tests `feeConfigMainnetFixture.ts`, `boost.spec.ts` and `buyQuoteSimulation.spec.ts`.
  - Pump's FEE_PROGRAM_README names this SDK as the reference for the fee logic.
  - The SDK comments cite the matching Rust functions ("rust reference: pump-fees-math::calculate_fee_tier()", "pump-amm trade_v2 sell_amounts()", and others).
- **Solana's own fee and rent rules**, from source on GitHub:
  - the Solana docs page `fee-structure.mdx` (solana-foundation/solana-com repo);
  - Agave `compute-budget/src/compute_budget_limits.rs` and `fee/src/lib.rs`;
  - `solana-sdk/rent/src/lib.rs`;
  - Agave `feature-set/src/lib.rs`.
- **Blocked or unavailable this session:** `solana.com` (WebFetch: host not resolvable); `api.github.com` (403); the `gh` CLI (repo not enabled). Jito's and Helius's own docs were not fetched; their figures are [VERIFIED-SEARCH].
- **Added for v1.1 (read from the shell through `raw.githubusercontent.com` and `registry.npmjs.org`, never run):**
  - the pinned IDLs in `phase0/scripts/idl/` (same SHA-256 as `PINNED.json`): error texts, `Pool` field docs, BOOST events, the admin instructions of §8a;
  - the SDK again: `fees.ts` (`SOL_LIKE_QUOTE_MINTS`), `sell.ts` (`sellAmounts`, the 6063 check), `boost.spec.ts` (how σ, vqr and the fee buckets relate);
  - Agave `svm/src/transaction_processor.rs` (inner instructions are recorded whatever the result), `program-runtime/src/execution_budget.rs` and `compute-budget-instruction/src/compute_budget_instruction_details.rs` (default compute limit), `fee/src/lib.rs` (signature count);
  - SPL Token and Token-2022 `processor.rs`, `error.rs` and `instruction.rs` (close fails on a non-zero balance; anyone can transfer in).

---

## 2. Every cost component of one trade

| # | Component | Amount / formula | Who receives it | Refunded? | Source |
|---|---|---|---|---|---|
| 1 | **LP fee** | `ceil(amount × lp_bps ÷ 10,000)`; tier 0: 2 bps, tiers 1+: 20 bps | Stays in the pool reserves | No | [VERIFIED-DOC fees.ts, util.ts `fee()`, TRADE_V2 "goes into the pool reserves on every trade"] |
| 2 | **Protocol fee** | `ceil(amount × protocol_bps ÷ 10,000)`; tier 0: 93 bps, tiers 1+: 5 bps | Pump.fun. A "buyback" slice of it goes to one of 8 buyback recipients | No | [VERIFIED-DOC same; buyback slice: TRADE_V2, SWEEP_FEES] |
| 3 | **Creator fee** | `ceil(amount × creator_bps ÷ 10,000)`; tier 0: 30 bps, tier 1: 95 bps, falling to 5 bps; **0 if `Pool.coin_creator` is the default key** | Coin creator vault, or a fee-sharing config, or the coin's holders (holder-rewards coins), or the buyer as cashback (old cashback coins) | No (cashback and holder rewards are rebates we **count as 0**) | [VERIFIED-DOC buy.ts/sell.ts, HOLDER_REWARDS_README] |
| 4 | **Network base fee** | 5,000 lamports × signatures (our transactions have 1) | 50% burned, 50% to the block's validator | No. **Paid even if the transaction fails** | [VERIFIED-DOC fee-structure.mdx; agave fee/src/lib.rs] |
| 5 | **Priority fee** | `ceil(cu_price_micro_lamports × cu_limit_requested ÷ 1,000,000)`, on the **requested** limit, not the units used | 100% to the validator | No. **Paid even if the transaction fails** | [VERIFIED-DOC compute_budget_limits.rs `get_prioritization_fee`; fee-structure.mdx] |
| 6 | **Jito tip** | Our choice: a transfer instruction inside the transaction; calm 100,000 lamports (DESIGN) | Jito tip account | No. Not paid if the transaction fails or a bundle is dropped | Minimum: Helius docs say 1,000 lamports on one page and 5,000 on another [VERIFIED-SEARCH, conflicting]. "Not paid on failure" [UNVERIFIED: test FC6] |
| 7 | **Helius Sender tip** | SWQoS-only minimum 5,000 lamports; Sender Max minimum 1,000,000 lamports (0.001 SOL). Sender also requires a compute-price instruction | Helius tip account | Same as 6 | [VERIFIED-SEARCH helius.dev sender-swqos-only] |
| 8 | **Price impact** | Constant-product maths (§3). Not a fee, but a real cost against the spot price | The pool (and later traders) | No | [VERIFIED-DOC formulas §3] |
| 9 | **Our token account (deposit)** | `(128 + data_len) × lamports_per_byte`. 165 bytes (classic SPL) or about 170 bytes (Token-2022 account with the ImmutableOwner extension) | Locked in our own account | **Yes, in full**, when the **separate clean-up transaction** (row 17) closes the account. Never inside a sell (FM-1) | Formula and constants [VERIFIED-DOC solana-sdk rent]. Token-2022 size [UNVERIFIED: FC5] |
| 10 | **wSOL account deposit** | One deposit, once (a persistent account, DESIGN #7) | Locked in our own account | Yes, if ever closed | as 9 |
| 11 | **`user_volume_accumulator`** | Created by PumpSwap on our wallet's first trade if missing, paid by us. About 90 bytes ≈ 0.0015 SOL at 6,960 lamports/byte. **Once per wallet** | Locked in the PDA | Yes, via `close_user_volume_accumulator` | Created-if-missing [VERIFIED-DOC TRADE_V2 #13]. Size [DERIVED from the IDL, UNVERIFIED: FC8] |
| 12 | **Pool layout top-up** | A few lamports, only on pools older than the latest appended fields. Fresh graduates: 0 | The pool | No | [VERIFIED-DOC TRADE_V2 #1] |
| 13 | **Failed attempts** | Base + priority per **landed** failure. 0 for a dropped bundle or an expired transaction. A sell the guard already predicts will fail with 6063 is never sent, so it costs 0 (§3a) | Validator | No | [VERIFIED-DOC fee doc]; bundle part [VERIFIED-SEARCH via A-039] |
| 14 | **Signer** | AWS KMS, $0.15 per 10,000 asymmetric signs ≈ $0.000015 per signature | AWS | No | [VERIFIED-SEARCH, A-065] |
| 15 | **API / route fee** | 0. We build PumpSwap instructions directly, with no aggregator | none | n/a | design (DESIGN #7) |
| 16 | **Sandwich allowance** (an expectation, not a fee) | Base view: crash sells 0.2% of sell proceeds (2% margin × 10% hit rate), other trades 0. **Pessimistic view: also 0.1 × m on every trade sent outside a Jito bundle**, until P14 measures it (PR-14a) | Attacker | No | [UNVERIFIED, P14; DESIGN §5b] |
| 17 | **Clean-up transaction** (new in v1.1, FM-1) | One extra transaction after the final sell: burn any dust, close the empty token account. 5,000 base + priority (paper fallback 1,000) = **6,000 lamports**; pessimistic view 12,000 (one dusted failure) | Validator | No, but it releases row 9's deposit | Close fails on a non-zero balance [VERIFIED-DOC SPL Token and Token-2022 `process_close_account`: `NonNativeHasBalance`, error 11]. Compute use [UNVERIFIED: X2] |

### 2a. The PumpSwap fee table (canonical, SOL-quoted pools)

**How a pool's fee schedule is chosen** [VERIFIED-DOC fees.ts `feesForQuoteMint`; FEE_PROGRAM_README]:
- **Non-canonical pool:** `flat_fees`. In the capture these are lp 25 / protocol 5 / creator 0. We do **not trade** non-canonical pools in v1.
- **Canonical pool** (`Pool.creator` = the Pump PDA `["pool-authority", base_mint]` of program `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`), by quote mint:
  - SOL-like quote: `fee_tiers`, chosen by market cap. **"SOL-like" means exactly three mints:** the default key `11111111111111111111111111111111` (what legacy curves store for SOL), wrapped SOL `So11111111111111111111111111111111111111112`, and the Token-2022 native mint `9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP` [VERIFIED-DOC SDK `fees.ts` `SOL_LIKE_QUOTE_MINTS` and its test in `fees.spec.ts`] (FM-9.2).
    - **Pricing** uses the SOL tiers for all three, because the chain does.
    - **Trading scope** (prereg U0, "wrapped SOL") is wSOL-quoted pools only. Pools quoted in the Token-2022 native mint or the default key are priced correctly but not traded, and are listed by name in the daily exclusion report. So prereg U0 and this file agree.
  - USDC: `stable_fee_tiers`;
  - any other quote: `exotic_flat_fees`, or `flat_fees` while those are all zero.
- **Per-pool creator rate:** if `GlobalConfig.creator_fee_configurable` is on and `Pool.creator_fee_bps > 0`, that rate replaces the tier's creator rate. Pump says this never applies to SOL- or USDC-quoted coins (error 6077 `CreatorFeeNotConfigurableForQuote`) [VERIFIED-DOC pump_amm.json errors; PUMP_SWAP_README].

**The SOL tier table.**
- Pump's README publishes it only as an image, which we read directly this session [VERIFIED-DOC docs/fees.png].
- The exact integer values come from the live mainnet `FeeConfig` account `5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx`, **captured at slot 445186127 on 2026-09-08**. The capture ships in the official SDK (`src/__tests__/feeConfigMainnetFixture.ts`).
- I decoded those 4,073 bytes myself with shell tools, and every row below matches the SDK's own reading [VERIFIED-DOC, decoded this session].
- The image rounds some creator rates (it shows 0.275%; the chain holds 28 bps), so **the chain values rule**. The live account must be re-read (test FC1), because the admin can change it at any time (§8).

| Tier | Market cap from (SOL) | LP bps | Protocol bps | Creator bps | **Total / side** |
|---|---|---|---|---|---|
| 0 | 0 | 2 | 93 | 30 | **1.25%** |
| 1 | 420 | 20 | 5 | 95 | **1.20%** |
| 2 | 1,470 | 20 | 5 | 90 | 1.15% |
| 3 | 2,460 | 20 | 5 | 85 | 1.10% |
| 4 | 3,440 | 20 | 5 | 80 | 1.05% |
| 5 | 4,420 | 20 | 5 | 75 | 1.00% |
| 6 | 9,820 | 20 | 5 | 70 | 0.95% |
| 7–24 | 14,740 → 98,240 | 20 | 5 | 65, 60, 55, 50, 45, 40, 35, 30, 28, 25, 23, 20, 18, 15, 13, 10, 8, 5 | 0.90% → 0.30% |

- Full thresholds for tiers 7–24, in SOL: 14,740; 19,650; 24,560; 29,470; 34,380; 39,300; 44,210; 49,120; 54,030; 58,940; 63,860; 68,770; 73,681; 78,590; 83,500; 88,400; 93,330; 98,240.
- On chain they are stored in lamports (× 10⁹) as `u128`.
- The bonding curve's own row in the image is creator 0.30% / protocol 0.95% / LP 0% = 1.25%. It is irrelevant after migration.

**This settles the Round 2 fee-split dispute.** At tier 0, the 1.25% is LP 0.02 / protocol 0.93 / creator 0.30. The "20 + 5 bps" figure is the old `GlobalConfig` fallback, which is no longer used: the SDK notes that "pump-fees is mandatory" [VERIFIED-DOC fees.ts comment].

**Why the 420 SOL boundary matters to us.**
- A typical pool opens at about 85 SOL and 206.9M tokens, a market cap of **≈ 411 SOL**: just under tier 1 [DERIVED from UNVERIFIED curve constants; FC3 reads Pump's `Global`].
- After about 17.6 SOL of BOOST buying (with the tokens burned), our illustrative pool sits near **577 SOL, which is tier 1 (1.20%)** [DERIVED, UNVERIFIED].
- So many trades near our entry time sit close to the boundary. A position can pay 1.25% to enter and 1.20% to exit, or the reverse.
- **The tier is chosen from the pool state just before the trade** [VERIFIED-DOC fees.ts/buy.ts/sell.ts: `computeFeesBps` receives the pre-trade reserves; on-chain behaviour checked by T6].

**The buyback slice.**
- `GlobalConfig.buyback_basis_points` sets a slice of the protocol fee that is paid out in the trade to a buyback recipient, even on v2 trades. It is **inside** the protocol fee, not extra [VERIFIED-DOC TRADE_V2, SWEEP_FEES: "The buyback part of the protocol fee is still paid in the trade"].
- Its exact formula (a share of `protocol_fee`, or of the trade amount) and its rounding are [UNVERIFIED: FC7]. It does not change our total cost, only where the money goes.
- **Warning:** the SDK's own on-chain test deliberately uses USDC pools "to avoid the SOL-only buyback fee path, so the SDK's predicted base out should match the on-chain BuyEvent exactly" [VERIFIED-DOC buyQuoteSimulation.spec.ts]. That implies the SDK may **not** match the chain exactly on SOL pools. T6 must have a SOL-pool v1-buy stratum (§7).

### 2b. v2 trades: "fees kept in the pool"
[VERIFIED-DOC PUMP_SWAP_TRADE_V2, SWEEP_FEES, VIRTUAL_QUOTE_RESERVES_FEE_ADJUSTMENT, NEGATIVE_VIRTUAL_QUOTE_RESERVES]
- `buy_v2`, `buy_exact_quote_in_v2`, `sell_v2` and `multi_hop_swap` **do not pay out** the protocol and creator fees. The money stays in the pool's quote vault and is recorded in `Pool.protocol_fees` and `Pool.creator_fees`.
- The program subtracts the same amount from `Pool.virtual_quote_reserves`, so the waiting fees never count as liquidity. That is why that field can be **negative**.
- Anyone can pay the fees out later (`sweep_protocol_fee`, `sweep_creator_fee`). A sweep lowers the vault and raises `virtual_quote_reserves` by the same amount, so the price does not move.
- **For our costs, nothing changes:** "Prices, slippage checks and fee amounts are the same" as v1 [VERIFIED-DOC TRADE_V2].
- **It does change our arithmetic in four places:**
  1. Never treat the raw vault balance as liquidity.
  2. Sells are paid only from *real* reserves = vault − `protocol_fees` − `creator_fees`. A sell larger than that fails with 6063 `InsufficientRealQuoteReserves` [VERIFIED-DOC sell.ts `sellAmounts`; pump_amm.json errors]. On boosted pools this cap can bind well before the quoted price runs out; §3a says how pricing, the simulator and the guard handle it (FM-2).
  3. The two-witness balance check (§7) must expect the kept fees to stay in the vault.
  4. When reconstructing pool state from events, sweep events (`SweepPoolFeeEvent`, bucket 0 = protocol, 1 = creator) must be applied. Fees must not be counted as income twice.
- **Exceptions:**
  - Cashback-coin pools reject v2 with 6079 `CashbackCoinNotSupported`, so use v1 [VERIFIED-DOC].
  - **The docs contradict each other on mayhem pools.** TRADE_V2 says "Mayhem pools work too", but the IDL has error 6080 `MayhemPoolNotSupported`: "v2 trades do not support mayhem-mode pools; use the v1 instructions" [VERIFIED-DOC, both]. Until FC9 settles it, the module refuses to quote v2 on mayhem pools.

### 2c. Network fees and tips
- **Base fee:** 5,000 lamports per signature, half burned. Charged whether the transaction succeeds or fails [VERIFIED-DOC fee-structure.mdx: "Charged whether the transaction succeeds or fails"].
- **Priority fee:** `ceil(cu_price × cu_limit ÷ 10⁶)` lamports, on the requested limit [VERIFIED-DOC agave `get_prioritization_fee`]. So the builder asks for a tight limit (test X2 measures real usage). Paper charges the **same requested limit** the live builder would use.
- **When a transaction sets no limit** (many rival transactions don't), the runtime uses a default, and the priority fee is charged on that default (FM-9.3) [VERIFIED-DOC agave `compute_budget_instruction_details.rs` `calculate_default_compute_unit_limit`; `execution_budget.rs` constants]:
  - `L_default = 200,000 × (top-level instructions of non-builtin programs) + 3,000 × (top-level builtin instructions)`, capped at `1,400,000`;
  - compute-budget, System and the other builtin programs count at 3,000 each; a builtin that has been migrated to an ordinary program (its feature gate active) counts at 200,000;
  - a requested limit above 1,400,000 is cut to 1,400,000; no `SetComputeUnitPrice` means a priority fee of 0.
- **Base fee signatures** include precompile signatures: `5,000 × (transaction signatures + ed25519 + secp256k1 + secp256r1 precompile signatures)` [VERIFIED-DOC agave `fee/src/lib.rs` `calculate_signature_fee`]. Ours have exactly 1; rivals may have more.
- **New transaction format.** In Solana's new "v1" transaction format, the priority fee is a fixed lamport amount, not price × limit [VERIFIED-DOC fee-structure.mdx]. We send v0 transactions. If we ever switch, this formula changes (watched, §8).
- **Tips** are ordinary transfer instructions inside our transaction. If the transaction fails on-chain, all its instructions are undone except the fee, so the tip is not paid [inference from "fee is still charged" on failure; UNVERIFIED: FC6 checks real failed transactions]. A bundle that fails is not included at all and costs nothing [VERIFIED-SEARCH, A-039].
- **Default sender plan, from DESIGN #8 and EXE-R §1a/§1c** (these are levels we chose, all [UNVERIFIED] until P4/X1 data). **This is the one bid table the simulator loads** (PR-14c). Prereg §2.5's "bid fallbacks" (S6) charge no tip on buys and calm sells; where the two differ, this table rules, and prereg S6 should point here (request to the lead, §9).

| Leg | Base | Priority | Tips | Total (lamports) |
|---|---|---|---|---|
| Calm buy (Jito bundle-only) | 5,000 | 20,000 | Jito 100,000 | **125,000** |
| Calm sell (Jito + Sender SWQoS-only, one signature) | 5,000 | 100,000 | Jito 100,000 + Sender 5,000 | **210,000** |
| Crash sell: 2 landed failures at the 0.001 SOL rung, then success | 3 × 5,000 | 2 × 1,000,000 (failures) + 1,000,000 (success) | success only: ≈ 1,000,000 (Jito ≈ p95 + Sender) | **4,015,000** |
| Bad crash: 4 landed failures at the 0.002 SOL rung, then success | 5 × 5,000 | 4 × 2,000,000 + 2,000,000 | success only: 1,000,000 | **11,025,000** |
| **Clean-up** (new, FM-1): separate transaction after the final sell; plain sender, never urgent | 5,000 | 1,000 (fallback: limit 20,000 CU × 50,000 micro-lamports per CU, until X2) | none | **6,000** |

- In simulation, the priority amounts above are **floors**. In a contested slot the paper bid is the larger of the floor and prereg's dynamic level (p75 of the pool's landed same-direction priority fee per CU over 150 slots for buys and calm sells, p90 for emergency sells), within prereg's caps.
- The bad crash is the sensitivity case. It is meant to be capped by the 0.01 SOL exit reserve per position (EXE-2). **Found in the v1.1 re-read:** 11,025,000 lamports is about 0.001 SOL *above* that 10,000,000-lamport reserve, so in this case the reserve binds before the ladder ends. What the chase does when the reserve runs out is a risk-manager decision (§9); paper keeps charging the ladder as written, which is the costlier choice.

### 2d. Account rent (deposits), now a moving number
- **Formula:** rent-exempt minimum = `(128 + data_len) × lamports_per_byte` [VERIFIED-DOC solana-sdk rent: `ACCOUNT_STORAGE_OVERHEAD = 128`, `DEFAULT_LAMPORTS_PER_BYTE = 6,960` with the SIMD-0194 threshold of 1.0].
- **SIMD-0437 cuts `lamports_per_byte` in five feature-gated steps:** 6,960 → 6,333 → 5,080 → 2,575 → 1,322 → 696. A sixth gate can revert it to 6,960.
  - The step values and gate IDs are in Agave's source [VERIFIED-DOC feature-set/src/lib.rs].
  - Step 1 went live on mainnet on 2026-09-03. Step 2 is reported live by one source and "expected mid-September" by another [VERIFIED-SEARCH solana.com/upgrades/reduced-rent, docs.chainstack.com; **sources conflict**].
  - **The module never hard-codes rent.** It reads `getMinimumBalanceForRentExemption(len)` or the Rent sysvar.
- **New coins are Token-2022.** Pump's `create_v2` uses the Token-2022 program [VERIFIED-DOC pump.json `create_v2.token_program = TokenzQdBN…`]. An ATA (associated token account) for such a coin is about 170 bytes, not 165 [UNVERIFIED: FC5].

| lamports/byte | 165-byte account | 170-byte account | as % of a 0.1 / 0.25 / 0.5 SOL stake (170 B), **only if never closed** |
|---|---|---|---|
| 6,960 (old) | 2,039,280 | 2,074,080 | 2.07% / 0.83% / 0.41% |
| 6,333 (step 1) | 1,855,569 | 1,887,234 | 1.89% / 0.75% / 0.38% |
| 5,080 (step 2) | 1,488,440 | 1,513,840 | 1.51% / 0.61% / 0.30% |
| 696 (final) | 203,928 | 207,408 | 0.21% / 0.08% / 0.04% |

- **Refund rule.** Closing an account returns *all* its lamports, so we get back exactly what we deposited, even if rent fell in the meantime [VERIFIED-SEARCH: "Accounts funded before each step keep their extra lamports", Raydium/Chainstack docs].
- **v1.1 (FM-1): the token account is never closed inside a sell.** v1.0 followed DESIGN #8 / EXE-7 and closed the account in the final sell. Red-team showed that this lets a stranger make our crash sell fail:
  - a PumpSwap sell sells a *fixed* `base_amount_in` [VERIFIED-DOC pump_amm.json `sell` args];
  - anyone can send tokens to any token account: a transfer is authorised by the *sender* only, and the receiving account just has to be unfrozen and of the same mint [VERIFIED-DOC SPL Token `process_transfer`];
  - closing an account that still holds tokens fails with `NonNativeHasBalance` (error 11, "Non-native account can only be closed if its balance is zero"), in **both** SPL Token and Token-2022 [VERIFIED-DOC both `process_close_account`];
  - a failed instruction undoes the whole transaction, sell included [standard Solana atomicity; UNVERIFIED on real Token-2022 sells: FM-T1].
  - So 1 raw unit of dust sent between building and landing makes a "sell all + close" fail. An attacker watching our wallet could repeat it every few slots for 5,000 lamports a time. Holder-reward payouts in the coin might do it by accident [UNVERIFIED].
- **The rule now:** the sell only sells; a separate clean-up transaction closes the empty account afterwards (§6 rule 11). The deposit stays **locked** until that clean-up lands, then comes back in full. The round-trip rent cost is still 0 if clean-up succeeds; clean-up itself costs 6,000 lamports (§2c). If clean-up is given up (repeated dusting), the deposit is booked as lost (the "token account left open" line in §5).
- Token-2022 accounts cannot be closed while holding withheld transfer fees [VERIFIED-DOC Token-2022 `process_close_account` checks `TransferFeeAmount`]. Security already rejects transfer-fee and transfer-hook coins before buying.

### 2e. Things in the data that are *not* costs to us
- **BOOST** (`boost_buy_and_burn`) buys from a separate boost vault and **burns** the tokens. This raises the price and **lowers the coin's total supply**, and the supply feeds the market cap and so the fee tier [VERIFIED-DOC pump_amm.json: `base_mint` is writable; the `BoostBuyAndBurnEvent` has `base_amount_burned` and `boost_vault_remaining`].
  - Its events carry no fee fields, so BOOST pays no pool fee [UNVERIFIED inference from the IDL].
  - A boosted pool carries positive "boost reserves" inside `virtual_quote_reserves`. These raise the effective quote reserve used for **price** but cannot be paid out, so sells are capped by real reserves (6063: "effective = real + virtual is pricing-only; payout is capped at real_vault") [VERIFIED-DOC].
  - The boost reserve σ is exactly `Q − Q_real = vqr + protocol_fees + creator_fees` [VERIFIED-DOC SDK `boost.spec.ts`: "sigma 1_000_000 minus 100_000 of fee buckets gives virtualQuoteReserves 900_000"]. So σ can be read from the `Pool` account alone (§3a).
  - Exactly how `init_boost` sets σ, and whether any σ is left when BOOST ends, is [UNVERIFIED: FC7 rebuilds it from `InitBoostEvent` (`virtual_quote_reserves`, `real_quote_reserves_after`) and `BoostBuyAndBurnEvent` (`quote_amount_in_used`, `base_amount_burned`, `virtual_quote_reserves`, `real_quote_reserves_after`, `base_reserves_after`, `boost_vault_remaining`); FM-T2 measures the leftover].
- **Sweeps** move waiting fees out of the vault; price is unchanged (§2b).
- **LP deposits and withdrawals** change reserves (`DepositEvent`, `WithdrawEvent`). They are not allowed on boost pools (6064).

---

## 3. Exact formulas (integer pseudo-code; the reference for every consumer)

All amounts are unsigned integers in base units (lamports for SOL; raw units for tokens, 6 decimals on pump coins). The exception is `vqr` (`virtual_quote_reserves`), which is a **signed i128**. Products need at least 128-bit integers (85 SOL × 206.9M raw tokens ≈ 1.8 × 10²⁵). **Floating point is never used in quoting**, only in reports.

```
ceil_div(a, b)   = (a + b - 1) // b
fee(amount, bps) = ceil_div(amount * bps, 10_000)                 # every fee rounds UP   [VERIFIED-DOC util.ts]

# ---- pool state (all read at the same slot) ----
Q_vault = pool_quote_token_account.amount                        # raw vault, includes waiting fees
vqr     = Pool.virtual_quote_reserves                            # SIGNED: = boost_reserves - protocol_fees - creator_fees
Q       = Q_vault + vqr                                          # effective quote reserves; program guarantees 0 <= Q < 2^64
Q_real  = Q_vault - Pool.protocol_fees - Pool.creator_fees       # what sells can be paid from
sigma   = Q - Q_real                                             # = vqr + protocol_fees + creator_fees = boost reserve
                                                                 #   (0 on unboosted pools)  [VERIFIED-DOC boost.spec.ts]
B       = pool_base_token_account.amount                         # base side has no virtual part
S       = 10^15 if Pool.is_mayhem_mode else base_mint.supply     # live supply (BOOST burns reduce it)
                                                                 # [VERIFIED-DOC PUMP_SWAP_README, NEGATIVE_VQR, VQR_FEE_ADJ, util.ts]
          # S is the LIVE supply: burns are already in it. Never subtract recorded burns again (prereg PR-15.1).
refuse to quote (class-A alarm) if Q == 0 or B == 0 or sigma < 0 or Q_real < 0

# ---- prices ----
spot_price  = Q / B                         # lamports per raw token; SOL per token = Q*10^6 / (B*10^9) for 6-decimal coins
market_cap  = Q * S // B                    # lamports; the program's own formula, also the fee-tier input [VERIFIED-DOC util.ts poolMarketCap]

# ---- fee rates (pre-trade state) ----
rates(state):
    if not canonical(state):            r = fee_config.flat_fees
    elif quote_mint in {SOL-like}:      r = tier(fee_config.fee_tiers, market_cap)   # SOL-like = {default key, wSOL, Token-2022 native} (§2a)
    elif quote_mint == USDC:            r = tier(stable_fee_tiers or fee_tiers, market_cap)
    else:                               r = exotic_flat_fees if nonzero else flat_fees
    if global_config.creator_fee_configurable and Pool.creator_fee_bps > 0:
                                        r.creator = Pool.creator_fee_bps
    if Pool.coin_creator == 11111111111111111111111111111111:
                                        r.creator = 0
    return r                            # [VERIFIED-DOC fees.ts computeFeesBps / feesForQuoteMint]

tier(tiers, m):                         # [VERIFIED-DOC fees.ts calculateFeeTier = Rust calculate_fee_tier]
    if m < tiers[0].threshold: return tiers[0].fees
    for t in tiers reversed:  if m >= t.threshold: return t.fees
    return tiers[0].fees

# ---- BUY, exact tokens out:  buy / buy_v2(base_amount_out=b, max_quote_amount_in)  [VERIFIED-DOC buy.ts buyBaseInput]
q_in    = ceil_div(Q * b, B - b)                                  # require b < B, else 6016
lp, pr, cr = fee(q_in, r.lp), fee(q_in, r.protocol), fee(q_in, r.creator)
pay     = q_in + lp + pr + cr                                     # fail 6004 if pay > max_quote_amount_in

# ---- BUY, exact SOL in:  buy_exact_quote_in(_v2)(spendable_quote_in=X, min_base_amount_out)
#      [VERIFIED-DOC buy.ts exactQuoteInFees + buyQuoteInput; SYNTHETIC_MIGRATION "out = floor((in-1)*pool_base/(pool_quote+in-1))"]
net0    = X * 10_000 // (10_000 + r.lp + r.protocol + r.creator)
lp, pr, cr = fee(net0, r.lp), fee(net0, r.protocol), fee(net0, r.creator)   # fees on the PRE-shave net
net     = min(net0, X - lp - pr - cr)                             # shave so the total fits X
          # variant to test (FC7): multi_hop uses net = X - lp - pr - cr ("whole budget spent")
b_out   = B * (net - 1) // (Q + net - 1)                          # note the "-1"
pay     = net + lp + pr + cr  (<= X)                              # fail 6040 if b_out < min_base_amount_out

# ---- SELL, exact tokens in:  sell / sell_v2(base_amount_in=b, min_quote_amount_out)  [VERIFIED-DOC sell.ts]
q_out   = Q * b // (B + b)                                        # gross, rounds DOWN
lp, pr, cr = fee(q_out, r.lp), fee(q_out, r.protocol), fee(q_out, r.creator)
leaves  = q_out - lp                                              # what leaves the reserves (LP fee stays)
fail 6063 if Q_real < leaves                                      # = SDK quoteAmountOutWithoutLpFee > realQuoteReserves
receive = q_out - lp - pr - cr                                    # fail 6004 if receive < min_quote_amount_out

# ---- largest sellable amount under the payout cap (§3a) ----
b_max(h) = largest b in [0, h] with leaves(b) <= Q_real           # integer binary search; leaves(b) never falls as b grows

# ---- state update after our own (or any) trade ----
# Effective reserves move the same way in v1 and v2:
#   buy:  Q += q_in + lp  (exact-quote-in: Q += net + lp);  B -= b
#   sell: Q -= q_out - lp;                                    B += b
# Raw vault and buckets:
#   v1 buy : Q_vault += q_in + lp                         (protocol and creator fees paid out)
#   v2 buy : Q_vault += q_in + lp + (pr - bb) + cr; vqr -= (pr - bb) + cr; protocol_fees += pr - bb; creator_fees += cr
#   v1 sell: Q_vault -= q_out - lp
#   v2 sell: Q_vault -= receive + bb;               vqr -= (pr - bb) + cr; buckets += as above
#   where bb = buyback_fee paid out in the trade   (the "- bb" split is [UNVERIFIED: FC7])
# sweep(amount, bucket): Q_vault -= amount; vqr += amount; bucket -= amount   -> Q unchanged
# BOOST, init_boost, deposit, withdraw: take post-state from the account update (primary) and the event (witness)
```

**Price limits we set.**
- **Buys:** `buy_exact_quote_in_v2` with `spendable_quote_in` = stake and a `min_base_amount_out` from `m` (below).
- **Sells:** a `min_quote_amount_out` from `m`.
- Both are quoted on the latest state.
- `m` follows DESIGN #9 and prereg §2.5: normal 1–5%, emergency 3–15%. **v1.1 defines it in whole basis points, with no floating point (FM-9.1):**

```
# P = Q/B is kept as a fraction; "end of slot s" = the effective reserves after the last change in slot s
# (a skipped slot keeps the previous state).  ref = end of slot s-2.
swing2_bps = ceil_div( |Q_s * B_ref - Q_ref * B_s| * 10_000,  Q_ref * B_s )      # = |P_s / P_ref - 1|, rounded up
m_bps      = clamp(2 * swing2_bps, 100, 500)            # normal
m_bps      = clamp(3 * swing2_bps, 300, 1_500)          # emergency: hard stop, sell pressure, insider flow, FAST_DUMP
min_base_amount_out  = b_out   * (10_000 - m_bps) // 10_000          # rounds down
min_quote_amount_out = receive * (10_000 - m_bps) // 10_000          # rounds down
max_quote_amount_in  = ceil_div(pay * (10_000 + m_bps), 10_000)      # only for exact-out buys, which we don't use
```

  - Rounding: the swing rounds up; min-outs round down and max-ins round up. So a limit is at most 1 base unit looser than `m`, and never tighter.
  - Products such as `Q × B` need 128-bit integers (as above).
- **Re-quote interval (PR-14d):** the live builder re-quotes at least every 2 blocks (DESIGN #9). **Paper prices every sell attempt with a quote 3 slots old** (prereg S7), the more conservative value. Both files say so.
- **There are no partial fills on PumpSwap:** each trade fills completely or fails [VERIFIED-DOC instruction semantics, PUMP_SWAP_README]. A smaller sell is a new trade, not a partial fill (§3a).

**Price impact, in plain terms [DERIVED from the formulas].**
- Buying with `net` lamports pays an average of `(Q + net)/B` per token, about `net/Q` above spot. 0.25 SOL into 85 SOL is about 0.29%.
- Selling `b` tokens gets an average of `Q/(B + b)`, about `b/(B + b)` below spot.
- In a pool where nothing else happens, a buy followed by a sell of the same tokens gets the buy's impact back (only the fees are lost). Whether our push "stays" in a live market is unknowable, so the **base view assumes it does not** (§6, rule 4).

### 3a. Boosted pools: the price can include SOL that sellers can't be paid (FM-2)

**In plain words.** On a "boosted" pool, part of the SOL that sets the price is virtual: it counts for the price but is not in the vault. A seller can only be paid from the real SOL. If too many people sell, the last ones fail (error 6063), whatever fee they pay.

**What the chain does** [VERIFIED-DOC pump_amm.json errors 6063 and 6065; SDK `sell.ts` `sellAmounts`; `boost.spec.ts`]:
- Price uses the effective reserve `Q = Q_real + σ`.
- A sell pays out only from `Q_real`. If `q_out − lp > Q_real`, the **whole** sell fails with 6063; nothing is partly filled. Pump's own error text says: "effective = real + virtual is pricing-only; payout is capped at real_vault, so quote min(out, real_vault)".
- BOOST spends SOL from a separate boost vault (`BoostBuyAndBurnEvent.boost_vault_remaining`). Whether σ falls to 0 when BOOST ends, or a remainder stays priced in, is **unmeasured** [UNVERIFIED: FM-T2].

**Definitions (integers):**
- `rho_bps = Q_real × 10,000 // Q`: the share of the quoted SOL that can actually be paid. It is 10,000 on unboosted pools.
- `b_max(h)`: the largest part of a holding `h` that one sell can carry (§3).
- **Payable value** of `h` tokens: `V_pay(h) = receive(b_max(h))`. The remainder `h − b_max(h)` is valued at **0** for risk, stops and exits until real reserves grow (new buys add real SOL). The position is flagged `PAYOUT_CAPPED`.

**Rules:**
1. **Pricing.** Every quote, mark-to-market, stop level and exit decision uses `V_pay`, never the effective-reserve value alone. On unboosted pools `V_pay` is the normal quote, so nothing changes there.
2. **Simulator.** 6063 is checked at our landing position: after the same-direction sells ahead of us in that slot (§6 rule 3), which use up `Q_real` first. A simulated 6063 is a landed failure (base + priority, no tip). Like the guard, the paper bot never *sends* a sell it already predicts will fail. Paper 6063s therefore come only from state that moved between decision and landing, which is exactly the crowded-exit case.
3. **Guard (Phase 3).** Before each sell attempt, on its own latest reads:
   - require `leaves ≤ Q_real − H`. The headroom `H` is the `leaves` of every sell on this pool seen in the guard's feed in the current and previous slot, and at least 1% of `Q_real` [proposal; risk-manager freezes the number];
   - if that fails: **don't send** (it would be a certain fee loss), raise a class-A alarm, and sell the largest chunk that passes, re-checking every block [proposal; risk-manager and security confirm partial selling under a payout cap];
   - **never escalate priority fees or tips because of 6063.** More fee can't create real reserves. The "never give up" chase continues with chunks, not with bigger bids;
   - after a landed 6063: re-read, recompute `b_max`, continue.
4. **Risk features** (request to risk-manager): `rho_bps` at the decision slot and through the hold, and our payout headroom `(Q_real − leaves(h)) × 10,000 // Q_real`, as skip and exit features. Their thresholds are set from FM-T2 and frozen in the preregistration before use. None is assumed here.
5. **Before T6 has validated the 6063 line** (T6a, or T6b if deferred, §7), paper treats any sell with `leaves > 0.98 × Q_real` at the landing position as a 6063 failure (a 2% safety band).

**Measurement FM-T2 (extends FC7; §10).** On 100 boosted pools drawn from the independent audit (prereg PR-1):
- σ, `Q`, `Q_real` and `rho_bps` at t_bend (the slot of the pool's last `BoostBuyAndBurnEvent`), t_bend + 900 slots and t_bend + 9,000 slots;
- σ compared with the last `boost_vault_remaining`;
- the count of 6063 failures per pool in [t_bend, t_bend + 9,000].
- **Decision:** if σ = 0 at t_bend + 900 on all 100 pools, FM-2 is rare in practice; the checks stay anyway, as they cost nothing. If not, `rho_bps` becomes a mandatory risk feature, and 6063 becomes a **core** stratum of T6b.

---

## 4. Where every value comes from

**Addresses** [VERIFIED-DOC PUMP_SWAP_README, TRADE_V2, MULTI_HOP_SWAP, pump_fees.json]:

| Item | Address |
|---|---|
| PumpSwap program | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` |
| GlobalConfig | `ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw` |
| Pump Fees program | `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` |
| PumpSwap FeeConfig | `5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx` |
| Bonding-curve FeeConfig | `8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt` |
| Pump program | `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` |
| Rent sysvar | `SysvarRent111111111111111111111111111111111` |

**Account layouts** (Anchor/Borsh, little-endian, 8-byte discriminator first; offsets [DERIVED] from the IDL):
- **`Pool`** (discriminator `f19a6d0411b16dbc`):
  - creator @11, base_mint @43, quote_mint @75;
  - pool_base_token_account @139, pool_quote_token_account @171;
  - coin_creator @211;
  - is_mayhem_mode @243, is_cashback_coin @244;
  - **virtual_quote_reserves i128 @245**;
  - creator_fee_bps u64 @261, can_edit_creator_fee @269, is_holder_reward @270;
  - **protocol_fees u64 @271, creator_fees u64 @279**.
  - Older pools are shorter (244, 245, … bytes), and missing trailing fields read as 0 [VERIFIED-DOC PUMP_SWAP_README; the 244/245-byte cases are in the SDK tests]. The account may be padded to 300 bytes.
- **`GlobalConfig`** (discriminator `95089ccaa0fcb0d9`):
  - lp_fee_basis_points @40, protocol_fee_basis_points @48;
  - **disable_flags u8 @56** (bit 3 = buy, bit 4 = sell [VERIFIED-DOC IDL field docs]);
  - coin_creator_fee_basis_points @313, is_cashback_enabled @642;
  - **buyback_basis_points @899**, **boost_enabled @939**;
  - creator_fee_configurable @940, max_configurable_creator_fee_bps @941.
- **`FeeConfig`** (discriminator `8f3492bbdb7b4c9b`):
  - bump @8, admin @9, flat_fees @41 (3 × u64);
  - fee_tiers: u32 count @65, then 40-byte rows (u128 threshold, then lp, protocol, creator u64);
  - then the stable_fee_tiers vector, then exotic_flat_fees.
  - This layout is **verified by my decode of the 2026-09-08 capture** (25 + 25 tiers, 4,073 bytes).

| Value | Live source (account, read by the module) | Historical / witness source (transaction) |
|---|---|---|
| `B` | `pool_base_token_account.amount` | `BuyEvent`/`SellEvent.pool_base_token_reserves`; tx `meta.preTokenBalances` of the base vault |
| `Q_vault` | `pool_quote_token_account.amount` | `event.pool_quote_token_reserves` (raw or effective? pre-trade? **FC7 decides**); `meta.preTokenBalances` |
| `vqr` | `Pool.virtual_quote_reserves` (signed) | `event.virtual_quote_reserves` (signed; pre- or post-trade: FC7); `InitBoostEvent`, `BoostBuyAndBurnEvent` |
| `protocol_fees`, `creator_fees` | `Pool` @271/@279 | `event.creator_fee_unclaimed` (creator bucket after the trade); the protocol bucket is rebuilt from trades and `SweepPoolFeeEvent` |
| `S` | base mint `supply` (SPL or Token-2022 mint) | `event.base_supply` |
| Canonical? | `Pool.creator == PDA("pool-authority", base_mint)` under the Pump program | same |
| Quote mint, mayhem, cashback, holder-reward, per-pool creator rate | `Pool` fields | `CreatePoolEvent` (`quote_mint`, `is_mayhem_mode`, `creator_fee_bps`, `is_holder_reward`) |
| `coin_creator` | `Pool.coin_creator` | `event.coin_creator` |
| Tier table, flat fees | `FeeConfig` (PumpSwap) | Pump Fees events: `UpdateFeeConfigEvent`, `UpsertFeeTiersEvent`, `UpdateStableFeeConfigEvent`, `SetExoticFlatFeesEvent` |
| Fees actually charged | — | `event.lp_fee_basis_points`, `lp_fee`, `protocol_fee_basis_points`, `protocol_fee`, `coin_creator_fee_basis_points`, `coin_creator_fee`, `buyback_fee_basis_points`, `buyback_fee`, `cashback_fee_basis_points`, `cashback`, `holder_rewards_bps`, `holder_rewards` |
| Trade amounts | instruction arguments | Buy: `base_amount_out`, `quote_amount_in`, `quote_amount_in_with_lp_fee`, `user_quote_amount_in`, `max_quote_amount_in`, `min_base_amount_out`, `ix_name`. Sell: `base_amount_in`, `quote_amount_out`, `quote_amount_out_without_lp_fee`, `user_quote_amount_out`, `min_quote_amount_out` |
| v1 or v2? | instruction discriminator | Buys: `ix_name`. Sells: `protocol_fee_recipient == 1111…1` means v2 [VERIFIED-DOC TRADE_V2] |
| BOOST | `GlobalConfig.boost_enabled` | `event.can_boost`; `BoostBuyAndBurnEvent` |
| Trading disabled | `GlobalConfig.disable_flags` | `DisableEvent` |
| Network fee | — | `meta.fee`; the compute-budget instructions (`SetComputeUnitLimit` / `SetComputeUnitPrice`); signature count |
| Tips | — | System transfers to the Jito or Sender tip accounts; `meta.pre/postBalances` |
| Rent | Rent sysvar, or `getMinimumBalanceForRentExemption` | `meta.pre/postBalances` of created and closed accounts |
| SOL/USD | reporting feed only, never used in decisions | — |

All the event field names above are [VERIFIED-DOC pump_amm.json]. Events are emitted as a self-call to the program's `event_authority` PDA (`["__event_authority"]`), so decoders read them from **inner instructions**, not only from logs [VERIFIED-DOC: `event_authority` is in every trade's account list].

**Events inside failed transactions are not trades (TS-6, new in v1.1).**
- *The risk.* A transaction can make a real trade by CPI, emit a perfect `BuyEvent`, and then fail on purpose in a later instruction. The chain undoes the trade, but the record of the transaction may still contain the event. Solana's validator software records the inner-instruction trace **whatever the transaction's result**: `deconstruct_transaction` runs before the success-or-failure status is set, and it is not conditioned on it [VERIFIED-DOC agave `svm/src/transaction_processor.rs`, `execute_loaded_transaction`]. Whether RPC and Yellowstone then *return* those inner instructions for failed transactions is [UNVERIFIED: AR-T1]. We record failed transactions on purpose (rival bids, the losers' tape), so they are in our data either way.
- *The rule* (§6 rule 13). An event counts only if it is a direct child of a PumpSwap instruction **in a successful transaction** (`meta.err` is null). From a failed transaction the model may use only: `meta.err`, `meta.fee`, the signature count, the instruction arguments, the compute-budget instructions, and the **pre**-balances as a witness of the state before it. Its events are tagged `FAILED_TX_EVENT` and never change pool state, prices, fee tiers, holdings, rival counts or labels.

**Who reads what, live.**
- The bot host takes everything from its Chainstack stream: account updates are the primary state, and events are the witness.
- The guard (ruling C9) subscribes to held pools, both vaults and GlobalConfig. **It must add the PumpSwap `FeeConfig` and each held coin's mint account to that list.** Without them its min-out quote can use a stale tier or supply (request to security and data, §9). The `Pool` account it already reads carries `virtual_quote_reserves` and both fee buckets, so σ, `Q_real` and `b_max` (§3a) need no extra subscription.

---

## 5. Worked examples (all integers computed with `bc` this session; [DERIVED])

**Inputs, all [UNVERIFIED] illustrations until Phase 1 replaces them with recorded states:**
- Entry pool: `Q` = 85,000,000,000 lamports, `B` = 206,900,000,000,000 (206.9M tokens), `S` = 10¹⁵, so market cap = 410.83 SOL, which is **tier 0** (2 / 93 / 30 bps).
- We buy with `buy_exact_quote_in_v2`. Network and tip levels are as in §2c. SOL = $100.
- **Base view:** our buy's push on the price does not persist (§6, rule 4).

**Leg detail at 0.25 SOL, calm:**

| Step | Lamports |
|---|---|
| Spend X | 250,000,000 |
| Fees (on net0 = 246,913,580): LP 49,383 + protocol 2,296,297 + creator 740,741 | 3,086,421 |
| Net into the pool (shaved by 1) | 246,913,579 |
| Tokens received | 599,275,881,600 raw (599,275.88 tokens) |
| Buy impact vs spot | 715,175 |
| Sell into the same pool: gross | 245,487,362 |
| Sell fees | 3,068,594 |
| **Received** | 242,418,768 |
| Sell impact | 711,042 |
| Network (125,000 + 210,000) | 335,000 |
| **Total cost** | **7,916,232 = 3.17% = $0.79** |

**Calm exit (exit price = entry price):**

| Stake | Pool fees (both legs) | Price impact (both legs) | Network + tips | Sandwich | **Total SOL** | **% of stake** | **USD** |
|---|---|---|---|---|---|---|---|
| 0.1 | 0.002466 | 0.000229 | 0.000335 | 0 | **0.003030** | **3.03%** | $0.30 |
| 0.25 | 0.006155 | 0.001426 | 0.000335 | 0 | **0.007916** | **3.17%** | $0.79 |
| 0.5 | 0.012275 | 0.005672 | 0.000335 | 0 | **0.018282** | **3.66%** | $1.83 |

**Crash exit:**
- The price falls 30% before we sell: `Q` = 71.12 SOL, `B` = 247.29M tokens, market cap ≈ 288 SOL, so still tier 0.
- The sell runs the escalated ladder (0.004140 SOL of network fees for the round trip), and the sandwich allowance is 0.2% of proceeds.
- The −30% fall itself (0.03 / 0.075 / 0.15 SOL) is the trade result and is **not** in these numbers.

| Stake | Pool fees | Price impact | Network + tips | Sandwich | **Total SOL** | **% of stake** | **USD** |
|---|---|---|---|---|---|---|---|
| 0.1 | 0.002097 | 0.000182 | 0.004140 | 0.000136 | **0.006150** | **6.15%** | $0.62 |
| 0.25 | 0.005235 | 0.001132 | 0.004140 | 0.000340 | **0.009706** | **3.88%** | $0.97 |
| 0.5 | 0.010448 | 0.004505 | 0.004140 | 0.000676 | **0.017061** | **3.41%** | $1.71 |

**Sensitivities (same method):**
- **−50% crash:** 5.57% / 3.23% / 2.64% of stake.
- **"Bad crash" network** (0.01115 SOL), 0.25 SOL, −30%: **6.69%**.
- **Tier 1 pool** (illustrative post-BOOST: `Q` 102.6 SOL, `B` 171.41M, `S` 964.51M, so market cap 577 SOL and 1.20%/side), calm: **2.89% / 2.97% / 3.37%**.
- **"Impact persists" (pure pool maths)**, 0.25 SOL calm: **2.60%**, which is only fees plus network. This is an upper bound on how cheap a round trip can be, never used for decisions.
- **Token account left open** (not our plan): add the rent in §2d, e.g. +0.61% at 0.25 SOL at 5,080 lamports/byte.

**Reading the numbers.**
- Pump's fee is about 2.1–2.5 points of every round trip.
- Network costs only matter at 0.1 SOL or in a crash.
- In calm exits, bigger bets cost more per SOL, because our own price impact grows with size.
- In crash exits, smaller bets cost more per SOL, because the escalated network fees are fixed amounts.
- The 0.1 SOL canary size pays about 6% in a crash. That's acceptable for a measurement run, never for a strategy.

---

## 6. Rules for the simulator, backtests, strategy and guard
1. **One module, one version.** Every fill, quote and min-out uses this maths. Each paper trade records the fee-model version and the slot of the `FeeConfig` / `GlobalConfig` snapshot it used.
2. **Before T6 passes**, paper charges `max(model, 125 bps)` per side (the tier-0 split 2/93/30) and every report is labelled **"fee model unproven"** (QNT-R §1b). After T6, the live tier applies.
3. **Position in the block** (QNT-2): our fill uses the recorded state *after* every same-direction trade in our landing slot and *before* the opposite-direction ones. The tier and the 6063/6004/6040 checks are evaluated on that state.
4. **Impact persistence.**
   - **Base and pessimistic views:** the exit is priced on the *recorded* pool state at the exit position, with our tokens sold into it. Our earlier buy is **not** added to the recorded state.
   - **Optimistic view:** our trades are injected and later recorded trades are replayed on top. It is shown only as an upper bound.
5. **Failures are charged.** Every landed failure pays base + priority. A dropped bundle or expired transaction pays 0. A failed sell then follows the 2-block chase (DESIGN #9).
6. **Rent.** The deposit is charged on the buy and refunded on the closing sell. An open position shows it as "locked", not "lost". The amount comes from the live Rent sysvar at the simulated slot.
7. **Rebates count as 0.** Cashback and holder rewards never improve paper P&L.
8. **Cost ledger.** Every trade logs each component separately:
   - LP, protocol, creator and buyback fees;
   - buy and sell impact;
   - base fee, priority fee and each tip;
   - each failed attempt;
   - rent locked and refunded;
   - the sandwich allowance.

   USD is added with the SOL price at trade time, for reports only.
9. **Integers only** in the money path; floats in reports only. The module refuses to quote on unknown account lengths, an unknown `ix_name`, `Q == 0` or `B == 0`, which raises a class-A alarm.
10. **The guard quotes from its own reads** of the same accounts (C9), never from numbers sent by the bot.

---

## 7. T6: the validation procedure (Gate 0 → 1)

**Goal.** Prove that this model reproduces real PumpSwap trades **exactly, to the lamport**, before any paper result counts.

**Step 0: freeze first.** Commit three things before looking at any trade, dated, in `docs/preregistration.md`:
- the selection script and its random seed;
- the model version;
- the pass criteria below.

**Step 1: calibration set (50 trades, not scored).** Settle the open semantics, then freeze the model. FC7 answers:
1. Are the event reserve fields pre-trade or post-trade, and raw vault or effective?
2. Is `event.virtual_quote_reserves` pre-trade or post-trade?
3. What is the buyback formula and its rounding, and does `protocol_fees` grow by `pr` or by `pr − buyback`?
4. Does `buy_exact_quote_in_v2` leave unspent lamports with the user, or spend the whole budget?
5. How is the boost state set?

**Step 2: the test set.**
- **500 different trades** chosen by the frozen seed, none of them from the calibration set.
- They come from canonical, SOL-quoted, non-mayhem PumpSwap pools, across **≥ 7 days and ≥ 100 pools**.
- The trades are fetched read-only: `getSignaturesForAddress(pool)`, then `getTransaction(…, maxSupportedTransactionVersion: 0)`. In Phase 1 they come from our own recorder.
- **Minimum strata** (one trade can count in several):

| Stratum | Minimum |
|---|---|
| Trades **crossing a fee-tier boundary** (pre-trade and post-trade market cap in different tiers, or pre-trade market cap within ±1% of a threshold), with both sides of 420 SOL represented | ≥ 50 |
| v2 trades (`buy_v2`, `buy_exact_quote_in_v2`, `sell_v2`) | ≥ 50 |
| v1 trades, including ≥ 25 v1 buys on SOL pools (the SDK's warned buyback path) | ≥ 50 |
| Sells | ≥ 100 |
| Buys, of which ≥ 50 are exact-SOL-in | ≥ 100 |
| Trades with `vqr < 0` (fees waiting) | ≥ 30 |
| Trades with `can_boost == true` (boost reserves present) | ≥ 30 |
| Trades at tier ≥ 2 (market cap ≥ 1,470 SOL) | ≥ 20 |

- Multi-hop, mayhem and cashback trades are reported separately and do not count toward the gate.

**Step 3: recompute and compare.** For every trade, the module takes the pre-trade state (FeeConfig as of that slot) and the decoded instruction arguments, and predicts the scored fields below.

**Pass criteria. All must hold; there is no tolerance:**

| # | Check | Required |
|---|---|---|
| P1 | Fee rates `(lp, protocol, creator)` equal the event's `*_basis_points` | **500 / 500** |
| P2 | `lp_fee`, `protocol_fee`, `coin_creator_fee`, `buyback_fee` equal the event, to the lamport | **500 / 500** |
| P3 | `quote_amount_in/out`, `user_quote_amount_in/out`, `base_amount_out/in` (and `quote_amount_in_with_lp_fee` / `quote_amount_out_without_lp_fee`) equal the event | **500 / 500** |
| P4 | **Balance witness**, on transactions with exactly one PumpSwap trade on that pool: the user's quote-account change, both pool-vault changes and the buyback-recipient change equal the §3 update rules (v1 or v2) | 100%, on ≥ 400 trades |
| P5 | **Continuity:** for consecutive trades on one pool with nothing in between (or with sweeps, BOOST and deposits applied), the predicted post-state of trade *i* equals the observed pre-state of trade *i+1* (`Q`, `B`, `vqr`, buckets) | 100%, on ≥ 200 pairs |
| P6 | **Network fee:** `meta.fee == 5,000 × signatures + ceil(cu_price × cu_limit ÷ 10⁶)` on ≥ 100 transactions, ≥ 30 of them failed. For failed transactions with a tip transfer, the tip account's balance is unchanged | 100% |
| P7 | All strata minimums are met; the seed and script are unchanged since Step 0 | yes |

**If anything fails:**
- Record every mismatch with its trade signature.
- Fix the model and bump its version.
- Re-run on a **fresh 500** with a new seed. Never re-score the same sample, which would fit the model to it.
- If one stratum can't be filled from 14 days of history, the gate waits for the recorder. A stratum we actually trade is never waived.

**After T6 passes:**
- The same recompute runs on **every recorded trade** (the two-witness check, DAT-1). Gate 1→2 allows < 0.1% mismatches, each explained.
- Any mismatch on a pool we hold or are about to buy is a **class-A alarm** (buys pause).
- After any change in §8, buys resume only after **1,000 clean market-wide trades** (DESIGN NEW-9). A tier-table change also triggers a T6 re-run on 500 trades made *after* the change before paper results count again (QNT-R §1d).

---

## 8. What can change with no program upgrade, so the monitors must watch it

Each item below is changed by an admin instruction, an off-chain policy, or a Solana feature gate. None needs Pump to redeploy. Detection is by **account subscription with byte-level diffs** (primary) plus the event, where one exists. Several admin instructions emit **no event** (marked "no event"), so account diffs are mandatory. Unless stated, every change is a **class-A alarm**: buys pause, sells continue, and the fee module reloads from the account (never from a constant).

| Where | What can change | Instruction / event | Effect on us |
|---|---|---|---|
| **PumpSwap FeeConfig** `5PHirr8…` | `fee_tiers` (thresholds and all three rates), `flat_fees` | `update_fee_config`, `upsert_fee_tiers` → `UpdateFeeConfigEvent`, `UpsertFeeTiersEvent` | Every cost; re-run T6 |
| | `stable_fee_tiers`, `exotic_flat_fees`, account size, admin | `upsert_stable_fee_tiers`, `update_stable_fee_config`, `set_exotic_flat_fees`, `extend_fee_config`, `update_admin` → their events | Decoder lengths; non-SOL pools |
| **Pump Fees global** | `disable_flags` (meaning [UNVERIFIED]) | `set_disable_flags` → `SetDisableFlagsEvent` | Unknown; alarm |
| **PumpSwap GlobalConfig** `ADyA8h…` | `disable_flags`: **buy (bit 3) and sell (bit 4) switches** | `disable` → `DisableEvent` | Sells stop (6021); "first out when reopened" (EXE-5). The alert must reach Paul within 10 s |
| | `buyback_basis_points` | `update_buyback_config` (**no event**) | Fee split |
| | `boost_enabled` | `toggle_boost` (**no event**) | Market-structure change (ruling R5) |
| | `is_cashback_enabled`, `mayhem_mode_enabled` | toggles (**no event**) | Pool types |
| | `creator_fee_configurable`, `max_configurable_creator_fee_bps` | `update_creator_fee_config` → `UpdateCreatorFeeConfigEvent` | Per-pool creator rates |
| | `lp/protocol/coin_creator_fee_basis_points` (fallback), `protocol_fee_recipients`, coin-creator authority | `update_fee_config` → `UpdateFeeConfigEvent` | Fallback fees; accounts |
| | `buyback_fee_recipients`, reserved recipients, `boost_authority`, `admin` | `set_reserved_fee_recipients`, `set_boost_authority`, `update_admin` → events | Required accounts in our transactions (guard template) |
| **Each Pool** we hold or watch | `coin_creator` | `set_coin_creator`, `admin_cto_pool`, `migrate_pool_coin_creator` → their events | Creator fee recipient; default key means 0 fee |
| | `creator_fee_bps`, `is_holder_reward`, `is_cashback_coin` | CTO / admin | Rates, v1 or v2 path |
| | `virtual_quote_reserves`, `protocol_fees`, `creator_fees` | trades, sweeps (anyone), BOOST | Price input. Normal flow, not an alarm |
| | Account length | `extend_account` | Decoder lengths |
| **BOOST policy** (off-chain) | Amount, timing and which pools are boosted | `boost_buy_and_burn` by the boost authority | Entry timing and our pass-mark assumptions. Daily stats, alarm on a shift (R5) |
| **Pump bonding-curve** `Global` + FeeConfig `8Wf5Ti…` | Curve fees, `pool_migration_fee`, initial reserves, supply, `enable_migrate`, buyback bps | admin instructions | Size and price of new pools, the tier at graduation |
| **Solana runtime** | `lamports_per_signature` (5,000), burn %, **rent `lamports_per_byte`** (SIMD-0437 gates `4a6f7o7i…`, `61BtM7Bk…`, `rntCigrT…`, `rntD7inv…`, `rntTjNZ9…`; revert gate `rnt8ZQpz…`), compute limits, transaction formats (v1 absolute priority fee) | feature gates (watch the gate accounts and the Rent sysvar each epoch) | Fixed costs, deposits. Rent changes are class C (info) |
| **Senders** | Jito tip floor, minimum tip and tip accounts; Helius Sender minimum tips, tip accounts and `mev-protect` behaviour | provider docs and APIs | Landing cost; guard tip allowlist. Weekly check, alarm on a change |
| **Program upgrades** of `pAMMBay…`, `pfeeUx…`, `6EF8rr…` | anything | the ProgramData deploy slot | Class A; IDL re-check (DESIGN #11) |
| **Pump's docs, IDL and SDK** | new instruction versions, appended fields | the README changelog; `raw.githubusercontent.com` (reachable today) | The rule-change reader (DESIGN §2b-6) |

Two documentation inconsistencies the monitors should not "fix" silently:
1. The README's GlobalConfig example lists a protocol-fee recipient (`JCRGumoE…`) that FEE_RECIPIENTS.md does not; FEE_RECIPIENTS has `CebN5WGQ…` instead.
2. The mayhem v2 contradiction (§2b).

In both cases **the live account is the truth.**

---

## 9. Differences from DESIGN §5b, and requests to teammates
1. **The fee level is now VERIFIED-DOC.** Assumption A-001 can be upgraded: the tier image was read directly, and the on-chain bytes from the SDK capture were decoded independently (2026-09-08). The split is 0.02 / 0.93 / 0.30, as execution said in Round 2. A-077 (base and priority fee) is now VERIFIED-DOC from Solana's source. The live account still needs FC1.
2. **Most post-BOOST trades are probably at 1.20%, not 1.25%** [DERIVED, UNVERIFIED]. Paper keeps 1.25% until T6 passes (§6, rule 2), so it stays conservative.
3. **Crash costs are about 1.0–1.3 points lower than DESIGN §5b** at 0.25–0.5 SOL, because a fallen position pays smaller sell-side fees. **No change to the approved break-even table is needed:** it stays a conservative envelope, and the simulator uses exact per-trade maths. The lead may choose to refresh §5b; that is a documentation change only.
4. **Rent is a moving number** (SIMD-0437). A-037/A-038 are unaffected; the round-trip rent is 0 because we close the account.
5. **Requests:**
   - *To security and data:* add `FeeConfig` and the held mint to the guard's subscriptions (§4).
   - *To data:* the recorder must store `meta.pre/postTokenBalances`, inner instructions and the compute-budget instructions for every trade (T6 witnesses).
   - *To quant:* adopt §6 rules 3–4 as the simulator's state convention.
   - *To security:* refuse v2 on mayhem pools until FC9.

**Open risks.**
- The SOL buyback path may make the SDK's predictions differ from the chain (§2a). T6 stratum P2 covers it.
- The BOOST reserve mechanics are not documented in the files we could read (§2e).
- The Token-2022 account size is [UNVERIFIED].

---

## 10. Tests to run once allowed (all read-only; no transaction is signed, sent or simulated)

| # | Test | Domain needed |
|---|---|---|
| FC1 | `getAccountInfo("5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx", base64)`: decode it with the §4 layout and diff it against the 2026-09-08 capture. Any difference updates the module | an RPC host: `api.mainnet-beta.solana.com`, `mainnet.helius-rpc.com` or Chainstack's RPC |
| FC2 | Read GlobalConfig `ADyA8h…`: `disable_flags`, `buyback_basis_points`, `boost_enabled`, `creator_fee_configurable`, `buyback_fee_recipients` | RPC host |
| FC3 | Read Pump `Global` (initial reserves, `pool_migration_fee`) and the curve FeeConfig `8Wf5Ti…`. Replace the 85 SOL / 206.9M example pool with measured opening states of 50 recent graduations | RPC host |
| FC4 | `getMinimumBalanceForRentExemption(165)` and `(170)`; `getAccountInfo` on each SIMD-0437 gate ID (activated or not) | RPC host |
| FC5 | The data length of 5 token accounts holding `create_v2` coins, and the mint extensions of those coins | RPC host |
| FC6 | 20 failed PumpSwap transactions that include a Jito or Sender tip transfer: check `meta.fee = base + priority` and that the tip account balance is unchanged | RPC host (or the Chainstack gRPC `failed` filter) |
| FC7 | The calibration set (§7 Step 1): event field semantics, buyback formula, v2 bucket increments, the exact-SOL-in leftover rule, `InitBoostEvent` / `BoostBuyAndBurnEvent` reconstruction | RPC host |
| FC8 | The `user_volume_accumulator` data length and rent for 3 active wallets | RPC host |
| FC9 | Do v2 trades ever succeed on mayhem pools (`is_mayhem_mode` pools with `ix_name = buy_v2`)? | RPC host |
| T6 | §7 in full | RPC host; later our recorder (Chainstack gRPC) |

`raw.githubusercontent.com` (Pump docs, IDLs, Solana source) and `registry.npmjs.org` (Pump's SDK) already work from this environment.

---

## 11. Sources

**[VERIFIED-DOC] Pump.fun official repository**, all fetched 2026-11-05 under `https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/`:
- README.md
- docs/PUMP_SWAP_README.md
- docs/FEE_PROGRAM_README.md
- **docs/fees.png** (read as an image)
- docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md
- docs/VIRTUAL_QUOTE_RESERVES_FEE_ADJUSTMENT.md
- docs/instructions/PUMP_SWAP_TRADE_V2.md
- docs/instructions/SWEEP_FEES.md
- docs/FEE_RECIPIENTS.md
- docs/SYNTHETIC_MIGRATION.md
- docs/HOLDER_REWARDS_README.md
- docs/PUMP_SWAP_CREATOR_FEE_README.md
- docs/instructions/MULTI_HOP_SWAP.md
- docs/FAQ.md
- idl/pump_amm.json
- idl/pump_fees.json
- idl/pump.json

**[VERIFIED-DOC] Pump's official SDK** `@pump-fun/pump-swap-sdk` 2.1.0:
- Source: https://registry.npmjs.org/@pump-fun/pump-swap-sdk/-/pump-swap-sdk-2.1.0.tgz (sha512 `O0ulb5In…h+35ueA==` matched the registry).
- Files read: `src/sdk/fees.ts`, `util.ts`, `buy.ts`, `sell.ts`, `multiHop.ts`, `offlinePumpAmm.ts`; `src/__tests__/feeConfigMainnetFixture.ts` (the mainnet FeeConfig capture, slot 445186127, 2026-09-08, decoded independently), `boost.spec.ts`, `buyQuoteSimulation.spec.ts`.

**[VERIFIED-DOC] Solana fee and rent rules:**
- https://raw.githubusercontent.com/solana-foundation/solana-com/main/apps/docs/content/docs/en/core/fees/fee-structure.mdx
- https://raw.githubusercontent.com/anza-xyz/agave/master/compute-budget/src/compute_budget_limits.rs
- https://raw.githubusercontent.com/anza-xyz/agave/master/fee/src/lib.rs
- https://raw.githubusercontent.com/anza-xyz/solana-sdk/master/rent/src/lib.rs
- https://raw.githubusercontent.com/anza-xyz/agave/master/feature-set/src/lib.rs (SIMD-0437 gates)

**[VERIFIED-SEARCH]:**
- Helius Sender tips: https://www.helius.dev/docs/sending-transactions/sender-swqos-only
- Jito minimum tip (Helius pages conflict, 1,000 vs 5,000 lamports): https://www.helius.dev/docs/sending-transactions/send-bundle
- SIMD-0437 mainnet status (sources conflict): https://solana.com/el/upgrades/reduced-rent ; https://docs.chainstack.com/docs/solana-rent-reduction-reclaim-excess-rent ; https://solanacompass.com/news/solanas-first-rent-reduction-goes-live-on-testnet-under-simd-0437-targeting-90-cut-in-five-steps ; https://docs.raydium.io/solana-fundamentals/rent-and-reclaimable-rent.md
- SOL ≈ $100 and AWS KMS pricing: via DESIGN.md §5b and `docs/assumption-register.md` (A-065)

**Team files:**
- `DESIGN.md` §4–5
- `team-debate/round3/rulings.md` R6
- `team-debate/round2/execution-engineer-response.md` §1a–1d
- `team-debate/round2/quant-tester-response.md` §1a–1b
- `docs/assumption-register.md` (A-001, A-002, A-037–A-040, A-065, A-077)
