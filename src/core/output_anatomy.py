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
