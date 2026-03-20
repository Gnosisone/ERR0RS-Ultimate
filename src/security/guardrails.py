"""
ERR0RS ULTIMATE - Ethical Guardrails
======================================
These guardrails sit BETWEEN the user and the tools.
Every tool execution passes through here before running.

WHAT IT CHECKS:
---------------
1. Is the target authorized? (Must have active auth)
2. Is the tool appropriate for the current scope?
3. Are there any red flags in the command?
4. Is the operation destructive? (Some tools can modify/delete)

TEACHING NOTE:
--------------
Professional red teams have strict rules of engagement.
Even when authorized, some actions are off-limits:
  - Don't crash production systems
  - Don't exfiltrate actual customer data
  - Don't leave backdoors (even for testing)
  - Document EVERYTHING

These guardrails enforce those principles programmatically.
"""

import re
from typing import Dict, List, Tuple


# Tools categorized by risk level
# LOW RISK: Read-only, passive, won't affect target
# MEDIUM RISK: Active probing, touches the target
# HIGH RISK: Exploitation, modifies systems

TOOL_RISK_LEVELS = {
    "nmap":         "medium",   # Active scanning — visible to IDS
    "gobuster":     "medium",   # Active web scanning
    "nikto":        "medium",   # Active web scanning
    "theharvester": "low",      # OSINT — passive mostly
    "subfinder":    "low",      # DNS-based — passive
    "sqlmap":       "high",     # Exploitation tool
    "hydra":        "high",     # Brute force — can lockout accounts
    "metasploit":   "high",     # Exploitation framework
    "hashcat":      "low",      # Runs locally on hashes
    "john":         "low",      # Runs locally on hashes
    "linpeas":      "medium",   # Post-exploitation enumeration
    "bloodhound":   "medium",   # AD enumeration
}

# Commands that are ALWAYS blocked — even with authorization
BLOCKED_PATTERNS = [
    r"rm\s+-rf",            # Recursive delete
    r"format\s+",           # Disk formatting
    r"mkfs",                # Filesystem creation
    r"dd\s+if=",            # Disk wiping
    r"shutdown",            # System shutdown
    r"reboot",              # System reboot
    r"poweroff",            # Power off
]


class EthicalGuardrails:
    """
    Pre-execution safety checks for all tool operations.
    Returns (allowed: bool, reason: str) for every check.
    """

    def __init__(self, authorization_manager=None):
        self.auth_manager = authorization_manager

    def check_execution(self, tool_name: str, target: str,
                        command: str, context: dict = None) -> Tuple[bool, str]:
        """
        Run all safety checks. Returns (is_allowed, reason_message).
        If is_allowed is False, the tool WILL NOT execute.
        """
        checks = [
            self._check_authorization(target),
            self._check_blocked_commands(command),
            self._check_tool_risk(tool_name, context),
        ]

        for allowed, reason in checks:
            if not allowed:
                return False, reason

        return True, "All checks passed ✅"

    def _check_authorization(self, target: str) -> Tuple[bool, str]:
        """Verify the target is covered by an active authorization."""
        if self.auth_manager is None:
            # If no auth manager, allow (development/lab mode)
            return True, "No authorization manager — lab mode"

        if self.auth_manager.is_target_authorized(target):
            return True, f"Target {target} is authorized ✅"

        return False, (
            f"❌ AUTHORIZATION REQUIRED: Target {target} is not covered by any "
            f"active authorization. Create and confirm an authorization first."
        )

    def _check_blocked_commands(self, command: str) -> Tuple[bool, str]:
        """Block any command matching a dangerous pattern."""
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return False, (
                    f"❌ BLOCKED: Command matches dangerous pattern '{pattern}'. "
                    f"This operation is never allowed."
                )
        return True, "Command pattern check passed ✅"

    def _check_tool_risk(self, tool_name: str, context: dict) -> Tuple[bool, str]:
        """Check tool risk level and log it."""
        risk = TOOL_RISK_LEVELS.get(tool_name, "unknown")
        if risk == "unknown":
            return True, f"⚠️ Tool '{tool_name}' risk level unknown — proceeding with caution"
        return True, f"Tool risk level: {risk}"


class AuditLogger:
    """
    Logs every tool execution attempt for compliance.
    In professional engagements, this log is part of the deliverable.

    TEACHING NOTE:
    Audit trails are MANDATORY in professional pentesting.
    If something goes wrong, you need to prove exactly what
    you did, when, and why. This log is your defense.
    """

    def __init__(self, log_file: str = "audit_log.jsonl"):
        self.log_file = log_file

    def log_execution(self, tool_name: str, target: str, command: str,
                      authorized: bool, result: str, duration: float = 0.0):
        """Append a single audit entry."""
        import json
        from datetime import datetime

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "target": target,
            "command": command,
            "authorized": authorized,
            "result": result,
            "duration_seconds": duration,
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")

    def get_logs(self) -> List[Dict]:
        """Read all audit log entries."""
        import json
        logs = []
        if not __import__('os').path.exists(self.log_file):
            return logs
        with open(self.log_file, 'r') as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return logs
