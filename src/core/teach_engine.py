#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — EXPANDED TEACH ENGINE                 ║
║              src/core/teach_engine.py                           ║
║                                                                  ║
║  Rich per-tool AND per-concept lessons covering:                 ║
║    Tools: nmap, nikto, gobuster, sqlmap, hydra, nuclei,         ║
║           whatweb, enum4linux, crackmapexec, ffuf, metasploit,  ║
║           bloodhound, hashcat, volatility, wireshark, burp,     ║
║           impacket, responder, mimikatz, linpeas, netcat        ║
║    Concepts: CIS Controls 1-18, OWASP Top 10, MITRE ATT&CK      ║
║              Kill Chain, CIA Triad, threat modeling, IR phases  ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

LESSONS = {

    # ══════════════════════════════════════════════════════════════
    # OFFENSIVE TOOLS
    # ══════════════════════════════════════════════════════════════

    "nmap": {
        "summary": "Network scanner — maps hosts, ports, services, and vulnerabilities",
        "typical": "nmap -sV -sC -p- 192.168.1.100",
        "flags": {
            "-sV":          "Version detection — fingerprints exact software running on each port",
            "-sC":          "Default NSE scripts — runs common checks like SMB signing, HTTP headers",
            "-p-":          "All 65535 ports (slow but thorough — default only checks top 1000)",
            "-p 80,443,22": "Specific ports only — fast for targeted checks",
            "-A":           "Aggressive: OS detection + version + scripts + traceroute",
            "-sS":          "SYN stealth scan — doesn't complete the handshake, harder to log",
            "-sU":          "UDP scan — finds DNS (53), SNMP (161), NTP (123)",
            "-O":           "OS detection — guesses OS from TCP/IP fingerprint",
            "--script":     "Run specific NSE scripts: --script smb-vuln-ms17-010",
            "-oA":          "Output all formats: -oA scan saves .nmap .xml .gnmap",
            "-T4":          "Timing template (0-5), T4 = aggressive speed, good for labs",
            "--open":       "Only show open ports — cleaner output",
            "-Pn":          "Skip host discovery — scan even if ICMP blocked",
            "-v":           "Verbose — see what nmap is doing in real time",
        },
        "read": [
            "STATE = open means the port is accepting connections — investigate it",
            "open|filtered = port exists but state unclear (firewall involved)",
            "service VERSION tells you exactly what software to search for CVEs",
            "NSE script output shows YES/NO/VULNERABLE for specific checks",
            "OS details may be wrong — it's a fingerprint guess, not a fact",
        ],
        "next": ["nikto (web ports)", "enum4linux (SMB)", "hydra (found services)", "searchsploit (service versions)"],
        "caution": "SYN scans require root. -p- is slow — use -T4 or limit port range first.",
    },

    "nikto": {
        "summary": "Web vulnerability scanner — checks for 6,700+ known issues",
        "typical": "nikto -h http://target.com -C all -maxtime 120",
        "flags": {
            "-h":           "Target host or URL",
            "-C all":       "Check ALL categories (default is limited)",
            "-ssl":         "Force HTTPS/SSL testing",
            "-p":           "Specify port: -p 8080",
            "-maxtime":     "Stop after N seconds: -maxtime 300",
            "-o":           "Save output: -o nikto_results.txt",
            "-Format":      "Output format: txt, csv, htm, xml",
            "-id":          "Authentication: -id user:password",
            "-useproxy":    "Route through proxy (Burp): -useproxy http://127.0.0.1:8080",
            "-Tuning":      "Only run certain test types: -Tuning 1 (interesting files)",
        },
        "read": [
            "+ means Nikto found something — every line starting with + is a finding",
            "Missing security headers (X-Frame-Options, CSP) = clickjacking risk",
            "Server: header reveals software version — check it in CVE databases",
            "OSVDB numbers are old — cross-reference with CVE.mitre.org",
            "False positives are common — verify every finding manually",
        ],
        "next": ["gobuster (path enum)", "sqlmap (if forms found)", "burp (manual testing)", "nuclei (template scan)"],
        "caution": "Nikto is loud — it will appear in IDS logs. Don't use without authorization.",
    },

    "gobuster": {
        "summary": "Directory/subdomain brute forcer — finds hidden paths and virtual hosts",
        "typical": "gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt -t 30 -q",
        "flags": {
            "dir":          "Directory enumeration mode",
            "dns":          "Subdomain enumeration: gobuster dns -d target.com -w wordlist.txt",
            "vhost":        "Virtual host discovery (different sites on same IP)",
            "-u":           "Target URL",
            "-w":           "Wordlist path",
            "-t":           "Threads (default 10, use 30-50 for speed in labs)",
            "-x":           "File extensions to append: -x php,html,txt,bak,zip",
            "-b":           "Status codes to ignore: -b 404,500",
            "-q":           "Quiet mode — only show results",
            "-o":           "Save output to file",
            "-k":           "Skip TLS certificate verification",
            "--exclude-length": "Hide responses of specific lengths (filter noise)",
        },
        "read": [
            "Status 200 = directly accessible — investigate immediately",
            "Status 301/302 = redirect, follow it — usually still accessible",
            "Status 403 = forbidden but EXISTS — try bypass techniques",
            "Status 401 = authentication required — credential attack opportunity",
            "Large response sizes vs small may indicate different content — compare",
        ],
        "next": ["ffuf (deeper fuzzing)", "curl/browser (inspect found paths)", "sqlmap (if forms)"],
        "caution": "High thread counts can crash fragile apps. Start with -t 10 on production.",
    },

    "sqlmap": {
        "summary": "Automated SQL injection scanner and exploiter",
        "typical": "sqlmap -u 'http://target.com/page?id=1' --dbs --batch",
        "flags": {
            "-u":           "Target URL with injectable parameter",
            "--dbs":        "Enumerate all databases",
            "--tables":     "Enumerate tables: -D dbname --tables",
            "--dump":       "Dump table data: -D db -T users --dump",
            "--batch":      "Auto-answer all prompts (non-interactive)",
            "--level":      "Test depth 1-5 (default 1, use 3+ for more vectors)",
            "--risk":       "Risk level 1-3 (higher = more aggressive, possible data modification)",
            "--forms":      "Auto-detect and test HTML forms",
            "--crawl":      "Spider the site and test all found parameters: --crawl=3",
            "--data":       "POST data: --data='user=test&pass=test'",
            "--cookie":     "Session cookie: --cookie='PHPSESSID=abc123'",
            "--tamper":     "Bypass WAF: --tamper=space2comment,randomcase",
            "--os-shell":   "Get OS shell (requires FILE privilege on DB user)",
            "--file-read":  "Read server file: --file-read=/etc/passwd",
            "--tor":        "Route through Tor (slow but anonymous)",
            "-p":           "Specify parameter to test: -p id",
        },
        "read": [
            "Type: UNION query based means we can extract data with UNION SELECT",
            "Type: Boolean-based blind means true/false responses — slower data extraction",
            "Type: Time-based blind means inferring data by response delay — very slow",
            "available databases shows everything accessible with the DB user's permissions",
            "Check the dump for password hashes — run them through hashcat next",
        ],
        "next": ["hashcat (crack dumped hashes)", "database browsing (find useful tables)", "os-shell (if FILE priv)"],
        "caution": "--risk 3 and --level 5 can modify data and crash the application. Use carefully.",
    },

    "hydra": {
        "summary": "Network login brute forcer supporting 50+ protocols",
        "typical": "hydra -l admin -P ~/.err0rs/wordlists/rockyou.txt ssh://192.168.1.100 -t 4",
        "flags": {
            "-l":           "Single username: -l admin",
            "-L":           "Username list file: -L users.txt",
            "-p":           "Single password: -p password123",
            "-P":           "Password list: -P rockyou.txt",
            "-C":           "Colon-separated credentials: -C creds.txt (user:pass per line)",
            "-t":           "Parallel tasks per target (default 16, use 4 for SSH to avoid lockout)",
            "-s":           "Custom port: -s 2222",
            "-f":           "Stop on first valid credential",
            "-v":           "Verbose (show attempts)",
            "-V":           "Very verbose (every attempt — very noisy)",
            "-o":           "Save found credentials to file",
            "http-post-form": "Web login: 'http-post-form://target/login:user=^USER^&pass=^PASS^:Invalid'",
        },
        "read": [
            "[DATA] line shows config — verify target/protocol are correct before waiting",
            "[STATUS] shows speed — if very slow, reduce threads or check connectivity",
            "login: USER   password: PASS = valid credential found — stop and test it",
            "Connection refused = service isn't running on that port",
            "Max connections reached = reduce -t (thread count)",
        ],
        "next": ["ssh/rdp with found creds", "crackmapexec (test creds across network)", "evil-winrm (Windows WinRM)"],
        "caution": "Account lockout is real. Use -t 4 for SSH. Test with 1-2 passwords first on prod systems.",
    },

    "nuclei": {
        "summary": "Fast template-based vulnerability scanner with 6,000+ templates",
        "typical": "nuclei -u http://target.com -t http/ -severity critical,high",
        "flags": {
            "-u":           "Target URL",
            "-l":           "List of targets: -l targets.txt",
            "-t":           "Template directory/file: -t http/cves/",
            "-severity":    "Filter by severity: -severity critical,high,medium",
            "-tags":        "Filter by tags: -tags rce,sqli,xss,cve",
            "-o":           "Output file: -o nuclei_output.txt",
            "-j":           "JSON output (good for parsing)",
            "-rate-limit":  "Requests per second: -rate-limit 50",
            "-c":           "Concurrency: -c 25",
            "-update-templates": "Update template library to latest",
            "-stats":       "Show scan statistics",
            "-silent":      "Only output findings",
            "-debug":       "Debug mode (see HTTP requests)",
        },
        "read": [
            "[critical] [template-name] means a confirmed critical vuln — exploit this first",
            "[info] findings are not vulnerabilities — just enumeration (interesting files, tech stack)",
            "Template ID tells you exactly what was found — google it for details",
            "[matched] shows what specific string or condition triggered the match",
            "False positives happen — verify critical/high findings manually",
        ],
        "next": ["exploit the CVE (searchsploit/metasploit)", "manual verification (curl/burp)", "report generation"],
        "caution": "Some templates send active exploit payloads. Use -severity info,low for passive-only.",
    },

    "whatweb": {
        "summary": "Web fingerprinter — identifies CMS, frameworks, servers, JS libraries",
        "typical": "whatweb http://target.com -a 3",
        "flags": {
            "-a":           "Aggression level 1-4 (3 = active fingerprinting, 4 = very aggressive)",
            "-v":           "Verbose output — shows all identified components",
            "--log-brief":  "Brief summary output",
            "--log-json":   "JSON output for scripting",
            "-i":           "Input file with multiple targets",
            "--proxy":      "Route through Burp: --proxy 127.0.0.1:8080",
        },
        "read": [
            "WordPress[x.x.x] = exact version — search WPScan database for vulns",
            "Apache[version], nginx[version] = known CVEs for that exact version",
            "PHP[version] = older PHP versions have many RCEs",
            "jQuery[version] = older jQuery has XSS vulnerabilities",
            "Country/IP info tells you CDN vs direct server",
        ],
        "next": ["searchsploit (identified CMS/versions)", "wpscan (WordPress)", "nikto/nuclei (full scan)"],
        "caution": "Aggression level 4 will POST data and may leave traces in app logs.",
    },

    "enum4linux": {
        "summary": "SMB/NetBIOS enumeration — dumps users, shares, groups, password policy",
        "typical": "enum4linux -a 192.168.1.100",
        "flags": {
            "-a":   "All enumeration (combines -U -S -G -P -r -o -n -i)",
            "-U":   "Enumerate users via RPC",
            "-S":   "Enumerate shares",
            "-G":   "Enumerate groups",
            "-P":   "Get password policy (min length, lockout threshold)",
            "-r":   "RID cycling (brute force user IDs to discover accounts)",
            "-n":   "NetBIOS nameservice info",
            "-u":   "Authentication: -u admin -p password",
            "-o":   "OS information",
        },
        "read": [
            "user:[USERNAME] rid:[N] = discovered user account — add to your list",
            "Sharename = accessible share — mount it: smbclient //target/share",
            "NULL session allowed = can enumerate without credentials (misconfiguration)",
            "Minimum password length shows how strong to make brute force attempts",
            "DOMAIN\\Group shows structure — interesting for AD attacks",
        ],
        "next": ["crackmapexec (test creds on discovered users)", "smbclient (mount shares)", "hydra (brute user list)"],
        "caution": "RID cycling (-r) generates lots of traffic and may trigger IDS.",
    },

    "crackmapexec": {
        "summary": "Swiss army knife for Active Directory pentesting and lateral movement",
        "typical": "crackmapexec smb 192.168.1.0/24 -u admin -p password",
        "flags": {
            "smb":          "SMB protocol (most common for AD)",
            "ssh":          "SSH credential testing",
            "winrm":        "Windows Remote Management",
            "rdp":          "Remote Desktop testing",
            "-u":           "Username or file: -u users.txt",
            "-p":           "Password or file: -p passwords.txt",
            "-H":           "NTLM hash (pass-the-hash): -H aad3b435b51404eeaad3b435b51404ee:hash",
            "--shares":     "Enumerate accessible SMB shares",
            "--sam":        "Dump SAM database (local accounts)",
            "--lsa":        "Dump LSA secrets",
            "--ntds":       "Dump Active Directory database",
            "-x":           "Execute command: -x 'whoami'",
            "-X":           "Execute PowerShell: -X 'Get-Process'",
            "--local-auth": "Authenticate as local account (not domain)",
        },
        "read": [
            "[+] = success — credentials work on this host",
            "Pwn3d! = you have admin access — this is the big one",
            "[*] = informational",
            "[-] = failed",
            "STATUS_LOGON_FAILURE = wrong creds",
            "STATUS_ACCOUNT_LOCKED_OUT = account locked — stop immediately",
        ],
        "next": ["evil-winrm (if WinRM open)", "mimikatz (dump hashes)", "bloodhound (map the domain)"],
        "caution": "Password spraying with wrong timing will lock out accounts. Check password policy first.",
    },

    "ffuf": {
        "summary": "Fast web fuzzer — directory, parameter, header, and vhost discovery",
        "typical": "ffuf -u http://target.com/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302",
        "flags": {
            "-u":           "URL with FUZZ keyword as injection point",
            "-w":           "Wordlist path",
            "-mc":          "Match HTTP codes: -mc 200,301,302,403",
            "-fc":          "Filter HTTP codes: -fc 404,500",
            "-fs":          "Filter by response size: -fs 1234",
            "-fw":          "Filter by word count",
            "-t":           "Threads: -t 50",
            "-H":           "Add header: -H 'Cookie: session=abc'",
            "-d":           "POST data: -d 'user=FUZZ&pass=password'",
            "-X":           "HTTP method: -X POST",
            "-e":           "Extensions: -e .php,.html,.txt,.bak",
            "-o":           "Output file: -o results.json",
            "-of":          "Output format: json, csv, ecsv, md",
            "-recursion":   "Recurse into found directories",
        },
        "read": [
            "High response size differences usually indicate real content",
            "Filter noise first: run once, note the common response size, add -fs to hide it",
            "403s are interesting — directory exists but is blocked",
            "FUZZ can go anywhere in the URL — parameters, headers, paths",
            "Use multiple wordlists by specifying -w multiple times with :FUZZ labels",
        ],
        "next": ["curl/browser (inspect findings)", "sqlmap (if parameter fuzzing found injection)"],
        "caution": "High thread counts can DoS unstable applications. Start at -t 25.",
    },

    "metasploit": {
        "summary": "Exploitation framework — 2000+ modules covering exploit, post, auxiliary",
        "typical": "msfconsole -q",
        "flags": {
            "search":       "search ms17-010 — find modules by CVE, name, or platform",
            "use":          "use exploit/windows/smb/ms17_010_eternalblue",
            "info":         "info — show module description, options, and targets",
            "show options": "show required and optional parameters",
            "set RHOSTS":   "Target IP: set RHOSTS 192.168.1.100",
            "set LHOST":    "Your IP for reverse shell: set LHOST 192.168.1.50",
            "set LPORT":    "Listening port: set LPORT 4444",
            "set PAYLOAD":  "Payload: set PAYLOAD windows/x64/meterpreter/reverse_tcp",
            "run / exploit":"Execute the module",
            "sessions":     "List active Meterpreter sessions",
            "sessions -i 1":"Interact with session 1",
            "background":   "Background current session (Ctrl+Z)",
            "getsystem":    "Attempt privilege escalation to SYSTEM",
            "hashdump":     "Dump password hashes from SAM",
            "run post/":    "Post-exploitation modules: run post/multi/recon/local_exploit_suggester",
        },
        "read": [
            "Meterpreter session opened = successful exploit — you have a shell",
            "No session created = exploit failed — check RHOSTS, LHOST, and payload",
            "PAYLOAD => shows what shell will be sent — reverse_tcp = target calls back to you",
            "Migration moves your shell into a stable process (migrate to explorer.exe)",
            "Always set LHOST to your actual reachable IP, not localhost",
        ],
        "next": ["hashdump", "getsystem", "run post/multi/recon/local_exploit_suggester", "persistence"],
        "caution": "Exploits can crash services and systems. Test on snapshots. Log every action.",
    },

    "bloodhound": {
        "summary": "Active Directory attack path mapper — visualizes paths to Domain Admin",
        "typical": "bloodhound-python -u user -p pass -d domain.local -c All --zip",
        "flags": {
            "-u":       "Domain username",
            "-p":       "Password",
            "-d":       "Domain name: domain.local",
            "-c All":   "Collect everything (Users, Groups, Sessions, ACLs, Trusts)",
            "--zip":    "Create zip for BloodHound import",
            "--dns-tcp":"Use TCP for DNS (if UDP fails)",
            "-ns":      "Name server (DC IP): -ns 192.168.1.10",
        },
        "read": [
            "Shortest path to Domain Admins = the attack path you want",
            "GenericAll/GenericWrite = full control over that object — huge privilege",
            "WriteDACL = can modify permissions — abuse to grant yourself GenericAll",
            "DCSync = right to pull all password hashes from the DC",
            "Kerberoastable accounts = extract their hashes offline without admin",
        ],
        "next": ["impacket-GetUserSPNs (Kerberoast)", "impacket-secretsdump (DCSync)", "mimikatz (local hashes)"],
        "caution": "SharpHound on-domain is noisier than bloodhound-python off-domain.",
    },

    "hashcat": {
        "summary": "GPU-accelerated password hash cracker — fastest on the planet",
        "typical": "hashcat -m 1000 -a 0 hashes.txt ~/.err0rs/wordlists/rockyou.txt",
        "flags": {
            "-m":       "Hash type: 1000=NTLM, 0=MD5, 1800=SHA512crypt, 13100=Kerberoast, 22000=WPA2",
            "-a":       "Attack mode: 0=dictionary, 3=brute force, 6=hybrid wordlist+mask",
            "-r":       "Rules file: -r /usr/share/hashcat/rules/best64.rule",
            "--show":   "Show cracked hashes from previous session",
            "--session": "Name session to resume: --session mysession",
            "-o":       "Output cracked to file: -o cracked.txt",
            "--potfile-disable": "Don't use potfile (start fresh)",
            "?u":       "Mask: uppercase letter",
            "?l":       "Mask: lowercase letter",
            "?d":       "Mask: digit",
            "?s":       "Mask: special character",
        },
        "read": [
            "Recovered = cracked — check hashcat --show for the plaintext",
            "Exhausted = wordlist finished with no crack — try rules or different wordlist",
            "Speed (H/s) shows how fast — GPU >>> CPU for this",
            "Status: Running = working, ETA shows estimated finish",
            "Use -a 0 -r rules/best64.rule before brute force — catches 80% faster",
        ],
        "next": ["test cracked password against target", "credential stuffing (same pass other services)"],
        "caution": "Without a GPU, hashcat is very slow. Use john the ripper as CPU alternative.",
    },

    "responder": {
        "summary": "LLMNR/NBT-NS poisoner — captures NTLM hashes on the local network",
        "typical": "responder -I eth0 -wF",
        "flags": {
            "-I":   "Interface: -I eth0",
            "-w":   "Enable WPAD rogue proxy server",
            "-F":   "Force NTLM authentication in WPAD responses",
            "-r":   "Enable rogue DNS",
            "-d":   "Enable DHCP replies",
            "-A":   "Analyze mode (don't poison — just observe)",
            "--lm": "Downgrade to LM hashes (older Windows)",
        },
        "read": [
            "[*] = informational event",
            "[+] Poisoned answer = machine asked for something, you replied — they'll send hashes",
            "Hash captured! shows the NTLMv2 hash — crack it with hashcat -m 5600",
            "NTLMv2 is strong but crackable with rockyou if password is weak",
            "Username and client IP tell you who the hash belongs to",
        ],
        "next": ["hashcat -m 5600 (crack NTLMv2)", "ntlmrelayx (relay instead of cracking)", "crackmapexec"],
        "caution": "LLMNR poisoning will disrupt legitimate network traffic. LAN attacks only with permission.",
    },

    "linpeas": {
        "summary": "Linux privilege escalation auditor — finds every path to root",
        "typical": "curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh",
        "flags": {
            "-a":   "All checks (more thorough, noisier)",
            "-s":   "Silent (less output — only critical findings)",
            "-q":   "Quick scan",
            "-o":   "Output to file",
        },
        "read": [
            "Red/Yellow highlight = critical finding — check this first",
            "SUID binaries = programs that run as root — check GTFOBins.github.io for exploits",
            "Writable paths in PATH = can hijack commands run by root scripts",
            "Sudo -l output = what you can run as sudo — huge if (ALL) NOPASSWD",
            "Interesting files in /etc = check /etc/passwd for hashes, /etc/shadow if readable",
        ],
        "next": ["gtfobins exploit (SUID)", "sudo exploitation", "CVE search (found kernel version)"],
        "caution": "LinPEAS creates lots of log entries — assume your presence is being recorded.",
    },

    "netcat": {
        "summary": "TCP/UDP Swiss army knife — listeners, port checks, file transfer, pivoting",
        "typical": "nc -lvnp 4444   # listen for reverse shell",
        "flags": {
            "-l":   "Listen mode",
            "-v":   "Verbose",
            "-n":   "No DNS resolution (faster)",
            "-p":   "Port: -p 4444",
            "-e":   "Execute program on connect: -e /bin/bash (some nc versions)",
            "-u":   "UDP mode",
            "-z":   "Port scan mode: nc -z target 80-443",
            "-w":   "Connection timeout: -w 3",
        },
        "read": [
            "Listening on [0.0.0.0] 4444 = ready for reverse shell",
            "connect to [...] = connection received — you have a shell",
            "$ or # prompt = shell working — # means root",
            "No response from -z scan = port closed",
        ],
        "next": ["python pty (upgrade shell)", "socat (encrypted shell)", "chisel (tunneling)"],
        "caution": "nc shells are fragile and unencrypted. Upgrade to a pty immediately.",
    },

    # ══════════════════════════════════════════════════════════════
    # CONCEPTS — CIS CONTROLS
    # ══════════════════════════════════════════════════════════════

    "cis": {
        "summary": "CIS Controls v8 — 18 controls that block 85% of common attacks",
        "typical": "Implement in order: Controls 1-6 first (IG1), then expand",
        "flags": {
            "CIS 1":   "Inventory of Enterprise Assets — know what's on your network",
            "CIS 2":   "Inventory of Software Assets — know what's running",
            "CIS 3":   "Data Protection — classify and protect sensitive data",
            "CIS 4":   "Secure Config — harden everything to CIS Benchmarks",
            "CIS 5":   "Account Management — control who has accounts and access",
            "CIS 6":   "Access Control — enforce least privilege",
            "CIS 7":   "Continuous Vulnerability Management — patch within 30 days",
            "CIS 8":   "Audit Log Management — log everything, retain 90+ days",
            "CIS 9":   "Email/Web Browser Protections — SPF/DKIM/DMARC, web filtering",
            "CIS 10":  "Malware Defenses — AV/EDR with behavior detection",
            "CIS 11":  "Data Recovery — encrypted backups, test restoration",
            "CIS 12":  "Network Infrastructure Management — firewall rules, segmentation",
            "CIS 13":  "Network Monitoring — IDS/IPS, NetFlow analysis",
            "CIS 14":  "Security Awareness Training — phishing sims, annual training",
            "CIS 15":  "Service Provider Management — vendor risk assessments",
            "CIS 16":  "Application Security — SDLC, SAST/DAST, dependency scanning",
            "CIS 17":  "Incident Response — IR plan, tabletop exercises",
            "CIS 18":  "Penetration Testing — annual tests, remediation tracking",
        },
        "read": [
            "IG1 (Controls 1-6) = essential hygiene — any org should have these",
            "IG2 (Controls 1-9) = security-mature orgs — medium risk tolerance",
            "IG3 (All 18) = high-risk environments — finance, healthcare, government",
            "Controls 1 and 2 are foundational — you can't protect what you don't know exists",
            "CIS 7 (patch management) blocks the most breaches in practice",
        ],
        "next": ["CIS Benchmarks (system hardening)", "NIST CSF (framework mapping)", "compliance report"],
        "caution": "CIS Controls are a starting point, not a guarantee. Threat model your specific environment.",
    },

    "owasp": {
        "summary": "OWASP Top 10 2021 — the 10 most critical web application security risks",
        "typical": "Map every finding to an OWASP category for your report",
        "flags": {
            "A01 Broken Access Control":     "Most critical — users accessing other users' data",
            "A02 Cryptographic Failures":    "Sensitive data in cleartext, weak ciphers, no TLS",
            "A03 Injection":                 "SQLi, OS command injection, LDAP injection, XPath",
            "A04 Insecure Design":           "Missing threat models, no security requirements",
            "A05 Security Misconfiguration": "Default creds, cloud misconfigs, verbose errors",
            "A06 Vulnerable Components":     "Outdated libraries with known CVEs",
            "A07 Auth Failures":             "Weak passwords, no MFA, credential stuffing",
            "A08 Software Integrity":        "Unsigned code, no SCA, supply chain attacks",
            "A09 Logging Failures":          "No audit logs, not alerting on attacks",
            "A10 SSRF":                      "Server fetches attacker-controlled URLs",
        },
        "read": [
            "A01 Broken Access Control causes the most real breaches — test EVERY endpoint",
            "A03 Injection (SQLi) is still everywhere despite being 30 years old",
            "A05 Misconfigs are easy wins for attackers and easy fixes for defenders",
            "A07 Auth Failures = almost always weak or reused passwords",
            "SSRF (A10) can reach internal APIs and cloud metadata endpoints (169.254.169.254)",
        ],
        "next": ["burp suite (manual web testing)", "nuclei owasp templates", "zap (automated scan)"],
        "caution": "OWASP is web-focused. Don't forget network, physical, and social engineering risks.",
    },

    "mitre": {
        "summary": "MITRE ATT&CK — structured knowledge base of attacker TTPs (Tactics, Techniques, Procedures)",
        "typical": "Map every attack technique you use to an ATT&CK ID for your report",
        "flags": {
            "TA0043 Reconnaissance":    "OSINT, port scanning, phishing for info",
            "TA0042 Resource Dev":      "Setting up infrastructure, malware, credentials",
            "TA0001 Initial Access":    "Phishing, exploit public-facing app, valid accounts",
            "TA0002 Execution":         "Running code: PowerShell, cmd, WMI, scripts",
            "TA0003 Persistence":       "Maintaining access: registry run keys, scheduled tasks, backdoors",
            "TA0004 Priv Escalation":   "Becoming SYSTEM/root: SUID, sudo, token impersonation",
            "TA0005 Defense Evasion":   "Hiding: obfuscation, AMSI bypass, log clearing",
            "TA0006 Credential Access": "Dumping: Mimikatz, SAM, LSASS, Kerberoasting",
            "TA0007 Discovery":         "Mapping the network: nmap, BloodHound, net commands",
            "TA0008 Lateral Movement":  "Moving host to host: Pass-the-Hash, RDP, PsExec",
            "TA0009 Collection":        "Staging data to exfiltrate",
            "TA0010 Exfiltration":      "Getting data out: DNS, HTTPS, cloud storage",
            "TA0011 C2":               "Command and Control: Cobalt Strike, Empire, Metasploit",
            "TA0040 Impact":           "Ransomware, data destruction, defacement",
        },
        "read": [
            "Every technique has sub-techniques — be specific in reports (T1059.001 = PowerShell)",
            "Use ATT&CK Navigator to map your engagement visually (free web tool)",
            "Mitigations section shows exactly what defenses block each technique",
            "Detections section shows what logs to collect to catch the technique",
            "Defenders use ATT&CK to find gaps — red teamers use it to find bypasses",
        ],
        "next": ["ATT&CK Navigator (visualization)", "MITRE D3FEND (defensive mapping)", "reporting"],
        "caution": "ATT&CK describes observed behaviors, not a complete list. Novel techniques won't be in it.",
    },

    "kill-chain": {
        "summary": "Cyber Kill Chain — 7 phases of every targeted attack (Lockheed Martin)",
        "typical": "Map your pentest phases to Kill Chain stages for professional reporting",
        "flags": {
            "1 Reconnaissance":  "OSINT, shodan, LinkedIn — learning about the target",
            "2 Weaponization":   "Building payloads, exploits, phishing emails",
            "3 Delivery":        "Getting the payload to the target: email, USB, exploit",
            "4 Exploitation":    "Triggering the vulnerability — code runs on target",
            "5 Installation":    "Persistence — making sure you stay after reboot",
            "6 C2":             "Establishing command and control channel",
            "7 Actions on Obj": "The actual goal: data theft, ransomware, espionage",
        },
        "read": [
            "Breaking the chain at ANY phase = attack failed (defenders use this model)",
            "Delivery is the most commonly defended phase — email filters, web proxies",
            "Most orgs are weakest at Exploitation and Installation phases",
            "Defenders aim to detect by phase 3 at the latest — phase 6 is too late",
            "Every phase leaves artifacts — logs, process spawns, network connections",
        ],
        "next": ["MITRE ATT&CK (more granular TTPs)", "diamond model (threat intel)", "IR planning"],
        "caution": "Kill Chain is linear — real attacks aren't. Use ATT&CK for non-linear mapping.",
    },

    "cia": {
        "summary": "CIA Triad — Confidentiality, Integrity, Availability — the foundation of security",
        "typical": "Frame every security decision around: does this protect C, I, or A?",
        "flags": {
            "Confidentiality": "Only authorized parties can access data (encryption, access controls)",
            "Integrity":       "Data hasn't been tampered with (hashing, digital signatures, audit logs)",
            "Availability":    "Systems are accessible when needed (redundancy, backups, DDoS mitigation)",
        },
        "read": [
            "Most attacks target Confidentiality (data theft) or Availability (ransomware, DDoS)",
            "Integrity attacks are sneakiest — you don't know your data was changed",
            "Security controls often trade against each other: more auth = less availability",
            "Pentests test Confidentiality and Integrity primarily",
            "CIA Triad maps to NIST CSF: Protect=C/I, Detect/Respond=all, Recover=A",
        ],
        "next": ["risk assessment", "threat modeling", "control mapping to framework"],
        "caution": "Some add a 4th: Non-repudiation (can't deny you did something). Check your scope.",
    },

    "incident-response": {
        "summary": "IR Phases (NIST SP 800-61) — Preparation, Detection, Containment, Eradication, Recovery, Lessons Learned",
        "typical": "Run a tabletop exercise annually covering all 6 phases for your top 3 threat scenarios",
        "flags": {
            "Phase 1 Preparation":    "IR plan, contact lists, runbooks, SIEM configured, EDR deployed",
            "Phase 2 Detection":      "Alert fires — is this a true positive? Triage and classify severity",
            "Phase 3 Containment":    "Stop the bleeding — isolate affected systems without destroying evidence",
            "Phase 4 Eradication":    "Remove the attacker — delete malware, close backdoors, patch the vuln",
            "Phase 5 Recovery":       "Restore from clean backups, verify integrity, monitor closely",
            "Phase 6 Lessons Learned":"Post-incident report — what happened, timeline, gaps, improvements",
        },
        "read": [
            "Containment before eradication — make sure you've found everything first",
            "Preserve evidence before wiping — disk image, memory dump, log collection",
            "Notify stakeholders early — legal, PR, and execs need time to prepare",
            "Treat phase 6 as critical — same vulnerability hitting you twice = embarrassing",
            "Chain of custody matters if legal action is possible — document everything",
        ],
        "next": ["forensics (memory/disk imaging)", "threat hunting (find lateral movement)", "lessons learned report"],
        "caution": "Never eradicate before you have full scope — attacker may have 10 more backdoors.",
    },

    "threat-modeling": {
        "summary": "Structured process to identify what can go wrong before you build or test",
        "typical": "STRIDE model: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation of Privilege",
        "flags": {
            "Spoofing":              "Can an attacker fake identity? (phishing, ARP spoofing, JWT forgery)",
            "Tampering":             "Can data be modified? (MITM, SQLi, file write)",
            "Repudiation":           "Can actions be denied? (no logs, log deletion)",
            "Information Disclosure":"Can private data be exposed? (verbose errors, IDOR, SQLi)",
            "Denial of Service":     "Can the system be made unavailable? (DDoS, resource exhaustion)",
            "Elevation of Privilege":"Can low-priv become high-priv? (SUID, sudo misconfig, token theft)",
        },
        "read": [
            "Start with data flow diagrams — follow data from user to storage and back",
            "Trust boundaries are where attacks happen — draw them explicitly",
            "STRIDE maps perfectly to MITRE ATT&CK techniques",
            "Threat model before you build — not after the breach",
            "PASTA and VAST are more advanced models for mature security programs",
        ],
        "next": ["risk register", "penetration test scoping", "security requirements in SDLC"],
        "caution": "Threat models go stale — update when architecture changes significantly.",
    },

    # ════════════════════════════════════════════════════════════════════
    #  ENGAGEMENT THEORY — the full lifecycle, beginning to end
    #  These teach the METHODOLOGY a professional follows, not a tool.
    #  Ordered: lifecycle → scoping → target-id → recon-theory → reporting
    # ════════════════════════════════════════════════════════════════════
    "engagement-lifecycle": {
        "summary": "The 7 phases of a professional security engagement, start to finish",
        "typical": "Pre-Engagement → Recon → Scanning/Enum → Exploitation → Post-Ex → Reporting → Remediation Retest",
        "flags": {
            "1. Pre-Engagement":   "Scope, rules of engagement, authorization, contracts. NO testing happens yet.",
            "2. Reconnaissance":   "OSINT + footprinting. Mostly passive. Build the target picture before touching it.",
            "3. Scanning/Enum":    "Active discovery — ports, services, versions, users, shares. First noisy phase.",
            "4. Exploitation":     "Turn a vulnerability into access. Where detection risk spikes.",
            "5. Post-Exploitation":"Privesc, lateral movement, persistence, data access. Prove business impact.",
            "6. Reporting":        "The actual deliverable. Findings, evidence, risk ratings, remediation steps.",
            "7. Remediation Retest":"Verify the client fixed what you found. Closes the loop.",
        },
        "read": [
            "Most beginners rush to phase 4 — pros spend the most time in 1, 2, and 6",
            "The report is what the client PAYS for — the hacking is just how you fill it",
            "Each phase feeds the next: recon scopes scanning, scanning scopes exploitation",
            "You can loop back — post-ex findings often trigger more recon on newly-found hosts",
            "PTES and the OSSTMM are the formal methodology standards worth reading",
        ],
        "next": ["scoping", "target-identification", "recon-theory", "reporting"],
        "caution": "Skipping phase 1 (authorization) isn't a methodology shortcut — it's a federal crime (CFAA).",
    },

    "scoping": {
        "summary": "Defining WHAT you're allowed to test, HOW, and WHEN — the contract that makes it legal",
        "typical": "Signed authorization + IP/domain scope list + ROE + testing window + emergency contacts",
        "flags": {
            "Authorization":     "Written permission from someone who OWNS the assets. Verbal isn't enough.",
            "Scope (in/out)":    "Explicit list of IPs, domains, apps that ARE and ARE NOT fair game.",
            "Rules of Engagement":"Allowed techniques. Is social engineering ok? DoS testing? Physical?",
            "Testing window":    "When you may test. Business hours? After-hours? Blackout dates?",
            "Data handling":     "What you may access, exfil, store, and how you destroy it after.",
            "Emergency contact": "Who to call if you break something or find an active breach.",
            "Get-out-of-jail":   "A signed authorization letter you carry — proves you're not a criminal.",
        },
        "read": [
            "Scope creep is the #1 way pentesters get in legal trouble — stay inside the lines",
            "If you find a vuln that leads OUT of scope, STOP and ask before following it",
            "Cloud assets need the PROVIDER's permission too (AWS/Azure have their own rules)",
            "'Out of scope' findings can still be reported as observations — just don't test them",
            "The scope document protects YOU as much as the client",
        ],
        "next": ["target-identification", "engagement-lifecycle", "recon-theory"],
        "caution": "No signed authorization = no testing. Ever. This is the line between pentester and criminal.",
    },

    "target-identification": {
        "summary": "Going from 'a company name' to a concrete, in-scope list of assets to test",
        "typical": "Company → domains → subdomains → IP ranges (ASN) → live hosts → services → attack surface",
        "flags": {
            "Seed data":      "Start from what scope gives you: a domain, a company name, an IP block.",
            "Domain expansion":"Find all domains the org owns (whois, reverse-whois, cert transparency).",
            "Subdomain enum": "subfinder/amass turn one domain into dozens of subdomains.",
            "ASN / IP ranges":"Find the org's owned IP blocks via ASN lookup (bgp.he.net, whois).",
            "Live host detection":"Which of those IPs/hosts actually respond? (the in-scope ones only)",
            "Attack surface mapping":"Catalog every service, app, and entry point you found.",
            "Asset validation":"Confirm each asset is IN SCOPE before you touch it actively.",
        },
        "read": [
            "Cert transparency logs (crt.sh) are gold — they leak subdomains for free, passively",
            "An ASN lookup tells you every IP block a company owns — huge for scoping",
            "Acquisitions matter: BigCorp may own SmallCo's domains too — check whois history",
            "Shadow IT (forgotten dev/staging boxes) is where the easy wins usually hide",
            "Always cross-check found assets against your authorized scope before scanning",
        ],
        "next": ["subfinder", "amass", "theHarvester", "recon-theory"],
        "caution": "Finding an asset doesn't mean it's in scope. Validate ownership + authorization before active testing.",
    },

    "recon-theory": {
        "summary": "The discipline of gathering intel — passive vs active, and why you always start passive",
        "typical": "Passive OSINT (no target contact) → Semi-passive → Active recon (direct contact, logged)",
        "flags": {
            "Passive recon":  "Zero packets to the target. Public data: search engines, certs, DNS, social media. Undetectable.",
            "Semi-passive":   "Light, normal-looking traffic: visiting their website, public DNS lookups. Blends in.",
            "Active recon":   "Direct probing: port scans, service enum. Effective but LOGGED on the target side.",
            "Attribution":    "Can the target trace recon back to you? Passive = no. Active = yes, unless proxied.",
            "OSINT-first":    "Exhaust passive sources BEFORE going active — you often won't need to make noise.",
            "Footprinting":   "Building the complete external picture: people, tech, infra, exposure.",
        },
        "read": [
            "Every active packet is potential evidence — passive recon leaves none",
            "A good OSINT phase means you arrive at active recon already knowing the answers",
            "Email formats + employee names (from LinkedIn) feed password spraying later",
            "Leaked credentials (HaveIBeenPwned, dumps) are passive AND devastating",
            "Tech stack fingerprints (whatweb, builtwith) tell you what exploits to prep",
        ],
        "next": ["subfinder", "theHarvester", "sherlock", "target-identification"],
        "caution": "Passive recon is undetectable BUT still bound by scope and privacy law. Public ≠ permission to harass.",
    },

    "reporting": {
        "summary": "Turning findings into the deliverable the client actually pays for",
        "typical": "Executive summary → methodology → findings (with evidence + risk) → remediation → retest plan",
        "flags": {
            "Executive summary":  "1 page for leadership: what you found, the business risk, what to do. No jargon.",
            "Methodology":        "What you tested and how — proves thoroughness and scope adherence.",
            "Findings":           "Each: title, severity, affected assets, evidence (screenshots), reproduction steps.",
            "Risk rating":        "CVSS score + business context. A 'high' on a dev box may be a 'low' in practice.",
            "Remediation":        "Specific, actionable fixes. Not 'patch it' — exactly WHAT and HOW.",
            "Evidence":           "Screenshots, request/response pairs, command output. Reproducible proof.",
            "Retest plan":        "How you'll verify the fix worked. Closes the engagement loop.",
        },
        "read": [
            "The report outlives the engagement — it's the only artifact the client keeps",
            "Map every finding to CIA impact and a CVSS score for defensible severity",
            "Reproduction steps must be exact — a dev has to be able to follow them",
            "Lead with business risk, not technical detail — execs fund fixes, not CVEs",
            "ERR0RS has a Professional Reporter — type 'report' to generate one from your session",
        ],
        "next": ["cvss scoring", "engagement-lifecycle", "remediation retest"],
        "caution": "A finding with no evidence is an opinion. Always capture reproducible proof as you go.",
    },

    # ════════════════════════════════════════════════════════════════════
    #  OSINT TOOLS — passive-first external footprinting
    #  Domain/infra: subfinder, amass, dnsrecon, theHarvester
    #  People/identity: sherlock, holehe, recon-ng, spiderfoot
    # ════════════════════════════════════════════════════════════════════
    "subfinder": {
        "summary": "Fast passive subdomain discovery — queries 30+ public sources, never touches the target",
        "typical": "subfinder -d example.com -all -silent",
        "flags": {
            "-d":      "Target domain to enumerate subdomains for",
            "-all":    "Use ALL sources (slower, more thorough) vs the fast default set",
            "-silent": "Only print subdomains, no banner — clean for piping to other tools",
            "-o":      "Output to file: -o subs.txt",
            "-recursive":"Recursively find subdomains of discovered subdomains",
            "-dL":     "Read a LIST of domains from a file instead of one -d",
            "-cs":     "Include the source that found each subdomain (provenance)",
        },
        "read": [
            "Every result comes from PUBLIC data (cert logs, passive DNS) — the target sees nothing",
            "Pipe straight into httpx or nmap: subfinder -d x.com -silent | httpx",
            "More sources = more results but slower — start with default, add -all if thin",
            "Cross-check with amass for coverage neither tool has alone",
            "Configure API keys (~/.config/subfinder/) to unlock premium sources",
        ],
        "next": ["amass", "httpx", "nmap", "whatweb"],
        "caution": "Subdomains found ≠ in scope. Validate each against authorization before active scanning.",
    },

    "amass": {
        "summary": "Deep attack-surface mapping — subdomains, ASNs, and infra relationships (passive or active)",
        "typical": "amass enum -passive -d example.com",
        "flags": {
            "enum":      "The enumeration subcommand (amass has intel/enum/viz/db modes)",
            "-passive":  "Passive only — no direct target contact, undetectable",
            "-active":   "Active — does DNS resolution + cert grabbing (touches target, more accurate)",
            "-d":        "Target domain",
            "-brute":    "Brute-force subdomains with a wordlist (active, noisier)",
            "-o":        "Output file",
            "-df":       "Domains-from-file for multi-domain enum",
            "intel":     "amass intel -org 'Company' finds domains/ASNs an org owns",
        },
        "read": [
            "amass intel -org 'Acme' maps every domain + IP block a company owns — huge for scoping",
            "-passive is safe for any phase; -active and -brute are louder and touch the target",
            "Deeper than subfinder but slower — use both, merge results",
            "amass viz generates a relationship graph of the discovered infrastructure",
            "Results persist in a local DB — amass db lets you query past enums",
        ],
        "next": ["subfinder", "target-identification", "nmap", "httpx"],
        "caution": "-active / -brute send packets to the target. Confirm scope before using them.",
    },

    "dnsrecon": {
        "summary": "DNS enumeration — records, zone transfers, subdomain brute, reverse lookups",
        "typical": "dnsrecon -d example.com",
        "flags": {
            "-d":      "Target domain",
            "-t":      "Enumeration type: std, axfr (zone transfer), brt (brute), rvl (reverse)",
            "-t axfr": "Attempt zone transfer — a misconfig that dumps the ENTIRE DNS zone",
            "-t brt":  "Brute-force subdomains with a dictionary (-D wordlist.txt)",
            "-D":      "Dictionary file for brute-force mode",
            "-r":      "Reverse lookup over an IP range: -r 10.0.0.0/24",
            "-n":      "Use a specific name server",
        },
        "read": [
            "A successful zone transfer (axfr) is a jackpot — the whole DNS map, instantly",
            "std enumeration (A, MX, NS, TXT, SOA) is light and quick — start there",
            "SPF/DMARC TXT records reveal mail infra + sometimes third-party services",
            "Reverse lookups on a found IP range surface neighboring hosts",
            "Zone transfers rarely work on modern DNS but ALWAYS worth a try — costs nothing",
        ],
        "next": ["subfinder", "amass", "theHarvester", "nmap"],
        "caution": "DNS queries to the target's own name servers are semi-active and logged there.",
    },

    "theharvester": {
        "summary": "Harvests emails, names, subdomains, and hosts from public search engines and data sources",
        "typical": "theHarvester -d example.com -b all",
        "flags": {
            "-d":   "Target domain or company name",
            "-b":   "Data source: all, bing, google, linkedin, crtsh, hunter, etc.",
            "-b all":"Query every available source (broadest sweep)",
            "-l":   "Limit number of results per source",
            "-f":   "Save results to an HTML/XML report file",
            "-s":   "Use Shodan for discovered hosts (needs API key)",
            "-r":   "Take DNS reverse lookups on the found range",
        },
        "read": [
            "Emails reveal the org's address FORMAT (first.last@, flast@) — feeds password spraying",
            "Employee names from LinkedIn source build your target-user list",
            "crtsh source pulls subdomains from cert transparency — overlaps subfinder",
            "Different sources find different data — -b all then dedupe is the move",
            "Found emails → check HaveIBeenPwned for breach exposure (still passive)",
        ],
        "next": ["sherlock", "holehe", "recon-theory", "subfinder"],
        "caution": "Harvested PII (names, emails) is bound by privacy law. Use only for authorized engagements.",
    },

    "sherlock": {
        "summary": "Hunts a username across 400+ social networks and sites — maps a person's online presence",
        "typical": "sherlock johndoe",
        "flags": {
            "username":  "One or more usernames to search (space-separated)",
            "--timeout": "Seconds to wait per site (default 60 — lower it to go faster)",
            "--site":    "Check only specific sites: --site GitHub --site Twitter",
            "--csv":     "Export results to CSV",
            "--folderoutput":"Save per-username result files to a folder",
            "--nsfw":    "Include adult sites in the search",
        },
        "read": [
            "A username reused across sites links a person's accounts together — pivot points",
            "Found profiles → read bios/posts for more seed data (other handles, employer, location)",
            "False positives happen — always manually verify a hit before relying on it",
            "Pair with the email format from theHarvester to confirm identity overlaps",
            "Queries hit the SITES, not your target's infra — target sees nothing",
        ],
        "next": ["holehe", "theHarvester", "recon-theory"],
        "caution": "Profiling real people is privacy-sensitive. Stay within engagement scope — public ≠ permission to stalk.",
    },

    "holehe": {
        "summary": "Checks if an email is registered on 120+ sites — without alerting the target",
        "typical": "holehe target@example.com",
        "flags": {
            "email":      "The email address to check across sites",
            "--only-used":"Show only sites where the email IS registered (cleaner output)",
            "--no-color": "Plain output for piping/parsing",
            "--csv":      "Export to CSV",
            "-T":         "Timeout per request",
        },
        "read": [
            "Tells you WHERE a person has accounts (Twitter, Spotify, Adobe...) — expands the attack surface",
            "Uses password-reset / registration flows that DON'T notify the account owner",
            "Combine with sherlock: holehe finds accounts by email, sherlock by username",
            "Registered-account list informs phishing pretext + credential-stuffing targets",
            "Some sites rate-limit — spread checks out if you're doing many emails",
        ],
        "next": ["sherlock", "theHarvester", "recon-theory"],
        "caution": "Enumerating someone's accounts is sensitive recon. Authorized engagements only — respect privacy law.",
    },

    "recon-ng": {
        "summary": "Modular OSINT framework with a Metasploit-style console — automates multi-source recon",
        "typical": "recon-ng → marketplace install all → modules load recon/domains-hosts/...",
        "flags": {
            "marketplace search":"Find available modules (recon, discovery, reporting)",
            "marketplace install":"Install a module or 'all' to grab everything",
            "modules load":      "Load a module: modules load recon/domains-hosts/hackertarget",
            "options set SOURCE":"Set the input (e.g. the target domain) for the loaded module",
            "run":               "Execute the loaded module",
            "show hosts":        "Display results stored in the workspace database",
            "workspaces create": "Isolate each engagement in its own workspace + database",
        },
        "read": [
            "Everything is stored in a per-workspace DB — results from one module feed the next",
            "It's a FRAMEWORK: chain modules (domains→hosts→ports→contacts) into a pipeline",
            "Many modules need API keys (keys add shodan_api ...) for full power",
            "Reporting modules export polished HTML/CSV straight from the workspace",
            "Think of it as Metasploit for recon — same console muscle memory",
        ],
        "next": ["spiderfoot", "theHarvester", "amass", "target-identification"],
        "caution": "Some modules do ACTIVE lookups (DNS, port checks). Know which before running against a scoped target.",
    },

    "spiderfoot": {
        "summary": "Automated OSINT engine — point it at a target and it correlates 200+ data sources for you",
        "typical": "spiderfoot -l 127.0.0.1:5001  (then drive the web UI)",
        "flags": {
            "-l":      "Launch the web UI on host:port (then use the browser)",
            "-s":      "Scan target (CLI mode): -s example.com",
            "-t":      "Restrict to specific data types: -t EMAILADDR,IP_ADDRESS",
            "-m":      "Use only specific modules",
            "-q":      "Quiet — only output data, no status",
            "-o":      "Output format: tab, csv, json",
        },
        "read": [
            "Give it a domain/email/IP/name and it auto-pivots across sources building a graph",
            "Scan modes: Passive (safe), Investigate, or Footprint (some active) — pick deliberately",
            "The web UI visualizes relationships — great for spotting non-obvious connections",
            "Correlations surface what manual recon misses (shared infra, leaked data, exposed services)",
            "Heavier than single tools — use when you want breadth without manual chaining",
        ],
        "next": ["recon-ng", "amass", "theHarvester", "target-identification"],
        "caution": "Footprint/Investigate modes make active connections. Use Passive mode to stay undetectable.",
    },

}


def lookup(topic: str) -> dict | None:
    """Return lesson dict for a tool name, or None if unknown."""
    if not topic:
        return None
    key = topic.lower().strip().replace(" ", "-").replace("_", "-")
    # Direct match
    if key in LESSONS:
        return LESSONS[key]
    # Partial match
    for k in LESSONS:
        if key in k or k in key:
            return LESSONS[k]
    return None


def list_topics() -> list:
    """Return all available lesson topics."""
    return sorted(LESSONS.keys())


def format_lesson(topic: str) -> str:
    """Produce a pretty multi-line lesson block for the live terminal."""
    lesson = lookup(topic)
    if not lesson:
        topics = ", ".join(sorted(LESSONS.keys()))
        return f"📖 No lesson for '{topic}'.\n\nAvailable: {topics}"

    lines = []
    lines.append(f"\n{'═'*62}")
    lines.append(f"📖 {topic.upper()} — {lesson['summary']}")
    lines.append(f"{'─'*62}")
    lines.append(f"\n  Typical use:  {lesson['typical']}\n")
    lines.append("  FLAGS / OPTIONS:")
    for flag, desc in lesson['flags'].items():
        lines.append(f"    {flag:<22} {desc}")
    lines.append("\n  READING THE OUTPUT:")
    for r in lesson['read']:
        lines.append(f"    • {r}")
    lines.append(f"\n  LOGICAL NEXT STEPS:  {', '.join(lesson['next'])}")
    if lesson.get('caution'):
        lines.append(f"\n  ⚠️  {lesson['caution']}")
    lines.append(f"{'═'*62}")

    # ── Append SOC-mentor coaching layer if available for this topic ─────────
    # The SOC mentor block adds noise-level rating, contextual next-step
    # recommendations (ordered quietest first), and OPSEC tips. Lives in
    # src/core/soc_mentor.py — separate file so teach_engine stays focused
    # on tool reference data. format_mentor_block returns "" for topics
    # without mentor data yet (graceful skip during the rollout).
    try:
        from src.core.soc_mentor import format_mentor_block
        mentor = format_mentor_block(topic)
        if mentor:
            lines.append(mentor)
    except Exception:
        pass  # Mentor failure must never break a regular lesson

    return "\n".join(lines)
