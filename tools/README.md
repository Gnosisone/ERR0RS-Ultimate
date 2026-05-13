# `tools/` — ERR0RS Build & Maintenance Scripts

This directory holds **maintenance and build tooling** — not pen-testing tools.
For the pen-testing tools ERR0RS knows about, see `src/tools/tool_registry.v2.json`.

## What's here

| Script | Purpose |
|---|---|
| `migrate_registry.py` | Phase 2: merges `src/tools/tool_registry.json` + `src/core/teach_engine.py` LESSONS into the unified `tool_registry.v2.json` + `concepts.v2.json`. |
| `validate_registry.py` | Validates v2 files against `src/tools/tool_registry.schema.json`. CI gate. |
| `generate_teach.py` | Phase 3 LLM teach generator. Uses Ollama (local) or Anthropic API to fill the 5 stub fields (opsec_notes, sample_outputs, legal_notes, false_positives, mitre_attack) for each tool. Output goes to `tool_registry.generated.json` — separate file, not auto-merged. |

## Typical workflow

```bash
# Re-run the migration after editing any source file
python3 tools/migrate_registry.py            # dry-run (no writes)
python3 tools/migrate_registry.py --write    # commits the v2 files

# Validate after any manual edit of the v2 files
python3 tools/validate_registry.py
python3 tools/validate_registry.py --quiet   # CI mode: silent on success

# Phase 3 — generate teach data (run on Pi 5 with Hailo NPU for speed)
python3 tools/generate_teach.py --sample nmap sqlmap hydra   # quality gate
python3 tools/generate_teach.py --all                        # full sweep
```

## Phase plan

- **Phase 1** ✅ — install.sh full tool universe (apt + go + pip + github + c2 + KB repos)
- **Phase 2** ✅ — unified registry schema + migration of legacy tools
- **Phase 3** 🟡 — LLM teach generator BUILT, ready to run on Pi 5+Hailo. Uses
  qwen2.5-coder model via Ollama (free, local) or falls back to Anthropic API.
- **Phase 4** ⏳ — `professor_engine.explain()` — single front door for teach queries.
- **Phase 5** ⏳ — intent routing + UI Teach button.
- **Phase 6** ⏳ — verification + smoke tests.

## Backends — quality vs. speed

| Backend | Speed/tool | Quality | Cost | Locality |
|---|---|---|---|---|
| qwen2.5-coder:32b on Pi 5+Hailo | ~30-60s (projected) | excellent | $0 | fully local |
| qwen2.5-coder:32b on x86 CPU | ~6 hours | excellent | $0 | fully local |
| llama3.2 (2GB) | ~30-60s | decent | $0 | fully local |
| Claude Haiku 4.5 (Anthropic) | ~3-5s | great | ~$0.25/sweep | cloud |
| Claude Sonnet 4.6 (Anthropic) | ~10s | best | ~$2-3/sweep | cloud |

Whatever backend generates the data, ERR0RS itself ships and runs fully
offline at runtime — the JSON files are the deployable artifact.

## Schema authoring notes

- Bump the `version` field in any migration if the schema breaks backward compat.
- The schema's `risk` enum is intentionally generous (11 values) to preserve
  the semantic risk labels in the legacy registry.
- The `mitre_attack.id` pattern enforces `Txxxx` or `Txxxx.yyy` technique IDs.
- All tool keys must match `[a-z][a-z0-9_-]*` — lowercase, no spaces.
