#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — REGISTRY → RAG BRIDGE                   ║
║              src/ai/registry_rag.py                              ║
║                                                                  ║
║  Feeds the unified tool_registry (deterministic ground truth)   ║
║  into the RAG so the LLM stops hallucinating tool syntax. Two    ║
║  halves:                                                         ║
║    • ingest_registry() — upserts tool_registry.to_rag_documents ║
║      into the ChromaDB 'err0rs_refs' collection. Upsert (not     ║
║      add) so re-running refreshes changed knowledge — the        ║
║      single source of truth stays live in the vector store.      ║
║      rag_retrieval.retrieve_for_query already reads err0rs_refs, ║
║      so ingested docs are retrievable with NO engine change.     ║
║    • ground_for_tool() — deterministic, in-process grounding     ║
║      straight from the registry, no embedding round-trip and no  ║
║      dependency on ChromaDB. Used as the reactive-path fallback  ║
║      so EVERY registry-known tool grounds the model.             ║
║                                                                  ║
║  Fail-soft everywhere: missing chromadb / DB never crashes a     ║
║  caller. Run `python -m src.ai.registry_rag` to (re)ingest.      ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

# Match rag_retrieval.py exactly — both sides must agree on path + collection.
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "errors_knowledge_db"
_REFS_COLLECTION = "err0rs_refs"


def _open_collection(db_path, collection_name: str, reset: bool = False):
    """Open (or create) the target collection. Raises ImportError if chromadb
    is missing, or other exceptions on real DB errors — the caller catches."""
    import chromadb
    client = chromadb.PersistentClient(path=str(db_path))
    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "ERR0RS references + unified tool-registry ground truth"},
    )


def ingest_registry(docs: Optional[List[Dict]] = None,
                    db_path=None,
                    collection: str = _REFS_COLLECTION,
                    reset: bool = False,
                    _collection=None) -> Dict:
    """Upsert the unified tool knowledge into the RAG refs collection.

    `docs`       — override the doc set (defaults to tool_registry docs).
    `_collection`— inject a collection object (tests use a fake; prod leaves None).
    Returns a status dict; never raises.
    """
    if docs is None:
        try:
            from src.core import tool_registry
            docs = tool_registry.to_rag_documents()
        except Exception as e:
            return {"status": "error", "reason": f"registry unavailable: {e}", "ingested": 0}
    if not docs:
        return {"status": "empty", "ingested": 0, "total": 0}

    col = _collection
    if col is None:
        try:
            col = _open_collection(db_path or _DB_PATH, collection, reset)
        except ImportError:
            return {"status": "unavailable", "reason": "chromadb not installed",
                    "ingested": 0, "total": len(docs)}
        except Exception as e:
            return {"status": "error", "reason": f"{type(e).__name__}: {e}",
                    "ingested": 0, "total": len(docs)}

    ids       = [d["id"] for d in docs]
    documents = [d["text"] for d in docs]
    # ChromaDB metadata values must be scalar — join the source list to a string.
    metas = [{"tool": d.get("tool", ""), "source": "registry", "section": "registry",
              "kb_sources": ",".join(d.get("sources", []))} for d in docs]

    try:
        col.upsert(ids=ids, documents=documents, metadatas=metas)
        try:
            count = col.count()
        except Exception:
            count = len(ids)
        return {"status": "ok", "ingested": len(ids),
                "collection": collection, "count": count}
    except Exception as e:
        return {"status": "error", "reason": f"{type(e).__name__}: {e}", "ingested": 0}


def ground_for_tool(tool_name: str) -> Optional[str]:
    """Deterministic, in-process grounding block for a tool — straight from the
    registry, no ChromaDB needed. This is the ground truth the model should
    prefer over its own priors. Returns None if the tool is unknown."""
    try:
        from src.core import tool_registry
    except Exception:
        return None
    tk = tool_registry.get_tool(tool_name)
    if not tk:
        return None
    lines = [f"### ERR0RS ground truth: {tk.name}", tk.summary]
    if tk.flags:
        flag_bits = "; ".join(f"{f} = {d['what']}" for f, d in list(tk.flags.items())[:12])
        lines.append(f"Key flags: {flag_bits}")
    if tk.commands:
        lines.append("Example: " + next(iter(tk.commands.values())))
    if tk.opsec:
        lines.append("OpSec: " + tk.opsec[0])
    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = ingest_registry()
    print(f"[registry_rag] ingest -> {result}")
