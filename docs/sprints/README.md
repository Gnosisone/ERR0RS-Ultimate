# ERR0RS Sprint Tracking

Sprint-based development log for [ERR0RS-Ultimate](https://github.com/Gnosisone/ERR0RS-Ultimate) — building toward a single-command autonomous penetration testing agent that teaches while it works.

**Vision:** `err0rs own <target>` → full recon report → autonomous attack → professional engagement report, narrated in real-time by an AI professor that adapts to your experience level. Authorization gates at every privileged step. 100% local, no cloud.

Each sprint builds **one general-purpose capability** that pays off on real engagements. Juice Shop serves as the validation benchmark — currently 27/111 autonomous (projected 35/111 after Sprint 03 portfolio update), target 111/111.

## Sprint log

| # | Title | What it gives the user | Status | Tests |
|---|---|---|---|:---:|
| 00 | [Engagement Orchestrator](./SPRINT_00_ORCHESTRATOR.md) | `err0rs own <target>` works end-to-end | 🟢 Complete | 72 |
| 01 | [JWT Manipulation Engine](./SPRINT_01_JWT_ENGINE.md) | JWT abuse on any target (5 JS challenges) | 🟢 Complete | 39 |
| 01.5 | JWT killchain wiring | JWT engine auto-fires when token detected | 🟢 Complete | 15 |
| 02 | NoSQL Injection Engine | Mongo + GraphQL pen-test capability (4 JS challenges) | 🟢 Complete | 45 |
| 02.5 | NoSQL killchain wiring | NoSQL engine auto-fires when Mongo error detected | 🟢 Complete | 38 |
| 03 | SSTI / Prototype Pollution Engine | RCE chain capability across 10 template engines (8 JS challenges) | 🟢 Complete | 56 |
| 03.5 | SSTI killchain wiring | SSTI engine auto-fires when template engine fingerprinted | 🟢 Complete | 14 |
| **04** | [**Professor Mode**](./SPRINT_04_PROFESSOR.md) | **Real-time AI security coaching during engagements** | 📋 **Next up** | — |
| 05 | OSINT Enrichment (planned) | Auto OSINT on any target (4 JS challenges) | 📝 Drafted | — |
| 06 | Race Conditions (planned) | Race exploit capability (3 JS challenges) | 📝 Drafted | — |
| 07 | Stego / Reverse Engineering (planned) | Asset archaeology (4 JS challenges) | 📝 Drafted | — |

**Cumulative (Sprints 00–03.5):** 279/279 tests pass | 3 native attack engines shipped | `err0rs own <target>` works end-to-end | Juice Shop autonomous: 27/111 → projected 35/111

## Why Sprint 04 is the product-defining sprint

Sprints 00–03 gave ERR0RS *capability*. Native engines, single-command UX, audit logs. That's table stakes for a serious pen-test platform.

What no other platform has — including Metasploit Pro, Cobalt Strike, hackingtool-plugin, Pentest-Tools.com, the entire commercial market — is **a senior pen-tester who lives in your terminal and teaches you while it works.**

Sprint 04 builds that. It's what makes ERR0RS:
- The OSU donation (educational platform, not just a tool)
- The Patreon pitch (something worth paying to support)
- The OSCP study companion (learn the craft, don't just run scripts)
- The differentiator that crushes everything else

Sprints 05+ get easier and cheaper to build BECAUSE Sprint 04 ships first — every new capability automatically inherits a professor that explains it.

## Status legend

- 📋 Planned — sprint doc exists, not yet started
- 📝 Drafted — placeholder in roadmap, no detailed sprint doc yet
- 🟡 In Progress — feature branch open, work happening
- 🟢 Complete — merged to main, portfolio updated, regression tests passing
- 🔴 Blocked — see sprint doc for blocker

## Process per sprint

1. **Plan** — write the sprint doc (acceptance criteria, week-by-week, risk register)
2. **Audit** — read existing code that the sprint touches; refine plan based on what's already built
3. **Branch** — `git checkout -b sprint-NN-<short-name>`
4. **Build** — implement deliverables in week-by-week order
5. **Validate** — pass all acceptance criteria, including regression against Juice Shop
6. **Update** — bump `juice-shop-portfolio` numbers, regenerate `ATTACK_PLAN.md`
7. **Ship** — Hunter S. Thompson commit message, tag release, merge to main
8. **Retro** — append "lessons learned" to sprint doc; update next sprint's plan

## Non-negotiable principles

These don't change between sprints:

1. **Authorization gates are sacred.** Every PR has to leave them intact.
2. **100% local.** No call goes off the device without explicit operator approval.
3. **Every module is general-purpose.** No hardcoded Juice Shop solutions.
4. **Tests first.** TDD on the module contract — API emerges from how tests need to call it.
5. **Reproducible.** Fresh Pi, fresh checkout, run install.sh, `err0rs own http://localhost:3000` works.
