#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           ERR0RS ULTIMATE — LIVE NARRATOR ENGINE                ║
║                  src/core/narrator.py                           ║
║                                                                  ║
║  Real-time operator feed: explains every action as it happens.  ║
║  Broadcasts to:                                                  ║
║    1. Spawned terminal (zsh/bash) via ANSI color output         ║
║    2. WebSocket clients (browser UI)                            ║
║    3. Log file /tmp/err0rs_live.log                             ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, json, threading, subprocess, shutil
from datetime import datetime
from typing import Optional, Callable, List

# ── ANSI color codes ──────────────────────────────────────────────────────────
R  = "\033[0m"          # reset
OR = "\033[38;5;208m"   # orange  — ERR0RS actions
CY = "\033[38;5;51m"    # cyan    — recon / scanning
GR = "\033[38;5;82m"    # green   — success / found
RD = "\033[38;5;196m"   # red     — exploitation / warning
YL = "\033[38;5;226m"   # yellow  — teaching / explanation
MA = "\033[38;5;135m"   # magenta — post-exploit
DM = "\033[38;5;240m"   # dim     — metadata / timestamps
BL = "\033[1m"          # bold
UL = "\033[4m"          # underline

LOG_FILE = "/tmp/err0rs_live.log"

# ── Phase color map ───────────────────────────────────────────────────────────
PHASE_COLORS = {
    "recon":       CY,
    "scanning":    CY,
    "exploitation":RD,
    "post_exploit":MA,
    "reporting":   GR,
    "teaching":    YL,
    "system":      OR,
    "success":     GR,
    "warning":     YL,
    "error":       RD,
}

# ── Action narration library ──────────────────────────────────────────────────
# Maps tool/action → human explanation of WHAT it does + WHY
NARRATIONS = {
    # RECON
    "whatweb": {
        "start":  "Fingerprinting the target web stack — identifying server, framework, CMS, and technology versions without sending any malicious traffic.",
        "why":    "WHY: Knowing the tech stack tells us which known CVEs to look for and what exploitation paths exist.",
        "phase":  "recon",
    },
    "nmap": {
        "start":  "Port scanning the target — sending TCP/UDP probes to discover open services, versions, and OS fingerprints.",
        "why":    "WHY: Every open port is a potential attack surface. nmap maps the target's exposure.",
        "phase":  "recon",
    },
    "nikto": {
        "start":  "Web vulnerability scanning — checking for dangerous files, outdated software, misconfigurations, and missing security headers.",
        "why":    "WHY: Nikto finds low-hanging fruit fast — unprotected admin pages, default credentials, exposed config files.",
        "phase":  "scanning",
    },
    "gobuster": {
        "start":  "Directory + file enumeration — brute-forcing URL paths to discover hidden endpoints the target isn't advertising.",
        "why":    "WHY: Web apps often have /admin, /backup, /api/v1 paths that aren't linked but are accessible.",
        "phase":  "scanning",
    },
    "sqlmap": {
        "start":  "SQL injection testing — probing parameters with payloads to detect and exploit database injection vulnerabilities.",
        "why":    "WHY: SQLi is the #1 web vulnerability. A single injectable parameter can expose the entire database.",
        "phase":  "exploitation",
    },
    "dalfox": {
        "start":  "XSS parameter fuzzing — injecting script payloads into every parameter to find reflected, stored, and DOM-based XSS.",
        "why":    "WHY: XSS lets attackers steal session cookies, hijack accounts, and pivot to stored attacks.",
        "phase":  "exploitation",
    },
    "hydra": {
        "start":  "Credential brute-forcing — systematically testing username/password combinations against the target service.",
        "why":    "WHY: Weak or default credentials are still the #1 entry point. Hydra automates the testing.",
        "phase":  "exploitation",
    },
    "hashcat": {
        "start":  "Hash cracking — running dictionary and rule-based attacks against captured password hashes.",
        "why":    "WHY: Cracked hashes reveal plaintext passwords that may be reused elsewhere.",
        "phase":  "exploitation",
    },
    "subfinder": {
        "start":  "Passive subdomain enumeration — querying public sources to map all subdomains without touching the target.",
        "why":    "WHY: Subdomains often run older, less-hardened apps. Each one is another attack vector.",
        "phase":  "recon",
    },
    "nuclei": {
        "start":  "Template-based vulnerability scanning — running thousands of fingerprint templates to detect known CVEs and misconfigurations.",
        "why":    "WHY: Nuclei has templates for every major OWASP category — fast, accurate, and community-maintained.",
        "phase":  "scanning",
    },
    # JUICE SHOP specific actions
    "sql_injection": {
        "start":  "Injecting SQL into the product search parameter — attempting to break out of the query context.",
        "why":    "WHY: The /rest/products/search?q= parameter concatenates user input directly into a SQL query — a textbook injection point.",
        "phase":  "exploitation",
    },
    "union_inject": {
        "start":  "Executing UNION-based injection — appending a second SELECT to the original query to read arbitrary table data.",
        "why":    "WHY: UNION injection lets us read any table in the database — Users, Passwords, everything.",
        "phase":  "exploitation",
    },
    "hash_crack": {
        "start":  "Cracking MD5 password hash — testing against common password dictionaries.",
        "why":    "WHY: Juice Shop stores passwords as unsalted MD5 — one of the weakest possible hash algorithms. Trivially reversible.",
        "phase":  "exploitation",
    },
    "jwt_decode": {
        "start":  "Decoding JWT token — base64 decoding the payload to inspect claims without needing the secret.",
        "why":    "WHY: JWTs are just base64 encoded. Any client can read the payload — sensitive data should never be in a JWT.",
        "phase":  "recon",
    },
    "ftp_access": {
        "start":  "Accessing the exposed /ftp/ directory — checking for publicly downloadable sensitive files.",
        "why":    "WHY: Web-accessible FTP directories are a critical misconfiguration — often contain backups and credentials.",
        "phase":  "exploitation",
    },
    "null_byte": {
        "start":  "Injecting null byte (%2500) to bypass file extension filter — tricking the server into serving blocked file types.",
        "why":    "WHY: The filter blocks .bak files by extension, but the null byte terminates the string early in the backend parser.",
        "phase":  "exploitation",
    },
    "xss_stored": {
        "start":  "Injecting XSS payload into username field — attempting to store a script that executes in admin browsers.",
        "why":    "WHY: Stored XSS is more dangerous than reflected — it fires automatically whenever the payload is rendered.",
        "phase":  "exploitation",
    },
    "password_reset": {
        "start":  "Attempting password reset using OSINT-derived security answer — extracted from photo EXIF metadata.",
        "why":    "WHY: Security questions are weak authentication. GPS coordinates in uploaded photos reveal answers.",
        "phase":  "exploitation",
    },
    "captcha_solve": {
        "start":  "Solving math captcha — the answer is returned in the same API response that issues the captcha.",
        "why":    "WHY: This is a broken captcha implementation — the answer is handed to the client, making it trivially bypassable.",
        "phase":  "exploitation",
    },
    "idor": {
        "start":  "Testing IDOR (Insecure Direct Object Reference) — accessing another user's resource by changing the ID.",
        "why":    "WHY: No authorization check on /rest/basket/:id means any authenticated user can read any basket.",
        "phase":  "exploitation",
    },
    "admin_login": {
        "start":  "Logging in with cracked admin credentials to obtain a privileged JWT token.",
        "why":    "WHY: With an admin JWT, all protected admin API routes are accessible — user management, feedback deletion, etc.",
        "phase":  "exploitation",
    },
    "exif_extract": {
        "start":  "Extracting EXIF metadata from uploaded photo — looking for GPS coordinates, timestamps, and device info.",
        "why":    "WHY: Most phones embed GPS coordinates in photos automatically. Users don't know their location is embedded.",
        "phase":  "recon",
    },
    "feedback_submit": {
        "start":  "Submitting feedback via POST /api/Feedbacks with a captcha bypass.",
        "why":    "WHY: The feedback form accepts rating=0 which is below the UI minimum — server-side validation is missing.",
        "phase":  "exploitation",
    },
}

# Partial match patterns for dynamic narration
PATTERNS = [
    (["sqlmap", "sql"],         "sql_injection"),
    (["union", "UNION"],        "union_inject"),
    (["md5", "hash", "crack"],  "hash_crack"),
    (["jwt", "token", "base64"],"jwt_decode"),
    (["ftp", "/ftp/"],          "ftp_access"),
    (["2500", "null byte"],     "null_byte"),
    (["xss", "iframe", "alert"],"xss_stored"),
    (["reset-password", "security-question"], "password_reset"),
    (["captcha", "captchaId"],  "captcha_solve"),
    (["basket", "idor"],        "idor"),
    (["admin", "login"],        "admin_login"),
    (["exif", "gps", "GPS"],    "exif_extract"),
    (["Feedbacks", "rating"],   "feedback_submit"),
]

# ── Narrator singleton ────────────────────────────────────────────────────────
class Narrator:
    """
    Single narrator instance shared across all ERR0RS modules.
    Call narrator.tell() from anywhere to broadcast a live narration.

    WebSocket broadcast model (Bug 1 fix, 2026-05-23):
      Each registered WS client is stored as (send_coroutine_fn, asyncio_loop).
      tell() schedules each send via run_coroutine_threadsafe(send_fn(payload), loop)
      which works from ANY thread — sync or async. Previous implementation
      used asyncio.get_event_loop() inside tell(), which creates a fresh
      idle loop in worker threads and silently fails on the await.
    """

    def __init__(self):
        self._lock       = threading.Lock()
        # Each entry: (send_fn, loop) — loop captured at registration time
        # so we can schedule the coroutine from any thread that calls tell().
        self._ws_clients : List[tuple] = []
        self._terminal_fd: Optional[int]  = None
        self._log_file   = LOG_FILE
        self._step       = 0

        # Open log file
        try:
            self._log = open(self._log_file, "a", buffering=1)
        except Exception:
            self._log = None

    # ── Register WebSocket client ─────────────────────────────────────────
    def register_ws(self, send_fn: Callable, loop=None):
        """Register an async websocket send function and the loop that owns it.

        If loop is None, we attempt to capture the currently-running loop.
        This MUST be called from within the WS handler's async context so the
        captured loop is the one that can actually drive the send coroutine.
        """
        if loop is None:
            try:
                import asyncio as _asyncio
                loop = _asyncio.get_event_loop()
            except Exception:
                loop = None
        with self._lock:
            # De-dup on send_fn so re-registration from the same handler doesn't
            # accumulate duplicate broadcasts.
            self._ws_clients = [(f, l) for (f, l) in self._ws_clients if f != send_fn]
            self._ws_clients.append((send_fn, loop))

    def unregister_ws(self, send_fn: Callable):
        with self._lock:
            self._ws_clients = [(f, l) for (f, l) in self._ws_clients if f != send_fn]

    # ── Core broadcast ────────────────────────────────────────────────────
    def tell(self,
             message:  str,
             phase:    str  = "system",
             tool:     str  = "",
             detail:   str  = "",
             finding:  str  = "",
             teach:    str  = ""):
        """
        Broadcast a narration event to all outputs.

        phase:   recon | scanning | exploitation | post_exploit | success | warning | error | system
        tool:    tool name if relevant
        detail:  extra technical detail
        finding: what was found (green highlight)
        teach:   educational explanation
        """
        self._step += 1
        ts    = datetime.now().strftime("%H:%M:%S")
        color = PHASE_COLORS.get(phase, OR)
        phase_tag = phase.upper().replace("_", "-")

        # ── Terminal output (ANSI colored) ────────────────────────────────
        lines = []
        lines.append(f"\n{DM}{'─'*70}{R}")
        lines.append(
            f"{DM}[{ts}]{R} {color}{BL}[ERR0RS:{phase_tag}]{R}"
            + (f" {OR}{BL}{tool.upper()}{R}" if tool else "")
        )
        lines.append(f"  {BL}{message}{R}")

        if detail:
            lines.append(f"  {DM}▸ {detail}{R}")
        if finding:
            lines.append(f"  {GR}{BL}✅ FOUND: {finding}{R}")
        if teach:
            lines.append(f"  {YL}📘 {teach}{R}")

        terminal_out = "\n".join(lines) + "\n"

        # Print to stderr (always visible in terminal)
        print(terminal_out, file=sys.stderr, end="", flush=True)

        # Write to log
        if self._log:
            try:
                plain = self._strip_ansi(terminal_out)
                self._log.write(plain)
                self._log.flush()
            except Exception:
                pass

        # ── WebSocket broadcast ───────────────────────────────────────────
        ws_payload = json.dumps({
            "type":    "narrate",
            "phase":   phase,
            "tool":    tool,
            "message": message,
            "detail":  detail,
            "finding": finding,
            "teach":   teach,
            "ts":      ts,
            "step":    self._step,
        })

        dead = []
        # Snapshot the clients list under lock so we don't iterate while
        # register_ws/unregister_ws could mutate it.
        with self._lock:
            clients_snapshot = list(self._ws_clients)

        import asyncio as _asyncio
        for send_fn, loop in clients_snapshot:
            try:
                if loop is not None and loop.is_running():
                    # Schedule the coroutine on the WS handler's loop from
                    # whatever thread we're currently on. Fire-and-forget —
                    # we don't wait on .result() because the broadcast call
                    # site can't afford to block on a slow client.
                    _asyncio.run_coroutine_threadsafe(send_fn(ws_payload), loop)
                else:
                    # No loop or loop not running — client is dead, mark
                    # for removal. We don't try the old run_until_complete
                    # fallback because it was the source of the bug.
                    dead.append(send_fn)
            except Exception:
                dead.append(send_fn)

        for d in dead:
            self.unregister_ws(d)

    # ── Convenience wrappers ──────────────────────────────────────────────
    def recon(self, msg, tool="", detail="", finding="", teach=""):
        self.tell(msg, "recon", tool, detail, finding, teach)

    def scan(self, msg, tool="", detail="", finding="", teach=""):
        self.tell(msg, "scanning", tool, detail, finding, teach)

    def exploit(self, msg, tool="", detail="", finding="", teach=""):
        self.tell(msg, "exploitation", tool, detail, finding, teach)

    def success(self, msg, tool="", detail="", finding="", teach=""):
        self.tell(msg, "success", tool, detail, finding, teach)

    def warn(self, msg, detail="", teach=""):
        self.tell(msg, "warning", detail=detail, teach=teach)

    def err(self, msg, detail=""):
        self.tell(msg, "error", detail=detail)

    def teach(self, msg, tool=""):
        self.tell(msg, "teaching", tool=tool)

    # ── Auto-narrate from tool name / action string ───────────────────────
    def auto(self, action: str, context: str = ""):
        """Look up narration for a tool or action and broadcast it."""
        key = action.lower().strip()

        # Direct match
        if key in NARRATIONS:
            n = NARRATIONS[key]
            self.tell(
                n["start"],
                phase  = n["phase"],
                tool   = action,
                teach  = n.get("why", ""),
            )
            return

        # Pattern match
        for patterns, narr_key in PATTERNS:
            if any(p.lower() in key or p.lower() in context.lower() for p in patterns):
                if narr_key in NARRATIONS:
                    n = NARRATIONS[narr_key]
                    self.tell(
                        n["start"],
                        phase  = n["phase"],
                        tool   = action,
                        detail = context[:80] if context else "",
                        teach  = n.get("why", ""),
                    )
                    return

        # Generic fallback
        self.tell(f"Executing: {action}", phase="system",
                  detail=context[:80] if context else "")

    @staticmethod
    def _strip_ansi(text: str) -> str:
        import re
        return re.sub(r'\033\[[0-9;]*m', '', text)


# ── Global singleton ──────────────────────────────────────────────────────────
narrator = Narrator()


# ── Convenience top-level functions ──────────────────────────────────────────
# ── 5-SLOT STEP NARRATION (opt-in, per tool) ──────────────────────────────────
# Richer than NARRATIONS{start,why}: the full do/why_now/watch_for/means/blue
# schema, rendered through teach_engine.format_step() so a LIVE executed step
# and a TAUGHT lesson step read identically. step_narration() returns "" for
# tools without an entry, so the agent loop degrades gracefully.
STEP_DETAILS = {
    "whatweb": {
        "cmd": "whatweb <target> -a 3",
        "do": "Fingerprint the web stack — server, framework, CMS, language, versions — from headers and page markers.",
        "why_now": "Before attacking a web app you map what it's built on; the stack dictates which CVEs and exploit paths are even relevant.",
        "watch_for": "Server/framework/CMS names and versions. Outdated versions and known-vulnerable CMS plugins are immediate leads.",
        "means": "The tech profile tells the next steps where to aim — which nuclei templates, which exploits, which manual tests.",
        "blue": "Lightly noisy (a few HTTP requests). Hardening: strip Server / X-Powered-By headers so you leak less of this.",
    },
    "nuclei": {
        "cmd": "nuclei -u <target> -t http/ -severity critical,high,medium",
        "do": "Run thousands of community templates against the target to detect known CVEs and misconfigurations.",
        "why_now": "Once the stack is known, nuclei confirms specific known issues fast and accurately before slower manual work.",
        "watch_for": "[critical]/[high] template matches with CVE IDs — each is a confirmed, citable finding.",
        "means": "Matched templates are confirmed vulns to weaponize or report; they often point straight at a public exploit.",
        "blue": "Signature-detectable — WAFs/IDS see the template request patterns. Patch the matched CVEs; that's the whole point.",
    },
    "hydra": {
        "cmd": "hydra -l <user> -P <wordlist> <service>://<target>",
        "do": "Brute-force or password-spray a login service (SSH, FTP, HTTP) with a username/password list.",
        "why_now": "Run it against any exposed auth service — weak, default, or reused credentials remain the #1 way in.",
        "watch_for": "A green 'login: ... password: ...' line means valid creds. Watch for lockouts; -f stops on the first hit.",
        "means": "Valid credentials give authenticated access — usually the pivot from outsider to insider.",
        "blue": "Very loud — bursts of failed logins in auth logs. Defenders alert on this; lockout policy + MFA + fail2ban kill it.",
    },
    "ffuf": {
        "cmd": "ffuf -u <target>/FUZZ -w <wordlist> -mc 200,301,302,403",
        "do": "Fast web fuzzing — brute-force paths or parameters and filter by response code to find hidden content.",
        "why_now": "Like gobuster but faster; you map the unadvertised attack surface once a web app is confirmed live.",
        "watch_for": "Hits on interesting names (admin, api, backup, .git). Tune matchers/filters to cut the noise.",
        "means": "Discovered endpoints or params open new logins, APIs, or files to test in the next step.",
        "blue": "Loud — heavy 404 volume from one IP. Rate-limit, alert on high 404s, and don't leave sensitive paths reachable.",
    },
    "enum4linux": {
        "cmd": "enum4linux -a <target>",
        "do": "Enumerate a Windows/Samba host over SMB — shares, users, groups, password policy, OS info.",
        "why_now": "When 139/445 are open, this harvests the low-effort intel that shapes credential and lateral-movement attacks.",
        "watch_for": "User lists, readable shares, and a weak password policy — all feed the next (credential) phase.",
        "means": "User names + share access + policy are the inputs for password spraying and lateral movement.",
        "blue": "Detectable SMB session/enumeration. Restrict null/guest sessions, segment SMB, alert on mass enumeration.",
    },
    "crackmapexec": {
        "cmd": "crackmapexec smb <target> --shares --users",
        "do": "Sweep SMB across hosts to test credentials and list shares/users, flagging where creds are valid.",
        "why_now": "After you hold a credential (or want to map SMB exposure), CME shows fast where it works and what's reachable.",
        "watch_for": "[+] valid creds vs [-], 'Pwn3d!' (admin), and readable/writable shares across the subnet.",
        "means": "A valid cred plus admin on a host is the lateral-movement and credential-dumping springboard.",
        "blue": "Noisy auth + SMB activity across hosts. Detect via logon-failure correlation; defend with LAPS, segmentation, MFA.",
    },
    "nmap_vuln": {
        "cmd": "nmap --script vuln -p <ports> <target>",
        "do": "Run nmap's NSE 'vuln' scripts against open ports to flag known, version-specific vulnerabilities.",
        "why_now": "After ports and versions are known, this maps which services carry public CVEs worth chasing.",
        "watch_for": "Script output naming CVE IDs and 'VULNERABLE' states — direct leads to an exploit.",
        "means": "Each flagged CVE is a candidate exploit path; confirm with searchsploit/nuclei before firing.",
        "blue": "Loud and script-heavy — IDS sees the probes. Patch the named CVEs; that closes the doors these scripts find.",
    },
    "nmap_smb": {
        "cmd": "nmap --script smb-vuln-* -p 139,445 <target>",
        "do": "Probe SMB with NSE scripts for known vulns (e.g. MS17-010), security mode, and shares.",
        "why_now": "When SMB ports are open, check for high-impact wormable bugs and misconfig before manual enumeration.",
        "watch_for": "'VULNERABLE: ... ms17-010' or guest/anonymous share access — both are serious, immediate findings.",
        "means": "An SMB RCE bug or an open share is often the fastest route to a foothold on a Windows network.",
        "blue": "Patch MS17-010-class bugs, disable SMBv1, require signing, segment. IDS detects the smb-vuln probes.",
    },
    "nmap": {
        "cmd": "nmap -sV -sC <target>",
        "do": "Send TCP/UDP probes to map open ports, service versions, and default-script results.",
        "why_now": "You cannot attack a service you have not found. Every open port is a door; this inventories them before you pick one.",
        "watch_for": "Open ports and their version banners. Odd high ports and outdated versions are your best leads.",
        "means": "The open-port + version list defines the entire attack surface the next steps work from.",
        "blue": "Noisy and logged — IDS/firewalls see the sweep. Defenders rate-limit, drop, or alert on it; -T2 / -sS shrink the footprint.",
    },
    "nikto": {
        "cmd": "nikto -h <target>",
        "do": "Sweep a web server for dangerous files, outdated software, misconfigurations, and missing security headers.",
        "why_now": "Once a web port is confirmed open, nikto grabs the fast, well-known wins before slower manual testing.",
        "watch_for": "CVE/OSVDB hits, exposed /admin or config files, default creds, missing headers (CSP, HSTS).",
        "means": "Each hit is a candidate vuln to confirm — it feeds sqlmap, manual testing, or an exploit search.",
        "blue": "Very loud — signature-heavy requests trip WAFs and fill logs. Defenders alert on the nikto user-agent and request pattern.",
    },
    "gobuster": {
        "cmd": "gobuster dir -u <target> -w <wordlist>",
        "do": "Brute-force URL paths to discover directories and files the site never links to.",
        "why_now": "Apps expose /admin, /backup, /api that are not advertised; you enumerate them once a web app is confirmed live.",
        "watch_for": "200/301/403 on interesting names (admin, backup, .git, api). A 403 still proves the path exists.",
        "means": "Discovered endpoints widen the attack surface — new logins, APIs, or leaked files to test next.",
        "blue": "Loud — hundreds of 404s from one IP in the access log. Defenders rate-limit and alert on high 404 volume.",
    },
    "sqlmap": {
        "cmd": "sqlmap -u '<url>?id=1' --batch",
        "do": "Probe a parameter with crafted payloads to detect and then exploit SQL injection automatically.",
        "why_now": "Run it against any parameter that reaches a database query — the highest-impact web flaw to confirm.",
        "watch_for": "'parameter is injectable' plus the DBMS type. From there it can enumerate DBs, tables, and dump data.",
        "means": "Confirmed SQLi can expose the whole database — credentials, PII — and sometimes RCE through the DB.",
        "blue": "Loud — anomalous/malformed queries hit WAFs and DB error logs. Parameterized queries + WAF rules block it.",
    },
    "airmon-ng": {
        "cmd": "airmon-ng start wlan0",
        "do": "Put the WiFi card into monitor mode (wlan0 -> wlan0mon).",
        "why_now": "Managed mode only hears traffic addressed to you; you cannot study the airspace until the card hears every frame.",
        "watch_for": "Interface renamed to wlan0mon. If it warns about interfering processes, run 'airmon-ng check kill' first.",
        "means": "The card can now see frames from every AP and client in range.",
        "blue": "Purely passive — nothing on the wire to detect. Recon leaves no trace, which is why defense cannot rely on catching it.",
    },
    "airodump-ng": {
        "cmd": "airodump-ng -c CH --bssid BSSID -w cap wlan0mon",
        "do": "Survey the air, then park on the target's channel and record its frames to disk.",
        "why_now": "You need the AP's BSSID, channel, and a connected client first — and you must be recording before the handshake happens.",
        "watch_for": "Target BSSID + CH with a STATION beneath it; then 'WPA handshake: <BSSID>' top-right once captured.",
        "means": "Any handshake that occurs lands on disk with the nonces and MIC needed to crack offline.",
        "blue": "Channel-locked listening is still passive and hard to detect. The loud step is the deauth that comes next.",
    },
    "aireplay-ng": {
        "cmd": "aireplay-ng --deauth 3 -a BSSID -c CLIENT wlan0mon",
        "do": "Send a few forged 'deauthenticate' frames so the client drops and immediately reconnects.",
        "why_now": "Forcing a fast reconnect beats waiting. It WORKS because WPA2 management frames are unauthenticated — the client cannot tell your deauth from the AP's.",
        "watch_for": "The STATION drops then reappears, and the capture flips to 'WPA handshake'. Send the minimum (3) — a flood denies service.",
        "means": "The forced reconnect re-runs the 4-way handshake, which the recorder just captured.",
        "blue": "THE LOUD STEP. A WIDS sees a deauth flood; 802.11w / PMF makes forged frames get dropped, defeating it. This is where WPA3 wins.",
    },
    "aircrack-ng": {
        "cmd": "aircrack-ng -w /usr/share/wordlists/rockyou.txt cap-01.cap",
        "do": "For each candidate password: derive the keys, compute the MIC, and compare it to the captured MIC.",
        "why_now": "You have everything except the password, and this needs zero contact with the target — fully offline.",
        "watch_for": "'KEY FOUND!' on success, or the list exhausts. For GPU speed, convert to mode 22000 and use hashcat.",
        "means": "A hit hands you the PSK. No hit means the password was not in your list — you have proven it was strong.",
        "blue": "Undetectable (offline). Defense is upstream: passphrase entropy and WPA3-SAE, which make offline guessing infeasible.",
    },
}


def step_narration(tool: str) -> str:
    """Return the rendered 5-slot step block (do/why_now/watch_for/means/blue)
    for a tool, via the shared teach_engine formatter, or '' if none is defined.
    Instant + static — safe to call synchronously in the agent's hot loop."""
    key = (tool or "").lower().strip()
    detail = (STEP_DETAILS.get(key)
              or STEP_DETAILS.get(key.replace("_", "-"))
              or STEP_DETAILS.get(key.split("_")[0]))   # family: nmap_quick -> nmap
    if not detail:
        return ""
    try:
        from .teach_engine import format_step
    except Exception:
        try:
            from src.core.teach_engine import format_step
        except Exception:
            return ""
    return format_step(detail)


def tell(msg, phase="system", tool="", detail="", finding="", teach=""):
    narrator.tell(msg, phase, tool, detail, finding, teach)

def narrate_tool(tool: str, target: str = ""):
    """Called right before a tool fires — gives full pre-execution narration."""
    narrator.auto(tool, target)

def narrate_finding(what: str, where: str = "", why: str = ""):
    """Called when a significant finding is made."""
    narrator.success(
        f"Finding confirmed: {what}",
        finding = f"{what}" + (f" at {where}" if where else ""),
        teach   = why,
    )

def narrate_phase(phase: str, target: str = ""):
    """Announce a new kill chain phase."""
    phase_intros = {
        "recon":        f"Starting reconnaissance against {target or 'target'} — passive and active information gathering.",
        "scanning":     f"Moving to scanning phase — mapping vulnerabilities and endpoints on {target or 'target'}.",
        "exploitation": f"Exploitation phase — attempting to leverage identified vulnerabilities on {target or 'target'}.",
        "post_exploit": f"Post-exploitation — maintaining access and expanding footprint on {target or 'target'}.",
        "reporting":    "Generating professional pentest report — documenting all findings with severity ratings.",
    }
    msg = phase_intros.get(phase, f"Phase: {phase}")
    narrator.tell(
        msg,
        phase   = phase,
        teach   = "Purple Team: each offensive action is paired with defensive countermeasures in the final report.",
    )
