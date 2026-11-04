# Shared brief for the design team (every agent reads this first)

Project: design (NOT build) an AI-assisted trading desk for Solana Pump.fun meme coins,
mainly trading them after they migrate (graduate) off the bonding curve. Owner: Paul (not a developer).
The original kickoff is reproduced at the bottom of this file. It is the source of truth.

## Non-negotiable rules for every agent
1. **Design only. No trading code.** Small scripts that only READ public data to check a fact are fine.
   Nothing that signs, sends or simulates a real transaction. No wallets, no private keys, ever.
2. **Paper trading is the default forever** unless Paul personally flips it.
3. **Start from zero.** Ignore any earlier code, bot.py or past projects. This repository
   (github.com/kuzushiiweb3-sketch/AIteam-bot) holds only the design work. Only write inside `team-debate/`
   (the lead architect also writes `DESIGN.md` and `QUESTIONS_FOR_PAUL.md` at the repo root).
4. **Compare every major choice against at least 2 real alternatives** on: speed (latency),
   cost per month, cost per trade, reliability, and how hard it is to build.
5. **Verify, don't remember.** Tag every factual claim:
   - `[VERIFIED-DOC]`: you read the primary source (official docs, GitHub, pricing page) this session. Give the URL.
   - `[VERIFIED-SEARCH]`: you only saw it in search results or a secondary blog. Give the URL.
   - `[UNVERIFIED]`: from memory or inference. Say what test would confirm it.
   Prices and limits change often. Never present a remembered price as fact.
6. **Plain English.** Every file starts with a 3–5 line "In plain English" summary Paul can read.
   Explain any jargon the first time you use it.
7. **Short.** A Round 1 proposal is about 1–2 pages: the options table, a recommendation, open risks.

## Paul's priorities, in order
1. Never lose money to bugs, bad data, slow execution, or security mistakes.
2. Catch every relevant coin fast (no blind spots).
3. Keep running costs (APIs, RPC, AI tokens) as low as possible.
4. Make rule-refining easy: clear logs of why every coin was bought or rejected.
(Later: a subscription product with a striking live visual. Execution comes first.)

## Environment facts (checked 2026-11-04 in this cloud session)
- **Shell network is almost fully blocked.** `curl` to api.mainnet-beta.solana.com, Helius, Jupiter,
  Jito, DEX Screener, Birdeye, PumpPortal, QuickNode, Triton, Shyft, X/Twitter, LunarCrush, Solscan
  and docs.anthropic.com was refused by the environment's proxy. **So no live latency or RPC tests are
  possible from here.** Where a test is needed, write the exact test and the exact domain it needs under
  "Tests to run once allowed". Do not fake results.
- **WebSearch works.** Use it heavily (prefer `mode: "standard"`; use "extended" for pricing/recent changes).
- **WebFetch works for some hosts, not others.** It worked for `raw.githubusercontent.com`
  (e.g. https://raw.githubusercontent.com/pump-fun/pump-public-docs/main/README.md, Pump.fun's
  official public docs repo with program/IDL docs). It failed for `docs.jito.wtf`. If a host fails,
  note it in your file and move on; don't retry the same host.
- Pump.fun's public docs README (fetched today) lists recent changes: "Depth 2 Pump Coin Quotes (Oct 13)",
  "Smaller Trades, Multi-Hop Swaps, Pump Coins as Quote Mints, Fees Kept on the Curve",
  "PumpSwap Update: Negative Virtual Quote Reserves (Sep 30)", "Holder Rewards Coins and the End of Cashback",
  "New Bonding Curve Trade Instructions" (TRADE_V3, PUMP_SWAP_TRADE_V2, MULTI_HOP_SWAP, SYNTHETIC_MIGRATION ...).
  **The programs change often. Any design that decodes them directly must plan for that.**

## Claude model prices (from Anthropic's API reference, cached 2026-10-06) [VERIFIED-DOC]
| Model | Input $/1M tokens | Output $/1M tokens | Cache read $/1M | Notes |
|---|---|---|---|---|
| claude-haiku-5-5 | $0.10 | $0.50 | ~0.1× input | prompts >100K tokens cost $0.50/$2.50; thinking on by default, effort default `medium` |
| claude-sonnet-5-5 | $2.00 | $10.00 | $0.20 | |
| claude-opus-5-5 | $4.00 | $20.00 | $0.20 | thinking always on; effort default `medium` |
| claude-fable-5-1 | $10.00 | $50.00 | $0.25 | thinking always on; Anthropic warns single hard requests "can run many minutes" |
- Batch API: 50% off, results arrive asynchronously (not for real-time decisions).
- Prompt caching: cache writes ~1.25× input price, cache reads ~0.1×; a minimum prefix length applies (512–4096 tokens depending on model).
- Every model can return `stop_reason: "refusal"`, and the bot must handle it as "no decision", never as "buy".

## File layout
- Round 1: `team-debate/round1/<your-role>.md`
- Round 2: red-team writes `team-debate/round2/red-team-attacks.md`; each specialist writes `team-debate/round2/<role>-response.md`
- Round 3: lead-architect writes `team-debate/round3/rulings.md`, then `DESIGN.md` and `QUESTIONS_FOR_PAUL.md` at repo root.

---
## Original kickoff from Paul (verbatim)

# KICKOFF: Design Team for an AI Meme Coin Trading Desk

## Ground rules (read first)
- Start from zero. Ignore any earlier code, bot.py, or past projects in this folder. Assume NOTHING about which tools, APIs or data sources to use.
- Every major choice (data source, execution path, infrastructure) must be compared against at least 2 real alternatives on: speed, cost per month, cost per trade, reliability, and how hard it is to build.
- Verify with current documentation and small tests, not memory. If something can't be verified, say so.
- NO trading code until I approve the design. Paper trading is the default forever unless I flip it.
- I (Paul) don't code. Explain decisions in plain English.

## The goal
Build a bot that trades Solana Pump.fun meme coins (mainly after they migrate) using MY rules, executing them perfectly and without emotion, so my only job is refining the rules. Priorities, in order:
1. Never lose money to bugs, bad data, slow execution, or security mistakes.
2. Catch every relevant coin fast (no blind spots).
3. Keep running costs (APIs, RPC, AI tokens) as low as possible.
4. Make rule-refining easy: clear logs of why every coin was bought or killed.
Later this becomes a subscription product with an insane live visual, but execution comes first.

## Step 2: The debate
- Round 1: each specialist (2–9) writes a short proposal for their area with alternatives compared.
- Round 2: red-team attacks every proposal. Specialists respond and revise. Agents may challenge each other's areas.
- Round 3: lead-architect settles open disagreements and explains why.

## Step 3: Deliver to me, then STOP
- DESIGN.md: final architecture in plain English, a table of every major decision with the alternatives rejected and why, total monthly cost estimate, cost per trade, known risks, and a build plan in phases.
- QUESTIONS_FOR_PAUL.md: everything you need from me: my trading rules, budget, bankroll, risk limits, wallets I track. Ask in plain language.
