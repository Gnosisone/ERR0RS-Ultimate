"""
╔══════════════════════════════════════════════════════════════════╗
║       ERR0RS ULTIMATE — MODULE 2: AI Debrief Engine              ║
║                  src/reporting/debrief_engine.py                 ║
║                                                                  ║
║  Transforms raw engagement session data into a complete          ║
║  professional debrief: attack narrative, timeline, executive     ║
║  summary, and "what would have stopped this" defender rec.       ║
║                                                                  ║
║  100% LOCAL — no data leaves the OS. Uses Ollama (local LLM).    ║
╚══════════════════════════════════════════════════════════════════╝

WHAT THIS DOES (Visual):
────────────────────────
  [EngagementSession] ← All your raw scan results + findings
       ↓
  [Chain Reconstructor] ← Traces the attack path finding-to-finding
       ↓
  [Attack Narrative Generator] ← Local LLM writes the story
       ↓
  [Timeline Builder] ← Ordered sequence of events with timestamps
       ↓
  [Executive Summary Generator] ← Non-technical 1-pager
       ↓
  [Defender Recommendations] ← "What would have stopped this"
       ↓
  [Full HTML Debrief Report] ← Professional deliverable

WHY THIS IS REVOLUTIONARY:
───────────────────────────
  Pentesters spend 40-60% of engagement time on report writing.
  ERR0RS cuts that to near-zero. The AI reads your findings,
  reconstructs HOW the attack chain flowed, writes the narrative
  IN YOUR VOICE, and produces a professional deliverable.
  The "what would have stopped this" section is uniquely valuable —
  it shows clients exactly where their defenses need to improve.
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.core.models import EngagementSession, Finding, ScanResult, Severity, PentestPhase


# ─────────────────────────────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────────────────────────────

@dataclass
class AttackChainStep:
    """One step in the reconstructed attack chain."""
    step_number:  int
    phase:        str
    tool:         str
    finding:      Optional[Finding]
    description:  str
    led_to:       str        # What this step enabled next
    timestamp:    str
    mitre_tactic: str = ""   # MITRE ATT&CK tactic mapping
    mitre_tech:   str = ""   # MITRE ATT&CK technique


@dataclass
class AttackChain:
    """The complete reconstructed attack path."""
    target:       str
    total_steps:  int
    steps:        List[AttackChainStep] = field(default_factory=list)
    entry_point:  str = ""      # How the attack started
    final_impact: str = ""      # What was ultimately achieved
    dwell_time:   float = 0.0   # Total time in seconds


@dataclass
class DebriefReport:
    """Complete debrief package — everything in one object."""
    engagement_id:   str
    engagement_name: str
    client_name:     str
    tester_name:     str
    generated_at:    str = field(default_factory=lambda: datetime.now().isoformat())

    # Sections
    executive_summary:     str = ""
    attack_narrative:      str = ""
    attack_chain:          Optional[AttackChain] = None
    timeline_html:         str = ""
    defender_recommendations: List[str] = field(default_factory=list)
    finding_summary:       Dict[str, int] = field(default_factory=dict)
    full_html:             str = ""


# ─────────────────────────────────────────────────────────────────
# MITRE ATT&CK MAPPER
# ─────────────────────────────────────────────────────────────────

MITRE_MAPPING = {
    # Tool/Finding → (Tactic, Technique ID, Technique Name)
    "nmap":          ("Reconnaissance",       "T1046",  "Network Service Discovery"),
    "gobuster":      ("Discovery",            "T1083",  "File and Directory Discovery"),
    "nikto":         ("Discovery",            "T1595",  "Active Scanning"),
    "theharvester":  ("Reconnaissance",       "T1589",  "Gather Victim Identity Info"),
    "sqlmap":        ("Initial Access",       "T1190",  "Exploit Public-Facing Application"),
    "hydra":         ("Credential Access",    "T1110",  "Brute Force"),
    "metasploit":    ("Execution",            "T1203",  "Exploitation for Client Execution"),
    "linpeas":       ("Privilege Escalation", "T1068",  "Exploitation for Privilege Escalation"),
    "bloodhound":    ("Discovery",            "T1482",  "Domain Trust Discovery"),
    "mimikatz":      ("Credential Access",    "T1003",  "OS Credential Dumping"),
    "hashcat":       ("Credential Access",    "T1110.002","Brute Force: Password Cracking"),
    "badusb":        ("Initial Access",       "T1200",  "Hardware Additions"),
    "keylogger":     ("Collection",           "T1056.001","Input Capture: Keylogging"),
}


class MitreMapper:
    def get(self, tool_name: str) -> Tuple[str, str, str]:
        """Returns (tactic, technique_id, technique_name) or defaults."""
        return MITRE_MAPPING.get(
            tool_name.lower(),
            ("Unknown", "T0000", "Unknown Technique")
        )


# ─────────────────────────────────────────────────────────────────
# ATTACK CHAIN RECONSTRUCTOR
# ─────────────────────────────────────────────────────────────────

class ChainReconstructor:
    """
    Reconstructs the logical attack path from a completed engagement session.

    The key insight: findings have phases (Recon → Scanning → Exploitation →
    Post-Exploitation). By ordering them by phase AND timestamp, we can
    rebuild EXACTLY how the attack flowed — which discovery led to which
    exploit which led to which escalation.
    """

    PHASE_ORDER = {
        PentestPhase.RECONNAISSANCE: 0,
        PentestPhase.SCANNING:       1,
        PentestPhase.ENUMERATION:    2,
        PentestPhase.EXPLOITATION:   3,
        PentestPhase.POST_EXPLOIT:   4,
        PentestPhase.REPORTING:      5,
    }

    PHASE_DESCRIPTIONS = {
        PentestPhase.RECONNAISSANCE: "Initial reconnaissance established the attack surface",
        PentestPhase.SCANNING:       "Active scanning revealed running services and versions",
        PentestPhase.ENUMERATION:    "Deep enumeration uncovered exploitable conditions",
        PentestPhase.EXPLOITATION:   "Vulnerabilities were successfully exploited",
        PentestPhase.POST_EXPLOIT:   "Post-exploitation expanded access and impact",
    }

    def __init__(self):
        self.mitre = MitreMapper()

    def reconstruct(self, session: EngagementSession) -> AttackChain:
        """Build the full attack chain from a completed session."""
        all_findings = session.all_findings

        # Sort findings by phase then timestamp
        sorted_findings = sorted(
            all_findings,
            key=lambda f: (
                self.PHASE_ORDER.get(f.phase, 99),
                f.timestamp
            )
        )

        steps = []
        for i, finding in enumerate(sorted_findings, 1):
            tactic, tech_id, tech_name = self.mitre.get(finding.tool_name)
            led_to = self._infer_led_to(finding, sorted_findings[i:] if i < len(sorted_findings) else [])
            steps.append(AttackChainStep(
                step_number  = i,
                phase        = finding.phase.value,
                tool         = finding.tool_name,
                finding      = finding,
                description  = finding.description or finding.title,
                led_to       = led_to,
                timestamp    = finding.timestamp.isoformat(),
                mitre_tactic = tactic,
                mitre_tech   = f"{tech_id} — {tech_name}",
            ))

        entry = steps[0].description if steps else "No findings recorded"
        impact = steps[-1].description if steps else "No impact determined"

        total_time = (session.ended_at - session.started_at).total_seconds() \
                     if session.ended_at else 0.0

        return AttackChain(
            target       = ", ".join(session.targets),
            total_steps  = len(steps),
            steps        = steps,
            entry_point  = entry,
            final_impact = impact,
            dwell_time   = total_time,
        )

    def _infer_led_to(self, finding: Finding, later_findings: List[Finding]) -> str:
        """Try to infer what this finding enabled in the subsequent steps."""
        if not later_findings:
            return "End of attack chain"
        next_finding = later_findings[0]
        next_phase = next_finding.phase.value
        return f"Enabled {next_phase.lower()} phase — {next_finding.title}"



# ─────────────────────────────────────────────────────────────────
# AI NARRATIVE GENERATOR — Uses local LLM to write the debrief
# ─────────────────────────────────────────────────────────────────

class AIDebriefNarrator:
    """
    Uses Ollama (local LLM) to generate professional narrative text.
    100% local — no API calls, no data leaves the OS.
    Falls back to template-based generation if Ollama not available.
    """

    def __init__(self, model: str = "llama3.2", host: str = "http://localhost:11434"):
        self.model   = model
        self.host    = host
        self._ollama = self._check_ollama()

    def _check_ollama(self) -> bool:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _ollama_generate(self, prompt: str, max_tokens: int = 600) -> str:
        """Send prompt to local Ollama and return response."""
        import urllib.request
        import json
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": 0.4}
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
                return data.get("response", "").strip()
        except Exception as e:
            return ""

    def generate_executive_summary(self, session: EngagementSession,
                                    chain: AttackChain) -> str:
        """Generate a non-technical executive summary."""
        summary = session.finding_summary
        targets = ", ".join(session.targets)
        critical = summary.get("Critical", 0)
        high     = summary.get("High", 0)

        if self._ollama:
            prompt = f"""You are a senior penetration testing consultant writing an executive summary.
Write a professional, non-technical 2-paragraph executive summary for this engagement.

Client: {session.client_name or "Confidential"}
Targets tested: {targets}
Duration: {session.total_duration_seconds / 60:.1f} minutes
Findings: {critical} Critical, {high} High, {summary.get('Medium',0)} Medium, {summary.get('Low',0)} Low
Attack entry point: {chain.entry_point}
Final impact achieved: {chain.final_impact}
Steps in attack chain: {chain.total_steps}

Write only the summary paragraphs. Be direct. Do not use bullet points. Professional tone."""
            result = self._ollama_generate(prompt)
            if result:
                return result

        # Template fallback
        risk_level = "CRITICAL" if critical > 0 else "HIGH" if high > 0 else "MODERATE"
        return (
            f"During the authorized security assessment of {targets}, ERR0RS identified "
            f"{sum(summary.values())} security findings across all tested systems, including "
            f"{critical} critical-severity and {high} high-severity vulnerabilities. "
            f"The overall risk posture is assessed as {risk_level}.\n\n"
            f"Testing confirmed that an attacker could successfully {chain.final_impact.lower()} "
            f"through a {chain.total_steps}-step attack chain beginning with {chain.entry_point.lower()}. "
            f"Immediate remediation of the critical and high findings is strongly recommended "
            f"to prevent unauthorized access and potential data compromise."
        )

    def generate_attack_narrative(self, session: EngagementSession,
                                   chain: AttackChain) -> str:
        """Generate a detailed technical narrative of the attack."""
        if self._ollama and chain.steps:
            steps_text = "\n".join([
                f"Step {s.step_number} ({s.phase}): {s.description} [{s.mitre_tech}]"
                for s in chain.steps
            ])
            prompt = f"""You are a penetration tester writing the technical narrative section of a report.
Write a flowing, 3-4 paragraph technical narrative describing this attack chain.
Write in past tense as if you performed the test. Be specific but professional.

Target: {chain.target}
Attack Chain:
{steps_text}

Write only the narrative paragraphs. Technical audience. No bullet points."""
            result = self._ollama_generate(prompt, max_tokens=800)
            if result:
                return result

        # Template fallback
        if not chain.steps:
            return "No successful attack chain was established during this engagement."

        phases_hit = list(dict.fromkeys([s.phase for s in chain.steps]))
        narrative = (
            f"Testing of {chain.target} progressed through {len(phases_hit)} phases: "
            f"{', '.join(phases_hit)}. "
        )
        for step in chain.steps[:3]:
            narrative += f"During {step.phase.lower()}, {step.description.lower()}. "
        if len(chain.steps) > 3:
            narrative += (
                f"The attack chain continued through {len(chain.steps) - 3} additional steps, "
                f"ultimately achieving: {chain.final_impact}."
            )
        return narrative

    def generate_defender_recommendations(self, session: EngagementSession,
                                           chain: AttackChain) -> List[str]:
        """Generate 'what would have stopped this' defender recommendations."""
        findings = session.all_findings
        recs = []

        if self._ollama and chain.steps:
            steps_text = "\n".join([f"- {s.description}" for s in chain.steps])
            prompt = f"""You are a defensive security expert reviewing a penetration test.
Based on this attack chain, provide exactly 5 specific technical recommendations
that would have prevented or detected this attack. Be concrete and actionable.
Format: one recommendation per line, starting with a verb.

Attack chain steps:
{steps_text}

Provide exactly 5 recommendations, one per line, no numbering or bullets."""
            result = self._ollama_generate(prompt, max_tokens=400)
            if result:
                return [r.strip() for r in result.split("\n") if r.strip()][:5]

        # Template fallback based on tools used
        tools_used = set(s.tool for s in chain.steps)
        if "nmap" in tools_used or "gobuster" in tools_used:
            recs.append("Deploy network intrusion detection (Snort/Suricata) to alert on active scanning patterns")
        if "hydra" in tools_used or "hashcat" in tools_used:
            recs.append("Enforce account lockout policies and implement MFA on all externally-facing services")
        if "sqlmap" in tools_used:
            recs.append("Implement parameterized queries and deploy a Web Application Firewall (WAF)")
        if "metasploit" in tools_used or "linpeas" in tools_used:
            recs.append("Apply the principle of least privilege and implement endpoint detection (EDR)")
        if "mimikatz" in tools_used or "bloodhound" in tools_used:
            recs.append("Enable Windows Credential Guard and audit Active Directory privileged groups")
        recs.append("Implement centralized SIEM logging with alerts on anomalous authentication events")
        return recs[:5]


# ─────────────────────────────────────────────────────────────────
# TIMELINE BUILDER — Creates visual HTML timeline
# ─────────────────────────────────────────────────────────────────

class TimelineBuilder:
    """Builds an interactive HTML timeline of the engagement."""

    PHASE_COLORS = {
        "Reconnaissance":  "#4fc3f7",
        "Scanning":        "#81c784",
        "Enumeration":     "#fff176",
        "Exploitation":    "#ff8a65",
        "Post-Exploitation":"#ce93d8",
        "Reporting":       "#90a4ae",
    }

    def build_html(self, chain: AttackChain, session: EngagementSession) -> str:
        items = ""
        for step in chain.steps:
            color = self.PHASE_COLORS.get(step.phase, "#888")
            ts = step.timestamp[:19].replace("T", " ")
            sev = step.finding.severity.value if step.finding else "Info"
            items += f"""
            <div class="timeline-item">
              <div class="timeline-dot" style="background:{color}"></div>
              <div class="timeline-content">
                <span class="step-badge" style="background:{color}">Step {step.step_number}</span>
                <span class="phase-tag">{step.phase}</span>
                <span class="sev-tag sev-{sev.lower()}">{sev}</span>
                <p class="step-desc">{step.description}</p>
                <p class="mitre-tag">MITRE: {step.mitre_tech}</p>
                <p class="tool-tag">Tool: {step.tool} &nbsp;|&nbsp; {ts}</p>
                <p class="led-to">→ {step.led_to}</p>
              </div>
            </div>"""

        return f"""
        <div class="timeline-container">
          <h3>⏱ Attack Timeline — {chain.total_steps} Steps</h3>
          <p class="timeline-meta">Target: {chain.target} &nbsp;|&nbsp;
             Duration: {chain.dwell_time/60:.1f} min &nbsp;|&nbsp;
             Started: {session.started_at.strftime('%Y-%m-%d %H:%M')}</p>
          <div class="timeline">{items}</div>
        </div>"""



# ─────────────────────────────────────────────────────────────────
# AI DEBRIEF ENGINE — Main orchestration class
# ─────────────────────────────────────────────────────────────────

class AIDebriefEngine:
    """
    Main entry point. Takes a completed EngagementSession and produces
    a full professional debrief report.

    Usage:
        engine = AIDebriefEngine()
        report = engine.generate(session)
        engine.save_html(report, "debrief_clientname_2024.html")
    """

    def __init__(self, output_dir: str = "./reports", ollama_model: str = "llama3.2"):
        self.output_dir   = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reconstructor= ChainReconstructor()
        self.narrator     = AIDebriefNarrator(model=ollama_model)
        self.timeline     = TimelineBuilder()

    def generate(self, session: EngagementSession) -> DebriefReport:
        """
        Full pipeline: reconstruct → narrate → build report.
        Returns a DebriefReport with all sections populated.
        """
        print(f"\n[DEBRIEF] Generating debrief for: {session.name}")
        print(f"[DEBRIEF] AI backend: {'Ollama (local)' if self.narrator._ollama else 'Template fallback'}")

        # 1. Reconstruct attack chain
        print("[DEBRIEF] Reconstructing attack chain...")
        chain = self.reconstructor.reconstruct(session)
        print(f"[DEBRIEF] Chain: {chain.total_steps} steps | Entry: {chain.entry_point[:60]}...")

        # 2. Generate AI narrative sections
        print("[DEBRIEF] Generating executive summary...")
        exec_summary = self.narrator.generate_executive_summary(session, chain)

        print("[DEBRIEF] Generating attack narrative...")
        narrative = self.narrator.generate_attack_narrative(session, chain)

        print("[DEBRIEF] Generating defender recommendations...")
        recs = self.narrator.generate_defender_recommendations(session, chain)

        # 3. Build timeline
        print("[DEBRIEF] Building attack timeline...")
        timeline_html = self.timeline.build_html(chain, session)

        # 4. Assemble report
        report = DebriefReport(
            engagement_id   = session.id,
            engagement_name = session.name,
            client_name     = session.client_name,
            tester_name     = session.tester_name,
            executive_summary = exec_summary,
            attack_narrative  = narrative,
            attack_chain      = chain,
            timeline_html     = timeline_html,
            defender_recommendations = recs,
            finding_summary   = session.finding_summary,
        )
        report.full_html = self._render_html(report, session)
        print(f"[DEBRIEF] ✅ Debrief complete.\n")
        return report

    def save_html(self, report: DebriefReport, filename: str = None) -> str:
        if not filename:
            safe = report.client_name.replace(" ", "_") or "client"
            filename = f"debrief_{safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        path = self.output_dir / filename
        path.write_text(report.full_html, encoding="utf-8")
        print(f"[DEBRIEF] Report saved: {path}")
        return str(path)

    def _render_html(self, report: DebriefReport, session: EngagementSession) -> str:
        """Render the complete HTML debrief report."""
        recs_html = "\n".join([f"<li>{r}</li>" for r in report.defender_recommendations])
        sev = report.finding_summary
        chain = report.attack_chain

        chain_steps_html = ""
        if chain:
            for step in chain.steps:
                sev_val = step.finding.severity.value if step.finding else "Info"
                chain_steps_html += f"""
                <tr>
                  <td>{step.step_number}</td>
                  <td><span class="phase-badge">{step.phase}</span></td>
                  <td><code>{step.tool}</code></td>
                  <td>{step.description}</td>
                  <td><small>{step.mitre_tech}</small></td>
                  <td><span class="sev-badge sev-{sev_val.lower()}">{sev_val}</span></td>
                </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ERR0RS Debrief — {report.engagement_name}</title>
<style>
  :root {{
    --bg: #0a0a0f; --card: #12121a; --border: #1e1e2e;
    --text: #e0e0e0; --accent: #00ff9f; --red: #ff4444;
    --orange: #ff8c00; --yellow: #ffd700; --blue: #4fc3f7;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif;
         font-size: 14px; line-height: 1.7; padding: 30px; }}
  h1 {{ color: var(--accent); font-size: 2em; margin-bottom: 4px; }}
  h2 {{ color: var(--accent); font-size: 1.3em; margin: 24px 0 10px;
        border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  h3 {{ color: var(--blue); margin: 16px 0 8px; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border);
           border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
  .sev-grid {{ display: grid; grid-template-columns: repeat(5,1fr); gap: 10px; }}
  .sev-box {{ border-radius: 6px; padding: 12px; text-align: center; }}
  .sev-box .count {{ font-size: 2em; font-weight: bold; }}
  .sev-critical {{ background: #2a0000; border: 1px solid var(--red); color: var(--red); }}
  .sev-high     {{ background: #1a0f00; border: 1px solid var(--orange); color: var(--orange); }}
  .sev-medium   {{ background: #1a1a00; border: 1px solid var(--yellow); color: var(--yellow); }}
  .sev-low      {{ background: #001a00; border: 1px solid #4caf50; color: #4caf50; }}
  .sev-info     {{ background: #001020; border: 1px solid var(--blue); color: var(--blue); }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1e1e2e; padding: 8px; text-align: left; color: var(--accent); font-size: 0.85em; }}
  td {{ padding: 8px; border-bottom: 1px solid #1e1e2e; vertical-align: top; }}
  .phase-badge {{ background: #1e2d3d; color: var(--blue); padding: 2px 6px;
                  border-radius: 3px; font-size: 0.8em; }}
  .sev-badge {{ padding: 2px 8px; border-radius: 3px; font-size: 0.8em; font-weight: bold; }}
  .sev-badge.sev-critical {{ background: #2a0000; color: var(--red); }}
  .sev-badge.sev-high     {{ background: #1a0f00; color: var(--orange); }}
  .sev-badge.sev-medium   {{ background: #1a1a00; color: var(--yellow); }}
  .sev-badge.sev-low      {{ background: #001a00; color: #4caf50; }}
  .rec-list {{ list-style: none; padding: 0; }}
  .rec-list li {{ padding: 8px 12px; margin-bottom: 6px; background: #0f1f0f;
                  border-left: 3px solid var(--accent); border-radius: 3px; }}
  code {{ background: #1e1e2e; padding: 1px 5px; border-radius: 3px; color: #ff79c6; }}
  .timeline-container {{ margin: 20px 0; }}
  .timeline-meta {{ color: #666; font-size: 0.85em; margin-bottom: 15px; }}
  .timeline {{ position: relative; padding-left: 30px; }}
  .timeline-item {{ position: relative; margin-bottom: 16px; }}
  .timeline-dot {{ position: absolute; left: -35px; top: 5px; width: 12px; height: 12px;
                   border-radius: 50%; }}
  .timeline-content {{ background: var(--card); border: 1px solid var(--border);
                        border-radius: 6px; padding: 10px 14px; }}
  .step-desc {{ margin: 6px 0; }}
  .mitre-tag, .tool-tag, .led-to {{ font-size: 0.8em; color: #666; }}
  .led-to {{ color: #888; font-style: italic; }}
  .step-badge, .phase-tag, .sev-tag {{ font-size: 0.75em; padding: 1px 6px;
             border-radius: 3px; margin-right: 6px; }}
  footer {{ text-align: center; color: #333; font-size: 0.8em; margin-top: 40px;
            padding-top: 16px; border-top: 1px solid var(--border); }}
</style>
</head>
<body>
<h1>⚡ ERR0RS — Engagement Debrief</h1>
<p class="meta">
  Client: <strong>{report.client_name or "Confidential"}</strong> &nbsp;|&nbsp;
  Tester: {report.tester_name or "ERR0RS"} &nbsp;|&nbsp;
  Targets: {", ".join(session.targets)} &nbsp;|&nbsp;
  Generated: {report.generated_at[:19].replace("T"," ")}
</p>

<h2>📋 Executive Summary</h2>
<div class="card"><p>{report.executive_summary.replace(chr(10),'<br>')}</p></div>

<h2>📊 Finding Summary</h2>
<div class="card">
  <div class="sev-grid">
    <div class="sev-box sev-critical"><div class="count">{sev.get('Critical',0)}</div>Critical</div>
    <div class="sev-box sev-high"><div class="count">{sev.get('High',0)}</div>High</div>
    <div class="sev-box sev-medium"><div class="count">{sev.get('Medium',0)}</div>Medium</div>
    <div class="sev-box sev-low"><div class="count">{sev.get('Low',0)}</div>Low</div>
    <div class="sev-box sev-info"><div class="count">{sev.get('Info',0)}</div>Info</div>
  </div>
</div>

<h2>⚔️ Attack Narrative</h2>
<div class="card"><p>{report.attack_narrative.replace(chr(10),'<br>')}</p></div>

<h2>🔗 Attack Chain Reconstruction</h2>
<div class="card">
  <table>
    <tr><th>#</th><th>Phase</th><th>Tool</th><th>Finding</th><th>MITRE ATT&CK</th><th>Severity</th></tr>
    {chain_steps_html}
  </table>
</div>

<h2>⏱ Timeline</h2>
<div class="card">{report.timeline_html}</div>

<h2>🛡️ What Would Have Stopped This</h2>
<div class="card">
  <p style="margin-bottom:12px;color:#888">Defender recommendations based on the observed attack chain:</p>
  <ul class="rec-list">{recs_html}</ul>
</div>

<footer>
  Generated by ERR0RS ULTIMATE — Authorized Penetration Testing Framework<br>
  CONFIDENTIAL — For authorized recipients only
</footer>
</body></html>"""


__all__ = [
    "AIDebriefEngine", "DebriefReport", "AttackChain",
    "ChainReconstructor", "AIDebriefNarrator", "TimelineBuilder",
]
