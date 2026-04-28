
# ── VulnChain Agent Registration (append to existing agents/__init__.py) ──
# Import and register VulnChainAgent in the factory

from src.ai.agents.vuln_chain import VulnChainAgent, Vulnerability, AttackChain

# Add to AGENT_REGISTRY in agents/__init__.py
# AGENT_REGISTRY["vuln_chain"] = VulnChainAgent  # Added below via patch

__vuln_chain_exports__ = ["VulnChainAgent", "Vulnerability", "AttackChain"]
