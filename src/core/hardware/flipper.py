# src/core/hardware/flipper.py
# ERR0RS-Ultimate — Flipper Zero Hardware Adapter
#
# This is the orchestration adapter, NOT the low-level driver.
# Low-level serial comms live in src/tools/flipper/flipper_bridge.py.
# This class wraps that driver and exposes it through DeviceBase so the
# HardwareManager can treat it like any other device.
#
# Supported operations via the Flipper CLI:
#   subghz_sniff  — passive Sub-GHz capture
#   subghz_replay — replay a captured signal
#   rfid_read     — read EM4100 / HID Prox card
#   rfid_write    — write a saved card to blank
#   nfc_read      — NFC card dump
#   badusb_run    — run a DuckyScript payload
#   ir_send       — transmit infrared command
#   gpio_pulse    — GPIO control
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import os
import logging
from typing import Dict, List, Optional

from .device_base import DeviceBase, DeviceStatus, PayloadResult

logger = logging.getLogger("Hardware.FlipperZero")

# Map of friendly payload names → Flipper CLI commands
PAYLOAD_MAP: Dict[str, str] = {
    "subghz_sniff":  "subghz rx 433920000",
    "subghz_replay": "subghz tx_from_file /ext/subghz/capture.sub",
    "rfid_read":     "lfrfid read",
    "rfid_write":    "lfrfid write EM4100 /ext/lfrfid/card.rfid",
    "nfc_read":      "nfc detect",
    "badusb_run":    "badusb run /ext/badusb/payload.txt",
    "ir_send":       "infrared transmit /ext/infrared/signal.ir",
}


class FlipperDevice(DeviceBase):
    """
    ERR0RS hardware adapter for Flipper Zero.

    Tries to import and use FlipperBridge (real serial comms).
    Falls back to mount-path file-based execution if the bridge
    isn't available (useful for offline/lab testing).
    """

    DEVICE_NAME = "Flipper Zero"
    CATEGORY    = "rf_hardware"

    def __init__(
        self,
        port: str         = None,
        mount_path: str   = "/media/flipper",
        event_bus         = None,
        safe_mode: bool   = False,
    ):
        super().__init__(event_bus=event_bus, safe_mode=safe_mode)
        self.port       = port or os.environ.get("FLIPPER_PORT", "/dev/ttyACM0")
        self.mount_path = mount_path
        self._bridge: Optional[object] = None
        self._bridge_available = self._try_load_bridge()

    # ── Bridge loader ─────────────────────────────────────────────────────

    def _try_load_bridge(self) -> bool:
        """Attempt to import the low-level FlipperBridge driver."""
        try:
            from src.tools.flipper.flipper_bridge import FlipperBridge
            self._bridge = FlipperBridge(port=self.port)
            logger.info("FlipperBridge loaded — serial mode active.")
            return True
        except ImportError:
            logger.debug("FlipperBridge not importable — mount-path mode.")
            return False
        except Exception as e:
            logger.warning(f"FlipperBridge init error: {e}")
            return False

    # ── DeviceBase implementation ─────────────────────────────────────────

    def _do_connect(self) -> bool:
        # Serial bridge path
        if self._bridge_available and self._bridge:
            try:
                connected = self._bridge.connect()
                if connected:
                    info = self._bridge.get_device_info()
                    self._status.firmware  = getattr(info, "firmware", "unknown")
                    self._status.battery_pct = getattr(info, "battery_pct", -1)
                return connected
            except Exception as e:
                logger.warning(f"Bridge connect failed: {e}")

        # Mount-path fallback
        connected = os.path.exists(self.mount_path)
        if connected:
            logger.debug(f"Flipper detected at mount path: {self.mount_path}")
        return connected

    def _do_execute(self, payload: str, args: Dict) -> PayloadResult:
        cli_cmd = PAYLOAD_MAP.get(payload)

        # Serial bridge — send CLI command
        if self._bridge_available and self._bridge and cli_cmd:
            try:
                output = self._bridge.run_cli(cli_cmd)
                return PayloadResult(
                    device=self.DEVICE_NAME, payload=payload,
                    success=True, output=str(output),
                )
            except Exception as e:
                return PayloadResult(
                    device=self.DEVICE_NAME, payload=payload,
                    success=False, error=str(e),
                )

        # Mount-path fallback — check file exists
        script_path = os.path.join(self.mount_path, "scripts", f"{payload}.txt")
        if os.path.exists(script_path):
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=True,
                output=f"[MOUNT] Payload queued: {script_path}",
            )

        return PayloadResult(
            device=self.DEVICE_NAME, payload=payload,
            success=False,
            error=f"Payload '{payload}' not found on Flipper. "
                  f"Known payloads: {', '.join(self.list_payloads())}",
        )

    def _do_status(self) -> DeviceStatus:
        connected = self._do_connect()
        return DeviceStatus(
            name=self.DEVICE_NAME,
            connected=connected,
            firmware=self._status.firmware,
            battery_pct=self._status.battery_pct,
            safe_mode=self.safe_mode,
            extra={"port": self.port, "mount": self.mount_path,
                   "bridge": self._bridge_available},
        )

    def list_payloads(self) -> List[str]:
        return list(PAYLOAD_MAP.keys())

    def run_cli(self, command: str) -> str:
        """
        Send a raw CLI command directly to the Flipper.
        Useful for advanced / custom operations.
        """
        if not self._bridge_available or not self._bridge:
            return "[ERROR] Serial bridge not available."
        try:
            return str(self._bridge.run_cli(command))
        except Exception as e:
            return f"[ERROR] CLI command failed: {e}"
