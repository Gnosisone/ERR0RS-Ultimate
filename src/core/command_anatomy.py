#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — COMMAND ANATOMY ENGINE                  ║
║              src/core/command_anatomy.py                          ║
║                                                                  ║
║  The anti-cookie-cutter layer. Given a REAL command, it breaks   ║
║  it into parts and explains — for every flag, sub-command, and   ║
║  argument — WHAT it is, HOW it acts, and WHY the operator put    ║
║  it there. It recurses into nested payloads (msfconsole -x       ║
║  "use …; set …; run", bash -c "…") and classifies bare           ║
║  arguments (IPs, CIDRs, URLs, ports, wordlists, interfaces,      ║
║  hashes) so the student learns the sentence, not the recipe.     ║
║                                                                  ║
║  Reuses teach_engine.LESSONS[tool]['flags'] as a data source     ║
║  where present, and enriches with a 'why' the reference lacks.   ║
║  Pure stdlib (shlex/re), 100% local, degrades gracefully:        ║
║  an unknown flag is still explained honestly as 'not in the      ║
║  local KB' rather than faked.                                    ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
import shlex
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# ONE-LINE TOOL SUMMARIES  (what the first token actually is)
# ═══════════════════════════════════════════════════════════════════════════

TOOL_SUMMARIES = {
    "msfconsole":  "the Metasploit Framework console — a menu of exploit, payload, and post modules you drive from one prompt.",
    "msfvenom":    "Metasploit's standalone payload generator — mints shellcode/binaries without launching the console.",
    "nmap":        "the network mapper — sends crafted packets to discover hosts, ports, services, and OS.",
    "nxc":         "NetExec (the maintained CrackMapExec fork) — authenticates to and enumerates SMB/LDAP/WinRM/MSSQL across a network.",
    "netexec":     "NetExec — authenticates to and enumerates SMB/LDAP/WinRM/MSSQL across a network.",
    "crackmapexec":"CrackMapExec — the older AD swiss-army knife for auth + enumeration (NetExec is its successor).",
    "hydra":       "an online login brute-forcer — throws username/password guesses at a live service.",
    "sqlmap":      "an automated SQL-injection tool — detects and exploits injectable parameters, can dump databases.",
    "hashcat":     "an offline GPU password cracker — recovers plaintext from captured hashes, never touches the target.",
    "john":        "John the Ripper — offline password cracker, CPU-focused, great at format auto-detection.",
    "gobuster":    "a content/DNS brute-forcer — requests each wordlist entry to find hidden paths or subdomains.",
    "ffuf":        "a fast web fuzzer — replaces a marker in a request with each wordlist entry to find hidden content/params.",
    "nikto":       "a known-vuln web scanner — fires thousands of checks for dangerous files and misconfigs.",
    "nuclei":      "a template-driven vuln scanner — runs YAML checks for specific CVEs and misconfigurations.",
    "impacket-psexec":  "Impacket's PsExec — runs a command / drops a SYSTEM shell over SMB using creds or a hash.",
    "impacket-secretsdump": "Impacket's secretsdump — extracts hashes (SAM/LSA/NTDS/DCSync) from a target.",
    "impacket-getnpusers":  "Impacket's GetNPUsers — AS-REP roasts accounts with Kerberos pre-auth disabled.",
    "impacket-getuserspns": "Impacket's GetUserSPNs — Kerberoasts accounts that have Service Principal Names.",
    "kerbrute":    "a Kerberos username enumerator / password sprayer that reads KDC replies.",
    "responder":   "a LAN poisoner — answers LLMNR/NBT-NS/mDNS broadcasts to capture NTLM hashes.",
    "curl":        "an HTTP(S) client — sends a single crafted request and prints the response.",
    "ssh":         "the secure-shell client — opens an encrypted remote session (and can tunnel/port-forward).",
    "bloodhound-python": "the off-domain BloodHound collector — pulls AD relationships into an ingestible dataset.",
    "ldapsearch":  "an LDAP query client — reads directory objects (users, groups, SPNs), often anonymously.",
}


# ═══════════════════════════════════════════════════════════════════════════
# ARGUMENT CLASSIFIERS  (what a bare, non-flag token most likely is)
# Each: (compiled regex, role, what, why-template).  Order = priority.
# ═══════════════════════════════════════════════════════════════════════════

_ARG_RULES = [
    (re.compile(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$"), "target-range",
     "a CIDR network range (an entire subnet of hosts).",
     "You're pointing the tool at every address in this block, not a single machine."),
    (re.compile(r"^\d{1,3}(\.\d{1,3}){3}$"), "target-host",
     "an IPv4 address — a single target host.",
     "This is the machine the tool will act against."),
    (re.compile(r"^https?://", re.I), "target-url",
     "a target URL.",
     "The tool will send its requests to this web endpoint."),
    (re.compile(r"^[\w.-]+@[\w.-]+$"), "cred-target",
     "a user@host pair — an account and the machine to use it on.",
     "You're supplying both WHO to authenticate as and WHERE."),
    (re.compile(r"\.(txt|lst|dic|wordlist)$", re.I), "wordlist",
     "a wordlist file.",
     "Each line becomes one guess/candidate the tool will try."),
    (re.compile(r"^(eth|wlan|tun|tap|en|wlp|mon)\d", re.I), "interface",
     "a network interface name.",
     "You're telling the tool which NIC to listen on or send from."),
    (re.compile(r"^[a-f0-9]{32}$", re.I), "hash-md5",
     "a 32-hex-char value — looks like an NT/MD5 hash.",
     "For pass-the-hash / cracking, this is the credential material itself."),
    (re.compile(r"^[a-f0-9]{40,}$", re.I), "hash",
     "a long hex value — looks like a hash.",
     "Likely the hash to crack or to authenticate with."),
    (re.compile(r"\.(pcap|pcapng|cap)$", re.I), "capture",
     "a packet-capture file.",
     "The tool will read traffic from this file instead of sniffing live."),
    (re.compile(r"\.[a-z0-9]{1,4}$", re.I), "file",
     "a file path.",
     "An input the tool reads or an output it writes."),
    (re.compile(r"^[\w.-]+\.[a-z]{2,}$", re.I), "domain",
     "a domain name.",
     "The tool will resolve and target this domain."),
]


def _classify_arg(token: str) -> Dict:
    """Best-effort classification of a bare argument token."""
    for rx, role, what, why in _ARG_RULES:
        if rx.search(token):
            return {"token": token, "role": role, "what": what, "why": why}
    return {"token": token, "role": "argument",
            "what": "a positional argument.",
            "why": "A value this tool consumes directly (target, name, or option value)."}


# ═══════════════════════════════════════════════════════════════════════════
# METASPLOIT CONSOLE KNOWLEDGE
# The -x payload is a mini-script of console commands; we explain each verb,
# and the datastore OPTIONS (RHOSTS/LHOST/…) that trip students up most.
# ═══════════════════════════════════════════════════════════════════════════

MSF_VERBS = {
    "use":     ("load a module into the current context.",
                "The path is a namespace you walk on YOUR OWN machine (e.g. exploit → windows → smb → the module). "
                "Loading it touches nothing on the target — it just arms the tool."),
    "set":     ("assign a value to a module option for THIS session.",
                "This is how you tell the loaded module its target, payload, and callback details."),
    "setg":    ("set a GLOBAL option that persists across modules.",
                "Handy for values you reuse (LHOST), so you don't retype them for every module."),
    "unset":   ("clear a previously set option.",
                "Resets a value back to default — useful when reusing a module for a new target."),
    "run":     ("launch the loaded module against its configured options.",
                "For an exploit this fires it at RHOSTS and, on success, delivers the PAYLOAD."),
    "exploit": ("launch the loaded exploit (an alias of run).",
                "Same as run; fires the exploit and opens a session if it lands."),
    "check":   ("test whether the target is vulnerable WITHOUT exploiting.",
                "The quiet, safe pre-flight — confirms the bug before you make noise firing it."),
    "search":  ("find modules by name/CVE/platform.",
                "Locates the right module path before you 'use' it."),
    "show":    ("list options/payloads/targets for the current module.",
                "'show options' is how you see what still needs setting before run."),
    "sessions":("list or interact with open sessions.",
                "After a successful exploit, this is where your shells live."),
    "back":    ("leave the current module context.",
                "Returns you to the top prompt to load something else."),
    "info":    ("print full documentation for the current/named module.",
                "Read this to understand a module's options and targets before firing."),
}

# Datastore options students most often misread.
MSF_OPTIONS = {
    "rhosts":   ("Remote HOSTS — the TARGET(s).",
                 "This is WHO you're attacking. Accepts a single IP, a range, or a file."),
    "rhost":    ("Remote HOST — the single TARGET.",
                 "The machine the module acts against."),
    "rport":    ("Remote PORT — the target's service port.",
                 "Where on the target the module connects (e.g. 445 for SMB)."),
    "lhost":    ("Local HOST — YOUR listener address (the connection back to you).",
                 "The payload calls home to this IP, so it must be an address the target can reach — usually your VPN/tun0 IP."),
    "lport":    ("Local PORT — the port YOUR listener waits on.",
                 "The payload connects back to LHOST on this port; 443 blends with HTTPS egress."),
    "payload":  ("the code that runs ON the target after the exploit succeeds.",
                 "Chooses what you get — a reverse shell, a meterpreter session, etc. — and how it calls back."),
    "srvhost":  ("the address ERR0RS/MSF binds its own delivery server to.",
                 "For exploits that serve a file/URL to the target."),
    "targeturi":("the URL path to the vulnerable endpoint on the target.",
                 "Points a web exploit at the exact vulnerable route."),
    "target":   ("the target index — which OS/build variant to exploit.",
                 "Picks the right offsets/technique for the specific target platform."),
    "smbuser":  ("the SMB username to authenticate as.", "Credential half of an authenticated module."),
    "smbpass":  ("the SMB password (or hash) to authenticate with.", "Credential half of an authenticated module."),
}


# ═══════════════════════════════════════════════════════════════════════════
# FLAG KNOWLEDGE BASE
# FLAG_KB[tool][flag] = {"what":…, "why":…, "arg": bool}
#   arg=True  → this flag consumes the NEXT token as its value.
# We deliberately seed the tools the operator lives in; unknown flags still
# get an honest, non-faked explanation via the resolver's fallback.
# ═══════════════════════════════════════════════════════════════════════════

FLAG_KB: Dict[str, Dict[str, Dict]] = {

    "msfconsole": {
        "-q": {"what": "quiet start.", "arg": False,
               "why": "Suppresses the banner/version splash so the console comes up clean and fast — and a hair lower-profile."},
        "-x": {"what": "execute these console commands immediately on startup.", "arg": True,
               "why": "Automates what you'd otherwise type at the msf prompt. The quoted string is a mini-script of console commands separated by ';'. This is what makes the launch one-shot."},
        "-r": {"what": "run a resource (script) file of console commands.", "arg": True,
               "why": "Like -x but reads the commands from a .rc file — better for long, reusable automation."},
        "-n": {"what": "disable database support.", "arg": False,
               "why": "Skips connecting to the Postgres workspace when you don't need stored hosts/loot."},
        "-v": {"what": "print version and exit.", "arg": False,
               "why": "Just a version check."},
    },

    "nmap": {
        "-sS": {"what": "SYN 'stealth' scan.", "arg": False,
                "why": "Sends only a SYN and reads the reply, never completing the handshake — faster and quieter (needs root)."},
        "-sT": {"what": "full TCP connect scan.", "arg": False,
                "why": "Completes the handshake; works without root but is louder and logged by the target."},
        "-sU": {"what": "UDP scan.", "arg": False,
                "why": "Probes UDP services (DNS, SNMP) that a TCP scan misses entirely."},
        "-sV": {"what": "service/version detection.", "arg": False,
                "why": "Banner-grabs each open port so you know WHAT is listening, not just that something is."},
        "-sC": {"what": "run the default NSE scripts.", "arg": False,
                "why": "Adds a batch of safe enumeration checks (a lightweight 'what's interesting here?')."},
        "-O":  {"what": "OS detection.", "arg": False,
                "why": "Fingerprints TCP/IP stack quirks to guess the operating system."},
        "-A":  {"what": "aggressive scan.", "arg": False,
                "why": "Bundles -sV, -O, default scripts, and traceroute — thorough but loud."},
        "-p-": {"what": "scan ALL 65535 ports.", "arg": False,
                "why": "Catches services hiding on non-standard ports that the default top-1000 would miss."},
        "-p":  {"what": "scan specific port(s).", "arg": True,
                "why": "Restricts the scan to the ports you name (e.g. 445 or 1-1000)."},
        "-F":  {"what": "fast scan (top 100 ports).", "arg": False,
                "why": "Quick triage when you just want the obvious services."},
        "-Pn": {"what": "skip host discovery — treat all hosts as up.", "arg": False,
                "why": "Bypasses the ping check for targets that block ICMP but are actually alive."},
        "-sn": {"what": "ping sweep only, no port scan.", "arg": False,
                "why": "Just enumerates which hosts are live — the map before the scan."},
        "-T4": {"what": "timing template 4 (aggressive).", "arg": False,
                "why": "Speeds the scan up; drop to -T2/-T1 when you need to stay quiet."},
        "--min-rate": {"what": "minimum packets per second.", "arg": True,
                       "why": "Forces a throughput floor so big scans finish in reasonable time."},
        "--script": {"what": "run named NSE script(s).", "arg": True,
                     "why": "Targeted deep checks (e.g. --script vuln for known CVEs)."},
        "-oN": {"what": "write normal output to a file.", "arg": True,
                "why": "Saves human-readable results for your notes/report."},
        "-oA": {"what": "write output in all formats.", "arg": True,
                "why": "Normal + XML + grepable at once — XML feeds other tools."},
    },

    "hydra": {
        "-l": {"what": "single login name.", "arg": True, "why": "Fixes the username so you're guessing only the password."},
        "-L": {"what": "login-name list file.", "arg": True, "why": "Tries many usernames from a file."},
        "-p": {"what": "single password.", "arg": True, "why": "Fixes the password (spray one password at many users)."},
        "-P": {"what": "password list file.", "arg": True, "why": "The wordlist of passwords to try."},
        "-t": {"what": "parallel tasks (threads).", "arg": True, "why": "More threads = faster, but too many trips rate-limits/lockouts. Keep low for SSH."},
        "-s": {"what": "target port.", "arg": True, "why": "Use when the service runs on a non-default port."},
        "-f": {"what": "stop after the first valid pair.", "arg": False, "why": "Quit once you've got one hit instead of grinding the whole list."},
        "-V": {"what": "verbose — show each attempt.", "arg": False, "why": "Watch progress live (noisy output)."},
    },

    "sqlmap": {
        "-u":       {"what": "the target URL.", "arg": True, "why": "The endpoint (with a parameter) to test for injection."},
        "-r":       {"what": "read the request from a saved file.", "arg": True, "why": "Feeds a full Burp request so POST bodies/headers/cookies are preserved exactly."},
        "--batch":  {"what": "never prompt — accept defaults.", "arg": False, "why": "Runs unattended; essential for scripting."},
        "--dbs":    {"what": "enumerate databases.", "arg": False, "why": "First thing after confirming injection — see what schemas exist."},
        "--dump":   {"what": "dump table contents.", "arg": False, "why": "Extracts the actual rows once you've found a target table."},
        "-T":       {"what": "target table.", "arg": True, "why": "Restricts --dump to one table (e.g. users)."},
        "--level":  {"what": "test thoroughness (1-5).", "arg": True, "why": "Higher tests more params/headers but is slower and louder."},
        "--risk":   {"what": "risk of injected payloads (1-3).", "arg": True, "why": "Higher allows heavier payloads that can modify data — escalate gradually."},
    },

    "nxc": {
        "-u": {"what": "username (or user-list file).", "arg": True, "why": "WHO you authenticate as against the target service."},
        "-p": {"what": "password (or password-list file).", "arg": True, "why": "The secret to try; with a list this becomes a spray."},
        "-H": {"what": "NT hash instead of a password.", "arg": True, "why": "Pass-the-Hash — authenticate with the hash directly, no plaintext needed."},
        "-x": {"what": "run a CMD command on success.", "arg": True, "why": "Executes on hosts where auth works (proof of access / quick recon)."},
        "-X": {"what": "run a PowerShell command on success.", "arg": True, "why": "Same as -x but via PowerShell."},
        "-d": {"what": "domain.", "arg": True, "why": "The AD domain to authenticate against (omit + --local-auth for local accounts)."},
        "--shares":     {"what": "list SMB shares and your access.", "arg": False, "why": "Quick read of what's reachable per share."},
        "--local-auth": {"what": "authenticate against the local SAM, not the domain.", "arg": False, "why": "For local accounts (e.g. local Administrator) — loud on that host, no DC involved."},
        "--rid-brute":  {"what": "enumerate users by cycling RIDs.", "arg": False, "why": "Pulls the user list even from a weak/guest session."},
        "--continue-on-success": {"what": "keep going after the first valid credential.", "arg": False, "why": "In a spray, find EVERY hit, not just the first."},
    },

    "hashcat": {
        "-m": {"what": "hash mode (which algorithm).", "arg": True, "why": "MUST match the hash type (0=MD5, 1000=NTLM, 13100=Kerberoast, 18200=AS-REP). Wrong mode = zero cracks."},
        "-a": {"what": "attack mode.", "arg": True, "why": "0=straight wordlist, 3=brute/mask, 6/7=hybrid. Picks HOW candidates are generated."},
        "-r": {"what": "rules file.", "arg": True, "why": "Mutates each word (capitalize, append digits) to multiply coverage from one list."},
        "-o": {"what": "output file for cracked results.", "arg": True, "why": "Where recovered plaintexts are written."},
        "--force": {"what": "ignore warnings.", "arg": False, "why": "Pushes past driver/temperature warnings (use knowingly)."},
    },

    "gobuster": {
        "dir":  {"what": "directory/file brute-force mode.", "arg": False, "why": "Hunts hidden web paths."},
        "dns":  {"what": "subdomain brute-force mode.", "arg": False, "why": "Hunts subdomains of a domain."},
        "-u":   {"what": "target URL.", "arg": True, "why": "The base to append wordlist entries to."},
        "-w":   {"what": "wordlist file.", "arg": True, "why": "Each line is a path/subdomain candidate."},
        "-x":   {"what": "file extensions to append.", "arg": True, "why": "Also try word.php, word.txt, etc."},
        "-t":   {"what": "concurrent threads.", "arg": True, "why": "Throughput vs. load on the target."},
    },

    "ffuf": {
        "-u": {"what": "target URL with a FUZZ marker.", "arg": True, "why": "ffuf swaps FUZZ for each wordlist entry — the marker is where the injection happens."},
        "-w": {"what": "wordlist file.", "arg": True, "why": "Supplies the values that replace FUZZ."},
        "-fc":{"what": "filter out these HTTP status codes.", "arg": True, "why": "Hides noise (e.g. 404) so real hits stand out."},
        "-mc":{"what": "match only these status codes.", "arg": True, "why": "Keep only responses you care about (e.g. 200,301)."},
        "-fs":{"what": "filter by response size.", "arg": True, "why": "Drops the uniform 'not found' size so anomalies surface."},
    },

    "curl": {
        "-X": {"what": "HTTP method.", "arg": True, "why": "GET/POST/PUT/… — chooses the verb the server sees."},
        "-H": {"what": "add a request header.", "arg": True, "why": "Set auth tokens, content-type, or spoofed headers."},
        "-d": {"what": "request body data (implies POST).", "arg": True, "why": "The payload you send to the endpoint."},
        "-k": {"what": "ignore TLS certificate errors.", "arg": False, "why": "Talk to self-signed/lab hosts without cert complaints."},
        "-s": {"what": "silent mode.", "arg": False, "why": "Suppresses the progress meter for clean, scriptable output."},
        "-i": {"what": "include response headers in output.", "arg": False, "why": "See status + headers, not just the body."},
        "-o": {"what": "write output to a file.", "arg": True, "why": "Save the response instead of printing it."},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def _tool_name(token: str) -> str:
    """Normalise the first token to a bare tool name (strip path, lowercase)."""
    name = token.split("/")[-1].strip().lower()
    return name


def _teach_flags(tool: str) -> Dict[str, str]:
    """Reuse teach_engine.LESSONS[tool]['flags'] as a secondary source.

    Lazy, guarded import so command_anatomy never hard-depends on the teach
    engine — if it's missing we simply lose the enrichment, not the feature.
    """
    try:
        from src.education_new.teach_engine import LESSONS
    except Exception:
        return {}
    lesson = LESSONS.get(tool)
    if not lesson:
        return {}
    return lesson.get("flags", {}) or {}


def _resolve_flag(tool: str, flag: str, use_help: bool = False) -> Dict:
    """Explain a flag: FLAG_KB first (has the 'why'), then teach_engine's
    flags (has a 'what'), then the tool's own --help/man (if use_help), then
    an honest 'not in local KB' fallback."""
    kb = FLAG_KB.get(tool, {})
    if flag in kb:
        info = kb[flag]
        return {"what": info["what"], "why": info["why"], "arg": info.get("arg", False)}
    # Secondary: teach engine flag text (what only) — infer arg heuristically.
    tf = _teach_flags(tool)
    if flag in tf:
        return {"what": tf[flag], "why": "(from the tool reference)", "arg": False}
    # Tertiary: the tool's OWN help output — long-tail coverage, offline.
    if use_help:
        try:
            from src.core.help_parser import flag_help
            desc = flag_help(tool, flag)
        except Exception:
            desc = None
        if desc:
            return {"what": desc, "why": f"(parsed from `{tool} --help`)", "arg": False}
    # Honest fallback — never fake it.
    return {"what": "a flag not in the local knowledge base.",
            "why": f"Check `{tool} --help` or `man {tool}` for its exact effect.",
            "arg": False}


def _explain_module_path(path: str) -> str:
    """Explain an msf module path as a namespace walk on the operator's box."""
    segs = [s for s in path.split("/") if s]
    kind = segs[0] if segs else path
    gloss = {
        "exploit":   "an exploit module",
        "auxiliary": "an auxiliary (scanner/enum) module",
        "post":      "a post-exploitation module",
        "payload":   "a payload",
        "encoder":   "an encoder",
        "nop":       "a NOP generator",
    }.get(kind, "a module")
    trail = " → ".join(segs) if segs else path
    return (f"loads {gloss}. The '/'-path is a namespace you traverse on YOUR OWN "
            f"machine ({trail}) — loading it arms Metasploit locally; nothing "
            f"touches the target yet.")


def _explain_msf_payload(payload: str) -> List[Dict]:
    """Break an msfconsole -x payload (';'-separated console commands) into
    explained sub-parts — the recursion that makes `-x "use…;set…;run"` teachable."""
    subparts: List[Dict] = []
    for raw in payload.split(";"):
        raw = raw.strip()
        if not raw:
            continue
        try:
            toks = shlex.split(raw)
        except ValueError:
            toks = raw.split()
        if not toks:
            continue
        verb = toks[0].lower()
        entry: Dict = {"token": raw, "role": "msf-cmd", "verb": verb}
        vinfo = MSF_VERBS.get(verb)
        if vinfo:
            entry["what"], entry["why"] = vinfo
        else:
            entry["what"] = "a console command."
            entry["why"] = "Runs inside the Metasploit session."

        if verb == "use" and len(toks) > 1:
            entry["operand"] = toks[1]
            entry["operand_note"] = _explain_module_path(toks[1])
        elif verb in ("set", "setg", "unset") and len(toks) >= 2:
            opt = toks[1].lower()
            val = " ".join(toks[2:]) if len(toks) > 2 else ""
            entry["operand"] = f"{toks[1]} {val}".strip()
            oinfo = MSF_OPTIONS.get(opt)
            if oinfo:
                entry["operand_note"] = f"{oinfo[0]} {oinfo[1]}"
            else:
                entry["operand_note"] = "a module option — set 'show options' to see them all."
        subparts.append(entry)
    return subparts


def explain_command(command: str, use_help: bool = False) -> Dict:
    """Break a full command into explained parts.

    With use_help=True, unknown flags fall back to parsing the tool's own
    --help/man output (long-tail coverage; runs a guarded subprocess).

    Returns: {command, tool, tool_summary, parts[], plain_english}. Each part
    has token/role/what/why (+ value, +sub for nested payloads). Never raises
    on odd input — worst case it classifies tokens generically.
    """
    command = (command or "").strip()
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return {"command": command, "tool": "", "tool_summary": "",
                "parts": [], "plain_english": "Nothing to explain."}

    tool = _tool_name(tokens[0])
    tool_summary = TOOL_SUMMARIES.get(tool, f"the `{tool}` command.")
    parts: List[Dict] = []

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        # Sub-command (e.g. gobuster dir, gobuster dns) — non-dash token the KB knows.
        if not tok.startswith("-") and tool in FLAG_KB and tok in FLAG_KB[tool]:
            info = FLAG_KB[tool][tok]
            parts.append({"token": tok, "role": "subcommand",
                          "what": info["what"], "why": info["why"]})
            i += 1
            continue

        if tok.startswith("-"):
            info = _resolve_flag(tool, tok, use_help=use_help)
            part = {"token": tok, "role": "flag",
                    "what": info["what"], "why": info["why"]}
            if info["arg"] and i + 1 < len(tokens):
                val = tokens[i + 1]
                part["value"] = val
                # The star case: msfconsole -x <payload> → recurse into it.
                if tool == "msfconsole" and tok == "-x":
                    part["sub"] = _explain_msf_payload(val)
                else:
                    part["value_note"] = _classify_arg(val)["what"]
                i += 2
                parts.append(part)
                continue
            parts.append(part)
            i += 1
            continue

        # Bare positional argument.
        parts.append(_classify_arg(tok))
        i += 1

    return {
        "command":       command,
        "tool":          tool,
        "tool_summary":  tool_summary,
        "parts":         parts,
        "plain_english": _plain_english(tool, parts),
    }


def _plain_english(tool: str, parts: List[Dict]) -> str:
    """Stitch a short narrative that reflects THIS command (not a template)."""
    target = module = callback = None

    def scan(ps: List[Dict]) -> None:
        nonlocal target, module, callback
        for p in ps:
            role = p.get("role")
            if role in ("target-host", "target-range") and not target:
                target = p["token"]
            if p.get("verb") == "use" and not module:
                module = p.get("operand")
            if p.get("verb") in ("set", "setg"):
                op = (p.get("operand") or "")
                low = op.lower()
                if low.startswith("rhost") and not target:
                    target = op.split()[-1]
                if low.startswith("lhost") and not callback:
                    callback = op.split()[-1]
            if p.get("sub"):
                scan(p["sub"])

    scan(parts)
    s = f"In plain English — you're driving {tool}: {TOOL_SUMMARIES.get(tool, '')}".rstrip()
    tail = []
    if module:
        tail.append(f"you load {module} (armed on your box, target untouched)")
    if target:
        tail.append(f"aim it at {target} (the target)")
    if callback:
        tail.append(f"set the payload to call home to {callback} (you)")
    if tail:
        s += "  Here, " + ", ".join(tail) + ", then fire it."
    return s


# ═══════════════════════════════════════════════════════════════════════════
# RENDER + PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def format_anatomy(command: str, use_help: bool = True) -> str:
    """Render a command breakdown as a terminal-friendly lesson.

    use_help defaults True here (the CLI-facing renderer) so unknown flags get
    explained from the tool's own --help; the pure explain_command default
    stays False for fast, deterministic programmatic use."""
    data = explain_command(command, use_help=use_help)
    if not data["tool"]:
        return "  Nothing to break down."
    bar = "═" * 60
    out = [bar,
           f"  🔬 COMMAND ANATOMY",
           f"  $ {data['command']}",
           bar,
           f"  ▸ {data['tool']} — {data['tool_summary']}",
           ""]
    for p in data["parts"]:
        tok = p["token"]
        out.append(f"  ┌─ {tok}")
        out.append(f"  │   WHAT: {p.get('what','')}")
        if p.get("why"):
            out.append(f"  │   WHY:  {p['why']}")
        if p.get("value") and "sub" not in p:
            note = f"  ({p['value_note']})" if p.get("value_note") else ""
            out.append(f"  │   VALUE: {p['value']}{note}")
        for sp in p.get("sub", []):
            out.append(f"  │   • {sp['token']}")
            out.append(f"  │       {sp.get('what','')}")
            if sp.get("why"):
                out.append(f"  │       {sp['why']}")
            if sp.get("operand_note"):
                out.append(f"  │       ↳ {sp['operand']}: {sp['operand_note']}")
        out.append("  └─")
    out += ["", "  " + "─" * 56, f"  {data['plain_english']}", bar]
    return "\n".join(out)


def is_command(text: str) -> bool:
    """Heuristic: does this look like a runnable command (vs. a topic query)?

    True only when the first token is a tool we know AND there's at least one
    argument/flag after it — so a bare 'nmap' stays a normal lesson, while
    'nmap -sV 10.0.0.5' becomes an anatomy breakdown.
    """
    toks = (text or "").strip().split()
    if len(toks) < 2:
        return False
    tool = _tool_name(toks[0])
    return tool in TOOL_SUMMARIES or tool in FLAG_KB


def anatomy_json(command: str, use_help: bool = False) -> Dict:
    """Structured breakdown for the API/frontend."""
    return explain_command(command, use_help=use_help)
