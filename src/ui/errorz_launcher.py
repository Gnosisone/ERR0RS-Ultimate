#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Main Launcher v3.0
WebSocket live terminal + HTTP API + inline education + interactive PTY

What's new in v3.0:
  - WebSocket /ws/terminal  → live streaming process output
  - Interactive stdin       → type INTO running tools from browser
  - Inline education        → [ERR0RS] annotations on scan results
  - Intent parser           → natural language → execute+teach mode
  - HTTP fallback           → all v2.1 endpoints still work

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, json, time, asyncio, threading, subprocess, webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# ── Ensure repo root is always on sys.path regardless of cwd ─────────────────
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# ── UTF-8 stdout/stderr (fixes Windows cp1252 charmap errors) ─────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ── Language Expansion Layer ──────────────────────────────────────────────
try:
    from src.core.language_layer import (
        ROUTE_TEACH_TRIGGERS, ROUTE_TOOL_MAP, BARE_TOOLS,
        SOC_TRIGGERS, REPORT_TRIGGERS, STATUS_TRIGGERS,
        ROCKETGOD_TRIGGERS, BADUSB_TRIGGERS, OLLAMA_TRIGGERS, MCP_TRIGGERS,
        PURPLE_TEAM_TRIGGERS, RAG_TRIGGERS,
        classify_command, resolve_tool_alias, get_soc_action,
    )
    _LANG_LOADED = True
    print("[ERR0RS] Language expansion layer loaded")
except ImportError as _le:
    _LANG_LOADED = False
    PURPLE_TEAM_TRIGGERS = []
    RAG_TRIGGERS = []
    print(f"[ERR0RS] Language layer fallback: {_le}")

ROOT_DIR = Path(__file__).resolve().parents[2]
UI_DIR   = Path(__file__).resolve().parent / "web"
SRC_DIR  = ROOT_DIR / "src"

if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR)  not in sys.path: sys.path.insert(0, str(SRC_DIR))

# ── Integration adapter — fixes module registry + wires all 25 tool entry points
try:
    from tools.integration_adapter import patch_registry
    patch_registry()
except Exception:
    try:
        from src.tools.integration_adapter import patch_registry
        patch_registry()
    except Exception as _ia_e:
        print(f"[ERR0RS] Integration adapter warning: {_ia_e}")

HOST     = os.getenv("ERRZ_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("ERRZ_PORT",    "8765"))
WS_PORT   = int(os.getenv("ERRZ_WS_PORT", "8766"))

# ── Framework import ──────────────────────────────────────────────────────────
try:
    from src.core.tool_executor import ToolExecutor
    from src.ai.natural_language import NaturalLanguageInterface
    FRAMEWORK_LOADED = True
    print("[ERR0RS] Framework loaded")
except Exception as e:
    FRAMEWORK_LOADED = False
    print(f"[ERR0RS] Framework dev mode: {e}")

# ── Live terminal engine ──────────────────────────────────────────────────────
try:
    from src.core.live_terminal import LiveProcess, parse_intent, build_command
    LIVE_TERMINAL = True
    print("[ERR0RS] Live terminal engine ready")
except Exception as e:
    LIVE_TERMINAL = False
    print(f"[ERR0RS] Live terminal unavailable: {e}")

# ── Smart Wizard ──────────────────────────────────────────────────────────────
try:
    from src.core.smart_wizard import detect_wizard, build_wizard_response, apply_target
    WIZARD_ENGINE = True
    print("[ERR0RS] Smart Wizard engine ready")
except Exception as e:
    WIZARD_ENGINE = False
    print(f"[ERR0RS] Smart Wizard unavailable: {e}")

# ── Terminal Bridge — OS terminal spawner + tool anatomy panel ───────────────
try:
    from src.tools.terminal_bridge import (
        get_tool_panel_data,
        load_registry as load_tool_registry,
        spawn_terminal_with_command,
        build_command_from_flags,
        get_preset_command,
    )
    TERMINAL_BRIDGE = True
    print("[ERR0RS] Terminal Bridge v2.0 ready — OS terminal launcher active")
except Exception as e:
    TERMINAL_BRIDGE = False
    print(f"[ERR0RS] Terminal Bridge unavailable: {e}")

# ── Hailo-10H NPU Integration ──────────────────────────────────────────────────
try:
    from src.ai.hailo_npu import (
        handle_hailo_request, hailo_available,
        hailo_status_line, HailoDetector
    )
    HAILO_ENGINE = True
    _hailo_status = hailo_status_line()
    print(f"[ERR0RS] Hailo NPU: {_hailo_status}")
except Exception as e:
    HAILO_ENGINE = False
    print(f"[ERR0RS] Hailo NPU unavailable: {e}")

# ── Flipper Zero Studio ───────────────────────────────────────────────────────
try:
    from src.tools.badusb_studio.flipper_studio import handle_flipper_request
    FLIPPER_ENGINE = True
    print("[ERR0RS] Flipper Zero Studio ready")
except Exception as e:
    FLIPPER_ENGINE = False
    print(f"[ERR0RS] Flipper Studio unavailable: {e}")

# ── ERR0RS Native Brain (replaces mr7 entirely — 100% local) ─────────────────
try:
    from src.ai.errz_brain import handle_brain_request, auto_route, BRAIN_MODES
    BRAIN_ENGINE = True
    print("[ERR0RS] Native AI Brain ready — 5 modes, zero cloud dependency")
except Exception as e:
    BRAIN_ENGINE = False
    print(f"[ERR0RS] Brain engine unavailable: {e}")

# ── BAS Engine ────────────────────────────────────────────────────────────────
try:
    from src.tools.breach.bas_engine import handle_bas_request
    BAS_ENGINE = True
    print("[ERR0RS] BAS engine ready")
except Exception as e:
    BAS_ENGINE = False
    print(f"[ERR0RS] BAS engine unavailable: {e}")

# ── Post-Exploitation Suite ───────────────────────────────────────────────────
try:
    from src.tools.postex.postex_module import run_postex
    from src.tools.postex.privesc_module import run_privesc
    from src.tools.postex.lateral_movement import run_lateral
    POSTEX_ENGINE = True
    print("[ERR0RS] Post-exploitation suite ready")
except Exception as e:
    POSTEX_ENGINE = False
    print(f"[ERR0RS] Post-exploitation suite unavailable: {e}")

# ── Wireless Attack Module ────────────────────────────────────────────────────
try:
    from src.tools.wireless.wireless_module import run_wireless
    WIRELESS_ENGINE = True
    print("[ERR0RS] Wireless module ready")
except Exception as e:
    WIRELESS_ENGINE = False
    print(f"[ERR0RS] Wireless module unavailable: {e}")

# ── Social Engineering Module ─────────────────────────────────────────────────
try:
    from src.tools.social.social_module import run_social
    SOCIAL_ENGINE = True
    print("[ERR0RS] Social engineering module ready")
except Exception as e:
    SOCIAL_ENGINE = False
    print(f"[ERR0RS] Social engineering module unavailable: {e}")

# ── Cloud Security Module ─────────────────────────────────────────────────────
try:
    from src.tools.cloud.cloud_module import run_cloud
    CLOUD_ENGINE = True
    print("[ERR0RS] Cloud security module ready")
except Exception as e:
    CLOUD_ENGINE = False
    print(f"[ERR0RS] Cloud security module unavailable: {e}")

# ── CTF Solver ────────────────────────────────────────────────────────────────
try:
    from src.tools.ctf.ctf_solver import run_ctf
    CTF_ENGINE = True
    print("[ERR0RS] CTF Solver ready")
except Exception as e:
    CTF_ENGINE = False
    print(f"[ERR0RS] CTF Solver unavailable: {e}")

# ── OPSEC Mode ────────────────────────────────────────────────────────────────
try:
    from src.tools.opsec.opsec_module import run_opsec
    OPSEC_ENGINE = True
    print("[ERR0RS] OPSEC mode ready")
except Exception as e:
    OPSEC_ENGINE = False
    print(f"[ERR0RS] OPSEC mode unavailable: {e}")

# ── Blue Team Toolkit ──────────────────────────────────────────────────────────
try:
    from src.security.blue_team import (
        handle_blue_team_request, auto_harden, generate_report, pcap_interpreter
    )
    BLUE_TEAM_ENGINE = True
    print("[ERR0RS] Blue Team toolkit ready — auto_harden / generate_report / pcap_interpreter")
except Exception as e:
    BLUE_TEAM_ENGINE = False
    print(f"[ERR0RS] Blue Team toolkit unavailable: {e}")

# ── Campaign Manager ───────────────────────────────────────────────────────────
try:
    from src.orchestration.campaign_manager import campaign_mgr, handle_campaign_command
    CAMPAIGN_ENGINE = True
    print("[ERR0RS] Campaign Manager ready")
except Exception as e:
    CAMPAIGN_ENGINE = False
    print(f"[ERR0RS] Campaign Manager unavailable: {e}")

# ── Auto Kill Chain ────────────────────────────────────────────────────────────
try:
    from src.orchestration.auto_killchain import handle_killchain_command, AutoKillChain
    KILLCHAIN_ENGINE = True
    print("[ERR0RS] Auto Kill Chain ready")
except Exception as e:
    KILLCHAIN_ENGINE = False
    print(f"[ERR0RS] Auto Kill Chain unavailable: {e}")

# ── Professional Reporter ──────────────────────────────────────────────────────
try:
    from src.reporting.pro_reporter import handle_report_command, ProReporter, reporter
    PRO_REPORTER = True
    print("[ERR0RS] Professional Reporter ready")
except Exception as e:
    PRO_REPORTER = False
    print(f"[ERR0RS] Professional Reporter unavailable: {e}")

# ── Credential Engine ──────────────────────────────────────────────────────────
try:
    from src.tools.credentials.credential_engine import cred_engine, CredentialEngine
    CRED_ENGINE = True
    print("[ERR0RS] Credential Engine ready")
except Exception as e:
    CRED_ENGINE = False
    cred_engine = None
    print(f"[ERR0RS] Credential Engine unavailable: {e}")

# ── Social Engineering Engine ──────────────────────────────────────────────────
try:
    from src.tools.se_engine.se_engine import handle_se_command, SocialEngineeringEngine
    SE_ENGINE = True
    print("[ERR0RS] Social Engineering Engine ready")
except Exception as e:
    SE_ENGINE = False
    print(f"[ERR0RS] SE Engine unavailable: {e}")

# ── AI Threat Intelligence Engine ─────────────────────────────────────────────
try:
    from src.tools.threat.ai_threat_engine import handle_ai_threat_command
    AI_THREAT_ENGINE = True
    print("[ERR0RS] AI Threat Intel Engine ready")
except Exception as e:
    AI_THREAT_ENGINE = False
    print(f"[ERR0RS] AI Threat Engine unavailable: {e}")

# ── Compliance Mapper ─────────────────────────────────────────────────────────
try:
    from src.tools.threat.compliance_mapper import handle_compliance_request
    COMPLIANCE_ENGINE = True
    print("[ERR0RS] Compliance mapper ready")
except Exception as e:
    COMPLIANCE_ENGINE = False
    print(f"[ERR0RS] Compliance mapper unavailable: {e}")

# ── Teach engine ─────────────────────────────────────────────────────────────
try:
    from src.education.teach_engine import handle_teach_request, find_lesson
    TEACH_ENGINE = True
    print("[ERR0RS] Teach engine ready")
except Exception as e:
    TEACH_ENGINE = False
    print(f"[ERR0RS] Teach engine unavailable: {e}")

# ── Flipper Zero Evolution Engine ─────────────────────────────────────────────
try:
    from src.tools.flipper.flipper_evolution import (
        run_flipper_evolution, FlipperEvolution, EVOLUTION_LEVELS, FLIPPER_WIZARD_MENU
    )
    _flipper_evo = FlipperEvolution()
    FLIPPER_ENGINE = True
    print("[ERR0RS] Flipper Evolution Engine ready — plug in your Flipper to evolve it!")

    def _flipper_cb(step):
        print(f"[ERR0RS] FLIPPER [{step.status.upper()}] {step.name}  +{step.xp_reward} XP")

    def start_flipper_watcher(poll_interval: int = 5):
        """
        Start the background Flipper auto-evolve watcher.
        Called explicitly by the server after boot — NOT at import time.
        Set env var FLIPPER_WATCH=1 to auto-start, or call this function manually.
        """
        import threading as _threading
        _ft = _threading.Thread(
            target=_flipper_evo.auto_evolve_on_connect,
            kwargs={"poll_interval": poll_interval, "callback": _flipper_cb},
            daemon=True, name="flipper-watcher"
        )
        _ft.start()
        print(f"[ERR0RS] Flipper watcher started (polling every {poll_interval}s)")

    # Only auto-start watcher if explicitly opted in via env var
    if os.environ.get("FLIPPER_WATCH", "0") == "1":
        start_flipper_watcher()

except Exception as e:
    FLIPPER_ENGINE = False
    start_flipper_watcher = None
    print(f"[ERR0RS] Flipper Evolution Engine unavailable: {e}")

# ── Active listener/server processes (payload studio auto-spin-up) ─────────────
_ACTIVE_SERVERS: dict = {}  # type → subprocess.Popen

# ── websockets library ────────────────────────────────────────────────────────
try:
    import websockets
    WEBSOCKETS_OK = True
except ImportError:
    WEBSOCKETS_OK = False
    print("[ERR0RS] websockets not installed — run: pip3 install websockets")

# Active processes registry: session_id → LiveProcess
_active_processes = {}
_ws_clients       = {}   # session_id → websocket

# ═══════════════════════════════════════════════════════════════════════════
# SHELL UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def run_shell(cmd: str, timeout: int = 60) -> dict:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True,
                                text=True, timeout=timeout)
        return {"stdout": result.stdout, "stderr": result.stderr,
                "returncode": result.returncode, "command": cmd,
                "status": "success" if result.returncode == 0 else "error"}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"Timed out after {timeout}s",
                "returncode": -1, "command": cmd, "status": "timeout"}
    except Exception as e:
        return {"stdout": "", "stderr": str(e),
                "returncode": -1, "command": cmd, "status": "error"}


def run_tool_async(tool: str, target: str, params: dict) -> dict:
    async def _run():
        executor = ToolExecutor()
        result   = await executor.run(tool, target, params)
        return {"tool": result.tool_name, "command": result.command,
                "status": result.status.value, "stdout": result.stdout,
                "stderr": result.stderr, "returncode": result.return_code,
                "duration_ms": result.duration_ms, "findings": result.findings,
                "error": result.error}
    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_run())
    except Exception as e:
        return {"status": "error", "error": str(e), "tool": tool}
    finally:
        loop.close()


def query_ollama(prompt: str) -> dict:
    import urllib.request, os
    # Pi-aware model selection
    _m = os.getenv("OLLAMA_MODEL", "")
    if not _m:
        try:
            with open("/proc/cpuinfo") as f:
                _m = "qwen2.5-coder:7b" if "Raspberry Pi" in f.read() else "qwen2.5-coder:32b"
        except Exception:
            _m = "qwen2.5-coder:32b"
    try:
        body = json.dumps({"model": _m,
            "prompt": f"You are ERR0RS, an AI penetration testing assistant. {prompt}",
            "stream": False}).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate",
            data=body, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            return {"stdout": data.get("response", ""), "status": "success", "source": "ollama"}
    except Exception as e:
        return {"stdout": (
            f"[ERR0RS] Ollama offline: {e}\n\n"
            "Built-in lessons (no Ollama needed):\n"
            "  teach me sqlmap    teach me nmap      teach me gobuster\n"
            "  teach me hydra     teach me metasploit teach me hashcat\n"
            "  teach me nikto     teach me nuclei     teach me privesc\n"
            "  teach me xss       teach me burp suite teach me wireshark\n\n"
            "Shell: $ whoami | $ nmap -sV target | use --teach flag for inline education"
        ), "status": "error", "source": "ollama"}


# ═══════════════════════════════════════════════════════════════════════════
# COMMAND ROUTER  (HTTP path — non-streaming fallback)
# ═══════════════════════════════════════════════════════════════════════════

def route_command(cmd: str) -> dict:
    lower = cmd.lower().strip()

    # ── WIZARD ENGINE — intercept vague commands first ────────────────────
    if WIZARD_ENGINE:
        wizard_key = detect_wizard(cmd)
        if wizard_key:
            wizard = build_wizard_response(wizard_key)
            if wizard:
                return {"status": "wizard", **wizard}

    # ── Use Language Layer classifier if available ────────────────────────
    _teach_triggers  = ROUTE_TEACH_TRIGGERS if _LANG_LOADED else [
        "teach me","how do i","how to use","how does","explain","what is","what are",
        "tell me about","how do you use","learn","help me learn","show me how","guide me",
        "tutorial","how to","walk me through","i want to learn","how can i use"]
    _bare_tools      = BARE_TOOLS if _LANG_LOADED else [
        "sqlmap","nikto","gobuster","hydra","hashcat","aircrack","nuclei",
        "subfinder","metasploit","meterpreter","wireshark","burp","burp suite",
        "privilege escalation","privesc","xss","sql injection","sqli","nmap"]
    _tool_map        = ROUTE_TOOL_MAP if _LANG_LOADED else {
        "nmap":"nmap","scan":"nmap","nikto":"nikto","gobuster":"gobuster",
        "dirbust":"gobuster","sqlmap":"sqlmap","sqli":"sqlmap",
        "hydra":"hydra","brute":"hydra","subfinder":"subfinder",
        "subdomain":"subfinder","nuclei":"nuclei","amass":"amass",
        "metasploit":"metasploit","msf":"metasploit","hashcat":"hashcat","crack":"hashcat"}
    _report_triggers = REPORT_TRIGGERS if _LANG_LOADED else ["report","generate report","debrief"]
    _status_triggers = STATUS_TRIGGERS if _LANG_LOADED else ["status","sysinfo","uname","whoami"]
    _rg_triggers     = ROCKETGOD_TRIGGERS if _LANG_LOADED else [
        "rocketgod","hackrf","rf jammer","jammer","protopirate",
        "rolling code","keyfob","sub file","subghz scan","wigle",
        "wardriv","radio scanner","keeloq","flipper sd","rg toolbox"]
    _bu_triggers     = BADUSB_TRIGGERS if _LANG_LOADED else [
        "flipper","badusb","ducky","duckyscript","reverse shell",
        "evil portal","captive portal","sd card","generate script"]
    _ollama_triggers = OLLAMA_TRIGGERS if _LANG_LOADED else ["ollama","models","ai status"]
    _mcp_triggers    = MCP_TRIGGERS    if _LANG_LOADED else ["mcp","kali tools"]

    # ── Teach / Learn / Explain ───────────────────────────────────────────
    if any(t in lower for t in _teach_triggers):
        if TEACH_ENGINE:
            return handle_teach_request(cmd)

    # ── Purple Team loop — Red + Blue + Remediation ───────────────────────
    _pt_triggers = PURPLE_TEAM_TRIGGERS if _LANG_LOADED else []
    if any(t in lower for t in _pt_triggers):
        return _query_brain_mode(cmd, "purple_team")

    # ── RAG knowledge base query ──────────────────────────────────────────
    _rag_triggers = RAG_TRIGGERS if _LANG_LOADED else []
    if any(t in lower for t in _rag_triggers):
        return _query_brain_mode(cmd, "rag_analyst")

    if lower.strip() in [b.lower() for b in _bare_tools] and TEACH_ENGINE:
        return handle_teach_request(lower.strip())

    # ── Tool execution ────────────────────────────────────────────────────
    parts  = cmd.strip().split()
    verb   = parts[0].lower() if parts else ""
    target = parts[1] if len(parts) > 1 else ""
    # Also try language layer resolve for natural phrases
    resolved_tool = (resolve_tool_alias(lower) if _LANG_LOADED else None) or _tool_map.get(verb)
    if resolved_tool and target:
        tool = resolved_tool
        if FRAMEWORK_LOADED:
            return run_tool_async(tool, target, {})
        cmds = {
            "nmap":         f"nmap -sV -sC --top-ports 1000 {target}",
            "nikto":        f"nikto -h {target}",
            "gobuster":     f"gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt",
            "sqlmap":       f"sqlmap -u http://{target} --batch --dbs",
            "hydra":        f"hydra -l root -P /usr/share/wordlists/rockyou.txt {target} ssh",
            "subfinder":    f"subfinder -d {target}",
            "nuclei":       f"nuclei -u http://{target}",
            "amass":        f"amass enum -d {target}",
            "metasploit":   f"msfconsole -q -x 'search type:exploit target:{target}; exit'",
            "hashcat":      f"hashcat -m 0 -a 0 {target} /usr/share/wordlists/rockyou.txt",
            "wpscan":       f"wpscan --url http://{target} --enumerate p,u",
            "crackmapexec": f"crackmapexec smb {target}",
            "enum4linux":   f"enum4linux -a {target}",
            "ffuf":         f"ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt",
        }
        return run_shell(cmds.get(tool, f"{tool} {target}"), timeout=120)

    # ── System info ───────────────────────────────────────────────────────
    if any(x in lower for x in _status_triggers):
        return run_shell("uname -a && whoami && ip addr show 2>/dev/null | grep inet")

    # ── Report ────────────────────────────────────────────────────────────
    if any(x in lower for x in _report_triggers):
        if BLUE_TEAM_ENGINE:
            result = generate_report(hours=1, include_harden=True)
            fmt    = result.get("format", "html")
            path   = result.get("path", "")
            count  = result.get("finding_count", 0)
            return {
                "status": "success",
                "stdout": (
                    f"[ERR0RS] Security Audit Report generated\n"
                    f"  Format:   {fmt.upper()}\n"
                    f"  Findings: {count}\n"
                    f"  Path:     {path}\n"
                    f"  Note:     {result.get('note','')}\n\n"
                    f"Open in browser: {path}"
                ),
                "path":   path,
                "format": fmt,
            }
        result = run_shell(f"cd {ROOT_DIR} && python3 demo_report.py 2>&1", timeout=30)
        if result["returncode"] == 0:
            result["stdout"] = "Report generated → /tmp/errorz_report.html\n" + result["stdout"]
        return result

    # ── MCP / Ollama ──────────────────────────────────────────────────────
    if any(x in lower for x in _mcp_triggers):
        return run_shell("mcp-server --list-tools 2>/dev/null || echo 'mcp-kali-server not installed'")
    if any(x in lower for x in _ollama_triggers):
        return run_shell("ollama list 2>/dev/null || echo 'Ollama not running'")

    # ── Raw shell ─────────────────────────────────────────────────────────
    if cmd.startswith("$") or cmd.startswith("!"):
        return run_shell(cmd[1:].strip(), timeout=60)

    # ── RocketGod ─────────────────────────────────────────────────────────
    if any(t in lower for t in _rg_triggers):
        try:
            from src.tools.rocketgod import handle_rocketgod_request
            if any(x in lower for x in ["jammer","jam"]):
                r = handle_rocketgod_request({"action":"jammer_modes"})
                out = "\n".join([f"  [{k}] {v}" for k,v in r.get("modes",{}).items()])
                return {"stdout": f"[RocketGod] RF Jammer Modes:\n{out}", "status":"success"}
            elif any(x in lower for x in ["proto","rolling code","keyfob"]):
                r = handle_rocketgod_request({"action":"protopirate"})
                return {"stdout": f"ProtoPirate: {', '.join(r.get('protocols',[]))}", "status":"success"}
            elif "hackrf" in lower:
                r = handle_rocketgod_request({"action":"hackrf"})
                return {"stdout": f"HackRF: {r.get('description','')} @ {r.get('path','')}", "status":"success"}
            else:
                r = handle_rocketgod_request({"action":"search","prompt":cmd})
                results = r.get("results",[])
                out = "\n".join([f"  [{x['repo']}] {x['description']}" for x in results])
                return {"stdout": f"[RocketGod Search: {cmd}]\n{out or 'No results'}", "status":"success"}
        except Exception:
            pass

    # ── BadUSB ────────────────────────────────────────────────────────────
    if any(t in lower for t in _bu_triggers):
        try:
            from src.tools.badusb import nlp_to_flipper
            return nlp_to_flipper(cmd)
        except Exception:
            pass

    # ── Post-Exploitation Module ──────────────────────────────────────────
    _postex_triggers = [
        "postex", "post ex", "post-ex", "post exploitation", "post-exploitation",
        "situational awareness", "i have a shell", "got a shell", "after shell",
        "what do i do after", "maintain access", "cron job", "ssh key persist",
        "chisel tunnel", "socks proxy", "lazagne", "shell history", "env creds",
        "timestomp", "clear history", "clear logs", "covering tracks",
    ]
    if any(t in lower for t in _postex_triggers):
        try:
            from src.tools.postex.postex_module import PostExController
            ctrl   = PostExController()
            action = _extract_postex_action(lower)
            result = ctrl.run(action)
            out = f"[💀 POST-EX: {result.technique}]\n\n"
            out += f"Command : {result.command}\n\n"
            if result.output:
                out += f"{result.output}\n\n"
            if result.teach:
                out += f"[TEACH] {result.teach}\n\n"
            if result.defend:
                out += f"[DEFEND] {result.defend}"
            return {"stdout": out, "status": "success" if result.success else "info", "source": "postex"}
        except Exception as e:
            pass

    # ── Privilege Escalation Module ───────────────────────────────────────
    _privesc_triggers = [
        "privesc", "privilege escalation", "escalate", "get root", "get system",
        "become root", "linpeas", "winpeas", "suid", "sudo exploit",
        "token impersonation", "potato attack", "seimpersonate",
        "alwaysinstallelevated", "unquoted service", "docker group",
    ]
    if any(t in lower for t in _privesc_triggers):
        try:
            from src.tools.postex.privesc_module import PrivescController
            ctrl   = PrivescController()
            action = _extract_privesc_action(lower)
            result = ctrl.run(action)
            vuln_icon = "🔴" if result.vulnerable else "⚪"
            out = f"[⬆️  PRIVESC: {result.technique}]\n\n"
            out += f"Command    : {result.command}\n"
            out += f"Vulnerable : {vuln_icon} {result.vulnerable}\n\n"
            if result.output:
                out += f"{result.output[:800]}\n\n"
            if result.exploit_cmd and result.vulnerable:
                out += f"[EXPLOIT]  {result.exploit_cmd}\n\n"
            if result.teach:
                out += f"[TEACH]  {result.teach}\n\n"
            if result.defend:
                out += f"[DEFEND] {result.defend}"
            return {"stdout": out, "status": "success", "source": "privesc"}
        except Exception as e:
            pass

    # ── Lateral Movement Module ───────────────────────────────────────────
    _lateral_triggers = [
        "lateral movement", "lateral move", "pass the hash", "pth attack",
        "kerberoast", "dcsync", "bloodhound", "psexec", "wmiexec",
        "smb spray", "password spray", "spread through network", "move laterally",
    ]
    if any(t in lower for t in _lateral_triggers):
        try:
            from src.tools.postex.lateral_movement import LateralMovementController
            ctrl   = LateralMovementController()
            action = _extract_lateral_action(lower)
            result = ctrl.run(action, {"target": target or "192.168.1.0/24"})
            out = f"[🔀 LATERAL: {result.technique}]\n\n"
            out += f"Command : {result.command}\n\n"
            if result.teach:
                out += f"[TEACH]  {result.teach}\n\n"
            if result.defend:
                out += f"[DEFEND] {result.defend}"
            return {"stdout": out, "status": "success", "source": "lateral"}
        except Exception as e:
            pass

    # ── Wireless Module ───────────────────────────────────────────────────
    _wireless_triggers = [
        "wireless pentest", "wifi pentest", "evil twin", "pmkid attack",
        "deauth clients", "crack handshake", "monitor mode", "airodump",
        "wpa crack", "wpa2 crack", "rogue ap", "handshake capture",
    ]
    if any(t in lower for t in _wireless_triggers):
        try:
            from src.tools.wireless.wireless_module import WirelessModule
            w      = WirelessModule()
            action = _extract_wireless_action(lower)
            result = w.run(action, {"interface": "wlan0", "mon_interface": "wlan0mon"})
            out = f"[📡 WIRELESS: {result.technique}]\n\n"
            out += f"Command : {result.command}\n\n"
            if result.teach:
                out += f"[TEACH]  {result.teach}\n\n"
            if result.defend:
                out += f"[DEFEND] {result.defend}"
            return {"stdout": out, "status": "success", "source": "wireless"}
        except Exception as e:
            pass

    # ── Social Engineering Module ─────────────────────────────────────────
    _social_triggers = [
        "social engineering", "phishing email", "spear phish", "phishing template",
        "email campaign", "harvest emails", "vishing", "pretexting",
        "linkedin recon", "email harvest",
    ]
    if any(t in lower for t in _social_triggers):
        try:
            from src.tools.social.social_module import SocialEngineeringController
            ctrl   = SocialEngineeringController()
            action = _extract_social_action(lower)
            params = {}
            if target:
                if "." in target:
                    params["domain"] = target
                else:
                    params["company"] = target
            result = ctrl.run(action, params)
            out = f"[🎭 SOCIAL ENG: {result.technique}]\n\n{result.output}"
            if result.teach:
                out += f"\n\n[TEACH]  {result.teach}"
            if result.defend:
                out += f"\n\n[DEFEND] {result.defend}"
            return {"stdout": out, "status": "success", "source": "social"}
        except Exception as e:
            pass

    # ── Cloud Security Module ─────────────────────────────────────────────
    _cloud_triggers = [
        "cloud security", "aws enum", "aws iam", "aws s3", "azure enum",
        "azure rbac", "gcp enum", "gcp iam", "cloud audit", "cloud pentest",
        "validate aws keys", "aws keys", "leaked aws", "s3 bucket",
        "prowler scan", "cloud misconfiguration", "cloud credentials",
        "enumerate cloud", "cloud recon", "azure storage", "gcs bucket",
        "iam enum", "aws whoami", "gcp whoami", "azure whoami",
    ]
    if any(t in lower for t in _cloud_triggers):
        if CLOUD_ENGINE:
            action = _extract_cloud_action(lower)
            return {"stdout": run_cloud(action), "status": "success", "source": "cloud"}

    # ── CTF Solver Mode ───────────────────────────────────────────────────
    _ctf_triggers = [
        "ctf", "capture the flag", "ctf mode", "ctf solver",
        "ctf web", "ctf pwn", "ctf crypto", "ctf forensics", "ctf rev",
        "solve ctf", "help me with ctf", "ctf challenge",
    ]
    if any(t in lower for t in _ctf_triggers):
        if CTF_ENGINE:
            category = _extract_ctf_category(lower)
            return {"stdout": run_ctf(category), "status": "success", "source": "ctf"}

    # ── OPSEC Mode ────────────────────────────────────────────────────────
    _opsec_triggers = [
        "opsec", "operational security", "stay anonymous", "anonymity",
        "proxychains", "tor setup", "mac spoof", "vpn tor", "persona management",
        "sock puppet", "cover tracks", "anti forensics", "anti-forensics",
        "opsec checklist", "tradecraft", "avoid detection", "engagement hygiene",
    ]
    if any(t in lower for t in _opsec_triggers):
        if OPSEC_ENGINE:
            topic = _extract_opsec_topic(lower)
            return {"stdout": run_opsec(topic), "status": "success", "source": "opsec"}

    # ── Campaign Manager ──────────────────────────────────────────────────
    _campaign_triggers = [
        "campaign", "new campaign", "create campaign", "start engagement",
        "campaign status", "list campaigns", "add finding", "log finding",
        "add credential", "log credential", "register session",
        "close campaign", "engagement status",
    ]
    if any(t in lower for t in _campaign_triggers):
        if CAMPAIGN_ENGINE:
            return handle_campaign_command(cmd)

    # ── Auto Kill Chain ────────────────────────────────────────────────────
    _killchain_triggers = [
        "auto pentest", "full pentest", "automated pentest", "run kill chain",
        "full auto", "auto scan and exploit", "full engagement",
        "automated engagement", "dry run pentest", "supervised pentest",
    ]
    if any(t in lower for t in _killchain_triggers):
        if KILLCHAIN_ENGINE:
            tgt = target or parts[1] if len(parts) > 1 else ""
            mode = "DRY_RUN" if "dry" in lower else (
                   "FULL_AUTO" if "full auto" in lower else "SUPERVISED")
            return handle_killchain_command({"target": tgt, "mode": mode})

    # ── Professional Report ────────────────────────────────────────────────
    _pro_report_triggers = [
        "pro report", "professional report", "generate pro report",
        "full report", "pentest report", "engagement report",
        "client report", "generate report", "debrief",
    ]
    if any(t in lower for t in _pro_report_triggers):
        if PRO_REPORTER:
            return handle_report_command({})

    # ── Credential Engine ──────────────────────────────────────────────────
    _cred_triggers = [
        "crack all hashes", "crack hashes", "spray credentials",
        "credential spray", "password spray creds", "analyze passwords",
        "password patterns", "import hashes", "bulk import creds",
        "credential engine", "cred summary", "cred engine",
    ]
    if any(t in lower for t in _cred_triggers):
        if CRED_ENGINE:
            from src.tools.credentials.credential_engine import cred_engine as _ce
            if "crack" in lower:
                r = _ce.crack_all()
                return {"status": "success", "stdout": str(r), "source": "cred_engine"}
            if "spray" in lower:
                tgts = [target] if target else []
                r = _ce.spray(tgts)
                return {"status": "success", "stdout": str(r), "source": "cred_engine"}
            if "analyz" in lower or "pattern" in lower:
                return {"status": "success", "stdout": _ce.analyze_patterns(), "source": "cred_engine"}
            return {"status": "success", "stdout": _ce.summary(), "source": "cred_engine"}

    # ── Social Engineering Engine ──────────────────────────────────────────
    _se_engine_triggers = [
        "social engineering", "phishing campaign", "build phishing",
        "vishing script", "call script", "pretext recommend",
        "se curriculum", "se topics", "teach me social engineering",
        "se engine", "human variable", "osint recon target",
        "spear phish template", "phishing template", "gophish setup",
    ]
    if any(t in lower for t in _se_engine_triggers):
        if SE_ENGINE:
            return handle_se_command(cmd)

    # ── AI Threat Intelligence Engine ─────────────────────────────────────
    _ai_threat_cmd_triggers = [
        "wormgpt", "fraudgpt", "criminal ai tools", "ai threat landscape",
        "corporate briefing", "board briefing", "executive briefing",
        "deepfake fraud", "voice clone attack", "ai malware",
        "mitre atlas", "ai attack framework", "prompt injection threat",
        "what are attackers using", "current threat landscape",
        "brief the board", "fortune 500 brief", "ai threat intel",
    ]
    if any(t in lower for t in _ai_threat_cmd_triggers):
        if AI_THREAT_ENGINE:
            return handle_ai_threat_command(cmd)

    # ── Teach engine second pass ──────────────────────────────────────────
    if TEACH_ENGINE:
        lesson = find_lesson(cmd)
        if lesson:
            from src.education.teach_engine import format_lesson
            return {"stdout": format_lesson(lesson), "status":"success", "source":"errz_builtin"}

    # ── ERR0RS Native Brain fallback (replaces Ollama direct + mr7) ─────────
    return _query_brain(cmd)


def _extract_postex_action(lower: str) -> str:
    """Map natural language to a PostExController action key."""
    mapping = {
        ("lazagne", "credential harvest", "cred harvest"):                "lazagne",
        ("shadow", "/etc/shadow"):                                        "shadow",
        ("shell history", "bash history", "history files"):               "history",
        ("env cred", "environment variable", "env var"):                  "env_creds",
        ("process arg", "proc cred"):                                     "proc_creds",
        ("network map", "arp table", "network info", "ip addr"):          "network",
        ("domain enum", "active directory", "domain admin"):              "domain",
        ("sensitive file", "hunt file", "find credential file"):         "sensitive_files",
        ("sysinfo", "system info", "os version"):                         "sysinfo",
        ("cron", "crontab"):                                              "cron",
        ("ssh key", "authorized key"):                                    "ssh_key",
        ("systemd", "service persist"):                                   "systemd",
        ("cleanup", "remove artifact"):                                   "cleanup",
        ("socks", "socks5", "dynamic proxy"):                             "socks",
        ("ssh forward", "port forward", "local forward"):                 "ssh_forward",
        ("chisel server", "chisel attacker"):                             "chisel_server",
        ("chisel client", "chisel target"):                               "chisel_client",
        ("portfwd", "meterpreter pivot"):                                 "portfwd",
        ("clear history", "bash history clear"):                          "clear_history",
        ("clear auth", "auth log", "clear log"):                          "clear_auth",
        ("timestomp",):                                                   "timestomp",
        ("full report", "situational awareness", "full awareness"):       "full_report",
        ("pivot", "pivoting"):                                            "socks",
        ("persist", "maintain access"):                                   "cron",
        ("whoami", "who am i", "current user"):                           "whoami",
    }
    for keywords, action in mapping.items():
        if any(k in lower for k in keywords):
            return action
    return "full_report"


def _extract_privesc_action(lower: str) -> str:
    """Map natural language to a PrivescController action key."""
    if any(k in lower for k in ("linpeas",)):           return "linpeas"
    if any(k in lower for k in ("winpeas",)):           return "winpeas"
    if any(k in lower for k in ("suid", "gtfobins")):   return "suid"
    if any(k in lower for k in ("sudo",)):              return "sudo"
    if any(k in lower for k in ("passwd", "/etc/pass")): return "etc_passwd"
    if any(k in lower for k in ("capabilit", "getcap")): return "caps"
    if any(k in lower for k in ("docker",)):            return "docker"
    if any(k in lower for k in ("alwaysinstall", "msi")): return "aie"
    if any(k in lower for k in ("unquoted",)):          return "unquoted"
    if any(k in lower for k in ("potato", "seimpersonat", "impersonat")): return "seimpersonate"
    return "all"


def _extract_lateral_action(lower: str) -> str:
    """Map natural language to a LateralMovementController action key."""
    if any(k in lower for k in ("pass the hash", "pth")):          return "pth"
    if any(k in lower for k in ("psexec",)):                        return "psexec"
    if any(k in lower for k in ("wmiexec", "wmi exec")):            return "wmiexec"
    if any(k in lower for k in ("kerberoast",)):                    return "kerberoast"
    if any(k in lower for k in ("dcsync", "dc sync")):              return "dcsync"
    if any(k in lower for k in ("bloodhound",)):                    return "bloodhound"
    return "smb_spray"


def _extract_wireless_action(lower: str) -> str:
    """Map natural language to a WirelessModule action key."""
    if any(k in lower for k in ("monitor mode", "enable monitor")):   return "monitor_on"
    if any(k in lower for k in ("scan", "airodump", "discover")):      return "scan"
    if any(k in lower for k in ("capture", "targeted")):               return "capture"
    if any(k in lower for k in ("deauth", "disconnect")):              return "deauth"
    if any(k in lower for k in ("crack", "wpa crack", "handshake crack")): return "crack"
    if any(k in lower for k in ("pmkid",)):                            return "pmkid"
    if any(k in lower for k in ("evil twin", "rogue ap", "fake ap")):  return "evil_twin"
    return "scan"


def _extract_social_action(lower: str) -> str:
    """Map natural language to a SocialEngineeringController action key."""
    if any(k in lower for k in ("harvest email", "find email")):       return "harvest_emails"
    if any(k in lower for k in ("linkedin",)):                         return "linkedin_recon"
    if any(k in lower for k in ("list template", "show template")):    return "list_templates"
    if any(k in lower for k in ("spear phish", "targeted phish")):     return "spear_phish"
    if any(k in lower for k in ("vishing", "voice phish", "helpdesk call")): return "vishing_helpdesk"
    if any(k in lower for k in ("password reset", "reset vishing")):   return "vishing_reset"
    return "phish_template"


def _extract_cloud_action(lower: str) -> str:
    """Map natural language to a cloud_module action key."""
    if any(k in lower for k in ("aws whoami", "aws identity", "caller identity")): return "aws_whoami"
    if any(k in lower for k in ("aws iam", "iam enum", "list users", "list roles")): return "aws_iam"
    if any(k in lower for k in ("s3", "s3 bucket", "bucket audit")):               return "aws_s3"
    if any(k in lower for k in ("prowler",)):                                       return "aws_prowler"
    if any(k in lower for k in ("azure whoami", "azure identity")):                 return "azure_whoami"
    if any(k in lower for k in ("azure rbac", "role assignment")):                  return "azure_rbac"
    if any(k in lower for k in ("azure storage", "blob storage")):                  return "azure_storage"
    if any(k in lower for k in ("gcp whoami", "gcp identity")):                     return "gcp_whoami"
    if any(k in lower for k in ("gcp iam",)):                                       return "gcp_iam"
    if any(k in lower for k in ("gcs bucket", "gcp storage")):                      return "gcp_storage"
    return ""  # show full menu


def _extract_ctf_category(lower: str) -> str:
    """Map natural language to a CTF category."""
    if any(k in lower for k in ("web", "sqli", "xss", "ssti", "lfi", "jwt")):         return "web"
    if any(k in lower for k in ("pwn", "binary", "bof", "buffer overflow", "rop")):   return "pwn"
    if any(k in lower for k in ("crypto", "cryptography", "rsa", "xor", "hash")):     return "crypto"
    if any(k in lower for k in ("forensics", "forensic", "steg", "pcap", "memory")):  return "forensics"
    if any(k in lower for k in ("rev", "reversing", "reverse engineering", "ghidra")): return "rev"
    return ""  # show full menu


def _extract_opsec_topic(lower: str) -> str:
    """Map natural language to an OPSEC topic."""
    if any(k in lower for k in ("tor", "proxychains")):                                 return "tor"
    if any(k in lower for k in ("mac spoof", "mac address")):                           return "mac"
    if any(k in lower for k in ("vpn", "whonix", "mullvad")):                           return "vpn"
    if any(k in lower for k in ("persona", "sock puppet", "fake identity")):             return "persona"
    if any(k in lower for k in ("anti forensics", "anti-forensics", "timestomp",
                                 "cover tracks", "log wipe", "clear log")):              return "antiforensics"
    if any(k in lower for k in ("checklist", "pre engagement", "post engagement")):      return "checklist"
    return ""  # show full menu


def _query_brain(prompt: str) -> dict:
    """Route through ERR0RS Native Brain — auto-selects the best mode."""
    if BRAIN_ENGINE:
        result = handle_brain_request({"action": "ask", "prompt": prompt, "mode": "auto"})
        mode_name = result.get("mode_name", "ERR0RS Brain")
        icon = result.get("icon", "🧠")
        return {
            "status": result.get("status", "error"),
            "stdout": f"[{icon} {mode_name}]\n\n{result.get('stdout', result.get('error', 'No response'))}",
            "source": "errz_brain_local",
        }
    return query_ollama(prompt)


def _query_brain_mode(prompt: str, mode: str) -> dict:
    """Route through ERR0RS Native Brain with a specific forced mode."""
    if BRAIN_ENGINE:
        result = handle_brain_request({"action": "ask", "prompt": prompt, "mode": mode})
        mode_name = result.get("mode_name", mode)
        icon = result.get("icon", "🧠")
        return {
            "status": result.get("status", "error"),
            "stdout": f"[{icon} {mode_name}]\n\n{result.get('stdout', result.get('error', 'No response'))}",
            "source": "errz_brain_local",
            "mode": mode,
        }
    return query_ollama(prompt)


# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET SERVER — live terminal streaming
# ═══════════════════════════════════════════════════════════════════════════

async def ws_terminal_handler(websocket):
    """
    WebSocket handler for live terminal sessions.

    Protocol (JSON messages):
      CLIENT → SERVER:
        {"type": "run",    "command": "nmap 192.168.1.1", "teach": true}
        {"type": "stdin",  "data": "yes\n"}
        {"type": "key",    "data": "\x03"}   ← Ctrl+C
        {"type": "kill"}

      SERVER → CLIENT:
        {"type": "system",     "data": "[ERR0RS] Spawned: nmap ..."}
        {"type": "output",     "data": "PORT   STATE  SERVICE"}
        {"type": "teach",      "data": "[ERR0RS] Port 22 = SSH ..."}
        {"type": "teach_block","data": "=====\n[ERR0RS TEACHES]..."}
        {"type": "error",      "data": "PTY fork failed"}
        {"type": "done",       "data": "[ERR0RS] Process complete."}
    """
    session_id = id(websocket)
    _ws_clients[session_id] = websocket
    proc = None

    try:
        await websocket.send(json.dumps({
            "type": "system",
            "data": f"[ERR0RS] WebSocket connected. Session {session_id}\n"
                    "[ERR0RS] Type commands below. Add '--teach' for inline education.\n"
                    "[ERR0RS] Use $ prefix for raw shell. Ctrl+C to stop running tools."
        }))

        async for message in websocket:
            try:
                msg = json.loads(message)
            except Exception:
                continue

            mtype = msg.get("type", "run")

            # ── Stdin forwarding to running process ───────────────────────
            if mtype == "stdin":
                if proc and proc.is_running:
                    proc.send_input(msg.get("data", ""))
                continue

            # ── Raw key (Ctrl+C etc) ──────────────────────────────────────
            if mtype == "key":
                if proc and proc.is_running:
                    data = msg.get("data", "")
                    proc.send_raw(data.encode("utf-8", errors="replace"))
                continue

            # ── Kill current process ──────────────────────────────────────
            if mtype == "kill":
                if proc and proc.is_running:
                    proc.terminate()
                    await websocket.send(json.dumps({"type":"system","data":"[ERR0RS] Process killed."}))
                continue

            # ── Run a command ─────────────────────────────────────────────
            if mtype == "run":
                raw_cmd   = msg.get("command", "").strip()
                teach_flag = msg.get("teach", False) or "--teach" in raw_cmd or "-t" in raw_cmd.split()

                # Clean --teach flag from command
                clean_cmd = raw_cmd.replace("--teach", "").replace(" -t ", " ").strip()

                # Kill any existing process
                if proc and proc.is_running:
                    proc.terminate()

                # Parse intent
                if LIVE_TERMINAL:
                    intent = parse_intent(clean_cmd)
                else:
                    intent = {"tool": None, "target": None, "raw_cmd": clean_cmd,
                              "execute": True, "teach": teach_flag, "mode": "execute"}

                # Teach-only mode
                if intent["mode"] == "teach" and not intent["execute"]:
                    if TEACH_ENGINE:
                        result = handle_teach_request(clean_cmd)
                        await websocket.send(json.dumps({
                            "type": "teach_block",
                            "data": result["stdout"]
                        }))
                    continue

                # Build actual command
                if intent.get("raw_cmd"):
                    final_cmd = intent["raw_cmd"]
                    tool      = ""
                elif intent["tool"] and intent["target"] and LIVE_TERMINAL:
                    final_cmd = build_command(intent["tool"], intent["target"])
                    tool      = intent["tool"]
                elif intent["tool"] and LIVE_TERMINAL:
                    # Tool with no target — teach instead
                    if TEACH_ENGINE:
                        result = handle_teach_request(intent["tool"])
                        await websocket.send(json.dumps({"type":"teach_block","data":result["stdout"]}))
                        await websocket.send(json.dumps({"type":"system",
                            "data":"[ERR0RS] Provide a target to run this tool. Example: nmap 192.168.1.1"}))
                    continue
                else:
                    # Not a tool command — route through normal handler
                    result = route_command(clean_cmd)
                    await websocket.send(json.dumps({
                        "type": "output",
                        "data": result.get("stdout") or result.get("error") or "No output"
                    }))
                    continue

                # Emit the command being run
                await websocket.send(json.dumps({
                    "type": "system",
                    "data": f"[ERR0RS] Running: {final_cmd}"
                }))

                # Teach mode: emit full lesson BEFORE running
                if (teach_flag or intent.get("teach")) and TEACH_ENGINE and tool:
                    result = handle_teach_request(tool)
                    await websocket.send(json.dumps({
                        "type": "teach_block",
                        "data": result["stdout"]
                    }))
                    await websocket.send(json.dumps({
                        "type": "system",
                        "data": "[ERR0RS] Lesson complete. Now running the actual tool...\n" + "="*54
                    }))

                # Spawn with PTY if available (Linux/Kali)
                if LIVE_TERMINAL:
                    def on_output(event):
                        # Thread-safe send back to websocket
                        try:
                            loop = asyncio.new_event_loop()
                            loop.run_until_complete(websocket.send(json.dumps(event)))
                            loop.close()
                        except Exception:
                            pass

                    proc = LiveProcess(
                        command=final_cmd,
                        tool=tool,
                        target=intent.get("target") or "",
                        output_callback=on_output,
                        teach_mode=(teach_flag or intent.get("teach", False))
                    )
                    proc.start()

                else:
                    # Fallback: non-streaming shell (Windows dev mode)
                    result = run_shell(final_cmd, timeout=120)
                    for line in result["stdout"].split("\n"):
                        if line.strip():
                            await websocket.send(json.dumps({"type":"output","data":line}))
                    await websocket.send(json.dumps({"type":"system","data":"[ERR0RS] Done (non-streaming mode)."}))

    except Exception as e:
        try:
            await websocket.send(json.dumps({"type":"error","data":str(e)}))
        except Exception:
            pass
    finally:
        if proc and proc.is_running:
            proc.terminate()
        _ws_clients.pop(session_id, None)


def start_ws_server():
    """Start the WebSocket server in its own thread/event loop"""
    if not WEBSOCKETS_OK:
        print("[ERR0RS] WebSocket server disabled — pip3 install websockets")
        return

    async def _serve():
        async with websockets.serve(ws_terminal_handler, HOST, WS_PORT):
            print(f"[ERR0RS] WebSocket terminal → ws://{HOST}:{WS_PORT}")
            await asyncio.Future()  # run forever

    def _thread():
        asyncio.run(_serve())

    t = threading.Thread(target=_thread, daemon=True)
    t.start()


# ═══════════════════════════════════════════════════════════════════════════
# HTTP SERVER — all original endpoints preserved + new /api/ws_info
# ═══════════════════════════════════════════════════════════════════════════

class ERR0RSHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR.resolve()), **kwargs)

    def log_message(self, format, *args): pass

    def log_error(self, format, *args):
        msg = format % args if args else str(format)
        # Suppress noisy non-errors
        if any(x in msg for x in ["BrokenPipe","Errno 32","Errno 104"]): return
        # Suppress 404s — static files browser auto-requests (favicon, manifests, etc.)
        # SimpleHTTPRequestHandler uses: "code 404, message File not found"
        if "404" in msg: return
        print(f"[ERR0RS] {msg}")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200); self.end_headers()

    def do_GET(self):
        try:
            if self.path == "/api/status":   self._json(self._status())
            elif self.path == "/api/phases": self._json(self._phases())
            elif self.path == "/api/tools":  self._json(self._tools_list())
            elif self.path == "/api/ws_info":
                self._json({"ws_url": f"ws://{HOST}:{WS_PORT}",
                            "ws_available": WEBSOCKETS_OK,
                            "live_terminal": LIVE_TERMINAL})
            elif self.path == "/api/payload_studio/snippets":
                self._payload_snippets()
            # ── Terminal Bridge GET routes ─────────────────────────────────
            elif self.path == "/api/tool/registry":
                if TERMINAL_BRIDGE:
                    self._json(load_tool_registry())
                else:
                    self._json({"error": "Terminal Bridge not loaded"})
            elif self.path.startswith("/api/tool/panel/"):
                if TERMINAL_BRIDGE:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(self.path)
                    tool   = parsed.path.split("/")[-1]
                    qs     = parse_qs(parsed.query)
                    target = qs.get("target", [""])[0]
                    self._json(get_tool_panel_data(tool, target))
                else:
                    self._json({"error": "Terminal Bridge not loaded"})
            elif self.path.startswith("/api/tool/preset"):
                if TERMINAL_BRIDGE:
                    from urllib.parse import urlparse, parse_qs
                    qs     = parse_qs(urlparse(self.path).query)
                    tool   = qs.get("tool",   [""])[0]
                    preset = qs.get("preset", [""])[0]
                    target = qs.get("target", [""])[0]
                    self._json(get_preset_command(tool, preset, target))
                else:
                    self._json({"error": "Terminal Bridge not loaded"})
            else: super().do_GET()
        except (BrokenPipeError, ConnectionResetError): pass

    def do_POST(self):
        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            payload = json.loads(body) if body else {}

            if self.path == "/api/command":
                cmd = payload.get("command","").strip()
                self._json(route_command(cmd) if cmd else {"error":"empty command"})

            elif self.path == "/api/tool":
                tool   = payload.get("tool","").strip()
                target = payload.get("target","").strip()
                params = payload.get("params",{})
                if not tool: self._json({"error":"no tool"}); return
                self._json(run_tool_async(tool,target,params) if FRAMEWORK_LOADED and target
                           else run_shell(f"{tool} {target}", timeout=120))

            elif self.path == "/api/shell":
                cmd     = payload.get("cmd","").strip()
                timeout = payload.get("timeout",60)
                self._json(run_shell(cmd,timeout) if cmd else {"error":"no cmd"})

            # ── Terminal Bridge POST routes ────────────────────────────────
            elif self.path == "/api/terminal/launch":
                if TERMINAL_BRIDGE:
                    tool    = payload.get("tool","").strip()
                    target  = payload.get("target","").strip()
                    flags   = payload.get("flags", [])
                    fvals   = payload.get("flag_values", {})
                    command = payload.get("command") or build_command_from_flags(tool, target, flags, fvals)
                    spawn_result = spawn_terminal_with_command(command, tool)
                    self._json({
                        "status":  "launched" if "pid" in spawn_result else "error",
                        "command": command,
                        "tool":    tool,
                        "target":  target,
                        "terminal_info": spawn_result,
                        "panel":   get_tool_panel_data(tool, target),
                    })
                else:
                    self._json({"error": "Terminal Bridge not loaded"})

            elif self.path == "/api/terminal/fire":
                if TERMINAL_BRIDGE:
                    command = payload.get("command","").strip()
                    tool    = payload.get("tool","")
                    if not command:
                        self._json({"error": "no command"}); return
                    result = spawn_terminal_with_command(command, tool)
                    self._json({"status": "fired", "result": result})
                else:
                    self._json({"error": "Terminal Bridge not loaded"})

            elif self.path == "/api/teach":
                query = payload.get("query","").strip()
                if TEACH_ENGINE:
                    self._json(handle_teach_request(query))
                else:
                    self._json({"status":"error","stdout":"Teach engine not loaded"})

            elif self.path == "/api/payload_studio/explain":
                line  = payload.get("line","").strip()
                self._json(self._explain_line(line))

            elif self.path == "/api/payload_studio/suggest":
                code  = payload.get("code","")
                plat  = payload.get("platform","windows")
                last  = payload.get("last_line","")
                self._json(self._get_suggestions(code, plat, last))

            elif self.path == "/api/payload_studio/validate":
                code  = payload.get("code","")
                self._json(self._validate_ducky(code))

            elif self.path == "/api/payload_studio/spin_server":
                self._json(self._spin_server(payload))

            elif self.path == "/api/payload_studio/stop_server":
                stype = payload.get("type","")
                self._json(self._stop_server(stype))

            # ── Payload Studio: AI generate endpoint ─────────────────────────
            elif self.path == "/api/payload_studio/generate":
                self._json(self._generate_payload(payload))

            # ── Payload Studio: DuckyScript → CircuitPython convert ───────────
            elif self.path == "/api/payload_studio/convert":
                self._json(self._convert_payload(payload))

            # ── RP2040 / Pico BadUSB Programmer ──────────────────────────────
            elif self.path == "/api/rp2040":
                self._json(self._rp2040_handler(payload))

            elif self.path == "/api/rocketgod":
                try:
                    from src.tools.rocketgod import handle_rocketgod_request
                    self._json(handle_rocketgod_request(payload))
                except Exception as e:
                    self._json({"status":"error","error":str(e)})

            elif self.path == "/api/badusb":
                try:
                    from src.tools.badusb import route_badusb
                    self._json(route_badusb(payload))
                except Exception as e:
                    self._json({"status":"error","error":str(e)})

            elif self.path == "/api/ollama":
                self._json(query_ollama(payload.get("prompt","").strip()))

            elif self.path == "/api/wizard":
                # Direct wizard request: { "tool": "nmap" }  OR  { "command": "scan for open ports" }
                tool = payload.get("tool", "").strip().lower()
                cmd  = payload.get("command", "").strip()
                if WIZARD_ENGINE:
                    if tool:
                        w = build_wizard_response(tool)
                    elif cmd:
                        key = detect_wizard(cmd)
                        w   = build_wizard_response(key) if key else None
                    else:
                        w = None
                    if w:
                        self._json({"status": "wizard", **w})
                    else:
                        self._json({"status": "error", "error": f"No wizard for: {tool or cmd}"})
                else:
                    self._json({"status": "error", "error": "Wizard engine not loaded"})

            elif self.path == "/api/wizard/run":
                # Execute a wizard option: { "tool": "nmap", "cmd": "nmap -F {target}", "target": "192.168.1.1" }
                tool   = payload.get("tool", "").strip()
                cmd    = payload.get("cmd", "").strip()
                target = payload.get("target", "").strip()
                if WIZARD_ENGINE and cmd:
                    final_cmd = apply_target(cmd, target) if target else cmd
                    self._json(run_shell(final_cmd, timeout=120))
                else:
                    self._json({"status": "error", "error": "Missing cmd or wizard engine not loaded"})

            elif self.path == "/api/flipper":
                action = payload.get("action", "studio")
                # Route evolution actions to the new Evolution Engine
                if action in ("evolve","detect","status","watch","level_up","upgrade"):
                    if FLIPPER_ENGINE:
                        self._json(run_flipper_evolution(action, payload))
                    else:
                        self._json({"status":"error","error":"Flipper Evolution Engine not loaded — check flipper_evolution.py"})
                elif FLIPPER_ENGINE:
                    # Legacy: BadUSB studio actions go to the old handler
                    self._json(handle_flipper_request(payload))
                else:
                    self._json({"status":"error","error":"Flipper engine not loaded"})

            elif self.path == "/api/flipper/evolve":
                # Convenience endpoint — always runs full evolution
                if FLIPPER_ENGINE:
                    self._json(run_flipper_evolution("evolve", payload))
                else:
                    self._json({"status":"error","error":"Flipper Evolution Engine not loaded"})

            elif self.path == "/api/flipper/status":
                # Quick status poll for the UI dashboard
                if FLIPPER_ENGINE:
                    self._json(run_flipper_evolution("status", payload))
                else:
                    self._json({"status":"ok","flipper_connected":False,"engine_loaded":False})

            elif self.path == "/api/hailo":
                if HAILO_ENGINE:
                    self._json(handle_hailo_request(payload))
                else:
                    self._json({
                        "status": "error",
                        "error":  "Hailo NPU module not loaded",
                        "fix":    "sudo bash scripts/install_hailo.sh",
                    })

            elif self.path == "/api/brain":
                # ERR0RS Native AI Brain — replaces mr7 entirely, 100% local
                if BRAIN_ENGINE:
                    self._json(handle_brain_request(payload))
                else:
                    self._json({"status":"error","error":"Brain engine not loaded — check Ollama"})

            elif self.path == "/api/bas":
                if BAS_ENGINE:
                    self._json(handle_bas_request(payload))
                else:
                    self._json({"status":"error","error":"BAS engine not loaded"})

            elif self.path == "/api/compliance":
                if COMPLIANCE_ENGINE:
                    self._json(handle_compliance_request(payload))
                else:
                    self._json({"status":"error","error":"Compliance mapper not loaded"})

            elif self.path == "/api/blue_team":
                # auto_harden / generate_report / pcap_interpreter
                if BLUE_TEAM_ENGINE:
                    self._json(handle_blue_team_request(payload))
                else:
                    self._json({"status":"error","error":"Blue Team toolkit not loaded"})

            elif self.path == "/api/harden":
                # Convenience alias: POST {"finding": "port 3306 open"} → remediation cmd
                if BLUE_TEAM_ENGINE:
                    finding = payload.get("finding", "").strip()
                    if not finding:
                        self._json({"status":"error","error":"No finding provided"})
                    else:
                        result = auto_harden(finding,
                                             prefer_ufw=payload.get("prefer_ufw", True))
                        self._json({"status":"ok", **result})
                else:
                    self._json({"status":"error","error":"Blue Team toolkit not loaded"})

            elif self.path == "/api/report":
                # Convenience alias: POST {"hours": 1, "client_name": "ACME"} → PDF audit
                if BLUE_TEAM_ENGINE:
                    result = generate_report(
                        hours         = payload.get("hours", 1),
                        output_path   = payload.get("output_path"),
                        client_name   = payload.get("client_name", "Confidential"),
                        tester_name   = payload.get("tester_name", "ERR0RS"),
                        include_harden= payload.get("include_harden", True),
                    )
                    self._json({"status":"ok", **result})
                else:
                    self._json({"status":"error","error":"Blue Team toolkit not loaded"})

            elif self.path == "/api/campaign":
                if CAMPAIGN_ENGINE:
                    self._json(handle_campaign_command(
                        payload.get("cmd","status"), payload
                    ))
                else:
                    self._json({"status":"error","error":"Campaign Manager not loaded"})

            elif self.path == "/api/killchain":
                if KILLCHAIN_ENGINE:
                    self._json(handle_killchain_command(payload))
                else:
                    self._json({"status":"error","error":"Kill Chain engine not loaded"})

            elif self.path == "/api/pro_report":
                if PRO_REPORTER:
                    self._json(handle_report_command(payload))
                else:
                    self._json({"status":"error","error":"Professional Reporter not loaded"})

            elif self.path == "/api/credentials":
                if CRED_ENGINE:
                    action = payload.get("action","summary")
                    if action == "add":
                        e = cred_engine.add(**{k:v for k,v in payload.items() if k != "action"})
                        from dataclasses import asdict
                        self._json({"status":"ok","entry": asdict(e)})
                    elif action == "crack":
                        self._json({"status":"ok","result": cred_engine.crack_all(
                            payload.get("wordlist","/usr/share/wordlists/rockyou.txt")
                        )})
                    elif action == "spray":
                        self._json({"status":"ok","result": cred_engine.spray(
                            payload.get("targets",[]),
                            payload.get("service","smb"),
                        )})
                    elif action == "bulk":
                        n = cred_engine.add_bulk(
                            payload.get("lines",[]),
                            payload.get("source",""),
                        )
                        self._json({"status":"ok","added": n})
                    elif action == "analyze":
                        self._json({"status":"ok","analysis": cred_engine.analyze_patterns()})
                    else:
                        self._json({"status":"ok","summary": cred_engine.summary()})
                else:
                    self._json({"status":"error","error":"Credential Engine not loaded"})

            elif self.path == "/api/se":
                if SE_ENGINE:
                    self._json(handle_se_command(
                        payload.get("command","list"),
                        payload.get("params",{}),
                    ))
                else:
                    self._json({"status":"error","error":"SE Engine not loaded"})

            elif self.path == "/api/ai_threat":
                if AI_THREAT_ENGINE:
                    self._json(handle_ai_threat_command(
                        payload.get("command","list"),
                        payload.get("params",{}),
                    ))
                else:
                    self._json({"status":"error","error":"AI Threat Engine not loaded"})

            elif self.path == "/api/soc":
                action = payload.get("action","").strip()
                soc_cmds = {
                    "failed-logins": "grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -30 || journalctl _SYSTEMD_UNIT=sshd 2>/dev/null | grep Failed | tail -30",
                    "active-conns":  "ss -tulpn && netstat -an 2>/dev/null | grep ESTABLISHED | head -30",
                    "open-ports":    "ss -tulpn | grep LISTEN",
                    "running-procs": "ps aux --sort=-%cpu | head -30",
                    "log-tail":      "tail -n 50 /var/log/auth.log /var/log/syslog 2>/dev/null || journalctl -n 50",
                    "who-online":    "who && last | head -20 && w",
                    "sudo-log":      "grep sudo /var/log/auth.log 2>/dev/null | tail -20 || journalctl | grep sudo | tail -20",
                    "firewall-rules":"iptables -L -n -v 2>/dev/null || ufw status verbose 2>/dev/null",
                    "cron-jobs":     "crontab -l 2>/dev/null; ls -la /etc/cron* 2>/dev/null",
                    "dns-cache":     "resolvectl statistics 2>/dev/null; cat /etc/hosts",
                    "volatility":    "volatility3 --info 2>/dev/null || echo 'volatility3 not installed'",
                }
                cmd = soc_cmds.get(action)
                if cmd:
                    result = run_shell(cmd, timeout=15)
                    # Auto-attach hardening recommendation if blue team engine available
                    if BLUE_TEAM_ENGINE and result.get("stdout"):
                        harden = auto_harden(action.replace("-", " ") + " " + result["stdout"][:200])
                        if harden.get("command"):
                            result["harden_cmd"]      = harden["command"]
                            result["harden_severity"] = harden["severity"]
                            result["harden_note"]     = harden["note"]
                            result["cis_ref"]         = harden.get("cis")
                    self._json(result)
                else:
                    self._json({"status":"error","error":f"Unknown SOC action: {action}"})

            else:
                self.send_response(404); self.end_headers()

        except (BrokenPipeError, ConnectionResetError): pass
        except Exception as e:
            try: self._json({"error":str(e)}, code=500)
            except Exception: pass

    def _json(self, data: dict, code: int = 200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── Payload Studio helpers ────────────────────────
    def _payload_snippets(self):
        try:
            from src.tools.payload_studio.snippets import SNIPPETS
            self._json({"status":"ok","snippets":SNIPPETS})
        except Exception as e:
            self._json({"status":"error","error":str(e)})

    def _explain_line(self, line: str) -> dict:
        try:
            from src.tools.payload_studio.payload_engine import get_line_explanation
            return {"status":"ok","explanation":get_line_explanation(line)}
        except Exception as e:
            return {"status":"error","error":str(e)}

    def _get_suggestions(self, code: str, platform: str, last_line: str) -> dict:
        try:
            from src.tools.payload_studio.payload_engine import get_suggestions
            sugs = get_suggestions(code, platform, last_line)
            return {"status":"ok","suggestions":sugs}
        except Exception as e:
            return {"status":"error","suggestions":[]}

    def _validate_ducky(self, code: str) -> dict:
        valid_cmds = {"REM","STRING","STRINGLN","DELAY","GUI","CTRL","ALT","SHIFT",
                      "ENTER","BACKSPACE","TAB","ESCAPE","DELETE","UPARROW","DOWNARROW",
                      "LEFTARROW","RIGHTARROW","HOME","END","PAGEUP","PAGEDOWN",
                      "CAPSLOCK","PRINTSCREEN","MENU","SPACE","WAIT_FOR_BUTTON_PRESS",
                      "HOLD","RELEASE","REPEAT","VAR","IF","WHILE","DEFINE",
                      "DEFAULT_DELAY","LOCALE","F1","F2","F3","F4","F5","F6",
                      "F7","F8","F9","F10","F11","F12"}
        errors = []
        for i, line in enumerate(code.split("\n"), 1):
            t = line.strip()
            if not t: continue
            cmd = t.split()[0].upper()
            if cmd not in valid_cmds:
                errors.append({"line":i,"msg":f"Unknown command: {cmd}"})
            if cmd == "DELAY":
                parts = t.split()
                if len(parts) < 2 or not parts[1].isdigit():
                    errors.append({"line":i,"msg":"DELAY requires a number (e.g. DELAY 500)"})
        return {"status":"ok","valid":len(errors)==0,"errors":errors,"line_count":len(code.split("\n"))}

    def _spin_server(self, payload: dict) -> dict:
        """Start a listener or HTTP server for a BadUSB/Flipper payload."""
        server_type = payload.get("type", "")
        port        = str(payload.get("port", "4444"))

        SERVER_CONFIGS = {
            "nc_listener": {
                "cmd":   ["nc", "-lvnp", port],
                "label": f"Netcat reverse-shell listener on :{port}",
            },
            "http_server": {
                "cmd":   ["python3", "-m", "http.server", port],
                "label": f"Python HTTP payload server on :{port}",
            },
        }

        cfg = SERVER_CONFIGS.get(server_type)
        if not cfg:
            return {"status": "error", "error": f"Unknown server type: {server_type}"}

        # Kill previous instance of same type if still alive
        old = _ACTIVE_SERVERS.get(server_type)
        if old and old.poll() is None:
            old.terminate()

        try:
            proc = subprocess.Popen(
                cfg["cmd"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            _ACTIVE_SERVERS[server_type] = proc
            return {
                "status": "ok",
                "type":   server_type,
                "port":   port,
                "pid":    proc.pid,
                "label":  cfg["label"],
                "cmd":    " ".join(cfg["cmd"]),
            }
        except FileNotFoundError:
            return {"status": "error", "error": f"'{cfg['cmd'][0]}' not found — is it installed?"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _stop_server(self, server_type: str) -> dict:
        proc = _ACTIVE_SERVERS.get(server_type)
        if not proc:
            return {"status": "error", "error": "No active server of that type"}
        try:
            proc.terminate()
            _ACTIVE_SERVERS.pop(server_type, None)
            return {"status": "ok", "stopped": server_type}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    # ── AI Payload Generator ──────────────────────────────────────────────────
    def _generate_payload(self, payload: dict) -> dict:
        """
        POST /api/payload_studio/generate
        Body: { "description": "wifi harvester", "target_os": "windows",
                "output_format": "duckyscript" }
        """
        try:
            from src.tools.badusb_studio.payload_generator import PayloadGenerator
            pg = PayloadGenerator()
            description   = payload.get("description", "").strip()
            target_os     = payload.get("target_os", "windows").strip()
            output_format = payload.get("output_format", "duckyscript").strip()
            if not description:
                return {"status": "error", "error": "description required"}
            script = pg.generate(description, target_os=target_os,
                                 output_format=output_format)
            return {
                "status":  "ok",
                "script":  script,
                "target_os": target_os,
                "format":  output_format,
                "lines":   len(script.splitlines()),
                "ai_used": pg._ollama_available,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── DuckyScript → CircuitPython converter ─────────────────────────────────
    def _convert_payload(self, payload: dict) -> dict:
        """
        POST /api/payload_studio/convert
        Body: { "code": "<duckyscript>", "target": "circuitpython" }
        Returns converted CircuitPython code ready to drop on CIRCUITPY drive.
        """
        try:
            from src.tools.badusb_studio.ducky_converter import DuckyConverter
            code   = payload.get("code", "").strip()
            target = payload.get("target", "circuitpython").strip()
            if not code:
                return {"status": "error", "error": "code required"}
            dc     = DuckyConverter()
            result = dc.convert(code, target=target)
            return result   # already {"status","output","target","lines"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── RP2040 / Pico BadUSB Programmer ───────────────────────────────────────
    def _rp2040_handler(self, payload: dict) -> dict:
        """
        POST /api/rp2040
        Body: { "action": "detect|flash_ducky|flash_circuitpython|flash_uf2|
                           wait|templates|get_template",
                "code":     "<duckyscript or circuitpython>",
                "filename": "code.py",
                "uf2_path": "/path/to/firmware.uf2",
                "template": "wifi_harvest",
                "timeout":  30 }
        """
        try:
            from src.tools.badusb_studio.rp2040_flasher import RP2040Flasher
            from src.tools.badusb_studio.ducky_converter import DuckyConverter
            from src.tools.badusb_studio.payload_generator import PayloadGenerator

            action  = payload.get("action", "detect").strip()
            flasher = RP2040Flasher()

            # ── detect ────────────────────────────────────────────────────────
            if action == "detect":
                info = flasher.get_device_info()
                status = flasher.detect_any_rp2040()
                return {"status": "ok", "device": status, "info": info}

            # ── flash DuckyScript payload (auto-converts to CircuitPython) ───
            elif action == "flash_ducky":
                code = payload.get("code", "").strip()
                if not code:
                    return {"status": "error", "error": "code required"}
                # Auto-detect drive mode: prefer pico-ducky (drop payload.txt),
                # fall back to CIRCUITPY (convert → CircuitPython)
                pico_drive = flasher.find_pico_ducky()
                if pico_drive:
                    result = flasher.flash_duckyscript_payload(code)
                    result["mode"] = "pico-ducky (payload.txt)"
                    return {"status": "ok" if result["success"] else "error", **result}
                else:
                    circ_drive = flasher.find_circuitpy()
                    if circ_drive:
                        dc = DuckyConverter()
                        conv = dc.convert(code, target="circuitpython")
                        if conv["status"] != "ok":
                            return conv
                        result = flasher.flash_circuitpython_payload(
                            conv["output"],
                            filename=payload.get("filename", "code.py")
                        )
                        result["mode"] = "circuitpython (converted)"
                        result["converted_lines"] = conv["lines"]
                        return {"status": "ok" if result["success"] else "error", **result}
                    else:
                        return {
                            "status": "error",
                            "error": "No RP2040 found. Hold BOOTSEL and plug in USB, "
                                     "or connect a flashed Pico.",
                            "hint": "Need firmware? Use action=flash_uf2 first."
                        }

            # ── flash raw CircuitPython code ──────────────────────────────────
            elif action == "flash_circuitpython":
                code     = payload.get("code", "").strip()
                filename = payload.get("filename", "code.py")
                if not code:
                    return {"status": "error", "error": "code required"}
                result = flasher.flash_circuitpython_payload(code, filename)
                return {"status": "ok" if result["success"] else "error", **result}

            # ── flash UF2 firmware ────────────────────────────────────────────
            elif action == "flash_uf2":
                uf2_path = payload.get("uf2_path", "").strip()
                if not uf2_path:
                    # List available UF2s from firmware dir
                    from pathlib import Path
                    fw_dir = Path(__file__).resolve().parents[2] / \
                             "src/tools/badusb_studio/firmware"
                    uf2s = list(fw_dir.glob("*.uf2"))
                    if not uf2s:
                        return {
                            "status": "error",
                            "error": "No UF2 firmware found.",
                            "hint": "Place .uf2 files in src/tools/badusb_studio/firmware/. "
                                    "Download pico-ducky from: "
                                    "https://github.com/dbisu/pico-ducky/releases"
                        }
                    return {"status": "ok", "available_firmware": [f.name for f in uf2s]}
                result = flasher.flash_uf2(uf2_path)
                return {"status": "ok" if result["success"] else "error", **result}

            # ── wait for device to appear ─────────────────────────────────────
            elif action == "wait":
                mode    = payload.get("mode", "any")
                timeout = int(payload.get("timeout", 30))
                result  = flasher.wait_for_device(mode=mode, timeout=timeout)
                return {"status": "ok", "result": result}

            # ── list payload templates ────────────────────────────────────────
            elif action == "templates":
                pg = PayloadGenerator()
                return {"status": "ok", "templates": pg.list_templates()}

            # ── get specific template ─────────────────────────────────────────
            elif action == "get_template":
                key = payload.get("template", "").strip()
                pg  = PayloadGenerator()
                script = pg.get_template(key)
                if script:
                    return {"status": "ok", "template": key, "script": script}
                return {"status": "error", "error": f"Template not found: {key}"}

            else:
                return {"status": "error", "error": f"Unknown action: {action}",
                        "valid_actions": ["detect","flash_ducky","flash_circuitpython",
                                          "flash_uf2","wait","templates","get_template"]}

        except Exception as e:
            import traceback
            return {"status": "error", "error": str(e),
                    "traceback": traceback.format_exc().splitlines()[-3:]}

    def _status(self) -> dict:
        import urllib.request as ur
        ollama_ok, ollama_models = False, []
        try:
            with ur.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
                data = json.loads(r.read())
                ollama_models = [m["name"] for m in data.get("models",[])]
                ollama_ok = bool(ollama_models)
        except Exception: pass
        mcp_ok = subprocess.run(["which","mcp-server"],capture_output=True).returncode == 0
        return {"version":"3.0","framework":FRAMEWORK_LOADED,"ollama":ollama_ok,
                "ollama_models":ollama_models,"mcp":mcp_ok,"shell_access":True,
                "live_terminal":LIVE_TERMINAL,"websocket":WEBSOCKETS_OK,
                "ws_port":WS_PORT,"uptime":_uptime(),"platform":_platform(),
                "campaign_engine":  CAMPAIGN_ENGINE,
                "killchain_engine": KILLCHAIN_ENGINE,
                "pro_reporter":     PRO_REPORTER,
                "cred_engine":      CRED_ENGINE,
                "se_engine":        SE_ENGINE,
                "ai_threat_engine": AI_THREAT_ENGINE,
                "postex_engine":    POSTEX_ENGINE,
                "wireless_engine":  WIRELESS_ENGINE,
                "social_engine":    SOCIAL_ENGINE,
                "cloud_engine":     CLOUD_ENGINE,
                "ctf_engine":       CTF_ENGINE,
                "opsec_engine":     OPSEC_ENGINE,
                "blue_team_engine": BLUE_TEAM_ENGINE,
                "teach_engine":     TEACH_ENGINE,
                "hailo_engine":     HAILO_ENGINE,
                "hailo_npu":        hailo_available() if HAILO_ENGINE else False,
                "hailo_status":     hailo_status_line() if HAILO_ENGINE else "not loaded",
                "flipper_engine":   FLIPPER_ENGINE if 'FLIPPER_ENGINE' in globals() else False}

    def _phases(self) -> dict:
        return {"phases":[
            {"id":1,"name":"RECON","status":"done"},
            {"id":2,"name":"SCANNING","status":"active"},
            {"id":3,"name":"ENUMERATION","status":"pending"},
            {"id":4,"name":"EXPLOITATION","status":"pending"},
            {"id":5,"name":"POST-EXPLOIT","status":"pending"},
            {"id":6,"name":"REPORTING","status":"pending"},
        ]}

    def _tools_list(self) -> dict:
        tools = ["nmap","nikto","gobuster","sqlmap","hydra","hashcat",
                 "subfinder","nuclei","amass","metasploit","wpscan",
                 "crackmapexec","enum4linux","dirb","ffuf","wfuzz"]
        available = []
        for t in tools:
            binary = "msfconsole" if t == "metasploit" else t
            available.append({"name":t,
                "available":subprocess.run(["which",binary],capture_output=True).returncode==0})
        return {"tools":available}


# ── Utilities ─────────────────────────────────────────────────────────────────
def _uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        h,r = divmod(secs,3600); m,s = divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception: return "N/A"

def _platform() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            cpu = f.read()
        if "Raspberry Pi" in cpu:
            # Read actual RAM from /proc/meminfo
            try:
                with open("/proc/meminfo") as m:
                    kb = int(m.readline().split()[1])
                gb = round(kb / 1024 / 1024)
            except Exception:
                gb = 8
            return f"Raspberry Pi 5 {gb}GB"
    except Exception: pass
    return "Kali Linux"

def check_ollama():
    import urllib.request, json as j, os
    _m = os.getenv("OLLAMA_MODEL", "")
    if not _m:
        try:
            with open("/proc/cpuinfo") as f:
                _m = "qwen2.5-coder:7b" if "Raspberry Pi" in f.read() else "qwen2.5-coder:32b"
        except Exception:
            _m = "qwen2.5-coder:32b"
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags",timeout=2) as r:
            models = [m["name"] for m in j.loads(r.read()).get("models",[])]
            if models: print(f"[ERR0RS] Ollama connected: {', '.join(models)}"); return True
        print(f"[ERR0RS] Ollama running but no models → ollama pull {_m}")
    except Exception:
        print(f"[ERR0RS] Ollama offline → sudo systemctl start ollama && ollama pull {_m}")
    return False

def check_ws_deps():
    if not WEBSOCKETS_OK:
        print("[ERR0RS] Install WebSocket support → pip3 install websockets")
        return False
    print(f"[ERR0RS] WebSocket ready → ws://{HOST}:{WS_PORT}")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# BOOT
# ═══════════════════════════════════════════════════════════════════════════

def _free_port(port: int):
    """Kill any process holding the given TCP port so ERR0RS can always restart cleanly."""
    import socket, signal
    try:
        import subprocess as _sp
        result = _sp.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True
        )
        pids = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        for pid_str in pids:
            try:
                pid = int(pid_str)
                if pid != os.getpid():
                    os.kill(pid, signal.SIGTERM)
                    print(f"[ERR0RS] Freed port {port} — killed stale PID {pid}")
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        if pids:
            import time as _t; _t.sleep(0.6)   # brief grace period
    except Exception:
        pass


def start_server():
    if not UI_DIR.exists() or not (UI_DIR/"index.html").exists():
        print(f"[ERR0RS] ERROR: UI not found at {UI_DIR}"); sys.exit(1)

    # Auto-free ports before binding — handles zombie ERR0RS processes
    _free_port(HTTP_PORT)
    _free_port(WS_PORT)

    # ── Boot the persistent operator terminal on the desktop ──────────────────
    if LIVE_TERMINAL:
        try:
            from src.core.live_terminal import OperatorTerminal
            _ot = OperatorTerminal.instance()
            if not _ot.is_alive():
                threading.Thread(target=_ot.spawn, daemon=True,
                                 name="operator-terminal").start()
                print("[ERR0RS] 🖥️  Operator terminal spawning on desktop...")
            else:
                print("[ERR0RS] 🖥️  Operator terminal already running")
        except Exception as _ote:
            print(f"[ERR0RS] Operator terminal unavailable: {_ote}")

    # SO_REUSEADDR — survive port-in-use after a crash/restart
    import socket
    class ReusableHTTPServer(HTTPServer):
        allow_reuse_address = True
        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            super().server_bind()

    server = ReusableHTTPServer((HOST, HTTP_PORT), ERR0RSHandler)
    url    = f"http://{HOST}:{HTTP_PORT}"
    print(f"[ERR0RS] Dashboard   → {url}")
    print(f"[ERR0RS] HTTP API    → {url}/api/command")
    print(f"[ERR0RS] Teach API   → {url}/api/teach")
    print(f"[ERR0RS] Shell API   → {url}/api/shell")
    if WEBSOCKETS_OK:
        print(f"[ERR0RS] Live Term   → ws://{HOST}:{WS_PORT}")
    print(f"[ERR0RS] Ctrl+C to stop\n")

    # ── HTTP server in background daemon thread ───────────────────────────────
    http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    http_thread.start()

    # ── WebSocket server in background daemon thread ──────────────────────────
    start_ws_server()

    # ── Flipper watcher in background (non-blocking daemon) ───────────────────
    # Singleton guard — check both thread names AND a module-level flag
    if not getattr(start_flipper_watcher, '_started', False):
        running = [t.name for t in threading.enumerate()]
        if FLIPPER_ENGINE and callable(start_flipper_watcher) and "flipper-watcher" not in running:
            start_flipper_watcher()
            start_flipper_watcher._started = True

    # ── Open browser (ARM64-safe — avoid stale Chromium flags) ───────────────
    try:
        import shutil, subprocess as _sp
        _opened = False
        # Try browsers in order, suppress flag errors with stderr redirect
        for _br in ["firefox", "chromium", "chromium-browser", "epiphany"]:
            if shutil.which(_br):
                _sp.Popen(
                    [_br, url],
                    stdout=_sp.DEVNULL,
                    stderr=_sp.DEVNULL,
                    start_new_session=True
                )
                _opened = True
                break
        if not _opened:
            webbrowser.open(url)
    except Exception:
        pass

    # ── Block main thread with clean Ctrl+C handling ──────────────────────────
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[ERR0RS] Shutdown. Stay safe operator.")
        server.shutdown()


def main():
    O='\033[0;33m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
    print(f"""
{O}  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗{N}
{O}  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝{N}
{Y}  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗{N}
{Y}  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║{N}
{R}  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║{N}
{R}  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝{N}
{C}        AI PENTEST ASSISTANT + INSTRUCTOR  v3.0{N}
{O}  ═══════════════════════════════════════════════════{N}
  {C}Root:{N}       {ROOT_DIR}
  {C}HTTP:{N}       http://{HOST}:{HTTP_PORT}
  {C}WebSocket:{N}  ws://{HOST}:{WS_PORT}
  {C}Live Term:{N}  {'YES - PTY streaming' if LIVE_TERMINAL else 'NO - install on Linux'}
  {C}WebSockets:{N} {'YES' if WEBSOCKETS_OK else 'NO - pip3 install websockets'}
  {C}Teach Engine:{N}{'YES - 13 topics offline' if TEACH_ENGINE else 'NO'}
{O}  ═══════════════════════════════════════════════════{N}
""")
    check_ollama()
    check_ws_deps()
    start_server()


if __name__ == "__main__":
    main()
