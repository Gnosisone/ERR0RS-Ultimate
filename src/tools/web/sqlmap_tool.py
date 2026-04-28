"""
ERR0RS ULTIMATE - SQLMap Tool Integration
===========================================
SQLMap is THE tool for SQL injection testing. It automates
the entire process from detection to exploitation.

TEACHING NOTE:
--------------
SQL injection is consistently in the OWASP Top 10 because
it's still everywhere. SQLMap can:
  - Detect if a parameter is injectable
  - Determine the database type (MySQL, PostgreSQL, etc.)
  - Extract database structure (tables, columns)
  - Dump data (if authorized!)

CRITICAL: SQLMap should ONLY be used with explicit authorization.
Never run against a target you don't have written permission to test.

Flags we use:
  --level=3    — More thorough testing (checks more parameters)
  --risk=2     — Moderate risk (balances speed vs thoroughness)
  --dbs        — List all databases (if injection works)
  --batch      — Non-interactive mode (for automation)
  --tuples=5   — Limit extracted data to 5 rows (safe for testing)
"""

import subprocess
import sys
import os
import time
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from core.models import Finding, Severity, PentestPhase


class SQLMapTool:
    TOOL_NAME = "sqlmap"
    TIMEOUT = 300  # SQLMap can take a while on complex targets

    def execute(self, target: str, context: dict = None) -> dict:
        """
        Run SQLMap against a target URL.
        Target should be a full URL with a parameter, e.g.:
          http://target.com/page?id=1
        """
        if not target.startswith("http"):
            target = f"http://{target}"

        command = [
            "sqlmap",
            "-u", target,
            "--level=3",
            "--risk=2",
            "--batch",          # Non-interactive
            "--dbs",            # Enumerate databases if injectable
            "--tuples=5",       # Limit data extraction
            "-q",               # Quiet
        ]

        command_str = " ".join(command)
        start = time.time()

        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=self.TIMEOUT)
            duration = time.time() - start
            raw_output = proc.stdout + proc.stderr

            findings = self._parse_output(raw_output, target)

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
                "error": "SQLMap not installed. Install: sudo apt install sqlmap",
                "findings": [], "raw_output": "", "duration": 0.0, "command": command_str,
            }
        except subprocess.TimeoutExpired:
            return {
                "tool_name": self.TOOL_NAME, "target": target,
                "phase": PentestPhase.EXPLOITATION, "success": False,
                "error": f"SQLMap timed out after {self.TIMEOUT}s",
                "findings": [], "raw_output": "", "duration": self.TIMEOUT, "command": command_str,
            }

    def _parse_output(self, output: str, target: str) -> list:
        """Parse SQLMap output for injection findings."""
        findings = []

        # Check if injectable parameter was found
        if "[+]" in output and "is vulnerable" in output.lower():
            findings.append(Finding(
                title="SQL Injection Vulnerability Detected",
                description="SQLMap confirmed a SQL injection vulnerability. "
                            "An attacker can manipulate database queries through "
                            "user-controlled input, potentially reading, modifying, "
                            "or deleting data.",
                severity=Severity.CRITICAL,
                phase=PentestPhase.EXPLOITATION,
                target=target,
                tool_name=self.TOOL_NAME,
                tags=["sql_injection", "injection", "owasp_a03"],
                proof=self._extract_proof(output),
                remediation="1. Use parameterized queries (prepared statements) — ALWAYS\n"
                            "2. Implement input validation and sanitization\n"
                            "3. Use least-privilege database accounts\n"
                            "4. Deploy a WAF as an additional layer\n"
                            "5. Conduct a full code review of all database interactions",
                confidence=0.95,
            ))

        # Check for enumerated databases
        db_match = re.findall(r"\[(\+|\*)\]\s+available databases:\s*\n((?:.*\n)*)", output)
        if db_match:
            findings.append(Finding(
                title="Database Enumeration Successful",
                description="SQLMap was able to enumerate database names on the target. "
                            "This confirms the injection is exploitable and the database "
                            "account has sufficient privileges.",
                severity=Severity.CRITICAL,
                phase=PentestPhase.EXPLOITATION,
                target=target,
                tool_name=self.TOOL_NAME,
                tags=["sql_injection", "database_enum"],
                proof=db_match[0][1].strip() if db_match else "See raw output",
                remediation="Same as SQL Injection finding above — fix the injection vector first.",
                confidence=0.99,
            ))

        # If no injection found
        if not findings and "no injection" in output.lower():
            findings.append(Finding(
                title="No SQL Injection Detected",
                description="SQLMap did not detect SQL injection vulnerabilities "
                            "on the tested parameter. This does not guarantee absence "
                            "of injection — manual testing is recommended.",
                severity=Severity.INFO,
                phase=PentestPhase.EXPLOITATION,
                target=target,
                tool_name=self.TOOL_NAME,
                tags=["sql_injection", "clean"],
                confidence=0.7,  # Lower confidence — absence of evidence ≠ evidence of absence
            ))

        return findings

    def _extract_proof(self, output: str) -> str:
        """Extract the injection proof from SQLMap output."""
        lines = output.split("\n")
        proof_lines = [l for l in lines if "[+]" in l or "vulnerable" in l.lower() or "payload" in l.lower()]
        return "\n".join(proof_lines[:10]) if proof_lines else "See raw output"
