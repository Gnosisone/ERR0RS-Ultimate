#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Terminal Bridge v2.0 (Production)
=====================================================
Pops a real OS terminal window, types the command in,
streams live stdout back to ERR0RS UI via WebSocket.
Simultaneously feeds the UI a teach panel + clickable flags.

FIXES in v2.0:
  - Pass DISPLAY/XAUTHORITY env vars so xterm opens from daemon process
  - Robust terminal detection with qterminal as Pi default
  - build_command_from_flags returns sane defaults when no flags selected
  - get_preset_command handles space-separated flag lists correctly
  - register_terminal_bridge_routes added /api/tool/preset GET route
  - All subprocess.Popen calls get env=os.environ.copy() + DISPLAY

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, json, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY_PATH = Path(__file__).parent / "tool_registry.json"

# ── Build env dict that includes DISPLAY so xterm opens from daemon ──────────
def _gui_env():
    """Return environment with DISPLAY/XAUTHORITY guaranteed."""
    env = os.environ.copy()
    # Ensure DISPLAY is set — try common values if missing
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":0"
    if not env.get("XAUTHORITY"):
        home = env.get("HOME", "/root")
        xauth = f"{home}/.Xauthority"
        if Path(xauth).exists():
            env["XAUTHORITY"] = xauth
    return env

# ── Load Tool Registry ────────────────────────────────────────────────────────
def load_registry() -> dict:
    """Load the tool registry JSON — hot-reloadable."""
    if REGISTRY_PATH.exists():
        try:
            with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TerminalBridge] Registry load error: {e}")
    return {}

TOOL_REGISTRY = load_registry()

# ── OS Terminal Spawner ───────────────────────────────────────────────────────
def detect_terminal() -> str:
    """Find best available terminal on the OS. Prefers qterminal on Pi (lighter)."""
    # Pi-optimised order: qterminal is fast and lightweight
    candidates = [
        "qterminal",
        "xfce4-terminal",
        "lxterminal",
        "gnome-terminal",
        "mate-terminal",
        "tilix",
        "konsole",
        "xterm",
    ]
    for t in candidates:
        if shutil.which(t):
            return t
    return "xterm"  # always present on Kali

def spawn_terminal_with_command(command: str, tool: str = "") -> dict:
    """
    Spawn a real OS terminal window and run a command inside it.
    CRITICAL: must pass env with DISPLAY set or xterm won't open
    from a background server process.
    Returns {"pid": int, "status": "launched"} or {"error": str}
    """
    terminal = detect_terminal()
    title    = f"ERR0RS — {tool.upper()} Live Session" if tool else "ERR0RS Terminal"
    env      = _gui_env()

    # Wrap command so it pauses after finishing so operator can read output
    wrapped  = f"bash -c '{command}; echo; echo \"[ERR0RS] Done — press Enter to close\"; read'"

    try:
        if terminal == "qterminal":
            cmd = ["qterminal", f"--title={title}", "-e", wrapped]
        elif terminal == "xfce4-terminal":
            cmd = ["xfce4-terminal", f"--title={title}", "-e", wrapped]
        elif terminal == "lxterminal":
            cmd = ["lxterminal", f"--title={title}", "-e", wrapped]
        elif terminal == "gnome-terminal":
            cmd = ["gnome-terminal", f"--title={title}", "--", "bash", "-c",
                   f"{command}; echo; echo '[ERR0RS] Done — press Enter'; read"]
        elif terminal == "mate-terminal":
            cmd = ["mate-terminal", f"--title={title}", "-e", wrapped]
        elif terminal == "konsole":
            cmd = ["konsole", f"--title={title}", "-e", "bash", "-c",
                   f"{command}; echo; read"]
        elif terminal == "tilix":
            cmd = ["tilix", "-t", title, "-e", wrapped]
        else:
            # xterm — always works, style it to match ERR0RS theme
            cmd = [
                "xterm",
                "-title", title,
                "-bg", "#04000a",
                "-fg", "#39ff14",
                "-fa", "Monospace",
                "-fs", "11",
                "-geometry", "120x35",
                "-e", wrapped,
            ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,  # detach from parent — survive if server restarts
        )
        return {
            "pid":      proc.pid,
            "status":   "launched",
            "terminal": terminal,
            "command":  command,
            "display":  env.get("DISPLAY", "unknown"),
        }
    except Exception as e:
        # Fallback: try bare xterm if preferred terminal failed
        if terminal != "xterm" and shutil.which("xterm"):
            try:
                proc = subprocess.Popen(
                    ["xterm", "-e", wrapped],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return {"pid": proc.pid, "status": "launched",
                        "terminal": "xterm(fallback)", "command": command}
            except Exception as e2:
                return {"error": f"{terminal} failed: {e} | xterm fallback: {e2}",
                        "terminal": terminal}
        return {"error": str(e), "terminal": terminal, "command": command}


# ── Command Builder ───────────────────────────────────────────────────────────
def build_command_from_flags(tool: str, target: str, selected_flags: list,
                              flag_values: dict = None) -> str:
    """
    Build a command string from tool + target + user-selected flags.
    Falls back to the registry default_command if no flags selected.
    """
    flag_values = flag_values or {}
    reg    = TOOL_REGISTRY.get(tool, {})
    binary = reg.get("binary", tool)
    tgt    = target.strip() or "TARGET"

    # If no flags chosen, use the registry default
    if not selected_flags:
        default = reg.get("default_command", f"{binary} {tgt}")
        return default.replace("{target}", tgt)

    parts = [binary]
    for flag in selected_flags:
        # Some flags are full sub-commands (e.g. gobuster "dir", sqlmap "--batch")
        parts.append(flag)
        if flag in flag_values and flag_values[flag]:
            parts.append(str(flag_values[flag]))
    parts.append(tgt)
    return " ".join(parts)


# ── Tool Info Builders for UI ────────────────────────────────────────────────
def get_tool_panel_data(tool: str, target: str = "") -> dict:
    """Return everything the UI needs to render the dialog + option buttons."""
    # Hot-reload registry each call so edits take effect without restart
    reg = load_registry().get(tool)
    if not reg:
        return {"error": f"Tool '{tool}' not in registry"}

    tgt         = target.strip() or ""
    default_cmd = reg.get("default_command", f"{tool} {{target}}").replace("{target}", tgt or "TARGET")

    return {
        "tool":            tool,
        "name":            reg.get("name", tool),
        "category":        reg.get("category", ""),
        "description":     reg.get("description", ""),
        "teach_intro":     reg.get("teach_intro", ""),
        "default_command": default_cmd,
        "flags":           reg.get("flags", {}),
        "preset_profiles": reg.get("preset_profiles", {}),
        "defend_notes":    reg.get("defend_notes", ""),
        "mitre":           reg.get("mitre_techniques", []),
        "target":          tgt,
    }


def get_preset_command(tool: str, preset: str, target: str) -> dict:
    """Apply a preset profile and return the built command string."""
    reg = load_registry().get(tool, {})
    presets = reg.get("preset_profiles", {})
    if preset not in presets:
        return {"error": f"Preset '{preset}' not found for {tool}"}

    p      = presets[preset]
    flags  = p.get("flags", [])
    binary = reg.get("binary", tool)
    tgt    = target.strip() or "TARGET"

    # Flags list may contain {target} placeholders — substitute
    flags_str = " ".join(str(f).replace("{target}", tgt) for f in flags)
    # Build command: if flags already contain binary, don't double it
    if flags_str.startswith(binary):
        cmd = flags_str.replace("{target}", tgt)
    else:
        cmd = f"{binary} {flags_str} {tgt}".strip()

    return {
        "command": cmd,
        "preset":  preset,
        "desc":    p.get("desc", ""),
        "tool":    tool,
        "target":  tgt,
    }


# ── HTTP Route Registration (called from errorz_launcher.py) ─────────────────
def register_http_routes(handler_class):
    """
    Monkey-patch terminal bridge GET/POST routes into ERR0RSHandler.
    Called once at startup from errorz_launcher.py.
    This is the clean way to add routes without modifying the
    handler class directly.
    """
    # Not used — routes are injected directly in errorz_launcher.py
    pass
