#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Payload Studio Engine
Indexes all existing payloads as a knowledge base for AI autosuggestion.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, re, json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
KB_DIR   = ROOT_DIR / "knowledge" / "badusb"

def detect_platform(content: str, filename: str = "") -> str:
    lower = content.lower() + filename.lower()
    if any(x in lower for x in ["powershell","winkey","gui r","reg add","cmd /c","taskkill"]):
        return "windows"
    if any(x in lower for x in ["osascript","command space","spotlight","terminal","brew","macos","osx"]):
        return "macos"
    if any(x in lower for x in ["android","adb","am start","settings put","pkg","dalvik"]):
        return "android"
    if any(x in lower for x in ["ios","iphone","ipad","mdm","mobileconfig","safari","siri"]):
        return "ios"
    return "cross"

def detect_category(content: str, filename: str = "") -> str:
    lower = content.lower() + filename.lower()
    if any(x in lower for x in ["recon","reconnaissance","exfil","loot","grab","steal","harvest","dump"]):
        return "recon"
    if any(x in lower for x in ["shell","reverse","backdoor","persist","startup","schedule"]):
        return "shell"
    if any(x in lower for x in ["cred","password","wifi","hash","login","auth"]):
        return "credentials"
    if any(x in lower for x in ["prank","troll","rickroll","chaos","annoy","fun","joke"]):
        return "prank"
    if any(x in lower for x in ["lock","nuke","destroy","wipe","ransom","encrypt","delete"]):
        return "disruption"
    if any(x in lower for x in ["keylog","screenshot","screen","record","mic","audio","spy"]):
        return "surveillance"
    if any(x in lower for x in ["escalat","uac","admin","privilege","bypass"]):
        return "privesc"
    if any(x in lower for x in ["network","wifi","ssid","ip","port","scan"]):
        return "network"
    return "utility"

DUCKY_COMMANDS = {
    "REM": "Comment — not executed",
    "STRING": "Type a string of text instantly",
    "STRINGLN": "Type a string then press Enter",
    "DELAY": "Wait N milliseconds",
    "GUI": "Windows key (WIN) or Command key (CMD)",
    "CTRL": "Hold Ctrl and press a key",
    "ALT": "Hold Alt and press a key",
    "SHIFT": "Hold Shift and press a key",
    "ENTER": "Press Enter",
    "BACKSPACE": "Press Backspace",
    "TAB": "Press Tab",
    "ESCAPE": "Press Escape",
    "DELETE": "Press Delete",
    "UPARROW": "Press Up arrow",
    "DOWNARROW": "Press Down arrow",
    "LEFTARROW": "Press Left arrow",
    "RIGHTARROW": "Press Right arrow",
    "HOME": "Press Home key",
    "END": "Press End key",
    "PAGEUP": "Press Page Up",
    "PAGEDOWN": "Press Page Down",
    "CAPSLOCK": "Toggle Caps Lock",
    "PRINTSCREEN": "Take a screenshot",
    "MENU": "Open context menu",
    "SPACE": "Press Spacebar",
    "WAIT_FOR_BUTTON_PRESS": "Pause until Flipper button is pressed",
    "HOLD": "Hold a key down",
    "RELEASE": "Release a held key",
    "REPEAT": "Repeat last command N times",
    "VAR": "Declare a variable (DuckyScript 3.0)",
    "IF": "Conditional logic (DuckyScript 3.0)",
    "WHILE": "Loop (DuckyScript 3.0)",
    "DEFINE": "Define a constant",
    "DEFAULT_DELAY": "Set default delay between all commands",
    "LOCALE": "Set keyboard locale",
}

CONTEXT_SUGGESTIONS = {
    "GUI R":       [("DELAY 500\nSTRING ", "Wait for Run dialog, then type command", 0.99)],
    "GUI r":       [("DELAY 500\nSTRING ", "Wait for Run dialog, then type command", 0.99)],
    "GUI SPACE":   [("DELAY 800\nSTRING terminal\nDELAY 600\nENTER\nDELAY 1200", "Open Spotlight + launch terminal", 0.98)],
    "ENTER":       [("DELAY 1000", "Wait for command to execute", 0.85), ("STRING ", "Type next command", 0.6)],
    "DELAY":       [("STRING ", "Type the command after delay", 0.8)],
    "STRING":      [("ENTER", "Press Enter to execute", 0.95), ("DELAY 500", "Add delay after typing", 0.6)],
    "STRINGLN":    [("DELAY 1000", "Wait for command to run", 0.85)],
}

def get_line_explanation(line: str) -> str:
    stripped = line.strip()
    if not stripped or stripped.startswith("REM"):
        return "Comment — not executed"
    parts = stripped.split(None, 1)
    cmd = parts[0].upper()
    arg = parts[1] if len(parts) > 1 else ""
    base = DUCKY_COMMANDS.get(cmd, f"DuckyScript: {cmd}")
    if cmd == "GUI" and "R" in arg.upper():
        return "Opens Windows Run dialog (Win+R)"
    if cmd == "GUI" and "SPACE" in arg.upper():
        return "Opens macOS Spotlight search (Cmd+Space)"
    if cmd == "STRING" and "powershell" in arg.lower():
        return "Types PowerShell command into active window"
    if cmd == "DELAY":
        ms = arg.strip()
        secs = round(int(ms)/1000, 2) if ms.isdigit() else "?"
        return f"Waits {secs}s — gives time for window/process to open"
    return base + (f" → {arg[:50]}" if arg else "")

def get_suggestions(partial_code: str, platform: str = "windows", last_line: str = "") -> list:
    suggestions = []
    last = last_line.strip()
    for trigger, options in CONTEXT_SUGGESTIONS.items():
        if last.upper().startswith(trigger.upper()):
            for text, desc, conf in options:
                suggestions.append({"text": text, "desc": desc, "confidence": conf})
    suggestions.sort(key=lambda x: x["confidence"], reverse=True)
    return suggestions[:5]

def index_existing_payloads() -> dict:
    index = {"windows": [], "macos": [], "android": [], "ios": [], "cross": []}
    extensions = [".txt", ".ducky", ".script"]
    for path in KB_DIR.rglob("*"):
        if path.suffix.lower() not in extensions:
            continue
        if ".git" in str(path):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            platform = detect_platform(content, path.name)
            category = detect_category(content, path.name)
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("REM")]
            index[platform].append({
                "name": path.name,
                "path": str(path.relative_to(ROOT_DIR)),
                "platform": platform,
                "category": category,
                "lines": len(lines),
                "preview": content[:200],
            })
        except Exception:
            pass
    return index

if __name__ == "__main__":
    print("[ERR0RS] Payload Studio Engine — indexing knowledge base...")
    idx = index_existing_payloads()
    for platform, payloads in idx.items():
        print(f"  {platform:10} → {len(payloads)} payloads indexed")
    total = sum(len(v) for v in idx.values())
    print(f"\n  TOTAL: {total} payloads")
