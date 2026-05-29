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
