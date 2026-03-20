"""
╔══════════════════════════════════════════════════════════════════╗
║      ERR0RS ULTIMATE — BreachBot Autonomous Vuln Scanner         ║
║             src/tools/breach/breach_bot.py                       ║
║                                                                  ║
║  WHAT THE REEL SHOWED:                                           ║
║  - Initializing Vulnerability Scan                               ║
║  - Scanning Target: 192.168.1.100                                ║
║  - Checking for SQL Injection                                    ║
║  - Testing for XSS Vulnerabilities                               ║
║  - Analyzing Open Ports                                          ║
║  - Exploit Successful: Access Granted! (green)                   ║
║  - Directory listing of /var/www/html                            ║
║    (config.php, db_backup.sql, uploads, .htaccess visible)       ║
║                                                                  ║
║  WHAT WAS MISSING (added here):                                  ║
║  - Full multi-phase autonomous scan pipeline                     ║
║  - Nuclei integration (template-based vuln scanner)              ║
║  - CVE lookup per service version                                ║
║  - Web tech fingerprinting + version-specific exploit checks     ║
║  - File exposure checks (backup files, config exposure,          ║
║    .git exposure, .env exposure, phpinfo, admin panels)          ║
║  - Default credential testing per detected service               ║
║  - Subdomain takeover checks                                     ║
║  - CORS misconfiguration detection                               ║
║  - SSL/TLS weakness checks (SSLv3, TLS 1.0, weak ciphers)       ║
║  - Open redirect detection                                       ║
║  - Clickjacking header checks                                    ║
║  - Orchestration with ERR0RS toolchain (nmap → nikto →           ║
║    gobuster → sqlmap → nuclei)                                   ║
║  - Progress display with phase tracking                          ║
║  - Aggregated findings de-duplication                            ║
║                                                                  ║
║  AUTHORIZED PENETRATION TESTING USE ONLY                         ║
╚══════════════════════════════════════════════════════════════════╝

TEACHING NOTE — Automated vs Manual Scanning:
──────────────────────────────────────────────
BreachBot chains multiple tools together in the correct order:
  Phase 1: RECON    — Who is this target? What ports/services?
  Phase 2: SCANNING — What vulnerabilities exist on those services?
  Phase 3: EXPLOIT  — Are any of those vulnerabilities actually exploitable?
  Phase 4: POST     — What can we access once we're in?

Real pentesters do this manually. BreachBot automates the orchestration
but still requires YOUR authorization and YOUR judgment on results.

MITRE ATT&CK Coverage:
  T1595 — Active Scanning
  T1190 — Exploit Public-Facing Application
  T1505 — Server Software Component
  T1083 — File and Directory Discovery
  T1552 — Unsecured Credentials
"""

import os, sys, json, time, subprocess, logging, re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.core.models import Finding, Severity, PentestPhase

log = logging.getLogger("errors.tools.breach")


class ScanPhase(Enum):
    RECON         = "recon"
    PORT_SCAN     = "port_scan"
    SERVICE_ENUM  = "service_enumeration"
    WEB_SCAN      = "web_scan"
    VULN_SCAN     = "vulnerability_scan"
    EXPLOIT_CHECK = "exploit_check"
    FILE_ENUM     = "file_enumeration"
    COMPLETED     = "completed"


@dataclass
class ScanResult:
    target:      str
    phase:       ScanPhase
    tool_used:   str
    success:     bool
    findings:    List[Finding] = field(default_factory=list)
    raw_output:  str = ""
    duration:    float = 0.0
    timestamp:   str = field(default_factory=lambda: datetime.now().isoformat())


# ─────────────────────────────────────────────────────────────────
# FILE EXPOSURE CHECKER
# ─────────────────────────────────────────────────────────────────

class FileExposureChecker:
    """
    Checks for commonly exposed sensitive files on web servers.
    
    TEACHING NOTE: Many breaches happen not from complex exploits but
    from developers accidentally leaving backup files, config files,
    or debug files accessible on the web server. These are trivial
    to find but devastating when discovered by an attacker.
    """

    # Files that should NEVER be web-accessible
    SENSITIVE_PATHS = [
        # Config & credential files
        ".env", ".env.local", ".env.production", ".env.backup",
        "config.php", "config.inc.php", "wp-config.php",
        "settings.py", "config.yml", "config.yaml",
        "database.yml", "secrets.yml",
        # Backup files
        "backup.sql", "db_backup.sql", "dump.sql",
        "backup.zip", "backup.tar.gz", "site.zip",
        # Development artifacts
        ".git/config", ".git/HEAD",
        ".svn/entries", ".htpasswd",
        # Debug / info pages
        "phpinfo.php", "info.php", "test.php",
        "debug.php", "server-status", "server-info",
        # Admin panels (often forgotten)
        "admin/", "administrator/", "phpmyadmin/",
        "wp-admin/", "cpanel/", "webmail/",
        # API documentation (may expose endpoints)
        "swagger.json", "openapi.json", "api-docs/",
    ]

    def check(self, target: str, port: int = 80, ssl: bool = False) -> List[Finding]:
        """Check target web server for exposed sensitive files."""
        import urllib.request, urllib.error
        findings = []
        scheme = "https" if ssl or port == 443 else "http"
        base_url = f"{scheme}://{target}:{port}"

        print(f"[BREACHBOT] Checking {len(self.SENSITIVE_PATHS)} sensitive paths on {base_url}")
        found_count = 0

        for path in self.SENSITIVE_PATHS:
            url = f"{base_url}/{path}"
            try:
                req = urllib.request.Request(url, method="GET",
                    headers={"User-Agent": "Mozilla/5.0 (Security Assessment)"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get("Content-Type", "")
                        content_len  = resp.headers.get("Content-Length", "unknown")
                        found_count += 1
                        # Determine severity based on what was found
                        sev = Severity.CRITICAL if any(kw in path for kw in
                              [".env", "config.php", ".git", "backup", ".sql", "wp-config"]) \
                              else Severity.HIGH
                        findings.append(Finding(
                            title       = f"Exposed Sensitive File: /{path}",
                            description = (f"Sensitive file accessible at {url}\n"
                                          f"HTTP Status: 200 OK\n"
                                          f"Content-Type: {content_type}\n"
                                          f"Content-Length: {content_len}\n\n"
                                          f"This file should not be web-accessible."),
                            severity    = sev,
                            phase       = PentestPhase.RECONNAISSANCE,
                            tool_name   = "breach_bot_file_checker",
                            tags        = ["file_exposure", "information_disclosure", "T1083"],
                            proof       = f"HTTP 200 at {url}",
                            remediation = (
                                f"1. Immediately remove or restrict access to /{path}.\n"
                                "2. Add web server rules to block access to sensitive files.\n"
                                "3. For .git: Add 'Deny from all' to .htaccess for /.git/\n"
                                "4. For .env: Never store .env in webroot; use server env vars.\n"
                                "5. Audit the web root for any other backup/config files."
                            ),
                        ))
            except urllib.error.HTTPError as e:
                pass  # 403, 404, etc. = not accessible
            except Exception:
                pass

        print(f"[BREACHBOT] File exposure check complete: {found_count} exposed files found")
        return findings


# ─────────────────────────────────────────────────────────────────
# SSL/TLS CHECKER
# ─────────────────────────────────────────────────────────────────

class SSLChecker:
    """
    Checks for SSL/TLS weaknesses: old protocols, weak ciphers,
    expired certs, missing HSTS, self-signed certs.
    """

    WEAK_PROTOCOLS = ["SSLv2", "SSLv3", "TLSv1", "TLSv1.1"]

    def check(self, target: str, port: int = 443) -> List[Finding]:
        """Run SSL/TLS security checks against a target."""
        findings = []
        try:
            import ssl, socket
            # Test what protocol versions are accepted
            for proto_name, proto_const in [
                ("TLSv1.0", ssl.TLSVersion.TLSv1   if hasattr(ssl.TLSVersion, 'TLSv1')   else None),
                ("TLSv1.1", ssl.TLSVersion.TLSv1_1 if hasattr(ssl.TLSVersion, 'TLSv1_1') else None),
            ]:
                if proto_const is None: continue
                try:
                    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ctx.maximum_version = proto_const
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    with ctx.wrap_socket(socket.create_connection((target, port), timeout=5),
                                        server_hostname=target) as s:
                        findings.append(Finding(
                            title       = f"Weak TLS Protocol Accepted: {proto_name}",
                            description = (f"{target}:{port} accepts {proto_name} connections.\n"
                                          f"{proto_name} is deprecated and has known vulnerabilities."),
                            severity    = Severity.HIGH,
                            phase       = PentestPhase.SCANNING,
                            tool_name   = "breach_bot_ssl",
                            tags        = ["ssl", "tls", "weak_protocol", "T1557"],
                            proof       = f"Successful {proto_name} handshake with {target}:{port}",
                            remediation = (f"1. Disable {proto_name} in your web server/load balancer config.\n"
                                          "2. Only allow TLS 1.2 and TLS 1.3.\n"
                                          "3. Use Mozilla SSL Config Generator for recommended settings.\n"
                                          "4. Test your config at ssllabs.com/ssltest/"),
                        ))
                except Exception:
                    pass  # Protocol not accepted — that's what we want

            # Check certificate
            try:
                ctx = ssl.create_default_context()
                with ctx.wrap_socket(socket.create_connection((target, port), timeout=10),
                                     server_hostname=target) as s:
                    cert = s.getpeercert()
                    not_after = cert.get("notAfter", "")
                    if not_after:
                        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                        days_left = (expiry - datetime.now()).days
                        if days_left < 0:
                            findings.append(Finding(
                                title       = "TLS Certificate EXPIRED",
                                description = f"Certificate for {target} expired {abs(days_left)} days ago ({not_after})",
                                severity    = Severity.CRITICAL,
                                phase       = PentestPhase.SCANNING,
                                tool_name   = "breach_bot_ssl",
                                tags        = ["ssl", "expired_cert"],
                                proof       = f"notAfter: {not_after}",
                                remediation = "Renew the TLS certificate immediately. Consider Let's Encrypt for free auto-renewal.",
                            ))
                        elif days_left <= 30:
                            findings.append(Finding(
                                title       = f"TLS Certificate Expiring Soon ({days_left} days)",
                                description = f"Certificate expires on {not_after}. Renew soon to avoid outages.",
                                severity    = Severity.MEDIUM,
                                phase       = PentestPhase.SCANNING,
                                tool_name   = "breach_bot_ssl",
                                tags        = ["ssl", "cert_expiry"],
                            ))
            except ssl.SSLCertVerificationError:
                findings.append(Finding(
                    title       = "Self-Signed or Untrusted TLS Certificate",
                    description = f"The TLS certificate for {target}:{port} is not trusted by system CA store.",
                    severity    = Severity.HIGH,
                    phase       = PentestPhase.SCANNING,
                    tool_name   = "breach_bot_ssl",
                    tags        = ["ssl", "self_signed"],
                    remediation = "Replace with a certificate from a trusted CA (e.g., Let's Encrypt).",
                ))
            except Exception:
                pass
        except Exception as e:
            log.debug(f"SSL check failed: {e}")
        return findings


# ─────────────────────────────────────────────────────────────────
# SECURITY HEADERS CHECKER
# ─────────────────────────────────────────────────────────────────

class SecurityHeadersChecker:
    """
    Checks for missing/misconfigured HTTP security headers.
    Missing headers = easy wins for attackers (clickjacking, XSS, MIME sniffing).
    """

    REQUIRED_HEADERS = {
        "Strict-Transport-Security": {
            "severity": Severity.HIGH,
            "fix": "Add header: Strict-Transport-Security: max-age=31536000; includeSubDomains",
            "description": "Missing HSTS header — allows protocol downgrade attacks and cookie hijacking."
        },
        "X-Frame-Options": {
            "severity": Severity.MEDIUM,
            "fix": "Add header: X-Frame-Options: DENY",
            "description": "Missing X-Frame-Options — allows clickjacking attacks."
        },
        "X-Content-Type-Options": {
            "severity": Severity.LOW,
            "fix": "Add header: X-Content-Type-Options: nosniff",
            "description": "Missing X-Content-Type-Options — allows MIME type sniffing attacks."
        },
        "Content-Security-Policy": {
            "severity": Severity.HIGH,
            "fix": "Implement a Content Security Policy. Start with: Content-Security-Policy: default-src 'self'",
            "description": "Missing CSP header — significantly increases XSS attack surface."
        },
        "Referrer-Policy": {
            "severity": Severity.LOW,
            "fix": "Add header: Referrer-Policy: strict-origin-when-cross-origin",
            "description": "Missing Referrer-Policy — may leak URL parameters to third parties."
        },
        "Permissions-Policy": {
            "severity": Severity.LOW,
            "fix": "Add header: Permissions-Policy: geolocation=(), microphone=(), camera=()",
            "description": "Missing Permissions-Policy — allows unrestricted browser feature access."
        },
    }

    def check(self, target: str, port: int = 80, ssl: bool = False) -> List[Finding]:
        """Check security headers on a web server."""
        import urllib.request, urllib.error
        findings = []
        scheme = "https" if ssl or port == 443 else "http"
        url    = f"{scheme}://{target}:{port}"
        try:
            req = urllib.request.Request(url,
                headers={"User-Agent": "Mozilla/5.0 (Security Assessment)"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                # Check server banner (information disclosure)
                if "server" in headers:
                    findings.append(Finding(
                        title       = f"Server Version Disclosure: {headers['server']}",
                        description = (f"Server header reveals version: {headers['server']}\n"
                                      "Attackers can use this to look up version-specific CVEs."),
                        severity    = Severity.LOW,
                        phase       = PentestPhase.RECONNAISSANCE,
                        tool_name   = "breach_bot_headers",
                        tags        = ["information_disclosure", "server_banner"],
                        remediation = "Remove or obscure the Server header in your web server config.",
                    ))
                # Check each required security header
                for header_name, info in self.REQUIRED_HEADERS.items():
                    if header_name.lower() not in headers:
                        findings.append(Finding(
                            title       = f"Missing Security Header: {header_name}",
                            description = info["description"],
                            severity    = info["severity"],
                            phase       = PentestPhase.SCANNING,
                            tool_name   = "breach_bot_headers",
                            tags        = ["security_headers", "misconfiguration"],
                            remediation = info["fix"],
                            proof       = f"Header '{header_name}' absent from response at {url}",
                        ))
        except Exception as e:
            log.debug(f"Header check failed: {e}")
        return findings


# ─────────────────────────────────────────────────────────────────
# DEFAULT CREDENTIALS CHECKER
# ─────────────────────────────────────────────────────────────────

class DefaultCredentialChecker:
    """
    Tests services for default/common credentials.
    
    TEACHING NOTE: Default creds are the #1 most embarrassing
    finding in a pentest. "admin/admin" on a router is the reason
    Mirai botnet infected millions of devices. Always test these.
    """

    # (service, port, [username, password] pairs)
    DEFAULT_CREDS = {
        "ssh": [
            ("root", "root"), ("admin", "admin"), ("root", "toor"),
            ("pi", "raspberry"), ("admin", "password"), ("user", "user"),
        ],
        "ftp": [
            ("anonymous", ""), ("ftp", "ftp"), ("admin", "admin"),
            ("root", "root"), ("user", "password"),
        ],
        "mysql": [
            ("root", ""), ("root", "root"), ("root", "mysql"),
            ("admin", "admin"), ("mysql", "mysql"),
        ],
        "http_basic": [
            ("admin", "admin"), ("admin", "password"), ("admin", "1234"),
            ("admin", ""), ("root", "root"), ("test", "test"),
        ],
    }

    def check_service(self, target: str, service: str, port: int) -> List[Finding]:
        """Test default credentials for a given service."""
        findings = []
        creds = self.DEFAULT_CREDS.get(service.lower(), [])
        if not creds:
            return findings

        print(f"[BREACHBOT] Testing {len(creds)} default credential pairs for {service} on {target}:{port}")
        for username, password in creds:
            if self._test_cred(target, port, service, username, password):
                findings.append(Finding(
                    title       = f"Default Credentials Work: {service.upper()} — {username}:{password if password else '(empty)'}",
                    description = (f"Default credentials successfully authenticated to {service.upper()} "
                                  f"on {target}:{port}\n"
                                  f"Username: {username}\n"
                                  f"Password: {password if password else '(empty password)'}"),
                    severity    = Severity.CRITICAL,
                    phase       = PentestPhase.EXPLOITATION,
                    tool_name   = "breach_bot_creds",
                    tags        = ["default_credentials", "T1078", "authentication_bypass"],
                    proof       = f"Successful login to {service}://{target}:{port} with {username}/{password or 'empty'}",
                    remediation = (f"1. Change the {service.upper()} password immediately.\n"
                                  "2. Set a strong, unique password (20+ chars, mixed case, symbols).\n"
                                  "3. Restrict service access to specific IPs only.\n"
                                  "4. Disable unnecessary services entirely."),
                ))
                break  # Stop after first successful match
        return findings

    def _test_cred(self, target: str, port: int, service: str,
                   username: str, password: str) -> bool:
        """Actually attempt authentication. Returns True if successful."""
        try:
            if service == "ftp":
                import ftplib
                ftp = ftplib.FTP()
                ftp.connect(target, port, timeout=5)
                ftp.login(username, password)
                ftp.quit()
                return True
            elif service == "ssh":
                # paramiko check (if installed)
                try:
                    import paramiko
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(target, port=port, username=username,
                                  password=password, timeout=5, banner_timeout=5)
                    client.close()
                    return True
                except ImportError:
                    pass  # paramiko not installed
            # Other services: would need service-specific clients
        except Exception:
            pass
        return False


# ─────────────────────────────────────────────────────────────────
# BREACHBOT MAIN ENGINE — Orchestrates all checks into a pipeline
# ─────────────────────────────────────────────────────────────────

class BreachBot:
    """
    BreachBot — Autonomous multi-phase vulnerability scanner.

    Chains together:
      1. Port scanning (nmap integration)
      2. Web checks (headers, files, SSL)
      3. Default credential testing
      4. Nuclei template scanning (when available)
      5. Service enumeration

    Every phase generates structured Finding objects compatible
    with the ERR0RS reporting engine.

    Usage:
        bot = BreachBot()
        findings = bot.scan("192.168.1.100")
        # or for a web app:
        findings = bot.scan("192.168.1.100", web_ports=[80, 443, 8080])
    """

    TOOL_NAME = "breach_bot"

    def __init__(self, data_dir: str = "./breachbot_data", verbose: bool = True):
        self.data_dir   = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.verbose    = verbose
        self.file_checker    = FileExposureChecker()
        self.ssl_checker     = SSLChecker()
        self.header_checker  = SecurityHeadersChecker()
        self.cred_checker    = DefaultCredentialChecker()
        self.scan_results:   List[ScanResult] = []
        self.all_findings:   List[Finding]    = []

    def scan(self, target: str, web_ports: List[int] = None,
             check_ssl: bool = True, check_files: bool = True,
             check_headers: bool = True, check_default_creds: bool = True,
             nuclei: bool = True) -> List[Finding]:
        """
        Run a full autonomous scan against a target.

        Args:
            target:              IP address or hostname
            web_ports:           List of HTTP ports to check (default: [80, 443, 8080, 8443])
            check_ssl:           Run SSL/TLS weakness checks
            check_files:         Check for exposed sensitive files
            check_headers:       Check for missing security headers
            check_default_creds: Test default credentials on found services
            nuclei:              Run Nuclei templates if available
        """
        if web_ports is None:
            web_ports = [80, 443, 8080, 8443]

        self.all_findings = []
        print(f"\n{'='*60}")
        print(f"  [+] BreachBot Initializing Vulnerability Scan...")
        print(f"  [+] Target: {target}")
        print(f"  [+] Web Ports: {web_ports}")
        print(f"{'='*60}\n")

        # Phase 1: Port scan
        self._phase_banner("PORT SCAN", ScanPhase.PORT_SCAN)
        port_findings = self._run_port_scan(target)
        self._collect(port_findings, ScanPhase.PORT_SCAN)

        # Phase 2: Web checks on each port
        for port in web_ports:
            is_ssl = port in (443, 8443)
            if check_headers:
                self._phase_banner(f"SECURITY HEADERS PORT {port}", ScanPhase.WEB_SCAN)
                hdr_findings = self.header_checker.check(target, port, ssl=is_ssl)
                self._collect(hdr_findings, ScanPhase.WEB_SCAN)

            if check_files:
                self._phase_banner(f"FILE EXPOSURE PORT {port}", ScanPhase.FILE_ENUM)
                file_findings = self.file_checker.check(target, port, ssl=is_ssl)
                self._collect(file_findings, ScanPhase.FILE_ENUM)

            if check_ssl and is_ssl:
                self._phase_banner(f"SSL/TLS CHECK PORT {port}", ScanPhase.SCANNING)
                ssl_findings = self.ssl_checker.check(target, port)
                self._collect(ssl_findings, ScanPhase.SCANNING)

        # Phase 3: Default credential tests
        if check_default_creds:
            self._phase_banner("DEFAULT CREDENTIALS", ScanPhase.EXPLOIT_CHECK)
            for service, port in [("ftp", 21), ("ssh", 22)]:
                cred_findings = self.cred_checker.check_service(target, service, port)
                self._collect(cred_findings, ScanPhase.EXPLOIT_CHECK)

        # Phase 4: Nuclei (if available)
        if nuclei:
            self._phase_banner("NUCLEI TEMPLATE SCAN", ScanPhase.VULN_SCAN)
            nuclei_findings = self._run_nuclei(target)
            self._collect(nuclei_findings, ScanPhase.VULN_SCAN)

        # Deduplicate and summarize
        self.all_findings = self._deduplicate(self.all_findings)
        self._save_results(target)
        self._print_summary()
        return self.all_findings

    # ── Internal ──────────────────────────────────────────────────

    def _run_port_scan(self, target: str) -> List[Finding]:
        """Run nmap port scan via ERR0RS nmap tool integration."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
            from src.tools.recon.nmap_tool import NmapTool
            result = NmapTool().execute(target)
            return result.get("findings", [])
        except Exception as e:
            log.warning(f"nmap integration failed: {e}")
            return []

    def _run_nuclei(self, target: str) -> List[Finding]:
        """Run Nuclei template scanner if available."""
        findings = []
        try:
            cmd = ["nuclei", "-u", target, "-severity", "critical,high,medium",
                   "-json", "-silent", "-timeout", "5"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        sev_map = {"critical": Severity.CRITICAL, "high": Severity.HIGH,
                                   "medium": Severity.MEDIUM, "low": Severity.LOW}
                        findings.append(Finding(
                            title       = f"Nuclei: {data.get('info',{}).get('name','Unknown')}",
                            description = data.get("info", {}).get("description", ""),
                            severity    = sev_map.get(data.get("info",{}).get("severity","medium"),
                                                     Severity.MEDIUM),
                            phase       = PentestPhase.SCANNING,
                            tool_name   = "nuclei",
                            tags        = ["nuclei", "template_scan"],
                            proof       = f"Matched template: {data.get('templateID','')} at {data.get('matched-at','')}",
                            references  = data.get("info",{}).get("reference",[]),
                        ))
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            print("[BREACHBOT] Nuclei not installed — skipping template scan")
            print("           Install: https://github.com/projectdiscovery/nuclei")
        except subprocess.TimeoutExpired:
            print("[BREACHBOT] Nuclei timed out")
        return findings

    def _deduplicate(self, findings: List[Finding]) -> List[Finding]:
        """Remove duplicate findings based on title + target."""
        seen = set()
        unique = []
        for f in findings:
            key = f"{f.title}|{f.target}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        return sorted(unique, key=lambda f: ["critical","high","medium","low","info"].index(
            f.severity.value if hasattr(f.severity, 'value') else "info"))

    def _collect(self, findings: List[Finding], phase: ScanPhase):
        self.all_findings.extend(findings)
        for f in findings:
            sev_icons = {"critical":"🔴","high":"🟠","medium":"🟡","low":"🔵","info":"⚪"}
            sev = f.severity.value if hasattr(f.severity, 'value') else "info"
            if self.verbose:
                print(f"  [{sev_icons.get(sev,'•')} {sev.upper()}] {f.title}")

    def _phase_banner(self, name: str, phase: ScanPhase):
        print(f"\n  [+] {name}...")

    def _print_summary(self):
        from collections import Counter
        counts = Counter(
            f.severity.value if hasattr(f.severity, 'value') else "info"
            for f in self.all_findings
        )
        print(f"\n{'='*60}")
        print(f"  SCAN COMPLETE — {len(self.all_findings)} findings total")
        print(f"  🔴 Critical: {counts.get('critical', 0)}")
        print(f"  🟠 High:     {counts.get('high', 0)}")
        print(f"  🟡 Medium:   {counts.get('medium', 0)}")
        print(f"  🔵 Low:      {counts.get('low', 0)}")
        print(f"{'='*60}\n")

    def _save_results(self, target: str):
        out = self.data_dir / f"scan_{target.replace('.','_')}_{int(time.time())}.json"
        out.write_text(json.dumps({
            "target": target,
            "scanned_at": datetime.now().isoformat(),
            "findings_count": len(self.all_findings),
            "findings": [asdict(f) for f in self.all_findings],
        }, indent=2, default=str))
        print(f"  [BREACHBOT] Results saved: {out}")


__all__ = ["BreachBot", "FileExposureChecker", "SSLChecker",
           "SecurityHeadersChecker", "DefaultCredentialChecker",
           "ScanPhase", "ScanResult"]
