# Next Session — ERR0RS Sprint Continuation

**Pick up here.** Updated 2026-05-14 at end of the backend-strategy session.

---

## 🎯 The 30-second status

Everything **structural and strategic** is done:
- install.sh is solid (936 lines, 6/6 smoke test pass on a fresh clone)
- 49-tool unified registry validated against schema
- 7 concept entries (CIA, OWASP, MITRE ATT&CK, kill chain, etc.)
- Phase 4 Professor Engine **already shipped** on `main` (commit `7a37052`)
- Phase 3 LLM teach generator built with **multi-backend support**:
  Claude (primary), DeepSeek (secondary), Ollama (tertiary) — see
  `docs/BACKEND_STRATEGY.md`
- **`src/ai/system_prompt.md` is the ERR0RS soul** — wise, compassionate,
  patient teacher voice. Loaded into every LLM API call regardless of backend.
- `.env.example` documents both API keys + the fallback chain

Everything **content** (the bleeding-edge teach data) is **still not** done.
The 5 stub fields per tool are empty on all 49 tools.

The runtime story works **today** — Professor Engine doesn't yet read the
v2 registry's teach fields anyway, so empty stubs don't block anything.
See "Open audit items" below.

---

## 🛤️ The fastest path to actual teach content

**Path A (recommended): Anthropic Claude at build time.**

```bash
cd /home/kali/ERR0RS-clean
nano .env                                          # paste ANTHROPIC_API_KEY
python3 tools/generate_teach.py --sample nmap sqlmap hydra   # smoke test
# eyeball src/tools/tool_registry.generated.json
python3 tools/generate_teach.py --all              # full sweep, ~10 min
```

Cost: ~$0.25 with Haiku 4.5, ~$2-3 with Sonnet 4.6. One-time.

**Path B (cheaper): DeepSeek build time.**

```bash
nano .env                                          # paste DEEPSEEK_API_KEY
python3 tools/generate_teach.py --all --backend deepseek
```

Cost: ~$0.03-0.05. Quality is good — not Claude-tier on careful pedagogy,
but good enough that hand-review after is easy. **Test on a 3-tool sample
first** to verify output quality matches the project's standards.

**Path C (offline): wait for HailoBackend or real GPU.**

Pi 5 + Hailo NPU + Ollama is NOT a viable generation path today — Ollama
doesn't use the NPU. See `docs/HAILO_PHASE3_STATUS.md` for the 4 options
to unblock truly local generation (custom HailoBackend is the prize,
~1-3 day project).

---

## 🏗️ Phase 3b — `tools/merge_generated.py` (NOT YET BUILT)

After generation, we need a script that:

1. Loads `tool_registry.v2.json` (canonical) and `tool_registry.generated.json`
   (LLM output)
2. For each tool in generated, validates against schema
3. Shows a diff per tool: what's being added to each stub field
4. Asks for approve / skip / edit (interactive)
5. Merges approved entries back into v2.json
6. Bumps the tool's `tier` from 1 to 2 (or leaves at 1 if hand-edited)
7. Updates `generated_at` timestamp

Estimate: ~200 lines of Python. ~30 min to build once we have generated
output to merge. Build this RIGHT AFTER the first successful Path A or B run.

---

## 🔬 Open audit items (not blockers, but should be checked)

### Professor Engine doesn't read the registry's teach data yet

**Finding from this session's audit:** `src/core/professor_engine.py`
(commit `7a37052`) doesn't import or reference `tool_registry.json` or
`tool_registry.v2.json` at all. It uses cached response templates +
ConversationEngine + RAG. That means even after Phase 3 generation fills
in the 5 stub fields per tool, **Professor Engine won't automatically use
that data** in its responses.

This is **Phase 4b**: wire the v2 registry teach data into the Professor
Engine so when a student asks "explain that nmap output to me", the engine
pulls from the registry's `output_read` patterns, `opsec_notes`,
`sample_outputs`, etc.

Estimate: ~150 lines of changes in `professor_engine.py` + the cache
loader. Probably a half-session project.

### The registry's `tier` field is unused

Phase 2 added a `tier` field (1=hand-curated, 2=LLM-generated, 3=man-page
fallback). Phase 3b should set tier=2 on merged entries. Currently every
tool is tier=1 by default. Cosmetic until Phase 3 actually runs.

### `requirements.txt` audit for new deps

The `DeepSeekBackend` requires the `openai` Python library. We should
make sure `requirements-kali.txt` includes it, or `install.sh` installs
it via pipx. Quick check in next session.

---

## 🌱 Bigger items further out

### Phase 5 — Intent routing + UI Teach button
Hook "teach me X" / "explain this output" queries from the Phoenix UI
to `professor_engine.explain()`. UI work mostly.

### Phase 6 — Verification + smoke tests
Add `tests/test_registry_integrity.py` that loads the v2 registry,
samples 5 tools, calls professor_engine.explain on each, asserts
non-empty response. Wire into install.sh smoke test.

### Project rename
`ERR0RS-Ultimate` → `ERR0RS`. Branding only — repo name stays.
Separate cleanup session.

### Knowledge repo strategy
Pi has lots of untracked knowledge content (`knowledge/badusb/`, etc.)
that's NOT being committed. Decide: ship with the repo (huge clone),
submodules (current pattern), or RAG-index only.

---

## 📍 What's on disk RIGHT NOW (Pi 5 `/home/kali/ERR0RS-clean`)

| Asset | Status |
|---|---|
| `install.sh` (936 lines) | ✅ on GitHub |
| `src/tools/tool_registry.v2.json` (49 tools) | ✅ on GitHub |
| `src/tools/concepts.v2.json` (7 concepts) | ✅ on GitHub |
| `src/tools/tool_registry.schema.json` | ✅ on GitHub |
| `tools/generate_teach.py` (multi-backend, system-prompt-aware) | ✅ on GitHub |
| `tools/migrate_registry.py`, `validate_registry.py`, `README.md` | ✅ on GitHub |
| `docs/HAILO_PHASE3_STATUS.md` | ✅ on GitHub |
| `docs/SAMPLE_qwen7b_nmap_OUTPUT.json` | ✅ on GitHub |
| `src/ai/system_prompt.md` (the soul) | ✅ on GitHub (committed end of this session) |
| `docs/BACKEND_STRATEGY.md` | ✅ on GitHub (committed end of this session) |
| `.env.example` | ✅ on GitHub (committed end of this session) |
| Local `.env` with `OLLAMA_MODEL=qwen2.5-coder:7b` | ✅ on Pi only (gitignored) |
| `tools/merge_generated.py` | ❌ not yet built (Phase 3b) |
| Phase 4b registry-aware professor engine | ❌ not yet built |

---

## 🔐 Safety nets still in place

- Git tag `pre-phase123-2026-05-13` on `ERR0RS-clean`
- Git tag `pi-local-phase123-2026-05-13-FINAL`
- 11 GB filesystem snapshot at
  `/home/kali/ERR0RS-clean-BEFORE-PHASE123-20260513-002756` — **safe to
  delete now:** `rm -rf /home/kali/ERR0RS-clean-BEFORE-PHASE123-20260513-002756`
- 64 KB micro-snapshot at `/home/kali/ERR0RS-RECOVERY-SNAPSHOT-20260513-001923`

---

## 🤝 Picking up next time

Open a fresh chat with this file. Best opening move:

1. **Read `docs/BACKEND_STRATEGY.md`** to remember why the chain is
   Claude → DeepSeek → Ollama
2. **Pick Path A or B** above and run the first 3-tool sample
3. **Eyeball the quality** — does it match the standard in `src/ai/system_prompt.md`?
4. **If yes:** run full sweep, then build `tools/merge_generated.py`
5. **If no:** tune the prompt in `tools/generate_teach.py` and iterate

---

*State as of commit pushed end of 2026-05-14 backend-strategy session.*
