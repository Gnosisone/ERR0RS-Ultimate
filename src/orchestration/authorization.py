"""
ERR0RS Authorization Gate
=========================
The safety wall. NO engagement starts without passing through this module.

Philosophy:
-----------
A penetration testing agent that can be aimed at any target is a weapon.
Weapons need safeties. This module is ERR0RS's safety.

Every PR that touches this file gets extra scrutiny. The bypass tests in
tests/test_authorization.py exist to make sure nobody accidentally weakens
the gate by removing a check or loosening a regex.

Three classes of target:
------------------------
1. ALWAYS_ALLOWED  — localhost, RFC1918 private networks, link-local.
                      No prompt needed. These are clearly lab/local targets.

2. REQUIRES_CONFIRM — public IPs and resolvable domains the user explicitly
                      passes. Requires interactive 'yes' typed in full,
                      AND the --i-have-authorization flag.

3. ALWAYS_REFUSED  — .gov, .mil, .edu (US/intl variants), and a curated
                      out-of-scope list (gov/mil ranges, known bug-bounty
                      out-of-scope IPs). Requires --override-refused with
                      a written justification logged to audit.

Author: Gary Holden Schneider (Eros) | Sprint 00
"""

from __future__ import annotations

import ipaddress
import re
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from urllib.parse import urlparse


# ── Classification ─────────────────────────────────────────────────────────

class TargetClass(Enum):
    ALWAYS_ALLOWED   = "always_allowed"
    REQUIRES_CONFIRM = "requires_confirm"
    ALWAYS_REFUSED   = "always_refused"


@dataclass
class AuthorizationResult:
    authorized:    bool
    target:        str
    target_class:  TargetClass
    resolved_ip:   Optional[str]
    reason:        str
    timestamp:     str
    operator:      str
    justification: Optional[str] = None  # Required for REFUSED-with-override


# ── TLDs that always require operator override ─────────────────────────────

REFUSED_TLDS = {
    ".gov", ".mil", ".edu",
    ".gov.uk", ".gov.au", ".gov.ca", ".gov.nz",
    ".mil.uk", ".mod.uk",
    ".ac.uk", ".edu.au",
    ".int",  # international intergovernmental orgs
}

# Curated CIDR ranges of known out-of-scope networks.
# Add to this list as new high-sensitivity ranges become known.
REFUSED_CIDRS = [
    "6.0.0.0/8",     # US Army
    "7.0.0.0/8",     # US DoD
    "11.0.0.0/8",    # US DoD
    "21.0.0.0/8",    # US DDN
    "22.0.0.0/8",    # US DISA
    "26.0.0.0/8",    # US DISA
    "28.0.0.0/8",    # US DISA
    "29.0.0.0/8",    # US DISA
    "30.0.0.0/8",    # US DISA
    "33.0.0.0/8",    # US DLA
    "55.0.0.0/8",    # US DoD
    "214.0.0.0/8",   # US DoD
    "215.0.0.0/8",   # US DoD
]
_REFUSED_NETWORKS = [ipaddress.ip_network(c) for c in REFUSED_CIDRS]


# ── URL parsing & host extraction ──────────────────────────────────────────

_HOST_PORT_RE = re.compile(
    r"^(?P<host>[a-zA-Z0-9\-\._\[\]:]+?)(?::(?P<port>\d{1,5}))?$"
)

def _extract_host(target: str) -> str:
    """
    Pull the bare host out of any of these formats:
      192.168.1.1
      192.168.1.1:8080
      example.com
      http://example.com
      https://example.com:8443/path
      [::1]:3000

    Raises ValueError on anything we can't make sense of.
    """
    t = target.strip()
    if not t:
        raise ValueError("Empty target")

    # Strip URL scheme by going through urlparse if present
    if "://" in t:
        parsed = urlparse(t)
        if not parsed.hostname:
            raise ValueError(f"Cannot parse host from URL: {target!r}")
        return parsed.hostname

    # Otherwise strip any path component and parse host:port
    if "/" in t:
        t = t.split("/", 1)[0]

    # IPv6 in brackets: [::1]:3000
    if t.startswith("["):
        end = t.find("]")
        if end == -1:
            raise ValueError(f"Malformed IPv6 in target: {target!r}")
        return t[1:end]

    # Plain host or host:port
    m = _HOST_PORT_RE.match(t)
    if not m:
        raise ValueError(f"Cannot parse target: {target!r}")
    return m.group("host")


# ── Suspicious / bypass-attempt detection ──────────────────────────────────

# Patterns that look like attempts to disguise an external target as local.
# These are LOGGED and REFUSED — they are never legitimate.
_BYPASS_PATTERNS = [
    re.compile(r"^localhost\.[a-zA-Z0-9\-]+\."),     # localhost.evil.com
    re.compile(r"^127\.0\.0\.1\.[a-zA-Z0-9\-]+\."),  # 127.0.0.1.attacker.com
    re.compile(r"^192\.168\.\d+\.\d+\.[a-zA-Z]"),    # 192.168.1.1.evil.com
    re.compile(r"^10\.\d+\.\d+\.\d+\.[a-zA-Z]"),     # 10.0.0.1.evil.com
    re.compile(r"@"),                                 # user@host weirdness
    re.compile(r"\\\\"),                              # UNC paths (\\?)
]

def _is_bypass_attempt(host: str) -> Optional[str]:
    """Return reason string if host looks like a bypass attempt, else None."""
    h = host.lower().strip()
    for pat in _BYPASS_PATTERNS:
        if pat.search(h):
            return f"Host {host!r} matches bypass pattern {pat.pattern!r}"
    # Unicode / IDN homograph attack guard — refuse non-ASCII hosts entirely
    try:
        h.encode("ascii")
    except UnicodeEncodeError:
        return f"Host {host!r} contains non-ASCII characters (IDN homograph risk)"
    return None


# ── DNS resolution (best effort) ───────────────────────────────────────────

def _resolve(host: str, timeout: float = 3.0) -> Optional[str]:
    """Return first A/AAAA record, or None on failure. Never raises."""
    try:
        # Already an IP literal? Just normalize and return.
        ip = ipaddress.ip_address(host)
        return str(ip)
    except ValueError:
        pass

    socket.setdefaulttimeout(timeout)
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, socket.herror, socket.timeout, OSError):
        return None
    finally:
        socket.setdefaulttimeout(None)


# ── Classification logic ───────────────────────────────────────────────────

def classify_target(target: str) -> tuple[TargetClass, str, Optional[str]]:
    """
    Classify a target into one of the three TargetClass values.
    Returns (classification, reason, resolved_ip_or_None).

    Pure function — no I/O except DNS resolution. No side effects.
    """
    try:
        host = _extract_host(target)
    except ValueError as e:
        return TargetClass.ALWAYS_REFUSED, f"Parse error: {e}", None

    # Bypass attempts get refused immediately.
    bypass = _is_bypass_attempt(host)
    if bypass:
        return TargetClass.ALWAYS_REFUSED, bypass, None

    host_lower = host.lower()

    # TLD-based refusal (only applies if not an IP literal)
    try:
        ipaddress.ip_address(host_lower)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False

    if not is_ip_literal:
        for tld in REFUSED_TLDS:
            if host_lower.endswith(tld):
                return (TargetClass.ALWAYS_REFUSED,
                        f"Host ends in protected TLD {tld!r}",
                        None)

    # Resolve DNS to classify by IP
    resolved = _resolve(host_lower)

    if resolved is None:
        # If we can't resolve and it's not localhost-ish, refuse to be safe
        if host_lower in ("localhost",):
            return (TargetClass.ALWAYS_ALLOWED,
                    "Hostname is 'localhost'",
                    "127.0.0.1")
        return (TargetClass.REQUIRES_CONFIRM,
                f"Host {host!r} did not resolve — cannot verify safety",
                None)

    # Check IP against refused CIDR ranges (gov/mil)
    try:
        ip_obj = ipaddress.ip_address(resolved)
    except ValueError:
        return TargetClass.ALWAYS_REFUSED, f"Resolved to invalid IP: {resolved!r}", resolved

    for net in _REFUSED_NETWORKS:
        if ip_obj in net:
            return (TargetClass.ALWAYS_REFUSED,
                    f"Resolved IP {resolved} is in protected range {net}",
                    resolved)

    # RFC1918 / loopback / link-local → ALWAYS_ALLOWED
    if (ip_obj.is_loopback or ip_obj.is_private or
        ip_obj.is_link_local or ip_obj.is_unspecified):
        return (TargetClass.ALWAYS_ALLOWED,
                f"Resolved IP {resolved} is loopback/private/link-local",
                resolved)

    # Public IP — requires confirmation
    return (TargetClass.REQUIRES_CONFIRM,
            f"Resolved IP {resolved} is a public address",
            resolved)


# ── Interactive authorization ──────────────────────────────────────────────

def authorize(
    target: str,
    *,
    operator: str = "unknown",
    have_authorization_flag: bool = False,
    override_refused: bool = False,
    justification: Optional[str] = None,
    interactive: bool = True,
    _input_fn=input,        # injected for tests
    _print_fn=print,        # injected for tests
) -> AuthorizationResult:
    """
    Authorization decision for a target. The ONLY way to legitimately
    start an engagement.

    Args:
        target: URL, hostname, or IP (possibly with port and path)
        operator: Identity of the operator launching the engagement
        have_authorization_flag: True if --i-have-authorization was passed
        override_refused: True if --override-refused was passed
        justification: Required text explaining why a REFUSED target is OK
        interactive: If False, never prompts — REQUIRES_CONFIRM auto-fails
                     unless have_authorization_flag is True
        _input_fn / _print_fn: Test injection points

    Returns:
        AuthorizationResult — caller MUST check .authorized before proceeding
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    cls, reason, resolved_ip = classify_target(target)

    # ── ALWAYS_ALLOWED ────────────────────────────────────────────────────
    if cls == TargetClass.ALWAYS_ALLOWED:
        return AuthorizationResult(
            authorized=True,
            target=target,
            target_class=cls,
            resolved_ip=resolved_ip,
            reason=reason,
            timestamp=timestamp,
            operator=operator,
        )

    # ── ALWAYS_REFUSED ────────────────────────────────────────────────────
    if cls == TargetClass.ALWAYS_REFUSED:
        if not override_refused:
            return AuthorizationResult(
                authorized=False,
                target=target,
                target_class=cls,
                resolved_ip=resolved_ip,
                reason=f"REFUSED: {reason}",
                timestamp=timestamp,
                operator=operator,
            )
        if not justification or len(justification.strip()) < 20:
            return AuthorizationResult(
                authorized=False,
                target=target,
                target_class=cls,
                resolved_ip=resolved_ip,
                reason=f"REFUSED: --override-refused requires --justification of >=20 chars",
                timestamp=timestamp,
                operator=operator,
            )
        # Override granted with justification — log it loudly
        return AuthorizationResult(
            authorized=True,
            target=target,
            target_class=cls,
            resolved_ip=resolved_ip,
            reason=f"OVERRIDE: {reason} | justification: {justification.strip()}",
            timestamp=timestamp,
            operator=operator,
            justification=justification.strip(),
        )

    # ── REQUIRES_CONFIRM ──────────────────────────────────────────────────
    # Public IP / unresolved external — interactive prompt + flag both required.
    if not have_authorization_flag:
        return AuthorizationResult(
            authorized=False,
            target=target,
            target_class=cls,
            resolved_ip=resolved_ip,
            reason=("REFUSED: external target requires --i-have-authorization "
                    f"flag. Detail: {reason}"),
            timestamp=timestamp,
            operator=operator,
        )

    if not interactive:
        # Non-interactive but flag is set — still require explicit env consent.
        # We do NOT silently allow this even with the flag, because misuse of
        # the flag in CI/scripts would be too easy.
        return AuthorizationResult(
            authorized=False,
            target=target,
            target_class=cls,
            resolved_ip=resolved_ip,
            reason=("REFUSED: external target requires interactive confirmation. "
                    "Run from a TTY or use --noninteractive-i-really-mean-it."),
            timestamp=timestamp,
            operator=operator,
        )

    # Interactive prompt — must type "yes" in full
    _print_fn("")
    _print_fn("┌─────────────────────────────────────────────────────────────┐")
    _print_fn("│  ⚠  AUTHORIZATION REQUIRED — EXTERNAL TARGET DETECTED       │")
    _print_fn("└─────────────────────────────────────────────────────────────┘")
    _print_fn(f"  Target:        {target}")
    _print_fn(f"  Resolved IP:   {resolved_ip}")
    _print_fn(f"  Classification:{reason}")
    _print_fn(f"  Operator:      {operator}")
    _print_fn(f"  Time (UTC):    {timestamp}")
    _print_fn("")
    _print_fn("  By typing 'yes' below, you confirm under penalty of law that")
    _print_fn("  you OWN this target or have WRITTEN AUTHORIZATION from the")
    _print_fn("  legal owner to perform a penetration test against it.")
    _print_fn("")
    _print_fn("  Unauthorized testing is a federal crime under 18 U.S.C. § 1030")
    _print_fn("  and equivalent statutes worldwide.")
    _print_fn("")

    try:
        answer = _input_fn("  Type 'yes' to proceed (anything else aborts): ").strip()
    except (EOFError, KeyboardInterrupt):
        answer = ""

    if answer != "yes":
        return AuthorizationResult(
            authorized=False,
            target=target,
            target_class=cls,
            resolved_ip=resolved_ip,
            reason=f"REFUSED: operator declined at prompt (typed: {answer!r})",
            timestamp=timestamp,
            operator=operator,
        )

    return AuthorizationResult(
        authorized=True,
        target=target,
        target_class=cls,
        resolved_ip=resolved_ip,
        reason=f"AUTHORIZED: operator confirmed at prompt | {reason}",
        timestamp=timestamp,
        operator=operator,
    )
