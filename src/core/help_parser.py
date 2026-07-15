#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — HELP / MAN-PAGE PARSER                  ║
║              src/core/help_parser.py                             ║
║                                                                  ║
║  The long-tail fallback for command_anatomy. When a flag isn't   ║
║  in the hand-authored FLAG_KB, this parses the tool's OWN        ║
║  `--help` / `-h` output (and man page) to extract a real         ║
║  description — so ERR0RS can explain flags for tools nobody      ║
║  hand-curated, entirely offline, from the source of truth the    ║
║  tool ships with itself.                                         ║
║                                                                  ║
║  SAFETY: only runs a binary that (a) matches a strict name       ║
║  pattern (no spaces/metacharacters/paths) and (b) exists on      ║
║  PATH (shutil.which). No shell, hard timeout, output captured.   ║
║  Results are cached per tool for the process lifetime.           ║
║                                                                  ║
║  Pure stdlib. Fail-soft: any error → no description, never a     ║
║  crash and never a fabricated answer.                            ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import shutil
import subprocess
from typing import Dict, Optional

# Strict: a bare binary name only. Blocks paths, spaces, shell metacharacters.
_SAFE_TOOL = re.compile(r"^[A-Za-z0-9_.\-]+$")

# A help line: leading flags section, then ':' or 2+ spaces, then description.
#   nmap:     "-iL <file>: Input from list of hosts"
#   gobuster: "--url value, -u value      The target URL"
#   curl:     "-d, --data <data>    HTTP POST data"
_HELP_LINE = re.compile(r"^\s*(-{1,2}[A-Za-z0-9][\w-]*.*?)(?:\s*:\s|\s{2,}|\t)(.+)$")
_FLAG_TOKEN = re.compile(r"-{1,2}[A-Za-z0-9][\w-]*")

# Per-process caches so we shell out at most once per tool.
_help_text_cache: Dict[str, str] = {}
_flag_map_cache: Dict[str, Dict[str, str]] = {}


def _run_help(tool: str) -> str:
    """Return raw help text for a tool, or '' if unavailable/unsafe.

    Tries --help, then -h, then `help`, then `man`. Many tools print help to
    stderr, so both streams are captured. Cached per tool.
    """
    if tool in _help_text_cache:
        return _help_text_cache[tool]

    text = ""
    if _SAFE_TOOL.match(tool or "") and shutil.which(tool):
        for args in ([tool, "--help"], [tool, "-h"], [tool, "help"]):
            try:
                r = subprocess.run(args, capture_output=True, text=True,
                                   timeout=5, check=False)
                candidate = f"{r.stdout or ''}\n{r.stderr or ''}".strip()
                if candidate:
                    text = candidate
                    break
            except Exception:
                continue
        if not text:
            # Last resort: the man page rendered as plain text.
            try:
                r = subprocess.run(["man", tool], capture_output=True, text=True,
                                   timeout=5, check=False,
                                   env={"MANPAGER": "cat", "PAGER": "cat", "PATH": "/usr/bin:/bin"})
                text = re.sub(r".\x08", "", r.stdout or "")  # strip man backspace bolding
            except Exception:
                text = ""

    _help_text_cache[tool] = text
    return text


def parse_help_text(text: str) -> Dict[str, str]:
    """Parse raw help text → {flag: description}. Pure; unit-testable.

    Handles the three common layouts (colon-delimited, multi-column, and
    'short, --long <arg>  desc'). Every flag on a line shares that line's
    description, so '-u' and '--url' both resolve.
    """
    flags: Dict[str, str] = {}
    for raw in text.splitlines():
        m = _HELP_LINE.match(raw.rstrip())
        if not m:
            continue
        flag_section, desc = m.group(1), m.group(2).strip()
        # Description = first sentence-ish, capped so we don't dump paragraphs.
        desc = re.split(r"\s{2,}| \(default", desc)[0].strip().rstrip(".")
        if len(desc) > 140:
            desc = desc[:137].rsplit(" ", 1)[0] + "…"
        if not desc:
            continue
        for tok in _FLAG_TOKEN.findall(flag_section):
            # Don't clobber a longer/better description with a worse duplicate.
            if tok not in flags or len(desc) > len(flags[tok]):
                flags[tok] = desc
    return flags


def _flag_map(tool: str) -> Dict[str, str]:
    """Parsed {flag: desc} for a tool, cached."""
    if tool not in _flag_map_cache:
        _flag_map_cache[tool] = parse_help_text(_run_help(tool))
    return _flag_map_cache[tool]


def flag_help(tool: str, flag: str) -> Optional[str]:
    """Best description for a flag from the tool's own --help/man, or None.

    This is the tertiary source under command_anatomy's FLAG_KB and the teach
    engine — used only when neither hand-curated source knows the flag.
    """
    if not tool or not flag:
        return None
    return _flag_map(_canon(tool)).get(flag)


def _canon(tool: str) -> str:
    return (tool or "").split("/")[-1].strip().lower()


def _reset_cache():
    """Clear caches (tests only)."""
    _help_text_cache.clear()
    _flag_map_cache.clear()
