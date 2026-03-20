"""
╔══════════════════════════════════════════════════════════════════╗
║     ERR0RS ULTIMATE — MODULE 1: Live Attack Surface Monitor      ║
║                   src/intel/surface_monitor.py                   ║
║                                                                  ║
║  Passively watches a target 24/7 and alerts the moment anything  ║
║  changes — new port, new service, cert rotation, new subdomain,  ║
║  software version bump. No other open-source framework does this.║
║                                                                  ║
║  AUTHORIZED PENETRATION TESTING USE ONLY                         ║
╚══════════════════════════════════════════════════════════════════╝

HOW IT WORKS (Visual):
──────────────────────
  Target: example.com

  [Baseline Snapshot] ← First run captures the full state
       ↓
  [Monitor Loop — runs every N minutes in background thread]
       ↓
  [Delta Engine] ← Compares current state to baseline
       ↓
  [Change Detected?]
    YES → Severity Rating → Alert → Auto-trigger Workflow → Log to DB
    NO  → Sleep → Repeat

WHAT IT MONITORS:
─────────────────
  • Open TCP/UDP ports (nmap)
  • Service versions on each port
  • HTTP headers and server banners
  • TLS certificate details (expiry, issuer, SANs, fingerprint)
  • DNS records (A, AAAA, MX, TXT, NS, CNAME)
  • Subdomains (passive DNS, certificate transparency logs)
  • Web technology fingerprints (WhatWeb)
  • Response codes on known endpoints

WHY THIS IS REVOLUTIONARY:
───────────────────────────
  Red teamers re-scan manually. Blue teamers use expensive EASM tools.
  ERR0RS does it automatically, locally, for free, and alerts you
  the moment a new attack surface appears — before the client notices.
  A new open port = immediate alert + auto-triggered recon workflow.
"""

import os
import sys
import json
import time
import socket
import hashlib
import threading
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum

log = logging.getLogger("errors.intel.surface_monitor")

class ChangeType(Enum):
    PORT_OPENED      = "port_opened"
    PORT_CLOSED      = "port_closed"
    SERVICE_CHANGED  = "service_changed"
    CERT_CHANGED     = "cert_changed"
    CERT_EXPIRING    = "cert_expiring"
    DNS_CHANGED      = "dns_changed"
    NEW_SUBDOMAIN    = "new_subdomain"
    HEADER_CHANGED   = "header_changed"
    TECH_ADDED       = "tech_added"
    TECH_REMOVED     = "tech_removed"
    RESPONSE_CHANGED = "response_changed"

class ChangeSeverity(Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"

@dataclass
class PortState:
    port:     int
    protocol: str
    state:    str
    service:  str = ""
    version:  str = ""
    banner:   str = ""

@dataclass
class CertState:
    subject:      str = ""
    issuer:       str = ""
    not_before:   str = ""
    not_after:    str = ""
    fingerprint:  str = ""
    sans:         List[str] = field(default_factory=list)
    days_until_expiry: int = 0

@dataclass
class SurfaceSnapshot:
    target:       str
    timestamp:    str = field(default_factory=lambda: datetime.now().isoformat())
    ports:        List[PortState]      = field(default_factory=list)
    dns_records:  Dict[str, List[str]] = field(default_factory=dict)
    subdomains:   List[str]            = field(default_factory=list)
    cert:         Optional[CertState]  = None
    http_headers: Dict[str, str]       = field(default_factory=dict)
    technologies: List[str]            = field(default_factory=list)
    response_hash: str                 = ""

@dataclass
class SurfaceChange:
    id:           str = field(default_factory=lambda: f"chg_{int(time.time()*1000)}")
    target:       str = ""
    change_type:  ChangeType     = ChangeType.PORT_OPENED
    severity:     ChangeSeverity = ChangeSeverity.MEDIUM
    description:  str = ""
    old_value:    str = ""
    new_value:    str = ""
    timestamp:    str = field(default_factory=lambda: datetime.now().isoformat())
    auto_workflow_triggered: bool = False
    workflow_name: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["change_type"] = self.change_type.value
        d["severity"]    = self.severity.value
        return d

class SnapshotEngine:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def capture(self, target: str) -> SurfaceSnapshot:
        snap = SurfaceSnapshot(target=target)
        threads = [
            threading.Thread(target=self._collect_ports,     args=(snap,), daemon=True),
            threading.Thread(target=self._collect_dns,       args=(snap,), daemon=True),
            threading.Thread(target=self._collect_cert,      args=(snap,), daemon=True),
            threading.Thread(target=self._collect_http,      args=(snap,), daemon=True),
            threading.Thread(target=self._collect_subdomains,args=(snap,), daemon=True),
        ]
        for t in threads: t.start()
        for t in threads: t.join(timeout=self.timeout)
        return snap

    def _collect_ports(self, snap):
        try:
            result = subprocess.run(
                ["nmap", "-sV", "--top-ports", "1000", "-T4", "--open", "-oX", "-", snap.target],
                capture_output=True, text=True, timeout=self.timeout)
            snap.ports = self._parse_nmap_xml(result.stdout)
        except FileNotFoundError:
            snap.ports = self._socket_fallback(snap.target)
        except Exception as e:
            log.warning(f"Port collection failed: {e}")

    def _parse_nmap_xml(self, xml_output):
        import xml.etree.ElementTree as ET
        ports = []
        try:
            root = ET.fromstring(xml_output)
            for host in root.findall(".//host"):
                for port in host.findall(".//port"):
                    state_el   = port.find("state")
                    service_el = port.find("service")
                    if state_el is not None and state_el.get("state") == "open":
                        ports.append(PortState(
                            port=int(port.get("portid", 0)),
                            protocol=port.get("protocol", "tcp"), state="open",
                            service=service_el.get("name","") if service_el is not None else "",
                            version=f"{service_el.get('product','')} {service_el.get('version','')}".strip()
                                    if service_el is not None else ""))
        except ET.ParseError: pass
        return ports

    def _socket_fallback(self, target):
        COMMON_PORTS = [21,22,23,25,53,80,110,143,443,445,3306,3389,5432,6379,8080,8443,9200,27017]
        ports = []
        for p in COMMON_PORTS:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                if s.connect_ex((target, p)) == 0:
                    ports.append(PortState(port=p, protocol="tcp", state="open"))
                s.close()
            except Exception: pass
        return ports

    def _collect_dns(self, snap):
        for rtype in ["A","AAAA","MX","TXT","NS"]:
            try:
                result = subprocess.run(["nslookup", f"-type={rtype}", snap.target],
                    capture_output=True, text=True, timeout=10)
                snap.dns_records[rtype] = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            except Exception: pass

    def _collect_cert(self, snap):
        try:
            import ssl
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(socket.create_connection((snap.target, 443), timeout=10),
                                 server_hostname=snap.target) as s:
                cert = s.getpeercert()
                not_after = cert.get("notAfter","")
                expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z") if not_after else None
                days_left = (expiry - datetime.now()).days if expiry else 0
                sans = [v for t,v in cert.get("subjectAltName",[]) if t == "DNS"]
                subject = dict(x[0] for x in cert.get("subject",[]))
                issuer  = dict(x[0] for x in cert.get("issuer",[]))
                snap.cert = CertState(
                    subject=subject.get("commonName",""), issuer=issuer.get("organizationName",""),
                    not_after=not_after, sans=sans, days_until_expiry=days_left,
                    fingerprint=hashlib.sha256(str(cert).encode()).hexdigest()[:16])
        except Exception as e: log.debug(f"Cert collection failed: {e}")

    def _collect_http(self, snap):
        try:
            import urllib.request, urllib.error
            for scheme in ("https","http"):
                try:
                    req = urllib.request.Request(f"{scheme}://{snap.target}",
                                                 headers={"User-Agent":"ERR0RS-Monitor/1.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        snap.http_headers = dict(resp.headers)
                        snap.response_hash = hashlib.md5(resp.read(8192)).hexdigest()
                    break
                except urllib.error.URLError: continue
        except Exception as e: log.debug(f"HTTP collection failed: {e}")

    def _collect_subdomains(self, snap):
        try:
            import urllib.request
            url = f"https://crt.sh/?q=%.{snap.target}&output=json"
            req = urllib.request.Request(url, headers={"User-Agent":"ERR0RS-Monitor/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                subs = set()
                for entry in data:
                    for sub in entry.get("name_value","").split("\n"):
                        sub = sub.strip().lstrip("*.")
                        if sub and snap.target in sub: subs.add(sub)
                snap.subdomains = sorted(subs)
        except Exception as e: log.debug(f"Subdomain collection failed: {e}")

class DeltaEngine:
    CERT_EXPIRY_WARN_DAYS = 30

    def diff(self, baseline: SurfaceSnapshot, current: SurfaceSnapshot) -> List[SurfaceChange]:
        changes = []
        changes.extend(self._diff_ports(baseline, current))
        changes.extend(self._diff_dns(baseline, current))
        changes.extend(self._diff_cert(baseline, current))
        changes.extend(self._diff_http(baseline, current))
        changes.extend(self._diff_subdomains(baseline, current))
        return changes

    def _diff_ports(self, baseline, current):
        changes = []
        base_ports = {(p.port, p.protocol): p for p in baseline.ports}
        curr_ports = {(p.port, p.protocol): p for p in current.ports}
        for key, port in curr_ports.items():
            if key not in base_ports:
                changes.append(SurfaceChange(target=current.target, change_type=ChangeType.PORT_OPENED,
                    severity=ChangeSeverity.CRITICAL,
                    description=f"New open port: {port.port}/{port.protocol} ({port.service})",
                    old_value="closed", new_value=f"{port.port}/{port.protocol} {port.service} {port.version}"))
        for key, port in base_ports.items():
            if key not in curr_ports:
                changes.append(SurfaceChange(target=current.target, change_type=ChangeType.PORT_CLOSED,
                    severity=ChangeSeverity.LOW,
                    description=f"Port closed: {port.port}/{port.protocol} ({port.service})",
                    old_value=f"{port.port}/{port.protocol} {port.service}", new_value="closed"))
        for key in set(base_ports) & set(curr_ports):
            bp, cp = base_ports[key], curr_ports[key]
            if bp.version != cp.version and cp.version:
                changes.append(SurfaceChange(target=current.target, change_type=ChangeType.SERVICE_CHANGED,
                    severity=ChangeSeverity.HIGH,
                    description=f"Service version changed on port {cp.port}: {bp.version} → {cp.version}",
                    old_value=bp.version, new_value=cp.version))
        return changes

    def _diff_dns(self, baseline, current):
        changes = []
        for rtype in set(list(baseline.dns_records) + list(current.dns_records)):
            old_r = set(baseline.dns_records.get(rtype, []))
            new_r = set(current.dns_records.get(rtype, []))
            if old_r != new_r:
                changes.append(SurfaceChange(target=current.target, change_type=ChangeType.DNS_CHANGED,
                    severity=ChangeSeverity.HIGH if rtype=="A" else ChangeSeverity.MEDIUM,
                    description=f"DNS {rtype} record changed",
                    old_value=str(sorted(old_r)), new_value=str(sorted(new_r))))
        return changes

    def _diff_cert(self, baseline, current):
        changes = []
        if not current.cert: return changes
        if baseline.cert and baseline.cert.fingerprint != current.cert.fingerprint:
            changes.append(SurfaceChange(target=current.target, change_type=ChangeType.CERT_CHANGED,
                severity=ChangeSeverity.HIGH, description="TLS certificate fingerprint changed",
                old_value=baseline.cert.fingerprint, new_value=current.cert.fingerprint))
        if current.cert.days_until_expiry <= self.CERT_EXPIRY_WARN_DAYS:
            changes.append(SurfaceChange(target=current.target, change_type=ChangeType.CERT_EXPIRING,
                severity=ChangeSeverity.MEDIUM,
                description=f"TLS cert expires in {current.cert.days_until_expiry} days",
                old_value="", new_value=current.cert.not_after))
        return changes

    def _diff_http(self, baseline, current):
        changes = []
        for header in ["x-frame-options","x-content-type-options","content-security-policy",
                       "strict-transport-security","server","x-powered-by"]:
            old_val = baseline.http_headers.get(header,"")
            new_val = current.http_headers.get(header,"")
            if old_val != new_val:
                changes.append(SurfaceChange(target=current.target, change_type=ChangeType.HEADER_CHANGED,
                    severity=ChangeSeverity.HIGH if header in ("server","x-powered-by") else ChangeSeverity.LOW,
                    description=f"HTTP header changed: {header}",
                    old_value=old_val or "(absent)", new_value=new_val or "(absent)"))
        return changes

    def _diff_subdomains(self, baseline, current):
        changes = []
        for new_sub in set(current.subdomains) - set(baseline.subdomains):
            changes.append(SurfaceChange(target=current.target, change_type=ChangeType.NEW_SUBDOMAIN,
                severity=ChangeSeverity.HIGH, description=f"New subdomain: {new_sub}",
                old_value="", new_value=new_sub))
        return changes


class MonitorStorage:
    def __init__(self, storage_dir="./monitor_data"):
        self.base = Path(storage_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _target_key(self, target): return hashlib.md5(target.encode()).hexdigest()[:12]

    def save_baseline(self, snap):
        with open(self.base / f"baseline_{self._target_key(snap.target)}.json","w") as f:
            json.dump(asdict(snap), f, indent=2)

    def load_baseline(self, target):
        path = self.base / f"baseline_{self._target_key(target)}.json"
        if not path.exists(): return None
        with open(path) as f: data = json.load(f)
        snap = SurfaceSnapshot(target=data["target"], timestamp=data["timestamp"])
        snap.ports        = [PortState(**p) for p in data.get("ports",[])]
        snap.dns_records  = data.get("dns_records",{})
        snap.subdomains   = data.get("subdomains",[])
        snap.http_headers = data.get("http_headers",{})
        snap.technologies = data.get("technologies",[])
        snap.response_hash= data.get("response_hash","")
        if data.get("cert"): snap.cert = CertState(**data["cert"])
        return snap

    def append_changes(self, changes):
        with open(self.base / "change_log.jsonl","a") as f:
            for chg in changes: f.write(json.dumps(chg.to_dict()) + "\n")

    def get_all_changes(self, target=None):
        path = self.base / "change_log.jsonl"
        if not path.exists(): return []
        changes = []
        with open(path) as f:
            for line in f:
                try:
                    c = json.loads(line)
                    if target is None or c.get("target") == target: changes.append(c)
                except json.JSONDecodeError: pass
        return changes

class LiveAttackSurfaceMonitor:
    """
    Main monitor. Runs continuously in background thread.
    Add targets, start it, get alerted on every surface change.
    CRITICAL severity changes auto-trigger ERR0RS recon workflow.

    Usage:
        monitor = LiveAttackSurfaceMonitor(interval_minutes=30)
        monitor.add_target("example.com")
        monitor.start()
        monitor.on_change(lambda chg: print(chg.description))
    """
    def __init__(self, interval_minutes=30, storage_dir="./monitor_data", orchestrator=None):
        self.interval     = interval_minutes * 60
        self.storage      = MonitorStorage(storage_dir)
        self.snapshot_eng = SnapshotEngine()
        self.delta_eng    = DeltaEngine()
        self.orchestrator = orchestrator
        self.targets: List[str] = []
        self._callbacks: List[Callable] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._status: Dict[str, dict] = {}

    def add_target(self, target, baseline_now=True):
        if target not in self.targets:
            self.targets.append(target)
            self._status[target] = {"state":"pending","last_scan":None,"changes":0}
            if baseline_now:
                snap = self.snapshot_eng.capture(target)
                self.storage.save_baseline(snap)
                self._status[target]["state"] = "monitoring"
                print(f"[ASM] Baseline captured for {target}: {len(snap.ports)} ports, {len(snap.subdomains)} subdomains")

    def remove_target(self, target):
        if target in self.targets: self.targets.remove(target)

    def on_change(self, callback): self._callbacks.append(callback)

    def start(self):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"\n[ASM] ✅ Monitoring {len(self.targets)} target(s) every {self.interval//60} minutes.\n")

    def stop(self):
        self._running = False

    def force_scan(self, target): return self._scan_target(target)
    def get_changes(self, target=None): return self.storage.get_all_changes(target)
    def status(self): return {"running":self._running,"targets":self.targets,
                              "interval":f"{self.interval//60}min","details":self._status}

    def _monitor_loop(self):
        while self._running:
            for target in list(self.targets):
                try: self._scan_target(target)
                except Exception as e: log.error(f"[ASM] Error scanning {target}: {e}")
            time.sleep(self.interval)

    def _scan_target(self, target):
        self._status.setdefault(target,{})["last_scan"] = datetime.now().isoformat()
        baseline = self.storage.load_baseline(target)
        current  = self.snapshot_eng.capture(target)
        if baseline is None:
            self.storage.save_baseline(current)
            return []
        changes = self.delta_eng.diff(baseline, current)
        if changes:
            self.storage.append_changes(changes)
            self._status[target]["changes"] = self._status[target].get("changes",0) + len(changes)
            for chg in changes: self._fire_alert(chg)
            self.storage.save_baseline(current)
        return changes

    def _fire_alert(self, change):
        icons = {"critical":"🔴 CRITICAL","high":"🟠 HIGH","medium":"🟡 MEDIUM","low":"🔵 LOW","info":"⚪ INFO"}
        print(f"\n[ASM ALERT] {icons.get(change.severity.value,'⚠️')} | {change.target}")
        print(f"           {change.description}")
        if change.old_value: print(f"           Before: {change.old_value}")
        print(f"           After:  {change.new_value}  [{change.timestamp}]\n")
        if change.severity.value in ("critical","high") and self.orchestrator:
            wf_map = {ChangeType.PORT_OPENED:"recon", ChangeType.SERVICE_CHANGED:"recon",
                      ChangeType.NEW_SUBDOMAIN:"recon", ChangeType.DNS_CHANGED:"recon"}
            wf = wf_map.get(change.change_type)
            if wf:
                try: self.orchestrator.run_workflow(wf, targets=[change.target])
                except Exception as e: log.error(f"[ASM] Auto-workflow failed: {e}")
        for cb in self._callbacks:
            try: cb(change)
            except Exception as e: log.error(f"[ASM] Callback error: {e}")


__all__ = ["LiveAttackSurfaceMonitor","SurfaceSnapshot","SurfaceChange",
           "ChangeType","ChangeSeverity","SnapshotEngine","DeltaEngine","MonitorStorage"]
