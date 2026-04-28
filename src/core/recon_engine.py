#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║     ERR0RS ULTIMATE — AUTONOMOUS RECON ENGINE                   ║
║              src/core/recon_engine.py                           ║
║                                                                  ║
║  Fully autonomous reconnaissance that runs continuously,        ║
║  chains tools intelligently, and feeds findings directly        ║
║  into the agent loop and surface monitor.                       ║
║                                                                  ║
║  Recon phases (auto-chained):                                   ║
║    1. PASSIVE  — OSINT, DNS, cert transparency, Shodan-style    ║
║    2. ACTIVE   — port scan, service ID, banner grab             ║
║    3. WEB      — tech fingerprint, dir enum, API discovery      ║
║    4. DEEP     — vuln scan, version CVEs, config check          ║
║    5. CORRELATE — map findings → attack surface graph           ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import re
import shutil
import socket
import subprocess
import threading
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any

log = logging.getLogger("err0rs.recon")


# ── Recon finding ─────────────────────────────────────────────────────────────
@dataclass
class ReconFinding:
    category:  str          # dns, port, service, web, vuln, cred, osint
    key:       str          # specific item (port number, domain, etc.)
    value:     str          # the actual data
    source:    str          # which tool produced this
    severity:  str = "info" # critical, high, medium, low, info
    confidence:float = 1.0
    ts:        str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "category": self.category, "key": self.key,
            "value": self.value, "source": self.source,
            "severity": self.severity, "confidence": self.confidence,
        }


# ── Recon state ───────────────────────────────────────────────────────────────
@dataclass
class ReconState:
    target:         str
    start_time:     str = field(default_factory=lambda: datetime.now().isoformat())
    phase:          str = "passive"
    findings:       List[ReconFinding] = field(default_factory=list)
    open_ports:     List[str] = field(default_factory=list)
    services:       Dict[str, str] = field(default_factory=dict)
    hostnames:      List[str] = field(default_factory=list)
    ips:            List[str] = field(default_factory=list)
    web_paths:      List[str] = field(default_factory=list)
    technologies:   List[str] = field(default_factory=list)
    vulnerabilities:List[str] = field(default_factory=list)
    subdomains:     List[str] = field(default_factory=list)
    emails:         List[str] = field(default_factory=list)
    completed_tools:List[str] = field(default_factory=list)
    running:        bool = True
    done:           bool = False

    def add(self, finding: ReconFinding):
        self.findings.append(finding)
        if finding.category == "port" and finding.key not in self.open_ports:
            self.open_ports.append(finding.key)
        elif finding.category == "service":
            self.services[finding.key] = finding.value
        elif finding.category == "hostname" and finding.value not in self.hostnames:
            self.hostnames.append(finding.value)
        elif finding.category == "web_path" and finding.key not in self.web_paths:
            self.web_paths.append(finding.key)
        elif finding.category == "technology" and finding.value not in self.technologies:
            self.technologies.append(finding.value)
        elif finding.category == "vuln" and finding.value not in self.vulnerabilities:
            self.vulnerabilities.append(finding.value)
        elif finding.category == "subdomain" and finding.value not in self.subdomains:
            self.subdomains.append(finding.value)
        elif finding.category == "email" and finding.value not in self.emails:
            self.emails.append(finding.value)
        elif finding.category == "ip" and finding.value not in self.ips:
            self.ips.append(finding.value)

    def summary(self) -> Dict:
        return {
            "target":    self.target,
            "phase":     self.phase,
            "findings":  len(self.findings),
            "ports":     self.open_ports,
            "services":  self.services,
            "hostnames": self.hostnames,
            "subdomains":self.subdomains,
            "web_paths": self.web_paths[:10],
            "techs":     self.technologies,
            "vulns":     self.vulnerabilities,
            "done":      self.done,
        }


# ══════════════════════════════════════════════════════════════════════════════
# PASSIVE RECON — no packets to target, pure OSINT
# ══════════════════════════════════════════════════════════════════════════════

def _passive_dns(target: str, state: ReconState, emit: Callable):
    """DNS enumeration — A, AAAA, MX, TXT, NS, CNAME."""
    emit({"type": "system", "data": "[RECON] 🌐 Passive DNS enumeration..."})
    record_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]
    for rtype in record_types:
        try:
            result = subprocess.run(
                ["dig", "+short", rtype, target],
                capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    line = line.strip().rstrip(".")
                    if not line:
                        continue
                    category = "ip" if rtype == "A" else "hostname"
                    state.add(ReconFinding(
                        category=category, key=rtype,
                        value=line, source="dig",
                    ))
                    emit({"type": "output", "data": f"  DNS {rtype}: {line}"})
        except Exception:
            pass

def _passive_cert_transparency(target: str, state: ReconState, emit: Callable):
    """Certificate transparency logs — find subdomains via crt.sh."""
    emit({"type": "system", "data": "[RECON] 🔐 Checking certificate transparency logs..."})
    domain = target.replace("https://","").replace("http://","").split("/")[0]
    try:
        import urllib.request
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent": "ERR0RS-Recon/3.3"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        seen = set()
        for entry in data[:100]:
            name = entry.get("name_value", "").strip()
            for sub in name.split("\n"):
                sub = sub.strip().lstrip("*.")
                if sub and sub not in seen and domain in sub:
                    seen.add(sub)
                    state.add(ReconFinding(
                        category="subdomain", key="crt.sh",
                        value=sub, source="cert_transparency",
                        confidence=0.95,
                    ))
        emit({"type": "output", "data": f"  crt.sh: {len(seen)} subdomains found"})
        for s in list(seen)[:10]:
            emit({"type": "output", "data": f"  → {s}"})
    except Exception as e:
        emit({"type": "output", "data": f"  crt.sh unavailable ({e.__class__.__name__})"})

def _passive_whois(target: str, state: ReconState, emit: Callable):
    """WHOIS lookup for registration info."""
    emit({"type": "system", "data": "[RECON] 📋 WHOIS lookup..."})
    domain = target.replace("https://","").replace("http://","").split("/")[0]
    if not shutil.which("whois"):
        return
    try:
        result = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
        for line in result.stdout.split("\n"):
            line = line.strip()
            if any(k in line.lower() for k in ["registrar:", "name server:", "creation date:", "expiry date:"]):
                emit({"type": "output", "data": f"  {line}"})
            # Extract emails
            emails = re.findall(r"[\w.+-]+@[\w.-]+\.\w+", line)
            for email in emails:
                state.add(ReconFinding(category="email", key="whois",
                                       value=email, source="whois"))
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# ACTIVE RECON — direct target interaction
# ══════════════════════════════════════════════════════════════════════════════

def _active_port_scan(target: str, state: ReconState, emit: Callable):
    """Fast nmap port scan — service detection + scripts."""
    emit({"type": "system", "data": "[RECON] ⚡ Active port scanning..."})
    if not shutil.which("nmap"):
        emit({"type": "output", "data": "  nmap not found — skipping"})
        return

    cmd = f"nmap -sV --top-ports 1000 -T4 --open {target}"
    emit({"type": "output", "data": f"$ {cmd}"})
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.rstrip()
            emit({"type": "output", "data": line})
            # Parse open ports
            m = re.match(r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", line)
            if m:
                port, service, version = m.group(1), m.group(2), m.group(3).strip()
                state.add(ReconFinding(category="port", key=port,
                                       value=f"{service} {version}".strip(), source="nmap"))
                state.add(ReconFinding(category="service", key=port,
                                       value=service, source="nmap"))
        proc.wait(timeout=120)
    except Exception as e:
        emit({"type": "output", "data": f"  Port scan error: {e}"})

def _active_banner_grab(target: str, state: ReconState, emit: Callable):
    """Banner grab on open ports not fully identified by nmap."""
    emit({"type": "system", "data": "[RECON] 🏷️  Banner grabbing open ports..."})
    ip = target.replace("https://","").replace("http://","").split("/")[0]
    for port in state.open_ports[:10]:
        try:
            with socket.create_connection((ip, int(port)), timeout=3) as s:
                s.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                banner = s.recv(1024).decode(errors="ignore").strip()
                if banner:
                    state.add(ReconFinding(
                        category="banner", key=port,
                        value=banner[:200], source="banner_grab",
                    ))
                    emit({"type": "output", "data": f"  Port {port}: {banner[:80]}"})
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# WEB RECON — if web ports found
# ══════════════════════════════════════════════════════════════════════════════

def _web_fingerprint(target: str, state: ReconState, emit: Callable):
    """WhatWeb + Nikto for web technology fingerprinting."""
    web_ports = [p for p in state.open_ports if p in ["80","443","8080","8443","3000","8000","5000"]]
    if not web_ports:
        return

    scheme = "https" if "443" in web_ports else "http"
    port = web_ports[0]
    url = f"{scheme}://{target}" if port in ("80","443") else f"{scheme}://{target}:{port}"

    emit({"type": "system", "data": f"[RECON] 🌐 Web fingerprinting: {url}"})

    if shutil.which("whatweb"):
        cmd = f"whatweb {url} -a 3 --no-errors 2>/dev/null"
        emit({"type": "output", "data": f"$ {cmd}"})
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                     text=True, timeout=30)
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line:
                    emit({"type": "output", "data": line})
                    # Extract technologies
                    for tech in re.findall(r"(WordPress|Drupal|Joomla|Apache|nginx|PHP|Django|Rails|Laravel|IIS|jQuery|Bootstrap)\[?[\d.]*\]?", line, re.IGNORECASE):
                        state.add(ReconFinding(category="technology", key="whatweb",
                                               value=tech, source="whatweb"))
        except Exception:
            pass

def _web_dir_enum(target: str, state: ReconState, emit: Callable):
    """Gobuster directory enumeration."""
    web_ports = [p for p in state.open_ports if p in ["80","443","8080","8443","3000","8000","5000"]]
    if not web_ports or not shutil.which("gobuster"):
        return

    scheme = "https" if "443" in web_ports else "http"
    port = web_ports[0]
    url = f"{scheme}://{target}" if port in ("80","443") else f"{scheme}://{target}:{port}"
    wordlist = "/usr/share/wordlists/dirb/common.txt"
    if not shutil.which("gobuster") or not __import__("os").path.exists(wordlist):
        return

    emit({"type": "system", "data": f"[RECON] 📂 Directory enumeration: {url}"})
    cmd = f"gobuster dir -u {url} -w {wordlist} -t 30 -q -b 404,500,503 2>/dev/null"
    emit({"type": "output", "data": f"$ {cmd}"})
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                emit({"type": "output", "data": line})
                m = re.search(r"((?:/\S+)+)\s+\(Status:", line)
                if m:
                    path = m.group(1)
                    sev = "high" if any(x in path.lower() for x in
                                       [".git",".env","admin","backup","config",".bak",".zip"]) else "info"
                    state.add(ReconFinding(category="web_path", key=path,
                                           value=line[:100], source="gobuster", severity=sev))
        proc.wait(timeout=90)
    except Exception as e:
        emit({"type": "output", "data": f"  Dir enum error: {e}"})


# ══════════════════════════════════════════════════════════════════════════════
# DEEP RECON — vulnerability checks
# ══════════════════════════════════════════════════════════════════════════════

def _vuln_scan(target: str, state: ReconState, emit: Callable):
    """Nmap vuln scripts on discovered ports."""
    if not state.open_ports or not shutil.which("nmap"):
        return
    ports = ",".join(state.open_ports[:15])
    emit({"type": "system", "data": f"[RECON] 🔴 Vulnerability scan on ports: {ports}"})
    cmd = f"nmap --script vuln -p {ports} {target} 2>/dev/null"
    emit({"type": "output", "data": f"$ {cmd}"})
    try:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.rstrip()
            emit({"type": "output", "data": line})
            if "VULNERABLE" in line or "vulnerable" in line.lower():
                state.add(ReconFinding(category="vuln", key="nmap_vuln",
                                       value=line.strip()[:100], source="nmap_scripts",
                                       severity="high"))
            cve = re.search(r"CVE-\d{4}-\d+", line)
            if cve:
                state.add(ReconFinding(category="vuln", key=cve.group(0),
                                       value=cve.group(0), source="nmap_scripts",
                                       severity="critical"))
        proc.wait(timeout=180)
    except Exception as e:
        emit({"type": "output", "data": f"  Vuln scan error: {e}"})

def _smb_recon(target: str, state: ReconState, emit: Callable):
    """SMB-specific recon if 445 is open."""
    if "445" not in state.open_ports and "139" not in state.open_ports:
        return
    emit({"type": "system", "data": "[RECON] 🏢 SMB recon..."})
    if shutil.which("nmap"):
        cmd = f"nmap --script smb-vuln-ms17-010,smb-security-mode,smb-enum-shares -p 139,445 {target} 2>/dev/null"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                     text=True, timeout=60)
            for line in result.stdout.split("\n"):
                emit({"type": "output", "data": line})
                if "VULNERABLE" in line:
                    state.add(ReconFinding(category="vuln", key="smb_vuln",
                                           value=line.strip()[:100], source="nmap_smb",
                                           severity="critical"))
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# CORRELATION ENGINE — connect the dots
# ══════════════════════════════════════════════════════════════════════════════

def _correlate(state: ReconState, emit: Callable):
    """Build attack surface map from all findings."""
    emit({"type": "system", "data": "[RECON] 🔗 Correlating findings into attack surface map..."})

    attack_paths = []

    if "445" in state.open_ports or "139" in state.open_ports:
        attack_paths.append("SMB → EternalBlue / NTLM relay / credential dump")
    if any(p in state.open_ports for p in ["80","443","8080","3000"]):
        attack_paths.append("Web → SQLi / XSS / file upload / admin panel")
    if "22" in state.open_ports:
        attack_paths.append("SSH → credential brute force / key theft")
    if "21" in state.open_ports:
        attack_paths.append("FTP → anonymous access / credential attack")
    if "3389" in state.open_ports:
        attack_paths.append("RDP → BlueKeep / credential spray")
    if any("critical" == f.severity for f in state.findings):
        attack_paths.append("CRITICAL VULNERABILITIES → immediate exploitation attempt")

    if state.vulnerabilities:
        attack_paths.append(f"Confirmed vulns: {', '.join(state.vulnerabilities[:3])}")

    emit({"type": "system", "data": "\n[RECON] 🗺️  ATTACK SURFACE MAP:"})
    for path in attack_paths:
        emit({"type": "output", "data": f"  → {path}"})

    # Push to auto-coach for each critical finding
    crits = [f for f in state.findings if f.severity == "critical"]
    if crits:
        emit({"type": "output", "data": f"\n  🔴 {len(crits)} CRITICAL FINDINGS — immediate action recommended"})

    return attack_paths


# ══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS RECON ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ReconEngine:
    """
    Fully autonomous recon engine.
    Chains passive → active → web → deep → correlate automatically.
    Every finding feeds the next phase.
    """

    def __init__(self, broadcast_fn: Callable):
        self.broadcast   = broadcast_fn
        self._thread:    Optional[threading.Thread] = None
        self._state:     Optional[ReconState] = None
        self._stop_flag  = threading.Event()

    def start(self, target: str, depth: str = "full") -> ReconState:
        """
        Start autonomous recon.
        depth: 'passive' | 'active' | 'web' | 'full'
        """
        if self._thread and self._thread.is_alive():
            self._emit("[RECON] Already running. Stop first.")
            return self._state

        self._stop_flag.clear()
        self._state = ReconState(target=target)

        self._thread = threading.Thread(
            target=self._run,
            args=(depth,),
            daemon=True,
        )
        self._thread.start()
        return self._state

    def stop(self):
        self._stop_flag.set()
        if self._state:
            self._state.running = False

    def status(self) -> Dict:
        if not self._state:
            return {"running": False}
        return self._state.summary()

    def _emit(self, msg: str):
        self.broadcast({"type": "system", "data": msg})

    def _run(self, depth: str):
        state = self._state
        emit  = self.broadcast
        target = state.target

        self._emit(f"""
{'═'*56}
  🔍 ERR0RS AUTONOMOUS RECON ENGINE — ACTIVE
{'─'*56}
  Target: {target}
  Depth:  {depth}
  Auto-chaining: passive → active → web → vuln → correlate
{'═'*56}
""")

        # Phase 1 — Passive (always)
        if not self._stop_flag.is_set():
            state.phase = "passive"
            _passive_dns(target, state, emit)
            _passive_cert_transparency(target, state, emit)
            _passive_whois(target, state, emit)

        if depth == "passive":
            self._finish(state)
            return

        # Phase 2 — Active
        if not self._stop_flag.is_set():
            state.phase = "active"
            _active_port_scan(target, state, emit)
            _active_banner_grab(target, state, emit)
            _smb_recon(target, state, emit)

        if depth == "active":
            self._finish(state)
            return

        # Phase 3 — Web (if web ports found)
        if not self._stop_flag.is_set() and any(
            p in state.open_ports for p in ["80","443","8080","8443","3000","8000"]
        ):
            state.phase = "web"
            _web_fingerprint(target, state, emit)
            _web_dir_enum(target, state, emit)

        if depth == "web":
            self._finish(state)
            return

        # Phase 4 — Deep vuln scan
        if not self._stop_flag.is_set():
            state.phase = "vuln"
            _vuln_scan(target, state, emit)

        # Phase 5 — Correlate
        if not self._stop_flag.is_set():
            state.phase = "correlate"
            attack_paths = _correlate(state, emit)

        # Award XP
        try:
            from src.core.progression import award_xp
            award_xp("complete_recon", target)
            if state.vulnerabilities:
                award_xp("found_vuln", f"recon: {len(state.vulnerabilities)} vulns")
        except Exception:
            pass

        self._finish(state)

    def _finish(self, state: ReconState):
        state.done    = True
        state.running = False
        crits = len([f for f in state.findings if f.severity == "critical"])
        highs = len([f for f in state.findings if f.severity == "high"])
        self._emit(f"""
{'═'*56}
  🔍 RECON COMPLETE
{'─'*56}
  Target:    {state.target}
  Findings:  {len(state.findings)} ({crits} critical, {highs} high)
  Ports:     {', '.join(state.open_ports) or 'none'}
  Subdomains:{len(state.subdomains)} found
  Web paths: {len(state.web_paths)} found
  Techs:     {', '.join(state.technologies[:5]) or 'none'}
  Vulns:     {', '.join(state.vulnerabilities[:3]) or 'none'}
{'═'*56}
""")


# ── Global singleton ──────────────────────────────────────────────────────────
_recon: Optional[ReconEngine] = None

def get_recon_engine(broadcast_fn: Callable = None) -> Optional[ReconEngine]:
    global _recon
    if _recon is None and broadcast_fn:
        _recon = ReconEngine(broadcast_fn=broadcast_fn)
    return _recon
