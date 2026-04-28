#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — APT Emulation Engine v1.0
Simulates real-world threat actor TTPs for purple team exercises.

Competes with: SCYTHE (Enterprise $$$), Vectr, MITRE Caldera,
               and underground custom implant frameworks

Philosophy: Understanding how real APTs operate is ESSENTIAL
for defenders. This engine teaches both sides simultaneously.
Every simulation shows the attacker perspective AND the
detection opportunities defenders should build for.

100% safe — no actual malware, no real C2, no weaponized payloads.
Simulations use documented techniques in safe, controlled ways
exactly like MITRE's Atomic Red Team and Caldera do.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
LEGAL: Authorized testing environments only.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
import json, subprocess, shutil


# ══════════════════════════════════════════════════════════════════
# APT GROUP PROFILES
# Based entirely on publicly documented MITRE ATT&CK group data
# Sources: attack.mitre.org (all public, all declassified)
# ══════════════════════════════════════════════════════════════════

APT_GROUPS = {

    "apt29": {
        "name":         "APT29 (Cozy Bear)",
        "aka":          ["The Dukes", "Cozy Bear", "NOBELIUM"],
        "origin":       "Russia (SVR)",
        "motivation":   "Espionage, intelligence collection",
        "targets":      ["Government", "Defense", "Think tanks", "Healthcare", "Energy"],
        "known_for":    "SolarWinds supply chain attack (2020), DNC breach (2016)",
        "mitre_id":     "G0016",
        "source":       "https://attack.mitre.org/groups/G0016/",
        "primary_ttps": [
            "T1566.001 — Spearphishing with malicious attachment",
            "T1059.001 — PowerShell execution",
            "T1055     — Process injection (DLL side-loading)",
            "T1071.001 — C2 over HTTP/HTTPS (domain fronting)",
            "T1027     — Obfuscated files (multi-layer encoding)",
            "T1562.001 — Disable Windows Defender",
            "T1003.001 — LSASS credential dumping",
            "T1078     — Valid accounts (supply chain compromise)",
        ],
        "key_techniques": {
            "Initial Access":      "Spearphishing emails with malicious documents (T1566.001)",
            "Execution":           "PowerShell + WMI for fileless execution (T1059.001, T1047)",
            "Persistence":         "Registry run keys + scheduled tasks (T1547.001, T1053.005)",
            "Defense Evasion":     "Domain fronting C2, multi-stage loaders, timestomping",
            "Credential Access":   "Mimikatz variant for LSASS dump (T1003.001)",
            "Lateral Movement":    "Pass-the-Hash, RDP with stolen credentials (T1550.002)",
            "Exfiltration":        "HTTPS to actor-controlled infrastructure (T1041)",
        },
        "detection_opportunities": [
            "PowerShell Script Block Logging (Event 4104) catches obfuscated PS",
            "AMSI telemetry on encoded commands",
            "Network: domain fronting creates unusual CDN → internal traffic patterns",
            "LSASS access: Sysmon Event 10 on lsass.exe",
            "Scheduled tasks created by non-standard parent processes",
            "Registry modification at HKCU/HKLM Run keys",
        ],
        "sigma_rules": [
            "proc_creation_win_powershell_encode.yml",
            "proc_creation_win_lsass_dump.yml",
            "proc_creation_win_scheduled_task.yml",
        ],
    },

    "fin7": {
        "name":         "FIN7",
        "aka":          ["Carbanak", "Navigator Group"],
        "origin":       "Eastern Europe (criminal)",
        "motivation":   "Financial — payment card theft, wire fraud, ransomware",
        "targets":      ["Hospitality", "Restaurant", "Retail", "Financial"],
        "known_for":    "$1B+ stolen from banks and retailers, Carbanak malware",
        "mitre_id":     "G0046",
        "source":       "https://attack.mitre.org/groups/G0046/",
        "primary_ttps": [
            "T1566.001 — Spearphishing with booby-trapped Word docs (macros)",
            "T1059.005 — VBA macro execution",
            "T1055.012 — Process Hollowing",
            "T1056.001 — Keylogging (targeting POS systems)",
            "T1071.001 — C2 over HTTP",
            "T1486     — Data encrypted for impact (ransomware pivot)",
        ],
        "key_techniques": {
            "Initial Access":    "Malicious Word docs sent to restaurant/hotel staff email",
            "Execution":         "VBA macros → PowerShell → Carbanak backdoor (T1059.005)",
            "Credential Access": "Keyloggers targeting POS login screens (T1056.001)",
            "Collection":        "Screenshot capture + keylogging (T1113, T1056)",
            "Exfiltration":      "Slow exfil over HTTPS, low and slow to avoid detection",
        },
        "detection_opportunities": [
            "Office macro execution: Event 4688 with Word/Excel spawning PowerShell",
            "Email: Word attachments with macros from external senders",
            "Network: HTTP POST to unusual domains from POS or front-desk machines",
            "Endpoint: Screenshot APIs called by non-standard processes",
            "SIEM: Login to financial systems from unusual source IPs/times",
        ],
    },

    "lazarus": {
        "name":         "Lazarus Group",
        "aka":          ["Hidden Cobra", "Guardians of Peace", "WhoisTeam"],
        "origin":       "North Korea (RGB Bureau 121)",
        "motivation":   "Financial (crypto theft, bank heists), espionage, sabotage",
        "targets":      ["Cryptocurrency", "Banking", "Defense", "Media"],
        "known_for":    "Sony Pictures hack, WannaCry, $1.7B in crypto theft",
        "mitre_id":     "G0032",
        "source":       "https://attack.mitre.org/groups/G0032/",
        "primary_ttps": [
            "T1566.002 — Spearphishing with malicious links",
            "T1059.001 — PowerShell + Python loaders",
            "T1486     — WannaCry ransomware (EternalBlue propagation)",
            "T1190     — Exploit public-facing apps (cryptocurrency exchanges)",
            "T1534     — Internal spearphishing after compromise",
            "T1564.001 — Hidden files in temp directories",
        ],
        "key_techniques": {
            "Initial Access":    "LinkedIn job offer spearphishing → malicious PDF",
            "Execution":         "Custom loaders with multi-stage decryption",
            "Impact":            "WannaCry: EternalBlue (MS17-010) worm propagation",
            "Financial Theft":   "Compromise SWIFT terminals, forge transactions",
        },
        "detection_opportunities": [
            "LinkedIn-delivered malware: PDF opened from browser, spawns process",
            "EternalBlue: Sysmon Event 3 on unusual SMB lateral connections",
            "Crypto draining: unusual outbound to crypto wallet addresses",
            "Custom loaders: high entropy PE files in %TEMP%",
        ],
    },

    "apt41": {
        "name":         "APT41 (Double Dragon)",
        "aka":          ["Winnti", "Barium", "Wicked Panda"],
        "origin":       "China (state-sponsored + criminal)",
        "motivation":   "Dual-use: espionage AND financial crime simultaneously",
        "targets":      ["Healthcare", "Telecom", "Tech", "Video games", "Finance"],
        "known_for":    "Supply chain attacks on video game companies, COVID-19 research theft",
        "mitre_id":     "G0096",
        "source":       "https://attack.mitre.org/groups/G0096/",
        "primary_ttps": [
            "T1195.002 — Supply chain compromise (software build systems)",
            "T1133     — External Remote Services (VPN exploitation)",
            "T1505.003 — Web shells on public servers",
            "T1027.002 — Software packing (custom packers)",
            "T1090     — Proxy C2 using compromised infrastructure",
        ],
        "key_techniques": {
            "Initial Access":    "VPN 0-days, web shells on public-facing servers",
            "Supply Chain":      "Compromise software update mechanisms",
            "Persistence":       "WMI subscriptions for persistent execution (T1546.003)",
            "Evasion":           "Rootkits signed with stolen code signing certificates",
        },
        "detection_opportunities": [
            "VPN exploitation: unusual authentication patterns from new IPs",
            "Web shells: web server process spawning cmd.exe or PowerShell",
            "WMI subscriptions: WMI-activity Event 5861",
            "Signed malware: certificate transparency logs, hash reputation",
        ],
    },

    "darkside": {
        "name":         "DarkSide / BlackMatter",
        "aka":          ["DarkSide", "BlackMatter", "ALPHV predecessor"],
        "origin":       "Eastern Europe (RaaS criminal)",
        "motivation":   "Ransomware-as-a-Service financial extortion",
        "targets":      ["Critical infrastructure", "Oil & gas", "Manufacturing"],
        "known_for":    "Colonial Pipeline attack (2021) — US fuel shortage",
        "mitre_id":     "G0135",
        "source":       "https://attack.mitre.org/groups/G0135/",
        "primary_ttps": [
            "T1486     — Data Encrypted for Impact (ransomware)",
            "T1490     — Inhibit System Recovery (shadow copy deletion)",
            "T1078     — Valid Accounts (stolen VPN credentials via dark web)",
            "T1003.001 — OS Credential Dumping (move through network)",
            "T1021.002 — SMB lateral movement",
            "T1567.002 — Exfiltration to cloud storage (double extortion)",
        ],
        "key_techniques": {
            "Initial Access":     "Purchased stolen VPN credentials on dark web markets",
            "Lateral Movement":   "CrackMapExec + Mimikatz credential spray across domain",
            "Pre-Ransomware":     "Weeks of data exfil before deploying encryption",
            "Ransomware Deploy":  "PowerShell deployment across domain via GPO or PsExec",
            "Double Extortion":   "Exfil data first, threaten to publish if ransom unpaid",
        },
        "detection_opportunities": [
            "VPN: credential stuffing attempts from unusual geolocations",
            "Shadow copy: vssadmin/wmic commands — should alert immediately",
            "Large exfil: sustained high-volume outbound 2-4 weeks before detonation",
            "Lateral movement: crackmapexec patterns in SMB logs",
            "GPO modification: unusual changes to Group Policy objects",
        ],
        "purple_team_lesson": (
            "DarkSide spent WEEKS in Colonial Pipeline's network before deploying ransomware. "
            "The detection window was wide open. Defenders who had: "
            "(1) VPN anomaly detection, (2) shadow copy monitoring, (3) lateral movement alerts "
            "would have caught this before any encryption. "
            "Ransomware is a DETECTION FAILURE, not an encryption problem."
        ),
    },
}


# ══════════════════════════════════════════════════════════════════
# SIMULATION PLAYBOOKS
# Safe, authorized exercises that demonstrate APT techniques.
# Based on MITRE ATT&CK Atomic Red Team test cases.
# ══════════════════════════════════════════════════════════════════

SIMULATION_PLAYBOOKS = {

    "initial_access_simulation": {
        "name":    "Initial Access Simulation",
        "mitre":   "TA0001",
        "desc":    "Simulates how APTs gain their first foothold",
        "teaches": "Phishing indicators, attachment analysis, macro behavior",
        "steps": [
            {
                "name":        "Phishing email indicator check",
                "technique":   "T1566.001",
                "safe_cmd_linux": "echo '[SIM] Checking email gateway logs for macro-enabled Office attachments...' && find /var/log -name 'mail*' 2>/dev/null | head -5",
                "safe_cmd_win":   "Get-EventLog -LogName Application -Source *Office* -Newest 20 2>$null | Select-Object Message",
                "teaches":     "APTs send Word/Excel with macros. Detection: filter .docm/.xlsm from external senders.",
                "mitre_id":    "T1566.001",
            },
            {
                "name":        "External remote service exposure check",
                "technique":   "T1133",
                "safe_cmd_linux": "ss -tulnp | grep -E '(:22|:3389|:5985|:5986|:8443)' 2>/dev/null",
                "safe_cmd_win":   "Get-NetTCPConnection -State Listen | Where-Object {$_.LocalPort -in @(22,3389,5985,5986)} | Select-Object LocalPort,OwningProcess",
                "teaches":     "APTs scan for and exploit exposed RDP/VPN/WinRM. Minimize your external attack surface.",
                "mitre_id":    "T1133",
            },
        ],
    },

    "credential_access_simulation": {
        "name":    "Credential Access Simulation",
        "mitre":   "TA0006",
        "desc":    "Simulates how APTs harvest credentials after foothold",
        "teaches": "Credential theft techniques, detection opportunities, Mimikatz indicators",
        "steps": [
            {
                "name":        "LSASS access monitoring check",
                "technique":   "T1003.001",
                "safe_cmd_linux": "ps aux | grep -i lsass 2>/dev/null || echo 'LSASS: not a Linux process — test Windows environment'",
                "safe_cmd_win":   "Get-WinEvent -FilterHashtable @{LogName='Security';Id=4656} -MaxEvents 10 2>$null | Where-Object {$_.Message -like '*lsass*'} | Select-Object TimeCreated,Message",
                "teaches":     "Mimikatz accesses lsass.exe to dump creds. Event 4656 (handle to process) should alert. Enable Credential Guard to block.",
                "mitre_id":    "T1003.001",
                "defense":     "Credential Guard, PPL on LSASS, Sysmon Rule for lsass access",
            },
            {
                "name":        "SAM registry hive access check",
                "technique":   "T1003.002",
                "safe_cmd_linux": "ls -la /etc/shadow 2>/dev/null && stat /etc/shadow 2>/dev/null | head -5",
                "safe_cmd_win":   "Get-Acl -Path 'HKLM:\\SAM\\SAM\\Domains\\Account\\Users' 2>$null | Select-Object Path,AccessToString",
                "teaches":     "SAM database stores local account NTLM hashes. Dumping requires SYSTEM. Monitor registry hive access.",
                "mitre_id":    "T1003.002",
            },
            {
                "name":        "Kerberoastable account discovery",
                "technique":   "T1558.003",
                "safe_cmd_linux": "which ldapsearch && ldapsearch -x -H ldap://127.0.0.1 -b 'DC=domain,DC=local' '(servicePrincipalName=*)' sAMAccountName 2>/dev/null | head -20 || echo 'ldapsearch not configured or no LDAP server'",
                "safe_cmd_win":   "Get-ADUser -Filter {ServicePrincipalName -ne '$null'} -Properties ServicePrincipalName 2>$null | Select-Object Name,ServicePrincipalName",
                "teaches":     "Accounts with SPNs can be Kerberoasted — get TGS ticket, crack offline. Use strong service account passwords + gMSA.",
                "mitre_id":    "T1558.003",
                "defense":     "gMSA for service accounts, monitor TGS requests for unusual accounts",
            },
        ],
    },

    "lateral_movement_simulation": {
        "name":    "Lateral Movement Simulation",
        "mitre":   "TA0008",
        "desc":    "Simulates how APTs move through networks after initial access",
        "teaches": "PTH, PsExec, WMI, detection patterns, network segmentation importance",
        "steps": [
            {
                "name":        "SMB share discovery",
                "technique":   "T1021.002",
                "safe_cmd_linux": "smbclient -L //127.0.0.1 -N 2>/dev/null | head -20 || echo 'No local SMB / smbclient not installed'",
                "safe_cmd_win":   "net view \\\\localhost 2>&1 | head -20",
                "teaches":     "APTs enumerate SMB shares after getting credentials. Admin$ and C$ access = lateral movement path.",
                "mitre_id":    "T1021.002",
                "defense":     "Disable Admin$ shares on workstations, network segmentation, monitor SMB from non-server sources",
            },
            {
                "name":        "WinRM / Remote Management availability",
                "technique":   "T1021.006",
                "safe_cmd_linux": "nmap -p 5985,5986 127.0.0.1 --open 2>/dev/null | grep -E 'open|filtered'",
                "safe_cmd_win":   "Test-WSMan localhost 2>$null | Select-Object ProductVendor,ProductVersion",
                "teaches":     "WinRM (port 5985/5986) enables remote PowerShell. APTs love it — it's a built-in tool (LOLBAS).",
                "mitre_id":    "T1021.006",
                "defense":     "Disable WinRM on workstations, restrict to jump servers only",
            },
        ],
    },

    "persistence_simulation": {
        "name":    "Persistence Mechanism Audit",
        "mitre":   "TA0003",
        "desc":    "Identifies and demonstrates persistence mechanisms APTs use",
        "teaches": "Registry run keys, scheduled tasks, services — the attacker toolkit for staying in",
        "steps": [
            {
                "name":        "Registry run key audit",
                "technique":   "T1547.001",
                "safe_cmd_linux": "cat /etc/rc.local 2>/dev/null; ls /etc/init.d/ 2>/dev/null | head -10",
                "safe_cmd_win":   "Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' 2>$null; Get-ItemProperty 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' 2>$null",
                "teaches":     "Run keys execute on every user login. APTs plant backdoors here. Audit regularly.",
                "mitre_id":    "T1547.001",
                "defense":     "Monitor registry run key changes (Sysmon Event 13), AppLocker/WDAC",
            },
            {
                "name":        "Scheduled task audit",
                "technique":   "T1053.005",
                "safe_cmd_linux": "crontab -l 2>/dev/null; cat /etc/cron* 2>/dev/null | head -30",
                "safe_cmd_win":   "Get-ScheduledTask | Where-Object {$_.TaskPath -notlike '\\Microsoft\\*'} | Select-Object TaskName,State,@{N='Action';E={$_.Actions.Execute}} | Format-Table -Auto",
                "teaches":     "Scheduled tasks survive reboots and run as SYSTEM. APTs create disguised tasks.",
                "mitre_id":    "T1053.005",
                "defense":     "Monitor new scheduled task creation (Event 4698), review non-Microsoft tasks regularly",
            },
        ],
    },

    "defense_evasion_simulation": {
        "name":    "Defense Evasion Audit",
        "mitre":   "TA0005",
        "desc":    "Tests if security controls would detect APT evasion techniques",
        "teaches": "How APTs hide from AV/EDR, what defenders need to catch them",
        "steps": [
            {
                "name":        "Security tool status check",
                "technique":   "T1562.001",
                "safe_cmd_linux": "systemctl status clamav-daemon 2>/dev/null || ps aux | grep -i 'falcon\\|crowdstrike\\|carbon\\|defender' 2>/dev/null | grep -v grep || echo 'No common AV detected'",
                "safe_cmd_win":   "Get-MpComputerStatus | Select-Object AMRunningMode,RealTimeProtectionEnabled,BehaviorMonitorEnabled,IoavProtectionEnabled",
                "teaches":     "APTs check for and disable AV before deploying tools. If your AV can be disabled by a local admin, it can be disabled by malware running as admin.",
                "mitre_id":    "T1562.001",
                "defense":     "Tamper protection enabled, EDR with kernel protection, separate admin accounts",
            },
            {
                "name":        "Log forwarding / SIEM check",
                "technique":   "T1070.001",
                "safe_cmd_linux": "journalctl --disk-usage 2>/dev/null; ls -la /var/log/*.log 2>/dev/null | tail -10",
                "safe_cmd_win":   "Get-WinEvent -ListLog Security | Select-Object LogName,RecordCount,IsEnabled; netstat -ano 2>$null | findstr ':514'",
                "teaches":     "APTs clear local logs after compromise. If logs aren't forwarded to a SIEM, clearing is undetectable.",
                "mitre_id":    "T1070.001",
                "defense":     "Forward logs to immutable SIEM in real time. Local log clearing should trigger alert.",
            },
        ],
    },

    "ransomware_precursor_simulation": {
        "name":    "Ransomware Precursor Detection",
        "mitre":   "TA0040",
        "desc":    "Tests if the environment would catch ransomware staging before encryption",
        "teaches": "Ransomware doesn't start with encryption — it starts with access, then moves, then exfils, then encrypts",
        "steps": [
            {
                "name":        "Shadow copy protection status",
                "technique":   "T1490",
                "safe_cmd_linux": "echo '[SIM] On Windows: vssadmin list shadows would show backup state'",
                "safe_cmd_win":   "Get-WmiObject Win32_ShadowCopy 2>$null | Select-Object ID,InstallDate,Count; (Get-WmiObject Win32_ShadowCopy).Count",
                "teaches":     "DarkSide, LockBit, REvil ALL delete shadow copies first. If shadow copy deletion alerts immediately — you catch them here.",
                "mitre_id":    "T1490",
                "defense":     "Alert on vssadmin/wmic shadow copy deletion commands IMMEDIATELY (highest priority alert)",
                "critical":    True,
            },
            {
                "name":        "Backup integrity check",
                "technique":   "T1486",
                "safe_cmd_linux": "df -h /backup 2>/dev/null || ls /backup 2>/dev/null || echo 'No /backup mount found'",
                "safe_cmd_win":   "Get-WmiObject Win32_LogicalDisk | Select-Object DeviceID,@{N='FreeGB';E={[math]::Round($_.FreeSpace/1GB,1)}},@{N='TotalGB';E={[math]::Round($_.Size/1GB,1)}}",
                "teaches":     "Ransomware targets backup locations specifically. Air-gapped backups that ransomware can't reach are the only real recovery option.",
                "mitre_id":    "T1486",
            },
        ],
    },
}


# ══════════════════════════════════════════════════════════════════
# APT ENGINE CLASS
# ══════════════════════════════════════════════════════════════════

import subprocess
from pathlib import Path

class APTEmulationEngine:
    """
    Runs APT technique simulations for purple team exercises.

    Usage:
        engine = APTEmulationEngine()
        engine.teach_group("apt29")           # Learn about APT29
        engine.run_simulation("credential_access_simulation")  # Run safe checks
        engine.generate_purple_report(results)               # Get red+blue report
    """

    def teach_group(self, group_id: str) -> str:
        """Return a deep-dive teaching lesson on an APT group."""
        group = APT_GROUPS.get(group_id.lower())
        if not group:
            available = ", ".join(APT_GROUPS.keys())
            return f"[APT ENGINE] Unknown group '{group_id}'. Available: {available}"

        sep  = "=" * 56
        dash = "-" * 56
        lines = [
            sep,
            f"  [ERR0RS APT INTEL] {group['name']}",
            sep, "",
            f"  Also known as:  {', '.join(group.get('aka', []))}",
            f"  Origin:         {group.get('origin', 'Unknown')}",
            f"  Motivation:     {group.get('motivation', 'Unknown')}",
            f"  MITRE ID:       {group.get('mitre_id', '')}",
            f"  Source:         {group.get('source', '')}",
            "",
            f"  Known for: {group.get('known_for', '')}",
            "",
            f"  Primary targets: {', '.join(group.get('targets', []))}",
            "",
            dash, "  PRIMARY TTPs (Tactics, Techniques & Procedures):", dash,
        ]
        for ttp in group.get("primary_ttps", []):
            lines.append(f"    • {ttp}")

        lines += ["", dash, "  KILL CHAIN BREAKDOWN:", dash]
        for phase, detail in group.get("key_techniques", {}).items():
            lines.append(f"    [{phase}]")
            lines.append(f"      {detail}")
            lines.append("")

        lines += [dash, "  DETECTION OPPORTUNITIES (for defenders):", dash]
        for det in group.get("detection_opportunities", []):
            lines.append(f"    🔵 {det}")

        if group.get("purple_team_lesson"):
            lines += ["", dash, "  PURPLE TEAM LESSON:", dash,
                      f"  {group['purple_team_lesson']}", ""]

        lines += [sep,
                  f"  Run simulation: apt emulate {group_id}",
                  f"  All groups: apt list groups", sep]
        return "\n".join(lines)

    def run_simulation(self, playbook_id: str,
                       target_os: str = "linux") -> dict:
        """Run a safe APT technique simulation."""
        playbook = SIMULATION_PLAYBOOKS.get(playbook_id)
        if not playbook:
            available = ", ".join(SIMULATION_PLAYBOOKS.keys())
            return {"status": "error",
                    "message": f"Unknown playbook. Available: {available}"}

        print(f"\n{'='*56}")
        print(f"  [ERR0RS APT SIM] {playbook['name']}")
        print(f"  MITRE Tactic: {playbook['mitre']}")
        print(f"  {playbook['desc']}")
        print(f"{'='*56}\n")

        results = {
            "playbook": playbook["name"],
            "mitre":    playbook["mitre"],
            "steps":    [],
            "timestamp": datetime.now().isoformat(),
        }

        for step in playbook.get("steps", []):
            cmd_key = f"safe_cmd_{target_os.lower()}"
            cmd = step.get(cmd_key, step.get("safe_cmd_linux", "echo 'N/A'"))

            print(f"  ▶ [{step['mitre_id']}] {step['name']}")
            print(f"    Technique: {step['technique']}")

            step_result = {
                "name":    step["name"],
                "mitre":   step.get("mitre_id", ""),
                "teaches": step.get("teaches", ""),
                "defense": step.get("defense", ""),
                "output":  "",
                "status":  "pending",
            }

            try:
                r = subprocess.run(cmd, shell=True, capture_output=True,
                                   text=True, timeout=20)
                step_result["output"] = (r.stdout + r.stderr).strip()[:1500]
                step_result["status"] = "ok"
                print(f"    ✅ Complete")
            except subprocess.TimeoutExpired:
                step_result["output"] = "TIMEOUT"
                step_result["status"] = "timeout"
                print(f"    ⏱  Timeout")
            except Exception as e:
                step_result["output"] = f"ERROR: {e}"
                step_result["status"] = "error"
                print(f"    ❌ Error: {e}")

            print(f"\n    📚 TEACHES: {step.get('teaches','')}")
            if step.get("defense"):
                print(f"    🔵 DEFENSE: {step['defense']}")
            print()

            results["steps"].append(step_result)

        return results

    def list_groups(self) -> str:
        lines = ["\n  [APT ENGINE] Known Threat Actor Profiles", "  " + "="*52]
        for gid, g in APT_GROUPS.items():
            lines.append(f"\n  {gid.upper():<12} {g['name']}")
            lines.append(f"             Origin: {g['origin']}")
            lines.append(f"             Known for: {g['known_for'][:60]}")
        lines.append(f"\n  Run: apt teach <group_id>  |  apt emulate <playbook>")
        return "\n".join(lines)

    def list_playbooks(self) -> str:
        lines = ["\n  [APT ENGINE] Simulation Playbooks", "  " + "="*52]
        for pid, p in SIMULATION_PLAYBOOKS.items():
            lines.append(f"\n  {pid}")
            lines.append(f"    {p['name']} — {p['desc']}")
            lines.append(f"    MITRE: {p['mitre']} | Steps: {len(p['steps'])}")
        return "\n".join(lines)

    def generate_purple_report(self, results: list) -> str:
        """Generate a purple team report from simulation results."""
        lines = [
            "# ERR0RS APT Emulation — Purple Team Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Red Team (Attacker) Findings",
            "",
        ]
        for r in results:
            lines.append(f"### {r.get('playbook', 'Simulation')}")
            lines.append(f"**MITRE Tactic:** {r.get('mitre', '')}")
            lines.append("")
            for step in r.get("steps", []):
                status = "✅ Technique demonstrated" if step["status"] == "ok" else f"⚠️ {step['status']}"
                lines.append(f"**[{step['mitre']}] {step['name']}** — {status}")
                if step.get("output"):
                    lines.append(f"```\n{step['output'][:400]}\n```")
                lines.append(f"*Teaches: {step.get('teaches','')}*")
                if step.get("defense"):
                    lines.append(f"\n🔵 **Defense:** {step['defense']}")
                lines.append("")

        lines += ["---",
                  "## Purple Team Recommendations", "",
                  "1. Implement all defenses noted above for each technique",
                  "2. Build SIEM detection rules for each MITRE technique observed",
                  "3. Run Atomic Red Team tests quarterly to validate detections",
                  "4. Re-run this simulation after implementing controls to verify",
                  "",
                  "*Generated by ERR0RS Ultimate APT Emulation Engine*"]
        return "\n".join(lines)


# Singleton
apt_engine = APTEmulationEngine()


def handle_apt_command(cmd: str, params: dict = None) -> dict:
    """Entry point from ERR0RS route_command()"""
    params  = params or {}
    cmd_low = cmd.lower().strip()

    if "list group" in cmd_low or "show group" in cmd_low:
        return {"status": "success", "stdout": apt_engine.list_groups()}

    if "list playbook" in cmd_low or "list sim" in cmd_low:
        return {"status": "success", "stdout": apt_engine.list_playbooks()}

    # Teach a specific group
    for gid in APT_GROUPS:
        if gid in cmd_low or APT_GROUPS[gid]["name"].lower() in cmd_low:
            return {"status": "success",
                    "stdout": apt_engine.teach_group(gid)}

    # Run a simulation
    for pid in SIMULATION_PLAYBOOKS:
        if any(w in cmd_low for w in pid.split("_")):
            r = apt_engine.run_simulation(pid,
                params.get("os", "linux"))
            return {"status": "success",
                    "stdout": json.dumps(r, indent=2)}

    # Default: show all groups
    return {"status": "success", "stdout": apt_engine.list_groups()}
