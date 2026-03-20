"""
ERR0RS ULTIMATE - Nikto Tool Integration
===========================================
Nikto is a web server scanner. It checks for thousands of
known misconfigurations, outdated software, dangerous files,
and security issues — all in one pass.

TEACHING NOTE:
--------------
Where Gobuster finds WHAT endpoints exist, Nikto checks if
those endpoints have KNOWN vulnerabilities. It's database-driven:
Nikto has a list of 6000+ checks built in. When it finds something
it KNOWS is bad, it flags it immediately.

Think of it this way:
  Gobuster = "What doors exist?"
  Nikto    = "Which of these doors are unlocked?"

Flags used:
  -h target     — Target host/URL
  -p port       — Port number
  -o output     — Output file (we use CSV for parsing)
  -format csv   — Machine-readable output
  -Tuning 1     — Tune to specific test categories
  -ssl          — Force SSL if target is HTTPS
"""

import subprocess
import sys
import os
import time
import csv
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


# Nikto severity mapping based on its internal categories
# Nikto doesn't always report severity — we infer from the finding type
NIKTO_SEVERITY_MAP = {
    "file":          Severity.MEDIUM,    # Sensitive file found
    "config":        Severity.HIGH,      # Misconfiguration
    "default":       Severity.HIGH,      # Default credentials/pages
    "auth":          Severity.HIGH,      # Authentication issues
    "software":      Severity.MEDIUM,    # Outdated software
    "vulnerability": Severity.HIGH,      # Known vulnerability
    "information":   Severity.INFO,      # Info disclosure
}


class NiktoTool:
    TOOL_NAME = "nikto"
    TIMEOUT = 240

    def execute(self, target: str, context: dict = None, port: int = 80,
                ssl: bool = False) -> dict:
        """
        Run Nikto web scanner against a target.

        Args:
            target: Hostname or IP
            port: Port to scan (default 80)
            ssl: Use SSL (default False, set True for port 443)
        """
        # Auto-detect SSL from port
        if port == 443:
            ssl = True

        command = [
            "nikto",
            "-h", target,
            "-p", str(port),
            "-format", "csv",
            "-output", "-",     # Output to stdout
        ]
        if ssl:
            command.append("-ssl")

        command_str = " ".join(command)
        start = time.time()

        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=self.TIMEOUT)
            duration = time.time() - start
            raw_output = proc.stdout

            findings = self._parse_csv_output(raw_output, target, port)

            return {
                "tool_name": self.TOOL_NAME,
                "target": f"{target}:{port}",
                "phase": PentestPhase.SCANNING,
                "raw_output": raw_output,
                "command": command_str,
                "findings": findings,
                "success": True,
                "duration": duration,
            }

        except FileNotFoundError:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.SCANNING, "success": False,
                "error": "Nikto not installed. Install: sudo apt install nikto",
                "findings": [], "raw_output": "", "duration": 0.0, "command": command_str,
            }
        except subprocess.TimeoutExpired:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.SCANNING, "success": False,
                "error": f"Nikto timed out after {self.TIMEOUT}s",
                "findings": [], "raw_output": "", "duration": self.TIMEOUT, "command": command_str,
            }

    # -----------------------------------------------------------------------
    # CSV PARSER — Nikto's output is CSV when using -format csv
    # -----------------------------------------------------------------------
    # Nikto CSV format: "Time","URL","Test","Description","References"
    # We parse each row into a structured Finding.
    # -----------------------------------------------------------------------

    def _parse_csv_output(self, output: str, target: str, port: int) -> list:
        """Parse Nikto CSV output into Findings."""
        findings = []

        try:
            # Nikto CSV has headers — filter them out
            lines = [l for l in output.strip().split("\n") if l.strip() and not l.startswith('"Time"')]

            reader = csv.reader(io.StringIO("\n".join(lines)))
            for row in reader:
                if len(row) < 4:
                    continue  # Skip malformed rows

                _time, url, test_id, description = row[0], row[1], row[2], row[3]
                references = row[4] if len(row) > 4 else ""

                # Determine severity from description keywords
                severity = self._infer_severity(description)

                # Determine tags
                tags = self._infer_tags(description, test_id)

                # Build remediation based on finding type
                remediation = self._get_remediation(description, tags)

                finding = Finding(
                    title=f"Nikto: {description[:80]}",
                    description=f"Nikto detected: {description}\n"
                                f"URL: {url}\n"
                                f"Test ID: {test_id}",
                    severity=severity,
                    phase=PentestPhase.SCANNING,
                    target=f"{target}:{port}",
                    tool_name=self.TOOL_NAME,
                    tags=tags,
                    proof=f"URL: {url} | Test: {test_id}",
                    remediation=remediation,
                    references=[r.strip() for r in references.split("|") if r.strip()] if references else [],
                    confidence=0.85,
                )
                findings.append(finding)

        except Exception as e:
            # If CSV parsing fails entirely, create a single info finding
            findings.append(Finding(
                title="Nikto Scan Completed (output parsing issue)",
                description=f"Nikto completed but CSV output could not be parsed: {str(e)}. "
                            "Raw output available in appendix.",
                severity=Severity.INFO,
                phase=PentestPhase.SCANNING,
                target=f"{target}:{port}",
                tool_name=self.TOOL_NAME,
            ))

        return findings

    def _infer_severity(self, description: str) -> Severity:
        """Guess severity from the description text."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["default password", "default credential", "backdoor"]):
            return Severity.CRITICAL
        if any(kw in desc_lower for kw in ["vulnerability", "exploit", "cve-", "remote code"]):
            return Severity.HIGH
        if any(kw in desc_lower for kw in ["sensitive file", "private key", "config", "admin"]):
            return Severity.HIGH
        if any(kw in desc_lower for kw in ["outdated", "deprecated", "old version"]):
            return Severity.MEDIUM
        if any(kw in desc_lower for kw in ["header", "information", "server version"]):
            return Severity.LOW
        return Severity.INFO

    def _infer_tags(self, description: str, test_id: str) -> list:
        """Infer tags from description and test ID."""
        tags = ["web_scan", "nikto"]
        desc_lower = description.lower()

        if "sql" in desc_lower:       tags.append("sql_injection")
        if "xss" in desc_lower:       tags.append("xss")
        if "csrf" in desc_lower:      tags.append("csrf")
        if "file" in desc_lower:      tags.append("file_exposure")
        if "header" in desc_lower:    tags.append("security_headers")
        if "cookie" in desc_lower:    tags.append("cookie_security")
        if "ssl" in desc_lower or "tls" in desc_lower:  tags.append("tls")
        if "admin" in desc_lower:     tags.append("admin_access")

        return tags

    def _get_remediation(self, description: str, tags: list) -> str:
        """Return remediation based on finding type."""
        desc_lower = description.lower()

        if "default" in desc_lower:
            return ("1. Change all default passwords immediately\n"
                    "2. Remove default admin accounts\n"
                    "3. Rename or disable default management interfaces")
        if "sensitive file" in desc_lower or "private key" in desc_lower:
            return ("1. Remove sensitive files from web-accessible directories\n"
                    "2. Restrict file permissions (chmod 600)\n"
                    "3. Add .htaccess rules to block access to config/key files")
        if "outdated" in desc_lower or "old version" in desc_lower:
            return ("1. Update software to the latest stable version\n"
                    "2. Subscribe to security advisories for this software\n"
                    "3. Implement automated patching where possible")
        if "header" in desc_lower:
            return ("1. Add missing security headers (HSTS, X-Frame-Options, etc.)\n"
                    "2. Remove server version information from responses\n"
                    "3. Implement Content Security Policy (CSP)")

        return ("1. Review the finding details and assess risk\n"
                "2. Apply vendor-recommended patches\n"
                "3. Implement least-privilege access controls")
