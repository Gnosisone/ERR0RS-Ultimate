#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Social Engineering Engine v1.0
The Human Variable Module

Covers: OSINT on humans, phishing campaign setup guidance,
vishing scripts, pretexting frameworks, physical SE,
defense recommendations, and purple team SE detection.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
LEGAL: All techniques require explicit written authorization.
"""

import json
from typing import Optional
from datetime import datetime
import importlib.util, sys
from pathlib import Path

# ── Load SE knowledge base from hyphenated directory ─────────────────────
# Python can't import from dirs with hyphens; use importlib instead.
_SE_KB_PATH = (
    Path(__file__).parents[3]
    / "knowledge" / "social-engineering" / "HUMAN_VARIABLE" / "se_knowledge_base.py"
)
SE_KNOWLEDGE_BASE: dict = {}
SE_KEYWORD_MAP: dict    = {}
_KB_LOADED = False

try:
    _spec = importlib.util.spec_from_file_location("se_knowledge_base", _SE_KB_PATH)
    _mod  = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    SE_KNOWLEDGE_BASE = getattr(_mod, "SE_KNOWLEDGE_BASE", {})
    SE_KEYWORD_MAP    = getattr(_mod, "SE_KEYWORD_MAP",    {})
    _KB_LOADED = bool(SE_KNOWLEDGE_BASE)
except Exception as _e:
    pass  # graceful fallback — engine still works with empty KB


# ═══════════════════════════════════════════════════════════════════════════
# PHISHING CAMPAIGN BUILDER
# Guides operatives through building a complete phishing campaign
# ═══════════════════════════════════════════════════════════════════════════

class PhishingCampaignBuilder:
    """
    Interactive phishing campaign planning assistant.
    Generates campaign configs, email templates, and GoPhish setup guides.
    """

    PRETEXT_TEMPLATES = {
        "it_password_reset": {
            "subject": "[ACTION REQUIRED] Password Expiration — Reset by {deadline}",
            "sender_name": "{company} IT Security Team",
            "sender_domain_suggestion": "it-helpdesk.{target_domain} OR {target_domain}-support.com",
            "body": (
                "Hi {first_name},\n\n"
                "Our security monitoring system has flagged your account following "
                "a third-party data exposure. As a precaution, all accounts in the "
                "{department} department must complete a mandatory password reset.\n\n"
                "Your access will be suspended at {deadline} if this is not completed.\n\n"
                "Reset your password here: {phishing_link}\n\n"
                "If you have questions, contact the Help Desk at {fake_ext}.\n\n"
                "— {company} IT Security"
            ),
            "urgency": "HIGH",
            "target_roles": ["All employees"],
            "difficulty": "Easy",
        },
        "hr_benefits": {
            "subject": "Benefits Enrollment Closes Friday — Verify Your Selections",
            "sender_name": "{company} Human Resources",
            "sender_domain_suggestion": "hr-benefits.{target_domain} OR {target_domain}-hr.net",
            "body": (
                "Dear {first_name},\n\n"
                "Open enrollment for the upcoming benefit year closes this Friday.\n\n"
                "Our records show your selections have not been confirmed. "
                "Employees who do not verify by the deadline will be enrolled "
                "in the default plan, which may not reflect your preferences.\n\n"
                "Several of your colleagues have already completed this step.\n\n"
                "Verify your benefits now: {phishing_link}\n\n"
                "— {company} Human Resources"
            ),
            "urgency": "MEDIUM",
            "target_roles": ["All employees"],
            "difficulty": "Easy",
        },
        "executive_wire": {
            "subject": "Confidential — Urgent Request",
            "sender_name": "{ceo_name}, {company}",
            "sender_domain_suggestion": "Spoof actual CEO email via display name",
            "body": (
                "Hi {target_name},\n\n"
                "I'm tied up in board meetings today. I need you to handle "
                "an urgent and confidential matter — please keep this between us "
                "until it's resolved.\n\n"
                "I'll send the details in a follow-up. Please confirm you're "
                "available to assist right now.\n\n"
                "— {ceo_first_name}"
            ),
            "urgency": "CRITICAL",
            "target_roles": ["Finance", "Executive Assistants", "Accounts Payable"],
            "difficulty": "Advanced — requires OSINT on CEO name and target relationship",
        },
        "mfa_verification": {
            "subject": "Security Alert: Unusual Login Detected on Your Account",
            "sender_name": "{company} Security Operations",
            "sender_domain_suggestion": "security-alerts.{target_domain}",
            "body": (
                "Hi {first_name},\n\n"
                "We detected a login attempt to your account from an unrecognized "
                "location ({fake_location}). If this was you, no action is needed.\n\n"
                "If this was NOT you, your account may be compromised. Please "
                "verify your identity immediately to secure your account:\n\n"
                "{phishing_link}\n\n"
                "This link expires in 30 minutes.\n\n"
                "— {company} Security Team"
            ),
            "urgency": "HIGH",
            "target_roles": ["All employees"],
            "difficulty": "Medium — pairs well with Evilginx2 for MFA capture",
        },
        "shared_document": {
            "subject": "{sender_name} shared a document with you",
            "sender_name": "{colleague_name}",
            "sender_domain_suggestion": "Spoof internal colleague email",
            "body": (
                "Hi {first_name},\n\n"
                "{colleague_name} has shared the following document with you:\n\n"
                "'{document_name}'\n\n"
                "Click to view: {phishing_link}\n\n"
                "— The {company} Team"
            ),
            "urgency": "LOW",
            "target_roles": ["All employees"],
            "difficulty": "Easy — looks like a SharePoint/Google Drive notification",
        },
    }

    def build_campaign_config(
        self,
        target_company: str,
        target_domain: str,
        pretext_type: str,
        target_list: list,
        lhost: str,
        lport: int = 80,
    ) -> dict:
        """
        Generate a complete phishing campaign configuration.
        Returns dict with all campaign parameters.
        """
        template = self.PRETEXT_TEMPLATES.get(pretext_type)
        if not template:
            return {"error": f"Unknown pretext type: {pretext_type}"}

        campaign = {
            "campaign_name": f"{target_company}_{pretext_type}_{datetime.now().strftime('%Y%m%d')}",
            "target_company": target_company,
            "target_domain": target_domain,
            "pretext_type": pretext_type,
            "urgency": template["urgency"],
            "target_roles": template["target_roles"],
            "infrastructure": {
                "phishing_domain_suggestion": template["sender_domain_suggestion"].format(
                    target_domain=target_domain,
                    company=target_company.lower().replace(" ", "")
                ),
                "landing_page_url": f"https://{lhost}:{lport}/login",
                "redirect_after_capture": f"https://www.{target_domain}",
                "ssl_required": True,
                "note": "Age the domain 30+ days before use. Set SPF/DKIM/DMARC."
            },
            "email_template": {
                "subject": template["subject"],
                "sender_name": template["sender_name"].format(company=target_company),
                "body_template": template["body"],
                "variables_needed": self._extract_variables(template["body"]),
            },
            "tracking": {
                "unique_links": True,
                "pixel_tracking": True,
                "capture_fields": ["username", "password"],
                "log_ip": True,
                "log_user_agent": True,
            },
            "gophish_setup": self._generate_gophish_steps(target_company, lhost, lport),
            "target_count": len(target_list),
            "targets": target_list[:5],  # Show first 5 as sample
            "legal_reminder": "Ensure written authorization covers phishing simulation.",
        }
        return campaign

    def _extract_variables(self, template_str: str) -> list:
        """Extract {variable} placeholders from a template."""
        import re
        return list(set(re.findall(r'\{(\w+)\}', template_str)))

    def _generate_gophish_steps(self, company: str, lhost: str, lport: int) -> list:
        return [
            "1. Launch GoPhish: ./gophish",
            "2. Login at https://localhost:3333 (default: admin / gophish)",
            "3. Sending Profiles → New Profile → configure SMTP relay",
            f"4. Landing Pages → Import Site → https://login.{company.lower()}.com",
            "5. Modify landing page to capture and redirect",
            "6. Email Templates → New Template → paste your phishing email",
            "7. Users & Groups → import target list CSV",
            "8. Campaigns → New Campaign → link template + page + profile + group",
            "9. Launch → monitor Results dashboard in real-time",
            "10. Export results CSV for engagement report",
        ]

    def generate_gophish_target_csv(self, targets: list) -> str:
        """Generate a GoPhish-compatible CSV from target list."""
        lines = ["First Name,Last Name,Email,Position"]
        for t in targets:
            lines.append(
                f"{t.get('first','')},{t.get('last','')},{t.get('email','')},{t.get('role','')}"
            )
        return "\n".join(lines)

    def teach(self, topic: str = "overview") -> str:
        """Return teaching content about phishing."""
        kb = SE_KNOWLEDGE_BASE.get("phishing_deep_dive", {})
        if topic == "overview":
            return (
                f"[ERR0RS] PHISHING — THE #1 INITIAL ACCESS VECTOR\n"
                f"{'='*54}\n"
                f"{kb.get('tldr', '')}\n\n"
                f"Types: {', '.join(kb.get('phishing_types', {}).keys())}\n\n"
                f"Tools: {', '.join(kb.get('tools', {}).keys())}\n\n"
                f"Type 'teach me phishing [type]' to go deeper on any area."
            )
        section = kb.get(topic) or kb.get('phishing_types', {}).get(topic)
        if section:
            return f"[ERR0RS] {topic.upper()}\n{'='*54}\n{section}"
        return f"[ERR0RS] Unknown phishing topic: {topic}"


# ═══════════════════════════════════════════════════════════════════════════
# VISHING SCRIPT GENERATOR
# Builds call scripts for authorized vishing engagements
# ═══════════════════════════════════════════════════════════════════════════

class VishingScriptGenerator:
    """
    Generates vishing call scripts for authorized SE engagements.
    Includes: hook, rapport, pretext, elicitation, close.
    """

    CALL_SCRIPTS = {
        "it_helpdesk": {
            "pretext": "IT Help Desk — Account Security Incident",
            "caller_id_spoof": "Internal extension (e.g., x5555 or x7777)",
            "script": {
                "hook": (
                    "Hello, this is {caller_name} calling from the IT Security team. "
                    "Am I speaking with {target_name}?"
                ),
                "rapport": (
                    "Hi {target_first_name}, thanks for picking up. I apologize for "
                    "interrupting your day — I know you're probably busy. "
                    "I'm going to keep this as brief as possible."
                ),
                "pretext": (
                    "We've detected some anomalous activity on your account over the "
                    "last couple hours. Our monitoring system flagged unusual login "
                    "patterns that could indicate a compromised credential. "
                    "We're reaching out to everyone in {department} as a precaution."
                ),
                "yes_ladder": [
                    "Can you confirm you're at your workstation right now?",
                    "And you're logged into your {company} account currently?",
                    "Great. And you haven't noticed anything unusual today — "
                    "any strange emails or pop-ups?",
                    "Okay, that's actually helpful. Let me pull up your account.",
                ],
                "elicitation": (
                    "I'm going to walk you through a quick verification process "
                    "so I can flag your account as confirmed on our end. "
                    "Can you confirm your username for me — just the part before the @?"
                ),
                "escalation_if_hesitant": (
                    "I completely understand the concern about verifying this — "
                    "that's actually a great security instinct. Here's what I can do: "
                    "I can send a verification code to your work email right now "
                    "so you can confirm who you're speaking with. "
                    "Would that help? [pause] Great. Check your inbox — "
                    "what does the code say?"
                    # Note: This pivots to credential capture via email link
                ),
                "close": (
                    "Perfect, I've got that noted. Your account is flagged as "
                    "verified on our end. You should receive a confirmation email "
                    "within the next few minutes — ticket number {fake_ticket}. "
                    "Thanks for your time, {target_first_name}. Have a good rest of your day."
                ),
            },
            "tips": [
                "Speak with confidence — hesitation kills credibility",
                "Use their name naturally, not robotically",
                "Have a 'supervisor' ready to escalate to if challenged",
                "If asked to call back on the main IT number — agree, then pivot",
                "Background noise (office sounds) increases believability",
            ],
        },
        "hr_verification": {
            "pretext": "HR — Payroll System Update",
            "caller_id_spoof": "HR department main line",
            "script": {
                "hook": (
                    "Hi, may I speak with {target_name}? "
                    "This is {caller_name} calling from Human Resources."
                ),
                "pretext": (
                    "We're making some updates to the payroll system ahead of "
                    "the upcoming pay cycle, and we need to verify a few details "
                    "for employees in {department}. This should only take a minute."
                ),
                "elicitation": (
                    "Can I confirm your employee ID with you? "
                    "I have {fake_id} on file — does that sound right?"
                    # Note: Bracketing technique — give wrong info to get real info
                ),
                "close": (
                    "Perfect. We're all set. Your direct deposit information "
                    "is confirmed on our end. You shouldn't see any disruption "
                    "to your next paycheck. Thanks for your time!"
                ),
            },
        },
        "security_audit": {
            "pretext": "Corporate Risk Management — Compliance Audit",
            "caller_id_spoof": "Corporate main line or unknown number",
            "script": {
                "hook": (
                    "Hello, is this {target_name}? "
                    "This is {caller_name} calling from Corporate Risk Management."
                ),
                "pretext": (
                    "We're conducting a quarterly security audit across all "
                    "business units, and your department has been selected for "
                    "a brief verification review. This has been signed off by "
                    "your VP, {vp_name}."
                ),
                "elicitation": (
                    "I just need to verify a few things on our end. "
                    "First — what system do you primarily use for {relevant_task}? "
                    "And how often would you say you access {target_system}?"
                    # Note: Gathering system intel for later technical attacks
                ),
            },
        },
    }

    def generate_script(
        self,
        pretext_type: str,
        caller_name: str,
        target_name: str,
        target_company: str,
        target_department: str = "your department",
        additional_intel: dict = None,
    ) -> dict:
        """
        Generate a populated vishing script for an authorized engagement.
        """
        template = self.CALL_SCRIPTS.get(pretext_type)
        if not template:
            return {"error": f"Unknown pretext type: {pretext_type}"}

        intel = additional_intel or {}
        target_first = target_name.split()[0]
        import random
        fake_ticket = f"INC-{random.randint(100000, 999999)}"
        fake_ext = f"x{random.randint(1000, 9999)}"

        script = template["script"].copy()
        variables = {
            "caller_name": caller_name,
            "target_name": target_name,
            "target_first_name": target_first,
            "company": target_company,
            "department": target_department,
            "fake_ticket": fake_ticket,
            "fake_ext": fake_ext,
            "fake_id": f"EMP-{random.randint(10000, 99999)}",
        }
        variables.update(intel)

        populated_script = {}
        for stage, content in script.items():
            if isinstance(content, str):
                try:
                    populated_script[stage] = content.format(**variables)
                except KeyError:
                    populated_script[stage] = content
            elif isinstance(content, list):
                populated_script[stage] = [
                    step.format(**variables) if isinstance(step, str) else step
                    for step in content
                ]

        return {
            "pretext": template["pretext"],
            "caller_id": template.get("caller_id_spoof", "Varies by pretext"),
            "script": populated_script,
            "tips": template.get("tips", []),
            "legal_note": "Authorized vishing engagements only. Record call if legally permitted.",
        }

    def teach(self) -> str:
        """Return vishing teaching content."""
        kb = SE_KNOWLEDGE_BASE.get("vishing", {})
        lines = [
            f"[ERR0RS] VISHING — VOICE-BASED SOCIAL ENGINEERING",
            "=" * 54,
            kb.get("tldr", ""),
            "",
            "WHY VOICE WORKS:",
            kb.get("why_voice_works", ""),
            "",
            "CALL FRAMEWORK:",
            kb.get("call_framework", ""),
            "",
            "PRETEXTS AVAILABLE: " + ", ".join(self.CALL_SCRIPTS.keys()),
            "",
            "Command: se_engine vishing --pretext it_helpdesk --target <name>",
        ]
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# PRETEXT BUILDER
# Constructs pretexts from OSINT input
# ═══════════════════════════════════════════════════════════════════════════

class PretextBuilder:
    """
    Builds social engineering pretexts from OSINT profile data.
    The better your OSINT, the more convincing the pretext.
    """

    def build_from_osint(self, osint_profile: dict) -> list:
        """
        Given an OSINT profile, generate ranked pretext recommendations.

        osint_profile keys:
          name, role, department, manager_name, company, company_size,
          industry, tenure, linkedin_activity, breach_data, personal_interests
        """
        recommendations = []
        role = osint_profile.get("role", "").lower()
        dept = osint_profile.get("department", "").lower()
        industry = osint_profile.get("industry", "").lower()

        # Finance roles → BEC / Wire fraud pretext
        if any(kw in role or kw in dept for kw in
               ["finance", "accounting", "accounts", "payable", "cfo", "controller"]):
            recommendations.append({
                "pretext": "Executive Wire Transfer (BEC)",
                "vector": "Email",
                "confidence": "HIGH",
                "rationale": "Finance roles routinely process wire transfers — BEC is highly effective",
                "requires": ["CEO/CFO name", "Target's manager name", "Ongoing transaction context"],
            })

        # IT roles → Vendor/System update pretext
        if any(kw in role or kw in dept for kw in
               ["it ", "sysadmin", "network", "infrastructure", "helpdesk", "security"]):
            recommendations.append({
                "pretext": "Vendor System Update / Maintenance Window",
                "vector": "Email + Phone",
                "confidence": "MEDIUM",
                "rationale": "IT staff expect vendor communication about system updates",
                "requires": ["Actual vendors the company uses (from LinkedIn/job postings)"],
            })

        # HR roles → Benefits/Payroll pretext
        if any(kw in role or kw in dept for kw in
               ["hr", "human resources", "people", "talent", "recruiter"]):
            recommendations.append({
                "pretext": "Benefits System Update / ATS Migration",
                "vector": "Email",
                "confidence": "HIGH",
                "rationale": "HR handles sensitive data and expects system communications",
                "requires": ["HR system name (Workday, BambooHR, etc.)"],
            })

        # Executive / C-suite → Targeted spear phish
        if any(kw in role for kw in ["ceo", "cfo", "ciso", "cto", "vp", "director", "president"]):
            recommendations.append({
                "pretext": "Board Document / Investor Communication",
                "vector": "Spear Phishing Email",
                "confidence": "HIGH",
                "rationale": "Executives receive sensitive board/investor comms regularly",
                "requires": ["Board member names", "Recent company filings or news"],
            })

        # New employee → Onboarding pretext
        if osint_profile.get("tenure", "").lower() in ["new", "recent", "< 1 year"]:
            recommendations.append({
                "pretext": "Onboarding System Access Setup",
                "vector": "Email",
                "confidence": "VERY HIGH",
                "rationale": "New employees expect system setup communications and don't know normal procedures",
                "requires": ["HR/IT onboarding system name"],
            })

        # Universal pretexts
        recommendations.append({
            "pretext": "IT Password Reset / Security Alert",
            "vector": "Email",
            "confidence": "MEDIUM",
            "rationale": "Works on all roles — everyone has IT credentials",
            "requires": ["Company email format", "Lookalike domain"],
        })

        return sorted(recommendations, key=lambda x: {
            "VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3
        }.get(x["confidence"], 4))


# ═══════════════════════════════════════════════════════════════════════════
# SE TEACH ENGINE
# Central teaching interface for all SE topics
# ═══════════════════════════════════════════════════════════════════════════

class SETeachEngine:
    """
    Teaching interface for all social engineering topics.
    Called by ERR0RS when operator asks to learn about SE.
    """

    TOPIC_MAP = {
        # Fundamental concepts
        "overview":           "why_human_variable",
        "intro":              "why_human_variable",
        "basics":             "why_human_variable",
        "human variable":     "why_human_variable",
        "psychology":         "why_human_variable",
        "cialdini":           "why_human_variable",
        "influence":          "why_human_variable",

        # Attack vectors
        "osint":              "osint_human_recon",
        "recon":              "osint_human_recon",
        "phishing":           "phishing_deep_dive",
        "spear phishing":     "phishing_deep_dive",
        "vishing":            "vishing",
        "smishing":           "vishing",
        "physical":           "physical_se",
        "pretexting":         "pretexting",
        "pretext":            "pretexting",
        "tailgating":         "physical_se",
        "impersonation":      "physical_se",
        "usb drop":           "physical_se",

        # Defense
        "defense":            "human_defense",
        "awareness":          "human_defense",
        "training":           "human_defense",
        "human firewall":     "human_defense",

        # Tools
        "tools":              "se_tools",
        "gophish":            "se_tools",
        "set":                "se_tools",
        "evilginx":           "se_tools",
    }

    def get_lesson(self, topic: str) -> str:
        """Return formatted lesson for a topic."""
        kb_key = self.TOPIC_MAP.get(topic.lower().strip())
        if not kb_key:
            # Fuzzy search
            for key in self.TOPIC_MAP:
                if topic.lower() in key or key in topic.lower():
                    kb_key = self.TOPIC_MAP[key]
                    break

        if not kb_key or kb_key not in SE_KNOWLEDGE_BASE:
            return self._unknown_topic(topic)

        entry = SE_KNOWLEDGE_BASE[kb_key]
        return self._format_lesson(entry)

    def _format_lesson(self, entry: dict) -> str:
        sep = "=" * 54
        dash = "-" * 54
        lines = [sep, f"  [ERR0RS TEACHES] {entry.get('title', 'Social Engineering')}", sep, ""]
        tldr = entry.get("tldr")
        if tldr:
            lines += [f"[TL;DR] {tldr}", ""]

        # Render all major string sections
        for key in ["the_truth", "the_psychology", "why_recon_first",
                    "call_framework", "pretext_framework",
                    "anatomy_of_effective_phish", "red_team_truth",
                    "why_training_fails", "red_team_vishing_workflow",
                    "physical_engagement_workflow", "red_team_notes"]:
            val = entry.get(key)
            if val:
                label = key.replace("_", " ").upper()
                lines += [dash, f"{label}:", val, ""]

        # Render sub-dictionaries
        for key in ["cialdini_principles", "attack_taxonomy", "phishing_types",
                    "tools", "pretexts", "voice_techniques", "pretext_categories",
                    "physical_tools", "defense_layers"]:
            val = entry.get(key)
            if isinstance(val, dict):
                label = key.replace("_", " ").upper()
                lines += [dash, f"{label}:"]
                for subkey, subval in val.items():
                    lines += [f"\n  [{subkey.upper()}]", f"  {subval}" if isinstance(subval, str) else str(subval)]
                lines.append("")

        lines += [sep, "Type 'teach me se [topic]' to go deeper.", sep]
        return "\n".join(lines)

    def _unknown_topic(self, topic: str) -> str:
        topics = ", ".join(self.TOPIC_MAP.keys())
        return (
            f"[ERR0RS] No lesson found for '{topic}'.\n"
            f"Available SE topics: {topics}\n"
            f"Try: 'teach me social engineering phishing'"
        )

    def list_topics(self) -> str:
        lines = ["[ERR0RS] SOCIAL ENGINEERING CURRICULUM", "=" * 54, ""]
        categories = {
            "Foundations": ["overview", "psychology", "cialdini"],
            "Reconnaissance": ["osint", "recon"],
            "Attack Vectors": ["phishing", "spear phishing", "vishing", "smishing", "physical", "usb drop", "pretexting"],
            "Tools": ["tools", "gophish", "set", "evilginx"],
            "Defense & Purple Team": ["defense", "awareness", "training", "human firewall"],
        }
        for cat, topics in categories.items():
            lines.append(f"  {cat}:")
            for t in topics:
                lines.append(f"    → teach me se {t}")
            lines.append("")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN SE ENGINE — Unified interface
# ═══════════════════════════════════════════════════════════════════════════

class SocialEngineeringEngine:
    """
    Main entry point for ERR0RS social engineering capabilities.
    Routes commands to the appropriate sub-module.
    """

    def __init__(self):
        self.phishing   = PhishingCampaignBuilder()
        self.vishing    = VishingScriptGenerator()
        self.pretext    = PretextBuilder()
        self.teach      = SETeachEngine()

    def route(self, command: str, params: dict = None) -> str:
        """Route an SE command to the correct sub-module."""
        params = params or {}
        cmd = command.lower().strip()

        if any(t in cmd for t in ["teach", "explain", "what is", "how does", "learn"]):
            topic = cmd
            for prefix in ["teach me", "explain", "what is", "how does", "learn about"]:
                topic = topic.replace(prefix, "").strip()
            topic = topic.replace("social engineering", "").replace("se", "").strip()
            if not topic:
                return self.teach.list_topics()
            return self.teach.get_lesson(topic)

        if "phishing campaign" in cmd or "build phishing" in cmd:
            return json.dumps(
                self.phishing.build_campaign_config(
                    target_company=params.get("company", "TargetCorp"),
                    target_domain=params.get("domain", "targetcorp.com"),
                    pretext_type=params.get("pretext", "it_password_reset"),
                    target_list=params.get("targets", []),
                    lhost=params.get("lhost", "10.10.14.5"),
                ), indent=2
            )

        if "vishing script" in cmd or "call script" in cmd:
            return json.dumps(
                self.vishing.generate_script(
                    pretext_type=params.get("pretext", "it_helpdesk"),
                    caller_name=params.get("caller", "Mike Torres"),
                    target_name=params.get("target", "Target Name"),
                    target_company=params.get("company", "TargetCorp"),
                    target_department=params.get("department", "IT"),
                ), indent=2
            )

        if "pretext" in cmd and "recommend" in cmd:
            profile = params.get("osint_profile", {})
            recs = self.pretext.build_from_osint(profile)
            return json.dumps(recs, indent=2)

        if "list" in cmd or "topics" in cmd or "curriculum" in cmd:
            return self.teach.list_topics()

        return self.teach.get_lesson(cmd)


# ── Module init ────────────────────────────────────────────────────────────
se = SocialEngineeringEngine()

def handle_se_command(command: str, params: dict = None) -> dict:
    """Entry point for errorz_launcher.py route_command()"""
    result = se.route(command, params)
    return {"status": "success", "source": "se_engine", "stdout": result}
