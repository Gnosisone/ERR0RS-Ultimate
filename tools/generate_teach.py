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
REGISTRY = ROOT / "src" / "tools" / "tool_registry.v2.json"
SCHEMA = ROOT / "src" / "tools" / "tool_registry.schema.json"
SYSTEM_PROMPT_FILE = ROOT / "src" / "ai" / "system_prompt.md"
OUT = ROOT / "src" / "tools" / "tool_registry.generated.json"

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

THE TOOL: {display_name} ({binary})
CATEGORY: {category}
DEFAULT RISK: {risk}
DESCRIPTION: {description}

CURRENT TEACH INTRO (for context — do not repeat):
{teach_intro}

FLAGS THE TOOL SUPPORTS (for context):
{flag_list}

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

7. NO MARKDOWN. NO ```json fences. NO "Here is the JSON:". Just the JSON.

Begin JSON output now:
"""


def build_prompt(tool_key: str, tool: dict) -> str:
    """Construct the prompt for one tool."""
    flag_lines = []
    for flag_name, flag_data in list(tool.get("flags", {}).items())[:15]:
        label = flag_data.get("label", flag_name)
        flag_lines.append(f"  {flag_name:20s} — {label}")
    flag_list = "\n".join(flag_lines) if flag_lines else "  (no flags documented)"

    return PROMPT_TEMPLATE.format(
        display_name=tool.get("display_name", tool_key),
        binary=tool.get("binary", tool_key),
        category=tool.get("category", "utility"),
        risk=tool.get("risk", "moderate"),
        description=tool.get("description", "")[:300],
        teach_intro=tool.get("teach_intro", "")[:500],
        flag_list=flag_list,
    )


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

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
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
                    break
                # Stall guard: if no tokens for 120s mid-stream, abort
                if time.time() - last_token_time > 120:
                    raise TimeoutError("generation stalled for 120s")

        return "".join(chunks)


class AnthropicBackend:
    """Talks to api.anthropic.com via the official anthropic library.
    Prepends ERR0RS's system prompt (src/ai/system_prompt.md) so the model
    speaks with ERR0RS's voice, not Anthropic's default Claude persona."""

    # Default model — claude-sonnet-4-6 for highest quality, claude-haiku-4-5
    # for fastest/cheapest. Sonnet recommended for the teach generation since
    # it's a one-time build cost and quality is critical.
    DEFAULT_MODEL = "claude-sonnet-4-6-20260101"

    def __init__(self, api_key: str, model: str = None):
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic library not installed in venv")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL
        self.system_prompt = load_system_prompt()

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=0.3,
            system=self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if hasattr(block, "text"))


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

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
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
        return resp.choices[0].message.content or ""


# ──────────────────────────────────────────────────────────────────────────────
# Response parsing — robust against LLMs that leak prose despite instructions
# ──────────────────────────────────────────────────────────────────────────────
def parse_response(text: str) -> Optional[dict]:
    """Pull a JSON object out of the LLM response, even if it's wrapped in
    markdown fences or has leading/trailing prose."""
    text = text.strip()

    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the first { ... } block (greedy match)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        print(f"     parse error after extraction: {e}", file=sys.stderr)
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
    """Generate teach data for one tool. Returns parsed+validated dict or None."""
    prompt = build_prompt(tool_key, tool)

    if dry_run:
        print(f"\n──── DRY RUN: prompt for {tool_key} ────")
        print(prompt)
        print(f"──── END {tool_key} ────\n")
        return None

    print(f"  → generating: {tool_key} ... ", end="", flush=True)
    t0 = time.time()
    try:
        raw = backend.generate(prompt, max_tokens=2000)
    except Exception as e:
        print(f"FAIL ({e})")
        return None
    elapsed = time.time() - t0

    data = parse_response(raw)
    if data is None:
        print(f"PARSE FAIL ({elapsed:.1f}s)")
        # Save raw output for debugging
        debug_dir = ROOT / "tools" / "_debug"
        debug_dir.mkdir(exist_ok=True)
        (debug_dir / f"{tool_key}.raw.txt").write_text(raw)
        return None

    valid, errors = validate_generated(data)
    if not valid:
        print(f"INVALID ({elapsed:.1f}s): {errors[0]}")
        debug_dir = ROOT / "tools" / "_debug"
        debug_dir.mkdir(exist_ok=True)
        (debug_dir / f"{tool_key}.invalid.json").write_text(json.dumps(data, indent=2))
        return None

    print(f"✓ ({elapsed:.1f}s)")
    return data


def main():
    parser = argparse.ArgumentParser(description="ERR0RS teach generator (Phase 3)")
    parser.add_argument("--sample", nargs="+", metavar="TOOL",
                        help="Generate only for these tools (quality gate mode)")
    parser.add_argument("--tool", metavar="NAME", help="Generate for one specific tool")
    parser.add_argument("--all", action="store_true",
                        help="Generate for every tool with empty stub fields")
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

    if not any([args.sample, args.tool, args.all, args.dry_run]):
        parser.error("Specify one of --sample, --tool, --all, or --dry-run")

    env = load_env()
    print("=" * 70)
    print(" ERR0RS Teach Generator — Phase 3")
    print("=" * 70)

    # Load registry
    registry_data = json.load(open(REGISTRY))
    tools = registry_data["tools"]
    print(f"\n  registry: {len(tools)} tools loaded")

    # Decide which tools to process
    if args.tool:
        targets = [args.tool.lower()]
    elif args.sample:
        targets = [t.lower() for t in args.sample]
    elif args.all:
        targets = [k for k, t in tools.items() if needs_generation(t)]
    else:
        targets = list(tools.keys())[:1]  # dry-run: just one for demo

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

    # Generate
    print("\n  starting generation...\n")
    for i, tool_key in enumerate(targets, 1):
        if tool_key in generated and not args.dry_run:
            print(f"  ~ skipping {tool_key} (already in {out_path.name})")
            continue
        print(f"  [{i}/{len(targets)}]", end=" ")
        result = generate_for_tool(tool_key, tools[tool_key], backend, args.dry_run)
        if result is not None:
            generated[tool_key] = result
            # Save after EVERY successful generation — protects against crashes
            out_data = {
                "version": "2.0.0",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_registry_version": registry_data.get("version", "unknown"),
                "tools": generated,
            }
            out_path.write_text(json.dumps(out_data, indent=2, ensure_ascii=False))

    if not args.dry_run:
        print(f"\n  ✓ wrote {out_path}")
        print(f"  ✓ {len(generated)} tools have generated teach data")
        print(f"\n  Next: review with `python3 tools/inspect_generated.py`,")
        print(f"        then merge with `python3 tools/merge_generated.py --write`")


if __name__ == "__main__":
    main()
