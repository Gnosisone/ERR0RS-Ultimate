#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Language Expansion Layer v1.0
Central vocabulary registry. ALL natural language triggers live here.
Import from this file — never hardcode phrases in other modules.

Usage:
    from src.core.language_layer import (
        TOOL_PATTERNS,       # for live_terminal.py  parse_intent()
        TEACH_TRIGGERS,      # for live_terminal.py  parse_intent()
        KEYWORD_MAP,         # for teach_engine.py   find_lesson()
        ROUTE_TEACH_TRIGGERS,# for errorz_launcher.py route_command()
        ROUTE_TOOL_MAP,      # for errorz_launcher.py route_command()
        BARE_TOOLS,          # for errorz_launcher.py route_command()
        SOC_TRIGGERS,        # for errorz_launcher.py route_command()
        REPORT_TRIGGERS,     # for errorz_launcher.py route_command()
        SHELL_PASSTHROUGH,   # for errorz_launcher.py route_command()
        PURPLE_TEAM_TRIGGERS,# for errorz_launcher.py route_command() → purple_team mode
        RAG_TRIGGERS,        # for errorz_launcher.py route_command() → rag mode
        ATTCK_KEYWORD_MAP,   # for teach_engine.py   MITRE ATT&CK lesson routing
        normalize,           # helper: lowercase + strip + collapse spaces
        resolve_tool_alias,  # helper: "port scan" → "nmap"
        is_teach_request,    # helper: True if user wants a lesson
        classify_command,    # helper: full command router → category string
    )

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
from typing import Optional

# ── Language Expansion v2 — extended NLP vocabulary ──────────────────────
try:
    from src.core.language_expansion_v2 import (
        EXTENDED_TEACH_TRIGGERS,
        EXTENDED_TOOL_PHRASES,
        OPERATOR_SLANG,
        BEGINNER_PHRASES,
        COMPOUND_INTENTS,
        TYPO_MAP,
        TEACHING_RESPONSES,
        CONFIRMATION_WORDS,
        NEGATION_WORDS,
        PHASE_TRIGGERS,
        TONE_INDICATORS,
        expand_keywords,
        fuzzy_match_tool,
        get_response_tone,
        detect_compound_intent,
        detect_engagement_phase,
        correct_typo,
        is_beginner_confusion,
        get_operator_slang_category,
    )
    _V2_LOADED = True
except ImportError:
    _V2_LOADED = False
    EXTENDED_TEACH_TRIGGERS = []
    EXTENDED_TOOL_PHRASES   = {}
    OPERATOR_SLANG          = {}
    BEGINNER_PHRASES        = {}
    COMPOUND_INTENTS        = {}
    TYPO_MAP                = {}
    TEACHING_RESPONSES      = {}
    CONFIRMATION_WORDS      = []
    NEGATION_WORDS          = []
    PHASE_TRIGGERS          = {}
    TONE_INDICATORS         = {}
    def expand_keywords(t): return [t]
    def fuzzy_match_tool(t): return (None, 0.0)
    def get_response_tone(t): return 'intermediate'
    def detect_compound_intent(t): return None
    def detect_engagement_phase(t): return None
    def correct_typo(t): return (t, False)
    def is_beginner_confusion(t): return None
    def get_operator_slang_category(t): return None


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    """Lowercase, strip, collapse internal whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 1 — TOOL PATTERNS
# Used by: live_terminal.py → parse_intent()
# Format: tool_name → regex OR string (pipe-separated alternatives)
# Adding a new alias: just add "|new phrase" to the right entry.
# ═══════════════════════════════════════════════════════════════════════════

TOOL_PATTERNS: dict[str, str] = {

    # ── RECON ──────────────────────────────────────────────────────────────
    "nmap": (
        r"nmap|port.?scan|scan.?ports?|network.?scan|host.?discovery|"
        r"ping.?sweep|service.?scan|os.?detect|fingerprint.?host|"
        r"find.?open.?ports?|check.?ports?|enumerate.?ports?|"
        r"what.?ports|which.?ports|map.?network|discover.?hosts?|"
        r"probe.?host|recon.?scan|tcp.?scan|udp.?scan|syn.?scan|"
        r"stealth.?scan|aggressive.?scan|full.?scan|quick.?scan"
    ),

    "subfinder": (
        r"subfinder|subdomain.?enum|find.?subdomains?|enumerate.?subdomains?|"
        r"subdomain.?discovery|subdomain.?scan|sub.?enum|list.?subdomains?|"
        r"discover.?subdomains?|passive.?recon|dns.?enum|ct.?log|"
        r"certificate.?transparency|subdomain.?harvest|subdomain.?brute"
    ),

    "amass": (
        r"amass|osint.?recon|attack.?surface|external.?recon|"
        r"deep.?subdomain|thorough.?recon|full.?recon|network.?intel"
    ),

    "nuclei": (
        r"nuclei|vuln.?scan|vulnerability.?scan|cve.?scan|template.?scan|"
        r"check.?cves?|scan.?for.?vuln|find.?vulnerabilit|detect.?vuln|"
        r"security.?scan|scan.?for.?cve|probe.?vulnerabilit|"
        r"projectdiscovery|pd.?scan|auto.?vuln|automated.?scan"
    ),

    # ── WEB ────────────────────────────────────────────────────────────────
    "nikto": (
        r"nikto|web.?server.?scan|web.?vuln.?scan|http.?scan|"
        r"scan.?web.?server|check.?web.?server|web.?audit|"
        r"enumerate.?web|web.?recon|check.?for.?misconfig|"
        r"web.?misconfig|find.?web.?vulns?|web.?fingerprint"
    ),

    "gobuster": (
        r"gobuster|dir.?bust|directory.?bust|dirb|fuzz.?dir|"
        r"enumerate.?dir|brute.?force.?dir|brute.?dir|"
        r"find.?hidden|discover.?paths?|discover.?directories|"
        r"directory.?enum|dir.?enum|web.?fuzz|path.?fuzz|"
        r"find.?admin|find.?panel|find.?login|find.?pages?|"
        r"enumerate.?files?|hidden.?paths?|check.?paths?|web.?crawl"
    ),

    "ffuf": (
        r"ffuf|fast.?fuzz|web.?fuzz.?fast|parameter.?fuzz|"
        r"fuzz.?params?|fuzz.?headers?|vhost.?fuzz|"
        r"fuzz.?web|fuzzing|fuzz.?it|rapid.?fuzz"
    ),

    "wfuzz": (
        r"wfuzz|w.?fuzz|fuzz.?tool"
    ),

    "wpscan": (
        r"wpscan|wordpress.?scan|wp.?scan|scan.?wordpress|"
        r"wordpress.?vuln|wp.?vuln|wordpress.?enum|wordpress.?audit|"
        r"find.?wp.?plugins?|wordpress.?plugin|wp.?plugin|cms.?scan"
    ),

    # ── CREDENTIAL ATTACKS ─────────────────────────────────────────────────
    "hydra": (
        r"hydra|brute.?force|bruteforce|credential.?attack|password.?attack|"
        r"login.?attack|crack.?login|crack.?ssh|crack.?ftp|crack.?rdp|"
        r"crack.?smb|crack.?web|spray.?password|password.?spray|"
        r"online.?crack|auth.?attack|guess.?password|try.?passwords?|"
        r"brute.?ssh|brute.?ftp|brute.?rdp|brute.?smb|brute.?http|"
        r"force.?login|dictionary.?attack|wordlist.?attack"
    ),

    "hashcat": (
        r"hashcat|crack.?hash|hash.?crack|password.?crack|crack.?password|"
        r"offline.?crack|gpu.?crack|crack.?md5|crack.?sha|crack.?ntlm|"
        r"crack.?bcrypt|crack.?wpa|recover.?password|hash.?recover|"
        r"decrypt.?hash|break.?hash|reverse.?hash|crack.?the.?hash|"
        r"what.?is.?this.?hash|identify.?hash"
    ),

    # ── EXPLOITATION ───────────────────────────────────────────────────────
    "metasploit": (
        r"metasploit|msfconsole|msf|exploit.?framework|"
        r"run.?exploit|launch.?exploit|fire.?exploit|use.?exploit|"
        r"get.?shell|get.?meterpreter|reverse.?shell|bind.?shell|"
        r"pop.?shell|open.?shell|gain.?access|pwn|compromise|"
        r"eternalblue|ms17.?010|bluekeep|log4shell|printnightmare|"
        r"smb.?exploit|rdp.?exploit|windows.?exploit"
    ),

    "sqlmap": (
        r"sqlmap|sql.?injection|sqli|sql.?inject|"
        r"inject.?sql|test.?sql|check.?sql|find.?sqli|"
        r"dump.?database|extract.?database|enumerate.?db|"
        r"attack.?database|database.?exploit|blind.?sqli|"
        r"union.?inject|error.?based|time.?based.?blind|"
        r"boolean.?based|db.?dump|steal.?data|data.?exfil"
    ),

    # ── NETWORK TOOLS ──────────────────────────────────────────────────────
    "crackmapexec": (
        r"crackmapexec|cme|smb.?spray|smb.?enum|lateral.?move|"
        r"domain.?enum|ad.?spray|active.?directory.?spray|"
        r"smb.?sweep|network.?auth.?test|smb.?recon"
    ),

    "enum4linux": (
        r"enum4linux|smb.?enum|samba.?enum|windows.?enum|"
        r"netbios.?enum|rpc.?enum|null.?session|smb.?null|"
        r"enumerate.?smb|enumerate.?samba|smb.?shares|"
        r"list.?shares|find.?shares|smb.?users|enumerate.?users.?smb"
    ),

    # ── WIRELESS ───────────────────────────────────────────────────────────
    "aircrack": (
        r"aircrack|wifi|wpa2|wpa|wep|wireless.?attack|handshake|"
        r"monitor.?mode|deauth|deauthenticate|capture.?handshake|"
        r"crack.?wifi|hack.?wifi|wireless.?hack|crack.?wpa|"
        r"airmon|airodump|aireplay|wifi.?pentest|wireless.?pentest|"
        r"crack.?wireless|evil.?twin|fake.?ap|rogue.?ap"
    ),
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2 — TEACH TRIGGERS
# Used by: live_terminal.py → parse_intent()
# Any phrase here causes teach=True on the parsed intent.
# ═══════════════════════════════════════════════════════════════════════════

TEACH_TRIGGERS: list[str] = [
    # Direct teach commands
    "teach me", "teach", "and teach", "--teach", "-t",
    # Explanation requests
    "explain", "and explain", "break it down", "break down",
    "walk me through", "walk through", "step by step",
    # Understanding requests
    "help me understand", "i want to learn", "i need to learn",
    "i want to know", "i need to know", "educate me",
    "show me how", "show me what", "show me why",
    # Question starters
    "what is", "what are", "what does", "what do",
    "what's", "whats", "what was", "what were",
    "how does", "how do", "how do i", "how can i",
    "how to", "how would", "how should",
    "why does", "why do", "why is", "why are",
    "when do", "when should", "when would",
    "where does", "where do",
    # Learning intent
    "learn", "learning", "study", "studying",
    "help me learn", "let me learn", "want to learn",
    "i dont know", "i don't know", "not sure what",
    "never used", "never heard of",
    # Tutorial requests
    "tutorial", "guide", "beginner", "basics", "intro",
    "introduction", "overview", "primer", "crash course",
    "cheat sheet", "cheatsheet", "quick reference",
    # Deep dive
    "deep dive", "in depth", "in-depth", "detailed",
    "tell me about", "tell me more", "more about",
    "give me info", "give me information", "info on",
    "what can", "can you explain",
]


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 3 — KEYWORD MAP (teach engine)
# Used by: teach_engine.py → find_lesson()
# Maps anything a user might type → a LESSONS key
# ═══════════════════════════════════════════════════════════════════════════

KEYWORD_MAP: dict[str, str] = {

    # ── NMAP ───────────────────────────────────────────────────────────────
    "nmap":               "nmap",
    "network scan":       "nmap",
    "port scan":          "nmap",
    "port scanning":      "nmap",
    "network mapper":     "nmap",
    "host discovery":     "nmap",
    "ping sweep":         "nmap",
    "syn scan":           "nmap",
    "tcp scan":           "nmap",
    "udp scan":           "nmap",
    "stealth scan":       "nmap",
    "os detection":       "nmap",
    "service detection":  "nmap",
    "nse scripts":        "nmap",
    "network discovery":  "nmap",
    "find open ports":    "nmap",
    "check open ports":   "nmap",
    "scan a network":     "nmap",
    "scan the network":   "nmap",
    "map the network":    "nmap",
    "discover hosts":     "nmap",

    # ── SQLMAP ─────────────────────────────────────────────────────────────
    "sqlmap":             "sqlmap",
    "sql map":            "sqlmap",
    "sglmap":             "sqlmap",
    "sql injection":      "sql injection",
    "sql inject":         "sql injection",
    "sqli":               "sql injection",
    "inject sql":         "sql injection",
    "database injection": "sql injection",
    "dump database":      "sqlmap",
    "extract database":   "sqlmap",
    "attack database":    "sqlmap",
    "test for sqli":      "sql injection",
    "find sql injection": "sql injection",
    "blind sqli":         "sql injection",
    "union injection":    "sql injection",
    "boolean injection":  "sql injection",
    "time based":         "sql injection",

    # ── NIKTO ──────────────────────────────────────────────────────────────
    "nikto":              "nikto",
    "web scanner":        "nikto",
    "web scan":           "nikto",
    "web server scan":    "nikto",
    "http scan":          "nikto",
    "scan web server":    "nikto",
    "web audit":          "nikto",
    "web recon":          "nikto",
    "web fingerprint":    "nikto",

    # ── GOBUSTER ───────────────────────────────────────────────────────────
    "gobuster":               "gobuster",
    "directory bruteforce":   "gobuster",
    "dir brute":              "gobuster",
    "dirbuster":              "gobuster",
    "directory fuzzing":      "gobuster",
    "gobust":                 "gobuster",
    "dirb":                   "gobuster",
    "find hidden pages":      "gobuster",
    "find hidden directories":"gobuster",
    "dir enum":               "gobuster",
    "directory enum":         "gobuster",
    "path fuzzing":           "gobuster",
    "find admin panel":       "gobuster",
    "enumerate directories":  "gobuster",
    "enumerate files":        "gobuster",
    "brute force directory":  "gobuster",

    # ── HYDRA ──────────────────────────────────────────────────────────────
    "hydra":                  "hydra",
    "brute force":            "hydra",
    "bruteforce":             "hydra",
    "password attack":        "hydra",
    "credential attack":      "hydra",
    "login attack":           "hydra",
    "online cracking":        "hydra",
    "dictionary attack":      "hydra",
    "wordlist attack":        "hydra",
    "password spraying":      "hydra",
    "credential stuffing":    "hydra",
    "brute force ssh":        "hydra",
    "brute force ftp":        "hydra",
    "brute force rdp":        "hydra",
    "brute force smb":        "hydra",
    "crack ssh":              "hydra",
    "crack ftp":              "hydra",
    "attack login":           "hydra",
    "force login":            "hydra",

    # ── METASPLOIT ─────────────────────────────────────────────────────────
    "metasploit":         "metasploit",
    "msf":                "metasploit",
    "msfconsole":         "metasploit",
    "exploit framework":  "metasploit",
    "framework":          "metasploit",
    "run exploit":        "metasploit",
    "launch exploit":     "metasploit",
    "get shell":          "metasploit",
    "get meterpreter":    "metasploit",
    "reverse shell":      "metasploit",
    "bind shell":         "metasploit",
    "eternalblue":        "metasploit",
    "ms17-010":           "metasploit",
    "ms17 010":           "metasploit",
    "bluekeep":           "metasploit",
    "log4shell":          "metasploit",
    "printnightmare":     "metasploit",

    # ── METERPRETER ────────────────────────────────────────────────────────
    "meterpreter":        "meterpreter",
    "meter":              "meterpreter",
    "post exploit":       "meterpreter",
    "post exploitation":  "meterpreter",
    "hashdump":           "meterpreter",
    "getsystem":          "meterpreter",
    "migrate process":    "meterpreter",
    "dump hashes":        "meterpreter",
    "keylogger":          "meterpreter",
    "screenshot":         "meterpreter",
    "persistence":        "meterpreter",

    # ── HASHCAT ────────────────────────────────────────────────────────────
    "hashcat":            "hashcat",
    "password crack":     "hashcat",
    "hash crack":         "hashcat",
    "crack hash":         "hashcat",
    "crack password":     "hashcat",
    "offline cracking":   "hashcat",
    "gpu cracking":       "hashcat",
    "crack md5":          "hashcat",
    "crack sha":          "hashcat",
    "crack ntlm":         "hashcat",
    "crack bcrypt":       "hashcat",
    "crack wpa":          "hashcat",
    "crack wpa2":         "hashcat",
    "crack hashes":       "hashcat",
    "hash identifier":    "hashcat",
    "identify hash":      "hashcat",
    "ntlm":               "hashcat",
    "md5":                "hashcat",

    # ── AIRCRACK ───────────────────────────────────────────────────────────
    "aircrack":           "aircrack",
    "aircrack-ng":        "aircrack",
    "wifi hack":          "aircrack",
    "wpa2 crack":         "aircrack",
    "wpa crack":          "aircrack",
    "wep crack":          "aircrack",
    "wireless attack":    "aircrack",
    "wireless hack":      "aircrack",
    "wifi cracking":      "aircrack",
    "wifi pentest":       "aircrack",
    "wireless pentest":   "aircrack",
    "monitor mode":       "aircrack",
    "deauth":             "aircrack",
    "deauthentication":   "aircrack",
    "capture handshake":  "aircrack",
    "4 way handshake":    "aircrack",
    "evil twin":          "aircrack",
    "rogue ap":           "aircrack",
    "fake ap":            "aircrack",
    "airmon":             "aircrack",
    "airodump":           "aircrack",
    "aireplay":           "aircrack",

    # ── NUCLEI ─────────────────────────────────────────────────────────────
    "nuclei":             "nuclei",
    "vuln scan":          "nuclei",
    "vulnerability scan": "nuclei",
    "cve scan":           "nuclei",
    "template scan":      "nuclei",
    "automated scanning": "nuclei",
    "check for cves":     "nuclei",
    "find vulnerabilities":"nuclei",

    # ── SUBFINDER ──────────────────────────────────────────────────────────
    "subfinder":          "subfinder",
    "subdomain":          "subfinder",
    "subdomains":         "subfinder",
    "subdomain enum":     "subfinder",
    "subdomain scan":     "subfinder",
    "subdomain discovery":"subfinder",
    "find subdomains":    "subfinder",
    "enumerate subdomains":"subfinder",
    "passive recon":      "subfinder",
    "dns enumeration":    "subfinder",
    "ct logs":            "subfinder",

    # ── XSS ────────────────────────────────────────────────────────────────
    "xss":                        "xss",
    "cross site scripting":       "xss",
    "cross-site scripting":       "xss",
    "javascript injection":       "xss",
    "script injection":           "xss",
    "stored xss":                 "xss",
    "reflected xss":              "xss",
    "dom xss":                    "xss",
    "cookie theft":               "xss",
    "steal cookie":               "xss",
    "client side attack":         "xss",
    "inject javascript":          "xss",

    # ── PRIVILEGE ESCALATION ───────────────────────────────────────────────
    "privilege escalation":       "privilege escalation",
    "privesc":                    "privilege escalation",
    "priv esc":                   "privilege escalation",
    "priv-esc":                   "privilege escalation",
    "root":                       "privilege escalation",
    "get root":                   "privilege escalation",
    "become root":                "privilege escalation",
    "escalate privileges":        "privilege escalation",
    "local privilege escalation": "privilege escalation",
    "lpe":                        "privilege escalation",
    "suid":                       "privilege escalation",
    "suid exploit":               "privilege escalation",
    "sudo exploit":               "privilege escalation",
    "sudo abuse":                 "privilege escalation",
    "linpeas":                    "privilege escalation",
    "winpeas":                    "privilege escalation",
    "gtfobins":                   "privilege escalation",
    "lolbas":                     "privilege escalation",
    "token impersonation":        "privilege escalation",
    "juicypotato":                "privilege escalation",

    # ── BURP SUITE ─────────────────────────────────────────────────────────
    "burp":               "burp suite",
    "burp suite":         "burp suite",
    "proxy":              "burp suite",
    "intercept":          "burp suite",
    "intercepting proxy": "burp suite",
    "web proxy":          "burp suite",
    "http proxy":         "burp suite",
    "repeater":           "burp suite",
    "intruder":           "burp suite",
    "web testing proxy":  "burp suite",
    "modify requests":    "burp suite",
    "intercept traffic":  "burp suite",
    "replay requests":    "burp suite",

    # ── WIRESHARK ──────────────────────────────────────────────────────────
    "wireshark":          "wireshark",
    "packet capture":     "wireshark",
    "pcap":               "wireshark",
    "packet sniffer":     "wireshark",
    "network capture":    "wireshark",
    "sniff traffic":      "wireshark",
    "capture traffic":    "wireshark",
    "capture packets":    "wireshark",
    "analyze traffic":    "wireshark",
    "protocol analyzer":  "wireshark",
    "tcpdump":            "wireshark",
    "network forensics":  "wireshark",
    "traffic analysis":   "wireshark",
    "sniffing":           "wireshark",
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 4 — ROUTE TEACH TRIGGERS
# Used by: errorz_launcher.py → route_command() first-pass
# Any of these in the command → route to teach engine first
# ═══════════════════════════════════════════════════════════════════════════

ROUTE_TEACH_TRIGGERS: list[str] = [
    "teach me", "teach", "how do i", "how to use", "how does",
    "how to", "explain", "what is", "what are", "what's",
    "tell me about", "how do you use", "learn", "help me learn",
    "show me how", "guide me", "tutorial", "i want to learn",
    "walk me through", "break it down", "break down",
    "educate me", "give me a lesson", "lesson on",
    "overview of", "intro to", "introduction to",
    "basics of", "beginner guide", "crash course",
    "cheat sheet", "quick reference", "primer on",
    "deep dive", "in depth on", "info on",
    "tell me more about", "more about", "what can",
    "never used", "never heard of", "don't know",
    "dont know", "help with", "stuck on",
    "confused about", "not sure about",
]


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 5 — BARE TOOL NAMES
# Used by: errorz_launcher.py → route_command()
# If user types ONLY one of these → teach mode (they want to know what it is)
# ═══════════════════════════════════════════════════════════════════════════

BARE_TOOLS: list[str] = [
    # Core pentest tools
    "nmap", "sqlmap", "nikto", "gobuster", "hydra", "hashcat",
    "aircrack", "aircrack-ng", "nuclei", "subfinder", "amass",
    "metasploit", "msfconsole", "msf", "meterpreter",
    "wireshark", "burp", "burp suite", "burpsuite",
    "wpscan", "crackmapexec", "cme", "enum4linux",
    "dirb", "ffuf", "wfuzz", "dirbuster",
    "netcat", "nc", "ncat",
    "john", "john the ripper",
    "responder",
    "impacket",
    "bloodhound",
    "mimikatz",
    "cobalt strike",
    "beef", "beef-xss",
    "set", "social engineer toolkit",
    # Concepts
    "sql injection", "sqli", "xss", "cross site scripting",
    "privilege escalation", "privesc", "priv esc",
    "reverse shell", "bind shell",
    "payload", "shellcode",
    "buffer overflow", "bof",
    "lfi", "rfi", "local file inclusion", "remote file inclusion",
    "ssrf", "server side request forgery",
    "xxe", "xml injection",
    "idor", "insecure direct object reference",
    "csrf", "cross site request forgery",
    "command injection", "code injection",
    "path traversal", "directory traversal",
    "open redirect",
    "xxs",           # common typo
    # Wireless
    "wifi", "wpa2", "wep", "wireless",
    "deauth", "evil twin",
    # Post-exploitation
    "lateral movement", "pivoting", "persistence",
    "pass the hash", "pth", "kerberoasting",
    "golden ticket", "silver ticket", "dcsync",
]


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 6 — ROUTE TOOL MAP
# Used by: errorz_launcher.py → route_command() tool execution path
# Maps a verb/keyword the user might type → canonical tool name
# ═══════════════════════════════════════════════════════════════════════════

ROUTE_TOOL_MAP: dict[str, str] = {
    # Nmap aliases
    "nmap":             "nmap",
    "scan":             "nmap",
    "portscan":         "nmap",
    "port-scan":        "nmap",
    "networkscan":      "nmap",
    "discover":         "nmap",
    "probe":            "nmap",
    "recon":            "nmap",
    "map":              "nmap",

    # Web scanning
    "nikto":            "nikto",
    "webscan":          "nikto",

    # Directory busting
    "gobuster":         "gobuster",
    "dirbust":          "gobuster",
    "dirb":             "gobuster",
    "fuzz":             "gobuster",
    "dirscan":          "gobuster",

    # SQL injection
    "sqlmap":           "sqlmap",
    "sqli":             "sqlmap",
    "inject":           "sqlmap",
    "sqltest":          "sqlmap",

    # Credential attacks
    "hydra":            "hydra",
    "brute":            "hydra",
    "crack":            "hydra",
    "spray":            "hydra",
    "attack":           "hydra",

    # Subdomain
    "subfinder":        "subfinder",
    "subdomain":        "subfinder",
    "subs":             "subfinder",
    "amass":            "amass",

    # Vuln scanning
    "nuclei":           "nuclei",
    "vulnscan":         "nuclei",
    "cve":              "nuclei",

    # Hash cracking
    "hashcat":          "hashcat",
    "hashcrack":        "hashcat",
    "crackmd5":         "hashcat",

    # Exploitation
    "metasploit":       "metasploit",
    "msf":              "metasploit",
    "exploit":          "metasploit",
    "pwn":              "metasploit",

    # SMB
    "enum4linux":       "enum4linux",
    "smbenum":          "enum4linux",
    "crackmapexec":     "crackmapexec",
    "cme":              "crackmapexec",

    # WordPress
    "wpscan":           "wpscan",
    "wordpress":        "wpscan",

    # Wireless
    "aircrack":         "aircrack",
    "wifi":             "aircrack",
    "wireless":         "aircrack",

    # Fuzzing
    "ffuf":             "ffuf",
    "wfuzz":            "wfuzz",
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 7 — SOC / BLUE TEAM TRIGGERS
# Used by: errorz_launcher.py → route_command()
# These phrases route to the defensive/monitoring SOC actions
# ═══════════════════════════════════════════════════════════════════════════

SOC_TRIGGERS: dict[str, str] = {
    # Failed logins
    "failed login":       "failed-logins",
    "failed logins":      "failed-logins",
    "login failures":     "failed-logins",
    "login attempts":     "failed-logins",
    "failed ssh":         "failed-logins",
    "brute force detect": "failed-logins",
    "auth failures":      "failed-logins",
    "bad passwords":      "failed-logins",
    "wrong passwords":    "failed-logins",

    # Active connections
    "active connections": "active-conns",
    "active conns":       "active-conns",
    "who is connected":   "active-conns",
    "network connections":"active-conns",
    "established connections": "active-conns",
    "current connections":"active-conns",
    "check connections":  "active-conns",

    # Open ports
    "open ports":         "open-ports",
    "listening ports":    "open-ports",
    "what ports":         "open-ports",
    "which ports":        "open-ports",
    "ports open":         "open-ports",
    "listening services": "open-ports",

    # Process audit
    "running processes":  "running-procs",
    "process list":       "running-procs",
    "process audit":      "running-procs",
    "top processes":      "running-procs",
    "what is running":    "running-procs",
    "suspicious processes":"running-procs",
    "process monitor":    "running-procs",

    # Log analysis
    "show logs":          "log-tail",
    "check logs":         "log-tail",
    "live logs":          "log-tail",
    "recent logs":        "log-tail",
    "auth log":           "log-tail",
    "syslog":             "log-tail",
    "system log":         "log-tail",
    "log tail":           "log-tail",

    # Who is online
    "who is online":      "who-online",
    "who is logged in":   "who-online",
    "logged in users":    "who-online",
    "active users":       "who-online",
    "current users":      "who-online",
    "who is on":          "who-online",

    # Sudo log
    "sudo log":           "sudo-log",
    "sudo history":       "sudo-log",
    "sudo audit":         "sudo-log",
    "privilege log":      "sudo-log",
    "root commands":      "sudo-log",
    "admin commands":     "sudo-log",

    # Firewall
    "firewall":           "firewall-rules",
    "firewall rules":     "firewall-rules",
    "iptables":           "firewall-rules",
    "ufw":                "firewall-rules",
    "firewall status":    "firewall-rules",
    "check firewall":     "firewall-rules",

    # Cron jobs
    "cron":               "cron-jobs",
    "cron jobs":          "cron-jobs",
    "scheduled tasks":    "cron-jobs",
    "crontab":            "cron-jobs",
    "scheduled jobs":     "cron-jobs",
    "persistence check":  "cron-jobs",

    # DNS
    "dns cache":          "dns-cache",
    "dns check":          "dns-cache",
    "hosts file":         "dns-cache",
    "dns entries":        "dns-cache",
    "check dns":          "dns-cache",
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 8 — REPORT / SYSTEM / SHELL TRIGGERS
# Used by: errorz_launcher.py → route_command()
# ═══════════════════════════════════════════════════════════════════════════

REPORT_TRIGGERS: list[str] = [
    "report", "generate report", "debrief", "create report",
    "make report", "write report", "pentest report",
    "export report", "save report", "finalize",
    "summarize findings", "summary", "findings",
    "document findings", "write up", "writeup",
]

STATUS_TRIGGERS: list[str] = [
    "status", "sysinfo", "uname", "whoami", "system info",
    "system status", "check system", "health check",
    "what am i running", "what os", "current user",
    "id", "hostname", "ip address", "my ip",
    "interfaces", "network interfaces",
]

SHELL_PASSTHROUGH: list[str] = ["$", "!"]

OLLAMA_TRIGGERS: list[str] = [
    "ollama", "models", "ai status", "ai models",
    "which models", "list models", "available models",
    "llm status", "llama",
]

MCP_TRIGGERS: list[str] = [
    "mcp", "kali tools", "mcp tools", "list tools",
    "available tools", "mcp server",
]

ROCKETGOD_TRIGGERS: list[str] = [
    "rocketgod", "hackrf", "rf jammer", "jammer", "protopirate",
    "rolling code", "keyfob", "sub file", "subghz scan", "wigle",
    "wardriv", "radio scanner", "keeloq", "flipper sd", "rg toolbox",
    "software defined radio", "sdr", "rf attack", "frequency",
    "transmit", "radio hack",
]

BADUSB_TRIGGERS: list[str] = [
    "flipper", "badusb", "bad usb", "ducky", "duckyscript",
    "rubber ducky", "hid attack", "keystroke injection",
    "evil portal", "captive portal", "sd card",
    "generate script", "generate payload", "hid payload",
    "usb attack", "usb hack", "flipper zero",
]

# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 9 (NEW) — PURPLE TEAM TRIGGERS
# Used by: errorz_launcher.py → route_command()
# Routes to purple_team brain mode — full Red+Blue+Remediation loop
# ═══════════════════════════════════════════════════════════════════════════

PURPLE_TEAM_TRIGGERS: list[str] = [
    # Purple team mode
    "purple team", "purple mode", "purple",
    "full loop", "attack and detect", "red and blue",
    "simulate and detect", "simulate and fix",
    # MITRE ATT&CK
    "mitre", "att&ck", "attack framework", "ttp", "technique id",
    "mitre attack", "mitre att", "t1059", "t1053", "t1078",
    "atomic test", "atomic red team", "atomic",
    # Sigma
    "sigma rule", "sigma detect", "sigma query", "detection rule",
    "siem rule", "elk rule", "splunk rule", "log detection",
    # Atomic Red Team
    "atomic red", "canary atomic", "red canary",
    # CIS Benchmarks + STIGs
    "cis benchmark", "cis hardening", "stig", "disa stig",
    "hardening guide", "harden after", "remediate", "remediation",
    # Full purple cycle
    "hack then patch", "exploit then fix", "attack then defend",
    "find and fix", "test and remediate",
]

# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 10 (NEW) — RAG / KNOWLEDGE BASE TRIGGERS
# Used by: errorz_launcher.py → route_command()
# Routes to rag_analyst brain mode — CVE/TTP/Sigma knowledge queries
# ═══════════════════════════════════════════════════════════════════════════

RAG_TRIGGERS: list[str] = [
    # CVE lookups
    "cve", "cve lookup", "look up cve", "find cve", "explain cve",
    "cve-20", "nvd", "nist vulnerability",
    # Exploit DB
    "exploitdb", "exploit-db", "searchsploit",
    # Knowledge base
    "knowledge base", "rag query", "search knowledge",
    # AI threat intelligence (new)
    "wormgpt", "worm gpt", "fraudgpt", "fraud gpt",
    "criminal ai", "malicious ai", "dark web ai", "ai weapon",
    "ai threat", "ai attack", "ai powered attack", "ai phishing",
    "ai bec", "ai malware", "ghostgpt", "darkgpt", "evil gpt",
    "deepfake", "deepfake fraud", "voice clone", "video deepfake",
    "ai voice", "synthetic voice", "cloned voice",
    "prompt injection", "llm injection", "ai injection",
    "mitre atlas", "atlas framework", "adversarial ml",
    "what are attackers using", "current threat landscape",
    "criminal tools", "dark web tools", "threat actor tools",
    "corporate briefing", "board briefing", "executive briefing",
    "fortune 500 threat", "brief the board", "ciso briefing",
    "what is the threat", "threat intelligence",
    "new attack methods", "emerging threats", "ai enabled attacks",
    "paradigm shift security", "democratized attacks",
    "spiderman gpt", "spider gpt",
    "ai ransomware", "ai social engineering",
    "ai powered malware", "polymorphic ai", "ai evasion",
]

# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 11 (NEW) — MITRE ATT&CK KEYWORD MAP additions
# Extends KEYWORD_MAP for teach engine lesson routing
# ═══════════════════════════════════════════════════════════════════════════

ATTCK_KEYWORD_MAP: dict[str, str] = {
    # MITRE ATT&CK Tactics
    "initial access":           "mitre_initial_access",
    "execution":                "mitre_execution",
    "persistence":              "mitre_persistence",
    "privilege escalation":     "mitre_privesc",
    "defense evasion":          "mitre_evasion",
    "credential access":        "mitre_creds",
    "discovery":                "mitre_discovery",
    "lateral movement":         "mitre_lateral",
    "collection":               "mitre_collection",
    "exfiltration":             "mitre_exfil",
    "command and control":      "mitre_c2",
    "c2":                       "mitre_c2",
    "impact":                   "mitre_impact",
    # Common TTPs
    "t1059":                    "mitre_execution",
    "t1053":                    "mitre_persistence",
    "t1078":                    "mitre_creds",
    "t1003":                    "mitre_creds",
    "t1110":                    "mitre_creds",
    "t1566":                    "mitre_initial_access",
    "t1190":                    "mitre_initial_access",
    "t1055":                    "mitre_evasion",
    "t1027":                    "mitre_evasion",
    "t1071":                    "mitre_c2",
    "t1041":                    "mitre_exfil",
    # Kill chain phases
    "recon phase":              "nmap",
    "weaponization":            "metasploit",
    "delivery":                 "metasploit",
    "exploitation phase":       "metasploit",
    "installation":             "meterpreter",
    "command control":          "mitre_c2",
    "actions on objectives":    "mitre_impact",
}


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 12 — NEW MODULE TRIGGERS
# Cloud Security, CTF Solver, OPSEC Mode, Post-Exploitation, Lateral Movement
# Wireless, Social Engineering
# ═══════════════════════════════════════════════════════════════════════════

CLOUD_TRIGGERS: list[str] = [
    "cloud security", "aws enum", "aws iam", "aws s3", "azure enum",
    "azure rbac", "gcp enum", "gcp iam", "cloud audit", "cloud pentest",
    "validate aws keys", "aws keys", "leaked aws", "s3 bucket audit",
    "prowler scan", "cloud misconfiguration", "cloud credentials",
    "enumerate cloud", "cloud recon", "azure storage", "gcs bucket",
    "iam enum", "cloud security posture", "aws whoami", "gcp whoami",
    "azure whoami", "cloud privilege escalation", "cloud privesc",
]

CTF_TRIGGERS: list[str] = [
    "ctf", "capture the flag", "ctf mode", "ctf solver",
    "ctf web", "ctf pwn", "ctf crypto", "ctf forensics", "ctf rev",
    "ctf reversing", "solve ctf", "help me with ctf",
    "binary exploitation", "buffer overflow", "rop chain",
    "format string vulnerability", "heap exploitation", "pwntools",
    "ctf challenge", "ctf writeup", "ctf hint",
    "crypto challenge", "forensics challenge", "reversing challenge",
    "web challenge", "pwn challenge",
]

OPSEC_TRIGGERS: list[str] = [
    "opsec", "operational security", "opsec mode", "opsec check",
    "stay anonymous", "anonymity", "hide my ip", "proxychains",
    "tor setup", "tor routing", "mac spoof", "mac address spoof",
    "vpn tor", "vpn chain", "persona management", "sock puppet",
    "fake identity", "cover tracks", "covering tracks", "anti forensics",
    "anti-forensics", "timestomp", "log wipe", "clear logs",
    "opsec checklist", "pre engagement checklist", "post engagement cleanup",
    "operational security", "tradecraft", "exfil opsec",
    "avoid detection", "evade logging", "engagement hygiene",
]

POSTEX_TRIGGERS: list[str] = [
    "post exploitation", "post-exploitation", "postex",
    "situational awareness", "persistence", "establish persistence",
    "credential harvest", "harvest credentials", "laZagne", "mimikatz",
    "pivot", "pivoting", "ssh tunnel", "socks proxy", "chisel",
    "port forward", "covering tracks", "clear bash history",
    "timestomping", "postex module", "after exploitation",
]

PRIVESC_TRIGGERS: list[str] = [
    "privilege escalation", "privesc", "priv esc", "escalate privileges",
    "become root", "get root", "linux privesc", "windows privesc",
    "suid", "sudo abuse", "sudo -l", "unquoted service path",
    "alwaysinstallelevated", "token impersonation", "juicy potato",
    "sweet potato", "printspoofer", "winpeas", "linpeas",
    "dll hijack", "writable passwd", "capabilities abuse",
    "docker escape", "lxc escape", "cron privesc",
]

LATERAL_TRIGGERS: list[str] = [
    "lateral movement", "lateral move", "move laterally",
    "pass the hash", "pth attack", "psexec", "wmiexec", "dcomexec",
    "crackmapexec", "cme smb", "smb spray", "kerberoasting",
    "kerberoast", "asreproast", "dcsync", "bloodhound",
    "impacket", "secretsdump", "pass the ticket", "overpass the hash",
    "spread through network", "pivot to domain",
]

WIRELESS_TRIGGERS: list[str] = [
    "wireless attack", "wifi attack", "wifi hack", "wpa crack",
    "wpa2 crack", "aircrack", "airodump", "monitor mode",
    "deauth attack", "deauthentication", "evil twin", "pmkid",
    "handshake capture", "wifi recon", "wireless recon",
    "airmon-ng", "aireplay-ng", "wifi pineapple",
]

SOCIAL_TRIGGERS: list[str] = [
    # General SE
    "social engineering", "social engineer", "se attack", "human hacking",
    "human variable", "human attack surface", "human factor",
    "exploit the human", "hack the human", "hack people",
    "people hacking", "manipulate", "manipulation",
    # Psychology
    "psychology of hacking", "cialdini", "influence principles",
    "cognitive bias", "why people get hacked", "human psychology",
    "social psychology", "behavioral manipulation",
    # Phishing
    "phishing", "spear phishing", "spearphishing", "whaling",
    "business email compromise", "bec", "clone phishing",
    "email attack", "phishing campaign", "phishing email",
    "credential harvesting page", "fake login", "fake login page",
    "gophish", "evilginx", "evilginx2", "mfa bypass phishing",
    "smishing", "sms phishing", "qr phishing", "qr code attack",
    # Vishing
    "vishing", "voice phishing", "phone phishing", "phone attack",
    "phone call attack", "caller id spoof", "spoofed call",
    "call script", "vishing script", "pretexting call",
    "elicitation", "yes ladder", "authority call",
    # Physical
    "physical social engineering", "physical pentest", "physical pen test",
    "tailgating", "piggybacking", "badge cloning", "impersonation",
    "usb drop", "usb baiting", "rubber ducky drop", "dumpster diving",
    "shoulder surfing", "lock picking", "physical access attack",
    # OSINT on humans
    "human osint", "target recon", "person recon", "employee recon",
    "theharvester", "maltego", "sherlock", "hunter.io",
    "email harvesting", "find emails", "linkedin recon",
    "breach data lookup", "osint person", "profile a target",
    # Pretexting
    "pretexting", "pretext", "build a pretext", "create a pretext",
    "false identity", "fake identity", "impersonate",
    # SET / Tools
    "setoolkit", "social engineer toolkit", "se tools",
    "credential harvester", "website cloner", "infectious media",
    # Defense
    "se defense", "social engineering defense", "human firewall",
    "security awareness", "phishing simulation", "simulated phishing",
    "phishing training", "awareness training",
    # Engagement context
    "initial access via human", "foothold via phishing",
    "get credentials via phishing", "bypass mfa with phishing",
]


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 9 — HELPER FUNCTIONS
# Utility functions that use the vocab above
# ═══════════════════════════════════════════════════════════════════════════

def is_teach_request(text: str) -> bool:
    """Return True if the text is a teach/learn/explain request."""
    lower = normalize(text)
    return any(t in lower for t in TEACH_TRIGGERS)


def resolve_tool_alias(text: str) -> Optional[str]:
    """
    Try to resolve a user phrase to a canonical tool name.
    Returns tool name (str) or None if no match.

    Examples:
        "port scan 192.168.1.1"  → "nmap"
        "brute force the ssh"    → "hydra"
        "dump the database"      → "sqlmap"
    """
    lower = normalize(text)

    # Check ROUTE_TOOL_MAP for first-word match (verb-style commands)
    first_word = lower.split()[0] if lower.split() else ""
    if first_word in ROUTE_TOOL_MAP:
        return ROUTE_TOOL_MAP[first_word]

    # Check full TOOL_PATTERNS regex match
    for tool, pattern in TOOL_PATTERNS.items():
        if re.search(pattern, lower):
            return tool

    # Check ROUTE_TOOL_MAP for any word match
    for keyword, tool in ROUTE_TOOL_MAP.items():
        if keyword in lower:
            return tool

    return None


def resolve_lesson_alias(text: str) -> Optional[str]:
    """
    Try to resolve a user phrase to a LESSONS key.
    Returns lesson key (str) or None if no match.

    Examples:
        "teach me about sql injection"  → "sql injection"
        "how does aircrack-ng work"     → "aircrack"
        "explain privesc"               → "privilege escalation"
    """
    lower = normalize(text)

    # Strip teach prefixes to get the topic
    for prefix in ROUTE_TEACH_TRIGGERS:
        if lower.startswith(prefix):
            lower = lower[len(prefix):].strip()
            break

    # Direct KEYWORD_MAP lookup
    if lower in KEYWORD_MAP:
        return KEYWORD_MAP[lower]

    # Substring scan through KEYWORD_MAP (longest match wins)
    best_match = None
    best_len = 0
    for keyword, lesson_key in KEYWORD_MAP.items():
        if keyword in lower and len(keyword) > best_len:
            best_match = lesson_key
            best_len = len(keyword)
    if best_match:
        return best_match

    return None


def get_soc_action(text: str) -> Optional[str]:
    """
    Return a SOC action string if the text matches a blue team trigger.
    Returns action key (str) or None.
    """
    lower = normalize(text)
    # Longest match wins
    best_match = None
    best_len = 0
    for phrase, action in SOC_TRIGGERS.items():
        if phrase in lower and len(phrase) > best_len:
            best_match = action
            best_len = len(phrase)
    return best_match


def classify_command(text: str) -> str:
    """
    Classify a raw user command into a routing category.
    v2: uses typo correction, operator slang, compound intent, and
        extended teach triggers from language_expansion_v2.
    """
    # Step 0 — typo correction (silent)
    corrected, _ = correct_typo(text)
    lower = normalize(corrected)

    # Shell passthrough ($, !)
    if text.startswith(tuple(SHELL_PASSTHROUGH)):
        return 'shell'

    # Beginner confusion check (highest priority — corrects before routing)
    if is_beginner_confusion(lower):
        return 'teach'

    # Compound intent detection
    compound = detect_compound_intent(lower)
    if compound:
        return compound

    # Operator slang → resolve to category
    slang_cat = get_operator_slang_category(lower)
    if slang_cat in ('exploit', 'payload', 'shell'):
        return 'tool'
    if slang_cat == 'privesc':
        return 'privesc'
    if slang_cat == 'lateral':
        return 'lateral'
    if slang_cat == 'recon':
        return 'tool'
    if slang_cat == 'credentials':
        return 'postex'
    if slang_cat == 'evasion':
        return 'teach'

    # Purple Team loop
    if any(t in lower for t in PURPLE_TEAM_TRIGGERS):
        return 'purple_team'

    # RAG knowledge base
    if any(t in lower for t in RAG_TRIGGERS):
        return 'rag'

    # Extended teach triggers (v2) + original triggers
    all_teach = list(TEACH_TRIGGERS) + list(EXTENDED_TEACH_TRIGGERS)
    if any(t in lower for t in all_teach) and not resolve_tool_alias(lower):
        return 'teach'

    # SOC blue team
    if get_soc_action(lower):
        return 'soc'

    # Report generation
    if any(t in lower for t in REPORT_TRIGGERS):
        return 'report'

    # System status
    if any(t in lower for t in STATUS_TRIGGERS):
        return 'status'

    # Cloud security
    if any(t in lower for t in CLOUD_TRIGGERS):
        return 'cloud'

    # CTF solver
    if any(t in lower for t in CTF_TRIGGERS):
        return 'ctf'

    # OPSEC mode
    if any(t in lower for t in OPSEC_TRIGGERS):
        return 'opsec'

    # Post-exploitation
    if any(t in lower for t in POSTEX_TRIGGERS):
        return 'postex'

    # Privilege escalation
    if any(t in lower for t in PRIVESC_TRIGGERS):
        return 'privesc'

    # Lateral movement
    if any(t in lower for t in LATERAL_TRIGGERS):
        return 'lateral'

    # Wireless attacks
    if any(t in lower for t in WIRELESS_TRIGGERS):
        return 'wireless'

    # Social engineering
    if any(t in lower for t in SOCIAL_TRIGGERS):
        return 'social'

    # RocketGod RF tools
    if any(t in lower for t in ROCKETGOD_TRIGGERS):
        return 'rocketgod'

    # BadUSB/Flipper
    if any(t in lower for t in BADUSB_TRIGGERS):
        return 'badusb'

    # Ollama / model queries
    if any(t in lower for t in OLLAMA_TRIGGERS):
        return 'ollama'

    # MCP server
    if any(t in lower for t in MCP_TRIGGERS):
        return 'mcp'

    # Tool execution — original resolver
    if resolve_tool_alias(lower):
        return 'tool'

    # Tool execution — v2 fuzzy match
    tool_v2, conf = fuzzy_match_tool(lower)
    if tool_v2 and conf >= 0.4:
        return 'tool'

    # Bare tool name
    if lower.strip() in [b.lower() for b in BARE_TOOLS]:
        return 'teach'

    # Teach triggers present
    if any(t in lower for t in all_teach):
        return 'teach'

    return 'unknown'
    """
    Classify a raw user command into a routing category.
    Returns one of:
        'teach'      → route to teach engine
        'tool'       → route to tool executor
        'soc'        → route to SOC/blue team actions
        'report'     → route to report generator
        'status'     → route to sysinfo
        'shell'      → passthrough to raw shell
        'rocketgod'  → route to RocketGod RF tools
        'badusb'     → route to BadUSB/Flipper tools
        'ollama'     → route to Ollama AI
        'mcp'        → route to MCP server
        'purple_team'→ route to Purple Team brain mode
        'rag'        → route to RAG knowledge base query
        'unknown'    → fallback to Ollama
    """
    lower = normalize(text)

    # Shell passthrough ($, !)
    if text.startswith(tuple(SHELL_PASSTHROUGH)):
        return 'shell'

    # Purple Team loop (before teach — purple team questions look like teach)
    if any(t in lower for t in PURPLE_TEAM_TRIGGERS):
        return 'purple_team'

    # RAG knowledge base queries
    if any(t in lower for t in RAG_TRIGGERS):
        return 'rag'

    # Teach intent (highest priority for pure teach requests)
    if is_teach_request(lower) and not resolve_tool_alias(lower):
        return 'teach'

    # SOC blue team
    if get_soc_action(lower):
        return 'soc'

    # Report generation
    if any(t in lower for t in REPORT_TRIGGERS):
        return 'report'

    # System status
    if any(t in lower for t in STATUS_TRIGGERS):
        return 'status'

    # Cloud security
    if any(t in lower for t in CLOUD_TRIGGERS):
        return 'cloud'

    # CTF solver
    if any(t in lower for t in CTF_TRIGGERS):
        return 'ctf'

    # OPSEC mode
    if any(t in lower for t in OPSEC_TRIGGERS):
        return 'opsec'

    # Post-exploitation
    if any(t in lower for t in POSTEX_TRIGGERS):
        return 'postex'

    # Privilege escalation
    if any(t in lower for t in PRIVESC_TRIGGERS):
        return 'privesc'

    # Lateral movement
    if any(t in lower for t in LATERAL_TRIGGERS):
        return 'lateral'

    # Wireless attacks
    if any(t in lower for t in WIRELESS_TRIGGERS):
        return 'wireless'

    # Social engineering
    if any(t in lower for t in SOCIAL_TRIGGERS):
        return 'social'

    # RocketGod RF tools
    if any(t in lower for t in ROCKETGOD_TRIGGERS):
        return 'rocketgod'

    # BadUSB/Flipper
    if any(t in lower for t in BADUSB_TRIGGERS):
        return 'badusb'

    # Ollama / model queries
    if any(t in lower for t in OLLAMA_TRIGGERS):
        return 'ollama'

    # MCP server
    if any(t in lower for t in MCP_TRIGGERS):
        return 'mcp'

    # Tool execution
    if resolve_tool_alias(lower):
        return 'tool'

    # Bare tool name (teach it)
    if lower.strip() in [b.lower() for b in BARE_TOOLS]:
        return 'teach'

    # Teach triggers present but tool also present = 'tool' (execute+teach)
    if is_teach_request(lower):
        return 'teach'

    return 'unknown'


# ── Quick test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_phrases = [
        "teach me sqlmap",
        "run nmap on 192.168.1.1",
        "scan 10.0.0.1 for open ports",
        "brute force the ssh login",
        "crack the wpa2 handshake",
        "dump the database",
        "find hidden directories",
        "check for failed logins",
        "who is currently logged in",
        "privilege escalation",
        "explain xss",
        "how does meterpreter work",
        "run a vuln scan",
        "lateral movement",
        "flipper zero ducky script",
        "rocketgod hackrf scan",
        "$ whoami",
    ]
    print("[ERR0RS] Language Layer self-test\n" + "="*50)
    for phrase in test_phrases:
        cat    = classify_command(phrase)
        tool   = resolve_tool_alias(phrase) or "—"
        lesson = resolve_lesson_alias(phrase) or "—"
        print(f"  [{cat:<10}] tool={tool:<14} lesson={lesson:<22} ← '{phrase}'")
    print("="*50)
