# src/core/interpreter.py
# ERR0RS-Ultimate — Output Interpreter
# Parses tool output → structured, prioritized, actionable suggestions

import re

# ── Rule table ───────────────────────────────────────────────────────────────
# Each rule: check (lambda), message, priority (1=critical→4=low), command, tag
RULES = [
    # ── Critical ─────────────────────────────────────────────────
    {
        "check":    lambda o: bool(re.search(r"CVE-\d{4}-\d+", o)),
        "message":  "CVEs detected — cross-reference and attempt exploitation",
        "priority": 1,
        "command":  "vuln",
        "tag":      "cve",
    },
    {
        "check":    lambda o: "VULNERABLE" in o.upper(),
        "message":  "Confirmed vulnerability — escalate to exploitation",
        "priority": 1,
        "command":  "full",
        "tag":      "confirmed_vuln",
    },
    # ── High ─────────────────────────────────────────────────────
    {
        "check":    lambda o: "445/tcp open" in o or "smb" in o.lower(),
        "message":  "SMB open — check for EternalBlue / MS17-010",
        "priority": 2,
        "command":  "vuln",
        "tag":      "smb",
    },
    {
        "check":    lambda o: "21/tcp open" in o,
        "message":  "FTP open — check for anonymous login and version exploits",
        "priority": 2,
        "command":  "vuln",
        "tag":      "ftp",
    },
    {
        "check":    lambda o: "3306/tcp open" in o or "mysql" in o.lower(),
        "message":  "MySQL exposed — attempt credential brute force",
        "priority": 2,
        "command":  "vuln",
        "tag":      "mysql",
    },
    {
        "check":    lambda o: "5432/tcp open" in o or "postgresql" in o.lower(),
        "message":  "PostgreSQL exposed — check auth and version",
        "priority": 2,
        "command":  "vuln",
        "tag":      "postgres",
    },
    {
        "check":    lambda o: "6379/tcp open" in o or "redis" in o.lower(),
        "message":  "Redis open — check for unauthenticated access",
        "priority": 2,
        "command":  "vuln",
        "tag":      "redis",
    },
    # ── Medium ───────────────────────────────────────────────────
    {
        "check":    lambda o: "22/tcp open" in o,
        "message":  "SSH open — enumerate version and test credentials",
        "priority": 3,
        "command":  "vuln",
        "tag":      "ssh",
    },
    {
        "check":    lambda o: "80/tcp open" in o,
        "message":  "HTTP open — run web vulnerability scan",
        "priority": 3,
        "command":  "vuln",
        "tag":      "http",
    },
    {
        "check":    lambda o: "443/tcp open" in o,
        "message":  "HTTPS open — check SSL/TLS config and web vulns",
        "priority": 3,
        "command":  "vuln",
        "tag":      "https",
    },
    {
        "check":    lambda o: "3389/tcp open" in o or "rdp" in o.lower(),
        "message":  "RDP open — check for BlueKeep (CVE-2019-0708)",
        "priority": 3,
        "command":  "vuln",
        "tag":      "rdp",
    },
    {
        "check":    lambda o: "8080/tcp open" in o or "8443/tcp open" in o,
        "message":  "Alternate web port open — check for admin panels",
        "priority": 3,
        "command":  "vuln",
        "tag":      "web_alt",
    },
    # ── Low ──────────────────────────────────────────────────────
    {
        "check":    lambda o: "login" in o.lower() or "authentication" in o.lower(),
        "message":  "Login surface detected — attempt credential testing",
        "priority": 4,
        "command":  None,
        "tag":      "auth",
    },
    {
        "check":    lambda o: "filtered" in o.lower(),
        "message":  "Filtered ports found — try UDP or full port scan",
        "priority": 4,
        "command":  "udp",
        "tag":      "filtered",
    },
    {
        "check":    lambda o: len([l for l in o.splitlines() if "open" in l]) > 10,
        "message":  "Many open ports — run full aggressive scan for detail",
        "priority": 4,
        "command":  "full",
        "tag":      "many_ports",
    },
]


class Interpreter:
    def __init__(self, max_suggestions: int = 5):
        self.max_suggestions = max_suggestions

    def analyze_output(self, output: str) -> list:
        """Returns prioritized list of finding dicts."""
        if not output:
            return []
        findings  = []
        seen_tags = set()
        for rule in RULES:
            try:
                if rule["check"](output) and rule["tag"] not in seen_tags:
                    findings.append({
                        "message":  rule["message"],
                        "priority": rule["priority"],
                        "command":  rule["command"],
                        "tag":      rule["tag"],
                    })
                    seen_tags.add(rule["tag"])
            except Exception:
                continue
        findings.sort(key=lambda x: x["priority"])
        return findings[:self.max_suggestions]

    def top_command(self, output: str) -> tuple:
        """Return (command, reason) for highest-priority actionable finding."""
        for f in self.analyze_output(output):
            if f["command"]:
                return f["command"], f["message"]
        return None, "No actionable findings"

    def summary(self, output: str) -> str:
        """One-liner severity summary for CLI and reports."""
        findings = self.analyze_output(output)
        if not findings:
            return "No significant findings."
        critical = [f for f in findings if f["priority"] == 1]
        high     = [f for f in findings if f["priority"] == 2]
        if critical:
            return f"🔴 {len(critical)} critical finding(s) — immediate action required"
        if high:
            return f"🟠 {len(high)} high-priority finding(s) detected"
        return f"🟡 {len(findings)} medium/low finding(s) — further enumeration recommended"
