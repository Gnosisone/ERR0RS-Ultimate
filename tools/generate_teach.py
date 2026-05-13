#!/usr/bin/env python3
"""
ERR0RS — Teach Generator (Phase 3)
══════════════════════════════════
Uses an LLM (Ollama by default, Anthropic API as fallback) to fill in
the 5 stub fields that Phase 2 left empty in tool_registry.v2.json:

  - opsec_notes
  - sample_outputs
  - legal_notes
  - false_positives
  - mitre_attack

Output goes to src/tools/tool_registry.generated.json (a SEPARATE file)
for human review. It is NOT auto-merged into tool_registry.v2.json.

Backends (auto-detected from .env LLM_BACKEND or runtime fallback):
  ollama     — local, free. Default. On Pi 5+Hailo expected ~30-60s/tool.
  anthropic  — Claude API, requires ANTHROPIC_API_KEY, costs money.

Usage:
  python3 tools/generate_teach.py --sample nmap sqlmap hydra
  python3 tools/generate_teach.py --all
  python3 tools/generate_teach.py --tool nmap --backend anthropic
  python3 tools/generate_teach.py --dry-run
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
OUT = ROOT / "src" / "tools" / "tool_registry.generated.json"

TARGET_FIELDS = (
    "opsec_notes", "sample_outputs", "legal_notes",
    "false_positives", "mitre_attack",
)


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
      "output": "Realistic 8-20 line excerpt — REAL formatting, REAL columns, REAL prefixes",
      "explanation": "What the output tells the operator AND the next 2-3 logical actions"
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
   - At least ONE beginner-grade entry: "what is the obvious noise this makes"
   - At least TWO cutting-edge 2025-2026 entries: reference current EDR products,
     modern detection telemetry, recent defensive shifts WHERE TRUTHFUL.
   - At least ONE concrete defender-side artifact: log path, EID, signature.
   - Generic advice like "be careful" is FORBIDDEN.

2. sample_outputs (2 entries, beginner + advanced):
   - First: SIMPLE beginner scenario, single host, default flags.
   - Second: ADVANCED real-world chain.
   - Output column alignment must be REAL.
   - NEVER fabricate CVE numbers — use realistic placeholders.

3. legal_notes (2-3 entries):
   - One US CFAA-grounded boundary specific to this tool.
   - One authorization-scope reminder.
   - One modern-cloud or modern-AD consideration where relevant.

4. false_positives (3-5 entries):
   - Specific, technical gotchas only experienced operators know.

5. mitre_attack (1-4 entries):
   - Real, current ATT&CK IDs in Txxxx or Txxxx.yyy format.
   - Only techniques the tool DIRECTLY enables.
   - Prefer sub-techniques over parent IDs when accurate.

6. HONESTY: When uncertain, use placeholders. Fabricated specifics teach
   wrong things and get students hurt on live engagements.

7. NO MARKDOWN. NO ```json fences. Just the JSON.

Begin JSON output now:
"""


def build_prompt(tool_key: str, tool: dict) -> str:
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


class OllamaBackend:
    """Streams /api/generate with format=json. Times out after stall."""

    def __init__(self, model: str, host: str, timeout: int = 900):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        import urllib.request
        self.urllib = urllib
        self._verify()

    def _verify(self):
        try:
            req = self.urllib.request.Request(f"{self.host}/api/tags")
            with self.urllib.request.urlopen(req, timeout=3) as r:
                data = json.loads(r.read())
                models = [m["name"] for m in data.get("models", [])]
                if self.model not in models:
                    print(f"  ⚠  model {self.model} not pre-pulled, will load on first call")
        except Exception as e:
            raise RuntimeError(f"Ollama at {self.host} unreachable: {e}")

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "format": "json",
            "options": {
                "temperature": 0.3,
                "num_predict": max_tokens,
                "top_p": 0.9,
                "num_ctx": 8192,
            },
        }).encode("utf-8")
        req = self.urllib.request.Request(
            f"{self.host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
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
                    if len(chunks) % 50 == 0:
                        print(".", end="", flush=True)
                if obj.get("done"):
                    break
                if time.time() - last_token_time > 120:
                    raise TimeoutError("generation stalled for 120s")
        return "".join(chunks)


class AnthropicBackend:
    def __init__(self, api_key: str):
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic library not installed in venv")
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        msg = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in msg.content if hasattr(block, "text"))


def parse_response(text: str) -> Optional[dict]:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        print(f"     parse error after extraction: {e}", file=sys.stderr)
        return None


MITRE_PATTERN = re.compile(r"^T[0-9]{4}(\.[0-9]{3})?$")


def validate_generated(data: dict) -> tuple:
    errors = []
    on = data.get("opsec_notes", [])
    if not isinstance(on, list) or not all(isinstance(x, str) for x in on):
        errors.append("opsec_notes must be array of strings")
    elif len(on) == 0:
        errors.append("opsec_notes is empty")
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
    ln = data.get("legal_notes", [])
    if not isinstance(ln, list) or not all(isinstance(x, str) for x in ln):
        errors.append("legal_notes must be array of strings")
    fp = data.get("false_positives", [])
    if not isinstance(fp, list) or not all(isinstance(x, str) for x in fp):
        errors.append("false_positives must be array of strings")
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


def get_backend(prefer: str, env: dict):
    if prefer == "anthropic":
        key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env or environment")
        return AnthropicBackend(key)
    if prefer == "ollama":
        return OllamaBackend(
            model=env.get("OLLAMA_MODEL", "qwen2.5-coder:32b"),
            host=env.get("OLLAMA_HOST", "http://localhost:11434"),
        )
    # auto
    try:
        return OllamaBackend(
            model=env.get("OLLAMA_MODEL", "qwen2.5-coder:32b"),
            host=env.get("OLLAMA_HOST", "http://localhost:11434"),
        )
    except Exception as e:
        print(f"  ⚠  Ollama unavailable ({e}), falling back to Anthropic")
        key = env.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("Both Ollama and Anthropic backends unavailable")
        return AnthropicBackend(key)


def needs_generation(tool: dict) -> bool:
    for field in TARGET_FIELDS:
        val = tool.get(field, [])
        if not val:
            return True
    return False


def generate_for_tool(tool_key: str, tool: dict, backend, dry_run: bool = False) -> Optional[dict]:
    prompt = build_prompt(tool_key, tool)
    if dry_run:
        print(f"\n──── DRY RUN: prompt for {tool_key} ────")
        print(prompt)
        print(f"──── END {tool_key} ────\n")
        return None
    print(f"  → generating: {tool_key} ... ", end="", flush=True)
    t0 = time.time()
    try:
        raw = backend.generate(prompt, max_tokens=2500)
    except Exception as e:
        print(f"FAIL ({e})")
        return None
    elapsed = time.time() - t0
    data = parse_response(raw)
    if data is None:
        print(f"PARSE FAIL ({elapsed:.1f}s)")
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
                        help="Generate only for these tools (quality gate)")
    parser.add_argument("--tool", metavar="NAME", help="Generate for one specific tool")
    parser.add_argument("--all", action="store_true",
                        help="Generate for every tool with empty stub fields")
    parser.add_argument("--backend", choices=["ollama", "anthropic", "auto"],
                        default="auto", help="Which LLM backend to use")
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

    registry_data = json.load(open(REGISTRY))
    tools = registry_data["tools"]
    print(f"\n  registry: {len(tools)} tools loaded")

    if args.tool:
        targets = [args.tool.lower()]
    elif args.sample:
        targets = [t.lower() for t in args.sample]
    elif args.all:
        targets = [k for k, t in tools.items() if needs_generation(t)]
    else:
        targets = list(tools.keys())[:1]

    missing = [t for t in targets if t not in tools]
    if missing:
        print(f"  ✗ unknown tools: {missing}")
        sys.exit(1)

    print(f"  targets: {len(targets)} tools — {', '.join(targets[:6])}"
          + ("..." if len(targets) > 6 else ""))

    if args.dry_run:
        backend = None
        print("\n  (dry-run — no LLM calls)")
    else:
        try:
            backend = get_backend(args.backend, env)
            backend_name = type(backend).__name__
            print(f"  backend: {backend_name}")
            if isinstance(backend, OllamaBackend):
                print(f"  model:   {backend.model}")
        except Exception as e:
            print(f"  ✗ backend init failed: {e}")
            sys.exit(2)

    out_path = Path(args.out)
    if out_path.exists():
        existing = json.load(open(out_path))
        generated = existing.get("tools", {})
        print(f"  resuming: {len(generated)} entries already in {out_path.name}")
    else:
        generated = {}

    print("\n  starting generation...\n")
    for i, tool_key in enumerate(targets, 1):
        if tool_key in generated and not args.dry_run:
            print(f"  ~ skipping {tool_key} (already in {out_path.name})")
            continue
        print(f"  [{i}/{len(targets)}]", end=" ")
        result = generate_for_tool(tool_key, tools[tool_key], backend, args.dry_run)
        if result is not None:
            generated[tool_key] = result
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


if __name__ == "__main__":
    main()
