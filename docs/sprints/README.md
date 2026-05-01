# ERR0RS Sprint Tracking

Sprint-based development log for [ERR0RS-clean](https://github.com/Gnosisone/Gnosisone/ERR0RS-clean) — building toward a single-command autonomous penetration testing agent.

**Vision:** `err0rs own <target>` → full recon report → autonomous attack → professional engagement report. Authorization gates at every privileged step. 100% local, no cloud.

Each sprint builds **one general-purpose capability** that pays off on real engagements. Juice Shop serves as the validation benchmark — currently 18/111 autonomous, target 111/111.

## Sprint log

| # | Title | What it gives the user | Status | Started | Completed |
|---|---|---|---|---|---|
| **00** | [**Engagement Orchestrator**](./SPRINT_00_ORCHESTRATOR.md) | **`err0rs own <target>` works end-to-end** | 📋 **Next up** | — | — |
| 01 | [JWT Manipulation Engine](./SPRINT_01_JWT_ENGINE.md) | JWT abuse on any target (5 JS challenges) | 📋 Planned | — | — |
| 02 | NoSQL Injection (planned) | NoSQL pen-test capability (4 JS challenges) | 📝 Drafted | — | — |
| 03 | SSTI / Prototype Pollution (planned) | RCE chain capability (8 JS challenges) | 📝 Drafted | — | — |
| 04 | OSINT Enrichment (planned) | Auto OSINT on any target (4 JS challenges) | 📝 Drafted | — | — |
| 05 | Race Conditions (planned) | Race exploit capability (3 JS challenges) | 📝 Drafted | — | — |
| 06 | Stego / Reverse Engineering (planned) | Asset archaeology (4 JS challenges) | 📝 Drafted | — | — |

**Cumulative target:** Sprint 00 ships the agent. Sprints 01-06 give it 28 new capabilities. Remaining 29 unsolved challenges are variants — ~1-3 days each.

**Total calendar:** ~6 months of evening + weekend work to 111/111 autonomous AND a working `err0rs own <target>` against arbitrary authorized targets.

## Why Sprint 00 comes first

The original plan started with the JWT engine. That was a mistake. Without an orchestrator:

- Every capability module reinvents its integration with ERR0RS
- Authorization gates get bolted on instead of built in
- There's no `err0rs own <target>` for the user to actually use
- The agent feels like a toolkit, not a junior pen-tester

Sprint 00 builds the orchestrator first. Subsequent sprints plug into a stable contract. From day one of Sprint 00 completing, the user can run `err0rs own http://target` and get a real engagement — even with only the 18 baseline solvers wired in.

## Status legend

- 📋 Planned — sprint doc exists, not yet started
- 📝 Drafted — placeholder in roadmap, no detailed sprint doc yet
- 🟡 In Progress — feature branch open, work happening
- 🟢 Complete — merged to main, portfolio updated, regression tests passing
- 🔴 Blocked — see sprint doc for blocker

## Process per sprint

1. **Plan** — write the sprint doc (acceptance criteria, week-by-week, risk register)
2. **Branch** — `git checkout -b sprint-NN-<short-name>`
3. **Build** — implement deliverables in week-by-week order
4. **Validate** — pass all acceptance criteria, including regression against Juice Shop
5. **Update** — bump `juice-shop-portfolio` numbers, regenerate `ATTACK_PLAN.md`
6. **Ship** — Hunter S. Thompson commit message, tag release, merge to main
7. **Retro** — append "lessons learned" to sprint doc; update next sprint's plan

## Non-negotiable principles

These don't change between sprints:

1. **Authorization gates are sacred.** Every PR has to leave them intact.
2. **100% local.** No call goes off the device without explicit operator approval.
3. **Every module is general-purpose.** No hardcoded Juice Shop solutions.
4. **Tests first.** TDD on the module contract — API emerges from how tests need to call it.
5. **Reproducible.** Fresh Pi, fresh checkout, run install.sh, `err0rs own http://localhost:3000` works.
