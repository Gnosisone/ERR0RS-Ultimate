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
- **Phase 3** ⏳ — LLM teach generator: fill `opsec_notes`, `sample_outputs`, `legal_notes`, `false_positives`, `mitre_attack` for all 49 tier-1 tools, then auto-generate tier-2 entries for the ~60 new tools install.sh now installs.
- **Phase 4** ⏳ — `professor_engine.explain()` — the single front door for "teach me X" queries.
- **Phase 5** ⏳ — intent routing + UI Teach button.
- **Phase 6** ⏳ — verification + smoke tests.

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
