"""
ERR0RS BadUSB Studio - Main Orchestrator
The top-level interface that ties together:
  - Payload Browser (Hak5 PayloadHub + local library)
  - AI Payload Generator
  - DuckyScript -> CircuitPython Converter
  - RP2040 Auto-Flasher
  - Payload Studio integration
"""

from .payload_browser import PayloadBrowser
from .payload_generator import PayloadGenerator
from .ducky_converter import DuckyConverter
from .rp2040_flasher import RP2040Flasher


class BadUSBStudio:
    """
    ERR0RS BadUSB Studio - One-stop RP2040 BadUSB programming environment

    Usage:
        studio = BadUSBStudio()
        studio.status()                             # check connected devices
        studio.browse_hak5()                        # list Hak5 categories
        studio.load_hak5("credentials","Duckie-Harvest")  # fetch payload
        studio.generate("harvest wifi passwords")   # AI generates payload
        studio.flash_ducky(payload_text)            # flash to RP2040
    """

    def __init__(self, ai_client=None):
        self.browser = PayloadBrowser()
        self.generator = PayloadGenerator(ai_client=ai_client)
        self.converter = DuckyConverter()
        self.flasher = RP2040Flasher()
        self._current_payload = None

    # ------------------------------------------------------------------ #
    #  DEVICE STATUS                                                      #
    # ------------------------------------------------------------------ #

    def status(self) -> dict:
        """Return full status of connected RP2040 devices"""
        info = self.flasher.get_device_info()
        detected = self.flasher.detect_any_rp2040()
        return {
            "detected_mode": detected["mode"],
            "device_path": detected["path"],
            "ready_for": detected.get("ready_for", "N/A"),
            "bootloader_drive": info["bootloader"],
            "circuitpython_drive": info["circuitpython"],
            "pico_ducky_drive": info["pico_ducky"],
            "available_firmware": info["available_firmware"],
            "platform": info["platform"]
        }

    # ------------------------------------------------------------------ #
    #  PAYLOAD BROWSING                                                   #
    # ------------------------------------------------------------------ #

    def browse_hak5(self) -> list[dict]:
        """List all categories in Hak5 PayloadHub"""
        return self.browser.get_hak5_categories()

    def list_hak5_payloads(self, category: str) -> list[dict]:
        """List payloads in a Hak5 category"""
        return self.browser.get_hak5_payloads(category)

    def load_hak5(self, category: str, payload_name: str) -> str | None:
        """Load a payload from Hak5 PayloadHub and set as current"""
        payload = self.browser.fetch_hak5_payload(category, payload_name)
        if payload:
            self._current_payload = payload
        return payload

    def search_hak5(self, keyword: str) -> list[dict]:
        """Search Hak5 PayloadHub by keyword"""
        return self.browser.search_hak5_payloads(keyword)

    def list_local(self) -> list[str]:
        """List locally saved payloads"""
        return self.browser.list_local_payloads()

    def load_local(self, filename: str) -> str | None:
        """Load a locally saved payload and set as current"""
        payload = self.browser.load_local_payload(filename)
        if payload:
            self._current_payload = payload
        return payload

    def save_current(self, name: str) -> str:
        """Save the current payload to local library"""
        if not self._current_payload:
            return "No current payload loaded."
        return self.browser.save_local_payload(name, self._current_payload)

    # ------------------------------------------------------------------ #
    #  AI PAYLOAD GENERATION                                              #
    # ------------------------------------------------------------------ #

    def generate(self, description: str, target_os: str = "windows",
                 output_format: str = "duckyscript") -> str:
        """Generate a payload using the ERR0RS AI agent"""
        payload = self.generator.generate(description, target_os, output_format)
        self._current_payload = payload
        return payload

    def refine(self, feedback: str) -> str:
        """Refine the current payload using AI feedback"""
        if not self._current_payload:
            return "No current payload to refine."
        refined = self.generator.refine(self._current_payload, feedback)
        self._current_payload = refined
        return refined

    # ------------------------------------------------------------------ #
    #  CONVERSION                                                         #
    # ------------------------------------------------------------------ #

    def convert_to_circuitpython(self, ducky_script: str = None) -> str:
        """Convert DuckyScript to CircuitPython HID script"""
        source = ducky_script or self._current_payload
        if not source:
            return "No payload provided or loaded."
        converted = self.converter.convert(source)
        self._current_payload = converted
        return converted

    # ------------------------------------------------------------------ #
    #  FLASHING                                                           #
    # ------------------------------------------------------------------ #

    def flash_ducky(self, payload: str = None) -> dict:
        """
        Flash a DuckyScript payload to a pico-ducky RP2040.
        If no payload given, uses current payload.
        """
        source = payload or self._current_payload
        if not source:
            return {"success": False, "message": "No payload provided or loaded."}
        return self.flasher.flash_duckyscript_payload(source)

    def flash_circuitpython(self, py_script: str = None, filename: str = "code.py") -> dict:
        """
        Flash a CircuitPython script to a CIRCUITPY RP2040.
        If no script given, uses current payload.
        """
        source = py_script or self._current_payload
        if not source:
            return {"success": False, "message": "No payload provided or loaded."}
        return self.flasher.flash_circuitpython_payload(source, filename)

    def flash_firmware(self, uf2_path: str) -> dict:
        """Flash a UF2 firmware file to RP2040 in bootloader mode"""
        return self.flasher.flash_uf2(uf2_path)

    def wait_for_rp2040(self, timeout: int = 30) -> dict:
        """Wait for an RP2040 to be connected (any mode)"""
        return self.flasher.wait_for_device(timeout=timeout)

    # ------------------------------------------------------------------ #
    #  PAYLOAD STUDIO                                                     #
    # ------------------------------------------------------------------ #

    def open_payload_studio(self) -> str:
        """Open Hak5 Payload Studio in browser"""
        return self.browser.open_payload_studio()

    def export_to_payload_studio(self, payload: str = None) -> str:
        """Save payload locally and open Payload Studio for manual import"""
        source = payload or self._current_payload
        if not source:
            return "No payload to export."
        return self.browser.open_payload_studio_with_payload(source)

    # ------------------------------------------------------------------ #
    #  QUICK WORKFLOWS                                                    #
    # ------------------------------------------------------------------ #

    def quick_program(self, description: str) -> dict:
        """
        Full pipeline: describe -> generate -> flash
        Returns result dict with payload and flash status
        """
        print(f"[ERR0RS] Generating payload: {description}")
        payload = self.generate(description)

        print("[ERR0RS] Detecting RP2040...")
        device = self.flasher.detect_any_rp2040()

        if device["mode"] == "pico-ducky":
            print("[ERR0RS] pico-ducky detected. Flashing DuckyScript...")
            result = self.flash_ducky(payload)
        elif device["mode"] == "circuitpython":
            print("[ERR0RS] CircuitPython detected. Converting and flashing...")
            py_script = self.converter.convert(payload)
            result = self.flash_circuitpython(py_script)
        else:
            result = {
                "success": False,
                "message": f"Device in '{device['mode']}' mode. "
                           "Connect a pico-ducky or CircuitPython RP2040."
            }

        return {
            "payload": payload,
            "device": device,
            "flash_result": result
        }

    def get_current_payload(self) -> str | None:
        """Return the currently loaded payload"""
        return self._current_payload

    def clear(self):
        """Clear the current payload"""
        self._current_payload = None
