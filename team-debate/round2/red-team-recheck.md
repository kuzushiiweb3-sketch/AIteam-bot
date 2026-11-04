# Round 2c: Red-team recheck of the eight Round 2b responses

## 0. In plain English (for Paul)
- **Most dangerous holes are now closed on paper.** A hacked bot server can't empty the wallet. STOP no longer blocks selling. Paper trading no longer pretends we win races we'd lose. Bets of 0.25 SOL or more now cover their fees. Of 81 attacks: 59 fixed, 4 acceptable risks, 16 partly fixed, 1 unacceptable risk, 1 still open.
- **Two gaps can still freeze selling.** If the small "guard" computer that does all the selling crashes at night, nothing sells until you wake up and click. And if Pump.fun forces a new sell format, a person must approve the update first. Both have simple fixes, listed below.
- **The team agrees not to race at graduation, and to buy after Pump's 5-minute BOOST buying ends.** The risk: every careful bot can see that same moment on the blockchain, so it may become the next crowded race. It must be measured.
- **There is no proven edge yet.** There are 23 ideas. The best five mostly come down to one idea: "buy after the quick sellers have gone, and sell the moment the insiders start moving their tokens."
- **Real money would need 25–50 SOL plus a "tuition budget" you accept losing** (up to ~5 SOL, plus ~$225–360 a month in bills) to learn whether the edge is real. The default stays paper.

**Tags.** [VERIFIED-DOC] = I read the primary source this session. [VERIFIED-SEARCH] = search results only. [UNVERIFIED] = inference, with the test that would settle it. [DERIVED] = my arithmetic. Response files are cited as RSK-R, SEC-R, EXE-R, DAT-R, CHN-R, QNT-R, AI-R and SOC-R (`team-debate/round2/<role>-response.md`). **Host notes:** `curl` and WebFetch worked on `raw.githubusercontent.com` (I re-read Pump's PumpSwap IDL and two docs). I used 8 web searches. No live tests were possible.

---

## 1. Scorecard

### 1a. The 18 attacks not yet closed (worst first)
| ID | Status | Why | What closes it |
|---|---|---|---|
| **SEC-3** | ACCEPTED-RISK-NOT-OK | A dead guard host leaves positions unmanaged until Paul clicks "launch standby" (SEC-R). Nothing restarts it. KMS second-region copies are untested (S2) | Auto-restart plus a 60 s heartbeat alert (NEW-1) |
| **PREMISE-2** | STILL OPEN | 23 hypotheses, none proven. That is correct for now; only data can close it | Section 4's first five tests |
| **SEAM-3** | PARTLY FIXED | STOP, the allowlist and the SDK paths are fixed. Guard death and a mandatory Pump account change still stop sells | NEW-1, NEW-7 |
| **SEC-6** | PARTLY FIXED | The tolerant allowlist covers *added* instructions, not *mandatory* new sell accounts (the Sep 1 2025 type). Sells fail until someone reviews the IDL and Paul approves | NEW-7 |
| **DAT-1** | PARTLY FIXED | Two of its rules clash with Pump's own docs (NEW-8) | Allowed lengths per version; treat the field as live |
| **PREMISE-3 / QNT-1** | PARTLY FIXED | The competition-aware simulator is good, but losing Jito bundles are invisible and the 20% contested-landing figure is a guess | Canary "paper filled / live failed" report |
| **PREMISE-5** | PARTLY FIXED | Change classes and the fast path are good. The first proof still takes 21+ days plus the canary, and there is no branch for BOOST being switched off | NEW-12 |
| **PREMISE-7** | PARTLY FIXED | Per-trade costs are fine at 0.25 SOL. Bills sum to ~$225–360 a month (data $162, guard $15, AI $47–63, social $0–45), not $150. The buy cap limits the trade count | NEW-10 |
| **SEAM-6 / DAT-3** | PARTLY FIXED | Rests on untested Chainstack `token_accounts` support (D13). A Chainstack docs PR lists 5 same-type filters and 50 accounts per stream [VERIFIED-SEARCH chainstack PR #72, merge unknown]. SOL funding of side wallets is still invisible | F2/D13. Fallback: Helius `transactionSubscribe` (CHN-R) |
| **CHN-2** | PARTLY FIXED | Holder map from the stream, so it inherits the SEAM-6 gap | As SEAM-6 |
| **RSK-3** | PARTLY FIXED | Cluster-level insider flow adopted. It rests on SEAM-6 and on the insider set's quality | F1, P5 |
| **CHN-5** | PARTLY FIXED | Labels frozen, but four teams froze four different "dump" labels | C13 |
| **QNT-4** | PARTLY FIXED | Day-block bootstrap and a measured spread, but 200 trades prove only edges of 9–22% against a ~5.4% hurdle (QNT-R 1c). "Top 5% removed" is disputed | C12; state the gate's real power to Paul |
| **SEAM-7 / DAT-5** | PARTLY FIXED | Credit table plus exit reserve plus a $25 autoscale cap. The guard's RPC reads are missing, and forensics (up to 4M) vs data (2.5M) disagree. The worst case is about the plan's 10M | One table that includes the guard |
| **RSK-8** | PARTLY FIXED | Sources named, but the files disagree on which machine runs them | C9 |

### 1b. Fixed (59) or acceptable risk (4)
| ID | Status | Why |
|---|---|---|
| PREMISE-1 | FIXED | No race. A shadow racer prices what we miss. The reopen rules differ (C15) |
| PREMISE-4 | FIXED | Null, random and do-nothing baselines on every report |
| PREMISE-6 | FIXED | AI is cut to labels in shadow mode, against a $0 baseline |
| SEAM-1 | FIXED | 0.25 SOL floor; the last sell closes the account; KMS signing |
| SEAM-2 | FIXED | The 300 s clock is gone; entry is event-based |
| SEAM-4 / QNT-3 / EXE-8 | FIXED | One fee module, 1.25% per side until T6 matches it to the fee rates each trade records |
| SEAM-5 / CHN-1 | FIXED | Zero-read gate; designed for a 0-block gap |
| SEAM-8 / DAT-8 | FIXED | Separate recorder disk; the guard's journal space is reserved |
| SEAM-9 / AI-4 | FIXED | Trial counter, forward-only scoring, hash split, placebo (but see NEW-14) |
| SEAM-10 / AI-3 / SOC-1 | FIXED | Input-availability metric; labels made at `CompleteEvent`; unknown counts as neutral |
| SEAM-11 / EXE-3 | FIXED | Margin over the pool-maths quote plus re-quoting. Strong fix |
| SEAM-12 | FIXED | Joint tip-account table, tested in paper (S7 still to read) |
| SEAM-13 | FIXED | L4 fires only when value leaves to an unlisted address |
| DAT-2 | ACCEPTED-RISK-OK | Degraded mode never buys, and exits keep two other companies |
| DAT-4 | FIXED | A processed breach *arms* the sell; min-out comes from confirmed state |
| DAT-6 | FIXED | Four independent audit keys |
| DAT-7 | FIXED | Never create a PumpPortal key (but see C16) |
| DAT-9 | FIXED | Floors set per hour of the week; two signals needed |
| CHN-3 | FIXED | Outcome-relevant early-buyer share, including onward transfers |
| CHN-4 | FIXED / ACCEPTED-RISK-OK | Our own ~3-credit lookup replaces `funded-by`'s 100. Evasion accepted |
| CHN-6 | FIXED | Hard REJECT for Mayhem and non-SOL quotes |
| CHN-7 | FIXED | History can never count in a coin's favour |
| EXE-1 / EXE-2 | FIXED | Sells rebuilt every 2 blocks; 0.01 SOL exit reserve per position |
| EXE-4 | FIXED | Jupiter is out of the live path; local SDK-versus-maths check, never on sells |
| EXE-5 | ACCEPTED-RISK-OK | No bot beats Pump's sell switch. Small size, plus "first out when it reopens" |
| EXE-6 / EXE-9 | FIXED | No contested auctions; no landing rate from blogs |
| EXE-7 | FIXED | Deposit, wSOL, failed attempts and the v1 cashback path all costed |
| RSK-1 | FIXED | BOOST events replace the clock (but see NEW-11 and NEW-12) |
| RSK-2 | FIXED | Pool-drain exit deleted; `EXIT_SELL_PRESSURE` added |
| RSK-4 | FIXED | Stops chosen from the shadow grid by a rule fixed in advance |
| RSK-5 | FIXED | Only journal mints are adopted; airdrops are ignored |
| RSK-6 | FIXED | Three levers. The guard-death part sits under SEC-3 |
| RSK-7 | FIXED | One-shot emergency sell with a computed min-out |
| QNT-2 | FIXED | Worst position in the block by default |
| QNT-5 / QNT-6 / QNT-7 | FIXED | Counts per regime; paper twin; reserve-continuity check |
| QNT-8 | ACCEPTED-RISK-OK | Stated to Paul, with a fresh-regime holdout |
| AI-1 / AI-5 / AI-6 | FIXED | Yes/no outcome with ~225 coins per band; labels instead of scores; 3,000-call cap |
| AI-2 | FIXED | Flags instruction patterns, not topic words |
| SOC-2 / SOC-4 / SOC-5 / SOC-6 | FIXED | Daily cap; KOL buys not positive; bursts count as negative; firehose instead of webhooks |
| SOC-3 | ACCEPTED-RISK-OK | X data is optional, and missing data counts as neutral |
| SEC-1 | FIXED | The bot sends requests; the guard builds every transaction and pins our accounts. Without lookup tables the sell still fits: `sell_v2` has 17 accounts, ≈ 22–26 with extras, ≈ 0.8–0.9 KB of 1,232 bytes [VERIFIED-DOC IDL; DERIVED] |
| SEC-2 | FIXED | Separate guard host on a separate account (new attacks NEW-1 to NEW-4) |
| SEC-4 / SEC-5 / SEC-7 | FIXED | PAUSE/STOP/KILL; builder generated from the IDL plus exact-version exemptions; no lookup tables |
| SEC-8 | FIXED | KMS supports Ed25519 (`ECC_NIST_EDWARDS25519`, `ED25519_SHA_512`, RAW messages) [VERIFIED-SEARCH docs.aws.amazon.com]. The signature may need converting to raw 64 bytes [VERIFIED-SEARCH, unofficial]. Latency is still S1 |

---

## 2. New attacks on the revised design
| ID | Attack | Sev / Lik | Fix or test demanded |
|---|---|---|---|
| **NEW-1** | **The guard host is the new single point for every sell.** One process in one data centre, and the standby needs Paul's click. The likeliest failure is a bug in our guard code, which the standby shares | Critical / Possible | Process supervisor, EC2 auto-recovery (same instance, so still one guard), a 60 s outside heartbeat that alerts Paul, and a minimal sell-only safe mode. Drill: kill the guard at random with 3 paper positions; flat in ≤ 60 s with no human |
| **NEW-2** | **The guard's price check can refuse honest crash sells.** It checks the bot's min-out against its own RPC quote (SEC-R). If its RPC lags in a crash, its quote is too high, so the bot's honest min-out looks "too loose" | High / Likely | For sells, use the freshest slot-stamped state from any source. Accept min-out down to `max(catastrophic floor, freshest quote × (1 − m_emergency))`. Never refuse two sells in a row on price alone. Replay 200 crashes (RC2) |
| **NEW-3** | **The guard loop adds 1–2 slots to every exit.** Bot → tunnel → guard RPC re-quote → KMS (25–250 ms, other key type [VERIFIED-SEARCH via SEC-R]) → send. Slots are ~218 ms [VERIFIED-SEARCH solanacompass], so "re-quote every 2 blocks" may be shorter than one loop | Medium / Likely | Guard streams held pools rather than polling them. Set the re-quote interval from the measured loop p99 (S1 plus the tunnel) |
| **NEW-4** | **The smart exits sit on the wrong machine.** Insider-flow and sell-pressure exits need the firehose and dossier (bot host). Security's guard has "two RPCs, no feeds". A dead bot host means price stops only. A hacked one can withhold exit requests | Medium / Certain | Guard owns price and pool-flow exits on its own stream. The bot host sends advisory insider exits, never required (C9, C10) |
| **NEW-5** | **Pre-signed emergency sells are riskier than claimed.** A 10% min-out lets whoever holds a copy push the price down first and take up to ~90% of the position. Copies on a third provider are a new place to steal from. Durable-nonce transactions never expire, so re-buying the same coin can revive an old copy. Removal of durable nonces is planned (~6 months after a replacement ships) [VERIFIED-SEARCH solana.com] | High / Possible | Keep security's ban for v1; NEW-1 covers most of the need. If allowed: one rung, min-out ≥ 50% of value at signing, nonce advanced on every close, copies kept only on the guard |
| **NEW-6** | **Exit tickets fail exactly in a crash.** A tight min-out on a price up to 20 s old fails when the price runs (EXE-R). A wide one invites sandwiches | Low / Likely | Count them as cover for signer blips only |
| **NEW-7** | **A mandatory Pump account change still needs a human before we can sell** (Sep 1 2025 added two required accounts [VERIFIED-SEARCH t.me/pump_tech_updates]) | High / Possible | Sells-only auto-adopt: if the new official IDL only adds sell accounts that are seed-derived PDAs or fixed program IDs, adopt within minutes and alert. Buys wait for review. Drill: replay Sep 1 (RC8) |
| **NEW-8** | **The strict decoder clashes with Pump's own docs.** Old pools are legally shorter ("read the missing trailing fields as 0" [VERIFIED-DOC PUMP_SWAP_README]), so exact-length checks on accounts alarm on every old pool. `FIELD_ACTIVATED` relies on the README line "`virtual_quote_reserves` is 0 on all pools today", but the Sep 30 doc says v2 trades push it negative to hide waiting fees [VERIFIED-DOC NEGATIVE_VIRTUAL_QUOTE_RESERVES.md]. That also answers EXE-R X6: price on vault + virtual | High / Likely if unfixed | Allow each known layout length per version. Treat the field as a live signed value. RC3, RC4 |
| **NEW-9** | **Alarm fatigue.** Many fail-closed alarms each pause buys, and resuming needs a human plus 1,000 clean trades. Paul, who isn't a developer, will rubber-stamp, or the bot never trades | Medium / Likely | Severity classes; 7 days log-only to calibrate (RC5); auto-resume for harmless classes |
| **NEW-10** | **Buy cap × trade count × bills.** Security's example cap of 1.5 SOL a day is 6 trades at 0.25 SOL, ~180 a month. With $225–360 of bills that is **5–8% of a $25 stake**, a hurdle of ~8–11%, not 4.5–5.4% [DERIVED] | High / Certain | One table for cap, trade count, bills and hurdle. Paid extras stay off until they earn |
| **NEW-11** | **The post-BOOST moment becomes the next crowded race.** BOOST's end is public on-chain (`boost_vault_remaining` [VERIFIED-DOC IDL]), and bots know the fixed 5-minute window [VERIFIED-SEARCH htx]. Patient insiders can hold and sell into the careful buyers. Forensics' "insiders held through BOOST" variant rewards exactly that | High / Likely | Entry on state, with random jitter. Measure rival buys and tips in our ±2 slots against the 60 s before (RC1). **Crowding kill, fixed now:** rivals above the calm baseline on > 30% of entries for 2 weeks → back to paper |
| **NEW-12** | **BOOST may change or stop.** `toggle_boost` exists [VERIFIED-DOC IDL], and the 17.6 SOL isn't confirmed as fixed [VERIFIED-SEARCH htx]. With BOOST off, the rule enters at ~3.5 min, untested | Medium / Possible | Branch on `boost_enabled` / `InitBoostEvent`. No BOOST = market-structure change, paper only |
| **NEW-13** | **The ruin simulation assumes independent trades.** If the thermometer's multi-day spells are real, losses cluster | Medium / Likely | Re-run by resampling whole days of the recorded null |
| **NEW-14** | **The trial counter gets flooded** by the AI desk (≤ 20 a month), placebos, grids and 23 ideas. A global counter hits 99% in ~2 months, and then nothing can pass | Medium / Likely | Lead fixes the trial families and each family's error budget now |
| **NEW-15** | **One idea, five tests:** "sellers exhausted" (DAT E1, CHN C, QNT E2, EXE E1, RSK E1), each with a different pass mark | Medium / Certain | One family: a primary rule plus named variants (section 4) |
| **NEW-16** | **Recorder bandwidth.** The 8 Jito tip accounts carry the *whole network's* tips. Add the Token-2022 stream, failed transactions and 30k metadata files a day | Medium / Likely | Q2/D11 first. Fallback: `getBlock` only around migrations and paper orders |
| **NEW-17** | **Control paths.** How do STOP and KILL reach a guard with no inbound ports at 3 a.m.? Through the bot host, they can be blocked or faked. A stolen `DisableKey` credential freezes our exits, and whoever holds the AWS account holds the key | Medium / Possible | Separate AWS account with hardware MFA. CloudTrail alert on any `Sign` call not from the guard role. Levers sent outside the bot host (console / SSM) |
| **NEW-18** | **Is 25–50 SOL safe for Paul?** At 25 SOL the floor equals the cap, so the sizing ideas can't act. Proving +5% takes ~860 trades (RSK-R), ≈ 215 SOL of turnover. The loss is bounded by the 20% drawdown stop (5 SOL), plus theft risk, plus bills | Medium / Certain | A "tuition budget" in SOL and dollars goes in QUESTIONS_FOR_PAUL. Default: paper |

---

## 3. Contradictions the lead must rule on
| # | Topic | Side A | Side B | Red-team suggestion |
|---|---|---|---|---|
| C1 | Emergency sells when the guard or KMS is down | Risk: PSES on durable nonces with 50% and 10% rungs | Security: durable nonces refused. Execution: 30 s exit tickets | Security's ban plus NEW-1 auto-restart (NEW-5) |
| C2 | Guard standby | Security: cold standby, Paul clicks | Risk: automatic, with no human | Auto-restart the same instance; cold standby only if the data centre is lost |
| C3 | Bankroll for 0.25 SOL bets | Risk: 1% cap → ≥25 SOL | Execution: 0.5% → 50 SOL | 25 SOL minimum, 50 SOL if sizing ideas matter (NEW-18) |
| C4 | Trades per month | Risk/quant: 600 per month in the break-even tables | Security: daily buy cap ≈ 6 trades a day | One joint table (NEW-10) |
| C5 | Monthly bills | Risk $150, quant $300 | Bottom-up sum $225–360 | Use the bottom-up sum |
| C6 | Take-profit below 0.5 SOL | Risk: one step (sell ½) | Execution: no ladder | Risk (it adds only ~0.12% at calm fees), as a shadow |
| C7 | Max share of the pool | Risk 1% | Execution 1.5% | 1% until the canary measures impact |
| C8 | Slot time | Execution: 200 ms since Oct 9 2026 | Data: 0.2–0.4 s, Alpenglow 400 ms. Security/risk: 350 ms | **Execution is right:** 200 ms target, 218 ms measured [VERIFIED-SEARCH solanacompass]. 150-slot blockhash life ≈ 33 s [UNVERIFIED] |
| C9 | Where exit sources run | Data: A = Chainstack gRPC, B = Helius WSS | Security: guard uses "its own two RPCs, no feeds" | Guard gets its own Helius stream plus a poll; Chainstack stays on the bot host |
| C10 | Where insider exits run | Risk/forensics: in the exit guard | Security: minimal guard | Bot host, advisory (NEW-4) |
| C11 | How to see plain transfers | Forensics: a mint filter misses `Transfer`; use Helius `transactionSubscribe` with 50k addresses | Data: Chainstack `token_accounts` plus a Helius mint `programSubscribe` | Both are right at different layers. Account-level mint subscription for held coins; wallet-based transaction filter for candidates; F2/D13 picks the provider |
| C12 | "Still positive with the top 5% removed" | Quant: report only (tail-dependent rules always fail it) | Risk, forensics, data, execution: hard pass condition | Hard for *filters and exits*; for *entries*, quant's ≥20 tail wins plus top-3-removed ≥ 0 |
| C13 | Dump label | Forensics: −70% before +50% within 60 min. Quant: ≤ −80% within 60 min | AI: ≥ −50% within 60 min. Data: ≥ −30% within 60 s | Freeze one label per purpose, before any test runs |
| C14 | Default entry rule | Risk: BOOST over + 180 s + net flow. Forensics: Rule C | Quant: flipper < 20%. Data: fast group ≤ 25%. Execution: auction cooled | Risk's rule is the paper default, since it needs no insider ledger. The merged family's primary rule (fast group plus insiders ≤ 25% of peak, section 4) is tested against it, and the rest are named variants (NEW-15) |
| C15 | Reopen the race if… | Data: +5 pts vs the best delayed rule. Execution: +10% net | Risk: +5% net on ≥300 coins without the top 5%. Quant: four-condition RACE rule | Quant's rule plus risk's sample size |
| C16 | PumpPortal key | Data: never create one; drop PumpPortal if no keyless channel | Security: Paul may create a ≤0.05 SOL prepaid wallet | Data's rule (no key at all) |
| C17 | Metadata scope | AI: record all ~30k launches a day | Social: fetch once at 20% of the curve | Free create-event fields for all; fetch the metadata file at 20% of the curve; image hash for all fetched |

---

## 4. Attacks on every edge idea
**Ratings:** STRONG = clear mechanism, a high-power test, no race to win, hard for apps to copy. PLAUSIBLE = worth a test. WEAK = test only if nearly free. DEAD = doesn't fit the adopted design. **"Honest?"** = pass mark fixed in advance / sample big enough / no look-ahead.

| ID | Idea | Strongest reason it fails | Honest? | Rating |
|---|---|---|---|---|
| RSK-E1 | Size by the insiders' worst-case dump | At 25 SOL the floor equals the cap, so it is really a skip filter. Rests on SEAM-6 | Yes; also test it as a filter | PLAUSIBLE |
| RSK-E2 | Exit tournament on every graduate | Paper crash fills drive the result. The best exit on null entries may not be best on ours | Yes; paired, ~200 a day, held-out weeks | **STRONG** (loses less) |
| RSK-E3 | Grow on proof, shrink on decay | Not an edge over bots. No room to grow below 50 SOL | Yes; needs 90 days | PLAUSIBLE (risk control) |
| SEC-E1 | First to work after a Pump update | DAT-1 pauses *our* buys after every change. Only ~5 events, and the outcome is rival counts, not P&L | Fixed, but n = 5 and a proxy outcome | WEAK |
| SEC-E2 | KMS cost parity | Not an edge | n/a | WEAK (adopt anyway) |
| EXE-E1 | Buy when the auction has cooled | After minute 5 nearly every slot is "cooled", so it becomes a fixed time. Cheaper than app users is relative, not profit | Yes; 500 coins | WEAK (hygiene) |
| EXE-E2 | Crash exits with no sandwich tax | The price may outrun the re-quote, and the guard loop adds 1–2 slots (NEW-3) | Yes; P14 + 200 crashes | PLAUSIBLE |
| EXE-E3 | Sell into BOOST's buys | We enter *after* BOOST, so we rarely hold during it, and front-runners already take it | Yes | DEAD |
| DAT-E1 | Clock of the fast wallets' remaining tokens | "Sellers gone" ≠ "buyers coming". May be crowded (NEW-11) | Yes; fit 300, test 300 | PLAUSIBLE (merge) |
| DAT-E2 | Blind-spot pockets | Synthetic migration is now normal. Non-SOL quotes are rejected in v1. Our buys are paused after changes | Yes, but groups of ≥ 50 are scarce | WEAK |
| DAT-E3 | Exit on insider transfers before the price moves | Dies if F1 finds under 10% of dumped tokens arrive by transfer. False exits cost ~3% each | Yes; ≥ 200 dumps | PLAUSIBLE (merge with CHN-A) |
| CHN-A | Insider overhang that follows the tokens | Exchange-funded unlinked wallets evade it. GMGN already shows an insider % [VERIFIED-SEARCH via CHN-R] | Yes; ≥ 1,000, held-out week, F1 kills it early | PLAUSIBLE |
| CHN-B | Crew fingerprints | Bundlers build a *new* lookup table per launch [VERIFIED-SEARCH via CHN-R]. Tip and compute settings are tool defaults shared by unrelated crews | Yes; shuffle placebo, forward only | PLAUSIBLE (low coverage) |
| CHN-C | Buy after the known sellers leave | Same family as DAT-E1. "Held through BOOST" is gameable | Yes; ≥ 500 | PLAUSIBLE (merge) |
| QNT-E1 | Losers' tape (failed buys) | Losing bundles never land. Slippage failures follow price moves, so it may be lagged momentum | Stage A's standard error ignores same-day correlation. Must beat a momentum baseline | WEAK |
| QNT-E2 | Flipper clock | Same family. 14-day warm-up. Flippers rotate wallets | Yes; walk-forward | PLAUSIBLE (merge) |
| QNT-E3 | Market thermometer | The "weather" may be obvious already (SOL price, launch count), or change faster than 24–72 h | Yes; 6–8 weeks. Add a $0 graduation-count baseline | PLAUSIBLE |
| AI-E1 | Original vs copy in a theme wave | A third-party GMGN extension already flags and auto-buys the "first same-name token" [VERIFIED-SEARCH extscope.org], so leaders are crowded. Waves can be spammed | Mostly; the optional extension to 1,000 coins is a mild forking path | PLAUSIBLE (merge with SOC-E1; avoid followers) |
| AI-E2 | Overnight research desk with a placebo | May be no better than random search. The kill test takes 3+ months | Yes; the placebo is excellent | PLAUSIBLE (process) |
| AI-E3 | Rule-change reader | Code already pauses on change. The answer key may be in training data. No P&L link | Partly (contamination admitted) | WEAK (~$10/month tool) |
| SOC-E1 | Theme-wave detector | As AI-E1. Counting distinct funders blunts spam | Yes; ≥ 1,000 | PLAUSIBLE (merge) |
| SOC-E2 | KOL side-wallet bait | Side wallets can be funded through exchanges. Maybe under 50 events in 60 days | Yes; 60 days | WEAK |
| SOC-E3 | Shape of organic spread on X | Few posts exist at entry (SEAM-10). X policy risk | Yes; cheap ($10–20) | WEAK |

**The 5 to test first**
1. **Exit tournament (RSK-E2)**, with EXE-E2's chase and DAT-E3/CHN-A's insider exits as contestants. It acts on every trade, whatever the entry. Paired tests on ~200 graduates a day give the most power we have, and it needs no race.
2. **One merged "sellers exhausted" entry family** (DAT-E1 + CHN-C + QNT-E2; EXE-E1 as a variant). Primary rule: "BOOST over **and** fast group plus insiders hold ≤ 25% of their peak", with the NEW-11 crowding kill. Everything else depends on the entry.
3. **Market thermometer (QNT-E3).** Free with the null. It decides *whether* to trade at all, and doubles as the silent-change alarm.
4. **Taint-tracked overhang (CHN-A)**, as a shared feature for tests 1 and 2 and RSK-E1. F1 can kill the taint part within days.
5. **Theme-wave position (SOC-E1 + AI-E1), code-only first.** It is the only off-chain information in the top five, and it **must be recorded from day 1** (it can't be backfilled honestly). Haiku is added only if it lifts AUC by ≥ 0.01.

Also record from day 1 (cheap now, impossible later): lookup tables and tips (CHN-B), and failed transactions (QNT-E1).

---

## 5. Verdict on the premise
**Is there a credible path to beating other bots? Yes, but it is narrow, and it is not the one Paul asked for.**
- **Speed.** The team has rightly given up on being faster at *entry*. We would be faster than app users at *exits* (sells triggered by the stream, pre-built, protected, with a tight margin, against apps that suggest 30–50% slippage [VERIFIED-SEARCH via RSK-R]), and faster to *understand* where insider tokens went. DESIGN.md must say plainly: "We won't be first in. We aim to choose better when to get in, and to get out faster."
- **What would have to be true** (all of it, measured on the recorder within 2–4 weeks):
  1. The post-BOOST null, after all costs and with last-in-block fills, loses **≤ ~5 points per trade**. At −15 to −20, no realistic filter closes the gap [UNVERIFIED; P2/P3].
  2. At least one tape-only feature (overhang, taint, flipper clock) passes Stage A (|ρ| ≥ 0.10 in both halves) **and** the crowding check (NEW-11).
  3. The exit tournament wins **≥ 2 points per trade** on held-out weeks.
  4. Together these give **≥ +5–6% net per trade** on ≥ 5–10 qualifying trades a day, so bills stay near 2–3% of turnover.
  5. Pump leaves BOOST and migration alone for **6–8 weeks at a time**. The recent pace is roughly one change every 4 weeks. The newest dated README entry is Oct 13 [VERIFIED-DOC], and I found no BOOST change since July [VERIFIED-SEARCH].
  6. The canary's "paper filled / live failed" gap is **≤ 1–2 points**.
- **Honest odds (my judgment, [UNVERIFIED]):** about 1 in 4 that some rule passes Gate v2 within ~3 months, and lower that it survives the canary and the next Pump change. What is near-certain: the desk will lose less to bugs, theft and fees than most retail bots. That is Paul's priority 1, and it is real.
- **Stop rule, fixed now:** after 4 weeks of tape, if the null is worse than −10% per trade at every entry time *and* no Stage A screen passes, recommend keeping only the recorder (~$160 a month) as research, with no canary.

## Tests to run once allowed (new in this round; read-only)
| # | Test | Domain(s) |
|---|---|---|
| RC1 | Crowding at BOOST's end: buys, failed buys and tips per slot from −60 s to +180 s around the last `BoostBuyAndBurnEvent`, on 300 graduates | gRPC host, `mainnet.helius-rpc.com` |
| RC2 | Guard-RPC lag during 50 recorded crashes: `getMultipleAccounts` versus the stream, by slot (NEW-2) | `mainnet.helius-rpc.com`, Chainstack gRPC host |
| RC3 | `virtual_quote_reserves` on 200 live pools: share non-zero, sign, size during and after BOOST (NEW-8) | `api.mainnet-beta.solana.com` |
| RC4 | Pool-account byte lengths across old and new pools: how many layout versions exist (NEW-8) | same |
| RC5 | Alarm rate per class with DAT-1's monitors running log-only for 7 days (NEW-9) | gRPC host |
| RC6 | MB/hour of the 8 Jito tip accounts and the Token-2022 stream (NEW-16, = Q2/D11) | gRPC host |
| RC7 | Qualifying entries per day under the merged primary rule (NEW-10) | recorder (local) |
| RC8 | Replay of the Sep 1 2025 mandatory-account change against the sells-only auto-adopt rule (NEW-7) | `api.github.com` (pump-public-docs history) |
| RC9 | KMS Ed25519 p99 sign time and output format from a Frankfurt instance (= S1) | `kms.eu-central-1.amazonaws.com` |

## Sources
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/idl/pump_amm.json (`sell_v2` has 17 accounts, `sell` 21, `buy_exact_quote_in_v2` 17; `BoostBuyAndBurnEvent` fields incl. `boost_vault_remaining`, `virtual_quote_reserves`; `toggle_boost`)
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/NEGATIVE_VIRTUAL_QUOTE_RESERVES.md (v2 fees make the field negative; price on vault + virtual)
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/docs/PUMP_SWAP_README.md ("0 on all pools today"; older pools are shorter, read missing fields as 0)
- [VERIFIED-DOC] https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md (newest dated entry Oct 13; no BOOST mention)
- [VERIFIED-SEARCH] AWS KMS Ed25519: https://docs.aws.amazon.com/cli/latest/reference/kms/sign.html ; https://github.com/gtg7784/solana-kms-signer ; https://pkg.go.dev/gitlab.com/phpboyscout/go/signing-aws-kms
- [VERIFIED-SEARCH] Durable nonce removal plan: https://solana.com/upgrades/durable-nonce-deprecation ; https://solana.com/docs/core/transactions/durable-nonces
- [VERIFIED-SEARCH] 200 ms slots live Oct 9 2026, 218.3 ms measured: https://solanacompass.com/news/solanas-200ms-slot-time-is-live-on-mainnet-at-epoch-1053-completing-simd-0525 ; https://solanacompass.com/news/solanas-first-full-epoch-at-the-200ms-slot-time-target-averaged-2183ms-and-lasted-262-hours ; https://theblock.co/news/ecosystems/2026-08-22-solana-cuts-mainnet-slot-time-to-350-milliseconds-in-first-step-toward-200ms-goal-412521
- [VERIFIED-SEARCH] BOOST window known to bots, 17.6 SOL not confirmed as fixed, post-window dump risk: https://www.htx.com/news/443626/ ; https://www.kucoin.com/blog/pump-fun-boost-mode-explained ; https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives
- [VERIFIED-SEARCH] Chainstack filter limits (PR, merge status unknown) and other providers' limits: https://github.com/chainstack/dev-portal/pull/72.patch ; https://docs.rpcfast.com/rpc-fast-saas-solana/data-streaming/yellowstone-grpc ; https://docs.vali.wtf/products/grpc/grpc.md
- [VERIFIED-SEARCH] "First among same-name tokens" auto-snipe extension: https://www.extscope.org/extension/nipccajfbdodfpbnnjaohckbjgiaodkk
- [VERIFIED-SEARCH] Pump mandatory-account change Sep 1: https://t.me/s/pump_tech_updates/29
- All other figures are cited from the eight `team-debate/round2/*-response.md` files and from `team-debate/round2/red-team-attacks.md`.
