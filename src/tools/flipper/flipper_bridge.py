"""
ERR0RS Flipper Bridge
=====================
Core serial communication layer between ERR0RS and Flipper Zero.
Handles device detection, connection, and CLI command execution.

Flipper communicates over USB CDC serial at 230400 baud.
The CLI is accessible after connection — send newline to get prompt.

Author: ERR0RS Project | Gary Holden Schneider (Eros)
Purpose: Authorized penetration testing assistance only
"""

import serial
import serial.tools.list_ports
import asyncio
import threading
import time
import re
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass, field, asdict


# ─────────────────────────────────────────────
#  Data models
# ─────────────────────────────────────────────

@dataclass
class DeviceInfo:
    port: str
    firmware: str = "unknown"
    hardware: str = "unknown"
    name: str = "unknown"
    battery_pct: int = -1
    storage_free_kb: int = -1
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self):
        return asdict(self)


@dataclass
class SubGHzCapture:
    timestamp: str
    frequency: float
    protocol: str
    raw_data: str
    rssi: float = 0.0
    engagement_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class NFCDump:
    timestamp: str
    card_type: str
    uid: str
    raw_pages: list
    atqa: str = ""
    sak: str = ""
    engagement_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)


# ─────────────────────────────────────────────
#  Bridge
# ─────────────────────────────────────────────

class FlipperBridge:
    """
    Manages serial connection to the Flipper Zero CLI.
    All methods are safe to call from async context via
    asyncio.to_thread() or the provided async wrappers.
    """

    BAUD_RATE   = 230400
    TIMEOUT_SEC = 3.0
    PROMPT      = b">: "

    def __init__(self, port: Optional[str] = None,
                 on_capture: Optional[Callable] = None):
        self.port        = port
        self.on_capture  = on_capture
        self._serial     = None
        self._lock       = threading.Lock()
        self._connected  = False
        self.device_info: Optional[DeviceInfo] = None

    # ── Connection ────────────────────────────

    def detect_port(self) -> Optional[str]:
        """Scan connected serial ports for a Flipper Zero."""
        for p in serial.tools.list_ports.comports():
            desc = (p.description or "").lower()
            mfg  = (p.manufacturer or "").lower()
            if "flipper" in desc or "flipper" in mfg:
                return p.device
            if p.vid == 0x0483 and p.pid == 0x5740:
                return p.device
        return None

    def connect(self) -> dict:
        """Open serial connection and fetch device info."""
        if self._connected:
            return {"status": "already_connected",
                    "device": self.device_info.to_dict()}
        port = self.port or self.detect_port()
        if not port:
            return {"status": "error",
                    "message": "Flipper Zero not detected. "
                               "Check USB cable and close qFlipper if open."}
        try:
            self._serial = serial.Serial(port, baudrate=self.BAUD_RATE,
                                         timeout=self.TIMEOUT_SEC)
            time.sleep(0.3)
            self._serial.reset_input_buffer()
            self._send_raw("\n")
            self._read_until_prompt()
            self._connected  = True
            self.port        = port
            self.device_info = DeviceInfo(port=port)
            self._populate_device_info()
            return {"status": "connected", "device": self.device_info.to_dict()}
        except serial.SerialException as e:
            return {"status": "error", "message": str(e)}

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._connected  = False
        self.device_info = None

    @property
    def is_connected(self) -> bool:
        return self._connected and self._serial and self._serial.is_open

    # ── Serial I/O ────────────────────────────

    def _send_raw(self, cmd: str):
        self._serial.write((cmd + "\r\n").encode())
        self._serial.flush()

    def _read_until_prompt(self, timeout: float = 3.0) -> str:
        buf   = b""
        start = time.time()
        while time.time() - start < timeout:
            chunk = self._serial.read(self._serial.in_waiting or 1)
            if chunk:
                buf += chunk
                if self.PROMPT in buf:
                    break
        return buf.decode(errors="replace")

    def _run_cmd(self, cmd: str, timeout: float = 5.0) -> str:
        if not self.is_connected:
            return ""
        with self._lock:
            self._serial.reset_input_buffer()
            self._send_raw(cmd)
            raw   = self._read_until_prompt(timeout)
            lines = raw.splitlines()
            lines = [l for l in lines
                     if l.strip() and l.strip() != cmd.strip()
                     and ">:" not in l]
            return "\n".join(lines).strip()

    # ── Device info ───────────────────────────

    def _populate_device_info(self):
        ver = self._run_cmd("version")
        for line in ver.splitlines():
            if "firmware" in line.lower():
                self.device_info.firmware = line.split(":")[-1].strip()
                break
        name = self._run_cmd("bt_name")
        if name:
            self.device_info.name = name.strip()
        power = self._run_cmd("power_info")
        m = re.search(r"(\d+)%", power)
        if m:
            self.device_info.battery_pct = int(m.group(1))
        stor = self._run_cmd("storage stat /ext")
        m = re.search(r"Free:\s*(\d+)", stor)
        if m:
            self.device_info.storage_free_kb = int(m.group(1))

    def get_status(self) -> dict:
        if not self.is_connected:
            return {"status": "disconnected"}
        power = self._run_cmd("power_info")
        m = re.search(r"(\d+)%", power)
        if m:
            self.device_info.battery_pct = int(m.group(1))
        return {"status": "connected", "device": self.device_info.to_dict()}

    # ── SubGHz ────────────────────────────────

    def capture_subghz(self, frequency_mhz: float = 433.92,
                       duration_sec: int = 10,
                       engagement_id: Optional[str] = None) -> dict:
        """Capture SubGHz RF signals. For authorized engagements only."""
        if not self.is_connected:
            return {"status": "error", "message": "Not connected"}
        freq_hz = int(frequency_mhz * 1_000_000)
        self._run_cmd(f"subghz_set_frequency {freq_hz}")
        time.sleep(0.2)
        self._run_cmd("subghz_rx_start")
        time.sleep(duration_sec)
        raw = self._run_cmd("subghz_rx_stop", timeout=5.0)
        captures = []
        for line in raw.splitlines():
            if not line.strip():
                continue
            cap = SubGHzCapture(
                timestamp=datetime.now().isoformat(),
                frequency=frequency_mhz,
                protocol=self._parse_protocol(line),
                raw_data=line.strip(),
                rssi=self._parse_rssi(line),
                engagement_id=engagement_id
            )
            captures.append(cap.to_dict())
            if self.on_capture:
                self.on_capture(cap)
        return {
            "status": "ok",
            "frequency_mhz": frequency_mhz,
            "duration_sec": duration_sec,
            "captures": captures,
            "count": len(captures),
            "engagement_id": engagement_id,
            "err0rs_context": self._build_subghz_context(frequency_mhz, captures)
        }

    def _parse_protocol(self, line: str) -> str:
        for p in ["Princeton","CAME","Nice","Keeloq","StarLine","Faac","HCS","RAW"]:
            if p.lower() in line.lower():
                return p
        return "Unknown"

    def _parse_rssi(self, line: str) -> float:
        m = re.search(r"RSSI[:\s]+(-?\d+\.?\d*)", line, re.I)
        return float(m.group(1)) if m else 0.0

    def _build_subghz_context(self, freq: float, captures: list) -> str:
        if not captures:
            return f"No signals captured on {freq} MHz."
        protocols = list(set(c["protocol"] for c in captures))
        return (f"Flipper Zero captured {len(captures)} signal(s) on "
                f"{freq} MHz during authorized engagement. "
                f"Detected protocols: {', '.join(protocols)}. "
                f"Analyze for protocol vulnerabilities and known CVEs.")

    # ── NFC ───────────────────────────────────

    def dump_nfc(self, engagement_id: Optional[str] = None) -> dict:
        """Read NFC card. Returns data for ERR0RS AI analysis."""
        if not self.is_connected:
            return {"status": "error", "message": "Not connected"}
        self._run_cmd("nfc_detect")
        time.sleep(1.5)
        raw = self._run_cmd("nfc_read", timeout=8.0)
        if not raw or "no card" in raw.lower():
            return {"status": "no_card",
                    "message": "No NFC card detected. Hold card against Flipper back."}
        dump = NFCDump(
            timestamp=datetime.now().isoformat(),
            card_type=self._parse_nfc_type(raw),
            uid=self._parse_nfc_uid(raw),
            raw_pages=self._parse_nfc_pages(raw),
            atqa=self._parse_field(raw, "ATQA"),
            sak=self._parse_field(raw, "SAK"),
            engagement_id=engagement_id
        )
        return {
            "status": "ok",
            "card": dump.to_dict(),
            "engagement_id": engagement_id,
            "err0rs_context": (
                f"NFC card read during authorized engagement. "
                f"Type: {dump.card_type}. UID: {dump.uid}. "
                f"ATQA: {dump.atqa} SAK: {dump.sak}. "
                f"Analyze for Mifare Classic, DESFire, Ultralight vulnerabilities."
            )
        }

    def _parse_nfc_type(self, raw: str) -> str:
        types = {
            "Mifare Classic":    ["mifare classic","mfc"],
            "Mifare Ultralight": ["ultralight","ntag"],
            "Mifare DESFire":    ["desfire"],
            "ISO 14443-A":       ["iso14443"],
            "iClass":            ["iclass","picopass"],
        }
        r = raw.lower()
        for name, kw in types.items():
            if any(k in r for k in kw):
                return name
        return "Unknown"

    def _parse_nfc_uid(self, raw: str) -> str:
        m = re.search(r"UID[:\s]+([0-9A-Fa-f :]+)", raw)
        return m.group(1).strip() if m else "unknown"

    def _parse_nfc_pages(self, raw: str) -> list:
        pages = []
        for line in raw.splitlines():
            m = re.match(r"\s*(\d+)\s*\|\s*([0-9A-Fa-f\s]+)", line)
            if m:
                pages.append({"page": int(m.group(1)), "data": m.group(2).strip()})
        return pages

    def _parse_field(self, raw: str, field: str) -> str:
        m = re.search(rf"{field}[:\s]+([0-9A-Fa-f]+)", raw, re.I)
        return m.group(1).strip() if m else ""

    # ── BadUSB ────────────────────────────────

    def push_badusb_payload(self, payload_name: str, duckyscript: str,
                             engagement_id: Optional[str] = None) -> dict:
        """
        Write DuckyScript to Flipper SD card.
        engagement_id REQUIRED — no engagement, no push.
        Physical execution by authorized tester only.
        """
        if not engagement_id:
            return {"status": "error",
                    "message": "engagement_id required. Start an engagement first."}
        if not self.is_connected:
            return {"status": "error", "message": "Not connected"}
        safe_name   = re.sub(r"[^a-zA-Z0-9_\-]", "_", payload_name)
        remote_path = f"/ext/badusb/err0rs_{safe_name}.txt"
        self._run_cmd(f"storage remove {remote_path}")
        time.sleep(0.1)
        for line in duckyscript.splitlines():
            escaped = line.replace('"', '\\"')
            self._run_cmd(f'storage write_chunk {remote_path} "{escaped}\n"')
        verify  = self._run_cmd(f"storage stat {remote_path}")
        success = "size" in verify.lower() or "file" in verify.lower()
        return {
            "status":       "ok" if success else "error",
            "path":         remote_path,
            "payload_name": safe_name,
            "engagement_id":engagement_id,
            "lines":        len(duckyscript.splitlines()),
            "note":         "Payload stored. Physical execution by authorized tester only."
        }

    # ── IR ────────────────────────────────────

    def capture_ir(self, duration_sec: int = 5,
                   engagement_id: Optional[str] = None) -> dict:
        if not self.is_connected:
            return {"status": "error", "message": "Not connected"}
        self._run_cmd("ir_rx start")
        time.sleep(duration_sec)
        raw     = self._run_cmd("ir_rx stop", timeout=4.0)
        signals = [l.strip() for l in raw.splitlines()
                   if "protocol" in l.lower() or "raw" in l.lower()]
        return {"status": "ok", "signals": signals, "count": len(signals),
                "engagement_id": engagement_id}

    # ── Async wrappers ────────────────────────

    async def async_connect(self) -> dict:
        return await asyncio.to_thread(self.connect)

    async def async_capture_subghz(self, **kwargs) -> dict:
        return await asyncio.to_thread(self.capture_subghz, **kwargs)

    async def async_dump_nfc(self, **kwargs) -> dict:
        return await asyncio.to_thread(self.dump_nfc, **kwargs)

    async def async_push_badusb_payload(self, **kwargs) -> dict:
        return await asyncio.to_thread(self.push_badusb_payload, **kwargs)


# ── Singleton ─────────────────────────────────

_bridge_instance: Optional[FlipperBridge] = None

def get_bridge() -> FlipperBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = FlipperBridge()
    return _bridge_instance
