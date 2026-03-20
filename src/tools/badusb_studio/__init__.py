# ERR0RS BadUSB Studio
# RP2040 BadUSB programmer, payload browser, and AI payload generator
# Integrates with Hak5 PayloadHub and Payload Studio

from .payload_browser import PayloadBrowser
from .payload_generator import PayloadGenerator
from .ducky_converter import DuckyConverter
from .rp2040_flasher import RP2040Flasher
from .badusb_studio import BadUSBStudio

__all__ = [
    "PayloadBrowser",
    "PayloadGenerator",
    "DuckyConverter",
    "RP2040Flasher",
    "BadUSBStudio",
]

__version__ = "1.0.0"
__author__ = "ERR0RS ULTIMATE"
__description__ = "BadUSB Studio - RP2040 programmer and payload manager for red teamers"
