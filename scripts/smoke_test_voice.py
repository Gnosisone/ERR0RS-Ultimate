#!/usr/bin/env python3
"""
ERR0RS voice + RAG smoke test (manual — NOT a pytest test).

Builds a system prompt via the conversation engine, confirms the RAG block is
injected, then hits a locally-running Ollama (err0rs-gemma) and reports the
answer plus generation timing / tok-s.

Requires `ollama serve` running with the err0rs-gemma model available. Lives in
scripts/ (not test_*) and is __main__-guarded so pytest never collects or
executes it on import.

Usage:
    venv/bin/python3 scripts/smoke_test_voice.py
    venv/bin/python3 scripts/smoke_test_voice.py "how does kerberoasting work"
"""
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "err0rs-gemma:latest"
DEFAULT_Q = "How does Kerberoasting work, and why is it considered offline cracking?"


def main() -> int:
    from src.core.conversation_engine import get_engine

    q = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_Q
    eng = get_engine()
    sysprompt = eng.build_system_prompt(None, user_msg=q)

    has_rag = ("RAG" in sysprompt) or ("Ethical Operator" in sysprompt)
    print("=== RAG injected into prompt? ===", has_rag, flush=True)
    idx = sysprompt.find("RAG")
    if idx >= 0:
        print("--- RAG block snippet ---", flush=True)
        print(sysprompt[max(0, idx - 30):idx + 420], flush=True)
    print("=" * 64, flush=True)

    t0 = time.time()
    try:
        r = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": sysprompt},
                {"role": "user", "content": q},
            ],
            "stream": False, "keep_alive": -1,
            "options": {"temperature": 0.7, "num_predict": 400, "num_ctx": 4096},
        }, timeout=600)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"[error] Ollama request failed: {e}", flush=True)
        print("Is `ollama serve` running with err0rs-gemma pulled?", flush=True)
        return 1

    dt = time.time() - t0
    d = r.json()
    ans = d.get("message", {}).get("content", "")
    ev = d.get("eval_count", 0)
    ed = (d.get("eval_duration", 1) or 1) / 1e9
    print(ans, flush=True)
    print("=" * 64, flush=True)
    print(f"[timing] {dt:.0f}s wall | {ev} gen tokens | {(ev / ed if ed else 0):.1f} tok/s", flush=True)
    print("[done]", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
