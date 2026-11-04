# TODO: master list

Rule: take the first unchecked item in "Now". When it's done, tick it, add anything new you discovered, and commit.
Items marked **[PAUL]** need Paul. Never wait on them: use the safe default noted, keep going, and come back.

## Now: design debate
- [x] Step 1: create the 10-agent team (`.claude/agents/`)
- [x] Shared brief with rules, network limits, verified prices (`team-debate/00_BRIEF.md`)
- [x] Paul's mandate added to the brief and to `CLAUDE.md` (the team owns the strategy, its own edge, speed, autonomy)
- [x] Round 1 proposals: security, risk, quant, execution, AI, social, chain forensics
- [x] Round 1 proposal: data-engineer
- [ ] Round 2a: red-team attacks all 8 proposals → `team-debate/round2/red-team-attacks.md`
- [ ] Round 2b: each specialist answers the attacks, challenges other areas, and proposes 2–3 edge ideas with a data test
- [ ] Round 2c: red-team re-check of the responses, plus attacks on every edge idea
- [ ] Round 3: lead-architect rulings → `team-debate/round3/rulings.md`
- [ ] Write `DESIGN.md` (architecture, decision table, monthly cost, cost per trade, risks, phased build plan, ranked edge ideas)
- [ ] Write `QUESTIONS_FOR_PAUL.md` (only what nobody else can answer, each with a safe default)
- [ ] Tell Paul the design is ready. **[PAUL]** approve `DESIGN.md` (default if no answer: keep building read-only tools only)

## Next: read-only groundwork (allowed once DESIGN.md exists; nothing signs or sends)
- [ ] Collect every "Tests to run once allowed" item from all round files into one checklist with the exact domains
- [ ] **[PAUL]** allow those domains in the cloud environment's network settings (default: keep using fixture data)
- [ ] (to be filled from DESIGN.md's build plan)

## Later
- [ ] (to be filled from DESIGN.md's build plan)

## Decisions made without Paul (safest option chosen; Paul can overrule any of them)
- 2026-11-04: Team members run as general agents that load their own role file, because new agent types only appear in a fresh session.
- 2026-11-04: The work moved from the SolanaView repo to this repo at Paul's request. Nothing more will be written to SolanaView.
- 2026-11-04: Paul's mandate asks the team to find its own edge. No 11th "strategy" agent was added; instead, every
  specialist runs an "edge hunt" in Round 2b, red-team attacks it, and the lead ranks it. This keeps the team Paul defined.
