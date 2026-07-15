#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — OUTPUT ANATOMY (RESULTS LITERACY)       ║
║              src/core/output_anatomy.py                          ║
║                                                                  ║
║  The follow-up every lesson was missing. command_anatomy         ║
║  explains the command you TYPE; this explains the data you GET   ║
║  BACK. For each tool: an annotated sample of real output, where  ║
║  every field is broken down into what it MEANS and what          ║
║  DECISION it drives — plus a reference for the tool's output     ║
║  'grammar' (states/status codes) and the misreads that burn      ║
║  students.                                                        ║
║                                                                  ║
║  The teaching arc is now complete:                               ║
║    lesson (how to run) → output_anatomy (how to read the         ║
║    results) → output_interpreter (act on YOUR live results).     ║
║                                                                  ║
║  Pure data + stdlib. Extend OUTPUT_LESSONS to cover more tools.  ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Alias map so "netexec"/"cme" reach the "nxc" lesson, etc.
_ALIASES = {
    "netexec": "nxc", "crackmapexec": "nxc", "cme": "nxc",
    "john": "hashcat",  # cracking output reads similarly enough to redirect
}


OUTPUT_LESSONS: Dict[str, Dict] = {

    "nmap": {
        "tool": "nmap",
        "headline": "An nmap report is a map of doors: which are open, what's behind them, and how sure you are.",
        "sample": (
            "Nmap scan report for 10.0.0.10\n"
            "Host is up (0.0011s latency).\n"
            "Not shown: 997 closed tcp ports (reset)\n"
            "PORT     STATE    SERVICE       VERSION\n"
            "22/tcp   open     ssh           OpenSSH 8.2p1 Ubuntu\n"
            "445/tcp  open     microsoft-ds  Samba smbd 4.6.2\n"
            "8080/tcp filtered http-proxy"
        ),
        "reading": [
            {"field": "Host is up (0.0011s latency)",
             "means": "The host answered. ~1ms latency = same LAN segment; tens/hundreds of ms = remote or tunnelled.",
             "do": "Proceed. If it says 'host seems down' but you know it's alive, add -Pn (it's blocking ping)."},
            {"field": "Not shown: 997 closed ports (reset)",
             "means": "997 ports actively REFUSED you (sent a TCP reset). The host is reachable; those services just aren't running.",
             "do": "Contrast with 'filtered' below — closed = reachable+empty, filtered = something is dropping you."},
            {"field": "22/tcp",
             "means": "Port number + transport protocol. The service lives on TCP port 22.",
             "do": "Map the port to its likely service and attack surface."},
            {"field": "STATE = open",
             "means": "The port completed a connection — a live, reachable service.",
             "do": "This is where you enumerate. Every 'open' is a candidate foothold."},
            {"field": "STATE = filtered (8080)",
             "means": "No usable reply came back — a firewall is DROPPING packets. You cannot confirm if the service exists.",
             "do": "Don't treat as a finding yet. Try different timing (-T2), source port tricks, or accept it's blocked."},
            {"field": "SERVICE = ssh",
             "means": "WITHOUT -sV this is just nmap's guess from the port number (22 → 'probably ssh'), not confirmation.",
             "do": "Never trust the bare service name for exploitation — confirm with -sV."},
            {"field": "VERSION = OpenSSH 8.2p1 Ubuntu",
             "means": "The REAL software + version (only present with -sV). Also leaks the OS (Ubuntu).",
             "do": "searchsploit/CVE-search this exact string. Version is what turns 'a service' into 'a specific vulnerable service'."},
        ],
        "reference": {
            "title": "The six port STATES (learn these cold)",
            "rows": [
                ("open", "service accepted a connection — your target"),
                ("closed", "host reachable, port refused (RST) — no service here"),
                ("filtered", "no reply — a firewall dropped it; existence unknown"),
                ("open|filtered", "nmap can't tell (common/normal on UDP) — not a finding"),
                ("closed|filtered", "can't tell if closed or filtered"),
                ("unfiltered", "reachable but nmap can't decide open/closed (ACK scan)"),
            ],
        },
        "work_with_it": (
            "Turn the port list into a plan: each 'open' service → its enumeration tool "
            "(445→nxc, 80/443→gobuster, 88→kerbrute). Feed every VERSION string into a CVE "
            "search. OS hints (Ubuntu/Windows) tailor your payloads. Ignore 'filtered' until "
            "you have a reason to revisit it."
        ),
        "misreads": [
            "'filtered' is NOT 'closed' — one is a firewall, the other is an open door with no room behind it.",
            "A SERVICE name without -sV is a guess, not a fact. Don't build an exploit on a guess.",
            "'open|filtered' on a UDP scan is normal and expected — it is not a vulnerability.",
        ],
    },

    "nxc": {
        "tool": "nxc (NetExec)",
        "headline": "Every nxc line is host + protocol + a marker. The marker ([*]/[+]/[-]) is the whole story; the tail is the detail.",
        "sample": (
            "SMB  10.0.0.15  445  DC01  [*] Windows 10 x64 (name:DC01) (domain:corp.local) (signing:True) (SMBv1:False)\n"
            "SMB  10.0.0.15  445  DC01  [+] corp.local\\jdoe:Autumn2025! (Pwn3d!)\n"
            "SMB  10.0.0.16  445  WS02  [-] corp.local\\jdoe:Autumn2025! STATUS_LOGON_FAILURE\n"
            "SMB  10.0.0.17  445  WS03  [-] corp.local\\svc:Passw0rd STATUS_PASSWORD_EXPIRED"
        ),
        "reading": [
            {"field": "[*] host banner line",
             "means": "The recon line: OS, hostname, domain, and two crucial flags — signing and SMBv1.",
             "do": "Read (signing:...) and (SMBv1:...) before anything else — they decide two whole attack paths."},
            {"field": "(signing:True)",
             "means": "SMB signing is REQUIRED on this host.",
             "do": "This host is NOT relayable. Only 'signing:False' hosts are valid NTLM-relay targets."},
            {"field": "(SMBv1:False)",
             "means": "The legacy SMBv1 protocol is disabled.",
             "do": "'SMBv1:True' would flag a possible EternalBlue (MS17-010) target — a classic instant win."},
            {"field": "[+] corp.local\\jdoe:Autumn2025!",
             "means": "VALID credentials — this user/password works on this host.",
             "do": "You have a foothold. Spread it and collect BloodHound data as this user."},
            {"field": "(Pwn3d!)",
             "means": "You are LOCAL ADMIN on that host. This is the difference between 'a user' and 'game over here'.",
             "do": "secretsdump this host for hashes; run commands with -x. Prioritise Pwn3d! hosts."},
            {"field": "[-] ... STATUS_LOGON_FAILURE",
             "means": "Wrong username/password for this host. A clean miss.",
             "do": "Nothing here — move on. But watch the volume: many of these = you're generating auth-failure noise."},
            {"field": "[-] ... STATUS_PASSWORD_EXPIRED",
             "means": "The password is CORRECT — it's just expired. This is a WIN wearing a '[-]' costume.",
             "do": "You have valid creds; you can often reset the password (-M change-password) and take the account."},
        ],
        "reference": {
            "title": "Markers and the STATUS codes that matter",
            "rows": [
                ("[*]", "informational — host/recon banner"),
                ("[+]", "success — valid creds (admin ONLY if it also says Pwn3d!)"),
                ("[-]", "failure — but read WHY, some 'failures' are wins"),
                ("STATUS_LOGON_FAILURE", "wrong creds — a true miss"),
                ("STATUS_PASSWORD_EXPIRED", "creds CORRECT but expired — resettable win"),
                ("STATUS_ACCOUNT_LOCKED_OUT", "STOP — you are locking accounts"),
                ("STATUS_LOGON_TYPE_NOT_GRANTED", "creds valid but no remote-logon right here"),
            ],
        },
        "work_with_it": (
            "Triage by marker: hit the (Pwn3d!) hosts first (secretsdump → more hashes). "
            "Bank every [+] as a usable identity. Re-read every [-] for the STATUS code — "
            "EXPIRED and LOCKED_OUT mean very different things, and one of them means stop."
        ),
        "misreads": [
            "[+] alone is NOT admin — only (Pwn3d!) is. A plain [+] is a normal user.",
            "STATUS_PASSWORD_EXPIRED means the password is RIGHT — don't discard it as a failure.",
            "signing:True is the defender's safe setting and YOUR blocker; signing:False is the relay target.",
        ],
    },

    "hydra": {
        "tool": "hydra",
        "headline": "Hydra output is mostly noise until one line names a host, a login, and a password. That line is the entire point.",
        "sample": (
            "[DATA] attacking ssh://10.0.0.5:22/\n"
            "[22][ssh] host: 10.0.0.5   login: admin   password: hunter2\n"
            "[STATUS] 1847.00 tries/min, 1847 tries in 00:01h, 10153 to do in 00:06h\n"
            "1 of 1 target successfully completed, 1 valid password found"
        ),
        "reading": [
            {"field": "[22][ssh] host:... login:... password:...",
             "means": "THE HIT. A working credential pair on that service/port. Everything else is progress noise.",
             "do": "Stop and use it: log in manually to confirm, then enumerate as that user."},
            {"field": "[STATUS] 1847.00 tries/min",
             "means": "Your current attempt rate. A sudden collapse in this number means you're being throttled or blocked.",
             "do": "If the rate craters, back off (-t lower) — you've tripped rate-limiting/fail2ban."},
            {"field": "1 valid password found",
             "means": "The end-of-run summary count.",
             "do": "0 found = nothing in THIS list cracked THIS service. Not proof the account is strong — try a better list."},
        ],
        "reference": {
            "title": "Reading a hydra run",
            "rows": [
                ("[DATA] attacking", "confirms target/service/port — sanity-check it's what you meant"),
                ("[PORT][service] host/login/password", "a confirmed valid credential — the win"),
                ("[STATUS] tries/min", "live rate; watch for throttling"),
                ("[ERROR] / all-succeed", "service returns success for everything = false positives"),
            ],
        },
        "work_with_it": (
            "The moment a hit line appears, leave hydra and verify the login by hand — then pivot "
            "to enumerating that account. If EVERY password 'works', the service is misconfigured "
            "(returns 200/OK for all) and hydra is lying — you need a better success/failure condition."
        ),
        "misreads": [
            "A hit isn't proven until you log in manually — some services falsely report success.",
            "'0 valid found' means this wordlist failed, not that the account is uncrackable.",
            "Cranking -t high on SSH doesn't go faster — it trips fail2ban and locks you out.",
        ],
    },
}

OUTPUT_LESSONS.update({

    "hashcat": {
        "tool": "hashcat",
        "headline": "Hashcat's status block tells you WHETHER you won; the potfile line tells you WHAT you won.",
        "sample": (
            "Session..........: hashcat\n"
            "Status...........: Cracked\n"
            "Hash.Mode........: 1000 (NTLM)\n"
            "Recovered........: 1/1 (100.00%) Digests\n"
            "Speed.#1.........: 12345.6 MH/s\n"
            "9f4e1b7c0a2d3e4f5061728394a5b6c7:Summer2024!"
        ),
        "reading": [
            {"field": "Status: Cracked",
             "means": "At least one hash fell. The other states are 'Running' (in progress) and 'Exhausted' (list finished, nothing left).",
             "do": "Cracked → collect the plaintext below. Exhausted → your wordlist lacked it; escalate to rules/another list."},
            {"field": "Hash.Mode: 1000 (NTLM)",
             "means": "Confirms the algorithm hashcat used — and that your -m matched the hash type.",
             "do": "If this is wrong, everything downstream is wrong. Mode mismatch = guaranteed zero cracks."},
            {"field": "Recovered: 1/1 (100.00%)",
             "means": "How many of the hashes you loaded have been cracked so far.",
             "do": "1/50 means keep going — one crack doesn't mean the job's done."},
            {"field": "hash:plaintext line",
             "means": "The actual result. LEFT of the colon is the hash, RIGHT is the recovered password.",
             "do": "Take the plaintext and reuse it (spray it, log in). If it's an NT hash you didn't need to crack — pass it instead."},
        ],
        "reference": {
            "title": "The three statuses that decide your next move",
            "rows": [
                ("Running", "still working — let it finish or check --status"),
                ("Cracked", "got at least one — plaintext is in the potfile"),
                ("Exhausted", "wordlist finished, nothing more — this list failed, not the password"),
                ("Recovered X/Y", "your progress across all loaded hashes"),
            ],
        },
        "work_with_it": (
            "A crack is a credential — immediately reuse it (users reuse passwords across accounts "
            "and hosts). 'Exhausted' is a prompt, not a wall: add a rule file (-r best64.rule), try a "
            "themed list (company name + season + year), or a mask attack for known patterns."
        ),
        "misreads": [
            "'Exhausted' does NOT mean the password is strong — it means THIS wordlist didn't hold it.",
            "The wrong -m mode silently yields zero cracks — always confirm Hash.Mode matches the hash type.",
            "If you cracked an NTLM hash you often didn't need to — that hash was already usable via pass-the-hash.",
        ],
    },

    "gobuster": {
        "tool": "gobuster",
        "headline": "Every line is a door that exists. The status code tells you whether it's open, locked, or hiding something.",
        "sample": (
            "/admin                (Status: 301) [Size: 312] [--> /admin/]\n"
            "/login.php            (Status: 200) [Size: 1240]\n"
            "/backup               (Status: 403) [Size: 278]\n"
            "/.git/HEAD            (Status: 200) [Size: 23]\n"
            "/uploads              (Status: 200) [Size: 4096]"
        ),
        "reading": [
            {"field": "(Status: 200)",
             "means": "The path exists and was served to you directly.",
             "do": "Visit it. This is live content — a page, a script, a directory listing."},
            {"field": "(Status: 301) [--> /admin/]",
             "means": "A redirect — almost always a directory missing its trailing slash.",
             "do": "Follow it (add the slash). Directories often reveal more paths inside."},
            {"field": "(Status: 403)",
             "means": "The path EXISTS but you're forbidden. This is a find, not a dead end — something worth hiding is there.",
             "do": "Try bypasses: trailing dot, //double slash, X-Forwarded-For / X-Original-URL headers, case tricks."},
            {"field": "/.git/HEAD (Status: 200)",
             "means": "An exposed git repository — a catastrophic leak of source code and often secrets.",
             "do": "Dump it (git-dumper) to reconstruct the whole codebase and hunt hardcoded creds."},
            {"field": "[Size: 278]",
             "means": "Response length in bytes. A CLUSTER of identical sizes is a soft-404 (the app returns 200 for everything).",
             "do": "If many hits share one size, that's a catch-all mask — filter it with -fs <size> or you drown in noise."},
        ],
        "reference": {
            "title": "Status codes as a triage table",
            "rows": [
                ("200", "exists and served — go look"),
                ("301/302", "redirect — usually a directory; follow it"),
                ("403", "exists but forbidden — a FIND; try bypasses"),
                ("401", "auth required — note the realm, creds needed"),
                ("Size clustering", "identical sizes = soft-404 mask; filter with -fs"),
            ],
        },
        "work_with_it": (
            "Sort by interest, not by order: 403s and juicy paths (/.git, /backup, /admin, /uploads) "
            "first. Uniform-size 200s are usually a soft-404 — filter them. Every redirect is a new "
            "directory to recurse into. The goal is to turn this list into 2–3 pages worth attacking."
        ),
        "misreads": [
            "403 is a discovery, not a failure — the content is there; you just need a way around the gate.",
            "A wall of 200s with the same [Size] is a soft-404, not fifty real pages — filter by size.",
            "301 without following the redirect hides everything inside that directory.",
        ],
    },

    "sqlmap": {
        "tool": "sqlmap",
        "headline": "sqlmap tells you WHICH input is injectable, by WHAT technique, and against WHAT database — each shapes your next step.",
        "sample": (
            "Parameter: id (GET)\n"
            "    Type: boolean-based blind\n"
            "    Title: AND boolean-based blind - WHERE or HAVING clause\n"
            "[INFO] the back-end DBMS is MySQL\n"
            "available databases [3]:\n"
            "[*] information_schema\n"
            "[*] app\n"
            "[*] users"
        ),
        "reading": [
            {"field": "Parameter: id (GET)",
             "means": "WHICH input is injectable and via which method (GET query param 'id').",
             "do": "This is your injection point — every follow-up (-p id) targets it."},
            {"field": "Type: boolean-based blind",
             "means": "The technique that worked. 'Blind' = the DB doesn't echo data; sqlmap infers it true/false, one bit at a time.",
             "do": "Expect SLOW extraction. Don't --dump a million-row table blindly; target specific columns."},
            {"field": "the back-end DBMS is MySQL",
             "means": "The database engine. This dictates the SQL syntax for any MANUAL follow-up.",
             "do": "If you go manual, use MySQL syntax (LIMIT, information_schema.tables, etc.)."},
            {"field": "available databases → information_schema / app / users",
             "means": "The schemas. information_schema is built-in METADATA; app/users are the real application data.",
             "do": "Ignore information_schema as loot — pivot into the app-specific DBs to find users/creds."},
        ],
        "reference": {
            "title": "Injection types, fastest to slowest",
            "rows": [
                ("UNION-based", "data comes back in the page — fast, bulk extraction"),
                ("error-based", "data leaks via error messages — fast"),
                ("boolean-based blind", "inferred true/false per character — slow"),
                ("time-based blind", "inferred via response DELAYS — slowest; be surgical"),
            ],
        },
        "work_with_it": (
            "Let the technique set your pace: UNION/error → dump freely; blind/time-based → be "
            "surgical (specific tables/columns only). Skip information_schema as a target; go straight "
            "for the app DB's users table, then feed any password hashes into hashcat."
        ),
        "misreads": [
            "'boolean-based blind' means extraction is SLOW — mass-dumping will take hours; be selective.",
            "information_schema is metadata, not loot — the app-named databases hold the real data.",
            "The reported DBMS matters even with sqlmap — it's what your MANUAL fallback syntax must match.",
        ],
    },
})


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def _canon(name: str) -> str:
    n = (name or "").split("/")[-1].strip().lower()
    return _ALIASES.get(n, n)


def has_output_lesson(tool: str) -> bool:
    """True if we have a results-literacy lesson for this tool."""
    return _canon(tool) in OUTPUT_LESSONS


def get_output_lesson(tool: str) -> Optional[Dict]:
    """The raw results-literacy lesson for a tool, or None."""
    return OUTPUT_LESSONS.get(_canon(tool))


def list_output_lessons() -> List[str]:
    """Tools that currently have a results-literacy lesson."""
    return sorted(OUTPUT_LESSONS)


def format_output_lesson(tool: str, compact: bool = False) -> str:
    """Render the 'how to read the results' lesson for a tool.

    compact=True trims the reference table + work-with-it prose — used when
    appending as a follow-up to a normal lesson so it doesn't overwhelm.
    """
    lesson = get_output_lesson(tool)
    if not lesson:
        avail = ", ".join(list_output_lessons())
        return (f"  No results-literacy lesson for '{tool}' yet.\n"
                f"  Available: {avail}")
    bar = "═" * 62
    out = [bar, f"  📖 READING THE RESULTS — {lesson['tool']}", bar,
           f"  {lesson['headline']}", "",
           "  ── SAMPLE OUTPUT ──"]
    for line in lesson["sample"].splitlines():
        out.append(f"    {line}")
    out += ["", "  ── LINE BY LINE (what it means · what to do) ──"]
    for r in lesson["reading"]:
        out.append(f"  ▸ {r['field']}")
        out.append(f"      means: {r['means']}")
        out.append(f"      do:    {r['do']}")
    if not compact:
        ref = lesson.get("reference")
        if ref:
            out += ["", f"  ── {ref['title']} ──"]
            for k, v in ref["rows"]:
                out.append(f"    {k:<26} {v}")
        if lesson.get("work_with_it"):
            out += ["", "  ── WORKING WITH THE DATA ──"]
            import textwrap
            for line in textwrap.wrap(lesson["work_with_it"], width=58):
                out.append(f"    {line}")
    if lesson.get("misreads"):
        out += ["", "  ⚠ COMMON MISREADS ──"]
        for m in lesson["misreads"]:
            out.append(f"    • {m}")
    out += [bar, "  Next: run the tool, then `interpret <output>` to act on YOUR results."]
    return "\n".join(out)
