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

# ── Load .env so OLLAMA_MODEL / LLM_BACKEND are available ────────────────────
try:
    from dotenv import load_dotenv as _load_dotenv
    _root = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):                          # walk up to repo root
        _env = os.path.join(_root, ".env")
        if os.path.isfile(_env):
            _load_dotenv(_env, override=False)
            break
        _root = os.path.dirname(_root)
except ImportError:
    pass

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

        # Resolve defaults at instantiation time (after .env is loaded), not at class-definition time
        _default_models = {
            "ollama":    os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
            "lmstudio":  "local-model",
            "anthropic": "claude-haiku-4-5-20251001",
            "openai":    "gpt-4o-mini",
        }
        _default_urls = {
            "ollama":   os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "lmstudio": "http://localhost:1234",
        }

        self.model     = model or _default_models.get(self.backend, "qwen2.5-coder:7b")
        self.api_key   = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        self._base_url = _default_urls.get(self.backend, "")

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
            if self.backend == "ollama":
                return self._chat_ollama_generate(system_prompt, user_message,
                                                  max_tokens, temperature)
            elif self.backend == "lmstudio":
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

    # ── Ollama /api/generate — primary Pi 5 path ─────────────────────────────

    def _chat_ollama_generate(self, system_prompt: str, user_message: str,
                               max_tokens: int, temperature: float) -> str:
        try:
            import requests
        except ImportError:
            return "[ERR0RS] requests not installed."

        # Build a flat prompt — /api/generate doesn't use message arrays
        prompt = ""
        if system_prompt:
            prompt += f"[SYSTEM]\n{system_prompt}\n\n"
        prompt += f"[USER]\n{user_message}\n\n[ASSISTANT]\n"

        try:
            r = requests.post(
                f"{self._base_url}/api/generate",
                json={
                    "model":   self.model,
                    "prompt":  prompt,
                    "stream":  False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
                timeout=180,
            )
            r.raise_for_status()
            response = r.json().get("response", "").strip()
            if response:
                return response
        except Exception as e:
            log.error(f"LLM chat error (ollama): {e}")

        return "[ERR0RS] Ollama not responding — is it running? (ollama serve)"

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
            r = requests.post(url, json=payload, timeout=180)
            r.raise_for_status()
            result = r.json()["choices"][0]["message"]["content"]
            if result:
                return result
        except Exception:
            pass

        # Fallback 1: Ollama native /api/chat
        if self.backend == "ollama":
            try:
                url_native = f"{self._base_url}/api/chat"
                payload_native = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }
                r = requests.post(url_native, json=payload_native, timeout=180)
                r.raise_for_status()
                result = r.json()["message"]["content"]
                if result:
                    return result
            except Exception:
                pass

            # Fallback 2: /api/generate — most compatible on ARM/Pi
            try:
                url_gen = f"{self._base_url}/api/generate"
                flat = ""
                for m in messages:
                    flat += f"[{m['role'].upper()}]\n{m['content']}\n\n"
                flat += "[ASSISTANT]\n"
                r = requests.post(url_gen, json={
                    "model": self.model, "prompt": flat,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }, timeout=180)
                r.raise_for_status()
                return r.json().get("response", "")
            except Exception:
                pass

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
