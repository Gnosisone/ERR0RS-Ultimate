"""
ERR0RS ULTIMATE - Nmap Tool Integration
============================================
Nmap is the single most important recon tool in pentesting.
This integration wraps it, parses its output, and converts
results into structured Findings.

TEACHING NOTE:
--------------
Nmap does more than "scan ports." Understanding its flags is
critical. This module uses the most important ones and teaches
you WHY each flag matters as it runs.

Key flags used here:
  -sV  — Service version detection (WHAT is running?)
  -sC  — Default scripts (quick vuln checks)
  -p-  — Scan ALL 65535 ports (not just top 1000)
  -T4  — Speed template 4 (aggressive but not too noisy)
  --open — Only show open ports (less noise)
  -oX  — Output in XML (machine-parseable)

These flags together give you a thorough, fast, useful scan.
"""

import subprocess
import xml.etree.ElementTree as ET
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


# Map common ports/services to severity and education tags
# TEACHING NOTE: Not all open ports are vulnerabilities. Port 80 (HTTP)
# being open on a web server is EXPECTED. The severity depends on context.
# This mapping provides baseline severity — the AI layer refines it.

PORT_RISK_MAP = {
    22:   {"severity": Severity.MEDIUM, "tags": ["ssh", "remote_access"], "note": "SSH open — check for weak auth"},
    23:   {"severity": Severity.HIGH,   "tags": ["telnet", "unencrypted"], "note": "Telnet is unencrypted — serious risk"},
    21:   {"severity": Severity.HIGH,   "tags": ["ftp", "unencrypted"],    "note": "FTP transmits credentials in plaintext"},
    25:   {"severity": Severity.MEDIUM, "tags": ["smtp", "email"],         "note": "SMTP open — check for relay abuse"},
    80:   {"severity": Severity.INFO,   "tags": ["http", "web"],           "note": "HTTP service detected"},
    443:  {"severity": Severity.INFO,   "tags": ["https", "web", "tls"],   "note": "HTTPS service detected"},
    3306: {"severity": Severity.HIGH,   "tags": ["mysql", "database"],     "note": "MySQL exposed — database access risk"},
    5432: {"severity": Severity.HIGH,   "tags": ["postgres", "database"],  "note": "PostgreSQL exposed — database access risk"},
    6379: {"severity": Severity.CRITICAL,  "tags": ["redis", "database"],  "note": "Redis often has no auth by default"},
    27017:{"severity": Severity.HIGH,   "tags": ["mongodb", "database"],   "note": "MongoDB exposed — check authentication"},
    3389: {"severity": Severity.HIGH,   "tags": ["rdp", "remote_access"],  "note": "RDP open — brute force target"},
    445:  {"severity": Severity.HIGH,   "tags": ["smb", "file_sharing"],   "note": "SMB open — check for EternalBlue, enum"},
    139:  {"severity": Severity.MEDIUM, "tags": ["netbios", "smb"],        "note": "NetBIOS open — information leakage"},
}


class NmapTool:
    """
    Full Nmap integration with XML output parsing.
    Converts raw Nmap output into structured Finding objects.
    """

    TOOL_NAME = "nmap"
    TIMEOUT = 120  # seconds — Nmap can take a while on full scans

    def __init__(self):
        self.last_raw_output = ""
        self.last_xml_output = ""

    def execute(self, target: str, context: dict = None) -> dict:
        """
        Run Nmap against a target. Returns a dict compatible with
        the orchestrator's ToolResult expectations.

        TEACHING NOTE:
        We use -oX for XML output AND -oC for "grepable" output.
        XML is for parsing. The grepable output is what you'd
        normally read in a terminal. We capture both.
        """
        command = [
            "nmap",
            "-sV",          # Service version detection
            "-sC",          # Default scripts
            "--open",       # Only open ports
            "-T4",          # Aggressive timing
            "-oX", "-",     # XML to stdout (we capture it)
            target
        ]

        command_str = " ".join(command)
        self.last_raw_output = ""
        findings = []

        start = time.time()
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.TIMEOUT
            )
            duration = time.time() - start
            self.last_xml_output = proc.stdout
            self.last_raw_output = proc.stdout + proc.stderr

            # Parse XML output into findings
            if proc.returncode == 0 and proc.stdout.strip():
                findings = self._parse_xml(proc.stdout, target)

            return {
                "tool_name": self.TOOL_NAME,
                "target": target,
                "phase": PentestPhase.RECONNAISSANCE,
                "raw_output": self.last_raw_output,
                "command": command_str,
                "findings": findings,
                "success": True,
                "duration": duration,
            }

        except FileNotFoundError:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.RECONNAISSANCE,
                "success": False,
                "error": "Nmap is not installed. Install with: sudo apt install nmap",
                "findings": [], "raw_output": "", "duration": 0.0, "command": command_str,
            }
        except subprocess.TimeoutExpired:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.RECONNAISSANCE,
                "success": False,
                "error": f"Nmap timed out after {self.TIMEOUT}s",
                "findings": [], "raw_output": "", "duration": self.TIMEOUT, "command": command_str,
            }

    # -----------------------------------------------------------------------
    # XML PARSER — Converts Nmap XML into structured Findings
    # -----------------------------------------------------------------------
    # TEACHING NOTE:
    # Nmap's XML output is incredibly detailed. Parsing it properly is how
    # professional tools extract intelligence from raw scans. Every open
    # port becomes a Finding with severity, tags, and remediation guidance.
    # -----------------------------------------------------------------------

    def _parse_xml(self, xml_string: str, target: str) -> list:
        """Parse Nmap XML output and return a list of Finding objects."""
        findings = []
        try:
            root = ET.fromstring(xml_string)

            for host in root.findall("host"):
                # Get the IP address
                address = host.find("address")
                if address is None:
                    continue
                ip = address.get("addr", target)

                # Get hostname if available
                hostname = ""
                hostnames = host.find("hostnames")
                if hostnames:
                    for hn in hostnames.findall("hostname"):
                        if hn.get("type") == "PTR":
                            hostname = hn.get("name", "")
                            break

                display_target = f"{hostname} ({ip})" if hostname else ip

                # Parse each port
                ports = host.find("ports")
                if ports is None:
                    continue

                for port_elem in ports.findall("port"):
                    state = port_elem.find("state")
                    if state is None or state.get("state") != "open":
                        continue

                    port_num = int(port_elem.get("portid", "0"))
                    protocol = port_elem.get("protocol", "tcp")

                    # Get service info
                    service = port_elem.find("service")
                    service_name    = service.get("name", "unknown") if service is not None else "unknown"
                    service_product = service.get("product", "") if service is not None else ""
                    service_version = service.get("version", "") if service is not None else ""

                    # Determine severity and tags from our risk map
                    risk = PORT_RISK_MAP.get(port_num, {
                        "severity": Severity.INFO,
                        "tags": ["open_port"],
                        "note": f"Port {port_num} is open"
                    })

                    # Build the finding
                    title = f"Open Port {port_num}/{protocol} — {service_name}"
                    if service_product:
                        title += f" ({service_product}"
                        if service_version:
                            title += f" {service_version}"
                        title += ")"

                    description = (
                        f"Port {port_num}/{protocol} is open on {display_target}.\n"
                        f"Service: {service_name}\n"
                    )
                    if service_product:
                        description += f"Product: {service_product}\n"
                    if service_version:
                        description += f"Version: {service_version}\n"
                    description += f"\n{risk['note']}"

                    finding = Finding(
                        title=title,
                        description=description,
                        severity=risk["severity"],
                        phase=PentestPhase.RECONNAISSANCE,
                        target=display_target,
                        tool_name=self.TOOL_NAME,
                        tags=risk["tags"],
                        proof=f"{protocol}/{port_num} {service_name} {service_product} {service_version}".strip(),
                        confidence=0.9,
                    )

                    # Add remediation based on service type
                    finding.remediation = self._get_remediation(port_num, service_name)
                    findings.append(finding)

        except ET.ParseError as e:
            # If XML parsing fails, create a single info finding with raw output
            findings.append(Finding(
                title="Nmap Scan Completed (Parse Error)",
                description=f"Nmap completed but XML output could not be parsed: {str(e)}. "
                            "Check raw output in appendix.",
                severity=Severity.INFO,
                phase=PentestPhase.RECONNAISSANCE,
                target=target,
                tool_name=self.TOOL_NAME,
            ))

        return findings

    def _get_remediation(self, port: int, service: str) -> str:
        """Return remediation guidance for a given port/service."""
        remediations = {
            22:   "1. Disable password authentication (use SSH keys only)\n2. Restrict SSH access by IP\n3. Change default port if possible\n4. Use Fail2Ban",
            23:   "1. Disable Telnet service entirely\n2. Replace with SSH (encrypted alternative)\n3. Block port 23 at the firewall",
            21:   "1. Disable FTP — use SFTP or FTPS instead\n2. If FTP is needed, restrict to specific IPs\n3. Never use anonymous FTP on production",
            80:   "1. Ensure all sensitive data uses HTTPS (port 443)\n2. Implement HTTP-to-HTTPS redirects\n3. Review web application security",
            443:  "1. Verify SSL/TLS certificate is valid and up to date\n2. Use TLS 1.2+ only\n3. Implement HSTS headers",
            3306: "1. Bind MySQL to localhost only (not 0.0.0.0)\n2. Block port 3306 at the firewall\n3. Use strong passwords for all DB users",
            3389: "1. Restrict RDP access to specific IPs\n2. Enable NLA (Network Level Authentication)\n3. Use MFA for RDP access",
            445:  "1. Disable SMB if not needed\n2. Block SMB at network perimeter\n3. Keep systems patched (EternalBlue protection)\n4. Disable SMBv1",
            6379: "1. Bind Redis to localhost only\n2. Set a strong password (requirepass)\n3. Block port 6379 at the firewall",
        }
        return remediations.get(port, f"1. Verify {service} on port {port} is required\n2. Restrict access if possible\n3. Keep software updated")
