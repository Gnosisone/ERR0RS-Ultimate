#!/usr/bin/env python3
"""
ERR0RS — err0rs-qwen + RAG stress test
═══════════════════════════════════════════════════════════════════

Tests whether the Pi 5 can sustain a real RAG-augmented inference round
against err0rs-qwen (qwen2.5-coder:7b + baked-in ERR0RS soul) without
thermal throttling or hard timeout.

Safety:
  - Background thermal watcher polls /sys/class/thermal every 5s
  - KILL_TEMP_C = 80.0 — if hit, ollama process is terminated immediately
  - WALL_CLOCK_TIMEOUT = 300s (5 min) hard cap regardless of progress
  - All output buffered to log file so a hung run can be inspected after

Test progression (configurable via --level):
  1. small  — 1 RAG card (~12k chars) + short question
  2. medium — 2 RAG cards + medium question (default)
  3. large  — 3 RAG cards + multi-part question (the failure case)

Outputs to docs/STRESS_TESTS/qwen_rag_{timestamp}.log
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "docs" / "STRESS_TESTS"
LOG_DIR.mkdir(parents=True, exist_ok=True)

THERMAL = Path("/sys/class/thermal/thermal_zone0/temp")
KILL_TEMP_C = 80.0       # hard kill — last session hit 85.9°C, stop 5° below that
WARN_TEMP_C = 72.0
WALL_CLOCK_TIMEOUT = 300  # 5 min absolute cap
POLL_INTERVAL_S = 5
OLLAMA_HOST = "http://127.0.0.1:11434"


def read_temp() -> float:
    try:
        return int(THERMAL.read_text().strip()) / 1000.0
    except Exception:
        return 0.0


def read_throttle() -> str:
    try:
        r = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2)
        return r.stdout.strip()
    except Exception:
        return "throttled=unknown"


class ThermalWatcher(threading.Thread):
    """Background thread — polls temp every POLL_INTERVAL_S, kills ollama if KILL_TEMP_C hit."""
    def __init__(self, log_fh):
        super().__init__(daemon=True)
        self.log_fh = log_fh
        self.stop_event = threading.Event()
        self.killed = False
        self.peak_temp = 0.0
        self.peak_throttle = ""
        self.samples: list[tuple[float, float, str]] = []  # (t, temp, throttle)

    def run(self):
        t0 = time.time()
        while not self.stop_event.is_set():
            t = time.time() - t0
            temp = read_temp()
            throttle = read_throttle()
            self.samples.append((t, temp, throttle))
            if temp > self.peak_temp:
                self.peak_temp = temp
            if "0x" in throttle and throttle != "throttled=0x0":
                self.peak_throttle = throttle
            self.log_fh.write(f"[+{t:6.1f}s] temp={temp:5.1f}°C  {throttle}\n")
            self.log_fh.flush()
            if temp >= KILL_TEMP_C:
                self.killed = True
                self.log_fh.write(f"\n!! KILL_TEMP_C ({KILL_TEMP_C}°C) reached at {temp:.1f}°C — killing ollama\n")
                self.log_fh.flush()
                subprocess.run(["pkill", "-9", "ollama"], capture_output=True)
                self.stop_event.set()
                return
            self.stop_event.wait(POLL_INTERVAL_S)


def query_rag(query: str, n_results: int) -> list[str]:
    """Use the existing ingest script's query API to fetch top-N teach cards."""
    import chromadb
    client = chromadb.PersistentClient(path=str(ROOT / "errors_knowledge_db"))
    coll = client.get_collection("err0rs_teach_v1")
    res = coll.query(query_texts=[query], n_results=n_results)
    docs = res["documents"][0] if res.get("documents") else []
    return docs


def build_prompt(question: str, contexts: list[str]) -> str:
    """Compose the RAG-augmented prompt the way the runtime would."""
    ctx_blob = "\n\n---\n\n".join(contexts)
    return (
        "You are ERR0RS, a senior red team operator and patient mentor. "
        "A student has asked the following question. Use the reference "
        "material below to ground your answer. Be concrete, cite specific "
        "techniques, and keep your voice consistent with the ERR0RS soul.\n\n"
        f"=== REFERENCE MATERIAL ===\n{ctx_blob}\n=== END REFERENCE ===\n\n"
        f"STUDENT QUESTION: {question}\n\n"
        "Answer:"
    )


def stream_ollama(prompt: str, log_fh, watcher: ThermalWatcher, model: str) -> dict:
    """Stream from ollama, log every chunk, return final stats."""
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.4,
            "num_predict": 1500,
            "num_ctx": 8192,
        },
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    chunks: list[str] = []
    in_tok = out_tok = 0
    first_token_t = None
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=WALL_CLOCK_TIMEOUT) as r:
            for raw in r:
                if watcher.stop_event.is_set():
                    log_fh.write("\n!! watcher signaled stop — aborting stream\n")
                    return {"aborted": True, "reason": "thermal_kill"}
                if not raw.strip():
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if obj.get("response"):
                    if first_token_t is None:
                        first_token_t = time.time() - t0
                        log_fh.write(f"\n[FIRST TOKEN at +{first_token_t:.1f}s]\n")
                    chunks.append(obj["response"])
                    log_fh.write(obj["response"])
                    log_fh.flush()
                if obj.get("done"):
                    in_tok = obj.get("prompt_eval_count", 0) or 0
                    out_tok = obj.get("eval_count", 0) or 0
                    eval_dur = (obj.get("eval_duration", 0) or 0) / 1e9
                    prompt_dur = (obj.get("prompt_eval_duration", 0) or 0) / 1e9
                    return {
                        "aborted": False,
                        "elapsed_s": time.time() - t0,
                        "first_token_s": first_token_t,
                        "in_tok": in_tok,
                        "out_tok": out_tok,
                        "eval_duration_s": eval_dur,
                        "prompt_eval_duration_s": prompt_dur,
                        "tokens_per_sec": (out_tok / eval_dur) if eval_dur > 0 else 0,
                        "response_chars": len("".join(chunks)),
                    }
    except Exception as e:
        return {"aborted": True, "reason": f"exception: {e}", "elapsed_s": time.time() - t0}
    return {"aborted": True, "reason": "stream ended without done", "elapsed_s": time.time() - t0}


LEVELS = {
    "small":  ("How do I avoid being caught when running Kerberoasting?",
               "kerberoasting active directory ticket extraction", 1),
    "medium": ("Walk me through enumerating SMB on a Windows target and what each step risks detecting me.",
               "SMB enumeration Windows", 2),
    "large":  ("I am on an internal Active Directory engagement. Walk me through the full kill chain from initial access through domain dominance, with opsec tradeoffs at each step.",
               "active directory kill chain credential extraction lateral movement", 3),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--level", choices=list(LEVELS), default="medium")
    p.add_argument("--model", default="err0rs-qwen",
                   help="ollama model name (e.g. err0rs-qwen, llama3.2:3b)")
    args = p.parse_args()

    ts = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    # Sanitize model name for filename
    model_tag = args.model.replace(":", "_").replace("/", "_")
    log_path = LOG_DIR / f"{model_tag}_rag_{args.level}_{ts}.log"
    log_fh = open(log_path, "w")

    question, query, n_results = LEVELS[args.level]
    log_fh.write(f"=== ERR0RS local-model+RAG stress test ===\n")
    log_fh.write(f"model:  {args.model}\n")
    log_fh.write(f"level:  {args.level}\n")
    log_fh.write(f"timestamp: {ts}\n")
    log_fh.write(f"baseline temp: {read_temp():.1f}°C  {read_throttle()}\n")
    log_fh.write(f"RAG query: {query!r}  (n_results={n_results})\n")
    log_fh.write(f"question: {question}\n\n")

    contexts = query_rag(query, n_results)
    log_fh.write(f"retrieved {len(contexts)} cards, total {sum(len(c) for c in contexts)} chars\n\n")
    prompt = build_prompt(question, contexts)
    log_fh.write(f"prompt size: {len(prompt)} chars\n")
    log_fh.write("─" * 70 + "\n")

    watcher = ThermalWatcher(log_fh)
    watcher.start()

    log_fh.write(f"STARTING INFERENCE on {args.model}...\n")
    log_fh.write("─" * 70 + "\n")
    result = stream_ollama(prompt, log_fh, watcher, args.model)

    watcher.stop_event.set()
    watcher.join(timeout=2)

    log_fh.write("\n" + "─" * 70 + "\n")
    log_fh.write("=== RESULTS ===\n")
    log_fh.write(json.dumps(result, indent=2) + "\n")
    log_fh.write(f"peak temp:    {watcher.peak_temp:.1f}°C\n")
    log_fh.write(f"peak throttle: {watcher.peak_throttle or 'none'}\n")
    log_fh.write(f"final temp:   {read_temp():.1f}°C\n")
    log_fh.close()

    # ── stdout summary ──
    print(f"\n=== stress test complete — log: {log_path.name} ===")
    print(f"  level:        {args.level}")
    print(f"  prompt size:  {len(prompt):,} chars")
    if result.get("aborted"):
        print(f"  RESULT:       ABORTED ({result.get('reason')})")
    else:
        print(f"  RESULT:       OK")
        print(f"  elapsed:      {result.get('elapsed_s', 0):.1f}s")
        print(f"  first token:  {result.get('first_token_s', 0):.1f}s")
        print(f"  tokens:       {result.get('in_tok', 0)} in / {result.get('out_tok', 0)} out")
        print(f"  speed:        {result.get('tokens_per_sec', 0):.1f} tok/s")
        print(f"  response:     {result.get('response_chars', 0):,} chars")
    print(f"  peak temp:    {watcher.peak_temp:.1f}°C")
    print(f"  peak throttle:{watcher.peak_throttle or ' none'}")
    print(f"  thermal kill: {'YES' if watcher.killed else 'no'}")


if __name__ == "__main__":
    main()
