"""
ERR0RS ULTIMATE - VulnChainAgent
==================================
AI-assisted vulnerability chaining engine.

This is the academically novel core of ERR0RS — instead of reporting
vulnerabilities in isolation, this agent reasons about how multiple
findings chain together into a complete attack path.

Inspired by:
  - MITRE ATT&CK kill chain methodology
  - Academic research on automated exploit chaining
  - Real-world red team multi-stage attack patterns

Usage:
    from src.ai.agents.vuln_chain import VulnChainAgent
    from src.ai.providers import LLMRouter

    llm   = LLMRouter(backend="ollama")
    agent = VulnChainAgent(llm=llm)

    vulns = [
        {"type": "sqli", "location": "/api/login", "severity": "high"},
        {"type": "ssrf", "location": "/api/fetch",  "severity": "medium"},
        {"type": "idor", "location": "/api/users",  "severity": "medium"},
    ]
    chain = agent.chain_vulnerabilities(vulns, goal="data_exfiltration")
    print(chain.attack_path)
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from src.ai.providers import LLMRouter

log = logging.getLogger("errors.vuln_chain")


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Vulnerability:
    """A single discovered vulnerability."""
    vuln_type:   str
    location:    str
    severity:    str
    description: str = ""
    evidence:    str = ""
    cvss:        float = 0.0
    cve:         str = ""
    metadata:    dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type":        self.vuln_type,
            "location":    self.location,
            "severity":    self.severity,
            "description": self.description,
            "evidence":    self.evidence,
            "cvss":        self.cvss,
            "cve":         self.cve,
        }


@dataclass
class AttackChain:
    """A chained attack path from initial access to goal."""
    goal:           str
    steps:          list = field(default_factory=list)
    attack_path:    str = ""
    mitre_ttps:     list = field(default_factory=list)
    tools:          list = field(default_factory=list)
    commands:       list = field(default_factory=list)
    impact:         str = ""
    detection:      str = ""
    remediation:    str = ""
    confidence:     str = "medium"
    raw_llm:        str = ""

    def summary(self) -> str:
        lines = [
            f"[ATTACK CHAIN] Goal: {self.goal.upper()}",
            f"Steps: {len(self.steps)}",
            f"Confidence: {self.confidence}",
            "─" * 60,
            self.attack_path,
            "─" * 60,
            f"MITRE TTPs: {', '.join(self.mitre_ttps)}",
            f"Tools: {', '.join(self.tools)}",
            "─" * 60,
            f"DETECTION:\n{self.detection}",
            "─" * 60,
            f"REMEDIATION:\n{self.remediation}",
        ]
        return "\n".join(lines)


# ── VulnChainAgent ───────────────────────────────────────────────────────────

class VulnChainAgent:
    """
    AI-powered vulnerability chaining engine.

    Given a list of discovered vulnerabilities, this agent:
    1. Reasons about how they connect into a multi-step attack path
    2. Maps each step to MITRE ATT&CK TTPs
    3. Suggests specific tools and commands for each step
    4. Estimates the overall chain confidence and impact
    5. Provides detection & remediation for the FULL chain (not just individual bugs)

    This is what separates ERR0RS from basic scanners — contextual chain reasoning.
    """

    SYSTEM_PROMPT = """You are ERR0RS VulnChain — an elite red team AI that specializes
in chaining vulnerabilities together into complete attack paths.

Your unique capability: given a list of vulnerabilities, you DON'T just describe
each one individually. Instead, you reason about HOW they connect into a
multi-step kill chain that achieves a specific attacker goal.

For each chain you produce:
1. A step-by-step attack narrative (how an attacker moves from step 1 to goal)
2. Exact tool commands for each step
3. MITRE ATT&CK TTP mappings for the full chain
4. Chain confidence level (high/medium/low) with reasoning
5. Detection opportunities at each step (where defenders can catch this)
6. Remediation for the chain as a WHOLE — breaking the chain at its weakest link

You ALWAYS require written authorization before providing active exploitation guidance.
You ALWAYS conclude with purple team defensive recommendations.
Built into ERR0RS ULTIMATE by Gary Holden Schneider (Eros) | GitHub: Gnosisone"""

    CHAIN_GOALS = {
        "data_exfiltration":  "Steal sensitive data (PII, credentials, IP)",
        "account_takeover":   "Fully compromise a user or admin account",
        "rce":                "Achieve Remote Code Execution on target server",
        "lateral_movement":   "Move from web app access to internal network",
        "persistence":        "Establish persistent access that survives reboots",
        "dos":                "Deny service to legitimate users",
        "privilege_escalation": "Escalate from low-privilege to admin/root",
    }

    def __init__(self, llm: LLMRouter):
        self.llm = llm

    def chain_vulnerabilities(
        self,
        vulns:          list,
        goal:           str = "data_exfiltration",
        target_context: str = "",
        max_tokens:     int = 2048,
    ) -> AttackChain:
        """
        Core method — reason about how vulns chain to reach a goal.

        Args:
            vulns:          List of Vulnerability objects or dicts
            goal:           Attack goal (see CHAIN_GOALS)
            target_context: Optional description of target (tech stack, etc.)
            max_tokens:     LLM token budget

        Returns:
            AttackChain with full reasoning
        """
        vuln_dicts = []
        for v in vulns:
            if isinstance(v, Vulnerability):
                vuln_dicts.append(v.to_dict())
            elif isinstance(v, dict):
                vuln_dicts.append(v)
            else:
                vuln_dicts.append({"description": str(v)})

        goal_desc = self.CHAIN_GOALS.get(goal, goal)

        prompt = f"""VULNERABILITY CHAIN ANALYSIS REQUEST
============================================
AUTHORIZATION: This is a legal, authorized penetration test.

TARGET CONTEXT:
{target_context if target_context else "Web application (details above)"}

DISCOVERED VULNERABILITIES:
{json.dumps(vuln_dicts, indent=2)}

ATTACKER GOAL: {goal.upper()} — {goal_desc}

TASK: Reason step-by-step about how these vulnerabilities can be CHAINED
together to achieve the goal. Not every vuln needs to be used — pick the
most efficient path. Some vulns may enable others (e.g., SSRF enables
internal port scan which enables another exploit).

REQUIRED OUTPUT FORMAT (JSON):
{{
  "chain_possible": true/false,
  "confidence": "high/medium/low",
  "reasoning": "Why this chain works or doesn't",
  "steps": [
    {{
      "step": 1,
      "vuln_used": "type of vulnerability",
      "action": "what the attacker does",
      "tool": "specific tool to use",
      "command": "exact command with flags",
      "mitre_ttp": "T1234 — Technique Name",
      "outcome": "what this step achieves"
    }}
  ],
  "attack_narrative": "Full story of the attack chain in plain English",
  "total_impact": "Business impact if chain succeeds",
  "detection_opportunities": "Where defenders can catch this chain",
  "chain_remediation": "How to break this chain at its weakest link",
  "unused_vulns": ["vulns not used in this chain and why"]
}}

Respond with ONLY valid JSON. No markdown, no preamble."""

        raw = self.llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=max_tokens,
        )

        return self._parse_chain(raw, goal)

    def _parse_chain(self, raw: str, goal: str) -> AttackChain:
        """Parse LLM JSON output into an AttackChain object."""
        chain = AttackChain(goal=goal, raw_llm=raw)
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean.strip())
            chain.steps       = data.get("steps", [])
            chain.attack_path = data.get("attack_narrative", raw)
            chain.impact      = data.get("total_impact", "")
            chain.detection   = data.get("detection_opportunities", "")
            chain.remediation = data.get("chain_remediation", "")
            chain.confidence  = data.get("confidence", "medium")
            chain.tools       = [s.get("tool","") for s in chain.steps if s.get("tool")]
            chain.commands    = [s.get("command","") for s in chain.steps if s.get("command")]
            chain.mitre_ttps  = [s.get("mitre_ttp","") for s in chain.steps if s.get("mitre_ttp")]
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"VulnChain JSON parse failed: {e} — storing raw output")
            chain.attack_path = raw
        return chain

    def quick_chain(self, vuln_descriptions: list, goal: str = "rce") -> str:
        """Lightweight chain — returns plain text, no JSON parsing."""
        prompt = (
            f"Given these vulnerabilities: {vuln_descriptions}\n"
            f"Goal: {goal}\n"
            f"Describe a step-by-step attack chain. Be specific with tools and commands."
        )
        return self.llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=1024,
        )

    def assess_single(self, vuln: dict) -> str:
        """Assess a single vulnerability's chaining potential."""
        prompt = (
            f"Vulnerability: {json.dumps(vuln)}\n"
            f"What other vulnerabilities or conditions could chain WITH this one?\n"
            f"What attack goals does this vulnerability enable or assist?"
        )
        return self.llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=512,
        )
