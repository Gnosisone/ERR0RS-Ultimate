#!/usr/bin/env python3
"""
ERR0RS — BadUSB/Flipper API bridge
Adds /api/badusb endpoint to the launcher
"""

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.tools.badusb.flipper_engine import handle_request, FlipperScriptEngine
    BADUSB_AVAILABLE = True
except Exception as e:
    BADUSB_AVAILABLE = False
    _BADUSB_ERR = str(e)


def route_badusb(payload: dict) -> dict:
    """Route /api/badusb requests"""
    if not BADUSB_AVAILABLE:
        return {"status": "error", "error": f"BadUSB engine not loaded: {_BADUSB_ERR}"}
    return handle_request(payload)


def nlp_to_flipper(prompt: str) -> dict:
    """
    Called from route_command() when badusb intent detected.
    Wraps generate() in a clean response.
    """
    if not BADUSB_AVAILABLE:
        return {"stdout": "BadUSB engine not available", "status": "error"}
    engine = FlipperScriptEngine()
    result = engine.generate(prompt)
    if result.get("status") in ("generated", "kb_match"):
        script = result.get("script", "")
        fname  = result.get("sd_filename", "ERRZ_script.txt")
        out_dir = ROOT_DIR / "output" / "flipper_sd" / "badusb"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / fname
        out_path.write_text(script, encoding="utf-8")
        return {
            "stdout": (
                f"[ERR0RS] Script generated: {result.get('description','')}\n"
                f"[ERR0RS] Saved to: {out_path}\n"
                f"[ERR0RS] Drop on Flipper SD card → /badusb/{fname}\n\n"
                f"{script}"
            ),
            "status":    "success",
            "sd_path":   str(out_path),
            "sd_filename": fname,
            "script":    script,
        }
    return {"stdout": result.get("error", "Generation failed"), "status": "error"}
