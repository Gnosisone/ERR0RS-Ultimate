import os
#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — AUTO COACH ENGINE                     ║
║              src/core/auto_coach.py                             ║
║                                                                  ║
║  After any tool finishes, analyzes the output and sends back    ║
║  a plain-English coaching message explaining:                   ║
║    - What was found                                             ║
║    - What it means (severity + context)                         ║
║    - Exactly what to do next (clickable suggestions)            ║
║    - The defensive side (what a blue team would do)             ║
║                                                                  ║
║  This is the core of "ERR0RS explains everything" — the diff    ║
║  between a tool that runs and a tool that teaches.              ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import re
from typing import List, Dict, Optional, Callable


# ── Deterministic coaching rules — fast, always work, offline ────────────────
# Each rule: pattern match on stdout → coaching message + next steps
COACHING_RULES: List[Dict] = [

    # ── NMAP ──────────────────────────────────────────────────────────────────
    {
        "tool": "nmap",
        "pattern": r"445/tcp\s+open",
        "severity": "critical",
        "heading": "SMB EXPOSED — Check for EternalBlue",
        "explain": (
            "Port 445 is Windows SMB (file sharing). It's open and accessible. "
            "This is the port EternalBlue (MS17-010) uses — the exploit behind WannaCry. "
            "Even on patched systems, SMB exposes authentication hashes via NTLM relay attacks."
        ),
        "next_steps": [
            ("nmap --script smb-vuln-ms17-010 -p 445 {target}", "Check EternalBlue"),
            ("enum4linux -a {target}", "Enumerate users, shares, policies"),
            ("nmap --script smb-security-mode -p 445 {target}", "Check auth requirement"),
        ],
        "defense": "Disable SMBv1, block port 445 at the perimeter, require SMB signing.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "nmap",
        "pattern": r"3389/tcp\s+open",
        "severity": "high",
        "heading": "RDP EXPOSED — Remote Desktop accessible",
        "explain": (
            "Port 3389 is RDP (Remote Desktop Protocol). This machine accepts remote GUI connections. "
            "Attack vectors: BlueKeep (CVE-2019-0708), credential brute force, pass-the-hash, "
            "and NLA bypass attacks. Any exposed RDP is a significant attack surface."
        ),
        "next_steps": [
            ("nmap --script rdp-vuln-ms12-020 -p 3389 {target}", "Check DoS vuln"),
            ("hydra -l administrator -P /usr/share/wordlists/rockyou.txt rdp://{target} -t 4", "Brute force"),
        ],
        "defense": "Enable NLA, restrict RDP access by IP, use a VPN or jump host instead of direct exposure.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "nmap",
        "pattern": r"21/tcp\s+open",
        "severity": "high",
        "heading": "FTP EXPOSED — Test anonymous access first",
        "explain": (
            "Port 21 is FTP. It transmits credentials in cleartext and often allows anonymous login. "
            "Even authenticated FTP can be exploited via version-specific vulnerabilities or "
            "writable directories to upload webshells."
        ),
        "next_steps": [
            ("ftp {target}", "Try anonymous login manually"),
            ("nmap --script ftp-anon -p 21 {target}", "Check anonymous access"),
            ("nmap --script ftp-vuln* -p 21 {target}", "Check known FTP CVEs"),
        ],
        "defense": "Replace FTP with SFTP or FTPS. Disable anonymous access. Restrict to known IPs.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "nmap",
        "pattern": r"6379/tcp\s+open.*redis",
        "severity": "critical",
        "heading": "REDIS EXPOSED — Likely unauthenticated",
        "explain": (
            "Redis on port 6379 is frequently deployed without authentication. "
            "An unauthenticated Redis instance can be abused to: read/write arbitrary keys, "
            "overwrite cron jobs (→ RCE), write SSH authorized_keys (→ root shell), "
            "or dump the entire session store if used by a web app."
        ),
        "next_steps": [
            ("redis-cli -h {target} KEYS *", "Check for unauthenticated access + dump keys"),
            ("redis-cli -h {target} INFO server", "Get server info"),
        ],
        "defense": "Enable requirepass in redis.conf. Bind to localhost only. Use ACLs.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "nmap",
        "pattern": r"VULNERABLE",
        "severity": "critical",
        "heading": "CONFIRMED VULNERABILITY — Escalate immediately",
        "explain": (
            "nmap's NSE scripts have confirmed a vulnerability on the target. "
            "This is a positive hit — not just 'maybe vulnerable' but 'the exploit conditions are met.' "
            "Check the script output carefully for CVE numbers and exploit path."
        ),
        "next_steps": [
            ("searchsploit {cve}", "Find exploits for the CVE"),
            ("msfconsole -q -x 'search {cve}'", "Check Metasploit for a module"),
        ],
        "defense": "Patch immediately. Segment the vulnerable service behind a firewall.",
        "xp_event": "found_vuln",
    },

    # ── NIKTO ─────────────────────────────────────────────────────────────────
    {
        "tool": "nikto",
        "pattern": r"X-Frame-Options.*not.*present|X-XSS-Protection.*not.*present|X-Content-Type",
        "severity": "medium",
        "heading": "MISSING SECURITY HEADERS — Clickjacking & XSS risk",
        "explain": (
            "Security headers are cheap defenses that block entire attack categories. "
            "Missing X-Frame-Options allows clickjacking — framing the site and tricking users into clicking things. "
            "Missing X-Content-Type-Options enables MIME sniffing attacks. "
            "These aren't theoretical — they're exploitable without authentication."
        ),
        "next_steps": [
            ("curl -I http://{target}", "Confirm headers manually"),
            ("nuclei -u http://{target} -t http/misconfiguration", "Run misconfiguration templates"),
        ],
        "defense": "Add security headers in your web server config. One-line fixes each.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "nikto",
        "pattern": r"phpMyAdmin|/admin|/wp-admin|/manager",
        "severity": "high",
        "heading": "ADMIN PANEL FOUND — Test default credentials",
        "explain": (
            "Nikto found an admin interface. These are high-value targets — "
            "access here often means full control. Default credentials (admin:admin, admin:password) "
            "still work on a shocking percentage of real-world deployments."
        ),
        "next_steps": [
            ("hydra -L /usr/share/wordlists/metasploit/http_default_users.txt -P /usr/share/wordlists/metasploit/http_default_pass.txt http-get-form://{target}/admin", "Brute default creds"),
        ],
        "defense": "Restrict admin paths by IP. Enforce MFA. Rename default admin URLs.",
        "xp_event": "found_vuln",
    },

    # ── GOBUSTER ──────────────────────────────────────────────────────────────
    {
        "tool": "gobuster",
        "pattern": r"Status: 200|Status: 301|Status: 302",
        "severity": "info",
        "heading": "DIRECTORIES FOUND — Investigate each 200/301",
        "explain": (
            "Gobuster found accessible paths. Status 200 = directly accessible. "
            "Status 301/302 = redirect (usually to the same page with a slash, still accessible). "
            "Pay special attention to: /api/, /admin/, /.git/, /backup/, /config/, /uploads/"
        ),
        "next_steps": [
            ("curl http://{target}/FOUND_PATH", "Inspect each path manually"),
            ("ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403", "Deeper fuzz"),
        ],
        "defense": "Return 404 for sensitive paths (not 403 — 403 confirms existence). Implement authentication.",
        "xp_event": "found_vuln",
    },
    {
        "tool": "gobuster",
        "pattern": r"\.git|\.env|backup|\.bak|config\.php|wp-config",
        "severity": "critical",
        "heading": "SENSITIVE FILE EXPOSED — Potential credential leak",
        "explain": (
            "A highly sensitive file or directory was found. "
            ".git repos contain your entire source code and commit history (including old hardcoded secrets). "
            ".env files contain database passwords, API keys, and secret keys. "
            "Backup files (.bak, .backup) often contain the same secrets without access controls."
        ),
        "next_steps": [
            ("wget -r http://{target}/.git/", "Download the entire .git directory"),
            ("git log --oneline", "Check commit history for secrets"),
            ("curl http://{target}/.env", "Read the .env file directly"),
        ],
        "defense": "Never deploy .git directories to production. Add .env to .gitignore. Delete backup files from the web root.",
        "xp_event": "found_creds",
    },

    # ── SQLMAP ────────────────────────────────────────────────────────────────
    {
        "tool": "sqlmap",
        "pattern": r"is vulnerable|parameter.*is.*injectable|Type.*UNION",
        "severity": "critical",
        "heading": "SQL INJECTION CONFIRMED",
        "explain": (
            "sqlmap has confirmed SQL injection. The database is directly accessible through "
            "this vulnerability. From here we can: dump all tables and data, "
            "read/write files on the OS (--file-read, --file-write), "
            "and potentially get a shell (--os-shell) if the DB user has FILE privilege."
        ),
        "next_steps": [
            ("sqlmap -u {url} --dbs", "Enumerate all databases"),
            ("sqlmap -u {url} -D db_name --tables", "Dump table names"),
            ("sqlmap -u {url} -D db_name -T users --dump", "Dump user table"),
            ("sqlmap -u {url} --os-shell", "Attempt OS shell (FILE privilege required)"),
        ],
        "defense": "Use parameterized queries (prepared statements). Never concatenate user input into SQL. Enable WAF.",
        "xp_event": "found_vuln",
    },

    # ── HYDRA ─────────────────────────────────────────────────────────────────
    {
        "tool": "hydra",
        "pattern": r"login:\s*\S+\s+password:\s*\S+|valid password found",
        "severity": "critical",
        "heading": "CREDENTIALS CRACKED",
        "explain": (
            "Hydra found valid credentials. This is a confirmed authentication bypass. "
            "These credentials may work across multiple services (credential stuffing) — "
            "people reuse passwords constantly. Immediately test them against SSH, RDP, web admin panels, "
            "email, VPN, and any other services you've found."
        ),
        "next_steps": [
            ("ssh {username}@{target}", "Test SSH access"),
            ("evil-winrm -i {target} -u {username} -p '{password}'", "Test WinRM"),
            ("crackmapexec smb {target} -u {username} -p '{password}'", "Test SMB access"),
        ],
        "defense": "Implement account lockout after 5 failed attempts. Require MFA. Monitor for brute-force patterns in logs.",
        "xp_event": "found_creds",
    },

    # ── NUCLEI ────────────────────────────────────────────────────────────────
    {
        "tool": "nuclei",
        "pattern": r"\[critical\]|\[high\]",
        "severity": "critical",
        "heading": "NUCLEI: CRITICAL/HIGH SEVERITY FINDINGS",
        "explain": (
            "Nuclei has matched a high or critical severity template against the target. "
            "Nuclei templates are precise — a match means the vulnerability signature was confirmed, "
            "not just guessed. Cross-reference the template name with CVE databases for full details."
        ),
        "next_steps": [
            ("nuclei -u http://{target} -severity critical,high -o nuclei_findings.txt", "Save all critical/high findings"),
        ],
        "defense": "Patch the specific CVEs identified. Subscribe to nuclei template updates for ongoing detection.",
        "xp_event": "found_vuln",
    },

    # ── GENERIC — always fires if no specific rule matches ────────────────────
    {
        "tool": "*",
        "pattern": r".",  # always matches
        "severity": "info",
        "heading": "TOOL COMPLETE",
        "explain": None,  # Skip generic explanation — too noisy
        "next_steps": [],
        "defense": None,
        "xp_event": None,
    },
]


def analyze_output(tool: str, stdout: str, target: str = "") -> Optional[Dict]:
    """
    Analyze tool output and return a coaching block, or None if nothing notable.

    Returns: {
        heading, explain, severity, next_steps, defense, command_suggestions
    }
    """
    tool_lower = tool.lower().replace("-", "_")

    matched = []

    for rule in COACHING_RULES:
        rule_tool = rule["tool"]
        # Skip generic catch-all for now — only add it if nothing matched
        if rule_tool == "*":
            continue

        if rule_tool not in tool_lower:
            continue

        if not re.search(rule["pattern"], stdout, re.IGNORECASE | re.MULTILINE):
            continue

        # Build next step commands with target substituted
        steps = []
        for cmd_template, label in rule.get("next_steps", []):
            cmd = cmd_template.replace("{target}", target).replace("{ip}", target)
            # Extract CVE if present
            cve_match = re.search(r"CVE-\d{4}-\d+", stdout)
            if cve_match:
                cmd = cmd.replace("{cve}", cve_match.group(0))
            # Extract URL if present
            url_match = re.search(r"https?://\S+", stdout) or re.search(r"http://\S+", stdout)
            if url_match:
                cmd = cmd.replace("{url}", url_match.group(0))
            steps.append({"command": cmd, "label": label})

        matched.append({
            "heading":   rule["heading"],
            "explain":   rule["explain"],
            "severity":  rule["severity"],
            "steps":     steps,
            "defense":   rule.get("defense"),
            "xp_event":  rule.get("xp_event"),
        })

    if not matched:
        return None

    # Return the highest severity match
    sev_order = ["critical", "high", "medium", "low", "info"]
    matched.sort(key=lambda r: sev_order.index(r["severity"]) if r["severity"] in sev_order else 99)

    # Build a combined result (may have multiple findings)
    primary = matched[0]
    all_steps = []
    for m in matched:
        all_steps.extend(m["steps"])

    # Deduplicate steps by command
    seen = set()
    deduped_steps = []
    for step in all_steps:
        if step["command"] not in seen:
            seen.add(step["command"])
            deduped_steps.append(step)

    return {
        "heading":          primary["heading"],
        "explain":          primary["explain"],
        "severity":         primary["severity"],
        "all_findings":     matched,
        "next_steps":       deduped_steps[:6],  # Max 6 suggestions
        "defense":          primary["defense"],
        "xp_event":         primary["xp_event"],
        "finding_count":    len(matched),
    }


def format_coaching_block(result: Dict, tool: str) -> str:
    """Format a coaching result as a readable text block for the terminal."""
    sev_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}
    icon = sev_icons.get(result["severity"], "⚪")

    lines = [
        f"\n{'═'*60}",
        f"{icon} ERR0RS ANALYSIS: {result['heading']}",
        f"{'─'*60}",
    ]

    if result.get("explain"):
        lines.append(f"\n📋 WHAT THIS MEANS:\n{result['explain']}\n")

    if result.get("next_steps"):
        lines.append("⚡ RECOMMENDED NEXT STEPS:")
        for i, step in enumerate(result["next_steps"], 1):
            lines.append(f"  {i}. [{step['label']}]")
            lines.append(f"     $ {step['command']}")

    if result.get("defense"):
        lines.append(f"\n🛡️  DEFENSIVE COUNTERMEASURE:")
        lines.append(f"  {result['defense']}")

    lines.append(f"{'═'*60}\n")
    return "\n".join(lines)


def coach_output(tool: str, stdout: str, target: str = "",
                 broadcast_fn: Optional[Callable] = None) -> Optional[Dict]:
    """
    Full coaching pipeline: analyze output → format → broadcast.

    Call this after any tool completes. broadcast_fn receives
    {"type": "coach", "data": str, "result": dict}
    """
    if not stdout or len(stdout.strip()) < 20:
        return None

    result = analyze_output(tool, stdout, target)
    if not result or result["severity"] == "info":
        return None

    coaching_text = format_coaching_block(result, tool)

    # Award XP if applicable
    if result.get("xp_event"):
        try:
            from src.core.progression import award_xp
            award_xp(result["xp_event"], f"{tool}: {result['heading']}")
        except Exception:
            pass

    if broadcast_fn:
        broadcast_fn({
            "type":    "coach",
            "data":    coaching_text,
            "result":  {k: v for k, v in result.items() if k != "all_findings"},
            "tool":    tool,
            "target":  target,
        })

    return result
