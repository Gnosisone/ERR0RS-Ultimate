#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║     ERR0RS ULTIMATE — ZERO-DAY TRAINING MODULE                  ║
║              src/core/zeroday_training.py                       ║
║                                                                  ║
║  Teaches vulnerability research and zero-day discovery          ║
║  methodology — the mindset and techniques used by elite         ║
║  researchers, not just tool operators.                          ║
║                                                                  ║
║  Modules:                                                        ║
║    1. Fuzzing fundamentals (dumb, smart, coverage-guided)       ║
║    2. Binary analysis (static, dynamic, symbolic execution)     ║
║    3. Source code auditing methodology                          ║
║    4. Attack surface mapping                                    ║
║    5. Exploit development basics (memory corruption)            ║
║    6. CVE research workflow                                     ║
║    7. Responsible disclosure process                            ║
║    8. Live fuzzing lab (against safe local targets)             ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Callable


# ══════════════════════════════════════════════════════════════════════════════
# CURRICULUM — structured zero-day research training
# ══════════════════════════════════════════════════════════════════════════════

ZERODAY_CURRICULUM = {

    "overview": {
        "title":   "What is Zero-Day Research?",
        "level":   "beginner",
        "summary": "A zero-day is a vulnerability that the vendor doesn't know about yet — giving attackers a head start of 'zero days' to patch it.",
        "content": """
ZERO-DAY RESEARCH — THE MINDSET
════════════════════════════════

A zero-day isn't magic. It's what happens when a security researcher
spends more time understanding a piece of software than the person who wrote it.

WHY IT MATTERS:
  • Nation-state actors stockpile 0days for cyber operations
  • Bug bounty programs pay $10,000 → $2,500,000 per vulnerability
  • Understanding 0day research makes you a better defender
  • The CVE database started empty — every entry was a 0day first

THE RESEARCH PROCESS:
  1. Choose a target (widely-deployed software = high impact)
  2. Map the attack surface (inputs, parsers, network protocols)
  3. Understand the code (source audit or reverse engineering)
  4. Find where assumptions break (edge cases, type confusion, length checks)
  5. Confirm exploitability (PoC that crashes or redirects execution)
  6. Responsible disclosure (notify vendor → 90-day window → publish)

CATEGORIES OF VULNERABILITIES:
  • Memory corruption: buffer overflow, heap spray, use-after-free
  • Logic flaws: auth bypass, privilege escalation, race conditions
  • Parser bugs: format string, integer overflow, type confusion
  • Injection: SQL, command, LDAP, XPath, template injection
  • Cryptographic: weak primitives, timing attacks, padding oracles

TOOLS OF THE TRADE:
  • AFL++        — coverage-guided fuzzer (finds crashes automatically)
  • Ghidra       — NSA's free reverse engineering framework
  • radare2      — open-source binary analysis framework  
  • pwntools     — Python exploit development library
  • GDB + pwndbg — dynamic analysis and exploit debugging
  • Valgrind     — memory error detector
  • AddressSanitizer — compiler instrumentation for memory bugs
""",
        "next": ["fuzzing", "source_audit", "binary_analysis"],
    },

    "fuzzing": {
        "title":   "Fuzzing — Finding Crashes Automatically",
        "level":   "intermediate",
        "summary": "Fuzzing feeds random or mutated inputs to a program until it crashes. A crash = potential vulnerability.",
        "content": """
FUZZING FUNDAMENTALS
════════════════════

WHAT IT IS:
  Automated testing that generates inputs designed to break things.
  If the program crashes, throws an exception, or hangs —
  something unexpected happened. That something might be a vulnerability.

THREE TYPES:

  1. DUMB FUZZING (random bytes)
     Fast but inefficient. Good for finding obvious parser bugs.
     $ cat /dev/urandom | program 2>/dev/null
     $ radamsa input.txt | program

  2. MUTATION FUZZING (mutate valid inputs)  
     Start with valid samples, apply bitflips, byte substitutions.
     AFL++ does this at massive scale with feedback about code coverage.

  3. COVERAGE-GUIDED FUZZING (the gold standard)
     The fuzzer learns which inputs explore new code paths.
     AFL++ instruments the binary to track branch coverage.
     Each new branch explored = fuzzer keeps that input and mutates it.
     This is how most real vulnerabilities are found today.

AFL++ QUICK START:
  # Install
  sudo apt install afl++
  
  # Compile with instrumentation
  AFL_USE_ASAN=1 afl-clang-fast -o target_afl target.c
  
  # Create seed corpus
  mkdir seeds && echo "test" > seeds/seed1
  
  # Start fuzzing
  afl-fuzz -i seeds/ -o findings/ -- ./target_afl @@
  
  # Monitor
  afl-whatsup findings/

WHAT TO FUZZ:
  • File parsers (PDF, image, audio, document formats)
  • Network protocol handlers (parse_packet(), handle_request())
  • Input parsers (JSON, XML, HTML, command-line args)
  • Compression/decompression (zlib, bzip2, lz4)
  • Cryptographic implementations (custom crypto = red flag)

READING CRASH OUTPUT:
  • SIGSEGV = segmentation fault → memory access violation → overflow candidate
  • SIGABRT = assertion failure → logic error or double-free
  • Heap buffer overflow → overwriting heap metadata → potentially exploitable
  • Stack buffer overflow → can overwrite return address → classic RCE
  • Use-after-free → dangling pointer → exploitable on heap

TRIAGE WORKFLOW:
  1. Fuzzer finds crash → saves input to crashes/ directory
  2. Run crash input under GDB: gdb ./program; run < crash_input
  3. Check crash address: info registers; x/20xg $rsp
  4. Determine exploitability: can we control $rip (instruction pointer)?
  5. Develop PoC, write CVE report
""",
        "tools": ["afl++", "radamsa", "gdb", "pwndbg"],
        "lab":   "fuzz_lab",
        "next":  ["binary_analysis", "exploit_dev"],
    },

    "binary_analysis": {
        "title":   "Binary Analysis — Reading Code You Can't See",
        "level":   "advanced",
        "summary": "When source isn't available, reverse engineering lets you understand what a binary does and find vulnerabilities in it.",
        "content": """
BINARY ANALYSIS
═══════════════

STATIC ANALYSIS (without running the code):
  Disassemble the binary → understand logic → find dangerous patterns.

  GHIDRA WORKFLOW:
    1. File → Import File → select binary
    2. Analyze → Auto Analyze (takes 2-10 minutes for large binaries)
    3. Symbol Tree → Functions → find interesting functions
    4. Look for: strcpy, sprintf, gets, memcpy with unchecked lengths
    5. Decompiler view: C-like pseudocode of each function
    6. Cross-references: who calls this function? where is this used?

  DANGEROUS FUNCTIONS TO SEARCH FOR:
    strcpy, strcat, sprintf, vsprintf → buffer overflow candidates
    gets → always vulnerable (no length check)
    scanf("%s") → buffer overflow
    malloc + memcpy without length validation → heap overflow
    fgets + strtok → potential off-by-one

DYNAMIC ANALYSIS (running the code):
  Run with debugger attached → observe real behavior → inspect memory.

  GDB + PWNDBG WORKFLOW:
    # Install pwndbg
    git clone https://github.com/pwndbg/pwndbg && cd pwndbg && ./setup.sh
    
    # Start debugging
    gdb ./vulnerable_binary
    
    # Key commands:
    run {args}         → run the program
    break *0x401234    → set breakpoint at address
    continue           → continue execution
    info registers     → show all registers
    x/20xg $rsp        → examine stack (20 qwords from rsp)
    x/s $rdi           → examine string at rdi
    backtrace          → show call stack
    pattern create 200 → create cyclic pattern to find offset
    pattern offset 0x41414141 → find offset to return address

SYMBOL ANALYSIS:
  # What functions does it call?
  nm ./binary | grep " T "
  strings ./binary | grep interesting
  ltrace ./binary      → trace library calls
  strace ./binary      → trace system calls
  objdump -d ./binary  → disassemble

MEMORY PROTECTION BYPASSES:
  • ASLR (Address Space Layout Randomization)
    → info leak vulnerability → leak a pointer → calculate base
    → ret2libc or ROP chain
  
  • NX/DEP (No-Execute on stack)
    → can't put shellcode on stack → use ROP (Return-Oriented Programming)
    → chain small existing code sequences ("gadgets") to build exploit
  
  • Stack Canary
    → detect overflow by checking canary before return
    → bypass: format string leak, brute force on 32-bit
  
  • PIE (Position-Independent Executable)
    → binary itself at random address → need base leak first
""",
        "tools": ["ghidra", "gdb", "pwndbg", "radare2", "ltrace", "strace"],
        "next":  ["exploit_dev", "cve_workflow"],
    },

    "source_audit": {
        "title":   "Source Code Auditing",
        "level":   "intermediate",
        "summary": "Systematic review of source code to find security vulnerabilities before attackers do.",
        "content": """
SOURCE CODE AUDITING METHODOLOGY
══════════════════════════════════

MINDSET: You're looking for places where the code trusts user input
         in ways it shouldn't. Every input is attacker-controlled.

THE AUDIT WORKFLOW:

  1. UNDERSTAND THE ARCHITECTURE FIRST
     • What does this application do?
     • What are the trust boundaries? (user input, network, files, DB)
     • Where does data enter? Where does it go?
     • What permissions does it run with?

  2. MAP ENTRY POINTS (all sources of external input)
     • HTTP parameters, headers, body
     • File uploads, file paths, file contents
     • Database queries (from ORM or raw SQL)
     • Environment variables
     • CLI arguments
     • IPC, sockets, pipes

  3. TRACE DATA FLOWS (from input to dangerous sinks)
     • Input → SQL query (SQLi)
     • Input → shell command (RCE)
     • Input → file path (path traversal, LFI)
     • Input → HTML output (XSS)
     • Input → deserialization (object injection)
     • Input → memory buffer (buffer overflow)

  4. GREP FOR DANGEROUS PATTERNS
     Web (Python/PHP/Ruby/Node):
       grep -rn "eval\\|exec\\|system\\|subprocess" .
       grep -rn "pickle.loads\\|yaml.load\\|json.loads" .
       grep -rn "render_template_string\\|format(" .
       grep -rn "open(.*request\\|open(.*param" .

     SQL:
       grep -rn "SELECT.*+\\|\\\".*%s\\|format.*SELECT" .
       grep -rn "execute(.*+" .   # string concat in SQL = SQLi

     C/C++:
       grep -rn "strcpy\\|strcat\\|sprintf\\|gets\\|scanf" .
       grep -rn "malloc.*memcpy\\|realloc" .

  5. REVIEW AUTHENTICATION AND AUTHORIZATION
     • Are session tokens cryptographically secure?
     • Are authorization checks on EVERY endpoint?
     • Can a low-priv user access high-priv functions?
     • Is there TOCTOU (time-of-check-time-of-use)?

  6. CRYPTOGRAPHY REVIEW
     • MD5/SHA1 for passwords = broken
     • ECB mode = patterns visible in ciphertext
     • Hardcoded keys or IVs = disaster
     • "Roll your own crypto" = almost always broken

TOOLS FOR AUTOMATED AUDIT:
  semgrep     → pattern-based SAST (run: semgrep --config=auto .)
  bandit      → Python security linter (run: bandit -r .)
  gosec       → Go security linter
  graudit     → grep-based audit database
  CodeQL      → GitHub's semantic analysis (free for open source)

COMMON FINDINGS BY LANGUAGE:
  PHP:    include($user_input), eval($data), preg_replace /e modifier
  Python: pickle.loads, yaml.load (not safe_load), exec/eval
  Node:   eval(), vm.runInNewContext(), child_process.exec with user input
  Java:   ObjectInputStream.readObject(), Runtime.exec(), ProcessBuilder
  Ruby:   send(method_name), eval, system, backticks with user input
""",
        "tools": ["semgrep", "bandit", "graudit"],
        "next":  ["fuzzing", "cve_workflow"],
    },

    "exploit_dev": {
        "title":   "Exploit Development Basics",
        "level":   "advanced",
        "summary": "Turning a crash into a working exploit — controlling program execution.",
        "content": """
EXPLOIT DEVELOPMENT FUNDAMENTALS
══════════════════════════════════

WARNING: This is for understanding how exploits work so you can
defend against them. Developing exploits for unauthorized targets
is illegal.

THE GOAL: Control the instruction pointer ($rip on x64, $eip on x86).
          If you control what instruction executes next, you control the program.

CLASSIC STACK BUFFER OVERFLOW:

  Vulnerable C code:
    void vuln(char *input) {
        char buf[64];
        strcpy(buf, input);  // no length check!
    }

  What happens:
    [buf (64 bytes)] [saved rbp (8)] [return address (8)]
    
    If input > 64 bytes, we overwrite rbp.
    If input > 72 bytes, we overwrite the return address.
    When function returns → jumps to OUR address.

  EXPLOIT STEPS (no protections):
    1. Find buffer size: afl-fuzz or send increasing lengths until crash
    2. Find exact offset: python3 -c "from pwn import *; print(cyclic(200))"
    3. Check crash: gdb → info registers → $rsp value = cyclic pattern
    4. Get offset: cyclic_find(0x61616161) → offset to return address
    5. Build exploit:
       payload = b"A" * offset + p64(target_address)

  WITH MODERN PROTECTIONS (NX + ASLR + PIE):
    • Need an info leak first (format string, out-of-bounds read)
    • Use leaked address to calculate base
    • Use ROP chains instead of shellcode
    • Find gadgets: ROPgadget --binary ./target | grep "pop rdi"
    • Chain gadgets to call system("/bin/sh")

PWNTOOLS CHEAT SHEET:
    from pwn import *
    
    # Connect
    p = process("./target")          # local
    p = remote("host", 1337)         # remote
    
    # Interact
    p.recv(1024)                     # receive data
    p.recvline()                     # receive until newline
    p.sendline(b"payload")           # send + newline
    p.send(b"payload")               # send raw
    
    # Pack addresses
    p64(0xdeadbeef)                  # 64-bit little-endian
    p32(0xdeadbeef)                  # 32-bit little-endian
    
    # Get shell
    p.interactive()                  # drop to interactive mode

RESOURCES:
  • pwn.college — free interactive exploit development courses
  • exploit.education — VM-based exploit dev challenges  
  • picoCTF — beginner-friendly CTF with pwn challenges
  • ROPemporium — ROP chain practice challenges
""",
        "tools": ["pwntools", "gdb", "pwndbg", "ROPgadget"],
        "next":  ["cve_workflow"],
    },

    "cve_workflow": {
        "title":   "CVE Research & Responsible Disclosure",
        "level":   "intermediate",
        "summary": "The professional process for reporting vulnerabilities — from discovery to CVE assignment.",
        "content": """
CVE RESEARCH & RESPONSIBLE DISCLOSURE
══════════════════════════════════════

THE PROCESS:

  1. CONFIRM THE VULNERABILITY
     • Write a minimal PoC that reproduces the crash reliably
     • Determine impact: CVSS score, affected versions, exploitability
     • CVSS Calculator: https://nvd.nist.gov/vuln-metrics/cvss

  2. IDENTIFY THE VENDOR
     • Who maintains the software?
     • Find their security contact: security@vendor.com, HackerOne, Bugcrowd
     • Check security.txt: https://target.com/.well-known/security.txt

  3. PREPARE YOUR REPORT
     Required elements:
       □ Vulnerability type (CVE category)
       □ Affected versions (oldest and newest)
       □ CVSS score + vector string
       □ Step-by-step reproduction instructions
       □ Working PoC (proof of concept)
       □ Suggested fix/mitigation
       □ Timeline of discovery

  4. SUBMIT TO VENDOR (private disclosure)
     • Send encrypted report to vendor security contact
     • Request CVE ID from MITRE if vendor doesn't assign
     • Set 90-day disclosure deadline (industry standard)
     • Document all communication with timestamps

  5. THE 90-DAY WINDOW
     • Vendor acknowledges receipt → confirms vulnerability
     • Vendor develops and tests patch
     • Coordinate public disclosure date
     • If vendor unresponsive after 90 days → disclose publicly
     • Extensions granted for complex/widespread issues

  6. PUBLIC DISCLOSURE
     • Vendor publishes advisory + patch
     • CVE assigned and published to NVD
     • You can publish technical blog/talk
     • Bug bounty paid (if program exists)

BUG BOUNTY PLATFORMS:
  HackerOne:  https://hackerone.com/bug-bounty-programs
  Bugcrowd:   https://bugcrowd.com/programs
  Intigriti:  https://www.intigriti.com
  Synack:     https://www.synack.com (invite only, high pay)

REQUESTING A CVE:
  1. MITRE: https://cveform.mitre.org
  2. CNA (CVE Numbering Authority) direct if vendor is one
  3. GitHub Security Advisories auto-assigns CVEs

FAMOUS BUG BOUNTIES:
  • Google Pixel: up to $250,000
  • Microsoft: up to $250,000
  • Apple: up to $2,500,000 (zero-click kernel vuln)
  • Crowdstrike: up to $25,000

LEGAL PROTECTION:
  • Bug bounty programs = explicit authorization
  • CFAA: unauthorized access is a federal crime
  • Always get written permission or use bug bounty scope
  • Responsible disclosure ≠ legal protection without authorization
""",
        "next":  ["overview"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# LIVE FUZZING LAB — safe local practice
# ══════════════════════════════════════════════════════════════════════════════

FUZZ_TARGETS = {
    "http_parser": {
        "description": "Fuzz the HTTP request parser in the local Python HTTP server",
        "safe":        True,
        "cmd_template": "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:{port}/' + '{payload}')\" 2>/dev/null",
        "payloads": [
            "A" * 1000,
            "../" * 50,
            "'" * 100,
            "%00" * 100,
            "\x00" * 100,
            "admin' OR '1'='1",
            "<script>alert(1)</script>",
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# ZERO-DAY TRAINING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ZeroDayTrainer:
    """
    Interactive zero-day research training.
    Teaches methodology, tools, and practice labs.
    """

    def __init__(self, broadcast_fn: Callable):
        self.broadcast = broadcast_fn

    def teach(self, topic: str) -> str:
        """Deliver a lesson on a zero-day research topic."""
        key = self._resolve(topic)
        if not key:
            topics = ", ".join(ZERODAY_CURRICULUM.keys())
            return f"⚠️ No lesson for '{topic}'. Available: {topics}"

        lesson = ZERODAY_CURRICULUM[key]
        return self._format(lesson)

    def list_topics(self) -> str:
        lines = ["\n📚 ZERO-DAY RESEARCH CURRICULUM", "═"*50]
        levels = {"beginner": "🔰", "intermediate": "⚡", "advanced": "🔥"}
        for key, lesson in ZERODAY_CURRICULUM.items():
            icon = levels.get(lesson.get("level",""), "•")
            lines.append(f"  {icon} {key:20s} — {lesson['summary'][:60]}")
        lines.append(f"\n  Usage: 'zeroday teach fuzzing' or 'zeroday <topic>'")
        return "\n".join(lines)

    def check_tools(self) -> str:
        """Check which research tools are installed."""
        tools = {
            "afl++":   "Coverage-guided fuzzer",
            "ghidra":  "Reverse engineering framework (check /opt/ghidra)",
            "gdb":     "GNU Debugger",
            "pwndbg":  "GDB enhancement for exploit dev (check ~/.gdbinit)",
            "radare2": "Binary analysis framework",
            "semgrep": "Static analysis / SAST",
            "bandit":  "Python security linter",
            "ROPgadget":"ROP chain finder",
            "pwntools":"Python exploit library",
            "valgrind":"Memory error detector",
        }
        lines = ["\n🔧 RESEARCH TOOL STATUS", "─"*40]
        for tool, desc in tools.items():
            binary = "afl-fuzz" if tool == "afl++" else tool
            installed = "✅" if shutil.which(binary) or (
                tool == "pwndbg" and os.path.exists(os.path.expanduser("~/.gdbinit"))
            ) or (
                tool == "ghidra" and any(os.path.exists(p) for p in ["/opt/ghidra", "/usr/share/ghidra"])
            ) or (
                tool == "pwntools" and __import__("importlib.util", fromlist=["find_spec"]).find_spec("pwn") is not None
            ) else "❌"
            lines.append(f"  {installed} {tool:12s} — {desc}")

        lines.append("\n  Install missing tools:")
        lines.append("    sudo apt install afl++ gdb radare2 valgrind")
        lines.append("    pip install pwntools semgrep --break-system-packages")
        lines.append("    pip install bandit --break-system-packages")
        return "\n".join(lines)

    def _resolve(self, topic: str) -> Optional[str]:
        topic = topic.lower().strip().replace(" ", "_").replace("-", "_")
        if topic in ZERODAY_CURRICULUM:
            return topic
        for key in ZERODAY_CURRICULUM:
            if topic in key or key in topic:
                return key
        return None

    def _format(self, lesson: dict) -> str:
        level_icons = {"beginner":"🔰","intermediate":"⚡","advanced":"🔥"}
        icon = level_icons.get(lesson.get("level",""), "📖")
        lines = [
            f"\n{'═'*60}",
            f"{icon} {lesson['title'].upper()}",
            f"Level: {lesson.get('level','').upper()}",
            f"{'─'*60}",
            f"SUMMARY: {lesson['summary']}",
            lesson["content"],
        ]
        if lesson.get("tools"):
            lines.append(f"TOOLS: {', '.join(lesson['tools'])}")
        if lesson.get("next"):
            lines.append(f"NEXT:  {', '.join(lesson['next'])}")
        lines.append(f"{'═'*60}")
        return "\n".join(lines)


# ── Global singleton ──────────────────────────────────────────────────────────
_trainer: Optional[ZeroDayTrainer] = None

def get_zeroday_trainer(broadcast_fn: Callable = None) -> Optional[ZeroDayTrainer]:
    global _trainer
    if _trainer is None and broadcast_fn:
        _trainer = ZeroDayTrainer(broadcast_fn=broadcast_fn)
    return _trainer

def handle_zeroday_command(cmd: str, broadcast_fn: Callable) -> str:
    """Route zeroday commands from the WS handler."""
    trainer = get_zeroday_trainer(broadcast_fn)
    cmd = cmd.strip()

    if re.match(r"^zeroday\s+(teach|lesson|learn)\s+(.+)", cmd, re.IGNORECASE):
        topic = re.sub(r"^zeroday\s+(?:teach|lesson|learn)\s+", "", cmd, flags=re.IGNORECASE)
        return trainer.teach(topic)
    elif re.match(r"^zeroday\s+topics?$", cmd, re.IGNORECASE):
        return trainer.list_topics()
    elif re.match(r"^zeroday\s+tools?$", cmd, re.IGNORECASE):
        return trainer.check_tools()
    elif re.match(r"^zeroday\s+(.+)", cmd, re.IGNORECASE):
        topic = re.sub(r"^zeroday\s+", "", cmd, flags=re.IGNORECASE)
        return trainer.teach(topic)
    else:
        return trainer.list_topics()
