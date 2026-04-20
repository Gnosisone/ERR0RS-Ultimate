#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           ERR0RS ULTIMATE — PHOENIX-OS BRIDGE MODULE            ║
║                  src/core/phoenix_bridge.py                     ║
║                                                                  ║
║  Integrates Phoenix-OS's full BlackArch arsenal (2,079+ tools)  ║
║  into ERR0RS — discovery, execution, RAG-aware tool routing.    ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import shutil
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
PHOENIX_ROOT   = Path("/home/kali/Phoenix-OS")
BLACKARCH_DIR  = Path("/opt/blackarch")
PHOENIX_TOOLS_PATH = PHOENIX_ROOT / "src" / "tools"

# ── Import Phoenix registry if available ──────────────────────────────────────
PHOENIX_REGISTRY: Dict[str, Any] = {}

def _load_phoenix_registry() -> Dict[str, Any]:
    global PHOENIX_REGISTRY
    if PHOENIX_REGISTRY:
        return PHOENIX_REGISTRY
    try:
        import importlib.util
        reg_path = PHOENIX_ROOT / "src" / "tools" / "registry.py"
        spec = importlib.util.spec_from_file_location("phoenix_registry", str(reg_path))
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        PHOENIX_REGISTRY = mod.TOOL_REGISTRY
        logger.info(f"[PhoenixBridge] Loaded {len(PHOENIX_REGISTRY)} tools from Phoenix registry")
    except Exception as e:
        logger.warning(f"[PhoenixBridge] Could not load Phoenix registry: {e}")
        PHOENIX_REGISTRY = {}
    return PHOENIX_REGISTRY


# ── Discover ALL tools in /opt/blackarch ──────────────────────────────────────
_BLACKARCH_CACHE: Optional[List[Dict[str, Any]]] = None
_CACHE_LOCK = threading.Lock()

def discover_blackarch_tools(force: bool = False) -> List[Dict[str, Any]]:
    """
    Scans /opt/blackarch and returns a list of tool dicts.
    Cached after first call.
    """
    global _BLACKARCH_CACHE
    with _CACHE_LOCK:
        if _BLACKARCH_CACHE is not None and not force:
            return _BLACKARCH_CACHE

        tools = []
        if not BLACKARCH_DIR.exists():
            logger.warning(f"[PhoenixBridge] {BLACKARCH_DIR} not found")
            _BLACKARCH_CACHE = []
            return []

        for tool_dir in sorted(BLACKARCH_DIR.iterdir()):
            if not tool_dir.is_dir():
                continue
            name = tool_dir.name
            entry = _probe_tool(name, tool_dir)
            if entry:
                tools.append(entry)

        _BLACKARCH_CACHE = tools
        logger.info(f"[PhoenixBridge] Discovered {len(tools)} BlackArch tools")
        return tools


def _probe_tool(name: str, tool_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Figures out how to invoke a tool from its directory.
    Returns a tool dict or None if unexecutable.
    """
    # Priority: wrapper in /usr/local/bin > main entry point in dir
    wrapper = shutil.which(name)
    
    # Find entry point
    candidates = [
        tool_dir / name,
        tool_dir / f"{name}.py",
        tool_dir / "main.py",
        tool_dir / f"{name}.sh",
        tool_dir / "run.py",
        tool_dir / "run.sh",
        tool_dir / f"{name}.rb",
        tool_dir / f"{name}.pl",
    ]
    entry = None
    for c in candidates:
        if c.exists():
            entry = c
            break

    if not wrapper and not entry:
        return None

    # Detect language
    lang = "unknown"
    if entry:
        suffix_map = {".py": "python3", ".rb": "ruby", ".pl": "perl",
                      ".sh": "bash", ".js": "node"}
        lang = suffix_map.get(entry.suffix, "binary")
        if lang == "binary" or lang == "unknown":
            # Try shebang
            try:
                first = entry.read_text(errors="ignore").splitlines()[0]
                if "python" in first:   lang = "python3"
                elif "ruby" in first:   lang = "ruby"
                elif "perl" in first:   lang = "perl"
                elif "node" in first:   lang = "node"
                elif "bash" in first or "sh" in first: lang = "bash"
            except Exception:
                pass

    # Check for README to grab description
    desc = f"BlackArch tool: {name}"
    for readme in [tool_dir/"README.md", tool_dir/"README", tool_dir/"README.txt"]:
        if readme.exists():
            try:
                lines = readme.read_text(errors="ignore").strip().splitlines()
                # Grab first non-empty, non-header line
                for ln in lines[:15]:
                    ln = ln.strip().lstrip("#").strip()
                    if ln and len(ln) > 8 and not ln.startswith("http"):
                        desc = ln[:120]
                        break
            except Exception:
                pass
            break

    invoke = wrapper or (f"{lang} {entry}" if lang not in ("binary","unknown") else str(entry))

    return {
        "name":        name,
        "path":        str(tool_dir),
        "invoke":      invoke,
        "lang":        lang,
        "wrapper":     bool(wrapper),
        "description": desc,
        "source":      "blackarch",
    }


# ── Unified tool catalog ───────────────────────────────────────────────────────

def get_all_tools() -> Dict[str, Any]:
    """
    Returns the merged catalog:
    - Phoenix registry (92 curated tools with full metadata)
    - BlackArch discovered tools (2,079+ from /opt/blackarch)
    """
    catalog = {}

    # 1. Phoenix registry (has full triggers, phases, docs)
    phoenix = _load_phoenix_registry()
    for name, info in phoenix.items():
        catalog[name] = {**info, "source": "phoenix_registry"}

    # 2. BlackArch tools (supplementary)
    for tool in discover_blackarch_tools():
        name = tool["name"]
        if name not in catalog:   # don't overwrite curated entries
            catalog[name] = tool

    return catalog


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """Filter tool catalog by phase/category."""
    all_t = get_all_tools()
    cat_l = category.lower()
    results = []
    for name, info in all_t.items():
        phase = info.get("phase", "").lower()
        cat   = info.get("category", "").lower()
        desc  = info.get("description", "").lower()
        if cat_l in phase or cat_l in cat or cat_l in desc:
            results.append({**info, "name": name})
    return results


def search_tools(query: str) -> List[Dict[str, Any]]:
    """NLP-style tool search across names, descriptions, triggers."""
    all_t = get_all_tools()
    q = query.lower().split()
    scored = []
    for name, info in all_t.items():
        text = " ".join([
            name,
            info.get("description", ""),
            info.get("phase", ""),
            info.get("category", ""),
            " ".join(info.get("triggers", [])),
        ]).lower()
        score = sum(1 for word in q if word in text)
        if score > 0:
            scored.append((score, {**info, "name": name}))
    scored.sort(key=lambda x: -x[0])
    return [t for _, t in scored[:20]]


# ── Tool execution ─────────────────────────────────────────────────────────────

class PhoenixToolResult:
    def __init__(self, tool: str, command: str, stdout: str, stderr: str,
                 returncode: int, duration: float, success: bool):
        self.tool = tool
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration
        self.success = success

    def to_dict(self):
        return {
            "tool": self.tool,
            "command": self.command,
            "stdout": self.stdout[:8000],   # cap for API response
            "stderr": self.stderr[:2000],
            "returncode": self.returncode,
            "duration": round(self.duration, 2),
            "success": self.success,
        }

    def summary(self) -> str:
        status = "✅" if self.success else f"❌ (rc={self.returncode})"
        preview = "\n".join(self.stdout.strip().splitlines()[:30])
        return f"[{self.tool}] {status} | {self.duration:.1f}s\n{preview}"


def run_tool(tool_name: str, args: list, timeout: int = 300,
             stream_cb=None) -> PhoenixToolResult:
    """
    Execute a BlackArch/Phoenix tool by name.
    Looks up the invoke path, builds subprocess args.
    """
    catalog = get_all_tools()
    info    = catalog.get(tool_name)

    if info:
        invoke = info.get("invoke", tool_name)
        # If it's a Python/Ruby/etc script, split cleanly
        cmd_parts = invoke.split() + [str(a) for a in args]
    else:
        # Try raw binary fallback
        binary = shutil.which(tool_name)
        if binary:
            cmd_parts = [binary] + [str(a) for a in args]
        else:
            return PhoenixToolResult(
                tool=tool_name, command=tool_name,
                stdout="", stderr=f"Tool '{tool_name}' not found in PATH or /opt/blackarch",
                returncode=-1, duration=0.0, success=False
            )

    cmd_str = " ".join(cmd_parts)
    t_start = time.time()
    stdout_buf = []
    stderr_buf = []

    try:
        proc = subprocess.Popen(
            cmd_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PATH": f"/usr/local/bin:/opt/blackarch:/usr/bin:/bin:{os.environ.get('PATH','')}"},
        )

        def _drain(stream, buf, label):
            for line in stream:
                line = line.rstrip()
                buf.append(line)
                if stream_cb:
                    try:
                        stream_cb(f"[{label}] {line}")
                    except Exception:
                        pass

        t_out = threading.Thread(target=_drain, args=(proc.stdout, stdout_buf, "OUT"), daemon=True)
        t_err = threading.Thread(target=_drain, args=(proc.stderr, stderr_buf, "ERR"), daemon=True)
        t_out.start(); t_err.start()

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stderr_buf.append(f"TIMEOUT: killed after {timeout}s")

        t_out.join(timeout=5)
        t_err.join(timeout=5)

    except Exception as e:
        return PhoenixToolResult(
            tool=tool_name, command=cmd_str,
            stdout="", stderr=str(e),
            returncode=-1, duration=time.time() - t_start, success=False
        )

    rc = proc.returncode if proc.returncode is not None else -1
    return PhoenixToolResult(
        tool=tool_name,
        command=cmd_str,
        stdout="\n".join(stdout_buf),
        stderr="\n".join(stderr_buf),
        returncode=rc,
        duration=time.time() - t_start,
        success=(rc == 0),
    )


# ── Prebuilt Juice Shop attack kit ────────────────────────────────────────────

JUICE_SHOP_TARGET = "localhost:3000"
JUICE_SHOP_URL    = f"http://{JUICE_SHOP_TARGET}"

JUICE_SHOP_KILLCHAIN = [
    {
        "phase": "recon",
        "tool": "whatweb",
        "args": [JUICE_SHOP_URL, "-a3"],
        "description": "Fingerprint tech stack — Node.js, Angular, Express version detection",
    },
    {
        "phase": "recon",
        "tool": "nikto",
        "args": ["-h", JUICE_SHOP_URL, "-C", "all"],
        "description": "Web server vuln scan — dangerous files, misconfigs, outdated software",
    },
    {
        "phase": "scanning",
        "tool": "gobuster",
        "args": ["dir", "-u", JUICE_SHOP_URL,
                 "-w", "/usr/share/wordlists/dirb/common.txt",
                 "-t", "30", "-q"],
        "description": "Directory enumeration — find hidden endpoints and API routes",
    },
    {
        "phase": "scanning",
        "tool": "nuclei",
        "args": ["-u", JUICE_SHOP_URL, "-tags", "owasp,xss,sqli,lfi,rce",
                 "-severity", "medium,high,critical", "-silent"],
        "description": "Template-based vuln scan — OWASP Top 10 detection",
    },
    {
        "phase": "exploitation",
        "tool": "sqlmap",
        "args": ["-u", f"{JUICE_SHOP_URL}/rest/products/search?q=1",
                 "--batch", "--level=3", "--risk=2",
                 "--dbs", "--output-dir=/tmp/err0rs_sqlmap"],
        "description": "SQL injection test on /rest/products/search endpoint (known vuln)",
    },
    {
        "phase": "exploitation",
        "tool": "dalfox",
        "args": ["url", f"{JUICE_SHOP_URL}/rest/products/search?q=test",
                 "--skip-bav", "--no-spinner"],
        "description": "XSS parameter fuzzing — finds reflected/stored XSS vectors",
    },
]


def get_juice_shop_killchain() -> List[Dict[str, Any]]:
    """Returns the pre-built Juice Shop attack chain for ERR0RS UI."""
    return JUICE_SHOP_KILLCHAIN


def run_juice_shop_phase(phase_name: str, stream_cb=None) -> List[PhoenixToolResult]:
    """Run all tools in a specific kill chain phase against Juice Shop."""
    results = []
    for step in JUICE_SHOP_KILLCHAIN:
        if step["phase"] == phase_name:
            result = run_tool(step["tool"], step["args"], timeout=180, stream_cb=stream_cb)
            results.append(result)
    return results


# ── Status / health check ─────────────────────────────────────────────────────

def bridge_status() -> Dict[str, Any]:
    phoenix = _load_phoenix_registry()
    ba_count = len(list(BLACKARCH_DIR.iterdir())) if BLACKARCH_DIR.exists() else 0
    total = len(phoenix) + ba_count

    return {
        "phoenix_registry": len(phoenix),
        "blackarch_tools":  ba_count,
        "total_tools":      total,
        "blackarch_path":   str(BLACKARCH_DIR),
        "phoenix_path":     str(PHOENIX_ROOT),
        "juice_shop_target": JUICE_SHOP_TARGET,
        "kill_chain_steps":  len(JUICE_SHOP_KILLCHAIN),
        "status": "✅ Phoenix Bridge Online" if total > 0 else "⚠️ No tools found",
    }
