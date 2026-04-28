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
    """

    def __init__(self):
        self._lock       = threading.Lock()
        self._ws_clients : List[Callable] = []   # async send callbacks
        self._terminal_fd: Optional[int]  = None
        self._log_file   = LOG_FILE
        self._step       = 0

        # Open log file
        try:
            self._log = open(self._log_file, "a", buffering=1)
        except Exception:
            self._log = None

    # ── Register WebSocket client ─────────────────────────────────────────
    def register_ws(self, send_fn: Callable):
        with self._lock:
            if send_fn not in self._ws_clients:
                self._ws_clients.append(send_fn)

    def unregister_ws(self, send_fn: Callable):
        with self._lock:
            self._ws_clients = [f for f in self._ws_clients if f != send_fn]

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
        for send_fn in list(self._ws_clients):
            try:
                # Try calling synchronously (for threaded WS) or schedule
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.run_coroutine_threadsafe(send_fn(ws_payload), loop)
                    else:
                        loop.run_until_complete(send_fn(ws_payload))
                except RuntimeError:
                    pass
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
