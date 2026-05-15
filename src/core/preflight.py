"""
ERR0RS Preflight — startup health checks that run before anything else.

Checks:
  1. Critical Python dependencies present
  2. SECRET_KEY is not the default placeholder
  3. Ollama reachability (blocking, 5-second timeout)
  4. Core security tools on PATH

All checks print clear, actionable messages to stdout.
Returns True only if everything critical passed.
"""

import os
import sys
import shutil
import subprocess
import importlib

# ── ANSI colours (no deps required) ─────────────────────────────────────────
_G  = "\033[92m"   # green
_Y  = "\033[93m"   # yellow
_R  = "\033[91m"   # red
_C  = "\033[96m"   # cyan
_B  = "\033[1m"    # bold
_N  = "\033[0m"    # reset

_OK   = f"{_G}✓{_N}"
_WARN = f"{_Y}⚠{_N}"
_FAIL = f"{_R}✗{_N}"


# ── 1. Python dependency check ───────────────────────────────────────────────
CRITICAL_DEPS = [
    ("requests",     "pip install requests"),
    ("dotenv",       "pip install python-dotenv",    "dotenv"),
    ("websockets",   "pip install websockets"),
]
OPTIONAL_DEPS = [
    ("chromadb",     "pip install chromadb",         "chromadb"),
    ("anthropic",    "pip install anthropic"),
    ("openai",       "pip install openai"),
    ("flask",        "pip install flask"),
    ("flask_socketio","pip install flask-socketio",  "flask_socketio"),
]

def check_python_deps() -> tuple[bool, list[str]]:
    """Returns (all_critical_ok, list_of_warnings)."""
    warnings = []
    ok = True
    for item in CRITICAL_DEPS:
        pkg, fix = item[0], item[1]
        import_name = item[2] if len(item) > 2 else pkg
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"  {_FAIL} Missing critical package: {_B}{pkg}{_N}  →  {_C}{fix}{_N}")
            ok = False

    for item in OPTIONAL_DEPS:
        pkg, fix = item[0], item[1]
        import_name = item[2] if len(item) > 2 else pkg
        try:
            importlib.import_module(import_name)
        except ImportError:
            warnings.append(f"{pkg} not installed ({fix}) — some features disabled")

    return ok, warnings


# ── 2. SECRET_KEY guard ──────────────────────────────────────────────────────
INSECURE_KEYS = {"changeme_replace_with_generated_key", "changeme", "secret", ""}

def check_secret_key() -> bool:
    """Warn loudly if SECRET_KEY is still the default. Never blocks boot."""
    key = os.environ.get("SECRET_KEY", "").strip()
    if key.lower() in INSECURE_KEYS or not key:
        print(f"  {_WARN} {_B}SECRET_KEY{_N} is not set or uses the default placeholder.")
        print(f"     Generate one:  {_C}python3 -c \"import secrets; print(secrets.token_hex(32))\"{_N}")
        print(f"     Then add it to your .env file.")
        return False
    return True


# ── 3. Ollama reachability check ─────────────────────────────────────────────
def check_ollama(host: str = None, timeout: int = 5) -> bool:
    """
    Blocking check — waits up to `timeout` seconds.
    Returns True if Ollama is up, False otherwise.
    """
    host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    try:
        import requests
        resp = requests.get(f"{host}/api/tags", timeout=timeout)
        if resp.ok:
            models = [m["name"] for m in resp.json().get("models", [])]
            if models:
                print(f"  {_OK} Ollama running — models: {_C}{', '.join(models[:4])}{_N}")
            else:
                print(f"  {_WARN} Ollama running but {_B}no models pulled{_N}.")
                model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")
                print(f"     Pull one:  {_C}ollama pull {model}{_N}")
            return True
        else:
            _print_ollama_down(host)
            return False
    except Exception:
        _print_ollama_down(host)
        return False

def _print_ollama_down(host: str):
    print(f"  {_FAIL} Ollama not reachable at {_B}{host}{_N}")
    print(f"     Start it:   {_C}ollama serve{_N}  (in a separate terminal)")
    print(f"     Or install: {_C}curl https://ollama.ai/install.sh | sh{_N}")
    print(f"     {_Y}ERR0RS will run but LLM features will be unavailable.{_N}")


# ── 4. Security tools on PATH ─────────────────────────────────────────────────
CORE_TOOLS = ["nmap", "sqlmap", "nikto", "gobuster", "hydra", "hashcat"]
NICE_TOOLS  = ["metasploit", "enum4linux", "crackmapexec", "ffuf", "nuclei",
               "bloodhound", "responder", "impacket-scripts"]

def check_security_tools() -> tuple[int, int]:
    """Returns (found_core, found_nice)."""
    missing_core = []
    for tool in CORE_TOOLS:
        if not shutil.which(tool):
            missing_core.append(tool)

    if missing_core:
        print(f"  {_WARN} Core tools not on PATH: {_Y}{', '.join(missing_core)}{_N}")
        print(f"     Install:  {_C}sudo apt install {' '.join(missing_core)}{_N}")
    else:
        print(f"  {_OK} Core security tools present ({', '.join(CORE_TOOLS)})")

    found_nice = sum(1 for t in NICE_TOOLS if shutil.which(t))
    return len(CORE_TOOLS) - len(missing_core), found_nice


# ── Master preflight runner ───────────────────────────────────────────────────
def run(check_ollama_flag: bool = True, verbose: bool = True) -> bool:
    """
    Run all preflight checks. Print results. Return True if critical checks pass.
    Call this early in main() before loading heavy subsystems.
    """
    if verbose:
        print(f"\n{_B}{'─'*54}{_N}")
        print(f"  {_C}{_B}ERR0RS PRE-FLIGHT CHECKS{_N}")
        print(f"{_B}{'─'*54}{_N}")

    critical_ok = True

    # 1. Python deps
    deps_ok, dep_warnings = check_python_deps()
    if not deps_ok:
        critical_ok = False

    # 2. SECRET_KEY
    check_secret_key()   # warn-only, never blocks

    # 3. Ollama
    if check_ollama_flag:
        backend = os.environ.get("LLM_BACKEND", "ollama").lower()
        if backend == "ollama":
            check_ollama()
        else:
            print(f"  {_OK} LLM backend: {_C}{backend}{_N} (Ollama check skipped)")

    # 4. Security tools
    check_security_tools()

    # Optional dep warnings (non-blocking)
    if dep_warnings and verbose:
        print(f"\n  {_Y}Optional features unavailable:{_N}")
        for w in dep_warnings:
            print(f"    • {w}")

    if verbose:
        print(f"{_B}{'─'*54}{_N}\n")

    return critical_ok
