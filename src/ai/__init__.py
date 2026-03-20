"""
ERR0RS ULTIMATE - AI Package
==============================
Central AI subsystem: LLM routing + agent management + RAG knowledge retrieval.

Quick start:
    from src.ai import ERR0RSAI

    ai = ERR0RSAI(backend="ollama")           # Pi5 / school build
    ai = ERR0RSAI(backend="anthropic")        # Personal build (needs ANTHROPIC_API_KEY)

    # Ask any agent
    print(ai.ask("How do I enumerate SMB shares?", agent="red_team"))
    print(ai.ask("How do I harden SMB?",           agent="blue_team"))

    # RAG-powered ask (searches knowledge base first)
    print(ai.ask_with_context("What is the CIA triad?"))
"""

import os
import logging
from typing import Optional

log = logging.getLogger("errors.ai")

from src.ai.providers import LLMRouter
from src.ai.agents   import create_agent, list_agents, BaseAgent


class ERR0RSAI:
    """
    Main AI interface for ERR0RS ULTIMATE.
    Combines LLM routing, agent selection, and RAG knowledge retrieval.

    Architecture:
        ERR0RSAI
        ├── LLMRouter      (Ollama or Anthropic)
        ├── Agents         (Red Team, Blue Team, Bug Bounty, Malware)
        └── KnowledgeBase  (ChromaDB RAG — optional, falls back to keyword)
    """

    def __init__(
        self,
        backend: str = None,
        model:   str = None,
        api_key: str = None,
        knowledge_dir: str = "./errors_knowledge_db",
        auto_ingest: bool = True,
    ):
        self.llm = LLMRouter(backend=backend, model=model, api_key=api_key)
        self._agents: dict = {}
        self._kb = None
        self._kb_available = False

        if auto_ingest:
            self._init_knowledge_base(knowledge_dir)

        log.info(f"ERR0RS AI ready — backend={self.llm.backend}, model={self.llm.model}")

    # ── Knowledge Base ───────────────────────────────────────────────────────

    def _init_knowledge_base(self, knowledge_dir: str):
        """Initialize ChromaDB knowledge base (graceful fallback if not installed)."""
        try:
            from src.ai.knowledge import ERR0RSKnowledgeBase
            self._kb = ERR0RSKnowledgeBase(persist_dir=knowledge_dir)
            self._kb.ingest()
            self._kb_available = True
            log.info("Knowledge base initialized (ChromaDB)")
        except ImportError:
            log.warning("ChromaDB not installed — knowledge search unavailable.")
            log.warning("Install: pip install chromadb sentence-transformers --break-system-packages")
        except Exception as e:
            log.warning(f"Knowledge base init failed: {e}")

    def search_knowledge(self, query: str, n: int = 4) -> list:
        """Search the RAG knowledge base. Returns list of relevant chunks."""
        if self._kb_available and self._kb:
            return self._kb.search(query, n_results=n)
        return []

    # ── Agent Management ─────────────────────────────────────────────────────

    def get_agent(self, agent_type: str = "red_team") -> BaseAgent:
        """Get (or create) an agent by type. Agents are cached after first creation."""
        if agent_type not in self._agents:
            self._agents[agent_type] = create_agent(agent_type, self.llm)
        return self._agents[agent_type]

    def ask(self, question: str, agent: str = "red_team", max_tokens: int = 1024) -> str:
        """Ask a question to a specific agent (no knowledge base lookup)."""
        return self.get_agent(agent).ask(question, max_tokens=max_tokens)

    def ask_with_context(
        self,
        question:   str,
        agent:      str = "red_team",
        n_context:  int = 4,
        max_tokens: int = 1024,
    ) -> dict:
        """
        RAG-powered ask: search knowledge base first, inject context, then ask LLM.
        Returns dict with 'answer' and 'sources' keys.
        """
        chunks  = self.search_knowledge(question, n=n_context)
        context = ""
        sources = []

        for chunk in chunks:
            title = chunk.get("metadata", {}).get("title", "Knowledge")
            context += f"\n--- {title} ---\n{chunk['content']}\n"
            sources.append(title)

        answer = self.get_agent(agent).ask(question, context=context, max_tokens=max_tokens)
        return {"answer": answer, "sources": sources}

    # ── Status ───────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return current AI subsystem status."""
        return {
            "backend":            self.llm.backend,
            "model":              self.llm.model,
            "llm_available":      self.llm.is_available(),
            "knowledge_base":     self._kb_available,
            "available_agents":   list_agents(),
            "loaded_agents":      list(self._agents.keys()),
        }

    def __repr__(self) -> str:
        return f"ERR0RSAI(backend={self.llm.backend!r}, model={self.llm.model!r})"


# ── Convenience exports ───────────────────────────────────────────────────────

__all__ = ["ERR0RSAI", "LLMRouter", "create_agent", "list_agents"]
