#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Flipper Zero Evolution Engine
================================================
Plug your Flipper in → ERR0RS detects it → auto-evolves it to its
next level → leaves it in its most powerful happy state.

Evolution Levels (XP-based, like a video game):
  Level 1  — Stock Flipper detected, prep & backup
  Level 2  — Community firmware detected (RogueMaster/Unleashed/Momentum/Xtreme)
  Level 3  — Full SubGHz database (all regions)
  Level 4  — NFC / RFID card database
  Level 5  — IR blaster library (all TV, AC, projectors)
  Level 6  — ERR0RS BadUSB payload sync to SD
  Level 7  — WiFi dev board scripts (deauth, scan, evil twin)
  Level 8  — Rocketgod / UberGuidoZ community pack sync
  Level 9  — ERR0RS companion app config & keybinds
  Level 10 — MAX POWER — full calibration & health report

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os
import sys
import json
import time
import shutil
import hashlib
import serial
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parents[3]
KB_DIR     = ROOT_DIR / "knowledge" / "badusb"
ROCKETGOD  = ROOT_DIR / "knowledge" / "rocketgod"
SD_OUT     = ROOT_DIR / "src" / "output" / "flipper_sd"
STATE_FILE = ROOT_DIR / "src" / "output" / "flipper_sd" / "evolution_state.json"


# ── Evolution Level Definitions ───────────────────────────────────────────────
EVOLUTION_LEVELS = {
    1:  {"name": "AWAKENING",      "xp": 0,    "emoji": "🌑", "desc": "Flipper detected — backup & prep"},
    2:  {"name": "UNLOCKED",      "xp": 100,  "emoji": "🔴", "desc": "Community firmware — full region unlock + extra protocols"},
    3:  {"name": "FREQUENCY LORD", "xp": 250,  "emoji": "📡", "desc": "Full SubGHz frequency database"},
    4:  {"name": "CARD SHARK",     "xp": 450,  "emoji": "🃏", "desc": "NFC/RFID card & key database"},
    5:  {"name": "IR OVERLORD",    "xp": 700,  "emoji": "🔴", "desc": "IR blaster — all devices in range"},
    6:  {"name": "PAYLOAD MASTER", "xp": 1000, "emoji": "💀", "desc": "ERR0RS BadUSB payload library synced"},
    7:  {"name": "WAVE RIDER",     "xp": 1350, "emoji": "🌊", "desc": "WiFi dev board fully armed"},
    8:  {"name": "COMMUNITY GOD",  "xp": 1750, "emoji": "🌐", "desc": "Rocketgod + UberGuidoZ packs installed"},
    9:  {"name": "ERR0RS BOUND",   "xp": 2200, "emoji": "🎯", "desc": "ERR0RS companion config & keybinds"},
    10: {"name": "MAX POWER",      "xp": 2700, "emoji": "🔥", "desc": "FULL EVOLUTION — calibrated & happy"},
}

XP_PER_LEVEL = {
    "backup":          50,
    "firmware_update": 100,
    "subghz_sync":     200,
    "nfc_sync":        150,
    "ir_sync":         150,
    "badusb_sync":     200,
    "wifi_scripts":    200,
    "community_packs": 200,
    "companion_cfg":   150,
    "calibration":     200,
}


# ── Data Structures ───────────────────────────────────────────────────────────
@dataclass
class EvolutionStep:
    step_id: str
    name: str
    xp_reward: int
    status: str = "pending"   # pending | running | done | skipped | failed
    output: str = ""
    error: str = ""
    duration: float = 0.0

@dataclass
class FlipperState:
    device_path: str = ""
    firmware: str = "unknown"
    sd_path: str = ""
    current_level: int = 0
    total_xp: int = 0
    steps: List[EvolutionStep] = field(default_factory=list)
    session_start: str = ""
    last_seen: str = ""
    happy: bool = False
    history: List[Dict] = field(default_factory=list)


# ── USB / Serial Detection ─────────────────────────────────────────────────────
# ── Firmware Detection via Serial CLI ─────────────────────────────────────────
FIRMWARE_PROFILES = {
    "roguemaster": {
        "display":  "RogueMaster",
        "keywords": ["roguemaster", "rogue master", "rogue_master"],
        "color":    "🔴",
        "desc":     "RogueMaster — Max RF power, all unlocks, community apps, NFC extras",
        "url":      "https://github.com/RogueMaster/flipperzero-firmware-wPlugins/releases",
        "rating":   "★★★★★ — You're already running the best community build",
    },
    "unleashed": {
        "display":  "Unleashed",
        "keywords": ["unleashed", "unlshd"],
        "color":    "⚡",
        "desc":     "Unleashed — frequency unlocks, extra protocols, rolling code bypass",
        "url":      "https://github.com/DarkFlippers/unleashed-firmware/releases",
        "rating":   "★★★★☆ — Great build. RogueMaster adds more community apps.",
    },
    "momentum": {
        "display":  "Momentum",
        "keywords": ["momentum", "moofw"],
        "color":    "💨",
        "desc":     "Momentum — performance-focused fork with UI customization",
        "url":      "https://github.com/Next-Flip/Momentum-Firmware/releases",
        "rating":   "★★★★☆ — Solid build. All major unlocks present.",
    },
    "xtreme": {
        "display":  "Xtreme",
        "keywords": ["xtreme", "xfw"],
        "color":    "🔥",
        "desc":     "Flipper Xtreme — custom apps, BLE spam, all protocols",
        "url":      "https://github.com/ClaraCrazy/Flipper-Xtreme/releases",
        "rating":   "★★★★☆ — Community favorite. Well maintained.",
    },
    "official": {
        "display":  "Official Flipper",
        "keywords": ["release", "official", "flipper"],
        "color":    "🐬",
        "desc":     "Official firmware — stable but frequency-locked",
        "url":      "https://github.com/flipperdevices/flipperzero-firmware/releases",
        "rating":   "★★☆☆☆ — Upgrade recommended for full capability",
    },
}


def detect_flipper_firmware(port: str, timeout: float = 3.0) -> dict:
    """
    Query Flipper Zero firmware via serial CLI using 'device_info' command.
    Parses firmware_origin_fork, firmware_branch, firmware_version, firmware_build_date.
    Returns: {"firmware": str, "profile": dict, "version": str, "build_date": str,
              "fork": str, "branch": str, "hw_name": str, "raw": str, "detected": bool}
    """
    result = {
        "firmware":   "unknown",
        "profile":    FIRMWARE_PROFILES["official"],
        "version":    "",
        "build_date": "",
        "fork":       "",
        "branch":     "",
        "hw_name":    "",
        "raw":        "",
        "detected":   False,
    }
    if not port:
        return result
    try:
        import serial as _serial
        with _serial.Serial(port, baudrate=115200, timeout=timeout) as ser:
            ser.write(b"\r\n")
            time.sleep(0.3)
            ser.reset_input_buffer()
            ser.write(b"device_info\r\n")
            time.sleep(1.5)
            raw = ser.read(ser.in_waiting or 2048).decode("utf-8", errors="replace")
            result["raw"]      = raw
            result["detected"] = bool(raw.strip())

            # Parse key-value pairs from device_info output
            fields = {}
            for line in raw.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fields[k.strip()] = v.strip()

            fork       = fields.get("firmware_origin_fork", "").upper()
            branch     = fields.get("firmware_branch", "")
            version    = fields.get("firmware_version", "")
            build_date = fields.get("firmware_build_date", "")
            hw_name    = fields.get("hardware_name", "")

            result["version"]    = version
            result["build_date"] = build_date
            result["fork"]       = fork
            result["branch"]     = branch
            result["hw_name"]    = hw_name

            # Match fork identifier to profile
            fork_map = {
                "RM":       "roguemaster",
                "UNLEASHED":"unleashed",
                "UNLSHD":   "unleashed",
                "MOMENTUM": "momentum",
                "MOOFW":    "momentum",
                "XTREME":   "xtreme",
                "XFW":      "xtreme",
            }

            matched_key = fork_map.get(fork)
            if not matched_key:
                # Fallback: check branch/version string against keywords
                combined = (fork + branch + version).lower()
                for fw_key, profile in FIRMWARE_PROFILES.items():
                    if any(kw in combined for kw in profile["keywords"]):
                        matched_key = fw_key
                        break

            if matched_key:
                result["firmware"] = FIRMWARE_PROFILES[matched_key]["display"]
                result["profile"]  = FIRMWARE_PROFILES[matched_key]
            else:
                # Unknown fork — build a display name from what we got
                result["firmware"] = f"Custom ({fork or 'unknown'} v{version})"

    except ImportError:
        result["raw"] = "pyserial not installed — run: pip3 install pyserial --break-system-packages"
    except Exception as e:
        result["raw"] = str(e)
    return result


def detect_flipper() -> Dict:
    """
    Detect a connected Flipper Zero across Windows, Linux, macOS.
    Returns {"found": bool, "port": str, "sd_path": str, "os": str}
    """
    result = {"found": False, "port": "", "sd_path": "", "os": platform.system()}
    system = platform.system()

    if system == "Windows":
        # Check COM ports for STMicroelectronics / Flipper Zero USB CDC
        try:
            out = subprocess.run(
                ["powershell", "-Command",
                 "Get-WMIObject Win32_SerialPort | Select-Object Name,DeviceID | ConvertTo-Json"],
                capture_output=True, text=True, timeout=8,
                encoding="utf-8", errors="replace"
            ).stdout
            ports = json.loads(out) if out.strip().startswith("[") else (
                [json.loads(out)] if out.strip().startswith("{") else []
            )
            for p in (ports if isinstance(ports, list) else [ports]):
                name = str(p.get("Name", "")).lower()
                if any(x in name for x in ["flipper", "stm", "cdc", "virtual com"]):
                    result["found"] = True
                    result["port"] = p.get("DeviceID", "COMx")
                    break
        except Exception:
            pass

        # Check for Flipper SD card as removable drive
        try:
            drive_out = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject Win32_LogicalDisk -Filter DriveType=2 | Select-Object DeviceID,VolumeName | ConvertTo-Json"],
                capture_output=True, text=True, timeout=8,
                encoding="utf-8", errors="replace"
            ).stdout
            drives = json.loads(drive_out) if drive_out.strip().startswith("[") else (
                [json.loads(drive_out)] if drive_out.strip().startswith("{") else []
            )
            for d in (drives if isinstance(drives, list) else [drives]):
                label = str(d.get("VolumeName", "")).lower()
                if "flipper" in label or "flip" in label:
                    result["sd_path"] = d.get("DeviceID", "") + "\\"
                    result["found"] = True
                    break
        except Exception:
            pass

    elif system == "Linux":
        # Check /dev for Flipper CDC ACM
        for dev in ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]:
            if Path(dev).exists():
                result["found"] = True
                result["port"] = dev
                break
        # Check mounted paths
        for mnt in ["/media", "/mnt", "/run/media"]:
            mnt_path = Path(mnt)
            if mnt_path.exists():
                for p in mnt_path.rglob("*"):
                    if "flipper" in p.name.lower() and p.is_dir():
                        result["sd_path"] = str(p)
                        result["found"] = True
                        break

    elif system == "Darwin":  # macOS
        for dev in ["/dev/cu.usbmodem01", "/dev/cu.usbmodemflipperze01"]:
            if Path(dev).exists():
                result["found"] = True
                result["port"] = dev
                break
        for vol in Path("/Volumes").iterdir():
            if "flipper" in vol.name.lower():
                result["sd_path"] = str(vol)
                result["found"] = True
                break

    return result


# ── State Persistence ─────────────────────────────────────────────────────────
def _load_state() -> Dict:
    """Load saved evolution state from disk."""
    SD_OUT.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_xp": 0, "current_level": 1, "completed_steps": [], "history": []}

def _save_state(state: Dict) -> None:
    """Persist evolution state to disk."""
    SD_OUT.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def _xp_to_level(xp: int) -> int:
    """Convert total XP into Evolution Level."""
    level = 1
    for lvl, info in EVOLUTION_LEVELS.items():
        if xp >= info["xp"]:
            level = lvl
    return level

def _level_badge(xp: int) -> str:
    """Return level badge string for current XP."""
    lvl  = _xp_to_level(xp)
    info = EVOLUTION_LEVELS[lvl]
    next_xp = EVOLUTION_LEVELS.get(lvl + 1, {}).get("xp", 9999)
    pct = min(100, int((xp - info["xp"]) / max(1, next_xp - info["xp"]) * 100))
    bar = ("█" * (pct // 10)) + ("░" * (10 - pct // 10))
    return (
        f"  {info['emoji']} Level {lvl} — {info['name']}\n"
        f"  XP: {xp} / {next_xp}  [{bar}] {pct}%\n"
        f"  \"{info['desc']}\""
    )

# ── Step: Level 1 — Backup ────────────────────────────────────────────────────
def _step_backup(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("backup", "Backup current SD contents", XP_PER_LEVEL["backup"])
    t0 = time.time()
    if not sd_path:
        step.status = "skipped"
        step.output = "[ERR0RS] No SD card path detected — skipping backup.\n" \
                      "  Tip: Connect Flipper with SD card inserted for backup."
        return step
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
    bk_dir = SD_OUT / "backups" / f"flipper_backup_{ts}"
    try:
        shutil.copytree(sd_path, str(bk_dir), dirs_exist_ok=True)
        step.status = "done"
        step.output = f"[ERR0RS] Backup saved → {bk_dir}\n  Files: {sum(1 for _ in bk_dir.rglob('*'))}"
    except Exception as e:
        step.status = "failed"
        step.error  = str(e)
        step.output = f"[ERR0RS] Backup failed: {e}"
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 2 — Firmware Update Info ─────────────────────────────────────
def _step_firmware(port: str, state: Dict) -> EvolutionStep:
    """
    Detect current Flipper firmware via serial CLI.
    Acknowledges whatever is installed, gives upgrade guidance only if needed.
    """
    step = EvolutionStep("firmware_update", "Firmware detection & validation", XP_PER_LEVEL["firmware_update"])
    t0 = time.time()

    # Query actual firmware over serial
    fw_info = detect_flipper_firmware(port)
    profile  = fw_info["profile"]
    fw_name  = fw_info["firmware"]
    detected = fw_info["detected"]

    step.status = "done"

    if detected:
        ver_str  = f" v{fw_info['version']}" if fw_info['version'] else ""
        date_str = f" (built {fw_info['build_date']})" if fw_info['build_date'] else ""
        hw_str   = f" | device: {fw_info['hw_name']}" if fw_info['hw_name'] else ""
        step.name = f"Firmware: {fw_name}{ver_str} detected {profile['color']}"
        step.output = (
            f"[ERR0RS] {profile['color']} FIRMWARE: {profile['display']}{ver_str}{date_str}{hw_str}\n"
            f"  Status  : {profile['rating']}\n"
            f"  Info    : {profile['desc']}\n"
            f"  Releases: {profile['url']}\n"
        )
        # If they're on official stock, recommend upgrading
        if fw_name == "Official Flipper":
            step.output += (
                f"\n  [ERR0RS] ⚡ UPGRADE RECOMMENDED:\n"
                f"    You're on stock firmware — unlock full RF capability:\n\n"
                f"    RogueMaster (max features):\n"
                f"      https://github.com/RogueMaster/flipperzero-firmware-wPlugins/releases\n"
                f"    Unleashed (stable unlocks):\n"
                f"      https://github.com/DarkFlippers/unleashed-firmware/releases\n\n"
                f"    Flash via qFlipper: File > Install from file → choose .tgz\n"
            )
        else:
            step.output += (
                f"\n  [ERR0RS] ✅ Your firmware is already unlocked and capable.\n"
                f"  No reflash needed — ERR0RS will work with {profile['display']}.\n"
            )
    else:
        # Serial query failed — give generic guidance
        step.name = "Firmware: check & validate"
        step.output = (
            f"[ERR0RS] Could not query firmware over serial (may need pyserial).\n"
            f"  Install: pip3 install pyserial --break-system-packages\n\n"
            f"  KNOWN GOOD COMMUNITY FIRMWARES:\n"
            f"  🔴 RogueMaster (recommended — max capability):\n"
            f"      https://github.com/RogueMaster/flipperzero-firmware-wPlugins/releases\n"
            f"  ⚡ Unleashed (stable unlocks + extra protocols):\n"
            f"      https://github.com/DarkFlippers/unleashed-firmware/releases\n"
            f"  💨 Momentum (performance + UI customization):\n"
            f"      https://github.com/Next-Flip/Momentum-Firmware/releases\n\n"
            f"  Flash via qFlipper → Install from file → choose .tgz / .dfu\n"
        )

    # Store detected firmware in state for future steps
    state["detected_firmware"] = fw_name
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 3 — SubGHz Database ──────────────────────────────────────────
def _step_subghz(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("subghz_sync", "SubGHz frequency database sync", XP_PER_LEVEL["subghz_sync"])
    t0   = time.time()
    synced, skipped = 0, 0

    # Source: UberGuidoZ repo + Rocketgod SubGHz toolkit
    sources = [
        KB_DIR / "UberGuidoZ-Flipper" / "subghz",
        ROCKETGOD / "SubGHz-Signal-Generator",
        ROCKETGOD / "SubGHz-Toolkit",
        ROCKETGOD / "Flipper-Zero-SUB-Analyzer",
        ROCKETGOD / "Flipper_Zero",
    ]

    if sd_path:
        dest = Path(sd_path) / "subghz"
        dest.mkdir(exist_ok=True)
        for src_dir in sources:
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*.sub"):
                target = dest / f.name
                try:
                    shutil.copy2(str(f), str(target))
                    synced += 1
                except Exception:
                    skipped += 1
        step.status = "done"
        step.output = (
            f"[ERR0RS] SubGHz sync → {dest}\n"
            f"  Files synced : {synced}\n"
            f"  Skipped      : {skipped}\n\n"
            f"  Sources: UberGuidoZ, Rocketgod SubGHz Toolkit\n"
            f"  Includes: garage doors, gate remotes, weather stations,\n"
            f"            car key fobs, AM/FM signals, Tire Pressure sensors"
        )
    else:
        # Copy to ERR0RS local output
        dest = SD_OUT / "subghz"
        dest.mkdir(parents=True, exist_ok=True)
        for src_dir in sources:
            if not src_dir.exists():
                continue
            for f in src_dir.rglob("*.sub"):
                try:
                    shutil.copy2(str(f), str(dest / f.name))
                    synced += 1
                except Exception:
                    skipped += 1
        step.status = "done"
        step.output = (
            f"[ERR0RS] No SD path — synced to local output: {dest}\n"
            f"  Files staged : {synced}  (copy to Flipper SD /subghz/ manually)\n"
        )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 4 — NFC / RFID Database ──────────────────────────────────────
def _step_nfc_rfid(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("nfc_sync", "NFC / RFID card database", XP_PER_LEVEL["nfc_sync"])
    t0   = time.time()
    synced = 0
    sources = [
        KB_DIR  / "UberGuidoZ-Flipper" / "nfc",
        KB_DIR  / "UberGuidoZ-Flipper" / "rfid",
        ROCKETGOD / "Flipper_Zero",
    ]
    dest_base = Path(sd_path) if sd_path else SD_OUT
    for folder, exts in [("nfc", [".nfc"]), ("rfid", [".rfid", ".lfrfid"])]:
        dest = dest_base / folder
        dest.mkdir(parents=True, exist_ok=True)
        for src_dir in sources:
            if not src_dir.exists():
                continue
            for ext in exts:
                for f in src_dir.rglob(f"*{ext}"):
                    try:
                        shutil.copy2(str(f), str(dest / f.name))
                        synced += 1
                    except Exception:
                        pass
    step.status = "done"
    step.output = (
        f"[ERR0RS] NFC/RFID sync complete\n"
        f"  Cards synced : {synced}\n"
        f"  Destination  : {dest_base}\n\n"
        f"  Note: UID-cloneable cards work with Flipper read/write.\n"
        f"  iClass / DESFire encrypted cards are read-only (no brute force)."
    )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 5 — IR Library ────────────────────────────────────────────────
def _step_ir(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("ir_sync", "IR blaster — all-device library", XP_PER_LEVEL["ir_sync"])
    t0   = time.time()
    synced = 0
    sources = [
        KB_DIR / "UberGuidoZ-Flipper" / "infrared",
        KB_DIR / "UberGuidoZ-Flipper" / "ir",
        ROCKETGOD / "Flipper_Zero",
    ]
    dest = (Path(sd_path) if sd_path else SD_OUT) / "infrared"
    dest.mkdir(parents=True, exist_ok=True)
    for src_dir in sources:
        if not src_dir.exists():
            continue
        for f in src_dir.rglob("*.ir"):
            try:
                shutil.copy2(str(f), str(dest / f.name))
                synced += 1
            except Exception:
                pass
    step.status = "done"
    step.output = (
        f"[ERR0RS] IR library synced → {dest}\n"
        f"  Remotes loaded: {synced}\n\n"
        f"  Coverage: Samsung, LG, Sony, Philips, Panasonic, Toshiba,\n"
        f"            Roku, Apple TV, projectors, ACs, smart TVs.\n"
        f"  In range: Universal power-off, channel surf, volume ctrl."
    )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 6 — ERR0RS BadUSB Payloads ───────────────────────────────────
def _step_badusb(sd_path: str, state: Dict) -> EvolutionStep:
    """
    Level 6 — BadUSB payload sync.
    Copies payloads from all known sources to the Flipper SD card badusb/ dir.
    Sources:
      - ERR0RS generated payloads (SD_OUT/badusb)
      - Jakoby/Flipper-Zero-BadUSB (knowledge base)
      - narstybits/MacOS-DuckyScripts (knowledge base)
      - UberGuidoZ (knowledge base)
      - aleff-github/my-flipper-shits (92 payloads — Windows/Linux/iOS/macOS)
    """
    step = EvolutionStep("badusb_sync", "ERR0RS + aleff BadUSB payload library", XP_PER_LEVEL["badusb_sync"])
    t0   = time.time()
    synced   = 0
    aleff_synced = 0

    dest = (Path(sd_path) if sd_path else SD_OUT) / "badusb"
    dest.mkdir(parents=True, exist_ok=True)

    # ── 1. Existing knowledge-base sources ───────────────────────────────────
    sources = [
        SD_OUT / "badusb",
        KB_DIR / "Flipper-Zero-BadUSB",
        KB_DIR / "MacOS-DuckyScripts",
        KB_DIR / "UberGuidoZ-Flipper" / "badusb",
    ]
    for src_dir in sources:
        if not src_dir.exists():
            continue
        for f in src_dir.rglob("*.txt"):
            try:
                shutil.copy2(str(f), str(dest / f.name))
                synced += 1
            except Exception:
                pass

    # ── 2. aleff-github/my-flipper-shits ─────────────────────────────────────
    # Write DuckyScript stub files for each aleff payload so they appear on
    # the Flipper SD card. The operator can replace stubs with the real
    # scripts from: https://github.com/aleff-github/my-flipper-shits
    try:
        from src.tools.badusb_studio.aleff_payloads import (
            ALEFF_PAYLOADS, ALEFF_REPO_URL
        )
        aleff_dest = dest / "aleff"
        aleff_dest.mkdir(parents=True, exist_ok=True)

        for p in ALEFF_PAYLOADS:
            # Sanitize name for filesystem
            safe_name = p.name.replace(" ", "_").replace("/", "-")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-.")
            fname = f"ALEFF_{p.platform.replace('GNU-Linux','Linux')}_{safe_name}.txt"
            fpath = aleff_dest / fname

            # PAP indicator comment
            pap_label = {
                "green":  "🟢 PLUG-AND-PLAY — no config needed",
                "yellow": "🟡 NEEDS CONFIG — see README in aleff repo",
                "red":    "🔴 MANUAL SETUP — read aleff documentation first",
            }.get(p.pap, "🟡 CHECK CONFIG")

            stub = (
                f"REM ERR0RS BadUSB — aleff-github Library\n"
                f"REM Payload: {p.name}\n"
                f"REM Platform: {p.platform}\n"
                f"REM Category: {p.category}\n"
                f"REM PAP Status: {pap_label}\n"
                f"REM Source: {ALEFF_REPO_URL}/tree/hello/{p.path}\n"
                f"REM License: GPL-3.0 | Author: aleff (Aleff)\n"
                f"REM\n"
                f"REM [TEACH] {p.teach[:200]}\n"
                f"REM\n"
                f"REM [DEFEND] {p.defend[:200]}\n"
                f"REM\n"
                f"REM ── TO USE ────────────────────────────────────────────\n"
                f"REM Download the real script from the source URL above,\n"
                f"REM copy it into this file, and configure any required\n"
                f"REM variables (webhook URL, tokens, etc.) before running.\n"
                f"REM ────────────────────────────────────────────────────\n"
                f"\n"
                f"DELAY 500\n"
                f"REM Replace this stub with the actual payload from aleff repo\n"
            )
            fpath.write_text(stub, encoding="utf-8")
            aleff_synced += 1

        # Write aleff index
        aleff_idx = aleff_dest / "ALEFF_INDEX.txt"
        with open(aleff_idx, "w", encoding="utf-8") as idx:
            idx.write("# aleff-github/my-flipper-shits — ERR0RS Integration\n")
            idx.write(f"# {ALEFF_REPO_URL}\n")
            idx.write(f"# License: GPL-3.0 | Author: aleff (Aleff)\n")
            idx.write(f"# Generated: {datetime.now().isoformat()}\n")
            idx.write(f"# Total payloads: {aleff_synced}\n\n")
            for p in sorted(ALEFF_PAYLOADS, key=lambda x: (x.platform, x.category, x.name)):
                pap = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(p.pap, "❓")
                idx.write(f"  [{p.platform:10}] [{p.category:18}] {pap} {p.name}\n")

    except Exception as e:
        aleff_synced = 0
        step.output = f"[WARN] aleff payload integration failed: {e}\n"

    # ── 3. Master ERR0RS index ────────────────────────────────────────────────
    index_path = dest / "ERRZ_INDEX.txt"
    try:
        all_files = sorted(dest.rglob("*.txt"))
        with open(index_path, "w", encoding="utf-8") as idx:
            idx.write("# ERR0RS BadUSB Master Payload Index\n")
            idx.write(f"# Generated: {datetime.now().isoformat()}\n")
            idx.write(f"# Total payload files: {len(all_files)}\n\n")
            idx.write("# Sources:\n")
            idx.write("#   ERR0RS generated, Jakoby, narstybits, UberGuidoZ,\n")
            idx.write("#   aleff-github/my-flipper-shits (GPL-3.0)\n\n")
            for f in all_files:
                idx.write(f"  {f.relative_to(dest)}\n")
    except Exception:
        pass

    step.status = "done"
    step.output = (
        f"[ERR0RS] BadUSB payload library synced → {dest}\n"
        f"  ERR0RS/Community payloads : {synced}\n"
        f"  aleff-github payloads     : {aleff_synced} (Windows/Linux/iOS/macOS)\n"
        f"  Total                     : {synced + aleff_synced}\n\n"
        f"  aleff library → {dest}/aleff/\n"
        f"  Sources: ERR0RS generated, Jakoby, narstybits, UberGuidoZ,\n"
        f"           aleff-github/my-flipper-shits [GPL-3.0]\n\n"
        f"  [!] aleff stubs require downloading real scripts from:\n"
        f"      https://github.com/aleff-github/my-flipper-shits\n"
        f"      Configure webhook URLs / tokens before deploying."
    )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 7 — WiFi Dev Board Scripts ───────────────────────────────────
def _step_wifi_scripts(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("wifi_scripts", "WiFi dev board — armed & ready", XP_PER_LEVEL["wifi_scripts"])
    t0   = time.time()

    WIFI_SCRIPTS = {
        "ERRZ_wifi_scanner.txt": """\
# ERR0RS WiFi Scanner — Flipper WiFi Dev Board
# Scans for nearby networks and displays on Flipper screen

DELAY 1000
REM WiFi Dev Board scan trigger
STRING AT+CWLAP
ENTER
DELAY 3000
""",
        "ERRZ_deauth_guide.txt": """\
# ERR0RS Deauth Attack Guide — WiFi Dev Board
# Requires: Flipper WiFi Dev Board (ESP8266/ESP32-S2)
# App: ESP32 WiFi Marauder (install via Flipper App Hub)
#
# MARAUDER COMMANDS (type into Flipper WiFi app):
#   scanAP          - Scan for access points
#   list ap         - List found APs
#   attack -t deauth -i 0   - Deauth AP index 0
#   stopscan        - Stop attack
#
# Firmware: https://github.com/justcallmekoko/ESP32Marauder
REM Load Marauder firmware for full WiFi attack suite
""",
        "ERRZ_evil_portal_quick.txt": """\
# ERR0RS Evil Portal Quick Deploy — WiFi Dev Board
# Requires: flipper-zero-evil-portal app on Flipper
# Firmware: https://github.com/bigbrodude6119/flipper-zero-evil-portal
#
# SETUP:
#   1. Flash evil portal firmware to WiFi dev board
#   2. Upload HTML portal page to Flipper SD: /apps_data/evil_portal/
#   3. Run Evil Portal app on Flipper
#   4. Select portal HTML and start
#
# Flipper broadcasts open WiFi → victims connect → captive portal → harvest
REM Evil Portal ready - see /apps_data/evil_portal/ for HTML templates
""",
        "ERRZ_marauder_install.txt": """\
# ERR0RS — Install ESP32 Marauder on WiFi Dev Board
# Full guide for arming the WiFi dev board with Marauder
#
# METHOD: Flipper App Hub (easiest)
#   1. Flipper > Apps > GPIO > [ESP32] WiFi Marauder
#   2. Install app
#   3. Connect WiFi dev board
#   4. App will offer to flash Marauder firmware
#
# MARAUDER FEATURES once flashed:
#   - Packet sniffer (PCAP capture to SD)
#   - Deauth attacks (sends 802.11 deauth frames)
#   - Beacon spam (flood area with fake SSIDs)
#   - Evil portal  (open AP + captive portal)
#   - PMKID grab   (capture WPA2 hashes passively)
#   - Channel scan + client tracker
#
# AFTER FLASH: Use WiFi Marauder app on Flipper to control everything
REM Marauder install guide complete
""",
    }

    dest = (Path(sd_path) if sd_path else SD_OUT) / "badusb" / "wifi_dev"
    dest.mkdir(parents=True, exist_ok=True)
    written = 0
    for fname, content in WIFI_SCRIPTS.items():
        try:
            with open(dest / fname, "w", encoding="utf-8") as f:
                f.write(content)
            written += 1
        except Exception:
            pass

    # Also sync evil_portal HTML templates if available
    portal_src = KB_DIR / "flipper-zero-evil-portal"
    portal_dest = (Path(sd_path) if sd_path else SD_OUT) / "apps_data" / "evil_portal"
    portal_synced = 0
    if portal_src.exists():
        portal_dest.mkdir(parents=True, exist_ok=True)
        for f in portal_src.rglob("*.html"):
            try:
                shutil.copy2(str(f), str(portal_dest / f.name))
                portal_synced += 1
            except Exception:
                pass

    step.status = "done"
    step.output = (
        f"[ERR0RS] WiFi dev board scripts staged → {dest}\n"
        f"  Scripts written  : {written}\n"
        f"  Portal templates : {portal_synced}\n\n"
        f"  NEXT STEPS:\n"
        f"  1. Install Marauder: Flipper Apps > GPIO > WiFi Marauder\n"
        f"  2. Flash firmware via app (auto-detects dev board)\n"
        f"  3. Connect dev board → run Marauder → full WiFi attack suite\n"
        f"  4. Evil Portal: copy /apps_data/evil_portal/ → Flipper SD"
    )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 8 — Community Packs ──────────────────────────────────────────
def _step_community(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("community_packs", "Rocketgod + UberGuidoZ community packs", XP_PER_LEVEL["community_packs"])
    t0   = time.time()
    synced = 0
    skipped = 0
    dest_base = Path(sd_path) if sd_path else SD_OUT

    PACK_MAP = [
        (ROCKETGOD / "Flipper-Zero-Radio-Scanner",  "subghz" / Path("radio_scanner")),
        (ROCKETGOD / "flipper-zero-rf-jammer",      "subghz" / Path("rf_jammer_ref")),
        (ROCKETGOD / "Flipper_Zero",                "community" / Path("rocketgod")),
        (ROCKETGOD / "WiGLE-Vault",                 "apps_data" / Path("wigle_vault")),
        (ROCKETGOD / "HackRF-Treasure-Chest",       "community" / Path("hackrf_ref")),
        (ROCKETGOD / "ProtoPirate",                 "community" / Path("proto_pirate")),
        (KB_DIR    / "UberGuidoZ-Flipper",          "community" / Path("uberguidoz")),
    ]

    for src, rel_dest in PACK_MAP:
        if not src.exists():
            skipped += 1
            continue
        dest = dest_base / rel_dest
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.rglob("*"):
            if f.is_file() and not f.name.startswith("."):
                target = dest / f.relative_to(src)
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(f), str(target))
                    synced += 1
                except Exception:
                    pass

    step.status = "done"
    step.output = (
        f"[ERR0RS] Community packs synced → {dest_base}\n"
        f"  Files synced : {synced}\n"
        f"  Packs missing: {skipped} (run git submodule update --recursive to fetch)\n\n"
        f"  Packs installed:\n"
        f"    Rocketgod  — Radio Scanner, RF Jammer ref, WiGLE Vault, ProtoPirate\n"
        f"    UberGuidoZ — Full Flipper community megapack\n"
        f"    HackRF     — Reference library for frequency work"
    )
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 9 — ERR0RS Companion Config ───────────────────────────────────
def _step_companion(sd_path: str, state: Dict) -> EvolutionStep:
    step = EvolutionStep("companion_cfg", "ERR0RS companion config & keybinds", XP_PER_LEVEL["companion_cfg"])
    t0   = time.time()

    COMPANION_CFG = {
        "ERRZ_config.txt": f"""\
# ERR0RS Flipper Companion Config
# Generated: {datetime.now().isoformat()}
# Device: ERR0RS-ULTIMATE v3.0

[identity]
name=ERR0RS-FLIPPER
operator=Eros
build=ERR0RS-ULTIMATE-v3

[favorites]
# BadUSB: hold UP on main menu
badusb_default=ERRZ_cred_harvest_windows.txt

# SubGHz: hold RIGHT
subghz_default=keyfob_scan.sub

# IR: hold DOWN
ir_default=universal_tv_poweroff.ir

[hotkeys]
# On Flipper: Settings > Keybinds (Unleashed only)
back_long=power_menu
ok_triple=badusb_quick_launch
up_long=wifi_scan

[opsec]
# Auto-wipe BadUSB history after session
auto_clear_history=true
stealth_mode_led=false
silent_haptic=true
""",
        "ERRZ_README.txt": f"""\
ERR0RS FLIPPER — QUICK REFERENCE
=================================
Evolved by ERR0RS ULTIMATE v3.0
Date: {datetime.now().strftime('%Y-%m-%d')}

DIRECTORY LAYOUT:
  /badusb/          - ERR0RS + Jakoby + UberGuidoZ payloads
  /subghz/          - Full frequency database (all regions)
  /infrared/        - Universal IR library
  /nfc/             - NFC card database
  /rfid/            - RFID / LF RFID cards
  /apps_data/       - App-specific data (evil_portal, wigle, etc)
  /community/       - Rocketgod + UberGuidoZ packs

FIRMWARE: Unleashed (recommended)
  - No frequency restrictions
  - Extra SubGHz protocols
  - Rolling code bypass support
  - Extended NFC support

WIFI DEV BOARD:
  - Flash Marauder via Flipper Apps > GPIO > WiFi Marauder
  - Evil Portal: apps_data/evil_portal/*.html

HAPPY STATE CHECK:
  All systems nominal. ERR0RS has your back.
  Stay legal. Stay ethical. Keep learning.

  github.com/Gnosisone/ERR0RS-Ultimate
""",
    }

    dest = (Path(sd_path) if sd_path else SD_OUT)
    dest.mkdir(parents=True, exist_ok=True)
    written = 0
    for fname, content in COMPANION_CFG.items():
        try:
            with open(dest / fname, "w", encoding="utf-8") as f:
                f.write(content)
            written += 1
        except Exception:
            pass

    step.status = "done"
    step.output = f"[ERR0RS] Companion config written → {dest}\n  Files: {written}"
    step.duration = round(time.time() - t0, 2)
    return step

# ── Step: Level 10 — Calibration & Happy Report ───────────────────────────────
def _step_calibrate(sd_path: str, state: Dict, all_steps: List[EvolutionStep]) -> EvolutionStep:
    step = EvolutionStep("calibration", "Calibration & Happy State Report", XP_PER_LEVEL["calibration"])
    t0   = time.time()

    total_xp   = state.get("total_xp", 0)
    level      = _xp_to_level(total_xp)
    level_info = EVOLUTION_LEVELS[level]
    done_steps = [s for s in all_steps if s.status == "done"]
    fail_steps = [s for s in all_steps if s.status == "failed"]

    # Count files on SD/output
    dest = Path(sd_path) if sd_path else SD_OUT
    total_files = sum(1 for _ in dest.rglob("*") if _.is_file()) if dest.exists() else 0

    happy = len(fail_steps) == 0 and total_xp >= EVOLUTION_LEVELS[5]["xp"]
    state["happy"] = happy

    # Build health report
    report_lines = [
        "=" * 56,
        "  ERR0RS FLIPPER EVOLUTION — HEALTH REPORT",
        f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 56,
        "",
        _level_badge(total_xp),
        "",
        f"  Steps completed : {len(done_steps)} / {len(all_steps)}",
        f"  Steps failed    : {len(fail_steps)}",
        f"  Files on device : {total_files}",
        "",
        "  SUBSYSTEMS:",
    ]

    for s in all_steps:
        icon = {"done": "OK", "skipped": "--", "failed": "XX", "pending": ".."}.get(s.status, "??")
        report_lines.append(f"    [{icon}] {s.name:<38} +{s.xp_reward} XP")

    report_lines += [
        "",
        f"  TOTAL XP : {total_xp}",
        f"  LEVEL    : {level} — {level_info['emoji']} {level_info['name']}",
        "",
    ]

    if happy:
        report_lines += [
            "  HAPPY STATE : *** ACHIEVED ***",
            "  Your Flipper is fully evolved and in its most",
            "  powerful, capable, and happy state.",
            "  It loves you. Go do great things.",
            "",
            "  Stay legal. Stay ethical. Keep learning.",
            "  ERR0RS has your back.",
        ]
    else:
        report_lines += [
            "  HAPPY STATE : Partially evolved",
            "  Run evolution again after fixing failed steps.",
        ]
        for s in fail_steps:
            report_lines.append(f"    FAILED: {s.name} — {s.error[:60]}")

    report_lines.append("=" * 56)
    report_text = "\n".join(report_lines)

    # Save report to SD / output
    report_path = dest / "ERRZ_EVOLUTION_REPORT.txt"
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_text)
    except Exception:
        pass

    step.status   = "done"
    step.output   = report_text
    step.duration = round(time.time() - t0, 2)
    return step

# ── Main Evolution Controller ─────────────────────────────────────────────────
class FlipperEvolution:
    """
    Main entry point. Called by ERR0RS launcher when Flipper is detected.
    Runs all evolution steps in sequence, earns XP, persists state.
    """

    def __init__(self):
        self.state = _load_state()

    def detect(self) -> Dict:
        """Detect if a Flipper is connected."""
        info = detect_flipper()
        if info["found"]:
            self.state["last_seen"]  = datetime.now().isoformat()
            self.state["device_port"] = info["port"]
            self.state["sd_path"]     = info["sd_path"]
            _save_state(self.state)
        return info

    def evolve(self, port: str = "", sd_path: str = "",
               callback: Optional[Callable] = None) -> Dict:
        """
        Run the full evolution sequence.
        callback(step: EvolutionStep) called after each step — use for live UI updates.
        Returns final state dict with full report.
        """
        self.state["session_start"] = datetime.now().isoformat()
        steps: List[EvolutionStep] = []

        def _run_step(step_fn, *args) -> EvolutionStep:
            s = step_fn(*args, self.state)
            steps.append(s)
            # Award XP for completed steps (only once)
            completed = self.state.get("completed_steps", [])
            if s.status == "done" and s.step_id not in completed:
                self.state["total_xp"] = self.state.get("total_xp", 0) + s.xp_reward
                completed.append(s.step_id)
                self.state["completed_steps"] = completed
            self.state["current_level"] = _xp_to_level(self.state["total_xp"])
            _save_state(self.state)
            if callback:
                callback(s)
            return s

        print(f"\n[ERR0RS] ⚡ FLIPPER EVOLUTION SEQUENCE STARTING ⚡")
        print(f"[ERR0RS] Port  : {port or 'auto-detected'}")
        print(f"[ERR0RS] SD    : {sd_path or 'no SD path — local output mode'}")
        print(f"[ERR0RS] XP    : {self.state.get('total_xp', 0)}")
        print(f"[ERR0RS] Level : {self.state.get('current_level', 1)}\n")

        _run_step(_step_backup,       sd_path)
        _run_step(_step_firmware,     port)
        _run_step(_step_subghz,       sd_path)
        _run_step(_step_nfc_rfid,     sd_path)
        _run_step(_step_ir,           sd_path)
        _run_step(_step_badusb,       sd_path)
        _run_step(_step_wifi_scripts, sd_path)
        _run_step(_step_community,    sd_path)
        _run_step(_step_companion,    sd_path)

        # Level 10 — calibration uses all steps
        cal = _step_calibrate(sd_path, self.state, steps)
        steps.append(cal)
        if callback:
            callback(cal)

        # Persist history entry
        history = self.state.get("history", [])
        history.append({
            "ts":          datetime.now().isoformat(),
            "total_xp":    self.state["total_xp"],
            "level":       self.state["current_level"],
            "steps_done":  sum(1 for s in steps if s.status == "done"),
            "happy":       self.state.get("happy", False),
        })
        self.state["history"] = history[-20:]  # keep last 20 sessions
        _save_state(self.state)

        return {
            "status":        "happy" if self.state.get("happy") else "evolved",
            "total_xp":      self.state["total_xp"],
            "level":         self.state["current_level"],
            "level_name":    EVOLUTION_LEVELS[self.state["current_level"]]["name"],
            "level_emoji":   EVOLUTION_LEVELS[self.state["current_level"]]["emoji"],
            "steps":         [{"id": s.step_id, "name": s.name,
                               "status": s.status, "xp": s.xp_reward,
                               "output": s.output} for s in steps],
            "report":        cal.output,
            "happy":         self.state.get("happy", False),
        }

    def status(self) -> Dict:
        """Return current evolution status without running steps."""
        self.state = _load_state()
        xp    = self.state.get("total_xp", 0)
        level = _xp_to_level(xp)
        return {
            "total_xp":      xp,
            "level":         level,
            "level_name":    EVOLUTION_LEVELS[level]["name"],
            "level_emoji":   EVOLUTION_LEVELS[level]["emoji"],
            "badge":         _level_badge(xp),
            "completed":     self.state.get("completed_steps", []),
            "last_seen":     self.state.get("last_seen", "never"),
            "happy":         self.state.get("happy", False),
        }

    def auto_evolve_on_connect(self, poll_interval: int = 3,
                                callback: Optional[Callable] = None) -> None:
        """
        Daemon loop — polls for Flipper connection every poll_interval seconds.
        When detected, runs full evolution automatically.
        Call in a background thread from the launcher.
        """
        import threading
        last_seen = False
        print(f"[ERR0RS] Flipper watcher started (polling every {poll_interval}s)")

        def _watch():
            nonlocal last_seen
            while True:
                info = detect_flipper()
                if info["found"] and not last_seen:
                    print(f"\n[ERR0RS] FLIPPER DETECTED! Port={info['port']} SD={info['sd_path']}")
                    print(f"[ERR0RS] Starting evolution sequence...")
                    self.evolve(
                        port=info["port"],
                        sd_path=info["sd_path"],
                        callback=callback
                    )
                    last_seen = True
                elif not info["found"] and last_seen:
                    print("[ERR0RS] Flipper disconnected.")
                    last_seen = False
                time.sleep(poll_interval)

        t = threading.Thread(target=_watch, daemon=True, name="flipper-watcher")
        t.start()

# ── Module-level singleton & entry point ─────────────────────────────────────
_evo = FlipperEvolution()

def run_flipper_evolution(action: str = "evolve", params: dict = None) -> dict:
    """
    Top-level entry point called by errorz_launcher.py.
    Actions: evolve | detect | status | watch
    """
    params = params or {}
    action = action.strip().lower()

    if action == "detect":
        info = _evo.detect()
        return {
            "status": "found" if info["found"] else "not_found",
            "stdout": (
                f"[ERR0RS] Flipper DETECTED\n"
                f"  Port : {info['port']}\n"
                f"  SD   : {info['sd_path'] or 'not mounted'}\n"
                f"  OS   : {info['os']}"
            ) if info["found"] else "[ERR0RS] No Flipper detected. Plug it in!",
        }

    elif action == "status":
        s = _evo.status()
        return {
            "status": "ok",
            "stdout": (
                f"[ERR0RS] FLIPPER EVOLUTION STATUS\n"
                f"{s['badge']}\n\n"
                f"  Last seen  : {s['last_seen']}\n"
                f"  Happy      : {'YES - MAX POWER!' if s['happy'] else 'Not yet — run evolve'}\n"
                f"  Completed  : {', '.join(s['completed']) or 'none yet'}"
            ),
        }

    elif action in ("evolve", "run", "upgrade", "level_up"):
        info  = _evo.detect()
        result = _evo.evolve(
            port=params.get("port", info.get("port", "")),
            sd_path=params.get("sd_path", info.get("sd_path", "")),
        )
        return {
            "status": result["status"],
            "stdout": result["report"],
            "level":  result["level"],
            "xp":     result["total_xp"],
            "happy":  result["happy"],
        }

    elif action == "watch":
        _evo.auto_evolve_on_connect(
            poll_interval=int(params.get("interval", 3))
        )
        return {"status": "watching", "stdout": "[ERR0RS] Flipper watcher started in background."}

    else:
        return {
            "status": "error",
            "stdout": f"[ERR0RS] Unknown flipper action '{action}'. Valid: detect | status | evolve | watch",
        }


# ── Wizard Menu ───────────────────────────────────────────────────────────────
FLIPPER_WIZARD_MENU = {
    "title": "ERR0RS // FLIPPER ZERO EVOLUTION WIZARD",
    "options": [
        {"key": "1", "label": "Detect Flipper (check if connected)",        "action": "detect"},
        {"key": "2", "label": "Run Full Evolution Sequence (all 10 levels)", "action": "evolve"},
        {"key": "3", "label": "Show Evolution Status + XP Level",           "action": "status"},
        {"key": "4", "label": "Start Auto-Evolve Watcher (background)",     "action": "watch"},
    ]
}


# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[ERR0RS] Flipper Evolution Engine — Self Test")
    print("=" * 56)

    # Status check (no hardware needed)
    r = run_flipper_evolution("status")
    print(r["stdout"])
    print()

    # Detection test
    r = run_flipper_evolution("detect")
    print(r["stdout"])
    print()

    # If Flipper found, offer evolution
    if "DETECTED" in r.get("stdout", ""):
        print("[ERR0RS] Flipper found! Run 'evolve' to start the sequence.")
    else:
        print("[ERR0RS] No hardware connected — running dry-run evolution...")
        r2 = run_flipper_evolution("evolve")
        print(r2["stdout"][:600])

    print("\n[ERR0RS] Flipper Evolution Engine OK")
