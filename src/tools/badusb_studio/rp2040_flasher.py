"""
ERR0RS BadUSB Studio - RP2040 Flasher
Auto-detects RP2040 in bootloader mode and flashes firmware or payloads
Supports: pico-ducky firmware, CircuitPython, raw UF2 files
"""

import os
import sys
import time
import shutil
import platform
from pathlib import Path

# Known RP2040 bootloader drive labels
RP2040_BOOT_LABELS = ["RPI-RP2", "RPIRP2", "RP2040"]
CIRCUITPY_LABELS = ["CIRCUITPY"]
PICO_DUCKY_LABELS = ["DUCKY", "PICORUBBER", "PICO-DUCKY"]

FIRMWARE_DIR = Path(__file__).parent / "firmware"


class RP2040Flasher:
    """Detect and flash RP2040 devices"""

    def __init__(self):
        self.platform = platform.system()

    # ------------------------------------------------------------------ #
    #  DEVICE DETECTION                                                   #
    # ------------------------------------------------------------------ #

    def find_rp2040_bootloader(self) -> str | None:
        """Find RP2040 in BOOTSEL mode (appears as RPI-RP2 drive)"""
        return self._find_drive_by_labels(RP2040_BOOT_LABELS)

    def find_circuitpy(self) -> str | None:
        """Find RP2040 running CircuitPython (CIRCUITPY drive)"""
        return self._find_drive_by_labels(CIRCUITPY_LABELS)

    def find_pico_ducky(self) -> str | None:
        """Find RP2040 running pico-ducky firmware"""
        return self._find_drive_by_labels(PICO_DUCKY_LABELS)

    def detect_any_rp2040(self) -> dict:
        """Detect any connected RP2040 in any mode"""
        boot = self.find_rp2040_bootloader()
        if boot:
            return {"mode": "bootloader", "path": boot, "ready_for": "firmware flash"}

        circ = self.find_circuitpy()
        if circ:
            return {"mode": "circuitpython", "path": circ, "ready_for": "payload drop"}

        pico = self.find_pico_ducky()
        if pico:
            return {"mode": "pico-ducky", "path": pico, "ready_for": "duckyscript drop"}

        return {"mode": "none", "path": None, "ready_for": "connect RP2040"}

    def _find_drive_by_labels(self, labels: list[str]) -> str | None:
        """Search mounted drives for matching volume labels"""
        if self.platform == "Windows":
            return self._find_drive_windows(labels)
        elif self.platform in ("Linux", "Darwin"):
            return self._find_drive_unix(labels)
        return None

    def _find_drive_windows(self, labels: list[str]) -> str | None:
        """Windows: check drive letters for matching volume labels"""
        import subprocess
        try:
            result = subprocess.run(
                ["wmic", "logicaldisk", "get", "DeviceID,VolumeName"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    drive, label = parts[0], parts[1]
                    if label.upper() in [l.upper() for l in labels]:
                        return drive + "\\"
        except Exception:
            pass
        return None

    def _find_drive_unix(self, labels: list[str]) -> str | None:
        """Linux/Mac: search /media and /Volumes for matching labels"""
        search_roots = ["/media", "/run/media", "/Volumes", "/mnt"]
        for root in search_roots:
            root_path = Path(root)
            if root_path.exists():
                for item in root_path.rglob("*"):
                    if item.is_dir() and item.name.upper() in [l.upper() for l in labels]:
                        return str(item)
        return None

    # ------------------------------------------------------------------ #
    #  FLASHING OPERATIONS                                                #
    # ------------------------------------------------------------------ #

    def flash_uf2(self, uf2_path: str) -> dict:
        """Flash a UF2 firmware file to RP2040 in bootloader mode"""
        boot_drive = self.find_rp2040_bootloader()
        if not boot_drive:
            return {
                "success": False,
                "message": "No RP2040 in bootloader mode detected. "
                           "Hold BOOTSEL button while plugging in USB."
            }

        dest = Path(boot_drive) / Path(uf2_path).name
        try:
            shutil.copy2(uf2_path, dest)
            time.sleep(2)  # Wait for device to reboot
            return {
                "success": True,
                "message": f"Firmware flashed successfully from {uf2_path}",
                "device": boot_drive
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def flash_circuitpython_payload(self, py_content: str, filename: str = "code.py") -> dict:
        """Drop a CircuitPython payload onto a CIRCUITPY drive"""
        circ_drive = self.find_circuitpy()
        if not circ_drive:
            return {
                "success": False,
                "message": "No CIRCUITPY drive found. Flash CircuitPython firmware first."
            }

        dest = Path(circ_drive) / filename
        try:
            dest.write_text(py_content, encoding="utf-8")
            return {
                "success": True,
                "message": f"Payload written to {dest}",
                "device": circ_drive
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def flash_duckyscript_payload(self, ducky_content: str) -> dict:
        """Drop a DuckyScript payload.txt onto a pico-ducky drive"""
        pico_drive = self.find_pico_ducky()
        if not pico_drive:
            return {
                "success": False,
                "message": "No pico-ducky drive found. Flash pico-ducky firmware first."
            }

        dest = Path(pico_drive) / "payload.txt"
        try:
            dest.write_text(ducky_content, encoding="utf-8")
            return {
                "success": True,
                "message": f"DuckyScript payload written to {dest}",
                "device": pico_drive
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def wait_for_device(self, mode: str = "any", timeout: int = 30) -> dict:
        """Poll for RP2040 to appear, returns when found or timeout"""
        start = time.time()
        while time.time() - start < timeout:
            result = self.detect_any_rp2040()
            if mode == "any" and result["mode"] != "none":
                return result
            if mode == result["mode"]:
                return result
            time.sleep(1)
        return {"mode": "timeout", "path": None, "message": f"No device found in {timeout}s"}

    def get_device_info(self) -> dict:
        """Return full status of all detected RP2040 devices"""
        return {
            "bootloader": self.find_rp2040_bootloader(),
            "circuitpython": self.find_circuitpy(),
            "pico_ducky": self.find_pico_ducky(),
            "platform": self.platform,
            "firmware_dir": str(FIRMWARE_DIR),
            "available_firmware": [f.name for f in FIRMWARE_DIR.glob("*.uf2")] if FIRMWARE_DIR.exists() else []
        }
