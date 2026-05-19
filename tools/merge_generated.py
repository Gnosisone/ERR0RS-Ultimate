#!/usr/bin/env python3
"""
ERR0RS — Generated Teach Card Merge Tool (Phase 3, finalization)
═══════════════════════════════════════════════════════════════════
Reviews each Sonnet-generated teach card in tool_registry.generated.json
and merges approved cards into the canonical tool_registry.v3.json.

Why this tool exists:
  The $5 Sonnet 4.6 generation run produced 67 gold-standard teach cards
  in src/tools/tool_registry.generated.json (gitignored, awaiting review).
  This tool is the human-in-the-loop gate between "AI generated it" and
  "it's in the canonical registry that ships with ERR0RS."

Per-card review actions:
  a / approve  — merge this card's fields into v3.json
  s / skip     — leave v3.json untouched for this tool
  e / edit     — open the generated card in $EDITOR for changes, then re-prompt
  d / diff     — show full side-by-side diff between generated and v3 fields
  q / quit     — stop reviewing, commit only what was approved so far

Safety nets:
  - Git tag created BEFORE any writes: pre-merge-YYYY-MM-DD-HHMMSS
  - Backup file: src/tools/tool_registry.v3.json.bak.YYYY-MM-DD-HHMMSS
  - Atomic write (write to .tmp, then rename) so an interrupted run can't
    corrupt the canonical registry.
  - Session summary written to docs/MERGE_SESSIONS/ for auditability.

Usage:
  python3 tools/merge_generated.py                  # interactive review
  python3 tools/merge_generated.py --dry-run        # show what would happen
  python3 tools/merge_generated.py --only crackmapexec,rubeus  # subset
  python3 tools/merge_generated.py --resume         # show only un-merged tools
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "src" / "tools" / "tool_registry.generated.json"
CANONICAL = ROOT / "src" / "tools" / "tool_registry.v3.json"
SESSIONS_DIR = ROOT / "docs" / "MERGE_SESSIONS"

# These are the exact field names the Sonnet generator emits. Anything outside
# this set must NOT be touched by the merger — that's how we keep the rest of
# the v3 schema (display_name, default_flags, references, etc.) safe.
MERGEABLE_FIELDS = (
    "opsec_notes",
    "sample_outputs",
    "legal_notes",
    "false_positives",
    "mitre_attack",
)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t):   return _color(t, "92")
def yellow(t):  return _color(t, "93")
def red(t):     return _color(t, "91")
def cyan(t):    return _color(t, "96")
def dim(t):     return _color(t, "2")
def bold(t):    return _color(t, "1")


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically — write to temp, fsync, rename. An interrupted
    run cannot leave the canonical registry half-written."""
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def git_in_repo() -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT, capture_output=True, text=True,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False


def git_tag(name: str, message: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "tag", "-a", name, "-m", message],
            cwd=ROOT, capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(red(f"  ✗ git tag failed: {r.stderr.strip()}"))
            return False
        return True
    except FileNotFoundError:
        return False


# ────────────────────────────────────────────────────────────────────────────
# Rendering
# ────────────────────────────────────────────────────────────────────────────

def render_field(name: str, value: Any, indent: str = "    ") -> str:
    """Render one field's content for human inspection."""
    if value is None or value == [] or value == {}:
        return f"{indent}{dim('(empty)')}"
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                # mitre_attack / sample_outputs are list-of-dicts
                sub = []
                for k, v in item.items():
                    vs = str(v)
                    if len(vs) > 140:
                        vs = vs[:137] + "..."
                    sub.append(f"{indent}  {dim(k+':')} {vs}")
                lines.append("\n".join(sub))
                lines.append("")
            else:
                s = str(item)
                if len(s) > 200:
                    s = s[:197] + "..."
                lines.append(f"{indent}- {s}")
        return "\n".join(lines).rstrip()
    return f"{indent}{value}"


def render_card(tool_key: str, gen_card: dict, v3_entry: dict) -> None:
    print()
    print(bold(cyan(f"═══ {tool_key} ") + cyan("═" * (60 - len(tool_key)))))
    display = v3_entry.get("display_name", tool_key)
    category = v3_entry.get("category", "?")
    tier = v3_entry.get("tier", "?")
    print(f"  {bold(display)}  {dim(f'(category={category}, tier={tier})')}")
    desc = v3_entry.get("description", "")
    if desc:
        d = desc if len(desc) <= 120 else desc[:117] + "..."
        print(f"  {dim(d)}")
    print()

    for field in MERGEABLE_FIELDS:
        gen_val = gen_card.get(field)
        v3_val = v3_entry.get(field)

        gen_size = len(gen_val) if isinstance(gen_val, (list, dict)) else (1 if gen_val else 0)
        v3_size = len(v3_val) if isinstance(v3_val, (list, dict)) else (1 if v3_val else 0)

        if v3_size == 0 and gen_size > 0:
            tag = green(f"[NEW: +{gen_size}]")
        elif v3_size > 0 and gen_size == 0:
            tag = yellow(f"[KEEP: v3 has {v3_size}, gen empty — would clear]")
        elif gen_val == v3_val:
            tag = dim(f"[SAME: {gen_size}]")
        else:
            tag = yellow(f"[OVERWRITE: v3={v3_size} → gen={gen_size}]")

        print(f"  {bold(field)}  {tag}")
        print(render_field(field, gen_val))
        print()


def render_diff(tool_key: str, gen_card: dict, v3_entry: dict) -> None:
    print()
    print(bold(cyan(f"═══ FULL DIFF: {tool_key} ═══")))
    for field in MERGEABLE_FIELDS:
        gv = gen_card.get(field)
        vv = v3_entry.get(field)
        if gv == vv:
            print(f"  {dim(field)}: {dim('(identical)')}")
            continue
        print()
        print(bold(field))
        print(red("  --- v3 (current) ---"))
        print(render_field(field, vv, "    "))
        print(green("  +++ generated (proposed) ---"))
        print(render_field(field, gv, "    "))
    print()


# ────────────────────────────────────────────────────────────────────────────
# Edit-in-$EDITOR flow
# ────────────────────────────────────────────────────────────────────────────

def edit_card(gen_card: dict) -> dict | None:
    """Open the generated card in $EDITOR. Return modified card on save, or
    None if the edit was invalid or aborted."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="err0rs_merge_", delete=False
    ) as f:
        json.dump(gen_card, f, indent=2, ensure_ascii=False)
        tmp_path = f.name
    try:
        subprocess.run([editor, tmp_path])
        with open(tmp_path) as f:
            edited = json.load(f)
        # Schema sanity: only allow the known fields, refuse anything else
        bad = set(edited.keys()) - set(MERGEABLE_FIELDS)
        if bad:
            print(red(f"  ✗ edit added unknown fields: {bad}"))
            return None
        return edited
    except json.JSONDecodeError as e:
        print(red(f"  ✗ edited JSON is invalid: {e}"))
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ────────────────────────────────────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────────────────────────────────────

def prompt_action(tool_key: str) -> str:
    while True:
        ans = input(
            cyan(f"  [{tool_key}] action — ") +
            "(a)pprove / (s)kip / (e)dit / (d)iff / (q)uit: "
        ).strip().lower()
        if ans in ("a", "approve"): return "a"
        if ans in ("s", "skip"):    return "s"
        if ans in ("e", "edit"):    return "e"
        if ans in ("d", "diff"):    return "d"
        if ans in ("q", "quit"):    return "q"
        print(red("  ?? unknown — type one of: a s e d q"))


def merge_field(v3_entry: dict, gen_card: dict) -> dict:
    """Apply approved generated fields onto a v3 entry. Empty generated fields
    do NOT clear existing v3 content (defensive — better to keep something
    real than overwrite with nothing)."""
    out = dict(v3_entry)
    for field in MERGEABLE_FIELDS:
        gv = gen_card.get(field)
        if gv:  # non-empty wins
            out[field] = gv
    return out


def write_session_log(decisions: list[dict], tag: str, backup: str) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    out = SESSIONS_DIR / f"merge_{_ts()}.md"
    approved = [d for d in decisions if d["action"] == "approved"]
    skipped = [d for d in decisions if d["action"] == "skipped"]
    edited = [d for d in decisions if d["action"] == "edited"]
    with open(out, "w") as f:
        f.write(f"# Merge session — {dt.datetime.now().isoformat(timespec='seconds')}\n\n")
        f.write(f"- Git tag:       `{tag}`\n")
        f.write(f"- Backup file:   `{backup}`\n")
        f.write(f"- Approved:      {len(approved)}\n")
        f.write(f"- Edited:        {len(edited)}\n")
        f.write(f"- Skipped:       {len(skipped)}\n\n")
        f.write("## Decisions\n\n")
        for d in decisions:
            f.write(f"- `{d['tool']}` — **{d['action']}**\n")
    return out


def run(args: argparse.Namespace) -> int:
    if not GENERATED.exists():
        print(red(f"  ✗ {GENERATED} not found. Run tools/generate_teach.py first."))
        return 1
    if not CANONICAL.exists():
        print(red(f"  ✗ {CANONICAL} not found."))
        return 1

    gen = load_json(GENERATED)
    v3 = load_json(CANONICAL)

    gen_tools: dict[str, dict] = gen.get("tools", {})
    v3_tools: dict[str, dict] = v3.get("tools", {})

    if not gen_tools:
        print(red("  ✗ Generated file has no tools"))
        return 1

    # Subset filtering
    keys = list(gen_tools.keys())
    if args.only:
        wanted = set(s.strip() for s in args.only.split(","))
        keys = [k for k in keys if k in wanted]
        if not keys:
            print(red(f"  ✗ none of --only matched: {wanted}"))
            return 1

    # Skip already-merged (resume mode): a tool is considered "already merged"
    # if v3 has non-empty content for ALL generated fields
    if args.resume:
        before = len(keys)
        keys = [
            k for k in keys
            if any(not v3_tools.get(k, {}).get(f) for f in MERGEABLE_FIELDS if gen_tools[k].get(f))
        ]
        print(dim(f"  resume: {before} → {len(keys)} tools still need review"))

    print(bold(cyan("=" * 70)))
    print(bold(cyan(f" ERR0RS Merge Tool — {len(keys)} cards queued")))
    print(bold(cyan("=" * 70)))

    if args.dry_run:
        print(yellow("  DRY RUN — no changes will be written"))

    # ── Safety net: git tag + file backup ──────────────────────────────────
    tag_name = f"pre-merge-{_ts()}"
    backup_path = CANONICAL.with_suffix(f".json.bak.{_ts()}")
    if not args.dry_run:
        # Backup file first (cheap, always works)
        shutil.copy2(CANONICAL, backup_path)
        print(green(f"  ✓ backup written: {backup_path.name}"))
        # Git tag (best-effort — proceed even if it fails)
        if git_in_repo():
            ok = git_tag(tag_name, f"Pre-merge snapshot before merge_generated.py ({len(keys)} cards queued)")
            if ok:
                print(green(f"  ✓ git tag created: {tag_name}"))
            else:
                print(yellow(f"  ! git tag skipped (see error above); backup file is still in place"))
        else:
            print(yellow("  ! not a git repo — skipped tag (backup file is in place)"))
    else:
        print(dim(f"  (would create tag {tag_name} and backup {backup_path.name})"))

    decisions: list[dict] = []
    approved_count = 0

    try:
        for i, tool_key in enumerate(keys, 1):
            gen_card = gen_tools[tool_key]
            v3_entry = v3_tools.get(tool_key)
            if v3_entry is None:
                print(red(f"  ✗ {tool_key}: not present in v3 registry — skipping"))
                decisions.append({"tool": tool_key, "action": "skipped"})
                continue

            print(dim(f"\n  ── card {i}/{len(keys)} ──"))
            render_card(tool_key, gen_card, v3_entry)

            # Action loop — d/diff doesn't consume the card, returns to prompt
            while True:
                action = prompt_action(tool_key)
                if action == "d":
                    render_diff(tool_key, gen_card, v3_entry)
                    continue
                if action == "e":
                    edited = edit_card(gen_card)
                    if edited is None:
                        print(yellow("  ! edit discarded, returning to prompt"))
                        continue
                    gen_card = edited
                    # Show the result of the edit and re-prompt
                    print(green("  ✓ edited card loaded — review again:"))
                    render_card(tool_key, gen_card, v3_entry)
                    continue
                break  # a / s / q

            if action == "a":
                v3_tools[tool_key] = merge_field(v3_entry, gen_card)
                decisions.append({"tool": tool_key, "action": "approved"})
                approved_count += 1
                print(green(f"  ✓ merged"))
            elif action == "s":
                decisions.append({"tool": tool_key, "action": "skipped"})
                print(dim("  → skipped"))
            elif action == "q":
                print(yellow(f"  ⏸  quit — will commit {approved_count} approved so far"))
                break

    except KeyboardInterrupt:
        print()
        print(yellow(f"  ⏸  interrupted — will commit {approved_count} approved so far"))

    # ── Commit ─────────────────────────────────────────────────────────────
    if approved_count == 0:
        print(yellow("\n  no cards were approved — canonical registry untouched"))
        return 0

    if args.dry_run:
        print(yellow(f"\n  DRY RUN: would write {approved_count} merged cards to {CANONICAL.name}"))
        return 0

    # Bump schema_version timestamp on every successful merge
    v3["generated_at"] = dt.datetime.now().isoformat(timespec="seconds")

    atomic_write_json(CANONICAL, v3)
    print(green(f"\n  ✓ wrote {approved_count} merged cards to {CANONICAL.name}"))

    session_log = write_session_log(decisions, tag_name, backup_path.name)
    print(green(f"  ✓ session log: {session_log.relative_to(ROOT)}"))

    print()
    print(bold(cyan("  Next steps:")))
    print(f"    git diff {CANONICAL.relative_to(ROOT)}")
    print(f"    python3 tools/validate_registry.py")
    print(f"    git add {CANONICAL.relative_to(ROOT)} {session_log.relative_to(ROOT)}")
    print(f"    git commit -m 'feat(registry): merge {approved_count} Sonnet teach cards'")
    return 0


def run_from_decisions(decisions_path: Path) -> int:
    """Non-interactive batch apply path. Used by the chat-driven review
    workflow: chat collects decisions into a JSON file, this code path applies
    them through the same safety net as the interactive tool (atomic write +
    git tag + backup file + session log)."""
    if not decisions_path.exists():
        print(red(f"  ✗ decisions file not found: {decisions_path}"))
        return 1
    if not GENERATED.exists() or not CANONICAL.exists():
        print(red(f"  ✗ registry files missing"))
        return 1

    with open(decisions_path) as f:
        decisions_in: dict[str, str] = json.load(f)

    gen = load_json(GENERATED)
    v3 = load_json(CANONICAL)
    gen_tools = gen.get("tools", {})
    v3_tools = v3.get("tools", {})

    # Validate every tool key up-front before touching anything
    unknown_gen = [k for k in decisions_in if k not in gen_tools]
    unknown_v3 = [k for k in decisions_in if k not in v3_tools]
    bad_actions = {k: v for k, v in decisions_in.items() if v not in ("approve", "skip")}
    if unknown_gen:
        print(red(f"  ✗ not in generated registry: {unknown_gen[:5]}{'...' if len(unknown_gen) > 5 else ''}"))
        return 1
    if unknown_v3:
        print(red(f"  ✗ not in v3 registry: {unknown_v3[:5]}{'...' if len(unknown_v3) > 5 else ''}"))
        return 1
    if bad_actions:
        print(red(f"  ✗ bad action values (must be approve/skip): {bad_actions}"))
        return 1

    approve_keys = [k for k, v in decisions_in.items() if v == "approve"]
    skip_keys = [k for k, v in decisions_in.items() if v == "skip"]

    print(bold(cyan("=" * 70)))
    print(bold(cyan(f" ERR0RS Batch Merge — applying {len(approve_keys)} approvals")))
    print(bold(cyan("=" * 70)))
    print(f"  approve: {len(approve_keys)}")
    print(f"  skip:    {len(skip_keys)}")
    print(f"  total:   {len(decisions_in)}")

    # Safety net — same as interactive path
    tag_name = f"pre-merge-{_ts()}"
    backup_path = CANONICAL.with_suffix(f".json.bak.{_ts()}")
    shutil.copy2(CANONICAL, backup_path)
    print(green(f"  ✓ backup written: {backup_path.name}"))
    if git_in_repo():
        if git_tag(tag_name, f"Pre-merge snapshot before batch apply ({len(approve_keys)} approvals)"):
            print(green(f"  ✓ git tag created: {tag_name}"))

    decisions_log: list[dict] = []
    applied = 0
    for k in approve_keys:
        v3_tools[k] = merge_field(v3_tools[k], gen_tools[k])
        decisions_log.append({"tool": k, "action": "approved"})
        applied += 1
    for k in skip_keys:
        decisions_log.append({"tool": k, "action": "skipped"})

    if applied == 0:
        print(yellow("  no approvals — canonical registry untouched"))
        return 0

    v3["generated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    atomic_write_json(CANONICAL, v3)
    print(green(f"  ✓ wrote {applied} merged cards to {CANONICAL.name}"))

    log = write_session_log(decisions_log, tag_name, backup_path.name)
    print(green(f"  ✓ session log: {log.relative_to(ROOT)}"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Merge Sonnet-generated teach cards into v3 registry")
    p.add_argument("--dry-run", action="store_true", help="Show review UI but don't write")
    p.add_argument("--only", metavar="K1,K2,...", help="Only review these tool keys")
    p.add_argument("--resume", action="store_true", help="Skip tools whose generated fields are all already in v3")
    p.add_argument("--from-decisions", metavar="PATH", help="Non-interactive batch apply from a JSON decisions file ({tool_key: approve|skip})")
    args = p.parse_args()
    if args.from_decisions:
        return run_from_decisions(Path(args.from_decisions))
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
