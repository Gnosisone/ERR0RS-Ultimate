#!/usr/bin/env python3
"""
ERR0RS — Teach Generator (Phase 3)
══════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚠  PHASE 3 IS GATED ON HAILO ACCELERATION ⚠                                 ║
║                                                                              ║
║  Reality-check (verified 2026-05-14 on Pi 5 + Hailo-10H + Kali ARM64):       ║
║    • Ollama does NOT use the Hailo NPU. It runs on CPU only.                 ║
║    • qwen2.5-coder:7b on Pi 5 ARM CPU = ~13+ min per tool.                   ║
║    • Full 49-tool sweep = ~8-15 hours wall time.                             ║
║                                                                              ║
║  Recommended paths BEFORE running this script:                               ║
║    1. docs/HAILO_PHASE3_STATUS.md — read first                               ║
║    2. Use --backend anthropic with ANTHROPIC_API_KEY set (~5-10 min total)   ║
║    3. Run on a GPU machine, ship the resulting JSON                          ║
║    4. Wait for a real HailoBackend implementation                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

Uses an LLM (Ollama by default, Anthropic API as fallback) to fill in
the 5 stub fields that Phase 2 left empty in tool_registry.v2.json:

  - opsec_notes
  - sample_outputs
  - legal_notes
  - false_positives
  - mitre_attack

Output goes to src/tools/tool_registry.generated.json (a SEPARATE file)
for human review. It is NOT auto-merged into tool_registry.v2.json.
After review, use tools/merge_generated.py to fold approved entries in.

Backends (auto-detected from .env LLM_BACKEND or runtime fallback):
  ollama     — local, free, slow on first call but cached. Default.
  anthropic  — Claude API, requires ANTHROPIC_API_KEY, costs money.

Usage:
  python3 tools/generate_teach.py --sample nmap sqlmap dalfox
        Generate teach data for just the 3 listed tools — for quality gate
  python3 tools/generate_teach.py --all
        Generate for every tool that has any empty stub field
  python3 tools/generate_teach.py --tool nmap --backend anthropic
        Force a specific tool and backend
  python3 tools/generate_teach.py --dry-run
        Print prompts, don't call any LLM (useful for prompt iteration)
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

# Default to v3 (full 5007-tool arsenal) if present; otherwise v2 (49 tools)
_V3 = ROOT / "src" / "tools" / "tool_registry.v3.json"
_V2 = ROOT / "src" / "tools" / "tool_registry.v2.json"
REGISTRY = _V3 if _V3.exists() else _V2

SCHEMA = ROOT / "src" / "tools" / "tool_registry.schema.json"
SYSTEM_PROMPT_FILE = ROOT / "src" / "ai" / "system_prompt.md"
RANKED = ROOT / "tools" / "arsenal_ranked.json"  # popularity ordering for batches
OUT = ROOT / "src" / "tools" / "tool_registry.generated.json"

# Per-million-token pricing for --limit-cost real-spend accounting.
# Backend.generate() returns (text, usage) so the cost loop can bill against
# msg.usage.input_tokens / output_tokens instead of a flat per-call guess.
# Verified against Anthropic / DeepSeek public pricing 2026-05-19.
#
# Why the old _BACKEND_COST_PER_CALL = 0.050 flat-rate scheme had to go:
#   On the 2026-05-17 Sonnet 4.6 run we projected $0.050/tool and actually
#   burned $0.078/tool (+36%). The cap fired ~28 tools late and Anthropic
#   credits exhausted before our counter said we'd hit the limit.
# Fix: bill real usage. Sonnet teach cards run ~1000 in + ~4500 out tokens
# (the 12k-char output is the dominant cost), which yields ~$0.075/tool —
# within 5% of observed.
#
# Format: (input_$_per_MTok, output_$_per_MTok). 0.0 = free.
_BACKEND_COST_PER_MTOK = {
    "anthropic": (3.00, 15.00),   # Claude Sonnet 4.6 (default model)
    "claude":    (3.00, 15.00),   # alias
    "deepseek":  (0.27,  1.10),   # DeepSeek V3 (deepseek-chat)
    "ollama":    (0.0,   0.0),    # local, no API charge
}

# Per-model overrides for `anthropic` backend when --model is used. Falls back
# to _BACKEND_COST_PER_MTOK["anthropic"] (Sonnet) if the model isn't listed.
_ANTHROPIC_MODEL_PRICING = {
    "claude-opus-4-7":    (5.00, 25.00),
    "claude-opus-4-6":    (5.00, 25.00),
    "claude-sonnet-4-6":  (3.00, 15.00),
    "claude-sonnet-4-5":  (3.00, 15.00),
    "claude-haiku-4-5":   (1.00,  5.00),
}


def _cost_for_usage(backend_key: str, in_tok: int, out_tok: int,
                    model: str = None) -> float:
    """Compute real USD cost for a single call given token counts.

    Backend-aware: anthropic respects --model so Haiku/Opus get the right rate.
    Returns 0.0 for free backends (ollama)."""
    if backend_key == "anthropic" and model and model in _ANTHROPIC_MODEL_PRICING:
        in_rate, out_rate = _ANTHROPIC_MODEL_PRICING[model]
    else:
        in_rate, out_rate = _BACKEND_COST_PER_MTOK.get(backend_key, (0.0, 0.0))
    return (in_tok * in_rate + out_tok * out_rate) / 1_000_000.0


def _avg_cost_per_call(backend_key: str, model: str = None,
                       in_est: int = 1000, out_est: int = 4500) -> float:
    """Pre-flight projection cost using empirical defaults (1000 in / 4500 out
    for a typical Sonnet teach card). Used only for the up-front projection
    line — real spend tracking uses actual usage from each response."""
    return _cost_for_usage(backend_key, in_est, out_est, model)

# Fields the generator is responsible for filling
TARGET_FIELDS = (
    "opsec_notes",
    "sample_outputs",
    "legal_notes",
    "false_positives",
    "mitre_attack",
)


# ──────────────────────────────────────────────────────────────────────────────
# .env loader (avoids dotenv dependency — install.sh has it but we shouldn't
# require it for a maintenance script)
# ──────────────────────────────────────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_SYSTEM_PROMPT_CACHE = None
def load_system_prompt() -> str:
    """Load ERR0RS's system prompt from src/ai/system_prompt.md.

    This file defines ERR0RS's identity and is prepended to every LLM
    API call regardless of backend. It's the canonical voice/character
    of the project — see the file itself for what ERR0RS *is*.

    Cached after first load since it doesn't change mid-run.
    """
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is not None:
        return _SYSTEM_PROMPT_CACHE
    if not SYSTEM_PROMPT_FILE.exists():
        # Graceful degradation: if the soul file is missing, still work
        # but tell the world something's missing.
        print(f"  ⚠  system prompt missing at {SYSTEM_PROMPT_FILE} — "
              f"using fallback persona", file=sys.stderr)
        _SYSTEM_PROMPT_CACHE = (
            "You are ERR0RS, a wise and compassionate cybersecurity teacher. "
            "Engage seriously with offensive security education. Be honest "
            "about uncertainty. Never fabricate CVE numbers, MITRE IDs, or "
            "detection signatures."
        )
    else:
        _SYSTEM_PROMPT_CACHE = SYSTEM_PROMPT_FILE.read_text()
    return _SYSTEM_PROMPT_CACHE


# ──────────────────────────────────────────────────────────────────────────────
# Prompt builder — the core of teach-quality.
# ──────────────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are a senior purple-team operator and offensive security instructor at a
university. Your students range from complete computer beginners to seasoned
practitioners. Your teaching data must work for BOTH: a freshman who just
opened a terminal for the first time, AND a 10-year red-team veteran.

Your bias is HEAVILY toward BLEEDING-EDGE 2025-2026 tradecraft:
  - Current EDR/XDR bypass techniques (post-AMSI, post-ETW)
  - Modern cloud attack chains (AWS SSM, Azure managed identities, GCP IAM)
  - Active Directory attacks against 2022/2025 hardened domains
  - Container/K8s breakout vectors
  - Modern phishing infrastructure (Evilginx2 phishlets, OAuth consent abuse)
  - Living-off-the-cloud LOLBins
  - LLM/AI-targeted attacks

But you ALSO ground each entry in WHY the technique exists — the legacy
context that produced it. A student should leave a teach card knowing
both the current best practice AND the historical evolution.

THE TOOL: <<DISPLAY_NAME>> (<<BINARY>>)
CATEGORY: <<CATEGORY>>
DEFAULT RISK: <<RISK>>
DESCRIPTION: <<DESCRIPTION>>

CURRENT TEACH INTRO (for context — do not repeat):
<<TEACH_INTRO>>

FLAGS THE TOOL SUPPORTS (for context):
<<FLAG_LIST>>

OUTPUT FORMAT
═════════════
Respond with ONE valid JSON object — NO prose, NO markdown fences,
NO leading "Here is the JSON:", NO trailing commentary. Just the JSON.

Required schema:

{{
  "opsec_notes": [
    "string — operational-security tip referencing CONCRETE detection vectors"
  ],
  "sample_outputs": [
    {{
      "scenario": "Brief context: target type, flags used, what the operator is hunting",
      "command": "Exact command line that produced this output",
      "output": "Realistic 8-20 line excerpt — REAL formatting, REAL columns, REAL prefixes ([+], ==>, PORT, etc.), realistic but fictional version strings",
      "explanation": "What the output tells the operator AND the next 2-3 logical actions in the kill chain"
    }}
  ],
  "legal_notes": [
    "string — specific authorization boundary relevant to THIS tool's capabilities"
  ],
  "false_positives": [
    "string — known way this tool will lie or mislead"
  ],
  "mitre_attack": [
    {{ "id": "T1046", "name": "Network Service Discovery" }}
  ]
}}

QUALITY RULES
═════════════
1. opsec_notes (4-6 entries, mix beginner + advanced):
   - At least ONE entry must be beginner-grade: "what is the obvious noise
     this makes" (DNS queries, ICMP, web logs, etc.)
   - At least TWO entries must be CUTTING-EDGE 2025-2026: reference current
     EDR products (CrowdStrike Falcon, SentinelOne, Defender for Endpoint),
     modern detection telemetry (process tree, parent-child anomalies,
     command-line entropy scoring, AMSI logs, ETW-TI), or evasion of recent
     defensive shifts (kernel callbacks since Win11 22H2, Sysmon EID 25,
     etc.) WHERE TRUTHFUL — do not fabricate if uncertain.
   - At least ONE entry must reference a CONCRETE artifact a defender sees:
     log path, EID, packet signature, network flow pattern, file write.
   - Generic advice like "be careful" or "use a VPN" is FORBIDDEN.

2. sample_outputs (2 entries, beginner + advanced):
   - First entry: SIMPLE — a beginner scenario, single host, default flags,
     a clear "open port found" or "credential cracked" outcome. The
     explanation must teach the beginner WHY the output looks that way.
   - Second entry: ADVANCED — a real-world chain. The explanation should
     mention 2-3 next-step tools or follow-up commands by name.
   - Output column alignment must be REAL — when nmap prints "PORT     STATE
     SERVICE VERSION" it's space-padded to specific widths. Get this right.
   - NEVER fabricate CVE numbers. Use realistic placeholders like
     "Apache/2.4.x" or "CVE-2025-XXXXX" if uncertain.

3. legal_notes (2-3 entries):
   - One US CFAA-grounded boundary specific to this tool
   - One authorization-scope reminder (rules of engagement, IP scope, etc.)
   - One modern-cloud or modern-AD consideration where relevant

4. false_positives (3-5 entries):
   - Specific, technical gotchas only an operator with hands-on experience
     knows. "Stateful firewalls make closed ports look filtered" — that
     kind of substance, not "results can vary".

5. mitre_attack (1-4 entries):
   - Real, current ATT&CK technique IDs in Txxxx or Txxxx.yyy format
   - Only techniques the tool DIRECTLY enables — not "downstream effects"
   - Prefer sub-techniques (T1110.001) over parent IDs (T1110) when accurate

6. HONESTY: When uncertain about a specific CVE, detection signature, or
   version string — say so or use a placeholder. Fabricated specifics
   teach students wrong things and get them hurt on live engagements.

7. JSON FORMATTING RULES (your output WILL be parsed by json.loads):
   * NO markdown fences (no ```json, no ``` anywhere). NO preamble text.
     NO "Here is the JSON:". NO trailing commentary. Just the JSON object.
   * Inside strings, backslashes are SPECIAL. Only these escapes are valid:
     \\"   for a literal double quote
     \\\\  for a literal backslash
     \\n   for a newline
     \\t   for a tab
     \\r   for a carriage return
     \\/   for a forward slash (optional)
   * For Windows paths, AD usernames, regex, or shell escape sequences:
     write the literal backslash as \\\\ (two backslashes in JSON source).
     Example: "command": "smbclient //10.10.10.5/share -U CORP\\\\jsmith"
              "output": "C:\\\\Users\\\\Admin\\\\Documents"
   * For quotes inside command strings, prefer escaping over single quotes:
     "command": "powershell -c \\"Get-Process | Where {{ $_.CPU -gt 5 }}\\""
   * Do NOT include trailing commas before } or ].
   * Do NOT use Python-style triple quotes or template strings.
   * Output must round-trip through json.loads() WITHOUT errors.

Begin JSON output now (start with `{` and end with `}` — nothing else):
"""


def build_prompt(tool_key: str, tool: dict) -> str:
    """Construct the prompt for one tool.

    Uses str.replace() instead of str.format() so curly braces inside the
    prompt template (example JSON, PowerShell scriptblocks) don't need to
    be escaped. Placeholders are <<NAME>> sentinels."""
    flag_lines = []
    for flag_name, flag_data in list(tool.get("flags", {}).items())[:15]:
        label = flag_data.get("label", flag_name)
        flag_lines.append(f"  {flag_name:20s} — {label}")
    flag_list = "\n".join(flag_lines) if flag_lines else "  (no flags documented)"

    out = PROMPT_TEMPLATE
    out = out.replace("<<DISPLAY_NAME>>", tool.get("display_name", tool_key))
    out = out.replace("<<BINARY>>", tool.get("binary", tool_key))
    out = out.replace("<<CATEGORY>>", tool.get("category", "utility"))
    out = out.replace("<<RISK>>", tool.get("risk", "moderate"))
    out = out.replace("<<DESCRIPTION>>", tool.get("description", "")[:300])
    out = out.replace("<<TEACH_INTRO>>", tool.get("teach_intro", "")[:500])
    out = out.replace("<<FLAG_LIST>>", flag_list)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Backends
# ──────────────────────────────────────────────────────────────────────────────
class OllamaBackend:
    """Talks to a local Ollama server. Uses /api/generate with format=json
    so the model is forced to return parseable JSON."""

    def __init__(self, model: str, host: str, timeout: int = 900):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        # Use stdlib urllib so we have zero extra deps
        import urllib.request, urllib.error
        self.urllib = urllib
        self.system_prompt = load_system_prompt()
        self._verify()

    def _verify(self):
        try:
            req = self.urllib.request.Request(f"{self.host}/api/tags")
            with self.urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
                models = [m["name"] for m in data.get("models", [])]
                if self.model not in models:
                    # Don't crash — Ollama can pull on first use
                    print(f"  ⚠  model {self.model} not pre-pulled, will load on first call")
        except Exception as e:
            raise RuntimeError(f"Ollama at {self.host} unreachable: {e}")

    def generate(self, prompt: str, max_tokens: int = 4000) -> tuple[str, dict]:
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": self.system_prompt,    # ERR0RS soul — see src/ai/system_prompt.md
            "stream": True,          # stream so we see progress + can timeout intelligently
            "format": "json",
            "options": {
                "temperature": 0.3,        # low for structured output
                "num_predict": max_tokens,
                "top_p": 0.9,
                "num_ctx": 8192,           # bigger context for our long prompts
            },
        }).encode("utf-8")

        req = self.urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )

        # Stream chunks — gives us per-token feedback and lets us bail
        # if generation stalls (vs blind socket-timeout wait)
        chunks = []
        last_token_time = time.time()
        in_tok = 0
        out_tok = 0
        with self.urllib.request.urlopen(req, timeout=self.timeout) as r:
            for raw_line in r:
                if not raw_line.strip():
                    continue
                try:
                    obj = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if obj.get("response"):
                    chunks.append(obj["response"])
                    last_token_time = time.time()
                    # Print a dot every ~50 tokens for visible progress
                    if len(chunks) % 50 == 0:
                        print(".", end="", flush=True)
                if obj.get("done"):
                    # Final chunk carries token counts (when supported)
                    in_tok  = obj.get("prompt_eval_count", 0) or 0
                    out_tok = obj.get("eval_count",         0) or 0
                    break
                # Stall guard: if no tokens for 120s mid-stream, abort
                if time.time() - last_token_time > 120:
                    raise TimeoutError("generation stalled for 120s")

        usage = {"input_tokens": in_tok, "output_tokens": out_tok, "model": self.model}
        return "".join(chunks), usage


class AnthropicBackend:
    """Talks to api.anthropic.com via the official anthropic library.
    Prepends ERR0RS's system prompt (src/ai/system_prompt.md) so the model
    speaks with ERR0RS's voice, not Anthropic's default Claude persona."""

    # Default model — claude-sonnet-4-6 for highest quality, claude-haiku-4-5
    # for fastest/cheapest. Sonnet recommended for the teach generation since
    # it's a one-time build cost and quality is critical.
    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, api_key: str, model: str = None):
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic library not installed in venv")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        self.system_prompt = load_system_prompt()

    def generate(self, prompt: str, max_tokens: int = 4000) -> tuple[str, dict]:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        # stop_reason "max_tokens" means truncation — output will be incomplete
        # JSON. Surface as a hard failure so the loop doesn't save garbage.
        if getattr(msg, "stop_reason", None) == "max_tokens":
            raise RuntimeError(
                f"response truncated at max_tokens={max_tokens}; "
                f"consider raising the cap or simplifying the prompt"
            )
        text = "".join(block.text for block in msg.content if hasattr(block, "text"))
        # Real token counts from the API response — what the cost loop bills against
        usage = {
            "input_tokens":  getattr(msg.usage, "input_tokens",  0),
            "output_tokens": getattr(msg.usage, "output_tokens", 0),
            "model":         self.model,
        }
        return text, usage


class DeepSeekBackend:
    """Talks to api.deepseek.com via OpenAI-compatible endpoint.
    Cheaper than Claude (~5-10x), open-weights model, good for student-
    accessible build-time generation. Honors the ERR0RS system prompt."""

    DEFAULT_MODEL = "deepseek-chat"   # deepseek-chat (V3) is the workhorse
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str, model: str = None, base_url: str = None):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai library not installed in venv "
                               "(DeepSeek uses OpenAI-compatible API)")
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
        )
        self.model = model or self.DEFAULT_MODEL
        self.system_prompt = load_system_prompt()

    def generate(self, prompt: str, max_tokens: int = 4000) -> tuple[str, dict]:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": prompt},
            ],
        )
        text = resp.choices[0].message.content or ""
        u = getattr(resp, "usage", None)
        usage = {
            "input_tokens":  getattr(u, "prompt_tokens", 0)     if u else 0,
            "output_tokens": getattr(u, "completion_tokens", 0) if u else 0,
            "model":         self.model,
        }
        return text, usage


# ──────────────────────────────────────────────────────────────────────────────
# Response parsing — robust against LLMs that leak prose despite instructions
# ──────────────────────────────────────────────────────────────────────────────
# Valid JSON escape characters (RFC 8259 §7)
_JSON_VALID_ESCAPES = set('"\\/bfnrtu')


def _repair_json(text: str) -> str:
    r"""Best-effort repair of LLM JSON output that's almost-valid.

    Common LLM mistakes this fixes:
      1. \X where X is not a valid JSON escape — e.g. \j, \W, \' in
         strings containing AD usernames (CORP\jsmith), Windows paths,
         shell-escaped quotes. Fixes by changing \X to \\X.
      2. Smart quotes/em-dashes — replaces curly typography with straight
         ASCII so the JSON parser doesn't see "string" as raw Unicode.
      3. Trailing commas before } or ] — strips them.

    These are safe transformations: any well-formed JSON passes through
    unchanged. Only malformed input gets repaired."""
    # 1. Smart quotes → straight quotes (must come before escape fix)
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    # Note: em-dashes (— —) and ellipsis (…) are valid inside JSON strings,
    # don't touch them — they're authentic ERR0RS voice.

    # 2. Fix invalid \X escape sequences.
    # State machine: walk through the string, tracking whether we're inside
    # a JSON string (between unescaped " marks). Only repair escapes inside strings.
    out = []
    i = 0
    in_string = False
    while i < len(text):
        c = text[i]
        if c == '"' and (i == 0 or text[i-1] != '\\'):
            in_string = not in_string
            out.append(c)
            i += 1
            continue
        if in_string and c == '\\' and i + 1 < len(text):
            nxt = text[i+1]
            if nxt in _JSON_VALID_ESCAPES:
                # Valid escape — pass through
                out.append(c)
                out.append(nxt)
                i += 2
                continue
            else:
                # Invalid escape — fix by doubling the backslash so the literal
                # backslash + character are preserved in the parsed string.
                out.append('\\\\')   # \\ in JSON = single backslash in output
                out.append(nxt)
                i += 2
                continue
        out.append(c)
        i += 1
    text = ''.join(out)

    # 3. Strip trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text


def parse_response(text: str) -> Optional[dict]:
    """Pull a JSON object out of the LLM response, even if it's wrapped in
    markdown fences or has leading/trailing prose, or has the common LLM
    JSON-escape mistakes (backslash-j, backslash-W, backslash-quote, smart quotes, trailing commas)."""
    text = text.strip()

    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try direct parse — fast path for well-formed responses
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first { ... } block (greedy match)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    candidate = match.group(0)

    # Try parsing the extracted block
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # JSON-repair pass — fix common LLM escape mistakes and retry
    repaired = _repair_json(candidate)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        print(f"     parse error even after repair: {e}", file=sys.stderr)
        # Save the failed attempt to debug dir for inspection
        try:
            from pathlib import Path
            dbg = Path(__file__).resolve().parent / "_debug"
            dbg.mkdir(exist_ok=True)
            (dbg / "last_unparseable.json").write_text(repaired)
        except Exception:
            pass
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Validation — make sure generated data matches schema before we accept it
# ──────────────────────────────────────────────────────────────────────────────
MITRE_PATTERN = re.compile(r"^T[0-9]{4}(\.[0-9]{3})?$")


def validate_generated(data: dict) -> tuple[bool, list[str]]:
    """Returns (is_valid, list_of_errors). Validates only the fields the
    generator is responsible for — ignores anything else."""
    errors = []

    # opsec_notes: list of strings, 1-5 entries
    on = data.get("opsec_notes", [])
    if not isinstance(on, list) or not all(isinstance(x, str) for x in on):
        errors.append("opsec_notes must be array of strings")
    elif len(on) == 0:
        errors.append("opsec_notes is empty")

    # sample_outputs: list of {scenario, command, output, explanation}
    so = data.get("sample_outputs", [])
    if not isinstance(so, list):
        errors.append("sample_outputs must be an array")
    else:
        for i, s in enumerate(so):
            if not isinstance(s, dict):
                errors.append(f"sample_outputs[{i}] must be an object")
                continue
            for req in ("scenario", "output", "explanation"):
                if req not in s:
                    errors.append(f"sample_outputs[{i}] missing '{req}'")

    # legal_notes
    ln = data.get("legal_notes", [])
    if not isinstance(ln, list) or not all(isinstance(x, str) for x in ln):
        errors.append("legal_notes must be array of strings")

    # false_positives
    fp = data.get("false_positives", [])
    if not isinstance(fp, list) or not all(isinstance(x, str) for x in fp):
        errors.append("false_positives must be array of strings")

    # mitre_attack
    ma = data.get("mitre_attack", [])
    if not isinstance(ma, list):
        errors.append("mitre_attack must be an array")
    else:
        for i, m in enumerate(ma):
            if not isinstance(m, dict) or "id" not in m or "name" not in m:
                errors.append(f"mitre_attack[{i}] must have id and name")
                continue
            if not MITRE_PATTERN.match(m["id"]):
                errors.append(f"mitre_attack[{i}].id '{m['id']}' not in Txxxx[.yyy] format")

    return (len(errors) == 0, errors)


# ──────────────────────────────────────────────────────────────────────────────
# Backend selection — Claude primary, DeepSeek secondary, Ollama tertiary
# ──────────────────────────────────────────────────────────────────────────────
def _try_anthropic(env: dict):
    key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return AnthropicBackend(key, model=env.get("ANTHROPIC_MODEL") or None)


def _try_deepseek(env: dict):
    key = env.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    return DeepSeekBackend(
        key,
        model=env.get("DEEPSEEK_MODEL") or None,
        base_url=env.get("DEEPSEEK_BASE_URL") or None,
    )


def _try_ollama(env: dict):
    return OllamaBackend(
        model=env.get("OLLAMA_MODEL") or "qwen2.5-coder:7b",
        host=env.get("OLLAMA_HOST") or "http://localhost:11434",
    )


# Map of backend name -> initializer. Used by both explicit and auto modes.
_BACKEND_INITS = {
    "claude":    _try_anthropic,
    "anthropic": _try_anthropic,   # alias
    "deepseek":  _try_deepseek,
    "ollama":    _try_ollama,
}


def get_backend(prefer: str, env: dict):
    """Return a configured backend object.

    `prefer` is one of:
      'claude' / 'anthropic'   → Claude only, fail if unavailable
      'deepseek'               → DeepSeek only, fail if unavailable
      'ollama'                 → Ollama only, fail if unavailable
      'auto'                   → fallback chain via LLM_FALLBACK_CHAIN env var
                                 (default: 'claude,deepseek,ollama')

    The fallback chain is the philosophical backbone of ERR0RS's backend
    strategy — Claude primary because of character fit for pedagogy,
    DeepSeek secondary for cost-accessibility and future-local potential
    (open weights), Ollama tertiary for true offline operation.
    """
    if prefer in _BACKEND_INITS:
        return _BACKEND_INITS[prefer](env)

    if prefer != "auto":
        raise ValueError(f"Unknown backend: {prefer!r}. "
                         f"Valid: {list(_BACKEND_INITS) + ['auto']}")

    # Auto mode — walk the fallback chain
    chain_str = env.get("LLM_FALLBACK_CHAIN") or "claude,deepseek,ollama"
    chain = [x.strip() for x in chain_str.split(",") if x.strip()]

    last_error = None
    for backend_name in chain:
        if backend_name not in _BACKEND_INITS:
            print(f"  ⚠  unknown backend {backend_name!r} in fallback chain — skipping")
            continue
        try:
            backend = _BACKEND_INITS[backend_name](env)
            if backend_name != chain[0]:
                # Indicate we fell back from earlier in the chain
                print(f"  ⚠  fell back to {backend_name} (earlier backends "
                      f"unavailable: {last_error})")
            return backend
        except Exception as e:
            last_error = f"{backend_name}: {e}"
            continue

    raise RuntimeError(f"All backends in fallback chain {chain} unavailable. "
                       f"Last error: {last_error}")


# ──────────────────────────────────────────────────────────────────────────────
# Main driver
# ──────────────────────────────────────────────────────────────────────────────
def needs_generation(tool: dict) -> bool:
    """A tool needs generation if ANY of the target fields is empty."""
    for field in TARGET_FIELDS:
        val = tool.get(field, [])
        if not val:  # empty list, empty dict, or missing
            return True
    return False


def generate_for_tool(tool_key: str, tool: dict, backend, dry_run: bool = False) -> Optional[dict]:
    """Generate teach data for one tool. Returns (parsed_dict, usage_dict)
    on success, or (None, usage_dict) on failure. usage_dict carries real
    input/output token counts the cost loop bills against."""
    prompt = build_prompt(tool_key, tool)

    if dry_run:
        print(f"\n──── DRY RUN: prompt for {tool_key} ────")
        print(prompt)
        print(f"──── END {tool_key} ────\n")
        return None, {"input_tokens": 0, "output_tokens": 0, "model": None}

    print(f"  → generating: {tool_key} ... ", end="", flush=True)
    t0 = time.time()
    usage = {"input_tokens": 0, "output_tokens": 0, "model": None}
    try:
        raw, usage = backend.generate(prompt, max_tokens=4000)
    except Exception as e:
        print(f"FAIL ({e})")
        return None, usage
    elapsed = time.time() - t0

    data = parse_response(raw)
    if data is None:
        print(f"PARSE FAIL ({elapsed:.1f}s)")
        # Save raw output for debugging
        debug_dir = ROOT / "tools" / "_debug"
        debug_dir.mkdir(exist_ok=True)
        (debug_dir / f"{tool_key}.raw.txt").write_text(raw)
        # NOTE: parse failure still spent the tokens — return usage so the
        # cost loop counts it (you got billed whether it parsed or not).
        return None, usage

    valid, errors = validate_generated(data)
    if not valid:
        print(f"INVALID ({elapsed:.1f}s): {errors[0]}")
        debug_dir = ROOT / "tools" / "_debug"
        debug_dir.mkdir(exist_ok=True)
        (debug_dir / f"{tool_key}.invalid.json").write_text(json.dumps(data, indent=2))
        return None, usage

    print(f"✓ ({elapsed:.1f}s)")
    return data, usage


def _select_targets_by_tier(tools, tier, ranked_list):
    """Return tool keys for a given tier — hand-curated v2 tools FIRST,
    then popularity-ranked BlackArch tools after.

    Why this order: hand-curated v2 tools (nmap, aircrack-ng, hashcat,
    metasploit, hydra, wireshark, etc.) are THE canon. They have rich
    flag metadata, real teach_intros, and are the tools every student
    will hit in their first 100 hours of training. They take priority
    over BlackArch tools regardless of how high a BlackArch tool scored,
    because BlackArch tools start with empty teach data while v2 tools
    only need the bleeding-edge 5-field stub filled in.
    """
    in_tier = {k for k, t in tools.items() if t.get("tier") == tier}
    # Tools that came from v2 (don't appear in ranked_list, which only
    # lists BlackArch tools): canonical, go FIRST alphabetically
    ranked_names = {r["name"].lower() for r in ranked_list}
    v2_first = sorted(in_tier - ranked_names)
    # Then BlackArch tools by popularity rank
    blackarch_by_rank = [r["name"].lower() for r in ranked_list if r["name"].lower() in in_tier]
    return v2_first + blackarch_by_rank


def main():
    parser = argparse.ArgumentParser(description="ERR0RS teach generator (Phase 3)")
    parser.add_argument("--sample", nargs="+", metavar="TOOL",
                        help="Generate only for these tools (quality gate mode)")
    parser.add_argument("--tool", metavar="NAME", help="Generate for one specific tool")
    parser.add_argument("--all", action="store_true",
                        help="Generate for every tool with empty stub fields")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], metavar="N",
                        help="Generate only tier-N tools, ordered by popularity "
                             "(use with --batch-size + --start-rank)")
    parser.add_argument("--batch-size", type=int, default=0, metavar="N",
                        help="Process at most N tools then stop (0 = no limit)")
    parser.add_argument("--start-rank", type=int, default=0, metavar="N",
                        help="Skip the first N target tools (resume support)")
    parser.add_argument("--limit-cost", type=float, default=0.0, metavar="USD",
                        help="Hard cap on estimated spend in USD. Aborts the run "
                             "before exceeding (0.0 = no limit). Honored only for "
                             "paid backends (anthropic, deepseek).")
    parser.add_argument("--backend",
                        choices=["claude", "anthropic", "deepseek", "ollama", "auto"],
                        default="auto",
                        help="Which LLM backend to use. 'auto' walks the "
                             "fallback chain (default: claude→deepseek→ollama)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print prompts, don't call any LLM")
    parser.add_argument("--out", default=str(OUT),
                        help="Output file (default: tool_registry.generated.json)")
    args = parser.parse_args()

    if not any([args.sample, args.tool, args.all, args.tier, args.dry_run]):
        parser.error("Specify one of --sample, --tool, --all, --tier, or --dry-run")

    env = load_env()
    print("=" * 70)
    print(" ERR0RS Teach Generator — Phase 3")
    print("=" * 70)

    # Load registry
    registry_data = json.load(open(REGISTRY))
    tools = registry_data["tools"]
    print(f"\n  registry: {REGISTRY.name}  ({len(tools)} tools)")

    # Load popularity ranking if available
    ranked_list = []
    if RANKED.exists():
        ranked_list = json.load(open(RANKED))

    # Decide which tools to process
    if args.tool:
        targets = [args.tool.lower()]
    elif args.sample:
        targets = [t.lower() for t in args.sample]
    elif args.tier:
        targets = _select_targets_by_tier(tools, args.tier, ranked_list)
        # Filter to ones that actually need generation
        targets = [t for t in targets if needs_generation(tools[t])]
        print(f"  tier {args.tier}: {len(targets)} tools need generation "
              f"(ordered by popularity rank)")
    elif args.all:
        targets = [k for k, t in tools.items() if needs_generation(t)]
    else:
        targets = list(tools.keys())[:1]  # dry-run: just one for demo

    # Apply --start-rank (resume support)
    if args.start_rank > 0:
        skipped = args.start_rank
        targets = targets[args.start_rank:]
        print(f"  skipping first {skipped} targets (--start-rank)")

    # Apply --batch-size cap
    if args.batch_size > 0:
        targets = targets[:args.batch_size]
        print(f"  batch capped at {args.batch_size} tools (--batch-size)")

    # Validate target tools exist
    missing = [t for t in targets if t not in tools]
    if missing:
        print(f"  ✗ unknown tools: {missing}")
        sys.exit(1)

    print(f"  targets: {len(targets)} tools — {', '.join(targets[:6])}"
          + ("..." if len(targets) > 6 else ""))

    # Get backend (unless dry-run)
    if args.dry_run:
        backend = None
        print("\n  (dry-run — no LLM calls)")
    else:
        try:
            backend = get_backend(args.backend, env)
            backend_name = type(backend).__name__
            print(f"  backend: {backend_name}")
            # Show model name for all backends so the user knows what's running
            if hasattr(backend, "model"):
                print(f"  model:   {backend.model}")
            # Confirm system prompt loaded
            sp_len = len(load_system_prompt())
            print(f"  system prompt: {sp_len} chars from {SYSTEM_PROMPT_FILE.name}")
        except Exception as e:
            print(f"  ✗ backend init failed: {e}")
            sys.exit(2)

    # Load existing generated.json if present (resume support)
    out_path = Path(args.out)
    if out_path.exists():
        existing = json.load(open(out_path))
        generated = existing.get("tools", {})
        print(f"  resuming: {len(generated)} entries already in {out_path.name}")
    else:
        generated = {}

    # Cost tracking — uses REAL token counts from each response.
    # The 2026-05-17 bug: we projected $0.050/tool and actually burned $0.078.
    # Now: project from empirical defaults, bill from msg.usage, cap on real spend.
    backend_key = args.backend if args.backend != "auto" else "ollama"
    if not args.dry_run and "backend" in dir() and backend is not None:
        bn = type(backend).__name__.lower()
        if "anthropic" in bn:
            backend_key = "anthropic"
        elif "deepseek" in bn:
            backend_key = "deepseek"
        else:
            backend_key = "ollama"

    # The model the user actually selected, if --model was passed. Used so
    # Haiku/Opus get the right per-MTok rate when --backend anthropic.
    backend_model = getattr(backend, "model", None) if backend is not None else None
    avg_cost = _avg_cost_per_call(backend_key, backend_model)
    real_spend = 0.0          # billed against actual usage tokens
    real_in_tok = 0
    real_out_tok = 0

    if avg_cost > 0:
        projected = avg_cost * len(targets)
        print(f"\n  cost projection: ~${projected:.2f} for {len(targets)} tools "
              f"(empirical avg ~${avg_cost:.4f}/tool with {backend_key}"
              f"{f'/{backend_model}' if backend_model else ''})")
        print(f"  NOTE: real spend is billed from msg.usage per call, not this projection")
        if args.limit_cost > 0 and projected > args.limit_cost:
            print(f"  ⚠  projected spend ${projected:.2f} exceeds "
                  f"--limit-cost ${args.limit_cost:.2f}")
            print(f"  ⚠  cap will fire on real spend mid-run if it ramps faster than projection")

    # Generate
    print("\n  starting generation...\n")
    successes = 0
    for i, tool_key in enumerate(targets, 1):
        if tool_key in generated and not args.dry_run:
            print(f"  ~ skipping {tool_key} (already in {out_path.name})")
            continue

        # Pre-flight cost check — bail BEFORE the call if a typical call
        # would push real spend over the cap. Worst case overshoots by one
        # avg_cost; without this we could overshoot by an entire batch.
        if not args.dry_run and args.limit_cost > 0 and avg_cost > 0:
            if real_spend + avg_cost > args.limit_cost:
                print(f"\n  ⚠  ABORTING: next call would push real spend to "
                      f"~${real_spend + avg_cost:.2f}, exceeding "
                      f"--limit-cost ${args.limit_cost:.2f}")
                print(f"  ⚠  {successes} tools completed at "
                      f"${real_spend:.4f} real spend "
                      f"({real_in_tok} in / {real_out_tok} out tokens)")
                break

        print(f"  [{i}/{len(targets)}]", end=" ")
        result, usage = generate_for_tool(tool_key, tools[tool_key], backend, args.dry_run)

        # Bill regardless of result — failed parses still cost real tokens
        call_cost = _cost_for_usage(
            backend_key,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("model"),
        )
        real_spend  += call_cost
        real_in_tok  += usage.get("input_tokens", 0)
        real_out_tok += usage.get("output_tokens", 0)

        if result is not None:
            generated[tool_key] = result
            successes += 1
            # Save after EVERY successful generation — protects against crashes
            out_data = {
                "version": "3.0.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_registry_version": registry_data.get("version", "unknown"),
                "tools": generated,
            }
            out_path.write_text(json.dumps(out_data, indent=2, ensure_ascii=False))

    if not args.dry_run:
        print(f"\n  ✓ wrote {out_path}")
        print(f"  ✓ {len(generated)} tools total in generated file "
              f"({successes} new this run)")
        if avg_cost > 0:
            print(f"  ≈ real spend this run: ${real_spend:.4f} "
                  f"({real_in_tok} input + {real_out_tok} output tokens)")
            if successes > 0:
                print(f"    actual avg: ${real_spend/successes:.4f}/tool "
                      f"(empirical projection was ${avg_cost:.4f}/tool)")
        print(f"\n  Next: review with `python3 tools/inspect_generated.py`,")
        print(f"        then merge with `python3 tools/merge_generated.py --write`")


if __name__ == "__main__":
    main()
