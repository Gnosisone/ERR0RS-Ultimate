# ERR0RS ULTIMATE — Deep Function Reference
### Every Function, Every Module, Every Line Explained
**Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone**
**Framework Version: 3.0 | Document Version: 1.0**

---

> This document explains EVERY function in ERR0RS Ultimate in plain English.
> Not just what it does — but WHY it exists, HOW it works internally,
> what data goes IN, what comes OUT, and what breaks if you touch it wrong.

---

# TABLE OF CONTENTS

1. [errorz_launcher.py — The Brain / Server](#1-errorz_launcherpy)
2. [live_terminal.py — The Live Shell Engine](#2-live_terminalpy)
3. [tool_executor.py — The Tool Runner](#3-tool_executorpy)
4. [teach_engine.py — The Offline Knowledge Base](#4-teach_enginepy)
5. [natural_language.py — The NLP Interface](#5-natural_languagepy)
6. [orchestrator.py — The Autonomous Agent](#6-orchestratorpy)
7. [cve_intelligence.py — The CVE Hunter](#7-cve_intelligencepy)
8. [browser_automation.py — The Web Crawler](#8-browser_automationpy)
9. [exploit_generator.py — The Exploit Planner](#9-exploit_generatorpy)

---

# 1. errorz_launcher.py
**File:** `src/ui/errorz_launcher.py`
**Role:** The main server — boots everything, handles all HTTP endpoints,
manages the WebSocket live terminal, and is the first thing that runs.

---

## `run_shell(cmd, timeout)`

```
INPUT:  cmd     = a shell command string like "nmap -sV 192.168.1.1"
        timeout = max seconds before killing it (default 60)
OUTPUT: dict with keys: stdout, stderr, returncode, command, status
```

**What it does in plain English:**
Runs any shell command synchronously (blocking). Waits for it to finish,
captures everything it printed, and returns it as a clean dictionary.
It uses Python's `subprocess.run` with `shell=True` so you can pass
full bash strings including pipes and redirects.

**Why it exists:**
Not every command needs live streaming. Quick commands like `whoami`,
`uname`, `ip addr` can just run and return. This is the simple version
for commands that finish fast.

**The three outcomes:**
- `status: "success"` → returncode was 0, command worked
- `status: "error"` → returncode was non-zero, something failed
- `status: "timeout"` → took longer than timeout seconds, was killed

**What can break it:**
- Passing unsanitized user input — shell=True is dangerous with untrusted input
- Very long-running commands with a short timeout — they get killed mid-run
- Commands that need interactive TTY (like msfconsole) — use LiveProcess instead

---

## `run_tool_async(tool, target, params)`

```
INPUT:  tool   = tool name string like "nmap"
        target = IP or domain like "192.168.1.1"
        params = dict of options like {"timing": "4", "ports": "1-65535"}
OUTPUT: dict with keys: tool, command, status, stdout, stderr, returncode,
                        duration_ms, findings, error
```

**What it does in plain English:**
Bridges the sync HTTP world to the async ToolExecutor. Since HTTP handlers
can't use async/await directly, this function spins up a brand new event
loop, runs the async `ToolExecutor.run()` inside it, gets the result,
closes the loop, and returns everything as a plain dict.

**Why it exists:**
Python's asyncio doesn't let you just call `await` from a regular function.
The HTTP server runs in a thread, not an async context. This wrapper is
the translation layer between those two worlds.

**The flow:**
```
HTTP handler (sync thread)
  → run_tool_async()
    → creates new event loop
      → runs ToolExecutor.run() (async)
        → builds command string
        → spawns subprocess
        → streams stdout/stderr
        → parses findings
      → returns ToolResult
    → converts to plain dict
  → returns to HTTP handler
→ HTTP sends JSON response to browser
```

**What can break it:**
- Calling from inside an existing event loop (asyncio doesn't allow nested loops)
- If ToolExecutor isn't loaded (FRAMEWORK_LOADED = False) — returns error dict
- The finally block always closes the loop, even on crash — no memory leaks

---

## `query_ollama(prompt)`

```
INPUT:  prompt = a plain English question or command
OUTPUT: dict with keys: stdout (the AI response), status, source
```

**What it does in plain English:**
Sends a prompt to the local Ollama server running on port 11434.
It automatically prepends "You are ERR0RS, an AI penetration testing assistant"
to every prompt so responses stay in character. Uses Python's built-in
`urllib.request` — no external HTTP library needed.

**Why it exists:**
This is the LOCAL AI brain. No OpenAI, no cloud, no data leaving the machine.
When the user asks something that no other handler knows the answer to,
this gets called as the final fallback. If Ollama is offline, it returns
a helpful offline message listing all the built-in teach commands.

**The model used:** `llama3.2` (hardcoded — change this if you use a different model)

**The offline fallback message lists:**
teach me sqlmap, teach me nmap, teach me gobuster, teach me hydra,
teach me metasploit, teach me hashcat, teach me nikto, teach me nuclei,
teach me privesc, teach me xss, teach me burp suite, teach me wireshark

**What can break it:**
- Ollama not running → returns offline message (graceful, not crash)
- Wrong model name → Ollama returns a 404 → caught by exception handler
- Timeout set to 30 seconds — complex questions may get cut off

---

## `route_command(cmd)`

```
INPUT:  cmd = raw string from user (could be anything)
OUTPUT: dict with stdout/stderr/status — whatever the matched handler returns
```

**What it does in plain English:**
This is the ROUTING BRAIN for the HTTP API. Every command typed in the
UI that goes through HTTP (not WebSocket) passes through here. It reads
the command, figures out what the user wants, and forwards to the right handler.

**The routing order (waterfall — first match wins):**

**Step 1 — Teach/Learn triggers:**
If the command contains phrases like "teach me", "explain", "what is",
"how does", "walk me through", etc., it calls `handle_teach_request()`.
This catches: "teach me sqlmap", "explain nmap flags", "what is XSS"

**Step 2 — Bare tool names:**
If the user types just "sqlmap" or just "nmap" with nothing else,
it treats that as a teach request and explains the tool.

**Step 3 — Tool + Target execution:**
Checks if the first word maps to a known tool (nmap, nikto, gobuster, etc.)
and if a target is provided as the second word.
"nmap 192.168.1.1" → runs nmap against 192.168.1.1

**Step 4 — System info:**
Commands containing "status", "sysinfo", "uname", "whoami" run
`uname -a && whoami && ip addr show` and return system information.

**Step 5 — Report generation:**
"generate report", "debrief" → runs demo_report.py

**Step 6 — MCP / Ollama status:**
"mcp", "kali tools" → checks MCP server
"ollama", "models", "ai status" → runs `ollama list`

**Step 7 — Raw shell passthrough:**
Commands starting with `$` or `!` are passed directly to bash.
`$ whoami` → runs whoami. `! cat /etc/passwd` → runs that.

**Step 8 — RocketGod RF tools:**
Detects HackRF, Flipper, jamming, rolling code, SubGHz keywords
and routes to the RocketGod module.

**Step 9 — BadUSB/DuckyScript:**
Detects flipper, badusb, ducky, reverse shell keywords
and routes to the BadUSB generator.

**Step 10 — Teach engine second pass:**
Tries `find_lesson()` one more time on whatever wasn't matched above.

**Step 11 — Ollama fallback:**
If NOTHING matched, sends to Ollama for AI response.

---

## `ws_terminal_handler(websocket)`

```
INPUT:  websocket = the connected WebSocket client object
OUTPUT: async generator — streams JSON events to browser forever until disconnect
```

**What it does in plain English:**
This is the LIVE TERMINAL ENGINE. When the browser connects on ws://127.0.0.1:8766,
this function handles the entire session. It listens for messages, interprets them,
runs tools as real PTY processes, and streams every line of output back to the browser
in real time — just like a real terminal window.

**The message protocol — what the browser sends:**

| Message Type | What It Does |
|---|---|
| `{"type":"run","command":"nmap 192.168.1.1"}` | Run that command |
| `{"type":"run","command":"...","teach":true}` | Run with inline education mode |
| `{"type":"stdin","data":"yes\n"}` | Type into the running process |
| `{"type":"key","data":"\x03"}` | Send Ctrl+C to kill the process |
| `{"type":"kill"}` | Force-kill the current process |

**What the server sends back:**

| Event Type | When |
|---|---|
| `{"type":"system","data":"..."}` | Status messages, ERR0RS announcements |
| `{"type":"output","data":"..."}` | Raw tool output lines |
| `{"type":"teach","data":"..."}` | Inline teaching annotations |
| `{"type":"teach_block","data":"..."}` | Full lesson before tool runs |
| `{"type":"error","data":"..."}` | Error messages |
| `{"type":"done","data":"..."}` | Process finished |

**The decision flow for a "run" message:**
```
1. Strip --teach flag from command, remember if it was there
2. Kill any currently running process
3. Call parse_intent() to understand what was typed
4. If mode == "teach" only → emit lesson, don't run
5. If tool detected with target → build_command() → run as LiveProcess
6. If tool detected WITHOUT target → emit lesson, ask for target
7. If not a tool command → route_command() → emit output
8. If teach mode is on → emit full lesson BEFORE running the tool
9. Spawn LiveProcess with PTY
10. LiveProcess streams output back via on_output callback
```

**The on_output callback (threading trick):**
LiveProcess runs in a background thread. WebSocket sends require being
in the async event loop. The callback creates a new event loop just to
send the message, then immediately closes it. Not the prettiest, but it
works reliably cross-platform.

---

## `start_ws_server()`

```
INPUT:  none
OUTPUT: none — starts a daemon thread running the WebSocket server
```

Starts the WebSocket server on `ws://127.0.0.1:8766` in a background daemon thread.
Uses `websockets.serve()` which runs an `asyncio.Future()` forever.
The thread is marked `daemon=True` so it dies automatically when the main process exits.
If `websockets` library isn't installed, prints an error and returns without crashing.

---

## `ERR0RSHandler` class (HTTP Request Handler)

The HTTP server class. Inherits from `SimpleHTTPRequestHandler` so it
automatically serves static files (index.html, CSS, JS) from the `web/` directory.
Every API endpoint is handled manually in `do_GET` and `do_POST`.

### `end_headers()`
Adds CORS headers to every response so the browser UI can call the API
from any origin. Required because the browser loads the page on port 8765
and makes API calls also to 8765 — same origin, but some browsers still check.

### `do_OPTIONS()`
Handles browser preflight CORS requests. Always returns 200. Without this,
some browsers would reject API calls.

### `do_GET()` — All GET endpoints

| Endpoint | What It Returns |
|---|---|
| `/api/status` | Full system status: framework, Ollama, MCP, live terminal, uptime, platform |
| `/api/phases` | The 6 pentest phases and their current status (done/active/pending) |
| `/api/tools` | List of 16 tools and whether each binary is installed on this system |
| `/api/ws_info` | WebSocket URL, whether websockets library is available |
| `/api/payload_studio/snippets` | DuckyScript snippet library |
| anything else | Served as static file from the `web/` directory |

### `do_POST()` — All POST endpoints

| Endpoint | Input | What It Does |
|---|---|---|
| `/api/command` | `{"command":"..."}` | Routes through route_command() |
| `/api/tool` | `{"tool":"nmap","target":"x.x.x.x","params":{}}` | Runs specific tool via ToolExecutor |
| `/api/shell` | `{"cmd":"whoami","timeout":60}` | Raw shell execution |
| `/api/teach` | `{"query":"explain nmap"}` | Returns offline lesson |
| `/api/ollama` | `{"prompt":"..."}` | Sends to local Ollama AI |
| `/api/soc` | `{"action":"failed-logins"}` | Runs SOC blue team commands |
| `/api/rocketgod` | `{"action":"hackrf"}` | RF/HackRF tools |
| `/api/badusb` | `{"action":"..."}` | Flipper BadUSB/DuckyScript |
| `/api/payload_studio/explain` | `{"line":"STRING hello"}` | Explains a DuckyScript line |
| `/api/payload_studio/suggest` | `{"code":"...","platform":"windows"}` | Next-line suggestions |
| `/api/payload_studio/validate` | `{"code":"..."}` | Validates DuckyScript syntax |

### `/api/soc` — The 11 SOC Blue Team Commands

| Action | Shell Command Run |
|---|---|
| `failed-logins` | grep 'Failed password' /var/log/auth.log OR journalctl for SSH failures |
| `active-conns` | ss -tulpn + netstat ESTABLISHED connections |
| `open-ports` | ss -tulpn LISTEN only |
| `running-procs` | ps aux sorted by CPU, top 30 |
| `log-tail` | Last 50 lines of auth.log + syslog OR journalctl |
| `who-online` | who + last + w commands |
| `sudo-log` | grep sudo from auth.log OR journalctl |
| `firewall-rules` | iptables -L OR ufw status |
| `cron-jobs` | crontab -l + /etc/cron* listing |
| `dns-cache` | resolvectl statistics + /etc/hosts |
| `volatility` | volatility3 --info (memory forensics framework) |

---

## `_validate_ducky(code)`

```
INPUT:  code = multi-line string of DuckyScript
OUTPUT: dict with: valid (bool), errors (list), line_count (int)
```

Validates every line of a DuckyScript payload against a hardcoded set of
52 valid DuckyScript commands. Also checks that DELAY has a number argument.
Reports line number and error message for every problem found.

**The valid command set includes:**
REM, STRING, STRINGLN, DELAY, GUI, CTRL, ALT, SHIFT, ENTER, BACKSPACE, TAB,
ESCAPE, DELETE, all arrow keys, HOME, END, PAGEUP, PAGEDOWN, CAPSLOCK,
PRINTSCREEN, MENU, SPACE, WAIT_FOR_BUTTON_PRESS, HOLD, RELEASE, REPEAT,
VAR, IF, WHILE, DEFINE, DEFAULT_DELAY, LOCALE, F1 through F12

---

## `_status()` — System Status Object

Returns a complete status snapshot:
- `version`: "3.0"
- `framework`: True/False — whether ToolExecutor imported successfully
- `ollama`: True/False — whether Ollama is running and has models
- `ollama_models`: list of installed model names
- `mcp`: True/False — whether mcp-server binary exists in PATH
- `shell_access`: always True
- `live_terminal`: True/False — whether PTY/websockets are available
- `websocket`: True/False — whether websockets library is installed
- `ws_port`: 8766
- `uptime`: system uptime string like "04:32:11"
- `platform`: "Raspberry Pi 5 16GB" or "Kali Linux"

---

## `_uptime()` and `_platform()`

`_uptime()` reads `/proc/uptime` (Linux only) and formats it as HH:MM:SS.
Returns "N/A" on Windows.

`_platform()` reads `/proc/cpuinfo` and checks for "Raspberry Pi" in the content.
Returns "Raspberry Pi 5 16GB" if found, otherwise "Kali Linux".

---

## `start_server()`

The main server boot function:
1. Checks that `web/index.html` exists — crashes with helpful error if not
2. Creates `HTTPServer` on HOST:HTTP_PORT
3. Prints all URLs to terminal
4. Starts HTTP server in a daemon thread
5. Calls `start_ws_server()` for the WebSocket server
6. Opens the browser automatically with `webbrowser.open()`
7. Joins the HTTP thread (blocks forever)
8. On Ctrl+C: prints shutdown message and calls `server.shutdown()`

---

## `main()`

The entry point. Prints the ASCII art banner in color using ANSI escape codes,
calls `check_ollama()` and `check_ws_deps()` to display startup status,
then calls `start_server()`.

---

---

# 2. live_terminal.py
**File:** `src/core/live_terminal.py`
**Role:** The real-time terminal engine. Spawns tools as actual PTY processes,
streams every output line to the browser live, handles interactive stdin,
and injects inline educational annotations into output.

---

## `parse_intent(raw)`

```
INPUT:  raw = anything the user typed (natural language or command)
OUTPUT: dict with keys: tool, target, raw_cmd, execute, teach,
                        teach_topic, mode
```

**What it does in plain English:**
Reads what the user typed and figures out WHAT they want. Is this a tool
command? A teach request? A raw shell command? Both? This is the natural
language → structured intent parser for the WebSocket terminal.

**The 5 detection steps:**

**Step 1 — Teach detection:**
Scans for any of 17 teach trigger phrases: "teach me", "teach", "and teach",
"explain", "what does", "what does it mean", "help me understand", "why",
"how does", "what is", "show me", "--teach", "-t", "and explain",
"walk me through", "break it down", "i want to learn", "educate me", "what are"

**Step 2 — Raw shell detection:**
If the command starts with `$` or `!`, it's a raw shell passthrough.
Returns `raw_cmd` = the command minus the prefix, `mode` = "interactive"

**Step 3 — Tool detection:**
Scans against 15 tool patterns using regex:

| Tool | Pattern matched |
|---|---|
| nmap | "nmap", "port scan", "scan ports", "network scan", "host discovery" |
| sqlmap | "sqlmap", "sql injection", "sqli", "sql inject" |
| nikto | "nikto", "web scan", "web server scan" |
| gobuster | "gobuster", "dir bust", "directory bust", "dirb", "fuzz dir", "enumerate dir" |
| hydra | "hydra", "brute force", "bruteforce", "credential attack", "password attack" |
| metasploit | "metasploit", "msfconsole", "msf", "exploit" |
| hashcat | "hashcat", "crack hash", "hash crack", "password crack" |
| nuclei | "nuclei", "vuln scan", "vulnerability scan" |
| subfinder | "subfinder", "subdomain", "subdomain enum" |
| aircrack | "aircrack", "wifi", "wpa2", "wireless attack", "handshake" |
| wpscan | "wpscan", "wordpress scan", "wp scan" |
| enum4linux | "enum4linux", "smb enum", "samba enum" |
| ffuf | "ffuf", "fuzz", "fuzzing", "web fuzz" |
| wfuzz | "wfuzz" |
| crackmapexec | "crackmapexec", "cme", "smb spray" |

**Step 4 — Target detection:**
Uses a regex to find an IP address (like 192.168.1.1), CIDR range (192.168.1.0/24),
hostname (example.com), or URL (https://target.com) in the text.
The target is extracted after keywords: "on", "against", "target", "scan", "at", "for"

**Step 5 — Mode determination:**
- tool + teach trigger → `mode: "both"` (run AND explain)
- tool only → `mode: "execute"` (just run it)
- teach only → `mode: "teach"` (just explain, don't run)
- neither → `mode: "execute"` (fallback — try to run as raw command)

**Example outputs:**
```
"scan 192.168.1.1 for ports" →
  {tool:"nmap", target:"192.168.1.1", mode:"execute", teach:False}

"teach me nmap then scan 10.0.0.1" →
  {tool:"nmap", target:"10.0.0.1", mode:"both", teach:True}

"$ whoami" →
  {raw_cmd:"whoami", mode:"interactive", execute:True}

"teach me sqlmap" →
  {tool:"sqlmap", target:None, mode:"teach", teach:True}
```

---

## `build_command(tool, target)`

```
INPUT:  tool   = tool name string
        target = IP, domain, or URL string
OUTPUT: complete shell command string ready to run
```

**What it does in plain English:**
Given a tool name and target, builds the "sensible default" command for that tool.
These are professionally tuned defaults — not just `nmap target`, but
`nmap -sV -sC --top-ports 1000 target` with good flags already set.

**The 15 command templates:**

| Tool | Command Built |
|---|---|
| nmap | `nmap -sV -sC --top-ports 1000 {target}` |
| sqlmap | `sqlmap -u '{target}' --batch --dbs --level=1 --risk=1` |
| nikto | `nikto -h {target}` |
| gobuster | `gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -t 20` |
| hydra | `hydra -l admin -P /usr/share/wordlists/rockyou.txt {target} ssh -t 4` |
| metasploit | `msfconsole -q` |
| hashcat | `hashcat -m 0 -a 0 {target} /usr/share/wordlists/rockyou.txt` |
| nuclei | `nuclei -u http://{target} -s critical,high,medium` |
| subfinder | `subfinder -d {target} -silent` |
| aircrack | `aircrack-ng {target}` |
| wpscan | `wpscan --url http://{target} --enumerate p,u` |
| enum4linux | `enum4linux -a {target}` |
| ffuf | `ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt` |
| wfuzz | `wfuzz -w /usr/share/wordlists/dirb/common.txt --hc 404 http://{target}/FUZZ` |
| crackmapexec | `crackmapexec smb {target}` |

Falls back to `{tool} {target}` for any unknown tool name.

---

## `annotate_line(line, tool, target)`

```
INPUT:  line   = single line of tool output text
        tool   = which tool produced this line
        target = the target being scanned (used in tip text)
OUTPUT: list of event dicts — at minimum [{"type":"output","data":line}]
        may include additional {"type":"teach","data":"[ERR0RS] ..."} events
```

**What it does in plain English:**
This is the INLINE EDUCATION ENGINE. Every single line of output from a
running tool passes through here. It pattern-matches the line and, when it
recognizes something interesting, appends a teaching annotation to the output.
The browser shows the tool output line, then immediately below it shows the
ERR0RS teaching card explaining what that line means.

**Nmap annotations:**

*Port open:* Matches `123/tcp  open  service  version`
- Looks up the port number in PORT_LESSONS
- If found: shows port name + what attackers do with it + the exact attack command
- If not found but version info present: shows "searchsploit {service}" tip

*CVE found:* Matches `CVE-XXXX-XXXXX` anywhere in the line
- Shows NVD lookup URL for that CVE
- Tells you to check Metasploit for an exploit

*VULNERABLE:* If the word VULNERABLE appears
- Shows documentation steps: screenshot, note CVE, check exploits, add to report

*OS detected:* Matches `OS details: {os name}`
- Shows the OS name and tells you which Metasploit platform to search

**The PORT_LESSONS dictionary — 24 ports:**

| Port | Service | What ERR0RS Teaches You |
|---|---|---|
| 21 | FTP | Try anonymous login first |
| 22 | SSH | Hydra brute force target |
| 23 | Telnet | Everything is cleartext, capture with Wireshark |
| 25 | SMTP | User enumeration with smtp-user-enum |
| 53 | DNS | Try zone transfer with dig axfr |
| 80 | HTTP | Run nikto + gobuster, look for admin panels |
| 88 | Kerberos | Active Directory! Try Kerberoasting |
| 110 | POP3 | Try default creds, email content exposure |
| 135 | RPC | Windows host, try rpcclient null session |
| 139 | NetBIOS | SMB! Use smbclient and enum4linux |
| 143 | IMAP | Banner grab reveals software version |
| 389 | LDAP | AD enumeration with ldapsearch |
| 443 | HTTPS | Same as 80, use nikto with -ssl flag |
| 445 | SMB | Check MS17-010 EternalBlue IMMEDIATELY |
| 1433 | MSSQL | Try default creds sa/sa, use sqlmap |
| 1521 | Oracle | Use odat.py, default SID: ORCL |
| 3306 | MySQL | Try empty root password |
| 3389 | RDP | Brute hydra, check BlueKeep |
| 5432 | PostgreSQL | Check for trust authentication |
| 5900 | VNC | Try no-password or common passwords |
| 6379 | Redis | Often no auth, try KEYS * |
| 8080 | HTTP-Alt | Dev/staging server, often less hardened |
| 8443 | HTTPS-Alt | Admin interfaces, API endpoints |
| 27017 | MongoDB | No-auth access extremely common |

**SQLMap annotations:**
- "is vulnerable" / "injection" + "found" → SQL INJECTION CONFIRMED with next steps
- "available databases" → shows how to enumerate tables
- "password" + "hash" → shows hashcat commands to crack the hash

**Gobuster annotations:**
- Status 200 → "THIS PAGE EXISTS! Visit it, look for login forms"
- Status 301/302 → "Redirect — follow it"
- Status 403 → "EXISTS but forbidden — try bypass techniques"

**Hydra annotations:**
- "login:" + "password:" in same line → CREDENTIAL FOUND! Document it, test reuse

**Nikto annotations:**
- "osvdb" or "+" prefix → Teaching card about researching the finding

---

## `LiveProcess` class

**What it is:**
The real terminal process runner. Spawns tools as PTY (pseudo-terminal) processes
so they behave EXACTLY like they're running in a real terminal — colors work,
interactive prompts work, Ctrl+C works. Streams every line of output to a callback.

---

### `LiveProcess.__init__(command, tool, target, output_callback, teach_mode)`

```
INPUT:
  command         = full shell command to run
  tool            = tool name (for annotation lookup)
  target          = scan target (inserted into teaching tips)
  output_callback = function to call with each output event dict
  teach_mode      = True = annotate output with lessons
```

Stores everything. Does NOT start the process yet. The process starts when
you call `.start()`.

---

### `LiveProcess.start()`

```
INPUT:  none
OUTPUT: True if started, False if PTY fork failed
```

**What it does in plain English:**
Creates a PTY (pseudo-terminal) using `pty.fork()`. This creates two things:
- A child process that runs your command in `/bin/bash -c "your command"`
- A parent process that holds the file descriptor (fd) to read/write to that PTY

After forking:
- Child: calls `os.execvp("/bin/bash", ["/bin/bash", "-c", command])` — becomes bash running your command
- Parent: starts the `_read_loop()` in a background thread, emits a "Spawned" system message
  If `teach_mode` is on, calls `_emit_pre_teach()` to show the lesson before the tool runs

**Why PTY instead of subprocess:**
With regular subprocess, tools that check if they're in a terminal will
disable colors, disable interactive features, and sometimes behave differently.
A PTY makes the tool think it's in a real terminal — full colors, full interactivity.

---

### `LiveProcess._emit_pre_teach()`

```
INPUT:  none (uses self.tool)
OUTPUT: none — calls output_callback with a teach_block event
```

Imports `handle_teach_request` from the teach engine and calls it for `self.tool`.
If it gets a success response, emits it as a `teach_block` event BEFORE any
tool output appears. The user sees the full lesson, then the tool starts running.
Exceptions are silently swallowed — if the teach engine isn't available, nothing breaks.

---

### `LiveProcess._read_loop()`

```
INPUT:  none (uses self.fd for the PTY file descriptor)
OUTPUT: none — calls output_callback with events
```

**What it does in plain English:**
This runs in a background thread and is the heartbeat of the live terminal.
It continuously reads from the PTY file descriptor in a loop:

1. Uses `select.select()` to check if data is available (non-blocking check with 0.1s timeout)
2. When data arrives: reads up to 4096 bytes at a time
3. Accumulates data in a buffer
4. When a newline `\n` is found: splits off the first complete line
5. Decodes bytes to UTF-8 string
6. Passes each line to `_process_line()`

Loop ends when:
- `self._running` is set to False
- `os.read()` raises OSError (process died)
- Data is empty (EOF — process exited)

After loop ends: emits `{"type":"system","data":"[ERR0RS] Process complete."}`

---

### `LiveProcess._process_line(line)`

```
INPUT:  line = single decoded output line from the tool
OUTPUT: none — calls output_callback with event list
```

If `teach_mode` is True: passes line through `annotate_line()` which may
return multiple events (the output line + optional teaching annotation).
If `teach_mode` is False: wraps line in `{"type":"output","data":line}` only.
Calls `output_callback` for each event.

---

### `LiveProcess.send_input(text)`

```
INPUT:  text = string to send to the running process
OUTPUT: none
```

Writes `text + "\n"` to the PTY file descriptor.
This is exactly like typing in a terminal and pressing Enter.
Used when the browser sends `{"type":"stdin","data":"yes"}` — the user
is answering an interactive prompt inside the running tool.
Silently ignores OSError (process already dead).

---

### `LiveProcess.send_raw(data)`

```
INPUT:  data = raw bytes
OUTPUT: none
```

Writes raw bytes directly to the PTY. Used for special key sequences like
Ctrl+C (`\x03`), Ctrl+D (`\x04`), Ctrl+Z (`\x1A`). These bytes have special
meanings in a terminal and can't be sent as regular text.

---

### `LiveProcess.terminate()`

```
INPUT:  none
OUTPUT: none
```

Sets `_running = False` (stops the read loop) then sends SIGTERM to the process PID.
SIGTERM is a "please stop gracefully" signal. The process gets a chance to clean up.
If the process ignores SIGTERM, you may need to send SIGKILL — not implemented here
but can be added: `os.kill(self.pid, signal.SIGKILL)`

---

### `LiveProcess.is_running` (property)

```
INPUT:  none
OUTPUT: bool — True if process is still alive
```

Returns `self._running`. Set to True when process starts, set to False
when `_read_loop()` exits naturally or `terminate()` is called.
The WebSocket handler checks this before sending stdin or kill commands.

---

---

# 3. tool_executor.py
**File:** `src/core/tool_executor.py`
**Role:** The real tool execution engine. Every security tool that ERR0RS runs
goes through here. Builds the command, spawns the subprocess, streams output,
enforces timeouts, and parses results into structured findings.

---

## Data Models

### `ToolStatus` (Enum)

The six possible states a tool run can be in:

| Value | Meaning |
|---|---|
| `PENDING` | Created but not started yet |
| `RUNNING` | Currently executing |
| `SUCCESS` | Finished with return code 0 |
| `FAILED` | Finished with non-zero return code |
| `TIMEOUT` | Killed because it exceeded the time limit |
| `NOT_FOUND` | The binary doesn't exist in PATH |

---

### `ToolResult` (dataclass)

The structured result object returned by every tool run:

| Field | Type | What It Contains |
|---|---|---|
| `tool_name` | str | Which tool was run ("nmap", "sqlmap", etc.) |
| `command` | str | The exact command string that was executed |
| `status` | ToolStatus | One of the 6 states above |
| `stdout` | str | Everything the tool printed to standard output |
| `stderr` | str | Everything the tool printed to standard error |
| `return_code` | int | The process exit code (0 = success) |
| `duration_ms` | int | How long it took in milliseconds |
| `findings` | List[Dict] | Parsed structured findings (ports, paths, vulns) |
| `error` | str|None | Human-readable error description if something went wrong |

---

## `_sanitise(value)`

```
INPUT:  value = any string
OUTPUT: string with only safe characters remaining
```

**What it does:**
Strips everything except: letters (a-z A-Z), digits (0-9), dot (.), dash (-),
colon (:), forward slash (/), and underscore (_).

**Why it exists:**
Every user-supplied value (target IP, port, wordlist path) passes through
this before being put into a shell command string. This prevents command injection —
if a user somehow passes `; rm -rf /` as a target, this strips the semicolons
and spaces, leaving just `rm-rf` which is harmless.

**Example:**
```
_sanitise("192.168.1.1; whoami")  → "192.168.1.1whoami"
_sanitise("../../etc/passwd")     → "....etcpasswd"
_sanitise("example.com")         → "example.com"
```

---

## Command Builder Functions

All 10 command builders take `(target: str, params: dict)` and return a complete
shell command string. Every value passed to shell goes through `_sanitise()` first.

---

### `build_nmap(target, params)`

**Builds:** `nmap -sV -sC [-O] [-p ports] -T{timing} -oA /tmp/errorz_nmap {target}`

**Always adds:** `-sV` (version detection) and `-sC` (default NSE scripts)
These two flags together give you the most useful basic scan output.

**Conditional additions:**
- `params["os_detection"] = True` → adds `-O` flag
- `params["ports"] = "top-1000"` → adds `--top-ports 1000` (default)
- `params["ports"] = "1-65535"` → adds `-p-` (scan all ports)
- `params["ports"] = "80,443,8080"` → adds `-p 80,443,8080`
- `params["timing"] = "4"` → adds `-T4` (default is T3)

**Always saves output** to `/tmp/errorz_nmap` in all formats (normal, XML, grepable)
so Metasploit can import the results later.

---

### `build_sqlmap(target, params)`

**Builds:** `sqlmap -u http://{target} --batch --level=3 --risk=2 [--dbs] [--dump]`

**Always adds:** `--batch` (no prompts) + `--level=3` (test more parameters) + `--risk=2`

**Conditional additions:**
- `params["dbs"] = True` → adds `--dbs` to enumerate all databases
- `params["dump"] = True` → adds `--dump` to extract table contents

**Note:** Always prefixes `http://` to the target. If target is already a full URL,
you'd need to pass it differently — this is a known limitation for HTTP-only targets.

---

### `build_nikto(target, params)`

**Builds:** `nikto -h {target} -o /tmp/errorz_nikto.html -format html`

Straightforward. Always saves output as HTML report.
No conditional params — Nikto's flags are simple enough that defaults are fine.

---

### `build_gobuster(target, params)`

**Builds:** `gobuster dir -u http://{target} -w {wordlist} -t {threads}`

**Params:**
- `params["wordlist"]` → defaults to `/usr/share/wordlists/dirb/common.txt`
- `params["threads"]` → defaults to "50"

---

### `build_hydra(target, params)`

**Builds:** `hydra -l {user} -P {wordlist} {target} {service}`

**Params:**
- `params["service"]` → defaults to "ssh"
- `params["wordlist"]` → defaults to `/usr/share/wordlists/rockyou.txt`
- `params["username"]` → defaults to "root"

---

### `build_hashcat(target, params)`

**Note:** In hashcat, `target` is the HASH STRING itself, not an IP address.
You pass the hash you want to crack as the "target".

**Builds:** `hashcat -m {mode} -a 0 {hash} {wordlist}`

**Params:**
- `params["hash_mode"]` → defaults to "0" (MD5)
- `params["wordlist"]` → defaults to rockyou.txt

---

### `build_subfinder(target, params)`

**Builds:** `subfinder -d {target} -o /tmp/errorz_subfinder.txt -json`

Saves results as JSON to `/tmp/errorz_subfinder.txt`.
JSON output makes it easier for the report generator to process findings.

---

### `build_nuclei(target, params)`

**Builds:** `nuclei -t http://{target} -json -o /tmp/errorz_nuclei.json`

Saves JSON results. No severity filter applied here — that's left for
the ExploitGenerator to filter on.

---

### `build_amass(target, params)`

**Builds:** `amass enum -d {target} -o /tmp/errorz_amass.txt -json`

Passive DNS enumeration. Saves to /tmp with JSON output.

---

### `build_metasploit(target, params)`

**This one is different — it writes a resource script (.rc file) first.**

**Builds:** `msfconsole -r /tmp/errorz_msf_resource.rc -q`

**With module specified (`params["module"]`):**
Writes a `.rc` file with:
```
use {module}
set RHOSTS {target}
set {option} {value}  (for each item in params["options"])
run
exit
```

**Without module:**
Writes a `.rc` file that does `search type:exploit target:{target}` then exits.
This gives you a list of relevant exploits without trying to run them.

**Why .rc files:**
msfconsole is interactive by default. The only way to automate it without
a full expect script is to write commands to a resource file and pass it with `-r`.

---

### `build_generic(tool_name, target, params)`

**Last resort builder for tools NOT in the registry.**

**Builds:** `{tool} {target} {extra_flags}`

- `params["extra_flags"]` = list of additional flags like `["-v", "--timeout", "30"]`

Every value is sanitized before insertion. This is the universal fallback
that handles nuclei templates, custom scripts, or any tool not explicitly coded.

---

## Output Parser Functions

### `parse_nmap_output(stdout)`

```
INPUT:  full nmap stdout string
OUTPUT: list of dicts: [{port, protocol, state, service}, ...]
```

Matches every line that looks like: `22/tcp   open   ssh   OpenSSH 8.2`
using the regex `r"(\d+)/(\w+)\s+(\w+)\s+(.*)"`.

Returns structured port objects with port number, protocol (tcp/udp),
state (open/closed/filtered), and service banner.

---

### `parse_subfinder_output(stdout)`

```
INPUT:  subfinder stdout (one subdomain per line or JSON)
OUTPUT: list of dicts: [{subdomain: "sub.example.com"}, ...]
```

Simple line-by-line split. Each non-empty line is a subdomain.

---

### `parse_gobuster_output(stdout)`

```
INPUT:  gobuster stdout
OUTPUT: list of dicts: [{path: "/admin", status_code: "200"}, ...]
```

Matches lines like `Found: /admin (Status: 200)`.
Returns the path and HTTP status code for each finding.

---

### `parse_nuclei_output(stdout)`

```
INPUT:  nuclei JSON-per-line output
OUTPUT: list of dicts: [{template, severity, matched}, ...]
```

Nuclei outputs one JSON object per line. This parser tries to JSON-decode
each line and extracts:
- `template-id`: which vulnerability template matched
- `info.severity`: critical/high/medium/low/info
- `matched-at`: the URL where it was found

Skips lines that aren't valid JSON without crashing.

---

### `parse_generic_output(stdout)`

```
INPUT:  any tool output string
OUTPUT: list of dicts: [{raw: "line of output"}, ...]
```

The fallback parser. Returns every non-empty line as a raw finding.
Used for tools like hashcat, hydra, amass that don't have specific parsers yet.

---

## `ToolExecutor` class

The main execution engine class.

---

### `ToolExecutor.__init__(on_line)`

```
INPUT:  on_line = optional async callback function (tool_name, line) → called for each output line
```

Stores the callback. If provided, every stdout line gets sent to this
callback as it streams — this is how the live dashboard shows progress.
If None (default), output is captured but not streamed in real time.

---

### `ToolExecutor.run(tool_name, target, params)`

```
INPUT:  tool_name = "nmap", "sqlmap", etc.
        target    = IP, domain, or hash
        params    = dict of tool-specific options
OUTPUT: ToolResult object
```

**The 5-step execution flow:**

**Step 1 — Binary check:**
Uses `shutil.which(binary)` to check if the tool is installed.
If not found, immediately returns `ToolResult(status=NOT_FOUND, error="'binary' not found in PATH")`.
This prevents cryptic errors and gives a clear message to install the tool.
Special case: "metasploit" looks for "msfconsole" binary.

**Step 2 — Build command:**
Looks up `COMMAND_BUILDERS[tool_name]` to get the right builder function.
Calls it with target and params to get the full command string.
If tool not in registry, falls back to `build_generic()`.

**Step 3 — Get timeout:**
Checks `params["timeout"]` first (user override).
Falls back to `DEFAULT_TIMEOUTS[tool_name]`.
Falls back to 120 seconds if neither exists.

**Step 4 — Execute:**
Calls `self._execute(tool_name, cmd_str, timeout)`.

**Step 5 — Return:**
Returns the ToolResult from _execute.

---

### `ToolExecutor._execute(tool_name, cmd_str, timeout)`

```
INPUT:  tool_name = for labeling the result
        cmd_str   = the full command to run
        timeout   = max seconds
OUTPUT: ToolResult with all fields populated
```

**What it does in plain English:**
This is where the tool actually runs. Uses Python's asyncio subprocess
to spawn the command and stream output without blocking.

**The async flow:**

1. Records start time
2. Calls `asyncio.create_subprocess_shell(cmd_str, stdout=PIPE, stderr=PIPE)`
   This spawns the tool as a non-blocking async subprocess.

3. Defines `_read_stream(stream, collector, is_stdout)`:
   - Reads line by line with `stream.readline()`
   - Appends each line to the collector list
   - If it's stdout AND there's an `on_line` callback: calls it with each line
   - Stops when readline returns empty bytes (EOF)

4. Runs both stdout and stderr streams concurrently with `asyncio.gather()`
   wrapped in `asyncio.wait_for()` with the timeout.
   Both streams drain simultaneously — this prevents deadlock where
   a tool fills stderr while we're waiting to read stdout.

5. After streams drain: calls `proc.wait()` to get the return code.

6. If `asyncio.TimeoutError`: kills the process, returns TIMEOUT status
   with whatever output was captured so far.

7. If any other exception: returns FAILED status with error message.

**Output parsing:**
After successful run, looks up `OUTPUT_PARSERS[tool_name]`.
Falls back to `parse_generic_output` if no specific parser exists.
Parses the full stdout string into structured findings list.

**Status logic:**
- return code 0 → SUCCESS
- return code non-zero → FAILED
- (Note: some tools like nmap return non-zero even on success in some cases —
   this could be refined per-tool in future versions)

---

### `ToolExecutor.run_batch(tasks, parallel)`

```
INPUT:  tasks    = list of dicts: [{"tool":"nmap","target":"x","params":{}}, ...]
        parallel = True = run all at once, False = run one at a time
OUTPUT: list of ToolResult objects
```

**Sequential mode (parallel=False):**
Loops through tasks, awaiting each one before starting the next.
Use this when tools might conflict or when you want clean sequential output.

**Parallel mode (parallel=True):**
Creates all coroutines at once, passes to `asyncio.gather()`.
All tools start simultaneously and run in parallel.
Use this for reconnaissance phase where tools are independent (subfinder + nmap + nuclei at the same time).

**When to use parallel:**
Good for: recon tools (subfinder, amass, nuclei all on the same target)
Bad for: exploitation tools (metasploit should wait for nmap to finish)

---

## Default Timeout Table

| Tool | Timeout | Reason |
|---|---|---|
| nmap | 300s (5 min) | Top-1000 port scan takes ~1-3 min typically |
| sqlmap | 600s (10 min) | Can be slow with blind injection detection |
| nikto | 180s (3 min) | Web scan against a single host |
| gobuster | 600s (10 min) | Wordlist can have 200k+ entries |
| hydra | 600s (10 min) | Brute force against network service |
| hashcat | 1800s (30 min) | GPU cracking can be very slow for hard hashes |
| subfinder | 120s (2 min) | Passive DNS query — should be fast |
| nuclei | 300s (5 min) | Many template checks |
| amass | 300s (5 min) | DNS/passive recon |
| metasploit | 600s (10 min) | Exploit attempts can take time |

---

---

# 4. teach_engine.py
**File:** `src/education/teach_engine.py`
**Role:** 100% offline knowledge base. No AI, no Ollama, no internet.
Pure Python with 16 built-in lessons that work on any system, any time.

---

## The `LESSONS` Dictionary

The master knowledge base. A nested Python dictionary where each key is a
tool/concept name and the value is a lesson dict with these possible keys:

| Key | What It Contains |
|---|---|
| `title` | Full name string |
| `tldr` | One sentence summary — the quickest possible explanation |
| `what` | Multi-paragraph explanation of what the tool/concept IS |
| `how` | How it works technically — the mechanism behind it |
| `phases` | List of numbered workflow steps |
| `commands` | Dict of {description: shell command} examples |
| `flags` | Dict of {flag: what it does} |
| `defense` | How defenders protect against this |
| `tips` | List of expert pro tips |
| `wordlists` | (hydra/gobuster) Common wordlist paths |
| `hash_modes` | (hashcat) Common hash mode numbers |
| `modules` | (burp suite) Sub-tool descriptions |
| `tools` | (privesc) Related tools with descriptions |
| `filters` | (wireshark) Display filter examples |
| `key_exploits` | (metasploit) Famous CVE → module mappings |

**The 16 built-in lessons:**
nmap, sqlmap, nikto, gobuster, hydra, metasploit, hashcat, aircrack,
nuclei, subfinder, sql injection, xss, meterpreter, privilege escalation,
burp suite, wireshark

---

## `format_lesson(lesson)`

```
INPUT:  lesson = a lesson dict from LESSONS
OUTPUT: formatted multi-line string ready to print to terminal
```

**What it does:**
Renders a lesson dict into a structured, readable terminal output block.
Uses ASCII separators (`=` and `-` lines), section headers, and indentation
to create a consistent layout.

**The rendering order:**
1. `=====` separator line
2. `[ERR0RS TEACHES] {title}` header
3. `=====` separator
4. `[TL;DR]` one-liner
5. `WHAT IT IS:` section (always shown)
6. `HOW IT WORKS:` section (if present)
7. `PENTEST PHASES:` section (numbered list, if present)
8. `KEY COMMANDS:` section (name → `$ command` pairs, if present)
9. `IMPORTANT FLAGS:` section (flag → description table, if present)
10. `MODULES:` section (for Burp Suite)
11. `KEY TOOLS:` section (for PrivEsc)
12. `WORDLISTS:` section (for Hydra/Gobuster)
13. `COMMON HASH MODES:` section (for Hashcat)
14. `DISPLAY FILTERS:` section (for Wireshark)
15. `KEY EXPLOITS:` section (for Metasploit)
16. `[DEFENSE]` section (always shown)
17. `[PRO TIPS]` section (if present — shown as bullet list)
18. Footer: "Type any tool name or 'teach me X' to learn more."

**The flag formatting:**
Each flag is left-justified to 15 characters for alignment:
```
  -sV             Service version detection
  -sC             Default NSE scripts
  -A              Aggressive (OS+version+scripts+traceroute)
```

---

## `find_lesson(query)`

```
INPUT:  query = raw user query string like "teach me how nmap works"
OUTPUT: lesson dict OR None if no match found
```

**What it does in plain English:**
Strips "noise" words from the query and tries to match the remaining
text to a lesson using three escalating strategies.

**Step 1 — Strip common prefixes:**
Removes these from the start of the query (in order):
"teach me", "teach me how to use", "how to use", "how does", "explain",
"what is", "what are", "tell me about", "help me with", "learn", "show me"

So "teach me how to use sqlmap" becomes just "sqlmap"

**Step 2 — Direct LESSONS key match:**
Checks if the stripped query exactly matches a key in LESSONS.
"sqlmap" → exact match → return LESSONS["sqlmap"]
"privilege escalation" → exact match → return that lesson

**Step 3 — KEYWORD_MAP lookup:**
The `KEYWORD_MAP` dictionary has ~60 alternate spellings and aliases:

| What user might type | Maps to lesson |
|---|---|
| "nmap", "network scan", "port scan", "network mapper", "host discovery" | nmap |
| "sqlmap", "sql map", "sglmap", "sql injection", "sqli", "sql inject" | sqlmap or sql injection |
| "gobuster", "directory bruteforce", "dir brute", "dirbuster", "gobust" | gobuster |
| "hydra", "brute force", "bruteforce", "password attack", "credential attack" | hydra |
| "metasploit", "msf", "msfconsole" | metasploit |
| "meterpreter" | meterpreter |
| "hashcat", "password crack", "hash crack", "crack hash", "crack password" | hashcat |
| "aircrack", "wifi hack", "wpa2 crack", "wireless attack", "aircrack-ng" | aircrack |
| "nuclei", "vuln scan", "vulnerability scan" | nuclei |
| "subfinder", "subdomain", "subdomain enum", "subdomain scan" | subfinder |
| "xss", "cross site scripting", "cross-site scripting" | xss |
| "privilege escalation", "privesc", "priv esc", "root" | privilege escalation |
| "burp", "burp suite", "proxy" | burp suite |
| "wireshark", "packet capture", "pcap" | wireshark |

Checks if any keyword appears as a SUBSTRING of the query.
"how do i brute force ssh" → "brute force" found → returns hydra lesson

**Step 4 — Fuzzy lesson key check:**
Checks if any lesson key appears as a substring of the query.
"tell me about nmap flags" → "nmap" found in LESSONS keys → returns nmap

**Returns None** if absolutely nothing matched — caller handles this.

---

## `handle_teach_request(query)`

```
INPUT:  query = raw user query string
OUTPUT: dict with keys: status, source, stdout
```

**What it does:**
The main entry point for all teach requests. Calls `find_lesson(query)`.
If a lesson is found: calls `format_lesson()` and returns:
```python
{"status": "success", "source": "errz_builtin", "stdout": <formatted lesson>}
```

If no lesson found: returns a helpful "I don't know this yet" message
that lists ALL available lessons:
```
[ERR0RS] I don't have a built-in lesson for 'topic' yet.
Topics I CAN teach right now: aircrack, burp suite, gobuster, ...
Try: 'teach me sqlmap' or 'teach me privilege escalation'
To get AI answers: make sure Ollama is running → ollama pull llama3.2
```

The `source: "errz_builtin"` tag lets the UI know this came from the
offline knowledge base (not Ollama) — useful for styling or logging.

---

# 5. natural_language.py
**File:** `src/ai/natural_language.py`
**Role:** Converts plain English sentences into structured tool execution plans.
The "understand English → run security tools" translation layer.

---

## `IntentType` (Enum)

The 10 types of things a user might want to do:

| Intent | Meaning | Example trigger |
|---|---|---|
| SCAN | Find open ports, services, hosts | "scan", "check", "find ports" |
| EXPLOIT | Attack a vulnerability | "exploit", "attack", "pwn", "gain access" |
| ENUMERATE | List subdomains, directories, users | "find subdomains", "enumerate" |
| CRACK | Break password hashes | "crack hash", "brute force", "decrypt" |
| ANALYZE | Inspect or examine something | "analyze", "inspect", "review" |
| REPORT | Generate output report | "generate report", "export findings" |
| MONITOR | Watch network traffic | "monitor", "capture" |
| SEARCH | Search for something | "search for", "find" |
| HELP | User needs assistance | "help", "how to", "what is", "explain" |
| UNKNOWN | Nothing matched | fallback |

---

## `NaturalLanguageInterface.__init__(llm_router)`

Creates the NLI instance. Builds the intent patterns and tool keywords
by calling the two builder methods. Creates a `ToolExecutor` instance
so it can actually run tools when called in YOLO mode.

---

## `_build_intent_patterns()`

```
OUTPUT: dict mapping IntentType → list of regex patterns
```

Builds the regex pattern library used by `_detect_intent()`.
Each IntentType has 2-8 patterns. First pattern that matches wins.

**Key patterns for each intent:**
- SCAN: `r"scan\s+(.+?)\s+for"`, `r"find\s+(open\s+)?ports"`, `r"recon\s+(.+)"`
- EXPLOIT: `r"exploit\s+(.+)"`, `r"test\s+(.+?)\s+for\s+(sql|xss|rce)"`, `r"pwn\s+(.+)"`
- CRACK: `r"crack\s+(this\s+)?(.+?)\s+(hash|password)"`, `r"brute\s*force\s+(.+)"`
- ENUMERATE: `r"find\s+(all\s+)?subdomains\s+of\s+(.+)"`, `r"list\s+(all\s+)?(.+)"`
- REPORT: `r"generate\s+(a\s+)?report"`, `r"export\s+findings"`
- HELP: `r"how\s+to\s+(.+)"`, `r"what\s+is\s+(.+)"`, `r"explain\s+(.+)"`

---

## `_build_tool_keywords()`

```
OUTPUT: dict mapping tool_name → list of trigger keywords
```

Maps keyword hints to tool names. Used by `_select_tools()` to score which tools
are most relevant to the user's request.

| Tool | Keywords that trigger it |
|---|---|
| nmap | port, scan, network, service, host, ip |
| sqlmap | sql, injection, sqli, database |
| nikto | web, server, vulnerability, cgi |
| gobuster | directory, directories, files, bruteforce |
| hydra | password, brute, login, crack |
| hashcat | hash, crack, md5, sha, password |
| metasploit | exploit, payload, shell, reverse |
| subfinder | subdomain, dns, enumerate |
| amass | subdomain, osint, recon, intelligence |
| nuclei | vulnerability, template, scan, detect |
| wpscan | wordpress, wp, cms |
| aircrack | wifi, wireless, wep, wpa, handshake |
| wireshark | packet, capture, network, traffic, pcap |

---

## `parse_command(user_input)`

```
INPUT:  user_input = plain English string
OUTPUT: ParsedIntent object with: intent, target, tools, parameters, confidence, raw_command
```

**The 5-step parsing pipeline:**

**Step 1 → `_detect_intent()`**
Scans the text against all intent regex patterns. Returns the FIRST matching IntentType.
Falls back to UNKNOWN if nothing matches.

**Step 2 → `_extract_target()`**
Tries 4 patterns in order:
1. Domain name: `(?:[a-z0-9]+\.)+[a-z]{2,}` (matches example.com)
2. IP address: `(?:\d{1,3}\.){3}\d{1,3}` (matches 192.168.1.1)
3. Hash: `[a-f0-9]{32,64}` (matches MD5/SHA hex strings)
4. URL: `https?://[^\s]+` (matches full URLs)

Returns the FIRST match found, or None.

**Step 3 → `_select_tools()`**
Scores every tool in `tool_keywords` by counting how many of its keywords
appear in the user's text. Sorts by score descending. Returns top 3 tools.
If no keywords matched, falls back to intent-based defaults:
- SCAN → ["nmap"]
- EXPLOIT → ["metasploit", "sqlmap"]
- CRACK → ["hashcat", "john"]
- ENUMERATE → ["gobuster", "subfinder"]

**Step 4 → `_extract_parameters()`**
Looks for parameter hints in the text:
- "all ports" or "65535" → `ports: "1-65535"`
- "common ports" → `ports: "top-1000"`
- "port 80" → `ports: "80"`
- "fast" or "quick" → `timing: "4"`
- "slow" or "stealth" → `timing: "1"`
- "version" or "service" → `version_detection: True`
- "os" or "operating system" → `os_detection: True`
- "wordlist: /path" → `wordlist: "/path"`
- "json" → `output_format: "json"`

**Step 5 → `_calculate_confidence()`**
Scores from 0.0 to 1.0:
- Intent detected (not UNKNOWN): +0.30
- Target found: +0.30
- Tools selected (up to 3): +0.20 * (count/3)

Maximum possible: 1.0 (capped)
Threshold for execution: 0.50 — below this, asks for clarification.

---

## `execute_command(user_input, mode)`

```
INPUT:  user_input = plain English string
        mode       = "interactive" (default) or "yolo"
OUTPUT: dict with execution results
```

**Interactive mode behavior:**
Returns a confirmation dict WITHOUT running anything:
```python
{
  "status": "awaiting_confirmation",
  "parsed_intent": {intent, target, tools, parameters},
  "message": "I'll scan example.com using nmap. Proceed?",
  "confidence": 0.8
}
```
The UI shows this to the user, they confirm, THEN the tools run.
This is the safe default — never runs tools without the user seeing the plan.

**YOLO mode behavior:**
Immediately calls `_execute_tools()` and runs everything.
Good for automation/scripting where you trust the input.

**Low confidence behavior (< 0.5):**
Returns suggestions list:
```python
{
  "status": "needs_clarification",
  "message": "I'm not sure what you want me to do...",
  "suggestions": ["Try: 'Scan example.com for open ports'", ...]
}
```

---

## `_execute_tools(parsed)`

```
INPUT:  ParsedIntent object
OUTPUT: dict with tool_results list
```

Iterates through `parsed.tools`, calls `_run_tool()` for each.
Catches exceptions per-tool so one failing tool doesn't abort the others.
Returns status "completed" with a list of all results.

---

## `_run_tool(tool_name, target, params)`

```
INPUT:  tool_name, target, params
OUTPUT: dict with tool, status, findings, duration_ms, stdout, stderr, error
```

The actual execution bridge. Calls `self.executor.run(tool_name, target, params)`
which is the real ToolExecutor subprocess runner. Converts the ToolResult object
to a plain dict for JSON serialization.

---

## `_get_suggestions(user_input)`

Returns a hardcoded list of 5 example commands the user can try.
Called when confidence is too low to understand the request.

---

## `get_help(topic)`

Returns help text strings. No `topic` → returns general usage guide with
all example commands. Topic provided → looks up topic-specific help
from a small hardcoded dict covering: scan, sql, crack, subdomain.

---

---

# 6. orchestrator.py
**File:** `src/ai/agents/orchestrator.py`
**Role:** The autonomous pentest brain. Coordinates all 4 agents (CVE, Browser,
Exploit, ToolExecutor) through 5 phases to run a complete pentest automatically.

---

## `AgentOrchestrator.__init__(llm_router, allow_remote)`

```
INPUT:  llm_router    = optional LLM connection for AI explanations
        allow_remote  = True = allow CVE agent to call NVD API online
```

Instantiates all 4 sub-agents:
- `self.cve_agent` = CVEIntelligenceAgent
- `self.browser_agent` = BrowserAutomationAgent
- `self.exploit_agent` = ExploitGeneratorAgent
- `self.executor` = ToolExecutor (the actual subprocess runner)

---

## `autonomous_pentest(target, software_hints)`

```
INPUT:  target         = IP or domain to test
        software_hints = optional list like ["apache log4j", "jquery"] from Nmap banners
OUTPUT: dict with: target, start_time, phases (5 phase results), report, end_time
```

**What it does in plain English:**
This is the BIG function. The "automate everything" button. It runs a complete
5-phase penetration test from start to finish, coordinating all agents,
printing progress to terminal, and assembling a final Markdown report.

**The 5 phases:**

**Phase 1 — Intelligence (CVE Hunting)**
Calls `_phase_intelligence(target, software_hints)`.
The CVE agent searches for known vulnerabilities matching the target's software.
Prints: how many CVEs found, how many critical, how many have working exploits.

**Phase 2 — Web Crawl**
Calls `_phase_web_crawl(target)`.
The browser agent crawls the web application.
Prints: pages crawled count, forms found, number of web findings.

**Phase 3 — Exploit Planning**
Calls `_phase_exploit_planning(intel, web, target)`.
Takes Phase 1 CVEs + Phase 2 web findings and generates tool-chain plans.
Prints: how many exploit plans were generated.

**Phase 4 — Tool Execution**
Calls `_phase_execution(exploit, target)`.
Runs every tool in every exploit plan's tool_chain against the target.
Prints: how many tools ran, total findings collected.

**Phase 5 — Report Assembly**
Calls `_build_report(results)`.
Takes all phase outputs and generates a structured Markdown report.

After all phases: prints total duration in seconds and final finding counts.

---

## `_phase_intelligence(target, software_hints)`

```
INPUT:  target, software_hints
OUTPUT: dict with: cve_count, critical_count, exploitable_count, cves (list of dicts)
```

Builds a `target_info` dict using software_hints (or just the domain name as fallback).
Passes it to `cve_agent.analyze_target()` which returns matching CVEEntry objects.
Counts and categorizes them:
- `critical_count`: CVEs with CVSS score >= 9.0
- `exploitable_count`: CVEs where `exploit_available = True`
Converts all CVEEntry objects to dicts for JSON serialization.

---

## `_phase_web_crawl(target)`

```
INPUT:  target = domain or URL
OUTPUT: full result dict from BrowserAutomationAgent.crawl_and_analyze()
```

Pure delegation — just calls the browser agent and returns everything.
The browser agent handles URL normalization, BFS crawling, and finding extraction.

---

## `_phase_exploit_planning(intel, web, target)`

```
INPUT:  intel = Phase 1 results dict, web = Phase 2 results dict, target
OUTPUT: dict with: plan_count, plans (list of plan dicts)
```

**Part A — CVE-driven plans:**
Iterates every CVE from Phase 1. For each CVE ID, calls
`exploit_agent.generate_from_cve(cve_id, cve_dict)`.
This returns an ExploitPlan with tool_chain, manual steps, and educational notes.

**Part B — Web-finding-driven plans:**
Passes Phase 2 web findings to `exploit_agent.generate_from_web_findings()`.
This generates plans for things like: auth forms found → Hydra brute force plan,
missing headers → security header analysis plan.

Combines all plans into a single list. Converts to dicts for serialization.

---

## `_phase_execution(exploit, target)`

```
INPUT:  exploit = Phase 3 results dict with plans list, target
OUTPUT: dict with: tools_run, total_findings, results (list)
```

**What it does:**
The most important execution phase. Walks through every plan from Phase 3
and runs every tool in every plan's `tool_chain`.

For each step:
1. Extracts `tool_name` and `params` from the step dict
2. Calls `self.executor.run(tool_name, target, params)` — actual subprocess
3. Increments `tools_run` counter
4. Adds `len(result.findings)` to `total_findings`
5. Records the result with status emoji (✅ or ⚠️)

Each tool run is wrapped in try/except so one failure doesn't stop the rest.
Failed tools get recorded as `{"tool": name, "status": "error", "error": message}`.

---

## `_build_report(results)` (static method)

```
INPUT:  results = the full results dict from autonomous_pentest()
OUTPUT: Markdown string — the complete pentest report
```

Builds a Markdown document with these sections:

**Header table:** Target, Start time, End time

**Section 1 — Intelligence Phase:**
CVE counts + a subsection for each CVE with:
- CVE ID, severity, description
- CVSS score, whether exploit is available

**Section 2 — Web Crawl Phase:**
Pages crawled, forms found, JS libraries detected, missing security headers.
A subsection for each finding with severity level.

**Section 3 — Exploit Plans:**
For each plan: technique name, CVE ID, preconditions, manual PoC steps, educational note.

**Section 4 — Execution Results:**
Tools run count, total findings.
For each tool: success/fail emoji, tool name, status, finding count.
Up to 5 findings displayed per tool.

**Section 5 — Recommendations:**
6 hardcoded professional security recommendations covering:
1. Patch critical CVEs immediately
2. Add missing security headers
3. Update third-party libraries
4. Implement rate limiting and account lockout
5. Use parameterized queries (prevent SQLi)
6. Deploy tuned WAF

**Footer:** Disclaimer note that all testing was authorized.

---

## `get_agent_status()`

```
OUTPUT: dict with all 4 agent names mapped to "ready"
```

Simple health check. Returns all agents as "ready" — could be extended to
actually ping the agents and return real status in future versions.

---

# 7. cve_intelligence.py
**File:** `src/ai/agents/cve_intelligence.py`
**Role:** Finds relevant CVEs for a target. Searches local bundled database first.
Optional NVD API fallback when allow_remote=True.

---

## `CVEEntry` (dataclass)

The standard CVE data object:

| Field | Type | Contents |
|---|---|---|
| `cve_id` | str | "CVE-2021-44228" |
| `description` | str | Human-readable description |
| `cvss_score` | float | 0.0 to 10.0 CVSS v3 score |
| `severity` | str | "CRITICAL", "HIGH", "MEDIUM", "LOW" |
| `affected_products` | List[str] | Software names affected |
| `exploit_available` | bool | True if known exploit exists |
| `references` | List[str] | URLs to CVE details |
| `published` | str | Publication date string |

`to_dict()` converts to a plain dictionary for JSON serialization.

---

## The `BUNDLED_CVES` Seed Data

10 pre-loaded high-impact CVEs that work with zero configuration:

| CVE | Name | CVSS | Has Exploit |
|---|---|---|---|
| CVE-2021-44228 | Log4Shell (Log4j RCE) | 10.0 | Yes |
| CVE-2021-34527 | PrintNightmare | 8.8 | Yes |
| CVE-2020-11022 | jQuery XSS | 6.1 | Yes |
| CVE-2021-3156 | Sudo Sequoia | 7.8 | Yes |
| CVE-2019-11358 | jQuery prototype pollution | 6.1 | No |
| CVE-2021-41773 | Apache 2.4.49 Path Traversal | 9.8 | Yes |
| CVE-2017-0144 | EternalBlue SMB RCE | 8.1 | Yes |
| CVE-2014-0160 | Heartbleed OpenSSL | 7.5 | Yes |
| CVE-2020-1472 | ZeroLogon Netlogon | 9.8 | Yes |
| CVE-2022-22965 | Spring4Shell | 9.8 | Yes |

These cover the most common vulnerabilities in CTF labs and real-world targets.

---

## `CVEIntelligenceAgent.__init__(llm_router, allow_remote)`

Stores config. Calls `_load_local_db()` immediately to populate the database.

---

## `_load_local_db()`

```
OUTPUT: list of CVE entry dicts
```

Tries to load `src/ai/data/cve_db.json` from disk — an extended CVE database
that can be pre-downloaded and bundled with the framework for production use.
If that file doesn't exist or can't be parsed: falls back to the 10 `BUNDLED_CVES`.
This graceful fallback means ERR0RS always has CVE data, even fresh installations.

---

## `analyze_target(target_info)`

```
INPUT:  target_info = dict with keys:
          software: ["apache log4j", "jquery"]  ← from Nmap banner grab
          os: "linux"                            ← from OS fingerprint
          services: ["ssh", "http"]             ← from service detection
OUTPUT: list of CVEEntry objects sorted by CVSS score descending
```

**What it does:**
Takes everything known about the target and finds matching CVEs.

**Step 1 — Build search terms:**
Combines software, OS, and service names into one flat list of lowercase strings.

**Step 2 — Search local DB:**
For each entry in the local database, calls `_terms_match()` to check if
ANY search term appears in ANY of the CVE's affected products (or vice versa).
Uses substring matching — "log4j" matches "apache log4j 2.0"

**Step 3 — Optional remote search:**
If no matches AND `allow_remote = True` AND `requests` library is available:
Calls `_query_nvd()` to search the NVD API online.

**Step 4 — Sort:**
Sorts results by (cvss_score, exploit_available) descending.
CVSS 10.0 with exploit comes first. CVSS 6.1 without exploit comes last.

---

## `lookup_cve(cve_id)`

```
INPUT:  cve_id = "CVE-2021-44228" (case insensitive — normalized with .upper())
OUTPUT: CVEEntry OR None
```

Direct lookup by CVE ID in the local database. Case-insensitive match.
If not found locally AND remote allowed: tries `_query_nvd_single()`.

---

## `_query_nvd(terms)` and `_query_nvd_single(cve_id)`

Both hit the NVD REST API v2 at `services.nvd.nist.gov`.

`_query_nvd()` sends a keyword search (first 3 terms, joined with spaces)
with `resultsPerPage=10`. Uses 15-second timeout.

`_query_nvd_single()` looks up one specific CVE ID directly.

Both parse the NVD JSON format through `_nvd_item_to_entry()`.
Both return empty/None on any exception (network error, rate limit, etc.).

**IMPORTANT:** Only called when `allow_remote = True`. Default is False.
This is the privacy-safe design — no data leaves by default.

---

## `_terms_match(search_terms, products)` (static)

```
INPUT:  search_terms = ["apache log4j", "linux"]
        products     = ["apache log4j", "log4j2"]
OUTPUT: True if ANY term matches ANY product
```

Bidirectional substring check:
- "log4j" IN "apache log4j" → True
- "apache log4j" IN "log4j" → False, but...
- "apache log4j" IN "apache log4j 2.14.1" → True

This fuzzy matching catches partial software name matches without requiring exact strings.

---

## `_dict_to_entry(d)` (static)

Converts a raw dict (from local DB or BUNDLED_CVES) to a CVEEntry.
Handles both field naming conventions:
- BUNDLED uses: `cvss`, `products`, `exploit`, `refs`
- External JSON uses: `cvss_score`, `affected_products`, `exploit_available`, `references`

---

## `_nvd_item_to_entry(item)` (static)

Parses one NVD API vulnerability object into CVEEntry format.
Extracts: CVE ID, English description, CVSS v3.1/v3.0 score, severity,
affected products from CPE strings, and reference URLs.

**CVSS extraction logic:**
Tries "cvssMetricV31" first (most recent), falls back to "cvssMetricV30".
Takes baseScore and baseSeverity from the first metric entry.

**Exploit availability heuristic:**
If CVSS >= 9.0 → assumes exploit likely available (conservative estimate).
Not ideal but works without querying separate exploit databases.

---

# 8. browser_automation.py
**File:** `src/ai/agents/browser_automation.py`
**Role:** Web crawler that finds forms, detects JS libraries, checks security headers,
and extracts HTML comments. No Selenium — pure Python regex + stdlib HTTP.

---

## Data Models

### `PageResult` (dataclass)

Per-page crawl result:

| Field | Contents |
|---|---|
| `url` | The page URL |
| `status_code` | HTTP response code |
| `headers` | Dict of response headers |
| `forms` | List of form dicts (action, method, inputs) |
| `links` | List of extracted link URLs |
| `js_libraries` | Detected library names with versions |
| `comments` | HTML comment strings found |
| `missing_headers` | Security headers not present |
| `body_snippet` | First 2KB of body for quick review |

---

## `_fetch(url, timeout)`

```
INPUT:  url     = URL to fetch
        timeout = seconds (default 10)
OUTPUT: (PageResult, full_body_string) tuple OR None on error
```

**What it does:**
Fetches a single URL. Uses `requests.get()` if requests is installed,
otherwise falls back to Python's built-in `http.client`.

**The User-Agent used:**
`"ERR0RS-Scout/1.0 (authorized pentest)"` — identifies the scanner.
Important for authorized assessments — always label your traffic.

**SSL verification disabled** (`verify=False`) — allows scanning sites with
self-signed certificates (common in internal networks and CTF labs).

Returns a tuple of (PageResult with headers, status), full_body string).
The full body is returned separately because PageResult only stores 2KB,
but parsers need the full content.

---

## Parser Functions

### `_extract_links(base_url, html)`

```
INPUT:  base_url = current page URL (for resolving relative links)
        html     = full HTML string
OUTPUT: list of absolute URL strings
```

Regex: `r'<a\s[^>]*href=["\']([^"\']+)["\']'`
Skips javascript:, mailto:, and anchor (#) links.
Uses `urljoin(base_url, raw)` to convert relative paths to absolute URLs.

---

### `_extract_forms(html)`

```
INPUT:  html string
OUTPUT: list of form dicts: [{action, method, inputs}, ...]
```

Regex matches every `<form>...</form>` block (including multi-line with DOTALL).
For each form:
- Extracts `action` attribute (the submission URL)
- Extracts `method` attribute (GET or POST, default GET)
- Within the form body: extracts all `<input name="..." type="...">` elements
- Also extracts `<textarea>` and `<select>` fields by name

Returns structured form objects that the exploit generator uses to plan
credential brute force and injection attacks.

---

### `_extract_comments(html)`

```
INPUT:  html string
OUTPUT: list of comment content strings
```

Regex: `r'<!--(.*?)-->'` with DOTALL flag.
Extracts everything between `<!--` and `-->`.
HTML comments often contain debug info, credentials, version numbers,
TODO/FIXME notes, and internal IP addresses left by developers.

---

### `_detect_js_libraries(html)`

```
INPUT:  html string
OUTPUT: list of strings like "jQuery 3.4.1", "Bootstrap 4.2"
```

Checks the HTML (lowercased) against 10 JS library patterns:

| Pattern | Library |
|---|---|
| `jquery[.\-](\d+\.\d+[\.\d]*)` | jQuery with version |
| `angular[.\-](\d+...)` | AngularJS with version |
| `react[.\-](\d+...)` | React with version |
| `vue[.\-](\d+...)` | Vue.js with version |
| `bootstrap[.\-](\d+...)` | Bootstrap with version |
| `lodash[.\-](\d+...)` | Lodash with version |
| `express[.\-](\d+...)` | Express.js with version |
| `wordpress` (no version) | WordPress |
| `drupal` (no version) | Drupal |
| `joomla` (no version) | Joomla |

Version is extracted from the regex capture group if available.
Output is like "jQuery 3.4.1" or just "WordPress" (no version).
These are cross-referenced against CVE databases for version-specific vulns.

---

### `_check_security_headers(headers)`

```
INPUT:  response headers dict
OUTPUT: list of MISSING security header names
```

Checks for these 8 security headers (case-insensitive):
1. `X-Content-Type-Options` — prevents MIME sniffing
2. `X-Frame-Options` — prevents clickjacking
3. `X-XSS-Protection` — legacy XSS filter hint
4. `Strict-Transport-Security` — forces HTTPS (HSTS)
5. `Content-Security-Policy` — controls resource loading
6. `Cache-Control` — controls caching behavior
7. `Referrer-Policy` — controls referrer header leakage
8. `Permissions-Policy` — controls browser feature access

Returns only the ones that are MISSING — these are findings.

---

## `BrowserAutomationAgent.__init__(llm_router, max_depth, max_pages)`

```
INPUT:  max_depth  = how many link levels deep to crawl (default 3)
        max_pages  = maximum total pages to visit (default 50)
```

Stores configuration. No HTTP connections made at init time.

---

## `crawl_and_analyze(target)`

```
INPUT:  target = URL or domain string
OUTPUT: dict with: target, pages_crawled, forms_found, forms, comments,
                   js_libraries, missing_security_headers, duration_ms, findings
```

**The BFS (Breadth-First Search) crawl:**

1. Normalize URL (add https:// if missing)
2. Extract base domain from URL
3. Initialize queue with `[(target_url, depth=0)]`
4. Initialize visited set, pages list, aggregation lists
5. BFS loop:
   - Pop next (url, depth) from front of queue
   - Skip if already visited OR depth > max_depth
   - Add to visited set
   - Fetch the page with `_fetch()`
   - Run all 5 parsers on the result
   - Add same-domain links to queue with depth+1
   - Stop when visited count reaches max_pages
6. Deduplicate JS libraries and missing headers
7. Return aggregated results

**Same-domain check:**
Only queues links where `urlparse(link).netloc == base_domain`.
This prevents the crawler from leaving the target site.

**Time tracking:**
Records start time at the beginning, calculates `duration_ms` at the end.
Useful for assessing how long reconnaissance took.

---

## `_build_findings(pages, forms, js_libs, missing_hdrs, comments)` (static)

```
INPUT:  all aggregated data from the crawl
OUTPUT: list of structured finding dicts
```

Generates 4 types of findings:

**1. Missing security headers (severity: medium)**
If any headers are missing, generates one finding listing them all.

**2. Interesting HTML comments (severity: low)**
Filters comments for these keywords: todo, fixme, hack, password, secret, key, debug, test, admin
If found: generates finding with count and up to 5 sample comments.

**3. Detected JS libraries (severity: info)**
If any libraries detected: generates finding listing them.
(Info severity because libraries themselves aren't vulns — versions need cross-referencing)

**4. Authentication forms (severity: info)**
Finds forms with a password input field (type=password or name contains "pass").
If found: generates finding with count and the actual form objects.
These are the targets for Hydra brute-force plans.

---

# 9. exploit_generator.py
**File:** `src/ai/agents/exploit_generator.py`
**Role:** Generates exploit PLANS — not shellcode, not weaponized payloads.
Tool configurations and educational PoC steps that feed into ToolExecutor.

---

## `ExploitPlan` (dataclass)

One complete exploit plan:

| Field | Type | Contents |
|---|---|---|
| `cve_id` | str | CVE ID or "N/A" for web-finding plans |
| `target` | str | Target IP or domain |
| `technique_name` | str | Human-readable name like "Log4Shell – JNDI Injection" |
| `severity` | str | CVSS score or "high/medium/low" |
| `tool_chain` | List[Dict] | Steps: [{tool, params, description}, ...] |
| `manual_steps` | List[str] | Numbered human-readable PoC steps |
| `educational_note` | str | Explanation of what the attack does and why it works |
| `preconditions` | List[str] | What must be true for this attack to work |

`to_dict()` converts to plain dict for JSON.

---

## `EXPLOIT_TEMPLATES` Dictionary

5 pre-built exploit plan templates for the most common CVEs and techniques:

**CVE-2021-44228 (Log4Shell):**
- Nuclei template scan for the specific CVE YAML
- 4 manual steps explaining JNDI injection
- Educational note explaining JNDI lookup mechanism
- Precondition: Log4j 2.x < 2.15.0

**CVE-2017-0144 (EternalBlue):**
- Nmap SMB vuln script check first
- Then Metasploit ms17_010_eternalblue module
- 5 manual steps from nmap check to SYSTEM shell
- Educational note on NSA origin and WannaCry connection

**CVE-2021-41773 (Apache Path Traversal):**
- Nuclei template scan
- 4 manual steps showing the URL-encoded traversal payload
- Educational note on the normalization bug
- Note about 2.4.50 bypass (use 2.4.51+)

**sql_injection (generic):**
- SQLMap with --dbs then --dump
- 5 manual steps from identifying injection point to data extraction
- Educational note on parameterized queries as the fix

**xss (generic):**
- Nuclei XSS templates
- 5 manual steps from basic `<script>alert()` test to stored XSS

**directory_bruteforce (generic):**
- Gobuster with 50 threads
- 5 manual steps from wordlist selection to analyzing 403 responses

---

## `ExploitGeneratorAgent.__init__(llm_router)`

Stores optional LLM router reference. No agents created here — they're
created by the Orchestrator and passed results, not instantiated here.

---

## `generate_from_cve(cve_id, cve_details)`

```
INPUT:  cve_id      = "CVE-2021-44228"
        cve_details = optional dict from CVEEntry.to_dict()
OUTPUT: ExploitPlan OR None
```

**Step 1 — Template lookup:**
Checks `EXPLOIT_TEMPLATES[cve_id]`. If found, uses that template.

**Step 2 — Keyword fallback:**
If no template for this CVE ID, reads the description:
- "sql" + "injection" in description → uses sql_injection template
- "xss" or "cross-site" in description → uses xss template
- Otherwise → `_generic_template(cve_id, details)`

**Step 3 — Target injection:**
Walks through the template's `tool_chain` and replaces `{target}` placeholders
in tool options with the actual affected product name from `cve_details`.

**Step 4 — Return ExploitPlan:**
Fills in the ExploitPlan fields from template + cve_details.
Uses CVSS score from details as the `severity` value.

---

## `generate_from_web_findings(web_findings, target)`

```
INPUT:  web_findings = list of finding dicts from BrowserAutomationAgent
        target       = domain/IP string
OUTPUT: list of ExploitPlan objects
```

**For `auth_forms_detected` finding:**
Creates a Hydra credential brute-force plan.
Tool chain: hydra with http-post-form service.
Manual steps: capture the POST request → note form fields → run hydra command.
Preconditions: login form accessible, no CAPTCHA/rate limiting confirmed.

**For `detected_libraries` finding:**
Creates a library version enumeration plan.
Tool chain: nuclei with technologies templates.
Manual steps: cross-reference versions with CVE databases.

**For `missing_security_headers` finding:**
Creates a security header analysis plan.
No tool chain (pure manual review).
Manual steps explain what each missing header means:
- Missing X-Frame-Options → clickjacking risk
- Missing CSP → XSS amplification risk
- Missing HSTS → protocol downgrade/MitM risk

---

## `_generic_template(cve_id, details)` (static)

```
INPUT:  any CVE ID with no specific template
OUTPUT: minimal template dict
```

Generates a basic plan when we have no specific knowledge:
- Tool chain: nuclei trying `cves/{CVE-ID}.yaml`
- 4 manual steps: look up CVE → find affected version → confirm → follow PoC
- Educational note: uses CVE description directly

This is the catch-all that ensures EVERY CVE produces SOME plan,
even if it's not as detailed as the hand-crafted templates.

---

# ARCHITECTURE SUMMARY

```
USER (browser) ← → ws://127.0.0.1:8766 ← → ws_terminal_handler()
                                                   ↓
                                              parse_intent()
                                                   ↓
                                             build_command()
                                                   ↓
                                            LiveProcess (PTY)
                                                   ↓
                              annotate_line() ← output lines → browser
                                   ↑
                             PORT_LESSONS


USER (browser) ← → http://127.0.0.1:8765 ← → ERR0RSHandler.do_POST()
                                                    ↓
                                              route_command()
                                                    ↓
                      ┌─────────────────────────────────────────┐
                      ↓         ↓           ↓          ↓        ↓
               teach_engine  run_shell  run_tool   query_ollama rocketgod/
                handle_       ()         _async()    ()          badusb
               teach_req()                ↓
                                    ToolExecutor
                                         ↓
                                  build_{tool}()
                                         ↓
                                  asyncio subprocess
                                         ↓
                                  parse_{tool}_output()
                                         ↓
                                    ToolResult


ORCHESTRATOR (autonomous mode):
  autonomous_pentest(target)
       ↓
  CVEIntelligenceAgent.analyze_target() → CVEEntry list
       ↓
  BrowserAutomationAgent.crawl_and_analyze() → PageResult list + findings
       ↓
  ExploitGeneratorAgent.generate_from_cve() + generate_from_web_findings()
       ↓
  ToolExecutor.run() × N (one per tool_chain step)
       ↓
  _build_report() → Markdown string
```

---

# ENVIRONMENT VARIABLES

| Variable | Default | Effect |
|---|---|---|
| `ERRZ_HOST` | 127.0.0.1 | HTTP/WS bind address |
| `ERRZ_PORT` | 8765 | HTTP server port |
| `ERRZ_WS_PORT` | 8766 | WebSocket server port |

**To run on all interfaces:** `ERRZ_HOST=0.0.0.0 python3 errorz_launcher.py`
**Custom port:** `ERRZ_PORT=9000 ERRZ_WS_PORT=9001 python3 errorz_launcher.py`

---

# DEPENDENCY MAP

| Feature | Required Packages | Fallback if Missing |
|---|---|---|
| WebSocket live terminal | `websockets` | HTTP polling mode only |
| CVE remote lookup | `requests` | Local DB only |
| Web crawling | `requests` | stdlib http.client |
| PTY terminal | Linux only (`pty` stdlib) | Non-streaming subprocess on Windows |
| Ollama AI | `ollama` running locally | Offline teach mode only |
| Framework (ToolExecutor/NLI) | All src imports | "dev mode" with raw shell |

---

*Document generated from live source code — H:\ERR0RS-Ultimate\*
*ERR0RS Ultimate v3.0 | Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone*
