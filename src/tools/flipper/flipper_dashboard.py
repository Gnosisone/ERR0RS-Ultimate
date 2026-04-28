"""
ERR0RS Flipper Dashboard Card
==============================
Penligent-style dashboard card for Flipper Zero status.
Drops into the existing ERR0RS dashboard alongside other tool cards.

Backend: shapes data from /flipper/status for the UI card.
Frontend: React JSX + CSS exported as strings for easy drop-in.

Author: ERR0RS Project | Gary Holden Schneider (Eros)
"""

from datetime import datetime


def shape_dashboard_card(status: dict) -> dict:
    """Transform bridge status into dashboard card data format."""
    connected = status.get("status") == "connected"
    device    = status.get("device", {})
    battery   = device.get("battery_pct", -1)
    ota       = status.get("ota", {})

    batt_icon = (
        "🔋" if battery > 60 else
        "🪫" if battery > 20 else
        "❌" if battery >= 0 else "—"
    )

    return {
        "card_id":     "flipper_zero",
        "title":       "Flipper Zero",
        "subtitle":    "ERR0RS Physical Sensor",
        "icon":        "🐬",
        "connected":   connected,
        "status_text": "Online" if connected else "Offline",
        "status_color":"green" if connected else "gray",
        "ota_status":  ota.get("stage3_firmware", {}).get("status", ""),
        "metrics": [
            {"label": "Battery",
             "value": f"{battery}% {batt_icon}" if battery >= 0 else "—"},
            {"label": "Firmware",
             "value": device.get("firmware", "—")},
            {"label": "Storage free",
             "value": (f"{device.get('storage_free_kb',0)//1024} MB"
                       if device.get("storage_free_kb", -1) >= 0 else "—")},
            {"label": "Port",
             "value": device.get("port", "—")},
        ],
        "quick_actions": [
            {"id": "subghz_433", "label": "Scan 433 MHz",
             "tool": "flipper_subghz_capture",
             "params": {"frequency_mhz": 433.92, "duration_sec": 10}},
            {"id": "subghz_315", "label": "Scan 315 MHz",
             "tool": "flipper_subghz_capture",
             "params": {"frequency_mhz": 315.0, "duration_sec": 10}},
            {"id": "nfc_read", "label": "Read NFC Card",
             "tool": "flipper_nfc_dump", "params": {}},
            {"id": "ir_capture", "label": "Capture IR",
             "tool": "flipper_ir_capture",
             "params": {"duration_sec": 5}},
        ],
        "last_updated": datetime.now().isoformat(),
    }
