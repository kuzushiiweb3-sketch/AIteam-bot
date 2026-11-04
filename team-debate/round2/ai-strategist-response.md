# AI strategist: Round 2b response

## 0. In plain English (for Paul)
- **AI still never decides a buy, a sell or a bet size.** Plain code does. AI is too slow for that job: Haiku 5.5, the fastest model, takes about 6 seconds just to start answering, which is about 20 blocks. Its output can only *block* a buy or *shrink* it.
- **The red team was right that "AI judges the vibe" was a guess with no test behind it.** It now has to beat a free baseline (simple word and length rules) and pass tests whose pass marks are written down *before* the data comes in. If it fails, we switch it off and keep the money.
- **Where AI can really give us an edge is in three jobs rule-based bots don't do.** (1) It spots which coin is the "original" in a wave of copycats. (2) Each night it works as a research team that proposes new rules, and those rules are tested only on future data. (3) It reads Pump.fun's rule changes the hour they appear and says which of our assumptions just broke.
- **Cost: about $1.60, $2.10 or $4.60 a day** at 200, 1,000 or 5,000 coins a day (about $48–137 a month). The overnight research and rule-change reading alone cost $1.42 a day. Every piece has a kill test. Anything that doesn't earn its cost gets cut.

Tags: [VERIFIED-DOC] = I read the primary page this session. [VERIFIED-SEARCH] = search results only. [UNVERIFIED] = inference, with the test that settles it. [DERIVED] = my arithmetic. Source codes (D1, S1 …) are listed at the bottom. **Host notes:** `platform.claude.com` fetched fine. `arxiv.org` failed to resolve, so I could read the two most relevant papers only through search snippets.

---

## 1. Answers to attacks

| ID | Verdict | What changed, or why |
|---|---|---|
| **AI-1** Shadow test too weak to prove anything | **FIXED** | See 1b. We now test on *every* graduate that passes the hard rules, using an outcome worked out from the recorded data, not only the ~20 paper buys a day. The outcome is a yes/no "did it dump?", not a fat-tailed return. That needs about 225 coins per score band, which is roughly 1–3 weeks of graduates. It must also beat a $0 baseline. |
| **AI-2** `INJECTION_BAIT` blocks the whole "AI agent" meme theme | **FIXED** | Topic words ("AI", "agent", "GPT", "bot") no longer trigger anything. We flag only text shaped like an instruction: role tags (`system:`, `assistant:`, `<|`, `[INST]`), "ignore/disregard previous…", "you are now…", "rate/score this", "respond with", JSON-looking `{"score":`, hidden zero-width or right-to-left characters, and long base64 runs. A flagged coin gets reason code `INJECTION_PATTERN`. The AI is never called on it, and while the AI is a gate that means no buy. Flagged coins are still tracked in shadow, so the rule's cost is known. Each week we hand-check 50 flags. If more than 10% are false alarms, or more than 2% of graduates get flagged, the pattern list goes to review. |
| **AI-3** Coins that finish the curve in one jump have no score | **FIXED (depends on the fork)** | In Branch B (entry after BOOST, section 2), labels are made when the migration is announced (`CompleteEvent`), minutes before entry, so nearly every graduate has one. In Branch A, labels are made at an earlier code trigger. Coins with no label are skipped and their outcomes logged separately. The gate turns on only if unlabelled coins are under 10% of graduates *and* don't do better than labelled ones. |
| **AI-4 / SEAM-9** The reviewers will overfit | **FIXED** | Proposals are written in a small, fixed rule language (no free code), carry a date stamp, and are scored only on data *after* that date. Every proposal adds 1 to the trial counter, adopted or not. At most 3 a night and 20 a month enter shadow. Reviewers never see the locked holdout data. **New: a placebo control.** Each night code also writes the same number of *random* rules in the same language. If the AI's rules don't beat the random ones on future data, the research desk is switched off (edge E2). |
| **AI-5** The score is noisy | **FIXED (procedure)** | The AI now outputs **fixed labels, not a number** (1a), and code turns the labels into a score using weights learned from data. This is social-intel's rule, and I'm adopting it. Repeatability test, run before any gating: 50 coins × 5 calls each. Pass = the same label on at least 4 of 5 calls for at least 85% of coin-label pairs. If it fails: majority of 3 calls (costs 2.45×, see 1c). If that also fails, the noisy label is dropped. |
| **AI-6** The volume assumption is unknown | **FIXED** | Code enforces a hard daily cap of 3,000 label calls. Graduates get first claim on the budget, coins still on the curve get the rest. On top, Paul sets a spend limit in the Anthropic Console (click-by-click steps go in `QUESTIONS_FOR_PAUL.md`). Once the cap is hit, coins get no label and the hard rules carry on. The recorder counts how many coins reach each trigger per day. Worst case for labels: 3,000 × $0.000713 = **$2.14/day** [DERIVED]. |
| **PREMISE-1** We lose the race at graduation | **ACCEPTED (not AI's fight)** | AI adds delay and cannot help win a race. No AI spend is justified by entry speed. See section 2. |
| **PREMISE-2** No named edge | **FIXED (as hypotheses)** | Section 4 names three, each with the information rivals don't have, how fast they could copy it, and a kill test with its pass mark fixed in advance. |
| **PREMISE-3** We get the fills nobody else wanted | **FIXED (for AI's part)** | AI labels could line up with "hot" coins, which are exactly the ones we fail to fill, and that would make the labels look better than they are. So AI lift is reported separately for coins with more than N competing buys in their first 3 blocks, using the quant-tester's competition-based fill model. |
| **PREMISE-4** No baseline to beat | **FIXED** | AI value = the null strategy (buy every coin that passes the hard rules) plus an AI veto, compared with the null alone, after all costs. The veto must improve on both the null and the $0 baseline. |
| **PREMISE-5** Pump changes the market faster than we can prove an edge | **FIXED (partly)** | A market-structure change, or a new model version, restarts validation of the AI labels. Edge E3 is AI's direct answer: it reads each change within the hour, and code has already paused buys. |
| **PREMISE-6** Don't inflate AI to fit the label | **ACCEPTED, and acted on** | Agreed. The live AI job shrinks to labels in shadow mode. The main AI work moves offline: research on the recorded data (E2) and reading rule changes (E3). |
| **PREMISE-7** The desk can't pay its bills | **ACCEPTED RISK, made smaller** | At 1,000 coins a day the AI costs ~$0.10 per paper trade, about 2% of a 0.05 SOL stake at ~$100/SOL [DERIVED; SOL price assumed]. That isn't small. So in paper mode AI counts as **research spend with a kill date**, and the cheapest useful setup (research only, $1.42/day) is the fallback. |
| **SEAM-10** Social data and AI labels may not exist at entry time | **FIXED (AI part)** | In Branch B the AI label is made at `CompleteEvent` and refreshed in the entry window, and we target a label on at least 95% of entries. In Branch A, if fewer than 90% of coins have a label at the gate, the AI is research-only. The social half belongs to social-intel. |

### 1a. The new AI output: labels only
One Haiku 5.5 call per coin at `low` effort, with structured output [VERIFIED-DOC D5, Round 1]. It returns fixed word lists only:
- `theme` (one of ~15 categories)
- `refers_to_real_event` (yes/no/unclear)
- `originality` (original / derivative / copy-of-known)
- `coherent_story` (yes/no)
- `image_matches_name` (yes/no/unclear)
- `injection_suspected` (true/false)
- `reason` (at most 200 characters)

It gives **no score and no buy opinion**. Labels can be checked against a human: we hand-label 200 coins and measure accuracy. That keeps "is the label right?" separate from "does the label predict anything?". A 200×200 thumbnail of the coin's image costs 64 input tokens [VERIFIED-DOC D4], which is about $0.0000064. That is noise in the budget. Images can carry written instructions, so the same rule applies to them: labels only, and labels can never create a buy.

### 1b. Power calculation (AI-1) [DERIVED]
- **Old plan.** It compared returns in high and low score bands of about 140 paper buys each. If each trade's result swings by about 150% (QNT-4), the smallest difference it could detect is (1.28 + 0.84) × 1.5 × √(2/140) ≈ **38 points per trade**. That is useless.
- **New plan.** The outcome is yes/no: "fell 50% or more from the entry price within 60 minutes". The label definition is fixed with quant-tester *before* any data. Assume about half of coins dump [UNVERIFIED]. To spot a 10-point gap (45% vs 55%) with 90% one-sided confidence and 80% power, we need n ≈ (1.28 + 0.84)² × 2 × 0.25 ÷ 0.10² ≈ **225 coins per band**.
- **Where the coins come from.** Every graduate that passes the hard rules gets labels and a counterfactual outcome worked out from the recorded data. At 50–100 such coins a day [UNVERIFIED; mid-2026 graduations were ~120–180 a day, S6], two bands take about **5–9 days**. Beating the $0 baseline within its own score groups needs about 3–4 weeks.
- **Correlation.** Coins from the same day or the same wave move together, so the bootstrap resamples whole days.

### 1c. Cost per day, redone (brief prices; batch prices re-checked [VERIFIED-DOC D3])
Assumptions:
- **Haiku label call**, same as Round 1: 2,500 cached tokens + 1,500 new tokens + 500 output tokens, including low-effort thinking [UNVERIFIED].
  - Cache hit: 2,500×$0.01/M + 1,500×$0.10/M + 500×$0.50/M = **$0.000425**.
- **New: 1-hour cache.** A 1-hour cache write costs 2× the input price [VERIFIED-DOC D2], so $0.20/M for Haiku. That keeps the hit rate high even at 200 coins a day.
  - Each rewrite costs an extra 2,500 × ($0.20 − $0.01)/M = $0.000475.
  - At most ~24 rewrites a day, so **$0.011/day**.
  - Calls sent in parallel miss the cache until the first response starts [VERIFIED-DOC D2], so calls are sent one after another.
- **Calls per coin:** 1.3 (one label call, plus a refresh for about 30% of coins at entry time).
- **Wave labels (E1):** 2,500 cached + 2,000 new input + 300 output = **$0.000375** per call.
  - Calls per day: 100, 300 or 1,000 at the three volumes.
- **Research desk (E2):** Opus 5.5 batch every night, 150K tokens in and 40K out (thinking included), at batch prices of $2/$10 per million [VERIFIED-DOC D3].
  - $0.30 + $0.40 = **$0.70 a night**.
- **Weekly deep review:** Fable 5.1 batch, 300K tokens in and 50K out, at $5/$25 per million [VERIFIED-DOC D3].
  - $1.50 + $1.25 = $2.75 a week, which is **$0.39/day**.
- **Rule-change reader (E3):** Opus 5.5 standard price, 100K in and 30K out.
  - $0.40 + $0.60 = $1.00 per change × ~10 changes a month [UNVERIFIED count] = **$0.33/day**.

| Coins labelled/day | Label calls | Haiku labels | Wave labels | Fixed (E2 + weekly + E3) | **Total $/day** | ~$/month | If majority-of-3 needed |
|---|---|---|---|---|---|---|---|
| 200 | 260 | 260×$0.000425 + $0.011 = $0.12 | $0.04 | $1.42 | **$1.58** | $47 | $1.74 |
| 1,000 | 1,300 | $0.55 + $0.011 = $0.56 | $0.11 | $1.42 | **$2.10** | $63 | $2.90 |
| 5,000 | 6,500 | $2.76 + $0.011 = $2.77 | $0.38 | $1.42 | **$4.57** | $137 | $8.58 |

The majority-of-3 column uses $0.00104 per coin [DERIVED]:
- call 1 caches the coin's text: $0.000025 + $0.000188 + $0.00025 = $0.000463;
- calls 2 and 3 read it from the cache: $0.00029 each.

That is 2.45× the cost of one call.

Until Fable 5.1 joins, the weekly review runs on Opus 5.5 batch instead: (300K × $2 + 50K × $10)/M = $1.10 a week, or $0.16/day. That lowers the fixed part to **$1.19/day**.

**Compared with the alternatives at 1,000 coins/day** (20 paper trades/day):

| Option | Delay added to a buy | $/day | $/month | $/paper trade | Reliability | Build |
|---|---|---|---|---|---|---|
| No AI at all | 0 | $0 | $0 | $0 | Best | Easiest |
| Research only (E2 + E3) | 0 | $1.42 | $43 | $0.07 | Best: nothing live | Easy |
| **Recommended** (labels in shadow, plus E1–E3) | 0 (looks up a stored label) | **$2.10** | **$63** | **$0.105** | An AI outage can't cause a buy | Medium |
| Haiku + Sonnet 5.5 live final call (Round 1, A2) | Haiku ~6 s to start answering [VERIFIED-SEARCH S1] + 3–15 s [UNVERIFIED] | $3.54 | $106 | $0.18 | Two live dependencies | Medium-hard |
| Haiku + Opus 5.5 low effort, live (Round 1, A3) | ~6 s + 5–20 s [UNVERIFIED] | $6.08 | $182 | $0.30 | Two live dependencies | Medium-hard |
| Starting proposal: Haiku + Fable 5.1 live | 5–20 s, minutes at worst | $18.58 | $557 | $0.93 | Poor | Hard |

**Fable 5.1 stays out of anything live.** Its thinking is always on, and Anthropic warns that hard requests "can run many minutes" (brief). It costs 100× Haiku's input price, and in batch it costs $5/$25 per million [VERIFIED-DOC D3]. Its place is the weekly review and, once it joins, the hardest research nights (CLAUDE.md "Note on models").

---

## 2. The big fork: race at graduation or not?

| | **Branch A: race at graduation** | **Branch B: entry after BOOST ends** (minute 5–30, on net-flow/holder events) |
|---|---|---|
| AI in the buy path | Only a stored label is looked up, in milliseconds. A live call (~6 s to start answering at low effort, about 20 blocks [VERIFIED-SEARCH S1; DERIVED]) is impossible | Still only a lookup, but the label can be **refreshed in the background** during the minutes before entry |
| When AI is asked | At an earlier code trigger while the coin is on the curve, so many coins that never graduate are labelled too (AI-6). If about 5× as many coins reach the trigger as graduate [UNVERIFIED; AI-6], 1,000 graduates a day lands near the 5,000 column: **~$4.6/day** | At `CompleteEvent` for graduates that pass the hard rules, plus one refresh: **~$2.1/day** at 1,000 |
| Coverage | Coins that finish in one jump have no label (AI-3) | ~100%. The label is ready minutes early |
| Is AI's question the right one? | Weakly. "Will snipers pile in?" matters little if we lose the race anyway (PREMISE-1) | **Yes.** "Will attention survive once the artificial buying stops?" is a narrative and attention question, which is the only kind AI is good at |
| Social data at decision time | Mostly "unknown" (SEAM-10) | Minutes of posts exist |
| AI's role | Research only (E2, E3) plus the copycat check (E1) | Labels as a veto/shrink input (after the kill tests pass), plus E1–E3 |

**My vote: Branch B**, with fast *exits* kept whatever happens. The fork itself is decided by tests P1/P2 and the null baseline, not by me. The AI design works in both branches: the buy path only ever reads a stored label, and a refusal, timeout or garbage answer means no label, which means no buy. The difference is how much the label can matter: in A almost nothing, in B possibly something.

---

## 3. Challenges to other areas (3)

**C1 → risk-manager: AI's two doors into sizing and exits.**
- **(a) Bigger bets on high conviction.** RSK §1.4 lets conviction grow a bet "with at least 30 trades per band". With each trade swinging ~150%, 30 trades per band can only detect a difference of (1.28 + 0.84) × 1.5 × √(2/30) ≈ **82 points per trade** [DERIVED]. That isn't proof.
  - **Demand:** the AI-derived part of conviction is capped at ×1.0 forever, so it can only shrink a bet. Any growth comes from code features through quant's gate, with a power calculation.
- **(b) "AI may say sell now" (RSK §3).** The AI reads text that attackers write. A fake "rug alert" campaign could shake us out at the bottom. At 0.05 SOL each needless sell costs ~2.5–12.5% in fees (SEAM-1).
  - **Demand:** exits come only from code-computed selling-pressure features. The AI may only tag a position "review" in the log.

**C2 → data-engineer and quant-tester: record every coin's off-chain details from day 1.** No Round 1 file records the coin's metadata: the name, ticker, metadata URI and JSON, description, social links, an image hash plus a small thumbnail, and first-seen time.
- This can't be fetched later without peeking at the future (quant §2.2), so without it **E1 and every AI kill test can never run.**
- **Demand:** store it for every launch, about 30,000 a day (S6). Keep the image hash for all of them, and thumbnails only for coins in a wave of 3 or more or past 25% of the curve.
- Storage could be hundreds of MB a day [UNVERIFIED size], so it goes on the recorder's disk, never the exit guard's (SEAM-8).
- The links come from attackers, so fetch only through one allowlisted gateway with size and time limits. Never follow other links, and never let the AI fetch anything.

**C3 → social-intel: one AI call, honest cost.**
- **Merge.** Social's Haiku theme-tagging call and my label call should be one call, with one schema and one log line, so we don't pay twice.
- **The cost is understated.** Social puts it at "~500 tokens ≈ $0.00005", which counts input only. Haiku 5.5 thinks by default (brief), and output costs 5× input. A realistic call is about **$0.0004, 8× higher**. That is still cheap.
- **Agreed:** "AI outputs labels, code computes the score." I've adopted it (AI-5). The "burst of KOL posts counts against a coin" feature (SOC-5) should be code too.

---

## 4. Edge hunt: where AI can beat rule-based bots

**Honest starting point.** The only rigorous Pump.fun prediction study I found (Marino et al., 2026) models graduation from **who is trading** (on-chain), and the snippets show no text or narrative features [VERIFIED-SEARCH S2]. Narrative research on meme stocks found unstable predictive value (Round 1, S6). An LLM memecoin trading system exists (S3), but I could not read its results because arxiv.org is blocked. **So any AI edge here is a hypothesis.** All three ideas below have the same kill rule: if the test fails, switch it off.

### E1. "Which one is the original?": a coin's position in its copycat wave
**Idea.** When something goes viral, dozens of coins with the same theme launch within hours. The hypothesis is that attention goes mostly to one or two (winner takes most), and the late copies become exit liquidity.

**How it works.**
- **Free part (code):** a local text-embedding model turns each name and description into numbers that capture meaning, and a perceptual image hash spots reused images. Code groups all ~30,000 daily launches into waves.
- **Paid part (Haiku):** labels only the first coin in each new wave, or any coin a code trigger flags. It names what the wave refers to, catches puns and other-language spellings, and judges whether this coin is the original or a copy.
- **At decision time, code adds:**
  - the wave's size in the last 6 hours;
  - this coin's rank in the wave (1st to launch or graduate, or 14th);
  - whether the wave is growing or fading (launches in the last hour vs the 5 before);
  - how earlier graduates from the same wave did.

**What rivals lack.** Bots and retail terminals show *per-coin* on-chain columns (P15 will confirm which). Vendor narrative trackers work at category level, over days or weeks [VERIFIED-SEARCH S4]. I found no sign that GMGN or Axiom tag minute-level waves [VERIFIED-SEARCH, absence only; P15]. Spotting the real one among 14 coins named after the same thing is a fuzzy judgement across many coins, text and images, and it is hard to write as rules. It is also **ready before graduation**, because it comes from the coin's siblings, so it adds zero delay at entry.

**Cost:** $0.04–0.38/day in Haiku. Embeddings and hashes cost $0 in API fees, only CPU on the recorder host [UNVERIFIED speed].

**How a rival copies it.** A good team needs 1–2 weeks. Our moat is thin: it's our recorded wave-to-outcome history and its calibration. Because this mostly tells us **what to avoid** (followers), being copied hurts it less than it would hurt an entry signal.

**Kill test.** Pass marks fixed now. Run it on the first 500 graduates that pass the hard rules, with metadata recorded live (C2).
1. **Pass if** leaders (rank 1–2 in a wave of 3 or more) dump less often than followers (rank 4 or later), by at least **8 points**, with a 90% day-block bootstrap range that excludes 0.
2. **And** adding wave features to the $0 on-chain baseline raises the out-of-sample AUC by at least **0.02** in walk-forward weeks. (AUC is a prediction score: 0.5 = coin flip, 1.0 = perfect.)
3. **And** the result holds in at least 2 of 3 separate weeks.
4. **Is Haiku needed?** Embeddings-only wave features must be beaten by embeddings + Haiku by at least 0.01 AUC. If not, Haiku is dropped from E1.
- One extension, to 1,000 coins, is allowed only if the point estimate passes but the range doesn't.

### E2. An overnight research desk with a placebo
**Idea.** Every night, code builds a data pack from the recorded data:
- per-coin features and outcomes;
- near misses and rejected coins;
- each past hypothesis and its *forward* result.

Names and addresses are hashed, so the model can't "remember" famous coins (quant §2.3).

Opus 5.5, or Fable 5.1 once it joins, then proposes up to 3 rules in a **fixed rule language**. An example: "net SOL inflow in the 60 s after BOOST ends > X AND holder growth in 5 min > Y". Code checks the grammar and rejects any unknown feature. **The AI never writes code that runs.** Rules go into shadow on future data only, and the trial counter applies. Each night code also writes **3 random rules from the same grammar as a placebo.**

**Why we'd win.**
- PREMISE-5: the market changed at least 4 times in 15 weeks. Bots tuned by people adapt slowly.
- We have our own full recorded data, including what we rejected.
- Hypotheses arrive every night and are tested honestly. The edge is **speed of disciplined adaptation, not AI genius.**
- Published LLM factor-mining work reports gains, but mostly on stocks, mostly from authors comparing their own systems, and with warnings about poor generalisation and fast decay [VERIFIED-SEARCH S5]. Hence the placebo.

**Cost:**
- **$0.70 a night with Opus 5.5 in batch.** Batches mostly finish within 1 hour and expire at 24 hours [VERIFIED-DOC D3], which is fine overnight.
- **$1.75 a night with Fable 5.1 in batch:** 150K × $5/M + 40K × $25/M.

**How a rival copies it.** Anyone with recorded data and an LLM can, in weeks. The moat is the discipline (placebo, forward-only testing, trial counter), which most won't bother with. The moat is low to moderate.

**Kill test.** Run until there are 60 AI and 60 placebo rules, each with at least 2 weeks of forward data.
- **Pass if** the share of AI rules that beat both the null baseline and the champion (paired, on the coins where they disagree) is at least **15 points higher** than the placebo share (Fisher exact test, one-sided p < 0.05).
- **Otherwise** the nightly desk stops (saving $21–53 a month) and only the weekly summary stays.

### E3. Rule-change reader: first to understand Pump's new rules
**What triggers it.** Code watches for:
- commits to `pump-fun/pump-public-docs`;
- IDL hash changes and program upgrades;
- changes to the fee and global config accounts (DAT-1);
- Pump's public tech-updates channel.

**What happens.**
- On any trigger, **code pauses buys at once** (DAT-1).
- The AI (Opus 5.5 at standard price, Fable 5.1 when available) reads the change alongside our **assumption register**: about 50 numbered facts the design depends on, such as "A31: BOOST buys 17.6 SOL over 5 minutes".
- It returns JSON: which assumptions are affected, how severe the change is, a plain-English note for Paul, and up to 3 testable "new predictable flow" rules. These go through E2's forward-test pipeline.

**Why we'd win.**
- **Losing less:** in August 2025 a Pump change broke bot selling for hours (protos, via red-team). We would pause in seconds and know within the hour which rules are affected.
- **Getting there first:** BOOST created a predictable buying schedule, and the actors who decoded it first reportedly took ~2–4 SOL per coin [VERIFIED-SEARCH, single source, via red-team RSK-1].
- **Why it needs AI:** code can see *that* something changed. Only reasoning can say *what it means*.

**Cost:** $1.00 per change with Opus, or $2.50 with Fable (100K × $10/M + 30K × $50/M). At ~10 changes a month that is **$0.33–0.83/day**.

**How a rival copies it.** The idea is easy to copy. The assumption register and the fast path from hypothesis to recorded-data test are ours.

**Kill test.**
- **Blind backtest on past changes.** Red-team first writes an answer key: which assumptions each of the 8 documented changes since July 2026 broke (BOOST, the Sep 1 fee accounts, negative virtual reserves, depth-2 quotes, v3/synthetic migration, fees kept on the curve, holder rewards, multi-hop). The model gets only the raw change.
- **Pass if** it finds at least 80% of the answer key's broken assumptions and never calls a high-severity change "safe".
- **Contamination risk.** The models may have seen some of these changes in training [UNVERIFIED cutoffs], so it is also scored live on the next 5 changes.
- **If it fails,** the AI's note becomes advisory only. The pause on any change is code and stays regardless.

### Where AI adds nothing (so we don't pay for it)
- Speed at graduation.
- Hard safety checks and forensics maths.
- Sizing and exits.
- Spotting copycat names by spelling (string matching and hashes do it).
- Social authenticity numbers (account age, duplicate-text ratio).
- KOL tweets as a buy signal (often a *negative*: 80% of promoted coins were down 70% a week later, SOC).
- An absolute "is this meme good?" score: taste is unverifiable, so it survives only as labels with a kill test.

---

## 5. Revised recommendation
1. **No AI in any buy, sell or sizing path.**
   - Live code only reads stored labels, and those can only veto or shrink a buy.
   - A refusal, timeout, cap hit or garbage answer means no label, which means no buy.
   - Fable 5.1 is never used live.
2. **AI outputs labels, not scores.** Code turns the labels and the embedding waves into features.
   - Everything starts in shadow mode, with kill tests fixed in advance against the $0 baseline and the null strategy.
   - The test uses a yes/no "dumped?" outcome on every graduate that passes the hard rules (about 225 per band).
3. **Most AI work moves offline.**
   - E2: a nightly Opus 5.5 batch research desk with a placebo, forward-only testing and the trial counter; Fable 5.1 weekly, and on the hardest nights once it joins.
   - E3: the rule-change reader. Code pauses buys, and the AI explains which assumptions broke.
4. **Prefer Branch B** (entry after BOOST ends). That is where AI labels have time to form and can matter. In Branch A, AI is research only.
5. **Cost:**
   - $1.58 / $2.10 / $4.57 a day at 200 / 1,000 / 5,000 coins ($47–137 a month).
   - The research-only floor is $1.42/day.
   - Hard caps: 3,000 label calls a day, plus a Console spend limit set by Paul. Default suggestion: $75/month. That is a question for Paul, and he decides the value.
   - Each piece is switched off if it fails its kill test.

---

## Tests to run once allowed
| # | Test | Domain(s) |
|---|---|---|
| A1 | Latency of 200 label calls at `low` (streaming): time to first token p50/p95/p99, output tokens, `cache_read_input_tokens` with the 1-hour cache, calls sent one after another | `api.anthropic.com` |
| A2 | Repeatability: 50 coins × 5 calls, label agreement (AI-5) | `api.anthropic.com` |
| A3 | Refusal rate on 500 real metadata samples, including crude names; check whether refused coins form a skewed group | `api.anthropic.com` |
| A4 | Injection set: 50 hostile samples (text and image) must not change the labels compared with clean twins; false-flag rate of the AI-2 patterns on 1,000 real coins | `api.anthropic.com` |
| A5 | Token counts for the real prompts (`/v1/messages/count_tokens`) to replace the 2,500/1,500/500 estimates | `api.anthropic.com` |
| A6 | Read the Pump.fun success paper (2602.14860) and the LLM copy-trading paper (2601.08641): which features predicted success, and was any of it text? | `arxiv.org` (blocked this session) |
| A7 | Do GMGN, Axiom or Sharpe show minute-level waves or narrative tags on fresh coins? (with P15) | `gmgn.ai`, `axiom.trade`, `sharpe.ai` |
| A8 | Metadata fetch: which gateway serves Pump metadata URIs, its latency, and the size per coin (C2) | the URI host seen in `create_v2` events [UNVERIFIED host] |
| A9 | Local embedding speed on the recorder VPS for 30,000 texts a day (E1) | none (offline, after a model download from `huggingface.co`) |
| A10 | Third-party latency charts for Haiku/Opus 5.5 at low effort | `artificialanalysis.ai` |

## Sources
- D1 Pricing (fetched in Round 1, today): https://platform.claude.com/docs/en/about-claude/pricing (the brief's price table is used throughout)
- D2 Prompt caching (fetched today): https://platform.claude.com/docs/en/build-with-claude/prompt-caching. "A cache entry only becomes available after the first response starts". The minimum is 512 tokens for Haiku/Sonnet/Opus 5.5 and Fable 5.1. 1-hour cache writes cost 2× the base input price.
- D3 Batch processing (fetched today): https://platform.claude.com/docs/en/build-with-claude/batch-processing. "Most batches completing within 1 hour", expiry at 24 h. Batch prices: Fable 5.1 $5/$25, Opus 5.5 $2/$10, Sonnet 5.5 $1/$5, Haiku 5.5 $0.05/$0.25 per million. Cache hits in batches are best effort, 30–98%.
- D4 Vision (fetched today): https://platform.claude.com/docs/en/build-with-claude/vision. An image costs ⌈w/28⌉×⌈h/28⌉ tokens, so a 200×200 image is 64 tokens.
- D5 Structured outputs, and the refusal handling from Round 1: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- S1 Haiku 5.5 low effort, ~6.28 s time to first answer token (10K-token workload): https://artificialanalysis.ai/zh/models/claude-haiku-5-5-low/providers and https://artificialanalysis.ai/models/claude-haiku-5-5-low/providers
- S2 Marino, Naviglio, Tarantelli, Lillo, "Predicting the success of new crypto-tokens: the Pump.fun case": https://arxiv.org/abs/2602.14860 (snippets only). 655,770 September 2025 tokens, 0.63% graduated: https://www.diariobitcoin.com/memecoins/estudio-revela-que-senales-anticipan-el-exito-de-los-tokens-lanzados-en-pump-fun/
- S3 Multi-agent LLM memecoin copy trading: https://arxiv.org/html/2601.08641v1 (snippets only)
- S4 Category-level narrative tracking, cycles of ~48 h to 1–3 weeks (vendor claims): https://www.sharpe.ai/learn/memecoin-narrative-tracker
- S5 LLM factor mining, decay and crowding: https://arxiv.org/pdf/2502.16789. Poor generalisation: https://arxiv.org/html/2505.11122v1
- S6 ~30,000 launches/day and a 0.4–0.6% mid-2026 graduation rate: https://madeonsol.com/blog/pump-fun-first-3-minutes-graduation-math. The BOOST spike to 6.7%: https://www.odaily.news/en/newsflash/504995
- Other teams' points cited by ID: `team-debate/round2/red-team-attacks.md`, `team-debate/round1/*.md`.
