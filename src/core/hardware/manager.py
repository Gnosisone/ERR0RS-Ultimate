# src/core/hardware/manager.py
# ERR0RS-Ultimate — Hardware Manager
# Single registry for all connected attack hardware.
# CLI, dashboard, and workflow engine all call this — never raw device classes.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import os
from typing import Dict, List, Optional

from .device_base import DeviceBase, DeviceStatus, PayloadResult
from .flipper      import FlipperDevice
from .hak5         import Hak5Device

logger = logging.getLogger("HardwareManager")


class HardwareManager:
    """
    Central registry for all ERR0RS hardware devices.

    Devices are registered on init using environment / config values.
    Additional devices can be registered at runtime via register().

    Usage
    -----
    manager = HardwareManager(event_bus=ctx.event_bus, safe_mode=False)
    manager.execute("flipper", "rfid_read")
    manager.execute("hak5_ducky", "wifi_harvest")
    print(manager.status_all())
    """

    def __init__(
        self,
        event_bus=None,
        safe_mode: bool = False,
        config:    Dict = None,
    ):
        self.event_bus = event_bus
        self.safe_mode = safe_mode
        self.config    = config or {}
        self._devices: Dict[str, DeviceBase] = {}
        self._register_defaults()

    # ── Registration ──────────────────────────────────────────────────────

    def register(self, name: str, device: DeviceBase):
        """Register a device under a given name."""
        if name in self._devices:
            logger.warning(f"Device '{name}' already registered — overwriting.")
        self._devices[name] = device
        logger.info(f"Registered device: {name} ({device.DEVICE_NAME})")

    def unregister(self, name: str):
        """Remove a device from the registry."""
        self._devices.pop(name, None)

    def _register_defaults(self):
        """Build the default device set from config / environment."""
        flipper_port = (
            self.config.get("flipper_port")
            or os.environ.get("FLIPPER_PORT", "/dev/ttyACM0")
        )
        self.register("flipper", FlipperDevice(
            port=flipper_port,
            event_bus=self.event_bus,
            safe_mode=self.safe_mode,
        ))
        self.register("hak5_ducky", Hak5Device(
            device_type="ducky",
            event_bus=self.event_bus,
            safe_mode=self.safe_mode,
        ))
        self.register("hak5_bunny", Hak5Device(
            device_type="bashbunny",
            event_bus=self.event_bus,
            safe_mode=self.safe_mode,
        ))
        self.register("pineapple", Hak5Device(
            device_type="pineapple",
            event_bus=self.event_bus,
            safe_mode=self.safe_mode,
        ))

    # ── Execution ─────────────────────────────────────────────────────────

    def execute(
        self,
        device_name: str,
        payload:     str,
        args:        Dict = None,
    ) -> PayloadResult:
        """
        Deploy a payload to a named device.
        Returns PayloadResult — never raises.
        """
        device = self._devices.get(device_name)
        if not device:
            available = list(self._devices.keys())
            return PayloadResult(
                device=device_name, payload=payload,
                success=False,
                error=f"Device '{device_name}' not found. "
                      f"Available: {', '.join(available)}",
            )

        result = device.execute(payload, args or {})
        logger.info(
            f"{'✓' if result.success else '✗'} "
            f"{device_name} → {payload} ({result.elapsed:.2f}s)"
        )
        return result

    # ── Status ────────────────────────────────────────────────────────────

    def status_all(self) -> Dict[str, Dict]:
        """Return status dict for every registered device."""
        return {
            name: device.status().to_dict()
            for name, device in self._devices.items()
        }

    def status(self, device_name: str) -> Optional[DeviceStatus]:
        """Return status for a single device, or None if not found."""
        device = self._devices.get(device_name)
        return device.status() if device else None

    def list_devices(self) -> List[Dict]:
        """
        Return a list of device info dicts for dashboard display.
        Does NOT probe hardware — uses cached status for speed.
        """
        return [
            {
                "name":      name,
                "device":    dev.DEVICE_NAME,
                "category":  dev.CATEGORY,
                "connected": dev._status.connected,
                "safe_mode": dev.safe_mode,
                "payloads":  dev.list_payloads(),
            }
            for name, dev in self._devices.items()
        ]

    def probe_all(self) -> Dict[str, bool]:
        """
        Actively probe each device for connection.
        Slower than list_devices() — use for health checks only.
        """
        return {
            name: device.connect()
            for name, device in self._devices.items()
        }

    def set_safe_mode(self, enabled: bool):
        """Toggle safe_mode on ALL devices simultaneously."""
        self.safe_mode = enabled
        for device in self._devices.values():
            device.safe_mode = enabled
        logger.info(f"Safe mode {'ENABLED' if enabled else 'DISABLED'} on all devices.")

    # ── Device retrieval ──────────────────────────────────────────────────

    def get(self, name: str) -> Optional[DeviceBase]:
        return self._devices.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._devices

    def __repr__(self):
        names = list(self._devices.keys())
        return f"<HardwareManager devices={names} safe_mode={self.safe_mode}>"
