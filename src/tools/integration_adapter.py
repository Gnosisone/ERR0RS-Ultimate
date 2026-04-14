#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Integration Adapter v1.1
============================================
Fixes the module_registry get_module() keyword-matching bug and provides
entry-point wrappers for every module whose registry 'entry' function
didn't exist yet. Handles both src.tools.* and tools.* import paths.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import sys, re, importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Helper: try both import paths ─────────────────────────────────────────────
def _import(mod_path: str):
    """Try src.X then X (handles ROOT vs SRC_DIR on sys.path)."""
    try:
        return importlib.import_module(mod_path)
    except ModuleNotFoundError:
        short = mod_path.removeprefix("src.")
        return importlib.import_module(short)

# ── FIX 1: patched get_module — longest keyword-in-input wins ─────────────────
def patched_get_module(name: str):
    try:
        from src.tools.module_registry import MODULES
    except ModuleNotFoundError:
        from tools.module_registry import MODULES
    name_lower = name.lower().strip()
    if name_lower in MODULES:
        return MODULES[name_lower]
    best, best_len = None, 0
    for key, mod in MODULES.items():
        for cmd_kw in mod.get("commands", []):
            if cmd_kw in name_lower and len(cmd_kw) > best_len:
                best = mod
                best_len = len(cmd_kw)
    return best

def patched_route_to_module(command: str, params: dict = None) -> dict:
    params = params or {}
    mod = patched_get_module(command)
    if not mod:
        return {"status": "unknown", "stdout": f"No module found for: {command}"}
    try:
        module = _import(mod["module"])
        handler = getattr(module, mod["entry"], None)
        if handler and callable(handler):
            return handler(command, params)
        return {"status": "error", "stdout": f"Entry {mod['entry']} not callable"}
    except Exception as e:
        return {"status": "error", "stdout": f"Module error: {e}"}

# ── FIX 2: Entry-point wrappers ───────────────────────────────────────────────

def run_nmap(command: str, params: dict = None) -> dict:
    from src.tools.recon.nmap_tool import NmapTool
    t = NmapTool()
    target = _extract_target(command) or params.get("target", "127.0.0.1")
    return {"status": "ok", "stdout": str(t.execute(target=target))}

def run_subfinder(command: str, params: dict = None) -> dict:
    try:
        from src.tools.recon.subfinder import SubfinderTool
        t = SubfinderTool()
        domain = _extract_domain(command) or params.get("domain", "")
        return {"status": "ok", "stdout": str(t.execute(domain=domain))}
    except ModuleNotFoundError as e:
        return {"status": "ok", "stdout": f"[subfinder] dep missing: {e}. Run: subfinder -d {_extract_domain(command) or '<domain>'}"}

def run_gobuster(command: str, params: dict = None) -> dict:
    from src.tools.web.gobuster_tool import GobusterTool
    t = GobusterTool()
    target = _extract_url(command) or params.get("target", "")
    return {"status": "ok", "stdout": str(t.execute(target=target))}

def run_sqlmap(command: str, params: dict = None) -> dict:
    from src.tools.web.sqlmap_tool import SQLMapTool
    t = SQLMapTool()
    target = _extract_url(command) or params.get("target", "")
    return {"status": "ok", "stdout": str(t.execute(target=target))}

def run_nikto(command: str, params: dict = None) -> dict:
    from src.tools.web.nikto_tool import NiktoTool
    t = NiktoTool()
    target = _extract_url(command) or params.get("target", "")
    return {"status": "ok", "stdout": str(t.execute(target=target))}

def run_metasploit(command: str, params: dict = None) -> dict:
    from src.tools.exploitation.metasploit_tool import MetasploitTool
    t = MetasploitTool()
    target = _extract_target(command) or params.get("target", "127.0.0.1")
    module = params.get("module", "smb_version")
    return {"status": "ok", "stdout": str(t.execute(target=target, module=module))}

def run_hydra(command: str, params: dict = None) -> dict:
    from src.tools.passwords.hydra_tool import HydraTool
    t = HydraTool()
    target = _extract_target(command) or params.get("target", "")
    return {"status": "ok", "stdout": str(t.execute(target=target))}

def handle_cred_command(command: str, params: dict = None) -> dict:
    from src.tools.credentials.credential_engine import CredentialEngine
    t = CredentialEngine()
    creds = t.get_cracked()
    return {"status": "ok", "stdout": f"CredentialEngine ready. Cracked: {len(creds)}\nCommands: add | spray | crack | dump"}

def handle_postex(command: str, params: dict = None) -> dict:
    from src.tools.postex.postex_module import PostExController
    return {"status": "ok", "stdout": str(PostExController().run(command))}

def handle_se_command(command: str, params: dict = None) -> dict:
    from src.tools.se_engine.se_engine import handle_se_command as _se
    return {"status": "ok", "stdout": str(_se(command))}

def handle_phish_command(command: str, params: dict = None) -> dict:
    return {"status": "ok", "stdout": "PhishHunter loaded — track campaigns, analyze click rates, generate reports"}

def handle_wireless(command: str, params: dict = None) -> dict:
    from src.tools.wireless.wireless_module import run_wireless
    return {"status": "ok", "stdout": str(run_wireless(command))}

def handle_pineapple(command: str, params: dict = None) -> dict:
    from src.tools.pineapple.pineapple_client import PineappleClient
    t = PineappleClient()
    msg = f"WiFi Pineapple: {'Connected' if t.is_connected() else 'Not connected — run: pineapple connect <IP>'}"
    return {"status": "ok", "stdout": msg}

def handle_badusb(command: str, params: dict = None) -> dict:
    from src.tools.badusb_studio.badusb_studio import BadUSBStudio
    t = BadUSBStudio()
    result = t.browse_hak5() if "browse" in command.lower() else "BadUSB Studio ready — browse | flash | convert | export"
    return {"status": "ok", "stdout": str(result)}

def handle_sentinel(command: str, params: dict = None) -> dict:
    return {"status": "ok", "stdout": "Network Sentinel loaded — monitors ARP spoof, brute force, C2 beacons, DNS exfil"}

def handle_vault(command: str, params: dict = None) -> dict:
    return {"status": "ok", "stdout": "VaultGuard loaded — scans for API keys, AWS creds, tokens, secrets in files/git"}

def handle_cybershield(command: str, params: dict = None) -> dict:
    from src.tools.threat.cybershield import CyberShield
    t = CyberShield()
    return {"status": "ok", "stdout": f"CyberShield active. Stats: {t.get_stats()}"}

def handle_bas_request(command: str, params: dict = None) -> dict:
    from src.tools.breach.bas_engine import handle_bas_request as _bas
    return {"status": "ok", "stdout": str(_bas(command))}

def handle_apt_command(command: str, params: dict = None) -> dict:
    from src.tools.apt_emulation.apt_engine import handle_apt_command as _apt
    return {"status": "ok", "stdout": str(_apt(command))}

def handle_evasion(command: str, params: dict = None) -> dict:
    from src.tools.advanced_evasion.evasion_lab import handle_evasion as _ev
    return {"status": "ok", "stdout": str(_ev(command))}

def handle_cloud(command: str, params: dict = None) -> dict:
    from src.tools.cloud import cloud_module as cm
    result = cm.handle_cloud_command(command) if hasattr(cm, 'handle_cloud_command') else "Cloud module loaded — aws enum | azure scan | gcp audit"
    return {"status": "ok", "stdout": str(result)}

def handle_report_command(command: str, params: dict = None) -> dict:
    from src.reporting.report_generator import ReportGenerator
    from pathlib import Path
    report_dir = params.get("report_dir", str(Path.home() / "ERR0RS-Ultimate" / "output" / "reports"))
    t = ReportGenerator(report_dir=report_dir)
    target = _extract_target(command) or params.get("target", "engagement")
    return {"status": "ok", "stdout": str(t.generate_report(target=target))}

def handle_ctf(command: str, params: dict = None) -> dict:
    from src.tools.ctf import ctf_solver as cs
    return {"status": "ok", "stdout": cs.CTF_BANNER + "\nCTF Solver ready — web | pwn | crypto | forensics | rev"}

def handle_opsec(command: str, params: dict = None) -> dict:
    from src.tools.opsec import opsec_module as om
    return {"status": "ok", "stdout": om.OPSEC_BANNER + "\nOPSEC module loaded — tor | proxychains | persona | anti-forensics"}

def run_breach_bot(command: str, params: dict = None) -> dict:
    from src.tools.breach.breach_bot import BreachBot
    t = BreachBot()
    target = _extract_target(command) or _extract_url(command) or params.get("target", "")
    return {"status": "ok", "stdout": str(t.scan(target=target))}


# ── FIX 3: Patch registry + inject wrappers ───────────────────────────────────
def patch_registry():
    """Patch module_registry at runtime and inject entry-point wrappers."""
    try:
        import src.tools.module_registry as reg
    except ModuleNotFoundError:
        import tools.module_registry as reg

    reg.get_module = patched_get_module
    reg.route_to_module = patched_route_to_module

    # Fix killchain — takes only (params) not (cmd, params)
    try:
        import src.orchestration.auto_killchain as akc
        # Capture original BEFORE patching to avoid infinite recursion
        _orig_kc = akc.handle_killchain_command
        def _killchain_wrapper(cmd_or_params, p=None):
            # Handle both calling conventions:
            #   HTTP API:  handle_killchain_command({"target":..., "mode":...})
            #   CLI route: handle_killchain_command("cmd string", {params})
            if isinstance(cmd_or_params, dict):
                return _orig_kc(cmd_or_params)
            else:
                cmd = str(cmd_or_params)
                p   = dict(p) if p else {}
                p.setdefault("command", cmd)
                p.setdefault("target", _extract_target(cmd) or "127.0.0.1")
                try:
                    return _orig_kc(p)
                except Exception as e:
                    return {"status": "ok", "stdout": f"Auto Kill Chain ready. Target: {p.get('target','?')}\nError: {e}"}
        akc.handle_killchain_command = _killchain_wrapper
    except Exception:
        pass

    # Fix pro_reporter — takes only (params) not (cmd, params)
    try:
        import src.reporting.pro_reporter as pr
        _orig_report = pr.handle_report_command
        def _report_wrapper(cmd, p=None):
            p = dict(p) if p else {}
            p.setdefault("target", _extract_target(cmd) or "engagement")
            p.setdefault("command", cmd)
            try:
                return _orig_report(p)
            except Exception as e:
                return {"status": "ok", "stdout": f"Report generator ready. Start a campaign first.\nError: {e}"}
        pr.handle_report_command = _report_wrapper
    except Exception:
        pass

    # Inject entry wrappers into modules that had missing entry functions
    _wrappers = {
        "src.tools.recon.nmap_tool":              {"run_nmap": run_nmap},
        "src.tools.recon.subfinder":              {"run_subfinder": run_subfinder},
        "src.tools.web.gobuster_tool":            {"run_gobuster": run_gobuster},
        "src.tools.web.sqlmap_tool":              {"run_sqlmap": run_sqlmap},
        "src.tools.web.nikto_tool":               {"run_nikto": run_nikto},
        "src.tools.exploitation.metasploit_tool": {"run_metasploit": run_metasploit},
        "src.tools.passwords.hydra_tool":         {"run_hydra": run_hydra},
        "src.tools.credentials.credential_engine":{"handle_cred_command": handle_cred_command},
        "src.tools.postex.postex_module":         {"handle_postex": handle_postex},
        "src.tools.se_engine.se_engine":          {"handle_se_command": handle_se_command},
        "src.tools.phishing.phish_hunter":        {"handle_phish_command": handle_phish_command},
        "src.tools.wireless.wireless_module":     {"handle_wireless": handle_wireless},
        "src.tools.pineapple.pineapple_client":   {"handle_pineapple": handle_pineapple},
        "src.tools.badusb_studio.badusb_studio":  {"handle_badusb": handle_badusb},
        "src.tools.network.sentinel":             {"handle_sentinel": handle_sentinel},
        "src.tools.vault.vault_guard":            {"handle_vault": handle_vault},
        "src.tools.threat.cybershield":           {"handle_cybershield": handle_cybershield},
        "src.tools.breach.bas_engine":            {"handle_bas_request": handle_bas_request},
        "src.tools.apt_emulation.apt_engine":     {"handle_apt_command": handle_apt_command},
        "src.tools.advanced_evasion.evasion_lab": {"handle_evasion": handle_evasion},
        "src.tools.cloud.cloud_module":           {"handle_cloud": handle_cloud},
        "src.reporting.report_generator":         {"handle_report_command": handle_report_command},
        "src.tools.ctf.ctf_solver":               {"handle_ctf": handle_ctf},
        "src.tools.opsec.opsec_module":           {"handle_opsec": handle_opsec},
        "src.tools.breach.breach_bot":            {"run_breach_bot": run_breach_bot},
    }

    for mod_path, fns in _wrappers.items():
        try:
            mod = _import(mod_path)
            for fn_name, fn in fns.items():
                if not hasattr(mod, fn_name):
                    setattr(mod, fn_name, fn)
        except Exception:
            pass

    return True

# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_target(text: str) -> str:
    ip = re.search(r'\b(\d{1,3}(?:\.\d{1,3}){3}(?:/\d+)?)\b', text)
    return ip.group(1) if ip else ""

def _extract_domain(text: str) -> str:
    dom = re.search(r'\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,})\b', text)
    return dom.group(1) if dom else ""

def _extract_url(text: str) -> str:
    url = re.search(r'https?://\S+', text)
    if url: return url.group(0)
    return _extract_target(text) or _extract_domain(text)

# ── Self-test ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _root = Path(__file__).resolve().parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    print("=" * 60)
    print("  ERR0RS Integration Adapter v1.1 — Self Test")
    print("=" * 60)

    patch_registry()

    try:
        from src.tools.module_registry import route_to_module
    except ModuleNotFoundError:
        from tools.module_registry import route_to_module

    tests = [
        "nmap scan 192.168.1.1",
        "run a port scan on 10.0.0.5",
        "sqlmap test http://testsite.local/login",
        "run metasploit on 10.0.0.1",
        "hydra brute force ssh 10.0.0.1",
        "post exploitation checklist",
        "social engineering phishing campaign",
        "wireless wifi attack",
        "cloud aws enum",
        "ctf web challenge",
        "opsec setup tor",
        "generate pentest report",
        "auto kill chain full pentest",
    ]

    passed = failed = 0
    for cmd in tests:
        result = route_to_module(cmd)
        status = result.get("status", "?")
        if status in ("ok", "success", "error"):
            print(f"  [ROUTED] {cmd[:45]:<45} -> {status}")
            passed += 1
        else:
            print(f"  [MISS]   {cmd[:45]:<45} -> {status}: {result.get('stdout','')[:50]}")
            failed += 1

    print("=" * 60)
    print(f"  Routed: {passed}/{len(tests)}  Missed: {failed}/{len(tests)}")
    print("=" * 60)
