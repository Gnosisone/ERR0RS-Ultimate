# ERR0RS Backend Strategy

> Why ERR0RS uses Claude as primary, DeepSeek as secondary, and Ollama as
> tertiary — and why this is a philosophical choice, not just a technical one.

---

## The fallback chain

```
PRIMARY:    Claude (Anthropic API)
            ↓ if unavailable or user prefers
SECONDARY:  DeepSeek API
            ↓ if no internet / fully offline mode
TERTIARY:   Local Ollama
            ↓ absolute last resort
FALLBACK:   Hand-curated registry data only (no LLM)
```

This is configured via `LLM_FALLBACK_CHAIN` in `.env` — default is
`claude,deepseek,ollama`. Set `LLM_BACKEND` to force a specific one.

## Why this order

### Claude (Anthropic) — primary

ERR0RS's mission is **pedagogy first** — teach a complete beginner to
become a purple-team master. That mission has specific requirements
that Claude is unusually well-matched to:

- **Calibration on offensive security.** Many models reflexively refuse
  half of any pentesting question. Claude engages with authorized
  security education seriously, without theater. That fit matters
  for a platform whose entire purpose is teaching offensive technique.
- **Careful, honest, structured output.** Claude tends to flag
  uncertainty rather than fabricate. ERR0RS's worst failure mode is a
  confidently hallucinated MITRE ID, fake CVE number, or wrong Sysmon
  event ID — exactly the kind of thing small-model generation produces.
  Claude avoids this much more reliably.
- **Voice and approach match the project.** This entire project was
  built in conversation with Claude. ERR0RS's character — the
  honest-and-patient-teacher voice in `src/ai/system_prompt.md` — is
  shaped by that collaboration. Using Claude as the backend means
  every ERR0RS interaction speaks with the consistent voice the
  project was designed around.

**Cost:** ~$0.25 for a full 49-tool Phase 3 generation with
Claude Haiku 4.5; ~$2-3 with Claude Sonnet 4.6. One-time at build
time. The generated JSON ships with the repo — runtime stays offline.

### DeepSeek — secondary

DeepSeek earns its position for two specific reasons that serve ERR0RS's
mission:

- **Cost accessibility.** DeepSeek's API is 5-10× cheaper than Claude.
  For students who want to regenerate teach data with their own keys,
  or for ERR0RS deployments in cost-constrained environments, DeepSeek
  lowers the barrier dramatically. Mission-critical for a project whose
  whole point is making security education accessible.
- **Open weights → future local path.** DeepSeek publishes model weights.
  That means DeepSeek's V3 or Coder models could one day be compiled to
  run on the Pi 5 + Hailo NPU directly (see `docs/HAILO_PHASE3_STATUS.md`
  Option B). Claude's weights are closed — there will never be a "Claude
  on Hailo." DeepSeek is the bridge to truly local, truly fast inference
  on cyberdeck hardware.

**Cost:** ~$0.03-0.05 for a full sweep with deepseek-chat.

### Ollama — tertiary

Ollama matters for one scenario the cloud APIs can't serve:

- **True offline operation.** Engagements where the cyberdeck is on an
  airgapped network, in a SCIF, or behind a client's strict no-cloud
  policy. Local Ollama with even a 7B model is better than nothing.

**Honest caveats** (verified 2026-05-14 on Pi 5):
- Ollama does NOT use the Hailo NPU. Pure CPU inference on Pi 5.
- qwen 7B on Pi 5 ARM CPU is ~13 min/tool — slow.
- Small local models hallucinate confidently (see
  `docs/SAMPLE_qwen7b_nmap_OUTPUT.json` for the cautionary evidence).
- Only use this backend when network access genuinely isn't available.

## Why NOT Gemini

Gemini 2.5 Pro is genuinely strong, but adding a third cloud backend
triples the surface area to maintain for marginal gain over Claude +
DeepSeek combined. We can revisit if there's a specific reason — until
then, two backends covers ~95% of needs cleanly.

## Why NOT OpenAI (GPT)

The DeepSeek backend uses the OpenAI Python SDK (DeepSeek is OpenAI-
compatible). Adding GPT itself would be a one-line addition (change
the base URL). Not done because:

1. ERR0RS's strategic argument for DeepSeek as the "second cloud backend"
   is cost + open weights. GPT loses on both axes vs DeepSeek.
2. OpenAI's safety calibration for security work tends toward more
   refusals than Claude's. Worse fit for the use case.

Could be added trivially if needed — `_try_openai()` follows the same
shape as `_try_deepseek()` in `tools/generate_teach.py`.

## The system prompt is the soul

Whatever backend is on the other end of the wire, **every ERR0RS LLM
call prepends `src/ai/system_prompt.md`**. That file defines who ERR0RS
*is* — the wise, compassionate, patient teacher voice you read in any
ERR0RS interaction. The backend is the substrate; the system prompt is
the character.

This means:
- Switch backends mid-project? Voice stays the same.
- Add a new backend (GPT, Mistral, Llama)? Inherit ERR0RS's voice for free.
- Want to change ERR0RS's character? Edit one file, every backend updates.

## Configuration recap

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...     # primary, recommended
DEEPSEEK_API_KEY=sk-...          # secondary, optional
OPENAI_API_KEY=                  # not used directly

# Backend selection
LLM_BACKEND=auto                              # or: claude, deepseek, ollama
LLM_FALLBACK_CHAIN=claude,deepseek,ollama     # auto-mode order

# Per-backend model overrides (optional)
ANTHROPIC_MODEL=claude-sonnet-4-6-20260101    # default
DEEPSEEK_MODEL=deepseek-chat                  # default
OLLAMA_MODEL=qwen2.5-coder:7b                 # whatever you have local
```

## Running Phase 3 generation

```bash
# Recommended — let auto-mode walk the chain
python3 tools/generate_teach.py --all

# Or be explicit
python3 tools/generate_teach.py --all --backend claude
python3 tools/generate_teach.py --all --backend deepseek
python3 tools/generate_teach.py --all --backend ollama   # slow on Pi
```

Output goes to `src/tools/tool_registry.generated.json` (separate from
the canonical v2 registry). Phase 3b — `tools/merge_generated.py`,
not yet built — handles human-reviewed merging into v2.

---

*Strategy committed 2026-05-14. Revisit if Anthropic or DeepSeek's
pricing, terms, or capabilities shift materially.*
