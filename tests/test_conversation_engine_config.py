"""
Tests for ConversationEngine's env-configurable LLM endpoint/model.

This is what lets ERR0RS point at either stock Ollama (CPU, :11434) or
hailo-ollama (Hailo-10H HAT, :8000) with no code change — via ERR0RS_LLM_HOST
and ERR0RS_LLM_MODEL. The warmup thread + model auto-select are neutralised so
these stay pure/offline.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.core import conversation_engine as ce


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    # Don't let __init__ touch the network (warmup thread + model probe).
    monkeypatch.setattr(ce.ConversationEngine, "_warmup", lambda self: None)
    monkeypatch.setattr(ce.ConversationEngine, "_pick_best_model", lambda self, d: d)
    # Clean slate for the env vars we test.
    monkeypatch.delenv("ERR0RS_LLM_HOST", raising=False)
    monkeypatch.delenv("ERR0RS_LLM_MODEL", raising=False)


def test_env_host_and_model_are_honored(monkeypatch):
    monkeypatch.setenv("ERR0RS_LLM_HOST", "http://localhost:8000")
    monkeypatch.setenv("ERR0RS_LLM_MODEL", "qwen2.5-coder:1.5b")
    e = ce.ConversationEngine()
    assert e.ollama_host == "http://localhost:8000"
    assert e.model == "qwen2.5-coder:1.5b"   # HAT model used verbatim


def test_explicit_args_beat_env(monkeypatch):
    monkeypatch.setenv("ERR0RS_LLM_HOST", "http://localhost:8000")
    monkeypatch.setenv("ERR0RS_LLM_MODEL", "qwen2.5-coder:1.5b")
    e = ce.ConversationEngine(model="llama3.2:3b", ollama_host="http://x:1")
    assert e.ollama_host == "http://x:1"
    assert e.model == "llama3.2:3b"


def test_defaults_when_no_env():
    e = ce.ConversationEngine()
    assert e.ollama_host == "http://localhost:11434"   # stock Ollama default
    assert e.model == "gemma3:1b"                       # auto-select fallback


def test_env_model_not_overridden_by_preference_list(monkeypatch):
    """A HAT model absent from CHAT_MODEL_PREFERENCE must survive — the env
    branch must skip _pick_best_model entirely."""
    monkeypatch.setenv("ERR0RS_LLM_MODEL", "qwen2.5-coder:1.5b")
    # If _pick_best_model were called it would return 'sentinel'; it must NOT be.
    monkeypatch.setattr(ce.ConversationEngine, "_pick_best_model",
                        lambda self, d: "sentinel-should-not-appear")
    e = ce.ConversationEngine()
    assert e.model == "qwen2.5-coder:1.5b"
