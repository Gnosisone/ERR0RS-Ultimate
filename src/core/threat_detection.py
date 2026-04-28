#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║     ERR0RS ULTIMATE — AI-POWERED THREAT DETECTION               ║
║              src/core/threat_detection.py                       ║
║                                                                  ║
║  Live threat detection that watches system logs, network        ║
║  traffic patterns, and process activity for IOCs and attack     ║
║  patterns — then explains what it found and what to do.         ║
║                                                                  ║
║  Detection categories:                                          ║
║    • Brute force attempts (failed auth spikes)                  ║
║    • Port scan signatures (sequential port access)              ║
║    • Malware indicators (suspicious processes, connections)      ║
║    • Lateral movement (unusual auth patterns)                   ║
║    • Data exfiltration (large outbound transfers)               ║
║    • Privilege escalation attempts                              ║
║    • Web attacks (SQLi, XSS, path traversal in logs)            ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import time
import json
import glob
import shutil
import socket
import threading
import subprocess
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Callable, Tuple

log = logging.getLogger("err0rs.threat_detection")


# ══════════════════════════════════════════════════════════════════════════════
# THREAT SIGNATURES — what we're looking for
# ══════════════════════════════════════════════════════════════════════════════

THREAT_SIGNATURES = {
    "brute_force_ssh": {
        "pattern":    r"Failed password|authentication failure|Invalid user",
        "log_files":  ["/var/log/auth.log", "/var/log/secure"],
        "severity":   "high",
        "threshold":  5,       # occurrences in window
        "window":     60,      # seconds
        "description":"SSH brute force — multiple failed authentication attempts",
        "mitre":      "T1110.001 — Brute Force: Password Guessing",
        "response":   ["Block source IP with: iptables -A INPUT -s {ip} -j DROP",
                      "Enable fail2ban: sudo apt install fail2ban && sudo systemctl start fail2ban",
                      "Check successful logins: last -20"],
    },
    "port_scan": {
        "pattern":    r"SYN|TCP.*Flags.*S\b|NMAP|connection.*refused",
        "log_files":  ["/var/log/syslog", "/var/log/messages", "/var/log/kern.log"],
        "severity":   "medium",
        "threshold":  20,
        "window":     30,
        "description":"Port scan detected — sequential connection attempts to multiple ports",
        "mitre":      "T1046 — Network Service Discovery",
        "response":   ["Identify scanner: netstat -an | grep SYN_RECV",
                      "Enable port-scan detection: sudo ufw enable",
                      "Check iptables: iptables -L -n -v"],
    },
    "web_attack_sqli": {
        "pattern":    r"union.*select|' or '1'='1|1=1|--\s*$|/\*.*\*/|0x[0-9a-f]+|xp_cmdshell|information_schema",
        "log_files":  ["/var/log/apache2/access.log", "/var/log/nginx/access.log",
                      "/var/log/apache2/error.log", "/var/log/nginx/error.log"],
        "severity":   "critical",
        "threshold":  1,
        "window":     300,
        "description":"SQL injection attempt in web logs",
        "mitre":      "T1190 — Exploit Public-Facing Application",
        "response":   ["Block IP immediately: iptables -A INPUT -s {ip} -j DROP",
                      "Enable WAF: sudo apt install libapache2-mod-security2",
                      "Review database logs for successful injections"],
    },
    "web_attack_path_traversal": {
        "pattern":    r"\.\./\.\./|%2e%2e%2f|%2e%2e/|\.\.%2f|etc/passwd|etc/shadow|proc/self",
        "log_files":  ["/var/log/apache2/access.log", "/var/log/nginx/access.log"],
        "severity":   "high",
        "threshold":  1,
        "window":     300,
        "description":"Path traversal attempt — trying to read sensitive files",
        "mitre":      "T1083 — File and Directory Discovery",
        "response":   ["Block source IP", "Check if /etc/passwd was successfully read",
                      "Review web app input validation"],
    },
    "privilege_escalation": {
        "pattern":    r"sudo.*COMMAND|su.*authentication failure|setuid|chmod.*4755|ptrace",
        "log_files":  ["/var/log/auth.log", "/var/log/secure", "/var/log/syslog"],
        "severity":   "critical",
        "threshold":  1,
        "window":     60,
        "description":"Privilege escalation attempt detected",
        "mitre":      "T1548 — Abuse Elevation Control Mechanism",
        "response":   ["Check running processes: ps aux | grep suspicious",
                      "Review sudo log: grep sudo /var/log/auth.log | tail -50",
                      "Check SUID binaries: find / -perm -4000 -type f 2>/dev/null"],
    },
    "malware_process": {
        "pattern":    r"nc\s+-[el]|ncat|netcat|/tmp/[a-z0-9]{8,}|wget.*-O\s*/tmp|curl.*-o\s*/tmp|base64.*eval|python.*-c.*exec",
        "log_files":  ["/var/log/syslog", "/var/log/auth.log"],
        "severity":   "critical",
        "threshold":  1,
        "window":     300,
        "description":"Suspicious process — potential malware or reverse shell",
        "mitre":      "T1059 — Command and Scripting Interpreter",
        "response":   ["Kill suspicious process immediately: kill -9 {pid}",
                      "Check process tree: ps auxf",
                      "Check network connections: ss -tulpn",
                      "Run rkhunter: sudo rkhunter --check"],
    },
    "lateral_movement": {
        "pattern":    r"scp.*authorized_keys|ssh.*-L.*-R|ProxyCommand|StrictHostKeyChecking=no|psexec|wmiexec",
        "log_files":  ["/var/log/auth.log", "/var/log/secure"],
        "severity":   "critical",
        "threshold":  1,
        "window":     300,
        "description":"Lateral movement detected — attacker pivoting to other systems",
        "mitre":      "T1021 — Remote Services",
        "response":   ["Isolate affected system immediately",
                      "Check authorized_keys: cat ~/.ssh/authorized_keys",
                      "Review SSH config: cat /etc/ssh/sshd_config",
                      "Block inter-system communication temporarily"],
    },
    "data_exfiltration": {
        "pattern":    r"curl.*\|\s*nc|wget.*\|\s*nc|tar.*\|\s*nc|dd.*\|\s*nc",
        "log_files":  ["/var/log/syslog", "/var/log/bash_history"],
        "severity":   "critical",
        "threshold":  1,
        "window":     300,
        "description":"Data exfiltration attempt — data being piped out via netcat",
        "mitre":      "T1048 — Exfiltration Over Alternative Protocol",
        "response":   ["Block outbound traffic: iptables -A OUTPUT -j DROP",
                      "Check what data was accessed: ls -la /proc/*/fd",
                      "Preserve evidence before response: cp -r /var/log /tmp/evidence"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# ALERT MODEL
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ThreatAlert:
    signature:   str
    severity:    str
    description: str
    mitre:       str
    raw_matches: List[str]
    source_ips:  List[str]
    count:       int
    response:    List[str]
    ts:          str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "signature":   self.signature,
            "severity":    self.severity,
            "description": self.description,
            "mitre":       self.mitre,
            "count":       self.count,
            "source_ips":  self.source_ips,
            "response":    self.response,
            "ts":          self.ts,
        }


# ══════════════════════════════════════════════════════════════════════════════
# LOG READER
# ══════════════════════════════════════════════════════════════════════════════

class LogTailer:
    """Tails log files and returns new lines."""

    def __init__(self):
        self._positions: Dict[str, int] = {}

    def read_new(self, filepath: str, max_lines: int = 200) -> List[str]:
        if not os.path.exists(filepath):
            return []
        try:
            pos = self._positions.get(filepath, 0)
            with open(filepath, errors="ignore") as f:
                f.seek(0, 2)
                end = f.tell()
                if pos == 0:
                    # First read — start near end
                    f.seek(max(0, end - 4096))
                else:
                    f.seek(pos)
                lines = f.readlines()
                self._positions[filepath] = f.tell()
            return [l.rstrip() for l in lines[-max_lines:]]
        except Exception:
            return []

    def initial_scan(self, filepath: str, max_lines: int = 500) -> List[str]:
        """Read last N lines from a file."""
        if not os.path.exists(filepath):
            return []
        try:
            result = subprocess.run(
                ["tail", "-n", str(max_lines), filepath],
                capture_output=True, text=True, errors="ignore", timeout=5
            )
            return result.stdout.split("\n")
        except Exception:
            return []


# ══════════════════════════════════════════════════════════════════════════════
# PROCESS MONITOR — watch running processes for IOCs
# ══════════════════════════════════════════════════════════════════════════════

SUSPICIOUS_PROCESS_PATTERNS = [
    r"nc\s+-[lp]",           # netcat listener
    r"ncat\s+--listen",      # ncat listener
    r"python.*-c.*socket",   # python reverse shell
    r"bash\s+-i\s+>&\s*/dev",# bash reverse shell
    r"msfconsole",           # metasploit (not ours)
    r"mimikatz",             # credential dumper
    r"bloodhound-python",    # AD enumeration (not ours)
]

def scan_processes() -> List[Dict]:
    """Scan running processes for suspicious patterns."""
    suspicious = []
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            for pat in SUSPICIOUS_PROCESS_PATTERNS:
                if re.search(pat, line, re.IGNORECASE):
                    suspicious.append({
                        "line": line.strip()[:120],
                        "pattern": pat,
                        "severity": "critical",
                    })
    except Exception:
        pass
    return suspicious


# ══════════════════════════════════════════════════════════════════════════════
# NETWORK MONITOR — watch active connections
# ══════════════════════════════════════════════════════════════════════════════

SUSPICIOUS_PORTS = {4444, 4445, 1337, 31337, 9001, 9999, 8888}  # common C2/shell ports

def scan_connections() -> List[Dict]:
    """Check active network connections for C2 or unusual activity."""
    suspicious = []
    if not shutil.which("ss"):
        return suspicious
    try:
        result = subprocess.run(
            ["ss", "-tulpn"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            for port in SUSPICIOUS_PORTS:
                if f":{port}" in line:
                    suspicious.append({
                        "line": line.strip(),
                        "port": port,
                        "severity": "high",
                        "description": f"Suspicious port {port} — potential C2 or reverse shell listener",
                    })
    except Exception:
        pass
    return suspicious


# ══════════════════════════════════════════════════════════════════════════════
# THREAT DETECTOR — the main engine
# ══════════════════════════════════════════════════════════════════════════════

class ThreatDetector:
    """
    AI-powered threat detection engine.
    Runs continuously, ingests logs + process/network state,
    fires alerts with MITRE mappings and response playbooks.
    """

    def __init__(self, broadcast_fn: Callable, poll_interval: int = 30):
        self.broadcast      = broadcast_fn
        self.poll_interval  = poll_interval
        self._tailer        = LogTailer()
        self._alert_history: List[ThreatAlert] = []
        self._event_buckets: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self._thread:        Optional[threading.Thread] = None
        self._stop_flag      = threading.Event()
        self._running        = False

    def start(self):
        """Start continuous threat monitoring."""
        if self._running:
            self._emit("[THREAT] Already monitoring.")
            return
        self._stop_flag.clear()
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        self._emit(f"""
{'═'*54}
  🛡️  ERR0RS THREAT DETECTION — ACTIVE
{'─'*54}
  Monitoring: system logs, processes, network connections
  Signatures: {len(THREAT_SIGNATURES)} threat patterns
  MITRE ATT&CK mapped — response playbooks included
  Poll interval: {self.poll_interval}s
{'═'*54}
""")

    def stop(self):
        self._stop_flag.set()
        self._running = False
        self._emit("[THREAT] Monitoring stopped.")

    def scan_once(self) -> List[ThreatAlert]:
        """Run a single threat scan and return alerts."""
        alerts = []
        alerts.extend(self._check_signatures())
        alerts.extend(self._check_processes())
        alerts.extend(self._check_connections())
        return alerts

    def status(self) -> Dict:
        return {
            "running":  self._running,
            "alerts":   len(self._alert_history),
            "critical": len([a for a in self._alert_history if a.severity == "critical"]),
            "high":     len([a for a in self._alert_history if a.severity == "high"]),
            "last_alert": self._alert_history[-1].ts if self._alert_history else None,
        }

    def _emit(self, msg: str):
        self.broadcast({"type": "system", "data": msg})

    def _emit_alert(self, alert: ThreatAlert):
        """Format and broadcast a threat alert."""
        sev_icons = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🔵"}
        icon = sev_icons.get(alert.severity, "⚪")
        lines = [
            f"\n{'═'*56}",
            f"{icon} THREAT DETECTED — {alert.severity.upper()}",
            f"{'─'*56}",
            f"Signature:   {alert.signature}",
            f"Description: {alert.description}",
            f"MITRE:       {alert.mitre}",
            f"Count:       {alert.count} occurrences",
        ]
        if alert.source_ips:
            lines.append(f"Source IPs:  {', '.join(alert.source_ips[:5])}")
        if alert.raw_matches:
            lines.append(f"\nSample evidence:")
            for m in alert.raw_matches[:3]:
                lines.append(f"  {m[:100]}")
        lines.append(f"\n⚡ RESPONSE PLAYBOOK:")
        for i, step in enumerate(alert.response, 1):
            if alert.source_ips:
                step = step.replace("{ip}", alert.source_ips[0])
            lines.append(f"  {i}. {step}")
        lines.append(f"{'═'*56}\n")

        self.broadcast({
            "type": "coach",
            "data": "\n".join(lines),
            "result": {
                "heading":   f"THREAT: {alert.description}",
                "explain":   f"MITRE {alert.mitre}",
                "severity":  alert.severity,
                "next_steps":[{"command": r, "label": f"Response {i+1}"}
                              for i, r in enumerate(alert.response[:3])],
                "defense":   f"Block source, preserve evidence, escalate to IR.",
                "xp_event":  None,
                "finding_count": alert.count,
            },
            "tool": "threat_detection",
        })

    def _monitor_loop(self):
        """Continuous monitoring loop."""
        while not self._stop_flag.is_set():
            alerts = self.scan_once()
            for alert in alerts:
                # Deduplicate — don't re-alert same signature within 5 minutes
                recent = [a for a in self._alert_history
                         if a.signature == alert.signature
                         and (datetime.now() - datetime.fromisoformat(a.ts)).seconds < 300]
                if not recent:
                    self._alert_history.append(alert)
                    self._emit_alert(alert)
                    try:
                        from src.core.progression import award_xp
                        award_xp("found_vuln", f"threat: {alert.signature}")
                    except Exception:
                        pass
            time.sleep(self.poll_interval)

    def _check_signatures(self) -> List[ThreatAlert]:
        """Check log files against all threat signatures."""
        alerts = []
        now = time.time()

        for sig_name, sig in THREAT_SIGNATURES.items():
            pattern = re.compile(sig["pattern"], re.IGNORECASE)
            matches = []
            source_ips = []

            for log_file in sig.get("log_files", []):
                # Try glob patterns
                for resolved in glob.glob(log_file):
                    lines = self._tailer.read_new(resolved, max_lines=100)
                    for line in lines:
                        if pattern.search(line):
                            matches.append(line)
                            # Extract IPs
                            ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line)
                            source_ips.extend([ip for ip in ips
                                              if not ip.startswith(("127.","10.","192.168.","172."))])

            # Add to event bucket with timestamp
            bucket_key = sig_name
            for m in matches:
                self._event_buckets[bucket_key].append(now)

            # Count events in window
            window = sig.get("window", 60)
            recent_events = [t for t in self._event_buckets[bucket_key]
                            if now - t <= window]

            if len(recent_events) >= sig.get("threshold", 1) and matches:
                alerts.append(ThreatAlert(
                    signature=sig_name,
                    severity=sig["severity"],
                    description=sig["description"],
                    mitre=sig["mitre"],
                    raw_matches=matches[:5],
                    source_ips=list(set(source_ips))[:5],
                    count=len(recent_events),
                    response=sig["response"],
                ))

        return alerts

    def _check_processes(self) -> List[ThreatAlert]:
        """Scan running processes for IOCs."""
        alerts = []
        suspicious = scan_processes()
        for proc in suspicious:
            alerts.append(ThreatAlert(
                signature="suspicious_process",
                severity="critical",
                description=f"Suspicious process pattern: {proc['pattern']}",
                mitre="T1059 — Command and Scripting Interpreter",
                raw_matches=[proc["line"]],
                source_ips=[],
                count=1,
                response=[
                    "Identify PID: ps aux | grep suspicious",
                    "Kill process: kill -9 {PID}",
                    "Check persistence: crontab -l && ls /etc/cron.d/",
                ],
            ))
        return alerts

    def _check_connections(self) -> List[ThreatAlert]:
        """Check network connections for C2 activity."""
        alerts = []
        suspicious = scan_connections()
        for conn in suspicious:
            alerts.append(ThreatAlert(
                signature="c2_port",
                severity=conn["severity"],
                description=conn.get("description", f"Suspicious port: {conn['port']}"),
                mitre="T1571 — Non-Standard Port",
                raw_matches=[conn["line"]],
                source_ips=[],
                count=1,
                response=[
                    f"Close connection: fuser -k {conn['port']}/tcp",
                    "Check process: ss -tulpn",
                    "Block port: iptables -A INPUT -p tcp --dport {PORT} -j DROP",
                ],
            ))
        return alerts


# ── Global singleton ──────────────────────────────────────────────────────────
_detector: Optional[ThreatDetector] = None

def get_threat_detector(broadcast_fn: Callable = None,
                        poll_interval: int = 30) -> Optional[ThreatDetector]:
    global _detector
    if _detector is None and broadcast_fn:
        _detector = ThreatDetector(broadcast_fn=broadcast_fn,
                                   poll_interval=poll_interval)
    return _detector
