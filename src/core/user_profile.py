"""
ERR0RS User Profile
====================
Persistent operator profile that drives adaptive coaching verbosity.

Philosophy:
-----------
A professor that explains "what is JWT" to a senior pen-tester is annoying.
A professor that uses jargon with a first-week student is useless. The
adaptive verbosity isn't optional — it's the difference between Professor
Mode being a feature operators love vs one they disable on day 2.

Schema:
-------
    {
      "operator_id":         "eros",
      "experience_level":    "novice" | "intermediate" | "expert",
      "concepts_explained":  {"jwt_alg_none": {"count": 3, "last": "ISO-8601"}},
      "concepts_mastered":   ["sql_union_basic", "xss_reflected_basic"],
      "vocab_calibration":   {"RFC1918": "private network IPs"},
      "preferred_techniques": ["jwt_attacks", "ssti", "nosql"],
      "skip_explanations":   ["what_is_nmap"],
      "sessions_count":      47,
      "first_seen":          "ISO-8601",
      "last_seen":           "ISO-8601",
      "schema_version":      1
    }

Storage:
--------
    Default: ~/.err0rs/profile.json
    Override via constructor for tests / multi-operator scenarios

Mastery inference:
------------------
    - Concept asked about (user question)             → -1 confidence
    - Concept used in advanced cmd without asking     → +1 confidence
    - Concept appears 5x without question             → marked mastered
    - 90 days no activity on concept                  → mastery decays
    - Operator explicit "I know X" / "skip X"         → forced to mastered

Author: Gary Holden Schneider (Eros) | Sprint 04 Workstream B
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────────

SCHEMA_VERSION = 1

# How long before a "mastered" concept needs reproof
MASTERY_DECAY_DAYS = 90

# How recently we count "explained" as "don't re-explain"
RECENT_EXPLANATION_DAYS = 30

# How many times a concept must appear without a question before we infer mastery
MASTERY_INFERENCE_THRESHOLD = 5

# Valid experience levels (closed enum — no free-form strings)
VALID_LEVELS = {"novice", "intermediate", "expert"}

# Default vocab calibrations applied at the novice level only
# (substitute the jargon → plain phrase when speaking to a novice)
DEFAULT_NOVICE_VOCAB = {
    "RFC1918":          "private network IPs",
    "loopback":         "your own machine (127.0.0.1)",
    "TLD":              "top-level domain (the .com / .gov part)",
    "fingerprint":      "identify what software/version is running",
    "enumeration":      "discovery — listing what's accessible",
    "kill chain":       "the standard sequence of pen-test phases",
    "MITRE ATT&CK":     "the standard catalog of attacker techniques",
    "RBAC":             "role-based access control (admin vs user perms)",
    "auth bypass":      "logging in without valid credentials",
    "lateral movement": "moving from one compromised machine to another",
    "C2":               "command and control (the attacker's remote server)",
    "exfiltrate":       "steal data out of the network",
    "OPSEC":            "operational security — avoiding detection",
    "TTP":              "tactics/techniques/procedures (how attackers operate)",
    "POST":             "an HTTP request that submits data",
    "GET":              "an HTTP request that fetches a page",
    "querystring":      "the URL parameters after the '?' symbol",
    "payload":          "the actual attack data we send",
    "CVE":              "the public ID for a known vulnerability",
    "CWE":              "the category of a vulnerability (a class of bug)",
    "PoC":              "proof of concept (a demo showing it works)",
    "OOB":              "out-of-band (the target talks back via a channel we control, like DNS)",
    "SAST":             "static code analysis (scanning source for bugs)",
    "DAST":             "dynamic scanning (testing the running app)",
    "0day":             "an unknown vulnerability with no patch yet",
    "n-day":            "a known vulnerability that may or may not be patched",
}


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class ConceptStats:
    """How often a concept has been explained, and when last."""
    count: int = 0
    last:  str = ""        # ISO-8601 UTC

    def touch(self) -> None:
        self.count += 1
        self.last = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, d: dict) -> "ConceptStats":
        return cls(count=int(d.get("count", 0)), last=str(d.get("last", "")))


@dataclass
class UserProfile:
    """
    Persistent operator profile. All fields have safe defaults so a fresh
    profile (no file on disk) is valid out of the box.
    """
    operator_id:           str
    experience_level:      str       = "novice"
    concepts_explained:    dict      = field(default_factory=dict)   # name → ConceptStats
    concepts_mastered:     list      = field(default_factory=list)
    vocab_calibration:     dict      = field(default_factory=dict)
    preferred_techniques:  list      = field(default_factory=list)
    skip_explanations:     list      = field(default_factory=list)
    sessions_count:        int       = 0
    first_seen:            str       = ""
    last_seen:             str       = ""
    schema_version:        int       = SCHEMA_VERSION

    # ── Construction / serialization ──────────────────────────────────────

    def __post_init__(self):
        if self.experience_level not in VALID_LEVELS:
            raise ValueError(
                f"experience_level must be one of {sorted(VALID_LEVELS)}, "
                f"got {self.experience_level!r}"
            )
        # Normalize concepts_explained dict values into ConceptStats
        normalized: dict[str, ConceptStats] = {}
        for k, v in (self.concepts_explained or {}).items():
            if isinstance(v, ConceptStats):
                normalized[k] = v
            elif isinstance(v, dict):
                normalized[k] = ConceptStats.from_dict(v)
            else:
                # Defensively skip garbage
                continue
        self.concepts_explained = normalized
        # De-dup mastered list defensively
        self.concepts_mastered = sorted(set(self.concepts_mastered))
        if not self.first_seen:
            self.first_seen = datetime.now(timezone.utc).isoformat()
        if not self.last_seen:
            self.last_seen = self.first_seen

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict."""
        return {
            "operator_id":          self.operator_id,
            "experience_level":     self.experience_level,
            "concepts_explained":   {k: asdict(v) for k, v in self.concepts_explained.items()},
            "concepts_mastered":    sorted(set(self.concepts_mastered)),
            "vocab_calibration":    dict(self.vocab_calibration),
            "preferred_techniques": list(self.preferred_techniques),
            "skip_explanations":    sorted(set(self.skip_explanations)),
            "sessions_count":       self.sessions_count,
            "first_seen":           self.first_seen,
            "last_seen":            self.last_seen,
            "schema_version":       self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserProfile":
        """Deserialize from JSON dict; tolerates missing/extra fields."""
        operator_id = str(d.get("operator_id", "default"))
        level       = d.get("experience_level", "novice")
        if level not in VALID_LEVELS:
            level = "novice"
        return cls(
            operator_id=operator_id,
            experience_level=level,
            concepts_explained=d.get("concepts_explained", {}) or {},
            concepts_mastered=list(d.get("concepts_mastered", []) or []),
            vocab_calibration=dict(d.get("vocab_calibration", {}) or {}),
            preferred_techniques=list(d.get("preferred_techniques", []) or []),
            skip_explanations=list(d.get("skip_explanations", []) or []),
            sessions_count=int(d.get("sessions_count", 0)),
            first_seen=str(d.get("first_seen", "")),
            last_seen=str(d.get("last_seen", "")),
            schema_version=int(d.get("schema_version", SCHEMA_VERSION)),
        )

    # ── Vocab adaptation ──────────────────────────────────────────────────

    def adapt_text(self, text: str) -> str:
        """
        Apply jargon substitutions for the current experience level.

        - novice:       apply DEFAULT_NOVICE_VOCAB + custom calibration
        - intermediate: apply only operator's explicit calibrations
        - expert:       no substitutions

        This is a simple word-boundary substitution. It's not natural-language-
        perfect — it's a "good enough" first pass that the LLM-generated text
        gets cleaned up with before display.
        """
        if not text or self.experience_level == "expert":
            return text or ""

        substitutions = dict(self.vocab_calibration)
        if self.experience_level == "novice":
            # Novice gets the full default vocab too. Operator overrides win.
            for k, v in DEFAULT_NOVICE_VOCAB.items():
                substitutions.setdefault(k, v)

        out = text
        for jargon, plain in substitutions.items():
            # Case-sensitive whole-word substitution. We deliberately skip
            # smarter substitutions (regex etc.) — false positives are worse
            # than missed substitutions for a coaching tool.
            out = _word_boundary_replace(out, jargon, plain)
        return out

    # ── Concept tracking ──────────────────────────────────────────────────

    def has_seen(self, concept: str, within_days: int = RECENT_EXPLANATION_DAYS) -> bool:
        """
        True if this concept was explained within the given window.
        Used to decide "do we re-explain?" — if recently explained, skip.
        """
        stats = self.concepts_explained.get(concept)
        if not stats or not stats.last:
            return False
        try:
            then = datetime.fromisoformat(stats.last)
        except ValueError:
            return False
        delta = datetime.now(timezone.utc) - then
        return delta <= timedelta(days=within_days)

    def has_mastered(self, concept: str) -> bool:
        """
        True if operator has mastered this concept (no need to explain at all).
        Mastery decays after MASTERY_DECAY_DAYS — re-explained at least once after
        that.
        """
        if concept in self.skip_explanations:
            return True
        if concept not in self.concepts_mastered:
            return False
        # Check decay
        stats = self.concepts_explained.get(concept)
        if stats and stats.last:
            try:
                then = datetime.fromisoformat(stats.last)
                if datetime.now(timezone.utc) - then > timedelta(days=MASTERY_DECAY_DAYS):
                    return False
            except ValueError:
                pass
        return True

    def mark_explained(self, concept: str) -> None:
        """Record that we just explained this concept."""
        if concept not in self.concepts_explained:
            self.concepts_explained[concept] = ConceptStats()
        self.concepts_explained[concept].touch()
        # Auto-infer mastery if the concept has been explained enough times
        # without a question being asked about it.
        if (self.concepts_explained[concept].count >= MASTERY_INFERENCE_THRESHOLD
            and concept not in self.concepts_mastered):
            self.concepts_mastered.append(concept)
            self.concepts_mastered.sort()

    def mark_questioned(self, concept: str) -> None:
        """
        Record that operator asked about this concept — they don't know it.
        Removes from mastered list if present (knowledge decay).
        """
        if concept in self.concepts_mastered:
            self.concepts_mastered.remove(concept)
        # Reset the count so we don't immediately re-mark mastered
        if concept in self.concepts_explained:
            self.concepts_explained[concept].count = 0

    def mark_mastered(self, concept: str) -> None:
        """Operator explicitly said 'I know this — don't explain again'."""
        if concept not in self.concepts_mastered:
            self.concepts_mastered.append(concept)
            self.concepts_mastered.sort()

    def add_skip(self, concept: str) -> None:
        """Operator said 'never explain this concept'."""
        if concept not in self.skip_explanations:
            self.skip_explanations.append(concept)
            self.skip_explanations.sort()

    # ── Session tracking ──────────────────────────────────────────────────

    def begin_session(self) -> None:
        """Call at start of an engagement / brainstorm / lesson."""
        self.sessions_count += 1
        self.last_seen = datetime.now(timezone.utc).isoformat()

    def update_from_session(self, audit_events: list[dict]) -> None:
        """
        Infer mastery / level changes from observed behavior in a session.

        Heuristics:
          - 3 sessions in a row in FULL_AUTO mode without --professor flag
            -> +1 toward expert (knows what they're doing)
          - User canceled at exploitation phase 3+ times
            -> stay novice/intermediate (cautious operator, more explanations)
          - User asked NO questions in a session of 10+ events
            -> +1 toward expert
          - User asked 5+ questions in one session
            -> reset to intermediate at most
        """
        if not audit_events:
            return

        questions = sum(1 for e in audit_events
                        if e.get("event") == "operator_response"
                        and "?" in str(e.get("data", {}).get("text", "")))
        approvals = sum(1 for e in audit_events if e.get("event") == "operator_approve")
        denies    = sum(1 for e in audit_events if e.get("event") == "operator_deny")
        events_n  = len(audit_events)

        # Promote: novice -> intermediate after no questions in a 10+ event session
        if (self.experience_level == "novice" and events_n >= 10 and questions == 0
            and approvals >= 1):
            self.experience_level = "intermediate"

        # Promote: intermediate -> expert after no questions, 20+ events, 0 denies
        elif (self.experience_level == "intermediate" and events_n >= 20
              and questions == 0 and denies == 0 and approvals >= 3):
            self.experience_level = "expert"

        # Demote: expert -> intermediate if many questions
        elif self.experience_level == "expert" and questions >= 5:
            self.experience_level = "intermediate"

    # ── Persistence ───────────────────────────────────────────────────────

    @classmethod
    def default_path(cls) -> Path:
        """Default profile location: ~/.err0rs/profile.json"""
        return Path.home() / ".err0rs" / "profile.json"

    @classmethod
    def load(cls, path: Optional[Path] = None,
             operator_id: Optional[str] = None) -> "UserProfile":
        """
        Load profile from disk. Returns a fresh default profile if the file
        doesn't exist or is corrupt.
        """
        p = Path(path) if path else cls.default_path()
        op = operator_id or os.environ.get("USER", "default")

        if not p.exists():
            return cls(operator_id=op)

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Corrupt file — back it up and start fresh rather than crash
            backup = p.with_suffix(f".json.corrupt.{int(datetime.now().timestamp())}")
            try:
                p.rename(backup)
            except OSError:
                pass
            return cls(operator_id=op)

        # Schema migration hook — if version differs, migrate
        version = int(data.get("schema_version", 0))
        if version < SCHEMA_VERSION:
            data = cls._migrate_schema(data, version)

        return cls.from_dict(data)

    def save(self, path: Optional[Path] = None) -> Path:
        """Atomically write profile to disk. Returns the path written."""
        p = Path(path) if path else self.default_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write via tmp file + rename
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True),
                        encoding="utf-8")
        tmp.replace(p)
        return p

    @staticmethod
    def _migrate_schema(data: dict, from_version: int) -> dict:
        """Future-proof migration hook. Currently no migrations needed."""
        # When we bump SCHEMA_VERSION later, add migration logic here.
        # E.g. if from_version == 0: data["new_field"] = default_value
        data["schema_version"] = SCHEMA_VERSION
        return data


# ── Helpers ────────────────────────────────────────────────────────────────

def _word_boundary_replace(text: str, needle: str, replacement: str) -> str:
    """
    Replace `needle` with `replacement` only at word boundaries.
    More careful than str.replace — avoids "POST" inside "POSTGRESQL" matching.
    """
    import re as _re
    # Escape regex specials in the needle, then wrap in word-boundary anchors.
    # Use case-sensitive matching — security jargon often differs by case
    # (CVE vs cve) and we want to preserve intent.
    pattern = r"(?<![A-Za-z0-9_])" + _re.escape(needle) + r"(?![A-Za-z0-9_])"
    return _re.sub(pattern, replacement, text)


# ── Module-level singleton ─────────────────────────────────────────────────

_profile_lock = threading.Lock()
_profile: Optional[UserProfile] = None


def get_profile(reload: bool = False) -> UserProfile:
    """
    Get the singleton current profile. Loads from disk on first call.
    Pass reload=True to force re-read (e.g. after external edit).
    """
    global _profile
    with _profile_lock:
        if _profile is None or reload:
            _profile = UserProfile.load()
        return _profile


def reset_profile() -> None:
    """For tests — clear the singleton so the next get_profile() reloads."""
    global _profile
    with _profile_lock:
        _profile = None
