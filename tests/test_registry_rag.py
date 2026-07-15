"""
Tests for src/ai/registry_rag.py + the retrieve_for_tool registry fallback.

Offline by design: a fake collection exercises the ingest path (no ChromaDB,
no embeddings), and the retrieval fallback is tested with RAG forced off.
Includes a regression test for the duplicate-RAG-id bug (aliases collapsing
to the same canonical id) found by running the real ingest.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.ai import registry_rag as rr


# ── Deterministic grounding ─────────────────────────────────────────────────

def test_ground_for_tool_known():
    g = rr.ground_for_tool("nmap")
    assert g and "nmap" in g
    assert "-sV" in g          # carries real flag ground truth
    assert "Key flags" in g


def test_ground_for_tool_alias_and_unknown():
    assert rr.ground_for_tool("netexec")            # alias → nxc, resolves
    assert rr.ground_for_tool("not-a-real-tool") is None


# ── Regression: unique RAG ids (the bug the real ingest caught) ─────────────

def test_rag_document_ids_are_unique():
    from src.core import tool_registry
    ids = [d["id"] for d in tool_registry.to_rag_documents()]
    assert len(ids) == len(set(ids)), "duplicate tool: ids would break upsert"


# ── Ingest with an injected fake collection (no chromadb / embeddings) ──────

class _FakeCollection:
    def __init__(self):
        self.upserts = []
    def upsert(self, ids, documents, metadatas):
        self.upserts.append((ids, documents, metadatas))
    def count(self):
        return sum(len(u[0]) for u in self.upserts)


class _RaisingCollection:
    def upsert(self, **kw):
        raise RuntimeError("boom")


def test_ingest_with_fake_collection():
    fake = _FakeCollection()
    docs = [{"id": "tool:nmap", "tool": "nmap", "text": "x", "sources": ["lessons", "mentor"]},
            {"id": "tool:nxc",  "tool": "nxc",  "text": "y", "sources": ["mentor"]}]
    res = rr.ingest_registry(docs=docs, _collection=fake)
    assert res["status"] == "ok" and res["ingested"] == 2
    ids, _docs, metas = fake.upserts[0]
    assert ids == ["tool:nmap", "tool:nxc"]
    assert metas[0]["source"] == "registry"
    assert metas[0]["kb_sources"] == "lessons,mentor"   # list joined to scalar


def test_ingest_empty_docs():
    assert rr.ingest_registry(docs=[], _collection=_FakeCollection())["status"] == "empty"


def test_ingest_error_path_is_soft():
    res = rr.ingest_registry(
        docs=[{"id": "t:x", "tool": "x", "text": "z", "sources": []}],
        _collection=_RaisingCollection())
    assert res["status"] == "error" and res["ingested"] == 0


def test_ingest_uses_registry_by_default():
    """With no docs override, it pulls from tool_registry — many docs, unique."""
    fake = _FakeCollection()
    res = rr.ingest_registry(_collection=fake)
    assert res["status"] == "ok" and res["ingested"] > 10
    ids = fake.upserts[0][0]
    assert len(ids) == len(set(ids))


# ── retrieve_for_tool falls back to the registry when RAG is unavailable ────

def test_retrieve_for_tool_registry_fallback(monkeypatch):
    from src.ai import rag_retrieval
    rag_retrieval._reset_for_testing()
    # Force the chunked RAG collection to be unavailable.
    monkeypatch.setattr(rag_retrieval, "_ensure_collection", lambda: None)
    block = rag_retrieval.retrieve_for_tool("nmap")
    assert block is not None and "nmap" in block


def test_retrieve_for_tool_empty_name():
    from src.ai import rag_retrieval
    assert rag_retrieval.retrieve_for_tool("") is None
