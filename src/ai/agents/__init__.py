"""
ERR0RS ULTIMATE - AI Agent Package
=====================================
Multi-agent system modeled on the NeuroSploit architecture.

Agents:
    RedTeamAgent      — offensive ops, tool guidance, exploit suggestions
    BlueTeamAgent     — defensive analysis, hardening advice, detection guidance
    BugBountyAgent    — vulnerability discovery, OWASP focus, report writing
    MalwareAnalyst    — sample analysis, IOC extraction, YARA rules

All agents share one LLMRouter and one knowledge base.
Swap the LLM backend without touching agent logic.

Usage:
    from src.ai.agents import RedTeamAgent
    from src.ai.providers import LLMRouter

    llm = LLMRouter(backend="ollama")
    agent = RedTeamAgent(llm=llm)
    result = agent.ask("How do I escalate privileges on this Linux box?")
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.ai.providers import LLMRouter

# ── Base Agent ──────────────────────────────────────────────────────────────

class BaseAgent:
    """
    All agents inherit from this. Provides the ask() interface and
    injects the system prompt that defines the agent's role.
    """

    SYSTEM_PROMPT = "You are ERR0RS, an AI-powered security assistant."

    def __init__(self, llm: LLMRouter):
        self.llm = llm

    def ask(self, question: str, context: str = "", max_tokens: int = 1024) -> str:
        """
        Ask this agent a question.
        Optionally pass context (RAG results, tool output, etc.).
        """
        user_message = question
        if context:
            user_message = (
                f"CONTEXT (from knowledge base or tool output):\n{context}\n\n"
                f"QUESTION: {question}"
            )
        return self.llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=max_tokens,
        )

    def __repr__(self):
        return f"{self.__class__.__name__}(backend={self.llm.backend!r})"


# ── Red Team Agent ───────────────────────────────────────────────────────────

class RedTeamAgent(BaseAgent):
    """
    Offensive security specialist. Guides tool usage, exploitation techniques,
    and post-exploitation methodology. Always requires authorization confirmation.
    """
    SYSTEM_PROMPT = """You are ERR0RS Red Team Agent — an elite offensive security AI
built into the ERR0RS ULTIMATE penetration testing framework.

Your role: guide penetration testers through reconnaissance, exploitation,
privilege escalation, lateral movement, and post-exploitation.

Rules you ALWAYS follow:
1. Before suggesting any active exploitation, confirm the tester has written authorization.
2. Explain WHAT a technique does and WHY before showing HOW.
3. Give exact commands with correct flags and syntax.
4. Think in phases: Recon → Scan → Exploit → Post-Ex → Report.
5. Purple team mindset — always mention the defensive counter to each attack.

You are running locally on the tester's machine. All data stays on device.
Built by Gary Holden Schneider (Eros) | GitHub: Gnosisone"""


# ── Blue Team Agent ──────────────────────────────────────────────────────────

class BlueTeamAgent(BaseAgent):
    """
    Defensive security specialist. Analyzes findings, recommends hardening,
    explains detection strategies, and helps write remediation guidance.
    """
    SYSTEM_PROMPT = """You are ERR0RS Blue Team Agent — a defensive security AI
built into the ERR0RS ULTIMATE framework.

Your role: analyze security findings, recommend hardening steps,
explain detection strategies, and help defenders understand attack techniques
so they can build better defenses.

Your approach:
1. For every attack technique, explain the defensive counter.
2. Prioritize remediations by business risk (Critical → High → Medium → Low).
3. Give specific, actionable hardening steps — not vague advice.
4. Reference industry frameworks: NIST, CIS Benchmarks, MITRE ATT&CK.
5. Always consider the defender's real-world constraints (budget, complexity, downtime).

Built by Gary Holden Schneider (Eros) | GitHub: Gnosisone"""


# ── Bug Bounty Agent ─────────────────────────────────────────────────────────

class BugBountyAgent(BaseAgent):
    """
    Bug bounty and web application specialist. OWASP Top 10 focused,
    helps with vulnerability discovery, impact assessment, and report writing.
    """
    SYSTEM_PROMPT = """You are ERR0RS Bug Bounty Agent — a web application security AI
built into the ERR0RS ULTIMATE framework.

Your role: guide bug bounty hunters and web app pentesters through
vulnerability discovery, impact assessment, and professional report writing.

Your focus areas:
1. OWASP Top 10 vulnerabilities and how to find them.
2. API security testing (REST, GraphQL, SOAP).
3. Business logic flaws — not just technical bugs.
4. Writing clear, impactful bug reports that get triaged (not dismissed).
5. Understanding CVSS scoring and how to justify severity ratings.

Always distinguish between finding a bug and proving its real-world impact.
Proof of concept + business impact = a well-paid bounty.

Built by Gary Holden Schneider (Eros) | GitHub: Gnosisone"""


# ── Malware Analyst Agent ────────────────────────────────────────────────────

class MalwareAnalystAgent(BaseAgent):
    """
    Malware analysis and threat intelligence specialist.
    Helps with static/dynamic analysis, IOC extraction, and YARA rules.
    """
    SYSTEM_PROMPT = """You are ERR0RS Malware Analyst Agent — a threat intelligence AI
built into the ERR0RS ULTIMATE framework.

Your role: assist with malware analysis, indicator extraction,
threat attribution, and detection rule creation.

Your capabilities:
1. Static analysis: file headers, strings extraction, entropy analysis, imports.
2. Dynamic analysis: behavioral indicators, network IOCs, registry changes.
3. YARA rule creation for detection.
4. MITRE ATT&CK technique mapping.
5. Threat actor TTPs and campaign attribution.

IMPORTANT: Analysis is for DEFENSIVE purposes — understanding threats to defend against them.
All analysis should conclude with detection and prevention recommendations.

Built by Gary Holden Schneider (Eros) | GitHub: Gnosisone"""


# ── Agent Factory ────────────────────────────────────────────────────────────

from src.ai.agents.vuln_chain import VulnChainAgent

AGENT_REGISTRY = {
    "red_team":       RedTeamAgent,
    "blue_team":      BlueTeamAgent,
    "bug_bounty":     BugBountyAgent,
    "malware":        MalwareAnalystAgent,
    "vuln_chain":     VulnChainAgent,
}


def create_agent(agent_type: str, llm: LLMRouter) -> BaseAgent:
    """
    Factory function — create an agent by name.

    Args:
        agent_type: 'red_team' | 'blue_team' | 'bug_bounty' | 'malware'
        llm: configured LLMRouter instance

    Returns:
        Agent instance ready to use

    Example:
        llm   = LLMRouter(backend="ollama")
        agent = create_agent("red_team", llm)
        print(agent.ask("How do I enumerate SMB shares?"))
    """
    cls = AGENT_REGISTRY.get(agent_type)
    if cls is None:
        raise ValueError(
            f"Unknown agent type: '{agent_type}'. "
            f"Available: {list(AGENT_REGISTRY.keys())}"
        )
    return cls(llm=llm)


def list_agents() -> list:
    """Return names of all available agents."""
    return list(AGENT_REGISTRY.keys())
