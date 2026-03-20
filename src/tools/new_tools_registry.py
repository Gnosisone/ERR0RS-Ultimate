"""
╔══════════════════════════════════════════════════════════════════╗
║      ERR0RS ULTIMATE — Tool Registry & Integration Hub           ║
║             src/tools/new_tools_registry.py                      ║
║                                                                  ║
║  Registers all 5 new tools into the ERR0RS ecosystem:            ║
║                                                                  ║
║  1. PhishHunter   — Phishing simulation & awareness platform     ║
║  2. SENTINEL      — Network packet analysis & threat detection   ║
║  3. VaultGuard    — Secret/credential exposure scanner           ║
║  4. CyberShield   — Real-time threat detection & log analysis    ║
║  5. BreachBot     — Autonomous multi-phase vuln scanner          ║
║                                                                  ║
║  HOW TO USE:                                                     ║
║    from src.tools.new_tools_registry import ToolRegistry         ║
║    registry = ToolRegistry()                                     ║
║    findings = registry.run("phish_hunter", target="example.com") ║
║    findings = registry.run("breach_bot",   target="192.168.1.1") ║
║    findings = registry.run("vault_guard",  target="/path/to/code")║
║    findings = registry.run("sentinel",     pcap="/path/to.pcap") ║
║    findings = registry.run("cybershield",  log="/var/log/auth.log")║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, sys, logging
from typing import List, Optional, Dict, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.models import Finding

log = logging.getLogger("errors.tools.registry")

# ─────────────────────────────────────────────────────────────────
# LAZY IMPORTS — Only load tools when actually needed
# ─────────────────────────────────────────────────────────────────

def _import_phish_hunter():
    from src.tools.phishing.phish_hunter import PhishHunter
    return PhishHunter

def _import_sentinel():
    from src.tools.network.sentinel import Sentinel
    return Sentinel

def _import_vault_guard():
    from src.tools.vault.vault_guard import VaultGuard
    return VaultGuard

def _import_cybershield():
    from src.tools.threat.cybershield import CyberShield
    return CyberShield

def _import_breach_bot():
    from src.tools.breach.breach_bot import BreachBot
    return BreachBot


# ─────────────────────────────────────────────────────────────────
# TOOL METADATA — Describes each tool for the AI orchestrator
# ─────────────────────────────────────────────────────────────────

TOOL_CATALOG = {
    "phish_hunter": {
        "name":        "PhishHunter",
        "description": "Phishing simulation and email security awareness platform. "
                       "Creates and tracks phishing campaigns, analyzes emails for IOCs, "
                       "tests employee security awareness.",
        "module":      "src.tools.phishing.phish_hunter",
        "class":       "PhishHunter",
        "category":    "social_engineering",
        "phases":      ["reconnaissance", "initial_access"],
        "mitre":       ["T1566", "T1598"],
        "requires":    [],
        "optional":    ["gophish"],
        "loader":      _import_phish_hunter,
        "capabilities": [
            "create_campaign",
            "analyze_email_for_phishing",
            "track_user_click_behavior",
            "generate_campaign_report",
            "extract_iocs_from_email",
            "assign_training_to_failed_users",
        ],
    },

    "sentinel": {
        "name":        "SENTINEL",
        "description": "Network packet capture analysis console. Parses PCAP files, "
                       "detects cleartext credentials, C2 beacons, DNS exfiltration, "
                       "ARP spoofing, port scans, and large data transfers.",
        "module":      "src.tools.network.sentinel",
        "class":       "Sentinel",
        "category":    "network_analysis",
        "phases":      ["reconnaissance", "lateral_movement"],
        "mitre":       ["T1040", "T1046", "T1071"],
        "requires":    [],
        "optional":    ["tshark", "tcpdump"],
        "loader":      _import_sentinel,
        "capabilities": [
            "analyze_pcap_file",
            "live_packet_capture",
            "detect_cleartext_credentials",
            "detect_c2_beacons",
            "detect_dns_exfiltration",
            "detect_port_scans",
            "protocol_breakdown",
        ],
    },

    "vault_guard": {
        "name":        "VaultGuard",
        "description": "Secret and credential exposure scanner. Scans codebases, "
                       "configuration files, and git history for hardcoded API keys, "
                       "passwords, AWS credentials, private keys, and connection strings.",
        "module":      "src.tools.vault.vault_guard",
        "class":       "VaultGuard",
        "category":    "credential_audit",
        "phases":      ["reconnaissance", "credential_access"],
        "mitre":       ["T1552", "T1213"],
        "requires":    [],
        "optional":    ["trufflehog", "gitleaks"],
        "loader":      _import_vault_guard,
        "capabilities": [
            "scan_directory_for_secrets",
            "scan_git_history",
            "entropy_analysis",
            "pattern_matching_for_credentials",
        ],
    },

    "cybershield": {
        "name":        "CyberShield AI",
        "description": "Real-time threat detection and log analysis engine. Ingests "
                       "syslog/Windows Event Log files, detects brute force, malware, "
                       "lateral movement, DDoS attempts. Correlates events into attack chains.",
        "module":      "src.tools.threat.cybershield",
        "class":       "CyberShield",
        "category":    "threat_detection",
        "phases":      ["reconnaissance", "defense_evasion"],
        "mitre":       ["T1110", "T1046", "T1071", "T1204"],
        "requires":    [],
        "optional":    [],
        "loader":      _import_cybershield,
        "capabilities": [
            "ingest_log_file",
            "detect_brute_force",
            "detect_malware_indicators",
            "correlate_attack_chains",
            "calculate_risk_score",
            "ioc_watchlist_matching",
        ],
    },

    "breach_bot": {
        "name":        "BreachBot",
        "description": "Autonomous multi-phase vulnerability scanner. Chains nmap port "
                       "scanning → security header checks → sensitive file exposure → "
                       "SSL/TLS weakness checks → default credential testing → Nuclei "
                       "template scanning into a single automated pipeline.",
        "module":      "src.tools.breach.breach_bot",
        "class":       "BreachBot",
        "category":    "vulnerability_scan",
        "phases":      ["reconnaissance", "scanning", "exploitation"],
        "mitre":       ["T1595", "T1190", "T1083", "T1078"],
        "requires":    [],
        "optional":    ["nmap", "nuclei"],
        "loader":      _import_breach_bot,
        "capabilities": [
            "full_autonomous_scan",
            "file_exposure_check",
            "ssl_tls_weakness_check",
            "security_headers_check",
            "default_credential_testing",
            "nuclei_template_scan",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────
# TOOL REGISTRY — Main interface for running any tool
# ─────────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Unified interface for all 5 new tools.
    The AI orchestrator calls this to run tools without needing
    to know the specific API of each tool.

    Quick usage:
        registry = ToolRegistry()

        # Run BreachBot full scan:
        findings = registry.run_breach_bot("192.168.1.100")

        # Scan codebase for secrets:
        findings = registry.run_vault_guard("/path/to/project")

        # Analyze PCAP:
        findings = registry.run_sentinel(pcap_path="/path/to/capture.pcap")

        # Analyze auth log:
        findings = registry.run_cybershield(log_path="/var/log/auth.log")

        # Analyze a suspicious email:
        result = registry.analyze_email(email_body, sender, org_domain)
    """

    def __init__(self, data_dir: str = "./tool_data"):
        self.data_dir = Path(data_dir)
        self._instances: Dict[str, Any] = {}

    def _get(self, tool_name: str):
        """Lazy-load and cache tool instance."""
        if tool_name not in self._instances:
            catalog = TOOL_CATALOG.get(tool_name)
            if not catalog:
                raise ValueError(f"Unknown tool: {tool_name}. Available: {list(TOOL_CATALOG)}")
            try:
                cls = catalog["loader"]()
                self._instances[tool_name] = cls(
                    data_dir=str(self.data_dir / tool_name)
                )
            except Exception as e:
                log.error(f"Failed to load tool '{tool_name}': {e}")
                raise
        return self._instances[tool_name]

    def run_breach_bot(self, target: str, **kwargs) -> List[Finding]:
        """Run full BreachBot autonomous scan against a target."""
        print(f"\n[REGISTRY] Launching BreachBot against: {target}")
        return self._get("breach_bot").scan(target, **kwargs)

    def run_vault_guard(self, scan_path: str, include_git: bool = True) -> List[Finding]:
        """Scan a codebase/directory for exposed secrets."""
        print(f"\n[REGISTRY] Launching VaultGuard scan on: {scan_path}")
        vault = self._get("vault_guard")
        findings = vault.scan_directory(scan_path)
        if include_git and Path(scan_path).joinpath(".git").exists():
            git_findings = vault.scan_git_history(scan_path)
            findings.extend(git_findings)
        return findings

    def run_sentinel(self, pcap_path: str = None, interface: str = None,
                     duration: int = 60) -> List[Finding]:
        """Analyze a PCAP file or run live capture."""
        sentinel = self._get("sentinel")
        if pcap_path:
            print(f"\n[REGISTRY] Launching SENTINEL analysis on: {pcap_path}")
            return sentinel.analyze_pcap(pcap_path)
        elif interface:
            print(f"\n[REGISTRY] Launching SENTINEL live capture on: {interface}")
            captured = sentinel.capture_live(interface, duration)
            return sentinel.analyze_pcap(captured) if captured else []
        print("[REGISTRY] sentinel: provide pcap_path or interface")
        return []

    def run_cybershield(self, log_path: str) -> List[Finding]:
        """Ingest a log file and detect threats."""
        print(f"\n[REGISTRY] Launching CyberShield on: {log_path}")
        return self._get("cybershield").ingest_log_file(log_path)

    def analyze_email(self, email_body: str, sender_email: str,
                      sender_display: str, org_domain: str) -> dict:
        """Analyze a suspicious email for phishing indicators."""
        from src.tools.phishing.phish_hunter import PhishHunter
        hunter = PhishHunter(data_dir=str(self.data_dir / "phishing"))
        return hunter.analyze_email(email_body, sender_email, sender_display, org_domain)

    def list_tools(self) -> dict:
        """List all available tools and their capabilities."""
        return {name: {
            "name": info["name"],
            "description": info["description"],
            "category": info["category"],
            "mitre": info["mitre"],
            "capabilities": info["capabilities"],
        } for name, info in TOOL_CATALOG.items()}

    def get_tool_info(self, tool_name: str) -> dict:
        """Get detailed info about a specific tool."""
        return TOOL_CATALOG.get(tool_name, {})


# ─────────────────────────────────────────────────────────────────
# CONVENIENCE — Quick access functions for CLI/REPL use
# ─────────────────────────────────────────────────────────────────

def quick_scan(target: str) -> List[Finding]:
    """Quick BreachBot scan from CLI."""
    return ToolRegistry().run_breach_bot(target)

def quick_secrets(path: str) -> List[Finding]:
    """Quick VaultGuard secrets scan from CLI."""
    return ToolRegistry().run_vault_guard(path)

def quick_pcap(pcap_path: str) -> List[Finding]:
    """Quick SENTINEL PCAP analysis from CLI."""
    return ToolRegistry().run_sentinel(pcap_path=pcap_path)


__all__ = ["ToolRegistry", "TOOL_CATALOG", "quick_scan", "quick_secrets", "quick_pcap"]
