# ERR0RS BadUSB Studio — Firmware Directory

Place RP2040 `.uf2` firmware files here. ERR0RS auto-detects them.

## Recommended Firmware

### pico-ducky (DuckyScript on Pico)
Download from: https://github.com/dbisu/pico-ducky/releases
File: `pico-ducky.uf2`
Flash method: Hold BOOTSEL → plug USB → RPI-RP2 drive appears → ERR0RS flashes it

### CircuitPython (for AI-generated payloads)
Download from: https://circuitpython.org/board/raspberry_pi_pico/
File: `adafruit-circuitpython-raspberry_pi_pico-*.uf2`
Required libraries (drop in CIRCUITPY/lib/):
  - adafruit_hid (from Adafruit CircuitPython Bundle)

## Flash Workflow via ERR0RS UI
1. Open Payload Studio → click "⚡ FLASH TO PICO"
2. ERR0RS calls POST /api/rp2040 { "action": "detect" }
3. If in bootloader mode → flash firmware automatically
4. If running pico-ducky → drop payload.txt directly
5. If running CircuitPython → convert DuckyScript → code.py and drop

## Manual Flash (fallback)
```bash
# Hold BOOTSEL, plug in Pico — RPI-RP2 drive mounts
cp firmware/pico-ducky.uf2 /media/$USER/RPI-RP2/
# Pico reboots as HID keyboard
```
