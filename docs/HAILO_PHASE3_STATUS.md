# ERR0RS — Phase 3 Hailo NPU Status

**TL;DR:** Phase 3 (LLM teach data generation) is built and tested, but **execution
is BLOCKED on a real Hailo acceleration path**. Don't waste hours running it on
Pi 5 CPU — the math doesn't work. Read this before firing `generate_teach.py`.

---

## What we confirmed on 2026-05-14

Pi 5 + Hailo-10H NPU + Kali ARM64 2026.1 + Ollama 0.20.0.

### The hardware is real and online
- `hailortcli fw-control identify` returns `HAILO10H`, firmware 5.1.1
- `lsmod` shows `hailo1x_pci` loaded
- PCIe device enumerates at `0001:01:00.0`

### Ollama doesn't use the NPU
- Ollama's runner has no Hailo backend in its `llama.cpp`-derived inference loop
- Even with `HAILO_ENABLED=true` in `.env`, the runner shows `size_vram: 0` and
  saturates 2-3 ARM CPU cores at 200-230% during generation
- The Hailo device sits idle while Ollama grinds on CPU

### What that means for Phase 3
On qwen2.5-coder:7b (Q4_K_M, 4.7GB) running on Pi 5 ARM CPU only:

| Metric | Measured value |
|---|---|
| Cold model load | ~2-3 minutes |
| Per-tool generation (~2500 tokens of structured JSON) | **~13+ minutes** (nmap test killed at 13m without finishing) |
| Estimated full-sweep wall time for 49 tools | **8-15 hours** |
| NPU utilization during generation | **0%** |

A full sweep is technically possible as an overnight `nohup` run, but the cost-
benefit isn't there. The same generation completes in **5-10 minutes total** via
Anthropic Claude Haiku 4.5 at a one-time build-time cost of ~$0.25.

---

## What actually unlocks local Phase 3 on the Pi

One of these has to happen first:

### Option A — Ollama gains Hailo backend support
Track Ollama upstream (`ollama/ollama` on GitHub) for Hailo backend issues/PRs.
Hailo would need to publish a `llama.cpp` integration analogous to their existing
ONNX runtime path. As of this writing: **not on Ollama's roadmap.**

### Option B — Use Hailo's own runtime (HailoRT) for inference directly
The proper path. Hailo-10H runs INT8-quantized models compiled with their HEF
toolchain. A 7B model running on Hailo-10H is projected at sub-second per-token
generation — that turns a 12-hour sweep into a coffee break.

Required work:
1. Quantize qwen2.5-coder:7b (or similar) to INT8 via Hailo Dataflow Compiler
2. Compile to .hef format
3. Write a thin Python wrapper that uses `hailo_platform` to run inference
   (NOT Ollama — direct HailoRT API)
4. Implement chat-template + JSON-output formatting in the wrapper
5. Replace `OllamaBackend` in `tools/generate_teach.py` with a `HailoBackend`

This is a 1-3 day project on its own, but unlocks **fast, fully-local, ERR0RS-
worthy generation** for everything Phase 3+ does. Worth doing once and
forever.

### Option C — Run on a bigger Linux machine with a GPU
If a workstation with an NVIDIA GPU exists, qwen 7B finishes a tool in seconds
via Ollama. The teach JSON ships with ERR0RS — it doesn't have to be generated
ON the Pi. The Pi is the deploy target, not necessarily the build target.

### Option D — Anthropic Claude API at build time
Highest quality, cheapest in time, ~$0.25 one-time cost. The output JSON ships
locally with ERR0RS — runtime still fully offline. Document this as the
official build-time generation path.

---

## Decision matrix for future-you

| If you have... | Best path |
|---|---|
| Just the Pi 5 + Hailo NPU, plenty of time, want to ship local | Build Option B (custom HailoBackend) |
| Just the Pi 5 + Hailo NPU, want it done this week | Use Option D (Anthropic), document the build process |
| A GPU workstation available | Option C (Ollama on GPU box) |
| Nothing changed since 2026-05-14 | Don't run Phase 3 generation. Wait. |

---

## What's been verified to work despite this

Everything ERR0RS-Ultimate's runtime DOES work on the Pi 5 with current
hardware:

- ✅ install.sh end-to-end (6/6 smoke test pass)
- ✅ 49-tool registry validated against schema
- ✅ 7 concept entries (CIA, OWASP, MITRE, etc.)
- ✅ Phase 4 Professor Mode already shipped (commit 7a37052)
- ✅ Hailo NPU available for OTHER ERR0RS workloads (RAG embedding, vision-
  based attack analysis, etc.) — just not Ollama-mediated LLM generation

The Phase 3 stub fields (opsec_notes, sample_outputs, legal_notes,
false_positives, mitre_attack) are EMPTY in the v2 registry by design. The
Phase 4 Professor Engine reads the registry gracefully when those fields are
missing — students still get the hand-curated flag-level teach data, just
not the bleeding-edge content layer until Phase 3 generation actually runs.

---

*Last updated: 2026-05-14 by Gary Holden Schneider / Eros*
