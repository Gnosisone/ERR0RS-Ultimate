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

def detect_platform(content: str, filename: str = "", path: str = "") -> str:
    lower = content.lower() + filename.lower() + path.lower()
    # macOS indicators — check FIRST because "terminal" is more specific
    if any(x in lower for x in ["gui space","osascript","command space","brew install",
                                  "launchagent","macos","osx","spotlight","open -a",
                                  "caffeinate","plutil","defaults write"]):
        return "macos"
    # Windows indicators
    if any(x in lower for x in ["powershell","gui r\n","reg add","cmd /c","taskkill",
                                  "net user","net localgroup","winrm","wscript","cscript"]):
        return "windows"
    # Android
    if any(x in lower for x in ["android","adb ","am start","settings put","dalvik",
                                  "apk","activity manager"]):
        return "android"
    # iOS
    if any(x in lower for x in ["ios","iphone","ipad","mobileconfig","safari\n","siri"]):
        return "ios"
    # DuckyScript macOS keyboard shortcut pattern
    if "gui space" in lower or "command space" in lower:
        return "macos"
    return "cross"

# Map parent directory names (from nocomp-style repos) to categories
_DIR_CATEGORY_MAP = {
    "remote_access":     "shell",
    "credentials":       "credentials",
    "execution":         "shell",
    "exfiltration":      "recon",
    "recon":             "recon",
    "prank":             "prank",
    "general":           "utility",
    "incident_response": "utility",
    "surveillance":      "surveillance",
    "mobile":            "utility",
    # narstybits MacOS-DuckyScripts categories
    "executions":        "shell",
    "goodusb":           "utility",
    "obscurity":         "evasion",
    "pranks":            "prank",
    "keylogger":         "surveillance",
    "reverse_shell":     "shell",
    "sudo_password_grabber": "credentials",
    "full_passwords_grabber": "credentials",
}

def detect_category(content: str, filename: str = "", path: str = "") -> str:
    # Priority 1: parent directory name maps cleanly
    if path:
        from pathlib import Path
        parts = Path(path).parts
        for part in reversed(parts[:-1]):  # walk up from file, skip filename
            mapped = _DIR_CATEGORY_MAP.get(part.lower())
            if mapped:
                return mapped

    lower = content.lower() + filename.lower()

    # Priority 2: strong content signals (ordered most→least specific)
    if any(x in lower for x in ["keylog","keystroke injection","keylogger"]):
        return "surveillance"
    if any(x in lower for x in ["reverse shell","reverseshell","bash -i >","tcp/","netcat","ncat -e",
                                  "winrm","psremoting","evil-winrm"]):
        return "shell"
    if any(x in lower for x in ["exfil","webhook","dropbox api","discord.com/api","http post",
                                  "curl -x post","invoke-restmethod","send.*loot"]):
        return "recon"
    if any(x in lower for x in ["sam.bak","system.bak","lsass","mimikatz","secretsdump",
                                  "hashdump","credential dump","password grab","sudo.*snatch",
                                  "wifi.*password","netsh wlan show"]):
        return "credentials"
    if any(x in lower for x in ["launchagent","run key","startup","schedule","persist",
                                  "hkcu.*run","crontab","autorun"]):
        return "persistence"
    if any(x in lower for x in ["uac bypass","fodhelper","disable.*defender","amsi","set-mppref",
                                  "spctl --master","gatekeeper","av bypass"]):
        return "evasion"
    if any(x in lower for x in ["escalat","privilege","admin","net localgroup","sudo su"]):
        return "privesc"
    if any(x in lower for x in ["prank","rickroll","troll","jumpscare","annoy","fun\n",
                                  "wallpaper","screensaver","rage","ascii"]):
        return "prank"
    if any(x in lower for x in ["port scan","nmap","ifconfig","ipconfig","network info",
                                  "arp -a","netstat","traceroute"]):
        return "network"
    if any(x in lower for x in ["recon","reconnaissance","hostname","whoami","sysinfo",
                                  "systeminfo","uname","lscpu","ip addr"]):
        return "recon"
    if any(x in lower for x in ["screenshot","screen capture","record","microphone","audio"]):
        return "surveillance"
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
            content  = path.read_text(encoding="utf-8", errors="ignore")
            rel_path = str(path.relative_to(ROOT_DIR))
            platform = detect_platform(content, path.name, rel_path)
            category = detect_category(content, path.name, rel_path)
            lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("REM")]
            index[platform].append({
                "name":     path.name,
                "path":     rel_path,
                "platform": platform,
                "category": category,
                "lines":    len(lines),
                "preview":  content[:200],
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
