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
    lines.append(f"\n  Typical use:  {lesson['typical']}\n")
    lines.append("  FLAGS / OPTIONS:")
    for flag, desc in lesson['flags'].items():
        lines.append(f"    {flag:<22} {desc}")
    lines.append("\n  READING THE OUTPUT:")
    for r in lesson['read']:
        lines.append(f"    • {r}")

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
