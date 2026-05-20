#!/usr/bin/env python3
"""
ERR0RS — LLM Performance Benchmark Suite
═══════════════════════════════════════════════════════════════════

Measures Ollama LLM performance on Pi 5 (and any ARM/x86 host) with the
rigor needed to confidently say "config A is N% faster than config B."

DESIGN PRINCIPLES:
  1. Decomposed timing — prompt-eval and generation are different physics,
     measured separately. TTFT (time-to-first-token) is the UX-critical
     number; everything else is supporting context.
  2. Multi-run with median — single Pi runs are noisy (thermal, scheduler);
     median of 3 runs eliminates ~80% of jitter without burning hours.
  3. State capture — governor, peak temp, throttle, RAM, model resident
     size logged for every run so we can correlate "this run was slow"
     with "the Pi was already warm" or "wrong governor."
  4. Cheap to extend — adding a model, prompt, or option is a dict entry.
  5. Comparable output — JSON results + Markdown summary table per session.

WHAT IT MEASURES (per run):
  - time_to_first_token_s        (UX critical)
  - prompt_eval_tokens_per_sec   (bottleneck metric)
  - generation_tokens_per_sec    (second-order)
  - total_elapsed_s
  - peak_temp_c, peak_throttle
  - response_chars

USAGE:
  # Default: gemma3:1b across 3 prompt sizes, 3 runs each
  python3 tools/llm_benchmark.py

  # Custom matrix
  python3 tools/llm_benchmark.py --models gemma3:1b qwen2.5-coder:7b \\
                                 --prompt-sizes small medium large \\
                                 --runs 3

  # Test ollama options (num_ctx, num_thread, num_batch)
  python3 tools/llm_benchmark.py --options-suite

  # Single-shot debug run
  python3 tools/llm_benchmark.py --model gemma3:1b --size small --runs 1

OUTPUTS:
  docs/BENCHMARKS/<timestamp>/
    results.json         — raw per-run data
    summary.md           — human-readable comparison table
    state_capture.json   — Pi config snapshot at session start
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = ROOT / "docs" / "BENCHMARKS"
THERMAL = Path("/sys/class/thermal/thermal_zone0/temp")
OLLAMA_HOST = "http://127.0.0.1:11434"

# Hard safety cap — same as stress test
KILL_TEMP_C = 80.0
POLL_INTERVAL_S = 2

# ── Prompt sizes ─────────────────────────────────────────────────────────
# We hold the question fixed and vary how much RAG context we prepend.
# This isolates "prompt size" as the variable; the model has to do roughly
# the same generation work regardless of size.

QUESTION = "How do I avoid being caught when running Kerberoasting?"

# Sizes are chosen to represent the three runtime scenarios we care about:
#   small  — chunked RAG (what v3.7 Phase 2 targets)
#   medium — half-card (intermediate)
#   large  — full card (current baseline, what failed for qwen/llama3.2:3b)
PROMPT_SIZES = {
    "small":  ("kerberoasting opsec", 1, 0.30),   # 1 chunk, ~750 tokens
    "medium": ("kerberoasting", 1, 0.60),         # half a card, ~1500 tokens
    "large":  ("kerberoasting", 1, 1.00),         # full card, ~3000 tokens
}


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


def read_cpu_governor() -> str:
    p = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    try:
        return p.read_text().strip()
    except Exception:
        return "unknown"


def read_cpu_freq_mhz() -> int:
    p = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    try:
        return int(p.read_text().strip()) // 1000
    except Exception:
        return 0


def capture_system_state() -> dict:
    """One-shot snapshot of Pi config for the session header."""
    mem = subprocess.run(["free", "-b"], capture_output=True, text=True).stdout
    return {
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "cpu_governor": read_cpu_governor(),
        "cpu_freq_mhz": read_cpu_freq_mhz(),
        "cpu_temp_c": read_temp(),
        "throttle_state": read_throttle(),
        "kernel": subprocess.run(["uname", "-r"], capture_output=True, text=True).stdout.strip(),
        "free_output": mem.splitlines()[1] if mem else "",
    }


class ThermalWatcher(threading.Thread):
    """Background thread polling temp every POLL_INTERVAL_S. Records peak
    temp/throttle across the run; aborts on KILL_TEMP_C. Designed to be
    started before each run and stopped after."""
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_event = threading.Event()
        self.peak_temp = 0.0
        self.peak_throttle = ""
        self.killed = False

    def run(self):
        while not self.stop_event.is_set():
            t = read_temp()
            thr = read_throttle()
            if t > self.peak_temp:
                self.peak_temp = t
            if "0x" in thr and thr != "throttled=0x0":
                self.peak_throttle = thr
            if t >= KILL_TEMP_C:
                self.killed = True
                subprocess.run(["pkill", "-9", "ollama"], capture_output=True)
                self.stop_event.set()
                return
            self.stop_event.wait(POLL_INTERVAL_S)


def get_rag_context(query: str, n_results: int, fraction: float) -> str:
    """Pull RAG context, optionally truncated to a fraction of full size.

    The `fraction` is how we control prompt size without changing the *kind*
    of content — we always pull the same card, just include more or less."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(ROOT / "errors_knowledge_db"))
        coll = client.get_collection("err0rs_teach_v1")
        res = coll.query(query_texts=[query], n_results=n_results)
        docs = res["documents"][0] if res.get("documents") else []
        if not docs:
            return ""
        joined = "\n\n---\n\n".join(docs)
        # Truncate to the requested fraction
        target_len = int(len(joined) * fraction)
        return joined[:target_len]
    except Exception as e:
        print(f"  ! RAG fetch failed: {e}")
        return ""


def build_prompt(question: str, context: str) -> str:
    if not context:
        return f"STUDENT QUESTION: {question}\n\nAnswer:"
    return (
        "You are ERR0RS, a senior red team operator and patient mentor. "
        "Use the reference material below to answer the student's question.\n\n"
        f"=== REFERENCE MATERIAL ===\n{context}\n=== END REFERENCE ===\n\n"
        f"STUDENT QUESTION: {question}\n\nAnswer:"
    )


def run_single(model: str, prompt: str, ollama_opts: dict,
               max_wait_s: int = 600) -> dict:
    """Execute one inference run. Returns timing breakdown + result.

    Why streaming: ollama's /api/generate streams progressively and the
    `done` chunk carries the official timing breakdowns (prompt_eval_count,
    prompt_eval_duration, eval_count, eval_duration) from llama.cpp itself.
    These are more accurate than our wall-clock estimates.

    Wall-clock cap (max_wait_s) is enforced INSIDE the read loop, not via
    urllib's `timeout=` (which is socket-idle timeout, not wall-clock —
    streaming responses send a token every ~150ms so the socket is never
    idle long enough for that timeout to fire). When the cap is hit, we
    close the HTTP response, which ollama detects and aborts inference
    server-side (per github.com/ollama/ollama/issues/2876)."""
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.3,
            "num_predict": 500,
            **ollama_opts,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )

    watcher = ThermalWatcher()
    watcher.start()

    t0 = time.time()
    first_token_t = None
    chunks: list[str] = []
    in_tok = out_tok = 0
    eval_dur_ns = prompt_eval_dur_ns = 0
    aborted = False
    abort_reason = None
    response = None

    # urllib socket-idle timeout: 90s. Catches genuinely dead servers.
    # Our wall-clock cap is enforced separately inside the read loop.
    SOCKET_IDLE_TIMEOUT = 90

    try:
        response = urllib.request.urlopen(req, timeout=SOCKET_IDLE_TIMEOUT)
        for raw in response:
            elapsed = time.time() - t0

            # ── Wall-clock cap (the real timeout) ────────────────────────
            if elapsed > max_wait_s:
                aborted = True
                abort_reason = f"wall_clock_timeout_{max_wait_s}s"
                break

            # ── Thermal kill (safety) ────────────────────────────────────
            if watcher.stop_event.is_set():
                aborted = True
                abort_reason = "thermal_kill"
                break

            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if obj.get("response"):
                if first_token_t is None:
                    first_token_t = elapsed
                chunks.append(obj["response"])
            if obj.get("done"):
                in_tok = obj.get("prompt_eval_count", 0) or 0
                out_tok = obj.get("eval_count", 0) or 0
                eval_dur_ns = obj.get("eval_duration", 0) or 0
                prompt_eval_dur_ns = obj.get("prompt_eval_duration", 0) or 0
                break
    except Exception as e:
        aborted = True
        abort_reason = f"{type(e).__name__}: {e}"
    finally:
        # CRITICAL: close the response so ollama detects the closed socket
        # and stops generating server-side. Without this, ollama keeps
        # inferring after we've already given up — wasting Pi CPU and
        # confusing thermal measurements for the next run.
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        # Stop the thermal watcher
        watcher.stop_event.set()
        watcher.join(timeout=2)

    elapsed = time.time() - t0

    # Ollama's internal timings (nanoseconds) — authoritative when present
    prompt_eval_s = prompt_eval_dur_ns / 1e9 if prompt_eval_dur_ns else None
    gen_s = eval_dur_ns / 1e9 if eval_dur_ns else None

    return {
        "model": model,
        "prompt_chars": len(prompt),
        "options": ollama_opts,
        "aborted": aborted,
        "abort_reason": abort_reason,
        "time_to_first_token_s": first_token_t,
        "total_elapsed_s": elapsed,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "prompt_eval_s": prompt_eval_s,
        "generation_s": gen_s,
        "prompt_eval_tok_per_s": (in_tok / prompt_eval_s) if prompt_eval_s else None,
        "generation_tok_per_s": (out_tok / gen_s) if gen_s else None,
        "response_chars": len("".join(chunks)),
        "peak_temp_c": watcher.peak_temp,
        "peak_throttle": watcher.peak_throttle or "none",
        "thermal_killed": watcher.killed,
        "temp_at_start_c": read_temp(),
    }


def aggregate_runs(runs: list[dict]) -> dict:
    """Summarize N runs of the same config. Median + min/max so we see
    variance without being fooled by single outlier runs."""
    successful = [r for r in runs if not r["aborted"] and r["time_to_first_token_s"]]
    if not successful:
        return {"runs": len(runs), "all_failed": True}

    def med(key):
        vals = [r[key] for r in successful if r.get(key) is not None]
        return statistics.median(vals) if vals else None

    def mn(key):
        vals = [r[key] for r in successful if r.get(key) is not None]
        return min(vals) if vals else None

    def mx(key):
        vals = [r[key] for r in successful if r.get(key) is not None]
        return max(vals) if vals else None

    peak_temps = [r["peak_temp_c"] for r in runs]
    return {
        "runs_completed": len(successful),
        "runs_attempted": len(runs),
        "ttft_median_s": med("time_to_first_token_s"),
        "ttft_min_s": mn("time_to_first_token_s"),
        "ttft_max_s": mx("time_to_first_token_s"),
        "prompt_eval_tok_per_s_median": med("prompt_eval_tok_per_s"),
        "generation_tok_per_s_median": med("generation_tok_per_s"),
        "total_elapsed_median_s": med("total_elapsed_s"),
        "peak_temp_observed_c": max(peak_temps) if peak_temps else 0,
    }


def matrix_row_label(config: dict) -> str:
    parts = [config["model"], config["size"]]
    opts = config.get("options", {})
    if opts:
        # E.g. ctx=2048,thr=4
        kv = ",".join(f"{k.replace('num_', '')}={v}" for k, v in sorted(opts.items()))
        parts.append(f"[{kv}]")
    return " ".join(parts)


def render_summary_md(state: dict, matrix: list[dict]) -> str:
    """Generate a human-readable Markdown summary."""
    lines = []
    lines.append("# LLM Benchmark Results\n")
    lines.append(f"**Date:** {state['timestamp']}")
    lines.append(f"**CPU governor:** `{state['cpu_governor']}` @ {state['cpu_freq_mhz']} MHz")
    lines.append(f"**Baseline temp:** {state['cpu_temp_c']:.1f}°C")
    lines.append(f"**Throttle state:** `{state['throttle_state']}`")
    lines.append(f"**Kernel:** {state['kernel']}\n")

    lines.append("## Results matrix\n")
    lines.append("| Config | Runs | TTFT (med) | Prompt eval | Generation | Total | Peak temp |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in matrix:
        cfg_label = matrix_row_label(row["config"])
        agg = row["aggregate"]
        if agg.get("all_failed"):
            lines.append(f"| {cfg_label} | {agg['runs']} | ❌ all failed | — | — | — | — |")
            continue
        ttft = agg.get("ttft_median_s")
        peval = agg.get("prompt_eval_tok_per_s_median")
        gen = agg.get("generation_tok_per_s_median")
        total = agg.get("total_elapsed_median_s")
        peak = agg.get("peak_temp_observed_c", 0)
        lines.append(
            f"| {cfg_label} | "
            f"{agg.get('runs_completed', 0)}/{agg.get('runs_attempted', 0)} | "
            f"{ttft:.1f}s | "
            f"{peval:.1f} tok/s | "
            f"{gen:.1f} tok/s | "
            f"{total:.1f}s | "
            f"{peak:.1f}°C |"
        )

    lines.append("\n## Notes\n")
    lines.append("- TTFT = time-to-first-token (UX-critical; what the user feels as 'wait')")
    lines.append("- Prompt eval tok/s = how fast the model chews input. Dominant cost on Pi 5.")
    lines.append("- Generation tok/s = how fast the model emits output. Steady-state speed.")
    lines.append("- Median of N runs is reported. Min/max are in `results.json`.\n")
    return "\n".join(lines)


# ── Built-in configurations ───────────────────────────────────────────────

def build_matrix(args) -> list[dict]:
    """Construct the list of (model, size, options) tuples to run."""
    matrix = []
    if args.options_suite:
        # Sweep ollama options at fixed model + medium prompt
        for ctx in (2048, 4096, 8192):
            for batch in (256, 512):
                matrix.append({
                    "model": args.models[0],
                    "size": "medium",
                    "options": {"num_ctx": ctx, "num_batch": batch},
                })
    else:
        for model in args.models:
            for size in args.prompt_sizes:
                matrix.append({"model": model, "size": size, "options": {}})
    return matrix


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--models", nargs="+", default=["gemma3:1b"])
    p.add_argument("--prompt-sizes", nargs="+", default=["small", "medium", "large"],
                   choices=list(PROMPT_SIZES))
    p.add_argument("--runs", type=int, default=3, help="Runs per config (median reported)")
    p.add_argument("--options-suite", action="store_true",
                   help="Sweep num_ctx/num_batch options on first model")
    p.add_argument("--warmup", action="store_true",
                   help="Run a discarded warmup before measurement")
    p.add_argument("--label", default="", help="Tag this session (e.g. 'governor-perf')")
    args = p.parse_args()

    ts = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    label = f"_{args.label}" if args.label else ""
    session_dir = RESULTS_ROOT / f"{ts}{label}"
    session_dir.mkdir(parents=True, exist_ok=True)

    state = capture_system_state()
    (session_dir / "state_capture.json").write_text(json.dumps(state, indent=2))

    print(f"╔{'═'*70}╗")
    print(f"║ LLM BENCHMARK — {ts}{label}{' '*(53-len(ts)-len(label))}║")
    print(f"╚{'═'*70}╝")
    print(f"  governor:  {state['cpu_governor']} @ {state['cpu_freq_mhz']} MHz")
    print(f"  baseline:  {state['cpu_temp_c']:.1f}°C   {state['throttle_state']}")
    print(f"  output:    {session_dir.relative_to(ROOT)}")

    matrix = build_matrix(args)
    print(f"\n  matrix:    {len(matrix)} configs × {args.runs} runs = {len(matrix)*args.runs} total inferences")
    print()

    if args.warmup:
        print("  → warmup (discarded)... ", end="", flush=True)
        wquery, wn, wfrac = PROMPT_SIZES["small"]
        wctx = get_rag_context(wquery, wn, wfrac)
        wprompt = build_prompt(QUESTION, wctx)
        _ = run_single(args.models[0], wprompt, {})
        print("done")
        print()

    results_matrix = []
    for i, cfg in enumerate(matrix, 1):
        query, n, frac = PROMPT_SIZES[cfg["size"]]
        ctx = get_rag_context(query, n, frac)
        prompt = build_prompt(QUESTION, ctx)
        print(f"  [{i}/{len(matrix)}] {matrix_row_label(cfg)}")
        print(f"        prompt: {len(prompt):,} chars")

        runs = []
        for r in range(1, args.runs + 1):
            print(f"        run {r}/{args.runs} ... ", end="", flush=True)
            res = run_single(cfg["model"], prompt, cfg["options"])
            runs.append(res)
            if res["aborted"]:
                print(f"ABORTED ({res['abort_reason']})  peak={res['peak_temp_c']:.1f}°C")
            else:
                ttft = res["time_to_first_token_s"] or 0
                print(f"TTFT={ttft:.1f}s  total={res['total_elapsed_s']:.1f}s  peak={res['peak_temp_c']:.1f}°C")
            # Cooldown between runs. 30s because ollama doesn't release
            # CPU instantly when we close the socket — runner takes 30-60s
            # to fully wind down (tested 2026-05-20). Short cooldowns pollute
            # the next run with leftover load.
            print(f"        cooldown 30s...")
            time.sleep(30)

        agg = aggregate_runs(runs)
        results_matrix.append({"config": cfg, "runs": runs, "aggregate": agg})
        if not agg.get("all_failed"):
            print(f"        median TTFT: {agg['ttft_median_s']:.1f}s   "
                  f"prompt-eval: {agg['prompt_eval_tok_per_s_median']:.1f} tok/s   "
                  f"gen: {agg['generation_tok_per_s_median']:.1f} tok/s")
        print()

    # Persist results
    (session_dir / "results.json").write_text(json.dumps({
        "state": state,
        "matrix": results_matrix,
    }, indent=2))
    summary = render_summary_md(state, results_matrix)
    (session_dir / "summary.md").write_text(summary)

    print(f"╔{'═'*70}╗")
    print(f"║ SESSION COMPLETE                                                     ║")
    print(f"╚{'═'*70}╝")
    print(f"  results:  {session_dir.relative_to(ROOT)}/results.json")
    print(f"  summary:  {session_dir.relative_to(ROOT)}/summary.md")
    print()
    print(summary.split("## Results matrix")[1])


if __name__ == "__main__":
    main()
