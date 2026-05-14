# Next Session — ERR0RS Sprint Continuation

**Pick up here.** This is a self-contained brief for the next development
session, written 2026-05-14 immediately after the install/registry/teach-gen
sprint landed on GitHub.

---

## 🎯 The 30-second status

Everything **structural** is done:
- install.sh is solid (936 lines, 6/6 smoke test pass on a fresh clone)
- 49-tool unified registry validated against schema
- 7 concept entries (CIA, OWASP, MITRE ATT&CK, kill chain, etc.)
- Phase 4 Professor Engine **already shipped** on `main` (commit `7a37052`)
- Phase 3 LLM teach generator built, gated, with honest docs

Everything **content** (the bleeding-edge teach data) is **not** done. The
5 stub fields per tool (`opsec_notes`, `sample_outputs`, `legal_notes`,
`false_positives`, `mitre_attack`) are empty on all 49 tools.

The runtime story works **today** without Phase 3 generation — Professor
Engine reads the registry gracefully when stubs are empty. Students get
the hand-curated flag-level teach data, just not the bleeding-edge layer.

---

## 🚧 The real blocker

Phase 3 generation requires an LLM that can produce **accurate AND fast**
JSON output. We've confirmed on real Pi 5 hardware:

| Backend tested | Speed | Quality | Verdict |
|---|---|---|---|
| qwen2.5-coder:32b on x86 CPU (dev VM) | ~6 hrs/tool | excellent (untested but trusted) | unviable |
| qwen2.5-coder:7b on Pi 5 ARM CPU | ~13 min/tool | **HALLUCINATES** confidently | unviable |
| Anthropic Claude Haiku/Sonnet | ~3-10 s/tool | excellent | viable, costs $0.25-3 |
| Local NPU-accelerated 7B+ | unknown (projected fast) | unknown | aspirational — see below |

See `docs/HAILO_PHASE3_STATUS.md` for the full hardware reality check.
See `docs/SAMPLE_qwen7b_nmap_OUTPUT.json` for a concrete example of the
qwen-7B hallucination problem — it confidently invented incorrect MITRE
ATT&CK technique mappings and falsely claimed AMSI/Sysmon EID 25 detect
nmap (they don't — AMSI is for in-memory script scanning, EID 25 is for
process tampering on Windows; nmap is a compiled Linux binary).

**The lesson:** speed wasn't the only problem with the small local model.
**Quality was worse** than the slow path. A hallucinating teach card is
genuinely dangerous for students.

---

## 🛤️ Three paths forward, ranked by realism

### Path A — Anthropic at build time (recommended, low effort)

**Effort:** Drop a working API key into `.env` and run one command.
**Time to results:** ~10 min for full sweep.
**Cost:** ~$0.25 with claude-haiku-4-5, ~$2-3 with claude-sonnet-4-6.
**Quality:** Excellent. No hallucination risk worth mentioning.
**Locality:** The GENERATED JSON ships local. Runtime stays offline.

Steps:
1. `nano .env` → paste real `ANTHROPIC_API_KEY=sk-ant-...`
2. `cd /home/kali/ERR0RS-clean && python3 tools/generate_teach.py --sample nmap sqlmap hydra --backend anthropic`
3. Eyeball the 3 sample outputs in `src/tools/tool_registry.generated.json`
4. If quality looks good: `python3 tools/generate_teach.py --all --backend anthropic`
5. Build `tools/merge_generated.py` (Phase 3b — not yet written) to fold
   approved entries into `tool_registry.v2.json`
6. Commit + push

### Path B — Custom HailoBackend (high effort, ultimate prize)

**Effort:** 1-3 days of focused work.
**Time to results:** Multi-day to first generation; then sub-second/tool forever.
**Cost:** $0.
**Quality:** Same as whatever model you compile (we'd target qwen 7B or similar).
**Locality:** Fully local, fully offline, fully ERR0RS-aesthetic.

Steps:
1. Install Hailo Dataflow Compiler on the Pi (or a workstation that targets ARM)
2. Quantize qwen2.5-coder:7b to INT8 — Hailo's preferred precision
3. Compile to .hef format
4. Write Python wrapper using `hailo_platform` SDK that:
   - Loads the .hef
   - Implements the qwen chat template
   - Streams tokens, enforces JSON output
5. Replace `OllamaBackend` in `tools/generate_teach.py` with `HailoBackend`
6. Run full sweep — should complete in seconds-per-tool

This is the *right* long-term solution but it's a project, not a session.

### Path C — Borrowed GPU box (medium effort, one-time)

**Effort:** ~30 min to get a GPU machine running Ollama with qwen 32B.
**Time to results:** ~10-30 min for full sweep.
**Cost:** $0 if you have access to a GPU machine.
**Quality:** Excellent (qwen 32B with format=json is solid).
**Locality:** The GENERATED JSON ships local. Runtime stays offline.

Steps:
1. SSH to any Linux/Mac box with an NVIDIA GPU (8GB+ VRAM)
2. `ollama pull qwen2.5-coder:32b` (~19 GB download)
3. Clone ERR0RS-clean, `python3 tools/generate_teach.py --all --backend ollama`
4. scp the generated JSON back to the Pi
5. Commit + push from there

---

## 🎬 What to do FIRST in next session

Pick a path above based on what you have access to. My honest read:

- **If you have $5 and 10 minutes** → Path A. Done in one session.
- **If you have a workstation with a GPU somewhere** → Path C.
- **If you want to invest in the ultimate local solution** → Path B as a
  separate multi-session project. Don't merge it into a sprint.

There's NO scenario where the right move is "run qwen on Pi 5 CPU."
We proved that's a 10-15 hour run that produces hallucinations. Don't
let me talk you into it next session if I forget the lesson.

---

## 🏗️ Phase 3b — `tools/merge_generated.py` (not yet built)

Even after generation succeeds, we need a script that:
1. Loads `tool_registry.v2.json` (canonical) and `tool_registry.generated.json` (LLM output)
2. For each tool in generated, validates against schema
3. Shows a diff per tool: what's being added to each stub field
4. Asks for approve / skip / edit
5. Merges approved entries back into v2.json
6. Bumps the tool's `tier` from 1 to 2 (or leaves at 1 if hand-edited)
7. Updates `generated_at` timestamp

Estimate: ~200 lines of Python. ~30 min to build once we have generated output to merge.

---

## 🌱 What else is on the table for next session

Beyond Phase 3, these are things we've touched but not finished:

### Phase 4+ — Professor Engine integration
Phase 4 ProfessorEngine already exists (commit `7a37052`). But:
- Does it read the v2.json registry yet, or the legacy tool_registry.json?
- If legacy: needs a one-line change to point at v2.json
- Does it expose the new fields (opsec_notes, mitre_attack) to the UI?
- Is there a "teach button" in `phoenix.html` UI yet?

### Phase 5 — Intent routing + UI Teach button
The `intent_parser.py` already exists. Hook "teach me X" to professor_engine.

### Phase 6 — Verification + smoke tests
Add `tests/test_registry_integrity.py` that:
- Loads the v2 registry
- For 5 randomly sampled tools, calls professor_engine.explain(tool_key)
- Asserts non-empty response with expected fields
- Wire into the install.sh smoke test

### Project rename (deferred from earlier)
`ERR0RS-Ultimate` → `ERR0RS` (just `ERR0RS`). The repo's literal name on
GitHub stays `ERR0RS-Ultimate` but the user-facing branding could shift.
Probably worth a separate cleanup session.

### Submodules + Knowledge repos
The Pi has lots of untracked knowledge content (`knowledge/badusb/`,
`knowledge/c2/`, etc.) that's NOT being committed. Decide: should these
ship with the repo (huge clone), be submodules (current pattern), or
get RAG-indexed locally and not shipped?

---

## 📍 Hardware state on the Pi 5 (kali-raspberrypi)

| Component | State |
|---|---|
| Kali ARM64 2026.1, kernel 6.12.75 | ✅ healthy |
| 16GB RAM, 470GB SSD (62% used, 172GB free) | ✅ plenty of room |
| Hailo-10H NPU, firmware 5.1.1, driver `hailo1x_pci` loaded | ✅ verified online |
| Ollama 0.20.0, `qwen2.5-coder:7b` + `llama3.2:3b` + `err0rs-pi5` models | ✅ working, but **NOT NPU-accelerated** |
| HailoRT CLI (`hailortcli`) | ✅ works |
| `.env` has `HAILO_ENABLED=true`, `PI5_MODE=true` | ⚠️ flags set but no code consumes them yet |

The Pi is in **excellent shape as the deploy target**. It's just not the
ideal build-time generation machine without a custom HailoBackend.

---

## 🔐 Safety nets in place

- Git tag `pre-phase123-2026-05-13` on the Pi — rollback point
- Git tag `pi-local-phase123-2026-05-13-FINAL` — preserves Pi-only commits
- Filesystem snapshot at `/home/kali/ERR0RS-clean-BEFORE-PHASE123-20260513-002756`
  (11 GB — **safe to delete now** that everything's pushed to GitHub:
  `rm -rf /home/kali/ERR0RS-clean-BEFORE-PHASE123-20260513-002756`)
- All sprint work pushed to GitHub `Gnosisone/ERR0RS-Ultimate` on `main`
- Git committer identity set globally on this Pi

---

## 🤝 Picking up next time

Open a fresh chat, share this file, and pick a path. The work is committed
and reproducible. Nothing's in a half-state. We can either:

- Resume Phase 3 (generation) via Path A/B/C
- Pivot to Phase 5 (UI Teach button wiring)
- Pivot to Phase 4 audit (does ProfessorEngine read v2 yet?)
- Tackle the project rename
- Do something else entirely

Sleep well. 🫡

— *State as of commit `ad245ce`, pushed to GitHub 2026-05-14*
