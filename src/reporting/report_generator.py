# src/reporting/report_generator.py
# ERR0RS-Ultimate — Professional Pentest Report Generator
# Produces: Markdown, HTML (Jinja2), and JSON report artefacts.
# Optionally enhances findings with AI narrative via the LLM router.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("ReportGenerator")


# ── Data models ──────────────────────────────────────────────────────────────

SEVERITY_RANK = {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5}
SEVERITY_COLOR = {
    "critical": "#d13434",
    "high":     "#ff6a00",
    "medium":   "#ffc400",
    "low":      "#0c9b49",
    "info":     "#4a90d9",
}


@dataclass
class Finding:
    title:          str
    severity:       str          # critical | high | medium | low | info
    description:    str
    evidence:       str
    recommendation: str
    plugin:         str  = ""
    mitre_id:       str  = ""
    mitre_tactic:   str  = ""
    learning:       str  = ""    # Educational note (ERR0RS purple team)
    timestamp:      str  = field(default_factory=lambda: datetime.utcnow().isoformat())
    cvss:           float = 0.0

    @property
    def priority(self) -> int:
        return SEVERITY_RANK.get(self.severity.lower(), 5)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ReportMeta:
    title:       str  = "ERR0RS-Ultimate Security Assessment"
    target:      str  = ""
    targets:     List[str] = field(default_factory=list)
    assessor:    str  = "ERR0RS-Ultimate"
    date:        str  = field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    session_id:  str  = ""
    scope:       str  = "Authorized penetration test"
    methodology: str  = "OWASP Testing Guide v4 / PTES"
    classification: str = "CONFIDENTIAL"


class ReportGenerator:
    """
    Builds professional penetration test reports from SharedContext memory.

    Usage
    -----
    gen     = ReportGenerator(memory=ctx, report_dir="reports")
    report  = gen.generate(target="192.168.1.10", session_id="AB12")
    md_path = gen.save_markdown(report, "session_AB12.md")
    html_path = gen.save_html(report, "session_AB12.html")
    json_path = gen.save_json(report, "session_AB12.json")
    """

    def __init__(
        self,
        memory,
        report_dir:  str          = "reports",
        ai_client                  = None,   # optional LLM for narrative enhancement
    ):
        self.memory     = memory
        self.report_dir = report_dir
        self.ai_client  = ai_client
        os.makedirs(report_dir, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────

    def generate(
        self,
        target:     str = "",
        session_id: str = "",
        enhance_ai: bool = False,
    ) -> Dict:
        """
        Build the full report dict from memory.
        Set enhance_ai=True to add AI-generated narrative (requires ai_client).
        """
        findings = self._extract_findings()
        tools    = self._extract_tool_summary()
        targets  = self._extract_targets(target)

        if enhance_ai and self.ai_client:
            findings = self._enhance_with_ai(findings)

        meta = ReportMeta(
            target     = target or (targets[0] if targets else ""),
            targets    = targets,
            session_id = session_id,
        )

        # Sort findings by severity
        findings.sort(key=lambda f: f.priority)

        summary = self._generate_summary(findings)

        return {
            "meta":     asdict(meta),
            "summary":  summary,
            "findings": [f.to_dict() for f in findings],
            "tools":    tools,
            "stats": {
                "total":    len(findings),
                "critical": sum(1 for f in findings if f.severity == "critical"),
                "high":     sum(1 for f in findings if f.severity == "high"),
                "medium":   sum(1 for f in findings if f.severity == "medium"),
                "low":      sum(1 for f in findings if f.severity == "low"),
                "info":     sum(1 for f in findings if f.severity == "info"),
            },
        }

    # ── Finding extraction ────────────────────────────────────────────────

    def _extract_findings(self) -> List[Finding]:
        """
        Pull findings from SharedContext, tool output history, and
        plugin analyze() results. Deduplicates by title.
        """
        findings: List[Finding] = []
        seen: set = set()

        # 1. SharedContext structured findings (highest fidelity)
        if hasattr(self.memory, "get_findings"):
            for raw in self.memory.get_findings():
                f = self._dict_to_finding(raw)
                if f and f.title not in seen:
                    findings.append(f)
                    seen.add(f.title)

        # 2. Parse raw tool output history
        raw_outputs = {}
        if hasattr(self.memory, "last_results"):
            raw_outputs = self.memory.last_results
        elif hasattr(self.memory, "history"):
            for entry in self.memory.history:
                cmd    = entry.get("command", "unknown")
                result = entry.get("result", "")
                if result:
                    raw_outputs[cmd] = str(result)

        for command, output in raw_outputs.items():
            for f in self._parse_output_findings(command, str(output)):
                if f.title not in seen:
                    findings.append(f)
                    seen.add(f.title)

        return findings

    def _dict_to_finding(self, raw: Dict) -> Optional[Finding]:
        try:
            return Finding(
                title          = raw.get("title", "Unnamed Finding"),
                severity       = raw.get("severity", "info").lower(),
                description    = raw.get("description", ""),
                evidence       = raw.get("evidence", raw.get("message", "")),
                recommendation = raw.get("recommendation", ""),
                plugin         = raw.get("plugin", ""),
                mitre_id       = raw.get("mitre_id", ""),
                mitre_tactic   = raw.get("mitre_tactic", ""),
                learning       = raw.get("learning", ""),
            )
        except Exception as e:
            logger.debug(f"Finding parse error: {e}")
            return None

    def _parse_output_findings(self, command: str, output: str) -> List[Finding]:
        """Heuristic parser — extracts findings from raw nmap/nikto/sqlmap output."""
        findings = []
        lower = output.lower()

        patterns = [
            # SSH
            ("22/tcp open", Finding(
                title="SSH Service Exposed",
                severity="medium",
                description="SSH is accessible — attackers may attempt brute force or use stolen credentials.",
                evidence="Port 22/tcp open detected in scan output.",
                recommendation="Disable password auth; enforce key-based login. Restrict by IP via firewall.",
                plugin=command, mitre_id="T1110", mitre_tactic="Credential Access",
                learning="SSH brute force is one of the most common post-recon attacks. Use fail2ban and disable root login.",
            )),
            # HTTP
            ("80/tcp open", Finding(
                title="HTTP Web Server Detected",
                severity="info",
                description="An unencrypted HTTP service is running. All traffic is cleartext.",
                evidence="Port 80/tcp open.",
                recommendation="Redirect all HTTP to HTTPS. Enable HSTS.",
                plugin=command,
            )),
            # HTTPS
            ("443/tcp open", Finding(
                title="HTTPS Web Server Detected",
                severity="info",
                description="HTTPS service detected. Ensure TLS is correctly configured.",
                evidence="Port 443/tcp open.",
                recommendation="Audit TLS version (disable TLS 1.0/1.1). Check certificate expiry.",
                plugin=command,
            )),
            # SMB
            ("445/tcp open", Finding(
                title="SMB Service Exposed",
                severity="high",
                description="SMB is accessible. Vulnerable to EternalBlue, credential relay, and share enumeration.",
                evidence="Port 445/tcp open.",
                recommendation="Disable SMBv1. Restrict SMB to internal VLAN only. Require signing.",
                plugin=command, mitre_id="T1021.002", mitre_tactic="Lateral Movement",
                learning="SMB is the #1 lateral movement vector. EternalBlue (MS17-010) still kills unpatched hosts.",
            )),
            # RDP
            ("3389/tcp open", Finding(
                title="RDP Exposed to Network",
                severity="high",
                description="Remote Desktop Protocol is publicly accessible — prime brute force target.",
                evidence="Port 3389/tcp open.",
                recommendation="Move RDP behind VPN. Enable NLA. Rate-limit login attempts.",
                plugin=command, mitre_id="T1021.001", mitre_tactic="Lateral Movement",
            )),
            # SQL injection
            ("sql injection", Finding(
                title="SQL Injection Vulnerability",
                severity="critical",
                description="Application is vulnerable to SQL injection — full database compromise possible.",
                evidence="SQLi indicator found in tool output.",
                recommendation="Use parameterised queries / prepared statements. Deploy WAF rule.",
                plugin=command, mitre_id="T1190", mitre_tactic="Initial Access",
                learning="SQLi is OWASP A03. Parameterised queries fix it in every language — no framework needed.",
            )),
            # XSS
            ("xss", Finding(
                title="Cross-Site Scripting (XSS)",
                severity="medium",
                description="Reflected or stored XSS detected. Attackers can steal sessions or redirect users.",
                evidence="XSS indicator in output.",
                recommendation="Encode all user-supplied output. Set Content-Security-Policy header.",
                plugin=command, mitre_id="T1059.007",
            )),
            # Directory traversal
            ("../", Finding(
                title="Directory Traversal Indicator",
                severity="high",
                description="Possible path traversal — application may serve files outside web root.",
                evidence="../ pattern in output.",
                recommendation="Canonicalise file paths server-side. Whitelist allowed paths.",
                plugin=command,
            )),
        ]

        for indicator, template in patterns:
            if indicator in lower:
                findings.append(template)

        return findings

    def _extract_tool_summary(self) -> List[Dict]:
        """Build a tool-run summary table for the report."""
        tools = []
        raw_outputs = {}
        if hasattr(self.memory, "last_results"):
            raw_outputs = self.memory.last_results
        elif hasattr(self.memory, "history"):
            for entry in self.memory.history:
                cmd = entry.get("command", "")
                if cmd:
                    raw_outputs[cmd] = entry.get("result", "")

        for tool, output in raw_outputs.items():
            output_str  = str(output)
            open_count  = len(re.findall(r"\d+/tcp\s+open", output_str))
            vuln_count  = output_str.lower().count("vulnerable")
            tools.append({
                "name":         tool,
                "status":       "Completed",
                "open_ports":   open_count,
                "vuln_hits":    vuln_count,
                "output_lines": len(output_str.splitlines()),
            })
        return tools

    def _extract_targets(self, primary: str) -> List[str]:
        targets = []
        if primary:
            targets.append(primary)
        if hasattr(self.memory, "targets"):
            for t in self.memory.targets:
                if t not in targets:
                    targets.append(t)
        return targets or ["Unknown"]

    def _generate_summary(self, findings: List[Finding]) -> str:
        crit = sum(1 for f in findings if f.severity == "critical")
        high = sum(1 for f in findings if f.severity == "high")
        med  = sum(1 for f in findings if f.severity == "medium")
        total = len(findings)
        if total == 0:
            return "No findings were identified during this assessment."
        parts = []
        if crit:
            parts.append(f"{crit} critical")
        if high:
            parts.append(f"{high} high")
        if med:
            parts.append(f"{med} medium")
        sev_str = ", ".join(parts) or "low/informational"
        return (
            f"This assessment identified {total} finding(s) including {sev_str} "
            f"severity issues. "
            + ("Immediate remediation is required for critical findings. " if crit else "")
            + "Refer to individual findings for detailed remediation guidance."
        )

    # ── AI enhancement ────────────────────────────────────────────────────

    def _enhance_with_ai(self, findings: List[Finding]) -> List[Finding]:
        if not self.ai_client:
            return findings
        enhanced = []
        for f in findings:
            try:
                prompt = (
                    f"Improve this pentest finding for a professional report.\n\n"
                    f"Title: {f.title}\n"
                    f"Severity: {f.severity}\n"
                    f"Description: {f.description}\n"
                    f"Recommendation: {f.recommendation}\n\n"
                    f"Respond with ONLY an improved 2-3 sentence description "
                    f"and a concise recommendation. No preamble."
                )
                response = self.ai_client.generate(prompt) if hasattr(self.ai_client, "generate") \
                    else self.ai_client.ask_with_context(prompt).get("answer", "")
                if response:
                    f.description = response[:800]
            except Exception as e:
                logger.debug(f"AI enhance failed for '{f.title}': {e}")
            enhanced.append(f)
        return enhanced

    # ── Savers ────────────────────────────────────────────────────────────

    def save_markdown(self, report: Dict, filename: str = "report.md") -> str:
        content = self._format_markdown(report)
        path = os.path.join(self.report_dir, filename)
        with open(path, "w") as fh:
            fh.write(content)
        logger.info(f"Markdown report saved: {path}")
        return path

    def save_html(self, report: Dict, filename: str = "report.html") -> str:
        content = self._format_html(report)
        path = os.path.join(self.report_dir, filename)
        with open(path, "w") as fh:
            fh.write(content)
        logger.info(f"HTML report saved: {path}")
        return path

    def save_json(self, report: Dict, filename: str = "report.json") -> str:
        path = os.path.join(self.report_dir, filename)
        with open(path, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        logger.info(f"JSON report saved: {path}")
        return path

    # ── Formatters ────────────────────────────────────────────────────────

    def _format_markdown(self, report: Dict) -> str:
        meta  = report["meta"]
        stats = report["stats"]
        lines = [
            f"# {meta['title']}",
            f"",
            f"**Classification:** {meta['classification']}  ",
            f"**Date:** {meta['date']}  ",
            f"**Assessor:** {meta['assessor']}  ",
            f"**Target(s):** {', '.join(meta['targets'])}  ",
            f"**Methodology:** {meta['methodology']}",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            report["summary"],
            f"",
            f"| Severity | Count |",
            f"|----------|-------|",
            f"| 🔴 Critical | {stats['critical']} |",
            f"| 🟠 High     | {stats['high']} |",
            f"| 🟡 Medium   | {stats['medium']} |",
            f"| 🟢 Low      | {stats['low']} |",
            f"| ⚪ Info     | {stats['info']} |",
            f"",
            f"---",
            f"",
            f"## Findings",
            f"",
        ]
        for f in report["findings"]:
            sev   = f["severity"].upper()
            lines += [
                f"### {f['title']}",
                f"",
                f"**Severity:** {sev}  ",
                f"**Plugin:** {f.get('plugin', 'N/A')}  ",
            ]
            if f.get("mitre_id"):
                lines.append(f"**MITRE:** [{f['mitre_id']}](https://attack.mitre.org/techniques/{f['mitre_id'].replace('.','/')}) — {f.get('mitre_tactic','')}")
            lines += [
                f"",
                f"**Description:**  ",
                f"{f['description']}",
                f"",
                f"**Evidence:**  ",
                f"```\n{f['evidence']}\n```",
                f"",
                f"**Recommendation:**  ",
                f"{f['recommendation']}",
            ]
            if f.get("learning"):
                lines += [
                    f"",
                    f"> 📘 **Learn:** {f['learning']}",
                ]
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        lines += [
            f"## Tool Run Summary",
            f"",
            f"| Tool | Status | Open Ports | Vuln Hits | Lines |",
            f"|------|--------|-----------|-----------|-------|",
        ]
        for t in report["tools"]:
            lines.append(
                f"| {t['name']} | {t['status']} | {t['open_ports']} "
                f"| {t['vuln_hits']} | {t['output_lines']} |"
            )
        lines.append(f"")
        lines.append(f"*Generated by ERR0RS-Ultimate — Authorized use only.*")
        return "\n".join(lines)

    def _format_html(self, report: Dict) -> str:
        """Full styled HTML report with severity colour coding."""
        meta   = report["meta"]
        stats  = report["stats"]
        colors = SEVERITY_COLOR

        findings_html = ""
        for f in report["findings"]:
            sev   = f["severity"].lower()
            color = colors.get(sev, "#888")
            mitre = ""
            if f.get("mitre_id"):
                mitre = (f'<p><strong>MITRE:</strong> '
                         f'<a href="https://attack.mitre.org/techniques/'
                         f'{f["mitre_id"].replace(".","/")}" target="_blank">'
                         f'{f["mitre_id"]}</a> — {f.get("mitre_tactic","")}</p>')
            learning = ""
            if f.get("learning"):
                learning = f'<div class="edu-note">📘 <strong>Learn:</strong> {f["learning"]}</div>'
            findings_html += f"""
            <div class="finding" style="border-left: 5px solid {color}">
                <h3>{f["title"]}</h3>
                <span class="badge" style="background:{color}">{f["severity"].upper()}</span>
                {mitre}
                <p><strong>Description:</strong> {f["description"]}</p>
                <pre class="evidence">{f["evidence"]}</pre>
                <p><strong>Recommendation:</strong> {f["recommendation"]}</p>
                {learning}
            </div>"""

        tools_html = "".join(
            f'<tr><td>{t["name"]}</td><td>✓ {t["status"]}</td>'
            f'<td>{t["open_ports"]}</td><td>{t["vuln_hits"]}</td>'
            f'<td>{t["output_lines"]}</td></tr>'
            for t in report["tools"]
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{meta["title"]}</title>
<style>
  body{{font-family:Arial,sans-serif;background:#0d0d0d;color:#e0e0e0;margin:40px;line-height:1.6}}
  h1{{color:#bf6fff}} h2{{color:#00f5ff;border-bottom:1px solid #333;padding-bottom:6px}}
  h3{{color:#c084fc}}
  .header{{background:#1a0033;padding:20px;border-radius:8px;border:1px solid #3d0080;margin-bottom:24px}}
  .header p{{margin:4px 0;color:#aaa}}
  .stats{{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}}
  .stat{{background:#1e0040;padding:12px 20px;border-radius:8px;text-align:center;min-width:80px}}
  .stat .num{{font-size:28px;font-weight:bold}} .stat .lbl{{font-size:12px;color:#888}}
  .finding{{background:#120020;padding:18px;border-radius:6px;margin:16px 0}}
  .badge{{display:inline-block;padding:3px 10px;border-radius:4px;font-size:12px;
          font-weight:bold;color:#fff;margin-bottom:8px}}
  pre.evidence{{background:#0a0a0a;border:1px solid #2d0060;padding:10px;
                border-radius:4px;overflow-x:auto;font-size:12px;color:#7fff7f}}
  .edu-note{{background:#0a1a2a;border-left:3px solid #00f5ff;padding:10px;
             margin-top:10px;border-radius:0 4px 4px 0;font-size:13px}}
  table{{width:100%;border-collapse:collapse;margin-top:12px}}
  th,td{{padding:10px 14px;border-bottom:1px solid #2d0060;text-align:left}}
  th{{background:#1a0033;color:#c084fc}}
  footer{{margin-top:40px;color:#444;font-size:12px;text-align:center}}
  a{{color:#00f5ff}}
</style>
</head>
<body>
<div class="header">
  <h1>🔐 {meta["title"]}</h1>
  <p><strong>Classification:</strong> {meta["classification"]}</p>
  <p><strong>Date:</strong> {meta["date"]}</p>
  <p><strong>Target(s):</strong> {", ".join(meta["targets"])}</p>
  <p><strong>Assessor:</strong> {meta["assessor"]}</p>
  <p><strong>Methodology:</strong> {meta["methodology"]}</p>
</div>

<h2>Executive Summary</h2>
<p>{report["summary"]}</p>

<div class="stats">
  <div class="stat"><div class="num" style="color:#d13434">{stats["critical"]}</div><div class="lbl">Critical</div></div>
  <div class="stat"><div class="num" style="color:#ff6a00">{stats["high"]}</div><div class="lbl">High</div></div>
  <div class="stat"><div class="num" style="color:#ffc400">{stats["medium"]}</div><div class="lbl">Medium</div></div>
  <div class="stat"><div class="num" style="color:#0c9b49">{stats["low"]}</div><div class="lbl">Low</div></div>
  <div class="stat"><div class="num" style="color:#4a90d9">{stats["info"]}</div><div class="lbl">Info</div></div>
</div>

<h2>Findings</h2>
{findings_html}

<h2>Tool Run Summary</h2>
<table>
  <tr><th>Tool</th><th>Status</th><th>Open Ports</th><th>Vuln Hits</th><th>Lines</th></tr>
  {tools_html}
</table>

<footer>Generated by ERR0RS-Ultimate | Authorized penetration testing only</footer>
</body>
</html>"""
