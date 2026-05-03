# Sprint 04 — Professor Mode

> **The product-defining sprint.** This is what makes ERR0RS different from every other pen-test tool — including hackingtool-plugin, Metasploit Pro, Cobalt Strike, and Pentest-Tools.com. None of them teach while they work.

**Goal:** Add a real-time, conversational, fully-local AI professor that explains every step of an engagement, holds in-depth security discussions, and adapts coaching to the operator's experience level.

**Sprint length:** 3 weeks (~25 hours of focused work, fits around school)
**Owner:** Eros (Gnosisone) + Claude
**Validation target:** Local Juice Shop engagement, OSU teach lessons, standalone brainstorming sessions

---

## Why this sprint matters more than the previous six combined

Sprints 00–03 gave ERR0RS *capability* — it can own targets autonomously now. JWT engine, NoSQL injector, SSTI/PP engine, single-command UX, audit logs, authorization gates. 279 tests, 100% passing.

But every other commercial platform also has capability. The thing nobody else has — the thing that's worth donating to OSU's cybersec program, worth a Patreon, worth being an OSCP study companion — is **a senior pen-tester who lives in your terminal and teaches you while it works.**

That's Professor Mode. It's the moat. It's the product.

---

## The user experience target

### Live narration during engagement

```
$ err0rs own http://localhost:3000 --professor

[ERR0RS] Engagement #2026-05-03-001-a87bda starting.
[Professor]
  We're going to run the full kill chain against Juice Shop. I'll narrate
  what each phase does and why. Ask me anything by typing in the chat
  panel — the engagement won't stop, we can talk while it runs.

──── Phase 1: Reconnaissance ────────────────────────────────────────
[Professor]
  Recon comes first because we can't attack what we don't understand.
  I'm starting with nmap -sV on the top 1000 ports — that's a service-
  version scan, less stealthy than -sS but it tells us what's actually
  RUNNING on each port. For Juice Shop, I expect to see node/express on
  3000.

  Want a deeper explanation of -sV vs -sS? Just ask.

[nmap_discovery] ✓ 3000/tcp open node.js (Express 4.x)  (8.4s)

[Professor]
  Found exactly what I expected. Express on 3000 is good news — that
  means we're looking at a Node.js stack, which opens up SSTI via EJS
  or Pug, prototype pollution, and NoSQL (Mongo is the typical Express
  pairing). I'll bias the next phases toward those vuln classes.

──── Phase 3: Vulnerability Assessment ──────────────────────────────
[Professor]
  Vuln assessment is where the native engines fire. Watch for these:
  - jwt_breaker scans every captured token from prior phases
  - nosql_injector looks for Mongo error fingerprints
  - template_injector probes for SSTI

  Each one is a Python module I wrote — they don't shell out, they call
  attack code directly. Faster, more reliable, fully testable.

[jwt_breaker] ✓ JWT cracked via curated wordlist  (0.3s)
              secret='mySecret' (top-100 weak secrets list)

[Professor]
  Critical finding! 'mySecret' is the canonical Juice Shop test secret —
  if you see it on a real engagement, the dev forgot to rotate the demo
  config. With this we can forge ANY token, including admin sessions.

  This is a CWE-321 (use of hardcoded cryptographic key). For your
  report, the remediation is: 1) rotate the secret immediately, 2) move
  to a secrets manager (HashiCorp Vault, AWS Secrets Manager), 3) add a
  startup check that refuses to boot if the secret matches a known
  weak list.

  [User typing in chat panel...] "wait, why did it crack so fast?"

[Professor]
  Great question. HMAC-SHA256 is fast — about 100M ops/sec on a Pi 5.
  We tested ~600 known-weak secrets, that's ~6 microseconds per try
  in pure Python. Speed isn't the vulnerability — using a known weak
  secret IS. If they'd used `openssl rand -base64 32`, our wordlist
  would never crack it and we'd need rockyou.txt (14M secrets, ~140
  seconds) which still wouldn't work for a properly-random secret.
```

That's the experience. The professor explains, predicts, contextualizes, and answers questions without stopping the engagement.

### Brainstorming mode

```
$ err0rs brainstorm

[Professor]
  What are we thinking about today?

[User] How would you approach a Joomla 4.x site for a black-box test?

[Professor]
  Good target — Joomla 4.x has a small but exploitable attack surface.
  Here's how I'd sequence it:

  Phase 1 (Recon, ~10 min):
    - Joomla version fingerprinting via /administrator/manifests/files/joomla.xml
      (often left readable — gives you exact version)
    - Plugin enumeration via /index.php?option=com_<name>
    - Template detection from <link href="/templates/...">
    - User enumeration through forgot-password timing differences

  Phase 2 (Vulns to check first, in priority order):
    1. CVE-2023-23752 — unauthenticated information disclosure via
       /api/index.php/v1/users (affects 4.0.0–4.2.7)
    2. SQLi in third-party com_* extensions — most Joomla CVEs are
       extension-side, not core
    3. SSTI in custom modules — Smarty is common, my template_injector
       has full Smarty RCE chains
    4. Default admin credentials (admin/admin still works on 1-in-30
       installs by my last engagement count)

  Want me to spin up a Joomla instance in docker and run through it?
  I can do `docker run -p 8080:80 joomla:4` and we'll do it together.

  Sources I'm pulling from:
    - JoomVS scanner methodology (in our knowledge/recon corpus)
    - HackTricks Joomla notes (in our knowledge/exploitation corpus)
    - My own training-data knowledge of Joomla's history
```

### Coaching mode (with teach engine)

```
$ err0rs lesson 14

[Lesson 14: SQL Injection Fundamentals]
[Professor]
  Lesson 14 is SQLi fundamentals. Before we start, let me check what
  you already know — last time we worked together you were comfortable
  with Union-based attacks. Have you done blind boolean SQLi yet?

[User] not really

[Professor]
  OK, then we'll cover it carefully. The lesson will walk through 4
  techniques: Union, Error-based, Blind boolean, and Time-based blind.
  I'll explain each one, show you the syntax, then give you a target
  to practice on.

  First concept: in classic SQLi, the database executes attacker-
  injected SQL because the app concatenates user input into a query
  without parameterization. Here's the vulnerable Python pattern:

      query = "SELECT * FROM users WHERE name = '" + user_input + "'"

  Why does that fail? Take a moment.

[User] because if user_input contains a quote it breaks the query

[Professor]
  Exactly right. And worse — if user_input is `' OR '1'='1`, the
  query becomes:

      SELECT * FROM users WHERE name = '' OR '1'='1'

  Which returns ALL users. We just bypassed authentication.

  Now, the FIX is parameterized queries — the database never confuses
  data with code. But you don't need that for this lesson; you need
  to know how to EXPLOIT the broken pattern. Ready for technique 1?
```

That's the experience. Three modes, one engine.

---

## Sprint deliverables — workstream breakdown

### Workstream A: ProfessorEngine core (week 1, ~9 hours)

**File:** `src/core/professor_engine.py`

The brain. Subscribes to AutoKillChain events, decides when to speak,
formulates explanations, streams them through the narrator.

```python
class ProfessorEngine:
    """
    Subscribes to engagement events and produces explanatory utterances.
    All three modes (live/brainstorm/coach) share this engine.
    """

    def __init__(self, *, mode: str, profile: UserProfile,
                 narrator: LiveNarrator, llm: LocalLLM,
                 rag: RagRetriever, audit: AuditLogger):
        ...

    async def on_event(self, event: ProfessorEvent) -> Optional[Utterance]:
        """Decide whether to speak about this event, and if so, what."""

    async def on_user_question(self, question: str) -> Utterance:
        """Operator asked something — answer it without blocking the chain."""

    def should_speak(self, event: ProfessorEvent) -> SpeakDecision:
        """
        Adaptive verbosity decision logic:
        - Always speak: phase_start, critical findings, risky actions, questions
        - Sometimes speak: intermediate findings (1st of kind = yes, Nth = no)
        - Never speak: bookkeeping, retries, parameter expansion
        """
```

**Decision logic for adaptive verbosity:**

| Event | Novice | Intermediate | Expert |
|---|:---:|:---:|:---:|
| phase_start | Always + full explanation | Always + brief | Phase name only |
| critical_finding | Always + how-it-works + remediation | Always + remediation | Always + 1-line |
| info_finding (1st of kind) | Always + concept | Often | Sometimes |
| info_finding (5th of same kind) | Briefly | Never | Never |
| user_question | Always (full answer) | Always | Always |
| risky_action_proposed | Always + risks + alternatives | Always + risks | Always |
| tool_skip (not installed) | Explain why + how to install | Brief mention | Silent |

**LLM prompt templates:** one per event type. Templates pull from RAG and inject context (current phase, last finding, user profile). Cached responses for canned events (phase_start narration is identical engagement-to-engagement).

**Tests (~30):**
- should_speak() decision matrix for all 7 event types × 3 levels
- LLM prompt rendering with mock context
- Cache hit/miss for canned vs novel events
- Async event processing doesn't block

### Workstream B: User profile + adaptation (week 2 first half, ~6 hours)

**File:** `src/core/user_profile.py` + `~/.err0rs/profile.json`

Persistent profile that drives adaptive verbosity.

```python
@dataclass
class UserProfile:
    operator_id: str                    # default: $USER
    experience_level: str               # novice | intermediate | expert
    concepts_explained: dict            # {"jwt_alg_none": {"count": 3, "last": "2026-05-01"}}
    concepts_mastered: set              # operator marked "I know this" or inferred
    vocab_calibration: dict             # {"RFC1918": "private network IP"} — substitutions for novices
    preferred_techniques: list          # [techniques user has shown interest in]
    skip_explanations: set              # things user explicitly said "don't explain"
    sessions_count: int
    first_seen: str
    last_seen: str

    def adapt_text(self, text: str) -> str:
        """Apply vocab substitutions for the current level."""

    def has_seen(self, concept: str, within_days: int = 30) -> bool:
        """Don't re-explain something we covered recently."""

    def update_from_session(self, audit_log: list[dict]) -> None:
        """Infer mastery from observed behavior (advanced commands without errors)."""
```

**Profile schema lives at `~/.err0rs/profile.json`:**

```json
{
  "operator_id": "eros",
  "experience_level": "intermediate",
  "concepts_explained": {
    "jwt_alg_none": {"count": 5, "last": "2026-05-02T14:30:00Z"},
    "ssti_jinja2_subclass_walking": {"count": 1, "last": "2026-05-03T10:15:00Z"}
  },
  "concepts_mastered": ["sql_union_basic", "xss_reflected_basic"],
  "vocab_calibration": {},
  "preferred_techniques": ["jwt_attacks", "ssti", "nosql"],
  "skip_explanations": ["what_is_nmap"],
  "sessions_count": 47,
  "first_seen": "2026-04-15T09:00:00Z",
  "last_seen": "2026-05-03T10:15:00Z"
}
```

**Mastery inference rules:**
- User issues `--mode FULL_AUTO` without `--professor` 3 sessions in a row → +1 confidence (knows what they're doing)
- User cancels engagement at exploitation phase 3 times → assume cautious operator, more explanations
- User asks "what is X" → mark X as not mastered
- User says "skip explaining X" → add to skip_explanations
- 90 days no activity on a concept → decay mastery flag

**Tests (~25):**
- Profile load/save round-trip
- Schema migration (when we add fields later)
- Mastery inference from synthetic audit logs
- Vocab adaptation correctness
- has_seen() respects time window

### Workstream C: Web UI chat panel (week 2 second half, ~6 hours)

**Files:**
- `src/ui/web/professor.html`
- `src/ui/web/professor.js`
- `src/ui/web/professor.css`
- `src/ui/errorz_launcher.py` — new WebSocket endpoint `/ws/professor`

The chat-style web interface. Renders inline alongside the existing engagement UI.

**Layout:**

```
┌──────────────────────────────────────────────────────────────────┐
│  ERR0RS  •  Engagement 2026-05-03-001  •  Professor Mode ON     │
├─────────────────────────────────┬────────────────────────────────┤
│                                 │  💬 Professor                   │
│   [ Engagement Output ]         │                                │
│                                 │  Phase 1 starting. We're       │
│   ──── Phase 1: Recon ────      │  doing recon first because     │
│   nmap_discovery ✓              │  we can't attack what we...    │
│   subfinder ✓                   │                                │
│                                 │  [✓ JWT cracked: mySecret]     │
│   ──── Phase 3: Vuln Assess ─   │  This is the canonical Juice   │
│   jwt_breaker ✓ (4 findings)    │  Shop test secret. CWE-321...  │
│   nosql_injector ✓              │                                │
│                                 │  ┌──────────────────────────┐  │
│                                 │  │ Ask the professor...     │  │
│                                 │  └──────────────────────────┘  │
└─────────────────────────────────┴────────────────────────────────┘
```

**Bidirectional WebSocket protocol:**

```javascript
// Server → Client (professor utterance)
{
  "type": "utterance",
  "speaker": "professor",
  "text": "Critical finding! 'mySecret' is the canonical Juice Shop...",
  "context": {
    "event": "finding",
    "phase": "vuln_assessment",
    "finding_title": "JWT cracked via curated wordlist"
  },
  "citations": [
    {"source": "knowledge/auth/jwt_attacks.md",
     "passage_id": "weak_secrets_section"}
  ],
  "timestamp": "2026-05-03T10:15:23Z"
}

// Client → Server (user question)
{
  "type": "question",
  "text": "wait, why did it crack so fast?",
  "engagement_id": "2026-05-03-001",
  "timestamp": "2026-05-03T10:15:30Z"
}
```

**Features:**
- Citations: clickable, opens source document inline
- Code blocks: syntax-highlighted (Prism.js, already shipped with Phoenix UI)
- MITRE links: T-numbers auto-link to attack.mitre.org
- Severity icons: 🔴 critical, 🟠 high, 🟡 medium, ℹ️ info
- Conversation history: persisted to engagement audit log via existing `audit.py`
- "Don't explain X again" button per utterance — updates user profile
- Theme: matches existing Phoenix-OS dark theme

**Tests (~15):**
- WebSocket connection lifecycle
- Message serialization round-trip
- Question queueing while engagement runs (no blocking)
- Profile updates from "don't explain again" actions

### Workstream D: Three modes integration (week 3, ~4 hours)

Three modes share Workstreams A/B/C. This workstream wires each mode into its trigger.

**Mode 1: Live narration during kill chain**

In `src/orchestration/auto_killchain.py`, add an event emitter alongside the existing `_kc_print()` calls:

```python
# Existing: _kc_print(f"  ▶ Running: {tool_id}...")
# New: also fire professor event
if professor:
    await professor.on_event(ProfessorEvent(
        type="phase_start", phase=phase_def["id"],
        tools_planned=phase_def["tools"],
    ))
```

Hooks needed at: phase_start, phase_end, tool_start, tool_end, finding_emitted, risky_action_proposed (e.g. exploitation phase about to fire).

CLI: `err0rs own <target> --professor` enables the mode.

**Mode 2: Brainstorm**

`bin/err0rs brainstorm` opens an interactive REPL backed by the same ProfessorEngine in "no engagement" context. Multi-turn coherence via conversation history persisted to a brainstorm session ID (separate audit log).

**Mode 3: Coach**

In `src/education_new/teach_engine.py`, hook professor into the lesson loop:

```python
# Existing: lesson.show_section(N)
# New: also let professor narrate the section
if professor:
    await professor.on_event(ProfessorEvent(
        type="lesson_section",
        lesson_id=lesson.id,
        section_id=N,
        section_text=lesson.sections[N].text,
    ))
```

The professor explains the concept, asks Socratic checks, adapts difficulty
based on user answers.

**Tests (~10):**
- Live narration end-to-end against fake kill chain
- Brainstorm session round-trip
- Coach mode: lesson section → professor narration → user answer → adaptation

---

## Acceptance criteria — all must pass

1. ✅ `err0rs own http://localhost:3000 --professor` runs to completion with live narration in the web UI chat panel
2. ✅ User can type questions in the chat panel mid-engagement; engagement does not pause; questions get answered within 30 seconds (LLM latency on Pi 5)
3. ✅ `err0rs brainstorm` opens an interactive session with multi-turn memory
4. ✅ `err0rs lesson <N>` runs a teach lesson with professor coaching
5. ✅ Adaptive verbosity verified: novice profile produces ~3x more explanation tokens than expert profile for same engagement
6. ✅ All citations link back to a real document in the knowledge corpus (or say "from training data" when no source exists)
7. ✅ Conversation history persists to `~/.err0rs/engagements/<id>/professor.jsonl` (separate from audit.jsonl)
8. ✅ "Don't explain X again" button updates `~/.err0rs/profile.json`
9. ✅ Profile mastery inference: after 5 sessions where user issues advanced commands without errors, experience_level promotes from novice → intermediate
10. ✅ Tests: 80+ unit tests + 20+ integration tests, 100% pass

---

## Risk register

| Risk | Mitigation |
|---|---|
| LLM latency on Pi 5 (~10-30s per response) | Pre-cache canned explanations per event type. Only call LLM for novel findings + user questions. Cache invalidation: 30 days. |
| Kill chain blocks waiting on user question | Async event loop. Engagement runs in one task, professor in another. Question goes through WebSocket queue, never blocks the chain. |
| Profile gets out of date / stale claims | Profile decays "mastery" claims after 90 days no activity. Operator can reset profile via `err0rs profile reset`. |
| RAG returns wrong/irrelevant source | All explanations cite sources; user can mark "this citation is wrong" — feeds back to RAG ranking. |
| LLM hallucinates non-existent CVEs/techniques | Only the LLM's prose is generative. All technical claims (CVE numbers, MITRE IDs, exact commands) come from RAG with explicit citations. If RAG has nothing, professor says "from training data, verify before relying on this." |
| User asks question that requires running another tool (e.g. "what does the response look like?") | Professor cannot trigger tool execution. Says "I can't query the target directly, but you can run X manually and paste the output." This is intentional — separation of conversation from action. |
| Web UI breaks on mobile | Defer mobile polish to Sprint 04.5. Desktop/tablet first. |
| Voice output requested mid-sprint | Out of scope. Sprint 04.5 — espeak fallback, piper-tts as nicety. |

---

## Out of scope (parking lot for next sprints)

- Voice output (espeak/piper) — Sprint 04.5
- Mobile-responsive UI — Sprint 04.5
- Multi-operator engagements (two people in same chat) — Sprint 05+
- LLM swap (use llama.cpp instead of Ollama) — out of scope, Ollama works
- Hailo NPU acceleration of LLM — defer until we can measure if it helps
- Discord / Slack notification integration — Sprint 06+
- Voice INPUT (operator dictation) — out of scope
- Image generation (diagrams of attack chains) — Sprint 06+
- Profile portability across devices — Sprint 05+

---

## Definition of "done"

All 10 acceptance criteria pass. `err0rs own <target> --professor` produces a coherent, useful, real-time narrated engagement with adaptive verbosity. `err0rs brainstorm` and `err0rs lesson <N>` work with the same professor backend. 100+ tests pass. Documentation operator-readable. Tagged release `v3.4.0-professor`.

The next sprint (05) gets to choose between completing Workstream 4-6 from the original Phase A roadmap (OSINT enrichment / Race Conditions / Stego), OR continuing to enhance the professor with voice and mobile.

---

## What I need to do BEFORE Sprint 04 Week 1 (read-only audit)

Before writing any code, I need to walk the existing pieces. Two hours of reading, no writing. Outputs go in `docs/sprints/SPRINT_04_AUDIT.md`:

1. Read `src/core/narrator.py` — what does the existing Live Narrator broadcast? Where does it send to? How is it constructed?
2. Read `src/core/conversation_engine.py` — does this already do multi-turn? What's the LLM interface?
3. Read `src/education_new/teach_engine.py` — what's the lesson model? How are sections delivered?
4. Read `src/ui/errorz_launcher.py` chat endpoints (lines around 326, 901, 2170) — how do existing WebSocket flows work?
5. List ChromaDB collections (`errors_knowledge_db/chroma.sqlite3`) — what corpora exist already?
6. Confirm Ollama is running, qwen2.5-coder:7b is the model, check latency for a 200-token response.

After that audit, the Sprint 04 spec gets refined (this doc) — specifically: which existing pieces we EXTEND vs. which we REPLACE vs. which we BUILD-NEW. Same discipline that turned Sprint 00 from "3 weeks" into "1 week" when we discovered AutoKillChain was 80% done.

---

## Definition of "started"

Sprint 04 hasn't started until:
- [ ] This document is committed to ERR0RS-clean
- [ ] SPRINT_04_AUDIT.md is written from the read-only audit above
- [ ] Sprint 04 spec is refined based on audit findings
- [ ] An issue is created on GitHub: "Sprint 04 — Professor Mode"
- [ ] A feature branch exists: `git checkout -b sprint-04-professor`
- [ ] Workstream A first task is in progress (`src/core/professor_engine.py` scaffolded)

---

## What ERR0RS becomes when this ships

Today: a fully-local, fully-autonomous penetration testing agent with single-command UX, authorization gates, audit logs, three native attack engines (JWT, NoSQL, SSTI/PP), and 279 passing tests.

After Sprint 04: all of the above PLUS a senior pen-tester who lives in your terminal, narrates every step, holds in-depth security discussions, and adapts coaching to your level. Fully local. Fully private. Fully under your control.

That's the OSU donation. That's the Patreon pitch. That's the OSCP study companion. That's the thing nobody else has built.

> *"Buy the ticket, take the ride."* — Hunter S. Thompson

---

**Created:** 2026-05-03
**Status:** Planned, not yet started — waiting on read-only audit
**Owner:** Eros (Gnosisone) + Claude
**Replaces:** Original Workstream 4 (OSINT Enrichment) as Sprint 04 — OSINT moves to Sprint 05
**Next:** Sprint 04 Week 1 — `src/core/professor_engine.py` scaffold
