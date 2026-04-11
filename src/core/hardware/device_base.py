# src/core/hardware/device_base.py
# ERR0RS-Ultimate — Abstract Hardware Device Base
# All physical attack hardware (Flipper Zero, Hak5, etc.) inherits from this.
# Provides: lifecycle, safe_mode gate, event emission, status reporting.
#
# NOTE: This is the orchestration layer that sits ABOVE the deep serial/USB
# drivers in src/tools/flipper/flipper_bridge.py — it calls those drivers.
# It does NOT duplicate them.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Hardware")


@dataclass
class DeviceStatus:
    name:          str
    connected:     bool    = False
    firmware:      str     = "unknown"
    battery_pct:   int     = -1
    last_seen:     float   = field(default_factory=time.time)
    safe_mode:     bool    = False
    extra:         Dict    = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self):
        state = "Connected" if self.connected else "Disconnected"
        batt  = f" | Battery: {self.battery_pct}%" if self.battery_pct >= 0 else ""
        fw    = f" | FW: {self.firmware}" if self.firmware != "unknown" else ""
        return f"{self.name}: {state}{batt}{fw}"


@dataclass
class PayloadResult:
    device:   str
    payload:  str
    success:  bool
    output:   str     = ""
    error:    str     = ""
    elapsed:  float   = 0.0
    timestamp: float  = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return asdict(self)

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.device} → {self.payload}: {self.output or self.error}"


class DeviceBase(ABC):
    """
    Abstract base for all ERR0RS hardware device drivers.

    Subclasses must implement:
        _do_connect()    -> bool
        _do_execute()    -> PayloadResult
        _do_status()     -> DeviceStatus

    Subclasses may override:
        list_payloads()  -> List[str]
        get_info()       -> Dict
    """

    # Override in subclass
    DEVICE_NAME: str = "Unknown Device"
    CATEGORY:    str = "generic"

    def __init__(self, event_bus=None, safe_mode: bool = False):
        self.event_bus = event_bus
        self.safe_mode = safe_mode
        self._status   = DeviceStatus(name=self.DEVICE_NAME, safe_mode=safe_mode)
        self._log      = logging.getLogger(f"Hardware.{self.DEVICE_NAME}")

    # ── Public API ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Attempt to connect to the device. Updates internal status."""
        try:
            connected = self._do_connect()
            self._status.connected = connected
            self._status.last_seen = time.time()
            if connected:
                self._log.info(f"{self.DEVICE_NAME} connected.")
                self._emit("device.connected", {"device": self.DEVICE_NAME})
            return connected
        except Exception as e:
            self._log.error(f"Connection error: {e}")
            self._status.connected = False
            return False

    def execute(self, payload: str, args: Dict = None) -> PayloadResult:
        """
        Deploy a payload to the device.
        Blocked in safe_mode. Calls _do_execute() on success.
        """
        if self.safe_mode:
            msg = (f"[SAFE_MODE] Hardware execution blocked — "
                   f"{self.DEVICE_NAME} → {payload}")
            self._log.warning(msg)
            return PayloadResult(
                device=self.DEVICE_NAME, payload=payload,
                success=False, error=msg,
            )

        if not self._status.connected:
            if not self.connect():
                err = f"{self.DEVICE_NAME} not connected — cannot deploy '{payload}'"
                return PayloadResult(
                    device=self.DEVICE_NAME, payload=payload,
                    success=False, error=err,
                )

        self._log.info(f"Deploying '{payload}'…")
        self._emit("device.action", {
            "device": self.DEVICE_NAME, "payload": payload,
        })

        t0     = time.time()
        result = self._do_execute(payload, args or {})
        result.elapsed = round(time.time() - t0, 3)

        event = "device.success" if result.success else "device.error"
        self._emit(event, result.to_dict())
        return result

    def status(self) -> DeviceStatus:
        """Refresh and return the device status."""
        try:
            self._status = self._do_status()
            self._status.safe_mode = self.safe_mode
        except Exception as e:
            self._log.debug(f"Status refresh error: {e}")
        return self._status

    def list_payloads(self) -> List[str]:
        """Return available payload names for this device."""
        return []

    def get_info(self) -> Dict:
        """Return device metadata for the dashboard."""
        return {
            "name":     self.DEVICE_NAME,
            "category": self.CATEGORY,
            "status":   self.status().to_dict(),
            "payloads": self.list_payloads(),
        }

    # ── Abstract — subclass must implement ────────────────────────────────

    @abstractmethod
    def _do_connect(self) -> bool:
        """Perform the actual connection attempt. Return True on success."""

    @abstractmethod
    def _do_execute(self, payload: str, args: Dict) -> PayloadResult:
        """Perform the actual payload deployment."""

    @abstractmethod
    def _do_status(self) -> DeviceStatus:
        """Return a fresh DeviceStatus."""

    # ── Helpers ───────────────────────────────────────────────────────────

    def _emit(self, event: str, data: Any = None):
        if self.event_bus:
            try:
                self.event_bus.emit(event, data)
            except Exception as e:
                self._log.debug(f"Event emit error: {e}")

    def __repr__(self):
        return f"<Device:{self.DEVICE_NAME} connected={self._status.connected}>"
