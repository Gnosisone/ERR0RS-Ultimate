"""
mr7_agent.py — DEPRECATED

ERR0RS no longer uses mr7.ai.
All functionality has been replaced by the native ERR0RS Brain (errz_brain.py)
which runs 100% locally via Ollama — zero cloud dependency, zero API keys needed.

The 5 mr7 "models" map to ERR0RS Brain modes:
  KaliGPT Fast      → brain mode: kali
  KaliGPT Thinking  → brain mode: red_team
  0Day Coder        → brain mode: vuln_hunter
  DarkGPT           → brain mode: threat_intel
  OnionGPT          → brain mode: opsec

Use: /api/brain instead of /api/mr7
"""
from src.ai.errz_brain import handle_brain_request, ask, BRAIN_MODES

# Backwards-compatible shim so nothing breaks if anyone calls handle_mr7_request
def handle_mr7_request(payload: dict) -> dict:
    action = payload.get("action", "ask")
    model_map = {
        "kali_fast":  "kali",
        "kali_think": "red_team",
        "day0_coder": "vuln_hunter",
        "darkgpt":    "threat_intel",
        "oniongpt":   "opsec",
    }
    if action in ("ask", "models", "status"):
        mode = model_map.get(payload.get("model", "kali_fast"), "kali")
        return handle_brain_request({**payload, "action": action, "mode": mode})
    return handle_brain_request(payload)
