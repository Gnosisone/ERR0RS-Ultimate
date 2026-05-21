"""
ERR0RS ULTIMATE — Pre-execution Safety Gate
═══════════════════════════════════════════════════════════════════

This is the SINGLE chokepoint every tool execution passes through.
`BaseTool.execute()` and `BasePlugin.stream()` both call
`check_tool_execution()` at the very top of their work — before
spawning any subprocess.

DESIGN PRINCIPLES:
  1. Fail closed — if we can't prove the target is authorized, refuse.
  2. Lab mode is OPT-IN — must be explicitly enabled in .env, prints
     a clear banner every session, and only applies to localhost +
     RFC1918 + explicitly-marked-lab targets.
  3. Authorization can come from three sources, in priority order:
       a) An active record in ~/.err0rs/authorization.json (real engagements)
       b) Lab-mode + target is in a lab range (localhost, RFC1918,
          explicitly listed in ERR0RS_LAB_TARGETS env var)
       c) The user just got asked and approved (interactive prompt
          — only when stdin is a real TTY)
  4. Refusals are LOUD and HELPFUL — tell the user exactly why,
     and exactly how to authorize legally.

WHY THIS MATTERS:
  Unauthorized access to computer systems violates the Computer Fraud
  and Abuse Act (18 U.S.C. § 1030) in the United States, and
  equivalent statutes worldwide. CFAA does NOT care about the user's
  age, intent, or skill level. ERR0RS is built for students from
  age 12 up. The gate prevents a curious teenager from accidentally
  committing a federal felony.

  This is not paranoia. This is engineering for the failure mode our
  architecture document explicitly warned about:
  "A 12-year-old running real pen-test tools against real targets
   is a legal disaster. CFAA does not care about age."

USAGE in base classes:
    from src.security.gate import check_tool_execution

    decision = check_tool_execution(
        tool_name="nmap",
        target="example.com",
        command="nmap -sV example.com",
    )
    if not decision.allowed:
        # Refuse, emit a tool.blocked event, return early
        return ...
"""
from __future__ import annotations

import ipaddress
import logging
import os
import re
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .authorization import AuthorizationManager
from .guardrails import EthicalGuardrails

log = logging.getLogger(__name__)

# ── Module-level singletons ──────────────────────────────────────────────
# We use a singleton pattern (not a global mutable) so:
#   - The same authorization records are visible to every code path
#   - Tests can override by calling _reset_for_testing()
#   - Lazy-loaded so importing this module doesn't read files

_auth_lock = threading.Lock()
_auth_manager: Optional[AuthorizationManager] = None
_guardrails:   Optional[EthicalGuardrails] = None

# Where authorization records live. Defaults to ~/.err0rs/ so they
# survive across runs and don't pollute the repo. Override via env
# for tests or per-engagement isolation.
DEFAULT_AUTH_FILE = Path.home() / ".err0rs" / "authorization.json"


def _get_managers():
    """Lazy-init the singleton managers."""
    global _auth_manager, _guardrails
    with _auth_lock:
        if _auth_manager is None:
            auth_path = Path(os.environ.get("ERR0RS_AUTH_FILE", str(DEFAULT_AUTH_FILE)))
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            _auth_manager = AuthorizationManager(str(auth_path))
            _guardrails   = EthicalGuardrails(_auth_manager)
        return _auth_manager, _guardrails


# ── Lab mode helpers ─────────────────────────────────────────────────────

# Targets that are considered safe to test in lab mode without an
# explicit authorization record. These are localhost, link-local,
# and the RFC1918 private ranges (10/8, 172.16/12, 192.168/16).
# Plus IPv6 equivalents.
_LAB_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),       # IPv4 localhost
    ipaddress.ip_network("10.0.0.0/8"),        # RFC1918 class A
    ipaddress.ip_network("172.16.0.0/12"),     # RFC1918 class B
    ipaddress.ip_network("192.168.0.0/16"),    # RFC1918 class C
    ipaddress.ip_network("169.254.0.0/16"),    # link-local IPv4
    ipaddress.ip_network("::1/128"),           # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

_LAB_HOSTNAMES = {
    "localhost", "ip6-localhost", "ip6-loopback",
}


def _is_lab_target(target: str) -> bool:
    """Return True if `target` is a localhost, RFC1918, or explicitly
    listed lab target.

    Handles:
      - Bare IPs:        127.0.0.1, 10.0.0.5
      - Localhost names: localhost
      - URLs:            http://192.168.1.1:8080/path  → strips to IP
      - Hostnames in ERR0RS_LAB_TARGETS env var (comma-separated)
    """
    if not target:
        return False

    # Strip URL scheme + port + path
    cleaned = target.strip().lower()
    cleaned = re.sub(r"^[a-z]+://", "", cleaned)
    cleaned = cleaned.split("/", 1)[0]
    cleaned = cleaned.split(":", 1)[0] if cleaned.count(":") == 1 else cleaned
    # IPv6 with brackets in URLs: [::1]
    cleaned = cleaned.strip("[]")

    if cleaned in _LAB_HOSTNAMES:
        return True

    # Check ERR0RS_LAB_TARGETS env var — comma-separated list of
    # explicit lab targets (e.g. for a deliberate-vuln VM at a non-
    # RFC1918 address inside a corporate network)
    explicit = os.environ.get("ERR0RS_LAB_TARGETS", "")
    if explicit:
        explicit_set = {t.strip().lower() for t in explicit.split(",") if t.strip()}
        if cleaned in explicit_set:
            return True

    # Try parsing as an IP and checking against lab nets
    try:
        ip = ipaddress.ip_address(cleaned)
        for net in _LAB_NETS:
            if ip in net:
                return True
    except ValueError:
        # Not an IP — bare hostname like "example.com" → NOT a lab target
        pass

    return False


def _lab_mode_enabled() -> bool:
    """Lab mode is opt-in. Set ERR0RS_LAB_MODE=1 in .env to enable."""
    return os.environ.get("ERR0RS_LAB_MODE", "0").strip() in ("1", "true", "yes", "on")


_lab_banner_shown = False


def _show_lab_banner_once():
    """Print a one-time banner so the user always knows lab mode is on."""
    global _lab_banner_shown
    if _lab_banner_shown:
        return
    _lab_banner_shown = True
    sys.stderr.write(
        "\n"
        "╔══════════════════════════════════════════════════════════════════╗\n"
        "║  ⚠️   ERR0RS LAB MODE IS ACTIVE                                  ║\n"
        "║                                                                  ║\n"
        "║  Tools may execute against localhost, RFC1918 ranges, and        ║\n"
        "║  any target listed in ERR0RS_LAB_TARGETS without an explicit     ║\n"
        "║  authorization record. NEVER use lab mode against real systems   ║\n"
        "║  you don't own. Unauthorized access is a federal crime under     ║\n"
        "║  CFAA (18 U.S.C. § 1030) and equivalent worldwide statutes.      ║\n"
        "║                                                                  ║\n"
        "║  Disable: unset ERR0RS_LAB_MODE in .env                          ║\n"
        "╚══════════════════════════════════════════════════════════════════╝\n"
        "\n"
    )
    sys.stderr.flush()


# ── The public gate ──────────────────────────────────────────────────────

@dataclass
class GateDecision:
    """Outcome of a pre-execution check.

    `allowed`  : bool      — proceed (True) or refuse (False)
    `reason`   : str       — human-readable explanation (always set)
    `source`   : str       — what authorized this (or what blocked it):
                             'authorization' | 'lab_mode' | 'blocked_command'
                             | 'no_authorization' | 'dangerous_pattern'
    `risk`     : str       — risk tier of the tool, if known
    """
    allowed: bool
    reason:  str
    source:  str
    risk:    str = "unknown"


def check_tool_execution(
    tool_name: str,
    target: str,
    command: str,
    context: Optional[dict] = None,
) -> GateDecision:
    """
    The single safety gate. Called from BaseTool.execute() and
    BasePlugin.stream() at the very top, before any subprocess work.

    Returns a GateDecision. Callers MUST honor `.allowed` — if False,
    they MUST NOT spawn the subprocess. The base classes additionally
    emit a `tool.blocked` event so the UI shows clear feedback.

    Args:
        tool_name : "nmap", "sqlmap", etc. — used for risk classification
        target    : the host/URL being attacked. Empty string is allowed
                    for tools that don't take a target (e.g. local hashcat)
        command   : the full shell command — checked for blocked patterns
        context   : optional dict of additional info (unused today, here
                    for future expansion without breaking the signature)

    Authorization sources, in priority order:
      1. Authorization record in ~/.err0rs/authorization.json
      2. Lab mode (ERR0RS_LAB_MODE=1) + target is in a lab range
      3. (No interactive prompt today — that's a v3.8 follow-up)
    """
    auth_mgr, guardrails = _get_managers()

    # ── First: dangerous-pattern check (independent of authorization) ───
    # Some commands are never allowed, even with authorization.
    # `rm -rf /`, `dd if=...`, `mkfs`, etc. — see BLOCKED_PATTERNS in guardrails.py
    pattern_ok, pattern_reason = guardrails._check_blocked_commands(command)
    if not pattern_ok:
        return GateDecision(
            allowed=False,
            reason=pattern_reason,
            source="dangerous_pattern",
        )

    # ── Second: tools that operate on local data only need no target auth ──
    # If no target was provided, we trust the tool is operating locally
    # (e.g. `hashcat` on a local hash file, `john` on a local file).
    # Pattern-check above still applies.
    risk = guardrails.TOOL_RISK_LEVELS.get(tool_name, "unknown") if hasattr(
        guardrails, "TOOL_RISK_LEVELS"
    ) else "unknown"
    # TOOL_RISK_LEVELS is module-level in guardrails.py; import it directly
    from .guardrails import TOOL_RISK_LEVELS
    risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")

    if not target or not target.strip():
        return GateDecision(
            allowed=True,
            reason="No remote target — local-only tool execution",
            source="no_target",
            risk=risk,
        )

    # ── Third: check the authorization manager ───────────────────────────
    if auth_mgr.is_target_authorized(target):
        auth_record = auth_mgr.get_active_authorization(target)
        client = auth_record.get("client_name", "unknown") if auth_record else "unknown"
        return GateDecision(
            allowed=True,
            reason=f"Target authorized under engagement for '{client}'",
            source="authorization",
            risk=risk,
        )

    # ── Fourth: lab mode (opt-in, only for lab ranges) ───────────────────
    if _lab_mode_enabled() and _is_lab_target(target):
        _show_lab_banner_once()
        return GateDecision(
            allowed=True,
            reason=f"Lab mode: {target} is in a permitted lab range",
            source="lab_mode",
            risk=risk,
        )

    # ── Refused — build a helpful error message ──────────────────────────
    msg_lines = [
        f"❌ AUTHORIZATION REQUIRED: target '{target}' is not covered.",
        "",
        "Pen-testing without written authorization is a federal crime under",
        "the Computer Fraud and Abuse Act (18 U.S.C. § 1030).",
        "",
        "You have two ways to proceed:",
        "",
        "  1. Create an authorization record for this engagement:",
        "       python3 -m src.security.cli_authorize --target {tgt} --client 'YourClient'",
        "",
        "  2. If you OWN the target (lab VM, your own machine), enable lab mode:",
        "       Add to .env:   ERR0RS_LAB_MODE=1",
        "       (Lab mode auto-allows localhost + RFC1918 + ERR0RS_LAB_TARGETS)",
        "",
        "Never test systems you don't own or have written permission to test.",
    ]
    return GateDecision(
        allowed=False,
        reason="\n".join(msg_lines).replace("{tgt}", target),
        source="no_authorization",
        risk=risk,
    )


# ── Test helpers ─────────────────────────────────────────────────────────

def _reset_for_testing():
    """Clear the singleton state. Used by tests; not for production callers."""
    global _auth_manager, _guardrails, _lab_banner_shown
    with _auth_lock:
        _auth_manager = None
        _guardrails = None
        _lab_banner_shown = False
