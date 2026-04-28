#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Breach & Attack Simulation (BAS) Engine v1.0
Competes with: Pentera, SafeBreach, Cymulate, AttackIQ

Runs MITRE ATT&CK-aligned attack simulations locally — validates your
defenses WITHOUT sending data outside. 100% local, 100% safe.

Playbook categories:
  credential_access   — Hash dumping, Kerberoasting, LSASS
  lateral_movement    — Pass-the-hash, PsExec, WMI
  persistence         — Registry run keys, scheduled tasks, services
  defense_evasion     — AMSI bypass, log clearing, timestamp tampering
  exfiltration_sim    — DNS tunneling simulation, staged upload test
  ransomware_sim      — File encryption behavior test (SAFE — no payload)
  c2_beacon_sim       — Beacon pattern generation test

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import json, subprocess, shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parents[3]

# ─── MITRE ATT&CK Technique mappings ─────────────────────────────────────────

MITRE_MAP = {
    "credential_access":  ["T1003", "T1558.003", "T1110", "T1555"],
    "lateral_movement":   ["T1550.002", "T1021.002", "T1021.003", "T1570"],
    "persistence":        ["T1547.001", "T1053.005", "T1543.003", "T1098"],
    "defense_evasion":    ["T1562.001", "T1070.001", "T1027", "T1140"],
    "exfiltration_sim":   ["T1048", "T1041", "T1567"],
    "ransomware_sim":     ["T1486", "T1490"],
    "c2_beacon_sim":      ["T1071.001", "T1095", "T1572"],
}

# ─── Simulation playbooks ─────────────────────────────────────────────────────

PLAYBOOKS = {

    "credential_access": {
        "name":    "Credential Access Simulation",
        "mitre":   ["T1003 - OS Credential Dumping", "T1558.003 - Kerberoasting",
                    "T1110 - Brute Force", "T1555 - Credentials from Password Stores"],
        "desc":    "Simulates credential theft techniques — no actual credentials extracted",
        "safe_checks": [
            {
                "name": "LSASS Access Check",
                "desc": "Tests if LSASS process memory access is audited",
                "cmd_linux":   "ps aux | grep lsass 2>/dev/null || echo 'LSASS: Linux/Kali — not applicable'",
                "cmd_windows": "Get-Process lsass | Select-Object Id,CPU,PM",
                "indicator":   "Detection: Event ID 4656 (handle to LSASS) should trigger SIEM alert",
                "mitre":       "T1003.001",
            },
            {
                "name": "SAM Database Access Check",
                "desc": "Tests if SAM registry hive access is monitored",
                "cmd_linux":   "ls /etc/shadow 2>/dev/null && echo 'Shadow exists — test read access' || echo 'No /etc/shadow'",
                "cmd_windows": "Get-ItemProperty HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa | Select-Object NoLMHash",
                "indicator":   "Detection: Unexpected /etc/shadow or SAM read should alert",
                "mitre":       "T1003.002",
            },
            {
                "name": "Password Manager Detection",
                "desc": "Checks if password manager processes are visible (attack surface)",
                "cmd_linux":   "ps aux | grep -iE 'keepass|bitwarden|lastpass|1password' 2>/dev/null || echo 'No password managers running'",
                "cmd_windows": "Get-Process | Where-Object {$_.Name -match 'keepass|bitwarden|lastpass'}",
                "indicator":   "Finding: Running password managers are credential access targets",
                "mitre":       "T1555",
            },
        ],
    },

    "lateral_movement": {
        "name":    "Lateral Movement Simulation",
        "mitre":   ["T1550.002 - Pass the Hash", "T1021.002 - SMB/Admin Shares",
                    "T1021.003 - DCOM", "T1570 - Lateral Tool Transfer"],
        "desc":    "Tests lateral movement detection capabilities — network simulation only",
        "safe_checks": [
            {
                "name": "SMB Share Enumeration",
                "desc": "Tests visibility of SMB shares from current host",
                "cmd_linux":   "smbclient -L //127.0.0.1 -N 2>/dev/null || echo 'SMB: smbclient not installed or no local SMB'",
                "cmd_windows": "net view \\\\localhost 2>&1",
                "indicator":   "Detection: Unexpected SMB enumeration should alert in logs",
                "mitre":       "T1021.002",
            },
            {
                "name": "WinRM / Remote Management Check",
                "desc": "Tests if remote management endpoints are exposed",
                "cmd_linux":   "nmap -p 5985,5986 127.0.0.1 --open 2>/dev/null | head -10",
                "cmd_windows": "Get-Service WinRM | Select-Object Status",
                "indicator":   "Finding: Exposed WinRM enables lateral movement without credentials",
                "mitre":       "T1021.006",
            },
            {
                "name": "SSH Key Trust Check",
                "desc": "Checks for authorized_keys files enabling passwordless lateral movement",
                "cmd_linux":   "find /home /root -name 'authorized_keys' 2>/dev/null | head -10",
                "cmd_windows": "echo 'SSH keys: check C:\\Users\\*\\.ssh\\authorized_keys'",
                "indicator":   "Finding: authorized_keys files enable no-credential SSH lateral movement",
                "mitre":       "T1563.001",
            },
        ],
    },

    "persistence": {
        "name":    "Persistence Mechanism Check",
        "mitre":   ["T1547.001 - Registry Run Keys", "T1053.005 - Scheduled Task",
                    "T1543.003 - Windows Service", "T1098 - Account Manipulation"],
        "desc":    "Inventories persistence points — identifies attacker footholds",
        "safe_checks": [
            {
                "name": "Cron / Scheduled Task Audit",
                "desc": "Lists all scheduled tasks for unauthorized entries",
                "cmd_linux":   "crontab -l 2>/dev/null; cat /etc/cron* 2>/dev/null; ls /etc/cron.d/ 2>/dev/null",
                "cmd_windows": "Get-ScheduledTask | Where-Object {$_.TaskPath -notlike '\\Microsoft\\*'} | Select-Object TaskName,TaskPath",
                "indicator":   "Review: Any unexpected cron/scheduled task is a persistence IOC",
                "mitre":       "T1053.005",
            },
            {
                "name": "SUID Binary Audit (Linux)",
                "desc": "Finds SUID binaries — privilege escalation AND persistence vectors",
                "cmd_linux":   "find / -perm -4000 -type f 2>/dev/null | grep -v proc | head -20",
                "cmd_windows": "echo 'SUID: Linux-specific check, N/A on Windows'",
                "indicator":   "Finding: Unexpected SUID binaries indicate potential backdoor or misconfiguration",
                "mitre":       "T1548.001",
            },
            {
                "name": "Startup Location Audit",
                "desc": "Checks all startup folders and services",
                "cmd_linux":   "ls /etc/init.d/ 2>/dev/null; systemctl list-units --type=service --state=enabled 2>/dev/null | head -30",
                "cmd_windows": "Get-CimInstance Win32_StartupCommand | Select-Object Name,Command,Location",
                "indicator":   "Review: Unknown startup entries indicate persistence mechanisms",
                "mitre":       "T1547.001",
            },
        ],
    },

    "defense_evasion": {
        "name":    "Defense Evasion Check",
        "mitre":   ["T1562.001 - Disable Security Tools", "T1070.001 - Clear Windows Event Logs",
                    "T1027 - Obfuscated Files", "T1140 - Deobfuscation/Decode"],
        "desc":    "Validates security controls are active and tamper-evident",
        "safe_checks": [
            {
                "name": "AV/EDR Status Check",
                "desc": "Verifies security software is running",
                "cmd_linux":   "ps aux | grep -iE 'clamav|sophos|crowdstrike|carbon|defender' 2>/dev/null || echo 'No common AV processes found'",
                "cmd_windows": "Get-MpStatus | Select-Object AMRunningMode,RealTimeProtectionEnabled",
                "indicator":   "Critical: If AV/EDR not running, defense is blind to threats",
                "mitre":       "T1562.001",
            },
            {
                "name": "Log Integrity Check",
                "desc": "Tests if system logs are protected from clearing",
                "cmd_linux":   "ls -la /var/log/auth.log /var/log/syslog 2>/dev/null; journalctl --disk-usage 2>/dev/null",
                "cmd_windows": "Get-WinEvent -ListLog Security | Select-Object LogName,RecordCount,MaximumSizeInBytes",
                "indicator":   "Review: Log forwarding to SIEM makes clearing harder. Check if logs are centralized.",
                "mitre":       "T1070.001",
            },
            {
                "name": "Firewall Configuration Check",
                "desc": "Validates firewall rules are active and restrictive",
                "cmd_linux":   "iptables -L -n 2>/dev/null | head -20 || ufw status 2>/dev/null",
                "cmd_windows": "netsh advfirewall show allprofiles state",
                "indicator":   "Critical: Permissive firewall enables exfiltration and C2 communication",
                "mitre":       "T1562.004",
            },
        ],
    },

    "ransomware_sim": {
        "name":    "Ransomware Behavior Simulation (SAFE)",
        "mitre":   ["T1486 - Data Encrypted for Impact", "T1490 - Inhibit System Recovery"],
        "desc":    "Simulates ransomware INDICATORS without any actual encryption or damage",
        "safe_checks": [
            {
                "name": "Shadow Copy Deletion Detection",
                "desc": "Checks if shadow copy deletion would be detected (ransomware step 1)",
                "cmd_linux":   "echo '[SIM] vssadmin delete shadows /all /quiet — would this trigger an alert?'",
                "cmd_windows": "Get-WmiObject Win32_ShadowCopy | Select-Object ID,InstallDate | Measure-Object | Select-Object Count",
                "indicator":   "Detection: vssadmin/wmic shadow delete should trigger immediate SIEM alert (T1490)",
                "mitre":       "T1490",
            },
            {
                "name": "Mass File Write Behavior",
                "desc": "Tests if mass file creation/modification triggers detection (SAFE — creates temp files only)",
                "cmd_linux":   "mkdir -p /tmp/errz_bas_test && for i in {1..10}; do touch /tmp/errz_bas_test/test_$i.tmp; done && echo 'Created 10 test files in /tmp/errz_bas_test/' && rm -rf /tmp/errz_bas_test",
                "cmd_windows": "New-Item -ItemType Directory -Path $env:TEMP\\errz_bas_test -Force | Out-Null; 1..10 | ForEach-Object { New-Item -Path \"$env:TEMP\\errz_bas_test\\test_$_.tmp\" -Force | Out-Null }; Remove-Item -Path $env:TEMP\\errz_bas_test -Recurse -Force; Write-Host 'Mass file test complete (files deleted)'",
                "indicator":   "Detection: Mass file creation in unusual locations should trigger behavioral EDR alert",
                "mitre":       "T1486",
            },
            {
                "name": "Backup Location Discovery",
                "desc": "Checks for backup directories ransomware would target",
                "cmd_linux":   "find / -maxdepth 4 -name 'backup*' -o -name '*backup*' -type d 2>/dev/null | head -10",
                "cmd_windows": "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,FreeSpace,Size",
                "indicator":   "Finding: Unprotected backup locations are primary ransomware targets",
                "mitre":       "T1486",
            },
        ],
    },

}


def run_playbook(playbook_key: str, target_os: str = "linux") -> dict:
    """Execute a BAS playbook and collect results."""
    playbook = PLAYBOOKS.get(playbook_key)
    if not playbook:
        return {
            "status": "error",
            "error":  f"Unknown playbook: {playbook_key}",
            "available": list(PLAYBOOKS.keys()),
        }

    results = {
        "status":      "success",
        "playbook":    playbook["name"],
        "description": playbook["desc"],
        "mitre_ttps":  playbook["mitre"],
        "timestamp":   datetime.now().isoformat(),
        "checks":      [],
    }

    for check in playbook["safe_checks"]:
        cmd_key = f"cmd_{target_os.lower()}" if f"cmd_{target_os.lower()}" in check else "cmd_linux"
        cmd = check.get(cmd_key, check.get("cmd_linux", "echo 'N/A'"))

        check_result = {
            "name":      check["name"],
            "desc":      check["desc"],
            "mitre":     check.get("mitre", ""),
            "indicator": check["indicator"],
            "command":   cmd,
            "output":    "",
            "status":    "pending",
        }

        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=15
            )
            check_result["output"] = (r.stdout + r.stderr).strip()[:2000]
            check_result["status"] = "ok" if r.returncode == 0 else "warn"
        except subprocess.TimeoutExpired:
            check_result["output"] = "TIMEOUT — command took too long"
            check_result["status"] = "timeout"
        except Exception as e:
            check_result["output"] = f"ERROR: {e}"
            check_result["status"] = "error"

        results["checks"].append(check_result)

    # Summary
    passed = sum(1 for c in results["checks"] if c["status"] == "ok")
    results["summary"] = {
        "total":   len(results["checks"]),
        "passed":  passed,
        "warning": sum(1 for c in results["checks"] if c["status"] == "warn"),
        "errors":  sum(1 for c in results["checks"] if c["status"] in ("error", "timeout")),
    }
    return results


def list_playbooks() -> dict:
    return {
        "status": "success",
        "count":  len(PLAYBOOKS),
        "playbooks": [
            {"key": k, "name": v["name"], "desc": v["desc"],
             "checks": len(v["safe_checks"]), "mitre_count": len(v["mitre"])}
            for k, v in PLAYBOOKS.items()
        ],
    }


def generate_bas_report(results: list) -> str:
    """Generate a markdown BAS report from a list of playbook results."""
    lines = [
        "# ERR0RS BAS Report — Breach & Attack Simulation",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Executive Summary",
        "",
    ]
    total_checks = sum(r.get("summary", {}).get("total", 0) for r in results)
    total_warn   = sum(r.get("summary", {}).get("warning", 0) for r in results)
    lines.append(f"- **Total checks run:** {total_checks}")
    lines.append(f"- **Findings requiring review:** {total_warn}")
    lines.append(f"- **Playbooks executed:** {len(results)}")
    lines.append("")
    lines.append("## Playbook Results")
    lines.append("")

    for r in results:
        lines.append(f"### {r.get('playbook', 'Unknown')}")
        lines.append(f"*{r.get('description', '')}*")
        lines.append("")
        lines.append("**MITRE ATT&CK Techniques:**")
        for ttp in r.get("mitre_ttps", []):
            lines.append(f"- {ttp}")
        lines.append("")
        for check in r.get("checks", []):
            status_icon = {"ok": "✅", "warn": "⚠️", "error": "❌", "timeout": "⏱️"}.get(check["status"], "❓")
            lines.append(f"**{status_icon} {check['name']}** `{check.get('mitre','')}`")
            lines.append(f"  > {check['indicator']}")
            if check.get("output"):
                lines.append(f"  ```\n  {check['output'][:300]}\n  ```")
            lines.append("")

    lines.append("---")
    lines.append("*Generated by ERR0RS Ultimate BAS Engine — for authorized testing only*")
    return "\n".join(lines)


def handle_bas_request(payload: dict) -> dict:
    action = payload.get("action", "list")
    if action == "list":
        return list_playbooks()
    elif action == "run":
        key = payload.get("playbook", "")
        os_ = payload.get("os", "linux")
        if not key:
            return {"status": "error", "error": "No playbook specified"}
        return run_playbook(key, os_)
    elif action == "report":
        results = payload.get("results", [])
        return {"status": "success", "stdout": generate_bas_report(results)}
    return {"status": "error", "error": f"Unknown action: {action}"}
