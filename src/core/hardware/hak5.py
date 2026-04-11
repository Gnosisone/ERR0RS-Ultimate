# src/core/hardware/hak5.py
# ERR0RS-Ultimate — Hak5 Device Adapter
# Supports: USB Rubber Ducky, Bash Bunny, WiFi Pineapple Nano, Shark Jack
#
# Each Hak5 device mounts as a USB mass-storage + CDC-serial combo.
# Payloads are DuckyScript (.txt) or Bash Bunny (.sh) files that we
# stage to the device's payload partition and trigger.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import os
import subprocess
import shutil
import logging
from typing import Dict, List, Optional

from .device_base import DeviceBase, DeviceStatus, PayloadResult

logger = logging.getLogger("Hardware.Hak5")

# Default payload staging directories per device type
PAYLOAD_DIRS: Dict[str, str] = {
    "ducky":      "devices/payloads/ducky",
    "bashbunny":  "devices/payloads/bashbunny",
    "pineapple":  "devices/payloads/pineapple",
    "sharkjack":  "devices/payloads/sharkjack",
}

# Pineapple Nano default API endpoint
PINEAPPLE_API = "http://172.16.42.1:1471/api"


class Hak5Device(DeviceBase):
    """
    ERR0RS hardware adapter for the Hak5 device family.

    device_type options:
        "ducky"     — USB Rubber Ducky (DuckyScript)
        "bashbunny" — Bash Bunny (Switch 1/2 payloads)
        "pineapple" — WiFi Pineapple Nano (REST API)
        "sharkjack" — Shark Jack (bash payloads over SSH)
    """

    DEVICE_NAME = "Hak5 Device"
    CATEGORY    = "usb_hardware"

    def __init__(
        self,
        device_type: str  = "ducky",
        payload_base: str = None,
        event_bus         = None,
        safe_mode: bool   = False,
    ):
        super().__init__(event_bus=event_bus, safe_mode=safe_mode)
        self.device_type  = device_type
        self.payload_base = payload_base or PAYLOAD_DIRS.get(device_type, "devices/payloads")
        self.DEVICE_NAME  = f"Hak5 {device_type.title()}"

    # ── DeviceBase implementation ─────────────────────────────────────────

    def _do_connect(self) -> bool:
        """
        Detect device presence.
        Ducky/BashBunny: check for USB mass-storage mount.
        Pineapple: check REST API reachability.
        """
        if self.device_type == "pineapple":
            return self._ping_pineapple()
        if self.device_type == "sharkjack":
            return self._check_sharkjack()
        # Ducky / BashBunny: check /dev/sdX or /media mount
        for path in ["/media/ducky", "/media/bashbunny", "/media/bunny",
                     "/dev/sdb1", "/dev/sdc1"]:
            if os.path.exists(path):
                return True
        # Fallback: lsblk check for removable USB mass-storage
        try:
            result = subprocess.run(
                ["lsblk", "-o", "NAME,RM,TYPE", "--noheadings"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "1" and parts[2] == "disk":
                    return True
        except Exception:
            pass
        return False

    def _do_execute(self, payload: str, args: Dict) -> PayloadResult:
        """Execute a payload by device type."""
        if self.device_type == "pineapple":
            return self._execute_pineapple(payload, args)
        return self._execute_script(payload, args)

    def _do_status(self) -> DeviceStatus:
        connected = self._do_connect()
        return DeviceStatus(
            name=self.DEVICE_NAME,
            connected=connected,
            safe_mode=self.safe_mode,
            extra={
                "device_type":  self.device_type,
                "payload_base": self.payload_base,
            },
        )

    # ── Script-based execution (Ducky / BashBunny / SharkJack) ───────────

    def _execute_script(self, payload: str, args: Dict) -> PayloadResult:
        """
        Stage and run a DuckyScript or bash payload.
        Tries .txt extension first (DuckyScript), then .sh (bash).
        """
        base = args.get("payload_dir", self.payload_base)
        candidates = [
            os.path.join(base, f"{payload}.txt"),
            os.path.join(base, f"{payload}.sh"),
            os.path.join(base, payload),
        ]

        script_path: Optional[str] = None
        for c in candidates:
            if os.path.isfile(c):
                script_path = c
                break

        if not script_path:
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=False,
                error=f"Payload '{payload}' not found in {base}. "
                      f"Available: {', '.join(self.list_payloads())}",
            )

        try:
            if script_path.endswith(".sh"):
                proc = subprocess.run(
                    ["bash", script_path],
                    capture_output=True, text=True, timeout=60
                )
            else:
                # DuckyScript: just confirm the file is staged; the device
                # runs it on its own after USB reconnect.
                proc = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout=f"DuckyScript staged: {script_path}", stderr=""
                )

            output = proc.stdout + proc.stderr
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=proc.returncode == 0,
                output=output.strip(),
                error="" if proc.returncode == 0 else proc.stderr,
            )
        except subprocess.TimeoutExpired:
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=False, error="Script timed out after 60s",
            )
        except Exception as e:
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=False, error=str(e),
            )

    # ── WiFi Pineapple REST API ───────────────────────────────────────────

    def _ping_pineapple(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(PINEAPPLE_API, timeout=3)
            return True
        except Exception:
            return False

    def _execute_pineapple(self, payload: str, args: Dict) -> PayloadResult:
        """Send a module activation request to the Pineapple REST API."""
        try:
            import urllib.request, json as _json, urllib.parse
            data = _json.dumps({"module": payload, **args}).encode()
            req  = urllib.request.Request(
                f"{PINEAPPLE_API}/module",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            resp   = urllib.request.urlopen(req, timeout=10)
            body   = resp.read().decode()
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=True, output=body,
            )
        except Exception as e:
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=False, error=str(e),
            )

    # ── Shark Jack ───────────────────────────────────────────────────────

    def _check_sharkjack(self) -> bool:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", "172.16.24.1"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── Payload listing ───────────────────────────────────────────────────

    def list_payloads(self) -> List[str]:
        payloads = []
        if os.path.isdir(self.payload_base):
            for fname in os.listdir(self.payload_base):
                if fname.endswith((".txt", ".sh")):
                    payloads.append(fname.rsplit(".", 1)[0])
        return sorted(payloads)
