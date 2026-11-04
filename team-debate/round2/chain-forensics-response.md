# Round 2b: Chain forensics responds to red-team

## 0. In plain English (for Paul)
- Red-team was right. My Round 1 checks were basic hygiene: the same numbers every free trading app already shows. They catch fake coins, but they give us no edge. The plan is now built around one number that nobody shows well: **how much of the coin the launch crew still holds, including tokens they quietly moved to fresh wallets** ("insider overhang"). It is the most they can still dump on us.
- At the moment we decide, the checks make **no network calls**. Everything is prepared in advance from our own live feed, so the checks take milliseconds, even when a coin graduates and trades in the same instant.
- My position on the big question: our safety checks are worth more if we **don't race** at graduation. The best evidence (do the insiders sell while Pump's 5-minute BOOST buying holds the price up?) only exists a few minutes after graduation.
- I have three edge ideas, each with a pass/fail test fixed in advance: follow the insiders' tokens wherever they move, recognise repeat scam crews by their tools instead of their wallets, and buy only after the known sellers have left. All three are hypotheses until our own recorded data proves them.

**Jargon.** A **dossier** is the running file we keep on each coin from the moment it is created. The **insider set** is the creator plus the wallets most likely working with them (defined in 1a). **Overhang** is the share of supply the insider set still holds. **Taint** means treating a wallet as an insider because it received the coin from one. A **lookup table (LUT)** is an on-chain address list that lets one transaction name many wallets; bundler tools create them. **Credits** are the units an RPC provider bills in. **Null strategy** means "buy every graduate", the baseline any rule must beat.

Tags: VERIFIED-DOC (I read the primary source this session), VERIFIED-SEARCH (seen in search results only), UNVERIFIED (inference; the test that settles it is named), DERIVED (my arithmetic). S-numbers point to my Round 1 sources and R-numbers to the list at the bottom.

## 1. Answers to attacks

| Attack | Verdict | What changed |
|---|---|---|
| **CHN-1 / SEAM-5** (the check window may be zero) | FIXED | **Zero-read gate** (§2). The decision makes no network reads. Facts that can never change are checked once, at creation. The dossier is updated from every streamed transaction. The only work at the gate is decoding the completing or migration transaction we already hold: who completed the curve, which pool, whether the LP was burned. It still works when complete, migrate and buy happen in one transaction. |
| **CHN-2** (top 20 holders only; nobody checked the exclusion list) | FIXED | A full holder map, built from the token balances recorded in every streamed transaction plus the token watch (1b). It is reconciled once against a full holder scan: DAS `getTokenAccounts` by mint, paged, about 10 credits per page [VERIFIED-SEARCH R5, low confidence]. Exclusions are **derived from addresses, never typed in by hand** (1b). An unknown program-owned holder is *counted* as a holder, never excluded, so a mistake costs us a missed trade, never a hidden insider. |
| **CHN-3** (bundle detection misses modern bundles) | FIXED | The primary measure is now red-team's own: **the share of supply still held at decision time by wallets that bought in the first N slots, plus everyone they passed tokens to** (logged for N = 1, 3 and 10). Ordinary snipers are counted too, and that is correct: unsold sniper supply is overhang whatever the buyer meant. The Jito bundle lookup is now research only. |
| **CHN-4** (funding checks are easy to dodge and cost credits) | FIXED (cost); ACCEPTED (evasion) | Helius `funded-by` costs **100 credits per call and needs a paid plan** [VERIFIED-SEARCH R4]. It is replaced by our own lookup: fetch the wallet's oldest signatures, then that one transaction. That is about 2–3 standard calls at roughly 1 credit each [VERIFIED-SEARCH R5; archival-call pricing UNVERIFIED, F3]. Lookups run only on "material" wallets (the top 25 holders plus early buyers), and results are cached forever, because a wallet's first funder never changes. `funded-by` stays as an accuracy check on 20 wallets a day. Dodging through exchange withdrawals or bought aged wallets is an accepted risk. "Fresh wallet funded straight from an exchange minutes before buying" is logged as its own feature. No veto until T10 shows the check adds value. |
| **CHN-5** (the checks that matter are unproven; no rug label) | FIXED (method); ACCEPTED (unproven until data) | Labels and a money-based scoring rule are frozen in 1c before any test runs. Every behaviour check stays WARN or log-only until it passes. |
| **CHN-6** (Mayhem coins; coins quoted in another Pump coin) | FIXED | Hard REJECT in v1: `REJECT mayhem_mode: v1 policy` and `REJECT quote_mint: <mint> is not SOL`. Both kinds are still recorded for research. |
| **CHN-7** (creator history counted as good evidence) | FIXED | Creator history and the recycled-wallet check can only WARN or REJECT. No history is neutral, never a bonus. |
| **SEAM-6 / DAT-3** (plain token transfers are invisible) | FIXED (design); QUESTION (provider limits) | A **token watch** stream for armed candidates and for coins we hold (1b). It filters by **the wallets' token accounts, not by the mint**. A plain `Transfer` does not include the mint account, so a mint filter would miss exactly the dev's move [UNVERIFIED; Token-2022 keeps every old instruction, VERIFIED-SEARCH R9; test F2]. Each transfer's destination joins the watch, and that is how taint spreads. **QUESTION for data-engineer:** Chainstack reportedly allows only 5 filters of one type per connection (from a 2025 pull request, possibly outdated [VERIFIED-SEARCH R8]), while Helius `transactionSubscribe` takes up to 50,000 addresses per filter [VERIFIED-SEARCH R6] and is available on the Developer plan [VERIFIED-SEARCH R7]. Test F2 decides between them. |
| **RSK-3** (the dev sells in 1.9% chunks through fresh wallets) | FIXED (design); ACCEPTED (what's left) | Fresh wallets that got tokens from an insider are tainted, so their sells all count toward **one rolling insider net-sell total** (exit proposal in §3). The transfer itself raises `WARN insider_transfer` before the first sell. What's left: an insider who bought from the start through unrelated, exchange-funded wallets after slot N is invisible to us. The pool-flow trigger, which ignores who is selling (RSK-2), is the backstop. Test F1 measures how real dumpers got their tokens. |
| **RSK-2** (the pool-drain exit can never fire first) | FIXED, jointly with risk | Agreed. The LP tokens are burned [VERIFIED-DOC S1], so SOL can only leave the pool through sells. Forensics feeds risk the insider-flow numbers; risk owns the pool net-flow trigger. |
| **RSK-1** (BOOST) | FIXED (holder maths) | BOOST buys over about 5 minutes and burns each token straight after buying [VERIFIED-SEARCH R10]. So percentages are taken of the **current supply**, not 1 billion. BOOST's buys will be left out of organic-buyer and wash-trading counts once its wallet is identified. That address is UNVERIFIED (F4); until then nothing is excluded for BOOST. |
| **RSK-5** (spam airdrops) | FIXED (supports risk) | Forensics can classify any unknown token that lands in the wallet (transfer hook, permanent delegate, transfer fee) for the log. It never triggers a sell of a token missing from the buy journal. |
| **SEAM-7** (Helius credits counted twice) | FIXED | The forensics budget is in 1d: about 0.6–4M credits a month [DERIVED]. Forensics gets its own API key with a hard daily cap of 100k credits. At the cap it logs `REJECT budget_exhausted` and stops new buys; exits are never affected. |
| **SEAM-10 / PREMISE-3** (coins that complete in one jump never get pre-checked) | FIXED | The free dossier exists for **every coin from creation** and costs 0 credits. Only the paid checks are staged. A coin that completes before its paid checks finish gets `REJECT paid_checks_missing` in v1. These coins are tracked as their own group, so we learn whether the rule throws away the best coins. |
| **DAT-1 / DAT-2** (silent decoding errors; the primary feed goes down) | FIXED | The forensics decoders are data-engineer's versioned decoders with exact byte-length checks. Each dossier stores `last_slot`. If our feed is more than 2 slots behind the chain's slot stream, the verdict is `REJECT DATA_STALE`. |
| **PREMISE-2** (no edge) | ACCEPTED; answered in §4 | True of Round 1. GMGN already shows insider %, dev %, top 10, bundle ratio, "rat" wallets and snipers [VERIFIED-SEARCH R11], and registries of early buyers across launches are sold commercially [VERIFIED-SEARCH R12]. Those checks stay as hygiene. §4 covers what we would compute that the apps don't. |
| **PREMISE-4** (no baseline) | FIXED | Every check is scored against the null strategy (1c). |
| **PREMISE-7** (the desk can't pay its bills) | FIXED | RugCheck Basic ($40/month) is dropped. Its free tier (cached reports, 3 requests/s [VERIFIED-SEARCH S13]) is logged at +5 minutes for research only. |

### 1a. Insider set, version 1 (frozen and versioned; each member is logged with its reason)
- **I0:** the create signer and the `creator` field. They can be different wallets [VERIFIED-DOC S1].
- **I1:** early buyers, meaning any wallet that bought in the creation slot or the next 2 slots (N can be tuned).
- **I2:** the funding cluster, meaning material wallets that share a direct funder with an I0 or I1 wallet, or that funded or were funded by I0.
- **I3:** taint, meaning any wallet that received the coin by plain transfer from an I0–I3 wallet, over any number of hops.
- **Overhang** = the I0–I3 balances ÷ current supply. Example log line: `WARN insider_overhang: 18.4% (I0 2.1, I1 9.0, I2 3.3, I3 4.0) limit 15% src=dossier slot=… 0.3ms`.
- **Partly reliable.** To evade it, a crew buys from unrelated, aged wallets funded through an exchange, after slot N. That costs them exchange fees, withdrawal delays and wallet preparation. It slows a determined crew down; it does not stop one.

### 1b. Holder map, exclusions and token watch
- **Holders** come from the token balances after each trade (owner and amount) in every streamed Pump or PumpSwap transaction, plus the token watch. When a coin is armed we run one full holder scan to reconcile, and in option C another at +5 minutes. A difference over 1% of supply logs `WARN holder_map_mismatch`.
- **Excluded only if derived from known addresses:** the bonding curve's token account, the canonical pool's base vault, the Mayhem token vault (an account named in `create_v2` [VERIFIED-DOC R1]; Mayhem coins are rejected in v1 anyway), and burned tokens (they reduce supply). Holder-reward coins need no exclusion: their fees are set aside and paid out by Pump [VERIFIED-DOC R2]; that no vault holds the coin itself is UNVERIFIED (F4). Everything else counts as a holder. An unknown program-owned holder is logged `UNCLASSIFIED_PDA owner_program=…` so it can be reviewed and added.
- **The token watch** covers the token accounts of the I0–I3 wallets and the top 50 holders, for armed candidates and the coins we hold (at most 3). On Helius it is billed by data volume, at 20 credits/MB [VERIFIED-SEARCH, DAT S5].

### 1c. Labels and scoring, frozen before T10 runs
- `CRASH`: within 60 minutes of the decision, the price falls 70% below the decision price before it rises 50% above it.
- `INSIDER_DUMP`: a CRASH where at least 40% of the SOL sold between the decision and the low came from the insider set. Labels may use hindsight; features may not.
- **The money test:** compare the null strategy's net profit on the coins a check rejects with its profit on the coins it passes, across every canonical graduate, not just the ones we filled. A check earns a veto only if **all** of these hold: the rejected group's average is at least 5 percentage points lower; the 90% bootstrap range excludes 0; it rejects no more than 40% of graduates; and the result holds in the second half of the sample. Every threshold we try counts as a trial (SEAM-9).

### 1d. Forensics credit budget per month (assumes 240–1,500 coins armed a day, i.e. 3–5× the 80–300 graduations a day [VERIFIED-SEARCH S21; the multiple is UNVERIFIED])
| Item | Unit cost | Credits per month, low to high |
|---|---|---|
| Permanent checks (decoded from the create transaction) | 0 | 0 |
| Confirming mint read when a coin is armed (batched) | about 1 per coin | under 0.05M |
| Holder scans: 2 per coin, 1–1.5 pages each | about 10 per page [VERIFIED-SEARCH R5] | 0.15–1.4M |
| Funding lookups: 25 wallets per coin, half already cached | about 3 per wallet [UNVERIFIED, F3] | 0.3–1.7M |
| Token watch | 20 per MB | 0.15–0.9M [UNVERIFIED size, F2] |
| `funded-by` accuracy check, 20 a day | 100 each [VERIFIED-SEARCH R4] | 0.06M |
| **Total** | | **≈ 0.6–4M** [DERIVED] |

Using `funded-by` for every funding lookup instead would cost about 9–56M credits a month [DERIVED]. That rules it out.

## 2. The big fork: race at graduation, or not?

| Check | Ready inside a race window (1 block, no network reads)? | Reliability |
|---|---|---|
| Genuine Pump coin, canonical pool: the pool address worked out in advance must match the one in the migration event | **Yes** | Reliable |
| Mint authority null, freeze authority null, only allowed extensions: checked once at creation. Pump coins' mint authority is null, and a null authority is permanent [VERIFIED-SEARCH R3]; freeze authority still needs T1 | **Yes** | Reliable |
| Quote mint is SOL; Mayhem flag | **Yes** | Reliable |
| LP burned: read from the migration transaction itself (T4) | **Yes** | Reliable on canonical pools |
| Concentration, dev holding, overhang, early-buyer share: as of the last processed slot | **Yes**, but transfers in the final slot can be missed | Partly reliable |
| Creator history, recycled wallets, crew fingerprints (Edge B) | **Yes** (lookups in memory) | Partly reliable |
| Funding cluster and fresh-wallet share | Only for wallets seen before the coin was armed. The completing buyer and last-second buyers show as `unknown` | Partly reliable |
| Full holder reconciliation by scan | No: hundreds of ms or more [UNVERIFIED, T2] | Reliable for the snapshot |
| **Insider behaviour after migration** (selling into BOOST, moving tokens to new wallets) | **No: needs 1–10 minutes** | Partly reliable, and **our strongest signal** |
| Wash trading in the pool | No: needs minutes of pool data | Not reliably detectable |
| Third-party scores | No: seconds away, and the free tier only serves cached reports [VERIFIED-SEARCH S13] | Partly reliable, opaque |

**Position.** Forensics recommends **option C: enter on evidence, after minutes, with no race on the entry side.** Three reasons:
1. At the race moment, what we know about a coin is what GMGN shows everyone: who holds what [VERIFIED-SEARCH R11]. Racing gives us no information edge, only a speed contest we lose (PREMISE-1).
2. What only we compute (where the insiders' tokens went, and whether they sell into BOOST) appears 1–10 minutes after graduation.
3. In race mode, the coins that complete in one jump arrive without paid checks. We either reject them, which makes the adverse selection in PREMISE-3 worse, or we trade them blind.

Either way, the gate is built with zero network reads. If lead-architect rules for racing, forensics adds only milliseconds of in-memory work and never blocks [UNVERIFIED until benchmarked on recorded data]. Racing then runs as a paper-only shadow so quant can compare the two.

## 3. Challenges to other areas (3)
1. **Data-engineer: store the raw facts, not just the decoded events.** The recorder must keep, for every Pump or PumpSwap transaction: token balances before and after, inner instructions, compute-budget instructions, the lookup tables used, and tip transfers. Without these, 1a, 1b and Edges A and B can be neither built nor backtested. Data-engineer should also own test F2, the token-watch provider choice: Chainstack's filter limits against Helius's 50,000 addresses.
2. **Risk-manager: replace `EXIT_DEV_SELL` and `EXIT_WHALE_DUMP`.** Rules that look at one wallet and one transaction at a time are easy to dodge (RSK-3). Proposed instead:
   - `EXIT_INSIDER_FLOW`: the insider set has sold at least 3% of supply within a rolling 120 seconds, or at least 30% of what it held when we entered.
   - `WARN_INSIDER_TRANSFER`: an insider moved tokens to an untagged wallet, so the trailing stop tightens to 10%.
   - Keep the pool net-flow trigger, which ignores who is selling, as the backstop.
   - Add an entry cap of `REJECT insider_overhang > 15%` once T10 supports it.
   All numbers are placeholders until F1 and P5.
3. **Quant-tester: forensic features must be point-in-time.** Wallet links are often discovered later, for example a shared funder found a week afterwards. A backtest may only use links that were in the dossier, as stored, at decision time. Clusters rebuilt with hindsight make every forensic rule look brilliant. Score checks on all graduates using 1c.

## 4. Edge hunt

**Edge A: follow the tokens ("taint-tracked overhang").**
- *What rivals lack:* the apps show a dev % and an insider %, built with formulas they don't publish [VERIFIED-SEARCH R11]. We keep a ledger, updated with every transaction, that follows insider tokens through any number of plain transfers and adds funding links. We use it at entry *and* as a live exit trigger while we hold.
- *Why we'd win:* we lose less on coins with a hidden overhang ("losing less is a real edge").
- *Cost:* the token watch plus funding lookups, about 0.5–2.6M credits a month [DERIVED from 1d], plus CPU and memory.
- *How a rival copies it:* a capable team could build it in weeks; the idea is no moat. Our advantage is that it is wired into both our entries and our exits.
- *Kill test (decided now):* on at least 14 days of recorded tape (at least 1,000 canonical graduates), compute overhang at +0 s and +300 s two ways: **naive** (I0 + I1 balances only) and **tainted** (I0–I3). It passes only if all of these hold:
  1. Tainted exceeds naive by at least 3 points of supply on at least 15% of graduates.
  2. Adding tainted overhang raises the AUC (a 0.5–1 score of how well a number separates dumps from non-dumps) for `INSIDER_DUMP` by at least 0.03 on the held-out second week.
  3. On paper positions, `EXIT_INSIDER_FLOW` fires before the −35% hard stop on at least 30% of `INSIDER_DUMP` coins, and on no more than 20% of its firings does the coin then rise 30% before it falls 30%.

  If F1 shows that under 10% of dumped tokens arrived by plain transfer, the taint part is dropped and only I0–I2 is kept.

**Edge B: recognise the crew, not the wallet.**
- *What rivals lack:* creator-history checks key on the creator wallet, and a new wallet costs nothing (CHN-7). We link launches by **tooling fingerprints** instead: the same lookup table or lookup-table owner in the early buys (open-source Pump bundlers build a lookup table for each launch and submit Jito bundles [VERIFIED-SEARCH R13]), the same compute-price and tip amounts, the same exchange-wallet-to-fresh-wallet funding pattern, the same metadata host or image hash, and the same shape of buy sizes. Two launches are linked only when at least 2 independent fingerprints match.
- *Why we'd win:* I found no source describing lookup-table reuse as a detection method [VERIFIED-SEARCH R13, R14 show other methods only; UNVERIFIED that crews reuse tables, F5]. Changing tools costs a crew real effort, and the history builds up in our own recorder.
- *Cost:* close to 0 credits (one cached read per new lookup table), extra storage, and medium build effort.
- *How a rival copies it:* anyone with raw history. Dune could backfill it, so our lead is weeks, not months. Crews adapt once they notice, so we publish nothing.
- *Kill test:* 30 days of tape. Days 1–20 build the links; days 21–30 test them, forward only. It passes only if all of these hold:
  1. At least 5% of test-period graduates link to an earlier launch.
  2. Graduates linked to 2 or more earlier `INSIDER_DUMP` launches dump at least 2× the base rate, with the lower bound of the 90% range above 1.3×.
  3. The real lift beats the 95th percentile of 100 runs with the fingerprints shuffled between launches.

**Edge C: buy after the known sellers have left.**
- *What rivals lack:* the racers can't wait, and the snapshot apps don't know which holders are proven sellers. Rule C enters only when all of these hold:
  1. BOOST has ended and the price has made no new low for N blocks. This is an event, not the fixed 300 s that RSK-1 attacks.
  2. Insider overhang has fallen below 3%, or the insiders held through BOOST.
  3. Organic net buying is positive.
- *Why we'd win:* we take the other side of a timing constraint. Launch snipers sell 85% within 5 minutes [VERIFIED-SEARCH R15; not yet checked for migrations], and we buy after the forced sellers are gone. The auction is quiet, so tips stay low, which helps the cost problem in SEAM-1.
- *Cost:* nothing beyond Edge A.
- *How a rival copies it:* the idea is simple; the insider ledger is the hard part.
- *Kill test:* on at least 500 post-BOOST graduates, using quant's fill model (we land last in the block) and risk's exits after all costs, compare Rule C with the null strategy at 300 s and at 600 s and with random entry in the same windows. It passes only if all of these hold:
  1. Its average net profit per trade beats the best baseline by at least 5 points.
  2. It is above 0, with the 90% bootstrap range excluding 0.
  3. It is still positive with the top 5% of trades removed (QNT-4).
  4. It averages at least 3 qualifying trades a day.

  "Insiders held through BOOST" is tested as a separate variant, and each variant counts as a trial.

## 5. Revised recommendation
- **Zero-read gate.** Permanent checks are decoded from the creation transaction and confirmed once. The dossier updates with every streamed transaction. The decision is a lookup in memory, and it fails closed on stale or missing data.
- **Overhang is the core number, not the top 10.** It rests on the full holder map, the insider set (creator, early buyers, funding cluster, taint) and the token watch, and it feeds both entry and exits. It stays WARN or log-only until it passes 1c.
- **Entry: forensics backs option C** (enter on evidence, after minutes). Racing runs only as a paper shadow.
- **Costs: our own funding lookups** (about 3 credits) instead of `funded-by` (100), staged and cached forever. Forensics runs on its own key with a hard daily cap, about 0.6–4M credits a month. RugCheck goes to the free tier for research only.
- **Hard REJECTs in v1:** non-canonical pool; any authority or extension failure; Mayhem; non-SOL quote; stale, missing or unpaid data; budget exhausted. Creator history can never count in a coin's favour. Each idea in §4 lives or dies by its pre-set test.

## Tests to run once allowed (read-only)
| # | Test | Domain(s) |
|---|---|---|
| F1 | For 200 `INSIDER_DUMP` coins: the share of dumped tokens that arrived by plain transfer, the number of hops, and the time from transfer to first sell (this extends P5) | `mainnet.helius-rpc.com` |
| F2 | Token watch: subscribe to 2,000 token accounts. Check that it is accepted, the delay, credits/MB, and the Chainstack equivalent; confirm whether plain `Transfer` includes the mint account | `mainnet.helius-rpc.com` (wss), `docs.chainstack.com`, Chainstack gRPC host |
| F3 | Credits and delay of `getSignaturesForAddress` + `getTransaction` for a funding lookup, and how often it agrees with `funded-by` on 200 wallets | `www.helius.dev/docs/billing/credits`, `api.helius.xyz` |
| F4 | The BOOST agent's wallet, and whether it buys and burns in the same transaction, on 20 graduates | `mainnet.helius-rpc.com`, `pump.fun` |
| F5 | Lookup-table use and reuse across launches in early-buy transactions, over 7 days | `mainnet.helius-rpc.com` |
| F6 | Holder-scan pages and credits on 50 fresh graduates | `mainnet.helius-rpc.com` |
| F7 | Does the RugCheck free tier have a report at +0, +60 and +300 s? | `api.rugcheck.xyz` |

T1 (freeze authority), T4 (LP burn inside the migration transaction) and T10 from Round 1 still stand.

## Sources (new this round; S-numbers are in round1/chain-forensics.md)
- R1 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/instructions/COIN_CREATION.md
- R2 [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md (holder-reward fees are "set aside … and paid out by pump.fun")
- R3 [VERIFIED-SEARCH] https://www.helius.dev/docs/orb/explore-authorities
- R4 [VERIFIED-SEARCH] https://www.helius.dev/docs/billing/credits ; https://docs.helius.xyz/docs/wallet-api/overview.md
- R5 [VERIFIED-SEARCH, low confidence] https://openskillindex.com/skills/neversight-learn-skills-dev-helius-api ; https://docs.helius.dev/docs/das/get-tokens.md
- R6 [VERIFIED-SEARCH] https://docs.rs/crate/helius/1.1.0/source/src/types/enhanced_websocket.rs
- R7 [VERIFIED-SEARCH] https://www.helius.dev/blog/laserstream-websockets
- R8 [VERIFIED-SEARCH] https://github.com/chainstack/dev-portal/pull/72 ; https://docs.chainstack.com/changelog/chainstack-updates-june-10-2026.md
- R9 [VERIFIED-SEARCH] https://spl.solana.com/token-2022
- R10 [VERIFIED-SEARCH] https://cryptobriefing.com/pump-fun-launches-boost-mode-to-recycle-dead-liquidity-through-token-burns/ ; https://www.kucoin.com/blog/pump-fun-boost-mode-explained
- R11 [VERIFIED-SEARCH] https://www.datawallet.com/crypto/gmgn-explained ; https://solanacompass.com/projects/GMGN
- R12 [VERIFIED-SEARCH] https://glama.ai/mcp/connectors/com.augur-trade/foresight-forensics/tools/bundler_profile
- R13 [VERIFIED-SEARCH] https://github.com/Open-Builders/pumpfun-bundler-pump.fun-bundler-solana-token-bundler-bot/wiki
- R14 [VERIFIED-SEARCH] https://docs.webacy.com/reference/what-is-bundling
- R15 [VERIFIED-SEARCH] https://pineanalytics.substack.com/p/exit-liquidity-machines (cited by red-team)
