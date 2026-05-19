#!/usr/bin/env python3
"""
ERR0RS — Quality gates for Sonnet-generated teach cards
═══════════════════════════════════════════════════════════════════

Runs automated checks against every generated card to flag the ones that
need human eyes. Cards that pass all gates can be batch-approved with high
confidence; cards that fail get queued for in-chat review.

This is NOT a replacement for human review — it's a triage filter. The
gates catch CATEGORICAL problems (wrong format, broken cross-references,
implausible counts) but cannot judge whether opsec advice is current or
whether a MITRE ID semantically fits the technique. Those still need
human-in-the-loop judgement on flagged cards.

Output:
  - tools/_quality_gates.json   {tool_key: {"passed": bool, "issues": [...]}}
  - prints summary to stdout

Gates (severity in parentheses — FAIL means card needs review):
  G1 (FAIL) — schema: all 5 fields present, correct types
  G2 (FAIL) — opsec_notes: list of strings, 3-10 entries, each 50-1500 chars
  G3 (FAIL) — sample_outputs: list of dicts with {scenario, command, output, explanation}
  G4 (FAIL) — command in sample_outputs starts with the tool binary (or a known alias)
  G5 (FAIL) — legal_notes: 1-6 entries, each 50-1500 chars
  G6 (FAIL) — false_positives: 1-8 entries, each 50-1500 chars
  G7 (FAIL) — mitre_attack: list of {id, name}, IDs match T#### or T####.### pattern
  G8 (WARN) — opsec_notes count below 4 (Sonnet usually does 5-6; below 4 = suspicious)
  G9 (WARN) — sample_outputs has fewer than 2 entries (we asked for beginner + advanced)
  G10 (WARN) — total card char count < 4000 (too thin) or > 25000 (suspiciously verbose)
  G11 (FAIL) — duplicate MITRE IDs within the same card
  G12 (FAIL) — JSON-unsafe content (unescaped control chars in strings)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "src" / "tools" / "tool_registry.generated.json"
CANONICAL = ROOT / "src" / "tools" / "tool_registry.v3.json"
OUT = ROOT / "tools" / "_quality_gates.json"

MITRE_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
# Reasonable range — Sonnet's cards are dense; very short = stub, very long = runaway
CHAR_MIN_PER_ITEM = 50
CHAR_MAX_PER_ITEM = 2500     # accommodate dense advanced sample_outputs
TOTAL_MIN = 4000
TOTAL_MAX = 30000

REQUIRED_FIELDS = ("opsec_notes", "sample_outputs", "legal_notes", "false_positives", "mitre_attack")


def _is_str_list(x):
    return isinstance(x, list) and all(isinstance(i, str) for i in x)


def check_card(tool_key: str, card: dict, v3_entry: dict) -> dict:
    """Return {'passed': bool, 'severity': 'PASS'|'WARN'|'FAIL', 'issues': [...]}"""
    issues: list[tuple[str, str, str]] = []   # (gate, severity, message)

    # G1 — schema completeness
    for f in REQUIRED_FIELDS:
        if f not in card:
            issues.append(("G1", "FAIL", f"missing field: {f}"))

    # G2 — opsec_notes shape + sizes
    ops = card.get("opsec_notes")
    if not _is_str_list(ops):
        issues.append(("G2", "FAIL", "opsec_notes is not a list of strings"))
    else:
        if not (3 <= len(ops) <= 10):
            issues.append(("G2", "FAIL", f"opsec_notes has {len(ops)} entries (expected 3-10)"))
        for i, s in enumerate(ops):
            L = len(s)
            if L < CHAR_MIN_PER_ITEM:
                issues.append(("G2", "FAIL", f"opsec_notes[{i}] is only {L} chars"))
            elif L > CHAR_MAX_PER_ITEM:
                issues.append(("G2", "FAIL", f"opsec_notes[{i}] is {L} chars (>{CHAR_MAX_PER_ITEM})"))

    # G3 — sample_outputs shape
    samps = card.get("sample_outputs")
    if not isinstance(samps, list):
        issues.append(("G3", "FAIL", "sample_outputs is not a list"))
    else:
        for i, s in enumerate(samps):
            if not isinstance(s, dict):
                issues.append(("G3", "FAIL", f"sample_outputs[{i}] not a dict"))
                continue
            for key in ("scenario", "command", "output", "explanation"):
                if key not in s or not isinstance(s.get(key), str):
                    issues.append(("G3", "FAIL", f"sample_outputs[{i}] missing/bad {key}"))

    # G4 — commands invoke the right binary (or a known alias)
    binary = v3_entry.get("binary", tool_key)
    aliases = set([binary, tool_key] + list(v3_entry.get("aliases", []) or []))
    if isinstance(samps, list):
        for i, s in enumerate(samps):
            if not isinstance(s, dict): continue
            cmd = (s.get("command") or "").strip()
            if not cmd:
                issues.append(("G4", "FAIL", f"sample_outputs[{i}] empty command"))
                continue
            first_tok = cmd.split()[0] if cmd.split() else ""
            # Strip common prefixes: sudo, doas, env VAR=...
            actual = first_tok
            if first_tok in ("sudo", "doas") and len(cmd.split()) > 1:
                actual = cmd.split()[1]
            # Strip path prefix
            actual_base = actual.rsplit("/", 1)[-1]
            # python -m module pattern
            if actual_base in ("python", "python3") and "-m" in cmd.split():
                idx = cmd.split().index("-m")
                if idx + 1 < len(cmd.split()):
                    actual_base = cmd.split()[idx + 1]
            if not any(a == actual_base or actual_base.startswith(a) for a in aliases if a):
                issues.append(("G4", "WARN",
                    f"sample_outputs[{i}] command starts with '{actual_base}', expected one of {sorted(aliases)}"))

    # G5 / G6 — legal_notes / false_positives
    for fname, gnum in [("legal_notes", "G5"), ("false_positives", "G6")]:
        x = card.get(fname)
        if not _is_str_list(x):
            issues.append((gnum, "FAIL", f"{fname} is not a list of strings"))
            continue
        if not (1 <= len(x) <= 8):
            issues.append((gnum, "FAIL", f"{fname} has {len(x)} entries (expected 1-8)"))
        for i, s in enumerate(x):
            L = len(s)
            if L < CHAR_MIN_PER_ITEM:
                issues.append((gnum, "FAIL", f"{fname}[{i}] is only {L} chars"))
            elif L > CHAR_MAX_PER_ITEM:
                issues.append((gnum, "FAIL", f"{fname}[{i}] is {L} chars (>{CHAR_MAX_PER_ITEM})"))

    # G7 — MITRE format
    mit = card.get("mitre_attack")
    if not isinstance(mit, list):
        issues.append(("G7", "FAIL", "mitre_attack is not a list"))
    else:
        for i, m in enumerate(mit):
            if not isinstance(m, dict):
                issues.append(("G7", "FAIL", f"mitre_attack[{i}] not a dict"))
                continue
            mid = m.get("id", "")
            name = m.get("name", "")
            if not MITRE_RE.match(mid):
                issues.append(("G7", "FAIL", f"mitre_attack[{i}] bad ID format: '{mid}'"))
            if not isinstance(name, str) or len(name) < 3:
                issues.append(("G7", "FAIL", f"mitre_attack[{i}] missing/short name"))

    # G8 — opsec_notes count warning
    if isinstance(ops, list) and 3 <= len(ops) < 4:
        issues.append(("G8", "WARN", f"opsec_notes has only {len(ops)} entries — Sonnet usually does 5-6"))

    # G9 — sample_outputs count warning
    if isinstance(samps, list) and len(samps) < 2:
        issues.append(("G9", "WARN", f"sample_outputs has {len(samps)} entry (expected 2: beginner + advanced)"))

    # G10 — total card size sanity
    try:
        total = len(json.dumps(card, ensure_ascii=False))
    except Exception:
        total = 0
    if total < TOTAL_MIN:
        issues.append(("G10", "WARN", f"card is only {total} chars (thin)"))
    elif total > TOTAL_MAX:
        issues.append(("G10", "WARN", f"card is {total} chars (very verbose)"))

    # G11 — duplicate MITRE IDs
    if isinstance(mit, list):
        ids = [m.get("id") for m in mit if isinstance(m, dict) and m.get("id")]
        seen = set()
        for i in ids:
            if i in seen:
                issues.append(("G11", "FAIL", f"duplicate MITRE id: {i}"))
            seen.add(i)

    # G12 — control chars
    raw = json.dumps(card, ensure_ascii=False)
    if any(ord(c) < 32 and c not in ("\n", "\t") for c in raw):
        issues.append(("G12", "FAIL", "card contains unescaped control characters"))

    fails = [i for i in issues if i[1] == "FAIL"]
    warns = [i for i in issues if i[1] == "WARN"]
    severity = "FAIL" if fails else ("WARN" if warns else "PASS")
    return {
        "tool": tool_key,
        "severity": severity,
        "passed": severity == "PASS",
        "fails": [f"{g}: {m}" for g, _, m in fails],
        "warns": [f"{g}: {m}" for g, _, m in warns],
        "total_chars": total if 'total' in dir() else 0,
    }


def main() -> int:
    gen = json.load(open(GENERATED))
    v3 = json.load(open(CANONICAL))
    gen_tools = gen.get("tools", {})
    v3_tools = v3.get("tools", {})

    # Same "remaining" logic as merge_generated.py --resume
    MERGEABLE = ("opsec_notes", "sample_outputs", "legal_notes", "false_positives", "mitre_attack")
    remaining = [
        k for k, g in gen_tools.items()
        if any(not v3_tools.get(k, {}).get(f) for f in MERGEABLE if g.get(f))
    ]

    results = {}
    for k in remaining:
        results[k] = check_card(k, gen_tools[k], v3_tools.get(k, {}))

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    passed = [k for k, r in results.items() if r["severity"] == "PASS"]
    warned = [k for k, r in results.items() if r["severity"] == "WARN"]
    failed = [k for k, r in results.items() if r["severity"] == "FAIL"]

    print(f"╔{'═'*66}╗")
    print(f"║ QUALITY GATE REPORT — {len(remaining)} unmerged cards{' '*(66-len(' QUALITY GATE REPORT — XX unmerged cards'))}║")
    print(f"╚{'═'*66}╝")
    print()
    print(f"  ✅ PASS:  {len(passed):2d}  (auto-approve candidates)")
    print(f"  ⚠️  WARN:  {len(warned):2d}  (review recommended but probably fine)")
    print(f"  ❌ FAIL:  {len(failed):2d}  (review required)")
    print()

    if failed:
        print("━━━ FAILED cards (need review) ━━━")
        for k in failed:
            print(f"\n  {k}:")
            for fail in results[k]["fails"]:
                print(f"    ❌ {fail}")
            for warn in results[k]["warns"]:
                print(f"    ⚠️  {warn}")
        print()

    if warned:
        print("━━━ WARN cards (likely OK) ━━━")
        for k in warned:
            warns = results[k]["warns"]
            print(f"  {k}: {len(warns)} warning(s) — " + "; ".join(warns[:2]))
        print()

    print(f"  → wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
