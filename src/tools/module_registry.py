#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Module Registry v2.0
Central routing table. Every module in ERR0RS registers here.

This is the single source of truth for what ERR0RS can do.
The launcher, the NLP layer, and the AI brain all call into here.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import sys, json
from pathlib import Path
from typing import Optional
from datetime import datetime

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

# ══════════════════════════════════════════════════════════════════
# MODULE CATALOG
# Every capability ERR0RS has, organized by category.
# Used by: NLP router, Smart Wizard, AI orchestrator, help system
# ══════════════════════════════════════════════════════════════════

MODULES = {

    # ── ENGAGEMENT MANAGEMENT ──────────────────────────────────────
    "campaign": {
        "name":        "Campaign Manager",
        "desc":        "Full engagement lifecycle: create, track objectives, log findings, manage credentials, close and report",
        "category":    "engagement",
        "module":      "src.orchestration.campaign_manager",
        "entry":       "handle_campaign_command",
        "commands":    ["new campaign", "campaign status", "add finding", "close campaign", "list campaigns"],
        "competes_with": ["Cobalt Strike (team ops)", "Metasploit Pro (engagement tracking)", "Dradis", "PlexTrac"],
    },

    "killchain": {
        "name":        "Auto Kill Chain",
        "desc":        "Fully automated pentest pipeline: recon → scan → vuln assess → exploit → post → report",
        "category":    "automation",
        "module":      "src.orchestration.auto_killchain",
        "entry":       "handle_killchain_command",
        "commands":    ["auto pentest", "full auto", "run kill chain", "automated scan"],
        "competes_with": ["Metasploit Pro automation", "Core Impact", "Pentera"],
    },

    # ── RECON & ENUMERATION ────────────────────────────────────────
    "nmap": {
        "name":        "Nmap",
        "desc":        "Network discovery and port scanning",
        "category":    "recon",
        "module":      "src.tools.recon.nmap_tool",
        "entry":       "run_nmap",
        "commands":    ["scan", "port scan", "nmap"],
        "competes_with": ["nmap (native)", "Masscan", "Shodan"],
    },

    "subfinder": {
        "name":        "Subfinder",
        "desc":        "Passive subdomain enumeration",
        "category":    "recon",
        "module":      "src.tools.recon.subfinder",
        "entry":       "run_subfinder",
        "commands":    ["subfinder", "find subdomains", "subdomain enum"],
        "competes_with": ["Amass", "Subfinder (native)", "OneForAll"],
    },

    "breach_bot": {
        "name":        "BreachBot",
        "desc":        "Autonomous multi-phase vulnerability scanner chain",
        "category":    "vuln_scan",
        "module":      "src.tools.breach.breach_bot",
        "entry":       "run_breach_bot",
        "commands":    ["breach scan", "vuln scan", "automated vuln"],
        "competes_with": ["Pentera", "Nessus", "Qualys"],
    },

    # ── WEB APPLICATION ────────────────────────────────────────────
    "gobuster": {
        "name":        "Gobuster",
        "desc":        "Directory and file brute forcing",
        "category":    "web",
        "module":      "src.tools.web.gobuster_tool",
        "entry":       "run_gobuster",
        "commands":    ["gobuster", "dir bust", "find directories"],
        "competes_with": ["Dirb", "Feroxbuster", "ffuf"],
    },

    "sqlmap": {
        "name":        "SQLMap",
        "desc":        "Automated SQL injection detection and exploitation",
        "category":    "web",
        "module":      "src.tools.web.sqlmap_tool",
        "entry":       "run_sqlmap",
        "commands":    ["sqlmap", "sql injection", "sqli"],
        "competes_with": ["SQLMap (native)", "Havij (underground)"],
    },

    "nikto": {
        "name":        "Nikto",
        "desc":        "Web server vulnerability scanner",
        "category":    "web",
        "module":      "src.tools.web.nikto_tool",
        "entry":       "run_nikto",
        "commands":    ["nikto", "web scan"],
        "competes_with": ["Nikto (native)", "Acunetix (paid)"],
    },

    # ── EXPLOITATION ───────────────────────────────────────────────
    "metasploit": {
        "name":        "Metasploit",
        "desc":        "Exploit framework integration with guided workflow",
        "category":    "exploitation",
        "module":      "src.tools.exploitation.metasploit_tool",
        "entry":       "run_metasploit",
        "commands":    ["metasploit", "msf", "run exploit", "get shell"],
        "competes_with": ["Metasploit Pro ($15k/yr)", "Core Impact ($30k/yr)"],
    },

    # ── CREDENTIALS ────────────────────────────────────────────────
    "hydra": {
        "name":        "Hydra",
        "desc":        "Online password brute forcing",
        "category":    "credentials",
        "module":      "src.tools.passwords.hydra_tool",
        "entry":       "run_hydra",
        "commands":    ["hydra", "brute force", "crack login"],
        "competes_with": ["Hydra (native)", "Medusa", "Ncrack"],
    },

    "credential_engine": {
        "name":        "Credential Engine",
        "desc":        "Central credential management: auto hash detection, bulk import, hashcat pipeline, spray automation",
        "category":    "credentials",
        "module":      "src.tools.credentials.credential_engine",
        "entry":       "handle_cred_command",
        "commands":    ["creds", "credential engine", "crack hashes", "spray", "credential store"],
        "competes_with": ["Pentera credential automation", "CrackMapExec", "Impacket suite"],
    },

    # ── POST-EXPLOITATION ──────────────────────────────────────────
    "postex": {
        "name":        "Post-Exploitation Module",
        "desc":        "Privilege escalation, persistence, lateral movement automation",
        "category":    "post_exploit",
        "module":      "src.tools.postex.postex_module",
        "entry":       "handle_postex",
        "commands":    ["post exploit", "privesc", "escalate", "lateral move"],
        "competes_with": ["Cobalt Strike post-ex", "Metasploit post modules"],
    },

    # ── SOCIAL ENGINEERING ─────────────────────────────────────────
    "se_engine": {
        "name":        "Social Engineering Engine",
        "desc":        "Phishing campaigns, vishing scripts, pretexting, OSINT, physical SE — full human attack surface module",
        "category":    "social_engineering",
        "module":      "src.tools.se_engine.se_engine",
        "entry":       "handle_se_command",
        "commands":    ["social engineering", "phishing", "vishing", "se attack", "human hacking"],
        "competes_with": ["GoPhish (open source)", "KnowBe4 ($paid)", "Proofpoint ($paid)", "SET"],
    },

    "phish_hunter": {
        "name":        "PhishHunter",
        "desc":        "Phishing simulation platform and awareness training",
        "category":    "social_engineering",
        "module":      "src.tools.phishing.phish_hunter",
        "entry":       "handle_phish_command",
        "commands":    ["phish hunter", "phishing campaign", "awareness training"],
        "competes_with": ["KnowBe4 ($1,850/yr)", "Proofpoint Security Awareness ($paid)"],
    },

    # ── WIRELESS ───────────────────────────────────────────────────
    "wireless": {
        "name":        "Wireless Attack Module",
        "desc":        "WPA2 handshake capture, PMKID attack, evil twin, deauth, monitor mode",
        "category":    "wireless",
        "module":      "src.tools.wireless.wireless_module",
        "entry":       "handle_wireless",
        "commands":    ["wifi", "wireless", "aircrack", "wpa2", "handshake"],
        "competes_with": ["Aircrack-ng suite", "Hcxtools", "WiFi Pineapple"],
    },

    "pineapple": {
        "name":        "WiFi Pineapple Studio",
        "desc":        "Full WiFi Pineapple Nano integration: PineAP, evil twin, KARMA, credential harvest",
        "category":    "wireless",
        "module":      "src.tools.pineapple.pineapple_studio",
        "entry":       "handle_pineapple",
        "commands":    ["pineapple", "wifi pineapple", "karma attack", "evil twin"],
        "competes_with": ["WiFi Pineapple web UI", "hak5 cloud C2 ($paid)"],
    },

    # ── HARDWARE / BADUSB ──────────────────────────────────────────
    "badusb_studio": {
        "name":        "BadUSB Studio",
        "desc":        "Flipper Zero, USB Rubber Ducky, pico-ducky payload generation and deployment",
        "category":    "hardware",
        "module":      "src.tools.badusb_studio.badusb_studio",
        "entry":       "handle_badusb",
        "commands":    ["badusb", "flipper", "duckyscript", "rubber ducky", "hid attack"],
        "competes_with": ["Hak5 Payload Studio ($paid)", "Flipper Zero community scripts"],
    },

    # ── INTELLIGENCE & ANALYSIS ────────────────────────────────────
    "sentinel": {
        "name":        "SENTINEL",
        "desc":        "Network packet analysis: PCAP parsing, C2 beacon detection, credential sniffing, DNS exfil detection",
        "category":    "network_analysis",
        "module":      "src.tools.network.sentinel",
        "entry":       "handle_sentinel",
        "commands":    ["sentinel", "analyze pcap", "packet capture", "network forensics"],
        "competes_with": ["Wireshark", "NetworkMiner", "Zeek"],
    },

    "vault_guard": {
        "name":        "VaultGuard",
        "desc":        "Secret and credential exposure scanner for code repos, config files, git history",
        "category":    "credential_audit",
        "module":      "src.tools.vault.vault_guard",
        "entry":       "handle_vault",
        "commands":    ["vault guard", "secrets scan", "find api keys", "credential exposure"],
        "competes_with": ["TruffleHog (open source)", "GitLeaks (open source)", "GitGuardian ($paid)"],
    },

    "cybershield": {
        "name":        "CyberShield AI",
        "desc":        "Real-time threat detection and log analysis — brute force, malware IOCs, lateral movement",
        "category":    "threat_detection",
        "module":      "src.tools.threat.cybershield",
        "entry":       "handle_cybershield",
        "commands":    ["cybershield", "analyze logs", "threat detection", "siem lite"],
        "competes_with": ["Splunk ($paid)", "ELK Stack (complex)", "Graylog"],
    },

    # ── SIMULATION & TRAINING ──────────────────────────────────────
    "bas_engine": {
        "name":        "BAS Engine",
        "desc":        "Breach & Attack Simulation — MITRE ATT&CK-aligned safe checks to validate defenses",
        "category":    "simulation",
        "module":      "src.tools.breach.bas_engine",
        "entry":       "handle_bas_request",
        "commands":    ["bas", "breach simulation", "attack simulation", "validate defenses"],
        "competes_with": ["SafeBreach ($200k/yr)", "AttackIQ ($paid)", "Cymulate ($paid)", "Pentera ($paid)"],
    },

    "apt_emulation": {
        "name":        "APT Emulation Engine",
        "desc":        "Simulate real-world threat actor TTPs for purple team exercises — based on MITRE ATT&CK groups",
        "category":    "simulation",
        "module":      "src.tools.apt_emulation.apt_engine",
        "entry":       "handle_apt_command",
        "commands":    ["apt emulation", "simulate apt", "threat actor", "mitre group", "emulate attack"],
        "competes_with": ["SCYTHE ($paid)", "Vectr ($paid)", "Caldera (MITRE - free but complex)"],
    },

    # ── EVASION & DETECTION EDUCATION ─────────────────────────────
    "evasion_lab": {
        "name":        "Evasion Lab",
        "desc":        "Teaches AV/EDR evasion concepts for authorized testing — AMSI, PPL, ETW, process injection theory",
        "category":    "education",
        "module":      "src.tools.advanced_evasion.evasion_lab",
        "entry":       "handle_evasion",
        "commands":    ["evasion", "av bypass", "amsi bypass", "edr evasion", "evasion lab"],
        "competes_with": ["Underground forums ($paid access)", "OffSec courses ($2,000+)"],
    },

    # ── CLOUD SECURITY ─────────────────────────────────────────────
    "cloud": {
        "name":        "Cloud Security Module",
        "desc":        "AWS/Azure/GCP enumeration, misconfiguration scanning, IAM analysis",
        "category":    "cloud",
        "module":      "src.tools.cloud.cloud_module",
        "entry":       "handle_cloud",
        "commands":    ["cloud security", "aws enum", "azure enum", "gcp enum", "cloud pentest"],
        "competes_with": ["Prowler (free)", "ScoutSuite (free)", "CloudSploit ($paid)"],
    },

    # ── REPORTING ──────────────────────────────────────────────────
    "reporter": {
        "name":        "Professional Report Generator",
        "desc":        "Executive-grade HTML pentest reports with CVSS scoring, MITRE mapping, remediation roadmap",
        "category":    "reporting",
        "module":      "src.reporting.pro_reporter",
        "entry":       "handle_report_command",
        "commands":    ["report", "generate report", "debrief", "final report"],
        "competes_with": ["Dradis Pro ($paid)", "PlexTrac ($paid)", "AttackForge ($paid)"],
    },

    # ── CTF & LEARNING ─────────────────────────────────────────────
    "ctf": {
        "name":        "CTF Solver",
        "desc":        "Capture The Flag tooling: crypto, forensics, binary exploitation, web challenges",
        "category":    "education",
        "module":      "src.tools.ctf.ctf_solver",
        "entry":       "handle_ctf",
        "commands":    ["ctf", "capture the flag", "crypto challenge", "forensics challenge"],
        "competes_with": ["CTFd", "pwndbg", "PicoCTF"],
    },

    # ── OPSEC ──────────────────────────────────────────────────────
    "opsec": {
        "name":        "OPSEC Module",
        "desc":        "Operational security: anonymity, anti-forensics, engagement hygiene, cover tracks",
        "category":    "opsec",
        "module":      "src.tools.opsec.opsec_module",
        "entry":       "handle_opsec",
        "commands":    ["opsec", "cover tracks", "stay anonymous", "operational security"],
        "competes_with": ["Underground OPSEC guides", "Tails OS concepts"],
    },
}


# ══════════════════════════════════════════════════════════════════
# COMPETITIVE ANALYSIS
# How ERR0RS stacks up — the honest breakdown
# ══════════════════════════════════════════════════════════════════

COMPETITIVE_POSITION = {
    "mainstream_paid": {
        "Cobalt Strike":     {"price": "$5,400/yr",   "errs_advantage": "Free, teaches while running, no license tied to C2 server"},
        "Metasploit Pro":    {"price": "$15,000/yr",  "errs_advantage": "Free, same exploit framework underneath, adds AI + teaching"},
        "Core Impact":       {"price": "$30,000+/yr", "errs_advantage": "Free, automated kill chain, no enterprise contract"},
        "Pentera":           {"price": "$50,000+/yr", "errs_advantage": "Free, credential engine, BAS, spray automation"},
        "SafeBreach":        {"price": "$200,000/yr", "errs_advantage": "Free, MITRE ATT&CK BAS playbooks"},
        "Tenable Nessus":    {"price": "$4,000/yr",   "errs_advantage": "Free, integrated with kill chain, not just a scanner"},
        "KnowBe4":           {"price": "$1,850+/yr",  "errs_advantage": "Free phishing simulation with GoPhish integration"},
        "Burp Suite Pro":    {"price": "$449/yr",     "errs_advantage": "Free, integrates gobuster/nikto/sqlmap with AI guidance"},
        "SCYTHE":            {"price": "Enterprise",  "errs_advantage": "Free APT emulation with MITRE ATT&CK group TTPs"},
        "AttackIQ":          {"price": "Enterprise",  "errs_advantage": "Free BAS engine with MITRE-aligned playbooks"},
        "Dradis Pro":        {"price": "$2,500/yr",   "errs_advantage": "Free professional HTML reports, CVSS scoring, remediation"},
        "PlexTrac":          {"price": "Enterprise",  "errs_advantage": "Free campaign management, finding tracking, report gen"},
    },
    "open_source": {
        "Metasploit CE":     {"gap": "No AI, no teaching, no campaign management"},
        "Armitage":          {"gap": "No AI, no teaching, outdated"},
        "OpenVAS":           {"gap": "Scanner only, no exploitation, no teaching"},
        "Caldera":           {"gap": "APT simulation only, no exploitation, no teaching, complex setup"},
        "Atomic Red Team":   {"gap": "Tests only, no exploitation, requires manual correlation"},
        "GoPhish":           {"gap": "Phishing only, no integration with rest of kill chain"},
    },
    "errs_unique_value": [
        "TEACHES while running — no other tool explains what it's doing inline",
        "FREE alternative to $200k+/yr enterprise tooling",
        "Purple team integrated — red, blue, and detection in one platform",
        "100% local — no cloud, no telemetry, no data leaves the machine",
        "Natural language interface — operators work in plain English",
        "Hardware integration — Flipper Zero, WiFi Pineapple, Pi5, BadUSB devices",
        "Complete kill chain — recon to report in one tool",
        "Engagement memory — gets smarter with every job",
        "Community curriculum — structured learning path built in",
        "APT emulation built in — no $50k SCYTHE license needed",
        "Social engineering module — the whole human attack surface, not just tech",
    ],
}

def get_module(name: str) -> Optional[dict]:
    """Return module info by name or command keyword."""
    name_lower = name.lower().strip()
    # Direct lookup
    if name_lower in MODULES:
        return MODULES[name_lower]
    # Search by command keywords
    for key, mod in MODULES.items():
        if any(name_lower in cmd for cmd in mod.get("commands", [])):
            return mod
    return None


def list_by_category(category: str = None) -> dict:
    """Return modules grouped by category."""
    result = {}
    for key, mod in MODULES.items():
        cat = mod.get("category", "misc")
        if category and cat != category:
            continue
        result.setdefault(cat, []).append({
            "key": key, "name": mod["name"], "desc": mod["desc"]
        })
    return result


def competitive_summary() -> str:
    """Print a human-readable competitive analysis."""
    lines = [
        "",
        "  ERR0RS ULTIMATE — COMPETITIVE ANALYSIS",
        "  " + "=" * 54,
        "  What ERR0RS replaces (and beats) — for free:",
        "",
    ]
    for tool, info in COMPETITIVE_POSITION["mainstream_paid"].items():
        lines.append(f"  {tool:<20} {info['price']:<15} → ERR0RS: {info['errs_advantage'][:50]}")
    lines.append("")
    lines.append("  WHAT MAKES ERR0RS UNIQUE:")
    for point in COMPETITIVE_POSITION["errs_unique_value"]:
        lines.append(f"    ✦ {point}")
    lines.append("")
    return "\n".join(lines)


def route_to_module(command: str, params: dict = None) -> dict:
    """
    Route a command string to the correct module handler.
    Called by errorz_launcher.py when a command doesn't match
    standard tool patterns.
    """
    params = params or {}
    cmd_lower = command.lower().strip()
    mod = get_module(cmd_lower)
    if not mod:
        return {"status": "unknown", "stdout": f"No module found for: {command}"}

    try:
        module_path, entry_fn = mod["module"], mod["entry"]
        parts = module_path.split(".")
        pkg   = ".".join(parts[:-1])
        cls   = parts[-1]
        import importlib
        module = importlib.import_module(module_path)
        handler = getattr(module, entry_fn, None)
        if handler:
            return handler(command, params) if callable(handler) else {"status": "error", "stdout": "Not callable"}
        return {"status": "error", "stdout": f"Entry point {entry_fn} not found in {module_path}"}
    except Exception as e:
        return {"status": "error", "stdout": f"Module load error: {e}"}


# Singleton accessor
def get_all_modules() -> dict:
    return MODULES


def handle_registry_command(cmd: str, params: dict = None) -> dict:
    """Entry point from route_command() for registry-level queries."""
    cmd_lower = cmd.lower().strip()
    if "list" in cmd_lower or "what can" in cmd_lower or "capabilities" in cmd_lower:
        cats = list_by_category()
        lines = ["[ERR0RS] Module Catalog:", ""]
        for cat, mods in sorted(cats.items()):
            lines.append(f"  [{cat.upper().replace('_',' ')}]")
            for m in mods:
                lines.append(f"    • {m['name']:<22} — {m['desc'][:55]}")
            lines.append("")
        return {"status": "success", "stdout": "\n".join(lines)}

    if "compet" in cmd_lower or "versus" in cmd_lower or "vs " in cmd_lower:
        return {"status": "success", "stdout": competitive_summary()}

    return {"status": "success", "stdout": competitive_summary()}
