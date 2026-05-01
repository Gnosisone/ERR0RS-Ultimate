# Sprint 00 — Engagement Orchestrator

> **The first sprint.** This is what makes ERR0RS feel like an agent, not a toolkit.

**Goal:** Implement `err0rs own <target>` — a single command that takes a target URL, performs full autonomous reconnaissance, enumerates attack surface, runs every applicable capability module, and produces a professional engagement report. With authorization gates at every privileged step.

**Sprint length:** 3 weeks (~22 hours of focused work)
**Owner:** Eros (Gnosisone) + Claude
**Validation target:** Local Juice Shop instance, then DVWA, then a deliberately-vulnerable Flask sandbox we ship in `tests/orchestrator_sandbox/`

---

## Why this sprint comes before JWT

Originally I sequenced the JWT engine as Sprint 01. That was a mistake.

Without the orchestrator, the JWT engine is a Python class with no home. Every subsequent capability module would have to invent its own integration path with the rest of ERR0RS, leading to inconsistent APIs and brittle glue code.

With the orchestrator built first:
- Every module plugs into a stable, tested contract
- `err0rs own <target>` is a real command from day one
- Authorization gates exist before they're needed
- The user-facing UX you actually want is there
- New workstreams *enhance* the agent, they don't *bootstrap* it

---

## The user experience target

```bash
$ err0rs own http://localhost:3000

╔════════════════════════════════════════════════════════════════╗
║  ERR0RS — Autonomous Engagement                                ║
║  Target: http://localhost:3000                                 ║
╚════════════════════════════════════════════════════════════════╝

[!] AUTHORIZATION REQUIRED
    You are about to launch an autonomous penetration test against:
        http://localhost:3000

    Confirm you own this target or have written authorization (yes/no): yes

[✓] Authorization confirmed. Engagement #2026-05-01-001 starting.
[✓] Live narration: http://127.0.0.1:8765/engagements/2026-05-01-001
[✓] Report destination: /home/kali/reports/2026-05-01-001/

──── Phase 1: Reconnaissance ─────────────────────────────────────
  [✓] DNS resolution + WHOIS                                  (1.2s)
  [✓] Port scan (top 1000 + service detection)                (8.4s)
  [✓] HTTP headers + technology fingerprint                   (0.6s)
  [✓] Robots.txt, sitemap.xml, .well-known                    (0.4s)
  [✓] TLS configuration analysis                              (1.1s)
  [→] Recon complete. 12 services identified, 1 web app.
                                                              [11.7s]
──── Phase 2: Enumeration ────────────────────────────────────────
  [✓] Crawl + endpoint discovery (847 unique paths)           (2m 4s)
  [✓] API surface mapping (REST + GraphQL probes)             (32s)
  [✓] Authentication mechanism detection                      (4s)
  [✓] Form + parameter inventory                              (18s)
  [→] Enumeration complete. 47 forms, 23 API endpoints, JWT auth detected.
                                                              [3m 0s]
──── Phase 3: Vulnerability Analysis ────────────────────────────
  [✓] Dispatching: SQL injection module                       (testing 23 params)
  [✓] Dispatching: JWT manipulation module                    (token captured)
  [✓] Dispatching: XSS module                                 (testing 47 forms)
  [✓] Dispatching: IDOR module                                (testing 18 endpoints)
  [✓] Dispatching: Path traversal module                      (testing 11 file params)
  [→] Analysis complete. 14 confirmed vulnerabilities.
                                                              [6m 22s]
──── Phase 4: Exploitation ──────────────────────────────────────
  [✓] SQLi → admin login bypass                              (Login Admin)
  [✓] SQLi → users table dumped                              (User Credentials)
  [✓] JWT secret cracked: 'mySecret'                         (JWT Forgery)
  [✓] JWT forged with admin claim → /admin accessed          (Admin Section)
  [✓] Path traversal → /etc/passwd retrieved                 (XXE Data Access)
  ...
  [→] Exploitation complete. 14/14 vulnerabilities confirmed.
                                                              [4m 18s]
──── Phase 5: Reporting ─────────────────────────────────────────
  [✓] Markdown report generated
  [✓] HTML report with screenshots
  [✓] PDF executive summary
  [→] Report ready: /home/kali/reports/2026-05-01-001/
                                                              [12s]

╔════════════════════════════════════════════════════════════════╗
║  Engagement complete.                                          ║
║  Total runtime: 13m 53s                                        ║
║  Critical: 3  •  High: 7  •  Medium: 4  •  Info: 0             ║
║                                                                ║
║  Top finding: JWT secret 'mySecret' allows full session        ║
║  forgery and complete authentication bypass.                   ║
║                                                                ║
║  Full report: /home/kali/reports/2026-05-01-001/REPORT.html    ║
╚════════════════════════════════════════════════════════════════╝
```

That's the experience. Everything we build serves it.

---

## Sprint deliverables

### 1. The `err0rs` command — `bin/err0rs`

Single executable entry point installed to `/usr/local/bin/err0rs` during install. Subcommands:

```
err0rs own <target>              # The big one — full autonomous engagement
err0rs recon <target>            # Recon phase only, no exploitation
err0rs report <engagement_id>    # Re-render a report
err0rs status                    # What engagements are running, what completed
err0rs lab start                 # Spin up local Juice Shop for testing
err0rs --version
err0rs --help
```

### 2. Engagement state machine — `src/orchestrator/engagement.py`

The phase-based engine that runs an engagement from authorization through reporting. States:

```
AUTHORIZED → RECON → ENUMERATION → VULN_ANALYSIS → EXPLOITATION → REPORTING → COMPLETE
                                                       ↓
                                                    [optional: POST_EXPLOIT]
                                                       ↓
                                                   PERSISTENCE → CLEANUP
```

Each phase has:
- A defined input contract (what the previous phase must hand over)
- A defined output contract (what the next phase consumes)
- A timeout (no phase runs forever)
- A failure mode (continue with partial data vs. abort)
- Logging hooks (every action gets recorded to engagement JSONL)

### 3. Authorization gate — `src/orchestrator/authorization.py`

Single-purpose module that:
- Confirms target is on an allowed-list (RFC1918 + localhost by default)
- For external targets, requires explicit `--i-have-authorization` flag AND interactive `yes` typed in full
- Logs the authorization confirmation with a timestamp + user identity
- Refuses to proceed against `*.gov`, `*.mil`, `*.edu` without an additional override flag
- Refuses to proceed against any IP in a curated bug-bounty out-of-scope list

This is non-negotiable code. Every PR has to leave this gate intact.

### 4. Module registry — `src/orchestrator/registry.py`

The plugin system that capability modules register into. Built on top of the existing `BasePlugin` architecture but with stricter contracts:

```python
@register_module(
    name="jwt_breaker",
    phases=["VULN_ANALYSIS", "EXPLOITATION"],
    triggers=["jwt_detected", "auth_token_seen"],
    requires=["http_traffic"],
    produces=["forged_token", "cracked_secret", "admin_session"],
    risk_level="medium",  # how loud is this attack on the wire
)
class JWTBreakerModule(CapabilityModule):
    async def execute(self, ctx: EngagementContext) -> ModuleResult:
        ...
```

Future workstreams (1-6) write modules against this contract. The orchestrator finds them automatically.

### 5. The recon subsystem — `src/orchestrator/phases/recon.py`

Wraps existing tools (nmap, whatweb, dig, curl) and produces a normalized recon report. NOT a new vuln scanner — just systematic information gathering.

### 6. The enumeration subsystem — `src/orchestrator/phases/enumerate.py`

Wraps web crawling (gospider/feroxbuster/ffuf) and API discovery (kiterunner-style) and produces a target attack-surface map. Identifies auth mechanism, parameter inventory, technology fingerprint.

### 7. The vuln-analysis dispatcher — `src/orchestrator/phases/vuln_analysis.py`

Iterates through registered capability modules and runs each one whose triggers fire on the enumeration output. JWT detected → run JWT module. Login form found → run SQLi module. Etc.

### 8. The exploitation phase — `src/orchestrator/phases/exploit.py`

For confirmed vulnerabilities, runs the exploit. Operator approval gate for anything destructive (file deletion, persistence, lateral movement). Read-only exploits (read /etc/passwd via XXE) run automatically; write/persistence exploits require approval.

### 9. The reporting engine — `src/orchestrator/reporting.py`

Generates three artifacts per engagement:
- `REPORT.md` — full technical writeup
- `REPORT.html` — pretty browser-friendly version with screenshots
- `EXEC_SUMMARY.pdf` — 1-page executive summary

Auto-includes MITRE ATT&CK mappings and CVSS scores per finding.

### 10. Live narration — extends existing `Live Narrator Engine`

Already built — broadcasts to terminal, log file, WebSocket. Sprint 00 wires the orchestrator to it so every phase emits clean narration in real time.

### 11. The engagement context — `src/orchestrator/context.py`

The shared blackboard every module reads from and writes to. Stores: target, phase outputs, captured tokens, identified vulns, exploit results, authorization metadata. Persisted to disk every 30 seconds so a crash doesn't lose state.

### 12. Tests

- Unit tests for state machine transitions
- Authorization gate negative tests (must refuse unauthorized targets)
- Integration test: `err0rs own http://localhost:3000` against fresh Juice Shop, asserts engagement completes and report is generated
- Sandbox test: same against deliberately-vuln Flask app

### 13. Documentation

- `docs/orchestrator/USAGE.md` — operator-facing usage guide
- `docs/orchestrator/ARCHITECTURE.md` — engagement state machine + phase contracts
- `docs/orchestrator/MODULE_AUTHORING.md` — how to write a new capability module
- Update top-level README with the new `err0rs own` workflow

---

## Week-by-week breakdown

### Week 1 — Skeleton + authorization

**Hours: ~8**

- [ ] Scaffold `src/orchestrator/` directory tree
- [ ] Implement `EngagementContext` (the blackboard)
- [ ] Implement state machine (`engagement.py`) with phase enum + transitions
- [ ] Implement authorization gate (`authorization.py`) with full negative testing
- [ ] Implement `bin/err0rs` entry point with subcommand routing (Click or argparse)
- [ ] Wire up logging to per-engagement JSONL files
- [ ] Wire up Live Narrator Engine integration

**Done when:** `err0rs own http://example.com` refuses to run without authorization, AND `err0rs own http://localhost:3000` runs through an empty state machine to COMPLETE without crashing.

### Week 2 — Phases + module registry

**Hours: ~8**

- [ ] Implement `recon.py` phase (wraps nmap/whatweb/dig)
- [ ] Implement `enumerate.py` phase (wraps feroxbuster + custom crawler)
- [ ] Implement module registry with `@register_module` decorator
- [ ] Port the existing 18 baseline Juice Shop solvers to the new module contract
- [ ] Implement `vuln_analysis.py` dispatcher
- [ ] Implement basic `exploit.py` phase

**Done when:** `err0rs own http://localhost:3000` runs through Recon → Enumeration → Vuln Analysis → Exploitation, finds and exploits at least the 18 already-covered Juice Shop challenges.

### Week 3 — Reporting + polish

**Hours: ~6**

- [ ] Implement `reporting.py` (Markdown, HTML, PDF)
- [ ] Add MITRE ATT&CK + CVSS auto-tagging
- [ ] Operator-approval gates for destructive exploits
- [ ] Write integration tests against Juice Shop
- [ ] Build `tests/orchestrator_sandbox/` Flask app
- [ ] Write all 4 documentation files
- [ ] Update top-level README + Quick Start
- [ ] Tag a release: `v3.3.0-orchestrator`
- [ ] Hunter S. Thompson commit

**Done when:** Fresh checkout + `err0rs own http://localhost:3000` produces a complete HTML report with all 18 known findings, correctly attributed to MITRE techniques. Reproducible on a clean Pi.

---

## Acceptance criteria — all must pass

1. ✅ `err0rs own http://example.com` (or any non-localhost) refuses to run without explicit authorization
2. ✅ `err0rs own http://localhost:3000` (Juice Shop) completes a full engagement in <15 minutes
3. ✅ Generated `REPORT.html` includes: target, phase timeline, findings table with severity, MITRE mappings, exploit reproductions
4. ✅ All 18 currently-covered Juice Shop challenges still solve via the new orchestrator path
5. ✅ Module registry has `@register_module` decorator that future workstream sprints can use without modification
6. ✅ Live Narrator emits status updates throughout — no silent runs
7. ✅ Engagement state persists every 30 seconds; crash recovery works
8. ✅ Authorization gate has 100% test coverage including bypass attempts (e.g., `localhost.evil.com` should fail)

---

## Risk register

| Risk | Mitigation |
|---|---|
| State machine over-engineering | Keep phase contracts simple — input/output dicts, not classes |
| Authorization gate has bypass | 100% coverage on negative tests, security review before merge |
| Existing 18 solvers don't port cleanly | Port one as a spike in Week 1, refine the contract before porting the rest in Week 2 |
| Reporting bloat (3 formats is a lot) | Start with Markdown only, HTML/PDF can ship in Sprint 00.1 if Week 3 runs over |
| `err0rs` command name conflicts with something on PATH | Confirm in Week 1; fall back to `errors` if needed |

---

## Out of scope (parking lot)

- Active Directory engagements (separate workstream after web is solid)
- Wireless / RF (separate hardware-dependent workstream)
- Cloud provider attacks (AWS/GCP/Azure — separate workstream)
- C2 / persistence frameworks (operator-approved only, deferred)
- Lateral movement (deferred until single-host is mature)
- Multi-target / chained engagements (deferred — one target at a time first)

---

## Definition of "done"

All 8 acceptance criteria pass. `err0rs own http://localhost:3000` works. Documentation operator-readable. Tagged release pushed.

The next sprint (01: JWT Engine) plugs into the registry contract this sprint defines. Every subsequent sprint inherits the orchestrator's discipline.

---

**Created:** 2026-05-01
**Status:** Planned, not yet started
**Replaces:** Original Sprint 01 plan (JWT Engine moves to Sprint 02 after orchestrator ships)
**Next:** Sprint 01 (renumbered) — JWT Manipulation Engine
