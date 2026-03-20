#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Blue Team Toolkit v1.0
Three core defensive/analytical functions baked into the framework:

  auto_harden(finding)      → firewall remediation command from a Blue Team finding
  generate_report(hours)    → PDF Security Audit from ChromaDB session data
  pcap_interpreter(iface)   → Scapy packet sniffer + AI exfil detection via Ollama/NPU

All functions are:
  - 100% local — no data leaves the OS
  - Gracefully degraded (work without optional deps)
  - Wired into the existing ERR0RS architecture
  - Pi 5 / Hailo-10H hook points documented

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import re
import json
import time
import logging
import threading
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger("errors.blue_team")

ROOT_DIR = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT_DIR / "output" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════
# PART 1 — auto_harden()
# Takes a Blue Team finding (open port, weak header, exposed service) and
# produces the exact remediation command (ufw / iptables / sysctl / etc.)
# ═══════════════════════════════════════════════════════════════════════════

# ── Harden rule database ──────────────────────────────────────────────────
# Maps finding keywords → (ufw_cmd, iptables_cmd, notes, severity, cis_ref)
_HARDEN_RULES = [

    # ── Open ports → block or restrict ────────────────────────────────────
    {
        "keywords":  ["port 21", "ftp", "ftp open", "ftp service"],
        "title":     "FTP service exposed",
        "severity":  "HIGH",
        "ufw":       "ufw deny 21/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 21 -j DROP",
        "sysctl":    None,
        "note":      "FTP transmits credentials in cleartext. Disable unless required; use SFTP instead.",
        "cis":       "CIS Control 4.4 — Restrict unnecessary services",
        "mitre":     "T1021.002",
    },
    {
        "keywords":  ["port 23", "telnet", "telnet open", "telnet service"],
        "title":     "Telnet service exposed",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 23/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 23 -j DROP",
        "sysctl":    None,
        "note":      "Telnet sends ALL data including passwords in cleartext. Disable immediately.",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1021.004",
    },
    {
        "keywords":  ["port 25", "smtp", "smtp open", "mail server exposed"],
        "title":     "SMTP relay exposed",
        "severity":  "HIGH",
        "ufw":       "ufw deny in 25/tcp && ufw allow from 127.0.0.1 to any port 25",
        "iptables":  "iptables -A INPUT -p tcp --dport 25 ! -s 127.0.0.1 -j DROP",
        "sysctl":    None,
        "note":      "Restrict SMTP to localhost unless this is a mail server. Open relay = spam/abuse vector.",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1071.003",
    },
    {
        "keywords":  ["port 22", "ssh", "ssh brute", "ssh exposed", "ssh accessible"],
        "title":     "SSH exposed to internet",
        "severity":  "MEDIUM",
        "ufw":       "ufw limit 22/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set\niptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 -j DROP",
        "sysctl":    None,
        "note":      "Rate-limit SSH. Disable password auth: set 'PasswordAuthentication no' in /etc/ssh/sshd_config. Use key-based auth only.",
        "cis":       "CIS Control 4.1",
        "mitre":     "T1110",
    },
    {
        "keywords":  ["port 3306", "mysql", "mysql exposed", "mysql open", "database exposed"],
        "title":     "MySQL database port exposed",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 3306/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 3306 -j DROP",
        "sysctl":    None,
        "note":      "Database ports must NEVER be internet-facing. Bind MySQL to 127.0.0.1: set bind-address=127.0.0.1 in /etc/mysql/mysql.conf.d/mysqld.cnf",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1190",
    },
    {
        "keywords":  ["port 5432", "postgresql", "postgres exposed", "postgres open"],
        "title":     "PostgreSQL port exposed",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 5432/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 5432 -j DROP",
        "sysctl":    None,
        "note":      "PostgreSQL should never be internet-facing. Edit pg_hba.conf to restrict to localhost.",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1190",
    },
    {
        "keywords":  ["port 6379", "redis", "redis exposed", "redis open", "redis no auth"],
        "title":     "Redis exposed without authentication",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 6379/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 6379 -j DROP",
        "sysctl":    None,
        "note":      "Unauthenticated Redis = full RCE via config write. Block port AND set requirepass in /etc/redis/redis.conf",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1190",
    },
    {
        "keywords":  ["port 27017", "mongodb", "mongodb exposed", "mongo open"],
        "title":     "MongoDB port exposed without auth",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 27017/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 27017 -j DROP",
        "sysctl":    None,
        "note":      "Enable MongoDB auth: mongod --auth. Bind to 127.0.0.1 with --bind_ip 127.0.0.1",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1190",
    },
    {
        "keywords":  ["port 3389", "rdp", "rdp exposed", "remote desktop"],
        "title":     "RDP exposed to internet",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 3389/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 3389 -j DROP",
        "sysctl":    None,
        "note":      "RDP should never be internet-facing. Use VPN + RDP internally. BlueKeep (CVE-2019-0708) is still active.",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1210",
    },
    {
        "keywords":  ["port 445", "smb", "smb exposed", "samba exposed", "eternalblue"],
        "title":     "SMB/Samba port exposed to internet",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 445/tcp && ufw deny 139/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 445 -j DROP\niptables -A INPUT -p tcp --dport 139 -j DROP",
        "sysctl":    None,
        "note":      "SMB must NEVER face the internet. EternalBlue (MS17-010) still pwns unpatched hosts. Block externally.",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1210",
    },

    # ── HTTP security headers missing ─────────────────────────────────────
    {
        "keywords":  ["x-frame-options missing", "clickjacking", "no x-frame-options",
                      "x-frame-options header missing", "missing x-frame-options",
                      "x-frame", "clickjack"],
        "title":     "Clickjacking protection missing",
        "severity":  "MEDIUM",
        "ufw":       None,
        "iptables":  None,
        "nginx":     'add_header X-Frame-Options "SAMEORIGIN" always;',
        "apache":    'Header always set X-Frame-Options "SAMEORIGIN"',
        "note":      "Add X-Frame-Options: SAMEORIGIN to web server config to prevent iframe embedding.",
        "cis":       "CIS Control 16.10",
        "mitre":     "T1185",
    },
    {
        "keywords":  ["content-security-policy missing", "csp missing", "no csp header",
                      "content-security-policy header absent", "content-security-policy header missing",
                      "csp absent", "csp header", "content security policy"],
        "title":     "Content Security Policy (CSP) missing",
        "severity":  "HIGH",
        "ufw":       None,
        "iptables":  None,
        "nginx":     "add_header Content-Security-Policy \"default-src 'self'; script-src 'self'; object-src 'none';\" always;",
        "apache":    "Header always set Content-Security-Policy \"default-src 'self'; script-src 'self'; object-src 'none';\"",
        "note":      "CSP is the strongest XSS defense. Start with default-src 'self' and tune from there.",
        "cis":       "CIS Control 16.10",
        "mitre":     "T1059.007",
    },
    {
        "keywords":  ["hsts missing", "strict-transport-security missing", "no hsts",
                      "hsts not configured", "strict-transport-security header missing",
                      "hsts absent", "http strict transport", "strict transport security"],
        "title":     "HTTP Strict Transport Security (HSTS) missing",
        "severity":  "HIGH",
        "ufw":       None,
        "iptables":  None,
        "nginx":     'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;',
        "apache":    'Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"',
        "note":      "HSTS forces HTTPS for the entire domain. Required to prevent SSL stripping attacks.",
        "cis":       "CIS Control 9.3",
        "mitre":     "T1557.002",
    },

    # ── System hardening ──────────────────────────────────────────────────
    {
        "keywords":  ["ip forwarding", "ip_forward enabled", "routing enabled"],
        "title":     "IP forwarding enabled (routing)",
        "severity":  "MEDIUM",
        "ufw":       None,
        "iptables":  None,
        "sysctl":    "sysctl -w net.ipv4.ip_forward=0 && echo 'net.ipv4.ip_forward=0' >> /etc/sysctl.conf && sysctl -p",
        "note":      "Disable IP forwarding unless this host is intentionally a router.",
        "cis":       "CIS Control 4.1 — Disable IP Forwarding",
        "mitre":     "T1599",
    },
    {
        "keywords":  ["icmp redirect", "send redirects", "accept redirects"],
        "title":     "ICMP redirects enabled",
        "severity":  "MEDIUM",
        "ufw":       None,
        "iptables":  None,
        "sysctl":    "sysctl -w net.ipv4.conf.all.send_redirects=0\nsysctl -w net.ipv4.conf.all.accept_redirects=0\necho 'net.ipv4.conf.all.send_redirects=0' >> /etc/sysctl.conf\necho 'net.ipv4.conf.all.accept_redirects=0' >> /etc/sysctl.conf\nsysctl -p",
        "note":      "ICMP redirects can be used to poison routing tables (MITM). Disable both send and accept.",
        "cis":       "CIS Control 4.1",
        "mitre":     "T1557",
    },
    {
        "keywords":  ["syn flood", "syn cookies", "tcp syncookies"],
        "title":     "TCP SYN flood protection disabled",
        "severity":  "MEDIUM",
        "ufw":       None,
        "iptables":  None,
        "sysctl":    "sysctl -w net.ipv4.tcp_syncookies=1 && echo 'net.ipv4.tcp_syncookies=1' >> /etc/sysctl.conf && sysctl -p",
        "note":      "SYN cookies mitigate SYN flood DoS attacks. Should be enabled on all Linux servers.",
        "cis":       "CIS Control 4.1",
        "mitre":     "T1499",
    },
    {
        "keywords":  ["failed login", "brute force", "ssh brute", "auth failure", "multiple failed"],
        "title":     "Brute force activity detected — no rate limiting",
        "severity":  "HIGH",
        "ufw":       "ufw limit ssh",
        "iptables":  "iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set --name SSH\niptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 6 --name SSH -j DROP",
        "sysctl":    None,
        "note":      "Also install fail2ban: apt install fail2ban && systemctl enable fail2ban && systemctl start fail2ban",
        "cis":       "CIS Control 4.2",
        "mitre":     "T1110",
    },

    # ── Service exposure / misconfig ──────────────────────────────────────
    {
        "keywords":  ["port 9200", "elasticsearch", "elastic exposed", "kibana exposed"],
        "title":     "Elasticsearch/Kibana port exposed",
        "severity":  "CRITICAL",
        "ufw":       "ufw deny 9200/tcp && ufw deny 9300/tcp && ufw deny 5601/tcp",
        "iptables":  "iptables -A INPUT -p tcp --dport 9200 -j DROP\niptables -A INPUT -p tcp --dport 9300 -j DROP",
        "sysctl":    None,
        "note":      "Elasticsearch has no auth by default. Bind to localhost: network.host: 127.0.0.1 in elasticsearch.yml",
        "cis":       "CIS Control 4.4",
        "mitre":     "T1190",
    },
    {
        "keywords":  ["directory listing", "directory traversal", "directory index"],
        "title":     "Web server directory listing enabled",
        "severity":  "MEDIUM",
        "ufw":       None,
        "iptables":  None,
        "nginx":     "autoindex off;  # Add to server{} or location{} block",
        "apache":    "Options -Indexes  # Add to <Directory> block in virtual host config",
        "note":      "Directory listing exposes source code, configs, and backup files. Disable it.",
        "cis":       "CIS Control 9.1",
        "mitre":     "T1083",
    },
]


def auto_harden(finding: str, prefer_ufw: bool = True) -> dict:
    """
    Takes a Blue Team finding string and returns the exact remediation command.

    Wired to: SOC triggers in errorz_launcher.py, surface_monitor.py alerts,
              and the /api/soc endpoint for the dashboard.

    Args:
        finding:     Plain text description of the finding
                     e.g. "port 3306 open", "brute force on SSH detected",
                          "X-Frame-Options header missing", "Redis exposed"
        prefer_ufw:  True → return ufw command (Kali/Ubuntu default)
                     False → return iptables command (universal)

    Returns:
        {
          "status":    "ok" | "no_rule",
          "title":     Human-readable finding name,
          "severity":  "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
          "command":   The exact command to run (ufw/iptables/sysctl/nginx/apache),
          "note":      Why this matters + extra hardening tips,
          "cis":       CIS Benchmark reference,
          "mitre":     MITRE ATT&CK technique ID,
          "all_commands": dict of all available remediation variants,
        }

    Examples:
        auto_harden("port 3306 open on internet-facing host")
        auto_harden("brute force attempts on SSH detected")
        auto_harden("X-Frame-Options header missing")
    """
    lower = finding.lower()

    # Score each rule by keyword match count (longer/more specific = higher score)
    best_rule  = None
    best_score = 0

    for rule in _HARDEN_RULES:
        score = 0
        for kw in rule["keywords"]:
            if kw in lower:
                score += len(kw)
        if score > best_score:
            best_score = score
            best_rule  = rule

    if not best_rule:
        # Try a broader port number extraction
        port_match = re.search(r'port\s+(\d+)', lower)
        if port_match:
            port_num = port_match.group(1)
            cmd = (
                f"ufw deny {port_num}/tcp"
                if prefer_ufw else
                f"iptables -A INPUT -p tcp --dport {port_num} -j DROP"
            )
            return {
                "status":   "generic_port",
                "title":    f"Port {port_num} open",
                "severity": "MEDIUM",
                "command":  cmd,
                "note":     f"Generic block for port {port_num}. Review whether this service is required.",
                "cis":      "CIS Control 4.4 — Restrict unnecessary services",
                "mitre":    "T1046",
                "all_commands": {
                    "ufw":      f"ufw deny {port_num}/tcp",
                    "iptables": f"iptables -A INPUT -p tcp --dport {port_num} -j DROP",
                },
            }
        return {
            "status":   "no_rule",
            "title":    "No hardening rule matched",
            "severity": "INFO",
            "command":  None,
            "note":     f"No specific rule for: '{finding}'. Run 'ufw status verbose' to review current firewall state.",
            "cis":      None,
            "mitre":    None,
            "all_commands": {},
        }

    # Build command priority: ufw > iptables > sysctl > nginx > apache
    all_cmds = {}
    for key in ("ufw", "iptables", "sysctl", "nginx", "apache"):
        val = best_rule.get(key)
        if val:
            all_cmds[key] = val

    if prefer_ufw:
        priority = ["ufw", "iptables", "sysctl", "nginx", "apache"]
    else:
        priority = ["iptables", "ufw", "sysctl", "nginx", "apache"]

    primary_cmd = None
    for p in priority:
        if best_rule.get(p):
            primary_cmd = best_rule[p]
            break

    return {
        "status":       "ok",
        "title":        best_rule["title"],
        "severity":     best_rule["severity"],
        "command":      primary_cmd,
        "note":         best_rule["note"],
        "cis":          best_rule["cis"],
        "mitre":        best_rule["mitre"],
        "all_commands": all_cmds,
    }


def auto_harden_batch(findings: list, prefer_ufw: bool = True) -> list:
    """
    Run auto_harden() across a list of findings.
    Returns list of remediation dicts, sorted by severity.

    Args:
        findings: List of finding strings
        prefer_ufw: Prefer ufw over iptables

    Returns: List of auto_harden() results, CRITICAL first
    """
    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    results = [auto_harden(f, prefer_ufw) for f in findings]
    results.sort(key=lambda r: SEVERITY_ORDER.get(r.get("severity", "INFO"), 4))
    return results


# ═══════════════════════════════════════════════════════════════════════════
# PART 2 — generate_report()
# Queries ChromaDB for session data from the last N hours and produces
# a professional PDF Security Audit using reportlab (already in requirements).
# Falls back to HTML if reportlab unavailable.
# ═══════════════════════════════════════════════════════════════════════════

def generate_report(
    hours:         int   = 1,
    output_path:   str   = None,
    client_name:   str   = "Confidential",
    tester_name:   str   = "ERR0RS",
    chroma_path:   str   = None,
    collection:    str   = "errz_session",
    include_harden: bool = True,
) -> dict:
    """
    Queries ChromaDB for all findings logged in the last N hours and
    produces a professional PDF Security Audit report.

    Wired to:
      - /api/command → "generate report" trigger in errorz_launcher.py
      - debrief_engine.py (can be called standalone or as PDF export)
      - ChromaDB RAG layer (errz_session collection)

    Args:
        hours:          How many hours back to query (default: 1)
        output_path:    Output PDF path (auto-generated if None)
        client_name:    Client name for report header
        tester_name:    Tester/operator name
        chroma_path:    ChromaDB persist path (auto-detected if None)
        collection:     ChromaDB collection name to query
        include_harden: Auto-append remediation commands for each finding

    Returns:
        {
          "status":      "ok" | "no_findings" | "error",
          "path":        Absolute path to generated PDF/HTML,
          "format":      "pdf" | "html",
          "findings":    List of finding dicts pulled from ChromaDB,
          "finding_count": int,
          "generated_at": ISO timestamp,
          "note":        Any warnings (e.g. ChromaDB not available),
        }

    Examples:
        generate_report(hours=1)
        generate_report(hours=24, client_name="ACME Corp", tester_name="Holden")
        generate_report(hours=8, include_harden=True)
    """
    now       = datetime.now()
    cutoff    = now - timedelta(hours=hours)
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    if output_path is None:
        output_path = str(REPORTS_DIR / f"security_audit_{timestamp}.pdf")

    findings  = []
    chroma_ok = False
    note      = ""

    # ── Step 1: Query ChromaDB for recent findings ────────────────────────
    try:
        import chromadb
        _chroma_path = chroma_path or str(ROOT_DIR / "chroma_db")
        client = chromadb.PersistentClient(path=_chroma_path)

        try:
            col = client.get_collection(collection)
        except Exception:
            col = None

        if col:
            # Pull everything and filter by timestamp in metadata
            results = col.get(include=["documents", "metadatas"])
            docs      = results.get("documents", [])
            metadatas = results.get("metadatas", [])

            for doc, meta in zip(docs, metadatas):
                # Filter to last N hours
                ts_str = meta.get("timestamp", "") or meta.get("created_at", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < cutoff:
                        continue
                except (ValueError, TypeError):
                    pass  # Include if we can't parse the timestamp

                findings.append({
                    "title":       meta.get("title", doc[:80]),
                    "severity":    meta.get("severity", "INFO"),
                    "tool":        meta.get("tool", "unknown"),
                    "target":      meta.get("target", "unknown"),
                    "description": doc,
                    "timestamp":   ts_str,
                    "mitre":       meta.get("mitre", ""),
                    "phase":       meta.get("phase", ""),
                })
            chroma_ok = True
            note = f"ChromaDB queried: {len(findings)} findings in last {hours}h"
        else:
            note = f"ChromaDB collection '{collection}' not found. Using demo findings."

    except ImportError:
        note = "ChromaDB not installed (pip install chromadb). Using demo findings for report structure."
    except Exception as e:
        note = f"ChromaDB error: {e}. Using demo findings."

    # ── Fallback demo findings (so the report always generates) ──────────
    if not findings:
        findings = [
            {
                "title":       "No live findings in ChromaDB",
                "severity":    "INFO",
                "tool":        "ERR0RS",
                "target":      "N/A",
                "description": f"No session data found in ChromaDB for the last {hours} hour(s). "
                               "Run a scan session to populate the knowledge base.",
                "timestamp":   now.isoformat(),
                "mitre":       "",
                "phase":       "Reporting",
            }
        ]

    if len(findings) == 1 and findings[0]["severity"] == "INFO" and not chroma_ok:
        pass  # proceed to generate report with note

    # ── Step 2: Attach auto_harden() remediation to each finding ─────────
    if include_harden:
        for f in findings:
            finding_text = f"{f.get('title','')} {f.get('description','')}"
            harden = auto_harden(finding_text)
            f["remediation_cmd"]  = harden.get("command")
            f["remediation_note"] = harden.get("note")
            f["cis_ref"]          = harden.get("cis")

    # ── Step 3: Generate PDF with reportlab ───────────────────────────────
    sev_counts = {}
    for f in findings:
        s = f.get("severity", "INFO")
        sev_counts[s] = sev_counts.get(s, 0) + 1

    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        doc    = SimpleDocTemplate(output_path, pagesize=A4,
                                   leftMargin=0.75*inch, rightMargin=0.75*inch,
                                   topMargin=0.75*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()

        # ── Custom styles ─────────────────────────────────────
        title_style = ParagraphStyle("Title", parent=styles["Heading1"],
                                      fontSize=22, spaceAfter=4,
                                      textColor=colors.HexColor("#1a1a2e"), alignment=TA_CENTER)
        sub_style   = ParagraphStyle("Sub", parent=styles["Normal"],
                                      fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
        h2_style    = ParagraphStyle("H2", parent=styles["Heading2"],
                                      fontSize=13, spaceBefore=14, spaceAfter=4,
                                      textColor=colors.HexColor("#0d3b6e"))
        body_style  = ParagraphStyle("Body", parent=styles["Normal"],
                                      fontSize=9, leading=13)
        code_style  = ParagraphStyle("Code", parent=styles["Code"],
                                      fontSize=8, leading=11,
                                      backColor=colors.HexColor("#f4f4f4"),
                                      leftIndent=8, rightIndent=8,
                                      borderPadding=(4,4,4,4))

        SEV_COLORS = {
            "CRITICAL": colors.HexColor("#d13434"),
            "HIGH":     colors.HexColor("#ff6a00"),
            "MEDIUM":   colors.HexColor("#ffc400"),
            "LOW":      colors.HexColor("#0c9b49"),
            "INFO":     colors.HexColor("#0077cc"),
        }

        story = []

        # ── Cover ──────────────────────────────────────────────
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("SECURITY AUDIT REPORT", title_style))
        story.append(Paragraph("Generated by ERR0RS ULTIMATE", sub_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(HRFlowable(width="100%", thickness=2,
                                 color=colors.HexColor("#1a1a2e")))
        story.append(Spacer(1, 0.15*inch))

        meta_data = [
            ["Client:", client_name,     "Tester:", tester_name],
            ["Generated:", now.strftime("%Y-%m-%d %H:%M"),
             "Period:", f"Last {hours} hour(s)"],
            ["Total Findings:", str(len(findings)),
             "Note:", (note[:60] + "..." if len(note) > 60 else note)],
        ]
        meta_table = Table(meta_data, colWidths=[1.0*inch, 2.8*inch, 1.0*inch, 2.5*inch])
        meta_table.setStyle(TableStyle([
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTNAME",      (2,0), (2,-1), "Helvetica-Bold"),
            ("TEXTCOLOR",     (0,0), (0,-1), colors.HexColor("#0d3b6e")),
            ("TEXTCOLOR",     (2,0), (2,-1), colors.HexColor("#0d3b6e")),
            ("ROWBACKGROUNDS",(0,0), (-1,-1), [colors.whitesmoke, colors.white]),
            ("GRID",          (0,0), (-1,-1), 0.25, colors.lightgrey),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.2*inch))

        # ── Severity summary ───────────────────────────────────
        story.append(Paragraph("Finding Summary", h2_style))
        sev_rows = [[sev, str(count)] for sev, count
                    in sorted(sev_counts.items(),
                               key=lambda x: ["CRITICAL","HIGH","MEDIUM","LOW","INFO"].index(x[0])
                               if x[0] in ["CRITICAL","HIGH","MEDIUM","LOW","INFO"] else 5)]
        if sev_rows:
            sev_table = Table([["Severity", "Count"]] + sev_rows,
                               colWidths=[2*inch, 1*inch])
            sev_styles = [
                ("BACKGROUND",   (0,0), (-1,0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
                ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",     (0,0), (-1,-1), 9),
                ("ALIGN",        (1,0), (1,-1), "CENTER"),
                ("GRID",         (0,0), (-1,-1), 0.25, colors.lightgrey),
                ("TOPPADDING",   (0,0), (-1,-1), 4),
                ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ]
            for i, (sev, _) in enumerate(sev_rows, 1):
                c = SEV_COLORS.get(sev, colors.grey)
                sev_styles.append(("TEXTCOLOR",    (0,i), (0,i), c))
                sev_styles.append(("FONTNAME",     (0,i), (0,i), "Helvetica-Bold"))
            sev_table.setStyle(TableStyle(sev_styles))
            story.append(sev_table)
        story.append(Spacer(1, 0.2*inch))

        # ── Findings detail ────────────────────────────────────
        story.append(Paragraph("Detailed Findings", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

        for i, f in enumerate(findings, 1):
            sev      = f.get("severity", "INFO")
            sev_col  = SEV_COLORS.get(sev, colors.grey)
            sev_hex  = sev_col.hexval() if hasattr(sev_col, "hexval") else "#888888"

            story.append(Spacer(1, 0.1*inch))
            finding_header = (
                f"<b>{i}. {f.get('title','Unknown Finding')}</b> &nbsp;"
                f"<font color='{sev_hex}'>[{sev}]</font>"
                f" &nbsp;— Tool: {f.get('tool','?')}"
                f" &nbsp;| Target: {f.get('target','?')}"
            )
            story.append(Paragraph(finding_header, body_style))

            desc = f.get("description", "")
            if desc:
                story.append(Spacer(1, 0.04*inch))
                story.append(Paragraph(desc[:500], body_style))

            if f.get("mitre"):
                story.append(Paragraph(f"<i>MITRE ATT&amp;CK: {f['mitre']}</i>",
                                        ParagraphStyle("small", parent=body_style,
                                                        fontSize=8, textColor=colors.grey)))
            if f.get("remediation_cmd"):
                story.append(Spacer(1, 0.04*inch))
                story.append(Paragraph("<b>Remediation:</b>", body_style))
                story.append(Paragraph(f"<code>{f['remediation_cmd']}</code>", code_style))
            if f.get("remediation_note"):
                story.append(Paragraph(f.get("remediation_note",""), body_style))
            if f.get("cis_ref"):
                story.append(Paragraph(f"<i>{f['cis_ref']}</i>",
                                        ParagraphStyle("small2", parent=body_style,
                                                        fontSize=8, textColor=colors.grey)))

        # ── Footer ─────────────────────────────────────────────
        story.append(Spacer(1, 0.3*inch))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        story.append(Spacer(1, 0.05*inch))
        story.append(Paragraph(
            "Generated by ERR0RS ULTIMATE — Authorized Penetration Testing Framework. "
            "CONFIDENTIAL — For authorized recipients only.",
            ParagraphStyle("footer", parent=styles["Normal"],
                           fontSize=7, textColor=colors.grey, alignment=TA_CENTER)
        ))

        doc.build(story)
        fmt = "pdf"

    except ImportError:
        # ── HTML fallback if reportlab not installed ───────────
        output_path = output_path.replace(".pdf", ".html")
        _write_html_report(findings, output_path, client_name, tester_name,
                           hours, now, sev_counts, note)
        fmt = "html"

    return {
        "status":        "ok",
        "path":          str(output_path),
        "format":        fmt,
        "findings":      findings,
        "finding_count": len(findings),
        "generated_at":  now.isoformat(),
        "sev_counts":    sev_counts,
        "note":          note,
    }


def _write_html_report(findings, path, client, tester, hours, now, sev_counts, note):
    """HTML fallback when reportlab is not available."""
    rows = ""
    for i, f in enumerate(findings, 1):
        sev   = f.get("severity","INFO")
        cmd   = f.get("remediation_cmd","")
        rows += f"""<tr>
          <td>{i}</td>
          <td><span class="sev sev-{sev.lower()}">{sev}</span></td>
          <td>{f.get('title','')}</td>
          <td>{f.get('tool','')}</td>
          <td>{f.get('target','')}</td>
          <td>{f.get('description','')[:200]}</td>
          <td><code>{cmd or '—'}</code></td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Security Audit Report</title>
<style>
  body{{font-family:Arial,sans-serif;background:#f9f9f9;color:#222;padding:30px}}
  h1{{color:#1a1a2e}} h2{{color:#0d3b6e;border-bottom:1px solid #ccc;padding-bottom:4px}}
  table{{border-collapse:collapse;width:100%}} th{{background:#1a1a2e;color:#fff;padding:8px;font-size:12px}}
  td{{padding:7px;border-bottom:1px solid #ddd;font-size:11px;vertical-align:top}}
  .sev{{padding:2px 8px;border-radius:3px;font-weight:bold;font-size:10px}}
  .sev-critical{{background:#fdd;color:#d13434}} .sev-high{{background:#ffe8d0;color:#c05000}}
  .sev-medium{{background:#fffbd0;color:#a07000}} .sev-low{{background:#d0fdd0;color:#006600}}
  .sev-info{{background:#d0eaff;color:#005599}} code{{background:#f0f0f0;padding:1px 4px;font-size:10px}}
  footer{{text-align:center;color:#999;font-size:10px;margin-top:30px}}
</style></head><body>
<h1>Security Audit Report</h1>
<p><b>Client:</b> {client} &nbsp;|&nbsp; <b>Tester:</b> {tester} &nbsp;|&nbsp;
   <b>Generated:</b> {now.strftime('%Y-%m-%d %H:%M')} &nbsp;|&nbsp;
   <b>Period:</b> Last {hours}h</p>
<p style="color:#888;font-size:11px">{note}</p>
<h2>Findings ({len(findings)} total)</h2>
<table><tr><th>#</th><th>Severity</th><th>Title</th><th>Tool</th>
<th>Target</th><th>Description</th><th>Remediation</th></tr>
{rows}
</table>
<footer>Generated by ERR0RS ULTIMATE — CONFIDENTIAL</footer>
</body></html>"""
    Path(path).write_text(html, encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# PART 3 — pcap_interpreter()
# Sniffs packets with scapy, sends hex payload to Ollama/NPU for analysis,
# and classifies each conversation as standard handshake or exfil attempt.
#
# Hailo-10H hook point: swap _ai_classify() for NPU inference.
# ═══════════════════════════════════════════════════════════════════════════

# ── AI packet classifier ──────────────────────────────────────────────────

def _ai_classify(packet_summary: str, hex_payload: str,
                  model: str = "llama3.2",
                  ollama_host: str = "http://localhost:11434") -> dict:
    """
    Sends packet hex data to Ollama (local LLM) and asks:
    "Is this a standard handshake or a data exfiltration attempt?"

    Hailo-10H NPU hook: Replace the Ollama call with NPU inference
    when running on Pi 5. Keep the function signature identical.

    Args:
        packet_summary: Human-readable summary (src→dst, protocol, size)
        hex_payload:    Hex bytes of the packet payload (first 256 bytes max)
        model:          Ollama model to use
        ollama_host:    Ollama API endpoint

    Returns:
        {
          "classification": "HANDSHAKE" | "EXFIL" | "SUSPICIOUS" | "NORMAL" | "UNKNOWN",
          "confidence":     float 0.0-1.0,
          "reason":         str explanation,
          "ioc":            list of indicators of compromise found,
          "source":         "ollama" | "heuristic",
        }
    """
    # ── Heuristic pre-filter (fast, no LLM needed) ───────────────────────
    iocs = []
    lower_hex = hex_payload.lower()
    lower_sum  = packet_summary.lower()

    # Known exfil patterns in hex
    EXFIL_PATTERNS = [
        ("base64 stream",     r"[a-zA-Z0-9+/]{40,}={0,2}"),
        ("dns tunnel",        r"\.txt\?|\.null\?"),
        ("large outbound",    None),   # handled by size check
        ("known C2 port",     None),   # handled by port check
    ]
    HANDSHAKE_PATTERNS = [
        b"\x16\x03",            # TLS ClientHello
        b"\x15\x03",            # TLS Alert
        bytes.fromhex("16030"),  # TLS fragment
    ]

    # Quick heuristic scoring
    exfil_score = 0
    reasons     = []

    # Large payload check
    try:
        payload_bytes = bytes.fromhex(hex_payload)
        if len(payload_bytes) > 1400:
            exfil_score += 2
            reasons.append(f"Large payload: {len(payload_bytes)} bytes")
        for h_pat in HANDSHAKE_PATTERNS:
            if payload_bytes.startswith(h_pat[:min(len(h_pat), len(payload_bytes))]):
                exfil_score -= 3
                reasons.append("TLS handshake signature detected")
                break
    except ValueError:
        pass

    # Suspicious port check (known non-standard C2 ports)
    C2_PORTS = {1337, 4444, 4445, 8443, 9001, 9050, 31337, 65535}
    port_match = re.search(r':(\d{4,5})\s*[→>]', packet_summary)
    if port_match:
        port = int(port_match.group(1))
        if port in C2_PORTS:
            exfil_score += 3
            iocs.append(f"Known C2 port: {port}")
            reasons.append(f"Traffic on known C2 port {port}")

    # DNS tunnel check: abnormally long DNS query
    if "dns" in lower_sum and len(packet_summary) > 120:
        exfil_score += 2
        reasons.append("Abnormally long DNS query (possible DNS tunnel)")

    # Heuristic-only classification (skip LLM for obvious cases)
    if exfil_score <= -3:
        return {
            "classification": "HANDSHAKE",
            "confidence":     0.85,
            "reason":         "TLS handshake signature confirmed. " + "; ".join(reasons),
            "ioc":            iocs,
            "source":         "heuristic",
        }
    if exfil_score >= 4:
        return {
            "classification": "EXFIL",
            "confidence":     min(0.95, 0.6 + exfil_score * 0.07),
            "reason":         "High exfil score: " + "; ".join(reasons),
            "ioc":            iocs,
            "source":         "heuristic",
        }

    # ── Ollama LLM classification for ambiguous packets ──────────────────
    try:
        prompt = (
            "You are a network security analyst. Analyze this packet and respond with ONLY a JSON object.\n\n"
            f"Packet: {packet_summary}\n"
            f"Payload (hex, first 256 bytes): {hex_payload[:512]}\n\n"
            "Respond with ONLY this JSON structure, nothing else:\n"
            "{\"classification\": \"HANDSHAKE|EXFIL|SUSPICIOUS|NORMAL|UNKNOWN\", "
            "\"confidence\": 0.0-1.0, "
            "\"reason\": \"one sentence explanation\", "
            "\"ioc\": [\"list of IOCs found or empty\"]}"
        )
        body = json.dumps({
            "model":  model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200},
        }).encode()
        req = urllib.request.Request(
            f"{ollama_host}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data     = json.loads(r.read())
            response = data.get("response", "").strip()
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                result["source"] = "ollama"
                result["ioc"]    = result.get("ioc", iocs)
                return result
    except Exception as e:
        log.debug(f"Ollama classify failed: {e}")

    # ── Final heuristic fallback ──────────────────────────────────────────
    if exfil_score >= 2:
        classification = "SUSPICIOUS"
        conf = 0.5 + exfil_score * 0.05
    else:
        classification = "NORMAL"
        conf = 0.6

    return {
        "classification": classification,
        "confidence":     min(0.9, conf),
        "reason":         ("; ".join(reasons) if reasons else "No anomalies detected"),
        "ioc":            iocs,
        "source":         "heuristic",
    }


def pcap_interpreter(
    interface:   str   = "eth0",
    count:       int   = 20,
    pcap_file:   str   = None,
    filter_bpf:  str   = "tcp or udp",
    model:       str   = "llama3.2",
    ollama_host: str   = "http://localhost:11434",
    callback     = None,
    timeout:     int   = 30,
) -> dict:
    """
    Sniff network packets and classify each one as a standard handshake
    or a data exfiltration attempt using the local AI (Ollama/NPU).

    On Pi 5 with Hailo-10H: _ai_classify() is the NPU hook point.
    Replace the Ollama call inside _ai_classify() with:
        from hailo_platform import HailoRuntime
        result = hailo_runtime.infer(packet_features)

    Args:
        interface:   Network interface to sniff on (e.g. "eth0", "wlan0")
        count:       Number of packets to capture (0 = infinite until timeout)
        pcap_file:   Path to .pcap/.pcapng file to analyze offline (overrides live sniff)
        filter_bpf:  BPF filter string (e.g. "tcp port 443", "not arp")
        model:       Ollama model for AI classification
        ollama_host: Ollama API endpoint
        callback:    Optional function(result_dict) called per packet in real time
        timeout:     Max seconds to sniff (0 = no timeout)

    Returns:
        {
          "status":   "ok" | "error" | "scapy_unavailable",
          "packets":  List of per-packet analysis dicts,
          "summary":  {HANDSHAKE: n, EXFIL: n, SUSPICIOUS: n, NORMAL: n, UNKNOWN: n},
          "exfil_detected": bool,
          "top_iocs": list of unique IOCs found,
          "interface": str,
          "count":    int packets analyzed,
          "duration_s": float,
        }

    Examples:
        # Live capture
        result = pcap_interpreter(interface="eth0", count=50)

        # Analyze existing pcap
        result = pcap_interpreter(pcap_file="/tmp/capture.pcap")

        # Real-time callback to dashboard
        def alert(r):
            if r["classification"] == "EXFIL":
                print(f"[ALERT] Exfil detected: {r['packet_summary']}")
        pcap_interpreter(interface="eth0", count=0, callback=alert, timeout=60)
    """
    start_time = time.time()

    try:
        from scapy.all import sniff, rdpcap, IP, TCP, UDP, DNS, Raw
        SCAPY_OK = True
    except ImportError:
        return {
            "status":          "scapy_unavailable",
            "error":           "scapy not installed. Run: pip install scapy --break-system-packages",
            "packets":         [],
            "summary":         {},
            "exfil_detected":  False,
            "top_iocs":        [],
            "interface":       interface,
            "count":           0,
            "duration_s":      0.0,
        }

    packets_analyzed = []
    summary          = {"HANDSHAKE": 0, "EXFIL": 0, "SUSPICIOUS": 0, "NORMAL": 0, "UNKNOWN": 0}
    all_iocs         = []

    def _analyze_packet(pkt):
        """Process one scapy packet → classify → store result."""
        try:
            # Build human-readable summary
            src = dst = proto = "?"
            size = len(pkt)

            if pkt.haslayer(IP):
                src   = pkt[IP].src
                dst   = pkt[IP].dst
                proto = "TCP" if pkt.haslayer(TCP) else "UDP" if pkt.haslayer(UDP) else "IP"
                if pkt.haslayer(TCP):
                    src += f":{pkt[TCP].sport}"
                    dst += f":{pkt[TCP].dport}"
                elif pkt.haslayer(UDP):
                    src += f":{pkt[UDP].sport}"
                    dst += f":{pkt[UDP].dport}"
                if pkt.haslayer(DNS):
                    proto = "DNS"

            pkt_summary = f"{proto} {src} → {dst} [{size}B]"

            # Extract raw payload hex (first 256 bytes)
            hex_payload = ""
            if pkt.haslayer(Raw):
                hex_payload = pkt[Raw].load[:256].hex()
            elif pkt.haslayer(IP):
                hex_payload = bytes(pkt[IP].payload)[:256].hex()

            # Classify via AI
            result = _ai_classify(pkt_summary, hex_payload, model, ollama_host)
            result["packet_summary"] = pkt_summary
            result["size_bytes"]     = size
            result["timestamp"]      = datetime.now().isoformat()
            result["src"]            = src
            result["dst"]            = dst
            result["protocol"]       = proto

            packets_analyzed.append(result)
            cls = result.get("classification", "UNKNOWN")
            summary[cls] = summary.get(cls, 0) + 1
            all_iocs.extend(result.get("ioc", []))

            # Print live output
            icon = {"EXFIL": "🔴 EXFIL",  "SUSPICIOUS": "🟡 SUSP",
                    "HANDSHAKE": "🟢 TLS", "NORMAL": "⚪ NORM",
                    "UNKNOWN": "❓ UNK"}.get(cls, "❓")
            conf = result.get("confidence", 0)
            print(f"[PCAP] {icon} [{conf:.0%}] {pkt_summary}")
            if cls in ("EXFIL", "SUSPICIOUS"):
                print(f"       Reason: {result.get('reason','')}")
                if result.get("ioc"):
                    print(f"       IOCs: {', '.join(result['ioc'])}")

            if callback:
                try: callback(result)
                except Exception as e: log.debug(f"Callback error: {e}")

        except Exception as e:
            log.debug(f"Packet analysis error: {e}")

    # ── Capture ───────────────────────────────────────────────────────────
    try:
        if pcap_file:
            # Offline pcap analysis
            print(f"[PCAP] Analyzing offline: {pcap_file}")
            pkts = rdpcap(pcap_file)
            target = pkts[:count] if count else pkts
            print(f"[PCAP] Loaded {len(target)} packets")
            for pkt in target:
                _analyze_packet(pkt)
        else:
            # Live capture
            print(f"[PCAP] Sniffing on {interface} | filter: '{filter_bpf}' | count: {count or 'unlimited'}")
            sniff_kwargs = {
                "iface":   interface,
                "filter":  filter_bpf,
                "prn":     _analyze_packet,
                "store":   False,
            }
            if count:       sniff_kwargs["count"]   = count
            if timeout > 0: sniff_kwargs["timeout"] = timeout
            from scapy.all import sniff as _sniff
            _sniff(**sniff_kwargs)

    except PermissionError:
        return {
            "status":         "error",
            "error":          "Permission denied. Run ERR0RS as root/sudo for packet capture.",
            "packets":        packets_analyzed,
            "summary":        summary,
            "exfil_detected": summary.get("EXFIL", 0) > 0,
            "top_iocs":       list(set(all_iocs))[:10],
            "interface":      interface,
            "count":          len(packets_analyzed),
            "duration_s":     round(time.time() - start_time, 2),
        }
    except Exception as e:
        return {
            "status":         "error",
            "error":          str(e),
            "packets":        packets_analyzed,
            "summary":        summary,
            "exfil_detected": summary.get("EXFIL", 0) > 0,
            "top_iocs":       list(set(all_iocs))[:10],
            "interface":      interface,
            "count":          len(packets_analyzed),
            "duration_s":     round(time.time() - start_time, 2),
        }

    duration = round(time.time() - start_time, 2)
    exfil    = summary.get("EXFIL", 0) > 0 or summary.get("SUSPICIOUS", 0) > 2

    print(f"\n[PCAP] Analysis complete: {len(packets_analyzed)} packets in {duration}s")
    print(f"       Summary: {summary}")
    if exfil:
        print(f"       ⚠️  EXFIL/SUSPICIOUS activity detected! Review findings.")

    return {
        "status":          "ok",
        "packets":         packets_analyzed,
        "summary":         summary,
        "exfil_detected":  exfil,
        "top_iocs":        list(set(all_iocs))[:10],
        "interface":       pcap_file or interface,
        "count":           len(packets_analyzed),
        "duration_s":      duration,
    }


# ═══════════════════════════════════════════════════════════════════════════
# MODULE EXPORTS + /api/blue_team handler
# ═══════════════════════════════════════════════════════════════════════════

def handle_blue_team_request(payload: dict) -> dict:
    """
    HTTP endpoint handler for /api/blue_team
    Wires auto_harden, generate_report, pcap_interpreter into the dashboard.

    Actions:
      harden        → auto_harden(finding)
      harden_batch  → auto_harden_batch(findings list)
      report        → generate_report(hours, ...)
      pcap          → pcap_interpreter(interface, count, ...)
    """
    action = payload.get("action", "harden")

    if action == "harden":
        finding = payload.get("finding", "").strip()
        if not finding:
            return {"status": "error", "error": "No finding provided"}
        result = auto_harden(finding, prefer_ufw=payload.get("prefer_ufw", True))
        return {"status": "ok", **result}

    elif action == "harden_batch":
        findings = payload.get("findings", [])
        if not findings:
            return {"status": "error", "error": "No findings list provided"}
        results = auto_harden_batch(findings, prefer_ufw=payload.get("prefer_ufw", True))
        return {"status": "ok", "results": results, "count": len(results)}

    elif action == "report":
        result = generate_report(
            hours        = payload.get("hours", 1),
            output_path  = payload.get("output_path"),
            client_name  = payload.get("client_name", "Confidential"),
            tester_name  = payload.get("tester_name", "ERR0RS"),
            chroma_path  = payload.get("chroma_path"),
            collection   = payload.get("collection", "errz_session"),
            include_harden = payload.get("include_harden", True),
        )
        return {"status": "ok", **result}

    elif action == "pcap":
        result = pcap_interpreter(
            interface  = payload.get("interface", "eth0"),
            count      = payload.get("count", 20),
            pcap_file  = payload.get("pcap_file"),
            filter_bpf = payload.get("filter", "tcp or udp"),
            model      = payload.get("model", "llama3.2"),
            timeout    = payload.get("timeout", 30),
        )
        return {"status": "ok", **result}

    else:
        return {"status": "error", "error": f"Unknown action: {action}"}


__all__ = [
    "auto_harden", "auto_harden_batch",
    "generate_report",
    "pcap_interpreter",
    "handle_blue_team_request",
]


# ── CLI self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== auto_harden() self-test ===\n")
    tests = [
        "port 3306 open on internet-facing host",
        "port 22 SSH brute force attempts detected",
        "Redis service exposed on port 6379 without auth",
        "X-Frame-Options header missing",
        "Content-Security-Policy header absent",
        "HSTS not configured",
        "Telnet service running on port 23",
        "IP forwarding enabled unexpectedly",
        "EternalBlue — port 445 exposed to internet",
        "failed login attempts on SSH from multiple IPs",
    ]
    for t in tests:
        r = auto_harden(t)
        print(f"[{r['severity']:<8}] {r['title']}")
        print(f"           cmd: {(r['command'] or '').split(chr(10))[0][:70]}")
        print()
    print(f"=== generate_report() test (no ChromaDB) ===\n")
    r = generate_report(hours=1, client_name="Test Client", include_harden=True)
    print(f"Status: {r['status']} | Format: {r['format']} | Findings: {r['finding_count']}")
    print(f"Path:   {r['path']}")
    print(f"Note:   {r['note']}")
