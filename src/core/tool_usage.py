"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — TOOL USAGE KNOWLEDGE BASE              ║
║              src/core/tool_usage.py                              ║
║                                                                  ║
║  Real-world usage examples for the Arsenal INFO cards. Each      ║
║  entry gives a student: what the tool is for, the most common    ║
║  invocations with explanations, and the SOC-mentor note on how   ║
║  to use it quietly. This is the "informative info card" layer    ║
║  Eros asked for — teach proper use, with examples, per tool.     ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""
from typing import Dict, List, Optional

# Each entry:
#   summary  — one-line what-it-does
#   examples — list of {cmd, explain} real invocations, simplest first
#   tips     — quick practical/OPSEC notes
USAGE: Dict[str, Dict] = {
    "nmap": {
        "summary": "Network mapper — discovers live hosts, open ports, services, and OS.",
        "examples": [
            {"cmd": "nmap -sV -p 80,443,3000 localhost",
             "explain": "Version-detect on specific ports. Fast, focused, quiet — start here."},
            {"cmd": "nmap -sC -sV 10.0.0.5",
             "explain": "Default NSE scripts + version detection. Good all-round enumeration scan."},
            {"cmd": "nmap -p- --min-rate 1000 10.0.0.5",
             "explain": "All 65535 ports. Thorough but LOUD — only when stealth isn't a concern."},
            {"cmd": "nmap -sn 192.168.1.0/24",
             "explain": "Ping sweep — just find live hosts on the subnet, no port scan."},
        ],
        "tips": [
            "-T2 slows timing to evade rate-based IDS; -T4 is faster but noisier.",
            "-Pn skips host discovery when the target blocks ping.",
            "Add -oN scan.txt to save output for your report.",
        ],
    },
    "nikto": {
        "summary": "Web server scanner — checks for known vulnerabilities and misconfigurations.",
        "examples": [
            {"cmd": "nikto -h http://localhost:3000",
             "explain": "Basic scan of a web app. Needs the server actually running."},
            {"cmd": "nikto -h https://target.com -ssl",
             "explain": "Force SSL for HTTPS targets."},
            {"cmd": "nikto -h http://target -Tuning 4,5,6",
             "explain": "Only run injection / file-retrieval / RCE checks — quieter, focused."},
        ],
        "tips": [
            "Nikto is LOUD — it identifies itself in the User-Agent. Use -useragent to blend in.",
            "-evasion 1 randomizes request encoding to slip past simple IDS.",
            "Target must be reachable first — verify with curl before scanning.",
        ],
    },
    "gobuster": {
        "summary": "Brute-forces hidden directories, files, DNS subdomains, and vhosts.",
        "examples": [
            {"cmd": "gobuster dir -u http://localhost:3000 -w /usr/share/wordlists/dirb/common.txt",
             "explain": "Directory discovery with the common wordlist. The classic first run."},
            {"cmd": "gobuster dir -u http://target -w list.txt -x php,txt,bak",
             "explain": "Also try each word with .php/.txt/.bak extensions."},
            {"cmd": "gobuster dns -d target.com -w subdomains.txt",
             "explain": "Subdomain enumeration via DNS."},
        ],
        "tips": [
            "--threads 5 --delay 250ms keeps the request rate stealthy.",
            "-s 200,301,302 filters to interesting status codes only.",
            "Note the plural: /usr/share/word\u200blists/ (a missing 's' is the #1 typo).",
        ],
    },
    "sqlmap": {
        "summary": "Automated SQL injection detection and exploitation.",
        "examples": [
            {"cmd": "sqlmap -u 'http://target/page?id=1' --batch",
             "explain": "Test a single parameter, auto-answer prompts. Start at default level."},
            {"cmd": "sqlmap -u 'http://target/page?id=1' --dbs",
             "explain": "Enumerate databases once injection is confirmed."},
            {"cmd": "sqlmap -r request.txt --batch --random-agent",
             "explain": "Replay a saved Burp request; rotate User-Agent to dodge WAF."},
        ],
        "tips": [
            "Very LOUD — every request is a textbook attack. Confirm scope first.",
            "--level/--risk default to 1; raise only if nothing fires. Higher = noisier.",
            "--tamper=space2comment helps bypass basic WAF filters.",
        ],
    },
    "hydra": {
        "summary": "Online password brute-forcer for many protocols (SSH, FTP, HTTP, etc.).",
        "examples": [
            {"cmd": "hydra -l admin -P rockyou.txt ssh://10.0.0.5",
             "explain": "Try every password in the list for user 'admin' over SSH."},
            {"cmd": "hydra -L users.txt -p 'Spring2026!' 10.0.0.5 smb",
             "explain": "Password spray — one password across many users. Avoids lockouts."},
        ],
        "tips": [
            "Loudest tool here — every attempt is a logged failed login.",
            "-t 4 -W 5 slows it down to look less like a bot.",
            "Prefer offline cracking (hashcat) whenever you can get a hash instead.",
        ],
    },
    "hashcat": {
        "summary": "GPU/CPU offline password-hash cracker. Silent — never touches the target.",
        "examples": [
            {"cmd": "hashcat -m 0 -a 0 hashes.txt rockyou.txt",
             "explain": "MD5 hashes, straight dictionary attack."},
            {"cmd": "hashcat -m 1000 -a 0 ntlm.txt rockyou.txt -r best64.rule",
             "explain": "NTLM hashes with the best64 mutation rules — cracks most corp passwords."},
            {"cmd": "hashcat -m 5600 netntlmv2.txt rockyou.txt",
             "explain": "Crack NTLMv2 hashes captured by responder."},
        ],
        "tips": [
            "-m is the hash mode — look it up with 'hashcat --help | grep -i <type>'.",
            "Always crack offline on YOUR hardware. Never upload hashes anywhere.",
            "-w 3 sets high workload for faster cracking on the Pi.",
        ],
    },
    "ffuf": {
        "summary": "Fast web fuzzer for directories, parameters, vhosts, and headers.",
        "examples": [
            {"cmd": "ffuf -u http://target/FUZZ -w wordlist.txt",
             "explain": "Directory fuzzing — FUZZ is the injection point."},
            {"cmd": "ffuf -u 'http://target/?FUZZ=x' -w params.txt -mc 200",
             "explain": "Parameter discovery, show only 200 responses."},
            {"cmd": "ffuf -u http://target -H 'Host: FUZZ.target.com' -w subs.txt",
             "explain": "Virtual-host discovery via the Host header."},
        ],
        "tips": [
            "-rate 5 -p 1 throttles to look like one human browsing.",
            "-mc 200,301,302 / -fc 404 filter responses to cut log noise.",
            "-H 'User-Agent: Mozilla/...' hides the default ffuf signature.",
        ],
    },
    "whatweb": {
        "summary": "Passive web fingerprinter — identifies CMS, frameworks, and tech stack.",
        "examples": [
            {"cmd": "whatweb http://target",
             "explain": "Single-request fingerprint. Almost invisible in logs."},
            {"cmd": "whatweb -a 3 http://target",
             "explain": "Aggression level 3 — more probes, more detail, slightly louder."},
        ],
        "tips": [
            "Default -a 1 sends ONE request — the quietest recon you can do on a web app.",
            "Run this BEFORE nikto/gobuster to know what you're dealing with.",
        ],
    },
    "nuclei": {
        "summary": "Template-driven vulnerability scanner for known CVEs and misconfigs.",
        "examples": [
            {"cmd": "nuclei -u http://target",
             "explain": "Run all default templates against one target."},
            {"cmd": "nuclei -u http://target -severity critical,high",
             "explain": "Only high-impact checks — fewer requests, more signal."},
            {"cmd": "nuclei -l urls.txt -tags cve",
             "explain": "Scan a list of URLs for CVE templates specifically."},
        ],
        "tips": [
            "-severity critical,high keeps it focused and quieter.",
            "-rate-limit 50 avoids tripping WAFs (default 150 is aggressive).",
            "Run whatweb/nmap first so you know which templates are relevant.",
        ],
    },
    "metasploit": {
        "summary": "Exploitation framework — verified exploits, payloads, and post-ex modules.",
        "examples": [
            {"cmd": "msfconsole -q",
             "explain": "Start the console quietly (no banner)."},
            {"cmd": "search type:exploit platform:windows smb",
             "explain": "Inside msfconsole — find SMB exploits for Windows."},
            {"cmd": "use exploit/multi/handler",
             "explain": "Set up a listener to catch a reverse shell payload."},
        ],
        "tips": [
            "Very LOUD — payloads have known signatures every EDR catches.",
            "Use staged payloads + StageEncoder to reduce AV detection.",
            "migrate to a stable process immediately after getting a session.",
        ],
    },
    "crackmapexec": {
        "summary": "Active Directory swiss-army knife — auth, enum, and lateral movement.",
        "examples": [
            {"cmd": "crackmapexec smb 10.0.0.0/24",
             "explain": "Sweep a subnet for SMB hosts and their info."},
            {"cmd": "crackmapexec smb 10.0.0.5 -u admin -p 'Pass1' --shares",
             "explain": "Authenticate and list shares on one host."},
            {"cmd": "crackmapexec smb targets.txt -u user -p pass --local-auth",
             "explain": "Spray local creds across many hosts."},
        ],
        "tips": [
            "Spray ONE password across users to avoid account lockouts.",
            "Each attempt is a logged auth event — wide sprays light up the SIEM.",
        ],
    },
    "netcat": {
        "summary": "TCP/UDP swiss-army knife — listeners, reverse shells, file transfer.",
        "examples": [
            {"cmd": "nc -lvnp 4444",
             "explain": "Listen on port 4444 for an incoming reverse shell."},
            {"cmd": "nc -nv 10.0.0.5 80",
             "explain": "Connect to a port to grab a banner or talk to a service."},
            {"cmd": "nc -lvnp 4444 > loot.zip",
             "explain": "Receive a file sent from the target side."},
        ],
        "tips": [
            "Use port 443 for callbacks — blends with HTTPS in egress logs.",
            "Reverse shells beat bind shells — outbound is usually allowed.",
        ],
    },
}


def get_usage(tool: str) -> Optional[Dict]:
    """Return the usage entry for a tool, or None if not covered."""
    return USAGE.get((tool or "").lower())


def list_usage_tools() -> List[str]:
    return sorted(USAGE.keys())
