# TODO: master list

Rule: take the first unchecked item in "Now". When it's done, tick it, add anything new you discovered, and commit.
Items marked **[PAUL]** need Paul. Never wait on them: use the safe default noted, keep going, and come back.

## Now: design debate
- [x] Step 1: create the 10-agent team (`.claude/agents/`)
- [x] Shared brief with rules, network limits, verified prices (`team-debate/00_BRIEF.md`)
- [x] Paul's mandate added to the brief and to `CLAUDE.md` (the team owns the strategy, its own edge, speed, autonomy)
- [x] Round 1 proposals: security, risk, quant, execution, AI, social, chain forensics
- [x] Round 1 proposal: data-engineer
- [x] Round 2a: red-team attacks all 8 proposals → `team-debate/round2/red-team-attacks.md`
- [x] Round 2b: each specialist answers the attacks, challenges other areas, and proposes 2–3 edge ideas with a data test
- [x] Round 2c: red-team re-check of the responses, plus attacks on every edge idea
- [x] Round 3: lead-architect rulings → `team-debate/round3/rulings.md`
- [x] Write `DESIGN.md` (architecture, decision table, monthly cost, cost per trade, risks, phased build plan, ranked edge ideas)
- [x] Write `QUESTIONS_FOR_PAUL.md` (only what nobody else can answer, each with a safe default)
- [x] Tell Paul the design is ready. Paul approved it on 2026-11-05

## Next: Phase 0 (DESIGN.md §7). Read-only work only; nothing signs or sends
Work that needs no network and no Paul (do these first, in order):
- [x] `docs/assumption-register.md`: the ~50 numbered facts the design relies on, each with its tag and the test that settles it
- [x] `docs/preregistration.md`: freeze and date the labels, every kill test and pass mark, and the trial families (top-5 ideas, crowding kill, race/no-race rule, stop rule)
- [x] `docs/fee-model.md`: the one shared fee model, from Pump's IDL and docs (raw.githubusercontent.com works)
- [x] `phase0/test-plan.md`: every network test (D-, F-, P-, RC-, T-, G-, S-, Q-, X- numbers) with its exact domain, expected result and fallback
- [ ] `docs/tech-stack.md`: choose the programming language and tools for the recorder, decoders and guard (DESIGN.md left this open), comparing at least 2 alternatives; red-team attacks it
- [ ] `phase0/scripts/`: the read-only Phase 0 test scripts, written in the chosen language and ready to run the moment `HELIUS_API_KEY` and the List 1 domains exist (they only read; they never sign or send)
- [x] `docs/costs.md`: the price table, re-checked by web search where possible; mark anything still needing the live pricing page
Needs network access or accounts:
- [x] Consolidated domain list → QUESTIONS_FOR_PAUL.md "Setup checklist"
- [ ] **[PAUL]** allow the List 1 domains and create a free Helius key (default: keep working offline from docs and IDLs)
- [x] **[PAUL]** Q1 approved, Q2 = CAD $1,000/month (2026-11-05)
- [ ] Check the live vendor pricing pages (PX-1 to PX-12 in docs/costs.md). Critical: is Chainstack's $49 add-on 1 stream or 2?
- [ ] Run the Phase 0 network tests → `phase0/results.md` (blocked until the domains are allowed)
- [ ] T6: fee and price maths match 500 historical trades to the last unit (blocked: needs history access)
- [ ] Gate 0 → 1 review (red-team signs off)

## Later (DESIGN.md §7)
- [ ] Phase 1: recorder, decoders, monitors, fees module, daily reports; 14–21 days of data. **[PAUL]** rent the bot server, upgrade Helius to Developer
- [ ] Phase 2: baselines, lateness curve plus the race/no-race memo (~day 21), BOOST study, gap study, top-5 edge screens, exit tournament, paper simulator, ruin simulation, nightly AI desk with placebo
- [ ] Week-4 stop checkpoint verdict to Paul (DESIGN.md §8)
- [ ] Phase 3: paper bot, guard in paper mode, standby seller, watchdog, dashboard, runbooks, drills. **[PAUL]** separate AWS account plus hardware key, alert app, lever drill
- [ ] Phase 4 (only with Paul's written OK): canary. Phase 5 (only with Paul's OK and ≥25 SOL): live at floor size

## Decisions made without Paul (safest option chosen; Paul can overrule any of them)
- 2026-11-04: Team members run as general agents that load their own role file, because new agent types only appear in a fresh session.
- 2026-11-04: The work moved from the SolanaView repo to this repo at Paul's request. Nothing more will be written to SolanaView.
- 2026-11-04: Paul's mandate asks the team to find its own edge. No 11th "strategy" agent was added; instead, every
  specialist runs an "edge hunt" in Round 2b, red-team attacks it, and the lead ranks it. This keeps the team Paul defined.
- 2026-11-05: Design debate finished (Rounds 1–3). DESIGN.md and QUESTIONS_FOR_PAUL.md delivered; waiting for Paul's OK per the kickoff. Until then, only read-only Phase 0 documents are written (CLAUDE.md rule 2).
