#!/usr/bin/env python3
"""
ERR0RS ULTIMATE — Social Engineering Module
============================================
Phishing email generators, pretexting frameworks, vishing scripts,
and open-source intelligence gathering for targeted attacks.

PHILOSOPHY: Social engineering is the most common initial access vector
in real breaches. Understanding it = understanding how to defend against it.
Every technique here comes with detection and defense guidance.

Integrates: SET (Social Engineer Toolkit), GoPhish, theHarvester, Maltego

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import subprocess
import shutil
import os
import sys
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


@dataclass
class SEResult:
    technique: str
    command: str = ""
    output: str = ""
    success: bool = False
    teach: str = ""
    defend: str = ""
    content: str = ""  # generated templates / scripts


def _run(cmd: str, timeout: int = 30) -> tuple:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip(), p.stderr.strip(), p.returncode
    except Exception as e:
        return "", str(e), 1


def _tool(name: str) -> bool:
    return shutil.which(name) is not None


# ─────────────────────────────────────────────────────────────────────
# OSINT FOR TARGET PROFILING
# ─────────────────────────────────────────────────────────────────────

class OSINTGathering:
    """Gather target information to craft convincing attacks."""

    def harvester_emails(self, domain: str, limit: int = 50) -> SEResult:
        """Find employee emails for a target domain using theHarvester."""
        if _tool("theHarvester"):
            cmd = f"theHarvester -d {domain} -b all -l {limit} 2>/dev/null"
        else:
            cmd = f"# Install: sudo apt install theharvester -y"
        out, err, rc = _run(cmd, timeout=60)
        return SEResult(
            technique="OSINT — Email Harvesting (theHarvester)",
            command=cmd,
            output=out or "[ERR0RS] theHarvester not installed or no results.",
            success=bool(out) and "@" in out,
            content="\n".join(re.findall(r"[\w.+-]+@[\w-]+\.[a-z]+", out or "")),
            teach=(
                "theHarvester queries: Google, Bing, LinkedIn, Hunter.io, "
                "certificate transparency logs, and DNS records to find employee "
                "email addresses. These become the target list for phishing campaigns. "
                "Email formats (firstname.lastname@domain.com) reveal naming conventions "
                "for username enumeration against VPN, OWA, and other portals."
            ),
            defend=(
                "Use email alias systems so real names aren't exposed in addresses. "
                "Google yourself and your employees — know what attackers will find. "
                "Disable directory harvesting on mail servers (SMTP VRFY/EXPN). "
                "Employee awareness training: recognize targeted phishing."
            )
        )

    def linkedin_recon(self, company: str) -> SEResult:
        """Generate LinkedIn OSINT guidance for target profiling."""
        content = (
            f"# LinkedIn Recon: {company}\n\n"
            f"## Search Queries:\n"
            f"  site:linkedin.com/in '{company}' employees\n"
            f"  site:linkedin.com/pub {company}\n\n"
            f"## Tools:\n"
            f"  - linkedin2username (GitHub: initstring/linkedin2username)\n"
            f"    → scrapes employee names → generates username wordlists\n"
            f"  - CrossLinked (GitHub: m8sec/CrossLinked)\n"
            f"    → enumerate employees from LinkedIn without API\n\n"
            f"## What to collect:\n"
            f"  • Names + titles (who has admin access?)\n"
            f"  • Technologies mentioned in profiles (what's their stack?)\n"
            f"  • Current projects (context for spear phishing)\n"
            f"  • Recent job postings (reveals internal tools and infrastructure)\n"
            f"  • Vendors/partners mentioned (third-party phishing vector)\n"
        )
        return SEResult(
            technique="OSINT — LinkedIn Employee Profiling",
            command=f"# linkedin2username -c {company}",
            content=content,
            output=content,
            success=True,
            teach=(
                "LinkedIn is the world's largest corporate org chart. "
                "Job postings reveal technology stacks (Splunk admin needed → they use Splunk). "
                "Employee titles reveal who has privileged access. "
                "crosslinked generates username wordlists from scraped names — "
                "feed directly into password spraying or phishing campaigns."
            ),
            defend=(
                "Restrict LinkedIn profile visibility for IT/security staff. "
                "Audit job postings for technology disclosures. "
                "Use generic technology names in job postings. "
                "Employee awareness: LinkedIn oversharing aids attackers."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# PHISHING EMAIL GENERATION
# ─────────────────────────────────────────────────────────────────────

class PhishingTemplates:
    """
    Generate convincing phishing email templates for authorized campaigns.
    All templates require operator to customize and are clearly for testing.
    """

    PRETEXT_TEMPLATES = {
        "password_reset": {
            "subject": "Action Required: Your {company} password will expire in 24 hours",
            "body": """Dear {name},

Our security systems have flagged your account for a required password reset.

Your current password expires in 24 hours. Please click the link below to update
your credentials and maintain access to your {company} account.

[Reset Password Now] → {lure_url}

If you do not reset your password, you will be locked out of your account.

IT Security Team
{company}

This is an automated security notification. Please do not reply to this email.
""",
            "teach": "Password expiry urgency is the #1 phishing pretext. Creates immediate panic without thinking."
        },

        "ceo_fraud": {
            "subject": "Quick request — confidential",
            "body": """Hi {name},

I'm in a meeting right now and can't talk. I need you to process an urgent wire
transfer before end of day. Please treat this as confidential until I get back.

Amount: {amount}
Account: {account_info}
Reference: Q4 acquisition (confidential)

I'll explain everything later. Can you confirm receipt of this email?

{ceo_name}
Sent from iPhone
""",
            "teach": "BEC (Business Email Compromise) — impersonates C-suite for financial fraud. $43B lost globally."
        },

        "it_helpdesk": {
            "subject": "[IT Support] Mandatory security software installation required",
            "body": """Dear {name},

The IT department is deploying a mandatory security update across all company devices.
You must install this update by {deadline} or your computer will be restricted.

Please download and run the installer from our secure portal:
{lure_url}

Note: You will need to temporarily disable your antivirus during installation.
This is normal and expected for this security update.

IT Helpdesk
{company} Technology Services
""",
            "teach": "IT authority phishing + AV disable instruction = social engineer AND technical bypass in one."
        },

        "sharepoint_share": {
            "subject": "{sender_name} shared a file with you",
            "body": """
{sender_name} ({sender_email}) has shared a document with you on {company} SharePoint.

Document: Q4 Financial Report - CONFIDENTIAL.xlsx

[Open in SharePoint] → {lure_url}

This link will expire in 7 days.

Microsoft SharePoint
""",
            "teach": "Mimics legitimate SharePoint notifications exactly. Hard to distinguish without sender inspection."
        },

        "voicemail": {
            "subject": "You have a new voicemail from +1 (405) {phone}",
            "body": """You received a voicemail on {date} at {time}.

Duration: 0:47
Caller: Unknown (+1-405-{phone})

[Listen to Voicemail] → {lure_url}

This message will be deleted in 7 days.

{company} Unified Communications
""",
            "teach": "Voicemail phishing triggers curiosity. Who called? Click rate is consistently high."
        },
    }

    def generate_template(self, template_key: str, variables: dict) -> SEResult:
        """Generate a filled phishing template for testing."""
        if template_key not in self.PRETEXT_TEMPLATES:
            available = ", ".join(self.PRETEXT_TEMPLATES.keys())
            return SEResult(
                technique="Phishing Template",
                output=f"[ERR0RS] Unknown template '{template_key}'. Available: {available}",
                success=False
            )

        tmpl = self.PRETEXT_TEMPLATES[template_key]
        try:
            subject = tmpl["subject"].format(**variables)
            body = tmpl["body"].format(**variables)
        except KeyError as e:
            subject = tmpl["subject"]
            body = tmpl["body"]
            body += f"\n\n[ERR0RS NOTE: Missing variable: {e}. Fill in before use.]"

        content = f"SUBJECT: {subject}\n\n{'='*60}\n\n{body}"
        return SEResult(
            technique=f"Phishing Template — {template_key.replace('_', ' ').title()}",
            content=content,
            output=content,
            success=True,
            teach=tmpl.get("teach", ""),
            defend=(
                "Email security gateways (Proofpoint, Mimecast) analyze sender reputation. "
                "DMARC/DKIM/SPF validation catches spoofed sender domains. "
                "User training: verify unexpected requests via phone call to known number. "
                "MFA on all accounts: credential theft alone doesn't complete the attack."
            )
        )

    def list_templates(self) -> SEResult:
        """List available phishing templates."""
        listing = "\n".join(
            f"  {k}: {v['subject'][:60]}..."
            for k, v in self.PRETEXT_TEMPLATES.items()
        )
        return SEResult(
            technique="Phishing Templates — Available List",
            output=f"[ERR0RS] Available phishing templates:\n{listing}",
            content=listing,
            success=True,
            teach="Each template targets a different pretext. Choose based on target organization's context."
        )

    def spear_phish_profile(self, target_name: str, target_title: str,
                             target_company: str, target_intel: str) -> SEResult:
        """Generate a targeted spear phishing guidance profile."""
        content = (
            f"SPEAR PHISHING PROFILE: {target_name}\n"
            f"{'='*50}\n"
            f"Target : {target_name} ({target_title})\n"
            f"Company: {target_company}\n"
            f"Intel  : {target_intel}\n\n"
            f"RECOMMENDED PRETEXTS:\n"
            f"  1. Reference a specific project/event from their LinkedIn\n"
            f"  2. Impersonate their direct manager or a vendor they use\n"
            f"  3. Time around a known corporate event (M&A, reorg, audit)\n\n"
            f"DELIVERY OPTIONS:\n"
            f"  Email → use password_reset or sharepoint_share template\n"
            f"  LinkedIn InMail → recruiter approach for credential harvesting\n"
            f"  SMS (smishing) → IT helpdesk 2FA bypass pretext\n\n"
            f"PAYLOAD OPTIONS:\n"
            f"  Credential harvesting page (clone target's SSO login)\n"
            f"  Office macro document (enable macros for 'security')\n"
            f"  LNK file (shortcut that runs malicious code)\n"
            f"  HTML smuggling (bypass email gateways)\n"
        )
        return SEResult(
            technique="Spear Phishing — Targeted Campaign Profile",
            output=content,
            content=content,
            success=True,
            teach=(
                "Spear phishing uses specific personal details to build credibility. "
                "Mass phishing has 3-5% click rates. Spear phishing: 70%+. "
                "Reference their recent LinkedIn post, a project they mentioned, "
                "their manager's name — anything that proves you 'know' them. "
                "The more personalized, the higher the success rate."
            ),
            defend=(
                "Security awareness training + phishing simulations. "
                "Report a phish button in email client — fast alerting. "
                "MFA: even if credentials are captured, account stays protected. "
                "Privileged users: separate hardened workstations for sensitive access."
            )
        )


# ─────────────────────────────────────────────────────────────────────
# VISHING (VOICE PHISHING) SCRIPTS
# ─────────────────────────────────────────────────────────────────────

class VishingScripts:

    SCRIPTS = {
        "it_helpdesk_call": """VISHING SCRIPT: IT Helpdesk
=============================
PRETEXT: IT calling about a security alert on their machine.

[OPENER]
"Hi, this is [NAME] calling from the IT security desk. Am I speaking with [TARGET]?
Great. I'm reaching out because our monitoring system flagged some unusual activity
on your workstation earlier today. Do you have a moment?"

[BUILD CREDIBILITY]
"We're seeing what appears to be an unauthorized login attempt from [CITY/IP].
Did you log in from [LOCATION] around [TIME] today?"
→ If yes: "Good, that explains it — just wanted to confirm it was you."
→ If no: "That's concerning. We need to secure your account right now."

[OBTAIN GOAL]
"To protect your account, I'm going to need to verify your identity.
Can you confirm the email address on your account?
[Pause] And I'll need to send you a verification code — what's the best number?"

[2FA BYPASS VARIANT]
"You should receive a code in the next 30 seconds. Once you get it, read it to me
so I can verify your identity on our end."
→ This captures the 2FA code in real-time = account takeover even with MFA.

[CLOSE]
"Perfect. Your account is secured. You'll receive a confirmation email shortly.
Have a great day and call us if you notice anything suspicious."

TEACH: Real-time phishing (RTP) bypasses MFA by collecting OTP codes during the call.
""",
        "help_desk_reset": """VISHING SCRIPT: Password Reset Social Engineering
==================================================
PRETEXT: User calling helpdesk, impersonating an employee.

GOAL: Get helpdesk to reset password without proper verification.

"Hi, this is [TARGET EMPLOYEE NAME]. I'm locked out of my account.
I'm traveling right now and need to access [SYSTEM] urgently for a client presentation."

PRESSURE TACTICS:
- "My manager [MANAGER NAME] is waiting — this is urgent"
- "I don't have access to my work phone for verification — I'm overseas"
- "Can you just reset it temporarily? I'll update everything when I'm back"

COUNTER VERIFICATION:
If asked for employee ID: Use LinkedIn profile info, company directory
If asked security questions: "I haven't set those up yet" / give OSINT-gathered info

TEACH: Helpdesk is the weakest link — pressure + authority bypass verification steps.
DEFEND: Strict identity verification policy that cannot be waived. No exceptions for urgency.
"""
    }

    def get_script(self, script_key: str) -> SEResult:
        if script_key not in self.SCRIPTS:
            return SEResult(
                technique="Vishing Script",
                output=f"[ERR0RS] Unknown script. Available: {', '.join(self.SCRIPTS.keys())}",
                success=False
            )
        return SEResult(
            technique=f"Vishing Script — {script_key.replace('_', ' ').title()}",
            content=self.SCRIPTS[script_key],
            output=self.SCRIPTS[script_key],
            success=True,
            teach="Vishing (voice phishing) has 3x higher success rate than email phishing.",
            defend="Security awareness training specifically covering phone-based attacks. Strict helpdesk verification SOP."
        )


# ─────────────────────────────────────────────────────────────────────
# MASTER CONTROLLER
# ─────────────────────────────────────────────────────────────────────

class SocialEngineeringController:

    def __init__(self):
        self.osint     = OSINTGathering()
        self.phishing  = PhishingTemplates()
        self.vishing   = VishingScripts()

    def run(self, action: str, params: dict = None) -> SEResult:
        params = params or {}
        a = action.strip().lower()

        dispatch = {
            "harvest_emails":    lambda: self.osint.harvester_emails(params.get("domain", ""), params.get("limit", 50)),
            "linkedin_recon":    lambda: self.osint.linkedin_recon(params.get("company", "")),
            "list_templates":    lambda: self.phishing.list_templates(),
            "phish_template":    lambda: self.phishing.generate_template(
                params.get("template", "password_reset"),
                params.get("variables", {"name": "[NAME]", "company": "[COMPANY]", "lure_url": "https://lure.example.com"})
            ),
            "spear_phish":       lambda: self.phishing.spear_phish_profile(
                params.get("name", ""), params.get("title", ""), params.get("company", ""), params.get("intel", "")
            ),
            "vishing_helpdesk":  lambda: self.vishing.get_script("it_helpdesk_call"),
            "vishing_reset":     lambda: self.vishing.get_script("help_desk_reset"),
        }

        if a in dispatch:
            return dispatch[a]()

        return SEResult(
            technique="Unknown",
            output=f"[ERR0RS] Unknown SE action '{a}'. Valid: {', '.join(dispatch.keys())}",
            success=False
        )


SE_WIZARD_MENU = {
    "title": "ERR0RS // SOCIAL ENGINEERING WIZARD",
    "options": [
        {"key": "1", "label": "Email Harvest — theHarvester (domain)",       "action": "harvest_emails"},
        {"key": "2", "label": "LinkedIn Recon — Employee Profiling",          "action": "linkedin_recon"},
        {"key": "3", "label": "List Phishing Templates",                      "action": "list_templates"},
        {"key": "4", "label": "Generate Phishing Email Template",             "action": "phish_template"},
        {"key": "5", "label": "Spear Phishing — Targeted Campaign Profile",   "action": "spear_phish"},
        {"key": "6", "label": "Vishing Script — IT Helpdesk (MFA Bypass)",    "action": "vishing_helpdesk"},
        {"key": "7", "label": "Vishing Script — Helpdesk Password Reset",     "action": "vishing_reset"},
    ]
}

if __name__ == "__main__":
    ctrl = SocialEngineeringController()
    print("[ERR0RS] Social Engineering Module OK")
    r = ctrl.run("list_templates")
    print(r.output)
