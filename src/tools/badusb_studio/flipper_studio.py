#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Flipper Zero Studio v2.0
Deep integration from d4rks1d33 curated repos.

Sources integrated:
  knowledge/rocketgod/flipper-zero-rf-jammer
  knowledge/rocketgod/Flipper-Zero-Radio-Scanner
  knowledge/rocketgod/flipper-zero-carjacker
  knowledge/rocketgod/ProtoPirate
  knowledge/rocketgod/SubGHz-Signal-Generator
  knowledge/badusb/Flipper-Zero-BadUSB
  knowledge/badusb/flipper-zero-evil-portal
  knowledge/badusb/UberGuidoZ-Flipper

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re, json
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[3]
KB_DIR   = ROOT_DIR / "knowledge"

# ─── SubGHz frequencies and RF protocol database ─────────────────────────────

SUBGHZ_FREQUENCIES = {
    "315MHz":  {"region": "US",        "use": "Car remotes, gate openers, garage doors"},
    "433MHz":  {"region": "EU/Global", "use": "Car remotes, weather stations, smart home"},
    "868MHz":  {"region": "EU",        "use": "Smart meters, LoRa, Z-Wave EU"},
    "915MHz":  {"region": "US",        "use": "Z-Wave US, LoRa US, smart meters"},
    "2.4GHz":  {"region": "Global",   "use": "WiFi, Bluetooth, Zigbee, drones"},
}

# Rolling code (NOT directly replayable — require RollJam technique)
ROLLING_CODE_PROTOCOLS = [
    "KeeLoq",        # Most OEM car remotes
    "HCS200",        # Garage doors
    "HCS300",        # Newer car remotes
    "HCS301",        # Security systems
    "CAME",          # Italian gate systems
    "NICE FLO",      # Italian gate/garage
    "BFT MITTO",     # Italian access control
    "Faac",          # Italian gates
    "HID Prox",      # Access control cards
]

# Fixed code (directly replayable with Flipper)
FIXED_CODE_PROTOCOLS = [
    "RAW",           # Raw signal capture/replay
    "Princeton",     # Simple remotes
    "Holtek HT12X",  # Common 12-bit encoder
    "CAME 12bit",    # Simple CAME systems
    "Linear",        # Garage doors
    "Chamberlain",   # Garage doors (older)
    "LiftMaster",    # Garage doors (older)
    "Genie",         # Garage doors
]

IR_PROTOCOLS = [
    "NEC",           # Most common — Samsung, LG
    "Sony SIRC",     # Sony products
    "RC5",           # Philips, older devices
    "RC6",           # Philips newer
    "Sharp",         # Sharp TVs
    "Samsung32",     # Samsung-specific
    "NECX",          # Extended NEC
    "Kaseikyo",      # Panasonic, JVC, Denon
]

# ─── BadUSB templates for educational/authorized pentest use ─────────────────

BADUSB_TEMPLATES = {
    "reverse_shell_windows": {
        "name": "Windows Reverse Shell",
        "desc": "Opens PowerShell hidden reverse shell (authorized testing only)",
        "platform": "windows",
        "teach": "Uses encoded PS to bypass logging. Needs listener: nc -lvnp LPORT",
        "steps": [
            "1. Start listener: nc -lvnp LPORT",
            "2. Deploy payload to authorized test machine",
            "3. Session opens in listener when payload runs",
        ],
    },
    "wifi_password_audit": {
        "name": "WiFi Password Audit",
        "desc": "Exports saved WiFi profiles for security audit",
        "platform": "windows",
        "teach": "netsh wlan show profile key=clear — lists all saved networks with keys",
        "steps": [
            "1. Run on test machine with authorization",
            "2. Output written to %TEMP%\\wifi_audit.txt",
            "3. Review exposed credentials for password hygiene assessment",
        ],
    },
    "persistence_test": {
        "name": "Persistence Test (HKCU Run Key)",
        "desc": "Demonstrates HKCU persistence — no admin needed",
        "platform": "windows",
        "teach": "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run runs on user login without elevation.",
        "steps": [
            "1. Deploy on authorized test machine",
            "2. Verify persistence key added with: reg query HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",
            "3. Remove with: reg delete HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v TestPersist /f",
        ],
    },
    "linux_bash_audit": {
        "name": "Linux Shell Audit",
        "desc": "Drops to bash on Linux/Mac for authorized access testing",
        "platform": "linux",
        "teach": "Ctrl+Alt+T opens terminal on most Linux DEs. Tests physical access controls.",
        "steps": [
            "1. Ensure authorized physical access test",
            "2. Target must have terminal shortcut enabled",
            "3. Document physical access findings in report",
        ],
    },
    "evil_portal_demo": {
        "name": "Evil Portal Captive Demo",
        "desc": "Deploys fake WiFi login page (Flipper Evil Portal app required)",
        "platform": "flipper",
        "teach": "Evil Portal creates AP with captive portal. Tests user phishing awareness.",
        "steps": [
            "1. Install Evil Portal app on Flipper from App Store",
            "2. Copy portal template to SD: /apps_data/evil_portal/",
            "3. Start from Flipper: Apps > Tools > Evil Portal",
            "4. Credentials captured to SD card log file",
        ],
    },
}


def list_badusb_templates() -> dict:
    return {
        "status": "success",
        "count": len(BADUSB_TEMPLATES),
        "templates": [
            {"key": k, "name": v["name"], "desc": v["desc"], "platform": v["platform"]}
            for k, v in BADUSB_TEMPLATES.items()
        ],
    }


def get_badusb_guide(template_key: str) -> dict:
    t = BADUSB_TEMPLATES.get(template_key)
    if not t:
        return {"status": "error", "error": f"Unknown template: {template_key}",
                "available": list(BADUSB_TEMPLATES.keys())}
    return {"status": "success", **t, "key": template_key}


def analyze_sub_file(filepath: str) -> dict:
    """Parse a Flipper .sub file and extract signal metadata."""
    try:
        path = Path(filepath)
        if not path.exists():
            return {"status": "error", "error": f"File not found: {filepath}"}
        content = path.read_text(errors="replace")
        info = {"status": "success", "file": path.name,
                "frequency": None, "preset": None, "protocol": None,
                "bit_count": None, "data_lines": 0}
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("Frequency:"):
                hz = int(line.split(":")[1].strip())
                info["frequency"] = f"{hz/1_000_000:.3f} MHz"
            elif line.startswith("Preset:"):
                info["preset"] = line.split(":")[1].strip()
            elif line.startswith("Protocol:"):
                info["protocol"] = line.split(":")[1].strip()
            elif line.startswith("Bit:"):
                info["bit_count"] = int(line.split(":")[1].strip())
            elif line.startswith(("RAW_Data:", "Data:")):
                info["data_lines"] += 1
        proto = info.get("protocol", "")
        if proto in FIXED_CODE_PROTOCOLS or proto == "RAW":
            info["replayable"] = True
            info["risk"] = "HIGH — Fixed code, direct replay possible"
        elif proto in ROLLING_CODE_PROTOCOLS:
            info["replayable"] = False
            info["risk"] = "MEDIUM — Rolling code, requires RollJam technique"
        else:
            info["replayable"] = None
            info["risk"] = "UNKNOWN — Manual analysis required"
        return info
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_rolljam_info() -> dict:
    """Educational overview of RollJam attack technique."""
    return {
        "status": "success",
        "attack": "RollJam",
        "description": (
            "RollJam defeats rolling code systems using simultaneous jamming and capture. "
            "When victim presses remote, jammer blocks signal while Flipper captures it. "
            "On second press, second code is captured while first is replayed to unlock. "
            "Attacker retains an unused valid code for later replay."
        ),
        "hardware_needed": ["Flipper Zero", "HackRF or RTL-SDR for jamming", "OR two Flipper Zeros"],
        "steps": [
            "1. Identify target frequency with SubGHz scanner",
            "2. Set Flipper to capture mode on that frequency",
            "3. Enable jammer on same frequency (HackRF/second device)",
            "4. Wait for victim to press remote (jammer blocks, Flipper captures code #1)",
            "5. Victim presses again — Flipper captures code #2, replays code #1",
            "6. Attacker now holds code #2 (unused, valid for one replay)",
        ],
        "protocols_vulnerable": ["KeeLoq", "HCS200", "HCS300", "Most OEM car remotes"],
        "protocols_immune": ["UWB digital key", "Tesla (app-based)", "Modern Toyota/Subaru"],
        "note": "For authorized penetration testing only. RF jamming is illegal in many jurisdictions.",
    }


def get_subghz_frequency_guide() -> dict:
    return {
        "status": "success",
        "frequencies": SUBGHZ_FREQUENCIES,
        "rolling_code_protocols": ROLLING_CODE_PROTOCOLS,
        "fixed_code_protocols": FIXED_CODE_PROTOCOLS,
        "flipper_tip": (
            "Flipper SubGHz > Frequency Analyzer to detect active frequencies. "
            "Read > specific frequency to capture signals. "
            "Fixed-code signals replay directly. Rolling-code requires RollJam."
        ),
    }


def list_uber_payloads() -> dict:
    """Catalog payloads from UberGuidoZ Flipper knowledge base."""
    uber_dir = KB_DIR / "badusb" / "UberGuidoZ-Flipper"
    payloads = []
    if uber_dir.exists():
        for f in uber_dir.rglob("*.txt"):
            try:
                content = f.read_text(errors="replace")[:400]
                desc = next(
                    (l.replace("REM ", "").strip() for l in content.split("\n")
                     if l.strip().startswith("REM ")),
                    "No description"
                )
                payloads.append({
                    "name": f.stem,
                    "path": str(f.relative_to(KB_DIR)),
                    "desc": desc,
                    "size_bytes": f.stat().st_size,
                })
            except Exception:
                pass
    return {
        "status": "success",
        "source": "UberGuidoZ-Flipper (local knowledge base)",
        "count": len(payloads),
        "payloads": sorted(payloads, key=lambda x: x["name"]),
    }


def get_nfc_clone_guide(uid: str = "AA BB CC DD") -> dict:
    return {
        "status": "success",
        "uid": uid,
        "guide": [
            "1. Flipper NFC > Read — hold card to back of Flipper",
            "2. Flipper auto-detects card type and UID",
            "3. Save: give it a name",
            "4. Emulate: NFC > Saved > [card name] > Emulate",
            "5. Hold Flipper to reader to use cloned card",
        ],
        "supported_types": [
            "Mifare Classic 1K/4K (most common access cards)",
            "Mifare Ultralight / NTAG",
            "EM4100 (older 125kHz RFID)",
            "HID Prox (common office access)",
        ],
        "limitations": [
            "Encrypted Mifare Classic sectors require additional cracking (mfoc tool)",
            "DESFire EV2/EV3 cards — encrypted, not directly cloneable",
            "Apple Pay / Google Pay — secure element, not cloneable",
        ],
        "teach": (
            "Most building access cards use 125kHz EM4100 or 13.56MHz Mifare Classic. "
            "Flipper reads both. DESFire and newer cards are encrypted — use Mifare Classic Autopwn "
            "app for encrypted cards with known key vulnerabilities."
        ),
    }


def get_ir_remote_guide(device: str = "tv") -> dict:
    IR_INFO = {
        "tv":        {"brands": ["Samsung", "LG", "Sony", "TCL", "Hisense"],
                      "protocols": ["NEC", "Samsung32", "Sony SIRC", "RC5"]},
        "ac":        {"brands": ["Daikin", "Mitsubishi", "LG", "Samsung"],
                      "protocols": ["NEC", "Kaseikyo"]},
        "projector": {"brands": ["Epson", "BenQ", "Optoma"],
                      "protocols": ["NEC", "RC5"]},
        "soundbar":  {"brands": ["Sonos", "Samsung", "LG"],
                      "protocols": ["NEC", "Samsung32"]},
    }
    info = IR_INFO.get(device, IR_INFO["tv"])
    return {
        "status":   "success",
        "device":   device,
        "brands":   info["brands"],
        "protocols": info["protocols"],
        "guide": [
            "Flipper IR > Learn New Remote > point original remote at Flipper",
            "Save signal with a name (e.g. Power, Mute, Vol_Up)",
            "Replay: Infrared > Saved > [remote name] > Send",
            "Universal: Infrared > Universal Remotes > TV/AC/etc",
        ],
        "tips": [
            "Hold remote 10-20cm from Flipper IR sensor (top)",
            "Press button slowly and hold for 1 second",
            "Test immediately after capture — save if it works",
            "Use Universal Remotes for common brands without original remote",
        ],
    }


def handle_flipper_request(payload: dict) -> dict:
    """Route handler for /api/flipper endpoint."""
    action = payload.get("action", "list")
    dispatch = {
        "list_badusb":       lambda: list_badusb_templates(),
        "badusb_guide":      lambda: get_badusb_guide(payload.get("template", "")),
        "analyze_sub":       lambda: analyze_sub_file(payload.get("file", "")),
        "rolljam_info":      lambda: get_rolljam_info(),
        "subghz_guide":      lambda: get_subghz_frequency_guide(),
        "uber_payloads":     lambda: list_uber_payloads(),
        "nfc_clone_guide":   lambda: get_nfc_clone_guide(payload.get("uid", "AA BB CC DD")),
        "ir_remote_guide":   lambda: get_ir_remote_guide(payload.get("device", "tv")),
        "protocols":         lambda: {"status": "success",
                                      "fixed_code": FIXED_CODE_PROTOCOLS,
                                      "rolling_code": ROLLING_CODE_PROTOCOLS,
                                      "ir": IR_PROTOCOLS},
    }
    handler = dispatch.get(action)
    if handler:
        return handler()
    return {
        "status": "error", "error": f"Unknown action: {action}",
        "available": list(dispatch.keys()),
    }


if __name__ == "__main__":
    print("[Flipper Studio] Self-test")
    r = list_badusb_templates()
    print(f"  BadUSB templates: {r['count']}")
    r = get_rolljam_info()
    print(f"  RollJam steps: {len(r['steps'])}")
    r = list_uber_payloads()
    print(f"  UberGuidoZ payloads found: {r['count']}")
    r = get_subghz_frequency_guide()
    print(f"  SubGHz freqs: {len(r['frequencies'])}, protocols: {len(r['fixed_code_protocols'])+len(r['rolling_code_protocols'])}")
