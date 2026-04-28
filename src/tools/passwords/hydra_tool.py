"""
ERR0RS ULTIMATE - Hydra Tool Integration
===========================================
Hydra automates credential brute-forcing across dozens of
network services.

TEACHING NOTE:
--------------
Credential attacks are one of the most common ways into networks.
Hydra supports: SSH, FTP, HTTP login forms, SMB, RDP, and many more.

AUTHORIZATION REMINDER:
Credential brute-forcing is ILLEGAL without explicit written
authorization. ERR0RS enforces this with scope validation.

Flags used:
  -l username     — Single username to test
  -L file         — File of usernames to test
  -P file         — File of passwords to test
  -t 16           — 16 parallel threads
  -e nsr          — Also try: n=no password, s=username as password, r=reverse
  -V              — Verbose (show each attempt)
"""

import subprocess
import sys
import os
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


# Default wordlist locations on Kali Linux
DEFAULT_USER_LIST = "/usr/share/wordlists/rockyou.txt"
DEFAULT_PASS_LIST = "/usr/share/wordlists/rockyou.txt"


class HydraTool:
    TOOL_NAME = "hydra"
    TIMEOUT = 300

    def __init__(self, user_list: str = None, pass_list: str = None):
        self.user_list = user_list or DEFAULT_USER_LIST
        self.pass_list = pass_list or DEFAULT_PASS_LIST

    def execute(self, target: str, context: dict = None, service: str = "ssh",
                username: str = None) -> dict:
        """
        Run Hydra against a target.

        Args:
            target: IP or hostname (port can be included as target:port)
            service: Protocol to attack (ssh, ftp, http-get, smb, etc.)
            username: If provided, tests only this user. Otherwise uses user list.
        """
        command = ["hydra", "-t", "16", "-e", "nsr"]

        # Username: single or list
        if username:
            command += ["-l", username]
        else:
            command += ["-L", self.user_list]

        # Password list
        command += ["-P", self.pass_list]

        # Target and service
        command += [target, service]

        command_str = " ".join(command)
        start = time.time()

        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=self.TIMEOUT)
            duration = time.time() - start
            raw_output = proc.stdout + proc.stderr

            findings = self._parse_output(raw_output, target, service)

            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.EXPLOITATION,
                "raw_output": raw_output, "command": command_str,
                "findings": findings, "success": True, "duration": duration,
            }

        except FileNotFoundError:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.EXPLOITATION, "success": False,
                "error": "Hydra not installed. Install: sudo apt install hydra",
                "findings": [], "raw_output": "", "duration": 0.0, "command": command_str,
            }
        except subprocess.TimeoutExpired:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.EXPLOITATION, "success": False,
                "error": f"Hydra timed out after {self.TIMEOUT}s",
                "findings": [], "raw_output": "", "duration": self.TIMEOUT, "command": command_str,
            }

    def _parse_output(self, output: str, target: str, service: str) -> list:
        """Parse Hydra output for cracked credentials."""
        findings = []

        # Hydra success format: [SERVICE] host: IP login: USER password: PASS
        pattern = re.compile(
            r"\[" + re.escape(service) + r"\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)"
        )

        for match in pattern.finditer(output):
            host, username, password = match.group(1), match.group(2), match.group(3)

            findings.append(Finding(
                title=f"Credential Cracked: {username}@{host} ({service})",
                description=f"Hydra successfully cracked credentials for the {service} service.\n"
                            f"Host: {host}\n"
                            f"Username: {username}\n"
                            f"Service: {service}\n"
                            f"This means an attacker can authenticate to this service.",
                severity=Severity.CRITICAL,
                phase=PentestPhase.EXPLOITATION,
                target=host,
                tool_name=self.TOOL_NAME,
                tags=["brute_force", "credential", "authentication"],
                proof=f"[{service}] {host} login:{username} password:{password}",
                remediation="1. Change the compromised password immediately\n"
                            "2. Implement Multi-Factor Authentication (MFA)\n"
                            "3. Enable account lockout after failed attempts\n"
                            "4. Implement rate limiting on login endpoints\n"
                            "5. Review password policy — enforce minimum 12 characters\n"
                            "6. Deploy Fail2Ban or equivalent IP-based blocking",
                confidence=1.0,  # Hydra confirmed — no false positive possible
            ))

        # If no creds cracked
        if not findings:
            findings.append(Finding(
                title=f"Brute Force Completed — No Credentials Cracked ({service})",
                description=f"Hydra completed brute-forcing {service} on {target} "
                            f"without cracking any credentials. The wordlist may not "
                            f"contain the password, or account lockout is in effect.",
                severity=Severity.INFO,
                phase=PentestPhase.EXPLOITATION,
                target=target,
                tool_name=self.TOOL_NAME,
                tags=["brute_force", "credential", "clean"],
                confidence=0.5,
            ))

        return findings
