#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Multi-LLM Router
Routes AI requests to LLM providers with LOCAL-FIRST architecture.

Priority chain (data NEVER leaves the machine unless explicitly configured):
  1. Ollama  (local, zero-network, default)
  2. LM Studio (local, zero-network)
  3. Claude / GPT-4 / Gemini (remote, opt-in only)

All remote providers are gated behind an explicit user flag.
"""

import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

try:
    import requests
except ImportError:
    requests = None  # graceful degradation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class LLMProvider(Enum):
    OLLAMA   = "ollama"       # local  – primary
    LMSTUDIO = "lmstudio"    # local  – fallback
    CLAUDE   = "claude"       # remote – opt-in
    GPT4     = "gpt4"        # remote – opt-in
    GEMINI   = "gemini"      # remote – opt-in


@dataclass
class LLMConfig:
    provider  : LLMProvider
    model     : str
    base_url  : str
    api_key   : Optional[str] = None
    temperature: float = 0.3        # low default – security tasks need precision
    max_tokens : int   = 2048
    timeout    : int   = 60         # seconds


@dataclass
class LLMResponse:
    provider     : LLMProvider
    content      : str
    tokens_used  : int
    model        : str
    latency_ms   : int
    cached       : bool = False


# ---------------------------------------------------------------------------
# Default configurations
# ---------------------------------------------------------------------------

DEFAULT_CONFIGS: Dict[LLMProvider, LLMConfig] = {
    LLMProvider.OLLAMA: LLMConfig(
        provider   = LLMProvider.OLLAMA,
        model      = "qwen2.5-coder:7b",   # ERR0RS default — Pi 5 Cyberdeck
        base_url   = "http://127.0.0.1:11434",
        timeout    = 180,                  # Pi 5 needs more time for 7B model
    ),
    LLMProvider.LMSTUDIO: LLMConfig(
        provider   = LLMProvider.LMSTUDIO,
        model      = "local-model",
        base_url   = "http://127.0.0.1:1234",
        timeout    = 90,
    ),
}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class LLMRouter:
    """
    Central routing layer.  Keeps a response cache keyed on (prompt hash, model)
    so repeated identical queries (common during recon loops) never hit the model twice.
    """

    def __init__(self, allow_remote: bool = False):
        self.configs: Dict[LLMProvider, LLMConfig] = dict(DEFAULT_CONFIGS)
        self.allow_remote   = allow_remote          # gate for cloud providers
        self.cache: Dict[str, LLMResponse]          = {}
        self.provider_health: Dict[LLMProvider, bool] = {}
        self._resolve_order = self._build_resolve_order()

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def register_provider(self, config: LLMConfig):
        self.configs[config.provider] = config
        logger.info("Registered provider: %s  model=%s", config.provider.value, config.model)

    def _build_resolve_order(self) -> List[LLMProvider]:
        """Local providers first, remote only if allow_remote is True."""
        order = [LLMProvider.OLLAMA, LLMProvider.LMSTUDIO]
        if self.allow_remote:
            order.extend([LLMProvider.CLAUDE, LLMProvider.GPT4, LLMProvider.GEMINI])
        return order

    # ------------------------------------------------------------------
    # Health check  (non-blocking, quick)
    # ------------------------------------------------------------------

    def _check_health(self, provider: LLMProvider) -> bool:
        """Ping the provider's base URL to see if it's alive."""
        if requests is None:
            logger.warning("requests library not installed – cannot health-check")
            return False
        cfg = self.configs.get(provider)
        if not cfg:
            return False
        try:
            # Ollama exposes GET /api/tags; LM Studio exposes GET /v1/models
            if provider == LLMProvider.OLLAMA:
                r = requests.get(f"{cfg.base_url}/api/tags", timeout=3)
            elif provider == LLMProvider.LMSTUDIO:
                r = requests.get(f"{cfg.base_url}/v1/models", timeout=3)
            else:
                r = requests.get(cfg.base_url, timeout=3)
            alive = r.status_code == 200
        except Exception:
            alive = False
        self.provider_health[provider] = alive
        return alive

    def check_all_providers(self) -> Dict[str, bool]:
        """Return health map  { provider_name: alive }."""
        results = {}
        for p in self._resolve_order:
            results[p.value] = self._check_health(p)
        return results

    # ------------------------------------------------------------------
    # Core: send a prompt, get a response
    # ------------------------------------------------------------------

    async def send(self, prompt: str, provider: Optional[LLMProvider] = None,
                   system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Send prompt through the resolution chain.
        If a specific provider is requested and alive, use it.
        Otherwise walk the resolve order until one succeeds.
        """
        # --- cache lookup ---
        cache_key = self._cache_key(prompt, provider)
        if cache_key in self.cache:
            resp = self.cache[cache_key]
            resp.cached = True
            return resp

        # --- build candidate list ---
        candidates = [provider] if provider else self._resolve_order

        for candidate in candidates:
            if candidate not in self.configs:
                continue
            if not self._check_health(candidate):
                logger.info("Provider %s not reachable – skipping", candidate.value)
                continue

            try:
                response = await self._call_provider(candidate, prompt, system_prompt)
                self.cache[cache_key] = response
                return response
            except Exception as exc:
                logger.warning("Provider %s failed: %s", candidate.value, exc)
                continue

        # --- nothing worked ---
        raise RuntimeError(
            "No LLM provider available.  Make sure Ollama is running "
            "(ollama serve) or configure a remote provider with allow_remote=True."
        )

    # ------------------------------------------------------------------
    # Provider-specific call implementations
    # ------------------------------------------------------------------

    async def _call_provider(self, provider: LLMProvider, prompt: str,
                             system_prompt: Optional[str] = None) -> LLMResponse:
        cfg = self.configs[provider]

        if provider in (LLMProvider.OLLAMA, LLMProvider.LMSTUDIO):
            return await self._call_openai_compat(cfg, provider, prompt, system_prompt)

        if provider == LLMProvider.CLAUDE:
            return await self._call_claude(cfg, prompt, system_prompt)

        if provider == LLMProvider.GPT4:
            return await self._call_openai_native(cfg, prompt, system_prompt)

        if provider == LLMProvider.GEMINI:
            return await self._call_gemini(cfg, prompt, system_prompt)

        raise ValueError(f"Unknown provider: {provider}")

    # --- Ollama / LM Studio (OpenAI-compatible /v1/chat/completions) ---

    async def _call_openai_compat(self, cfg: LLMConfig, provider: LLMProvider,
                                  prompt: str, system_prompt: Optional[str]) -> LLMResponse:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        url = f"{cfg.base_url}/v1/chat/completions"
        # Ollama also supports /api/chat natively; prefer /v1 for compatibility
        # but fall back to /api/chat if /v1 fails
        payload = {
            "model"      : cfg.model,
            "messages"   : messages,
            "temperature": cfg.temperature,
            "max_tokens" : cfg.max_tokens,
            "stream"     : False,
        }

        start = time.time()
        try:
            r = requests.post(url, json=payload, timeout=cfg.timeout)
            r.raise_for_status()
            data = r.json()
            if not data.get("choices"):
                raise ValueError("Empty choices in response")
        except Exception:
            try:
                # Fallback 1: /api/chat native
                url_native = f"{cfg.base_url}/api/chat"
                payload_native = {
                    "model"   : cfg.model,
                    "messages": messages,
                    "stream"  : False,
                    "options" : {"temperature": cfg.temperature, "num_predict": cfg.max_tokens},
                }
                r = requests.post(url_native, json=payload_native, timeout=cfg.timeout)
                r.raise_for_status()
                data = r.json()
                if not data.get("message"):
                    raise ValueError("Empty message in response")
                data = {
                    "choices": [{"message": {"content": data.get("message", {}).get("content", "")}}],
                    "usage"  : {"total_tokens": 0},
                }
            except Exception:
                # Fallback 2: /api/generate — most compatible, confirmed working on Pi 5
                url_generate = f"{cfg.base_url}/api/generate"
                # Flatten messages into a single prompt
                flat_prompt = ""
                for m in messages:
                    role = m["role"].upper()
                    flat_prompt += f"[{role}]\n{m['content']}\n\n"
                flat_prompt += "[ASSISTANT]\n"
                payload_generate = {
                    "model"  : cfg.model,
                    "prompt" : flat_prompt,
                    "stream" : False,
                    "options": {"temperature": cfg.temperature, "num_predict": cfg.max_tokens},
                }
                r = requests.post(url_generate, json=payload_generate, timeout=cfg.timeout)
                r.raise_for_status()
                gen_data = r.json()
                data = {
                    "choices": [{"message": {"content": gen_data.get("response", "")}}],
                    "usage"  : {"total_tokens": gen_data.get("eval_count", 0)},
                }

        elapsed_ms = int((time.time() - start) * 1000)
        content = data["choices"][0]["message"]["content"]
        tokens  = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            provider    = provider,
            content     = content,
            tokens_used = tokens,
            model       = cfg.model,
            latency_ms  = elapsed_ms,
        )

    # --- Anthropic Claude ---

    async def _call_claude(self, cfg: LLMConfig, prompt: str,
                           system_prompt: Optional[str]) -> LLMResponse:
        if not cfg.api_key:
            raise ValueError("Claude API key not configured")
        headers = {"x-api-key": cfg.api_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        body: Dict[str, Any] = {
            "model"      : cfg.model or "claude-sonnet-4-5-20250929",
            "max_tokens" : cfg.max_tokens,
            "messages"   : [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            body["system"] = system_prompt

        start = time.time()
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers=headers, json=body, timeout=cfg.timeout)
        r.raise_for_status()
        data = r.json()
        elapsed_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            provider    = LLMProvider.CLAUDE,
            content     = data["content"][0]["text"],
            tokens_used = data.get("usage", {}).get("output_tokens", 0),
            model       = cfg.model,
            latency_ms  = elapsed_ms,
        )

    # --- OpenAI GPT-4 ---

    async def _call_openai_native(self, cfg: LLMConfig, prompt: str,
                                  system_prompt: Optional[str]) -> LLMResponse:
        if not cfg.api_key:
            raise ValueError("GPT-4 API key not configured")
        headers = {"Authorization": f"Bearer {cfg.api_key}",
                   "content-type": "application/json"}
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = {"model": cfg.model or "gpt-4", "messages": messages,
                "temperature": cfg.temperature, "max_tokens": cfg.max_tokens}

        start = time.time()
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=body, timeout=cfg.timeout)
        r.raise_for_status()
        data = r.json()
        elapsed_ms = int((time.time() - start) * 1000)

        return LLMResponse(
            provider    = LLMProvider.GPT4,
            content     = data["choices"][0]["message"]["content"],
            tokens_used = data.get("usage", {}).get("total_tokens", 0),
            model       = cfg.model,
            latency_ms  = elapsed_ms,
        )

    # --- Google Gemini ---

    async def _call_gemini(self, cfg: LLMConfig, prompt: str,
                           system_prompt: Optional[str]) -> LLMResponse:
        if not cfg.api_key:
            raise ValueError("Gemini API key not configured")
        model_name = cfg.model or "gemini-pro"
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model_name}:generateContent?key={cfg.api_key}")

        contents: List[Dict] = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"[SYSTEM] {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body = {"contents": contents,
                "generationConfig": {"temperature": cfg.temperature,
                                     "maxOutputTokens": cfg.max_tokens}}

        start = time.time()
        r = requests.post(url, json=body, timeout=cfg.timeout,
                          headers={"content-type": "application/json"})
        r.raise_for_status()
        data = r.json()
        elapsed_ms = int((time.time() - start) * 1000)

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return LLMResponse(
            provider    = LLMProvider.GEMINI,
            content     = text,
            tokens_used = 0,        # Gemini doesn't always return token counts here
            model       = model_name,
            latency_ms  = elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _cache_key(prompt: str, provider: Optional[LLMProvider]) -> str:
        tag = provider.value if provider else "auto"
        return hashlib.sha256(f"{tag}:{prompt}".encode()).hexdigest()[:16]

    def clear_cache(self):
        self.cache.clear()

    def get_status(self) -> Dict[str, Any]:
        return {
            "allow_remote"   : self.allow_remote,
            "resolve_order"  : [p.value for p in self._resolve_order],
            "registered"     : [p.value for p in self.configs],
            "health"         : self.provider_health,
            "cache_entries"  : len(self.cache),
        }
