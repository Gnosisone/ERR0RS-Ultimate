"""
ERR0RS ULTIMATE — Operator Tier System
═══════════════════════════════════════════════════════════════════

Three operator tiers control which features are available, scaling
ERR0RS from kid-safe exploration up to full professional offensive
tradecraft. The tier is declared once in .env and applies to every
feature surface that checks it.

TIERS (ascending capability):

  EXPLORE  — default, kid-safe, concept-only
    • No live tool execution against any target
    • Teach content uses chunked-RAG narration
    • BadUSB Payload Studio renders previews with placeholder values
    • No IP auto-fill, no listener spinup
    • No attestation needed

  LEARN    — for students learning offensive security
    • Lab-mode-style demos against 127.0.0.1 with consent
    • IP auto-fill into demos (read-only LAN address detection)
    • BadUSB previews show the user's real LAN IP substituted in
    • Curated demo recipes only (no LLM-authored shell commands)
    • Step-by-step confirmation between demo steps
    • No listener spinup, no working-payload deploy
    • Requires ERR0RS_LAB_MODE=1 in .env

  OPERATE  — full professional toolkit
    • Everything in LEARN, plus:
    • Auto-listener spinup with consent + banner + auto-teardown
    • Working BadUSB payloads with user's IP/port baked in (deploy button)
    • LLM-authored demo commands allowed (with display-before-execute)
    • Multi-host targets if the safety gate authorizes them
    • Requires ERR0RS_OPERATOR_TIER=operate in .env
    • REQUIRES ONE-TIME ATTESTATION (see operator_attestation())
      Acceptance is recorded to ~/.err0rs/operator_acceptance.json
      with timestamp, hostname, hashed system fingerprint.

DESIGN PRINCIPLES:
  1. Default to safety. The default tier (no env var set) is EXPLORE.
  2. Declared, not detected. A user must explicitly opt into LEARN/OPERATE
     via .env. No "auto-promote" based on usage patterns.
  3. One-time friction. OPERATE attestation happens once per device.
     After that, no per-feature friction.
  4. Auditable. Every OPERATE acceptance is logged with timestamp.
     If the legal record matters (it might, someday), it exists.
  5. Composable with the safety gate. Tier controls FEATURE availability;
     the safety gate (src/security/gate.py) still applies to every tool
     execution. The gate is the runtime authority; tier is the policy
     authority.

USAGE:
    from src.security.operator_tier import (
        OperatorTier, current_tier, require_tier, ensure_attestation
    )

    # Feature gate
    if current_tier() < OperatorTier.LEARN:
        return "Demo mode requires LEARN or OPERATE tier."

    # Hard requirement (raises if not met)
    require_tier(OperatorTier.OPERATE)  # raises TierRequired

    # First-run check (call from launcher startup)
    if not ensure_attestation():
        sys.exit(1)  # user declined or skipped attestation
"""
from __future__ import annotations

import enum
import hashlib
import json
import logging
import os
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Acceptance record lives in the user's home so it survives across
# checkouts, reinstalls, and project moves. Per-device, not per-repo.
ACCEPTANCE_PATH = Path.home() / ".err0rs" / "operator_acceptance.json"

# The exact phrase a user must type to accept OPERATE responsibility.
# Long enough to be deliberate, short enough that a serious user will
# read it. Mirrors the language in docs/SAFETY_GATE.md.
ATTESTATION_PHRASE = (
    "I am a professional and I accept responsibility under CFAA "
    "for every action taken with this tool."
)


class OperatorTier(enum.IntEnum):
    """Ordered tiers — higher value = more capability."""
    EXPLORE = 0
    LEARN   = 1
    OPERATE = 2

    @classmethod
    def from_env(cls) -> "OperatorTier":
        """Parse ERR0RS_OPERATOR_TIER env var. Unknown values → EXPLORE."""
        val = (os.environ.get("ERR0RS_OPERATOR_TIER", "") or "").strip().lower()
        return {
            "explore": cls.EXPLORE,
            "learn":   cls.LEARN,
            "operate": cls.OPERATE,
        }.get(val, cls.EXPLORE)

    def label(self) -> str:
        return self.name


class TierRequired(Exception):
    """Raised when a feature requires a higher tier than the user has."""
    def __init__(self, required: OperatorTier, actual: OperatorTier):
        self.required = required
        self.actual   = actual
        super().__init__(
            f"This feature requires tier {required.label()} or higher "
            f"(current: {actual.label()}). Set ERR0RS_OPERATOR_TIER="
            f"{required.label().lower()} in your .env to enable it."
        )


def current_tier() -> OperatorTier:
    """Return the active tier. Reads env each call so .env changes take
    effect across restarts without code reload."""
    return OperatorTier.from_env()


def require_tier(tier: OperatorTier) -> None:
    """Raise TierRequired if current tier is below the required one."""
    cur = current_tier()
    if cur < tier:
        raise TierRequired(tier, cur)


# ── Attestation flow ─────────────────────────────────────────────────────

def _device_fingerprint() -> str:
    """Compute a stable hash of host identity. Used in the acceptance
    record so it's tied to a specific device, not transferable.

    Includes hostname + platform + machine architecture. NOT a perfect
    fingerprint — virtualization can spoof it — but enough to make
    casual transfer of acceptance records non-trivial."""
    parts = [
        socket.gethostname(),
        platform.system(),
        platform.release(),
        platform.machine(),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _load_acceptance() -> Optional[dict]:
    """Return existing acceptance record or None."""
    try:
        if not ACCEPTANCE_PATH.exists():
            return None
        return json.loads(ACCEPTANCE_PATH.read_text())
    except Exception as e:
        log.warning(f"could not read acceptance record: {e}")
        return None


def has_valid_attestation() -> bool:
    """True if a valid OPERATE acceptance exists for this device."""
    rec = _load_acceptance()
    if not rec:
        return False
    if rec.get("phrase") != ATTESTATION_PHRASE:
        return False
    if rec.get("device_fingerprint") != _device_fingerprint():
        return False
    if rec.get("revoked"):
        return False
    return True


def _save_acceptance(extra_notes: str = "") -> Path:
    """Persist the acceptance record. Called only after a user types
    the attestation phrase verbatim."""
    ACCEPTANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "phrase":             ATTESTATION_PHRASE,
        "accepted_at_utc":    datetime.now(timezone.utc).isoformat(),
        "accepted_at_local":  datetime.now().isoformat(),
        "hostname":           socket.gethostname(),
        "platform":           f"{platform.system()} {platform.release()} ({platform.machine()})",
        "device_fingerprint": _device_fingerprint(),
        "user":               os.environ.get("USER", "unknown"),
        "tier_when_accepted": OperatorTier.OPERATE.label(),
        "notes":              extra_notes,
        "revoked":            False,
    }
    ACCEPTANCE_PATH.write_text(json.dumps(record, indent=2))
    try:
        ACCEPTANCE_PATH.chmod(0o600)  # private to user
    except Exception:
        pass
    return ACCEPTANCE_PATH


def prompt_attestation(stdin=None, stdout=None) -> bool:
    """Show the attestation prompt and require the user to type the
    exact phrase. Returns True if accepted, False otherwise.

    stdin/stdout are parameters for testability; defaults are sys.stdin/stdout."""
    _in  = stdin  or sys.stdin
    _out = stdout or sys.stdout

    banner = (
        "\n"
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║                ERR0RS — OPERATE TIER ATTESTATION                     ║\n"
        "║                                                                      ║\n"
        "║  You have set ERR0RS_OPERATOR_TIER=operate in your .env.            ║\n"
        "║  This unlocks the full professional offensive toolkit:               ║\n"
        "║                                                                      ║\n"
        "║    • Auto-IP injection into payloads and demos                       ║\n"
        "║    • Automatic listener spinup (with per-action consent)             ║\n"
        "║    • Working BadUSB payloads (no template placeholders)              ║\n"
        "║    • LLM-authored demo commands                                      ║\n"
        "║    • Multi-host targeting (still gated by authorization records)     ║\n"
        "║                                                                      ║\n"
        "║  WHAT THIS MEANS:                                                    ║\n"
        "║                                                                      ║\n"
        "║  • You are solely responsible for every command ERR0RS runs at       ║\n"
        "║    your direction. The Computer Fraud and Abuse Act                  ║\n"
        "║    (18 U.S.C. § 1030) and equivalent worldwide statutes apply.       ║\n"
        "║  • The ERR0RS safety gate still refuses unauthorized targets unless  ║\n"
        "║    you have an authorization record OR lab mode is active.           ║\n"
        "║  • This acceptance is recorded with timestamp + device fingerprint   ║\n"
        "║    at ~/.err0rs/operator_acceptance.json.                            ║\n"
        "║  • You can revoke OPERATE tier any time by removing that file or by  ║\n"
        "║    setting ERR0RS_OPERATOR_TIER=explore in .env.                     ║\n"
        "║                                                                      ║\n"
        "║  To proceed, type the following phrase EXACTLY (or anything else     ║\n"
        "║  to decline):                                                        ║\n"
        "║                                                                      ║\n"
        "║    \"I am a professional and I accept responsibility under CFAA      ║\n"
        "║     for every action taken with this tool.\"                         ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝\n"
        "\n> "
    )
    _out.write(banner)
    _out.flush()

    try:
        typed = _in.readline().strip()
    except (EOFError, KeyboardInterrupt):
        _out.write("\n[attestation cancelled]\n")
        return False

    if typed != ATTESTATION_PHRASE:
        _out.write(
            "\n[attestation phrase did not match — OPERATE tier remains locked]\n"
            "ERR0RS will run in EXPLORE mode for this session. Re-run when ready.\n\n"
        )
        return False

    path = _save_acceptance()
    _out.write(
        f"\n[✓ OPERATE tier accepted — recorded to {path}]\n"
        "Full toolkit unlocked. Use it responsibly.\n\n"
    )
    return True


def ensure_attestation(interactive: bool = True) -> bool:
    """Called at launcher startup. Returns True if the current tier is
    permitted (either non-OPERATE, or OPERATE with valid attestation).

    If the user set OPERATE but has no valid acceptance:
      - interactive=True: prompts; returns whether they accepted
      - interactive=False: returns False (used by service installs)
    """
    tier = current_tier()
    if tier < OperatorTier.OPERATE:
        return True
    if has_valid_attestation():
        return True
    if not interactive:
        log.warning(
            "OPERATE tier requested but no attestation on file. "
            "Run interactively to accept, or set ERR0RS_OPERATOR_TIER="
            "explore for non-interactive use."
        )
        return False
    return prompt_attestation()


def revoke_attestation() -> bool:
    """Set revoked=True in the acceptance record (preserves history)."""
    rec = _load_acceptance()
    if not rec:
        return False
    rec["revoked"]      = True
    rec["revoked_at"]   = datetime.now(timezone.utc).isoformat()
    ACCEPTANCE_PATH.write_text(json.dumps(rec, indent=2))
    return True


# ── Inspection helpers ───────────────────────────────────────────────────

def tier_summary() -> dict:
    """Return a serializable summary of the current tier state.
    Useful for the preflight check and the UI 'about ERR0RS' panel."""
    tier = current_tier()
    rec  = _load_acceptance()
    return {
        "tier":               tier.label(),
        "tier_value":         int(tier),
        "lab_mode":           os.environ.get("ERR0RS_LAB_MODE", "0") in ("1", "true", "yes", "on"),
        "has_attestation":    has_valid_attestation(),
        "acceptance_path":    str(ACCEPTANCE_PATH),
        "acceptance_at":      rec.get("accepted_at_local") if rec else None,
        "acceptance_revoked": bool(rec.get("revoked")) if rec else False,
    }


# ── Test helpers ─────────────────────────────────────────────────────────

def _reset_for_testing():
    """Remove any acceptance record. Tests only."""
    try:
        if ACCEPTANCE_PATH.exists():
            ACCEPTANCE_PATH.unlink()
    except Exception:
        pass
