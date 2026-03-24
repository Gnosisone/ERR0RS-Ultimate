"""
ERR0RS ULTIMATE - Security Knowledge Base
============================================
This is the library. Every vulnerability type, every attack technique,
every tool — if ERR0RS encounters it, the education is here.

STRUCTURE:
----------
KNOWLEDGE_BASE is a dict. The key is a tag or vulnerability type.
The value is an EducationContent instance with all the teaching.

When a Finding comes in with tag "sql_injection", the engine looks up
KNOWLEDGE_BASE["sql_injection"] and attaches that education.

This file is designed to be EXTENDED easily. To add a new topic:
1. Create a new EducationContent instance
2. Give it a key that matches what your tool outputs
3. Drop it in the KNOWLEDGE_BASE dict
4. Done. It auto-teaches.
"""

try:
    from src.education.education_engine import EducationContent
except ImportError:
    from education_engine import EducationContent


# =============================================================================
# RED TEAM TECHNIQUES — Offensive attack knowledge
# =============================================================================

KNOWLEDGE_BASE = {

# ---------------------------------------------------------------------------
# SQL INJECTION
# ---------------------------------------------------------------------------
"sql_injection": EducationContent(
    topic="SQL Injection (SQLi)",
    what="SQL Injection is when an attacker inserts malicious SQL code into "
         "input fields that get passed directly to a database query without "
         "proper sanitization. The database executes the attacker's code as if "
         "it were a legitimate query.",
    why="SQLi can give an attacker full control over a database. That means "
        "reading all user data (passwords, credit cards, PII), modifying or "
        "deleting data, or in some cases executing commands on the server itself. "
        "It consistently ranks in the OWASP Top 10.",
    how="Example: A login form takes username input and builds a query like:\n"
        "  SELECT * FROM users WHERE username = '[INPUT]'\n"
        "If you type: ' OR '1'='1\n"
        "The query becomes:\n"
        "  SELECT * FROM users WHERE username = '' OR '1'='1'\n"
        "That returns ALL users. The database just ran your code.",
    defend="1. Use parameterized queries / prepared statements — ALWAYS.\n"
           "2. Input validation and sanitization on every field.\n"
           "3. Least-privilege database accounts (app shouldn't be root).\n"
           "4. Web Application Firewalls (WAF) as a second layer.\n"
           "5. Regular security testing with tools like SQLMap.",
    real_world="In 2012, Yahoo was breached via SQL injection. Hackers extracted "
               "4.1 million usernames and passwords. The vulnerability was in a "
               "legacy ad management system that hadn't been updated in years.",
    difficulty="Beginner",
    references=[
        "https://owasp.org/www-community/attacks/SQL_Injection",
        "https://portswigger.net/web-security/sql-injection",
        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
    ]
),

# ---------------------------------------------------------------------------
# PORT SCANNING / NMAP
# ---------------------------------------------------------------------------
"port_scanning": EducationContent(
    topic="Port Scanning & Network Reconnaissance",
    what="Port scanning is the process of probing a network host to determine "
         "which ports are open, what services are running on them, and what "
         "software versions those services use. It is the foundation of almost "
         "every penetration test.",
    why="Open ports are attack surface. Every service running on a network is "
        "a potential entry point. Before exploiting anything, an attacker needs "
        "to know what's there. This is reconnaissance — the first phase.",
    how="Nmap sends packets to ports 1-65535 and analyzes responses:\n"
        "- Port OPEN: Service accepted the connection\n"
        "- Port CLOSED: Port exists but nothing is listening\n"
        "- Port FILTERED: Firewall is dropping packets (hiding the port)\n"
        "SYN scanning (-sS) is the default — it sends a SYN packet and checks "
        "the response without completing the TCP handshake. Stealthy.",
    defend="1. Close every port you don't need (principle of least privilege).\n"
           "2. Use firewalls to filter inbound traffic.\n"
           "3. Network segmentation — isolate critical systems.\n"
           "4. IDS/IPS systems detect and alert on scanning activity.\n"
           "5. Regular auditing of what's actually listening on your network.",
    real_world="Before the Colonial Pipeline attack in 2021, attackers performed "
               "reconnaissance scanning to map the network. Finding exposed "
               "services was how they identified their initial entry point.",
    difficulty="Beginner",
    references=[
        "https://nmap.org/book/techniques-scan-types.html",
        "https://owasp.org/www-project-testing-guide/",
    ]
),

# ---------------------------------------------------------------------------
# BRUTE FORCE / CREDENTIAL ATTACKS
# ---------------------------------------------------------------------------
"brute_force": EducationContent(
    topic="Brute Force & Credential Attacks",
    what="Brute force attacks systematically try every possible password "
         "combination until the correct one is found. Dictionary attacks are "
         "a smarter variant — they use wordlists of common passwords instead "
         "of random guessing.",
    why="Weak or reused passwords are one of the most common ways attackers "
        "gain initial access. If you can crack one account, you might access "
        "the entire network depending on that user's privileges.",
    how="Tools like Hydra automate this:\n"
        "  hydra -l admin -P wordlist.txt http-post-form\n"
        "It sends login attempts at high speed. Modern tools can try "
        "thousands of passwords per second against web login forms, SSH, "
        "FTP, and many other protocols.",
    defend="1. Multi-Factor Authentication (MFA) — kills brute force.\n"
           "2. Account lockout after failed attempts.\n"
           "3. Rate limiting on login endpoints.\n"
           "4. Strong password policies (length > complexity).\n"
           "5. Fail2Ban or similar tools to auto-block IPs.",
    real_world="The 2020 Microsoft Exchange hack used credential stuffing "
               "(reusing leaked passwords) to get initial access before "
               "deploying the actual exploit.",
    difficulty="Beginner",
    references=[
        "https://owasp.org/www-community/attacks/Brute_Force_Attack",
        "https://portswigger.net/web-security/authentication/brute-force",
    ]
),

# ---------------------------------------------------------------------------
# DIRECTORY / ENDPOINT DISCOVERY
# ---------------------------------------------------------------------------
"directory_brusting": EducationContent(
    topic="Web Directory & Endpoint Discovery",
    what="Directory busting (or web content discovery) is the process of "
         "finding hidden or unlisted pages, files, and API endpoints on a "
         "web server by trying common paths against it. Just because a URL "
         "isn't linked on a website doesn't mean it doesn't exist.",
    why="Developers often leave admin panels, backup files, API documentation, "
        "debug endpoints, and configuration files accessible but unlisted. "
        "These are goldmines for attackers.",
    how="Tools like Gobuster send HTTP requests to paths from a wordlist:\n"
        "  gobuster dir -u http://target.com -w /usr/share/wordlists/common.txt\n"
        "If the server returns 200 OK, the path exists. 301/302 means redirect. "
        "403 means it exists but access is denied (still interesting!).",
    defend="1. Remove all unnecessary files from production servers.\n"
           "2. Disable directory listing on web servers.\n"
           "3. Restrict access to admin and management endpoints.\n"
           "4. Use Web Application Firewalls to detect enumeration.\n"
           "5. Return identical responses for 404s (don't reveal info).",
    real_world="Many bug bounty hunters have found admin panels at /admin, "
               "backup databases at /db_backup.sql, and API docs at /swagger "
               "simply by running a wordlist against the target.",
    difficulty="Beginner",
    references=[
        "https://github.com/OJ/gobuster",
        "https://owasp.org/www-project-testing-guide/latest/4-Web_Application_Testing/02-Configuration_and_Deployment_Management_Testing/",
    ]
),

# ---------------------------------------------------------------------------
# CROSS-SITE SCRIPTING (XSS)
# ---------------------------------------------------------------------------
"xss": EducationContent(
    topic="Cross-Site Scripting (XSS)",
    what="XSS is when an attacker injects malicious JavaScript into a web "
         "page that other users then execute in their browsers. The victim's "
         "browser thinks the script is legitimate because it came from the "
         "trusted website.",
    why="XSS can steal session cookies (hijack accounts), redirect users to "
        "phishing sites, log keystrokes, deface websites, and in some cases "
        "spread to other users automatically (worm XSS).",
    how="Stored XSS: Attacker posts a comment containing <script>alert('xss')</script>. "
        "Every user who views that comment executes the script.\n"
        "Reflected XSS: A URL parameter is echoed back in the page without "
        "sanitization. Attacker sends a victim a crafted URL.",
    defend="1. Output encoding — ALWAYS encode user input before rendering.\n"
           "2. Content Security Policy (CSP) headers.\n"
           "3. HttpOnly cookies prevent JavaScript from reading them.\n"
           "4. Input validation on both client AND server side.\n"
           "5. Use modern frameworks that auto-escape by default (React, Angular).",
    real_world="The 2010 Samy worm on MySpace was a stored XSS attack that "
               "automatically added the creator as a friend for 1.5 million "
               "users in just 24 hours.",
    difficulty="Intermediate",
    references=[
        "https://owasp.org/www-community/attacks/xss/",
        "https://portswigger.net/web-security/cross-site-scripting",
    ]
),

# =============================================================================
# BLUE TEAM / DEFENSE — Understanding the defender's perspective
# =============================================================================

"incident_response": EducationContent(
    topic="Incident Response Process",
    what="Incident response (IR) is the structured process an organization "
         "follows when a security breach or attack is detected. It ensures "
         "the threat is contained, damage is minimized, and the organization "
         "can recover and learn from what happened.",
    why="Without a plan, a breach becomes a catastrophe. Organizations that "
        "follow IR procedures recover faster, lose less data, and pay less "
        "in damages. It's the defensive counterpart to red team operations.",
    how="The standard IR phases (NIST framework):\n"
        "1. PREPARATION — Have a plan before you need it\n"
        "2. IDENTIFICATION — Detect that something is wrong\n"
        "3. CONTAINMENT — Stop the attack from spreading\n"
        "4. ERADICATION — Remove the threat completely\n"
        "5. RECOVERY — Restore normal operations\n"
        "6. LESSONS LEARNED — Document and improve",
    defend="IR IS the defense. Blue teams run these procedures. Every pentest "
           "report should help the client improve their IR plan by showing "
           "exactly how an attacker moved through their network.",
    real_world="After the SolarWinds breach in 2020, affected organizations "
               "followed IR procedures to identify compromised systems, revoke "
               "attacker access, and patch the supply chain vulnerability.",
    difficulty="Intermediate",
    references=[
        "https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final",
        "https://www.sans.org/security-resources/incident-response-cheat-sheets",
    ]
),

# ---------------------------------------------------------------------------
# PENTEST REPORTING — The product you deliver
# ---------------------------------------------------------------------------
"pentest_reporting": EducationContent(
    topic="Professional Pentest Reporting",
    what="A pentest report is the ONLY deliverable that matters in a "
         "professional engagement. The testing is research. The report is "
         "the product. It must communicate findings clearly to both "
         "technical and non-technical audiences.",
    why="The best pentest in the world is worthless if the report is unclear. "
        "Reports drive remediation decisions, budget allocations, and security "
        "strategy. A bad report = no action taken = vulnerabilities persist.",
    how="Professional reports have two core sections:\n"
        "1. EXECUTIVE SUMMARY — Written for C-suite. No jargon. Focus on "
        "   business risk and impact. Usually 1-2 pages.\n"
        "2. TECHNICAL DETAILS — Written for IT teams. Exact reproduction "
        "   steps, tool output, severity ratings, and remediation steps.\n"
        "Both sections are critical. Neither can be skipped.",
    defend="Good reporting IS defense. When the report clearly explains "
           "how to fix each finding, the organization can actually remediate. "
           "This is how pentesters protect organizations.",
    real_world="Many pentest firms charge 30-50% of their total fee purely "
               "for the report writing. It's that valuable. A well-written "
               "report has gotten organizations millions in budget approval "
               "for security improvements.",
    difficulty="Intermediate",
    references=[
        "https://www.sans.org/security-resources/glossary-of-terms/penetration-testing",
        "https://owasp.org/www-project-web-security-testing-guide/",
    ]
),

# ---------------------------------------------------------------------------
# PRIVILEGE ESCALATION
# ---------------------------------------------------------------------------
"privilege_escalation": EducationContent(
    topic="Privilege Escalation",
    what="Privilege escalation is when an attacker moves from a low-privilege "
         "account to a higher-privilege one — for example, from a regular "
         "web app user to a system administrator. It's how initial access "
         "becomes full compromise.",
    why="Most initial access gives you limited privileges. Escalation is what "
        "turns a foothold into full control. It's one of the most critical "
        "steps in any attack chain and the hardest to detect.",
    how="Common techniques:\n"
        "- Exploiting misconfigurations (SUID binaries on Linux)\n"
        "- Kernel exploits (unpatched OS vulnerabilities)\n"
        "- Credential reuse (found passwords work for admin accounts)\n"
        "- Token/ticket abuse (Kerberoasting on Windows AD)\n"
        "Tools: LinPEAS, WinPEAS, PowerSploit",
    defend="1. Keep all systems patched (kernel exploits need patches).\n"
           "2. Principle of least privilege for all accounts.\n"
           "3. Disable SUID on unnecessary binaries.\n"
           "4. Strong Active Directory hardening.\n"
           "5. Monitor for unusual privilege changes.",
    real_world="In the Colonial Pipeline attack, after gaining initial access "
               "via compromised credentials, attackers escalated privileges "
               "to deploy ransomware across the entire network.",
    difficulty="Advanced",
    references=[
        "https://hacktricks.xyz/linux-hardening/privilege-escalation",
        "https://attack.mitre.org/tactics/TA0008/",
    ]
),


# ---------------------------------------------------------------------------
# MIMIKATZ — Windows Credential Extraction
# ---------------------------------------------------------------------------
"mimikatz": EducationContent(
    topic="Mimikatz — Windows Credential Extraction",
    what="Mimikatz is a post-exploitation tool that reads credential data from "
         "Windows memory. It targets lsass.exe (Local Security Authority Subsystem "
         "Service) to extract NTLM hashes, Kerberos tickets, and sometimes plaintext "
         "passwords. IMPORTANT: Mimikatz is Windows authentication ONLY. It cannot "
         "crack WiFi passwords, Linux credentials, or web passwords.",
    why="After gaining initial access, credentials let you move laterally, escalate "
        "privileges, and persist. A single set of admin credentials from Mimikatz "
        "can unlock an entire domain. sekurlsa::logonpasswords is often the fastest "
        "path from foothold to Domain Admin.",
    how="Core workflow:\n"
        "1. Run as Administrator (or SYSTEM)\n"
        "2. privilege::debug — grants SeDebugPrivilege to read lsass\n"
        "3. sekurlsa::logonpasswords — dumps NTLM hashes + plaintext (if WDigest on)\n"
        "4. lsadump::sam — dumps local SAM database (needs SYSTEM)\n"
        "5. lsadump::dcsync /user:krbtgt — pulls domain hashes without touching lsass\n"
        "6. sekurlsa::pth /user:X /ntlm:HASH /run:cmd.exe — Pass-the-Hash\n\n"
        "Offline method (stealthier):\n"
        "  rundll32 comsvcs.dll MiniDump <lsass_pid> C:\\lsass.dmp full\n"
        "  Then: sekurlsa::minidump lsass.dmp → sekurlsa::logonpasswords",
    defend="1. Enable Credential Guard (virtualizes lsass — blocks Mimikatz).\n"
           "2. Add sensitive accounts to Protected Users group.\n"
           "3. Enable PPL (Protected Process Light) on lsass.\n"
           "4. Disable WDigest authentication (prevents plaintext creds).\n"
           "5. Monitor: Sysmon Event 10 (lsass access), Windows Event 4648.",
    real_world="Mimikatz was used in the NotPetya attack (2017) to spread laterally "
               "across networks by harvesting credentials from memory and using them "
               "to authenticate to other machines via Pass-the-Hash.",
    difficulty="Intermediate",
    references=[
        "https://github.com/gentilkiwi/mimikatz",
        "https://attack.mitre.org/techniques/T1003/001/",
    ]
),

# ---------------------------------------------------------------------------
# WIFI / WIRELESS — Password Recovery and WPA2 Cracking
# ---------------------------------------------------------------------------
"wifi_cracking": EducationContent(
    topic="WiFi Password Recovery and WPA2 Cracking",
    what="WiFi password attacks have THREE completely different paths depending "
         "on your situation. The correct tool depends on what you have access to. "
         "WiFi uses WPA2 (PBKDF2-HMAC-SHA1) — a completely different algorithm than "
         "Windows NTLM. Mimikatz, John, and NTLM crackers DO NOT work on WiFi hashes.",
    why="Wireless credentials are a common initial access vector. A cracked WiFi "
        "password gives network access. Saved WiFi profiles on a compromised machine "
        "can reveal passwords to corporate, home, or client networks the machine "
        "has ever connected to.",
    how="PATH 1 — Machine already has saved WiFi (fastest, no cracking):\n"
        "  netsh wlan show profiles\n"
        "  netsh wlan show profile name='SSID' key=clear\n"
        "  Look for: Key Content = <plaintext password>\n\n"
        "PATH 2 — Capture and crack WPA2 handshake:\n"
        "  airmon-ng check kill && airmon-ng start wlan0\n"
        "  airodump-ng -c CH --bssid AP_MAC -w capture wlan0mon\n"
        "  aireplay-ng -0 5 -a AP_MAC -c CLIENT_MAC wlan0mon  (force reconnect)\n"
        "  hcxpcapngtool -o capture.hc22000 capture-01.cap\n"
        "  hashcat -m 22000 capture.hc22000 rockyou.txt\n\n"
        "PATH 3 — PMKID attack (no clients needed):\n"
        "  hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=1\n"
        "  hcxpcapngtool -o pmkid.hc22000 pmkid.pcapng\n"
        "  hashcat -m 22000 pmkid.hc22000 rockyou.txt",
    defend="1. Use WPA3 — immune to PMKID and offline dictionary attacks.\n"
           "2. Long random passphrase (20+ chars) — dictionary attacks fail.\n"
           "3. 802.11w (Management Frame Protection) — blocks deauth attacks.\n"
           "4. WIDS (Wireless IDS) — alerts on rogue APs and deauth floods.\n"
           "5. WPA2-Enterprise with certificates — no shared password to crack.",
    real_world="Wardriving studies consistently find 20-30% of WPA2 networks use "
               "passwords in the rockyou.txt wordlist. Most home networks are "
               "cracked within minutes. PMKID attacks require only seconds of "
               "proximity to the AP — no clients needed.",
    difficulty="Beginner",
    references=[
        "https://www.aircrack-ng.org/documentation.html",
        "https://hashcat.net/wiki/doku.php?id=hashcat",
    ]
),

# ---------------------------------------------------------------------------
# WIRELESS TOOL SELECTION — Decision tree for common confusion
# ---------------------------------------------------------------------------
"wireless_tool_selection": EducationContent(
    topic="Wireless vs Windows Credentials — Tool Selection Guide",
    what="The most common student mistake: using the wrong tool for the credential "
         "type. Mimikatz is for Windows authentication (NTLM/Kerberos). Aircrack/"
         "hashcat are for WiFi (WPA2/PBKDF2). These are completely different "
         "cryptographic systems with no overlap.",
    why="Using the wrong tool wastes time and produces no results. Understanding "
        "the underlying crypto tells you instantly which tool to reach for.",
    how="DECISION TREE:\n"
        "Q: What do I have?\n"
        "  .cap/.pcapng file from WiFi → hashcat -m 22000 or aircrack-ng\n"
        "  Windows machine with saved WiFi → netsh wlan show profile key=clear\n"
        "  NTLM hash (from SAM/lsass) → hashcat -m 1000 or Mimikatz PTH\n"
        "  NTLMv2 net-hash (from Responder) → hashcat -m 5600\n"
        "  Kerberos TGS ticket → hashcat -m 13100 (Kerberoasting)\n\n"
        "HASH TYPE CHEAT SHEET:\n"
        "  WPA2 PBKDF2   → hashcat mode 22000\n"
        "  NTLM           → hashcat mode 1000\n"
        "  NTLMv2         → hashcat mode 5600\n"
        "  Kerberos TGS   → hashcat mode 13100\n"
        "  MD5            → hashcat mode 0\n"
        "  SHA-256        → hashcat mode 1400",
    defend="N/A — this is a tool selection reference entry.",
    real_world="During a pentest, a tester found a .cap file on a compromised workstation. "
               "They ran Mimikatz against it expecting WiFi creds — got nothing. "
               "The correct move: hcxpcapngtool to convert, then hashcat -m 22000. "
               "Password cracked in 4 minutes.",
    difficulty="Beginner",
    references=[
        "https://hashcat.net/wiki/doku.php?id=hashcat",
        "https://attack.mitre.org/techniques/T1040/",
    ]
),

}  # End KNOWLEDGE_BASE


# =============================================================================
# LOOKUP FUNCTION — The interface the rest of the framework uses
# =============================================================================

def get_education(tag: str, difficulty_max: str = "Advanced") -> EducationContent | None:
    """
    Look up education content by tag.
    Returns None if not found (graceful — doesn't crash the pipeline).
    """
    difficulty_order = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    content = KNOWLEDGE_BASE.get(tag.lower().replace(" ", "_"))
    if content is None:
        return None
    if difficulty_order.get(content.difficulty, 0) > difficulty_order.get(difficulty_max, 2):
        return None
    return content


def get_education_for_finding(finding_tags: list) -> list:
    """
    Given a list of tags from a Finding, return all matching education.
    A single finding can trigger multiple education blocks.
    """
    results = []
    for tag in finding_tags:
        edu = get_education(tag)
        if edu:
            results.append(edu)
    return results


def list_all_topics() -> list:
    """Return all available education topics."""
    return list(KNOWLEDGE_BASE.keys())
