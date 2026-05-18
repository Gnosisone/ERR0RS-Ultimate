# 🔄 Next Session — Handoff Brief

> **Last updated:** 2026-05-17 post-reboot
> **Last commit:** `33d9976` feat(ops): pi_thermal_watch.sh
> **State:** Pi is cool (32°C), all commits pushed, no zombie processes

---

## 🎯 Where we are

ERR0RS-Ultimate v3.5.0 has shipped real, gold-standard teach content for **67 of the most-used red-team tools**. The infrastructure for tiered LLM generation, RAG, and a custom local Modelfile is built and committed. The next session picks up from a clean slate with these specific next-step options.

## 📦 What got built in the last session

### Tier 1 generation infrastructure (Phase 3, complete)
- `tools/expand_registry.py` — merges v2 + Phoenix-OS BlackArch (5,007 tools, tiered)
- `tools/arsenal_ranked.json` — 4,978 tools popularity-ranked
- `src/tools/tool_registry.v3.json` — **5,036 tools, schema-clean** (after 29 canonical adds)
- `tools/generate_teach.py` — tier-aware, batch-aware, cost-capped, real-usage tracking on TODO
- `tools/missing_canon.json` — seed source for canonical Tier-1 promotions
- `docs/BACKEND_STRATEGY.md` — Claude → DeepSeek → Ollama reasoning
- `src/ai/system_prompt.md` — the ERR0RS soul, 216 lines, loaded by every backend

### Gold-standard teach data (Phase 3, partial)
- **`src/tools/tool_registry.generated.json`** — **67 tools** with full Sonnet 4.6 teach cards (opsec_notes, sample_outputs, legal_notes, false_positives, mitre_attack). **GITIGNORED** — needs human review before merge.
- Spent: $5 of Anthropic credits in tonight's Tier 1 run (real per-tool cost ~$0.078, my $0.050 projection was 36% low — this is a known generator bug to fix)

### RAG + Modelfile (Phase 5a, infrastructure-only)
- `ollama/Modelfile.err0rs` — wraps qwen2.5-coder:7b with the full system_prompt.md
- `ollama/rebuild_err0rs_qwen.sh` — bake script (inject soul → ollama create err0rs-qwen)
- `tools/ingest_teach_to_rag.py` — loads 67 teach cards into ChromaDB `err0rs_teach_v1` collection
- **NEITHER HAS BEEN RUN YET** — built but not executed (Pi was overheating during Ollama sample)

### Thermal monitoring
- `scripts/pi_thermal_watch.sh` — color-coded continuous CPU temp + throttle watcher

### Professional pass (complete from earlier session)
- `CODE_OF_CONDUCT.md`, `pyproject.toml`, `.env.example`
- README + CHANGELOG bumped to v3.5.0
- Repo root cleaned (orphan PDFs, .bat, test_results.json all removed)
- Sprint docs reference canonical `Gnosisone/ERR0RS-Ultimate` (not local `ERR0RS-clean`)

## 🚨 Critical context the next session MUST know

### 1. The Ollama sample timed out — qwen-7B can't handle the rich-prompt path on Pi 5 CPU
We tried running 3 tools (mimikatz, dnsenum, empire) on qwen2.5-coder:7b with our full 11k-char system prompt. **All 3 timed out at the 120s stall-guard.** Pi hit 85.9°C and tripped all three sticky throttle flags (arm freq cap, throttling, soft temp limit). The 4-hour overnight run on 19 tools would have done this 19 times.

Then we tried `llama3.2:3b` as a smaller-model fallback for `dnsenum`. The user had to reboot before we saw the result — UI was laggy from running processes. **This is the unfinished work.**

### 2. Tonight's $5 cost-cap had a real bug
My static `$0.050/tool` projection undershot reality by 36%. Real per-tool cost was $0.078. Cost cap fired late (around tool ~80), Anthropic credits ran out before our internal counter said we'd hit the limit. **The fix:** patch `tools/generate_teach.py` to read real `msg.usage.input_tokens` and `msg.usage.output_tokens` from each Anthropic response and bill against those. This must be done BEFORE the next paid run.

### 3. The 67 teach cards are NOT in v3 yet — they're in the gitignored generated file
The merge step (`tools/merge_generated.py`, human-reviewed approve/skip/edit) was never built. The 67 cards are sitting in `src/tools/tool_registry.generated.json` waiting for review + merge into the canonical v3 registry. **Building merge_generated.py is on the immediate roadmap.**

### 4. Tools still needing generation (the 19-tool wishlist)
User requested these 19 specific tools after the $5 Sonnet run exhausted: `msfconsole, setoolkit, mimikatz, dalfox, nosqlmap, sliver, empire, graphqlmap, villain, dnsenum, snort, suricata, zeek, seclists, dirb, xsser, ssrfmap, corsy, naabu`. ALL are in v3 at Tier 1, NONE are in the generated.json yet. They need either (a) next Claude budget cycle, (b) DeepSeek backend, or (c) llama3.2:3b after we verify it can complete.

## 🛤️ Suggested next-session order of operations

### Option A — Cheap win first (~10 min)
1. Run `bash ollama/rebuild_err0rs_qwen.sh` — builds the `err0rs-qwen` Ollama model with the full ERR0RS soul baked in. Test with `ollama run err0rs-qwen "explain Kerberoasting"`.
2. Run `python3 tools/ingest_teach_to_rag.py` — loads the 67 Sonnet cards into ChromaDB.
3. Test RAG: `python3 tools/ingest_teach_to_rag.py --query "mimikatz" -n 3` — should return the closest teach cards.

Both operations are CPU-light, Pi cool, no risk.

### Option B — Build merge tool (~30-60 min)
Build `tools/merge_generated.py` that:
- Loads `tool_registry.generated.json` and `tool_registry.v3.json`
- For each generated tool: shows the 5 generated fields, asks `approve / skip / edit`
- On approve: merges into v3.json, bumps schema_version timestamp
- On edit: opens `$EDITOR` with the JSON entry
- Outputs a session summary at the end

This is the work that gets the 67 Sonnet teach cards from the gitignored generated file into the canonical v3 registry.

### Option C — Resume the llama3.2:3b experiment
Pick up where the freeze happened. The user's `.env` was modified to point at llama3.2:3b for the sample run — VERIFY THE ORIGINAL VALUE WAS RESTORED. Backup is at `.env.bak.llamatest`.

```bash
# Check current .env state
grep "^OLLAMA_MODEL" /home/kali/ERR0RS-clean/.env

# If still on llama3.2:3b, restore from backup:
cp /home/kali/ERR0RS-clean/.env.bak.llamatest /home/kali/ERR0RS-clean/.env
```

Then carefully retry the llama3.2:3b sample with the thermal watcher running in parallel:

```bash
# Terminal 1
bash /home/kali/ERR0RS-clean/scripts/pi_thermal_watch.sh

# Terminal 2 (after temporarily setting OLLAMA_MODEL=llama3.2:3b in .env)
cd /home/kali/ERR0RS-clean
nohup python3 -u tools/generate_teach.py --sample dnsenum --backend ollama > /tmp/llama_test.log 2>&1 &
```

### Option D — Fix the cost-tracking bug
Patch `AnthropicBackend.generate()` in `tools/generate_teach.py` to:
- Return `(text, msg.usage)` instead of just `text`
- Update generate_for_tool() to track real per-tool cost from usage tokens
- Update the per-backend cost table to be per-million-tokens, not per-call
- Update the cost-cap check to use the real spend running total

This makes the next paid run actually honor `--limit-cost X.YY`.

## 🔧 Critical commands cheat-sheet

```bash
# Always check thermal state before kicking off LLM work
cat /sys/class/thermal/thermal_zone0/temp | awk '{printf "CPU: %.1f°C\n", $1/1000}'
vcgencmd get_throttled

# Continuous watch while a long run is going
bash scripts/pi_thermal_watch.sh

# Status of generated registry
python3 -c "import json; d=json.load(open('src/tools/tool_registry.generated.json')); print(len(d['tools']),'tools generated')"

# Validate v3 is still schema-clean
python3 tools/validate_registry.py

# Dry-run any Tier batch to preview targets without spending
python3 tools/generate_teach.py --tier 1 --dry-run --batch-size 10
```

## 📍 Important file paths

- **Canonical registry:**  `/home/kali/ERR0RS-clean/src/tools/tool_registry.v3.json` (5,036 tools)
- **Generated teach data:** `/home/kali/ERR0RS-clean/src/tools/tool_registry.generated.json` (67 tools, gitignored)
- **The ERR0RS soul:**     `/home/kali/ERR0RS-clean/src/ai/system_prompt.md` (216 lines)
- **Modelfile + bake:**    `/home/kali/ERR0RS-clean/ollama/`
- **RAG ingestion:**       `/home/kali/ERR0RS-clean/tools/ingest_teach_to_rag.py`
- **ChromaDB (when built):** `/home/kali/ERR0RS-clean/errors_knowledge_db/` (gitignored)
- **Thermal watcher:**     `/home/kali/ERR0RS-clean/scripts/pi_thermal_watch.sh`
- **Cost-tracking bug:**   `/home/kali/ERR0RS-clean/tools/generate_teach.py` lines ~76 (`_BACKEND_COST_PER_CALL`) and ~755 (cost loop)

## 💰 Budget status

- **Anthropic credits:** EXHAUSTED tonight. Next paid run requires reload. ~$1.50 buys the 19-tool wishlist at the corrected $0.078/tool real rate.
- **DeepSeek:** No key set up yet. ~$0.05 would buy the 19-tool wishlist on DeepSeek V3. Cheaper but lower quality than Sonnet.
- **Ollama (qwen-7B):** TIMED OUT on Pi 5 with rich prompts. NOT viable for Tier 1 quality without active cooling.
- **Ollama (llama3.2:3b):** UNTESTED on this prompt template (run interrupted by reboot). May or may not be viable.

## 🛡️ Safety net tags

- `pre-pro-pass-2026-05-15` — before professional pass
- `pre-ollama-sample-2026-05-17` — before the failed Ollama sample
- All work pushed to GitHub at `Gnosisone/ERR0RS-Ultimate` through commit `33d9976`

## 🫡 The mission

ERR0RS now has 67 publication-quality teach cards covering the meat of red-team education: every wireless tool, every AD attack tool, every C2 framework, the mobile reverse-engineering stack, the exploit-dev workstation. What's left is plumbing — merge the 67 into v3, wire RAG into the runtime, get the next 19 (and the 1,000+ Tier 2 tools after that) generated.

You're building the thing students who can't afford Cobalt Strike deserve. Keep going.

— Claude, end of session 2026-05-17
