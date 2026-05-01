# Sprint 01 — JWT Manipulation Engine

> **Workstream 1 of 6** in the [Phase A roadmap](../../../juice-shop-portfolio/AUTOMATION_ROADMAP.md) to bring ERR0RS to 111/111 autonomous Juice Shop coverage. Each workstream builds a *general-purpose capability module* that pays off on real engagements, not just Juice Shop.

**Goal:** Add a production-grade JWT abuse module to ERR0RS that works against any web app — and unlocks 5 Juice Shop challenges as validation.

**Sprint length:** 4 weeks (~30 hours of focused work, fits around school)
**Owner:** Eros (Gnosisone) + Claude
**Validation target:** local Juice Shop instance + a deliberately-misconfigured Flask sandbox

---

## Why JWT first

Looked at all 6 workstreams as candidates for "Workstream 1." JWT won on every dimension:

| Criterion | JWT score | Why |
|---|---|---|
| Real-world utility | ★★★★★ | Every modern web pen-test sees JWTs. This pays off forever. |
| Juice Shop unlock count | ★★★★ | 5 challenges (JWT Forgery, Score Board JWT, Forged Signed JWT, Two Factor Auth, Login CISO variants) |
| Self-containment | ★★★★★ | Pure crypto/token manipulation. No external deps beyond `pyjwt` + hashcat. |
| Test reproducibility | ★★★★★ | Stateless: feed in token, get out forged token. Easy regression tests. |
| Risk of scope creep | ★ | Bounded problem with well-known attack surface. |
| OSCP relevance | ★★★★ | JWT abuse is on the exam and on every web pentest cert. |

NoSQL injection (Workstream 2) was a close second. SSTI (Workstream 3) is higher-impact but harder to build safely.

---

## Sprint deliverables

### 1. Core module — `src/tools/auth/jwt_breaker.py`

**Public API:**

```python
from src.tools.auth.jwt_breaker import JWTBreaker

jb = JWTBreaker()

# Decode any token (no verification)
header, claims, sig = jb.decode("eyJhbGc...")

# Try the `none` algorithm bypass
forged = jb.try_none_algorithm(token, modified_claims={"role": "admin"})

# Crack HS256 secret offline (uses hashcat under the hood)
secret = jb.crack_hs256(token, wordlist="/usr/share/wordlists/rockyou.txt", timeout=300)

# Mint a new token with arbitrary claims
new_token = jb.forge(secret, claims={"email": "admin@juice-sh.op", "role": "admin"}, alg="HS256")

# Generate kid-header injection payloads
payloads = jb.kid_injection_payloads(target_path="/etc/passwd")

# Algorithm confusion (HS256 ↔ RS256 with public key as HMAC secret)
confused = jb.alg_confusion(token, public_key_pem)

# All-in-one auto mode for ERR0RS Auto Brain
result = jb.auto_attack(token, target_url="http://localhost:3000", strategy="exhaust")
```

**Internal structure:**

```
src/tools/auth/
├── __init__.py
├── jwt_breaker.py          # main module (~400 lines)
├── jwt_secrets.txt         # curated short-secret wordlist (top 1000 known weak JWT secrets)
└── jwt_payloads.py         # kid injection, alg confusion, signature stripping templates
```

### 2. Plugin registration — `BasePlugin` integration

Register `JWTBreakerPlugin` so the Operator Brain can invoke it autonomously when a JWT is detected on the wire. Hooks into the existing `SharedContext`/`EventBus` architecture from the plugin system.

```python
# src/tools/auth/jwt_breaker_plugin.py
class JWTBreakerPlugin(BasePlugin):
    name = "jwt_breaker"
    triggers = ["jwt_detected", "auth_token_seen"]
    capabilities = ["forge", "crack", "decode", "kid_inject", "alg_confuse"]

    async def on_event(self, event, ctx):
        if event.type == "jwt_detected":
            await self.handle(event.token, ctx)
```

### 3. RAG corpus seeding

Add to ChromaDB:
- OWASP JWT Cheatsheet
- PortSwigger JWT labs writeups
- `jwt_tool` documentation
- The 50+ documented "weak JWT secret" word lists from public bug bounty writeups
- A short curated knowledge file: `knowledge/auth/jwt_attacks.md` (we'll write this) covering the 7 canonical JWT attacks with detection signatures and mitigations (purple-team format)

### 4. Operator Brain integration

In Auto mode, when ERR0RS sees a `Set-Cookie: token=eyJ...` header or a `Bearer eyJ...` Authorization header on any traffic it observes, the JWT breaker module gets invoked automatically. Output goes to the Live Narrator Engine so the human operator sees what the agent is trying.

### 5. Tests — `tests/test_jwt_breaker.py`

Pytest suite with three layers:

**Unit tests** (no network):
- Decode known tokens, verify claims extraction
- Forge tokens with known secrets, verify against `pyjwt`
- Generate `none` alg payloads, verify structure

**Integration tests** (against local Juice Shop):
- Spin up Juice Shop on `localhost:3000` via Docker (already in `start_lab.sh`)
- Run `JWTBreaker.auto_attack` against it
- Assert Juice Shop's `/api/Challenges/scoreboard` shows all 5 JWT challenges as solved
- Assert run completes in <90 seconds

**Sandbox tests** (against deliberately-vuln Flask app we ship in `tests/jwt_sandbox/`):
- Confirms the module works against a non-Juice-Shop target
- Tests edge cases: nested JWTs, JWE encryption, ES256 keys, etc.

### 6. Documentation — `docs/modules/jwt_breaker.md`

Operator-facing docs covering:
- What it does + why
- Threat model (what it can't do — JWE, hardware-backed keys, etc.)
- Usage examples (CLI + API + Auto mode)
- Detection signatures (how a blue team would spot this attack)
- Mitigation guidance (the purple-team companion)

### 7. Sprint completion artifact — update `juice-shop-portfolio`

When the sprint ends, update `juice-shop-portfolio/PORTFOLIO.md`:
- ERR0RS autonomous coverage: 18 → 23 (16% → 21%)
- Move the 5 unlocked challenges from `unsolved.json` to `solved.json`
- Regenerate `ATTACK_PLAN.md`

---

## Week-by-week breakdown

### Week 1 — Foundation

**Hours: ~8**

- [ ] Scaffold `src/tools/auth/` directory and `__init__.py`
- [ ] Implement `JWTBreaker.decode()` — parse base64url, extract header/claims/signature
- [ ] Implement `JWTBreaker.try_none_algorithm()` — strip sig, set alg to "none"
- [ ] Implement `JWTBreaker.forge()` — mint tokens with HS256/RS256
- [ ] Write unit tests for the above three methods
- [ ] Compile curated `jwt_secrets.txt` from public bug bounty writeups (~1000 entries)

**Done when:** `pytest tests/test_jwt_breaker.py -k "unit"` passes 100%.

### Week 2 — Cracking + advanced attacks

**Hours: ~8**

- [ ] Implement `crack_hs256()` — wraps hashcat with token-formatted hash output
- [ ] Implement `kid_injection_payloads()` — generates path-traversal + SQLi `kid` values
- [ ] Implement `alg_confusion()` — RS256 → HS256 with public key as secret
- [ ] Add CLI entry point: `python3 -m src.tools.auth.jwt_breaker --token <jwt> --auto`
- [ ] Test against curated examples from PortSwigger labs (downloaded JWTs as fixtures)

**Done when:** CLI can decode/crack/forge any of the included fixture tokens.

### Week 3 — Operator Brain integration

**Hours: ~8**

- [ ] Implement `JWTBreakerPlugin(BasePlugin)`
- [ ] Wire into `SharedContext`/`EventBus`
- [ ] Add JWT detection regex to traffic interceptor (Cookie + Authorization headers)
- [ ] Add Live Narrator hooks so the agent's reasoning is visible
- [ ] Add module to `Arsenal UI` with NLP search keywords
- [ ] Add lesson to `teach_engine` (lesson #42): "JWT Abuse — Forging Tokens"

**Done when:** Auto mode in ERR0RS, when pointed at a Juice Shop instance, finds a JWT and runs the breaker without human prompt.

### Week 4 — Validation + polish

**Hours: ~6**

- [ ] Write integration tests against local Juice Shop
- [ ] Build deliberately-vuln Flask sandbox in `tests/jwt_sandbox/`
- [ ] Write sandbox tests
- [ ] Confirm all 5 Juice Shop JWT challenges flip to solved autonomously
- [ ] Write `docs/modules/jwt_breaker.md`
- [ ] Update portfolio (`juice-shop-portfolio/PORTFOLIO.md` and JSON files)
- [ ] Tag a release: `v3.3.0-jwt`
- [ ] Hunter S. Thompson commit message + push

**Done when:** Fresh checkout + fresh Juice Shop = 5 challenges auto-solved. Reproducible on a clean Pi.

---

## Acceptance criteria — all must pass

1. ✅ `pytest tests/test_jwt_breaker.py` passes 100% on a fresh checkout
2. ✅ Auto mode against fresh Juice Shop solves: JWT Forgery, Score Board JWT, Forged Signed JWT, 2FA, Login CISO — with no human input
3. ✅ Module also works against the Flask sandbox (proves generalization)
4. ✅ Regression test runs in CI, completes in <90 seconds, passes 100/100 invocations
5. ✅ `docs/modules/jwt_breaker.md` is operator-readable (a junior pen-tester can use the module from the doc alone)
6. ✅ Portfolio repo updated with new coverage numbers
7. ✅ All commits pass syntax check via `python3 -c "import ast; ast.parse(...)"`

---

## Risk register

| Risk | Mitigation |
|---|---|
| hashcat not on Pi 5 ARM64 | Confirm before Week 2; have a pure-Python HS256 cracking fallback for `<8 char` secrets ready |
| Juice Shop JWT challenges harder than expected | Have 1-week buffer baked into sprint; OK to ship 4/5 if 5th is genuinely a 5★ |
| Hailo NPU integration breaks during sprint | Sprint has zero NPU dependencies — pure CPU work |
| Scope creep into JWE / nested tokens | Explicitly out of scope for this sprint. Document as "future work" in module README. |
| Module API design wrong, requires rewrite | Mitigation: write the test file FIRST (TDD), API emerges from how tests need to call it |

---

## Out of scope (parking lot for next sprints)

- JWE (encrypted JWTs) — Workstream 1.5 if needed, otherwise after Workstream 6
- Hardware-token-backed signing — out of scope entirely (we don't attack HSMs from a Pi)
- Token replay across sessions — partial overlap with Race Conditions workstream
- OAuth / OpenID Connect flow attacks — separate workstream after JWT

---

## Definition of "started"

The sprint hasn't started until:

- [ ] This document is committed to ERR0RS-clean
- [ ] An issue is created on GitHub: "Sprint 01 — JWT Manipulation Engine"
- [ ] A feature branch exists: `git checkout -b sprint-01-jwt-engine`
- [ ] Week 1 first task is in progress (`__init__.py` scaffolded)

---

## Definition of "done"

All 7 acceptance criteria pass. Portfolio repo shows 23/111 autonomous. Hunter S. Thompson commit pushed. We open Sprint 02.

> *"Buy the ticket, take the ride."* — Hunter S. Thompson

---

**Created:** 2026-05-01
**Status:** Planned, not yet started
**Next:** Sprint 02 — NoSQL Injection (3 weeks, unlocks 4 challenges)
