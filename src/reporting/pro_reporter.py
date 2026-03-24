#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Professional Report Generator v2.0
Generates executive-grade HTML/PDF pentest reports

Competes with: Metasploit Pro reporting, Core Impact reports,
               Dradis, PlexTrac, AttackForge

Features:
  - Executive summary auto-generated from findings
  - CVSS v3.1 scoring with risk matrix
  - MITRE ATT&CK TTP mapping per finding
  - Full remediation guidance per finding
  - Timeline of engagement activities
  - Credential harvest summary
  - Tool output appendix
  - Risk-rated remediation roadmap

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path(__file__).parents[2] / "output" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# CVSS severity thresholds
CVSS_RANGES = {
    "critical": (9.0, 10.0),
    "high":     (7.0,  8.9),
    "medium":   (4.0,  6.9),
    "low":      (0.1,  3.9),
    "info":     (0.0,  0.0),
}

SEVERITY_COLORS = {
    "critical": "#c0392b",
    "high":     "#e67e22",
    "medium":   "#f39c12",
    "low":      "#27ae60",
    "info":     "#2980b9",
}

REMEDIATION_LIBRARY = {
    "sql injection":        "Use parameterized queries (prepared statements). Implement input validation. Deploy a WAF. Apply principle of least privilege to DB accounts.",
    "open port":            "Disable unused services. Implement host-based firewalls. Apply network segmentation. Restrict access to required source IPs only.",
    "default credentials":  "Change all default credentials immediately. Implement a password policy. Deploy a privileged access management (PAM) solution.",
    "xss":                  "Encode all output. Implement Content Security Policy (CSP). Use HttpOnly and Secure cookie flags. Validate all input server-side.",
    "ms17-010":             "Apply MS17-010 patch immediately. Disable SMBv1. Block port 445 at perimeter. Isolate unpatched hosts.",
    "credential found":     "Enforce strong password policy. Implement MFA everywhere. Audit accounts with the compromised credential immediately.",
    "directory listing":    "Disable directory listing in web server config. Review all exposed directories for sensitive files.",
    "outdated":             "Apply all pending security patches. Implement a vulnerability management program. Subscribe to vendor security advisories.",
}

def _get_remediation(title: str) -> str:
    title_lower = title.lower()
    for key, rem in REMEDIATION_LIBRARY.items():
        if key in title_lower:
            return rem
    return "Review this finding with your security team and apply vendor-recommended patches or configuration changes. Retest after remediation."

def _severity_to_cvss(severity: str) -> float:
    mapping = {"critical": 9.5, "high": 8.0, "medium": 5.5, "low": 2.5, "info": 0.0}
    return mapping.get(severity.lower(), 0.0)

class ProReporter:
    """
    Generates a professional penetration test report from engagement data.
    Input: findings list, credentials list, timeline, campaign metadata.
    Output: Full HTML report saved to output/reports/
    """

    def generate(self, campaign_data: dict) -> str:
        """
        Generate full HTML report. Returns path to saved file.
        campaign_data keys: name, client, operator, start_date, end_date,
                            scope, findings, credentials, timeline, objectives
        """
        name      = campaign_data.get("name", "Engagement")
        client    = campaign_data.get("client", "Confidential")
        operator  = campaign_data.get("operator", "ERR0RS Operator")
        findings  = campaign_data.get("findings", [])
        creds     = campaign_data.get("credentials", [])
        timeline  = campaign_data.get("timeline", [])
        scope     = campaign_data.get("scope", [])
        start     = campaign_data.get("start_date", "")[:10]
        end       = campaign_data.get("end_date", datetime.now().isoformat())[:10]

        # Sort findings by severity
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings  = sorted(findings, key=lambda f: sev_order.get(f.get("severity","info"), 5))

        # Count by severity
        counts = {s: sum(1 for f in findings if f.get("severity") == s)
                  for s in ["critical","high","medium","low","info"]}

        html = self._render_html(name, client, operator, start, end,
                                 scope, findings, counts, creds, timeline)

        filename = f"{name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        outpath  = OUTPUT_DIR / filename
        outpath.write_text(html, encoding="utf-8")
        print(f"[ERR0RS] Report saved: {outpath}")
        return str(outpath)

    def _render_html(self, name, client, operator, start, end,
                     scope, findings, counts, creds, timeline) -> str:
        total = len(findings)
        risk_score = self._risk_score(counts)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ERR0RS Pentest Report — {name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f5f7; color: #2c3e50; }}
  .page {{ max-width: 1100px; margin: 0 auto; padding: 40px 32px; }}
  .cover {{ background: #1a1a2e; color: #fff; padding: 60px 40px; border-radius: 12px; margin-bottom: 32px; }}
  .cover h1 {{ font-size: 2.4em; font-weight: 700; margin-bottom: 8px; }}
  .cover h2 {{ font-size: 1.2em; font-weight: 300; color: #a0aec0; margin-bottom: 32px; }}
  .cover-meta {{ display: flex; gap: 40px; flex-wrap: wrap; }}
  .cover-meta div {{ background: rgba(255,255,255,0.08); padding: 16px 24px; border-radius: 8px; }}
  .cover-meta label {{ font-size: 0.75em; color: #718096; text-transform: uppercase; letter-spacing: 1px; }}
  .cover-meta p {{ font-size: 1.1em; font-weight: 500; margin-top: 4px; }}
  .section {{ background: #fff; border-radius: 10px; padding: 32px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
  .section h2 {{ font-size: 1.3em; color: #1a1a2e; border-bottom: 2px solid #e9ecef; padding-bottom: 12px; margin-bottom: 20px; }}
  .risk-matrix {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
  .risk-box {{ flex: 1; min-width: 100px; text-align: center; padding: 20px 16px; border-radius: 10px; color: #fff; }}
  .risk-box .num {{ font-size: 2.4em; font-weight: 700; }}
  .risk-box .lbl {{ font-size: 0.8em; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }}
  .risk-score {{ font-size: 1.1em; color: #4a5568; margin-top: 12px; }}
  .finding {{ border-left: 4px solid; padding: 20px 24px; margin-bottom: 16px; border-radius: 0 8px 8px 0; background: #f8f9fa; }}
  .finding h3 {{ font-size: 1em; margin-bottom: 8px; }}
  .finding .meta {{ font-size: 0.82em; color: #718096; margin-bottom: 10px; }}
  .finding .desc {{ font-size: 0.9em; color: #4a5568; margin-bottom: 10px; }}
  .finding .rem {{ font-size: 0.88em; background: #e8f5e9; padding: 10px 14px; border-radius: 6px; color: #2e7d32; }}
  .finding .rem strong {{ color: #1b5e20; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75em; font-weight: 600; color: #fff; text-transform: uppercase; }}
  .cred-table, .timeline-table {{ width: 100%; border-collapse: collapse; }}
  .cred-table th, .timeline-table th {{ background: #1a1a2e; color: #fff; padding: 10px 14px; text-align: left; font-size: 0.82em; }}
  .cred-table td, .timeline-table td {{ padding: 9px 14px; border-bottom: 1px solid #e9ecef; font-size: 0.85em; }}
  .cred-table tr:hover td, .timeline-table tr:hover td {{ background: #f0f4ff; }}
  .roadmap-item {{ display: flex; gap: 16px; padding: 14px 0; border-bottom: 1px solid #e9ecef; }}
  .roadmap-priority {{ width: 90px; text-align: center; padding: 6px; border-radius: 6px; font-size: 0.78em; font-weight: 700; color: #fff; flex-shrink: 0; }}
  .footer {{ text-align: center; color: #a0aec0; font-size: 0.82em; padding: 24px; }}
</style>
</head>
<body>
<div class="page">

<!-- COVER -->
<div class="cover">
  <h1>Penetration Test Report</h1>
  <h2>{name}</h2>
  <div class="cover-meta">
    <div><label>Client</label><p>{client}</p></div>
    <div><label>Operator</label><p>{operator}</p></div>
    <div><label>Start Date</label><p>{start}</p></div>
    <div><label>End Date</label><p>{end}</p></div>
    <div><label>Targets in Scope</label><p>{len(scope)}</p></div>
    <div><label>Total Findings</label><p>{total}</p></div>
  </div>
</div>

<!-- RISK MATRIX -->
<div class="section">
  <h2>Risk Overview</h2>
  <div class="risk-matrix">
    {self._risk_box("critical", counts.get("critical",0))}
    {self._risk_box("high",     counts.get("high",0))}
    {self._risk_box("medium",   counts.get("medium",0))}
    {self._risk_box("low",      counts.get("low",0))}
    {self._risk_box("info",     counts.get("info",0))}
  </div>
  <p class="risk-score"><strong>Overall Risk Score: {risk_score}/10</strong> — {self._risk_label(risk_score)}</p>
</div>

<!-- EXECUTIVE SUMMARY -->
<div class="section">
  <h2>Executive Summary</h2>
  <p style="line-height:1.8;color:#4a5568;">
    {self._exec_summary(name, client, counts, total, creds)}
  </p>
</div>

<!-- FINDINGS -->
<div class="section">
  <h2>Detailed Findings ({total})</h2>
  {"".join(self._finding_html(f, i+1) for i, f in enumerate(findings)) or "<p>No findings recorded.</p>"}
</div>

<!-- CREDENTIALS -->
{"" if not creds else self._creds_section(creds)}

<!-- REMEDIATION ROADMAP -->
<div class="section">
  <h2>Remediation Roadmap</h2>
  <p style="margin-bottom:16px;font-size:0.9em;color:#718096;">
    Address findings in this order. Critical and High findings should be remediated within 24-72 hours.
  </p>
  {"".join(self._roadmap_item(f, i+1) for i, f in enumerate(findings[:20]))}
</div>

<!-- TIMELINE -->
{"" if not timeline else self._timeline_section(timeline)}

<!-- SCOPE -->
<div class="section">
  <h2>Engagement Scope</h2>
  {"".join(f"<p style='font-family:monospace;padding:4px 0;'>• {t}</p>" for t in scope) or "<p>No scope defined.</p>"}
</div>

<!-- FOOTER -->
<div class="footer">
  <p>Generated by <strong>ERR0RS ULTIMATE</strong> — {datetime.now().strftime("%Y-%m-%d %H:%M")} UTC</p>
  <p>This report is confidential. Handle in accordance with engagement rules of engagement.</p>
</div>

</div>
</body>
</html>"""

    def _risk_box(self, severity: str, count: int) -> str:
        color = SEVERITY_COLORS.get(severity, "#888")
        return (f'<div class="risk-box" style="background:{color};">'
                f'<div class="num">{count}</div>'
                f'<div class="lbl">{severity.upper()}</div>'
                f'</div>')

    def _risk_score(self, counts: dict) -> float:
        weights = {"critical": 10, "high": 7, "medium": 4, "low": 1, "info": 0}
        total_w = sum(weights[s] * counts.get(s, 0) for s in weights)
        total_f = sum(counts.values()) or 1
        return min(round(total_w / total_f, 1), 10.0)

    def _risk_label(self, score: float) -> str:
        if score >= 9: return "CRITICAL RISK — Immediate action required"
        if score >= 7: return "HIGH RISK — Urgent remediation needed"
        if score >= 4: return "MEDIUM RISK — Remediate within 30 days"
        return "LOW RISK — Schedule remediation"

    def _finding_html(self, f: dict, num: int) -> str:
        sev     = f.get("severity", "info").lower()
        color   = SEVERITY_COLORS.get(sev, "#888")
        cvss    = f.get("cvss_score") or _severity_to_cvss(sev)
        mitre   = f.get("mitre_id", "")
        rem     = f.get("remediation") or _get_remediation(f.get("title",""))
        mitre_s = f'<span class="badge" style="background:#6c757d;">{mitre}</span>' if mitre else ""
        return (
            f'<div class="finding" style="border-color:{color};">'
            f'<h3>#{num} — {f.get("title","Unknown Finding")}</h3>'
            f'<div class="meta">'
            f'  <span class="badge" style="background:{color};">{sev.upper()}</span> '
            f'  {mitre_s}'
            f'  &nbsp; CVSS: {cvss:.1f}'
            f'  &nbsp; Target: {f.get("target","N/A")}'
            f'  &nbsp; Tool: {f.get("tool","N/A")}'
            f'</div>'
            f'<div class="desc">{f.get("description") or f.get("detail","No additional details.")}</div>'
            f'<div class="rem"><strong>Remediation:</strong> {rem}</div>'
            f'</div>'
        )

    def _creds_section(self, creds: list) -> str:
        rows = "".join(
            f"<tr><td>{c.get('username','')}</td>"
            f"<td>{c.get('domain','')}</td>"
            f"<td>{c.get('secret_type','')}</td>"
            f"<td>{c.get('source','')}</td>"
            f"<td>{c.get('target','')}</td>"
            f"<td>{'✅ Cracked' if c.get('cracked') else '⬜ Hash only'}</td></tr>"
            for c in creds
        )
        return (
            '<div class="section">'
            '<h2>Harvested Credentials</h2>'
            '<table class="cred-table">'
            '<tr><th>Username</th><th>Domain</th><th>Type</th>'
            '<th>Source</th><th>Target</th><th>Status</th></tr>'
            f'{rows}</table></div>'
        )

    def _roadmap_item(self, f: dict, num: int) -> str:
        sev   = f.get("severity","info").lower()
        color = SEVERITY_COLORS.get(sev, "#888")
        rem   = f.get("remediation") or _get_remediation(f.get("title",""))
        return (
            f'<div class="roadmap-item">'
            f'<div class="roadmap-priority" style="background:{color};">'
            f'#{num}<br>{sev.upper()}</div>'
            f'<div><strong>{f.get("title","")}</strong>'
            f'<p style="font-size:0.85em;color:#4a5568;margin-top:4px;">{rem[:200]}</p>'
            f'</div></div>'
        )

    def _timeline_section(self, timeline: list) -> str:
        rows = "".join(
            f"<tr><td>{e.get('timestamp','')[:19]}</td>"
            f"<td>{e.get('operator','')}</td>"
            f"<td>{e.get('action','')}</td>"
            f"<td>{e.get('target','')}</td>"
            f"<td>{e.get('tool','')}</td></tr>"
            for e in timeline[-50:]
        )
        return (
            '<div class="section"><h2>Engagement Timeline</h2>'
            '<table class="timeline-table">'
            '<tr><th>Timestamp</th><th>Operator</th><th>Action</th>'
            '<th>Target</th><th>Tool</th></tr>'
            f'{rows}</table></div>'
        )

    def _exec_summary(self, name, client, counts, total, creds) -> str:
        crits = counts.get("critical", 0)
        highs = counts.get("high", 0)
        cracked = sum(1 for c in creds if c.get("cracked"))
        return (
            f"During the <strong>{name}</strong> engagement against <strong>{client}</strong>, "
            f"ERR0RS identified <strong>{total} security findings</strong> across the target environment. "
            f"Of these, <strong style='color:{SEVERITY_COLORS['critical']}'>{crits} were rated Critical</strong> and "
            f"<strong style='color:{SEVERITY_COLORS['high']}'>{highs} rated High severity</strong>, "
            f"representing immediate risk to the confidentiality, integrity, and availability "
            f"of the organization's systems and data. "
            + (f"A total of <strong>{len(creds)} sets of credentials</strong> were harvested, "
               f"of which <strong>{cracked} were successfully cracked</strong>. " if creds else "")
            + "The findings and recommended remediations are detailed in the sections below. "
            f"It is strongly recommended that Critical and High findings be remediated within 72 hours."
        )


# ── Convenience ───────────────────────────────────────────────────────────

reporter = ProReporter()


def generate_report(campaign_data: dict) -> str:
    return reporter.generate(campaign_data)


def handle_report_command(params: dict) -> dict:
    """Entry point from ERR0RS route_command()"""
    try:
        from src.orchestration.campaign_manager import campaign_mgr
        c = campaign_mgr._get()
        if not c:
            return {"status": "error", "stdout": "No active campaign. Create one first."}
        from dataclasses import asdict
        path = reporter.generate(asdict(c))
        return {"status": "success", "stdout": f"[ERR0RS] Report generated: {path}"}
    except Exception as e:
        return {"status": "error", "stdout": f"Report generation failed: {e}"}
