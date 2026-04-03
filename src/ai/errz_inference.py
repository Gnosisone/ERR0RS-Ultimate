#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Inference Layer v1.0
=======================================
This IS the ERR0RS AI engine. Not Ollama. Not llama.cpp.
Those are just pipes. THIS is the brain.

The architecture that makes ERR0RS its own AI system:

  ┌──────────────────────────────────────────────────────────┐
  │                   ERR0RS INFERENCE LAYER                  │
  │                                                          │
  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
  │  │  INTENT     │  │  CONTEXT     │  │  PERSONA       │  │
  │  │  CLASSIFIER │→ │  BUILDER     │→ │  INJECTOR      │  │
  │  │             │  │              │  │                │  │
  │  │ Figures out │  │ Pulls from   │  │ Wraps prompt   │  │
  │  │ WHAT you    │  │ scan history,│  │ in specialized │  │
  │  │ need        │  │ KB, CVE DB,  │  │ system prompt  │  │
  │  │             │  │ MITRE ATT&CK │  │                │  │
  │  └─────────────┘  └──────────────┘  └────────────────┘  │
  │         ↓                                   ↓            │
  │  ┌─────────────────────────────────────────────────────┐ │
  │  │              BACKEND ROUTER                         │ │
  │  │  Ollama (local) → llama.cpp direct → Pi Hailo NPU  │ │
  │  │  Any backend. Swap without changing anything above. │ │
  │  └─────────────────────────────────────────────────────┘ │
  │         ↓                                                 │
  │  ┌─────────────────────────────────────────────────────┐ │
  │  │              RESPONSE PROCESSOR                      │ │
  │  │  Parses output → Extracts commands → Formats for UI │ │
  │  │  Feeds into teach engine, report gen, intel feed    │ │
  │  └─────────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────────┘

The model file (.gguf) is just weights. THIS layer is the expertise.
Change the backend: behavior stays the same.
Change the persona: backend stays the same.
Everything is owned by ERR0RS.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import json, time, hashlib, subprocess, shutil
from pathlib import Path
from typing import Optional, Generator
import urllib.request

ROOT_DIR  = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT_DIR / "models"          # local .gguf files go here
CACHE_DIR = ROOT_DIR / ".errz_cache"    # response cache

MODEL_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


# ─── Backend detection ────────────────────────────────────────────────────────
# ERR0RS figures out what's available and uses the best option.
# Priority: llama.cpp direct > Ollama > LM Studio > fallback

def detect_backend() -> dict:
    """
    Auto-detect which inference backend is available.
    Returns the best one with its connection details.
    Priority: Hailo NPU > llama.cpp > Ollama > LM Studio > fallback
    """
    backends = []

    # 0. Hailo-10H NPU via hailo-ollama (Pi 5 — highest priority)
    try:
        from src.ai.hailo_npu import HailoDetector, HAILO_OLLAMA_URL
        det = HailoDetector.detect()
        if det["hailo_found"] and det["hailo_ollama"]:
            backends.append({
                "name":     "hailo_npu",
                "url":      HAILO_OLLAMA_URL,
                "type":     "hailo_ollama",
                "chip":     det.get("chip", "Hailo-10H"),
                "firmware": det.get("firmware_version"),
                "models":   det.get("hailo_ollama_models", []),
                "priority": 0,
            })
    except Exception:
        pass

    # 1. llama.cpp server (direct — fastest, no middleman)
    try:
        r = urllib.request.urlopen("http://localhost:8080/health", timeout=1)
        if r.status == 200:
            backends.append({
                "name": "llama.cpp",
                "url":  "http://localhost:8080",
                "type": "llamacpp",
                "priority": 1,
            })
    except Exception:
        pass

    # 2. Ollama (most common)
    try:
        r = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        data = json.loads(r.read())
        models = [m["name"] for m in data.get("models", [])]
        if models:
            backends.append({
                "name":    "ollama",
                "url":     "http://localhost:11434",
                "type":    "ollama",
                "models":  models,
                "priority": 2,
            })
    except Exception:
        pass

    # 3. LM Studio
    try:
        r = urllib.request.urlopen("http://localhost:1234/v1/models", timeout=1)
        backends.append({
            "name": "lmstudio",
            "url":  "http://localhost:1234",
            "type": "openai_compat",
            "priority": 3,
        })
    except Exception:
        pass

    # Sort by priority and return best
    backends.sort(key=lambda x: x["priority"])
    return backends[0] if backends else {"name": "none", "type": "none"}


# ─── Response cache ───────────────────────────────────────────────────────────
# ERR0RS caches responses locally. Same question = instant answer.
# Especially useful for CVE lookups and tool explanations asked repeatedly.

class ResponseCache:
    """Disk-backed response cache. Survives restarts."""

    def __init__(self, cache_dir: Path = CACHE_DIR, ttl_hours: int = 24):
        self.cache_dir = cache_dir
        self.ttl_secs  = ttl_hours * 3600

    def _key(self, prompt: str, mode: str, model: str) -> str:
        raw = f"{mode}:{model}:{prompt}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, prompt: str, mode: str, model: str) -> Optional[str]:
        path = self.cache_dir / f"{self._key(prompt, mode, model)}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            if time.time() - data["ts"] > self.ttl_secs:
                path.unlink(missing_ok=True)
                return None
            return data["response"]
        except Exception:
            return None

    def set(self, prompt: str, mode: str, model: str, response: str):
        path = self.cache_dir / f"{self._key(prompt, mode, model)}.json"
        path.write_text(json.dumps({"ts": time.time(), "response": response}))

    def clear(self):
        for f in self.cache_dir.glob("*.json"):
            f.unlink(missing_ok=True)

    def stats(self) -> dict:
        files = list(self.cache_dir.glob("*.json"))
        return {"entries": len(files), "size_kb": sum(f.stat().st_size for f in files) // 1024}


# ─── Context builder ──────────────────────────────────────────────────────────
# This is what makes ERR0RS smarter than raw Ollama.
# We enrich every prompt with relevant context before sending it.

class ContextBuilder:
    """
    Enriches prompts with ERR0RS-specific context.
    This is the secret sauce — the model gets better answers
    because we feed it relevant structured context, not just raw user text.
    """

    def __init__(self, root: Path = ROOT_DIR):
        self.root = root

    def build(self, prompt: str, mode: str, extras: dict = None) -> str:
        """Build an enriched prompt with relevant context injected."""
        parts = []

        # 1. Session context (what has been scanned/found this session)
        session_ctx = self._get_session_context()
        if session_ctx:
            parts.append(f"CURRENT ENGAGEMENT CONTEXT:\n{session_ctx}")

        # 2. CVE context if the prompt mentions a CVE
        cve_ctx = self._get_cve_context(prompt)
        if cve_ctx:
            parts.append(f"KNOWN CVE DATA:\n{cve_ctx}")

        # 3. MITRE context if attack planning
        if mode == "red_team":
            parts.append(self._get_mitre_context())

        # 4. Tool-specific context if a known tool is mentioned
        tool_ctx = self._get_tool_context(prompt)
        if tool_ctx:
            parts.append(f"TOOL REFERENCE:\n{tool_ctx}")

        # 5. Extra context passed in (scan output, target info, etc.)
        if extras:
            for key, val in extras.items():
                if val:
                    parts.append(f"{key.upper()}:\n{val}")

        # Assemble
        if parts:
            context_block = "\n\n".join(parts)
            return f"{context_block}\n\n---\n\nUSER REQUEST:\n{prompt}"
        return prompt

    def _get_session_context(self) -> str:
        """Pull relevant findings from the current session if available."""
        session_file = self.root / ".errz_session.json"
        if not session_file.exists():
            return ""
        try:
            data = json.loads(session_file.read_text())
            findings = data.get("findings", [])[:5]  # top 5 recent findings
            if findings:
                return "Recent findings:\n" + "\n".join(f"  - {f}" for f in findings)
        except Exception:
            pass
        return ""

    def _get_cve_context(self, prompt: str) -> str:
        """Pull CVE data from local KB if prompt mentions a CVE."""
        import re
        cves = re.findall(r'CVE-\d{4}-\d+', prompt, re.IGNORECASE)
        if not cves:
            return ""
        # Check local CVE database
        cve_db = self.root / "src" / "ai" / "data" / "cve_db.json"
        if not cve_db.exists():
            return ""
        try:
            db = json.loads(cve_db.read_text())
            results = []
            for cve in cves:
                entry = db.get(cve.upper())
                if entry:
                    results.append(
                        f"{cve}: CVSS {entry.get('cvss', 'N/A')} — {entry.get('description', '')[:200]}"
                    )
            return "\n".join(results)
        except Exception:
            return ""

    def _get_mitre_context(self) -> str:
        """Inject MITRE ATT&CK context for red team planning."""
        return (
            "MITRE ATT&CK phases to consider:\n"
            "  TA0001 Initial Access → TA0002 Execution → TA0003 Persistence\n"
            "  TA0004 Privilege Escalation → TA0005 Defense Evasion\n"
            "  TA0006 Credential Access → TA0007 Discovery → TA0008 Lateral Movement\n"
            "  TA0009 Collection → TA0010 Exfiltration → TA0011 Command & Control"
        )

    def _get_tool_context(self, prompt: str) -> str:
        """Add relevant tool flags/context if a known tool is mentioned."""
        TOOL_HINTS = {
            "nmap": "Key flags: -sV (version), -sC (scripts), -p- (all ports), -A (aggressive), --script vuln",
            "sqlmap": "Key flags: --batch, --dbs, -D db -T table --dump, --os-shell, --tamper=space2comment",
            "hydra": "Key flags: -l user, -L users.txt, -P pass.txt, -t 4 (threads), protocol://target",
            "gobuster": "Modes: dir, dns, vhost. Key flags: -w wordlist, -x extensions, -t threads",
            "metasploit": "Workflow: search → use → show options → set RHOSTS → set PAYLOAD → run",
            "hashcat": "Key modes: -m 0 (MD5), -m 1000 (NTLM), -m 3200 (bcrypt), -m 22000 (WPA2)",
        }
        lower = prompt.lower()
        for tool, hint in TOOL_HINTS.items():
            if tool in lower:
                return hint
        return ""


# ─── Response processor ───────────────────────────────────────────────────────
# Takes raw LLM output and makes it actionable.
# Extracts commands, findings, CVEs, severity levels.

class ResponseProcessor:
    """
    Post-processes raw model output into structured ERR0RS data.
    This is what makes the output actually USEFUL vs just raw text.
    """

    @staticmethod
    def extract_commands(text: str) -> list:
        """Pull all shell commands from markdown code blocks."""
        import re
        # Match ```bash, ```sh, or plain ``` blocks
        pattern = r'```(?:bash|sh|shell|zsh|cmd)?\n?(.*?)```'
        commands = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        # Also match $ or # prefixed inline commands
        inline   = re.findall(r'(?:^|\n)\s*[$#]\s+(.+)', text)
        all_cmds = []
        for block in commands:
            for line in block.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    all_cmds.append(line)
        all_cmds.extend(inline)
        return list(dict.fromkeys(all_cmds))  # deduplicate preserving order

    @staticmethod
    def extract_severity(text: str) -> str:
        """Determine highest severity mentioned in response."""
        text_lower = text.lower()
        for level in ["critical", "high", "medium", "low", "informational"]:
            if level in text_lower:
                return level.upper()
        return "UNKNOWN"

    @staticmethod
    def extract_cves(text: str) -> list:
        """Pull all CVE identifiers from response."""
        import re
        return list(set(re.findall(r'CVE-\d{4}-\d+', text, re.IGNORECASE)))

    @staticmethod
    def extract_mitre_ttps(text: str) -> list:
        """Pull all MITRE ATT&CK technique IDs from response."""
        import re
        return list(set(re.findall(r'T\d{4}(?:\.\d{3})?', text)))

    @staticmethod
    def format_for_terminal(text: str, mode: str, icon: str) -> str:
        """Format response for the ERR0RS terminal UI."""
        separator = "─" * 54
        header    = f"[{icon} ERR0RS // {mode.upper().replace('_', ' ')}]"
        return f"\n{separator}\n{header}\n{separator}\n{text}\n{separator}"


# ─── Core inference engine ────────────────────────────────────────────────────

class ERRZInference:
    """
    The ERR0RS inference engine.

    This is NOT Ollama. This is NOT llama.cpp.
    This is the layer ABOVE those that gives ERR0RS its intelligence.

    Backends are interchangeable. The intelligence layer is ours.
    """

    def __init__(self):
        self.cache    = ResponseCache()
        self.context  = ContextBuilder()
        self.proc     = ResponseProcessor()
        self._backend = None          # lazy-initialized

    @property
    def backend(self) -> dict:
        if self._backend is None:
            self._backend = detect_backend()
        return self._backend

    def infer(self, prompt: str, system: str, mode: str,
              model: str = "llama3.2", use_cache: bool = True,
              extras: dict = None) -> dict:
        """
        Core inference call.
        1. Check cache
        2. Build enriched context
        3. Send to detected backend
        4. Process response
        5. Cache result
        6. Return structured output
        """
        # Cache check
        if use_cache:
            cached = self.cache.get(prompt, mode, model)
            if cached:
                cmds = self.proc.extract_commands(cached)
                return {
                    "status":    "success",
                    "response":  cached,
                    "commands":  cmds,
                    "cves":      self.proc.extract_cves(cached),
                    "ttps":      self.proc.extract_mitre_ttps(cached),
                    "severity":  self.proc.extract_severity(cached),
                    "cached":    True,
                    "backend":   "cache",
                    "latency_ms": 0,
                }

        # Build enriched prompt
        enriched = self.context.build(prompt, mode, extras)

        # Route to backend
        backend = self.backend
        if backend["type"] == "none":
            return self._offline_fallback(prompt, mode)

        start = time.time()
        raw   = self._call_backend(backend, enriched, system, model)
        ms    = int((time.time() - start) * 1000)

        if raw["status"] != "success":
            return raw

        response = raw["response"]

        # Cache it
        if use_cache:
            self.cache.set(prompt, mode, model, response)

        # Process and return
        return {
            "status":    "success",
            "response":  response,
            "commands":  self.proc.extract_commands(response),
            "cves":      self.proc.extract_cves(response),
            "ttps":      self.proc.extract_mitre_ttps(response),
            "severity":  self.proc.extract_severity(response),
            "cached":    False,
            "backend":   backend["name"],
            "latency_ms": ms,
        }

    def _call_backend(self, backend: dict, prompt: str,
                      system: str, model: str) -> dict:
        """Route to the appropriate backend API."""
        btype = backend["type"]

        if btype == "hailo_ollama":
            # Route through Hailo NPU via hailo-ollama server
            from src.ai.hailo_npu import HailoOllamaClient
            client = HailoOllamaClient(base_url=backend["url"])
            # Use best available Hailo model — not the standard Ollama model
            hailo_model = (backend.get("models") or ["qwen2.5-coder-1.5b-instruct"])[0]
            return client.generate(prompt=prompt, system=system, model=hailo_model)
        elif btype == "ollama":
            return self._call_ollama(backend["url"], prompt, system, model)
        elif btype in ("openai_compat", "llamacpp"):
            return self._call_openai_compat(backend["url"], prompt, system, model)
        else:
            return {"status": "error", "response": f"Unknown backend: {btype}"}

    def _call_ollama(self, url: str, prompt: str,
                     system: str, model: str) -> dict:
        """Call Ollama's native API."""
        body = json.dumps({
            "model":   model,
            "system":  system,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": 0.2, "num_predict": 2048},
        }).encode()
        try:
            req = urllib.request.Request(
                f"{url}/api/generate", data=body,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
                return {"status": "success", "response": data.get("response", "")}
        except Exception as e:
            return {"status": "error", "response": str(e)}

    def _call_openai_compat(self, url: str, prompt: str,
                             system: str, model: str) -> dict:
        """Call any OpenAI-compatible API (LM Studio, llama.cpp server, etc.)"""
        body = json.dumps({
            "model":    model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens":  2048,
            "stream":      False,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{url}/v1/chat/completions", data=body,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read())
                return {
                    "status":   "success",
                    "response": data["choices"][0]["message"]["content"]
                }
        except Exception as e:
            return {"status": "error", "response": str(e)}

    def _offline_fallback(self, prompt: str, mode: str) -> dict:
        """
        When NO backend is available, ERR0RS still works.
        Falls back to the built-in teach engine knowledge base.
        """
        from src.education.teach_engine import handle_teach_request
        result = handle_teach_request(prompt)
        if result.get("status") == "success":
            return {
                "status":    "success",
                "response":  result["stdout"],
                "commands":  [],
                "cves":      [],
                "ttps":      [],
                "severity":  "UNKNOWN",
                "cached":    False,
                "backend":   "errz_builtin",
                "latency_ms": 0,
                "note":      "Offline mode — using built-in ERR0RS knowledge base",
            }
        return {
            "status":   "error",
            "response": (
                "[ERR0RS Brain] No inference backend available.\n\n"
                "To activate the AI brain, start any of these:\n"
                "  • Ollama:    sudo systemctl start ollama\n"
                "  • LM Studio: open LM Studio and load a model\n"
                "  • llama.cpp: ./server -m models/your-model.gguf\n\n"
                "ERR0RS works offline with the built-in teach engine.\n"
                "Type 'teach me [tool]' for offline lessons."
            ),
            "backend":  "none",
        }

    def status(self) -> dict:
        """Full status report of the inference layer."""
        backend = self.backend
        cache   = self.cache.stats()
        return {
            "inference_layer": "ERR0RS Native (v1.0)",
            "backend":         backend,
            "cache":           cache,
            "offline_mode":    backend["type"] == "none",
            "note": (
                "ERR0RS owns the intelligence layer. "
                "The backend is just a pipe — swap it without changing anything."
            ),
        }

    def clear_cache(self):
        self.cache.clear()


# ─── Global instance ──────────────────────────────────────────────────────────
_engine: Optional[ERRZInference] = None

def get_engine() -> ERRZInference:
    global _engine
    if _engine is None:
        _engine = ERRZInference()
    return _engine
