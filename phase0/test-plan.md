# Phase 0 test plan: every network test, deduplicated and ordered

**Status:** written by the data engineer on 2026-11-05, after Paul approved DESIGN.md. Every test is **read-only**. Nothing here signs or sends a transaction. Results go into `phase0/results.md`, using the template in §6.

## In plain English (for Paul)
- This is the one checklist of every live test the team asked for. About 180 test names from the debate are merged here into 115 rows, so each question is tested once.
- **The first block (rows A01–A32) can run as soon as you add `HELIUS_API_KEY` (the free plan is enough) and allow the List 1 web domains.** It needs about 3–4 hours of script time spread over a few days, and uses about 10–15% of Helius's free monthly allowance.
- The most important row is **A09 (test "T6")**. It proves our fee maths matches real trades to the last unit. It is the gate to Phase 1.
- Later blocks need, in order: the Chainstack account, a few weeks of our own recording, then Lists 2–4.
- Tests that would sign or send anything are marked **FORBIDDEN** (§4, tier I). They are moved to Phase 3 or dropped.

**Tags.** [VERIFIED-DOC] = primary source read this session. [VERIFIED-SEARCH] = search results only. [VERIFIED-LOCAL] = run in this environment today. [UNVERIFIED] = needs the test. [DERIVED] = our arithmetic. Pass marks labelled "proposal" still need freezing in `docs/preregistration.md`.

---

## 1. How to read this plan

**Row IDs.** A letter for the tier, then the order in which to run the tests. The tiers are:

| Tier | What it needs |
|---|---|
| **A** | `HELIUS_API_KEY` (free plan) + List 1 only |
| **B** | The Helius Developer plan |
| **C** | Chainstack |
| **D** | Our own recorded tape (Phase 1) |
| **E** | List 2 |
| **F** | List 3 |
| **G** | List 4 (optional) |
| **H** | Offline (no network) |
| **I** | FORBIDDEN in Phase 0 |

**Test IDs** are the debate's own names. Some names repeat across files, so these prefixes are used (the same scheme as `docs/assumption-register.md` §2):

| Prefix | Meaning |
|---|---|
| **CF-T1–T11** | Chain-forensics round 1 (DESIGN's "T1/T4") |
| **QT-T1–T11** | Quant-tester round 1 (DESIGN's "T6/T7") |
| **SEC-S1–S8** | Security round 2 (DESIGN's key-vault "S1/S2/S3") |
| **SOC-S1–S8** | Social round 2 (the "X history test S1") |
| **AI-r1.n, EXE-r1.n, RSK-r1.n, SEC-r1.n, SOC-r1.n** | The unnumbered round-1 lists, in their file order |
| **FC1–FC9** | `docs/fee-model.md` §10 |
| **PX-1–PX-12** | `docs/costs.md` §11 |
| **STK-1–3** | `docs/tech-stack.md` §12 |

Every other ID (D, P, RC, R, X, Q, F, A, G) is unique as written. §5 maps **every** original ID to its row, so nothing is silently dropped.

**Rules for every Phase 0 script** (these hold for all rows):
1. **Allowed calls only (read-only):**
   - **JSON-RPC:** `getAccountInfo`, `getMultipleAccounts`, `getProgramAccounts` (with `dataSlice`), `getSignaturesForAddress`, `getTransaction`, `getBlock`, `getSlot`, `getBlockHeight`, `getLatestBlockhash`, `isBlockhashValid`, `getRecentPerformanceSamples`, `getRecentPrioritizationFees`, `getMinimumBalanceForRentExemption`, `getTokenSupply`, `getTokenLargestAccounts`; Helius `getTransactionsForAddress` and DAS `getTokenAccounts`.
   - **Websockets:** `slotSubscribe`, `accountSubscribe`, `programSubscribe`, `transactionSubscribe`, and their unsubscribes.
   - **Yellowstone gRPC:** `Subscribe`, `Ping`, `GetSlot`, `GetVersion`.
   - **Jito:** `getTipAccounts`; HTTP GET on the tip-floor endpoint.
   - **HTTP GET** on documentation pages.
2. **Never called:** `sendTransaction`, `sendBundle`, `simulateTransaction`, `simulateBundle`, `requestAirdrop`, any POST to Helius Sender, or any signing library. CI scans `phase0/scripts/` for these names and fails if one appears.
3. **Keys:**
   - read only from the environment;
   - never printed, logged or saved;
   - `api-key=` is redacted from every logged URL;
   - fixtures store responses only, never requests that contain a key.
4. **Rate limits:**
   - at most 8 requests/s on the Helius free plan (its limit is 10 [VERIFIED-SEARCH helius.dev/docs/billing/plans]);
   - DAS calls at most 1.5/s (limit 2);
   - exponential back-off on HTTP 429.
5. **Output:**
   - raw responses go to `fixtures/phase0/<row>/` with a `provenance.json` (method, redacted parameters, provider, slot, UTC time fetched, SHA-256);
   - one entry per row goes in `phase0/results.md`;
   - a blocked host is recorded as `BLOCKED: <host>`, never guessed.
6. **Languages** (docs/tech-stack.md §5k):
   - Python standard library for HTTP fetches;
   - Rust (`crates/feed/examples/`) for websocket and gRPC probes;
   - any decoding or fee maths runs offline in the Rust `decoders` / `fees` crates over the saved fixtures.
7. **Endpoints:**
   - Helius HTTPS: `https://mainnet.helius-rpc.com/?api-key=…`; websockets: `wss://mainnet.helius-rpc.com/?api-key=…` [UNVERIFIED format; confirm on docs.helius.dev in A24];
   - public RPC: `https://api.mainnet-beta.solana.com`;
   - Chainstack: from the three `CHAINSTACK_*` variables.

**What this session could reach (probed 2026-11-05):**

| Host | Result |
|---|---|
| `raw.githubusercontent.com`, `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`, `index.crates.io`, `static.crates.io`, `proxy.golang.org`, `nodejs.org` | **Reachable** |
| `api.github.com` | Reachable, but answered "GitHub access to this repository is not enabled for this session" for pump-fun/pump-public-docs |
| `mainnet.helius-rpc.com`, `api.mainnet-beta.solana.com`, `www.helius.dev` | **Blocked** [VERIFIED-LOCAL] |

---

## 2. Constants the tests use

| Name | Value | Tag |
|---|---|---|
| Pump program | `6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P` | [VERIFIED-DOC idl/pump.json `address`] |
| PumpSwap program | `pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA` | [VERIFIED-DOC idl/pump_amm.json] |
| Pump fee program | `pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ` | [VERIFIED-DOC idl/pump_fees.json] |
| Pump `Global` | `4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf` | [VERIFIED-DOC via DAT R1 P1] |
| `withdraw_authority` (in every migrate) | `39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg` | [VERIFIED-DOC via DAT R1 P1] |
| PumpSwap `GlobalConfig` | `ADyA8hdefvWN2dbGGWFotbzWxrAvLW83WG6QCVXvJKqw` | [VERIFIED-DOC via DAT-R] |
| PumpSwap FeeConfig / curve FeeConfig | `5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx` / `8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt` | [VERIFIED-DOC via docs/fee-model.md §4] |
| Event-call prefix (inner instruction data) | `e445a52e51cb9a1d` (little-endian form of sha256("anchor:event")[..8]) | [DERIVED; A04 confirms] |
| Event discriminators | `CreateEvent 1b72a94ddeeb6376`, `TradeEvent bddb7fd34ee661ee`, `CompleteEvent 5f72619cd42e9808`, `CompletePumpAmmMigrationEvent bde95db95c94ea94`, `PostCompleteBuyEvent 6fb06d8b316cd5fb`, `CreatePoolEvent b1310cd2a076a774`, `BuyEvent 67f4521f2cf57777`, `SellEvent 3e2f370aa503dc2a`, `BoostBuyAndBurnEvent 3f451c16305cc2b9` | [VERIFIED-DOC IDLs; each equals sha256("event:Name")[..8], computed locally] |
| Instruction discriminators | `migrate 9beae792ec9ea21e`, `migrate_v2 bbcb121fceedfe29`, `buy_v3 07051dc4f5176550`, `multi_hop_swap 2b644913e9f66f94`. `buy_v2 b817ee6167c5d33d` is **the same in both programs**, so always key on the program first | [VERIFIED-DOC IDLs] |
| IDL SHA-256 today | pump.json `7616681e…7207`, pump_amm.json `b7d8c57a…b89b`, pump_fees.json `6b9fa3ec…2b29` | [VERIFIED-LOCAL] |
| `virtual_quote_reserves` | **signed 128-bit** (`i128`) in PumpSwap `Pool`, `BuyEvent`, `SellEvent`, `BoostBuyAndBurnEvent` | [VERIFIED-DOC pump_amm.json] |

---

## 3. Budget for tier A [DERIVED; credits per method UNVERIFIED until A24]
- **About 90,000 calls in total.** The largest are:

  | Row | Calls |
  |---|---|
  | A16 (BOOST) | ~20k |
  | A29 (price per block) | ~15k |
  | A04 (10k transactions) | ~10k |
  | A13 (polls) | ~11k |
  | A30 | ~8k |
  | A31 | ~6k |
  | All other rows | under 3k each |

- At 1 credit per standard call [VERIFIED-SEARCH via CHN R1], plus premiums for `getBlock` and `getProgramAccounts`, that is **about 100–150k credits = 10–15% of the free plan's 1M a month**.
- At 8 requests/s, that is **about 3–4 hours** of request time.
- Two rows also poll keylessly for a while: A18 polls for 7 days and A23 listens for 24 h.
- **Run order:**
  1. The keyless rows (A18, A19, A20, A23, A24, A26, A27, A28) can start the moment List 1 is allowed, even before the key.
  2. Then A01–A09 (the Gate 0→1 core).
  3. Then the rest.

---

## 4. The table (one table, ordered by tier, then by run order)

| Row | Test ID(s) | Question | Exact read-only method | Domain(s) | Env var | Expected result | Pass / fail | Fallback if it fails |
|---|---|---|---|---|---|---|---|---|
| **TIER A** | **HELIUS_API_KEY (free) + List 1 only** | | | | | | | |
| A01 | **D1**, FC3 (Global part) | Are Pump's migration settings unchanged? | `getAccountInfo(Global, base64)`; decode with the pinned pump.json; read `withdraw_authority`, `enable_migrate`, `pool_migration_fee`, initial reserves; record the data length | mainnet.helius-rpc.com (else api.mainnet-beta.solana.com) | HELIUS_API_KEY | authority `39azUY…`, `enable_migrate = true`, fee 15,000,001 lamports [VERIFIED-DOC via DAT R1] | PASS: all match and every byte decodes. FAIL: anything differs | Re-point the backup filter and audit to the new authority, re-run A03, log `ADMIN_CHANGE` |
| A02 | **D7**, SEC-r1.4 (Pump part) | Can we see program upgrades? What is today's baseline? | For the 3 programs: `getAccountInfo(program, jsonParsed)` → `programData`; `getAccountInfo(programData, jsonParsed)` → `slot` (last deploy) and `upgradeAuthority`; compare the IDs with the IDL `address` fields | same | HELIUS_API_KEY | Upgradeable programs; recent deploy slots; authority set | PASS: 3/3 read and saved as regime tag v0 | Decode the loader account bytes ourselves; public RPC |
| A03 | **D2**, CF-T3, P1 (one-transaction share) | How does a migration look today, and does the `withdraw_authority` key catch every one? | `getSignaturesForAddress(39azUY…, limit 1000, paging with before=)` back 7 days. Then `getTransaction(sig, {encoding:"base64", maxSupportedTransactionVersion:0})`. Decode the inner event calls. Per transaction, count: `CompletePumpAmmMigrationEvent`, `CreatePoolEvent`, `PostCompleteBuyEvent` (synthetic), `CompleteEvent`; the signers; same-transaction complete + migrate + buy; slots from `CompleteEvent` to migration. Cross-check: 50 random `CompleteEvent`s from Pump-program signatures must each map to a migration | mainnet.helius-rpc.com | HELIUS_API_KEY | ~200 a day [UNVERIFIED]; both events in every success; some non-Pump signers; some one-transaction migrations; synthetic share > 0 | PASS: 100% of successful migrations carry both events and the authority; 50/50 cross-checks found. FAIL: any migration without the authority (a blind spot) | Make "CompleteEvent → derived pool" (DAT-6 key 2) the primary audit, and re-run |
| A04 | **D5** | Are events always inner event calls? How often are logs cut off? | 10,000 recent Pump + PumpSwap transactions (`getSignaturesForAddress` on each program + `getTransaction`, json): count "Log truncated" in `logMessages`; for each trade instruction, check the matching inner event call (prefix `e445a52e51cb9a1d`) | mainnet.helius-rpc.com | HELIUS_API_KEY | Truncation rare but > 0; events present 100% | PASS: 100% of successful trades have the inner event | Add a "Program data:" log fallback decoder with its own alarm |
| A05 | **CF-T1**, D16, R9, FC5 | What kind of token is a Pump coin today? | 100 recent `create_v2` mints + 20 legacy `create` mints (from A04): `getAccountInfo(mint, jsonParsed)` → token program, mint and freeze authorities, extensions; data length of 5 holders' token accounts; share of graduates on each token program; per coin, count plain `transfer` vs `transferChecked` | mainnet.helius-rpc.com | HELIUS_API_KEY | `create_v2` = Token-2022; authorities null; only metadata-pointer/metadata extensions [UNVERIFIED]; plain transfers present | PASS: authorities null on 100%; no transfer hook, permanent delegate or transfer fee. FAIL: add a coin-safety veto before Phase 3 | Public RPC |
| A06 | **CF-T4** | Is the migrated pool the canonical one, and is its LP burned? | 20 migrations from A03: derive the pool address from seeds `["pool", u16 0, creator, base_mint, quote_mint]` [VERIFIED-DOC PUMP_SWAP_README via DAT-R]; compare with the event's `pool`; decode `Pool` (`index`, `lp_supply`); `getTokenSupply` + `getTokenLargestAccounts` on `lp_mint`; check the LP burn in the migration's token-balance changes | mainnet.helius-rpc.com | HELIUS_API_KEY | index 0; addresses equal; LP burned in the same transaction | PASS: 20/20 | Learn and pin the creator used for migrated pools (DAT-6), then re-derive |
| A07 | **RC4**, RC3 | How many pool layouts exist? Is `virtual_quote_reserves` live and signed? | RC4: `getProgramAccounts(PumpSwap, {dataSlice:{offset:0,length:8}})` → count by discriminator and data length; if the length isn't returned, repeat with `filters:[{dataSize:N}]` for each candidate N. RC3: 200 pools from A03 via `getMultipleAccounts` (100 per call); decode `virtual_quote_reserves` (i128); split during vs after BOOST | mainnet.helius-rpc.com | HELIUS_API_KEY | ≥ 2 lengths (older, shorter layouts read missing fields as 0 [VERIFIED-DOC via RT-R]); non-zero and negative values present | PASS: every observed length is in our allowed-lengths table and decodes exactly. FAIL: add a reviewed version entry | If `getProgramAccounts` is refused or too costly: take lengths from A03's pools only |
| A08 | **QT-T5**, FC1, FC2, FC3, FC4, FC8, EXE-r1.2 (config, depth, rent) | Do the live fee settings, opening pool sizes and deposits match `docs/fee-model.md`? | `getAccountInfo` on FeeConfig `5PHirr8…` (diff against the 2026-09-08 capture), GlobalConfig (`disable_flags`, `boost_enabled`, buyback fields), curve FeeConfig `8Wf5Ti…`; vault balances of 50 fresh pools (`getMultipleAccounts`); `getMinimumBalanceForRentExemption(165)` and `(170)`; the SIMD-0437 gate accounts; `user_volume_accumulator` length for 3 wallets | mainnet.helius-rpc.com, raw.githubusercontent.com | HELIUS_API_KEY | Matches fee-model §2–4 | PASS: every field equals fee-model's values, or the module is updated and versioned **before** A09 | Public RPC |
| A09 | **QT-T6 = the Gate 0→1 test**, FC6, FC7, D12 (reserve semantics), X6, Q1, RSK-r1.3 | Do our fee and price maths reproduce real trades to the lamport? | Exactly as `docs/fee-model.md` §7: a frozen seed; 50 calibration trades (FC7: before/after reserves, buyback rounding, exact-in leftover, boost state); then 500 scored trades from ≥ 100 canonical SOL pools over ≥ 7 days, meeting every stratum; fetched with `getSignaturesForAddress(pool)` + `getTransaction`; saved as fixtures; scored **offline** by the Rust `fees` crate against the event fields and vault balance changes; ≥ 100 network-fee checks, ≥ 30 of them failed (FC6). Optional: SDK referee vectors from `@pump-fun/pump-swap-sdk` (pinned, 7-day cooldown) | mainnet.helius-rpc.com, registry.npmjs.org | HELIUS_API_KEY | Exact | PASS: fee-model checks P1–P7 all hold (500/500, no tolerance). FAIL: fix, bump the model version, re-run on a **fresh** 500 | If the free plan's history is too shallow or too slow: Chainstack RPC (tier C), or wait for the recorder (fee-model §7) |
| A10 | **P6**, SEC-S4 (mainnet-history part) | Does PumpSwap allow a payout account owned by someone other than the signer? | 1,000 historical PumpSwap buys and sells: user base/quote token accounts from the instruction's accounts; their owner from `pre/postTokenBalances[].owner`; compare with the signer | mainnet.helius-rpc.com | HELIUS_API_KEY | Some exist (no owner check) [UNVERIFIED] | Measurement. Any count > 0 confirms the guard's output pinning is the only defence (already the design) | None needed |
| A11 | **X2**, Q4, FC9, EXE-r1.2 (swaps, priority fees) | How much compute do trades use? What do failed buys look like? | From A09's fixtures + 200 more: `computeUnitsConsumed` per instruction type (curve v1/v2/v3, pool v1/v2, buy/sell/exact-in); failure share and error codes (count 6004); 100 failed 6004 buys: decode the requested amount and limit, check that no event was emitted; v2 trades on mayhem pools (FC9); `getRecentPrioritizationFees([PumpSwap, pool])` every 60 s for 1 h | mainnet.helius-rpc.com | HELIUS_API_KEY | Compute well under 200k; failed transactions carry arguments but no events | PASS: compute p99 per type recorded (proposed compute limit = p99 × 1.2); ≥ 95% of failed buys decodable. FAIL: the losers'-tape idea (QNT-E1) loses its price-limit feature | n/a |
| A12 | **D6 (lite)**, QT-T7 (slot time), EXE-r1.2 (performance samples) | How long is a slot today? How far is "processed" ahead of "confirmed"? | `getRecentPerformanceSamples(60)`; websocket `slotSubscribe` for 1 h (time between slots); `getSlot` at processed vs confirmed, 5 times a second for 10 min | mainnet.helius-rpc.com (https + wss) | HELIUS_API_KEY | ~200 ms target, ~218 ms measured [VERIFIED-SEARCH solanacompass via RT-R]; gap ≤ 1 slot | PASS: medians recorded; every slot-based timer re-derived. Flag if the median slot is > 300 ms | Public RPC; the full version is C03 |
| A13 | **RC2 (lite)**, RSK-r1.2 | How fresh is each exit-price source we can reach without Chainstack? | 3 active pools in a busy hour: Helius websocket `accountSubscribe` on both vaults (processed and confirmed) vs `getMultipleAccounts` polled twice a second on Helius vs once a second on the public RPC; log `context.slot` and the receive time per update; order by slot (Helius websocket updates can arrive out of order [VERIFIED-SEARCH via DAT-R]) | mainnet.helius-rpc.com, api.mainnet-beta.solana.com | HELIUS_API_KEY | Websocket within 1 slot of the freshest; polls 1–3 slots behind | PASS (lite): websocket ≤ 2 slots behind the freshest source at p95. The real pass mark is C07 | Drop the public-RPC leg if rate-limited |
| A14 | **X3** | How long does a blockhash stay usable? | Every 10 s for 1 h: `getLatestBlockhash(confirmed)` → `lastValidBlockHeight`; `getBlockHeight`; `isBlockhashValid` on hashes aged 100/130/140/150 blocks | mainnet.helius-rpc.com | HELIUS_API_KEY | ~150 blocks ≈ 33 s [UNVERIFIED, rulings C8] | PASS: window measured; exit-ticket expiry set below it with a margin | Public RPC |
| A15 | **RC8** (rulings R2 drill) | Would the sells-only auto-adopt rule have adopted Pump's Sep 1 2025 change, and refused 5 hostile diffs? | `git clone https://github.com/pump-fun/pump-public-docs`; `git log --since=2025-08-15 --until=2025-09-15 -p -- idl/`. Run our IDL-diff checker (R2 checks 1–3, offline) on the real diff and on 5 synthetic hostile diffs (an unseeded writable account, an added signer, a changed output account, a new program ID, a removed account). Check 4 becomes **historical replay**: read 5 real sells after the change and confirm the added accounts. No simulation | github.com, api.github.com, raw.githubusercontent.com, mainnet.helius-rpc.com | HELIUS_API_KEY (replay part only) | Adopts 1/1, refuses 5/5 | PASS: 1/1 adopted **and** 5/5 refused. FAIL: fix the rule before Phase 3 | api.github.com was gated today. If `git clone` also fails: fetch both IDL versions from raw.githubusercontent.com by commit SHA, or use t.me/s/pump_tech_updates/29 [VERIFIED-SEARCH via RT-A] for the account list |
| A16 | **R2**, F4, X7 | What does BOOST look like on-chain? | 50 graduates from A03: pool signatures for the first 10 min + `getTransaction`; decode `BoostBuyAndBurnEvent` and `InitBoostEvent`: spacing, size, whether `boost_vault_remaining` reaches 0, the authority wallet, buy-and-burn in one transaction, net flow ±2 min around the last one; also `GlobalConfig.boost_enabled` | mainnet.helius-rpc.com | HELIUS_API_KEY | ~17.6 SOL over ~5 min [VERIFIED-SEARCH kucoin; not confirmed as fixed]; vault reaches 0 | PASS: schedule described on 50/50; graduates without BOOST counted as their own group (rulings R5) | n/a |
| A17 | **P4**, X1 (winning tips) | What do winners tip at migration, and how many buys compete? | 100 migrations: `getBlock(slot, {transactionDetails:"full", maxSupportedTransactionVersion:0, rewards:false})` for slots +0…+3; transfers to the Jito tip accounts (from A19); landed buys on the new pool; bundle membership via the Jito lookup (A20) | mainnet.helius-rpc.com, bundles.jito.wtf, explorer.jito.wtf | HELIUS_API_KEY | High tips at +0/+1 [UNVERIFIED] | Measurement: tip p50/p75/p95 and competing-buy counts; feeds the race/no-race memo (rulings C15) | If `getBlock` is costly: use 30 migrations, or the Chainstack RPC (C08) |
| A18 | **X1**, EXE-r1.3, QT-T8 | What is Jito's tip floor, and does a failed bundle pay nothing? | `GET https://bundles.jito.wtf/api/v1/bundles/tip_floor` once a minute for 7 days (no key); read docs.jito.wtf for the minimum tip, "no fee on failure" and rate limits | bundles.jito.wtf, docs.jito.wtf | none | Minimum 1,000 or 5,000 lamports (Helius pages conflict [VERIFIED-SEARCH via fee-model]) | PASS: 7 days logged with < 1% gaps; the docs state the failure rule | explorer.jito.wtf |
| A19 | **Q5**, SEC-S7, X4, EXE-r1.4 | Which tip accounts are official? How does Helius Sender's protection work? | Jito JSON-RPC `getTipAccounts` via POST to `https://mainnet.block-engine.jito.wtf/api/v1/getTipAccounts` [path UNVERIFIED; confirm on docs.jito.wtf]; the Sender docs: tip accounts, minimum tip, regions, `mev-protect` in Max mode; `GET https://sender.helius-rpc.com/ping` ×100 for latency only | mainnet.block-engine.jito.wtf, docs.jito.wtf, docs.helius.dev, www.helius.dev, sender.helius-rpc.com | none | 8 Jito tip accounts (rulings NEW-16) | PASS: lists captured with URL and date, then pinned in config | The Nozomi part is F08 |
| A20 | **CF-T11** | How often are create transactions bundled? | Jito bundle lookup by transaction signature for 50 creates (endpoint from docs.jito.wtf [UNVERIFIED]); hit rate, rate limits | bundles.jito.wtf, explorer.jito.wtf, docs.jito.wtf | none | Some are bundled | Measurement; feeds crew fingerprints (CHN-B) | n/a |
| A21 | **F5** | Do launch crews reuse lookup tables? | Early-buy transactions from A04/A16: `message.addressTableLookups`; count reuse of each table across launches; `getAccountInfo(table)` once per new table (its authority) | mainnet.helius-rpc.com | HELIUS_API_KEY | Some reuse | Measurement. Proposal: CHN-B keeps the feature if ≥ 1 table is reused across ≥ 5 launches | n/a |
| A22 | **A8 (step 1)**, SOC-S3 (host part) | Where does Pump coin metadata live? | Tabulate the `uri` host of 1,000 `CreateEvent`s from A04. **No fetching** | (data from A04) | HELIUS_API_KEY | A few gateway hosts | PASS: host list written and added to List 2 | n/a |
| A23 | **D9**, D14, EXE-r1.6 (PumpPortal part) | Does PumpPortal offer a keyless migration feed, and is it complete? | Read pumpportal.fun's docs (data API, fees, who holds the Lightning key). Open `wss://pumpportal.fun/api/data`; send `{"method":"subscribeNewToken"}` and `{"method":"subscribeMigration"}` with **no key**; log 24 h; match each message to truth from cheap polling of the authority on Helius | pumpportal.fun, mainnet.helius-rpc.com | none (never create a key, rulings C16) | `subscribeMigration` exists without a key [UNVERIFIED] | PASS: a keyless channel delivers ≥ 99% of the day's migrations (synthetic included), so it stays as a tripwire. FAIL: PumpPortal is dropped (allowed by DAT-7) | Drop it |
| A24 | **D15**, P12, R8, G5, G8, PX-2 | What does each Helius method cost? How do separate keys and autoscaling behave? | Read www.helius.dev/docs/billing (credits, plans, rate limits, autoscaling) and docs.helius.dev. Price every consumer in rulings §6d: `getSignaturesForAddress`, `getTransaction`, `getBlock`, `getTransactionsForAddress`, `getMultipleAccounts`, `getProgramAccounts`, DAS, `funded-by`, websocket MB, `accountSubscribe`/`programSubscribe`, Enhanced websockets. Also: limits per key; behaviour at the autoscale cap; the websocket host | www.helius.dev, docs.helius.dev | none | 1 credit per standard call; 20 credits per MB streamed; `funded-by` 100; free 1M / Developer 10M; 10 vs 50 requests/s [VERIFIED-SEARCH] | PASS: every §6d line priced from the docs; worst case ≤ 10M + cap. FAIL: re-plan the meter | Measure in A25 |
| A25 | **CF-T2**, F6 | What do forensics lookups really cost, and how fast are they? | 50 migrated coins: p50/p95 latency and call count for `getTokenLargestAccounts`, `getMultipleAccounts` (top holders), `getSignaturesForAddress(holder)`, and a full holder scan with DAS `getTokenAccounts` (paged). Credits from the dashboard's usage before/after (Paul reads one number), or a usage API if A24 finds one | mainnet.helius-rpc.com | HELIUS_API_KEY | DAS ~10 credits a page [VERIFIED-SEARCH, low confidence]; free DAS limit 2/s [VERIFIED-SEARCH] | PASS: cost per graduate fits the 100k credits/day forensics cap at ~200–300 graduates a day | Narrow the scan to top holders |
| A26 | **PX-1**, PX-2, D10 (Helius and Chainstack part) | Are the two main vendors' prices still what the budget assumes? **Does Chainstack's $49 add-on buy 1 stream or 2?** | Read chainstack.com/pricing, /products/yellowstone-grpc and the docs.chainstack.com changelog; www.helius.dev/pricing and /docs/billing/plans | chainstack.com, docs.chainstack.com, www.helius.dev | none | $49 + $49 with 2 streams; Helius $49 / 10M / $5 per extra 1M | PASS: matches costs.md U1–U4. FAIL: costs.md flag F3 (merge filters into one stream, or take the $149 tier) | Paul reads the price in his dashboard |
| A27 | **G4 (docs)**, D13 (docs) | What request allowance and `getBlock` cost does Chainstack Growth have? Which Yellowstone filters does it support, with what limits? | Read docs.chainstack.com: request units, Solana requests/s, support for `token_accounts` and `cuckoo_account_include`, accounts per filter, filters per stream | chainstack.com, docs.chainstack.com | none | 20M request units [VERIFIED-SEARCH via costs.md U1]; filter support UNVERIFIED | PASS: documented, so the C02 plan is set | Measure in C02 / C08 |
| A28 | **PX-11**, EXE-r1.8 | What are the SOL price and exchange rates for the money tables? | `GET https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd,cad` daily; Bank of Canada rates | api.coingecko.com; www.bankofcanada.ca (**not on any list yet**) | none | SOL ≈ $100 [VERIFIED-SEARCH, Oct 2026] | Recorded monthly in costs.md | api.jup.ag/price/v3 (List 4) |
| A29 | **P1 (pilot)** | How fast does the price move in blocks 0–20 after a pool opens? | 100 post-BOOST graduations from A03: every pool transaction in slots +0…+20 (`getSignaturesForAddress(pool)` + `getTransaction`); price per block from `BuyEvent`/`SellEvent` | mainnet.helius-rpc.com | HELIUS_API_KEY | Large early moves; synthetic migrations open pre-moved [VERIFIED-DOC SYNTHETIC_MIGRATION] | Pilot only (sizes D03); no pass mark | n/a |
| A30 | **RC1 + X5 (pilot)** | How crowded is the end of BOOST? What share of transactions fail in a new pool's first 5 min? | 20 graduates: pool signatures include failed ones (`err` set). Per slot, from −60 s to +180 s around the last `BoostBuyAndBurnEvent`: landed buys, failed buys, priority fee per compute unit; tips from `getBlock` on 5 of them | mainnet.helius-rpc.com | HELIUS_API_KEY | Varies | Pilot only (sizes D02) | n/a |
| A31 | **F1 + P5 (pilot)** | How do dumping insiders get their tokens? | 20 coins that fell ≥ 50% within 60 min (from A29): the biggest sellers' token inflows (`getSignaturesForAddress(wallet)` + `getTransaction`, token-balance changes): bought vs plain transfer, number of hops, time from transfer to sell | mainnet.helius-rpc.com | HELIUS_API_KEY | A real share arrives by transfer [UNVERIFIED] | Pilot only. The fixed early kill (< 10% by plain transfer drops the "follow" part of idea 4) is applied on 200 coins in D06 | n/a |
| A32 | **F3 (our own lookup)** | What does our own funding lookup cost? | 200 early-buyer wallets: the oldest page of `getSignaturesForAddress(wallet)` + `getTransaction` of the first SOL inflow → the funder; calls and latency | mainnet.helius-rpc.com | HELIUS_API_KEY | ~3 credits per lookup [DERIVED, CHN-R] | PASS (proposal): median ≤ 5 credits and p95 ≤ 2 s | n/a |
| **TIER B** | **Helius Developer plan ($49; Paul upgrades in Phase 1); still List 1** | | | | | | | |
| B01 | **F2 (Helius leg)** | Can Helius `transactionSubscribe` watch 2,000 token accounts cheaply? | Enhanced websocket `transactionSubscribe` with `accountInclude` = 2,000 watched token accounts, for 24 h: accepted? delay vs block time; credits per MB; does a plain transfer include the mint? | Websocket host from docs.helius.dev (mainnet.helius-rpc.com, or a host to add) | HELIUS_API_KEY (Developer) | Up to 50k addresses [VERIFIED-SEARCH via CHN-R] | PASS: accepted; p95 delay ≤ 2 slots vs C02; credits inside rulings §6d | Chainstack `token_accounts` (C02) |
| B02 | **CF-T5**, F3 (`funded-by` part) | Is Helius `funded-by` worth 100 credits a call? | `GET https://api.helius.xyz/v1/wallet/{w}/funded-by` [path UNVERIFIED] for A32's 200 wallets: hit rate, latency, agreement with our own lookup | api.helius.xyz | HELIUS_API_KEY (paid) | Needs a paid plan [VERIFIED-SEARCH via CHN-R] | PASS for our own lookup: agreement ≥ 95% means we keep ours and use `funded-by` only for accuracy samples | Our lookup only |
| **TIER C** | **Chainstack account + its gRPC host added to Allowed domains** | | | | | | | |
| C01 | **D4**, Q2, D11, RC6, P11, STK-1 | How much data is the full firehose, and does our recorder keep up? | Yellowstone `Subscribe`: transactions `{account_include:[Pump, PumpSwap, fee program], vote:false, failed:true}`, processed, plus slots. Run 1 h each of: (a) that filter, (b) the 8 tip accounts, (c) the Token-2022 program. Measure protobuf MB/hour, messages/s p50/p99, zstd bytes/hour, and the recorder's CPU and memory (STK-1) | Chainstack gRPC host | CHAINSTACK_GRPC_ENDPOINT, CHAINSTACK_GRPC_TOKEN | 15–135 GB a month raw [UNVERIFIED, DAT-8] | PASS: 1 h with no throttling or forced disconnect; projected disk fits 200 GB + archive; recorder ≥ 10× headroom at p99 (STK-1). Part (c) decides whether Token-2022 joins the firehose (NEW-16) | If throttled: Solana Tracker €200 (DESIGN high case) |
| C02 | **D13**, F2 (Chainstack leg) | Can Chainstack watch wallets through their token balances, and what are its limits? | Subscribe with `account_include` of 2,000 wallets + `token_accounts: BALANCE_CHANGED`; repeat with `cuckoo_account_include`; record accept/reject text, delay, MB | Chainstack gRPC host, docs.chainstack.com | CHAINSTACK_* | UNVERIFIED | PASS: accepted for ≥ 2,000 wallets with ≤ 2-slot p95 delay, so Chainstack does the wallet watch. FAIL: use B01 | B01 |
| C03 | **D6 (full)** | How many dead blocks are there, and how long from processed to confirmed? | Slots stream at all commitment levels for 24 h: count `SLOT_DEAD`; processed→confirmed delay per slot; slot-length distribution | Chainstack gRPC host | CHAINSTACK_* | About 1 slot; a few dead per day | Measured; confirms "pre-arm on processed, buy on confirmed" | A12's numbers |
| C04 | **D8** | After a 60 s disconnect, does `from_slot` replay fill the gap? | Stop the client for 60 s, reconnect with `from_slot` = last slot seen; compare with the gap's signatures from Helius (authority + 5 busy pools) | Chainstack gRPC host, mainnet.helius-rpc.com | CHAINSTACK_*, HELIUS_API_KEY | Depends on the provider [UNVERIFIED] | PASS: 100% of the gap's transactions replayed. FAIL: the Helius backfill job covers it (already the design) | Backfill |
| C05 | **D3** | Over 72 h with all feeds side by side, when does each migration arrive, and which feed misses any? | Chainstack firehose; Helius Enhanced `transactionSubscribe` requiring `withdraw_authority` (Developer plan); PumpPortal keyless; an audit every 5 min (`getSignaturesForAddress` or `getTransactionsForAddress` on the authority) | Chainstack gRPC host, mainnet.helius-rpc.com, pumpportal.fun | CHAINSTACK_*, HELIUS_API_KEY (Developer) | Chainstack first | PASS: the union equals the audit (100%); Chainstack ≥ 99.5% (Gate 1 target); each feed's lag p50/p95 recorded | Name the missing class, fix the filter or decoder, re-run 24 h |
| C06 | **Q3**, D12 (index) | Is Yellowstone's `index` the position in the block? | 100 streamed transactions: compare `index` with their order in `getBlock(slot)` from the Chainstack RPC | Chainstack gRPC + RPC hosts | CHAINSTACK_* | Equal [UNVERIFIED] | PASS: 100/100, so `index` drives last-in-block fills. FAIL: take block order from `getBlock` | `getBlock` |
| C07 | **RC2 (full)**, G3 | During crashes, does the guard's Helius stream lag the bot's Chainstack stream? | ≥ 50 recorded `FAST_DUMP`s: Helius `transactionSubscribe` + `accountSubscribe` on ≤ 3 pools vs the Chainstack stream; slot and receive-time difference per update; plus `getMultipleAccounts` | mainnet.helius-rpc.com, Chainstack gRPC host | HELIUS_API_KEY (Developer), CHAINSTACK_* | ≤ 2 slots | PASS: ≤ 2 slots at p95 (rulings R3). FAIL: the guard gets a second stream before any canary | Second stream |
| C08 | **G4 (measured)**, PX-1 (over the allowance) | Does block capture fit inside Chainstack's included requests? | Count our requests during C01–C07 (≈ 20 `getBlock` per migration) against the dashboard | Chainstack RPC host, chainstack.com | CHAINSTACK_RPC_URL | Within 20M units | PASS: fits, so block capture uses Chainstack (rulings §6d) | Use the Helius optional-consumer budget |
| **TIER D** | **Needs our own recorded tape (Phase 1), plus the domains shown** | | | | | | | |
| D01 | **QT-T1**, Q6 | Does our daily graduation count match an independent count? | 14 days of recorder counts vs Dune or a public dashboard; spot-check 20 rugged coins | recorder; dune.com, api.dune.com (List 2) | DUNE_API_KEY (optional) | Within 0.5% | PASS: ≤ 0.5% difference every day | The Helius audit as the independent count |
| D02 | **RC1**, X5 (full) | How crowded is BOOST's end (300 graduates)? What share fails in the first 5 min? | Tape including failed transactions, plus block capture | recorder | none | Per rulings R5's definitions | Sets the baseline for the crowding kill rule; feeds the landing model | n/a |
| D03 | **P1 (full)** | Price per block, blocks 0–20, on 500 post-BOOST graduations | Tape | recorder | none | n/a | Feeds the lateness curve and the race memo | Helius history |
| D04 | **P2**, R2 (full) | BOOST study: entries at 60/300/330/600/900 s vs buy-every-graduate | Tape (Dune optional) | recorder, dune.com | none | n/a | Per `docs/preregistration.md` | n/a |
| D05 | **P3** | Buy-every-graduate and random baselines after all costs, 60–90 days | Tape + Helius history including dead coins | recorder, mainnet.helius-rpc.com | HELIUS_API_KEY | n/a | Input to the week-4 stop checkpoint (DESIGN §8) | Dune |
| D06 | **F1**, P5 (full) | Of 200 `INSIDER_DUMP` coins, what share of dumped tokens arrived by plain transfer? | Tape + Helius lookups | recorder, mainnet.helius-rpc.com | HELIUS_API_KEY | n/a | Early kill: under 10% drops the "follow" part of idea 4 (DESIGN §3b) | n/a |
| D07 | **CF-T10** | Over one week of graduations, how often does each gate check catch a dump or raise a false alarm, ours vs the vendors'? | Tape + vendor APIs (G01–G04) | recorder; List 4 hosts | vendor keys | n/a | Per preregistration | Our checks only |
| D08 | **P14**, EXE-r1.9 | How often are PumpSwap sells sandwiched, and how much is lost, by slippage setting? | Our own tape; Dune optional | recorder; dune.com | DUNE_API_KEY (optional) | n/a | Evidence for the sell margin | n/a |
| D09 | **RC5** | Alarm rate per class, with the monitors log-only for 7 days | Monitors | recorder host | none | ≤ 1 phone alert a week in calm periods | PASS per NEW-9 | Retune thresholds |
| D10 | **RC7** | Qualifying entries per day under the merged primary rule | Tape | local | none | ≥ 5 a day or ≥ 30% of graduates | Gate qualifier (rulings §4c) | n/a |
| D11 | **R1**, RSK-r1.1 | Gap study: how far stops slip, by minute since migration | Tape (+ Helius history) | recorder | none | n/a | Sets the stop grid | Helius history |
| D12 | **R3–R5** | Kill tests for RSK-E1, E2, E3 | Tape (+ Dune) | recorder, dune.com | none | n/a | Per preregistration | n/a |
| D13 | **SOC-S3**, A8 (fetch rate) | Theme-wave detector on the tape; metadata fetch rate | Tape + the metadata gateway (E07) | recorder + gateway host | none | n/a | Idea 5's pass marks (DESIGN §3b) | Code-only (names and tickers) |
| D14 | **SOC-S4**, SOC-r1.7 (labels) | Does following, fading or ignoring KOL wallets (at 2/10/60 s delays) beat buy-every-graduate? | Tape + seed labels | recorder, kolscan.io, gmgn.ai (List 4) | none | n/a | Per preregistration | Public seed lists only |
| D15 | **SOC-S5** | Bait detector: are side wallets funded and then sold from? | gRPC wallet watch + funding lookups | Chainstack gRPC host, mainnet.helius-rpc.com | CHAINSTACK_*, HELIUS_API_KEY | n/a | Fewer than 50 events in 60 days kills it (DESIGN) | n/a |
| **TIER E** | **List 2** | | | | | | | |
| E01 | **A1**, AI-r1.1 | How fast do AI label calls return? | 200 streaming calls at `low` effort on Haiku 5.5; 50 each on Sonnet, Opus and Fable: time to first token p50/p95/p99, output tokens, `cache_read_input_tokens` | api.anthropic.com | ANTHROPIC_API_KEY | ~6 s to start on the big models (DESIGN decision 15) | Measured; labels stay in shadow either way | n/a |
| E02 | **A2**, AI-r1.3 | Do labels repeat? (50 coins × 5 calls) | Same | api.anthropic.com | ANTHROPIC_API_KEY | n/a | Agreement threshold per AI-R | Drop the label |
| E03 | **A3**, AI-r1.4 | Refusal rate on 500 real samples, and whether refused coins form a skewed group | Same | api.anthropic.com | ANTHROPIC_API_KEY | n/a | A refusal = "no decision" | n/a |
| E04 | **A4**, AI-r1.5 | Can injected text change the labels? (50 hostile samples; false flags on 1,000 coins) | Same | api.anthropic.com | ANTHROPIC_API_KEY | 0/50 changed | PASS: 0/50 | Stricter filtering |
| E05 | **A5**, AI-r1.2 | Real token counts | `/v1/messages/count_tokens` | api.anthropic.com | ANTHROPIC_API_KEY | n/a | Replaces the estimates | n/a |
| E06 | **A6** | What do the two papers say predicted success? | Read arXiv 2602.14860 and 2601.08641 | arxiv.org | none | n/a | Notes only | n/a |
| E07 | **A8 (step 2)**, SOC-S3 (fetch) | How fast and how big are metadata fetches? | Sandboxed GET with size and time limits on 200 URIs | gateway host(s) from A22 | none | n/a | Proposal: p95 < 2 s, < 1 MB | Names only |
| E08 | **A9** | How fast are local text embeddings for 30,000 texts a day? | Model download, then offline | huggingface.co | none | n/a | Proposal: ≤ 30 min a day on the bot host | String similarity only |
| E09 | **A10**, AI-r1.6 | Third-party latency charts | Read the pages | artificialanalysis.ai | none | n/a | Cross-check for E01 | n/a |
| E10 | **R10** | BOOST schedule write-up | Read | onchaindivers.substack.com | none | n/a | Notes; A16 is the primary source | n/a |
| E11 | **QT-T2** | Does Dune show v2 trades correctly, with `virtual_quote_reserves` signed? | Dune query | dune.com, api.dune.com | DUNE_API_KEY | n/a | Decides whether Dune can cross-check at all | Skip Dune |
| E12 | **PX-8** | Anthropic prices, batch discount, cache cost, spend-limit behaviour | Read | platform.claude.com | none | Matches costs.md U15 | PASS if it matches | Update costs.md |
| **TIER F** | **List 3** (mostly Phase 3; **F01 is needed before Phase 1**) | | | | | | | |
| F01 | **G7**, PX-6, PX-7 | Which provider for the bot server: Frankfurt price, terms that allow bots, how narrowly tokens can be limited, disk prices? | Read pricing and terms pages | www.vultr.com, www.digitalocean.com | none | ~$48 shared / $86–126 dedicated (costs.md U6–U7) | Pick a provider **before Phase 1** | A second provider |
| F02 | **P9**, SEC-S6 | 12-month incident history of the stream, RPC and signer vendors | Read status pages | status.helius.dev, status.chainstack.com, health.aws.amazon.com, status.privy.io | none | n/a | Input to the risk table | isdown.app via search |
| F03 | **SEC-S2** | Does KMS support Ed25519 multi-Region keys? What is the raw-signing size limit? | Read the docs | docs.aws.amazon.com | none | n/a | Decides the second-region standby | n/a |
| F04 | **SEC-S3** | Can an IAM policy allow only `kms:DisableKey` on one key, with role access and no stored secret? | Docs, then Paul's AWS sandbox (Phase 3) | docs.aws.amazon.com, iam.amazonaws.com | Paul's AWS account (Phase 3) | n/a | The policy works | n/a |
| F05 | **G1** | Does EC2 auto-recovery work for t4g in eu-central-1, and how fast? | Docs, then a sandbox instance (Phase 3) | docs.aws.amazon.com, ec2.eu-central-1.amazonaws.com | Phase 3 | n/a | n/a | n/a |
| F06 | **G2** | DynamoDB/SSM read latency and conditional writes, read every 2 s | Phase 3 | dynamodb / ssm .eu-central-1.amazonaws.com | Phase 3 | n/a | n/a | n/a |
| F07 | **G6**, PX-10 | Which dead-man's-switch alert service, with phone push? | Read pricing and docs | healthchecks.io, betterstack.com, cronitor.io, pushover.net, ntfy.sh (**not on any list yet** [UNVERIFIED hosts]) | none | n/a | Pick one | n/a |
| F08 | **EXE-r1.5**, SEC-S7 (Nozomi part) | Temporal/Nozomi tips, tip accounts and pricing | Read | use.temporal.xyz, dashboard.nozomi.temporal.xyz | none | n/a | n/a | n/a |
| F09 | **PX-4**, PX-5, SEC-r1.3 (KMS part) | AWS Frankfurt prices for the guard pair, disks, IPv4 and KMS | Read | aws.amazon.com, docs.aws.amazon.com, calculator.aws (**not on any list yet**) | none | Total ≤ $48 a month | PASS ≤ $48 | Update costs.md |
| **TIER G** | **List 4 (optional; extra keys and some of Paul's answers)** | | | | | | | |
| G01 | **CF-T6**, F7 | Does RugCheck have a fresh report at +0/+5/+30/+60/+300 s? | GET reports | api.rugcheck.xyz | none (free tier) | n/a | Comparison only (DESIGN decision 17) | n/a |
| G02 | **CF-T7** | GoPlus `token_security` coverage and cost on new coins | GET | api.gopluslabs.io, gopluslabs.io | none | n/a | Comparison only | n/a |
| G03 | **CF-T8** | Birdeye `token_security` latency and cost | GET | public-api.birdeye.so, docs.birdeye.so | BIRDEYE_API_KEY (new; not in the Setup checklist) | n/a | Comparison only | n/a |
| G04 | **CF-T9** | Solana Tracker's risk object; the Mayhem agent wallet | GET + docs | data.solanatracker.io, pump.fun (docs) | Solana Tracker key (new) | n/a | Comparison only | n/a |
| G05 | **QT-T3** | Bitquery: full history of a coin that rugged 60+ days ago | GraphQL | graphql.bitquery.io, bitquery.io | Bitquery key (new) | n/a | Optional history source | Our recorder |
| G06 | **QT-T4** | Birdeye candles of a dead coin | GET | public-api.birdeye.so | BIRDEYE_API_KEY | n/a | Optional | n/a |
| G07 | **QT-T9** | BigQuery freshness, as a $0 dry run | `bq query --dry_run 'SELECT MAX(block_timestamp) …'` | bigquery.googleapis.com | Google Cloud credentials (the `bq` tool is installed here, but we have no project) | n/a | Optional | n/a |
| G08 | **QT-T10** | Old Faithful epoch size and download speed | HEAD/GET | files.old-faithful.net, docs.old-faithful.net | none | n/a | Last-resort history | n/a |
| G09 | **D10 (others)**, QT-T11, PX-3, SOC-S7, EXE-r1.7, SEC-r1.3 (Turnkey/Privy) | Re-check the other vendors' prices | Read pricing pages | docs.solanatracker.io, www.solanatracker.io, shyft.to, docs.shyft.to, pumpportal.fun/data-api/pump-swap, docs.birdeye.so, bitquery.io/pricing, dune.com/pricing, docs.x.ai, docs.bloxroute.com, www.turnkey.com, www.privy.io | none | costs.md values | Update costs.md | n/a |
| G10 | **P7**, SEC-r1.4 (Jupiter IDs) | How does Jupiter's `destinationTokenAccount` behave? What are its program IDs? | Read docs | developers.jup.ag, dev.jup.ag | none | n/a | Low priority (Jupiter is not in the money path, decision 7) | n/a |
| G11 | **P8**, SEC-S5, SEC-r1.5, P10 (docs part) | What can Turnkey and Privy policies restrict? (Comparison only; KMS is chosen) | Read docs | docs.turnkey.com, docs.privy.io | none | n/a | Comparison only | n/a |
| G12 | **P13** (red-team and social versions) | How many non-team posts mention the coin at t = 0/60/300/900 s, for 200 graduations? | Search or count API | api.x.com, api.twitterapi.io, api.socialdata.tools | X_BEARER_TOKEN / TWITTERAPI_IO_KEY / SOCIALDATA_API_KEY | n/a | Only if Paul says yes to Q17 | No X data |
| G13 | **P15**, A7, X8 | What filters and fees do GMGN, Axiom, Photon and Sharpe show? | Read the pages | gmgn.ai, axiom.trade, photon-sol.tinyastro.io [UNVERIFIED host], sharpe.ai | none | n/a | Notes | n/a |
| G14 | **SOC-S1**, SOC-r1.1, PX-9 | X counts backfill for 1,000 graduates, and the billed price | `/2/tweets/counts/all` | api.x.com, console.x.com, docs.x.com | X_BEARER_TOKEN | Within $10–20 | **Only with Paul's yes (Q17)** | No X data |
| G15 | **SOC-S2** | Does search match a raw contract address and `pump.fun/coin/<CA>` links? | Search APIs | api.x.com, api.twitterapi.io, api.socialdata.tools | as G12 | n/a | Q17 | n/a |
| G16 | **SOC-S6** | Pump.fun page fields (reply count, livestream on/off), research only, terms read first | Read the terms, then GET | pump.fun, frontend-api-v3.pump.fun | none | n/a | Terms first | n/a |
| G17 | **SOC-S8** | How was the KOL report made? | Read | madeonsol.com | none | n/a | Notes | n/a |
| G18 | **EXE-r1.1** | Jupiter quotes 0–120 s after migration | GET `/swap/v2/order` and `/build` quotes (no sending) | api.jup.ag, developers.jup.ag, portal.jup.ag | none | `feeBps` 50 | Low priority | n/a |
| G19 | **RSK-r1.4** | Jupiter Trigger V2 | Read docs | developers.jup.ag | none | n/a | Superseded: exits run in the guard | n/a |
| G20 | **SOC-r1.2** | twitterapi.io prices; stream delay on 10 accounts | API | docs.twitterapi.io, api.twitterapi.io | TWITTERAPI_IO_KEY | n/a | Q17 | n/a |
| G21 | **SOC-r1.3** | SocialData monitor price and freshness | API | docs.socialdata.tools, api.socialdata.tools | SOCIALDATA_API_KEY | n/a | Q17 | n/a |
| G22 | **SOC-r1.4** | Apify actor run time for 100 tweets | API | apify.com, api.apify.com | Apify token (new) | n/a | Q17 | n/a |
| G23 | **SOC-r1.5** | LunarCrush coverage of coins under 1 hour old | Read | lunarcrush.com, lunarcrush.ai | none | n/a | Rejected in the design (decision 16); low priority | n/a |
| G24 | **SOC-r1.6** | Kaito coverage | Trial request | kaito.ai | none | n/a | Same as G23 | n/a |
| G25 | **SOC-r1.8** | Helius webhook delay for 5 wallets | Webhook | api.helius.xyz | HELIUS_API_KEY | n/a | Superseded: KOL wallets moved to the gRPC stream (SOC-6), and webhooks need a public receiver we don't have | n/a |
| G26 | **SOC-r1.9** | Terms-of-service reads | Read | x.com, developer.x.com, core.telegram.org, discord.com | none | n/a | Notes | n/a |
| **TIER H** | **Offline (no network beyond package downloads)** | | | | | | | |
| H01 | **R6**, SEC-S8, RSK-r1.6, DRILL-R1, DRILL-SELL5 | Do the paper-mode drills meet their pass marks? (Five sell-blocking paths, guard kill, standby takeover, disk full) | Phase 3 drills | none | none | n/a | Pass marks in rulings R1 and DESIGN Gate 3→4 | n/a |
| H02 | **RSK-r1.5** | Does systemd restart a process that misses its watchdog ping? | Local container (docs on www.man7.org, List 3) | none | none | Restart | PASS: restart within the set time | n/a |
| H03 | **SOC-r1.10** | Do fixture tweets trigger the right flags? | Offline fixtures | none | none | n/a | Each flag fires | n/a |
| H04 | **STK-2** | Do `i128`/`u64` extremes round-trip through Parquet into DuckDB and Polars exactly? | Offline | pypi.org, files.pythonhosted.org, static.crates.io (reachable today) | none | Exact | PASS: exact equality | n/a |
| H05 | **STK-3** | Does CI reject a dependency younger than 7 days? | Offline + the index | index.crates.io (reachable today) | none | Fails closed | PASS: fails closed | n/a |
| H06 | **RUIN** | Ruin simulation on whole recorded days (Phase 2) | Offline | none | none | n/a | rulings NEW-13 | n/a |
| **TIER I** | **FORBIDDEN in Phase 0 (it would sign, send or simulate)** | | | | | | | |
| I01 | **SEC-S1**, RC9, SEC-r1.1 | KMS / Turnkey / Privy signing latency | **Signs** (a dummy message with a test key) | kms.eu-central-1.amazonaws.com, api.turnkey.com, api.privy.io | n/a | n/a | **FORBIDDEN in Phase 0.** Allowed in Phase 3 in Paul's AWS account (Gate 3→4 needs SEC-S1), with a test key only and never a funded key | n/a |
| I02 | **R7** | Pre-signed emergency sells on durable nonces, on devnet | **Signs and sends** | api.devnet.solana.com | n/a | n/a | **FORBIDDEN**, and obsolete: rulings R4 rejected these sells | n/a |
| I03 | **SEC-S4 (devnet part)**, P10 (devnet part) | A devnet sell to a foreign payout account; a manual dashboard sell | **Sends** | api.devnet.solana.com | n/a | n/a | **FORBIDDEN.** CLAUDE.md rule 4 has no devnet exception. The mainnet-history part runs as A10 | A10 |
| I04 | **SEC-r1.2** | Turnkey/Privy policy refusal on devnet | **Signs** | api.devnet.solana.com | n/a | n/a | **FORBIDDEN**, and obsolete (Turnkey and Privy rejected) | Paper-mode refusal tests in H01 |
| I05 | rulings R2 check 4 (no test number) | `simulateTransaction` of a new sell layout | **Simulates** (brief rule 1 forbids it) | an RPC host | n/a | n/a | **FORBIDDEN in Phase 0.** Phase 0 uses historical replay (A15). Live use only inside the Phase 3 guard | A15 replay |

---

## 5. Where every original test ID went (nothing dropped)

**Data engineer (D):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| D1 | A01 | D5 | A04 | D9 | A23 | D13 | A27, C02 |
| D2 | A03 | D6 | A12, C03 | D10 | A26, G09 | D14 | A23 |
| D3 | C05 | D7 | A02 | D11 | C01 | D15 | A24 |
| D4 | C01 | D8 | C04 | D12 | A09 (reserves), C06 (index) | D16 | A05 |

**Chain forensics (CF-T):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| CF-T1 | A05 | CF-T4 | A06 | CF-T7 | G02 | CF-T10 | D07 |
| CF-T2 | A25 | CF-T5 | B02 | CF-T8 | G03 | CF-T11 | A20 |
| CF-T3 | A03 | CF-T6 | G01 | CF-T9 | G04 | | |

**Quant tester (QT-T):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| QT-T1 | D01 | QT-T4 | G06 | QT-T7 | A12 | QT-T10 | G08 |
| QT-T2 | E11 | QT-T5 | A08 | QT-T8 | A18 | QT-T11 | G09 |
| QT-T3 | G05 | QT-T6 | A09 | QT-T9 | G07 | | |

**Red-team attacks (P):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| P1 | A03, A29, D03 | P5 | A31, D06 | P9 | F02 | P13 | G12 |
| P2 | D04 | P6 | A10 | P10 | G11, I03 | P14 | D08 |
| P3 | D05 | P7 | G10 | P11 | C01 | P15 | G13 |
| P4 | A17 | P8 | G11 | P12 | A24 | | |

**Red-team re-check (RC):**

| ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|
| RC1 | A30, D02 | RC4 | A07 | RC7 | D10 |
| RC2 | A13, C07 | RC5 | D09 | RC8 | A15 |
| RC3 | A07 | RC6 | C01 | RC9 | I01 |

**Risk manager (R):**

| ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|
| R1 | D11 | R6 | H01 | R9 | A05 |
| R2 | A16, D04 | R7 | I02 | R10 | E10 |
| R3–R5 | D12 | R8 | A24 | | |

**Security (SEC-S):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| SEC-S1 | I01 | SEC-S3 | F04 | SEC-S5 | G11 | SEC-S7 | A19, F08 |
| SEC-S2 | F03 | SEC-S4 | A10, I03 | SEC-S6 | F02 | SEC-S8 | H01 |

**Social (SOC-S):**

| ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|
| SOC-S1 | G14 | SOC-S3 | A22, E07, D13 | SOC-S6 | G16 |
| SOC-S2 | G15 | SOC-S4 | D14 | SOC-S7 | G09 |
| SOC P13 | G12 | SOC-S5 | D15 | SOC-S8 | G17 |

**Execution (X), quant (Q) and forensics (F):**

| ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|
| X1 | A18, A17 | Q1 | A09 | F1 | A31, D06 |
| X2 | A11 | Q2 | C01 | F2 | B01, C02 |
| X3 | A14 | Q3 | C06 | F3 | A32, B02 |
| X4 | A19 | Q4 | A11 | F4 | A16 |
| X5 | A30, D02 | Q5 | A19 | F5 | A21 |
| X6 | A09 | Q6 | D01 | F6 | A25 |
| X7 | A16 | | | F7 | G01 |
| X8 | G13 | | | | |

**AI strategist (A) and lead-architect rulings (G):**

| ID | Row | ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|---|---|
| A1 | E01 | A6 | E06 | G1 | F05 | G5 | A24 |
| A2 | E02 | A7 | G13 | G2 | F06 | G6 | F07 |
| A3 | E03 | A8 | A22, E07 | G3 | C07 | G7 | F01 |
| A4 | E04 | A9 | E08 | G4 | A27, C08 | G8 | A24 |
| A5 | E05 | A10 | E09 | | | | |

**Fee model (FC) and price checks (PX):**

| ID | Row | ID | Row |
|---|---|---|---|
| FC1–FC4, FC8 | A08 | PX-1 | A26, C08 |
| FC5 | A05 | PX-2 | A24, A26 |
| FC6, FC7, fee-model "T6" | A09 | PX-3 | G09 |
| FC9 | A11 | PX-4, PX-5 | F09 |
| | | PX-6, PX-7 | F01 |
| | | PX-8 | E12 |
| | | PX-9 | G14 |
| | | PX-10 | F07 |
| | | PX-11 | A28 |
| | | PX-12 | Not a network test (a question for Paul in costs.md) |

**Unnumbered round-1 lists:**

| ID | Row | ID | Row | ID | Row |
|---|---|---|---|---|---|
| AI-r1.1 | E01 | EXE-r1.1 | G18 | RSK-r1.1 | D11 |
| AI-r1.2 | E05 | EXE-r1.2 | A08, A11, A12 | RSK-r1.2 | A13, C07 |
| AI-r1.3 | E02 | EXE-r1.3 | A18 | RSK-r1.3 | A09 |
| AI-r1.4 | E03 | EXE-r1.4 | A19 | RSK-r1.4 | G19 |
| AI-r1.5 | E04 | EXE-r1.5 | F08 | RSK-r1.5 | H02 |
| AI-r1.6 | E09 | EXE-r1.6 | A23 (pump.fun/docs/fees is covered by fee-model's fees.png read) | RSK-r1.6 | H01 |
| | | EXE-r1.7 | G09 | | |
| | | EXE-r1.8 | A28 | | |
| | | EXE-r1.9 | D08 | | |

| ID | Row | ID | Row |
|---|---|---|---|
| SEC-r1.1 | I01 | SOC-r1.1 | G14 |
| SEC-r1.2 | I04 | SOC-r1.2 | G20 |
| SEC-r1.3 | F09, G09 | SOC-r1.3 | G21 |
| SEC-r1.4 | A02, G10 | SOC-r1.4 | G22 |
| SEC-r1.5 | G11 | SOC-r1.5 | G23 |
| | | SOC-r1.6 | G24 |
| | | SOC-r1.7 | D14, G13 |
| | | SOC-r1.8 | G25 |
| | | SOC-r1.9 | G26 |
| | | SOC-r1.10 | H03 |

**Tech stack and drills:**

| ID | Row |
|---|---|
| STK-1 | C01 |
| STK-2 | H04 |
| STK-3 | H05 |
| DRILL-R1, DRILL-SELL5 | H01 |
| RUIN | H06 |

**Domains not yet on any QUESTIONS_FOR_PAUL.md list:** `www.bankofcanada.ca` (A28), `calculator.aws` (F09), and the alert-service hosts (F07). Also add the Helius Enhanced-websocket host if A24 shows it differs from `mainnet.helius-rpc.com`.

---

## 6. Template for `phase0/results.md`
```
### <Row> <test IDs> — <date UTC>
- Domain(s) used: …   Provider: …   Env var: … (value never shown)
- Outcome: PASS | FAIL | MEASURED | BLOCKED: <host> | SKIPPED: <reason>
- Numbers: …   (each with its tag; [VERIFIED-LOCAL] = measured by us)
- Fixtures: fixtures/phase0/<row>/ (sha256 manifest)
- Follow-up: … (fallback taken, file updated, alarm rule changed)
```

## Sources
- [VERIFIED-DOC] Pump IDLs and docs, fetched 2026-11-05: https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump.json ; …/idl/pump_amm.json ; …/idl/pump_fees.json ; …/README.md
- [VERIFIED-DOC] Yellowstone gRPC README: https://raw.githubusercontent.com/rpcpool/yellowstone-grpc/master/README.md
- [VERIFIED-SEARCH] Helius plan limits: https://helius.dev/docs/billing/plans ; https://www.helius.dev/pricing
- Team files (every test's origin): `team-debate/round1/*.md`, `team-debate/round2/*.md`, `team-debate/round3/rulings.md` §8, `docs/fee-model.md` §7 and §10, `docs/costs.md` §11, `docs/assumption-register.md` §2, `docs/tech-stack.md` §12, `QUESTIONS_FOR_PAUL.md` (List 1–4)
