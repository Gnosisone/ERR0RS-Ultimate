#!/usr/bin/env python3
"""
ERR0RS — Tool Registry Migration (Phase 2)
══════════════════════════════════════════
Merges the two existing tool-knowledge sources into one canonical
unified registry conforming to tool_registry.schema.json:

  1. src/tools/tool_registry.json        — 47 tools, structured, deep flags
  2. src/core/teach_engine.py  LESSONS   — 23 entries: 14 tools (overlap) + 9 concepts

Output:
  src/tools/tool_registry.v2.json        — Unified registry
  src/tools/concepts.v2.json             — Concept entries (CIA, OWASP, MITRE, etc.)

The new schema introduces 6 new fields that are NOT in legacy sources:
  opsec_notes, sample_outputs, legal_notes, false_positives,
  mitre_attack, learning_path

These start as None/empty in the v2 file. Phase 3 (LLM generator) fills them.

Usage:
  python3 tools/migrate_registry.py           # dry-run, prints plan
  python3 tools/migrate_registry.py --write   # actually write v2 files
"""

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_REGISTRY = ROOT / "src" / "tools" / "tool_registry.json"
TEACH_ENGINE    = ROOT / "src" / "core" / "teach_engine.py"
OUT_REGISTRY    = ROOT / "src" / "tools" / "tool_registry.v2.json"
OUT_CONCEPTS    = ROOT / "src" / "tools" / "concepts.v2.json"

# ──────────────────────────────────────────────────────────────────────────────
# Category mapping. Legacy registry uses freeform strings; the schema uses an
# enum. Map any non-conforming legacy value here.
# ──────────────────────────────────────────────────────────────────────────────
CATEGORY_MAP = {
    "recon": "recon",
    "web": "web",
    "exploitation": "exploitation",
    "exploit": "exploitation",
    "post-exploit": "post-exploit",
    "post-exploitation": "post-exploit",
    "persistence": "persistence",
    "c2": "c2",
    "wireless": "wireless",
    "credentials": "credentials",
    "cracking": "credentials",
    "forensics": "forensics",
    "reverse": "reverse",
    "reverse-engineering": "reverse",
    "evasion": "evasion",
    "social": "social-engineering",
    "social-engineering": "social-engineering",
    "phishing": "social-engineering",
    "mobile": "mobile",
    "cloud": "cloud",
    "container": "container",
    "ad": "ad",
    "active-directory": "ad",
    "network": "network",
    "hardware": "hardware",
    "ids": "ids",
    "monitoring": "ids",
    "utility": "utility",
    "general": "utility",
}

# Entries in teach_engine.LESSONS that are concepts, not tools.
CONCEPT_KEYS = {
    "cia", "cis", "incident-response", "kill-chain",
    "mitre", "owasp", "threat-modeling",
}

CONCEPT_CATEGORIES = {
    "cia": "doctrine",
    "cis": "framework",
    "incident-response": "phase",
    "kill-chain": "model",
    "mitre": "framework",
    "owasp": "standard",
    "threat-modeling": "doctrine",
}


def load_legacy_registry() -> dict:
    with open(LEGACY_REGISTRY) as f:
        return json.load(f)


def load_lessons() -> dict:
    src = TEACH_ENGINE.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "LESSONS":
                    return ast.literal_eval(node.value)
    raise RuntimeError("Could not find LESSONS dict in teach_engine.py")


def normalize_category(cat: str) -> str:
    cat = (cat or "utility").lower().strip()
    return CATEGORY_MAP.get(cat, "utility")


def migrate_tool_entry(key: str, legacy: dict, lessons: dict) -> dict:
    canonical = key.lower()
    entry = {
        "display_name": legacy.get("name", canonical.title()),
        "aliases":      [canonical, legacy.get("name", "").lower()] if legacy.get("name") else [canonical],
        "binary":       legacy.get("binary", canonical),
        "category":     normalize_category(legacy.get("category", "utility")),
        "phases":       legacy.get("phases", []),
        "tier":         1,
        "risk":         legacy.get("risk", "moderate"),
        "authorization_required": legacy.get("authorization_required", True),

        "description":   legacy.get("description", ""),
        "teach_intro":   legacy.get("teach_intro", ""),

        "default_flags":   legacy.get("default_flags", []),
        "default_command": legacy.get("default_command", ""),

        "flags": {},

        "output_read":     [],
        "opsec_notes":     [],
        "sample_outputs":  [],
        "legal_notes":     [],
        "false_positives": [],
        "mitre_attack":    [],
        "learning_path":   {"prerequisites": [], "leads_to": []},
        "common_pitfalls": [],
        "related_tools":   legacy.get("related_tools", []),
        "next_steps":      legacy.get("next_steps", []),
        "references":      legacy.get("references", []),
    }

    for flag_name, flag_data in legacy.get("flags", {}).items():
        entry["flags"][flag_name] = {
            "label":     flag_data.get("label", flag_name),
            "desc":      flag_data.get("desc", ""),
            "example":   flag_data.get("example", ""),
            "teach":     flag_data.get("teach", flag_data.get("desc", "")),
            "risk":      flag_data.get("risk", "moderate"),
            "mechanism": "",
            "detection": "",
            "evasion":   "",
        }

    entry["aliases"] = sorted(set(filter(None, entry["aliases"])))

    # Layer LESSONS on top if there's an overlap
    if canonical in {k.lower() for k in lessons}:
        lesson_key = next(k for k in lessons if k.lower() == canonical)
        lesson = lessons[lesson_key]

        if "summary" in lesson:
            entry["teach_alt"] = lesson["summary"]

        if not entry["default_command"] and "typical" in lesson:
            entry["default_command"] = lesson["typical"]

        for read_line in lesson.get("read", []):
            parsed = False
            for sep in (" means ", " = ", " indicates ", " shows "):
                if sep in read_line:
                    pattern, meaning = read_line.split(sep, 1)
                    entry["output_read"].append({
                        "pattern": pattern.strip(),
                        "meaning": meaning.strip(),
                    })
                    parsed = True
                    break
            if not parsed:
                entry["output_read"].append({"pattern": "(general)", "meaning": read_line.strip()})

        for flag_name, flag_teach in lesson.get("flags", {}).items():
            if flag_name in entry["flags"]:
                existing = entry["flags"][flag_name].get("teach", "")
                if flag_teach and flag_teach not in existing:
                    entry["flags"][flag_name]["teach"] = (existing + "\n\n" + flag_teach).strip()
            else:
                entry["flags"][flag_name] = {
                    "label":     flag_name,
                    "desc":      "",
                    "example":   "",
                    "teach":     flag_teach,
                    "mechanism": "",
                    "detection": "",
                    "evasion":   "",
                    "risk":      "moderate",
                }

    return entry


def migrate_lessons_only_tool(key: str, lesson: dict) -> dict:
    """Tools in LESSONS but NOT registry (netcat, whatweb)."""
    canonical = key.lower()
    entry = {
        "display_name": key,
        "aliases":      [canonical, key],
        "binary":       canonical,
        "category":     "utility",
        "phases":       [],
        "tier":         1,
        "risk":         "moderate",
        "authorization_required": True,

        "description":   lesson.get("summary", "")[:160],
        "teach_intro":   lesson.get("summary", ""),

        "default_flags":   [],
        "default_command": lesson.get("typical", ""),

        "flags": {},
        "output_read":     [],
        "opsec_notes":     [],
        "sample_outputs":  [],
        "legal_notes":     [],
        "false_positives": [],
        "mitre_attack":    [],
        "learning_path":   {"prerequisites": [], "leads_to": []},
        "common_pitfalls": [],
        "related_tools":   [],
        "next_steps":      [],
        "references":      [],
    }

    for flag_name, flag_teach in lesson.get("flags", {}).items():
        entry["flags"][flag_name] = {
            "label":     flag_name,
            "desc":      "",
            "example":   "",
            "teach":     flag_teach,
            "mechanism": "",
            "detection": "",
            "evasion":   "",
            "risk":      "moderate",
        }

    for read_line in lesson.get("read", []):
        parsed = False
        for sep in (" means ", " = ", " indicates ", " shows "):
            if sep in read_line:
                pattern, meaning = read_line.split(sep, 1)
                entry["output_read"].append({"pattern": pattern.strip(), "meaning": meaning.strip()})
                parsed = True
                break
        if not parsed:
            entry["output_read"].append({"pattern": "(general)", "meaning": read_line.strip()})

    entry["aliases"] = sorted(set(filter(None, entry["aliases"])))
    return entry


def migrate_concept(key: str, lesson: dict) -> dict:
    canonical = key.lower()
    summary = lesson.get("summary", "")
    # Use everything before " — " as display_name; if no dash, just use the key uppercased
    if " — " in summary:
        display = summary.split(" — ")[0].strip()
    elif "—" in summary:
        display = summary.split("—")[0].strip()
    else:
        display = key.upper().replace("-", " ")

    entry = {
        "display_name": display,
        "aliases":      sorted(set(filter(None, [canonical, key.upper(), key.replace("-", " ").title()]))),
        "category":     CONCEPT_CATEGORIES.get(canonical, "framework"),
        "summary":      summary,
        "teach":        summary,
        "components":   [],
        "related":      [],
        "references":   [],
    }

    # Concept entries in LESSONS reuse the tool template — the `flags` field
    # is overloaded to mean "framework components". Pull from `flags` if no
    # dedicated component-list key is present.
    for component_key in ("pillars", "phases", "controls", "items",
                          "techniques", "risks", "tactics", "principles"):
        if component_key in lesson:
            val = lesson[component_key]
            if isinstance(val, list):
                entry["components"] = [str(x) for x in val]
            elif isinstance(val, dict):
                entry["components"] = [f"{k}: {v}" for k, v in val.items()]
            break

    # Fallback — if no dedicated key, use `flags` (which is what teach_engine
    # actually uses for concept components like OWASP A01-A10, CIA C/I/A, etc.)
    if not entry["components"] and "flags" in lesson:
        flags = lesson["flags"]
        if isinstance(flags, dict):
            entry["components"] = [f"{k}: {v}" for k, v in flags.items()]

    # Pull "read" lines into a separate field for concept-specific guidance.
    # We extend the schema in a minor way here: concepts get a `read` array.
    # (Validator allows additionalProperties via... wait, it doesn't. Skip
    # this for now — we can extend the schema in a follow-up if useful.)

    return entry


def main():
    write = "--write" in sys.argv

    print("=" * 70)
    print(" ERR0RS Registry Migration — Phase 2")
    print("=" * 70)

    legacy = load_legacy_registry()
    lessons = load_lessons()

    print(f"\n  legacy registry entries:    {len(legacy)}")
    print(f"  teach_engine LESSONS:       {len(lessons)}")
    print(f"  concept keys → concepts:    {len(CONCEPT_KEYS)}")

    tools = {}
    concepts = {}

    # 1. Migrate every legacy registry entry
    for key, data in legacy.items():
        tools[key.lower()] = migrate_tool_entry(key, data, lessons)

    # 2. Add tools that are in LESSONS but NOT in the legacy registry
    legacy_lower = {k.lower() for k in legacy}
    for key, data in lessons.items():
        if key.lower() in CONCEPT_KEYS:
            continue
        if key.lower() not in legacy_lower:
            print(f"  + adding from LESSONS only: {key}")
            tools[key.lower()] = migrate_lessons_only_tool(key, data)

    # 3. Build concepts dict
    for key, data in lessons.items():
        if key.lower() in CONCEPT_KEYS:
            concepts[key.lower()] = migrate_concept(key, data)

    out_registry = {
        "version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tools": tools,
    }
    out_concepts = {
        "version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "concepts": concepts,
    }

    print(f"\n  → unified tools: {len(tools)}")
    print(f"  → concepts:      {len(concepts)}")

    flag_counts = [len(t["flags"]) for t in tools.values()]
    if flag_counts:
        print(f"\n  flag coverage: min={min(flag_counts)}, max={max(flag_counts)}, "
              f"avg={sum(flag_counts) / len(flag_counts):.1f}")

    empty_intro = [k for k, t in tools.items() if not t["teach_intro"]]
    if empty_intro:
        print(f"  ⚠  tools missing teach_intro: {empty_intro}")
    else:
        print("  ✓ every tool has a teach_intro")

    print(f"\n  new fields stub status (Phase 3 will populate):")
    for field in ("opsec_notes", "sample_outputs", "legal_notes",
                  "false_positives", "mitre_attack"):
        filled = sum(1 for t in tools.values() if t.get(field))
        print(f"    {field:18s}  {filled:3d}/{len(tools)} filled")

    if write:
        OUT_REGISTRY.write_text(json.dumps(out_registry, indent=2, ensure_ascii=False))
        OUT_CONCEPTS.write_text(json.dumps(out_concepts, indent=2, ensure_ascii=False))
        print(f"\n  ✓ wrote {OUT_REGISTRY}")
        print(f"  ✓ wrote {OUT_CONCEPTS}")
    else:
        print(f"\n  (dry-run — pass --write to actually emit files)")


if __name__ == "__main__":
    main()
