"""
ERR0RS ULTIMATE - AI Providers Package
========================================
Exposes LLMRouter — a sync wrapper that works with all agents.

The providers package bridges the agent system (which calls llm.chat())
to the underlying LLM backends (Ollama, LM Studio, Claude, etc.).

Usage:
    from src.ai.providers import LLMRouter
    llm = LLMRouter(backend="ollama", model="llama3.2")
    response = llm.chat(system_prompt="...", user_message="...")
"""

import os
import json
import logging
from typing import Optional

log = logging.getLogger("errors.ai.providers")


class LLMRouter:
    """
    Synchronous LLM router for ERR0RS agents.
    Local-first: Ollama → LM Studio → Claude (opt-in with API key).

    Attributes:
        backend   : 'ollama' | 'lmstudio' | 'anthropic' | 'openai'
        model     : model string (e.g. 'llama3.2', 'claude-sonnet-4-5-20250929')
        api_key   : only used for remote providers
    """

    DEFAULT_MODELS = {
        "ollama":     os.getenv("OLLAMA_MODEL",    "llama3.2"),
        "lmstudio":   "local-model",
        "anthropic":  "claude-haiku-4-5-20251001",
        "openai":     "gpt-4o-mini",
    }

    DEFAULT_URLS = {
        "ollama":    os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "lmstudio":  "http://localhost:1234",
    }

    def __init__(
        self,
        backend:  str = None,
        model:    str = None,
        api_key:  str = None,
    ):
        # Auto-detect backend from env if not specified
        if backend is None:
            backend = os.getenv("LLM_BACKEND", "ollama")

        self.backend = backend.lower()
        self.model   = model or self.DEFAULT_MODELS.get(self.backend, "llama3.2")
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._base_url = self.DEFAULT_URLS.get(self.backend, "")

        log.info(f"LLMRouter init — backend={self.backend}, model={self.model}")

    # ── Core: synchronous chat ────────────────────────────────────────────────

    def chat(
        self,
        system_prompt: str = "",
        user_message:  str = "",
        max_tokens:    int = 1024,
        temperature:   float = 0.3,
    ) -> str:
        """
        Send a chat message. Returns the response string.
        Routes to the configured backend.
        """
        try:
            if self.backend in ("ollama", "lmstudio"):
                return self._chat_openai_compat(system_prompt, user_message,
                                                max_tokens, temperature)
            elif self.backend == "anthropic":
                return self._chat_anthropic(system_prompt, user_message, max_tokens)
            elif self.backend == "openai":
                return self._chat_openai(system_prompt, user_message, max_tokens, temperature)
            else:
                return f"[ERR0RS] Unknown backend: {self.backend}"
        except Exception as e:
            log.error(f"LLM chat error ({self.backend}): {e}")
            return f"[ERR0RS] LLM error: {e}"

    # ── Ollama / LM Studio (OpenAI-compatible) ───────────────────────────────

    def _chat_openai_compat(self, system_prompt: str, user_message: str,
                             max_tokens: int, temperature: float) -> str:
        try:
            import requests
        except ImportError:
            return "[ERR0RS] requests not installed. Run: pip install requests --break-system-packages"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        # Try OpenAI-compatible endpoint first
        url = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        try:
            r = requests.post(url, json=payload, timeout=90)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

        # Fallback: Ollama native /api/chat
        if self.backend == "ollama":
            url_native = f"{self._base_url}/api/chat"
            payload_native = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            r = requests.post(url_native, json=payload_native, timeout=90)
            r.raise_for_status()
            return r.json()["message"]["content"]

        return "[ERR0RS] LM Studio not responding."

    # ── Anthropic Claude ─────────────────────────────────────────────────────

    def _chat_anthropic(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        if not self.api_key:
            return "[ERR0RS] ANTHROPIC_API_KEY not set."
        try:
            import requests
        except ImportError:
            return "[ERR0RS] requests not installed."

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": user_message}],
        }
        if system_prompt:
            body["system"] = system_prompt

        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        return r.json()["content"][0]["text"]

    # ── OpenAI ───────────────────────────────────────────────────────────────

    def _chat_openai(self, system_prompt: str, user_message: str,
                     max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            return "[ERR0RS] OPENAI_API_KEY not set."
        try:
            import requests
        except ImportError:
            return "[ERR0RS] requests not installed."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        headers = {"Authorization": f"Bearer {self.api_key}",
                   "content-type": "application/json"}
        body = {"model": self.model, "messages": messages,
                "max_tokens": max_tokens, "temperature": temperature}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=body, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    # ── Utility ───────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Quick check if the configured backend is reachable."""
        if self.backend in ("anthropic", "openai"):
            return bool(self.api_key)
        try:
            import requests
            if self.backend == "ollama":
                r = requests.get(f"{self._base_url}/api/tags", timeout=3)
            else:
                r = requests.get(f"{self._base_url}/v1/models", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"LLMRouter(backend={self.backend!r}, model={self.model!r})"
