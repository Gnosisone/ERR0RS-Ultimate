#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — AI Threat Intelligence Engine v1.0
Teaches, briefs, and demonstrates the AI-powered criminal threat landscape.

Audiences:
  - Red teamers: understand what adversaries are using
  - SOC analysts: detect AI-powered attack indicators
  - Corporate leaders: risk-aware briefings for boards and C-suites
  - Security educators: teaching the next generation

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

from datetime import datetime
from pathlib import Path
import importlib.util

# ── Load AI threat KB from hyphenated directory ───────────────────────────
_AI_KB_PATH = (
    Path(__file__).parents[3]
    / "knowledge" / "threat-intelligence" / "ai-powered-threats" / "ai_threat_intel.py"
)
AI_THREAT_INTELLIGENCE: dict = {}
AI_THREAT_KEYWORD_MAP: dict  = {}
_KB = False

try:
    _spec = importlib.util.spec_from_file_location("ai_threat_intel", _AI_KB_PATH)
    _mod  = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    AI_THREAT_INTELLIGENCE = getattr(_mod, "AI_THREAT_INTELLIGENCE", {})
    AI_THREAT_KEYWORD_MAP  = getattr(_mod, "AI_THREAT_KEYWORD_MAP",  {})
    _KB = bool(AI_THREAT_INTELLIGENCE)
except Exception:
    pass  # graceful fallback

REPORT_DIR = Path(__file__).parents[2] / "output" / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class AIThreatTeachEngine:
    """Teaches the AI threat landscape at multiple depth levels."""

    def teach(self, topic: str, depth: str = "intermediate") -> str:
        key = self._resolve(topic)
        if not key or key not in AI_THREAT_INTELLIGENCE:
            return self._not_found(topic)
        entry = AI_THREAT_INTELLIGENCE[key]
        return self._format(entry, depth)

    def _resolve(self, topic: str) -> str:
        t = topic.lower().strip()
        if t in AI_THREAT_KEYWORD_MAP:
            return AI_THREAT_KEYWORD_MAP[t]
        for kw, key in AI_THREAT_KEYWORD_MAP.items():
            if kw in t or t in kw:
                return key
        return ""

    def _format(self, entry: dict, depth: str) -> str:
        sep  = "=" * 58
        dash = "-" * 58
        lines = [
            sep,
            f"  [ERR0RS THREAT INTEL]  {entry.get('title','')}",
        ]
        if entry.get("classification"):
            lines.append(f"  ⚠️  {entry['classification']}")
        if entry.get("first_seen"):
            lines.append(f"  First documented: {entry['first_seen']}")
        lines += [sep, ""]

        tldr = entry.get("tldr")
        if tldr:
            lines += [f"[TL;DR]\n{tldr}", ""]

        # Render all string sections
        string_keys = [
            "the_core_change", "scale_of_threat", "what_it_is",
            "why_corporations_must_understand", "polymorphic_generation",
            "vulnerability_research", "automated_reconnaissance",
            "defense_implications", "executive_narrative",
            "recommended_investments", "red_team_role", "defender_application",
        ]
        for key in string_keys:
            val = entry.get(key)
            if val:
                label = key.replace("_", " ").upper()
                lines += [dash, f"{label}:", val, ""]

        # Render nested dicts
        for key in ["capabilities_documented", "documented_capabilities",
                    "detection_and_defense", "detection_defense",
                    "documented_tools", "deepfake_fraud",
                    "prompt_injection_attacks", "board_risk_framing",
                    "key_techniques"]:
            val = entry.get(key)
            if isinstance(val, dict):
                label = key.replace("_", " ").upper()
                lines += [dash, f"{label}:"]
                for subkey, subval in val.items():
                    if isinstance(subval, str):
                        lines += [f"\n  [{subkey.replace('_',' ').upper()}]",
                                  f"  {subval}"]
                lines.append("")

        lines += [sep,
                  "  Type 'teach me [topic]' to drill deeper.",
                  "  Type 'corporate briefing' for executive deck content.", sep]
        return "\n".join(lines)

    def _not_found(self, topic: str) -> str:
        topics = list(set(AI_THREAT_KEYWORD_MAP.values()))
        return (
            f"[ERR0RS THREAT INTEL] No entry for '{topic}'.\n"
            f"Available topics:\n"
            + "\n".join(f"  → {t}" for t in sorted(topics))
        )

    def list_topics(self) -> str:
        lines = [
            "\n[ERR0RS] AI THREAT INTELLIGENCE CURRICULUM",
            "=" * 58,
            "",
            "  The Criminal AI Ecosystem:",
            "    → teach me wormgpt",
            "    → teach me fraudgpt",
            "    → teach me the ai threat ecosystem",
            "    → teach me ghostgpt",
            "",
            "  Technical Threats:",
            "    → teach me ai malware",
            "    → teach me deepfake fraud",
            "    → teach me voice cloning attacks",
            "    → teach me prompt injection",
            "",
            "  Frameworks:",
            "    → teach me mitre atlas",
            "    → teach me the ai attack framework",
            "",
            "  Corporate / Executive:",
            "    → corporate briefing",
            "    → board briefing on ai threats",
            "    → what are attackers using right now",
            "    → current threat landscape",
            "",
            "  Red Team Applications:",
            "    → how do defenders simulate ai attacks",
            "    → what do i need to show a fortune 500",
        ]
        return "\n".join(lines)


class CorporateBriefingGenerator:
    """
    Generates executive-ready threat briefing content.
    Output can be used for board presentations, CISO reports,
    and security awareness campaigns.
    """

    def generate_briefing(self, company_name: str = "Your Organization",
                          industry: str = "Enterprise",
                          focus_areas: list = None) -> str:
        focus = focus_areas or ["bec", "deepfake", "phishing", "ai_malware"]
        now   = datetime.now().strftime("%B %Y")
        lines = self._header(company_name, industry, now)
        lines += self._executive_summary(focus)
        lines += self._threat_landscape()
        lines += self._specific_threats(focus)
        lines += self._risk_quantification()
        lines += self._recommendations()
        lines += self._footer()
        return "\n".join(lines)

    def _header(self, company, industry, date) -> list:
        return [
            "=" * 70,
            f"  CONFIDENTIAL — AI-POWERED CYBER THREAT BRIEFING",
            f"  Prepared for: {company}",
            f"  Industry:     {industry}",
            f"  Date:         {date}",
            f"  Prepared by:  ERR0RS Security Intelligence Platform",
            "=" * 70, "",
        ]

    def _executive_summary(self, focus: list) -> list:
        return [
            "EXECUTIVE SUMMARY",
            "-" * 70,
            "",
            "The threat landscape has fundamentally changed. Artificial intelligence",
            "has democratized sophisticated cyberattack capability, placing tools",
            "previously available only to nation-state actors in the hands of",
            "opportunistic criminals for as little as $200 per month.",
            "",
            "KEY FINDING: The quality, volume, and speed of cyberattacks targeting",
            "your organization and employees has increased significantly due to the",
            "proliferation of criminal AI tools including WormGPT, FraudGPT, and",
            "AI-powered deepfake technology.",
            "",
            "THIS BRIEFING COVERS:",
            "  • What criminal AI tools exist and what they can do",
            "  • Documented attacks against organizations like yours",
            "  • Specific risks to your industry and role",
            "  • Quantified financial and regulatory exposure",
            "  • Prioritized investment recommendations",
            "",
        ]

    def _threat_landscape(self) -> list:
        return [
            "THE CRIMINAL AI ECOSYSTEM",
            "-" * 70,
            "",
            "DOCUMENTED TOOLS IN ACTIVE USE BY CRIMINAL ACTORS:",
            "",
            "  WORMGPT (July 2023 — Present)",
            "  Purpose: Business Email Compromise, phishing, malware assistance",
            "  Cost: Subscription-based, dark web",
            "  Documented by: SlashNext Security Research, 2023",
            "  Risk to your org: BEC attacks against finance teams",
            "",
            "  FRAUDGPT (August 2023 — Present)",
            "  Purpose: Financial fraud, fake banking portals, vishing scripts",
            "  Cost: $200/month — $1,700/year",
            "  Documented by: Netenrich Threat Research, 2023",
            "  Risk to your org: Customer-facing fraud, credential harvesting",
            "",
            "  AI VOICE/VIDEO DEEPFAKES (2024 — Present)",
            "  Purpose: Executive impersonation, identity fraud",
            "  Cost: Consumer tools from $30/month",
            "  Documented: $25.6M single incident (Hong Kong, 2024)",
            "  Risk to your org: CEO fraud, wire transfer theft",
            "",
            "  AI-POWERED SPEAR PHISHING",
            "  Purpose: Targeted attacks using OSINT + AI personalization",
            "  Impact: 1,265% increase in phishing since ChatGPT launch (SlashNext)",
            "  Risk to your org: Every employee is a potential target",
            "",
        ]

    def _specific_threats(self, focus: list) -> list:
        lines = ["THREATS MOST RELEVANT TO YOUR ORGANIZATION", "-" * 70, ""]
        threat_map = {
            "bec": (
                "BUSINESS EMAIL COMPROMISE (BEC)\n"
                "  How it works: AI generates executive-quality impersonation emails.\n"
                "  Target: Finance teams, accounts payable, executive assistants.\n"
                "  Average loss: $125,000 per incident.\n"
                "  AI impact: AI-generated BEC is indistinguishable from real communications.\n"
                "  Your exposure: Any employee who can approve transfers is a target."
            ),
            "deepfake": (
                "DEEPFAKE EXECUTIVE FRAUD\n"
                "  How it works: AI clones executive voice/video for real-time calls.\n"
                "  Target: CFO, finance teams, any employee authorized for transfers.\n"
                "  Documented loss: $25.6M in a single incident (2024).\n"
                "  AI impact: Real-time deepfake quality fools even skeptical employees.\n"
                "  Your exposure: Any financial authorization process using video/voice."
            ),
            "phishing": (
                "AI-POWERED PHISHING AT SCALE\n"
                "  How it works: AI generates thousands of personalized phishing emails.\n"
                "  Target: All employees — any credential is valuable.\n"
                "  AI impact: Perfect grammar, personalized context, infinite variants.\n"
                "  Detection problem: Traditional email security can no longer rely on\n"
                "  quality indicators — AI generates flawless content.\n"
                "  Your exposure: 91% of breaches begin with phishing."
            ),
            "ai_malware": (
                "AI-ACCELERATED MALWARE\n"
                "  How it works: AI generates unique malware variants evading signature AV.\n"
                "  Target: Any endpoint — ransomware prep, data theft, espionage.\n"
                "  AI impact: Polymorphic generation means signature AV catches nothing.\n"
                "  Behavioral EDR is now the only reliable layer.\n"
                "  Your exposure: Any unprotected endpoint or legacy AV deployment."
            ),
        }
        for f in focus:
            if f in threat_map:
                lines.append(f"  {threat_map[f]}\n")
        return lines

    def _risk_quantification(self) -> list:
        return [
            "FINANCIAL AND REGULATORY EXPOSURE",
            "-" * 70,
            "",
            "  DIRECT FINANCIAL RISK:",
            "    • BEC average loss per incident:         $125,000",
            "    • Enterprise ransomware average payment:  $812,000",
            "    • Deepfake executive fraud documented:    $25,600,000",
            "    • Data breach average total cost:         $4,450,000 (IBM, 2023)",
            "",
            "  REGULATORY EXPOSURE:",
            "    • SEC: Material incidents disclosed within 4 business days (2023 rule)",
            "    • GDPR/CCPA: Per-record fines for breached personal data",
            "    • SOX: Financial data breach may trigger audit requirements",
            "    • Board liability: Directors face duty-of-care claims post-breach",
            "",
            "  INSURANCE CONTEXT:",
            "    • Cyber insurance premiums +50-300% since 2020",
            "    • Exclusions increasing for 'preventable' incidents",
            "    • Underwriters now require proof of specific controls",
            "    • MFA, DMARC, EDR increasingly mandatory for coverage",
            "",
        ]

    def _recommendations(self) -> list:
        return [
            "PRIORITIZED RECOMMENDATIONS",
            "-" * 70,
            "",
            "  IMMEDIATE (30 days) — Highest ROI, Lowest Cost:",
            "    □ Enforce DMARC at p=reject — blocks email domain spoofing",
            "    □ Deploy phishing-resistant MFA (FIDO2) for privileged users",
            "    □ Implement wire transfer dual-authorization policy",
            "    □ Brief finance and executive teams on AI-powered BEC and deepfakes",
            "",
            "  SHORT TERM (90 days) — Close Critical Gaps:",
            "    □ AI-powered email security gateway (Abnormal, Proofpoint, Darktrace)",
            "    □ Behavioral EDR on 100% of endpoints",
            "    □ Establish executive verification code word system",
            "    □ Run AI-quality phishing simulation to establish baseline",
            "",
            "  STRATEGIC (6-18 months) — Build Resilient Posture:",
            "    □ AI Security Operations integration",
            "    □ Deception technology (honeypots, canary tokens)",
            "    □ Third-party AI risk assessment",
            "    □ Red team engagement simulating AI-powered attack chain",
            "    □ AI governance policy for internal AI tool use",
            "",
        ]

    def _footer(self) -> list:
        return [
            "=" * 70,
            "  This briefing was generated by ERR0RS ULTIMATE Security Platform.",
            "  Intelligence sourced from: Verizon DBIR, SlashNext, Netenrich,",
            "  IBM X-Force, Darktrace, FBI IC3, MITRE ATLAS.",
            "  For technical implementation details, contact your security team.",
            "=" * 70,
        ]

    def save_html(self, company: str = "Enterprise", industry: str = "Enterprise",
                  focus_areas: list = None) -> str:
        """Generate and save an HTML version of the briefing."""
        text = self.generate_briefing(company, industry, focus_areas)
        html_lines = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>AI Threat Briefing — {company}</title>
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e2e8f0;margin:0;padding:40px}}
  .container{{max-width:900px;margin:0 auto;background:#16213e;padding:40px;border-radius:12px}}
  pre{{white-space:pre-wrap;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;line-height:1.7}}
  h1{{color:#e94560;margin-bottom:20px}}
  .warning{{background:#e94560;color:#fff;padding:8px 16px;border-radius:6px;
            display:inline-block;font-size:12px;font-weight:700;letter-spacing:1px;margin-bottom:20px}}
</style></head><body>
<div class="container">
  <div class="warning">CONFIDENTIAL — THREAT INTELLIGENCE BRIEFING</div>
  <pre>{html_lines}</pre>
</div></body></html>"""
        fname = f"AI_Threat_Briefing_{company.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.html"
        path  = REPORT_DIR / fname
        path.write_text(html, encoding="utf-8")
        return str(path)


# ── Singletons ──────────────────────────────────────────────────────────

ai_teacher  = AIThreatTeachEngine()
ai_briefer  = CorporateBriefingGenerator()


def handle_ai_threat_command(cmd: str, params: dict = None) -> dict:
    """Entry point from ERR0RS route_command()"""
    params = params or {}
    cmd    = cmd.lower().strip()

    if any(t in cmd for t in ["corporate briefing", "board briefing",
                               "executive briefing", "fortune 500"]):
        path = ai_briefer.save_html(
            company=params.get("company", "Enterprise Organization"),
            industry=params.get("industry", "Enterprise"),
        )
        brief = ai_briefer.generate_briefing(
            params.get("company","Enterprise"),
            params.get("industry","Enterprise"),
        )
        return {"status":"success","stdout": brief + f"\n\n[ERR0RS] HTML report saved: {path}"}

    if any(t in cmd for t in ["list","topics","curriculum","what can you teach"]):
        return {"status":"success","stdout": ai_teacher.list_topics()}

    # Default: teach the topic
    for prefix in ["teach me","explain","what is","tell me about","brief me on"]:
        cmd = cmd.replace(prefix,"").strip()
    return {"status":"success","stdout": ai_teacher.teach(cmd)}
