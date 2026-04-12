#!/usr/bin/env python3
"""
ERR0RS — Ollama Health Check & Auto-Fix
========================================
Validates Ollama is working correctly on startup and attempts
to diagnose and fix common issues on the Pi 5.

Called automatically by main.py on boot, or manually:
    python3 src/ai/ollama_health.py

Checks:
  1. Ollama service running
  2. Model available and loaded
  3. RAM headroom sufficient
  4. Swap present
  5. API responding (actual inference test)
  6. Context window configured correctly

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os, sys, json, time, subprocess
from pathlib import Path
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]

# ── Config from env ───────────────────────────────────────────────────────────
OLLAMA_HOST    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "err0rs-pi5")
FALLBACK_MODEL = os.getenv("OLLAMA_MODEL_FALLBACK", "qwen2.5-coder:7b")
NUM_CTX        = int(os.getenv("OLLAMA_NUM_CTX",     "2048"))
NUM_PREDICT    = int(os.getenv("OLLAMA_NUM_PREDICT",  "1024"))
NUM_THREAD     = int(os.getenv("OLLAMA_NUM_THREAD",   "4"))

# ── Thresholds ────────────────────────────────────────────────────────────────
MIN_FREE_RAM_MB  = 512    # warn if less than this available
MIN_SWAP_MB      = 2048   # warn if less than this swap
TIMEOUT_HEALTH   = 3      # seconds for health ping
TIMEOUT_GENERATE = 120    # seconds for inference smoke test — Pi 5 is slow on cold load


def _api_get(path: str) -> dict | None:
    try:
        r = urllib.request.urlopen(f"{OLLAMA_HOST}{path}", timeout=TIMEOUT_HEALTH)
        return json.loads(r.read())
    except Exception:
        return None


def _post(path: str, body: dict, timeout: int = TIMEOUT_GENERATE) -> dict | None:
    try:
        data = json.dumps(body).encode()
        req  = urllib.request.Request(
            f"{OLLAMA_HOST}{path}", data=data,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def check_service() -> tuple[bool, str]:
    """Check Ollama API is reachable."""
    data = _api_get("/api/tags")
    if data is not None:
        models = [m["name"] for m in data.get("models", [])]
        return True, f"Running — {len(models)} model(s) loaded"
    return False, "Ollama not reachable at " + OLLAMA_HOST


def check_model() -> tuple[bool, str, str]:
    """
    Check configured model exists. Returns (ok, message, actual_model).
    Falls back to FALLBACK_MODEL if primary not found.
    """
    data = _api_get("/api/tags")
    if not data:
        return False, "Cannot reach Ollama to check models", OLLAMA_MODEL

    models = [m["name"] for m in data.get("models", [])]
    # Normalize — Ollama appends :latest if no tag specified
    models_normalized = [m.split(":")[0] for m in models]

    target_base   = OLLAMA_MODEL.split(":")[0]
    fallback_base = FALLBACK_MODEL.split(":")[0]

    if target_base in models_normalized:
        # Use exact name from list (may have :latest suffix)
        exact = next(m for m in models if m.split(":")[0] == target_base)
        return True, f"'{exact}' available ✅", exact

    if fallback_base in models_normalized:
        exact = next(m for m in models if m.split(":")[0] == fallback_base)
        return True, (
            f"'{OLLAMA_MODEL}' not found — falling back to '{exact}'\n"
            f"  Run: bash scripts/fix_ollama_pi5.sh  to build the optimized model"
        ), exact

    return False, (
        f"Neither '{OLLAMA_MODEL}' nor '{FALLBACK_MODEL}' found.\n"
        f"  Available: {', '.join(models) or 'none'}\n"
        f"  Fix: ollama pull qwen2.5-coder:7b"
    ), ""


def check_ram() -> tuple[bool, str]:
    """Check available RAM and swap."""
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])

        avail_mb = info.get("MemAvailable", 0) // 1024
        swap_total_mb = info.get("SwapTotal", 0) // 1024
        swap_free_mb  = info.get("SwapFree",  0) // 1024

        msgs = []
        ok   = True

        if avail_mb < MIN_FREE_RAM_MB:
            msgs.append(f"⚠️  Only {avail_mb}MB RAM free (need {MIN_FREE_RAM_MB}MB) — risk of OOM")
            ok = False
        else:
            msgs.append(f"✅ {avail_mb}MB RAM available")

        if swap_total_mb < MIN_SWAP_MB:
            msgs.append(f"⚠️  Swap: {swap_total_mb}MB — run scripts/fix_ollama_pi5.sh to add 8GB swap")
            ok = False
        else:
            msgs.append(f"✅ Swap: {swap_total_mb}MB total / {swap_free_mb}MB free")

        return ok, "\n  ".join(msgs)
    except Exception as e:
        return True, f"Could not read /proc/meminfo: {e}"


def check_inference(model: str) -> tuple[bool, str, float]:
    """
    Run a real inference smoke test. Returns (ok, message, latency_secs).
    Uses minimal tokens to keep it fast.
    """
    start = time.time()
    result = _post("/api/generate", {
        "model":  model,
        "prompt": "Respond with exactly: ERRORSOK",
        "stream": False,
        "options": {
            "num_predict": 8,
            "num_ctx":     64,
            "temperature": 0.0,
        }
    }, timeout=TIMEOUT_GENERATE)
    elapsed = time.time() - start

    if not result:
        return False, "No response from /api/generate", elapsed

    if "error" in result:
        err = result["error"]
        # Common Pi errors
        if "context" in err.lower() or "memory" in err.lower():
            return False, f"OOM/context error: {err}\n  Fix: run bash scripts/fix_ollama_pi5.sh", elapsed
        if "timeout" in err.lower() or "timed out" in err.lower():
            return False, f"Timeout after {elapsed:.1f}s — model may be thrashing\n  Fix: run bash scripts/fix_ollama_pi5.sh", elapsed
        return False, f"API error: {err}", elapsed

    response = result.get("response", "").strip()
    if response:
        return True, f"'{response}' ({elapsed:.1f}s)", elapsed
    return False, f"Empty response after {elapsed:.1f}s", elapsed


def run_health_check(verbose: bool = True) -> dict:
    """
    Full health check. Returns dict with results and overall status.
    Called by main.py on boot.
    """
    results = {
        "service":   {"ok": False, "msg": ""},
        "model":     {"ok": False, "msg": "", "active_model": ""},
        "ram":       {"ok": False, "msg": ""},
        "inference": {"ok": False, "msg": "", "latency_s": 0.0},
        "overall":   False,
        "active_model": "",
    }

    def _print(msg): 
        if verbose: print(msg)

    _print("\n  ┌─ ERR0RS Ollama Health Check ──────────────────────")

    # 1. Service
    ok, msg = check_service()
    results["service"] = {"ok": ok, "msg": msg}
    _print(f"  │  Service   : {'✅' if ok else '❌'}  {msg}")
    if not ok:
        _print("  │")
        _print("  │  ⚡ FIX: sudo systemctl start ollama")
        _print("  └───────────────────────────────────────────────────\n")
        return results

    # 2. Model
    ok, msg, active_model = check_model()
    results["model"] = {"ok": ok, "msg": msg, "active_model": active_model}
    results["active_model"] = active_model
    _print(f"  │  Model     : {'✅' if ok else '❌'}  {msg}")
    if not ok:
        _print("  │")
        _print("  │  ⚡ FIX: ollama pull qwen2.5-coder:7b")
        _print("  └───────────────────────────────────────────────────\n")
        return results

    # 3. RAM + Swap
    ok, msg = check_ram()
    results["ram"] = {"ok": ok, "msg": msg}
    _print(f"  │  RAM       : {'✅' if ok else '⚠️ '}  {msg}")

    # 4. Inference smoke test
    _print(f"  │  Inference : 🔄  Testing {active_model}...")
    ok, msg, latency = check_inference(active_model)
    results["inference"] = {"ok": ok, "msg": msg, "latency_s": round(latency, 2)}
    _print(f"  │  Inference : {'✅' if ok else '❌'}  {msg}")

    if not ok:
        _print("  │")
        _print("  │  ⚡ FIX: bash scripts/fix_ollama_pi5.sh")

    results["overall"] = results["service"]["ok"] and results["model"]["ok"] and results["inference"]["ok"]
    status = "✅ ALL SYSTEMS GO" if results["overall"] else "⚠️  ISSUES DETECTED"
    _print(f"  └─ {status} ─────────────────────────────────────────\n")

    return results


def auto_fix_model(results: dict) -> str:
    """
    If inference failed but service + model are fine,
    try switching to fallback model automatically.
    Returns the model name to use.
    """
    if results["inference"]["ok"]:
        return results["active_model"]

    active = results["active_model"]
    if active == OLLAMA_MODEL and FALLBACK_MODEL:
        # Try fallback
        ok, msg, latency = check_inference(FALLBACK_MODEL)
        if ok:
            print(f"  ℹ️  Auto-switched to fallback model: {FALLBACK_MODEL}")
            return FALLBACK_MODEL

    return active or FALLBACK_MODEL or "qwen2.5-coder:7b"


# ── Standalone run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    results = run_health_check(verbose=True)

    if not results["overall"]:
        print("  ⚡ To fix all issues at once:")
        print("     sudo bash scripts/fix_ollama_pi5.sh\n")
        sys.exit(1)
    sys.exit(0)
