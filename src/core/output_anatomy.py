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
    "impacket-secretsdump": "secretsdump", "secretsdump.py": "secretsdump",
    "enum4linux-ng": "enum4linux", "enum4linux.pl": "enum4linux",
    "feroxbuster": "ffuf", "wfuzz": "ffuf",  # column-based fuzzers read alike
    "impacket-getuserspns": "getuserspns", "getuserspns.py": "getuserspns",
    "netstat": "ss", "ss": "ss",             # network-state reading
    "ps": "tasklist", "ps aux": "tasklist",  # process-list reading (Win/Linux)
    "impacket-getnpusers": "getnpusers", "getnpusers.py": "getnpusers",
    "certipy-ad": "certipy", "certipy.py": "certipy",
    "msf": "msfconsole", "metasploit": "msfconsole",
    "meterp": "meterpreter",
    "impacket-psexec": "psexec", "impacket-wmiexec": "psexec",
    "impacket-smbexec": "psexec", "wmiexec": "psexec", "smbexec": "psexec",
    "psexec.py": "psexec", "wmiexec.py": "psexec",
    "airodump": "airodump-ng", "aircrack": "aircrack-ng",
    "winpeas": "linpeas", "linpeas.sh": "linpeas", "winpeas.exe": "linpeas",
    "peass": "linpeas", "pspy64": "pspy", "pspy32": "pspy",
    "evilwinrm": "evil-winrm", "evil-winrm.rb": "evil-winrm",
    "rustscan": "masscan", "snmp-check": "snmpwalk",
    "amass": "subfinder", "assetfinder": "subfinder", "sublist3r": "subfinder",
    "dnsenum": "dnsrecon", "fierce": "dnsrecon",
    "testssl": "sslscan", "testssl.sh": "sslscan", "sslyze": "sslscan",
    "theharvester": "theharvester",
    "impacket-ntlmrelayx": "ntlmrelayx", "ntlmrelayx.py": "ntlmrelayx",
    "rubeus.exe": "rubeus", "nanodump": "lsassy", "pypykatz": "lsassy",
    "bloodhound.py": "bloodhound-python", "sharphound": "bloodhound-python",
    "impacket-getadusers": "getadusers", "getadusers.py": "getadusers",
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


# ── Batch 2: AD credential + directory + SMB enumeration outputs ────────────
OUTPUT_LESSONS.update({

    "secretsdump": {
        "tool": "impacket-secretsdump",
        "headline": "A hash dump is a wall of colons. The trick is knowing which fields are real hashes, which are empty placeholders, and which are cleartext gifts.",
        "sample": (
            "[*] Dumping local SAM hashes (uid:rid:lmhash:nthash)\n"
            "Administrator:500:aad3b435b51404eeaad3b435b51404ee:9f4e1b7c0a2d3e4f5061728394a5b6c7:::\n"
            "Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::\n"
            "[*] Dumping LSA Secrets\n"
            "CORP\\svc_sql:Summer2024!\n"
            "[*] Dumping cached domain logon information"
        ),
        "reading": [
            {"field": "uid:rid:lmhash:nthash header",
             "means": "The format of every line below: username : RID : LM hash : NT hash.",
             "do": "Read each line against this template — the 4th field (NT hash) is the one you crack or pass."},
            {"field": "Administrator:500:...",
             "means": "RID 500 is ALWAYS the true built-in Administrator, regardless of rename.",
             "do": "This is the crown jewel local account. RID 501 = Guest; 1000+ = created accounts."},
            {"field": "aad3b435b51404eeaad3b435b51404ee (the LM field)",
             "means": "This exact value is the EMPTY/disabled LM hash — it appears on every modern line.",
             "do": "Ignore it. It's a placeholder, not a hash to crack. Only the NT field matters."},
            {"field": "31d6cfe0d16ae931b73c59d7e0c089c0 (an NT field)",
             "means": "This exact NT hash is the hash of an EMPTY password.",
             "do": "That account has NO password — you don't even need to crack it. (Common on Guest/disabled accounts.)"},
            {"field": "[*] Dumping LSA Secrets → CORP\\svc_sql:Summer2024!",
             "means": "LSA secrets are frequently CLEARTEXT — service-account passwords in the open.",
             "do": "Read these FIRST. A cleartext password beats any hash — no cracking, instantly reusable."},
        ],
        "reference": {
            "title": "Fields and magic values",
            "rows": [
                ("user:RID:LM:NT:::", "the line format — NT (4th field) is the credential"),
                ("RID 500", "built-in Administrator (even if renamed)"),
                ("aad3b435b51404eeaad3b435b51404ee", "the EMPTY LM hash — a placeholder, never crack it"),
                ("31d6cfe0d16ae931b73c59d7e0c089c0", "NT hash of a BLANK password — no password set"),
                ("LSA Secrets / cleartext", "often plaintext service creds — check before cracking"),
                ("$MACHINE.ACC / host$", "machine account hash — usually not worth cracking"),
            ],
        },
        "work_with_it": (
            "Triage before you crack: scan LSA secrets for cleartext first, flag any NT hash "
            "equal to the empty-password value (already 'cracked'), then feed the remaining NT "
            "hashes to hashcat -m 1000 — OR skip cracking entirely and pass-the-hash. From a DC "
            "dump, the krbtgt NT hash is your golden-ticket key."
        ),
        "misreads": [
            "aad3b435b51404eeaad3b435b51404ee is the empty LM placeholder — cracking it wastes hours.",
            "31d6cfe0d16ae931b73c59d7e0c089c0 means the password is BLANK — that account is already open.",
            "You often don't need to crack anything — LSA cleartext and pass-the-hash skip the whole step.",
        ],
    },

    "ldapsearch": {
        "tool": "ldapsearch",
        "headline": "LDAP output is LDIF: each object is a 'dn' followed by attributes. The gold is in memberOf, description, and userAccountControl.",
        "sample": (
            "# jdoe, Users, corp.local\n"
            "dn: CN=jdoe,CN=Users,DC=corp,DC=local\n"
            "sAMAccountName: jdoe\n"
            "memberOf: CN=Domain Admins,CN=Users,DC=corp,DC=local\n"
            "description: temp account - pw Welcome1!\n"
            "userAccountControl: 4260352\n"
            "servicePrincipalName: MSSQL/db01.corp.local"
        ),
        "reading": [
            {"field": "dn: CN=jdoe,CN=Users,DC=corp,DC=local",
             "means": "Distinguished Name — the object's full, unique path in the directory tree.",
             "do": "Read it right-to-left as a path: domain → container → object. It anchors every other attribute."},
            {"field": "sAMAccountName: jdoe",
             "means": "The actual login name (what you authenticate WITH).",
             "do": "Collect these into your user list for spraying / roasting."},
            {"field": "memberOf: ...Domain Admins",
             "means": "Group membership — and this user is in Domain Admins.",
             "do": "Flag high-value groups immediately. This account is a priority target."},
            {"field": "description: temp account - pw Welcome1!",
             "means": "Free-text field admins abuse to store passwords/notes.",
             "do": "ALWAYS read description and info fields — cleartext creds hide here constantly, silently."},
            {"field": "userAccountControl: 4260352",
             "means": "A BITMASK of account flags. 4260352 includes 0x400000 = DONT_REQ_PREAUTH.",
             "do": "Decode it: 0x400000 set = AS-REP roastable; 0x20 = no password required; 0x2 = disabled."},
            {"field": "servicePrincipalName: MSSQL/db01...",
             "means": "The account has an SPN — it runs a service.",
             "do": "Any account with an SPN is Kerberoastable. Add it to your roast list."},
        ],
        "reference": {
            "title": "userAccountControl flags worth decoding",
            "rows": [
                ("0x2 (2)", "ACCOUNTDISABLE — account is disabled"),
                ("0x20 (32)", "PASSWD_NOTREQD — no password required"),
                ("0x10000 (65536)", "DONT_EXPIRE_PASSWORD"),
                ("0x400000 (4194304)", "DONT_REQ_PREAUTH — AS-REP roastable"),
                ("0x80000 (524288)", "TRUSTED_FOR_DELEGATION — delegation abuse"),
            ],
        },
        "work_with_it": (
            "Grep the LDIF for the three money attributes: memberOf (find the admins), description/info "
            "(find hidden passwords), and servicePrincipalName (find roast targets). Decode every "
            "userAccountControl — a single DONT_REQ_PREAUTH bit hands you an offline crack with no login."
        ),
        "misreads": [
            "description and info fields routinely contain plaintext passwords — never skip them.",
            "userAccountControl is a bitmask, not a category — you must decode the bits, not read the number.",
            "An SPN on a user account = Kerberoastable; don't overlook servicePrincipalName lines.",
        ],
    },

    "enum4linux": {
        "tool": "enum4linux(-ng)",
        "headline": "enum4linux dumps what a null session leaks. The three lines that matter: does null work, what's the lockout policy, and which shares are readable.",
        "sample": (
            "[+] Server allows sessions using username '', password ''\n"
            " =========== Users on 10.0.0.15 ===========\n"
            "index: 0x1 RID: 0x1f4 acb: 0x00000210 Account: Administrator\n"
            "index: 0x2 RID: 0x1f5 acb: 0x00000214 Account: Guest\n"
            " =========== Share Enumeration ===========\n"
            "\tSYSVOL          Disk      Logon server share\n"
            "\tUsers           Disk\n"
            "[+] Password Info: Minimum password length: 7  Lockout threshold: None"
        ),
        "reading": [
            {"field": "Server allows sessions using '' ''",
             "means": "A NULL SESSION is permitted — you enumerated without any credentials.",
             "do": "Big win. Everything below came for free. If this line is absent, the rest is empty."},
            {"field": "RID: 0x1f4 Account: Administrator",
             "means": "RID cycling recovered domain users. 0x1f4 = 500 = Administrator.",
             "do": "Harvest every Account: line into your user list for spraying/roasting."},
            {"field": "Share Enumeration → SYSVOL, Users",
             "means": "Readable shares. SYSVOL/NETLOGON are readable by any domain context.",
             "do": "Mount SYSVOL — it often holds Groups.xml with GPP cpassword (a decryptable domain cred)."},
            {"field": "Lockout threshold: None",
             "means": "There is NO account-lockout policy on this domain.",
             "do": "You can password-spray freely without locking anyone out. If it's a number, stay under it."},
        ],
        "reference": {
            "title": "The signals that shape your next move",
            "rows": [
                ("null session allowed", "free enumeration — users, shares, policy"),
                ("RID 500 / 501 / 1000+", "Administrator / Guest / created accounts"),
                ("SYSVOL, NETLOGON", "domain shares — hunt GPP cpassword in Groups.xml"),
                ("Lockout threshold: None", "spray with no lockout risk"),
                ("acb flags", "account control bits — 0x210 normal, 0x211 disabled"),
            ],
        },
        "work_with_it": (
            "Turn the dump into three artifacts: a users.txt (from RID cycling) for spraying, a shares "
            "list to mount (SYSVOL first, for GPP passwords), and the lockout number to bound your spray. "
            "No null session? Note it and pivot to LDAP or authenticated enum."
        ),
        "misreads": [
            "'Lockout threshold: None' is a green light to spray — no accounts will lock.",
            "SYSVOL is readable by design and frequently leaks GPP cpassword — always check it.",
            "No null-session line means the enumeration below is empty, not that the host is hardened everywhere.",
        ],
    },
})


# ── Batch 2b: web fuzzing + kerberos enum + credential capture outputs ──────
OUTPUT_LESSONS.update({

    "ffuf": {
        "tool": "ffuf",
        "headline": "ffuf gives you four numbers per hit — Status, Size, Words, Lines. You read the status like gobuster, but you FILTER on the other three.",
        "sample": (
            "[Status: 200, Size: 1256, Words: 210, Lines: 45] :: FUZZ: admin\n"
            "[Status: 301, Size: 178, Words: 6, Lines: 8]     :: FUZZ: uploads\n"
            "[Status: 403, Size: 278, Words: 20, Lines: 10]   :: FUZZ: backup\n"
            "[Status: 200, Size: 4096, Words: 900, Lines: 120] :: FUZZ: .git\n"
            ":: Progress: [4614/4614] :: 1200 req/sec"
        ),
        "reading": [
            {"field": "Status: 200 / 301 / 403",
             "means": "Same HTTP triage as any content scan: 200 exists, 301 redirects, 403 forbidden-but-present.",
             "do": "403 is a find (try bypasses); 301 is usually a directory (recurse); 200 is live (go look)."},
            {"field": "Size / Words / Lines",
             "means": "Three measurements of the response body. A CLUSTER sharing all three = a soft-404 catch-all.",
             "do": "Find the common (Size,Words,Lines) of the noise and filter it: -fs / -fw / -fl. This is the whole skill."},
            {"field": "FUZZ: .git",
             "means": "The wordlist entry that produced the hit — where FUZZ was substituted.",
             "do": "Recognise dangerous hits (.git, .env, backup, /api) and prioritise them."},
            {"field": ":: 1200 req/sec",
             "means": "Throughput. Very high rates can trip WAFs/rate-limits and produce false 403/429s.",
             "do": "If 403s suddenly flood, you may be blocked — slow down (-rate) and re-baseline."},
        ],
        "reference": {
            "title": "Filtering is the skill — match/filter flags",
            "rows": [
                ("-fc 404,403", "filter OUT these status codes"),
                ("-fs 278", "filter OUT this response size (the soft-404)"),
                ("-fw 20", "filter OUT this word count"),
                ("-mc 200,301", "MATCH only these codes"),
                ("-ac", "auto-calibrate the soft-404 filter for you"),
            ],
        },
        "work_with_it": (
            "Run once unfiltered to learn the noise signature (the size/words/lines everything shares), "
            "then re-run filtering it out so only anomalies remain. ffuf shows EVERYTHING by default — "
            "unfiltered output is unreadable; the operator's job is to subtract the baseline."
        ),
        "misreads": [
            "ffuf floods by default — a wall of 200s is a soft-404, not hundreds of real pages. Filter it.",
            "A sudden burst of 403/429 usually means you tripped a rate-limit, not that you found 400 secrets.",
            "Size, Words, AND Lines together identify the noise — one alone can miss a variable-length catch-all.",
        ],
    },

    "kerbrute": {
        "tool": "kerbrute",
        "headline": "kerbrute's useful output is a short list of '[+] VALID USERNAME' lines — usernames confirmed against the KDC without a single password guess.",
        "sample": (
            "2024/06/01 12:00:00 >  [+] VALID USERNAME:  jdoe@corp.local\n"
            "2024/06/01 12:00:00 >  [+] VALID USERNAME:  svc_sql@corp.local\n"
            "2024/06/01 12:00:01 >  [+] admin@corp.local:Spring2024! \n"
            "2024/06/01 12:00:02 >  Done! Tested 5000 usernames"
        ),
        "reading": [
            {"field": "[+] VALID USERNAME: jdoe@corp.local",
             "means": "This account EXISTS — confirmed by how the KDC replied, with no password attempted.",
             "do": "Collect every valid name. This is your vetted spray/roast list — no wasted lockout budget on bad names."},
            {"field": "[+] admin@corp.local:Spring2024!",
             "means": "In passwordspray/bruteuser mode, a username:password hit — valid CREDENTIALS.",
             "do": "That's a live login. Stop and use it."},
            {"field": "Done! Tested 5000 usernames",
             "means": "Run summary — how much of the list was checked.",
             "do": "No valid lines = your username list didn't match this domain's naming (try firstname.lastname, etc.)."},
        ],
        "reference": {
            "title": "kerbrute modes",
            "rows": [
                ("userenum", "which usernames exist (no passwords) — build the list"),
                ("passwordspray", "one password vs many valid users"),
                ("bruteuser", "many passwords vs one user"),
                ("[+] VALID USERNAME", "confirmed account — feed to spray/roast"),
            ],
        },
        "work_with_it": (
            "Use userenum FIRST to trim a huge name list down to real accounts, THEN spray only those — "
            "you never spend a lockout attempt on a username that doesn't exist. Valid names also feed "
            "AS-REP roasting (GetNPUsers) directly."
        ),
        "misreads": [
            "userenum still touches the KDC — bad guesses generate 4768 failures; it's quiet-ish, not invisible.",
            "Zero valid usernames usually means wrong naming convention, not an empty domain — change the format.",
            "Valid username ≠ valid login — it's a confirmed account to spray, not access yet.",
        ],
    },

    "responder": {
        "tool": "responder",
        "headline": "When Responder catches something, it prints a NetNTLMv2 hash. Know what that hash IS — because it is NOT an NT hash and you cannot pass it.",
        "sample": (
            "[SMB] NTLMv2-SSP Client   : 10.0.0.50\n"
            "[SMB] NTLMv2-SSP Username : CORP\\jdoe\n"
            "[SMB] NTLMv2-SSP Hash     : jdoe::CORP:1122334455667788:AABB...:0101000000...\n"
            "[*] Skipping previously captured hash for CORP\\jdoe"
        ),
        "reading": [
            {"field": "NTLMv2-SSP Username : CORP\\jdoe",
             "means": "WHOSE authentication you captured (a user or a machine account ending in $).",
             "do": "Machine accounts ($) rarely crack — prioritise USER hashes for cracking."},
            {"field": "NTLMv2-SSP Hash : jdoe::CORP:...",
             "means": "A NetNTLMv2 (challenge/response) hash — NOT the account's NT hash.",
             "do": "You can CRACK it offline (hashcat -m 5600) or RELAY it live — but you CANNOT pass-the-hash with it."},
            {"field": "[*] Skipping previously captured hash",
             "means": "Responder already grabbed this identity; it won't spam duplicates.",
             "do": "Check the logs (/usr/share/responder/logs) for the full captured hashes."},
        ],
        "reference": {
            "title": "NetNTLMv2 — what you can and can't do",
            "rows": [
                ("crack offline", "hashcat -m 5600 — works if the password is weak"),
                ("relay live", "ntlmrelayx to an unsigned target — works even if uncrackable"),
                ("pass-the-hash", "NO — NetNTLMv2 is not the NT hash; PtH is impossible"),
                ("machine account ($)", "almost never cracks — relay instead"),
            ],
        },
        "work_with_it": (
            "Decide immediately: is the password likely weak? Crack it (-m 5600). Uncrackable or a machine "
            "account? Turn off Responder's SMB/HTTP servers and RELAY instead (ntlmrelayx) to a signing-"
            "disabled host. The one thing you can never do with this hash is pass it."
        ),
        "misreads": [
            "NetNTLMv2 is NOT an NT hash — pass-the-hash will not work; crack or relay only.",
            "Machine-account ($) hashes almost never crack — don't waste GPU time; relay them.",
            "Responder is LOUD (it poisons broadcasts) — every capture is also a detection event.",
        ],
    },
})


# ── Batch 3: share perms + vuln-scan triage + kerberoast hash format ────────
OUTPUT_LESSONS.update({

    "smbmap": {
        "tool": "smbmap",
        "headline": "smbmap is a permission map of shares. The Permissions column is the whole game: NO ACCESS, READ ONLY, or the jackpot — READ, WRITE.",
        "sample": (
            "[+] IP: 10.0.0.15:445    Name: DC01\n"
            "        Disk                Permissions     Comment\n"
            "        ----                -----------     -------\n"
            "        ADMIN$              NO ACCESS       Remote Admin\n"
            "        C$                  READ, WRITE     Default share\n"
            "        SYSVOL              READ ONLY       Logon server share\n"
            "        Users               READ ONLY"
        ),
        "reading": [
            {"field": "Permissions column",
             "means": "Your access level PER share — the only column that decides what you can do.",
             "do": "Scan it first: NO ACCESS = skip, READ ONLY = exfil, READ+WRITE = drop files."},
            {"field": "C$  READ, WRITE",
             "means": "Write access to the C$ admin share — that is effectively admin on the machine.",
             "do": "You can write anywhere on C:. This is a foothold; drop a payload or read SAM."},
            {"field": "SYSVOL  READ ONLY",
             "means": "The domain policy share, readable by any authenticated context.",
             "do": "Mount it and hunt Groups.xml for GPP cpassword (a decryptable domain credential)."},
            {"field": "ADMIN$  NO ACCESS",
             "means": "You lack rights to the remote-admin share on this account.",
             "do": "Not admin here (with this identity). Try other creds/hosts, or use a READ+WRITE share instead."},
        ],
        "reference": {
            "title": "Permission levels → what they buy you",
            "rows": [
                ("NO ACCESS", "nothing — move on"),
                ("READ ONLY", "download/exfil everything in the share"),
                ("READ, WRITE", "upload files — payloads, SCF/.lnk hash-capture, overwrite"),
                ("C$ / ADMIN$ writable", "effectively local admin on the host"),
            ],
        },
        "work_with_it": (
            "Sort shares by permission: writable shares first (drop a payload, or an SCF/.url file to "
            "capture hashes from anyone browsing), then readable shares for exfil (configs, backups, "
            "creds). Writable C$/ADMIN$ means you're already admin — pivot to secretsdump."
        ),
        "misreads": [
            "READ, WRITE on C$ or ADMIN$ is effectively admin on the box — not just 'a writable folder'.",
            "READ ONLY isn't a dead end — you can still exfil every file in the share.",
            "Writable non-admin shares enable SCF/.url hash-capture attacks — don't overlook them.",
        ],
    },

    "nuclei": {
        "tool": "nuclei",
        "headline": "Nuclei prints one line per match: [template-id] [protocol] [severity] [url]. Triage by SEVERITY, top-down — and know that [info] is noise, not findings.",
        "sample": (
            "[tech-detect:nginx] [http] [info] http://target.com\n"
            "[CVE-2021-44228] [http] [critical] http://target.com/api\n"
            "[ssl-issuer] [ssl] [info] target.com:443\n"
            "[exposed-panels/grafana] [http] [medium] http://target.com/grafana\n"
            "[git-config] [http] [high] http://target.com/.git/config"
        ),
        "reading": [
            {"field": "[severity] tag ([info]…[critical])",
             "means": "The triage key. Ordered: info < low < medium < high < critical.",
             "do": "Read the [critical]/[high] lines FIRST. They're your entry points; everything else waits."},
            {"field": "[info] tech-detect / ssl-issuer",
             "means": "Informational — fingerprinting and metadata, NOT vulnerabilities.",
             "do": "Don't report these as findings. They're context (what stack it is), not weaknesses."},
            {"field": "[CVE-2021-44228] … [critical]",
             "means": "A specific named check (here, Log4Shell) that MATCHED against a live URL.",
             "do": "This is a real, exploitable entry. Look up the template-id, confirm, and exploit."},
            {"field": "the trailing URL",
             "means": "Exactly WHERE the match fired.",
             "do": "Go straight to that endpoint — nuclei already told you the vulnerable path."},
        ],
        "reference": {
            "title": "Severity triage + noise control",
            "rows": [
                ("critical / high", "exploitable — start here"),
                ("medium", "worth investigating (exposed panels, misconfigs)"),
                ("low", "minor — note it"),
                ("info", "fingerprinting/metadata — NOT a vulnerability"),
                ("-severity critical,high", "run this to skip the noise entirely"),
            ],
        },
        "work_with_it": (
            "Read the output as a ranked target list: hit [critical] → [high] → [medium], and ignore "
            "[info] for reporting. Re-run with -severity critical,high,medium on noisy targets. Each "
            "high/critical line hands you a template-id (look up the CVE) and the exact URL to attack."
        ),
        "misreads": [
            "[info] lines are fingerprinting, not vulnerabilities — don't pad a report with them.",
            "Triage top-down by severity; drowning in 50 [info] lines while missing the [critical] is the classic mistake.",
            "A match means the check's condition was met — still confirm exploitability before claiming it.",
        ],
    },

    "getuserspns": {
        "tool": "impacket-GetUserSPNs (Kerberoast)",
        "headline": "GetUserSPNs gives you a table (WHO is roastable and whether they matter) and a hash. The digit right after '$krb5tgs$' tells you if it'll crack fast.",
        "sample": (
            "ServicePrincipalName   Name      MemberOf         PasswordLastSet\n"
            "--------------------   ----      --------         --------------\n"
            "MSSQL/db01.corp.local  svc_sql   Domain Admins    2019-01-01\n"
            "\n"
            "$krb5tgs$23$*svc_sql$CORP.LOCAL$MSSQL/db01*$a1b2c3...long...hash"
        ),
        "reading": [
            {"field": "MemberOf: Domain Admins",
             "means": "This service account is a Domain Admin. Cracking it = full domain compromise.",
             "do": "Prioritise roastable accounts in privileged groups — those are the ones that matter."},
            {"field": "PasswordLastSet: 2019-01-01",
             "means": "The password is years old — likely set before modern complexity policy.",
             "do": "Old service-account passwords crack far more often. Move it up your list."},
            {"field": "$krb5tgs$23$",
             "means": "The '23' is the Kerberos encryption type: 23 = RC4. RC4 tickets crack fast.",
             "do": "Crack with hashcat -m 13100. If it read $krb5tgs$18$ that's AES (etype 18) → -m 19700, much slower."},
            {"field": "*svc_sql$CORP.LOCAL$MSSQL/db01*",
             "means": "Embedded metadata — the account, realm, and SPN the ticket is for.",
             "do": "Confirms which account this hash belongs to when you crack a batch."},
        ],
        "reference": {
            "title": "Encryption type = crack difficulty",
            "rows": [
                ("$krb5tgs$23$", "RC4 (etype 23) — fast crack, hashcat -m 13100"),
                ("$krb5tgs$18$", "AES256 (etype 18) — slow, hashcat -m 19700"),
                ("$krb5tgs$17$", "AES128 (etype 17) — slow, hashcat -m 19600"),
                ("MemberOf privileged", "prioritise — these accounts are worth the crack"),
                ("old PasswordLastSet", "weaker password likely — crack these first"),
            ],
        },
        "work_with_it": (
            "Rank roast targets by two signals before spending GPU time: privileged MemberOf (does it "
            "matter?) and old PasswordLastSet (will it crack?). Feed RC4 ($23) hashes to hashcat -m 13100 "
            "first — a cracked Domain-Admin service account ends the engagement."
        ),
        "misreads": [
            "The number after $krb5tgs$ is the ENCRYPTION type, not a version — 23=RC4 (easy), 18=AES (hard).",
            "A roastable account only matters if it has privilege — check MemberOf before you burn hours cracking.",
            "Getting the hash needs valid domain creds (unlike AS-REP roasting, which doesn't).",
        ],
    },
})


# ── Batch 3b: attack-path edges + post-exploitation host reading ────────────
OUTPUT_LESSONS.update({

    "bloodhound": {
        "tool": "BloodHound (attack paths)",
        "headline": "A BloodHound path is nodes joined by EDGES. Each edge is not a line — it's an abusable privilege. Read the path as a to-do list from you to Domain Admin.",
        "sample": (
            "jdoe@corp.local\n"
            "  -[MemberOf]->      IT Support\n"
            "    -[GenericAll]->  svc_backup\n"
            "      -[MemberOf]->  Backup Operators\n"
            "        -[DCSync]->  corp.local"
        ),
        "reading": [
            {"field": "jdoe@corp.local (a node)",
             "means": "Your starting principal — the account you control right now.",
             "do": "This is the top of the path; every edge below is a step you can take from here."},
            {"field": "-[MemberOf]-> IT Support",
             "means": "Group membership, and it's TRANSITIVE — you inherit everything the group can do.",
             "do": "Free step. You already have the group's rights; keep following the chain."},
            {"field": "-[GenericAll]-> svc_backup",
             "means": "FULL control over the svc_backup object — the single most powerful edge.",
             "do": "Abuse it: reset svc_backup's password (or set an SPN and Kerberoast it) to take the account."},
            {"field": "-[DCSync]-> corp.local",
             "means": "Replication rights on the domain — you can pull EVERY hash, including krbtgt.",
             "do": "secretsdump -just-dc → domain compromise / golden ticket. This is the finish line."},
        ],
        "reference": {
            "title": "Common edges = the abuse they authorise",
            "rows": [
                ("MemberOf", "inherit the group's rights (transitive)"),
                ("AdminTo", "local admin on that computer"),
                ("GenericAll / GenericWrite", "full/most control — reset pw, set SPN, etc."),
                ("WriteDacl / WriteOwner", "grant YOURSELF rights over the object"),
                ("ForceChangePassword", "reset the target's password"),
                ("DCSync", "replicate all domain hashes (krbtgt) — game over"),
            ],
        },
        "work_with_it": (
            "Convert the path into an ordered playbook: perform each edge's specific abuse in sequence "
            "(MemberOf is free; GenericAll → reset password; DCSync → dump hashes). The shortest path "
            "isn't always the quietest — some edges (AddMember, ForceChangePassword) are noisier than "
            "others, so weigh detection against speed."
        ),
        "misreads": [
            "Each edge is an abusable PRIVILEGE, not a relationship label — GenericAll means 'reset their password'.",
            "MemberOf is transitive: you inherit rights several groups deep, not just direct memberships.",
            "The shortest path can be the loudest — pick edges for stealth, not only hop count.",
        ],
    },

    "ss": {
        "tool": "ss / netstat",
        "headline": "Post-compromise, ss shows the box's network reality. Two things matter: what's LISTENING (and on which interface) and what's ESTABLISHED (where this host talks).",
        "sample": (
            "State   Recv-Q Send-Q  Local Address:Port    Peer Address:Port   Process\n"
            "LISTEN  0      128     0.0.0.0:22            0.0.0.0:*           sshd\n"
            "LISTEN  0      80      127.0.0.1:3306        0.0.0.0:*           mysqld\n"
            "ESTAB   0      0       10.0.0.5:49152        10.0.0.10:445       "
        ),
        "reading": [
            {"field": "LISTEN  0.0.0.0:22",
             "means": "A service listening on ALL interfaces — reachable from the network.",
             "do": "Already exposed; you'd have seen it in an external scan. Note the Process (sshd)."},
            {"field": "LISTEN  127.0.0.1:3306",
             "means": "Bound to LOCALHOST only — invisible from outside, reachable only ON this box.",
             "do": "PIVOT GOLD. An external scan missed this. Port-forward/tunnel to reach the internal MySQL."},
            {"field": "ESTAB  10.0.0.5 → 10.0.0.10:445",
             "means": "An established SMB connection to another host — a live trust/relationship.",
             "do": "Maps where this box talks. 10.0.0.10:445 is your next lateral-movement candidate."},
            {"field": "Process column",
             "means": "Which program owns the socket (needs sufficient privilege to see).",
             "do": "Ties a port to a service so you know what you're pivoting into."},
        ],
        "reference": {
            "title": "What to look for post-exploitation",
            "rows": [
                ("0.0.0.0 / :: LISTEN", "reachable service (all interfaces / IPv6)"),
                ("127.0.0.1 LISTEN", "localhost-only — a hidden pivot target; tunnel to it"),
                ("ESTABLISHED", "active connection — reveals internal trust & next hops"),
                ("ss -tulpn / netstat -ano", "the commands (TCP/UDP, listening, PID)"),
            ],
        },
        "work_with_it": (
            "Build two lists from the output: localhost-only LISTEN ports (tunnel to these — they were "
            "invisible externally and are often unauthenticated internal services) and ESTABLISHED peers "
            "(the box's trust map — where to move laterally). This is how a foothold becomes a pivot."
        ),
        "misreads": [
            "127.0.0.1-bound services are the prize, not the boring ones — they're hidden internal pivot targets.",
            "ESTABLISHED connections reveal the internal trust map — read them for your next hop.",
            "0.0.0.0 = all interfaces (reachable); 127.0.0.1 = localhost only (needs a tunnel).",
        ],
    },

    "tasklist": {
        "tool": "tasklist / ps",
        "headline": "A process list is a threat-and-target map. Before you act, read it for the defenders watching (EDR/AV) and the process holding the creds (LSASS).",
        "sample": (
            "Image Name          PID     Session   Mem Usage\n"
            "=========           ===     =======   =========\n"
            "lsass.exe           648     0         12,400 K\n"
            "MsMpEng.exe         2100    0         181,000 K\n"
            "Sysmon64.exe        1520    0         9,200 K\n"
            "cmd.exe             4400    1         3,100 K"
        ),
        "reading": [
            {"field": "MsMpEng.exe / Sysmon64.exe",
             "means": "Defenders. MsMpEng = Windows Defender (AV); Sysmon = detailed event logging.",
             "do": "READ THIS FIRST. Their presence dictates OpSec — Defender scans payloads, Sysmon logs your every move."},
            {"field": "lsass.exe  PID 648",
             "means": "The Local Security Authority — where credentials/hashes live in memory.",
             "do": "This is your credential-dump target. Note the PID; dumping it triggers Sysmon EID 10."},
            {"field": "Session column (0 vs 1)",
             "means": "Session 0 = services/system; Session 1+ = an interactive user desktop.",
             "do": "Session 1+ processes mean a user is logged in — potential live tokens to steal."},
            {"field": "an unexpected / unsigned process",
             "means": "Could be another operator's implant, a monitoring agent, or a target service.",
             "do": "Investigate odd names/high memory — it's either competition, a defender, or an opportunity."},
        ],
        "reference": {
            "title": "Names to recognise instantly",
            "rows": [
                ("MsMpEng.exe", "Windows Defender (AV)"),
                ("Sysmon / Sysmon64", "Sysmon — deep event logging"),
                ("CSFalconService / cb*", "CrowdStrike / Carbon Black EDR"),
                ("lsass.exe", "credential store — your dump target"),
                ("Session 1+", "interactive user — live tokens available"),
            ],
        },
        "work_with_it": (
            "Read defensively before offensively: catalogue every AV/EDR process and adjust your TTPs "
            "(no on-disk payloads if Defender's up; memory-only + no LSASS touch if an EDR is watching). "
            "THEN note lsass's PID and any interactive sessions as your credential/token targets."
        ),
        "misreads": [
            "Scan for EDR/AV FIRST — acting before you spot CrowdStrike or Sysmon is how engagements get burned.",
            "lsass isn't just a process — it's the credential vault; its PID is your dump target.",
            "Session 1+ means a live user with stealable tokens; Session 0 is services only.",
        ],
    },
})


# ── Batch 4: AS-REP roast + web-stack fingerprint + WordPress enum ──────────
OUTPUT_LESSONS.update({

    "getnpusers": {
        "tool": "impacket-GetNPUsers (AS-REP roasting)",
        "headline": "GetNPUsers is Kerberoasting's no-password cousin. It lists accounts with pre-auth disabled and hands you a $krb5asrep$ hash — the '23' means RC4, and RC4 cracks fast.",
        "sample": (
            "Name        MemberOf  PasswordLastSet      LastLogon\n"
            "----------  --------  -------------------  -------------------\n"
            "svc_backup            2020-05-01 10:00:00  2024-01-01 08:00:00\n"
            "mjones                2019-03-15 14:00:00  <never>\n"
            "\n"
            "$krb5asrep$23$svc_backup@CORP.LOCAL:a1b2c3...$d4e5f6...long...hash"
        ),
        "reading": [
            {"field": "the account list itself",
             "means": "Every name here has Kerberos pre-authentication DISABLED (DONT_REQ_PREAUTH) — a misconfiguration.",
             "do": "You got these WITHOUT any password. That's the whole point: AS-REP roasting needs only a username list."},
            {"field": "$krb5asrep$23$svc_backup@CORP.LOCAL",
             "means": "The roastable hash. '23' is the Kerberos etype = RC4. The account+realm are embedded.",
             "do": "Crack with hashcat -m 18200 (NOT -m 13100 — that's Kerberoast/TGS). RC4 cracks quickly."},
            {"field": "LastLogon: <never>  (mjones)",
             "means": "A stale/never-used account — often a forgotten service or test account.",
             "do": "Stale accounts frequently have weak, ancient passwords. Prioritise them in the crack."},
            {"field": "PasswordLastSet: 2019/2020",
             "means": "Old passwords, likely pre-complexity-policy.",
             "do": "Feed the oldest first — best odds of a fast crack."},
        ],
        "reference": {
            "title": "AS-REP vs Kerberoast — don't mix them up",
            "rows": [
                ("$krb5asrep$23$", "AS-REP (RC4) — crack with hashcat -m 18200"),
                ("$krb5tgs$23$", "Kerberoast (RC4) — that's GetUserSPNs, -m 13100"),
                ("needs NO creds", "AS-REP only needs a username list (pre-auth off)"),
                ("needs valid creds", "Kerberoast needs a domain account to request tickets"),
                ("root cause", "an admin set 'do not require pre-auth' on the account"),
            ],
        },
        "work_with_it": (
            "This is your FIRST Kerberos move on a domain — it needs no credentials, just names (feed it "
            "a list, or -usersfile from kerbrute/enum4linux output). Rank hits by stale LastLogon and old "
            "PasswordLastSet, crack RC4 ($23) with -m 18200, and you may get a foothold before you've "
            "authenticated to anything."
        ),
        "misreads": [
            "AS-REP roasting needs NO password — that's what separates it from Kerberoasting.",
            "The mode is -m 18200 (AS-REP), not -m 13100 (that's the TGS/Kerberoast hash).",
            "No results doesn't mean the domain is safe — it means no accounts have pre-auth disabled (good hygiene).",
        ],
    },

    "whatweb": {
        "tool": "whatweb",
        "headline": "whatweb is a routing tool: it fingerprints the web stack so you know WHAT to attack next. Every version in brackets is a CVE lookup waiting to happen.",
        "sample": (
            "http://target.com [200 OK] Apache[2.4.29], HTTPServer[Apache/2.4.29 (Ubuntu)], "
            "PHP[7.2.24], WordPress[5.7], JQuery[1.12.4], X-Powered-By[PHP/7.2.24], "
            "Country[US], IP[10.0.0.50]"
        ),
        "reading": [
            {"field": "[200 OK]",
             "means": "The HTTP status — the site responded normally.",
             "do": "Live target; proceed. A 301/302 here means fingerprint the redirect destination instead."},
            {"field": "Apache[2.4.29], PHP[7.2.24]",
             "means": "The server + language, WITH exact versions.",
             "do": "searchsploit these strings — old Apache/PHP versions carry known CVEs. This is your fastest win check."},
            {"field": "WordPress[5.7]",
             "means": "A CMS was detected — the app is WordPress.",
             "do": "Pivot immediately to wpscan; WordPress has its own rich attack surface (plugins/themes/users)."},
            {"field": "JQuery[1.12.4]",
             "means": "An old client-side JS library.",
             "do": "Outdated jQuery → known XSS/prototype-pollution CVEs; note it for client-side testing."},
            {"field": "HTTPServer[... Ubuntu], X-Powered-By",
             "means": "Leaked OS + framework details the server didn't need to reveal.",
             "do": "Ubuntu → tailor payloads; X-Powered-By confirms the backend. Also: these headers are a finding (info leak)."},
        ],
        "reference": {
            "title": "What each fingerprint routes you toward",
            "rows": [
                ("Server/language + version", "searchsploit for version-specific CVEs"),
                ("WordPress / Drupal / Joomla", "run the CMS-specific scanner (wpscan, droopescan)"),
                ("old JS libs (jQuery, Angular)", "client-side CVEs / XSS"),
                ("X-Powered-By, Server headers", "info leak — note it, and it confirms the stack"),
                ("WAF/CDN (Cloudflare)", "expect filtering; plan evasion"),
            ],
        },
        "work_with_it": (
            "Don't attack from whatweb output — ROUTE from it. Each finding points to the next tool: a CMS "
            "→ its scanner, a versioned server/language → a CVE search, an old JS lib → client-side testing. "
            "It turns 'a website' into a prioritised list of specific, version-pinned things to try."
        ),
        "misreads": [
            "whatweb finds direction, not vulnerabilities — the versions are leads to chase, not confirmed bugs.",
            "A detected CMS (WordPress) means switch to its dedicated scanner — don't hand-test it generically.",
            "Server/X-Powered-By headers are themselves a reportable info-leak, not just recon for you.",
        ],
    },

    "wpscan": {
        "tool": "wpscan",
        "headline": "wpscan output is a triage list for a WordPress site. The [!] markers are the findings — and a vulnerable PLUGIN is usually the way in, not the core.",
        "sample": (
            "[+] WordPress version 5.7 identified (Insecure, released 2021-03-09)\n"
            "[+] WordPress theme in use: twentytwenty\n"
            "[i] Plugin(s) Identified:\n"
            "[+] contact-form-7\n"
            " | Version: 5.3.1 (Latest is 5.7.5)\n"
            " | [!] Title: Contact Form 7 < 5.3.2 - Unrestricted File Upload\n"
            "[+] Enumerating Users\n"
            " | admin\n"
            " | editor"
        ),
        "reading": [
            {"field": "WordPress version 5.7 (Insecure)",
             "means": "The core version, flagged 'Insecure' = known CVEs exist for it.",
             "do": "Note it, but core is usually hardened/patched fast — the plugins below are the softer target."},
            {"field": "[!] Title: Contact Form 7 < 5.3.2 - Unrestricted File Upload",
             "means": "THE finding. A [!] line is a confirmed vulnerable plugin with a named exploit class.",
             "do": "This is your entry point. 'Unrestricted File Upload' → drop a webshell. Look up the exploit/PoC."},
            {"field": "Version: 5.3.1 (Latest is 5.7.5)",
             "means": "The plugin is far behind — the gap is where the vulns live.",
             "do": "The bigger the version gap, the more accumulated CVEs. Confirm the vuln applies to 5.3.1."},
            {"field": "Enumerating Users → admin, editor",
             "means": "Valid WordPress usernames were enumerated.",
             "do": "Feed these to a wp-login brute: wpscan --passwords rockyou.txt --usernames admin."},
        ],
        "reference": {
            "title": "Reading the markers",
            "rows": [
                ("[+]", "identified item (version, plugin, theme, user)"),
                ("[!]", "a VULNERABILITY — this is what you act on"),
                ("[i]", "informational context"),
                ("'Insecure' tag", "known CVEs exist for that version"),
                ("Enumerated users", "feed a wp-login password attack"),
            ],
        },
        "work_with_it": (
            "Scan the [!] lines first — vulnerable plugins/themes are the classic WordPress foothold "
            "(especially file-upload and RCE classes → webshell). Bank enumerated usernames for a targeted "
            "login brute. Treat the core version as context, not usually the way in. Run authenticated "
            "(--api-token) for complete vuln data."
        ),
        "misreads": [
            "The core version is rarely the way in — [!] vulnerable PLUGINS are; read those first.",
            "A big plugin version gap = accumulated CVEs, but still confirm the specific bug applies.",
            "Enumerated users aren't access — they're the username half of a login brute you still have to run.",
        ],
    },
})


# ── Batch 4b: credential extraction + DNS zone transfer + ADCS ESC ──────────
OUTPUT_LESSONS.update({

    "mimikatz": {
        "tool": "mimikatz (sekurlsa::logonpasswords)",
        "headline": "Mimikatz dumps a block per logon session. Read the packages: msv gives you the NTLM hash (pass it), wdigest sometimes gives cleartext (a gift on older Windows).",
        "sample": (
            "Authentication Id : 0 ; 515762\n"
            "User Name         : jdoe\n"
            "Domain            : CORP\n"
            "        msv :\n"
            "         * NTLM     : 9f4e1b7c0a2d3e4f5061728394a5b6c7\n"
            "         * SHA1     : aabbccddeeff...\n"
            "        wdigest :\n"
            "         * Password : Summer2024!\n"
            "        kerberos :\n"
            "         * Password : (null)"
        ),
        "reading": [
            {"field": "User Name / Domain",
             "means": "Whose logon session this block belongs to (a user, or a machine account if it ends in $).",
             "do": "Prioritise interactive USER sessions — they hold the credentials worth stealing."},
            {"field": "msv → NTLM : 9f4e...",
             "means": "The account's NT hash, straight from LSASS memory.",
             "do": "Pass-the-Hash with this immediately (nxc -H, psexec -hashes) — no cracking needed. Or crack it (-m 1000)."},
            {"field": "wdigest → Password : Summer2024!",
             "means": "CLEARTEXT password. Present on Win7/2008R2, or when UseLogonCredential=1 is set on newer Windows.",
             "do": "The jackpot — a plaintext credential. Reuse it everywhere; no hash, no cracking."},
            {"field": "kerberos → Password : (null)",
             "means": "This package held no cleartext (normal on patched/modern Windows).",
             "do": "(null) means empty package, NOT an empty account password — fall back to the msv NTLM hash."},
        ],
        "reference": {
            "title": "The credential packages",
            "rows": [
                ("msv → NTLM", "the NT hash — pass it or crack it (always present)"),
                ("wdigest → Password", "cleartext on old Win / when UseLogonCredential=1"),
                ("kerberos → Password", "cleartext on some configs; often (null)"),
                ("tspkg / credman", "extra cleartext sources worth scanning"),
                ("machine account ($)", "usually not useful for reuse"),
            ],
        },
        "work_with_it": (
            "Scan every block for a wdigest/kerberos CLEARTEXT first (instant win). Absent that, take the "
            "msv NTLM hash and pass it — you rarely need to crack. Map which sessions belong to privileged "
            "users (a Domain Admin's cached session on a workstation is how domains fall). Dumping LSASS is "
            "loud: Sysmon EID 10 fires — see the Purple Team module."
        ),
        "misreads": [
            "(null) means that package was empty, NOT that the account password is blank.",
            "You usually don't need to crack — the msv NTLM hash is directly passable, and wdigest may be cleartext.",
            "wdigest cleartext isn't guaranteed — it appears on legacy Windows or when explicitly re-enabled.",
        ],
    },

    "dig": {
        "tool": "dig (AXFR zone transfer)",
        "headline": "A successful AXFR is a jackpot misconfiguration: the DNS server hands you its ENTIRE zone — every internal hostname and IP. SRV records even point you at the domain controllers.",
        "sample": (
            "; <<>> DiG <<>> axfr corp.local @10.0.0.10\n"
            "corp.local.            3600 IN SOA   dc01.corp.local. admin.corp.local. ...\n"
            "corp.local.            3600 IN NS    dc01.corp.local.\n"
            "dc01.corp.local.       3600 IN A     10.0.0.10\n"
            "_ldap._tcp.corp.local. 600  IN SRV   0 100 389 dc01.corp.local.\n"
            "internal-vpn.corp.local. 3600 IN A   10.0.0.200\n"
            "dev-jenkins.corp.local.  3600 IN A   10.0.0.55"
        ),
        "reading": [
            {"field": "the transfer succeeding at all",
             "means": "The server allowed AXFR (zone transfer) — almost always a misconfiguration.",
             "do": "You just got the whole internal namespace for free. If it says 'Transfer failed'/'connection refused', AXFR is (correctly) disabled."},
            {"field": "A records (dc01, internal-vpn, dev-jenkins)",
             "means": "Hostname → IP for every host in the zone — a full internal inventory.",
             "do": "This IS your target list. Names leak purpose: dev-jenkins, internal-vpn, backup-* are juicy pivots."},
            {"field": "_ldap._tcp ... SRV ... dc01",
             "means": "SRV records advertise WHERE domain services live — _ldap._tcp/_kerberos._tcp = the Domain Controllers.",
             "do": "You just found the DCs without scanning. Point your AD tooling (nxc, bloodhound) straight at them."},
            {"field": "SOA / NS records",
             "means": "The authoritative + name servers for the zone.",
             "do": "Confirms the primary DNS/DC; the NS host is high-value."},
        ],
        "reference": {
            "title": "Record types worth reading",
            "rows": [
                ("A / AAAA", "hostname → IP — your inventory"),
                ("SRV (_ldap/_kerberos._tcp)", "locates Domain Controllers & services"),
                ("MX", "mail servers — phishing/relay targets"),
                ("TXT", "SPF/DKIM, sometimes leaked config/secrets"),
                ("CNAME", "aliases — reveal internal naming & third parties"),
            ],
        },
        "work_with_it": (
            "Turn the dump into a map: every A record is a host to enumerate, naming conventions reveal "
            "purpose (target dev/backup/vpn hosts), and SRV records hand you the DCs to aim AD attacks at. "
            "If AXFR is refused (the norm), fall back to brute-forcing subdomains (gobuster dns / dnsrecon)."
        ),
        "misreads": [
            "A successful AXFR is a serious misconfiguration handing you the whole namespace — not routine DNS.",
            "SRV records (_ldap._tcp, _kerberos._tcp) locate the Domain Controllers — don't skip them for the A records.",
            "'Transfer failed' means AXFR is correctly disabled — pivot to subdomain brute-forcing, don't assume no hosts.",
        ],
    },

    "certipy": {
        "tool": "certipy (AD CS enumeration)",
        "headline": "Certipy does the hard part for you: it flags vulnerable certificate templates with an ESC number. That [!] ESC1 isn't a config note — it's a direct path to impersonating any user.",
        "sample": (
            "Certificate Templates\n"
            "  0\n"
            "    Template Name          : UserCert\n"
            "    Enabled                : True\n"
            "    Client Authentication  : True\n"
            "    Enrollee Supplies Subject : True\n"
            "    Requires Manager Approval : False\n"
            "    [!] Vulnerabilities\n"
            "      ESC1 : Enrollee can supply arbitrary SAN and use for authentication"
        ),
        "reading": [
            {"field": "[!] Vulnerabilities → ESC1",
             "means": "Certipy already CLASSIFIED the misconfiguration. ESC1 = you can request a cert as ANY user (incl. Domain Admin).",
             "do": "This is a direct domain-compromise path. Request a cert for a DA, then authenticate as them (certipy req → auth)."},
            {"field": "Enrollee Supplies Subject : True",
             "means": "The dangerous setting BEHIND ESC1 — you choose the certificate's subject/SAN.",
             "do": "Combined with Client Authentication, this is what lets you impersonate. Confirm both are True."},
            {"field": "Client Authentication : True",
             "means": "The cert can be used to authenticate (not just encrypt/sign).",
             "do": "Required for the impersonation to work — a cert you can't auth with is harmless."},
            {"field": "Requires Manager Approval : False",
             "means": "No human approves the request — enrollment is automatic.",
             "do": "Nothing stands between you and the cert. (If True, the path is gated and much harder.)"},
        ],
        "reference": {
            "title": "The ESC classes certipy flags",
            "rows": [
                ("ESC1", "enrollee-supplied SAN + client auth → impersonate anyone"),
                ("ESC2", "any-purpose EKU → broad misuse"),
                ("ESC3", "enrollment agent → request on behalf of others"),
                ("ESC4", "template ACL is writable → make it vulnerable"),
                ("ESC6/8", "CA flag / NTLM relay to web enrollment (certipy relay)"),
            ],
        },
        "work_with_it": (
            "Trust certipy's classification — the ESC number tells you the exact abuse and the certipy "
            "subcommand to run it (ESC1 → req with an alt SAN → auth as that user → you're them). ADCS paths "
            "are often the quietest route to Domain Admin, bypassing password/hash attacks entirely. Prioritise "
            "ESC1/ESC8 when 'Requires Manager Approval' is False."
        ),
        "misreads": [
            "[!] ESC1 is a direct path to impersonate any user (incl. DA) — it's an exploit, not a hardening note.",
            "'Enrollee Supplies Subject: True' + 'Client Authentication: True' is the ESC1 combo — one alone isn't it.",
            "'Requires Manager Approval: True' gates the attack — the easy wins are the ones that say False.",
        ],
    },
})


# ── Batch 5: post-exploitation — getting and reading a shell ────────────────
OUTPUT_LESSONS.update({

    "msfconsole": {
        "tool": "msfconsole (exploit run)",
        "headline": "Metasploit narrates with markers: [*] status, [+] a step succeeded, [-] failure. But only ONE line means you won — 'session opened'. 'Exploit completed, but no session' is a loss.",
        "sample": (
            "[*] Started reverse TCP handler on 10.10.14.5:4444\n"
            "[*] 10.0.0.5:445 - Connecting to target for exploitation.\n"
            "[+] 10.0.0.5:445 - Connection established for exploitation.\n"
            "[+] 10.0.0.5:445 - Target OS selected valid for OS indicated by SMB reply\n"
            "[*] 10.0.0.5:445 - Sending exploit packet\n"
            "[+] 10.0.0.5:445 - ETERNALBLUE overwrite completed successfully!\n"
            "[*] Sending stage (200774 bytes) to 10.0.0.5\n"
            "[*] Meterpreter session 1 opened (10.10.14.5:4444 -> 10.0.0.5:49158)"
        ),
        "reading": [
            {"field": "[*] Started reverse TCP handler on 10.10.14.5:4444",
             "means": "YOUR listener is up, waiting for the payload to call back to LHOST:LPORT.",
             "do": "Confirms the callback address the target must reach. If the target can't reach 10.10.14.5, no session — check routing/VPN."},
            {"field": "[+] ... overwrite completed successfully!",
             "means": "The exploit primitive landed — but this is NOT yet a shell.",
             "do": "Encouraging, but don't celebrate. Wait for the 'session opened' line before assuming access."},
            {"field": "[*] Meterpreter session 1 opened (LHOST -> TARGET)",
             "means": "THE win. You have a live session; the arrow shows your listener ← the target's connection back.",
             "do": "Type `sessions -i 1` to interact. This is the line that matters — everything above was setup."},
            {"field": "(absent) Exploit completed, but no session was created",
             "means": "The exploit FIRED but you got nothing — wrong target build, payload blocked, or EDR ate it.",
             "do": "Treat as failure: re-check target/payload/LHOST, try a different target index or a staged/stageless payload."},
        ],
        "reference": {
            "title": "The markers + the two outcomes",
            "rows": [
                ("[*]", "informational status — what MSF is doing"),
                ("[+]", "a step succeeded (connection, overwrite) — NOT a session"),
                ("[-]", "an error/failure step"),
                ("'session N opened'", "SUCCESS — you have a shell"),
                ("'completed, but no session'", "FAILURE — exploit ran, no access"),
            ],
        },
        "work_with_it": (
            "Scan for exactly one line: 'session opened'. If it's there, drop into it (sessions -i N). If "
            "instead you see 'Exploit completed, but no session was created', it's a miss — the most common "
            "cause is LHOST the target can't reach, or the wrong target build. Green [+] steps are progress, "
            "not proof; the session line is proof."
        ),
        "misreads": [
            "'Exploit completed, but no session was created' is a FAILURE — the exploit fired and gave you nothing.",
            "A [+] 'overwrite completed' is not a shell — only the 'session opened' line is.",
            "No callback usually means LHOST is unreachable from the target (VPN/routing), not that the bug is patched.",
        ],
    },

    "meterpreter": {
        "tool": "meterpreter (post-exploitation)",
        "headline": "Meterpreter answers 'where am I and what can I do?'. getuid tells you your privilege (SYSTEM = you own it), sysinfo tells you the box, and that dictates every next move.",
        "sample": (
            "meterpreter > getuid\n"
            "Server username: NT AUTHORITY\\SYSTEM\n"
            "meterpreter > sysinfo\n"
            "Computer     : WS01\n"
            "OS           : Windows 10 (10.0 Build 19045)\n"
            "Architecture : x64\n"
            "meterpreter > getsystem\n"
            "...got system via technique 1 (Named Pipe Impersonation)."
        ),
        "reading": [
            {"field": "getuid → NT AUTHORITY\\SYSTEM",
             "means": "Your privilege level. SYSTEM is the highest local account — you fully own this machine.",
             "do": "No local privesc needed. Go straight to hashdump / credential theft / lateral movement."},
            {"field": "getuid → a normal user (CORP\\jdoe)",
             "means": "You're a limited user — most post-ex actions (hashdump) will fail.",
             "do": "Escalate FIRST: run getsystem, or a local exploit suggester, before trying to dump anything."},
            {"field": "sysinfo → OS ... Build 19045, x64",
             "means": "The exact OS build and architecture.",
             "do": "Build number = patch level → pick the right kernel exploit; arch (x64) → match your payloads/DLLs."},
            {"field": "getsystem → got system via technique 1",
             "means": "You just escalated from admin to SYSTEM.",
             "do": "Confirm with getuid. Now hashdump and token manipulation are available."},
        ],
        "reference": {
            "title": "Reading your position",
            "rows": [
                ("getuid = SYSTEM", "max local privilege — proceed to loot"),
                ("getuid = user", "escalate before dumping (getsystem / suggester)"),
                ("sysinfo Build", "patch level → kernel-exploit selection"),
                ("hashdump", "local SAM hashes (needs SYSTEM)"),
                ("getsystem failed", "try local exploits / potato attacks"),
            ],
        },
        "work_with_it": (
            "Always run getuid FIRST — it decides everything. SYSTEM means loot immediately (hashdump, "
            "lsa secrets, pivot). A normal user means escalate before anything else, or your commands just "
            "error out. Use sysinfo's build to choose kernel exploits, and remember migrating to a stable "
            "process protects your session from the exploited process dying."
        ),
        "misreads": [
            "getuid = SYSTEM means you're already at max local privilege — stop looking for privesc, start looting.",
            "A non-SYSTEM getuid means hashdump will fail — escalate first, don't just retry it.",
            "sysinfo's Build number is the patch level; it's how you pick a working kernel exploit.",
        ],
    },

    "psexec": {
        "tool": "impacket psexec / wmiexec / smbexec",
        "headline": "These lateral-movement tools narrate HOW they land a shell. psexec creates a service and drops a binary (loud); wmiexec uses WMI (quiet, no binary). The shell you get is usually SYSTEM.",
        "sample": (
            "[*] Requesting shares on 10.0.0.5.....\n"
            "[*] Found writable share ADMIN$\n"
            "[*] Uploading file kxwGtMsl.exe\n"
            "[*] Opening SVCManager on 10.0.0.5.....\n"
            "[*] Creating service kZlP on 10.0.0.5.....\n"
            "[*] Starting service kZlP.....\n"
            "[!] Press help for extra shell commands\n"
            "C:\\Windows\\system32>"
        ),
        "reading": [
            {"field": "[*] Found writable share ADMIN$",
             "means": "You have admin-level write access to that share — psexec needs it to drop its binary.",
             "do": "Confirms admin rights on the target. No writable ADMIN$ → psexec fails; try wmiexec (no share needed)."},
            {"field": "Uploading file kxwGtMsl.exe + Creating service",
             "means": "psexec's mechanism: drop a service binary and register a Windows service to run it.",
             "do": "Know this is LOUD — the service creation logs Event ID 7045, and the binary touches disk (AV can catch it)."},
            {"field": "C:\\Windows\\system32> prompt",
             "means": "You have a shell — and via psexec/smbexec it's almost always running as SYSTEM.",
             "do": "Confirm with `whoami` (expect nt authority\\system). You're now executing on the target."},
            {"field": "(wmiexec instead) no upload, no service",
             "means": "wmiexec runs commands over WMI with no binary drop and no service — much quieter.",
             "do": "Prefer wmiexec/atexec when stealth matters; psexec/smbexec when you need a full SYSTEM shell and don't mind noise."},
        ],
        "reference": {
            "title": "Which exec method, and how loud",
            "rows": [
                ("psexec", "service + binary drop → SYSTEM shell, LOUD (7045)"),
                ("smbexec", "service, no binary → semi-interactive, loud-ish"),
                ("wmiexec", "WMI, no binary, no service → quieter"),
                ("atexec", "scheduled task → runs one command, quiet-ish"),
                ("writable ADMIN$", "confirms admin rights on the target"),
            ],
        },
        "work_with_it": (
            "Match the method to your goal: need a full interactive SYSTEM shell and noise is fine → psexec. "
            "Need stealth → wmiexec (no binary, no service, no 7045). 'Found writable share' is your proof of "
            "admin on the box. Whatever lands, run whoami first to confirm the context, then enumerate or pivot."
        ),
        "misreads": [
            "psexec is LOUD — it creates a service (Event 7045) and drops a binary AV can flag; wmiexec is the quiet option.",
            "'Found writable share ADMIN$' confirms you already have admin rights there — that's why it works.",
            "The shell is usually SYSTEM, but confirm with whoami — don't assume your privilege level.",
        ],
    },
})


# ── Batch 5b: wireless recon/crack + RPC enumeration ───────────────────────
OUTPUT_LESSONS.update({

    "airodump-ng": {
        "tool": "airodump-ng",
        "headline": "airodump-ng is a live radio survey. Read PWR for distance (negative dBm, closer to 0 = nearer), ENC for the attack, and the STATION list for clients you can deauth to force a handshake.",
        "sample": (
            " BSSID              PWR  Beacons  #Data  CH  MB   ENC  CIPHER AUTH ESSID\n"
            " AA:BB:CC:11:22:33  -42     120     340   6  270  WPA2 CCMP   PSK  HomeNet\n"
            " AA:BB:CC:44:55:66  -78      45       2  11  130  WPA2 CCMP   PSK  Corp-WiFi\n"
            "\n"
            " BSSID              STATION            PWR   Rate    Frames\n"
            " AA:BB:CC:11:22:33  DE:AD:BE:EF:00:11  -50   1e-1e   210"
        ),
        "reading": [
            {"field": "PWR  -42  vs  -78",
             "means": "Signal strength in dBm (negative). Closer to 0 = STRONGER/nearer. -42 is close, -78 is far/weak.",
             "do": "Target the strong ones — you need a solid signal to capture a clean handshake and to deauth reliably."},
            {"field": "CH 6",
             "means": "The channel the AP is on.",
             "do": "Lock airodump to it: --channel 6. If you keep hopping channels you'll miss the handshake."},
            {"field": "ENC/CIPHER/AUTH = WPA2/CCMP/PSK",
             "means": "The security. WPA2-PSK = capture-a-handshake-and-crack. WEP = trivial. OPN = open, no crack needed.",
             "do": "For WPA2-PSK: capture the 4-way handshake (-w to a file), then crack offline with aircrack/hashcat."},
            {"field": "STATION  DE:AD:BE:EF:00:11 (under a BSSID)",
             "means": "A CLIENT currently connected to that AP.",
             "do": "This is your deauth target — knock it off (aireplay-ng --deauth) to force it to reconnect and capture the handshake."},
        ],
        "reference": {
            "title": "The columns that drive the attack",
            "rows": [
                ("PWR (negative dBm)", "closer to 0 = stronger/nearer target"),
                ("CH", "channel — lock to it with --channel"),
                ("#Data climbing", "active traffic — good for capture"),
                ("ENC (WPA2/WEP/OPN)", "picks the attack (handshake / trivial / none)"),
                ("STATION rows", "connected clients — your deauth targets"),
            ],
        },
        "work_with_it": (
            "Pick a strong (PWR near 0), WPA2-PSK target with at least one STATION, lock to its CH, and "
            "capture to a file (-w). Deauth a listed client to force the 4-way handshake, watch the top-right "
            "for 'WPA handshake: <BSSID>', then take the .cap offline to aircrack/hashcat. No clients = no "
            "easy handshake; find an AP with active stations."
        ),
        "misreads": [
            "PWR is negative dBm — -42 is a STRONG/close signal, -78 is weak/far. Closer to 0 wins.",
            "You need a connected STATION to deauth for a WPA handshake — an AP with no clients is much harder.",
            "Lock to the target channel (--channel) — channel-hopping means you'll miss the handshake capture.",
        ],
    },

    "aircrack-ng": {
        "tool": "aircrack-ng",
        "headline": "aircrack-ng first tells you whether your capture is even usable: '(1 handshake)' means crackable, '(0 handshakes)' means go re-capture. Then it's a dictionary race to 'KEY FOUND!'.",
        "sample": (
            "Opening capture.cap\n"
            "Read 4521 packets.\n"
            "   #  BSSID              ESSID       Encryption\n"
            "   1  AA:BB:CC:11:22:33  HomeNet     WPA (1 handshake)\n"
            "Choosing first network as target.\n"
            "\n"
            "      [00:02:14] 1823/9999 keys tested (13.5 k/s)\n"
            "      KEY FOUND! [ Summer2024! ]"
        ),
        "reading": [
            {"field": "WPA (1 handshake)",
             "means": "Your capture CONTAINS a valid 4-way handshake — the prerequisite to crack.",
             "do": "Good to go. If it read '(0 handshakes)', stop — your capture is useless; go back and capture one (deauth a client)."},
            {"field": "keys tested (13.5 k/s)",
             "means": "Your cracking rate. WPA is deliberately slow to brute (PBKDF2).",
             "do": "For real speed, convert to hashcat -m 22000 on a GPU — CPU aircrack is fine for small lists only."},
            {"field": "KEY FOUND! [ Summer2024! ]",
             "means": "The Wi-Fi PSK — the network password.",
             "do": "You're on the network. Connect, then treat it as an internal foothold (scan, pivot)."},
            {"field": "(instead) Passphrase not in dictionary",
             "means": "Your wordlist didn't contain the password. The handshake is fine; the list wasn't.",
             "do": "Not uncrackable — try a bigger/targeted list (rockyou, or ESSID-themed) or rules. WPA-PSK is dictionary-only."},
        ],
        "reference": {
            "title": "Two checkpoints",
            "rows": [
                ("(1 handshake)", "capture is valid — crack can proceed"),
                ("(0 handshakes)", "capture unusable — re-capture (deauth a client)"),
                ("keys tested k/s", "your rate — move to hashcat -m 22000 for GPU speed"),
                ("KEY FOUND!", "the PSK — you're on the network"),
                ("not in dictionary", "wrong wordlist, not uncrackable — try a better one"),
            ],
        },
        "work_with_it": (
            "Read the handshake count FIRST — no handshake, no crack, full stop. With a valid capture, aircrack "
            "on CPU is only for tiny lists; convert the .cap/.pcapng to hashcat -m 22000 and crack on a GPU for "
            "real throughput. A found PSK is an internal foothold — connect and pivot like any other network."
        ),
        "misreads": [
            "'(0 handshakes)' means your capture is worthless — you must capture a handshake before cracking.",
            "aircrack only tests YOUR wordlist — 'not in dictionary' means try a better list, not that it's uncrackable.",
            "WPA/WPA2-PSK is dictionary-only (no WEP-style shortcut) — success depends entirely on your wordlist.",
        ],
    },

    "rpcclient": {
        "tool": "rpcclient",
        "headline": "rpcclient talks MS-RPC to a target — and with a null session it enumerates the domain without creds. The gold: user lists (enumdomusers), hidden passwords (querydispinfo), and the password policy.",
        "sample": (
            "rpcclient $> enumdomusers\n"
            "user:[Administrator] rid:[0x1f4]\n"
            "user:[jdoe] rid:[0x44f]\n"
            "user:[svc_sql] rid:[0x450]\n"
            "rpcclient $> querydispinfo\n"
            "Name: John Doe  Desc: (temp pw Welcome1!)  RID: 0x44f\n"
            "rpcclient $> getdompwinfo\n"
            "min_password_length: 7\n"
            "password_properties: 0x00000000"
        ),
        "reading": [
            {"field": "enumdomusers → user:[...] rid:[0x...]",
             "means": "The domain user list with RIDs. 0x1f4 = 500 = Administrator; 0x44f+ = created users.",
             "do": "Harvest every username into a list (convert hex RIDs if needed). If a null session got you here, you had NO creds."},
            {"field": "querydispinfo → Desc: (temp pw Welcome1!)",
             "means": "User descriptions — and admins hide passwords in them, just like LDAP description fields.",
             "do": "READ every Desc. Cleartext creds here are a free foothold — a classic, still-common finding."},
            {"field": "getdompwinfo → min_password_length: 7",
             "means": "The domain password policy (min length, complexity, lockout).",
             "do": "Sets your spray parameters — short minimum + weak complexity = spray-friendly."},
            {"field": "password_properties: 0x00000000",
             "means": "The complexity bitmask. 0x0 = NO complexity requirement enforced.",
             "do": "Weak-password heaven. 0x1 would mean complexity ON. Combine with lockout info before spraying."},
        ],
        "reference": {
            "title": "The commands worth running",
            "rows": [
                ("enumdomusers", "domain user list + RIDs (feed your spray list)"),
                ("querydispinfo", "user descriptions — hunt hidden passwords"),
                ("getdompwinfo", "password policy — sets spray parameters"),
                ("queryuser <rid>", "detail on one account (last logon, flags)"),
                ("null session (-U '' -N)", "all of the above with NO credentials"),
            ],
        },
        "work_with_it": (
            "Try a null session first (-U '' -N) — if it works, you enumerate users, descriptions, and policy "
            "for free. Build a username list from enumdomusers, scrape querydispinfo Desc fields for plaintext "
            "creds, and read getdompwinfo to set safe spray parameters (stay under the lockout threshold). "
            "It's the no-creds AD-enum workhorse alongside enum4linux."
        ),
        "misreads": [
            "rpcclient with '-U \"\" -N' enumerates the domain with NO credentials when null sessions are allowed.",
            "querydispinfo Desc fields routinely hold cleartext passwords — read them like LDAP descriptions.",
            "password_properties 0x0 means complexity is OFF (spray-friendly); 0x1 means it's enforced.",
        ],
    },
})


# ── Batch 6: privilege-escalation enumeration + fast recon ─────────────────
OUTPUT_LESSONS.update({

    "linpeas": {
        "tool": "linpeas / winpeas",
        "headline": "linpeas output is a firehose — thousands of lines. The skill is NOT reading it top to bottom; it's hunting the RED/YELLOW highlights, which mean '99% a privesc vector'.",
        "sample": (
            "╔══════╣ Sudo version\n"
            "Sudo version 1.8.21p2          <-- highlighted RED (known CVE)\n"
            "╔══════╣ CVEs Check\n"
            "[+] [CVE-2021-4034] PwnKit\n"
            "   Vulnerable! polkit pkexec found\n"
            "╔══════╣ Interesting writable files\n"
            "/etc/passwd                    <-- highlighted YELLOW (writable!)\n"
            "/usr/bin/find (SUID)           <-- highlighted RED"
        ),
        "reading": [
            {"field": "RED / YELLOW highlighted text",
             "means": "linpeas's colour code: bright RED+YELLOW = 95-99% a privilege-escalation vector. This is the signal in the noise.",
             "do": "Jump straight to the highlights. Ignore the plain-white text on the first pass — the colours ARE the findings."},
            {"field": "[+] [CVE-2021-4034] PwnKit — Vulnerable!",
             "means": "linpeas actively confirmed a known privesc exploit is present (PwnKit here).",
             "do": "A near-guaranteed win. Grab the public PoC and run it — these confirmed CVEs are your fastest path to root."},
            {"field": "/etc/passwd (writable!)",
             "means": "A sensitive file you can write to.",
             "do": "Writable /etc/passwd → add a root user (openssl passwd). Writable cron/service → hijack it. Direct privesc."},
            {"field": "/usr/bin/find (SUID) — RED",
             "means": "A SUID binary that runs as its owner (often root).",
             "do": "Check GTFOBins for that binary — SUID find/vim/nmap etc. are instant root."},
        ],
        "reference": {
            "title": "The colour code (learn this, skip the rest)",
            "rows": [
                ("RED + YELLOW", "95-99% a privesc vector — start here"),
                ("RED", "special interest — worth checking"),
                ("[+] CVE ... Vulnerable!", "confirmed exploit present — near-guaranteed"),
                ("(writable!) on system files", "direct privesc (passwd/cron/service)"),
                ("SUID/sudo highlights", "GTFOBins path to root"),
            ],
        },
        "work_with_it": (
            "Never read linpeas linearly — you'll drown. Scroll for colour: RED+YELLOW first, then RED. Cross-"
            "reference every confirmed CVE and SUID against public PoCs and GTFOBins. Run linpeas with -a for the "
            "full sweep, but triage by highlight — the tool already did the ranking for you in colour."
        ),
        "misreads": [
            "Don't read linpeas top to bottom — hunt the RED/YELLOW highlights; they're the 99%-real vectors.",
            "A highlighted version (e.g. Sudo 1.8.21) means linpeas suspects a CVE — verify and grab the PoC.",
            "Plain-white lines are context, not findings — the colour is doing the triage; trust it first-pass.",
        ],
    },

    "pspy": {
        "tool": "pspy",
        "headline": "pspy watches processes and cron WITHOUT root — its whole purpose is to reveal the root-run scheduled jobs you can't see in your own crontab. A UID=0 command on a timer is a privesc lead.",
        "sample": (
            "2024/06/01 12:00:01 CMD: UID=0    PID=1234 | /bin/bash /opt/backup.sh\n"
            "2024/06/01 12:01:01 CMD: UID=0    PID=1250 | /bin/bash /opt/backup.sh\n"
            "2024/06/01 12:02:01 CMD: UID=0    PID=1266 | /bin/bash /opt/backup.sh\n"
            "2024/06/01 12:05:00 CMD: UID=1000 PID=1301 | curl http://internal/api?token=abc123"
        ),
        "reading": [
            {"field": "UID=0 ... /opt/backup.sh (repeating every minute)",
             "means": "A ROOT-owned script running on a schedule (a cron job). The repeating timestamp reveals the interval.",
             "do": "Check if you can WRITE to /opt/backup.sh (or anything it calls). If yes → put your payload in it → root on next run."},
            {"field": "the timestamp interval (00, 01, 02...)",
             "means": "How often the job fires — here every minute.",
             "do": "Tells you how long you'll wait for your hijack to trigger. A wildcard/tar cron may also be abusable."},
            {"field": "UID=1000 ... curl ...?token=abc123",
             "means": "Command arguments leak secrets — here an API token in a URL.",
             "do": "Harvest creds/tokens from command lines; they're visible to any user watching with pspy."},
            {"field": "PID climbing each run",
             "means": "A fresh process each interval confirms it's scheduled, not a one-off.",
             "do": "Confirms a recurring job you can target, versus a single manual command."},
        ],
        "reference": {
            "title": "What pspy surfaces",
            "rows": [
                ("UID=0 on a timer", "root cron job — check write access to the script"),
                ("repeating timestamps", "the schedule/interval of the job"),
                ("tokens/passwords in args", "creds leaked on the command line"),
                ("tar/rsync with wildcards", "wildcard-injection privesc"),
                ("no crontab access needed", "pspy shows root's jobs you can't read"),
            ],
        },
        "work_with_it": (
            "Let pspy run for a few minutes to catch the cron cycle. For every UID=0 job, test write access to the "
            "script and every path it references — a writable root cron script is game over. Watch command "
            "arguments for leaked tokens/passwords, and note wildcard tar/rsync jobs (classic wildcard-injection root)."
        ),
        "misreads": [
            "A UID=0 command on a repeating timer is a root cron job — its value is whether you can write to what it runs.",
            "pspy's whole point is showing root's cron jobs you CAN'T see in your own crontab — that's the win.",
            "Command arguments leak secrets (tokens, passwords) to anyone watching — harvest them.",
        ],
    },

    "snmpwalk": {
        "tool": "snmpwalk",
        "headline": "SNMP with a guessed community string ('public') is authentication-free enumeration: it leaks processes, users, network config, even installed software. 'private' often means WRITE.",
        "sample": (
            "snmpwalk -v2c -c public 10.0.0.5\n"
            "SNMPv2-MIB::sysDescr.0 = STRING: Linux fileserver 5.4.0 x86_64\n"
            "HOST-RESOURCES-MIB::hrSWRunName.42 = STRING: apache2\n"
            "HOST-RESOURCES-MIB::hrSWRunName.51 = STRING: mysqld\n"
            "IP-MIB::ipAdEntAddr.10.0.0.5 = IpAddress: 10.0.0.5\n"
            "SNMPv2-MIB::sysContact.0 = STRING: admin@corp.local"
        ),
        "reading": [
            {"field": "the fact it returned data at all (-c public)",
             "means": "The 'public' community string worked — SNMP handed you data with no real authentication.",
             "do": "'public'/'private' are the default guesses. If you get output, the device is leaking. No output = wrong community/version."},
            {"field": "sysDescr = Linux fileserver 5.4.0",
             "means": "OS, hostname, kernel version — free fingerprinting.",
             "do": "Version → CVE search; hostname/role ('fileserver') → prioritise the target."},
            {"field": "hrSWRunName = apache2 / mysqld",
             "means": "The list of RUNNING processes — effectively a remote tasklist over SNMP.",
             "do": "See what services run without touching them; plan attacks on the exposed software."},
            {"field": "sysContact = admin@corp.local",
             "means": "Leaked admin contact / usernames — and other OIDs leak full user lists, ARP, routes.",
             "do": "Harvest usernames/emails for spraying/phishing; walk further for network topology."},
        ],
        "reference": {
            "title": "SNMP essentials",
            "rows": [
                ("-c public", "the default READ community to guess first"),
                ("-c private", "often grants WRITE — reconfigure the device"),
                ("-v2c / -v1", "version must match; try both if no output"),
                ("hrSWRunName", "running processes (remote tasklist)"),
                ("no output", "wrong community or version — try onesixtyone to brute"),
            ],
        },
        "work_with_it": (
            "Guess community strings first (public/private, or brute with onesixtyone). A working READ community "
            "leaks a goldmine: OS, processes, users, network layout — enumerate a host without authenticating. If "
            "'private' works you may reconfigure the device. No output usually means the wrong community or SNMP version."
        ),
        "misreads": [
            "'public' is a default community that leaks huge amounts with NO real auth — always try it.",
            "'private' frequently grants WRITE access — you can reconfigure the device, not just read it.",
            "No output usually means wrong community/version, not that SNMP is absent — brute the community.",
        ],
    },
})


# ── Batch 6b: WinRM shell + exploit search + fast port discovery ───────────
OUTPUT_LESSONS.update({

    "evil-winrm": {
        "tool": "evil-winrm",
        "headline": "evil-winrm is a POST-auth PowerShell shell over WinRM — you don't get the prompt without valid creds or a hash. Read whoami (you're the user, not SYSTEM) and use the menu for its built-in helpers.",
        "sample": (
            "$ evil-winrm -i 10.0.0.15 -u jdoe -H 9f4e1b7c0a2d3e4f5061728394a5b6c7\n"
            "Evil-WinRM shell v3.5\n"
            "*Evil-WinRM* PS C:\\Users\\jdoe\\Documents> whoami\n"
            "corp\\jdoe\n"
            "*Evil-WinRM* PS C:\\Users\\jdoe\\Documents> menu\n"
            "  upload  download  services  Bypass-4MSI  Dll-Loader  Invoke-Binary"
        ),
        "reading": [
            {"field": "-u jdoe -H <hash>  (or -p <pass>)",
             "means": "evil-winrm authenticates with a password (-p) OR an NT hash (-H, pass-the-hash). It is NOT an exploit.",
             "do": "You need valid creds/hash to connect. If auth fails, the account lacks WinRM rights (Remote Management Users) — try another."},
            {"field": "*Evil-WinRM* PS C:\\...> prompt",
             "means": "You have an interactive PowerShell session over WinRM (port 5985/5986).",
             "do": "You're executing on the target. Enumerate, but check your privilege first — you're not automatically admin."},
            {"field": "whoami → corp\\jdoe",
             "means": "You are the AUTHENTICATED user, not SYSTEM.",
             "do": "A normal user — run winPEAS/privesc checks before assuming you can dump creds. Escalate if needed."},
            {"field": "menu → Bypass-4MSI, Dll-Loader, Invoke-Binary",
             "means": "evil-winrm's built-in helpers: AMSI bypass, in-memory DLL/EXE loading, file transfer.",
             "do": "Run Bypass-4MSI BEFORE loading PowerShell tools so AMSI doesn't flag them; use Invoke-Binary to run .NET in memory."},
        ],
        "reference": {
            "title": "Connecting + the menu",
            "rows": [
                ("-u/-p", "auth with username + password"),
                ("-u/-H", "pass-the-hash with the NT hash"),
                ("prompt appears", "valid auth — you have a PS session"),
                ("Bypass-4MSI", "disable AMSI before loading tools"),
                ("Invoke-Binary / Dll-Loader", "run .NET/DLLs in memory (no disk)"),
            ],
        },
        "work_with_it": (
            "Reach evil-winrm only AFTER you have creds or a hash (from secretsdump, responder-cracked, etc.). "
            "Once in, run whoami/whoami /priv to fix your privilege level, Bypass-4MSI before any PowerShell "
            "tooling, and load tools in memory (Invoke-Binary) to avoid touching disk. It's the clean interactive "
            "shell for a Windows box you already have valid access to."
        ),
        "misreads": [
            "evil-winrm is post-auth — it needs valid creds or an NT hash (-H); it does not exploit anything.",
            "You're the authenticated USER, not SYSTEM — check whoami and escalate before dumping creds.",
            "Run Bypass-4MSI first or AMSI will flag your PowerShell payloads as you load them.",
        ],
    },

    "searchsploit": {
        "tool": "searchsploit",
        "headline": "searchsploit is a local grep of Exploit-DB. It gives you a Title and a Path — but the version in the title must match your target EXACTLY, and a hit is a lead, not a guarantee.",
        "sample": (
            "$ searchsploit vsftpd 2.3.4\n"
            "--------------------------------------------- -------------------------\n"
            " Exploit Title                                |  Path\n"
            "--------------------------------------------- -------------------------\n"
            " vsftpd 2.3.4 - Backdoor Command Execution    | unix/remote/17491.rb\n"
            " vsftpd 2.3.4 - Backdoor Command Exec (Meta.) | unix/remote/49757.py\n"
            "--------------------------------------------- -------------------------\n"
            " Shellcodes: No Results"
        ),
        "reading": [
            {"field": "the version in the Title (vsftpd 2.3.4)",
             "means": "The exact software+version the exploit targets.",
             "do": "Match it to YOUR target's version precisely — a 2.3.4 exploit may not touch 2.3.5. Version drift = wasted time."},
            {"field": "Path: unix/remote/17491.rb",
             "means": "The exploit file's location in the local Exploit-DB copy, and its category (unix/remote).",
             "do": "'remote' = fire it at the target; 'local' = privesc once you're on the box. Copy it out with -m <path>."},
            {"field": "-m <path> vs -x <path>",
             "means": "-m mirrors (copies) the exploit to your cwd; -x examines (prints) it.",
             "do": "Read it with -x FIRST (understand/verify it, check for hardcoded IPs), then -m to use it."},
            {"field": "No Results (Shellcodes/Papers)",
             "means": "Nothing matched in that category — NOT proof the target is safe.",
             "do": "Exploit-DB isn't exhaustive and titles vary; also search the CVE, GitHub, and try broader terms."},
        ],
        "reference": {
            "title": "Using the results",
            "rows": [
                ("Title version", "must match your target EXACTLY"),
                ("unix/linux/windows + remote/local", "how/where the exploit runs"),
                ("-x <path>", "read/verify the exploit first"),
                ("-m <path>", "copy it locally to use"),
                ("No Results", "not 'safe' — search CVE/GitHub too"),
            ],
        },
        "work_with_it": (
            "Feed it the EXACT version string from your -sV/banner output. Read promising hits with -x (verify they "
            "apply, and check for hardcoded attacker IPs/ports to change), then -m to copy locally. Remember it only "
            "knows Exploit-DB — cross-check the CVE and GitHub for PoCs it doesn't carry before concluding 'no exploit'."
        ),
        "misreads": [
            "The title version must match the target EXACTLY — a near-miss version often won't work.",
            "'No Results' means Exploit-DB has nothing indexed, not that the target is unexploitable — search wider.",
            "Read the exploit (-x) before running it — many have hardcoded IPs/ports you must edit.",
        ],
    },

    "masscan": {
        "tool": "masscan",
        "headline": "masscan finds open ports at internet scale in minutes — but gives you NOTHING but the port and IP. No service, no version. It's the fast first pass; nmap does the detail second.",
        "sample": (
            "$ masscan 10.0.0.0/24 -p1-65535 --rate 10000\n"
            "Discovered open port 445/tcp on 10.0.0.5\n"
            "Discovered open port 22/tcp on 10.0.0.15\n"
            "Discovered open port 3389/tcp on 10.0.0.20\n"
            "Discovered open port 8080/tcp on 10.0.0.20"
        ),
        "reading": [
            {"field": "Discovered open port 445/tcp on 10.0.0.5",
             "means": "A port + host — that's ALL. No service name, no version, no depth.",
             "do": "Collect these into a target/port list. This is breadth, not detail — don't try to act on it directly."},
            {"field": "the absence of service/version info",
             "means": "masscan does NOT do -sV — it only confirms a port answered.",
             "do": "Follow up: nmap -sV -sC -p445,22,3389 <hosts> on exactly these hits to learn what's actually there."},
            {"field": "--rate 10000",
             "means": "Packets per second — masscan's speed dial, and its accuracy trade-off.",
             "do": "Too high a rate drops packets and MISSES open ports (false negatives). Lower it on unreliable links / big ranges."},
            {"field": "a whole /24 in seconds",
             "means": "masscan's strength is breadth — huge ranges, fast.",
             "do": "Use it to triage a large scope quickly, then hand the discovered ports to nmap for depth."},
        ],
        "reference": {
            "title": "masscan vs nmap (breadth vs depth)",
            "rows": [
                ("masscan", "huge ranges, FAST, port+IP only"),
                ("nmap -sV", "one/few hosts, service+version detail"),
                ("--rate", "speed vs accuracy — too high drops packets"),
                ("-p1-65535", "all ports (masscan is fast enough to)"),
                ("workflow", "masscan to find → nmap -sV on the hits"),
            ],
        },
        "work_with_it": (
            "Use masscan for the breadth pass on a big scope: all ports, whole ranges, in minutes — then pipe the "
            "discovered host:port pairs into nmap -sV for the detail that masscan deliberately skips. Tune --rate "
            "down if you see inconsistent results; a too-fast scan silently misses ports and gives false confidence."
        ),
        "misreads": [
            "masscan gives port+IP only — NO service/version; you must follow up with nmap -sV on the hits.",
            "A too-high --rate drops packets and misses open ports — speed is traded for accuracy.",
            "masscan is breadth, nmap is depth — use them together, not one instead of the other.",
        ],
    },
})


# ── Batch 7: OSINT + subdomain/DNS enumeration ─────────────────────────────
OUTPUT_LESSONS.update({

    "theharvester": {
        "tool": "theHarvester",
        "headline": "theHarvester is passive OSINT — it pulls emails, hosts, and subdomains from public sources without touching the target. The emails reveal the username CONVENTION, which you extrapolate into a full list.",
        "sample": (
            "[*] Target: corp.com  |  Sources: crtsh, bing, duckduckgo\n"
            "[*] Emails found:\n"
            "jdoe@corp.com\n"
            "a.smith@corp.com\n"
            "[*] Hosts found:\n"
            "mail.corp.com:203.0.113.25\n"
            "vpn.corp.com:203.0.113.5\n"
            "dev-portal.corp.com:203.0.113.40"
        ),
        "reading": [
            {"field": "Emails: jdoe@ , a.smith@",
             "means": "Real addresses — and more importantly, the USERNAME FORMAT the org uses (firstinitial+last, or first.last).",
             "do": "Extrapolate the convention to build a full username list from employee names (LinkedIn) for spraying/phishing."},
            {"field": "Hosts: mail / vpn / dev-portal",
             "means": "Public-facing subdomains and their IPs — the external attack surface.",
             "do": "Prioritise by name: vpn (auth to attack), dev-portal (less hardened), mail (phishing/relay)."},
            {"field": "Sources: crtsh vs bing/duckduckgo",
             "means": "WHERE each result came from. crt.sh = certificate transparency (authoritative); search engines = scraped, hit-or-miss.",
             "do": "Trust crt.sh subdomains most; treat scraped results as leads to verify."},
            {"field": "the whole run being passive",
             "means": "No packets went to the target — it's all third-party data.",
             "do": "Stealthy recon you can run before touching anything, but only as fresh/complete as public records are."},
        ],
        "reference": {
            "title": "What to extract",
            "rows": [
                ("email format", "the username convention → full user list"),
                ("subdomains/hosts", "external attack surface (crt.sh most reliable)"),
                ("IPs", "map the external footprint / IP ranges"),
                ("passive", "no target contact — stealthy, but only public data"),
                ("-b crtsh,hunter,...", "pick sources; more sources = more coverage"),
            ],
        },
        "work_with_it": (
            "Mine the email format first — one 'jdoe@corp.com' tells you every employee's likely username, which you "
            "turn into a spray/phish list from public name sources. Feed subdomains into your active enum, trusting "
            "crt.sh over scraped hits. It's the quiet first move before any packet hits the target."
        ),
        "misreads": [
            "Harvested emails reveal the username CONVENTION — extrapolate it into a full list, don't just use the few found.",
            "It's passive OSINT — stealthy, but only as current and complete as public sources are.",
            "crt.sh (cert transparency) subdomains are more reliable than search-engine-scraped ones.",
        ],
    },

    "subfinder": {
        "tool": "subfinder / amass",
        "headline": "Subdomain enumeration prints one host per line — but the NAMES leak purpose. dev/staging/test are your softest targets; jenkins/gitlab/admin the juiciest. A found subdomain isn't necessarily live.",
        "sample": (
            "$ subfinder -d corp.com -silent\n"
            "www.corp.com\n"
            "mail.corp.com\n"
            "dev.corp.com\n"
            "staging-api.corp.com\n"
            "jenkins.corp.com\n"
            "vpn.corp.com\n"
            "[found 47 subdomains]"
        ),
        "reading": [
            {"field": "dev / staging-api / test.*",
             "means": "Non-production environments — typically far less hardened than prod.",
             "do": "Hit these FIRST. Dev/staging often have debug enabled, default creds, and weaker WAF/monitoring."},
            {"field": "jenkins / gitlab / admin / internal",
             "means": "High-value services exposed by name — CI/CD, source, admin panels.",
             "do": "Jenkins/GitLab → RCE + secrets goldmines; admin panels → auth attacks. Prioritise these."},
            {"field": "the count (47 subdomains)",
             "means": "Breadth of the discovered surface.",
             "do": "A big list needs triage — resolve and probe for LIVE ones before scanning everything."},
            {"field": "(implicit) a listed name may not resolve/be live",
             "means": "Passive sources include stale/dead records.",
             "do": "Pipe into dnsx (resolve) then httpx (probe) to keep only live hosts — don't waste scans on dead names."},
        ],
        "reference": {
            "title": "Triage by name, then verify",
            "rows": [
                ("dev/staging/test/uat", "softer targets — start here"),
                ("jenkins/gitlab/git", "CI/CD & source — RCE + secrets"),
                ("admin/portal/vpn", "auth surfaces to attack"),
                ("passive (subfinder) vs brute (amass)", "combine for coverage"),
                ("subfinder | dnsx | httpx", "resolve + probe → live hosts only"),
            ],
        },
        "work_with_it": (
            "Read the list as a priority queue, not just names: dev/staging/test are the softest, CI/CD and admin the "
            "richest. Then verify — pipe through dnsx and httpx so you only scan hosts that actually resolve and "
            "respond. Combine passive (subfinder) with brute-forcing (amass/gobuster dns) to catch hosts with no public record."
        ),
        "misreads": [
            "Subdomain names leak purpose — dev/staging/test are the softest targets, internal/admin the juiciest.",
            "A discovered subdomain isn't necessarily LIVE — resolve and probe (dnsx/httpx) before attacking it.",
            "Passive enum misses hosts with no public record — pair it with brute-forcing for full coverage.",
        ],
    },

    "dnsrecon": {
        "tool": "dnsrecon",
        "headline": "dnsrecon bundles three things: record enumeration, a zone-transfer attempt, and subdomain brute-forcing. Read which one produced each finding — and watch for internal RFC1918 IPs leaking the network layout.",
        "sample": (
            "[*] General Enumeration of Domain: corp.com\n"
            "[*]     SOA ns1.corp.com 203.0.113.53\n"
            "[*]     MX mail.corp.com 10\n"
            "[*]     A  www.corp.com 203.0.113.10\n"
            "[*]     TXT corp.com \"v=spf1 include:_spf.google.com\"\n"
            "[-] Zone Transfer Failed (Refused)\n"
            "[*] Brute-forcing subdomains...\n"
            "[*]     A  dev.corp.com 10.0.0.60"
        ),
        "reading": [
            {"field": "SOA / MX / A / TXT records",
             "means": "The standard DNS record set — name servers, mail, hosts, and TXT policy.",
             "do": "MX → mail/phishing targets; TXT → SPF (reveals mail providers), sometimes leaked verification/config."},
            {"field": "[-] Zone Transfer Failed (Refused)",
             "means": "AXFR was attempted and (correctly) denied — the common case.",
             "do": "If it ever SUCCEEDS, that's a jackpot dumping the whole zone (see the dig lesson). Refused → rely on the brute-force below."},
            {"field": "Brute-forcing → A dev.corp.com 10.0.0.60",
             "means": "A subdomain found by guessing, resolving to an INTERNAL IP.",
             "do": "dev + internal IP is a double signal: soft target AND it exposes the internal range (10.0.0.0/24)."},
            {"field": "an RFC1918 IP (10.0.0.60) in public DNS",
             "means": "A private/internal IP is leaking into public DNS records.",
             "do": "This maps the internal network for you — note the range for later pivoting/scanning."},
        ],
        "reference": {
            "title": "The three phases + the leaks",
            "rows": [
                ("record enum (SOA/MX/A/TXT)", "providers, mail, hosts, policy"),
                ("AXFR attempt", "jackpot if it succeeds; usually refused"),
                ("subdomain brute", "fallback discovery when AXFR fails"),
                ("RFC1918 IPs in records", "internal network layout leak"),
                ("TXT records", "SPF/DKIM, sometimes config/secrets"),
            ],
        },
        "work_with_it": (
            "Separate the findings by phase: records give you providers and mail targets, the AXFR attempt is a "
            "long-shot jackpot, and the brute-force is your reliable subdomain discovery. Flag any internal "
            "(10.x/192.168.x/172.16.x) IPs in the output — they leak the internal network you'll pivot into later."
        ),
        "misreads": [
            "dnsrecon bundles record-enum + AXFR + brute-force — read which phase produced each finding.",
            "Internal RFC1918 IPs in public DNS leak the internal network layout — note the ranges.",
            "Zone-transfer 'Refused' is normal; the brute-force results are your fallback, not a failure.",
        ],
    },
})


# ── Batch 7b: web-server vuln scan + WAF detection + TLS analysis ──────────
OUTPUT_LESSONS.update({

    "nikto": {
        "tool": "nikto",
        "headline": "nikto fires thousands of checks for known dangerous files and misconfigs — so it's LOUD, and its output mixes real findings with false positives. Read the '+' lines for interesting paths and info leaks.",
        "sample": (
            "+ Server: Apache/2.4.29 (Ubuntu)\n"
            "+ /admin/: Admin login page/section found.\n"
            "+ /phpinfo.php: Output from the phpinfo() function was found.\n"
            "+ OSVDB-3268: /backup/: Directory indexing found.\n"
            "+ Apache/2.4.29 appears outdated (current is at least 2.4.58)\n"
            "+ /: Server leaks inodes via ETags, header found, inode: 12345"
        ),
        "reading": [
            {"field": "+ /phpinfo.php: phpinfo() output found",
             "means": "A real info-disclosure finding — phpinfo dumps the full server config, paths, modules, env vars.",
             "do": "Go read it. It leaks absolute paths (for LFI/upload), loaded modules, and sometimes secrets."},
            {"field": "+ /admin/ , /backup/ (Directory indexing)",
             "means": "Interesting paths nikto found — an admin panel, and a browsable backup directory.",
             "do": "/admin/ → auth attacks; /backup/ with indexing → download everything (source, DB dumps)."},
            {"field": "OSVDB-3268 and version-outdated notes",
             "means": "Known-issue references and version-based warnings.",
             "do": "Leads, not proof — confirm the outdated version's CVEs actually apply; some warnings are generic."},
            {"field": "the sheer volume + '+' prefix",
             "means": "nikto is noisy and every check prints; not all '+' lines are exploitable.",
             "do": "Triage: info leaks (phpinfo) and browsable dirs are gold; ETag/inode and generic notes are low-value."},
        ],
        "reference": {
            "title": "Signal vs noise in nikto",
            "rows": [
                ("phpinfo / .env / config leaks", "high-value info disclosure"),
                ("browsable dirs (indexing)", "download source/backups"),
                ("/admin /login panels", "auth attack surface"),
                ("OSVDB / version notes", "leads — verify the CVE applies"),
                ("ETag/inode, generic headers", "low-value, often noise"),
            ],
        },
        "work_with_it": (
            "Because nikto is LOUD (thousands of requests, trivially logged/blocked), save it for authorized/lab scans, "
            "not stealth. Triage the '+' lines: chase info leaks (phpinfo, exposed config) and browsable directories "
            "first, verify version/OSVDB notes against real CVEs, and ignore the generic ETag/header noise."
        ),
        "misreads": [
            "nikto is LOUD (thousands of requests) — fine for authorized scans, terrible for stealth.",
            "phpinfo.php disclosure leaks the whole server config (paths, modules, secrets) — a real, actionable finding.",
            "Not every '+' line is exploitable — many (ETags, generic notes) are noise; triage for info leaks and dirs.",
        ],
    },

    "wafw00f": {
        "tool": "wafw00f",
        "headline": "wafw00f tells you if a WAF/CDN sits in front of the target — which changes everything downstream. A WAF means your payloads get filtered; a CDN like Cloudflare hides the real origin IP.",
        "sample": (
            "[*] Checking https://corp.com\n"
            "[+] The site https://corp.com is behind Cloudflare (Cloudflare Inc.) WAF.\n"
            "[~] Number of requests: 12"
        ),
        "reading": [
            {"field": "[+] behind Cloudflare ... WAF",
             "means": "A Web Application Firewall / CDN is inspecting and filtering traffic to the site.",
             "do": "Expect your scanners and injection payloads to be blocked/challenged. Plan evasion (encoding, slow rate, unusual methods)."},
            {"field": "Cloudflare / Akamai / CDN specifically",
             "means": "A CDN proxies the site — the IP you're hitting is the CDN's, not the real server.",
             "do": "Find the ORIGIN IP (DNS history, non-proxied subdomains like mail/dev, SSL cert search) and hit it directly to bypass the WAF."},
            {"field": "the specific vendor named (F5, ModSecurity, Imperva)",
             "means": "wafw00f fingerprinted WHICH WAF.",
             "do": "Look up vendor-specific bypasses — each WAF has known evasion techniques and default rule gaps."},
            {"field": "(instead) No WAF detected",
             "means": "wafw00f didn't identify a WAF — but that's not a guarantee one isn't there.",
             "do": "Scan more freely, but stay alert for silent blocking (sudden 403s) — some WAFs hide from wafw00f."},
        ],
        "reference": {
            "title": "What a WAF result means for you",
            "rows": [
                ("WAF detected", "payloads filtered — plan evasion"),
                ("Cloudflare/CDN", "origin IP hidden — find + hit it directly"),
                ("named vendor", "look up vendor-specific bypasses"),
                ("No WAF detected", "scan freer, but not a guarantee"),
                ("sudden 403 flood mid-scan", "you tripped a WAF rule — back off"),
            ],
        },
        "work_with_it": (
            "Run wafw00f BEFORE heavy web testing so blocks don't surprise you. If a CDN is in front, your priority "
            "becomes finding the origin IP (DNS history, non-proxied subdomains, cert search) to sidestep the WAF "
            "entirely. If it's an inline WAF, throttle down, encode payloads, and research that vendor's known bypasses."
        ),
        "misreads": [
            "A detected WAF means payloads get filtered — expect blocks and plan evasion, don't just blast harder.",
            "Cloudflare/CDN hides the origin IP — bypass the WAF by finding and hitting the real server directly.",
            "'No WAF detected' is not a guarantee — some WAFs evade wafw00f; watch for silent 403 blocking.",
        ],
    },

    "sslscan": {
        "tool": "sslscan / testssl.sh",
        "headline": "A TLS scan flags weak protocols/ciphers (reportable findings) and runs vuln checks — but the sleeper win is the certificate's Subject/SAN, which routinely leaks INTERNAL hostnames.",
        "sample": (
            "Supported Server Cipher(s):\n"
            "Accepted  TLSv1.0  112 bits  DES-CBC3-SHA        <-- weak/deprecated\n"
            "Accepted  TLSv1.2  256 bits  ECDHE-RSA-AES256-GCM-SHA384\n"
            "Heartbleed:  not vulnerable\n"
            "SSL Certificate:\n"
            "  Not valid after: 2021-01-01 (EXPIRED)\n"
            "  Subject:  CN=vcenter-prod.corp.local\n"
            "  Altnames: DNS:vcenter.corp.local, DNS:esxi01.corp.local"
        ),
        "reading": [
            {"field": "Accepted TLSv1.0 / DES-CBC3-SHA",
             "means": "A deprecated protocol and a weak cipher are enabled.",
             "do": "Reportable findings (TLS 1.0/SSLv3, RC4/DES/3DES, export ciphers). Note them; some enable downgrade attacks."},
            {"field": "Heartbleed / POODLE / ROBOT checks",
             "means": "Named TLS vulnerability tests.",
             "do": "'not vulnerable' is good for them; read the WHOLE list, since one 'vulnerable' (e.g. Heartbleed) is a memory-leak win."},
            {"field": "Subject: CN=vcenter-prod.corp.local + Altnames",
             "means": "The certificate leaks INTERNAL hostnames (vcenter, esxi01) and the internal AD domain.",
             "do": "Recon gold — these are real internal targets and confirm the internal domain (corp.local) for AD attacks."},
            {"field": "Not valid after: 2021 (EXPIRED) / Self-signed",
             "means": "Certificate hygiene issues.",
             "do": "Expired/self-signed = reportable, and often signals an unmanaged/forgotten host worth a closer look."},
        ],
        "reference": {
            "title": "What to pull from a TLS scan",
            "rows": [
                ("TLS 1.0/SSLv3, RC4/DES/3DES", "weak protocols/ciphers — findings"),
                ("Heartbleed/POODLE/ROBOT", "named vulns — one hit is a win"),
                ("cert Subject/SAN", "INTERNAL hostnames + AD domain leak"),
                ("expired/self-signed", "hygiene finding + unmanaged-host signal"),
                ("weak key (RSA 1024)", "reportable weakness"),
            ],
        },
        "work_with_it": (
            "Skim the protocol/cipher list for deprecated entries (quick reportable findings) and check the named-vuln "
            "results for any 'vulnerable'. But don't miss the certificate: the Subject and SAN fields hand you internal "
            "hostnames and the internal AD domain — some of the best recon on the whole engagement, straight off port 443."
        ),
        "misreads": [
            "Weak/deprecated protocols (TLS 1.0, SSLv3) and ciphers (RC4, DES, 3DES) are reportable findings.",
            "The certificate Subject/SAN often leaks INTERNAL hostnames and the AD domain — prime recon.",
            "Read the whole vuln list, not one line — a single Heartbleed 'vulnerable' is a memory-disclosure win.",
        ],
    },
})


# ── Batch 8: advanced Active Directory — relay, Kerberos, LSASS, dumps ──────
OUTPUT_LESSONS.update({

    "ntlmrelayx": {
        "tool": "impacket-ntlmrelayx",
        "headline": "ntlmrelayx catches an authentication and forwards it to a target. 'SUCCEED' means SMB signing was off and the relayed account had rights. Read whose auth you caught and what it bought you.",
        "sample": (
            "[*] Servers started, waiting for connections\n"
            "[*] SMBD-Thread-4: Received connection from 10.0.0.50\n"
            "[*] Authenticating against smb://10.0.0.15 as CORP/JDOE SUCCEED\n"
            "[*] Target system bootKey: 0x8a1f...\n"
            "[*] Dumping local SAM hashes (uid:rid:lmhash:nthash)\n"
            "Administrator:500:aad3b435b51404eeaad3b435b51404ee:9f4e...b7c1:::\n"
            "[*] Done dumping SAM hashes for host: 10.0.0.15"
        ),
        "reading": [
            {"field": "Received connection from 10.0.0.50",
             "means": "A victim authenticated to YOUR rogue server (you poisoned the request via Responder/coercion/PetitPotam).",
             "do": "That's the captured identity. What it's worth depends on the relay result below."},
            {"field": "Authenticating against smb://10.0.0.15 as CORP/JDOE SUCCEED",
             "means": "You RELAYED JDOE's auth to 10.0.0.15 and it worked — you're now acting AS JDOE on that host.",
             "do": "SUCCEED = SMB signing was OFF on the target. FAILED usually means signing is required (relay blocked)."},
            {"field": "Dumping local SAM hashes",
             "means": "The relayed account had ADMIN on the relay target, so ntlmrelayx dumped its hashes.",
             "do": "A low-priv relay wouldn't get here — you only dump SAM if JDOE was admin on 10.0.0.15."},
            {"field": "(option) -socks / -i",
             "means": "Instead of a one-shot action, keep the authenticated session alive as a SOCKS proxy / interactive.",
             "do": "Use -socks to reuse the relayed session repeatedly (proxychains) rather than firing a single command."},
        ],
        "reference": {
            "title": "What makes a relay land",
            "rows": [
                ("SUCCEED", "target's SMB signing was OFF — relay worked"),
                ("FAILED", "signing required (or account lacks access)"),
                ("SAM dumped", "relayed user was ADMIN on the target"),
                ("-socks", "keep the session as a proxy for reuse"),
                ("source: Responder/PetitPotam", "how the auth was coerced to you"),
            ],
        },
        "work_with_it": (
            "The whole attack hinges on two things the output tells you: was signing off (SUCCEED), and did the "
            "relayed account have rights on the target (SAM dumped = admin). Target signing-disabled hosts (nxc "
            "--gen-relay-list), coerce auth to yourself (Responder/PetitPotam), and use -socks to turn a caught "
            "login into a reusable session rather than a one-shot dump."
        ),
        "misreads": [
            "Relaying needs SMB signing DISABLED on the target — 'SUCCEED' confirms it was; 'FAILED' usually means signing is on.",
            "You only dump SAM if the relayed account is ADMIN on the relay target — a low-priv relay just gets their access.",
            "You cannot relay auth back to the SAME host it came from (that's patched) — relay to a DIFFERENT signing-disabled host.",
        ],
    },

    "rubeus": {
        "tool": "Rubeus",
        "headline": "Rubeus is the Windows Kerberos toolkit — it runs ON a domain host. Read the Action: kerberoast gives crackable hashes, asktgt/overpass gives a .kirbi ticket you inject with Pass-the-Ticket.",
        "sample": (
            "[*] Action: Ask TGT\n"
            "[*] Using rc4_hmac hash: 9f4e1b7c0a2d3e4f5061728394a5b6c7\n"
            "[*] Building AS-REQ for 'dc01.corp.local' ... \n"
            "[+] TGT request successful!\n"
            "[*] base64(ticket.kirbi):\n"
            "      doIFuj...<snip>...AAA=="
        ),
        "reading": [
            {"field": "Action: Ask TGT + Using rc4_hmac hash",
             "means": "You requested a Ticket-Granting Ticket using an NT hash instead of a password — this is Overpass-the-Hash.",
             "do": "You just turned a stolen NT hash into a full Kerberos TGT. No plaintext needed."},
            {"field": "[+] TGT request successful!",
             "means": "The KDC issued you a ticket — the hash was valid.",
             "do": "You now have Kerberos authority as that account. Failure here means the hash/account was wrong."},
            {"field": "base64(ticket.kirbi)",
             "means": "The actual ticket, base64-encoded — a credential you can inject into a logon session.",
             "do": "Inject it with Rubeus ptt /ticket:<b64> (Pass-the-Ticket), then access resources as that user without their password."},
            {"field": "(other actions) kerberoast / monitor / s4u",
             "means": "kerberoast = dump $krb5tgs$ SPN hashes; monitor = harvest TGTs as users log in; s4u = delegation abuse.",
             "do": "kerberoast output feeds hashcat -m 13100; monitor is patient credential harvesting on a busy host."},
        ],
        "reference": {
            "title": "Rubeus actions",
            "rows": [
                ("asktgt /rc4:<hash>", "overpass-the-hash → a TGT from an NT hash"),
                ("kerberoast", "$krb5tgs$ SPN hashes → hashcat -m 13100"),
                ("ptt /ticket:<b64>", "inject a ticket (Pass-the-Ticket)"),
                ("monitor", "harvest new TGTs as users authenticate"),
                ("s4u", "constrained-delegation abuse"),
            ],
        },
        "work_with_it": (
            "Rubeus runs on a Windows foothold (the counterpart to impacket's Kerberos tools). Turn a stolen hash "
            "into a ticket (asktgt /rc4) and inject it (ptt) to move without plaintext; kerberoast for crackable SPN "
            "hashes; or leave monitor running on a busy server to passively collect TGTs of everyone who logs in."
        ),
        "misreads": [
            "Rubeus runs ON Windows (a domain host) — it's the Windows counterpart to impacket's Kerberos tooling.",
            "asktgt /rc4:<hash> is Overpass-the-Hash — it converts an NT hash into a usable Kerberos TGT.",
            "The base64 .kirbi is a ticket to INJECT (ptt) — Pass-the-Ticket, not something to crack.",
        ],
    },

    "lsassy": {
        "tool": "lsassy",
        "headline": "lsassy dumps and parses LSASS on a remote host — extracting the same creds as mimikatz WITHOUT dropping mimikatz.exe on disk. But it needs admin, and reading LSASS still lights up EDR.",
        "sample": (
            "$ nxc smb 10.0.0.15 -u admin -H 9f4e... -M lsassy\n"
            "LSASSY  10.0.0.15  [+] CORP\\jdoe        9f4e1b7c0a2d3e4f5061728394a5b6c7\n"
            "LSASSY  10.0.0.15  [+] CORP\\administrator aabbccddeeff00112233445566778899\n"
            "LSASSY  10.0.0.15  [+] CORP\\svc_sql      Summer2024!  (wdigest)"
        ),
        "reading": [
            {"field": "the -M lsassy invocation via nxc",
             "means": "lsassy usually runs as a NetExec module against hosts you already have admin on.",
             "do": "It sweeps LSASS across many hosts at once — spray it over a subnet where you hold admin creds/hash."},
            {"field": "[+] CORP\\administrator  aabbcc... (a hash)",
             "means": "An NT hash pulled straight from LSASS memory — same material as mimikatz's msv.",
             "do": "Pass-the-Hash with it immediately, or crack it. A domain admin's cached session here is a domain win."},
            {"field": "[+] CORP\\svc_sql  Summer2024! (wdigest)",
             "means": "A CLEARTEXT credential (wdigest present on legacy/misconfigured Windows).",
             "do": "The jackpot — reuse the plaintext everywhere, no cracking."},
            {"field": "(implicit) it needs admin on the target",
             "means": "Reading LSASS requires local admin / SYSTEM on that host.",
             "do": "lsassy is POST-admin harvesting — get admin first (relay, PtH, cracked creds), then sweep for MORE creds."},
        ],
        "reference": {
            "title": "lsassy essentials",
            "rows": [
                ("-M lsassy (via nxc)", "sweep LSASS across many admin'd hosts"),
                ("NTLM hash output", "pass-the-hash or crack"),
                ("wdigest cleartext", "instant reuse, no cracking"),
                ("needs admin/SYSTEM", "post-admin credential harvesting"),
                ("still fires EDR (EID 10)", "stealthier on DISK, not on telemetry"),
            ],
        },
        "work_with_it": (
            "Use lsassy AFTER you have admin somewhere: sweep it (via nxc -M lsassy) across every host you can admin "
            "to snowball credentials — one admin hash often unlocks LSASS on ten machines, and one of those holds a "
            "Domain Admin's cached session. It avoids dropping mimikatz on disk, but LSASS access still triggers "
            "Sysmon EID 10 / EDR, so it's a disk-stealth win, not a telemetry-stealth win."
        ),
        "misreads": [
            "lsassy needs ADMIN on the target to read LSASS — it's post-admin harvesting, not initial access.",
            "Reading LSASS still fires Sysmon EID 10 / EDR regardless of tool — lsassy is stealthier on disk, not telemetry.",
            "It parses the dump remotely, so mimikatz.exe never touches the target's disk — that's the on-disk advantage.",
        ],
    },
})


# ── Batch 8b: AD collection + directory dumps ──────────────────────────────
OUTPUT_LESSONS.update({

    "bloodhound-python": {
        "tool": "bloodhound-python (collector)",
        "headline": "This is the COLLECTOR, not the graph. It authenticates to the DC and pulls AD data into a .zip of JSON. The counts tell you the domain size; the value is the relationships you analyze LATER in the GUI.",
        "sample": (
            "$ bloodhound-python -u jdoe -p Pass123 -d corp.local -ns 10.0.0.10 -c All\n"
            "INFO: Found AD domain: corp.local\n"
            "INFO: Connecting to LDAP server: dc01.corp.local\n"
            "INFO: Found 412 users\n"
            "INFO: Found 88 groups\n"
            "INFO: Found 55 computers\n"
            "INFO: Compressing output into 20240601_bloodhound.zip"
        ),
        "reading": [
            {"field": "the -u/-p/-d/-ns arguments",
             "means": "It's AUTHENTICATED enumeration — valid domain creds, and -ns pointing at the DC's DNS.",
             "do": "You need working creds and DC reachability. -ns is mandatory in isolated labs or collection fails on DNS."},
            {"field": "Found 412 users / 88 groups / 55 computers",
             "means": "The scope of what it pulled — the domain's size.",
             "do": "Context only. The counts don't win anything; the EDGES between these objects do (analyzed next)."},
            {"field": "-c All",
             "means": "Ran all collection methods (sessions, ACLs, group membership, trusts, etc.).",
             "do": "Use -c All for full data. Session/loggedon collection may need admin; ACL data drives the best paths."},
            {"field": "Compressing output into ..._bloodhound.zip",
             "means": "The deliverable — JSON files, NOT a readable report.",
             "do": "This is step ONE. Ingest the .zip into the BloodHound GUI/neo4j, THEN read attack paths (see the bloodhound lesson)."},
        ],
        "reference": {
            "title": "Collect now, analyze later",
            "rows": [
                ("bloodhound-python / SharpHound", "the COLLECTOR — pulls AD data"),
                (".zip of JSON", "the output — ingest into the GUI"),
                ("-c All", "all collection methods (best coverage)"),
                ("-ns <DC IP>", "nameserver — required or DNS fails"),
                ("reading paths", "a separate step in the GUI (bloodhound lesson)"),
            ],
        },
        "work_with_it": (
            "Treat collection and analysis as two distinct steps: bloodhound-python (or SharpHound on Windows) "
            "authenticates and dumps the .zip; you then ingest it into the BloodHound GUI to find and read attack "
            "PATHS. Collect with -c All and valid creds, remember -ns for the DC, and don't expect the console output "
            "to tell you anything but scope — the intelligence lives in the graph you build from the zip."
        ),
        "misreads": [
            "bloodhound-python COLLECTS data — you then ingest the .zip into the GUI to READ paths; two separate steps.",
            "Collection is authenticated — it needs valid domain creds and DC reachability (-ns), not anonymous access.",
            "The object counts are just domain size — the value is the relationships, analyzed later in the graph.",
        ],
    },

    "ldapdomaindump": {
        "tool": "ldapdomaindump",
        "headline": "ldapdomaindump gives you a fast, readable AD inventory — HTML to browse, JSON to parse, grep to filter. It's not a graph like BloodHound; it's the quick 'who/what is in this domain' dump, and the columns leak a lot.",
        "sample": (
            "$ ldapdomaindump -u 'CORP\\jdoe' -p Pass123 10.0.0.10\n"
            "[*] Connecting to host...\n"
            "[*] Dumping domain users...\n"
            "[*] Writing domain_users.html, domain_users.json, domain_users.grep\n"
            "[*] Dumping domain groups...\n"
            "[*] Writing domain_groups.html, ...\n"
            "[*] Dumping domain computers..."
        ),
        "reading": [
            {"field": "domain_users.html (the browsable output)",
             "means": "A sortable table of every user with description, userAccountControl flags, and group memberships.",
             "do": "Open it and read the DESCRIPTION column (hidden passwords) and the UAC column (disabled, no-preauth, pwd-not-required)."},
            {"field": "the three formats (.html / .json / .grep)",
             "means": "Same data, three shapes: HTML to browse, JSON to script, grep for instant filtering.",
             "do": "Use .grep to filter fast: grep 'Domain Admins' domain_groups.grep, or grep the UAC for roastable accounts."},
            {"field": "domain_computers output",
             "means": "Every computer object — OS versions, and often outdated/unsupported OSes.",
             "do": "Spot legacy Windows (2008/7) for known exploits, and servers by name for targeting."},
            {"field": "(implicit) authenticated LDAP",
             "means": "Needs valid domain creds to bind to LDAP.",
             "do": "It's authenticated enum — a fast inventory once you have any domain account."},
        ],
        "reference": {
            "title": "ldapdomaindump vs BloodHound",
            "rows": [
                ("ldapdomaindump", "readable INVENTORY (users/groups/computers)"),
                ("BloodHound", "attack PATHS (relationship graph)"),
                (".html", "browse tables (descriptions, UAC, membership)"),
                (".grep", "instant filtering (DA members, no-preauth)"),
                ("description / UAC columns", "hidden creds + roastable/weak accounts"),
            ],
        },
        "work_with_it": (
            "Use it for a fast readable snapshot of the domain (where BloodHound gives you the attack graph). Open the "
            "HTML and mine the description fields for plaintext creds and the userAccountControl column for roastable "
            "(no-preauth) and weak (pwd-not-required) accounts; use the .grep files to instantly list Domain Admins "
            "members or filter by flag. It's the low-effort inventory step after you get any domain account."
        ),
        "misreads": [
            "ldapdomaindump is an INVENTORY (HTML/JSON/grep), while BloodHound gives attack PATHS — different tools, different jobs.",
            "The HTML description and userAccountControl columns leak hidden creds and roastable/weak accounts — read them.",
            "It's authenticated LDAP — needs valid domain creds, not anonymous access.",
        ],
    },

    "getadusers": {
        "tool": "impacket-GetADUsers",
        "headline": "GetADUsers is a quick authenticated user inventory. The two columns that matter are PasswordLastSet and LastLogon — old + '<never>' together flag stale accounts, which are prime spray and roast targets.",
        "sample": (
            "$ GetADUsers.py -all corp.local/jdoe:Pass123 -dc-ip 10.0.0.10\n"
            "Name            Email             PasswordLastSet      LastLogon\n"
            "-------------   ---------------   -------------------  -------------------\n"
            "Administrator                     2023-05-01 09:00:00  2024-06-01 08:00:00\n"
            "svc_backup      svc@corp.local    2019-02-10 14:00:00  <never>\n"
            "jdoe            jdoe@corp.local   2024-01-15 10:00:00  2024-06-01 07:00:00"
        ),
        "reading": [
            {"field": "the -all + creds invocation",
             "means": "Authenticated enumeration — it needs a valid domain account to list users.",
             "do": "This is post-foothold recon (you have creds). It's a fast inventory, not an anonymous attack."},
            {"field": "PasswordLastSet: 2019-02-10 (svc_backup)",
             "means": "A password set years ago — likely pre-complexity-policy and weak.",
             "do": "Old service-account passwords crack well. Move these up your roast/spray priority."},
            {"field": "LastLogon: <never>",
             "means": "The account has never logged in — a stale, forgotten, or automation account.",
             "do": "Stale accounts are low-risk to attack (nobody notices) and often have weak, unmanaged passwords."},
            {"field": "Email column (username mapping)",
             "means": "Confirms the exact SamAccountName and email format.",
             "do": "Feed the usernames into spraying; the email format aids phishing."},
        ],
        "reference": {
            "title": "The signals to sort on",
            "rows": [
                ("old PasswordLastSet", "likely weak — prioritise for cracking"),
                ("LastLogon <never>", "stale account — quiet, often weak"),
                ("service accounts (svc_*)", "cross-check with GetUserSPNs (roastable)"),
                ("needs valid creds", "authenticated inventory, not anonymous"),
                ("-all", "dump every user (vs a single lookup)"),
            ],
        },
        "work_with_it": (
            "Use it right after getting any domain account to build a target-ranked user list: sort by oldest "
            "PasswordLastSet and '<never>' LastLogon to surface stale, weak accounts nobody watches. Then pivot the "
            "service accounts into GetUserSPNs (Kerberoast) and the pre-auth-disabled ones into GetNPUsers (AS-REP) — "
            "GetADUsers finds the candidates, the roasting tools weaponize them."
        ),
        "misreads": [
            "GetADUsers is authenticated enum — it needs valid domain creds, not anonymous access.",
            "'<never>' LastLogon + old PasswordLastSet flags stale, weak accounts — prime spray/roast targets.",
            "It's an inventory step — pair it with GetUserSPNs/GetNPUsers to actually find the roastable accounts.",
        ],
    },
})
