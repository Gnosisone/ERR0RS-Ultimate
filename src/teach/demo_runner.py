"""
ERR0RS ULTIMATE — Demo Runner (v3.8 Phase 1)
═══════════════════════════════════════════════════════════════════

Loads curated demo recipes from src/teach/demos/*.yaml and exposes
a clean stepping API for the launcher's `teach <tool>` flow.

WHY THIS EXISTS:
  When a LEARN/OPERATE-tier user types `teach nmap`, we want more
  than a wall of chunked-RAG text — we want a real, safe demonstration
  of the tool against localhost, with the LLM narrating each step.
  This module is the curated-recipe loader that makes that possible
  without letting the local LLM author shell commands.

DESIGN PRINCIPLES:
  1. Curated, never LLM-authored at LEARN tier. The commands in each
     recipe step are written by humans, audited, and version-controlled.
  2. Lazy load + cache. Recipes are read once per process. Adding a
     new recipe requires an ERR0RS restart (acceptable — recipes are
     not changed during a session).
  3. Placeholder-aware. Every command is run through
     host_context.substitute_placeholders() so {USER_IP}, {LHOST},
     {HOSTNAME} etc. fill in correctly per host.
  4. Tier-gated. The recipe's min_tier and requires_lab_mode fields
     are enforced before the demo can start.
  5. The demo runner does NOT execute commands. It produces a
     DemoPlan that the launcher's WS handler drives — separating
     "what to run" from "how to run it" so the safety gate stays the
     single execution chokepoint.

USAGE:
    from src.teach.demo_runner import (
        load_recipe, get_available_tools, build_demo_plan
    )

    plan = build_demo_plan('nmap')   # returns DemoPlan or None
    if plan:
        for step in plan.steps:
            print(step.name)
            print(step.command)      # already placeholder-substituted
            print(step.intent)

    # The launcher uses the plan to drive step-at-a-time confirmation
    # in the WebSocket UI.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

DEMOS_DIR = Path(__file__).resolve().parent / "demos"

# Optional dependency — PyYAML. If not installed, recipes are unreadable
# but the rest of ERR0RS still works (we fail soft and log a warning).
try:
    import yaml as _yaml
    _HAS_YAML = True
except ImportError:
    _yaml = None
    _HAS_YAML = False
    log.warning(
        "PyYAML not installed — demo recipes disabled. "
        "Install with: pip install pyyaml --break-system-packages"
    )


@dataclass
class DemoStep:
    """One step in a demo sequence — name, intent, command, and metadata."""
    name:           str
    intent:         str
    command:        str            # placeholder-substituted, ready to run
    timeout:        int = 30
    requires_root:  bool = False
    teach_chunks:   list = field(default_factory=list)
    explain_after:  Optional[str] = None


@dataclass
class DemoPlan:
    """Full plan for a `teach <tool>` interactive demo."""
    tool:                str
    display_name:        str
    description:         str
    default_target:      str
    min_tier:            str         # "EXPLORE" / "LEARN" / "OPERATE"
    requires_lab_mode:   bool
    steps:               list[DemoStep] = field(default_factory=list)
    next_steps:          list[str] = field(default_factory=list)
    source_path:         Optional[Path] = None


# ── Recipe loading ───────────────────────────────────────────────────────

_recipe_cache: dict[str, DemoPlan] = {}
_cache_built = False


def _build_cache() -> None:
    """Scan DEMOS_DIR for *.yaml and populate _recipe_cache.
    Called lazily on first lookup; safe to call repeatedly."""
    global _cache_built
    if _cache_built:
        return
    if not _HAS_YAML:
        _cache_built = True   # avoid retrying on every call
        return
    if not DEMOS_DIR.exists():
        log.warning(f"demos directory missing: {DEMOS_DIR}")
        _cache_built = True
        return

    for yaml_path in sorted(DEMOS_DIR.glob("*.yaml")):
        try:
            data = _yaml.safe_load(yaml_path.read_text())
            if not data or "tool" not in data:
                log.warning(f"skipping recipe (missing 'tool' key): {yaml_path}")
                continue
            plan = _plan_from_dict(data, source_path=yaml_path)
            _recipe_cache[plan.tool.lower()] = plan
        except Exception as e:
            log.warning(f"failed to load recipe {yaml_path}: {e}")

    _cache_built = True


def _plan_from_dict(data: dict, source_path: Optional[Path] = None) -> DemoPlan:
    """Convert a parsed YAML dict into a DemoPlan. NO placeholder
    substitution yet — that happens at build_demo_plan() time so we
    can use the user's current IP, not a stale cached one."""
    steps_raw = data.get("steps") or []
    steps = [
        DemoStep(
            name=s.get("name", "unnamed"),
            intent=s.get("intent", ""),
            command=s.get("command", ""),        # raw template, not substituted yet
            timeout=int(s.get("timeout", 30)),
            requires_root=bool(s.get("requires_root", False)),
            teach_chunks=list(s.get("teach_chunks") or []),
            explain_after=s.get("explain_after"),
        )
        for s in steps_raw
    ]
    return DemoPlan(
        tool=str(data.get("tool", "")).lower(),
        display_name=str(data.get("display_name", data.get("tool", ""))),
        description=str(data.get("description", "")).strip(),
        default_target=str(data.get("default_target", "127.0.0.1")),
        min_tier=str(data.get("min_tier", "LEARN")).upper(),
        requires_lab_mode=bool(data.get("requires_lab_mode", True)),
        steps=steps,
        next_steps=list(data.get("next_steps") or []),
        source_path=source_path,
    )


# ── Public API ───────────────────────────────────────────────────────────

def get_available_tools() -> list[str]:
    """Return the sorted list of tool keys that have a demo recipe."""
    _build_cache()
    return sorted(_recipe_cache.keys())


def load_recipe(tool: str) -> Optional[DemoPlan]:
    """Return the raw (unsubstituted) recipe for a tool, or None."""
    _build_cache()
    return _recipe_cache.get(tool.lower().strip())


def build_demo_plan(
    tool: str,
    user_ip: Optional[str] = None,
    extra_substitutions: Optional[dict] = None,
) -> Optional[DemoPlan]:
    """Return a DemoPlan with placeholders substituted, ready for the
    launcher to drive. Returns None if no recipe exists for this tool.

    Substitutions: {USER_IP}/{LHOST}/{HOSTNAME} from host_context, plus
    anything passed in extra_substitutions (e.g. {PORT: '4444'}).
    """
    raw = load_recipe(tool)
    if raw is None:
        return None

    # Import here so demo_runner doesn't depend on host_context at
    # module load — host_context's IP detection touches subprocess
    # which can be slow on cold start.
    from src.ai.host_context import substitute_placeholders

    substituted_steps = [
        DemoStep(
            name=s.name,
            intent=substitute_placeholders(s.intent, extra=extra_substitutions,
                                           user_ip=user_ip),
            command=substitute_placeholders(s.command, extra=extra_substitutions,
                                            user_ip=user_ip),
            timeout=s.timeout,
            requires_root=s.requires_root,
            teach_chunks=list(s.teach_chunks),
            explain_after=(
                substitute_placeholders(s.explain_after, extra=extra_substitutions,
                                        user_ip=user_ip)
                if s.explain_after else None
            ),
        )
        for s in raw.steps
    ]

    return DemoPlan(
        tool=raw.tool,
        display_name=raw.display_name,
        description=substitute_placeholders(raw.description, extra=extra_substitutions,
                                            user_ip=user_ip),
        default_target=raw.default_target,
        min_tier=raw.min_tier,
        requires_lab_mode=raw.requires_lab_mode,
        steps=substituted_steps,
        next_steps=list(raw.next_steps),
        source_path=raw.source_path,
    )


# ── Diagnostic / inspection ──────────────────────────────────────────────

def recipe_stats() -> dict:
    """Diagnostic snapshot of the recipe cache state."""
    _build_cache()
    return {
        "yaml_available":      _HAS_YAML,
        "demos_dir":           str(DEMOS_DIR),
        "demos_dir_exists":    DEMOS_DIR.exists(),
        "recipes_loaded":      len(_recipe_cache),
        "available_tools":     sorted(_recipe_cache.keys()),
    }


def _reset_for_testing():
    """Clear the recipe cache. Tests only."""
    global _cache_built, _recipe_cache
    _recipe_cache = {}
    _cache_built = False
