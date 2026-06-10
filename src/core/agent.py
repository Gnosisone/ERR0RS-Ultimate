#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — AUTONOMOUS PENTEST AGENT              ║
║              src/core/agent.py                                  ║
║                                                                  ║
║  A real ReAct (Reason-Act-Observe) autonomous agent loop.       ║
║                                                                  ║
║  Architecture:                                                   ║
║    1. OBSERVE  — collect current findings + target state        ║
║    2. REASON   — LLM decides what to do next and why            ║
║    3. ACT      — execute the chosen tool via LiveProcess        ║
║    4. ANALYZE  — parse output → new findings → update state     ║
║    5. LOOP     — repeat until goal reached or max steps hit     ║
║                                                                  ║
║  The agent is goal-aware: it knows whether it's doing           ║
║  full-chain, web-only, AD-only, stealth, or quick-recon.        ║
║  It adapts its tool choices based on what it finds.             ║
║                                                                  ║
║  Every action is broadcast live to the WebSocket so the         ║
║  operator sees the agent's reasoning AND the tool output        ║
║  in real time. The agent narrates its own decisions.            ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import re
import shutil
import subprocess
import threading
import time
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

log = logging.getLogger("err0rs.agent")


# ══════════════════════════════════════════════════════════════════════════════
# AGENT GOALS — what the agent is trying to achieve
# ══════════════════════════════════════════════════════════════════════════════

GOALS = {
    "full_chain": {
        "description": "Complete penetration test — recon through exploitation",
        "phases": ["recon", "enum", "vuln_scan", "exploit", "post_exploit", "report"],
        "max_steps": 20,
    },
    "web": {
        "description": "Web application security assessment",
        "phases": ["web_recon", "web_enum", "web_vuln", "web_exploit"],
        "max_steps": 12,
    },
    "network": {
        "description": "Network penetration test",
        "phases": ["port_scan", "service_enum", "vuln_check", "exploit_attempt"],
        "max_steps": 12,
    },
    "ad": {
        "description": "Active Directory attack — path to Domain Admin",
        "phases": ["ad_recon", "kerberoast", "bloodhound", "escalate"],
        "max_steps": 10,
    },
    "stealth": {
        "description": "Low-noise recon without triggering IDS",
        "phases": ["passive_recon", "slow_scan", "minimal_enum"],
        "max_steps": 8,
    },
    "quick": {
        "description": "Fast surface-level vulnerability assessment",
        "phases": ["fast_scan", "quick_web", "summary"],
        "max_steps": 6,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT STATE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentFinding:
    tool:     str
    kind:     str          # open_port, vulnerability, credential, service, etc.
    value:    str          # the actual finding (port number, CVE, password, etc.)
    severity: str          # critical, high, medium, low, info
    detail:   str = ""
    ts:       str = field(default_factory=lambda: datetime.now().isoformat())
    key:        str   = ""      # recon: specific item (port/domain) — folded from ReconFinding
    confidence: float = 1.0     # folded from ReconFinding

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_report_finding(self, target: str = ""):
        """Convert this runtime finding into a rich models.Finding for reporting."""
        from .models import Finding as _RF, Severity as _Sev
        sev = {"critical": _Sev.CRITICAL, "high": _Sev.HIGH, "medium": _Sev.MEDIUM,
               "low": _Sev.LOW, "info": _Sev.INFO}.get((self.severity or "info").lower(), _Sev.INFO)
        return _RF(title=f"{self.kind}: {self.value}",
                   description=self.detail or self.value,
                   severity=sev, target=target, tool_name=self.tool,
                   confidence=float(getattr(self, "confidence", 1.0) or 1.0),
                   tags=[self.kind] if self.kind else [])

@dataclass
class Task:
    """A node in the Penetration Testing Tree (PTT)."""
    id:     str
    title:  str
    status: str = "todo"           # todo | done | skipped | n/a
    tool:   Optional[str] = None   # tool that satisfies this task, if any
    parent: Optional[str] = None   # parent task id (None = phase root)

@dataclass
class AgentStep:
    step:     int
    phase:    str
    tool:     str
    command:  str
    stdout:   str
    findings: List[AgentFinding]
    decision: Dict          # the LLM's reasoning for this step
    duration: float         # seconds the tool took
    ts:       str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class AgentState:
    target:         str
    goal:           str               = ""
    phase:          str               = "init"
    steps:          List[AgentStep]   = field(default_factory=list)
    findings:       List[AgentFinding] = field(default_factory=list)
    open_ports:     List[str]         = field(default_factory=list)
    services:       Dict[str, str]    = field(default_factory=dict)  # port → service
    vulnerabilities: List[str]        = field(default_factory=list)
    credentials:    List[str]         = field(default_factory=list)
    shells:         List[str]         = field(default_factory=list)
    completed_tools: List[str]        = field(default_factory=list)
    running:        bool              = True
    done:           bool              = False
    abort_reason:   str               = ""

    # -- folded-in recon superset (was ReconState) --
    hostnames:      List[str]         = field(default_factory=list)
    ips:            List[str]         = field(default_factory=list)
    subdomains:     List[str]         = field(default_factory=list)
    web_paths:      List[str]         = field(default_factory=list)
    technologies:   List[str]         = field(default_factory=list)
    emails:         List[str]         = field(default_factory=list)
    start_time:     str               = field(default_factory=lambda: datetime.now().isoformat())
    # -- Penetration Testing Tree: what's done / what's next --
    ptt:            List["Task"]      = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Target: {self.target}  Goal: {self.goal}  Phase: {self.phase}",
            f"Steps: {len(self.steps)}  Findings: {len(self.findings)}",
            f"Open ports: {', '.join(self.open_ports[:10]) or 'none yet'}",
        ]
        if self.services:
            lines.append(f"Services: {', '.join(f'{p}={s}' for p,s in list(self.services.items())[:6])}")
        if self.vulnerabilities:
            lines.append(f"Vulns: {', '.join(self.vulnerabilities[:5])}")
        if self.credentials:
            lines.append(f"Creds: {len(self.credentials)} found")
        if self.shells:
            lines.append(f"Shells: {', '.join(self.shells)}")
        return "\n".join(lines)

    def findings_for_prompt(self) -> str:
        """Compact findings summary for LLM context."""
        if not self.findings:
            return "No findings yet."
        lines = []
        for f in self.findings[-20:]:  # last 20 findings
            lines.append(f"[{f.severity.upper()}] {f.kind}: {f.value} ({f.tool})")
        return "\n".join(lines)

    def tools_used_str(self) -> str:
        return ", ".join(self.completed_tools) if self.completed_tools else "none"

    # -- PTT: what's done / what's next -------------------------------------
    def seed_ptt(self, phases) -> None:
        """Create one root task per planned phase (idempotent)."""
        if self.ptt:
            return
        self.ptt = [Task(id=str(i + 1), title=f"Phase: {p}", status="todo")
                    for i, p in enumerate(phases)]

    def _phase_root(self, phase: str) -> "Task":
        for t in self.ptt:
            if t.parent is None and t.title == f"Phase: {phase}":
                return t
        root = Task(id=str(len(self.ptt) + 1), title=f"Phase: {phase}", status="todo")
        self.ptt.append(root)
        return root

    def add_task(self, phase: str, tool: str, title: str) -> "Task":
        """Add a sub-task for a tool (idempotent by tool)."""
        for t in self.ptt:
            if t.tool == tool:
                return t
        root = self._phase_root(phase)
        sibs = [t for t in self.ptt if t.parent == root.id]
        task = Task(id=f"{root.id}.{len(sibs) + 1}", title=title,
                    status="todo", tool=tool, parent=root.id)
        self.ptt.append(task)
        return task

    def complete_task(self, tool: str, ok: bool = True) -> None:
        task = next((t for t in self.ptt if t.tool == tool), None)
        if task is None:
            task = self.add_task(self.phase, tool, tool)
        task.status = "done" if ok else "skipped"
        self._roll_up()

    def _roll_up(self) -> None:
        """Mark a phase root done once all its sub-tasks are resolved."""
        for root in [t for t in self.ptt if t.parent is None]:
            kids = [t for t in self.ptt if t.parent == root.id]
            if kids and all(k.status in ("done", "skipped", "n/a") for k in kids):
                root.status = "done"

    def next_todo(self):
        for t in self.ptt:
            if t.parent is not None and t.status == "todo":
                return t
        return None

    def ptt_for_prompt(self) -> str:
        """Compact PTT render for LLM context or the operator feed."""
        if not self.ptt:
            return "PTT: (empty)"
        mark = {"todo": "[ ]", "done": "[x]", "skipped": "[-]", "n/a": "[~]"}
        out = []
        for t in self.ptt:
            indent = "" if t.parent is None else "    "
            out.append(f"{indent}{mark.get(t.status, '[ ]')} {t.id} {t.title}")
        return "\n".join(out)

    # -- persistence: resumable engagements --------------------------------
    def _engagement_path(self) -> str:
        d = os.path.expanduser("~/.err0rs/engagements")
        os.makedirs(d, exist_ok=True)
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", self.target or "unknown")
        return os.path.join(d, f"{safe}.json")

    def to_dict(self) -> Dict:
        d = asdict(self)
        for s in d.get("steps", []):
            if len(s.get("stdout", "")) > 2000:
                s["stdout"] = s["stdout"][:2000] + "...[trimmed]"
        return d

    def save(self) -> None:
        with open(self._engagement_path(), "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, d: Dict) -> "AgentState":
        st = cls(target=d.get("target", ""), goal=d.get("goal", ""))
        for k in ("phase", "running", "done", "abort_reason", "start_time"):
            if k in d:
                setattr(st, k, d[k])
        for k in ("open_ports", "services", "vulnerabilities", "credentials",
                  "shells", "completed_tools", "hostnames", "ips", "subdomains",
                  "web_paths", "technologies", "emails"):
            if k in d:
                setattr(st, k, d[k])
        st.ptt = [Task(**t) for t in d.get("ptt", [])]
        st.findings = [AgentFinding(**f) for f in d.get("findings", [])]
        return st


# ══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY — every tool the agent can choose from
# ══════════════════════════════════════════════════════════════════════════════

# Format: tool_key → {cmd_template, phases, requires, description}
AGENT_TOOLS = {
    # ── Reconnaissance ────────────────────────────────────────────────────────
    "nmap_quick": {
        "cmd":        "nmap -sV --top-ports 1000 -T4 {target}",
        "phases":     ["recon", "port_scan", "fast_scan", "quick"],
        "description":"Fast port scan — top 1000 ports with version detection",
        "timeout":    120,
    },
    "nmap_full": {
        "cmd":        "nmap -sV -sC -p- -T4 {target}",
        "phases":     ["recon", "port_scan", "enum"],
        "description":"Full port scan — all 65535 ports with scripts",
        "timeout":    300,
    },
    "nmap_udp": {
        "cmd":        "nmap -sU --top-ports 100 {target}",
        "phases":     ["recon", "enum"],
        "requires":   [],
        "description":"UDP scan — DNS(53), SNMP(161), NTP(123)",
        "timeout":    180,
    },
    "nmap_stealth": {
        "cmd":        "nmap -sS -T2 --top-ports 500 {target}",
        "phases":     ["passive_recon", "slow_scan", "stealth"],
        "description":"Stealth SYN scan — slower, quieter",
        "timeout":    240,
    },
    "nmap_vuln": {
        "cmd":        "nmap --script vuln -p {ports} {target}",
        "phases":     ["vuln_check", "vuln_scan"],
        "requires":   ["open_ports"],
        "description":"Nmap vuln scripts on known open ports",
        "timeout":    180,
    },

    # ── Web ───────────────────────────────────────────────────────────────────
    "whatweb": {
        "cmd":        "whatweb {target} -a 3 --no-errors",
        "phases":     ["web_recon", "recon", "quick_web"],
        "description":"Web fingerprinting — CMS, frameworks, server versions",
        "timeout":    30,
    },
    "nikto": {
        "cmd":        "nikto -h {target} -C all -maxtime 120 -nointeractive",
        "phases":     ["web_vuln", "web_enum", "quick_web"],
        "requires":   ["web_port"],
        "description":"Web vulnerability scanner — 6700+ checks",
        "timeout":    150,
    },
    "gobuster_dir": {
        "cmd":        "gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt -t 30 -q -b 404,500",
        "phases":     ["web_enum", "web_recon"],
        "requires":   ["web_port"],
        "description":"Directory enumeration — find hidden paths",
        "timeout":    120,
    },
    "gobuster_ext": {
        "cmd":        "gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt -t 30 -q -x php,html,txt,bak,zip,env -b 404,500",
        "phases":     ["web_enum"],
        "requires":   ["web_port", "gobuster_dir"],
        "description":"File extension enumeration — find source/backup/config files",
        "timeout":    120,
    },
    "nuclei_web": {
        "cmd":        "nuclei -u {target} -t http/ -severity critical,high,medium -silent",
        "phases":     ["web_vuln", "vuln_scan"],
        "requires":   ["web_port"],
        "description":"Nuclei web templates — 6000+ known vulnerability checks",
        "timeout":    180,
    },
    "sqlmap_crawl": {
        "cmd":        "sqlmap -u {target} --crawl=2 --batch --level=2 --risk=1 --forms --output-dir=/tmp/sqlmap_agent",
        "phases":     ["web_exploit", "web_vuln"],
        "requires":   ["web_port"],
        "description":"Automated SQL injection — crawl and test all forms",
        "timeout":    300,
    },
    "ffuf_params": {
        "cmd":        "ffuf -u {target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403 -t 50 -s",
        "phases":     ["web_enum"],
        "requires":   ["web_port"],
        "description":"Fast URL fuzzer — find hidden endpoints",
        "timeout":    90,
    },

    # ── SMB / Windows ─────────────────────────────────────────────────────────
    "enum4linux": {
        "cmd":        "enum4linux -a {target}",
        "phases":     ["enum", "service_enum", "ad_recon"],
        "requires":   ["smb_port"],
        "description":"SMB enumeration — users, shares, password policy",
        "timeout":    60,
    },
    "nmap_smb": {
        "cmd":        "nmap --script smb-vuln-ms17-010,smb-security-mode,smb-enum-shares -p 139,445 {target}",
        "phases":     ["vuln_check", "enum"],
        "requires":   ["smb_port"],
        "description":"SMB vulnerability check — EternalBlue + share enum",
        "timeout":    60,
    },
    "crackmapexec_smb": {
        "cmd":        "crackmapexec smb {target} --shares --users 2>/dev/null",
        "phases":     ["ad_recon", "enum"],
        "requires":   ["smb_port"],
        "description":"CME SMB null session — users, shares, domain info",
        "timeout":    30,
    },

    # ── Credentials ───────────────────────────────────────────────────────────
    "hydra_ssh": {
        "cmd":        "hydra -l root -P {wordlist} ssh://{target} -t 4 -f -q",
        "phases":     ["exploit_attempt", "vuln_scan"],
        "requires":   ["ssh_port"],
        "description":"SSH brute force — root + rockyou",
        "timeout":    120,
    },
    "hydra_ftp": {
        "cmd":        "hydra -l anonymous -P /usr/share/wordlists/metasploit/unix_passwords.txt ftp://{target} -t 4 -f -q",
        "phases":     ["exploit_attempt"],
        "requires":   ["ftp_port"],
        "description":"FTP brute force — anonymous + common passwords",
        "timeout":    60,
    },
    "hydra_http": {
        "cmd":        "hydra -L /usr/share/wordlists/metasploit/http_default_users.txt -P /usr/share/wordlists/metasploit/http_default_pass.txt {target} http-get / -t 4 -f -q",
        "phases":     ["exploit_attempt", "web_exploit"],
        "requires":   ["web_port"],
        "description":"HTTP basic auth brute force — default credentials",
        "timeout":    60,
    },

    # ── Vulnerability checking ─────────────────────────────────────────────────
    "nmap_http_scripts": {
        "cmd":        "nmap --script http-title,http-server-header,http-methods,http-shellshock,http-auth -p {ports} {target}",
        "phases":     ["web_recon", "vuln_check"],
        "requires":   ["web_port"],
        "description":"HTTP NSE scripts — headers, methods, shellshock, auth",
        "timeout":    60,
    },
    "nmap_ftp_scripts": {
        "cmd":        "nmap --script ftp-anon,ftp-vuln* -p 21 {target}",
        "phases":     ["vuln_check"],
        "requires":   ["ftp_port"],
        "description":"FTP anonymous access and vulnerability check",
        "timeout":    30,
    },

    # ── Post-exploitation / reporting ─────────────────────────────────────────
    "generate_report": {
        "cmd":        None,  # handled internally
        "phases":     ["report", "summary"],
        "description":"Generate professional penetration test report",
        "timeout":    10,
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# FINDING PARSERS — extract structured findings from tool output
# ══════════════════════════════════════════════════════════════════════════════

def _parse_findings(tool: str, stdout: str, target: str) -> List[AgentFinding]:
    """Extract structured findings from raw tool output."""
    findings = []
    lines = stdout.lower()

    if "nmap" in tool:
        # Open ports
        for m in re.finditer(r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", stdout, re.IGNORECASE):
            port, service, version = m.group(1), m.group(2), m.group(3).strip()
            findings.append(AgentFinding(
                tool=tool, kind="open_port", value=port,
                severity="info", detail=f"{service} {version}".strip()
            ))
        # Vulnerabilities
        if "VULNERABLE" in stdout or "vulnerable" in stdout:
            for m in re.finditer(r"(CVE-\d{4}-\d+)", stdout):
                findings.append(AgentFinding(
                    tool=tool, kind="vulnerability", value=m.group(1),
                    severity="critical", detail="Confirmed by nmap NSE"
                ))
        # SMB specific
        if "smb-vuln-ms17-010" in stdout.lower() and "vulnerable" in stdout.lower():
            findings.append(AgentFinding(
                tool=tool, kind="vulnerability", value="MS17-010 (EternalBlue)",
                severity="critical", detail="SMB RCE — unauth SYSTEM shell possible"
            ))

    elif "nikto" in tool:
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("+") and len(line) > 5:
                sev = "high" if any(x in line.lower() for x in ["admin","shell","rce","upload","exec"]) else "medium"
                findings.append(AgentFinding(
                    tool=tool, kind="web_finding", value=line[2:80],
                    severity=sev, detail=line
                ))

    elif "gobuster" in tool or "ffuf" in tool:
        for m in re.finditer(r"((?:/\S+)+)\s+\(Status:\s*(\d+)", stdout):
            path, code = m.group(1), m.group(2)
            sev = "high" if any(x in path.lower() for x in [".git",".env","backup","admin","config"]) else "info"
            findings.append(AgentFinding(
                tool=tool, kind="web_path", value=path,
                severity=sev, detail=f"HTTP {code}"
            ))

    elif "nuclei" in tool:
        for line in stdout.split("\n"):
            if "[critical]" in line.lower() or "[high]" in line.lower():
                sev = "critical" if "[critical]" in line.lower() else "high"
                findings.append(AgentFinding(
                    tool=tool, kind="vulnerability", value=line.strip()[:100],
                    severity=sev, detail=line
                ))

    elif "sqlmap" in tool:
        if "is vulnerable" in stdout.lower() or "injectable" in stdout.lower():
            for m in re.finditer(r"Parameter: (\S+) \((.*?)\)", stdout):
                findings.append(AgentFinding(
                    tool=tool, kind="sqli", value=m.group(1),
                    severity="critical", detail=f"Type: {m.group(2)}"
                ))

    elif "hydra" in tool:
        for m in re.finditer(r"login:\s*(\S+)\s+password:\s*(\S+)", stdout, re.IGNORECASE):
            findings.append(AgentFinding(
                tool=tool, kind="credential", value=f"{m.group(1)}:{m.group(2)}",
                severity="critical", detail="Valid credential confirmed"
            ))

    elif "enum4linux" in tool or "crackmapexec" in tool:
        # Users
        for m in re.finditer(r"user:\[(\w+)\]", stdout, re.IGNORECASE):
            findings.append(AgentFinding(
                tool=tool, kind="user", value=m.group(1),
                severity="info", detail="Enumerated user account"
            ))
        # Shares
        for m in re.finditer(r"Sharename\s+(\S+)", stdout, re.IGNORECASE):
            findings.append(AgentFinding(
                tool=tool, kind="share", value=m.group(1),
                severity="info", detail="Accessible SMB share"
            ))

    elif "whatweb" in tool:
        for m in re.finditer(r"(WordPress|Drupal|Joomla|Laravel|Django|Rails|PHP|Apache|nginx|IIS)[^\s,\]]*", stdout, re.IGNORECASE):
            findings.append(AgentFinding(
                tool=tool, kind="technology", value=m.group(0),
                severity="info", detail="Identified technology"
            ))

    return findings


def _update_state_from_findings(state: AgentState, findings: List[AgentFinding]):
    """Update agent state with new findings."""
    for f in findings:
        state.findings.append(f)
        if f.kind == "open_port" and f.value not in state.open_ports:
            state.open_ports.append(f.value)
            # Map service
            if f.detail:
                state.services[f.value] = f.detail.split()[0] if f.detail else "unknown"
        elif f.kind == "vulnerability" and f.value not in state.vulnerabilities:
            state.vulnerabilities.append(f.value)
        elif f.kind in ("credential",) and f.value not in state.credentials:
            state.credentials.append(f.value)
        elif f.kind == "shell":
            state.shells.append(f.value)


def _state_flags(state: AgentState) -> Dict[str, bool]:
    """Derived boolean flags for tool selection."""
    ports = set(state.open_ports)
    services_lower = {v.lower() for v in state.services.values()}
    return {
        "open_ports":  bool(ports),
        "web_port":    bool(ports & {"80", "443", "8080", "8443", "3000", "8000", "5000"}),
        "ssh_port":    "22" in ports,
        "smb_port":    bool(ports & {"139", "445"}),
        "ftp_port":    "21" in ports,
        "rdp_port":    "3389" in ports,
        "web_service": any(x in services_lower for x in ["http","https","nginx","apache","iis"]),
        "smb_service": any(x in services_lower for x in ["smb","netbios","samba"]),
        "ssh_service": "ssh" in services_lower,
    }


# ══════════════════════════════════════════════════════════════════════════════
# LLM DECISION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

AGENT_SYSTEM_PROMPT = """You are ERR0RS, an autonomous penetration testing agent.
Your job is to decide what security tool to run next based on findings so far.

You must respond ONLY with a valid JSON object. No explanation outside the JSON.

AVAILABLE TOOLS:
{tool_list}

RESPONSE SCHEMA:
{
  "tool":    "tool_key from the list above, or null if done",
  "target":  "the target (IP or URL — use http:// for web tools)",
  "reason":  "one concise sentence: why this tool, what we expect to find",
  "phase":   "current kill-chain phase name",
  "done":    false,
  "confidence": 0.85
}

Set "done": true when:
- All reasonable attack paths have been explored for the goal
- A shell has been obtained and post-exploitation is complete
- The goal scope has been fully covered
- No more meaningful findings are expected

RULES:
- Never repeat a tool that has already been run (completed_tools)
- Pick tools appropriate to findings: web tools for web ports, SMB tools for 445, etc.
- Prioritize HIGH SEVERITY findings — if you see MS17-010, exploit it immediately
- For web targets, always run whatweb → nikto → gobuster → nuclei in sequence
- For network targets: nmap_quick → service-specific tools → vuln checks
- credentials found = try crackmapexec/evil-winrm/ssh with those creds next
- When you have open_ports but haven't run service-specific tools, do that next"""


def _build_llm_prompt(state: AgentState, flags: Dict) -> str:
    goal_info = GOALS.get(state.goal, GOALS["full_chain"])
    tool_list = "\n".join(
        f'  "{k}": {v["description"]}'
        for k, v in AGENT_TOOLS.items()
        if k not in state.completed_tools
    )
    return f"""GOAL: {state.goal} — {goal_info['description']}
PHASES: {' → '.join(goal_info['phases'])}
CURRENT PHASE: {state.phase}

TARGET: {state.target}

CURRENT FINDINGS:
{state.findings_for_prompt()}

TOOLS ALREADY RUN: {state.tools_used_str()}

ENVIRONMENT FLAGS:
- open_ports: {', '.join(state.open_ports) or 'none yet'}
- web_port available: {flags.get('web_port', False)}
- SSH available: {flags.get('ssh_port', False)}
- SMB available: {flags.get('smb_port', False)}
- FTP available: {flags.get('ftp_port', False)}
- credentials found: {bool(state.credentials)}
- vulnerabilities confirmed: {', '.join(state.vulnerabilities) or 'none'}

STEP COUNT: {len(state.steps)} of max {goal_info['max_steps']}

What tool should run next? Choose from the available tools list.
Respond with JSON only."""


def _llm_decide(state: AgentState, flags: Dict, model: str = "gemma3:1b",
                ollama_host: str = "http://localhost:11434") -> Dict:
    """Ask the LLM to decide the next tool. Falls back to deterministic rules."""
    import requests

    tool_list = "\n".join(
        f'  "{k}": {v["description"]}'
        for k, v in AGENT_TOOLS.items()
        if k not in state.completed_tools
    )
    system = AGENT_SYSTEM_PROMPT.replace("{tool_list}", tool_list)
    prompt = _build_llm_prompt(state, flags)

    try:
        resp = requests.post(
            f"{ollama_host}/api/chat",
            json={
                "model":      model,
                "messages":   [
                    {"role": "system",  "content": system},
                    {"role": "user",    "content": prompt},
                ],
                "stream":     False,
                "keep_alive": -1,
                "options":    {"temperature": 0.2, "num_predict": 400},
            },
            timeout=90,
        )
        raw = resp.json().get("message", {}).get("content", "")
        # Strip markdown fences
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        decision = json.loads(clean)
        assert "tool" in decision
        return decision
    except Exception as e:
        log.warning(f"LLM decision failed: {e} — falling back to rules")
        return _rule_based_decision(state, flags)


def _rule_based_decision(state: AgentState, flags: Dict) -> Dict:
    """Deterministic fallback when LLM is unavailable."""
    done_tools = set(state.completed_tools)

    # No scan yet → quick scan first
    if not state.open_ports:
        for tool in ["nmap_quick", "nmap_stealth"]:
            if tool not in done_tools:
                return {"tool": tool, "target": state.target,
                        "reason": "No ports known yet — start with discovery scan",
                        "phase": "recon", "done": False, "confidence": 0.99}

    # Web ports found → web recon pipeline
    if flags.get("web_port"):
        target_url = _web_target(state)
        for tool, reason in [
            ("whatweb",    "Fingerprint web stack"),
            ("nikto",      "Scan for web vulnerabilities"),
            ("gobuster_dir", "Enumerate hidden directories"),
            ("nuclei_web", "Template-based vulnerability scan"),
            ("gobuster_ext", "Find backup/config/source files"),
        ]:
            if tool not in done_tools:
                return {"tool": tool, "target": target_url,
                        "reason": reason, "phase": "web_enum",
                        "done": False, "confidence": 0.9}

    # SMB found
    if flags.get("smb_port"):
        for tool, reason in [
            ("nmap_smb",       "Check SMB for EternalBlue"),
            ("enum4linux",     "Enumerate users, shares, password policy"),
            ("crackmapexec_smb", "CME null session recon"),
        ]:
            if tool not in done_tools:
                return {"tool": tool, "target": state.target,
                        "reason": reason, "phase": "enum",
                        "done": False, "confidence": 0.9}

    # SSH found
    if flags.get("ssh_port") and "hydra_ssh" not in done_tools:
        return {"tool": "hydra_ssh", "target": state.target,
                "reason": "SSH port open — test common credentials",
                "phase": "exploit_attempt", "done": False, "confidence": 0.7}

    # FTP found
    if flags.get("ftp_port") and "nmap_ftp_scripts" not in done_tools:
        return {"tool": "nmap_ftp_scripts", "target": state.target,
                "reason": "FTP open — check anonymous access",
                "phase": "vuln_check", "done": False, "confidence": 0.85}

    # Run vuln scan if not done
    if state.open_ports and "nmap_vuln" not in done_tools:
        ports = ",".join(state.open_ports[:10])
        return {"tool": "nmap_vuln", "target": state.target,
                "reason": f"Known open ports — run vuln scripts on {ports}",
                "phase": "vuln_scan", "done": False, "confidence": 0.85}

    # Nothing left meaningful
    return {"tool": None, "target": state.target,
            "reason": "All reasonable attack paths explored for this goal",
            "phase": state.phase, "done": True, "confidence": 0.9}


def _web_target(state: AgentState) -> str:
    """Build the right web URL from state."""
    target = state.target
    if target.startswith(("http://", "https://")):
        return target
    # Determine scheme from ports
    if "443" in state.open_ports or "8443" in state.open_ports:
        scheme = "https"
    else:
        scheme = "http"
    # Determine port
    web_ports = [p for p in state.open_ports if p in ["80","443","8080","8443","3000","8000","5000","8765"]]
    port = web_ports[0] if web_ports else "80"
    if port in ("80", "443"):
        return f"{scheme}://{target}"
    return f"{scheme}://{target}:{port}"


# ══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTOR — runs tools and captures live output
# ══════════════════════════════════════════════════════════════════════════════

def _build_command(tool_key: str, decision: Dict, state: AgentState) -> str:
    """Build the actual shell command from tool template + decision."""
    tool_def = AGENT_TOOLS[tool_key]
    cmd = tool_def["cmd"]
    target = decision.get("target", state.target)

    # Wordlist path
    wordlist = "/usr/share/wordlists/rockyou.txt"
    import os
    if not os.path.exists(wordlist):
        wordlist = os.path.expanduser("~/.err0rs/wordlists/rockyou.txt")

    # Port list
    ports = ",".join(state.open_ports[:15]) if state.open_ports else "1-1000"

    cmd = cmd.replace("{target}", target)
    cmd = cmd.replace("{ip}", state.target)
    cmd = cmd.replace("{ports}", ports)
    cmd = cmd.replace("{wordlist}", wordlist)

    return cmd


def _run_tool(cmd: str, timeout: int, broadcast: Callable) -> str:
    """Execute a shell command, streaming output via broadcast callback."""
    broadcast({"type": "output", "data": f"$ {cmd}"})
    stdout_lines = []
    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        start = time.time()
        for line in proc.stdout:
            line = line.rstrip()
            stdout_lines.append(line)
            broadcast({"type": "output", "data": line})
            if time.time() - start > timeout:
                proc.kill()
                broadcast({"type": "system", "data": f"[ERR0RS AGENT] Tool timeout after {timeout}s"})
                break
        proc.wait(timeout=5)
    except Exception as e:
        broadcast({"type": "error", "data": f"Tool execution error: {e}"})
    return "\n".join(stdout_lines)


# ══════════════════════════════════════════════════════════════════════════════
# THE AGENT
# ══════════════════════════════════════════════════════════════════════════════

class PentestAgent:
    """
    ERR0RS Autonomous Penetration Testing Agent.

    ReAct loop: Observe → Reason → Act → Observe → ...

    Usage:
        agent = PentestAgent(broadcast_fn=ws_send)
        agent.start(target="192.168.1.100", goal="full_chain")
    """

    def __init__(self,
                 broadcast_fn:  Callable,
                 model:         str = "gemma3:1b",
                 ollama_host:   str = "http://localhost:11434"):
        self.broadcast   = broadcast_fn
        self.model       = model
        self.ollama_host = ollama_host
        self._thread:    Optional[threading.Thread] = None
        self._state:     Optional[AgentState]       = None
        self._stop_flag  = threading.Event()

    def start(self, target: str, goal: str = "full_chain") -> AgentState:
        """Start the agent in a background thread."""
        if self._thread and self._thread.is_alive():
            self._emit_system("Agent already running. Stop it first.")
            return self._state

        self._stop_flag.clear()
        goal_cfg = GOALS.get(goal, GOALS["full_chain"])

        self._state = AgentState(
            target=target,
            goal=goal,
            phase=goal_cfg["phases"][0],
        )

        self._thread = threading.Thread(
            target=self._run_loop,
            args=(goal_cfg,),
            daemon=True,
        )
        self._thread.start()
        return self._state

    def stop(self, reason: str = "Operator requested stop"):
        """Stop the agent."""
        self._stop_flag.set()
        if self._state:
            self._state.running = False
            self._state.abort_reason = reason

    def status(self) -> Dict:
        if not self._state:
            return {"running": False, "state": None}
        s = self._state
        return {
            "running":   s.running and not s.done,
            "target":    s.target,
            "goal":      s.goal,
            "phase":     s.phase,
            "steps":     len(s.steps),
            "findings":  len(s.findings),
            "open_ports": s.open_ports,
            "vulns":     s.vulnerabilities,
            "creds":     len(s.credentials),
            "next":      (s.next_todo().title if s.next_todo() else None),
            "ptt":       s.ptt_for_prompt(),
        }

    # ── Internal loop ─────────────────────────────────────────────────────────

    def _run_loop(self, goal_cfg: Dict):
        state = self._state
        max_steps = goal_cfg["max_steps"]
        state.seed_ptt(goal_cfg.get("phases", []))

        self._emit_banner(state)

        step_num = 0
        while step_num < max_steps and not self._stop_flag.is_set():
            step_num += 1
            self._emit_system(f"\n{'═'*54}")
            self._emit_system(f"[AGENT] Step {step_num}/{max_steps} — Phase: {state.phase}")
            self._emit_system(f"[AGENT] Findings so far: {len(state.findings)} | Open ports: {', '.join(state.open_ports) or 'none'}")
            self._emit_system(f"{'─'*54}")

            # ── OBSERVE: build flags from current state ───────────────────────
            flags = _state_flags(state)

            # ── REASON: LLM (or rules) picks next tool ────────────────────────
            self._emit_system("[AGENT] 🧠 Reasoning about next action...")
            # Rules plan the loop (instant). gemma3:1b is too slow for the hot
            # path on Pi CPU (~248s/decision measured) - it narrates async below.
            decision = _rule_based_decision(state, flags)

            tool_key = decision.get("tool")
            reason   = decision.get("reason", "")
            done     = decision.get("done", False)

            self._emit_system(f"[AGENT] Decision: {tool_key or 'DONE'}")
            self._emit_system(f"[AGENT] Reasoning: {reason}")

            # ── CHECK DONE ────────────────────────────────────────────────────
            if done or not tool_key or tool_key == "null":
                self._emit_system(f"\n[AGENT] ✅ Goal complete — {reason}")
                state.done = True
                break

            # ── VALIDATE TOOL ─────────────────────────────────────────────────
            if tool_key not in AGENT_TOOLS:
                self._emit_system(f"[AGENT] ⚠️  Unknown tool '{tool_key}' — skipping")
                continue

            if tool_key in state.completed_tools:
                self._emit_system(f"[AGENT] ⚠️  '{tool_key}' already run — skipping")
                continue

            tool_def = AGENT_TOOLS[tool_key]

            # ── Check binary available ────────────────────────────────────────
            if tool_def.get("cmd"):
                binary = tool_def["cmd"].split()[0]
                if not shutil.which(binary):
                    self._emit_system(f"[AGENT] ⚠️  '{binary}' not in PATH — skipping")
                    state.completed_tools.append(tool_key)
                    continue

            # ── Handle report generation ──────────────────────────────────────
            if tool_key == "generate_report":
                self._generate_report(state)
                state.completed_tools.append(tool_key)
                state.done = True
                break

            # ── ACT: build and run the command ────────────────────────────────
            # NARRATE (async): gemma explains the move while the tool runs.
            self._narrate_async(state, tool_key, reason)
            cmd = _build_command(tool_key, decision, state)
            # ── 5-slot STEP narration (instant, static) ───────────────────────
            # Explains WHAT this step does and WHY *before* the tool fires, via
            # the shared teach_engine formatter. No LLM, no blocking; degrades
            # to nothing for tools without a STEP_DETAILS entry.
            try:
                from .narrator import step_narration as _step_narr
                _sn = _step_narr(tool_key)
                if _sn:
                    self._emit_system("[AGENT] 🪜 STEP — what this does & why:\n" + _sn)
            except Exception:
                pass
            self._emit_system(f"\n[AGENT] ⚡ Running: {tool_key}")

            start_time = time.time()
            stdout = _run_tool(cmd, tool_def.get("timeout", 120), self.broadcast)
            duration = time.time() - start_time

            # ── ANALYZE: extract findings ─────────────────────────────────────
            findings = _parse_findings(tool_key, stdout, state.target)
            _update_state_from_findings(state, findings)
            state.completed_tools.append(tool_key)

            # ── Store step ────────────────────────────────────────────────────
            step = AgentStep(
                step=step_num, phase=state.phase,
                tool=tool_key, command=cmd,
                stdout=stdout, findings=findings,
                decision=decision, duration=duration,
            )
            state.steps.append(step)

            # -- PTT: mark this tool done, peek the next pick, persist memory --
            state.complete_task(tool_key, ok=bool(stdout and stdout.strip()))
            try:
                _nxt = _rule_based_decision(state, _state_flags(state))
                if _nxt.get("tool") and _nxt["tool"] not in state.completed_tools:
                    state.add_task(_nxt.get("phase", state.phase),
                                   _nxt["tool"], _nxt.get("reason", _nxt["tool"]))
            except Exception:
                pass
            try:
                state.save()
            except Exception:
                pass

            self._emit_system("[AGENT] 🧭 PTT (done / next):\n" + state.ptt_for_prompt())

            # ── Report new findings ───────────────────────────────────────────
            if findings:
                self._emit_system(f"\n[AGENT] 🔍 {len(findings)} finding(s) from {tool_key}:")
                for f in findings[:8]:
                    icon = {"critical":"🔴","high":"🟠","medium":"🟡","info":"⚪"}.get(f.severity,"•")
                    self._emit_system(f"  {icon} [{f.severity.upper()}] {f.kind}: {f.value}")
                    if f.detail:
                        self._emit_system(f"      {f.detail[:80]}")

            # ── Auto-coach on significant findings ───────────────────────────
            try:
                from src.core.auto_coach import coach_output
                coach_output(tool_key, stdout, state.target, self.broadcast)
            except Exception:
                pass

            # ── Update phase based on progress ───────────────────────────────
            state.phase = decision.get("phase", state.phase)

            # ── Award XP ─────────────────────────────────────────────────────
            try:
                from src.core.progression import award_xp
                award_xp(f"run_{tool_key.split('_')[0]}", state.target)
                if any(f.severity in ("critical","high") for f in findings):
                    award_xp("found_vuln", f"{tool_key}: {len(findings)} findings")
                if any(f.kind == "credential" for f in findings):
                    award_xp("found_creds", state.target)
            except Exception:
                pass

            # ── Brief pause between tools ────────────────────────────────────
            if not self._stop_flag.is_set():
                time.sleep(1.5)

        # ── Loop ended ────────────────────────────────────────────────────────
        state.running = False
        self._emit_final_summary(state)

    def _narrate_async(self, state: "AgentState", tool_key: str, reason: str):
        """Fire gemma in the background to explain this step in plain English.
        Best-effort commentary; never blocks the loop."""
        threading.Thread(
            target=self._narrate_worker,
            args=(state.target, state.phase, tool_key, reason,
                  dict(state.services), list(state.open_ports)),
            daemon=True,
        ).start()

    def _narrate_worker(self, target, phase, tool_key, reason, services, open_ports):
        """Short scoped gemma call -> one plain-English line of operator narration."""
        import requests
        tool_desc = AGENT_TOOLS.get(tool_key, {}).get("description", tool_key)
        known = ", ".join(f"{p}/{services.get(p, '?')}" for p in open_ports) or "nothing yet"
        prompt = (
            "You are a senior red-team operator narrating a live engagement to a "
            "student. In 1-2 short sentences of plain English, explain WHY we now run "
            f"'{tool_key}' ({tool_desc}) against {target}, and what a good result would "
            f"tell us. Current phase: {phase}. Known so far: {known}. "
            "Be concrete and calm. No preamble, no markdown, no lists."
        )
        try:
            resp = requests.post(
                f"{self.ollama_host}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "keep_alive": -1,
                    "options": {"temperature": 0.3, "num_predict": 90},
                },
                timeout=240,
            )
            text = resp.json().get("message", {}).get("content", "").strip()
            if text and not self._stop_flag.is_set():
                self._emit_system("🗣️  " + text)
        except Exception:
            pass  # narration is best-effort; never disrupt the loop

    def _emit_system(self, msg: str):
        self.broadcast({"type": "system", "data": msg})

    def _emit_banner(self, state: AgentState):
        goal_cfg = GOALS.get(state.goal, GOALS["full_chain"])
        self.broadcast({"type": "system", "data": f"""
{'═'*60}
  🤖 ERR0RS AUTONOMOUS AGENT — ACTIVATED
{'─'*60}
  Target:  {state.target}
  Goal:    {state.goal} — {goal_cfg['description']}
  Phases:  {' → '.join(goal_cfg['phases'])}
  Max steps: {goal_cfg['max_steps']}
  Mode:    Rules-driven ReAct loop · gemma3:1b narrates live
{'═'*60}
  [AGENT] Engage. Zero tolerance for missed findings.
{'═'*60}
"""})

    def _generate_report(self, state: AgentState):
        """Generate a final report from agent findings."""
        self._emit_system("\n[AGENT] 📄 Generating penetration test report...")
        try:
            from src.core.report_gen import generate as gen_report
            result = gen_report(state, output_dir="/tmp")
            self._emit_system(f"[AGENT] Report saved → {result}")
        except Exception as e:
            # Inline markdown report
            report = self._build_inline_report(state)
            self._emit_system(report)

    def _build_inline_report(self, state: AgentState) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        crits = [f for f in state.findings if f.severity == "critical"]
        highs = [f for f in state.findings if f.severity == "high"]
        meds  = [f for f in state.findings if f.severity == "medium"]

        lines = [
            f"\n{'═'*60}",
            f"  PENETRATION TEST REPORT",
            f"  ERR0RS-Ultimate Autonomous Agent",
            f"{'─'*60}",
            f"  Target:    {state.target}",
            f"  Goal:      {state.goal}",
            f"  Date:      {now}",
            f"  Steps:     {len(state.steps)}",
            f"  Tools:     {', '.join(state.completed_tools)}",
            f"{'─'*60}",
            f"  FINDINGS SUMMARY",
            f"  🔴 Critical: {len(crits)}",
            f"  🟠 High:     {len(highs)}",
            f"  🟡 Medium:   {len(meds)}",
            f"{'─'*60}",
            f"  OPEN PORTS: {', '.join(state.open_ports) or 'None identified'}",
        ]
        if state.vulnerabilities:
            lines.append(f"  VULNERABILITIES: {', '.join(state.vulnerabilities)}")
        if state.credentials:
            lines.append(f"  CREDENTIALS: {len(state.credentials)} credential(s) found")
        if crits:
            lines.append(f"\n  CRITICAL FINDINGS:")
            for f in crits:
                lines.append(f"  🔴 {f.kind}: {f.value}")
                if f.detail:
                    lines.append(f"     {f.detail}")
        lines.append(f"{'═'*60}")
        return "\n".join(lines)

    def _emit_final_summary(self, state: AgentState):
        crits = len([f for f in state.findings if f.severity == "critical"])
        highs = len([f for f in state.findings if f.severity == "high"])
        self._emit_system(f"""
{'═'*60}
  🤖 AGENT COMPLETE
{'─'*60}
  Target:    {state.target}
  Steps run: {len(state.steps)}
  Findings:  {len(state.findings)} ({crits} critical, {highs} high)
  Ports:     {', '.join(state.open_ports) or 'none'}
  Vulns:     {', '.join(state.vulnerabilities) or 'none'}
  Creds:     {len(state.credentials)} found
  Status:    {'✅ Goal complete' if state.done else '⚠️  Stopped: ' + state.abort_reason}
{'═'*60}
""")


# ── Global agent singleton ────────────────────────────────────────────────────
_agent: Optional[PentestAgent] = None

def get_agent(broadcast_fn: Callable = None,
              model: str = "gemma3:1b") -> PentestAgent:
    global _agent
    if _agent is None and broadcast_fn:
        _agent = PentestAgent(broadcast_fn=broadcast_fn, model=model)
    return _agent
