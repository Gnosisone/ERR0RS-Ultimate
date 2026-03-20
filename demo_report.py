#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Demo Report Generator
==========================================
Run this ANYWHERE — no Kali needed, no targets, no network.
It generates a FULL professional pentest report using realistic
mock data so you can see exactly what ERR0RS produces.

Usage:
    python3 demo_report.py

Output:
    ERR0RS_Demo_Report.html  — Open in any browser. Print-ready.

TEACHING NOTE:
--------------
This is your portfolio piece. Show this to anyone who wants to
see what ERR0RS can do. Every section, every finding, every
education block — all real. The only fake thing is the targets.
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.models import (
    Finding, ScanResult, EngagementSession, ReportConfig,
    Severity, PentestPhase, ToolStatus
)
from reporting.html_reporter import HTMLReportEngine
from education.knowledge_base import get_education


def build_demo_session() -> EngagementSession:
    """
    Build a realistic engagement session with findings across
    all severity levels, multiple tools, and multiple phases.
    This is what a real pentest engagement looks like.
    """

    # ---------------------------------------------------------------
    # PHASE 1: RECONNAISSANCE — Nmap findings
    # ---------------------------------------------------------------
    nmap_findings = [
        Finding(
            title="Open Port 22/tcp — SSH (OpenSSH 7.9)",
            description="SSH service is running on port 22. Version 7.9 detected.\n"
                        "OpenSSH 7.9 has known vulnerabilities (CVE-2018-15473).\n"
                        "This port is a common brute-force target.",
            severity=Severity.MEDIUM,
            phase=PentestPhase.RECONNAISSANCE,
            target="192.168.10.50",
            tool_name="nmap",
            tags=["ssh", "remote_access", "outdated_software"],
            proof="22/tcp open ssh OpenSSH 7.9p1 Debian-5+deb10u3",
            remediation="1. Update OpenSSH to latest version\n"
                        "2. Disable password authentication (PasswordAuthentication no)\n"
                        "3. Restrict SSH to specific IPs via AllowUsers\n"
                        "4. Deploy Fail2Ban for brute-force protection",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2018-15473"],
            confidence=0.99,
            education=get_education("port_scanning").to_html_block() if get_education("port_scanning") else "",
        ),
        Finding(
            title="Open Port 80/tcp — Apache HTTP Server 2.4.38",
            description="Apache web server running on port 80.\n"
                        "Version 2.4.38 is below current release.\n"
                        "Web application requires further testing.",
            severity=Severity.INFO,
            phase=PentestPhase.RECONNAISSANCE,
            target="192.168.10.50",
            tool_name="nmap",
            tags=["http", "web", "apache"],
            proof="80/tcp open http Apache httpd 2.4.38 ((Debian))",
            remediation="1. Update Apache to latest stable version\n"
                        "2. Disable unnecessary modules\n"
                        "3. Remove server version from response headers",
            confidence=0.99,
        ),
        Finding(
            title="Open Port 3306/tcp — MySQL 5.7.44",
            description="MySQL database server exposed on the network.\n"
                        "Database services should NEVER be directly accessible.\n"
                        "This is a critical misconfiguration.",
            severity=Severity.HIGH,
            phase=PentestPhase.RECONNAISSANCE,
            target="192.168.10.50",
            tool_name="nmap",
            tags=["mysql", "database", "exposed_service"],
            proof="3306/tcp open mysql MySQL 5.7.44-0ubuntu0.18.04.3",
            remediation="1. Bind MySQL to localhost only (bind-address = 127.0.0.1)\n"
                        "2. Block port 3306 at the network firewall\n"
                        "3. Use application-level database proxies\n"
                        "4. Restrict database accounts by source IP",
            references=["https://dev.mysql.com/doc/refman/8.0/en/server-system-variables.html"],
            confidence=0.99,
        ),
        Finding(
            title="Open Port 23/tcp — Telnet Service",
            description="Telnet service is running. Telnet transmits ALL data\n"
                        "including passwords in PLAIN TEXT. This is a critical\n"
                        "security violation on any production system.",
            severity=Severity.HIGH,
            phase=PentestPhase.RECONNAISSANCE,
            target="192.168.10.50",
            tool_name="nmap",
            tags=["telnet", "unencrypted", "legacy_protocol"],
            proof="23/tcp open telnet Linux telnetd",
            remediation="1. DISABLE Telnet service immediately\n"
                        "2. Replace with SSH (encrypted equivalent)\n"
                        "3. Block port 23 at all firewalls\n"
                        "4. Audit logs for any Telnet usage",
            confidence=0.99,
        ),
    ]

    # ---------------------------------------------------------------
    # PHASE 2: WEB SCANNING — Gobuster + Nikto findings
    # ---------------------------------------------------------------
    gobuster_findings = [
        Finding(
            title="Exposed Admin Panel — /admin (HTTP 200)",
            description="Administrator control panel is publicly accessible.\n"
                        "No authentication prompt detected on initial access.\n"
                        "This is a critical attack surface.",
            severity=Severity.HIGH,
            phase=PentestPhase.SCANNING,
            target="http://192.168.10.50/admin",
            tool_name="gobuster",
            tags=["admin_access", "directory_busting", "high_value_path"],
            proof="/admin (Status: 200) [Size: 4821]",
            remediation="1. Restrict /admin to internal IPs only\n"
                        "2. Implement multi-factor authentication\n"
                        "3. Rate-limit login attempts\n"
                        "4. Monitor access logs for this path",
            education=get_education("directory_busting").to_html_block() if get_education("directory_busting") else "",
            confidence=0.95,
        ),
        Finding(
            title="Exposed .env Configuration File — /.env (HTTP 200)",
            description=".env files contain environment variables — secrets,\n"
                        "API keys, database passwords. This file being publicly\n"
                        "accessible is a CRITICAL data exposure.",
            severity=Severity.HIGH,
            phase=PentestPhase.SCANNING,
            target="http://192.168.10.50/.env",
            tool_name="gobuster",
            tags=["file_exposure", "secrets", "high_value_path"],
            proof="/.env (Status: 200) [Size: 312]",
            remediation="1. Remove .env from web root IMMEDIATELY\n"
                        "2. Add .env to .gitignore\n"
                        "3. Block .env access in web server config\n"
                        "4. Rotate ALL credentials that may have been in the file",
            confidence=0.99,
        ),
        Finding(
            title="API Endpoint Discovered — /api/v1 (HTTP 200)",
            description="API endpoint found. Requires further testing for\n"
                        "authentication, authorization, and input validation.",
            severity=Severity.INFO,
            phase=PentestPhase.SCANNING,
            target="http://192.168.10.50/api/v1",
            tool_name="gobuster",
            tags=["api", "web"],
            proof="/api/v1 (Status: 200) [Size: 1024]",
            remediation="1. Verify API requires authentication on all endpoints\n"
                        "2. Implement rate limiting\n"
                        "3. Test for IDOR and parameter tampering",
            confidence=0.90,
        ),
    ]

    nikto_findings = [
        Finding(
            title="Nikto: Server Version Disclosure",
            description="The server reveals its exact version in HTTP response headers.\n"
                        "Attackers use version info to target known CVEs.",
            severity=Severity.LOW,
            phase=PentestPhase.SCANNING,
            target="192.168.10.50:80",
            tool_name="nikto",
            tags=["information_disclosure", "security_headers", "nikto"],
            proof="Server: Apache/2.4.38 (Debian) — disclosed in response header",
            remediation="1. Set ServerTokens Prod in Apache config\n"
                        "2. Set ServerSignature Off\n"
                        "3. Add X-Powered-By header removal",
            confidence=0.85,
        ),
        Finding(
            title="Nikto: Default phpMyAdmin Accessible",
            description="phpMyAdmin is accessible at the default path.\n"
                        "Database admin tool exposed to network — critical risk.",
            severity=Severity.HIGH,
            phase=PentestPhase.SCANNING,
            target="192.168.10.50:80",
            tool_name="nikto",
            tags=["phpmyadmin", "database", "default_path", "nikto"],
            proof="/phpmyadmin/ (Status: 200) [Size: 8192]",
            remediation="1. Move phpMyAdmin to a non-default path\n"
                        "2. Restrict access to localhost or VPN only\n"
                        "3. Implement IP whitelisting\n"
                        "4. Enable two-factor authentication",
            confidence=0.90,
        ),
    ]

    # ---------------------------------------------------------------
    # PHASE 3: EXPLOITATION — SQLMap + Hydra findings
    # ---------------------------------------------------------------
    sqlmap_findings = [
        Finding(
            title="SQL Injection — UNION-Based on /login (user parameter)",
            description="Confirmed SQL injection vulnerability on the login form.\n"
                        "The 'user' parameter is injectable via UNION-based technique.\n"
                        "Full database read access is achievable.\n\n"
                        "This is the most critical finding of this engagement.",
            severity=Severity.CRITICAL,
            phase=PentestPhase.EXPLOITATION,
            target="http://192.168.10.50/login",
            tool_name="sqlmap",
            tags=["sql_injection", "owasp_a03", "critical"],
            proof="Parameter 'user' is vulnerable\n"
                  "Technique: UNION-based\n"
                  "Payload: user=1 UNION SELECT NULL,NULL,NULL--\n"
                  "Result: Database version extracted successfully",
            remediation="1. Use parameterized queries (prepared statements) EVERYWHERE\n"
                        "2. Implement input validation and sanitization\n"
                        "3. Use least-privilege database accounts\n"
                        "4. Deploy a Web Application Firewall (WAF)\n"
                        "5. Conduct full code review of all database queries",
            references=[
                "https://owasp.org/Top10/A03_2021-Injection/",
                "https://portswigger.net/web-security/sql-injection",
            ],
            education=get_education("sql_injection").to_html_block() if get_education("sql_injection") else "",
            confidence=1.0,
        ),
    ]

    hydra_findings = [
        Finding(
            title="Credential Cracked — SSH root:shadow123",
            description="Hydra successfully brute-forced the SSH service.\n"
                        "Root account compromised with a weak password.\n"
                        "This grants full system access to an attacker.",
            severity=Severity.CRITICAL,
            phase=PentestPhase.EXPLOITATION,
            target="192.168.10.50",
            tool_name="hydra",
            tags=["brute_force", "credential_cracked", "ssh", "root"],
            proof="[22][ssh] host: 192.168.10.50  login: root  password: shadow123",
            remediation="1. Change password IMMEDIATELY\n"
                        "2. Disable root SSH login (PermitRootLogin no)\n"
                        "3. Implement MFA on all SSH access\n"
                        "4. Deploy account lockout after 5 failed attempts\n"
                        "5. Enforce password policy: 16+ chars, complexity required\n"
                        "6. Deploy Fail2Ban",
            references=["https://attack.mitre.org/techniques/T1110/"],
            education=get_education("brute_force").to_html_block() if get_education("brute_force") else "",
            confidence=1.0,
        ),
        Finding(
            title="Credential Cracked — MySQL admin:admin",
            description="MySQL admin account has default credentials.\n"
                        "Immediate database compromise is possible.",
            severity=Severity.CRITICAL,
            phase=PentestPhase.EXPLOITATION,
            target="192.168.10.50",
            tool_name="hydra",
            tags=["brute_force", "credential_cracked", "mysql", "default_creds"],
            proof="[3306][mysql] host: 192.168.10.50  login: admin  password: admin",
            remediation="1. Change ALL database passwords immediately\n"
                        "2. Rename or disable admin account\n"
                        "3. Bind MySQL to localhost\n"
                        "4. Use strong, randomly generated passwords",
            confidence=1.0,
        ),
    ]

    metasploit_findings = [
        Finding(
            title="MSF Enum: SMBv1 Protocol Detected (EternalBlue Risk)",
            description="SMB Version 1 is enabled on the target.\n"
                        "SMBv1 is vulnerable to EternalBlue (MS17-010) —\n"
                        "the exploit used in the WannaCry ransomware attack.",
            severity=Severity.HIGH,
            phase=PentestPhase.SCANNING,
            target="192.168.10.50",
            tool_name="metasploit",
            tags=["smb", "smbv1", "legacy_protocol", "eternalblue"],
            proof="[+] 192.168.10.50:445 - SMBv1 detected (Windows/Samba)",
            remediation="1. Disable SMBv1 at system level\n"
                        "2. Apply MS17-010 patch immediately\n"
                        "3. Block port 445 at the network firewall\n"
                        "4. Migrate to SMBv3 only",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2017-0144"],
            confidence=0.90,
        ),
    ]

    # ---------------------------------------------------------------
    # PHASE 4: POST-EXPLOITATION (simulated finding)
    # ---------------------------------------------------------------
    postex_findings = [
        Finding(
            title="Sensitive Data Found — /etc/shadow Readable",
            description="After gaining SSH access as root, /etc/shadow\n"
                        "was confirmed readable. All system password hashes\n"
                        "are now in attacker possession.",
            severity=Severity.CRITICAL,
            phase=PentestPhase.POST_EXPLOITATION,
            target="192.168.10.50",
            tool_name="manual_review",
            tags=["post_exploitation", "password_hashes", "data_exfil"],
            proof="$ cat /etc/shadow\n"
                  "root:$6$rounds=5000$saltsalt$hash...:18000:0:99999:7:::\n"
                  "admin:$6$rounds=5000$saltsalt$hash...:18001:0:99999:7:::",
            remediation="1. All user passwords must be reset\n"
                        "2. Consider full system rebuild\n"
                        "3. Implement file integrity monitoring (FIM)\n"
                        "4. Review root access privileges",
            education=get_education("privilege_escalation").to_html_block() if get_education("privilege_escalation") else "",
            confidence=1.0,
        ),
    ]

    # ---------------------------------------------------------------
    # ASSEMBLE THE FULL ENGAGEMENT SESSION
    # ---------------------------------------------------------------
    session = EngagementSession(
        name="Comprehensive Security Assessment — Demo",
        client_name="Acme Corp",
        tester_name="Gary Holden Schneider",
        targets=["192.168.10.50", "192.168.10.51"],
        scope_notes=(
            "Full-scope internal network assessment. All services on targets "
            "are in scope. Web application testing, credential attacks, and "
            "post-exploitation enumeration authorized. No data exfiltration. "
            "Rules of engagement signed 2025-01-15."
        ),
        status="completed",
    )

    # Attach scan results in order of the attack chain
    session.scan_results = [
        ScanResult(
            tool_name="nmap", status=ToolStatus.SUCCESS,
            phase=PentestPhase.RECONNAISSANCE,
            target="192.168.10.50", findings=nmap_findings,
            duration=18.4,
            command="nmap -sV -sC --open -T4 -oX - 192.168.10.50",
        ),
        ScanResult(
            tool_name="gobuster", status=ToolStatus.SUCCESS,
            phase=PentestPhase.SCANNING,
            target="http://192.168.10.50", findings=gobuster_findings,
            duration=42.1,
            command="gobuster dir -u http://192.168.10.50 -w /usr/share/wordlists/dirb/common.txt -t 50 -q",
        ),
        ScanResult(
            tool_name="nikto", status=ToolStatus.SUCCESS,
            phase=PentestPhase.SCANNING,
            target="192.168.10.50:80", findings=nikto_findings,
            duration=67.3,
            command="nikto -h 192.168.10.50 -p 80 -format csv -output -",
        ),
        ScanResult(
            tool_name="sqlmap", status=ToolStatus.SUCCESS,
            phase=PentestPhase.EXPLOITATION,
            target="http://192.168.10.50/login", findings=sqlmap_findings,
            duration=123.8,
            command="sqlmap -u http://192.168.10.50/login?user=1 --level=3 --risk=2 --batch --dbs -q",
        ),
        ScanResult(
            tool_name="hydra", status=ToolStatus.SUCCESS,
            phase=PentestPhase.EXPLOITATION,
            target="192.168.10.50", findings=hydra_findings,
            duration=89.2,
            command="hydra -t 16 -e nsr -L users.txt -P /usr/share/wordlists/rockyou.txt 192.168.10.50 ssh",
        ),
        ScanResult(
            tool_name="metasploit", status=ToolStatus.SUCCESS,
            phase=PentestPhase.SCANNING,
            target="192.168.10.50", findings=metasploit_findings,
            duration=34.6,
            command="msfconsole -q -r smb_scan.rc",
        ),
        ScanResult(
            tool_name="manual_review", status=ToolStatus.SUCCESS,
            phase=PentestPhase.POST_EXPLOITATION,
            target="192.168.10.50", findings=postex_findings,
            duration=15.0,
            command="ssh root@192.168.10.50 → cat /etc/shadow",
        ),
    ]

    return session


# =============================================================================
# MAIN — GENERATE THE REPORT
# =============================================================================

def main():
    print("=" * 60)
    print("  ERR0RS ULTIMATE — Demo Report Generator")
    print("=" * 60)
    print()
    print("[*] Building engagement session with mock data...")

    session = build_demo_session()

    # Print session summary
    summary = session.finding_summary
    total = sum(summary.values())
    print(f"[+] Session: {session.name}")
    print(f"[+] Client:  {session.client_name}")
    print(f"[+] Tester:  {session.tester_name}")
    print(f"[+] Targets: {', '.join(session.targets)}")
    print(f"[+] Total Findings: {total}")
    print(f"    Critical: {summary['Critical']}  |  High: {summary['High']}  "
          f"|  Medium: {summary['Medium']}  |  Low: {summary['Low']}  |  Info: {summary['Info']}")
    print()

    # Configure the report — enable EVERYTHING
    config = ReportConfig(
        format="html",
        include_executive=True,
        include_technical=True,
        include_education=True,
        include_remediation=True,
        include_raw_output=True,
        include_timeline=True,
        company_name="ERR0RS ULTIMATE",
    )

    print("[*] Generating full HTML report...")
    engine = HTMLReportEngine(config)
    html = engine.generate(session)

    # Write output
    output_path = os.path.join(os.path.dirname(__file__), "ERR0RS_Demo_Report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[+] Report written to: {output_path}")
    print(f"[+] File size: {len(html):,} bytes")
    print()
    print("[+] Open ERR0RS_Demo_Report.html in any web browser.")
    print("[+] The report is fully self-contained — no internet needed.")
    print()
    print("=" * 60)
    print("  Done. Enjoy the masterwork.")
    print("=" * 60)


if __name__ == "__main__":
    main()
