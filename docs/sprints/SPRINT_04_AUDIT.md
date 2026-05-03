# Sprint 04 Pre-Work Audit — Findings

> **Discipline check:** Same audit pattern that turned Sprint 00 from 3 weeks into 1 week. Read what exists before writing any code.

**Date:** 2026-05-03
**Auditor:** Claude + Eros
**Outcome:** Sprint 04 scope reduces dramatically — most of ProfessorEngine is already built.

---

## TL;DR

**ConversationEngine in `src/core/conversation_engine.py` already implements 90% of what the Sprint 04 spec called "ProfessorEngine."** It has streaming Ollama integration, multi-turn history, operator-state injection, auto-model selection, background warmup, and is already wired to the WebSocket UI.

**Live Narrator in `src/core/narrator.py` already broadcasts to terminal + WebSocket + log file** with phase coloring, timestamps, and an explicit `teach` field for educational content. ProfessorEngine outputs route through this — no replacement needed.

**TeachEngine in `src/education_new/teach_engine.py` is a 2,294-line lesson framework.** Not yet connected to ConversationEngine. Wiring it up = small adapter, not a workstream.

**What's actually missing (Sprint 04 real scope):**
1. UserProfile + adaptation logic (~/.err0rs/profile.json)
2. AutoKillChain → Narrator event emission (~10 hook points)
3. Pre-cached canned explanations layer (caching wrapper around ConversationEngine)
4. CLI `--professor` flag and event subscription glue
5. Web UI chat panel polish (existing chat probably needs UX work but not full rebuild)
6. Tests for the new pieces

**Revised sprint length:** 3 weeks (~25 hours) → **1 week (~10 hours).** Same compression as Sprint 00.

---

## Audit findings — file by file

### 1. `src/core/narrator.py` (398 lines) ✅ READY

**What it has:**
- `Narrator` singleton class with thread-safe broadcast
- `tell(message, phase, tool, detail, finding, teach)` — the `teach` field is exactly what Professor Mode produces
- Three output channels: ANSI-colored stderr, WebSocket clients (`register_ws()`/`unregister_ws()`), log file `/tmp/err0rs_live.log`
- Phase color map for recon/scanning/exploitation/post_exploit/reporting/teaching/system
- Convenience functions: `tell()`, `narrate_tool()`, `narrate_finding()`, `narrate_phase()`
- WebSocket payload schema already defined (JSON with type/phase/tool/message/detail/finding/teach/ts/step)

**What ProfessorEngine adds:** Just calls `narrator.tell(message=..., teach=..., phase="teaching")`.

**Verdict:** No changes needed. Plug in.

---

### 2. `src/core/conversation_engine.py` (403 lines) ✅ MOSTLY READY

**What it has:**
- `ConversationEngine` class with streaming Ollama HTTP integration
- `ConversationHistory` per-session (multi-turn coherence built in)
- Auto-model selection: prefers `llama3.2:3b` → `llama3.2:1b` → `qwen2.5-coder:7b` → `err0rs-pi5:latest`
- `chat_stream(user_msg, session_id, operator_state, on_token, on_done)` — token-by-token streaming with callbacks
- `build_system_prompt(operator_state)` — injects current target/findings/mode into system prompt
- Background `_warmup()` thread keeps model in RAM (15-min `keep_alive`)
- Singleton `get_engine()`
- XP integration via `progression.award_xp("ask_question", ...)`
- 1,400+ word system prompt covering all of red/blue/CIS/OWASP/MITRE/CVE knowledge

**What's missing for full ProfessorEngine:**
- Adaptive verbosity (no profile-aware behavior)
- Pre-cached canned responses layer
- Citation tracking for RAG sources
- "Don't explain X again" feedback loop

**Verdict:** Wrap, don't replace. ProfessorEngine becomes a thin wrapper that adds caching + profile awareness + RAG citation tracking on top of ConversationEngine.

---

### 3. `src/education_new/teach_engine.py` (2,294 lines) ✅ READY (not wired)

**What it has:**
- `TeachEngine` class (line 200)
- `format_lesson(lesson)`, `find_lesson(query)`, `handle_teach_request(query)` helpers
- Per memory: 41 lessons covering AD, Kerberos, Mimikatz, BloodHound, web shells, etc.

**What's missing:**
- Zero references to `conversation_engine` in this file
- No hook point for ProfessorEngine to walk alongside the lesson

**Verdict:** Add a `with_professor=False` parameter to lesson rendering. When True, after each section, call `professor.coach_lesson_section(lesson_id, section)` which produces an utterance.

---

### 4. `src/ui/errorz_launcher.py` chat endpoints

**What it has:**
- Imports `from src.core.conversation_engine import get_engine as _get_conv_engine, is_conversational` (line 257)
- Already calls `CONV_ENGINE.chat_stream(...)` at line 1472 — chat is wired to Ollama already
- WebSocket support implied by the imports

**What's missing:**
- A dedicated `/ws/professor` channel (currently uses general chat WS)
- Event subscription model (UI doesn't get notified when AutoKillChain emits findings)

**Verdict:** Add a new WebSocket route `/ws/professor` that fans out narrator events PLUS chat. Chat-side stays as-is.

---

### 5. ChromaDB `errors_knowledge_db/` ✅ EXISTS

Multiple collection directories present (UUIDs `216cf9aa-...`, `3614bc5f-...`, etc.). Per memory: BadUSB collection has 1,903+ payloads, plus knowledge corpora across recon/exploitation/c2/credentials/evasion/badusb/wireless. RAG layer is real.

**Verdict:** No changes needed. ProfessorEngine queries ChromaDB for citations using existing infrastructure.

---

### 6. Ollama LLM performance on Pi 5 ⚠️ CRITICAL CONSTRAINT

| Test | Time |
|---|---:|
| Cold start (model not in RAM) — 40 tokens | **82.5s** |
| Warm (model loaded, keep_alive active) — 80 tokens | **38.3s** |
| Per-token estimate (warm) | ~0.5 sec/token |

**Available models on the Pi:**
- `llama3.2:3b` (fastest, what ConversationEngine prefers)
- `qwen2.5-coder:7b` (slower but available)
- `err0rs-pi5:latest` (custom model)

**Implication for Professor Mode:**

A 38s response per event is unusable for live narration if every event triggers an LLM call. **Caching is non-negotiable.** Per the spec:

- **Always cached (no LLM):** phase_start narration (one of ~7 phases — explanations don't change), tool_start narration ("running nmap because..."), tool_skip narration ("nmap not installed, install with apt"), generic boilerplate
- **LLM only:** novel critical findings (rare — maybe 3-10 per engagement), user questions (rare — maybe 0-5 per engagement), brainstorming sessions (whole purpose)

That gives ~5-15 LLM calls per engagement instead of ~500. At 38s each, that's 3-10 minutes of cumulative LLM compute spread across a 15-minute engagement. **Acceptable.**

---

## Revised Sprint 04 plan — what we actually build

Original spec had 4 workstreams over 3 weeks. After audit, scope shrinks dramatically:

### Workstream A (revised) — ProfessorEngine wrapper (~3 hours)

`src/core/professor_engine.py`:
- Wraps `ConversationEngine` (don't replace it)
- Adds `CannedExplanations` dict (phase_start/tool_start/tool_skip → static text)
- `should_speak(event, profile) -> bool` decision logic
- `narrate_event(event)` → either canned response (instant) or async LLM call
- `answer_question(text)` → always LLM, streamed
- `coach_lesson_section(lesson, section)` → templated + LLM if needed

### Workstream B (revised) — UserProfile (~2 hours)

`src/core/user_profile.py`:
- Load/save `~/.err0rs/profile.json`
- Mastery inference from session audit logs
- Adaptive verbosity decision: novice/intermediate/expert

### Workstream C (revised) — AutoKillChain event emission (~2 hours)

Edit `src/orchestration/auto_killchain.py`:
- Add `professor` param to `AutoKillChain.__init__()`
- Hook points at: phase_start, tool_start, tool_end, finding_emitted, risky_action_proposed
- Each hook calls `professor.narrate_event(...)` if professor enabled

### Workstream D (revised) — CLI flag + UI polish (~2 hours)

- Add `--professor` to `bin/err0rs own` command
- Wire ProfessorEngine into `cmd_own()` in CLI
- Confirm web UI chat panel works for both narration + Q&A
- Document in `docs/professor.md`

### Workstream E (NEW) — Tests (~2 hours)

- Unit tests for UserProfile (~15 tests)
- Unit tests for ProfessorEngine decision logic (~20 tests)
- Integration test: AutoKillChain with professor enabled emits expected events
- Smoke test: `err0rs own http://localhost:3000 --professor` runs without crash

**Total: ~11 hours, doable in 1-2 evening sessions.**

---

## Risk register update

| Risk from original spec | Audit finding |
|---|---|
| LLM latency 10-30s | Confirmed, actually 38s warm, 82s cold. Caching is mandatory. |
| Kill chain blocks on user questions | ConversationEngine already handles streaming; just need async fan-out |
| Profile gets stale | Same plan — 90-day decay |
| RAG returns wrong source | Same plan — explicit citations |
| LLM hallucinates | Same plan — RAG citations or "from training data" disclaimer |
| Multi-operator chats | Same — out of scope |

---

## Definition of "Sprint 04 ready to start"

- [x] Audit complete (this document)
- [ ] Workstream A: scaffold `src/core/professor_engine.py`
- [ ] Workstream B: scaffold `src/core/user_profile.py` + initial profile.json
- [ ] Workstream C: hook points added to AutoKillChain
- [ ] Workstream D: `--professor` flag in CLI
- [ ] Workstream E: tests pass

**Next action:** Start Workstream A. Engine is the foundation; everything else depends on it.

---

## What changes in `SPRINT_04_PROFESSOR.md`

The spec doc is mostly still correct — but the timeline shrinks from 3 weeks to ~1 week, and Workstream A becomes "wrap the existing ConversationEngine" instead of "build from scratch." I'll update the spec status from "Planned, not yet started" to "Audited, ready to execute."

> *"Buy the ticket, take the ride."* — Hunter S. Thompson
