"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — OPERATOR PROFILE MODULE                ║
║              src/core/operator_profile.py                         ║
║                                                                  ║
║  Consolidates everything about the human using ERR0RS:           ║
║    - Per-launch ethics gate (full re-acceptance every boot)      ║
║    - Lesson progress tracking (which teach topics they've done)  ║
║    - Combined profile view for the Operator Profile UI panel     ║
║    - Profile reset with automatic backup                         ║
║                                                                  ║
║  Reads from existing files (profile.json, progression.json,      ║
║  preferences.json, mission_state.json) — does not duplicate.     ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

ERR0RS_DIR        = os.path.expanduser("~/.err0rs")
ETHICS_ACK_FILE   = os.path.join(ERR0RS_DIR, "session_ethics_ack.json")
LESSON_FILE       = os.path.join(ERR0RS_DIR, "lesson_progress.json")

_LOCK = threading.Lock()

# Skill level names used in greeting cards and profile display.
# Mirrors the values from the onboarding wizard's skill assessment.
SKILL_LEVEL_NAMES = {
    0: "🔰 Total Beginner",
    1: "🎯 CTF Player",
    2: "⚡ Intermediate",
    3: "🔥 Advanced",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: str, default: Dict) -> Dict:
    """Load a JSON file, returning default on missing/corrupt."""
    if not os.path.exists(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _write_json(path: str, data: Dict) -> None:
    """Persist a JSON file atomically (write to tmp + rename)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)


# ── ETHICS GATE ──────────────────────────────────────────────────────────────
# Per-launch ethics agreement. State lives in session_ethics_ack.json with a
# pid field — the file is invalidated when the launcher PID changes (every
# fresh start), forcing re-acceptance. Pi reboot also clears this naturally
# since all PIDs change.

def is_ethics_ack_current(current_launcher_pid: int) -> bool:
    """
    Return True if the user has accepted ethics for THIS launcher process.
    False if first launch, after reboot, after relaunch, or after manual clear.
    """
    state = _read_json(ETHICS_ACK_FILE, {})
    return state.get("launcher_pid") == current_launcher_pid and state.get("agreed") is True


def record_ethics_ack(current_launcher_pid: int) -> Dict:
    """Mark ethics acknowledged for the current launcher PID."""
    state = {
        "agreed":          True,
        "agreed_at":       _now_iso(),
        "launcher_pid":    current_launcher_pid,
    }
    _write_json(ETHICS_ACK_FILE, state)
    return state


def get_ethics_agreement_text() -> Dict:
    """The exact text shown in the gate. Kept here so legal can review it."""
    return {
        "version": "1.0",
        "title":   "ERR0RS ETHICAL USE AGREEMENT",
        "preamble": (
            "ERR0RS is a fully-functional offensive security platform. "
            "By using it you agree to the following terms."
        ),
        "clauses": [
            "I will ONLY use ERR0RS against systems I OWN or have EXPLICIT WRITTEN PERMISSION to test.",
            "I understand that running these tools against unauthorized targets is a CRIME in most jurisdictions (e.g. CFAA in the US, Computer Misuse Act in the UK).",
            "I understand ERR0RS is for AUTHORIZED PENETRATION TESTING, CTF CHALLENGES, and PERSONAL LAB USE only.",
            "I accept that I am SOLELY RESPONSIBLE for how I use this software. The authors and contributors disclaim all liability.",
            "I will respect the privacy and data of others. I will not exfiltrate, share, or misuse anything I discover during authorized testing.",
        ],
        "footer": "Click 'I AGREE' below to acknowledge these terms and continue.",
    }


# ── LESSON PROGRESS ──────────────────────────────────────────────────────────
# Tracks which teach topics the user has read/completed. Used by the
# "Continue Lessons" button to pick the next unread topic, and by the
# Operator Profile panel to show a 5/23 progress badge.

def _default_lesson_state() -> Dict:
    return {
        "schema_version":    1,
        "lessons_completed": [],   # topic IDs user marked done
        "lessons_started":   [],   # topic IDs user opened but didn't finish
        "last_lesson":       None, # the most recent topic — used for "continue"
        "last_opened_at":    None,
    }


def get_lesson_state() -> Dict:
    """Load lesson progress and join with the full topic list from teach_engine."""
    state = _read_json(LESSON_FILE, _default_lesson_state())
    # Backfill any missing default keys (forward-compat)
    for k, v in _default_lesson_state().items():
        state.setdefault(k, v)

    # Get the full topic list. Wrapped in try because teach_engine may not
    # always be importable in test contexts.
    try:
        from src.core.teach_engine import list_topics
        all_topics = list_topics()
    except Exception:
        all_topics = []

    completed_set = set(state["lessons_completed"])
    started_set   = set(state["lessons_started"])

    # Annotate each topic with status for UI rendering
    topics_view = []
    for t in all_topics:
        status = "completed" if t in completed_set else "started" if t in started_set else "new"
        topics_view.append({"id": t, "status": status})

    return {
        "lessons_completed": state["lessons_completed"],
        "lessons_started":   state["lessons_started"],
        "last_lesson":       state["last_lesson"],
        "total_topics":      len(all_topics),
        "topics":            topics_view,
        "next_unread":       next((t for t in all_topics if t not in completed_set), None),
    }


def mark_lesson(topic: str, status: str) -> Dict:
    """
    Update lesson status. status ∈ {"started", "completed"}.
    Idempotent: marking the same topic completed twice is a no-op.
    Returns the new full state (same shape as get_lesson_state).
    """
    if status not in ("started", "completed"):
        return get_lesson_state()

    state = _read_json(LESSON_FILE, _default_lesson_state())
    started   = set(state.get("lessons_started",   []))
    completed = set(state.get("lessons_completed", []))

    if status == "started":
        # Don't downgrade a completed lesson back to "started"
        if topic not in completed:
            started.add(topic)
    else:  # completed
        completed.add(topic)
        started.discard(topic)  # completed implies no longer "in progress"

    state["lessons_started"]   = sorted(started)
    state["lessons_completed"] = sorted(completed)
    state["last_lesson"]       = topic
    state["last_opened_at"]    = _now_iso()
    _write_json(LESSON_FILE, state)
    return get_lesson_state()


# ── FULL OPERATOR PROFILE VIEW ───────────────────────────────────────────────
# One endpoint, everything the UI needs in one shot. Joins profile.json,
# progression.json, preferences.json, mission_state, and lesson_state into
# a single payload sized for the Operator Profile panel.

def get_full_profile() -> Dict:
    """
    Return the consolidated view used by the Operator Profile panel and the
    welcome-back greeting card. Pulls from existing files only — does not
    duplicate state.
    """
    profile_data    = _read_json(os.path.join(ERR0RS_DIR, "profile.json"), {})
    prefs_data      = _read_json(os.path.join(ERR0RS_DIR, "preferences.json"), {})
    progression     = _read_json(os.path.join(ERR0RS_DIR, "progression.json"), {})

    # Get live mission state (in case it changed in this session)
    try:
        from src.core.mission_state import load_state as _load_mission
        mission_state = _load_mission()
    except Exception:
        mission_state = {}

    lesson_state = get_lesson_state()

    skill_level     = prefs_data.get("skill_level", 0)
    skill_name      = SKILL_LEVEL_NAMES.get(skill_level, "🔰 Operator")

    return {
        # Identity
        "name":               prefs_data.get("name", "Operator"),
        "skill_level":        skill_level,
        "skill_name":         skill_name,
        "mode":               prefs_data.get("mode", "guided"),
        "agreed_to_tos":      prefs_data.get("agreed_to_tos", False),

        # Sessions
        "sessions":           profile_data.get("sessions", 0),
        "joined":             profile_data.get("joined") or progression.get("joined"),

        # Progression
        "xp":                 progression.get("xp", 0),
        "level":              progression.get("level", 0),
        "total_events":       progression.get("total_events", 0),
        "streak_days":        progression.get("streak_days", 0),
        "achievements":       progression.get("achievements", []),
        "domains":            progression.get("domains", {}),

        # Missions
        "active_mission":     mission_state.get("active_mission"),
        "missions_completed": len(mission_state.get("completion_history", [])),
        "completion_history": mission_state.get("completion_history", []),

        # Lessons
        "lessons_completed_count": len(lesson_state["lessons_completed"]),
        "lessons_total":           lesson_state["total_topics"],
        "next_lesson":             lesson_state["next_unread"],
        "last_lesson":             lesson_state["last_lesson"],

        # Toggles (read from prefs)
        "teach_mode":         prefs_data.get("show_explanations", True),
        "auto_coach":         prefs_data.get("auto_coach", True),
    }


# ── TOGGLES ──────────────────────────────────────────────────────────────────
# Setters for the three mode flags in the Operator Profile panel. All three
# live in preferences.json (the existing onboarding file) so we don't fragment.

def set_toggle(key: str, value: bool) -> Dict:
    """
    Update a toggle in preferences.json. Whitelisted keys only — refuses to
    write arbitrary keys so a malicious request can't poison the prefs file.
    """
    allowed = {"teach_mode", "auto_coach", "beginner_mode"}
    if key not in allowed:
        return {"error": f"unknown toggle key '{key}'"}

    prefs_file = os.path.join(ERR0RS_DIR, "preferences.json")
    prefs = _read_json(prefs_file, {})

    # Map our public toggle names to the actual preference keys used elsewhere.
    # show_explanations is the legacy name for teach_mode in onboarding.py.
    pref_key_map = {
        "teach_mode":    "show_explanations",
        "auto_coach":    "auto_coach",
        "beginner_mode": "beginner_mode",
    }
    prefs[pref_key_map[key]] = bool(value)
    _write_json(prefs_file, prefs)
    return {"ok": True, "key": key, "value": bool(value)}


# ── PROFILE RESET ────────────────────────────────────────────────────────────
# Destructive. Creates a backup directory in case the user regrets it.

def reset_profile(confirm: bool = False) -> Dict:
    """
    Wipe all profile state. Confirm must be True; this is a safety against
    accidental API calls. Backs up ~/.err0rs/ to a timestamped folder first.
    Returns {success, backup_path} or {error}.
    """
    if not confirm:
        return {"error": "confirm=True required to reset profile"}

    if not os.path.exists(ERR0RS_DIR):
        return {"success": True, "note": "nothing to reset", "backup_path": None}

    # Backup first. Use a sibling directory so we don't recurse into ourselves.
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.expanduser(f"~/.err0rs.backup_{ts}")
    try:
        shutil.copytree(ERR0RS_DIR, backup_dir)
    except Exception as e:
        return {"error": f"backup failed: {e}"}

    # Files to wipe. We do NOT wipe the backup we just created (different dir).
    # listeners.log is kept (operational, not user-progress).
    files_to_remove = [
        "profile.json",
        "progression.json",
        "preferences.json",
        "mission_state.json",
        "onboarding_complete.json",
        "lesson_progress.json",
        "session_ethics_ack.json",
    ]
    removed = []
    for fname in files_to_remove:
        path = os.path.join(ERR0RS_DIR, fname)
        if os.path.exists(path):
            try:
                os.remove(path)
                removed.append(fname)
            except Exception:
                pass

    return {
        "success":     True,
        "backup_path": backup_dir,
        "removed":     removed,
        "note":        "Profile reset complete. Restart the launcher or hard-refresh the browser to re-onboard.",
    }
