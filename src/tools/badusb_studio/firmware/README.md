# ERR0RS BadUSB Studio - Firmware Directory

Place your RP2040 UF2 firmware files here.

## Required Firmware Files

### Option 1: pico-ducky (RECOMMENDED for Hak5 DuckyScript compatibility)
- Download from: https://github.com/dbisu/pico-ducky
- File: `pico-ducky.uf2` (or the duckyinpython .uf2)
- After flashing: RP2040 appears as "DUCKY" drive
- Drop `payload.txt` directly onto the drive

### Option 2: CircuitPython (for AI-generated Python payloads)
- Download from: https://circuitpython.org/board/raspberry_pi_pico/
- File: `adafruit-circuitpython-raspberry_pi_pico-*.uf2`
- After flashing: RP2040 appears as "CIRCUITPY" drive
- Drop `code.py` onto the drive
- Also install adafruit_hid library in CIRCUITPY/lib/

### How to Flash Firmware
1. Hold BOOTSEL button on RP2040
2. Plug in USB while holding BOOTSEL
3. RP2040 appears as "RPI-RP2" drive
4. Use ERR0RS BadUSB Studio: studio.flash_firmware("path/to/firmware.uf2")
   OR manually drag the .uf2 file onto the RPI-RP2 drive

## RP2040 Compatible Hardware
- Raspberry Pi Pico / Pico W / Pico 2
- Adafruit Feather RP2040
- SparkFun Pro Micro RP2040
- Waveshare RP2040 Zero (tiny form factor, great for BadUSB)
- Any board with RP2040 chip

## Notes
- .uf2 files are NOT included due to size. Download separately.
- ERR0RS BadUSB Studio handles everything else automatically.
