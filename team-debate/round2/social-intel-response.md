# Round 2b: Social intel response

## 0. In plain English (for Paul)
- The red team is right on the main points. At the moment we'd buy, there are usually few or no tweets about a brand-new coin, and paid hype looks like real hype. So social data becomes a **small, cheap, neutral-by-default input**. We spend nothing on X (Twitter) until a one-off history test costing about $10–20 shows it predicts anything.
- Our best idea in this area costs nothing. Pump.fun's own stream of new coins shows **which themes are heating up**, because dozens of copycat coins with the same name appear within minutes, before any of them graduates. Trading apps show one coin at a time. We'd see the whole wave.
- Thousands of copy bots watch the same influencer (KOL) wallets and pile in within seconds, so we won't follow them. We use those wallets the other way round: to spot an influencer who has quietly loaded a side wallet and is about to sell to his followers. That is a "don't buy" or "get out" signal.
- Social data never decides a trade, never makes a buy wait for a slow website, and never blocks a sell. **Cost: $0 a month to start**, rising to a capped ~$45 a month only if the tests pass.

Tags: [VERIFIED-DOC] primary source read this session; [VERIFIED-SEARCH] seen in search results only; [UNVERIFIED] memory or inference, with the test that settles it; [DERIVED] my arithmetic. Jargon: **pp** = percentage points. **Null baseline** = "buy every graduate with the standard exits", the thing any rule must beat. **Bootstrap CI** = a range for the true result, built by resampling the trades. **AUC** = how well a score ranks winners above losers (0.5 = coin flip, 1.0 = perfect). Host notes: `madeonsol.com` failed to resolve in WebFetch. Round 1 found `docs.x.com`, `docs.socialdata.tools` and `twitterapi.io` refused, so I did not retry them.

---

## 1. Answers to attacks

**SOC-1 + SEAM-10: social can't weigh in at minute 5. FIXED (design), with a hard data gate.**
- Social collection moves onto the **bonding curve**. It starts when a coin crosses the same curve-progress trigger as the AI pre-scoring (50% to start, Paul-tunable). At decision time the bot reads a stored value, which takes milliseconds. It never calls out to the network at that point.
- The window is now "from coin creation to decision time", not a fixed 30 minutes.
- There are four social states. **CONFIRMED** = 3 or more independent clusters (Round 1 §2), including one non-X channel and a bottom-up shape (see SOC-5). **CAMPAIGN** = negative. **THIN** (a few posts) and **UNKNOWN** both score **0**, so a young coin is never punished for being young.
- Coins that complete the curve in one jump (synthetic migration) get UNKNOWN and are reported as their own group, matching AI-3.
- Gate (pre-registered): test P13/S2 measures the share of graduates with 5 or more non-team posts at t = 0, 60, 300 and 900 s. **If that share is under 25% at the adopted entry time, X data is dropped as an entry input** and kept for exits and research only.

**SOC-2: the prepaid cap runs out mid-month; author-history calls are not costed. FIXED.**
- **The cap is daily, not monthly**: the budget divided by 30 per UTC day, with unused budget carried over for at most 2 days. It cannot run dry by the 20th.
- **Author history comes free from our own searches.** Every search returns the authors' numeric IDs. We keep a rolling 24-hour table of author → distinct CAs we have seen them post. An author seen with 5 or more CAs is a "shotgun shiller" at $0. Paid timeline calls are made for at most 5 high-reach unknown authors per coin.
- **When the daily cap is hit**, cuts happen in this order: (1) the random research sample, (2) author timelines, (3) all X calls. The coin's social state is then UNKNOWN (neutral) and the log shows `SOCIAL_BUDGET_EXHAUSTED`. Hitting the cap never blocks a trade and never counts as positive.
- Revised cost, used only if test S1 passes [DERIVED from Round 1 rates and the counts price below; the coin counts are UNVERIFIED]:

| Item | Coins/day | $/coin | $/day |
|---|---|---|---|
| Official X counts, minute buckets, 1 request at decision time | ~40 gate-passers | $0.005 | $0.20 |
| twitterapi.io, 1 page (~20 posts + authors) | 40 | ~$0.007 | $0.28 |
| At most 5 author timelines | 40 | ~$0.015 | $0.60 |
| Deleted-tweet re-checks (top 5 posts at +15 and +60 min) | 40 | <$0.002 | $0.08 |
| Random research sample of other graduates | 20 | ~$0.012 | $0.24 |
| **Total** | | | **≈$1.40/day → hard cap $1.50/day (≈$45/mo)** |

Where "~40 gate-passers" comes from: about 30,000 launches/day and a mid-2026 graduation rate of 0.26–0.6% [VERIFIED-SEARCH theblock via kucoin/binance square; madeonsol blog estimate] give roughly 80–180 graduates/day [DERIVED]. I assume about a quarter of them pass the on-chain gates [UNVERIFIED; the recorder counts this].

**SOC-3: X is shutting down third-party readers. FIXED by design; the remaining risk is ACCEPTED.**
- The v1 core (the wave detector and the KOL wallet watch) uses **no X data at all**. X is a bolt-on.
- Three X routes, on different legal footing:
  1. Official X counts plus small reads. This is legitimate, billed per request.
  2. twitterapi.io.
  3. SocialData: $0.0002 per item, empty responses not billed by default, HTTP 402 when the balance is empty [VERIFIED-SEARCH docs.socialdata.tools/getting-started/pricing].
- xAI's `x_search` is a fourth legitimate route. Since 21 Sep 2026 it reportedly bills $5 per 1k posts and $10 per 1k profiles, plus model tokens [VERIFIED-SEARCH usagepricing.com tracker, single source; docs.x.ai snippet]. That is no cheaper than official X, so it is reserved for the future subscriber product.
- I found no 2026 reports of action against twitterapi.io [VERIFIED-SEARCH; absence of results is weak evidence]. The Nitter and XCancel cease-and-desist letters show the risk is real. **Accepted**, because missing data is treated as neutral.

**SOC-4: KOL wallets are crowded copy trades. ACCEPTED as true; FIXED in how we use them.**
- New evidence, from a vendor that sells KOL data, so treat it with care. In Aug 2026, across 533 wallets, the **median gap between the first and second KOL buy on a token was 9 seconds**, and about 80% of tokens got a second KOL within 60 s. The 457 scored KOL wallets had an average 30-day win rate of 42% [VERIFIED-SEARCH madeonsol.com; methodology not checked]. We would arrive seconds late behind a crowd that loses more often than it wins.
- **So "KOL bought" is not a positive entry feature in v1.** It is logged and tested three ways at our *measured* delay (2, 10 and 60 s): follow it, fade it (contrarian), and ignore it. Pass rule: following must beat the null by 5 pp or more per trade after costs. Otherwise its weight stays at 0.
- Pump.fun owns Kolscan [VERIFIED-SEARCH dlnews], so the public labels belong to the venue and everyone has them. We build our own behaviour-based labels (edge 2). Public lists are only a starting point.

**SOC-5: the confirm logic rewards paid campaigns. FIXED, and stricter than the demand.**
- If 3 or more accounts with more than 10k followers (a placeholder) post the CA within 10 minutes, the burst counts as **one CAMPAIGN cluster with negative weight, even if their wallets bought**. "Buy first, then tweet" *is* the pump-and-dump pattern, and vendor data says KOL wallets often buy minutes to hours before their call [VERIFIED-SEARCH madeonsol]. A wallet buy only removes the extra "says but doesn't buy" penalty.
- CONFIRMED also requires a **bottom-up shape**: the first non-team mentions come from small accounts, and reach grows over time (edge 3). Top-down (big accounts first, then swarms of replies) means CAMPAIGN.

**SOC-6: Helius webhooks give up after 3 failed tries. FIXED.**
- KOL trades on Pump and PumpSwap are **already in the primary firehose**, which carries every transaction that touches either program (DAT §3). We match the signer against the watchlist inside our own decoder. That costs $0, with no webhook and no Helius credits.
- This also removes social's ~150k credits from **SEAM-7**.
- What the firehose misses is plain SOL and token transfers from KOL wallets (SEAM-6). Edge 2 needs those, so I ask for one extra stream filter (challenge 1).

**PREMISE-2 (no edge): answered in section 4.** I agree that mention counts and KOL wallet buys are public columns in every trading app, not an edge.

**PREMISE-3 (adverse selection): ACCEPTED, and it hits social hardest.** If social works, it selects the hot coins, which are exactly where our buys fail. The fix is challenge 3.

**PREMISE-4 (no baseline): FIXED.** Every social feature is tested as "null + feature" against the null, never on its own.

**PREMISE-6 (vibe score versus a $0 baseline): AGREED.** Edge 1's wave detector is the $0 narrative baseline (challenge 2).

**PREMISE-7 (the desk can't pay its bills): FIXED for social.**
- Round 1's $50–65/month becomes **$0/month recurring** until test S1 (a one-off ≈$10–20) passes. After that, a hard cap of $1.50/day.
- One point of disagreement: X history can't be rebuilt honestly later, because deleted promo tweets and suspended bot accounts disappear from it. So if S1 passes, the live sample starts at once rather than after the paper period.

**SEAM-9 (the trial counter): FIXED.**
- Social weights are frozen during paper trading.
- Only the pre-registered features in section 4 are tested, and each counts as one trial. Any new social feature adds a trial.
- Following the two-timestamp rule (QNT §2), every post is logged with its creation time, decoded from the post ID, and the time *we* fetched it. Backtests use the fetch time.

---

## 2. The big fork: race at graduation or not?

Social can never compete in a 1–2 second race. Every social call takes seconds: the twitterapi.io stream averages about 1.2 s and is "occasionally 10+ s", and search is slower [VERIFIED-SEARCH, Round 1 mirror]. So the timing is fixed by design:

| Input | On the bonding curve | At graduation (0–2 s) | Minutes 1–15 after | Exits |
|---|---|---|---|---|
| Narrative wave (edge 1) | Computed continuously from launches | Lookup only | Lookup and refresh | Wave exhausted → tighten stops |
| KOL wallets and bait flag (edge 2) | Live from the firehose | Lookup only | Swarm and side-wallet sells | Side-wallet sell → exit input |
| X counts, sample and shape (edge 3) | 1 call at the curve trigger | Lookup only | 1 call at decision time | Deleted promo tweet → red flag |
| Pump.fun's own page data (reply count, livestream on/off) | Research only. Unofficial API, 60 requests/min per IP [VERIFIED-SEARCH apify.com listing]. ToS not yet read | — | — | — |

**My position:** for entries, social favours **option C (event-based entry after BOOST ends, roughly minutes 5–15)**. That is when independent posts exist, campaigns have shown themselves and promo tweets get deleted. If test P1 shows the graduation race is affordable, social's only role there is a **pre-approval made on the curve** (the wave is hot, no bait flag). At graduation that is a lookup with zero added delay. Social never makes a buy wait for data, and never sits on the sell path.

The curve is where social has its natural head start, because the wave forms there. Buying on the curve is outside Paul's main brief, so "will it graduate?" predictions are logged as research only.

---

## 3. Challenges to other areas

1. **Data-engineer: the narrative inputs and side-wallet funding.**
   - (a) Confirm the recorder keeps every Pump `create` event with its name, symbol, URI and creator. That is about 30,000 a day [VERIFIED-SEARCH], and it is the wave detector's whole input.
   - (b) Say who fetches each coin's metadata file (description, X and Telegram links, image), from which host, and at what rate. I propose once per coin, when it reaches 20% of the curve.
   - (c) Add one stream filter for outgoing SOL and token transfers from the 100–250 watched wallets (SEAM-6), costed against Chainstack's per-stream account limit.
   - Pass test: a replay captures at least 99% of create events against an RPC sample.
2. **AI-strategist: Haiku can't know "a real current event" (AI §1).**
   - It has a training cutoff, so code must hand it today's trend list. That list must come from data: edge 1's clusters, or X trends at $0.010 per request [VERIFIED-SEARCH, third-party pricing blogs].
   - Don't label all 30,000 launches a day with Haiku: at $0.000425 per call (AI §3) that is about $12.75/day [DERIVED]. Label one representative per new cluster instead: an estimated 500–2,000 a day, so $0.21–0.85/day [DERIVED; cluster count UNVERIFIED].
   - The vibe score must beat the wave detector, not just $0 name features.
3. **Quant-tester: measure social causally.**
   - (a) Randomly assign, coin by coin, which gate-passers get the paid X lookup (50/50). Then we learn whether the *spend* changes outcomes, not just a correlation.
   - (b) Score social-boosted coins under PREMISE-3's "counted as missed when more than N competing buys" rule.
   - (c) Record S1's survivorship bias: deleted and suspended content is gone, so backfilled history looks cleaner than the live feed. The live sample measures that gap.

---

## 4. Edge hunt

**Edge 1: the narrative wave detector (strongest; $0).**
- **What others lack:** how fast a theme is spreading across *all* launches, seen before graduation. Deployers are a revealing crowd. Each launch costs them money, and they launch where they think buyers are. A theme that suddenly spawns dozens of copies is forming now.
- **How it works:**
  - Normalise every launch's name and ticker (lower case, strip emoji and digits, compare spellings) and cluster them in rolling 60-minute windows.
  - Once a coin passes 20% of the curve, add its image fingerprint and the tweet its metadata links to.
  - Features at decision time:
    - **heat**: launches in the cluster in the last 60 minutes, counted by *distinct funding sources*, not by raw count;
    - the cluster's **recent graduates** and how they did;
    - **position**: first, best-funded or a late copy;
    - **saturation**: copies arriving faster while getting worse.
- **Why we'd win:** trading apps and most bots score one coin at a time [UNVERIFIED: P15]. We see the wave before its coins graduate, and we can tell the leading coin from late copies.
- **Faking it:** an operator can spam copies to fake a wave. Counting distinct funders blunts this. Bubblemaps traced one set of same-name tokens to a single deployer [VERIFIED-SEARCH digitalmoneybox/Bubblemaps].
- **Cost:** $0 on the existing firehose. Optional Haiku cluster labels cost ≈$0.2–0.85/day.
- **How a rival copies it:** easily, in 2–4 weeks, if they think of it. The moat is our tuned thresholds and labelled tape, not the idea. Similar "same-name" views may already exist [UNVERIFIED].
- **Kill test S3** (pre-registered; at least 14 days of tape and 1,000 graduates; entry at the adopted time):
  - PASS if the top third by heat beats the bottom third by **8 pp or more** in median +30-minute return after all costs, *and* the top third beats the null with a bootstrap CI above 0 after dropping the best 5% of trades, *and* the sign holds in both halves of the period.
  - KILL if the gap is under 4 pp or the sign flips.
  - Side test: for coins at 30% of the curve, an AUC of 0.60 or more for "graduates within 2 h" makes heat useful for pre-arming even if the return test fails.

**Edge 2: the KOL bait detector (losing less).**
- **The pattern:**
  1. A KOL funds a fresh wallet (1–2 hops away), and that wallet buys early.
  2. The public wallet buys a small amount later.
  3. The KOL posts the coin.
  4. The side wallet sells into the swarm of followers.
- Copy bots see step 2 and pile in within seconds. We watch step 1.
- **Uses:**
  - (a) **Entry veto**: an early holder was funded by a watched wallet in the last 14 days, not via an exchange.
  - (b) **Exit input**: a side wallet sells, or moves tokens to fresh wallets, while we hold.
  - (c) **Our own labels**: "swarm leaders" are wallets whose buys draw 3 or more watched wallets within 60 s. A leader whose median hold time is under 5 minutes is a dumper, so his buy means selling is minutes away.
- **Why we'd win:** copy bots are built to follow, so they *are* the exit liquidity. Avoiding coins built to dump on followers is real money at our size.
- **Cost:** $0 if the transfer filter fits in the current stream plan. Otherwise a second Chainstack stream add-on of ≈$49/mo [VERIFIED-SEARCH, DAT S7], in Phase 2 only. Seeing funding live avoids paid look-ups of who funded each wallet.
- **How a rival copies it:** funding analysis exists (Arkham, Bubblemaps) [VERIFIED-SEARCH beincrypto, Round 1]. KOLs can adapt by funding side wallets through exchanges, which breaks the link. Expect this edge to fade over months.
- **Kill test S5** (60 days of tape, 100–300 wallets):
  - PASS if all three hold: (i) at least 100 "pre-loaded" events; (ii) a follower entry 10 s after the public buy does **10 pp or more worse** at +30 min on pre-loaded coins than on clean ones, with a CI that excludes 0; (iii) as an exit rule it improves affected held trades by 3 pp or more over the default exits.
  - KILL if there are fewer than 50 events in 60 days (too rare to matter) or the gap is under 5 pp.

**Edge 3: the shape of organic spread on X (weakest; cheap to kill).**
- **The idea:** real interest spreads bottom-up. Small accounts come first and posts arrive irregularly over tens of minutes. Paid campaigns are top-down and spiky. Most bots count mentions (more = better). We treat a spike as a warning.
- **What we measure:** X's counts endpoint returns minute-by-minute post counts for a query in **one request**. Recent counts cover 7 days, and full-archive counts are open to pay-per-use accounts [VERIFIED-SEARCH docs.x.com/x-api/posts/counts/introduction]. The price is ≈$0.005 recent and $0.010 full-archive per request [VERIFIED-SEARCH, third-party pricing blogs; X's page not reached]. X notes that counts may differ slightly from search results [VERIFIED-SEARCH same page]. One sample page of authors adds follower size in time order.
- **Features:**
  - **burstiness**: how spiky the per-minute counts are (variance ÷ mean);
  - the **follower size of the first non-team poster**;
  - the **growth slope** of posts over time.
- **Cost:** S1 is one-off: 1,000–2,000 past graduates × 1 full-archive counts request ≈ **$10–20** [DERIVED]. Live, ~$0.012 per coin, inside the $1.50/day cap.
- **How a rival copies it:** easily. It is also fragile to X policy, and the most exposed to SEAM-10.
- **Kill test S1** (run first, because it is cheap; needs S2 to pass):
  - PASS if two things hold. (i) At least 25% of graduates have 5 or more posts by entry time. (ii) Among those, the low-burstiness half beats the high-burstiness half by **8 pp or more** in median +60-minute return after costs, with a CI that excludes 0.
  - KILL means no paid X spend at all, and social becomes on-chain only.
  - The backfill is cleaner than live data (fakes get deleted), so this test is generous: if it fails here, it fails live.

---

## 5. Revised recommendation
1. **Social is a capped, neutral-by-default input.** CONFIRMED adds a small boost (20% of the score at most), CAMPAIGN subtracts, THIN and UNKNOWN count 0. It never triggers a buy, never waits on a network call, and never touches sells.
2. **v1 costs $0/month.** The wave detector and the KOL wallet watch run on the existing firehose. A KOL buy is not a positive entry feature unless S4 proves it at our real delay.
3. **One cheap gate comes before any X spend: S1 (≈$10–20 one-off).** If it passes: the X sample runs under a hard cap of $1.50/day with a daily budget, three providers and coin-level randomisation. If it fails: no X data at all.
4. **KOL wallets are used defensively.** The bait detector acts as a veto and an exit input, and we build our own behaviour-based labels. Public lists are only seeds.
5. **Timing:** collect on the curve and look up at graduation. Social favours event-based entry after BOOST. If the team races at graduation, social supplies only a pre-approval. Still rejected or deferred: LunarCrush, Kaito, Telegram user accounts, Discord self-bots, and KOL post streams ($79–149/mo).

## Tests to run once allowed (exact domains)
| # | Test | Domain(s) |
|---|---|---|
| S1 | Backfill minute-level counts for 1,000+ past graduates; confirm the billed price per request in the console | `api.x.com` (`/2/tweets/counts/all`), `console.x.com`, `docs.x.com` |
| S2 | Does search or counts match a raw CA string and `pump.fun/coin/<CA>` links? Check 20 known CAs against a manual count | `api.x.com`, `api.twitterapi.io`, `api.socialdata.tools` |
| P13 | Non-team posts at t = 0, 60, 300 and 900 s for 200 graduates | Same as S2 |
| S3 | Wave detector on recorder tape; metadata fetch rate | Offline, plus the metadata host [UNVERIFIED; data-engineer to name it] |
| S4 | KOL follow / fade / ignore at 2, 10 and 60 s delays against the null | Recorder, plus `kolscan.io`, `gmgn.ai` for seed labels |
| S5 | Bait detector: side-wallet funding and sells | gRPC host (e.g. Chainstack), RPC host |
| S6 | Pump.fun page fields (reply count, livestream on/off): read the ToS first, research only | `pump.fun` (terms), `frontend-api-v3.pump.fun` |
| S7 | xAI `x_search` current price | `docs.x.ai` |
| S8 | Read the KOL report methodology (WebFetch failed: host not resolved) | `madeonsol.com` |

## Sources
- [VERIFIED-SEARCH] X counts endpoint (7-day, minute granularity, full archive for pay-per-use, may differ from search): https://docs.x.com/x-api/posts/counts/introduction
- [VERIFIED-SEARCH] X pay-per-use prices incl. counts $0.005/$0.010, trends $0.010, 24 h dedup (third-party): https://www.outstand.so/blog/x-api-pricing ; https://opentweet.io/x-api-pricing ; https://postproxy.dev/blog/x-api-pricing-2026/ ; https://www.xpoz.ai/blog/guides/understanding-twitter-api-pricing-tiers-and-alternatives/
- [VERIFIED-SEARCH] xAI x_search pricing: https://www.usagepricing.com/blueprint/activity/xai-2026-09-21-x-search-per-result-billing ; https://docs.x.ai/developers/pricing.md
- [VERIFIED-SEARCH] SocialData pricing: https://docs.socialdata.tools/getting-started/pricing
- [VERIFIED-SEARCH] Launch and graduation rates: https://madeonsol.com/blog/pump-fun-first-3-minutes-graduation-math ; https://www.kucoin.com/news/flash/pump-fun-meme-coin-graduation-rate-hits-2-01-highest-since-july-2025 ; https://www.binance.com/ar/square/post/350129618837073
- [VERIFIED-SEARCH, vendor] KOL timing and win rates: https://madeonsol.com/blog/solana-kol-trading-report-august-2026 ; https://madeonsol.com/blog/how-to-find-pumpfun-tokens-before-kols-tweet ; https://madeonsol.com/blog/scout-signal-first-kol-touch-backtest-solana
- [VERIFIED-SEARCH] Pump.fun bought Kolscan: https://www.dlnews.com/articles/defi/memecoin-kols-bag-millions-as-pump-fun-buys-kolscan-tracker/
- [VERIFIED-SEARCH] Pump.fun front-end fields and rate limit (third-party scraper): https://apify.com/neverempty/pump-fun-new-tokens-monitor
- [VERIFIED-SEARCH] Same-name tokens from one deployer: https://digitalmoneybox.com/news/cryptocurrency/fake-eric-trump-themed-token-is-rug-in-the-making-says-bubblemaps
- [VERIFIED-SEARCH] Coordinated-account dataset: https://arxiv.org/html/2602.13480
- [VERIFIED-SEARCH] Nitter cease-and-desist (Aug 2026): https://zeli.app/story/49437283 ; red-team's techcrunch link
- Round 1 references (SOC §n, DAT §n, AI §n, QNT §n) point to `team-debate/round1/<role>.md`.
