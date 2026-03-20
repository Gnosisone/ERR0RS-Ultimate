#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Compliance Mapper v1.0
Maps pentest findings → compliance frameworks automatically.

Competes with: Drata, Vanta, Tugboat Logic
Frameworks supported:
  - SOC 2 Type II
  - PCI-DSS v4.0
  - ISO 27001:2022
  - HIPAA Security Rule
  - NIST CSF 2.0
  - CIS Controls v8

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from datetime import datetime
from typing import Optional

# ─── Finding category → compliance control mappings ──────────────────────────

COMPLIANCE_MAP = {

    "open_ports_unnecessary": {
        "finding": "Unnecessary open ports / services",
        "severity": "HIGH",
        "soc2":    ["CC6.6 - Logical and physical access controls"],
        "pci_dss": ["1.3 - Restrict inbound/outbound traffic", "2.2.5 - Remove unnecessary functionality"],
        "iso27001":["A.8.20 - Network security", "A.8.22 - Segregation of networks"],
        "hipaa":   ["164.312(a)(2)(iii) - Automatic logoff", "164.312(e)(1) - Transmission security"],
        "nist_csf":["PR.AC-5 - Network integrity protected", "PR.DS-2 - Data-in-transit protected"],
        "cis_v8":  ["CIS 4 - Secure Configuration of Enterprise Assets"],
        "remediation": "Disable or firewall unnecessary services. Apply principle of least exposure.",
    },

    "weak_credentials": {
        "finding": "Weak or default credentials found",
        "severity": "CRITICAL",
        "soc2":    ["CC6.1 - Logical access security", "CC6.2 - Authentication"],
        "pci_dss": ["8.3 - Secure individual non-consumer user authentication", "8.6 - Password policies"],
        "iso27001":["A.8.5 - Secure authentication", "A.5.17 - Authentication information"],
        "hipaa":   ["164.308(a)(5)(ii)(D) - Password management"],
        "nist_csf":["PR.AC-1 - Identities managed", "PR.AC-7 - Users and assets authenticated"],
        "cis_v8":  ["CIS 5 - Account Management", "CIS 6 - Access Control Management"],
        "remediation": "Enforce password policy: 12+ chars, complexity, MFA for all accounts.",
    },

    "unpatched_systems": {
        "finding": "Unpatched OS or software with known CVEs",
        "severity": "HIGH",
        "soc2":    ["CC7.1 - Detection and monitoring of vulnerabilities"],
        "pci_dss": ["6.3 - Security vulnerabilities identified and addressed", "6.3.3 - Patches/updates"],
        "iso27001":["A.8.8 - Management of technical vulnerabilities"],
        "hipaa":   ["164.308(a)(1)(ii)(A) - Risk analysis"],
        "nist_csf":["ID.RA-1 - Asset vulnerabilities identified", "PR.MA-1 - Maintenance performed"],
        "cis_v8":  ["CIS 7 - Continuous Vulnerability Management"],
        "remediation": "Implement patch management: critical patches within 30 days, all patches within 90 days.",
    },

    "no_mfa": {
        "finding": "Multi-factor authentication not enforced",
        "severity": "HIGH",
        "soc2":    ["CC6.2 - Multi-factor authentication"],
        "pci_dss": ["8.4 - MFA for all non-console admin access", "8.5 - MFA for all access into CDE"],
        "iso27001":["A.8.5 - Secure authentication"],
        "hipaa":   ["164.312(d) - Person or entity authentication"],
        "nist_csf":["PR.AC-7 - Users authenticated commensurate with risk"],
        "cis_v8":  ["CIS 6.3 - Require MFA for externally-exposed applications"],
        "remediation": "Enable MFA for all user accounts, especially admin and remote access.",
    },

    "unencrypted_data": {
        "finding": "Sensitive data transmitted or stored without encryption",
        "severity": "CRITICAL",
        "soc2":    ["CC6.7 - Transmission and disposal of data", "CC9.2 - Risk management"],
        "pci_dss": ["3.5 - PAN must be secured where stored", "4.2 - Encrypt PAN over open networks"],
        "iso27001":["A.8.24 - Use of cryptography", "A.8.11 - Data masking"],
        "hipaa":   ["164.312(a)(2)(iv) - Encryption and decryption", "164.312(e)(2)(ii) - Encryption at rest"],
        "nist_csf":["PR.DS-1 - Data-at-rest protected", "PR.DS-2 - Data-in-transit protected"],
        "cis_v8":  ["CIS 3.11 - Encrypt sensitive data at rest", "CIS 11.1 - Maintain TLS"],
        "remediation": "Implement AES-256 encryption at rest, TLS 1.2+ in transit. No plaintext secrets.",
    },

    "sql_injection": {
        "finding": "SQL injection vulnerability confirmed",
        "severity": "CRITICAL",
        "soc2":    ["CC7.1 - Vulnerability identification", "CC8.1 - Change management"],
        "pci_dss": ["6.2 - Secure bespoke software", "6.4 - Protect web-facing applications"],
        "iso27001":["A.8.25 - Secure development life cycle", "A.8.28 - Secure coding"],
        "hipaa":   ["164.308(a)(1) - Risk analysis and management"],
        "nist_csf":["ID.RA-1 - Asset vulnerabilities identified and documented"],
        "cis_v8":  ["CIS 16.12 - Implement code-level security checks"],
        "remediation": "Use parameterized queries/prepared statements. Never concatenate user input into SQL.",
    },

    "no_logging": {
        "finding": "Insufficient logging and monitoring",
        "severity": "MEDIUM",
        "soc2":    ["CC7.2 - System monitoring", "CC4.1 - COSO monitoring"],
        "pci_dss": ["10.2 - Implement audit logs", "10.3 - Protect audit logs"],
        "iso27001":["A.8.15 - Logging", "A.8.16 - Monitoring activities"],
        "hipaa":   ["164.312(b) - Audit controls"],
        "nist_csf":["DE.CM-1 - Network monitored for cybersecurity events"],
        "cis_v8":  ["CIS 8 - Audit Log Management"],
        "remediation": "Enable centralized logging (SIEM). Retain logs 90+ days. Alert on anomalies.",
    },

    "missing_firewall": {
        "finding": "Host-based firewall not configured or disabled",
        "severity": "HIGH",
        "soc2":    ["CC6.6 - Boundary protection controls"],
        "pci_dss": ["1.3 - Restrict traffic between networks"],
        "iso27001":["A.8.20 - Network security controls"],
        "hipaa":   ["164.312(e)(1) - Transmission security"],
        "nist_csf":["PR.AC-5 - Network integrity protected"],
        "cis_v8":  ["CIS 4.4 - Implement and manage firewall rules"],
        "remediation": "Enable host firewall (ufw/iptables/Windows Firewall). Default deny inbound.",
    },

    "exposed_admin_interface": {
        "finding": "Administrative interface exposed to internet",
        "severity": "CRITICAL",
        "soc2":    ["CC6.6 - Boundary protection", "CC6.2 - Access control"],
        "pci_dss": ["1.5 - Firewall rules restrict admin access", "12.3 - Restrict admin access to minimum"],
        "iso27001":["A.8.2 - Privileged access rights", "A.8.20 - Network security"],
        "hipaa":   ["164.308(a)(3) - Workforce access management"],
        "nist_csf":["PR.AC-4 - Access permissions managed"],
        "cis_v8":  ["CIS 6 - Access Control Management", "CIS 12 - Network Infrastructure Management"],
        "remediation": "Restrict admin interface to management VLAN/VPN only. Never expose to internet.",
    },

    "certificate_issues": {
        "finding": "SSL/TLS certificate issues (expired, self-signed, weak cipher)",
        "severity": "MEDIUM",
        "soc2":    ["CC6.7 - Encryption in transit"],
        "pci_dss": ["4.2.1 - Strong cryptography for PAN transmission"],
        "iso27001":["A.8.24 - Use of cryptography"],
        "hipaa":   ["164.312(e)(2)(ii) - Encryption in transit"],
        "nist_csf":["PR.DS-2 - Data-in-transit protected"],
        "cis_v8":  ["CIS 3.10 - Encrypt sensitive data in transit"],
        "remediation": "Use valid CA-signed certs. TLS 1.2+ minimum. Disable SSLv3, TLS 1.0/1.1.",
    },
}

FRAMEWORK_INFO = {
    "soc2":    {"name": "SOC 2 Type II",     "focus": "Trust Services Criteria",    "audience": "Service organizations"},
    "pci_dss": {"name": "PCI-DSS v4.0",      "focus": "Cardholder data protection", "audience": "Payment processors"},
    "iso27001":{"name": "ISO 27001:2022",    "focus": "Information security ISMS",  "audience": "All organizations"},
    "hipaa":   {"name": "HIPAA Security Rule","focus": "Protected health information","audience": "Healthcare entities"},
    "nist_csf":{"name": "NIST CSF 2.0",      "focus": "Cybersecurity risk management","audience": "Critical infrastructure"},
    "cis_v8":  {"name": "CIS Controls v8",   "focus": "Prioritized security actions","audience": "All organizations"},
}


def map_finding(finding_key: str, frameworks: list = None) -> dict:
    """Map a finding to compliance controls across specified frameworks."""
    finding = COMPLIANCE_MAP.get(finding_key)
    if not finding:
        return {
            "status": "error",
            "error":  f"Unknown finding: {finding_key}",
            "available": list(COMPLIANCE_MAP.keys()),
        }

    result = {
        "status":      "success",
        "finding":     finding["finding"],
        "severity":    finding["severity"],
        "remediation": finding["remediation"],
        "controls":    {},
    }

    active_frameworks = frameworks or list(FRAMEWORK_INFO.keys())
    for fw in active_frameworks:
        if fw in finding and fw != "finding" and fw != "severity" and fw != "remediation":
            result["controls"][fw] = {
                "framework": FRAMEWORK_INFO.get(fw, {}).get("name", fw),
                "controls":  finding[fw],
            }

    return result


def generate_compliance_report(findings: list, frameworks: list = None,
                                org_name: str = "Target Organization") -> str:
    """Generate a full compliance gap report from a list of finding keys."""
    active_fw = frameworks or ["soc2", "pci_dss", "iso27001", "nist_csf"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# Compliance Gap Report — {org_name}",
        f"*Generated by ERR0RS Ultimate | {now}*",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Findings assessed | {len(findings)} |",
        f"| Frameworks mapped | {', '.join(active_fw)} |",
        f"| Critical findings | {sum(1 for f in findings if COMPLIANCE_MAP.get(f,{}).get('severity')=='CRITICAL')} |",
        f"| High findings     | {sum(1 for f in findings if COMPLIANCE_MAP.get(f,{}).get('severity')=='HIGH')} |",
        "",
        "## Findings & Control Gaps",
        "",
    ]

    for finding_key in findings:
        m = map_finding(finding_key, active_fw)
        if m["status"] != "success":
            continue

        severity_color = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(m["severity"], "⚪")
        lines.append(f"### {severity_color} {m['finding']} ({m['severity']})")
        lines.append("")
        lines.append(f"**Remediation:** {m['remediation']}")
        lines.append("")
        lines.append("**Compliance Controls Violated:**")
        lines.append("")
        lines.append("| Framework | Controls |")
        lines.append("|-----------|---------|")
        for fw_key, fw_data in m["controls"].items():
            controls_str = " | ".join(fw_data["controls"])
            lines.append(f"| {fw_data['framework']} | {controls_str} |")
        lines.append("")

    lines += [
        "---",
        "## Framework References",
        "",
    ]
    for fw in active_fw:
        info = FRAMEWORK_INFO.get(fw, {})
        lines.append(f"- **{info.get('name', fw)}**: {info.get('focus', '')} — {info.get('audience', '')}")

    lines += ["", "---", "*ERR0RS Compliance Mapper — 100% local, no data leaves your environment*"]
    return "\n".join(lines)


def list_findings() -> dict:
    return {
        "status": "success",
        "count":  len(COMPLIANCE_MAP),
        "findings": [
            {"key": k, "finding": v["finding"], "severity": v["severity"]}
            for k, v in COMPLIANCE_MAP.items()
        ],
    }


def handle_compliance_request(payload: dict) -> dict:
    action = payload.get("action", "list")
    if action == "list":
        return list_findings()
    elif action == "map":
        return map_finding(payload.get("finding", ""), payload.get("frameworks"))
    elif action == "report":
        report = generate_compliance_report(
            payload.get("findings", []),
            payload.get("frameworks"),
            payload.get("org_name", "Target Organization"),
        )
        return {"status": "success", "stdout": report}
    elif action == "frameworks":
        return {"status": "success", "frameworks": FRAMEWORK_INFO}
    return {"status": "error", "error": f"Unknown action: {action}"}
