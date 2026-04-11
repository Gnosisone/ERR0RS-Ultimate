# plugins/hardware/flipper_plugin/plugin.py
import time
from src.core.plugin_base import BasePlugin

DEFAULT_PORT   = "/dev/ttyACM0"
DEFAULT_BAUD   = 115200
SERIAL_TIMEOUT = 2


class Plugin(BasePlugin):

    def on_load(self):
        self.ser  = None
        port = self.context.config.get("flipper_port", DEFAULT_PORT) \
               if hasattr(self.context, "config") else DEFAULT_PORT
        self._connect(port)

    def on_unload(self):
        self._disconnect()

    def _connect(self, port: str):
        try:
            import serial
            self.ser = serial.Serial(port, DEFAULT_BAUD, timeout=SERIAL_TIMEOUT)
            time.sleep(1)
            self.log(f"Connected on {port}")
            if hasattr(self.context, "register_hardware"):
                self.context.register_hardware("flipper", {
                    "port": port, "firmware": self._detect_firmware()
                })
            self.emit("hardware.connected", {"device": "flipper", "port": port})
        except Exception as e:
            self.log(f"Serial connect failed ({port}): {e}", level="warning")
            self.ser = None

    def _disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            if hasattr(self.context, "unregister_hardware"):
                self.context.unregister_hardware("flipper")

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
            return f"[flipper] Serial error: {e}"

    def _detect_firmware(self) -> str:
        raw = self._send("version")
        for fw in ["RogueMaster", "Unleashed", "Momentum", "Xtreme"]:
            if fw.lower() in raw.lower():
                return fw
        return "Official" if "flipper" in raw.lower() else "Unknown"

    def run(self, command: str, args: dict):
        if not self.ser or not self.ser.is_open:
            return "[flipper] Not connected — check USB cable and port"
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
        if hasattr(self.context, "add_finding"):
            self.context.add_finding({
                "plugin": "flipper", "type": command,
                "args": args, "output": result,
            })
        self.emit(f"flipper.{command}", {"args": args, "result": result})
        return result

    def _status(self, args):
        hw   = self.context.get_hardware("flipper") \
               if hasattr(self.context, "get_hardware") else {}
        return (f"[Flipper] Port: {hw.get('port','?')} | "
                f"Firmware: {hw.get('firmware','Unknown')}")

    def _subghz(self, args):
        action = args.get("action", "scan")
        freq   = args.get("freq", "433920000")
        if action == "scan":     return self._send(f"subghz rx {freq}")
        if action == "transmit": return self._send(f"subghz tx {args.get('payload','')}")
        if action == "replay":   return self._send(f"subghz tx_from_file {args.get('file','')}")
        return "[flipper] Unknown subghz action"

    def _badusb(self, args):
        script = args.get("script", "")
        if not script: return "[flipper] No script specified"
        return self._send(f"badusb run {script}")

    def _nfc(self, args):
        return self._send(f"nfc {args.get('action','read')}")

    def _ir(self, args):
        if args.get("action") == "send":
            return self._send(f"ir tx {args.get('signal','')}")
        return self._send("ir rx")

    def _gpio(self, args):
        pin = args.get("pin", "")
        if args.get("mode") == "write":
            return self._send(f"gpio set {pin} {args.get('value','')}")
        return self._send(f"gpio read {pin}")
