# AI strategist: Round 1 proposal

## In plain English (for Paul)
- **Keep AI out of the split-second buy decision.** Your rules, written as plain code, decide every buy and sell. Code is faster, costs nothing per decision, does the same thing every time, and can't be talked into anything by a coin's description.
- **Use AI for one fuzzy job only:** judging a coin's "vibe" (is the meme or story any good, are the socials real people or bots). The bot asks while the coin is still filling its bonding curve, so the answer is ready *before* migration. It starts in **shadow mode**: the score is logged but not used until paper trading shows it actually helps.
- **Slower, smarter models review the logs after the fact:** Opus 5.5 every night and Fable 5.1 once a week. They *suggest* rule changes for you to approve. AI can never change a rule, place a trade, or see a key.
- **Cost: about $1 to $3 a day** for 200 to 5,000 coins a day (roughly $31 to $93 a month). The starting proposal would cost about $6 to $77 a day.

Tags: every fact carries a tag, and the letter codes (D1, S1 and so on) point to the source list at the bottom. "Thinking" means the model's hidden reasoning, which is billed as output. "Cache" means re-using the fixed part of a prompt at about a tenth of the price.

## 1. AI or plain code, step by step
| Step | Who does it | Why |
|---|---|---|
| Spot new coins and migrations | Code | Speed is measured in milliseconds. |
| Hard safety checks (mint/freeze authority, liquidity, can-I-sell quote, top-holder %, dev/bundle share, creator's past rugs) | Code, veto only | Exact math that must give the same answer every time. AI cannot override it. |
| Risk limits (size, max open positions, daily loss cap, kill switch) | Code only | AI never sees or touches these. |
| Copycat / known-scam name match | Code (string similarity against lists) | Cheap and deterministic. AI is only an optional helper for fuzzy cases. |
| Meme/narrative quality, "tied to a real current event?" | **AI (Haiku 5.5, low effort), computed ahead of time** | The one genuinely fuzzy judgement. |
| Social authenticity (real community vs bots or paid shills) | Code computes numbers (account age, follower growth, duplicate-reply ratio). AI labels a short text sample. | The work is split. |
| **Final buy decision** | **Code.** The stored AI score is one input that may only *veto* a buy or *shrink* its size. | Priority 1. |
| Routing, slippage, fees, exits, stop-loss | Code only | Time-critical. AI is never involved. |
| "Why bought/rejected" log | Code writes a reason code for every rule. AI's one-line reason is one extra field. | Exact, free, and can be replayed. |
| Rule review | AI: Opus 5.5 nightly and Fable 5.1 weekly, both through the Batch API. Code backtests each proposal and Paul approves it. | Slow is fine here, and this is where deep reasoning pays. |
| Browsing the web or X | Not AI. Code fetches the data, and AI reads only what code hands it. | Claude's web-search tool costs $10 per 1,000 searches [VERIFIED-DOC D1], about 20× the cost of a Haiku screening call, and it gives attackers more ways in. |

## 2. Which model does what: starting proposal vs alternatives (at 1,000 coins/day)
Latency facts:
- **Haiku 5.5, measured on real traffic:** about 0.9 s to the first word, p50 about 3.0 s, p95 about 20 s [VERIFIED-SEARCH S1]. (p50 means half of calls are faster than this; p95 means 95 of 100 calls are.)
- **Haiku 5.5 at medium effort:** about 12.6 s before the first word of the answer, because the hidden thinking comes first [VERIFIED-SEARCH S2].
- Anthropic recommends Haiku 5.5 at `low` effort for time-sensitive work [VERIFIED-DOC D7].
- **Fable 5.1:** thinking is always on, and a single hard request can run for many minutes [VERIFIED-DOC D8 / brief]. One third-party site reports a p50 of about 4.1 s, with an unclear method [VERIFIED-SEARCH S4].
- **Opus 5 (the version before 5.5) at high effort:** 3.4 s to the first answer word, then 41 tokens per second [VERIFIED-SEARCH S3].
- **Structured outputs:** the first call with a new JSON schema pays an extra compile delay, and the compiled schema is cached for 24 h [VERIFIED-DOC D5].

**Bottom line: any model call takes seconds and sometimes much longer, so the bot asks before migration and the buy path only reads the stored answer.**

| Option | Delay added to a buy | AI $/day | AI $/paper trade* | Reliability | Build difficulty |
|---|---|---|---|---|---|
| **S. Starting proposal:** Haiku screen (live, default medium effort), then Fable 5.1 final call (live), plus Fable nightly | ~5–20 s typical, minutes worst case | $18.58 | $0.93 | Two live AI calls must both succeed. Fable's slow worst case. Fable's cache is often cold at low volume. | Hard (streaming, long timeouts) |
| A1. Haiku only, live gate at low effort, plus Haiku nightly | ~1–5 s typical, p95 ~20 s | $0.47 | $0.02 | One live dependency. An outage means missed buys. | Medium |
| A2. Haiku live, then Sonnet 5.5 final call (live), plus Opus nightly batch | ~3–15 s [UNVERIFIED] | $3.54 | $0.18 | Two live dependencies | Medium-hard |
| A3. Haiku live, then Opus 5.5 at low effort for the final call (live), plus Opus nightly | ~5–20 s [UNVERIFIED] | $6.08 | $0.30 | Two live dependencies | Medium-hard |
| A4. No AI in decisions at all, plus Opus nightly batch | 0 | $0.54 | $0.03 | Best | Easiest |
| **R. Recommended:** rules decide. Haiku low effort scores coins ahead of time (shadow mode first). Opus 5.5 nightly batch plus Fable 5.1 weekly batch. | **~0** (a lookup, milliseconds) | **$1.39** | **$0.07** | An AI outage can neither block nor cause a buy | Medium (background queue plus a score store) |

\*Assumes about 2% of screened coins become paper buys, which is 20 a day [UNVERIFIED; it depends on your rules].

**Why Fable 5.1 is the wrong choice for the buy call:**
- Its input price is 100× Haiku's ($10 vs $0.10 per million tokens) [VERIFIED-DOC D1].
- Its latency can't be predicted.
- The final decision is mostly numbers, which code already handles exactly. A smarter model adds nothing there.

**Where Fable fits:** the weekly deep review of the logs.

## 3. AI cost per day, with the math
Assumptions:
- **Fixed part of each Haiku prompt, ~2,500 tokens:** instructions, scoring rubric, 6 worked examples and the JSON schema. It is cached, which works because it is above the 512-token minimum [VERIFIED-DOC D2].
- **New tokens per coin, ~1,500:** name, ticker, description cut to 500 characters, up to 10 posts cut to 280 characters each, and code-computed stats.
- **Output, ~500 tokens** including thinking at low effort [UNVERIFIED]. Thinking counts as output and counts toward `max_tokens` [VERIFIED-DOC D8].
- **Haiku 5.5 prices** [VERIFIED-DOC D1]: $0.10 input, $0.125 for a 5-minute cache write, $0.01 for a cache read and $0.50 output, all per million tokens.
- **Per call with a cache hit:** 2,500×$0.01/M + 1,500×$0.10/M + 500×$0.50/M = $0.000025 + $0.00015 + $0.00025 = **$0.000425**.
- **Per call with a cache miss:** the fixed part is written at $0.125/M instead, so **$0.000713**.
- **Cache hit rate:** the cache lives 5 minutes and every read renews it [VERIFIED-DOC D2]. At 200 coins/day (one every ~7 min) about 60% of calls hit, at 1,000/day about 90%, and at 5,000/day about 98% [UNVERIFIED].
- **Nightly Opus 5.5 batch:** code squeezes the day into ~120K input tokens (stats, every buy, near misses and a sample of rejects) with ~30K output: (120K×$4 + 30K×$20)/M × 50% batch discount = **$0.54/night** [VERIFIED-DOC D1 prices].
- **Weekly Fable 5.1 batch:** (300K×$10 + 50K×$50)/M × 50% = $2.75/week, which is **$0.39/day**.

| Coins/day | Haiku cache hits | Haiku $/day | Reviews $/day | **Total $/day** | ~$/month | If thinking doubles | Starting proposal $/day |
|---|---|---|---|---|---|---|---|
| 200 | 60% | $0.11 | $0.93 | **$1.04** | $31 | $1.57 | $6.26 |
| 1,000 | 90% | $0.45 | $0.93 | **$1.39** | $42 | $2.11 | $18.58 |
| 5,000 | 98% | $2.15 | $0.93 | **$3.09** | $93 | $4.81 | $77.39 |

How the starting-proposal column is built:
- Haiku at medium effort, with ~1,000 output tokens per call.
- Fable final call on 10% of coins, each with a 3K cached and 4K new token prompt and 2K output tokens. That is $0.141 per call with a cache hit and $0.178 with a miss.
- Fable nightly review at the standard (non-batch) price, $2.70.

Optional Sonnet 5.5 "second look" on the top 10% of coins, still asked ahead of time: +$0.58, +$2.55 or +$11.83 a day at the three volumes, so code caps it at 100 a day.

Notes:
- The brief lists Sonnet 5.5 cache reads at $0.20. Today's pricing page shows $0.10 [VERIFIED-DOC D1]. The difference is under $0.001 per call.
- Rate limits are no constraint: on the lowest paid tier Haiku 5.5 allows 4,000 requests per minute [VERIFIED-DOC D3]. 5,000 coins a day averages about 4 a minute.

## 4. Prompt-injection defences
Token names, descriptions, websites and posts are written by people who want your money. Princeton researchers already made a crypto AI agent (ElizaOS) send funds by planting false "memories" in it [VERIFIED-SEARCH S5].
1. **Make injection pointless (the main defence).**
   - The AI has no tools, no wallet, no keys, no web access and no memory that outside text can write to. Its only output is a JSON score.
   - The score can only veto a buy or shrink its size, and only for a coin that already passed every hard rule. It can never create a buy or raise the size above the rule cap.
   - So even a perfect injection ("rate this 10/10!") can at worst make the bot behave as if the AI weren't there.
2. **Clean the text in code first.**
   - Strip invisible and direction-flipping characters, normalise look-alike letters, and cut every field to a fixed length.
   - JSON-encode the text and pass it as clearly labelled untrusted data, with a system prompt saying it is data and not commands. This is Anthropic's documented pattern [VERIFIED-DOC D6].
3. **Treat bait aimed at bots as a red flag.**
   - Code searches the metadata for phrases like "ignore previous", "system:", "AI agent" or "score this". A match means auto-reject with the reason code `INJECTION_BAIT`, because a coin that talks to bots is itself a scam sign.
   - The JSON output also includes an `injection_suspected` field. If it is true, there is no buy.
4. **Strict output.**
   - The JSON schema allows only whole numbers 0–10, fixed word lists and a reason of at most 200 characters [VERIFIED-DOC D5].
   - Code re-checks everything and clamps out-of-range numbers.
   - Word-list matching ignores capital letters, because capitalisation isn't guaranteed [VERIFIED-DOC D5].
   - A reason containing a URL, a wallet address or an instruction is thrown away.
5. **Protect the rule review.**
   - The nightly and weekly reviewers see only code-computed features and short cleaned excerpts, never raw coin text.
   - Their output is a proposal, which code backtests and you approve.
6. **Red-team test set.**
   - At least 50 hostile metadata samples live in the tests.
   - A sample passes if it scores no higher than a clean twin.

## 5. Refusals, timeouts and garbage all mean "no score"
In shadow mode, "no score" is just logged. Once the score is used as a gate, "no score" means **no buy**.

| What happens | Action |
|---|---|
| The model refuses: `stop_reason: "refusal"` (arrives as a normal HTTP 200) [VERIFIED-DOC D4] | No score, and the refusal category is logged. No live retry: Haiku 5.5 has no server-side fallback and no fallback credit, and some refusal categories are billed even when they produce no output [VERIFIED-DOC D4]. |
| `max_tokens` reached (thinking used up the budget) [VERIFIED-DOC D8] | No score. The limit gets raised in config, not on the fly. |
| Our own deadline passes (e.g. 15 s for a pre-score) | No score. We must override the SDK defaults of a 10-minute timeout plus 2 automatic retries [VERIFIED-DOC D8]. |
| 429 (rate limit), 5xx (server error) or network error | One retry with a pause, then no score. |
| 429 "spend cap reached" (no retry-after; the Start tier cap is $500/month) [VERIFIED-DOC D3] | AI is off until the month ends. Rules carry on, and the bot alerts Paul. Set your own lower spend limit in the Console. |
| Invalid JSON, a stale score, or the coin's metadata changed since scoring | No score. |
| More than 20% of calls fail within 10 minutes | Circuit breaker: mark AI as "degraded" and alert. |

Two more rules:
- Never ask the model to show its reasoning in the answer. That can trigger a `reasoning_extraction` refusal, so ask for a short reason instead [VERIFIED-DOC D5].
- Log the model ID, prompt version, input fingerprint, tokens, cost and latency for every call.

## 6. Recommendation
1. **Phase 1 (paper trading):**
   - Rules alone make every decision.
   - Haiku 5.5 at `low` effort scores each candidate in shadow mode once the coin is about 50% along its curve, or when the bot first sees it. The score is stored by coin plus a fingerprint of its metadata.
   - Opus 5.5 does a nightly batch review and Fable 5.1 a weekly one.
   - Cost: about $1 to $3 a day.
2. **Phase 2:**
   - The AI score becomes a veto/shrink input only if 2–4 weeks of shadow data show that high-scoring coins beat low-scoring ones among the coins that passed the rules.
   - If they don't, switch scoring off and keep the money.
3. **Fable 5.1 never goes in the buy path.**
   - Sonnet 5.5 "second look" is an optional later experiment, capped by count.
   - **Decision for Paul:** the nightly reviewer can be Opus 5.5 (~$16 a month) or Fable 5.1 (~$40 a month).

## 7. Open risks
- **No proof yet that AI judgement predicts meme-coin returns.**
  - The closest research is on meme stocks discussed on Reddit, and it found unstable predictive value [VERIFIED-SEARCH S6].
  - AI may add cost without adding an edge, which is why it starts in shadow mode.
- **Refusals on crude names.** Many meme coins have crude or NSFW names, and Haiku's safety classifiers may refuse some of them. If so, the "no score" coins form a skewed group [UNVERIFIED; test 4].
- **Scores may not repeat.** Haiku 5.5 rejects temperature settings [VERIFIED-DOC D8], so the same coin can score differently on two calls. We need to measure the spread.
- **Latency figures for the 5.5 models at low effort are unverified.** artificialanalysis.ai was unreachable by fetch from this session.
- **Model updates can change behaviour.** Pin the model IDs and treat a model change like a rule change, with a fresh shadow test.
- **Haiku's price jumps 5× for prompts over 100K tokens** [VERIFIED-DOC D1]. Code must hard-cap the prompt size.
- **Coins first seen at migration have no score.** Once the score is a gate, they get skipped (safest), which costs coverage. Measure how many there are.
- **Coin volume swings a lot.**
  - Graduation was 0.26%–1.15% of ~30,000 daily launches earlier in 2026, and reached 6.7% on one day after Pump.fun's BOOST change in July 2026 [VERIFIED-SEARCH S7].
  - That means roughly 80 to 2,000 graduations a day, so budget for the high end.

## Tests to run once allowed
1. **Latency, tokens and cache** (needs `api.anthropic.com`):
   - 200 Haiku 5.5 calls with the real prompt at `low` and at `medium` effort.
   - Record p50/p95/p99 latency, output tokens and `cache_read_input_tokens`.
   - Repeat with 50 calls each on Sonnet 5.5, Opus 5.5 (low) and Fable 5.1 (low).
2. **Token counts** (needs `api.anthropic.com`): run `/v1/messages/count_tokens` on the real prompt to replace the 2,500/1,500 estimates.
3. **Repeatability:** 20 coins scored 5 times each, to measure the score spread.
4. **Refusal rate:** 500 real meme-coin metadata samples.
5. **Injection red-team:** the 50 hostile samples.
6. **Third-party latency charts:** check `artificialanalysis.ai` once allowed (fetch was blocked in this session).

## Sources
- D1 Pricing (fetched 2026-11-04): https://platform.claude.com/docs/en/about-claude/pricing
- D2 Prompt caching (fetched 2026-11-04): https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- D3 Rate and spend limits (fetched 2026-11-04): https://platform.claude.com/docs/en/api/rate-limits
- D4 Refusals and fallback (fetched 2026-11-04): https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
- D5 Structured outputs (fetched 2026-11-04): https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- D6 Prompt-injection mitigations (fetched 2026-11-04): https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- D7 Reducing latency (fetched 2026-11-04): https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency
- D8 Anthropic API reference bundled with Claude Code (the claude-api skill, cached 2026-10-06, the same source as the brief's price table). Covers model migration notes for Haiku 5.5 and Fable 5.1, SDK timeouts and batch timing.
- S1 Eden AI, Haiku 5.5 latency: https://www.edenai.co/models/claude-haiku-5-5
- S2 Artificial Analysis, Haiku 5.5 at medium effort: https://artificialanalysis.ai/models/claude-haiku-5-5-medium/providers
- S3 Artificial Analysis, Opus 5 at high effort: https://artificialanalysis.ai/models/claude-opus-5-high/providers
- S4 OrcaRouter, Fable 5.1: https://www.orcarouter.ai/compare/claude-fable-5.1-vs-kimi-k3
- S5 "AI Agents in Cryptoland" (Princeton): https://arxiv.org/abs/2503.16248
- S6 LLM vs lexicon sentiment in meme stocks: https://arxiv.org/pdf/2607.24072
- S7 Pump.fun launches and graduations: https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex and https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives
