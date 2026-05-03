"""
ERR0RS Native Tool Runner
==========================
Pluggable runner for Python-native capability modules in AutoKillChain.

Why this exists:
----------------
The original AutoKillChain dispatches tools by building shell commands and
running them with subprocess. That works great for nmap/nuclei/sqlmap, but
it doesn't work for Python-native modules like JWTBreaker that don't have
a CLI in $PATH.

This runner provides a registry that maps tool_id → callable. AutoKillChain
checks the registry first, and if the tool_id is registered, calls it directly
with shared phase state (target, prior outputs, params). If not registered,
falls back to the existing shell-command path.

Each native tool is a function:
    def run(ctx: NativeToolContext) -> NativeToolResult: ...

The tool reads from ctx.prior_outputs to get JWTs/endpoints/etc. discovered
by earlier phases, and returns findings the orchestrator merges into the run.

Author: Gary Holden Schneider (Eros) | Sprint 01.5
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional


# ── Context + Result types ────────────────────────────────────────────────

@dataclass
class NativeToolContext:
    """What a native tool gets from the orchestrator."""
    target:        str                 # raw target string (URL or IP)
    target_parts:  dict                # output of _normalize_target()
    phase_id:      str                 # current phase
    params:        dict                # operator-supplied params
    prior_outputs: dict                # tool_id → str output from earlier phases
    prior_findings: list               # findings from earlier phases


@dataclass
class NativeToolResult:
    """What a native tool returns to the orchestrator."""
    tool_id:   str
    findings:  list = field(default_factory=list)   # [{title, severity, detail}]
    raw_output: str = ""
    success:   bool = True
    error:     str = ""


# ── Registry ──────────────────────────────────────────────────────────────

_REGISTRY: dict[str, Callable[[NativeToolContext], NativeToolResult]] = {}


def register(tool_id: str):
    """Decorator: register a function as a native tool."""
    def deco(fn):
        _REGISTRY[tool_id] = fn
        return fn
    return deco


def is_native(tool_id: str) -> bool:
    return tool_id in _REGISTRY


def run_native(tool_id: str, ctx: NativeToolContext) -> NativeToolResult:
    fn = _REGISTRY.get(tool_id)
    if fn is None:
        return NativeToolResult(tool_id=tool_id, success=False,
                                error=f"Unknown native tool: {tool_id}")
    try:
        return fn(ctx)
    except Exception as e:
        return NativeToolResult(tool_id=tool_id, success=False,
                                error=f"{type(e).__name__}: {e}")


def list_native_tools() -> list[str]:
    return sorted(_REGISTRY.keys())


# ── JWT discovery helper ──────────────────────────────────────────────────

# A JWT is base64url(header).base64url(claims).base64url(sig)
# Header must decode to JSON starting with {"alg" or {"typ"
# This regex finds plausible JWT strings; the JWT engine validates.
_JWT_RE = re.compile(
    r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{0,})\b"
)


def find_jwts_in_text(text: str) -> list[str]:
    """Extract all plausible JWTs from a blob of text. De-duplicated."""
    if not text:
        return []
    seen = set()
    out = []
    for match in _JWT_RE.findall(text):
        if match in seen:
            continue
        seen.add(match)
        out.append(match)
    return out


def find_jwts_in_prior_outputs(prior_outputs: dict) -> list[tuple[str, str]]:
    """Walk all prior phase outputs and return [(source_tool, jwt), ...]."""
    found = []
    for tool_id, output in (prior_outputs or {}).items():
        if not isinstance(output, str):
            continue
        for jwt in find_jwts_in_text(output):
            found.append((tool_id, jwt))
    return found


# ── Import the actual tools so their @register decorators fire ────────────
# (Keep this import at the bottom to avoid circular issues.)

from . import jwt_tool      # noqa: F401, E402
from . import nosql_tool    # noqa: F401, E402
from . import template_tool # noqa: F401, E402
