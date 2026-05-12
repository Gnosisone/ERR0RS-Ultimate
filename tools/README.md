# `tools/` — ERR0RS Build & Maintenance Scripts

This directory holds **maintenance and build tooling** — not pen-testing tools.
For the pen-testing tools ERR0RS knows about, see `src/tools/tool_registry.v2.json`.

## What's here

| Script | Purpose |
|---|---|
| `migrate_registry.py` | Phase 2: merges `src/tools/tool_registry.json` (47 tools) + `src/core/teach_engine.py` LESSONS (23 entries) into the unified `tool_registry.v2.json` (49 tools) + `concepts.v2.json` (7 concepts). |
| `validate_registry.py` | Validates the v2 files against `src/tools/tool_registry.schema.json`. Used as a CI gate. Falls back to a hand-rolled validator if `jsonschema` is not installed. |

## Typical workflow

```bash
# Re-run the migration after editing any source file
python3 tools/migrate_registry.py            # dry-run (no writes)
python3 tools/migrate_registry.py --write    # commits the v2 files

# Validate after any manual edit of the v2 files
python3 tools/validate_registry.py
python3 tools/validate_registry.py --quiet   # CI mode: silent on success
```

## Phase plan (where this fits)

- **Phase 1** ✅ — install.sh full tool universe (apt + go + pip + github + c2 + KB repos)
- **Phase 2** ✅ — unified registry schema + migration of existing 47 tools
- **Phase 3** 🟡 — LLM teach generator BUILT but DEFERRED. The generator
  (`generate_teach.py`) is fully functional with both Ollama (local) and
  Anthropic (cloud) backends. It uses a structured prompt designed to
  produce beginner-accessible + bleeding-edge content (2025-2026
  tradecraft, modern EDR bypass, current cloud/AD chains).

  **Why deferred:** qwen2.5-coder:32b on the x86 dev VM is CPU-bound at
  ~6 hours per tool (proven by pre-warm benchmark). Full sweep of 49
  tools would take weeks of wall time. The plan is to defer execution
  until Pi 5 + Hailo-10H NPU hardware is online — that combination
  runs qwen at orders-of-magnitude faster, making local generation
  practical.

  **Ready-to-run command on Pi 5:**
  ```bash
  python3 tools/generate_teach.py --all --backend ollama
  ```
  Generator emits to `src/tools/tool_registry.generated.json` (separate
  file, NOT auto-merged into v2). After review, run
  `tools/merge_generated.py --write` (built in Phase 3b) to fold
  approved entries into the canonical registry.

  **Anthropic fallback** for build-time hand-curation is available right
  now via `--backend anthropic` if you set `ANTHROPIC_API_KEY` in `.env`.

- **Phase 4** ⏳ — `professor_engine.explain()` — single front door for
  "teach me X" queries. Can be built NOW against the existing 49-tool
  v2 registry, which already has deep hand-curated flag-level teach
  data + 7 concept entries (CIA, OWASP, MITRE, kill chain, etc.).
- **Phase 5** ⏳ — intent routing + UI Teach button.
- **Phase 6** ⏳ — verification + smoke tests.

## Generator backends — quality vs. speed reality

| Backend | Speed/tool | Quality | Cost | Locality |
|---|---|---|---|---|
| qwen2.5-coder:32b on Pi 5+Hailo | ~30-60s (projected) | excellent | $0 | fully local |
| qwen2.5-coder:32b on x86 CPU (this VM) | ~6 hours | excellent | $0 | fully local |
| llama3.2 (2GB) | ~30-60s | decent — needs retry on JSON | $0 | fully local |
| Claude Haiku 4.5 (Anthropic) | ~3-5s | great | ~$0.25/sweep | cloud |
| Claude Sonnet 4.6 (Anthropic) | ~10s | best | ~$2-3/sweep | cloud |

Whatever backend generates the data, ERR0RS itself ships and runs
fully offline at runtime — the JSON files are the deployable artifact.

## Schema authoring notes

When editing `src/tools/tool_registry.schema.json`:

- Bump the `version` field in any migration if the schema breaks backward compat.
- The schema's `risk` enum is intentionally generous (11 values) — the legacy
  data uses semantic risk labels like `safe`, `quiet`, `very_noisy`,
  `requires_root`, `slow`, `depends_on_script`, and `destructive`. Don't
  collapse these — they carry teaching value.
- The `mitre_attack.id` pattern enforces `Txxxx` or `Txxxx.yyy` MITRE
  ATT&CK technique IDs.
- All tool keys must match `[a-z][a-z0-9_-]*` — lowercase, no spaces.
