# plugins/hardware/flipper_plugin/plugin.py
# ERR0RS-Ultimate — Flipper Zero Hardware Plugin
# Communicates via serial (RogueMaster firmware default: /dev/ttyACM0)

import serial
import time
from src.core.plugin_base import BasePlugin

DEFAULT_PORT    = "/dev/ttyACM0"
DEFAULT_BAUD    = 115200
SERIAL_TIMEOUT  = 2


class Plugin(BasePlugin):

    def on_load(self):
        self.ser = None
        port = self.context.config.get("flipper_port", DEFAULT_PORT)
        self._connect(port)

    def on_unload(self):
        self._disconnect()

    # ── Serial connection ────────────────────────────────────────

    def _connect(self, port: str):
        try:
            self.ser = serial.Serial(port, DEFAULT_BAUD, timeout=SERIAL_TIMEOUT)
            time.sleep(1)  # let Flipper boot CLI
            self.log(f"Connected on {port}")
            self.context.register_hardware("flipper", {
                "port":     port,
                "firmware": self._detect_firmware(),
            })
            self.emit("hardware.connected", {"device": "flipper", "port": port})
        except Exception as e:
            self.log(f"Serial connect failed ({port}): {e}", level="warning")
            self.ser = None

    def _disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.context.unregister_hardware("flipper")
            self.log("Disconnected")

    def _send(self, cmd: str) -> str:
        if not self.ser or not self.ser.is_open:
            return "[flipper] Not connected"
        try:
            self.ser.write((cmd + "\r\n").encode())
            time.sleep(0.3)
            response = b""
            while self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)
                time.sleep(0.05)
            return response.decode(errors="replace").strip()
        except Exception as e:
            self.log(f"Serial send error: {e}", level="error")
            return f"[flipper] Serial error: {e}"

    def _detect_firmware(self) -> str:
        raw = self._send("version")
        for fw in ["RogueMaster", "Unleashed", "Momentum", "Xtreme"]:
            if fw.lower() in raw.lower():
                return fw
        return "Official" if "flipper" in raw.lower() else "Unknown"

    # ── Command dispatch ─────────────────────────────────────────

    def validate_args(self, args: dict) -> bool:
        return True  # all commands can run with empty args

    def run(self, command: str, args: dict):
        if not self.ser or not self.ser.is_open:
            return "[flipper] Not connected — check USB and port in config"

        dispatch = {
            "status": self._status,
            "subghz": self._subghz,
            "badusb": self._badusb,
            "nfc":    self._nfc,
            "ir":     self._ir,
            "gpio":   self._gpio,
        }

        handler = dispatch.get(command)
        if not handler:
            return f"[flipper] Unknown command: '{command}'"

        result = handler(args)

        self.context.add_finding({
            "plugin":  "flipper",
            "type":    command,
            "args":    args,
            "output":  result,
        })
        self.emit(f"flipper.{command}", {"args": args, "result": result})
        return result

    # ── Command handlers ─────────────────────────────────────────

    def _status(self, args: dict) -> str:
        hw = self.context.get_hardware("flipper") or {}
        fw = hw.get("firmware", "Unknown")
        port = hw.get("port", "?")
        bat = self._send("power_info")
        return f"[Flipper] Port: {port} | Firmware: {fw} | Power: {bat}"

    def _subghz(self, args: dict) -> str:
        action = args.get("action", "scan")
        freq   = args.get("freq", "433920000")
        if action == "scan":
            return self._send(f"subghz rx {freq}")
        elif action == "transmit":
            payload = args.get("payload", "")
            return self._send(f"subghz tx {payload}")
        elif action == "replay":
            return self._send(f"subghz tx_from_file {args.get('file','')}")
        return "[flipper] Unknown subghz action"

    def _badusb(self, args: dict) -> str:
        script = args.get("script", "")
        if not script:
            return "[flipper] No script specified"
        return self._send(f"badusb run {script}")

    def _nfc(self, args: dict) -> str:
        action = args.get("action", "read")
        return self._send(f"nfc {action}")

    def _ir(self, args: dict) -> str:
        action  = args.get("action", "receive")
        signal  = args.get("signal", "")
        if action == "send":
            return self._send(f"ir tx {signal}")
        return self._send("ir rx")

    def _gpio(self, args: dict) -> str:
        pin   = args.get("pin", "")
        mode  = args.get("mode", "read")
        value = args.get("value", "")
        if mode == "write":
            return self._send(f"gpio set {pin} {value}")
        return self._send(f"gpio read {pin}")

    def info(self):
        hw = self.context.get_hardware("flipper") or {}
        return {
            "name":        "flipper_plugin",
            "description": "Flipper Zero controller — SubGHz, BadUSB, NFC, IR, GPIO",
            "firmware":    hw.get("firmware", "Unknown"),
            "port":        hw.get("port", "Not connected"),
            "commands":    ["status", "subghz", "badusb", "nfc", "ir", "gpio"],
        }
