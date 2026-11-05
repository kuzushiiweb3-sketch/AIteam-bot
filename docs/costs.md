# Costs: the re-checked price table (Phase 0 deliverable)

## In plain English (for Paul)
- **Expected bills: about USD $295 a month (about CAD $420) once the paper bot and guard computers run.** While we only record and research, it is about USD $230–260 (CAD $330–370). That is 33–42% of your CAD $1,000 monthly budget.
- **The expected figure rose about $20 from DESIGN.md.** Re-checking the prices showed the recorder's disk costs a little more, and Amazon charges for the guard computers' internet addresses.
- **The worst case is tight.** It is about USD $698 (CAD ~$990), right at your budget, and it goes over if your card adds a foreign-currency fee, if sales tax is added, or if the US dollar strengthens.
  - The worst case can only happen through several deliberate choices, and we would ask you first.
  - Every line that is billed by usage has a hard cap.
- **Vendor pricing pages are blocked in this environment**, so every price here comes from search results. Each line says which live page still needs checking.
- **Two questions for you** (§10): does the CAD $1,000 include sales tax and card fees? And the research ceiling (Q3, default USD $750) would be reached about 2–3 weeks *before* the month-3 checkpoint.

---

## 1. How this was checked
- **Exchange rates and SOL price used:**
  - 1.42 CAD per USD (Oct 14 2026 [VERIFIED-SEARCH, 30rates]; July–August 2026 was 1.40–1.41 [VERIFIED-SEARCH, pluang]). No November quote was found.
  - 1.12 USD per EUR (Oct 30 2026 [VERIFIED-SEARCH]).
  - SOL ≈ $100 (about $101 on Oct 27 2026 [VERIFIED-SEARCH]).
  - CAD figures = USD × 1.42, rounded to the dollar.
- **Searches.** 12 web searches on 2026-11-05, mostly in extended mode.
- **Direct fetches failed.** Fetching `chainstack.com`, `www.helius.dev` and `docs.solanatracker.io` was refused because those hosts are not on this session's allowed list. So **every line still needs its live pricing page** (tests PX-1 to PX-12, §11). Lines where search results *conflict* are marked **critical**.
- **Tags** are as in `docs/assumption-register.md`: [VERIFIED-DOC], [VERIFIED-SEARCH], [UNVERIFIED], [DERIVED]. A-0xx numbers point to that register.

---

## 2. Vendor unit prices (re-checked 2026-11-05)

| # | Item | Price found | USD / month | CAD / month | Tag (date) | Live page still needed | Register, test |
|---|---|---|---|---|---|---|---|
| U1 | Chainstack Growth plan | $49 a month ($40 if paid yearly). 20M request units. 250 requests/s in general, but one source says Solana is limited to 50/s on Growth | 49 | 70 | VERIFIED-SEARCH (11-05) | Yes | A-051, PX-1 |
| U2 | Chainstack Yellowstone gRPC add-on | Chainstack's own guide: **$49 for 2 streams**, $149 for 7, $449 for 25. A third-party page: $49 for **1** stream, $149 for 5 | 49 (or 149) | 70 (or 212) | VERIFIED-SEARCH, **conflicting** (11-05) | **Yes, critical** | A-052, PX-1 |
| U3 | Helius Developer plan | $49 a month, 10M credits, 50 requests/s | 49 | 70 | VERIFIED-SEARCH (11-05). One source mentions a Sep 2026 pricing refresh | Yes | A-062, PX-2 |
| U4 | Helius extra credits / autoscale | $5 per 1M credits. A third-party page says autoscale is capped on Developer | 5 per 1M (25 at a 5M cap) | 7 per 1M (36) | VERIFIED-SEARCH (11-05) | Yes | A-050, PX-2, G8 |
| U5 | Solana Tracker standalone gRPC (fallback only) | €200 a month flat, no data caps, 25 connections, EU and US | 224 | 318 | VERIFIED-SEARCH (11-05) | Yes | A-063, PX-3 |
| U6 | Bot server, shared 4 vCPU / 8 GB | about $48 | 48 | 68 | UNVERIFIED | Yes (G7) | A-058, PX-6 |
| U7 | Bot server, dedicated 4 vCPU / 16 GB | Vultr VX1 ~$86, Vultr High Frequency $96, DigitalOcean General Purpose $126. These are default-region prices (Frankfurt not confirmed); the DigitalOcean snapshot is ~10 months old | 86–126 | 122–179 | VERIFIED-SEARCH (11-05) | Yes | A-058, PX-6 |
| U8 | Block storage (recorder disk) | ~$0.10 per GB-month on NVMe (DigitalOcean $10 per 100 GB); ~$0.025 on HDD tiers | 200 GB: 20 (NVMe) / 5 (HDD) | 28 / 7 | VERIFIED-SEARCH (11-05; aggregators disagree) | Yes | A-067, PX-7 |
| U9 | Archive (object storage) | ~$5–6 for 250 GB–1 TB | 5 | 7 | UNVERIFIED | Yes | A-057, PX-7 |
| U10 | AWS t4g.small, Frankfurt | ~$0.019 an hour | 14 | 20 | VERIFIED-SEARCH (11-05; aggregator) | Yes | A-064, PX-4 |
| U11 | AWS t4g.micro, Frankfurt (standby) | about half of t4g.small | 7 | 10 | UNVERIFIED | Yes | PX-4 |
| U12 | AWS public IPv4 address | ~$0.005 an hour each | 3.65 each | 5 each | UNVERIFIED (memory) | Yes | A-066, PX-4 |
| U13 | AWS KMS key vault | $1 per key a month, plus $0.15 per 10,000 asymmetric signs. Asymmetric calls are excluded from the free tier. One source lists $0.03 for ECC keys | ~1.05 | ~1.5 | VERIFIED-SEARCH (11-05) | Yes | A-065, PX-5 |
| U14 | AWS disks, lease table, alarms, logs, data out | small | 3–9 | 4–13 | UNVERIFIED | Yes | PX-4 |
| U15 | Anthropic Claude API | Per million input / output tokens: Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10, Opus 5.5 $4 / $20, Fable 5.1 $10 / $50. Batch is 50% off | by use (capped, §9) | — | VERIFIED-DOC (cached 10-06), matched by VERIFIED-SEARCH (11-05) | Yes | A-068, PX-8 |
| U16 | X API, pay-per-use | Post read $0.005 [docs.x.com in search]; user read $0.010. Counts requests about $0.005 (recent) / $0.010 (full archive) [third-party] | by use (capped, §9) | — | VERIFIED-SEARCH (11-05) | Yes | A-070, PX-9 |
| U17 | Dead-man's switch / alert service | Free tiers: Healthchecks.io (20 checks), Better Stack (10 heartbeats), Cronitor (5). Paid: Healthchecks $5–17+, Cronitor ~$10–25, Better Stack $29. Native phone push not confirmed | 0 (free) to 17 | 0–24 | VERIFIED-SEARCH (11-05; blogs disagree) | Yes (G6) | A-055, PX-10 |

**Rejected alternatives, for reference** [VERIFIED-SEARCH, Round 1–2 files, 11-04; A-080]:

| Item | Price |
|---|---|
| Helius LaserStream (needs the Business plan) | $499 |
| Second full firehose (Shyft) | $199 |
| bloXroute | ~$300 |
| Own Solana node | $1,800+ |
| Racing infrastructure | ~$2,000+ |
| Turnkey | $0.10 per signature |
| Dune | ~$75 |

---

## 3. Monthly bills, line by line (DESIGN.md §5a, re-checked)

| # | Line | Starts in phase | DESIGN.md Low / Exp / High (USD) | **Re-checked Low** | **Exp** | **High** (USD) | Exp CAD | High CAD | Tag (date) | What changed and why |
|---|---|---|---|---|---|---|---|---|---|---|
| L1 | Chainstack Growth + Yellowstone add-on (2 streams) | 0–1 | 98 / 98 / 215 | 98 | 98 | **273** | 139 | 388 | VERIFIED-SEARCH (11-05) | High = Solana Tracker €200 (**$224** at 1.12) **plus** keeping Chainstack Growth ($49) for the guard's backup price reads and block capture. DESIGN.md used $215 and assumed Chainstack was dropped. If the add-on turns out to be 1 stream for $49, the expected figure becomes $198 (flag F3) |
| L2 | Helius Developer | 1 (free in 0) | 49 / 49 / 49 | 49 | 49 | 49 | 70 | 70 | VERIFIED-SEARCH (11-05) | No change |
| L3 | Helius autoscale (capped) | 3 | 0 / 0 / 25 | 0 | 0 | 25 | 0 | 36 | VERIFIED-SEARCH (11-05) | No change ($5 per 1M confirmed) |
| L4 | Bot server | 1 | 24 / 48 / 120 | 24 | 48 | **126** | 68 | 179 | Low/exp UNVERIFIED; high VERIFIED-SEARCH (11-05) | High = DigitalOcean's 4 vCPU / 16 GB General Purpose plan at $126 |
| L5 | Recorder disk (200 GB) + archive | 1 | 10 / 15 / 30 | 10 | **25** | **40** | 36 | 57 | VERIFIED-SEARCH (price per GB) + UNVERIFIED (archive) (11-05) | 200 GB NVMe at ~$0.10/GB = $20, plus ~$5 archive. Low = an HDD tier. High = a bigger disk plus an archive that grows every month |
| L6 | Guard + standby + key vault + alarms (AWS Frankfurt) | 3 | 22 / 25 / 35 | **27** | **35** | **48** | 50 | 68 | t4g and KMS VERIFIED-SEARCH; the rest UNVERIFIED (11-05) | DESIGN.md left out AWS's public-IPv4 charge (~$7 for two machines) and priced the standby too low. Itemised in §3a |
| L7 | AI (Anthropic API) | 1 (change reader only) / 2 (research desk) | 10 / 40 / 75 | Ph1: 5 / Ph2+: 10 | Ph1: 10 / Ph2+: 40 | Ph1: 25 / Ph2+: 75 | 14 / 57 | 36 / 107 | DERIVED (prices VERIFIED-DOC/SEARCH) | Prices unchanged. In Phase 1 only the rule-change reader runs: ~$1 per Pump change × ~10 a month |
| L8 | X (Twitter) data, only if test SOC-S1 passes **and** you say yes | 2 | 0 / 0 / 45 | 0 | 0 | 45 | 0 | 64 | VERIFIED-SEARCH (11-05) | No change; capped at $1.50 a day |
| L9 | Alert and dead-man's-switch service | 3 | 0 / 0 / 10 | 0 | 0 | **17** | 0 | 24 | VERIFIED-SEARCH (11-05) | We plan on a free tier. A paid heartbeat tier costs $5–29 |

### 3a. The AWS guard account, itemised (Frankfurt, USD a month)

| Item | Low | Expected | High | Tag |
|---|---|---|---|---|
| Guard: t4g.small (730 h × ~$0.019) | 14 | 14 | 14 | VERIFIED-SEARCH |
| Standby: t4g.micro (low, expected) or t4g.small (high) | 7 | 7 | 14 | micro UNVERIFIED; small VERIFIED-SEARCH |
| Disks (2 small gp3 volumes) | 1.5 | 3 | 4 | UNVERIFIED |
| Public IPv4 addresses (1–2 × ~$3.65) | 3.65 | 7.30 | 7.30 | UNVERIFIED |
| KMS key + signatures | 1 | 1.1 | 1.2 | VERIFIED-SEARCH |
| Lease record + lever parameter | 0 | 1.5 | 3 | UNVERIFIED |
| Alarms, audit trail, logs | 0 | 1 | 3 | UNVERIFIED |
| Data sent out | 0 | 0 | 1 | UNVERIFIED |
| **Total (rounded)** | **27** | **35** | **48** | DERIVED |

The low case assumes the standby can reach the internet without its own public IPv4 address [UNVERIFIED; PX-4].

---

## 4. Monthly totals by phase, against your budget
**Budget: CAD $1,000 a month = USD $704 at 1.42.**

### 4a. The totals

| Phase | What is running | Low USD (CAD) | **Expected USD (CAD)** | High USD (CAD) | Expected, % of budget | High, % of budget |
|---|---|---|---|---|---|---|
| **0** Setup and network tests (1–2 weeks) | Free tiers; perhaps one month of Chainstack for the bandwidth tests | 0 (0) | **98 (139)** | 150 (213) | 14% | 21% |
| **1** Recorder and decoders | L1, L2, L4, L5, L7 (reader only) | 186 (264) | **230 (327)** | 513 (728) | 33% | 73% |
| **2** Research and backtests | Phase 1 plus the AI research desk; X only if its test passes | 191 (271) | **260 (369)** | 608 (863) | 37% | 86% |
| **3** Paper bot + guard pair (**Phases 4–5 have the same bills**) | Phase 2 plus L3, L6, L9 | 218 (310) | **295 (419)** | **698 (991)** | 42% | **99%** |
| **Recorder-only** (the week-4 stop option) | L1, L4, L5; Helius on its free plan if that suffices; AI desk off | 132 (187) | **171 (243)** | 371 (527) | 24% | 53% |
| *DESIGN.md, for comparison* | *Phases 1–2 / Phase 3+* | *191 / 213* | *250 / 275* | *534 / 604* | | |

How each total is built (USD):
- **Phase 0:**
  - Expected = one month of Chainstack ($98), which then carries on into Phase 1 (not counted twice).
  - High = that, plus an early Helius Developer month ($49) if the free tier's limits block the history tests, plus ~$3 of test calls.
- **Phase 1:**
  - Low 98 + 49 + 24 + 10 + 5 = 186.
  - Expected 98 + 49 + 48 + 25 + 10 = 230.
  - High 273 + 49 + 126 + 40 + 25 = 513.
- **Phase 2:**
  - Low 98 + 49 + 24 + 10 + 10 = 191.
  - Expected 98 + 49 + 48 + 25 + 40 = 260.
  - High 273 + 49 + 126 + 40 + 75 + 45 = 608.
- **Phase 3:**
  - Low 191 + 27 = 218.
  - Expected 260 + 35 = 295.
  - High 608 + 25 + 48 + 17 = 698.
  - Phases 4–5 add only KMS signing (cents). Real money at risk is separate (§8).
- **Recorder-only:**
  - Low 98 + 24 + 10 = 132.
  - Expected 98 + 48 + 25 = 171.
  - High 224 (Solana Tracker) + 49 + 48 + 40 + 10 = 371. That is **$245 if we never had to switch provider**.

### 4b. What it takes to reach the high case
Going from the Phase 3 expected ($295) to the high ($698) adds $403:

| Kind | Driver | Extra USD |
|---|---|---|
| **Deliberate choices** (they can't happen by drift) | Switch the stream to Solana Tracker | +175 |
| | Biggest bot server | +78 |
| | Bigger disk and archive | +15 |
| | Larger standby and AWS extras | +13 |
| | Paid alert tier | +17 |
| | X data (needs your yes) | +45 |
| **Usage-billed, hard-capped** | Helius autoscale | +25 |
| | AI up to its Console cap | +35 |

**Usage drift alone**, with no new decisions, can lift Phase 3 from $295 to about **$355 (CAD ~$504)**. That is half the budget.

### 4c. Sales tax, card fees and the exchange rate
Two unknowns sit on top of the sticker prices [UNVERIFIED; question PX-12 / A-061]:
- **Card fee.** Many Canadian credit cards add about 2.5% on purchases in US dollars or euros.
- **Sales tax.** Foreign digital-service vendors may add Canadian sales tax: 5% GST, up to 15% HST, depending on your province.

| Case | Sticker CAD | + 5% GST + 2.5% card fee (× 1.076) | + 15% HST + 2.5% card fee (× 1.179) |
|---|---|---|---|
| Phase 1 expected / high | 327 / 728 | 351 / 784 | 385 / 859 |
| Phase 2 expected / high | 369 / 863 | 397 / 929 | 435 / **1,018** |
| Phase 3 expected / high | 419 / 991 | 451 / **1,067** | 494 / **1,168** |

| CAD per USD | 1.35 | 1.42 (used) | 1.45 | 1.50 |
|---|---|---|---|---|
| Phase 3 expected (USD 295) in CAD | 398 | 419 | 428 | 443 |
| Phase 3 high (USD 698) in CAD | 942 | 991 | **1,012** | **1,047** |

**The verdict.**
- **The expected cost fits in every combination** (at most CAD ~$494).
- **The high case does not.** Its sticker price crosses CAD $1,000 once the rate passes **1.433 CAD per USD**, and it crosses earlier with any tax or card fee.

So the team follows two rules:
1. When forced into one expensive choice (for example the provider switch), we offset it elsewhere: X stays off, and the server stays at the expected size.
2. The budget guard (cap C-12, §9) asks you **before** any change that would push the projected all-in month above **CAD $900**.

---

## 5. One-off costs

| Item | When | USD | CAD | Tag (date) | Note |
|---|---|---|---|---|---|
| X history test (SOC-S1) | Phase 2, only with your yes (Q17) | 10–20 | 14–28 | DERIVED from VERIFIED-SEARCH prices (11-05) | Prepaid credit, so it can't overrun |
| Chainstack month bought in Phase 0, if the bandwidth test (D4) then fails | Phase 0 | up to 98 | up to 139 | VERIFIED-SEARCH (11-05) | The most we could waste; accepted as the price of the test |
| Hardware security keys for the AWS root login (main + backup) | Phase 3 | ~60–120 | ~85–170 | UNVERIFIED | DESIGN.md names one key; a spare is safe practice |
| Hardware wallet (your cold wallet) | Before Phase 5 only | 80–150 | 114–213 | UNVERIFIED | Only if you ever go live |
| Dune | — | ~75 a month | ~107 | VERIFIED-SEARCH (11-04) | Skipped by default |
| *Not counted* | — | — | — | — | Your own Claude subscription for the design team |

---

## 6. Cost per trade (DESIGN.md §5b), in USD and CAD
**Inputs** (register rows in brackets):
- Pump fee 1.25% per side [VERIFIED-SEARCH, A-001].
- Price impact ≈ 2 × bet ÷ 85 SOL pool [DERIVED; pool size UNVERIFIED, A-036, A-037].
- Network fees and tips [DERIVED, A-038–A-040].
- Sandwich allowance 0.2% on crash exits [UNVERIFIED, A-041].
- Exit mix 70% calm / 30% crash [UNVERIFIED, A-042].
- SOL = $100 [VERIFIED-SEARCH, A-059].
- KMS signing: $0.000015 per signature [VERIFIED-SEARCH, A-065]. That is under $0.0002 a trade even with 10 re-signs in a crash chase, so we ignore it.

| Bet | Calm | Calm USD | Calm CAD | Crash | Crash USD | Crash CAD | **Blended (70/30)** | **USD** | **CAD** |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 SOL (canary only) | 3.07% | 0.31 | 0.44 | 7.04% | 0.70 | 1.00 | **4.26%** | **0.43** | **0.60** |
| **0.25 SOL (the floor)** | 3.22% | 0.81 | 1.14 | 4.93% | 1.23 | 1.75 | **3.73%** | **0.93** | **1.32** |
| 0.5 SOL | 3.75% | 1.87 | 2.66 | 4.70% | 2.35 | 3.34 | **4.04%** | **2.02** | **2.87** |
| 1.0 SOL (≥ 100 SOL bankroll and pool) | 4.88% | 4.88 | 6.93 | 5.46% | 5.46 | 7.75 | **5.05%** | **5.05** | **7.17** |

The 0.1 SOL row is new, worked out by the same method [DERIVED]. Fixed fees weigh more on small bets, so a 50-trade canary costs about 0.21 SOL in fees, well inside its 1 SOL budget.

**Bills per trade:** at the expected $295 and 10 trades a day (300 a month), each trade also carries **$0.98 (CAD $1.40)** of bills. At 20 a day, it is $0.49.

---

## 7. Break-even gain per trade (DESIGN.md §5c), recomputed with the $295 expected bills
Break-even = blended per-trade cost + bills ÷ monthly turnover (30 days, SOL = $100) [DERIVED].

| Bankroll → bet | 3 trades/day | 6/day | **10/day** | 20/day |
|---|---|---|---|---|
| 25 SOL → 0.25 SOL | 16.8% | 10.3% | **7.7%** | 5.7% |
| 50 SOL → 0.5 SOL | 10.6% | 7.3% | **6.0%** | 5.0% |

- **Against DESIGN.md.** DESIGN.md had 16.0 / 9.8 / 7.4 / 5.6 and 10.2 / 7.1 / 5.9 / 5.0. The change is small.
- **At 10 trades a day,** the low ($218) and high ($698) bill cases give:
  - 6.6% / 13.0% at 0.25 SOL;
  - 5.5% / 8.7% at 0.5 SOL.
- **The SOL price matters here.** At 0.25 SOL and 10 trades a day, the break-even is 9.3% at SOL $70 and 6.4% at SOL $150. A cheaper SOL means less dollar turnover to spread the bills over.

---

## 8. Money at risk, only if you ever go live (DESIGN.md §5d). These are not bills
At a 25 SOL bankroll (USD $2,500, CAD ~$3,550):

| Item | SOL | USD | CAD |
|---|---|---|---|
| Drawdown stop (live trading halts after a 20% fall) | 5 | 500 | 710 |
| Optional canary budget | 1 | 100 | 142 |
| Hot-wallet theft bound (only if the guard itself is hacked) | ~3.3 | ~330 | ~469 |
| Daily buying limit (10%; the bound if the bot server is hacked) | 2.5 | 250 | 355 |

---

## 9. Every hard spending cap, and who sets it

### 9a. Caps on the bills

| # | What it limits | Cap (default) | Who sets it, and where | Hard or soft | From |
|---|---|---|---|---|---|
| C-1 | Anthropic API spend | **$75 a month** (Q11) | **You**, in the Anthropic Console's spend-limit setting, when you create the key | Hard: the API stops at the limit [VERIFIED-DOC, AI round 1 source D3: https://platform.claude.com/docs/en/api/rate-limits] | Phase 1 |
| C-2 | AI volume | 3,000 label calls a day; ≤ 3 AI rules a night; research runs batch-only | **The bot** (settings file; every change is logged in the daily summary) | Hard, in code | Phases 1–2 |
| C-3 | Helius overage | Autoscaling **off** (Q10). If you say yes: **$25 a month** (5M credits) | **You**, in the Helius dashboard's billing settings | Hard at the vendor [cap behaviour UNVERIFIED, G8] | Phase 3 |
| C-4 | Helius credit use | Optional jobs stop at 6M credits (5M if autoscale is off); forensics 100k a day (60k if off); a 2.6M guard reserve nothing else may touch | **The bot** (credit meter in `monitors/`) | Hard, in code | Phase 1 |
| C-5 | Chainstack | Flat plan with 20M request units included; no automatic upgrade | **You** choose the plan. **The bot** meters its Chainstack requests against the 20M (proposed here) | Fixed price; behaviour over 20M UNVERIFIED (G4, PX-1) | Phase 0–1 |
| C-6 | Solana Tracker (only if we must switch) | €200 flat, no overages [VERIFIED-SEARCH] | **You** | Fixed | If needed |
| C-7 | X data | Prepaid credit with no automatic top-up ($10–20 for the test), then **$1.50 a day** | **You** (prepaid balance in the X Developer Console); **the bot** (daily cap) | Hard (prepaid) and in code | Only if Q17 = yes |
| C-8 | twitterapi.io / SocialData | Prepaid balances. SocialData refuses calls when the balance is empty [VERIFIED-SEARCH] | **You** | Hard (prepaid) | Only if the X test passes |
| C-9 | Bot server | One fixed plan. The bot's provider token can't create or resize servers [UNVERIFIED per provider, G7] | **You** | Fixed | Phase 1 |
| C-10 | Disk and archive | Alarms at 70 / 85 / 95% full; the recorder stops at 95%; archive size in the daily summary | **The bot** | Soft: alarms, no dollar cap (flag F7) | Phase 1 |
| C-11 | AWS guard account | AWS has no hard spending cap [UNVERIFIED]. An AWS Budgets alert at **$45 a month** (actual and forecast) goes to your email and phone | **You**, in the AWS Billing console under Budgets (we write the click-by-click steps in Phase 3) | Alert only (flag F6) | Phase 3 |
| C-12 | **Monthly budget guard** (*proposed in this file; red-team must review it before adoption*) | The daily summary shows month-to-date and projected spend in CAD. **At 75%** of CAD $1,000: a warning line. **At 90% (CAD $900)**: a phone alert, and optional usage-billed jobs pause. The team never changes a plan or adds a paid service that would push the projected all-in month above CAD $900 without your OK | **The bot** (`reports/daily/`) plus a team rule | Soft (code and process) | Phase 1 |
| C-13 | Research ceiling (stop rule §8, point 5) | **USD $750 in total** (Q3 default). See flag F8 | **You** (Q3); the bot keeps the running total | Stop rule | Phase 1 onward |
| C-14 | Stop checkpoints | Week 4 → recorder-only; month 3 → full stop (DESIGN.md §8) | Written in DESIGN.md; you can overrule | Process | — |

### 9b. Caps on real money (only matter if you go live; all enforced on the guard computer)

| Cap | Limit | Who can change it |
|---|---|---|
| Per bet | ≥ 0.25 SOL floor, ≤ 1% of the bankroll, ≤ 1% of the pool's SOL | Loosening waits 10 minutes and alerts you. Above 2% needs your second confirmation |
| Open positions | 3, at most 3% of the bankroll in total | Guard host only |
| Daily buying | 10% of the bankroll per rolling 24 h (Q8) | Guard host only |
| Daily loss | 6 × the bet percentage | Guard host only |
| Drawdown stop | 20% of the bankroll | Only you can resume |
| Hot wallet | Daily limit + open positions + fee reserves (≈ 3.3 SOL at 25 SOL). Anything extra is swept to your cold wallet | You top it up; we never move funds |
| Tip per transaction | ≤ 0.003 SOL | Guard host only |
| Exit reserve | 0.01 SOL per open position | Guard host only |
| Canary | 1 SOL including fees (Q6; default no canary) | You fund it |
| Tuition budget | Q5 default: 0, paper only | You |

---

## 10. Flags: what could push spending over the budget

| # | Flag | Size | What we do |
|---|---|---|---|
| **F1** | **The high case sits at the budget line.** Phase 3 high = USD $698 = CAD $991 at 1.42 (99%) | Over at any rate above 1.433, or with a card fee or sales tax (up to CAD $1,168) | The high case needs several deliberate choices (§4b). When one is forced, we offset it with another. The budget guard (C-12) asks you first |
| **F2** | **Sales tax and card fees are unknown** | 0–18% on top of the sticker price | **Question for you:** is the CAD $1,000 before or after tax and card fees, and which province (for GST/HST)? Default: treated as the sticker price; the budget guard reports both |
| **F3** | **Chainstack's add-on may buy only 1 stream** for $49 (sources conflict) | +$100 a month (CAD +$142) if we need the $149 tier | PX-1 checks the live page. A cheaper fix may be to run both filter sets on one stream, if Chainstack allows that [UNVERIFIED] |
| **F4** | **Chainstack throttles the full firehose** | +$126 (Solana Tracker instead) to +$175 (keeping Chainstack for backup reads) a month, billed in euros | D4 / RC6 measure the bandwidth in Phase 0. Switching is a team decision reported to you |
| **F5** | **The bot server is too small** for the recorder plus research | +$38–78 a month (CAD +$54–111) | D4 and A9 measure the load. **Recommendation:** because "no blind spots" ranks above cost and the budget has room, plan G7 around the 16 GB dedicated server if the 8 GB server runs above ~60% load in the test |
| **F6** | **AWS has no hard cap.** A bug (a log loop, runaway writes) could grow the bill | Unbounded until noticed | The Budgets alert (C-11), short log retention, write rates fixed in code, and the AWS line in the daily summary |
| **F7** | **The archive grows every month** with no dollar cap | At 135 GB a month, ~1.6 TB after a year: about +$8–32 a month by month 12 [UNVERIFIED] | Archive size goes in the daily summary. The existing 70%-full rule already drops raw bytes for untracked coins. Monthly review |
| **F8** | **The research ceiling would be reached early.** Cumulative expected spend: ~$230 in month 1, ~$525 by month 2, ~$820 by month 3, ~$960 by week 14 (when 3 months of recorded data exist) | The $750 default would stop us around weeks 11–12, about 2–3 weeks before the month-3 checkpoint | **Question for you (Q3):** raise the ceiling to about **USD $1,000 (CAD ~$1,420)** to line up with the checkpoint, or keep $750 and accept the earlier stop. **Default: $750 stands** until you answer |
| F9 | **A stronger AI model joins.** Fable 5.1 costs 2.5× Opus | AI could reach its $75 cap | Capped by C-1 and C-2. The desk runs fewer nights rather than overspend |
| F10 | **Helius may have changed its prices** (a Sep 2026 refresh is mentioned in search) | Unknown | PX-2 before Gate 0→1 |
| F11 | **The Phase 0 Chainstack month may be wasted** if D4 fails | Up to $98 once | Accepted: it is the price of the test |
| F12 | **The SOL price moves the break-even**, not the bills | Break-even 6.4–9.3% across SOL $150–70 (§7) | Reported in the weekly summary |

---

## 11. Tests to run once allowed (price checks; read-only)

| ID | What to check | Pass, and what we do if it fails | Domain(s) |
|---|---|---|---|
| PX-1 | Chainstack: Growth price, included request units, Solana requests/s, the price over 20M. Yellowstone add-on: streams per tier, and whether one stream can carry several filters | Pass: $49 + $49 with ≥ 2 streams. If not: merge both filter sets into 1 stream, or take the $149 tier (flag F3) | `chainstack.com`, `docs.chainstack.com` |
| PX-2 | Helius: Developer price, credits and requests/s; extra-credit price; autoscale cap setting and what happens at the cap; any Sep 2026 changes (with D10, G8) | Pass: $49 / 10M / $5 per 1M, and a cap that stops spending | `www.helius.dev` (`/pricing`, `/docs/billing/plans`, `/docs/billing/autoscaling`) |
| PX-3 | Solana Tracker: the €200 standalone price, no data caps, whether RPC is included, billing currency | Confirms the F4 figure | `docs.solanatracker.io`, `www.solanatracker.io` |
| PX-4 | AWS in Frankfurt: t4g.small and t4g.micro on-demand prices, gp3 disk per GB, the public IPv4 hourly charge, lease-table writes, alarms, data sent out, AWS Budgets alerts | Pass: total ≤ $48 a month | `aws.amazon.com`, `calculator.aws`, `docs.aws.amazon.com` |
| PX-5 | KMS: key fee, Ed25519 sign price, free-tier exclusion | Pass: ≈ $1 a month at our volume | `aws.amazon.com` (`/kms/pricing/`) |
| PX-6 | Bot server in Frankfurt (= G7): 4 vCPU / 8 GB shared and 4 vCPU / 16 GB dedicated prices; terms allow trading bots; how narrowly provider tokens can be limited | Pick a provider; L4 updated | `www.vultr.com`, `www.digitalocean.com` |
| PX-7 | Block storage (200 GB) and object storage (250 GB–1 TB) prices in Frankfurt | L5 updated | `www.vultr.com`, `www.digitalocean.com` |
| PX-8 | Anthropic: model prices, batch discount, cache-write cost, how the Console spend limit behaves | Pass: matches U15 | `platform.claude.com` |
| PX-9 | X: counts price (recent and full archive); whether counts are billed per request or per result; prepaid with no auto top-up | Pass: the SOC-S1 test stays within $10–20 | `docs.x.com`, `console.x.com` |
| PX-10 | Alert service (= G6): free heartbeat tier, phone push (built in or through a push app), price | Pick one; L9 updated | `healthchecks.io`, `betterstack.com`, `cronitor.io`, `pushover.net`, `ntfy.sh` [hosts UNVERIFIED] |
| PX-11 | Exchange rates and SOL price, **monthly**: Bank of Canada USD/CAD and EUR/CAD, SOL/USD | Update every CAD figure; F1 re-checked | `www.bankofcanada.ca`, `api.coingecko.com` |
| PX-12 | **You:** is the budget before or after sales tax and card fees, and which province | Sets the multiplier in §4c | none (a question for you) |

**Domains not yet on the QUESTIONS_FOR_PAUL.md lists:** `calculator.aws`, `www.bankofcanada.ca`, and the alert-service hosts under PX-10 (the G6 placeholder in List 3).

---

## 12. Sources (searched 2026-11-05 unless marked)
- [VERIFIED-SEARCH] Chainstack Growth and Yellowstone add-on: https://chainstack.com/pricing/ ; https://chainstack.com/learn/compare/best-yellowstone-grpc-providers-solana-2026/ ; https://chainstack.com/yellowstone-grpc-more-streams-same-price/ ; https://coinsaga.com/news/technology/chainstack-solana-rpc-review-2026-free-plan-and-features/ ; https://www.alchemy.com/overviews/solana-rpc
- [VERIFIED-SEARCH] Helius plans and extra credits: https://www.helius.dev/pricing ; https://apis.io/plans/helius/helius-plans-pricing/ ; https://dappatlas.com/projects/helius/
- [VERIFIED-SEARCH] Solana Tracker gRPC: https://docs.solanatracker.io/pricing ; https://www.solanatracker.io/yellowstone-grpc ; https://shyft.to/solana-yellowstone-grpc
- [VERIFIED-SEARCH] AWS t4g.small: https://www.devzero.io/instances/aws/t4g.small ; https://aws-pricing.com/t4g.small.html
- [VERIFIED-SEARCH] AWS KMS: https://aws.amazon.com/kms/pricing/ ; https://cloudburn.io/blog/aws-kms-pricing ; https://wring.co/blog/aws-kms-pricing-guide
- [VERIFIED-SEARCH] Bot server and block storage: https://www.digitalocean.com/pricing/droplets ; https://getdeploying.com/digitalocean-vs-vultr ; https://ployz.dev/blog/vultr-pricing ; https://www.vultr.com/pricing/ ; (11-04) https://spendark.com/compare/g-4vcpu-16gb-vs-voc-g-4c-16gb/
- [VERIFIED-DOC, cached 2026-10-06] and [VERIFIED-SEARCH] Claude prices: https://platform.claude.com/docs/en/about-claude/pricing ; https://costgoat.com/pricing/claude-api ; https://www.aipricing.guru/anthropic-pricing/
- [VERIFIED-SEARCH] X API: https://docs.x.com/x-api/getting-started/pricing ; https://www.outstand.so/blog/x-api-pricing ; https://postproxy.dev/blog/x-api-pricing-2026/
- [VERIFIED-SEARCH] Alert services: https://betterstack.com/community/comparisons/better-stack-vs-healthchecks-io/ ; https://hyperping.com/blog/healthchecks-io-alternatives ; https://makerstack.co/reviews/healthchecksio-review/
- [VERIFIED-SEARCH] Exchange rates: (Round 3, Oct 14) https://30rates.com/ ; https://pluang.com/en/tools/currency-converter/usd-cad ; https://30rates.com/eur-usd-forecast-tomorrow-this-week ; https://www.poundsterlinglive.com/history/EUR-USD-2026
- [VERIFIED-SEARCH] SOL price: (11-04) https://www.mexc.com/news/82737 ; 2026-11-05 search snippet attributed to 24/7 Wall St (Oct 27 2026, $101); no dated November quote found
- Per-trade inputs and all other figures: DESIGN.md §5, `team-debate/round3/rulings.md` R6, and the round 2 files, with their original tags. Each is also listed in `docs/assumption-register.md`.
