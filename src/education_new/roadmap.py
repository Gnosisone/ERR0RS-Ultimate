#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — LEARNING ROADMAP                        ║
║              src/education_new/roadmap.py                         ║
║                                                                  ║
║  The ordered curriculum: WHAT to learn, in WHAT order, and WHY   ║
║  each stage sits where it does. Distinct from progression.py     ║
║  (which tracks XP/how-much-you've-done) — this answers           ║
║  "what should I learn next, and why is it next?"                 ║
║                                                                  ║
║  Each stage carries the reasoning (prerequisite logic), the key  ║
║  topics, a concrete "you're ready when…" gate, teach-engine      ║
║  cross-links, and the progression skill-domain it builds.        ║
║                                                                  ║
║  Pure data + stdlib. Cross-links degrade gracefully.             ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Ordered because the order IS the lesson: each stage is the prerequisite for
# attacking the next. You can't exploit what you can't enumerate, can't
# enumerate what you can't navigate, and can't write an exploit for a system
# whose kernel you don't understand.
ROADMAP: List[Dict] = [
    {
        "n": 1, "name": "Networking", "domain": "network", "time": "weeks",
        "why": ("Every attack is packets on a wire. If TCP/IP, DNS, routing, and "
                "the OSI model are fuzzy, everything above collapses — you must be "
                "able to read a packet before you can forge one."),
        "topics": ["TCP/IP", "DNS", "HTTP", "subnetting", "ports & protocols", "Wireshark"],
        "gate":   "you can explain the TCP 3-way handshake and read a pcap without googling.",
        "see":    ["wireshark", "nmap"],
    },
    {
        "n": 2, "name": "Linux", "domain": "network", "time": "weeks",
        "why": ("Your tools live here and half your targets run it. The shell, "
                "permissions, and processes are the ground you stand on for "
                "everything that follows."),
        "topics": ["bash", "file permissions", "processes", "systemd", "SUID", "pipes"],
        "gate":   "you live in the terminal and SUID/permissions make intuitive sense.",
        "see":    ["privilege escalation", "linux"],
    },
    {
        "n": 3, "name": "Python", "domain": "network", "time": "weeks",
        "why": ("The moment a tool doesn't exist, you write it. Automation, exploit "
                "tweaking, and parsing tool output all need code — Python is the "
                "lingua franca of security scripting."),
        "topics": ["sockets", "requests", "argparse", "file I/O", "pwntools basics"],
        "gate":   "you can script a port scanner and parse tool output yourself.",
        "see":    ["python"],
    },
    {
        "n": 4, "name": "Web", "domain": "web_app", "time": "weeks",
        "why": ("The internet is web apps, so most real targets are too. The OWASP "
                "Top 10 is the highest-ROI attack surface you'll ever learn."),
        "topics": ["Burp Suite", "SQLi", "XSS", "SSRF", "auth flaws", "OWASP Top 10"],
        "gate":   "you can find and exploit an SQLi and an XSS end-to-end.",
        "see":    ["sql injection", "xss", "burp suite", "sqlmap"],
    },
    {
        "n": 5, "name": "Active Directory", "domain": "active_dir", "time": "months",
        "why": ("~95% of enterprises run AD. Corporate pentesting IS AD attacking — "
                "Kerberos, ACLs, lateral movement. This is where the job lives."),
        "topics": ["Kerberos", "BloodHound", "NTLM", "ACL abuse", "delegation", "DCSync"],
        "gate":   "you can walk a lab domain from null session to Domain Admin.",
        "see":    ["lateral movement", "bloodhound", "kerberos", "pass-the-hash"],
    },
    {
        "n": 6, "name": "Cloud", "domain": "network", "time": "months",
        "why": ("The perimeter moved to AWS/Azure/GCP. IAM misconfigurations are the "
                "new open share, and on-prem skills don't transfer for free."),
        "topics": ["IAM", "S3/blob", "metadata SSRF", "Azure AD", "GCP IAM", "ScoutSuite"],
        "gate":   "you can enumerate cloud IAM and spot a privilege-escalation path.",
        "see":    ["ssrf", "cloud"],
    },
    {
        "n": 7, "name": "Red Team", "domain": "network", "time": "months",
        "why": ("Now you chain it. Full-kill-chain operations under stealth "
                "constraints, C2, and evasion — the difference between running "
                "tools and running an operation."),
        "topics": ["C2 (Sliver/Havoc)", "MITRE ATT&CK", "evasion", "OpSec", "LOLBins"],
        "gate":   "you can run a stealthy end-to-end engagement and evade basic EDR.",
        "see":    ["command and control", "defense evasion", "mitre overview"],
    },
    {
        "n": 8, "name": "Malware Analysis", "domain": "forensics", "time": "months",
        "why": ("To evade defenses you must understand what defenders analyze. "
                "Reversing malware teaches you how detection works from the inside."),
        "topics": ["x86/x64 asm", "static analysis", "dynamic analysis", "PE format"],
        "gate":   "you can reverse a simple sample and explain its behavior.",
        "see":    ["defense evasion"],
    },
    {
        "n": 9, "name": "Kernel", "domain": "forensics", "time": "months",
        "why": ("The deepest persistence and the strongest evasion live in ring 0. "
                "Rootkits, driver exploits, and EDR bypasses require understanding "
                "the OS from underneath."),
        "topics": ["syscalls", "drivers", "memory management", "kernel debugging"],
        "gate":   "you understand user↔kernel transitions and can debug a driver.",
        "see":    [],
    },
    {
        "n": 10, "name": "Exploit Development", "domain": "network", "time": "the long game",
        "why": ("The summit: finding and weaponizing your own 0-days. Everything "
                "before this — networking, code, kernel — was the foundation this "
                "stands on. This is original research."),
        "topics": ["fuzzing", "ROP", "heap exploitation", "ASLR/DEP bypass", "shellcoding"],
        "gate":   "you can find a memory-corruption bug and write a working exploit (never really ends).",
        "see":    [],
    },
]

_BY_NAME = {s["name"].lower(): s for s in ROADMAP}


def get_roadmap() -> List[Dict]:
    """The full ordered curriculum."""
    return ROADMAP


def get_stage(ref) -> Optional[Dict]:
    """Look up a stage by number (1-based) or by name (case-insensitive)."""
    if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
        n = int(ref)
        return ROADMAP[n - 1] if 1 <= n <= len(ROADMAP) else None
    return _BY_NAME.get(str(ref).strip().lower())


def next_stage(current) -> Optional[Dict]:
    """The stage after `current` (by number or name), or None if at the summit."""
    stage = get_stage(current)
    if not stage:
        return None
    nxt = stage["n"] + 1
    return ROADMAP[nxt - 1] if nxt <= len(ROADMAP) else None


def format_stage(stage: Dict) -> str:
    """Render one stage as a terminal block."""
    out = [f"  STAGE {stage['n']:>2} — {stage['name'].upper()}   ({stage['time']})",
           "  " + "─" * 54,
           "  WHY HERE:"]
    _wrap(out, stage["why"], "    ")
    out.append("  KEY TOPICS: " + ", ".join(stage["topics"]))
    out.append(f"  ✓ READY WHEN: {stage['gate']}")
    if stage.get("see"):
        out.append("  LEARN NOW:  " + "  ".join(f"`teach me {t}`" for t in stage["see"]))
    return "\n".join(out)


def format_roadmap(highlight: Optional[str] = None) -> str:
    """Render the whole path; optionally mark the operator's current stage."""
    hl = get_stage(highlight)["n"] if highlight and get_stage(highlight) else None
    bar = "═" * 58
    out = [bar, "  🗺  ERR0RS LEARNING ROADMAP", bar,
           "  The order is the lesson: each stage unlocks the next.", ""]
    for s in ROADMAP:
        marker = "▶" if s["n"] == hl else ("✓" if hl and s["n"] < hl else "·")
        out.append(f"  {marker} {s['n']:>2}. {s['name']:<20} {s['time']}")
    out.append("")
    out.append("  Type `roadmap <n>` or `roadmap <name>` for the full stage detail.")
    out.append(bar)
    return "\n".join(out)


def _wrap(out: List[str], text: str, indent: str, width: int = 56) -> None:
    import textwrap
    for line in textwrap.wrap(text, width=width):
        out.append(indent + line)
