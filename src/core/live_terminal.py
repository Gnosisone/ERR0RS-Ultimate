#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Live Terminal Engine v3.1
WebSocket-based streaming terminal with inline education injection.

Architecture:
  - WebSocket /ws/terminal — bidirectional live shell stream
  - Spawns tools as PTY subprocesses (real interactive terminal)
  - Streams stdout line-by-line to browser in real time
  - Forwards stdin FROM browser TO running process (interactive!)
  - Inline education: parses output and injects [ERR0RS] teaching cards
  - Intent parser: "run nmap on X and teach me" → execute + teach mode
  - OperatorTerminal: persistent desktop xterm — ERR0RS types every tool
    call into it live so operator can see and interact at any time

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os, sys, re, json, time, asyncio, threading, subprocess, shlex, pty, select
from pathlib import Path

# ── Language Expansion Layer ──────────────────────────────────────────────
try:
    from src.core.language_layer import (
        TOOL_PATTERNS as _LL_TOOL_PATTERNS,
        TEACH_TRIGGERS as _LL_TEACH_TRIGGERS,
    )
    # Merge in expanded vocab (LL entries override defaults)
    _LANG_LOADED = True
except ImportError:
    _LANG_LOADED = False

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR  = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path: sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR)  not in sys.path: sys.path.insert(0, str(SRC_DIR))

# ── INTENT PARSER ────────────────────────────────────────────────────────────
# Understands natural language like:
#   "run nmap on 192.168.1.1"
#   "scan 10.0.0.1 and teach me what the results mean"
#   "use sqlmap against http://target.com --teach"
#   "teach me how nmap works then run it on 192.168.1.0/24"

# Use expanded language layer if available, fall back to originals
if _LANG_LOADED:
    TOOL_PATTERNS  = _LL_TOOL_PATTERNS
    TEACH_TRIGGERS = _LL_TEACH_TRIGGERS
else:
    TOOL_PATTERNS = {
        "nmap":        r"nmap|port scan|scan ports|network scan|host discovery",
        "sqlmap":      r"sqlmap|sql injection|sqli|sql inject",
        "nikto":       r"nikto|web scan|web server scan",
        "gobuster":    r"gobuster|dir bust|directory bust|dirb|fuzz dir|enumerate dir",
        "hydra":       r"hydra|brute force|bruteforce|credential attack|password attack",
        "metasploit":  r"metasploit|msfconsole|msf|exploit",
        "hashcat":     r"hashcat|crack hash|hash crack|password crack",
        "nuclei":      r"nuclei|vuln scan|vulnerability scan",
        "subfinder":   r"subfinder|subdomain|subdomain enum",
        "aircrack":    r"aircrack|wifi|wpa2|wireless attack|handshake",
        "wpscan":      r"wpscan|wordpress scan|wp scan",
        "enum4linux":  r"enum4linux|smb enum|samba enum",
        "ffuf":        r"ffuf|fuzz|fuzzing|web fuzz",
        "wfuzz":       r"wfuzz",
        "crackmapexec":r"crackmapexec|cme|smb spray",
    }
    TEACH_TRIGGERS = [
        "teach me", "teach", "and teach", "explain", "what does",
        "what does it mean", "help me understand", "why", "how does",
        "what is", "show me", "--teach", "-t", "and explain",
        "walk me through", "break it down", "i want to learn",
        "educate me", "what are",
    ]

TARGET_PATTERN = re.compile(
    r'(?:on|against|target|scan|at|for)\s+'
    r'((?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?'   # IPv4 / CIDR
    r'|(?:https?://)?[\w\-]+(?:\.[\w\-]+)+(?:/\S*)?'  # hostname / URL
    r')',
    re.IGNORECASE
)

def parse_intent(raw: str) -> dict:
    """
    Parse natural language into structured intent.
    Returns:
      {
        tool: str | None,
        target: str | None,
        raw_cmd: str | None,   # if user typed a direct command
        execute: bool,
        teach: bool,
        teach_topic: str | None,
        mode: 'execute' | 'teach' | 'both' | 'interactive'
      }
    """
    text = raw.strip()
    lower = text.lower()

    # Detect teach intent
    wants_teach = any(t in lower for t in TEACH_TRIGGERS)

    # Detect direct shell passthrough
    if text.startswith('$') or text.startswith('!'):
        return {
            "tool": None, "target": None,
            "raw_cmd": text[1:].strip(),
            "execute": True, "teach": wants_teach,
            "teach_topic": None,
            "mode": "interactive"   # raw shell = always interactive
        }

    # Detect tool
    detected_tool = None
    for tool, pattern in TOOL_PATTERNS.items():
        if re.search(pattern, lower):
            detected_tool = tool
            break

    # Detect target
    target_match = TARGET_PATTERN.search(text)
    detected_target = target_match.group(1) if target_match else None

    # Determine mode
    if detected_tool and wants_teach:
        mode = "both"
    elif detected_tool:
        mode = "execute"
    elif wants_teach:
        mode = "teach"
    else:
        mode = "execute"  # fallback

    return {
        "tool":        detected_tool,
        "target":      detected_target,
        "raw_cmd":     None,
        "execute":     bool(detected_tool or text.startswith('$')),
        "teach":       wants_teach,
        "teach_topic": detected_tool or None,
        "mode":        mode,
    }


# ── COMMAND BUILDER ──────────────────────────────────────────────────────────
# Builds sensible default commands for each tool given a target

def build_command(tool: str, target: str) -> str:
    """Build a real command string for a tool + target."""
    t = target or "TARGET"
    commands = {
        "nmap":         f"nmap -sV -sC --top-ports 1000 {t}",
        "sqlmap":       f"sqlmap -u '{t}' --batch --dbs --level=1 --risk=1",
        "nikto":        f"nikto -h {t}",
        "gobuster":     f"gobuster dir -u http://{t} -w /usr/share/wordlists/dirb/common.txt -t 20",
        "hydra":        f"hydra -l admin -P /usr/share/wordlists/rockyou.txt {t} ssh -t 4",
        "metasploit":   f"msfconsole -q",
        "hashcat":      f"hashcat -m 0 -a 0 {t} /usr/share/wordlists/rockyou.txt",
        "nuclei":       f"nuclei -u http://{t} -s critical,high,medium",
        "subfinder":    f"subfinder -d {t} -silent",
        "aircrack":     f"aircrack-ng {t}",
        "wpscan":       f"wpscan --url http://{t} --enumerate p,u",
        "enum4linux":   f"enum4linux -a {t}",
        "ffuf":         f"ffuf -u http://{t}/FUZZ -w /usr/share/wordlists/dirb/common.txt",
        "wfuzz":        f"wfuzz -w /usr/share/wordlists/dirb/common.txt --hc 404 http://{t}/FUZZ",
        "crackmapexec": f"crackmapexec smb {t}",
    }
    return commands.get(tool, f"{tool} {t}")


# ── INLINE EDUCATION — output line annotator ─────────────────────────────────
# Parses tool output in real time and injects teaching notes

NMAP_PATTERNS = [
    (r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)",   "PORT_OPEN"),
    (r"(\d+)/tcp\s+closed",                "PORT_CLOSED"),
    (r"(\d+)/tcp\s+filtered",              "PORT_FILTERED"),
    (r"OS details:\s*(.*)",                "OS_DETECTED"),
    (r"CVE-\d{4}-\d+",                     "CVE_FOUND"),
    (r"VULNERABLE",                         "VULN_FOUND"),
]

PORT_LESSONS = {
    "21":   ("FTP — File Transfer Protocol",       "Often misconfigured with anonymous login. Try: ftp {target} then 'anonymous' as user."),
    "22":   ("SSH — Secure Shell",                  "Brute force target! Try: hydra -l root -P rockyou.txt {target} ssh"),
    "23":   ("Telnet — CLEARTEXT remote access",    "Everything sent in plaintext including passwords. Capture with Wireshark."),
    "25":   ("SMTP — Mail server",                  "User enumeration possible. Try: smtp-user-enum -M VRFY -U users.txt -t {target}"),
    "53":   ("DNS — Domain Name System",            "Try zone transfer: dig axfr @{target} domain.com — often dumps all hostnames."),
    "80":   ("HTTP — Web server",                   "Run nikto + gobuster immediately. Look for admin panels, login forms, CMS."),
    "88":   ("Kerberos — Active Directory",         "AD environment! Kerberoasting possible. Try: GetUserSPNs.py domain/user:pass@{target}"),
    "110":  ("POP3 — Email retrieval",              "Try default creds. May expose email content if not encrypted."),
    "135":  ("RPC/MSRPC — Windows RPC",             "Windows host. Try: rpcclient -U '' {target} for null session enum."),
    "139":  ("NetBIOS — Windows file sharing",      "SMB! Try: smbclient -L //{target} -N and enum4linux -a {target}"),
    "143":  ("IMAP — Email protocol",               "Like POP3 but more powerful. Try default creds. Banner grabs reveal software version."),
    "389":  ("LDAP — Active Directory directory",   "AD enumeration goldmine. Try: ldapsearch -x -h {target} -b 'dc=domain,dc=com'"),
    "443":  ("HTTPS — Encrypted web server",        "Same as port 80 — run nikto -h https://{target} -ssl and gobuster with -k flag."),
    "445":  ("SMB — Windows file sharing",          "CRITICAL. Check MS17-010 (EternalBlue): nmap --script smb-vuln-ms17-010 {target}"),
    "1433": ("MSSQL — Microsoft SQL Server",        "Try: sqsh -S {target} -U sa or sqlmap. Default creds: sa/sa, sa/password."),
    "1521": ("Oracle DB",                           "Try: odat.py all -s {target}. Default SID: ORCL, XE."),
    "3306": ("MySQL — Database server",             "Try: mysql -h {target} -u root -p. Check for empty root password!"),
    "3389": ("RDP — Remote Desktop",               "Brute force: hydra -l administrator -P rockyou.txt rdp://{target} BlueKeep: nmap --script rdp-vuln-ms12-020"),
    "5432": ("PostgreSQL — Database",               "Try: psql -h {target} -U postgres. Check for trust authentication."),
    "5900": ("VNC — Remote desktop",                "Try: vncviewer {target} with no password or common passwords."),
    "6379": ("Redis — In-memory database",          "Often no auth! Try: redis-cli -h {target} KEYS '*' — may expose sensitive data."),
    "8080": ("HTTP-Alt — Secondary web port",       "Same attack surface as 80. Often dev/staging server with less hardening."),
    "8443": ("HTTPS-Alt — Secondary HTTPS",         "Same as 443. Often hosts admin interfaces or API endpoints."),
    "27017":("MongoDB — NoSQL database",            "Check for no-auth access: mongo {target}:27017 — very common misconfiguration!"),
}

def annotate_line(line: str, tool: str, target: str = "") -> list:
    """
    Given a line of tool output, return a list of output events:
    [
      {"type": "output",  "data": original_line},
      {"type": "teach",   "data": annotation},   # optional
    ]
    """
    events = [{"type": "output", "data": line}]

    if tool == "nmap":
        # Port open annotation
        m = re.search(r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", line)
        if m:
            port, service, version = m.group(1), m.group(2), m.group(3).strip()
            lesson = PORT_LESSONS.get(port)
            if lesson:
                title, tip = lesson
                tip = tip.replace("{target}", target or "TARGET")
                events.append({"type": "teach", "data":
                    f"[ERR0RS] Port {port} = {title}\n"
                    f"         {tip}"
                })
            elif version:
                events.append({"type": "teach", "data":
                    f"[ERR0RS] {service} {version} — Research this version for known CVEs: searchsploit {service}"
                })

        # CVE found
        cves = re.findall(r"CVE-\d{4}-\d+", line)
        for cve in cves:
            events.append({"type": "teach", "data":
                f"[ERR0RS] {cve} detected! Look this up: https://nvd.nist.gov/vuln/detail/{cve}\n"
                f"         Check if Metasploit has an exploit: search {cve}"
            })

        # VULNERABLE
        if "VULNERABLE" in line.upper():
            events.append({"type": "teach", "data":
                "[ERR0RS] VULNERABILITY CONFIRMED! Document this finding:\n"
                "         1. Screenshot the output  2. Note the CVE  "
                "3. Check exploit availability  4. Add to report"
            })

        # OS detected
        m = re.search(r"OS details:\s*(.*)", line)
        if m:
            events.append({"type": "teach", "data":
                f"[ERR0RS] OS fingerprinted: {m.group(1)}\n"
                f"         This helps narrow exploit selection. Search Metasploit: "
                f"search platform:{'windows' if 'windows' in m.group(1).lower() else 'linux'}"
            })

    elif tool == "sqlmap":
        if "is vulnerable" in line.lower() or "injection" in line.lower() and "found" in line.lower():
            events.append({"type": "teach", "data":
                "[ERR0RS] SQL INJECTION CONFIRMED!\n"
                "         The database will execute your SQL. Next steps:\n"
                "         --dbs (list databases) → -D dbname --tables → --dump\n"
                "         Potential OS shell: --os-shell (if high privileges)"
            })
        if "available databases" in line.lower():
            events.append({"type": "teach", "data":
                "[ERR0RS] Databases listed! Choose a target:\n"
                "         -D <database_name> --tables   to see tables inside\n"
                "         Look for: users, accounts, customers, admin, wp_users"
            })
        if "password" in line.lower() and "hash" in line.lower():
            events.append({"type": "teach", "data":
                "[ERR0RS] Password hash found! Copy it and crack with:\n"
                "         hashcat -m 0 -a 0 hash.txt rockyou.txt  (MD5)\n"
                "         hashcat -m 3200 hash.txt rockyou.txt    (bcrypt)\n"
                "         Use hash-identifier to find the hash type first"
            })

    elif tool == "gobuster":
        m = re.search(r"(\/[\w\-/\.]+)\s+\(Status:\s*(\d+)\)", line)
        if m:
            path, status = m.group(1), m.group(2)
            if status == "200":
                events.append({"type": "teach", "data":
                    f"[ERR0RS] Found: {path} (200 OK) — This page exists and is accessible!\n"
                    f"         Visit it in browser. Look for: login forms, admin panels, version info."
                })
            elif status == "301" or status == "302":
                events.append({"type": "teach", "data":
                    f"[ERR0RS] Found: {path} (Redirect) — Follow the redirect, may lead somewhere interesting."
                })
            elif status == "403":
                events.append({"type": "teach", "data":
                    f"[ERR0RS] Found: {path} (403 Forbidden) — EXISTS but access denied.\n"
                    f"         Try bypass techniques: add trailing slash, change case, use X-Forwarded-For header."
                })

    elif tool == "hydra":
        if "login:" in line.lower() and "password:" in line.lower():
            events.append({"type": "teach", "data":
                "[ERR0RS] CREDENTIAL FOUND! This is valid login!\n"
                "         Document immediately. Try these creds on:\n"
                "         - All other services on this host\n"
                "         - Other hosts on the network (password reuse)\n"
                "         - Web application, VPN, email"
            })

    elif tool == "nikto":
        if "osvdb" in line.lower() or "+" in line:
            events.append({"type": "teach", "data":
                "[ERR0RS] Nikto finding! Each '+' line is a potential vulnerability.\n"
                "         Research the OSVDB/CVE number. Cross-reference with Metasploit."
            })

    return events


# ═══════════════════════════════════════════════════════════════════════════════
# OPERATOR TERMINAL — persistent desktop xterm that ERR0RS types into
# ═══════════════════════════════════════════════════════════════════════════════

class OperatorTerminal:
    """
    One persistent xterm lives on the desktop for the entire ERR0RS session.
    Every time ERR0RS fires a tool, it types the command into this terminal
    via xdotool so the operator can see exactly what's running and jump in.

    Lifecycle:
        ot = OperatorTerminal.instance()   # singleton
        ot.send_command("nmap -sV 10.0.0.1", tool="nmap")

    The terminal is a real interactive bash shell — operator can type freely
    between ERR0RS tool calls.
    """

    _singleton = None
    _lock      = threading.Lock()

    # Window title — used by xdotool to find the window reliably
    WINDOW_TITLE = "ERR0RS Operator Terminal"

    # ERR0RS green-on-black colour scheme
    XTERM_ARGS = [
        "xterm",
        "-T",  WINDOW_TITLE,
        "-fa", "Monospace",
        "-fs", "10",               # Smaller font for Pi display
        "-bg", "#0a0a0a",
        "-fg", "#00ff41",
        "-cr", "#00ff41",          # cursor colour
        "-geometry", "120x32",     # default — overridden by dynamic probe
        "-sl", "10000",            # scrollback lines
        "-b",  "4",                # inner border
    ]

    @staticmethod
    def _dynamic_geometry():
        """Probe screen size via xdotool/xrandr and pick a geometry that fits.
        Returns (cols, rows, font_size) — or defaults if probing fails."""
        try:
            import subprocess
            r = subprocess.run(["xdotool", "getdisplaygeometry"],
                               capture_output=True, text=True, timeout=2,
                               env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")})
            if r.returncode == 0 and r.stdout.strip():
                w, h = map(int, r.stdout.strip().split())
                # Rough: 1 char ≈ 6px wide × 13px tall at font-size 10
                # Leave 10% margin
                cols = max(80, min(160, int(w * 0.85 / 6)))
                rows = max(24, min(42, int(h * 0.75 / 13)))
                # Pick font size based on resolution
                if w < 1024:   fs = 9
                elif w < 1600: fs = 10
                else:          fs = 11
                return cols, rows, fs
        except Exception:
            pass
        # Fallback for unknown/headless
        return 120, 32, 10

    def __init__(self):
        self._proc   = None   # Popen for the xterm process
        self._wid    = None   # X window ID (found via xdotool)
        self._ready  = False

    # ── Singleton accessor ────────────────────────────────────────────────────
    @classmethod
    def instance(cls) -> "OperatorTerminal":
        with cls._lock:
            if cls._singleton is None:
                cls._singleton = cls()
            return cls._singleton

    # ── Spawn the persistent terminal ─────────────────────────────────────────
    def spawn(self) -> bool:
        """
        Launch the operator xterm if it isn't already running.
        Returns True if the terminal is (now) available.
        """
        import shutil

        if not shutil.which("xterm"):
            print("[OperatorTerminal] xterm not found — install with: apt install xterm")
            return False
        if not shutil.which("xdotool"):
            print("[OperatorTerminal] xdotool not found — install with: apt install xdotool")
            return False

        # Kill previous orphan with same title (safe no-op if none)
        subprocess.run(
            ["xdotool", "search", "--name", self.WINDOW_TITLE, "windowkill"],
            capture_output=True
        )
        time.sleep(0.3)

        # Build the shell that runs inside xterm — it stays open as a bash REPL
        init_script = (
            "export PS1='\\n\\033[1;31m[ERR0RS]\\033[0m \\033[0;33m\\w\\033[0m $ ';"
            "export TERM=xterm-256color;"
            "clear;"
            "echo ''"
            "echo -e '\\033[0;31m  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗\\033[0m';"
            "echo -e '\\033[0;31m  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝\\033[0m';"
            "echo -e '\\033[0;36m        OPERATOR TERMINAL — ERR0RS will type tool calls here\\033[0m';"
            "echo -e '\\033[0;36m        You can interact freely between calls.\\033[0m';"
            "echo '';"
            "exec bash --norc --noprofile"
        )

        env = {**os.environ, "TERM": "xterm-256color", "DISPLAY": os.environ.get("DISPLAY", ":0")}

        # Build dynamic geometry-aware args
        cols, rows, fs = self._dynamic_geometry()
        xterm_args = [a for a in self.XTERM_ARGS]  # copy
        # Override geometry & font-size from defaults
        for i, a in enumerate(xterm_args):
            if a == "-geometry" and i + 1 < len(xterm_args):
                xterm_args[i + 1] = f"{cols}x{rows}"
            elif a == "-fs" and i + 1 < len(xterm_args):
                xterm_args[i + 1] = str(fs)
        print(f"[OperatorTerminal] Geometry: {cols}×{rows} @ {fs}pt")

        self._proc = subprocess.Popen(
            xterm_args + ["-e", "bash", "-c", init_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )

        # Give xterm time to appear, then grab its window ID
        for _ in range(20):
            time.sleep(0.3)
            result = subprocess.run(
                ["xdotool", "search", "--name", self.WINDOW_TITLE],
                capture_output=True, text=True
            )
            wids = result.stdout.strip().splitlines()
            if wids:
                self._wid   = wids[-1].strip()
                self._ready = True
                print(f"[OperatorTerminal] ✅ Spawned — WID {self._wid}")
                return True

        print("[OperatorTerminal] ⚠️  Window didn't appear within timeout")
        return False

    def is_alive(self) -> bool:
        """Check xterm process is still running."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def ensure_alive(self):
        """Re-spawn the terminal if the operator closed it."""
        if not self.is_alive():
            print("[OperatorTerminal] Window was closed — re-spawning...")
            self._ready = False
            self._wid   = None
            self.spawn()

    # ── Type a command into the terminal ──────────────────────────────────────
    def send_command(self, command: str, tool: str = "", announce: bool = True):
        """
        Focus the operator terminal and type `command` into it using xdotool.
        ERR0RS types a short announcement line first so it's obvious this is
        an AI-driven call, then the actual command, then hits Enter.

        The operator can immediately start typing to interact with the tool.
        """
        self.ensure_alive()
        if not self._ready or not self._wid:
            return

        tool_label = tool.upper() if tool else "TOOL"
        announce_line = (
            f"echo -e '\\n\\033[1;33m[ERR0RS] ▶ Calling {tool_label}\\033[0m'; "
        )

        try:
            # ── Pre-clear any held keys before grabbing focus ──────────────────
            # If the user clicked a UI button that triggered this call, the
            # browser may still be releasing keys when xdotool starts typing.
            # Explicitly release common stuck-key culprits before focus shift
            # so we don't end up with output like "hhhhhhhhhydra ...".
            # The space prefix on the typed command also absorbs any residual
            # stuck-key into a harmless leading space the shell ignores.
            for stuck_key in ("h", "shift", "ctrl", "alt", "super"):
                subprocess.run(["xdotool", "keyup", stuck_key],
                               capture_output=True, timeout=1)

            # Raise & focus the window
            subprocess.run(["xdotool", "windowraise",  self._wid], capture_output=True)
            subprocess.run(["xdotool", "windowfocus", "--sync", self._wid], capture_output=True)
            time.sleep(0.30)   # longer settle so X server fully processes focus shift

            # Type the announce line then the real command. Leading space on
            # the actual command absorbs any residual stuck-key as a harmless
            # leading whitespace (the shell trims it).
            for i, text in enumerate(([announce_line] if announce else []) + [command]):
                # Only prefix the real command, not the announce line which
                # already starts with echo.
                if i == (1 if announce else 0) and not text.startswith(" "):
                    text = " " + text
                subprocess.run(
                    ["xdotool", "type", "--window", self._wid,
                     "--clearmodifiers", "--delay", "25", text],
                    capture_output=True
                )
            # Press Enter to execute
            subprocess.run(
                ["xdotool", "key", "--window", self._wid, "Return"],
                capture_output=True
            )
        except Exception as e:
            print(f"[OperatorTerminal] xdotool error: {e}")

    # ── Print a plain status/info line (no Enter) ─────────────────────────────
    def print_status(self, message: str):
        """Echo an informational message into the operator terminal."""
        self.send_command(f"echo -e '\\033[0;36m[ERR0RS] {message}\\033[0m'",
                          announce=False)


# ── Module-level helper — always returns the singleton ────────────────────────
def get_operator_terminal() -> OperatorTerminal:
    return OperatorTerminal.instance()


# ── Auto-spawn on import (background thread so import is non-blocking) ────────
def _boot_operator_terminal():
    """Called once at module import time — spawns the persistent terminal."""
    ot = OperatorTerminal.instance()
    if not ot.is_alive():
        ot.spawn()

_ot_boot_thread = threading.Thread(target=_boot_operator_terminal, daemon=True, name="operator-terminal-boot")
_ot_boot_thread.start()


# ── LIVE PROCESS RUNNER ──────────────────────────────────────────────────────
# Runs a process with PTY for real interactive terminal behavior

class LiveProcess:
    """
    Spawns a process with a PTY so it behaves like a real terminal.
    Streams output to a callback. Accepts stdin input.
    """

    def __init__(self, command: str, tool: str = "", target: str = "",
                 output_callback=None, teach_mode: bool = False):
        self.command         = command
        self.tool            = tool
        self.target          = target
        self.output_callback = output_callback or (lambda e: None)
        self.teach_mode      = teach_mode
        self.pid             = None
        self.fd              = None
        self._thread         = None
        self._running        = False
        self._stdin_queue    = []
        self._stdout_buffer  = []   # rolling buffer for auto-coach analysis

    # ── Terminal emulator preference order (Kali/Pi friendly) ────────────────
    _TERM_EMULATORS = [
        # (binary, [arg_to_run_command, ...])  — {title} and {cmd} filled in below
        ("kitty",            ["kitty", "--title", "{title}", "--", "bash", "-c", "{cmd}"]),
        ("xterm",            ["xterm", "-T", "{title}", "-fa", "Monospace", "-fs", "11",
                               "-bg", "black", "-fg", "#00ff41",
                               "-e", "bash", "-c", "{cmd}"]),
        ("lxterminal",       ["lxterminal", "--title={title}", "-e", "bash -c '{cmd}'"]),
        ("xfce4-terminal",   ["xfce4-terminal", "--title={title}", "-x", "bash", "-c", "{cmd}"]),
        ("gnome-terminal",   ["gnome-terminal", "--title={title}", "--",
                               "bash", "-c", "{cmd}"]),
        ("mate-terminal",    ["mate-terminal", "--title={title}", "-x", "bash", "-c", "{cmd}"]),
        ("konsole",          ["konsole", "--title", "{title}", "-e", "bash", "-c", "{cmd}"]),
        ("tilix",            ["tilix", "--title={title}", "-e", "bash -c '{cmd}'"]),
    ]

    def _find_terminal(self):
        """Return (binary, argv_template) for the first available terminal emulator."""
        import shutil
        for binary, argv in self._TERM_EMULATORS:
            if shutil.which(binary):
                return binary, argv
        return None, None

    def _spawn_popup_terminal(self):
        """
        Open a new, dedicated terminal window for this tool.
        The window title shows the tool name; the command runs inside it.
        A 'Press ENTER to close' hold is appended so the window stays open
        after the tool finishes, letting you read the output.
        Output is ALSO still streamed back to the browser UI via the PTY.
        """
        binary, argv_template = self._find_terminal()
        if not binary:
            self.output_callback({"type": "system",
                "data": "[ERR0RS] No terminal emulator found (install xterm or kitty)"})
            return

        tool_label = self.tool.upper() if self.tool else "TOOL"
        title      = f"ERR0RS ⟫ {tool_label}"

        # Wrap command so window stays open with a pause at the end
        hold_cmd = (
            f"{self.command} ; "
            f"echo '' ; "
            f"echo '─────────────────────────────────────────────────' ; "
            f"echo '[ERR0RS] {tool_label} finished. Press ENTER to close.' ; "
            f"read _ignored"
        )

        # Build final argv, substituting {title} and {cmd}
        argv = []
        for part in argv_template:
            part = part.replace("{title}", title).replace("{cmd}", hold_cmd)
            argv.append(part)

        try:
            subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,   # detach — won't die when ERR0RS restarts
                env={**os.environ, "TERM": "xterm-256color"},
            )
            self.output_callback({"type": "system",
                "data": f"[ERR0RS] 🖥️  Popup terminal opened: {title}"})
        except Exception as e:
            self.output_callback({"type": "system",
                "data": f"[ERR0RS] Popup terminal launch failed: {e}"})

    def start(self):
        """Spawn process with PTY (streams to UI) AND drives the operator terminal."""
        # ── 1. Type command into the persistent operator terminal ─────────────
        try:
            ot = OperatorTerminal.instance()
            ot.send_command(self.command, tool=self.tool)
        except Exception as _ote:
            pass   # never crash ERR0RS because of terminal issues

        # ── 2. Open a dedicated popup terminal for this tool ─────────────────
        self._spawn_popup_terminal()

        # ── 3. Also stream output back to the browser UI via PTY ─────────────
        try:
            self.pid, self.fd = pty.fork()
        except Exception as e:
            self.output_callback({"type": "error", "data": f"PTY fork failed: {e}"})
            return False

        if self.pid == 0:
            # Child process
            os.execvp("/bin/bash", ["/bin/bash", "-c", self.command])
            os._exit(1)
        else:
            # Parent process
            self._running = True
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()
            self.output_callback({"type": "system",
                "data": f"[ERR0RS] Spawned: {self.command} (PID {self.pid})"})
            if self.teach_mode:
                self._emit_pre_teach()
            return True

    def _emit_pre_teach(self):
        """Emit teaching content BEFORE the tool runs"""
        try:
            from src.education.teach_engine import handle_teach_request
            result = handle_teach_request(self.tool)
            if result["status"] == "success":
                self.output_callback({"type": "teach_block",
                    "data": result["stdout"]})
        except Exception:
            pass

    def _read_loop(self):
        """Read output from PTY and stream to callback"""
        buffer = b""
        while self._running:
            try:
                r, _, _ = select.select([self.fd], [], [], 0.1)
                if r:
                    try:
                        data = os.read(self.fd, 4096)
                        if not data:
                            break
                        buffer += data
                        # Process complete lines
                        while b"\n" in buffer:
                            line, buffer = buffer.split(b"\n", 1)
                            decoded = line.decode("utf-8", errors="replace").rstrip()
                            if decoded:
                                self._process_line(decoded)
                    except OSError:
                        break
            except Exception:
                break

        self._running = False
        self.output_callback({"type": "system", "data": "[ERR0RS] Process complete."})

        # ── Auto Coach: analyze output and explain findings ───────────────────
        if self.tool and self._stdout_buffer:
            try:
                from src.core.auto_coach import coach_output
                coach_output(
                    tool        = self.tool,
                    stdout      = "\n".join(self._stdout_buffer[-500:]),
                    target      = self.target,
                    broadcast_fn= self.output_callback,
                )
            except Exception:
                pass

    def _process_line(self, line: str):
        """Process a line and emit output + optional inline education"""
        # Buffer for auto-coach analysis (keep last 500 lines)
        self._stdout_buffer.append(line)
        if len(self._stdout_buffer) > 500:
            self._stdout_buffer = self._stdout_buffer[-500:]

        if self.teach_mode:
            events = annotate_line(line, self.tool, self.target)
        else:
            events = [{"type": "output", "data": line}]

        for event in events:
            self.output_callback(event)

    def send_input(self, text: str):
        """Send keystrokes to the running process"""
        if self.fd and self._running:
            try:
                os.write(self.fd, (text + "\n").encode())
            except OSError:
                pass

    def send_raw(self, data: bytes):
        """Send raw bytes (for Ctrl+C etc)"""
        if self.fd and self._running:
            try:
                os.write(self.fd, data)
            except OSError:
                pass

    def terminate(self):
        """Kill the process"""
        self._running = False
        if self.pid:
            try:
                import signal
                os.kill(self.pid, signal.SIGTERM)
            except Exception:
                pass

    @property
    def is_running(self):
        return self._running
