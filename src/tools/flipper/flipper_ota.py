"""
ERR0RS Flipper OTA Asset Pusher
================================
Runs automatically on first Flipper connect to ERR0RS.
Pushes SD card assets, config files, and ERR0RS branding.
Detects firmware version and optionally triggers firmware flash.

Three-stage process:
  Stage 1 — SD card assets  (automatic, silent)
  Stage 2 — Config patching  (automatic, silent)
  Stage 3 — Firmware update  (prompt-gated, tester confirms)

Author: ERR0RS Project | Gary Holden Schneider (Eros)
Purpose: Authorized penetration testing use only
"""

import os
import time
import hashlib
import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from .flipper_bridge import FlipperBridge


# ─────────────────────────────────────────────
#  ERR0RS asset manifest
#  Everything we push to the Flipper SD card
# ─────────────────────────────────────────────

ROOT = Path(__file__).parents[4]   # ERR0RS-Ultimate/

ASSET_MANIFEST = {

    # SubGHz: extended frequency list + region unlock
    "subghz/assets/extend_range.txt": (
        ROOT / "src/tools/flipper/assets/extend_range.txt"
    ),

    # SubGHz: expanded signal database from Unleashed
    "subghz/assets/setting_user.options": (
        ROOT / "src/tools/flipper/assets/setting_user.options"
    ),

    # NFC: expanded Mifare Classic key dictionary
    "nfc/assets/mf_classic_dict_user.nfc": (
        ROOT / "src/tools/flipper/assets/mf_classic_dict_user.nfc"
    ),

    # BadUSB: ERR0RS placeholder payload (empty, tester fills via agent)
    "badusb/err0rs_ready.txt": (
        ROOT / "src/tools/flipper/assets/badusb/err0rs_ready.txt"
    ),

    # IR: expanded remote library
    "infrared/assets/err0rs_remotes.ir": (
        ROOT / "src/tools/flipper/assets/infrared/err0rs_remotes.ir"
    ),

    # ERR0RS identity file — shows on Flipper info screen
    "err0rs_identity.txt": (
        ROOT / "src/tools/flipper/assets/err0rs_identity.txt"
    ),
}

# Minimum firmware version we consider current
# Momentum firmware versioning: YYYYMMDD
MIN_FIRMWARE_DATE = "20240901"

# ERR0RS branding name pushed to device
DEVICE_NAME = "ERR0RS-FZ"


class FlipperOTA:
    """
    Handles first-connect provisioning of a Flipper Zero
    with ERR0RS assets, config, and optional firmware update.
    """

    def __init__(self, bridge: FlipperBridge,
                 confirm_callback=None,
                 progress_callback=None):
        """
        bridge            : connected FlipperBridge instance
        confirm_callback  : async fn(message: str) -> bool
                            called before firmware flash to get tester consent
                            If None, firmware flash is skipped
        progress_callback : fn(stage: str, pct: int, message: str)
                            called to update dashboard progress bar
        """
        self.bridge   = bridge
        self.confirm  = confirm_callback
        self.progress = progress_callback
        self._log     = []

    def _emit(self, stage: str, pct: int, message: str):
        entry = {"stage": stage, "pct": pct, "message": message,
                 "ts": datetime.now().isoformat()}
        self._log.append(entry)
        print(f"[ERR0RS OTA] {stage} ({pct}%) — {message}")
        if self.progress:
            self.progress(stage, pct, message)

    # ─────────────────────────────────────────
    #  Main entry point
    # ─────────────────────────────────────────

    async def provision(self) -> dict:
        """
        Full provisioning sequence.
        Returns summary dict with stage results and any errors.
        """
        results = {
            "started_at":  datetime.now().isoformat(),
            "device":      self.bridge.device_info.to_dict()
                           if self.bridge.device_info else {},
            "stage1_assets":   None,
            "stage2_config":   None,
            "stage3_firmware": None,
            "errors":          [],
            "completed_at":    None,
        }

        self._emit("init", 0, "ERR0RS OTA provisioning started")

        # Stage 1 — SD card assets
        self._emit("assets", 5, "Pushing SD card assets...")
        try:
            results["stage1_assets"] = await self._push_assets()
        except Exception as e:
            results["errors"].append(f"Stage 1 error: {e}")
            self._emit("assets", 33, f"Asset push error: {e}")

        # Stage 2 — Config patching
        self._emit("config", 40, "Patching device configuration...")
        try:
            results["stage2_config"] = await self._patch_config()
        except Exception as e:
            results["errors"].append(f"Stage 2 error: {e}")
            self._emit("config", 66, f"Config patch error: {e}")

        # Stage 3 — Firmware check + optional flash
        self._emit("firmware", 70, "Checking firmware version...")
        try:
            results["stage3_firmware"] = await self._check_and_flash_firmware()
        except Exception as e:
            results["errors"].append(f"Stage 3 error: {e}")
            self._emit("firmware", 95, f"Firmware check error: {e}")

        results["completed_at"] = datetime.now().isoformat()
        results["log"]          = self._log
        self._emit("done", 100, "ERR0RS provisioning complete ✅")
        return results

    # ─────────────────────────────────────────
    #  Stage 1: SD card assets
    # ─────────────────────────────────────────

    async def _push_assets(self) -> dict:
        pushed  = []
        skipped = []
        failed  = []
        total   = len(ASSET_MANIFEST)

        for i, (remote_path, local_path) in enumerate(ASSET_MANIFEST.items()):
            pct = 5 + int((i / total) * 30)
            self._emit("assets", pct, f"Pushing {remote_path}...")

            if not local_path.exists():
                # Generate default asset if missing
                content = self._default_asset(remote_path)
                if content is None:
                    skipped.append(remote_path)
                    continue
            else:
                content = local_path.read_text(errors="replace")

            result = await asyncio.to_thread(
                self._write_file_to_flipper, remote_path, content
            )
            if result:
                pushed.append(remote_path)
            else:
                failed.append(remote_path)

        return {"pushed": pushed, "skipped": skipped, "failed": failed}

    def _write_file_to_flipper(self, remote_path: str, content: str) -> bool:
        """Write a text file to Flipper SD card via CLI storage commands."""
        try:
            full_path = f"/ext/{remote_path}"
            # Ensure parent directory exists
            parent = "/".join(full_path.split("/")[:-1])
            self.bridge._run_cmd(f"storage mkdir {parent}")
            # Remove old version
            self.bridge._run_cmd(f"storage remove {full_path}")
            time.sleep(0.05)
            # Write in lines
            for line in content.splitlines():
                escaped = line.replace('"', '\\"')
                self.bridge._run_cmd(
                    f'storage write_chunk {full_path} "{escaped}\n"'
                )
            # Verify
            stat = self.bridge._run_cmd(f"storage stat {full_path}")
            return bool(stat and "error" not in stat.lower())
        except Exception as e:
            print(f"[OTA] Write failed for {remote_path}: {e}")
            return False

    def _default_asset(self, remote_path: str) -> Optional[str]:
        """Generate sensible defaults for missing asset files."""
        defaults = {
            "subghz/assets/extend_range.txt": (
                "# ERR0RS SubGHz extended range config\n"
                "# Generated by ERR0RS OTA provisioner\n"
                "extend_range=false\n"
                "# Set extend_range=true only for authorized testing\n"
            ),
            "err0rs_identity.txt": (
                f"ERR0RS-Ultimate\n"
                f"Physical Sensor Mode\n"
                f"Provisioned: {datetime.now().strftime('%Y-%m-%d')}\n"
                f"Knowledge. Integrity. Security.\n"
                f"github.com/Gnosisone/ERR0RS-Ultimate\n"
            ),
            "badusb/err0rs_ready.txt": (
                "REM ERR0RS BadUSB Payload Slot\n"
                "REM This file is replaced by ERR0RS Payload Studio\n"
                "REM during authorized engagements.\n"
                "REM Engagement ID required to push payloads.\n"
                "STRING ERR0RS ready\n"
            ),
        }
        return defaults.get(remote_path)

    # ─────────────────────────────────────────
    #  Stage 2: Config patching
    # ─────────────────────────────────────────

    async def _patch_config(self) -> dict:
        changes = []

        # Set device name to ERR0RS-FZ
        self._emit("config", 45, f"Setting device name to {DEVICE_NAME}...")
        result = await asyncio.to_thread(
            self.bridge._run_cmd, f"bt_name {DEVICE_NAME}"
        )
        changes.append({"key": "device_name", "value": DEVICE_NAME,
                        "result": result or "ok"})

        # Write dolphin level to max (unlocks all animations)
        self._emit("config", 52, "Unlocking dolphin animations...")
        result = await asyncio.to_thread(
            self.bridge._run_cmd, "dolphin level 30"
        )
        changes.append({"key": "dolphin_level", "value": 30,
                        "result": result or "ok"})

        # Disable USB re-enumeration lock (lets ERR0RS stay connected)
        self._emit("config", 58, "Configuring USB connection mode...")
        result = await asyncio.to_thread(
            self.bridge._run_cmd, "usb_type_hid 0"
        )
        changes.append({"key": "usb_mode", "value": "cdc_only",
                        "result": result or "ok"})

        return {"changes": changes}

    # ─────────────────────────────────────────
    #  Stage 3: Firmware check + flash
    # ─────────────────────────────────────────

    async def _check_and_flash_firmware(self) -> dict:
        """
        Check firmware version. If outdated, prompt tester to confirm
        before triggering flash via fwflash CLI.

        We NEVER flash without explicit tester confirmation.
        The prompt_callback is what makes this safe —
        it shows the version diff and waits for 'yes'.
        """
        fw_version = self.bridge.device_info.firmware \
                     if self.bridge.device_info else "unknown"

        self._emit("firmware", 72,
                   f"Current firmware: {fw_version}")

        is_outdated = self._firmware_is_outdated(fw_version)

        if not is_outdated:
            self._emit("firmware", 95,
                       f"Firmware {fw_version} is current. No update needed.")
            return {"status": "current", "version": fw_version}

        self._emit("firmware", 75,
                   f"Firmware {fw_version} is older than {MIN_FIRMWARE_DATE}. "
                   f"Update recommended.")

        # Check if we have a confirm callback — required for flash
        if not self.confirm:
            self._emit("firmware", 90,
                       "No confirm callback set. Skipping firmware flash. "
                       "Run flipper_firmware_update() manually to update.")
            return {"status": "update_available",
                    "current": fw_version,
                    "recommended": "Momentum latest",
                    "action": "manual_required"}

        # Ask tester
        msg = (
            f"Flipper firmware {fw_version} is available for update.\n"
            f"ERR0RS recommends Momentum firmware (latest).\n"
            f"This will put the Flipper into DFU mode and flash.\n"
            f"Confirm firmware update? (yes/no)"
        )
        confirmed = await self.confirm(msg)

        if not confirmed:
            self._emit("firmware", 90,
                       "Firmware update declined by tester. Skipping.")
            return {"status": "skipped", "current": fw_version}

        # Trigger flash
        self._emit("firmware", 80, "Initiating firmware flash sequence...")
        flash_result = await asyncio.to_thread(self._flash_firmware)
        return flash_result

    def _firmware_is_outdated(self, fw_version: str) -> bool:
        """
        Parse firmware date string and compare to minimum.
        Handles Momentum format: 'momentum-f7-XX.YYYYMMDD'
        and plain date strings.
        """
        import re
        m = re.search(r"(\d{8})", fw_version)
        if m:
            fw_date = m.group(1)
            return fw_date < MIN_FIRMWARE_DATE
        # Can't parse — assume current to be safe
        return False

    def _flash_firmware(self) -> dict:
        """
        Trigger firmware flash via Flipper CLI DFU mode.

        The Flipper's 'dfu' command reboots into DFU mode.
        From there, `fwflash` (installed as part of qFlipper toolchain)
        handles the actual flash. ERR0RS downloads the latest
        Momentum release from GitHub and flashes it.

        This runs ONLY after tester confirmation.
        """
        try:
            import subprocess
            import tempfile
            import urllib.request

            self._emit("firmware", 82, "Downloading latest Momentum firmware...")

            # Latest Momentum release URL pattern
            # In production, query GitHub API for actual latest tag
            fw_url = (
                "https://github.com/Next-Flip/Momentum-Firmware"
                "/releases/latest/download/momentum-f7-release.tgz"
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                fw_path = Path(tmpdir) / "momentum.tgz"

                # Download
                urllib.request.urlretrieve(fw_url, fw_path)
                self._emit("firmware", 86,
                           f"Downloaded to {fw_path}. Entering DFU mode...")

                # Put Flipper into DFU mode
                self.bridge._run_cmd("dfu")
                time.sleep(3.0)

                # Flash via fwflash (qFlipper CLI tool)
                # Must be installed: pip install flipperzero-tools
                # or via qFlipper installation
                result = subprocess.run(
                    ["fwflash", str(fw_path)],
                    capture_output=True, text=True, timeout=120
                )
                self._emit("firmware", 94,
                           "Flash complete. Waiting for reboot...")
                time.sleep(5.0)

                return {
                    "status":   "flashed",
                    "fw_url":   fw_url,
                    "stdout":   result.stdout[-500:] if result.stdout else "",
                    "returncode": result.returncode
                }

        except FileNotFoundError:
            return {
                "status":  "fwflash_not_found",
                "message": (
                    "fwflash not found. Install qFlipper or "
                    "flipperzero-tools, then re-run provisioning."
                )
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# ─────────────────────────────────────────────
#  Convenience: run OTA from bridge instance
# ─────────────────────────────────────────────

async def run_first_connect_ota(
    bridge: FlipperBridge,
    confirm_callback=None,
    progress_callback=None
) -> dict:
    """
    Called automatically by flipper_agent on first successful connect.

    confirm_callback signature:
        async def my_confirm(message: str) -> bool: ...

    progress_callback signature:
        def my_progress(stage: str, pct: int, message: str): ...
    """
    ota = FlipperOTA(bridge, confirm_callback, progress_callback)
    return await ota.provision()


# ─────────────────────────────────────────────
#  State tracking — only provision once per session
# ─────────────────────────────────────────────

_provisioned_devices = set()


async def maybe_provision(bridge: FlipperBridge, **kwargs) -> Optional[dict]:
    """
    Checks if this device (by port) has been provisioned this session.
    If not, runs full OTA. Safe to call on every connect().
    """
    port = bridge.port or "unknown"
    if port in _provisioned_devices:
        return None   # Already done this session
    _provisioned_devices.add(port)
    print(f"[ERR0RS OTA] First connect on {port} — running provisioning...")
    return await run_first_connect_ota(bridge, **kwargs)
