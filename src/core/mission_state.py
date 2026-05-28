"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — PERSISTENT MISSION STATE               ║
║              src/core/mission_state.py                            ║
║                                                                  ║
║  Server-authoritative mission progress tracking. Survives reboots,║
║  browser refreshes, multiple tabs. Anchored to ~/.err0rs/         ║
║  mission_state.json — single source of truth.                    ║
║                                                                  ║
║  Architecture:                                                   ║
║    - Frontend reads state on every page load via /api/mission/state ║
║    - Frontend signals tool completions via /api/mission/advance   ║
║    - Backend decides if completion counts (matches expected tool) ║
║    - Returns updated state for re-render                          ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, List

STATE_FILE = os.path.expanduser("~/.err0rs/mission_state.json")
_LOCK = threading.Lock()
SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_state() -> Dict:
    return {
        "schema_version":     SCHEMA_VERSION,
        "active_mission":     None,
        "current_step":       0,
        "steps_completed":    [],
        "started_at":         None,
        "last_advance_at":    None,
        "completion_history": [],
    }


def load_state() -> Dict:
    """Load the persisted mission state. Returns default if missing/corrupt."""
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        defaults = _default_state()
        for k, v in defaults.items():
            state.setdefault(k, v)
        return state
    except (json.JSONDecodeError, OSError):
        return _default_state()


def save_state(state: Dict) -> None:
    """Persist state to disk. Creates ~/.err0rs/ if needed."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with _LOCK:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)


def _tool_from_command(cmd: str) -> str:
    """Extract the tool name from a command string."""
    if not cmd:
        return ""
    first = cmd.strip().split()[0] if cmd.strip() else ""
    return first.split("/")[-1].lower()


def _mission_def(mission_id: str) -> Optional[Dict]:
    """Look up a mission definition from onboarding.FIRST_MISSIONS."""
    try:
        from src.core.onboarding import FIRST_MISSIONS
        return FIRST_MISSIONS.get(mission_id)
    except (ImportError, AttributeError):
        return None


def get_full_state() -> Dict:
    """
    Return the full state INCLUDING the joined step data for the active
    mission. This is what the frontend gets to render the Mission Coach.
    """
    state = load_state()
    mission_def = _mission_def(state["active_mission"]) if state["active_mission"] else None

    if mission_def and mission_def.get("steps"):
        total_steps = len(mission_def["steps"])
        state["total_steps"] = total_steps
        state["is_complete"] = state["current_step"] >= total_steps
        if not state["is_complete"]:
            state["current_step_data"] = mission_def["steps"][state["current_step"]]
        else:
            state["current_step_data"] = None
    else:
        state["total_steps"] = 0
        state["is_complete"] = False
        state["current_step_data"] = None

    state["mission_def"] = (
        {k: v for k, v in mission_def.items() if k != "steps"}
        if mission_def else None
    )
    return state


def start_mission(mission_id: str) -> Dict:
    """Begin a mission. Resets step progress."""
    mission_def = _mission_def(mission_id)
    if not mission_def or not mission_def.get("steps"):
        state = load_state()
        state["error"] = f"Mission '{mission_id}' has no steps defined"
        return state

    state = load_state()
    state["active_mission"]  = mission_id
    state["current_step"]    = 0
    state["steps_completed"] = []
    state["started_at"]      = _now_iso()
    state["last_advance_at"] = None
    save_state(state)
    return get_full_state()


def advance_mission(completed_tool: str) -> Dict:
    """
    Frontend signals tool completion. Backend decides if it counts.
    Wrong tool = silent no-op (user exploration is allowed, not punished).
    """
    state = load_state()
    if not state["active_mission"]:
        return get_full_state()

    mission_def = _mission_def(state["active_mission"])
    if not mission_def or not mission_def.get("steps"):
        return get_full_state()

    steps = mission_def["steps"]
    if state["current_step"] >= len(steps):
        return get_full_state()

    current = steps[state["current_step"]]
    expected_tool = _tool_from_command(current.get("command", ""))
    completed_tool_clean = _tool_from_command(completed_tool)

    # Silent no-op when wrong tool was run (user is exploring)
    if expected_tool and completed_tool_clean and expected_tool != completed_tool_clean:
        return get_full_state()

    state["steps_completed"].append(completed_tool_clean)
    state["current_step"]   += 1
    state["last_advance_at"] = _now_iso()

    if state["current_step"] >= len(steps):
        # Mission complete. Record it in history and clear active_mission
        # so the user isn't perpetually "in" a finished mission. The FE's
        # next refresh will see active_mission=None and offer the next
        # available mission via showMissionInvite.
        #
        # We keep current_step at len(steps) so a single get_full_state
        # call right after completion (e.g. from the frontend's advance
        # response handler) still shows is_complete=true, letting the
        # celebration card render. On the NEXT call (page reload or
        # explicit refresh) the cleared state takes over.
        state["completion_history"].append({
            "mission_id":   state["active_mission"],
            "completed_at": _now_iso(),
        })
        # Save the celebration-rendering state first
        save_state(state)
        # Then immediately clear active_mission so subsequent loads
        # know to offer a new mission, not re-show the celebration.
        # We use a 'just_completed' field to signal one-shot celebration.
        cleared = load_state()
        cleared["active_mission"] = None
        cleared["just_completed"] = {
            "mission_id":  state["completion_history"][-1]["mission_id"],
            "completed_at": state["completion_history"][-1]["completed_at"],
        }
        cleared["current_step"] = 0
        cleared["steps_completed"] = []
        save_state(cleared)
        return get_full_state()

    save_state(state)
    return get_full_state()


def reset_state() -> Dict:
    """Wipe mission state. Preserves completion_history."""
    state = load_state()
    history = state.get("completion_history", [])
    fresh = _default_state()
    fresh["completion_history"] = history
    save_state(fresh)
    return get_full_state()


def clear_celebration() -> Dict:
    """
    Clear the one-shot just_completed flag after the FE has rendered the
    celebration. Without this, every page load would re-show the celebration
    indefinitely. Idempotent — no-op if just_completed isn't set.
    """
    state = load_state()
    if "just_completed" in state:
        state.pop("just_completed", None)
        save_state(state)
    return get_full_state()


def list_available_missions() -> List[Dict]:
    """
    Return all known missions with metadata for a 'pick a mission' UI.
    Hides missions with empty steps[] (e.g. stubs like sql_basics).
    """
    try:
        from src.core.onboarding import FIRST_MISSIONS
    except ImportError:
        return []

    state = load_state()
    completed_ids = {h["mission_id"] for h in state.get("completion_history", [])}

    out = []
    for mid, mdef in FIRST_MISSIONS.items():
        steps = mdef.get("steps", [])
        if not steps:
            continue
        out.append({
            "id":           mid,
            "title":        mdef.get("title", mid),
            "description":  mdef.get("description", ""),
            "difficulty":   mdef.get("difficulty", "Beginner"),
            "total_steps":  len(steps),
            "total_xp":     sum(s.get("xp_reward", 0) for s in steps),
            "completed":    mid in completed_ids,
            "active":       mid == state.get("active_mission"),
        })
    return out
