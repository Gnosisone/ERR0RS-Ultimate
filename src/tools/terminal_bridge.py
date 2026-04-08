#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Terminal Bridge v1.0
========================================
Pops a real OS terminal window, types the command in,
and streams live output back to the ERR0RS web UI via WebSocket.
Simultaneously feeds the UI a dialog box + clickable option buttons
so the operator learns the anatomy of every tool they run.

Architecture:
  POST /api/terminal/launch   — open OS terminal + start streaming
  GET  /api/tool/registry     — fetch tool flags, descriptions, presets
  WS   /ws/terminal_bridge    — live stdout stream + teach annotations
  POST /api/terminal/fire     — send final built command to terminal

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, json, asyncio, subprocess, threading, time, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY_PATH = Path(__file__).parent / "tool_registry.json"

# ── Load Tool Registry ────────────────────────────────────────────────────────
def load_registry() -> dict:
    """Load the tool registry JSON — hot-reloadable."""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

TOOL_REGISTRY = load_registry()

# ── OS Terminal Spawner ───────────────────────────────────────────────────────
def detect_terminal() -> str:
    """Find the best available terminal emulator on the OS."""
    candidates = [
        "xterm", "gnome-terminal", "xfce4-terminal",
        "konsole", "lxterminal", "mate-terminal", "tilix",
    ]
    for t in candidates:
        if shutil.which(t):
            return t
    return "xterm"  # fallback — always present on Kali

def spawn_terminal_with_command(command: str, tool: str = "") -> dict:
    """
    Spawn a real OS terminal window and type the command.
    Returns {"pid": int, "status": "launched"} or {"error": str}
    """
    terminal = detect_terminal()
    title = f"ERR0RS — {tool.upper()} Live Session" if tool else "ERR0RS Terminal"

    if terminal == "xterm":
        cmd = ["xterm", "-title", title, "-bg", "#04000a", "-fg", "#39ff14",
               "-fa", "Monospace", "-fs", "12",
               "-e", f"bash -c '{command}; echo; echo [ERR0RS] Done. Press Enter.; read'"]
    elif terminal == "gnome-terminal":
        cmd = ["gnome-terminal", f"--title={title}", "--",
               "bash", "-c", f"{command}; echo; echo '[ERR0RS] Done. Press Enter.'; read"]
    elif terminal in ("xfce4-terminal", "lxterminal", "mate-terminal"):
        cmd = [terminal, f"--title={title}",
               "-e", f"bash -c '{command}; echo; echo [ERR0RS] Done. Press Enter.; read'"]
    elif terminal == "konsole":
        cmd = ["konsole", f"--title={title}",
               "-e", f"bash -c '{command}; echo; echo [ERR0RS] Done.; read'"]
    else:
        cmd = [terminal, "-e", f"bash -c '{command}; read'"]

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"pid": proc.pid, "status": "launched", "terminal": terminal, "command": command}
    except Exception as e:
        return {"error": str(e), "terminal": terminal, "command": command}

# ── Command Builder ───────────────────────────────────────────────────────────
def build_command_from_flags(tool: str, target: str, selected_flags: list,
                              flag_values: dict = None) -> str:
    """
    Build a command string from tool + target + user-selected flags.
    flag_values: {"-p": "80,443", "--script": "smb-vuln-ms17-010"}
    """
    flag_values = flag_values or {}
    reg = TOOL_REGISTRY.get(tool, {})
    binary = reg.get("binary", tool)

    parts = [binary]
    for flag in selected_flags:
        parts.append(flag)
        # If this flag takes a value, append it
        if flag in flag_values:
            parts.append(flag_values[flag])

    parts.append(target)
    return " ".join(parts)


# ── Tool Info Builders for UI ────────────────────────────────────────────────
def get_tool_panel_data(tool: str, target: str = "") -> dict:
    """
    Return everything the UI needs to render the dialog + option buttons.
    """
    reg = TOOL_REGISTRY.get(tool)
    if not reg:
        return {"error": f"Tool '{tool}' not in registry"}

    default_cmd = reg.get("default_command", f"{tool} {{target}}").replace("{target}", target or "TARGET")

    return {
        "tool":            tool,
        "name":            reg["name"],
        "category":        reg.get("category", ""),
        "description":     reg["description"],
        "teach_intro":     reg.get("teach_intro", ""),
        "default_command": default_cmd,
        "flags":           reg.get("flags", {}),
        "preset_profiles": reg.get("preset_profiles", {}),
        "defend_notes":    reg.get("defend_notes", ""),
        "mitre":           reg.get("mitre_techniques", []),
        "target":          target,
    }


def get_preset_command(tool: str, preset: str, target: str) -> dict:
    """Apply a preset profile and return the built command."""
    reg = TOOL_REGISTRY.get(tool, {})
    presets = reg.get("preset_profiles", {})
    if preset not in presets:
        return {"error": f"Preset '{preset}' not found for {tool}"}

    p = presets[preset]
    flags = p["flags"]
    binary = reg.get("binary", tool)
    cmd = f"{binary} {' '.join(flags)} {target}"
    return {"command": cmd, "preset": preset, "desc": p["desc"]}


# ── FastAPI Route Registration ────────────────────────────────────────────────
def register_terminal_bridge_routes(app, ws_clients=None):
    """
    Register all Terminal Bridge HTTP + WebSocket routes on the FastAPI app.
    Call this from errorz_launcher.py after app = FastAPI(...)
    """
    from fastapi import WebSocket, WebSocketDisconnect
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from typing import Optional, List

    class LaunchRequest(BaseModel):
        tool:   str
        target: str
        flags:  List[str] = []
        flag_values: dict = {}
        command: Optional[str] = None   # override: use this exact command

    class FireRequest(BaseModel):
        command: str
        tool:    str = ""
        target:  str = ""

    # Active WebSocket connections for terminal bridge
    _bridge_clients: set = set()

    async def _broadcast(msg: dict):
        dead = set()
        for ws in _bridge_clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        _bridge_clients.difference_update(dead)

    # ── GET /api/tool/registry ────────────────────────────────────────────────
    @app.get("/api/tool/registry")
    async def api_tool_registry():
        """Return full tool registry (hot-reload from disk each call)."""
        return JSONResponse(load_registry())

    # ── GET /api/tool/panel/{tool} ────────────────────────────────────────────
    @app.get("/api/tool/panel/{tool}")
    async def api_tool_panel(tool: str, target: str = ""):
        """Return dialog + flags + presets for a specific tool."""
        data = get_tool_panel_data(tool, target)
        if "error" in data:
            return JSONResponse(data, status_code=404)
        return JSONResponse(data)

    # ── GET /api/tool/preset ──────────────────────────────────────────────────
    @app.get("/api/tool/preset")
    async def api_tool_preset(tool: str, preset: str, target: str = ""):
        """Build a command from a preset profile."""
        return JSONResponse(get_preset_command(tool, preset, target))

    # ── POST /api/terminal/launch ─────────────────────────────────────────────
    @app.post("/api/terminal/launch")
    async def api_terminal_launch(req: LaunchRequest):
        """
        Spawn OS terminal with the built command.
        Returns the command, tool panel data, and terminal PID.
        """
        # Build command from flags, or use override
        if req.command:
            command = req.command
        else:
            command = build_command_from_flags(
                req.tool, req.target, req.flags, req.flag_values
            )

        # Spawn the OS terminal window
        result = spawn_terminal_with_command(command, req.tool)

        # Broadcast to any listening WS clients
        await _broadcast({
            "type":    "terminal_launched",
            "tool":    req.tool,
            "target":  req.target,
            "command": command,
            "pid":     result.get("pid"),
        })

        return JSONResponse({
            "status":  "launched" if "pid" in result else "error",
            "command": command,
            "tool":    req.tool,
            "target":  req.target,
            "terminal_info": result,
            "panel": get_tool_panel_data(req.tool, req.target),
        })

    # ── POST /api/terminal/fire ───────────────────────────────────────────────
    @app.post("/api/terminal/fire")
    async def api_terminal_fire(req: FireRequest):
        """
        Fire an exact command to a new OS terminal window.
        Used by the UI's FIRE button after the operator customizes flags.
        """
        result = spawn_terminal_with_command(req.command, req.tool)
        await _broadcast({
            "type":    "fired",
            "command": req.command,
            "tool":    req.tool,
            "pid":     result.get("pid"),
        })
        return JSONResponse({"status": "fired", "result": result})

    # ── WS /ws/terminal_bridge ────────────────────────────────────────────────
    @app.websocket("/ws/terminal_bridge")
    async def ws_terminal_bridge(ws: WebSocket):
        """
        WebSocket for live terminal bridge events.
        Clients subscribe here to receive tool launch events and
        flag explanation pushes in real time.
        """
        await ws.accept()
        _bridge_clients.add(ws)
        try:
            await ws.send_json({"type": "connected", "msg": "Terminal Bridge active"})
            while True:
                data = await ws.receive_json()
                # Client can request tool panel data over WS too
                if data.get("action") == "get_panel":
                    panel = get_tool_panel_data(
                        data.get("tool", ""),
                        data.get("target", "")
                    )
                    await ws.send_json({"type": "panel_data", **panel})
        except WebSocketDisconnect:
            _bridge_clients.discard(ws)
        except Exception:
            _bridge_clients.discard(ws)
