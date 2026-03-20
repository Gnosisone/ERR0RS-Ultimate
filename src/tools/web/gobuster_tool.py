"""
ERR0RS ULTIMATE - Gobuster Tool Integration
==============================================
Gobuster discovers hidden web endpoints by brute-forcing
paths against a target using a wordlist.

TEACHING NOTE:
--------------
Web applications often have endpoints that aren't linked
anywhere on the site. Admin panels, APIs, backup files,
config files. Gobuster finds them by trying thousands of
common paths automatically.

Common finds:
  /admin          — Admin panel
  /api/v1/        — API endpoints
  /wp-admin/      — WordPress admin
  /phpmyadmin/    — Database manager
  /.env           — Environment variables (secrets!)
  /backup/        — Backup files
"""

import subprocess
import sys
import os
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


# Paths that are HIGH value when found
HIGH_VALUE_PATHS = {
    "/admin", "/administrator", "/wp-admin", "/phpmyadmin",
    "/api", "/swagger", "/docs", "/console",
    "/.env", "/config", "/backup", "/.git",
    "/root", "/panel", "/dashboard", "/login",
}


class GobusterTool:
    TOOL_NAME = "gobuster"
    TIMEOUT = 180  # Web scanning takes longer
    DEFAULT_WORDLIST = "/usr/share/wordlists/dirb/common.txt"  # Standard Kali path

    def __init__(self, wordlist: str = None):
        self.wordlist = wordlist or self.DEFAULT_WORDLIST

    def execute(self, target: str, context: dict = None) -> dict:
        """
        Run Gobuster dir mode against a target URL.
        Target should be a URL like http://192.168.1.100
        If just an IP is given, we prepend http://
        """
        # Normalize target to URL format
        if not target.startswith("http"):
            target = f"http://{target}"

        command = [
            "gobuster", "dir",
            "-u", target,
            "-w", self.wordlist,
            "-t", "50",         # 50 threads — fast
            "-q",               # Quiet mode — only show results
            "--no-error",       # Don't show errors (cleaner output)
        ]

        command_str = " ".join(command)
        start = time.time()

        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=self.TIMEOUT)
            duration = time.time() - start
            raw_output = proc.stdout

            findings = self._parse_output(raw_output, target)

            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.SCANNING,
                "raw_output": raw_output, "command": command_str,
                "findings": findings, "success": True, "duration": duration,
            }

        except FileNotFoundError:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.SCANNING, "success": False,
                "error": "Gobuster not installed. Install: sudo apt install gobuster",
                "findings": [], "raw_output": "", "duration": 0.0, "command": command_str,
            }
        except subprocess.TimeoutExpired:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.SCANNING, "success": False,
                "error": f"Gobuster timed out after {self.TIMEOUT}s",
                "findings": [], "raw_output": "", "duration": self.TIMEOUT, "command": command_str,
            }

    def _parse_output(self, output: str, target: str) -> list:
        """Parse Gobuster output lines into Findings."""
        findings = []
        # Gobuster output format: /path (Status: 200) [Size: 1234]
        pattern = re.compile(r"(/\S+)\s+\(Status:\s*(\d+)\)(?:\s*\[Size:\s*(\d+)\])?")

        for line in output.strip().split("\n"):
            match = pattern.search(line)
            if not match:
                continue

            path, status_code, size = match.group(1), int(match.group(2)), match.group(3)

            # Determine severity based on status and path value
            severity = Severity.INFO
            if status_code == 200 and any(path.startswith(hp) for hp in HIGH_VALUE_PATHS):
                severity = Severity.HIGH
            elif status_code == 200:
                severity = Severity.MEDIUM
            elif status_code in (301, 302):
                severity = Severity.LOW

            finding = Finding(
                title=f"Discovered Endpoint: {path} (HTTP {status_code})",
                description=f"Hidden endpoint found at {target}{path}\n"
                            f"HTTP Status: {status_code}\n"
                            f"Size: {size or 'unknown'} bytes\n"
                            f"{'⚠️ HIGH VALUE PATH — investigate immediately.' if severity == Severity.HIGH else ''}",
                severity=severity,
                phase=PentestPhase.SCANNING,
                target=target,
                tool_name=self.TOOL_NAME,
                tags=["directory_busting", "web_discovery"],
                proof=f"GET {target}{path} → HTTP {status_code}",
                remediation="1. Verify this endpoint is intentional\n"
                            "2. If not needed, remove or restrict access\n"
                            "3. Ensure sensitive endpoints require authentication\n"
                            "4. Review access controls on all discovered paths",
                confidence=0.95,
            )
            findings.append(finding)

        return findings
