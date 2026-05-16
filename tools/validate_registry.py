#!/usr/bin/env python3
"""
ERR0RS — Tool Registry Validator (Phase 2)
══════════════════════════════════════════
Validates tool_registry.v2.json and concepts.v2.json against
tool_registry.schema.json. Used as a CI gate to make sure no entry
slips through with a malformed shape.

Falls back to a hand-rolled validator if `jsonschema` isn't installed
(it's a common case on minimal Kali boxes that haven't pip-installed it).

Usage:
  python3 tools/validate_registry.py
  python3 tools/validate_registry.py --quiet   # only output on failure
"""

import json
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA   = ROOT / "src" / "tools" / "tool_registry.schema.json"

# Default to v3 (full arsenal) if present, fall back to v2.
# Override with: --registry path/to/file.json
if "--registry" in sys.argv:
    idx = sys.argv.index("--registry")
    REGISTRY = Path(sys.argv[idx + 1])
    del sys.argv[idx:idx + 2]
elif (ROOT / "src" / "tools" / "tool_registry.v3.json").exists():
    REGISTRY = ROOT / "src" / "tools" / "tool_registry.v3.json"
else:
    REGISTRY = ROOT / "src" / "tools" / "tool_registry.v2.json"
CONCEPTS = ROOT / "src" / "tools" / "concepts.v2.json"

QUIET = "--quiet" in sys.argv


def vprint(*args, **kwargs):
    if not QUIET:
        print(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Try real jsonschema validation first
# ──────────────────────────────────────────────────────────────────────────────
def try_jsonschema():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        return None

    from jsonschema import Draft202012Validator
    schema = json.load(open(SCHEMA))
    registry = json.load(open(REGISTRY))

    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(registry))
    return errors


# ──────────────────────────────────────────────────────────────────────────────
# Fallback: hand-rolled validator for the fields we care most about
# ──────────────────────────────────────────────────────────────────────────────
VALID_CATEGORIES = {
    "recon", "web", "exploitation", "post-exploit", "persistence",
    "c2", "wireless", "credentials", "forensics", "reverse",
    "evasion", "social-engineering", "mobile", "cloud", "container",
    "ad", "network", "hardware", "ids", "utility"
}
VALID_RISK = {"stealthy", "moderate", "noisy", "loud", "safe", "quiet",
              "very_noisy", "requires_root", "slow", "depends_on_script",
              "destructive"}
MITRE_PATTERN = re.compile(r"^T[0-9]{4}(\.[0-9]{3})?$")
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def hand_rolled_validate(registry: dict) -> list:
    """Returns a list of error strings, empty if valid."""
    errors = []

    if "version" not in registry:
        errors.append("missing top-level 'version'")
    if "tools" not in registry:
        errors.append("missing top-level 'tools'")
        return errors

    for tool_key, tool in registry["tools"].items():
        prefix = f"tools.{tool_key}"

        if not KEY_PATTERN.match(tool_key):
            errors.append(f"{prefix}: key must match [a-z][a-z0-9_-]*")

        for required in ("display_name", "binary", "category", "tier",
                         "description", "teach_intro"):
            if required not in tool:
                errors.append(f"{prefix}: missing required field '{required}'")

        if tool.get("category") and tool["category"] not in VALID_CATEGORIES:
            errors.append(f"{prefix}.category: '{tool['category']}' not in valid set")

        if tool.get("tier") not in (1, 2, 3, 4):
            errors.append(f"{prefix}.tier: must be 1, 2, 3, or 4 (got {tool.get('tier')!r})")

        if tool.get("risk") and tool["risk"] not in VALID_RISK:
            errors.append(f"{prefix}.risk: '{tool['risk']}' not in valid set")

        # Validate MITRE entries if present
        for mitre in tool.get("mitre_attack", []):
            if "id" not in mitre or "name" not in mitre:
                errors.append(f"{prefix}.mitre_attack: entry missing id or name")
            elif not MITRE_PATTERN.match(mitre.get("id", "")):
                errors.append(f"{prefix}.mitre_attack: id '{mitre['id']}' "
                              f"must match Txxxx or Txxxx.yyy")

        # Validate flags
        for flag_key, flag in tool.get("flags", {}).items():
            fprefix = f"{prefix}.flags.{flag_key}"
            if "label" not in flag:
                errors.append(f"{fprefix}: missing 'label'")
            if "teach" not in flag:
                errors.append(f"{fprefix}: missing 'teach'")
            if flag.get("risk") and flag["risk"] not in VALID_RISK:
                errors.append(f"{fprefix}.risk: '{flag['risk']}' not in valid set")

        # Validate output_read entries
        for i, item in enumerate(tool.get("output_read", [])):
            if "pattern" not in item or "meaning" not in item:
                errors.append(f"{prefix}.output_read[{i}]: missing pattern or meaning")

        # Validate sample_outputs entries
        for i, item in enumerate(tool.get("sample_outputs", [])):
            for req in ("scenario", "output", "explanation"):
                if req not in item:
                    errors.append(f"{prefix}.sample_outputs[{i}]: missing '{req}'")

        # Validate next_steps entries
        for i, item in enumerate(tool.get("next_steps", [])):
            for req in ("if", "suggest"):
                if req not in item:
                    errors.append(f"{prefix}.next_steps[{i}]: missing '{req}'")

    return errors


def main():
    if not REGISTRY.exists():
        print(f"✗ {REGISTRY} not found — run tools/migrate_registry.py --write first")
        sys.exit(2)

    vprint(f"  Schema:   {SCHEMA}")
    vprint(f"  Registry: {REGISTRY}")
    vprint(f"  Concepts: {CONCEPTS}\n")

    js_errors = try_jsonschema()

    if js_errors is None:
        vprint("  (jsonschema package not installed — using hand-rolled validator)")
        registry = json.load(open(REGISTRY))
        errors = hand_rolled_validate(registry)
    else:
        errors = [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
                  for e in js_errors]

    if errors:
        print(f"  ✗ {len(errors)} validation errors:\n")
        for e in errors:
            print(f"    {e}")
        sys.exit(1)
    else:
        registry = json.load(open(REGISTRY))
        tool_count = len(registry.get("tools", {}))
        vprint(f"\n  ✓ {tool_count} tools validated, schema clean")

    # Also validate concepts file if it exists
    if CONCEPTS.exists():
        concepts_data = json.load(open(CONCEPTS))
        concept_count = len(concepts_data.get("concepts", {}))
        vprint(f"  ✓ {concept_count} concepts present")


if __name__ == "__main__":
    main()
