"""
ERR0RS — RAG Retrieval Helper (v3.7 Phase 2 runtime wiring)
═══════════════════════════════════════════════════════════════════

The runtime-side companion to tools/ingest_chunked.py. Where the ingest
script BUILDS the chunked collection (build-time), this module READS
from it (runtime) and returns prompt-ready text the conversation engine
injects into its system prompt.

WHY THIS EXISTS:
  Before this module, the conversation engine called teach_engine.lookup()
  which returned static hand-written lessons from a Python dict (LESSONS).
  Good for what it covered (the 49 hand-written tools), useless for the
  4,987 others — and missing the 67 we paid Sonnet to teach to operator
  depth in v3.6.0.

  This module bridges the v3.6.0 chunked-RAG work into the runtime
  conversation flow. The conversation engine still falls back to the
  legacy teach_engine for tools that don't have RAG content, so nothing
  regresses.

DESIGN PRINCIPLES:
  1. Fail soft — if ChromaDB isn't installed, the collection doesn't
     exist, or the query fails, return None and let the caller fall
     back to legacy behavior. Never crash the conversation engine.
  2. Lazy load — collection isn't opened until the first query. New
     installs that haven't run the chunked ingest yet won't pay any
     startup cost.
  3. Prompt-ready output — callers don't need to format the chunks
     themselves; we return text that drops directly into the system
     prompt as a "Reference Material" block.
  4. Tool-name and free-text both supported — the conversation engine
     has both reactive (post-tool-run) and proactive (user-mentions-tool)
     injection points, and they need slightly different retrieval shapes.
  5. Singleton — the ChromaDB client + collection are opened once and
     reused. Each query is a fast in-process lookup, not a process spawn.

USAGE:
    from src.ai.rag_retrieval import retrieve_for_tool, retrieve_for_query

    # Reactive: ERR0RS just saw nmap finish, fetch its teach content
    block = retrieve_for_tool("nmap")
    if block:
        system_prompt += "\\n\\n" + block

    # Proactive: user asked "what is kerberoasting?"
    block = retrieve_for_query("kerberoasting opsec", n=2)
    if block:
        system_prompt += "\\n\\n" + block
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Match the chunked-ingest tool's paths exactly. If either side changes,
# both have to change together.
_DB_PATH        = Path(__file__).resolve().parent.parent.parent / "errors_knowledge_db"
_COLLECTION     = "err0rs_teach_v1_chunked"
_REFS_COLLECTION = "err0rs_refs"   # optional external reference corpora (OWASP/PaTT/...)

# Singleton state — populated on first query. Wrapped in a lock because
# the conversation engine is multi-threaded.
_lock = threading.Lock()
_collection = None       # type: ignore  — chromadb.Collection or None
_init_attempted = False  # so we don't keep re-trying a failed init
_refs_collection = None
_refs_attempted = False


def _ensure_collection():
    """Open the chunked collection on first use. Returns the collection
    or None if anything went wrong (caller falls back gracefully).

    We deliberately swallow exceptions here because the conversation
    engine SHOULD NOT crash if the RAG DB is missing or corrupt — that
    would make the gemma3:1b chat path unavailable for users who haven't
    run ingest_chunked.py yet. Logging is the right consequence; crashing
    is not."""
    global _collection, _init_attempted

    with _lock:
        if _collection is not None:
            return _collection
        if _init_attempted:
            # Already tried and failed — don't spam ChromaDB import attempts
            return None
        _init_attempted = True

        try:
            import chromadb
        except ImportError:
            log.info("chromadb not installed — RAG retrieval disabled")
            return None

        # Silence ChromaDB's bundled ONNX embedder probing for a GPU the
        # Pi doesn't have (harmless /sys/class/drm/cardN misses -> CPU).
        try:
            import onnxruntime
            onnxruntime.set_default_logger_severity(3)  # 3=ERROR (hide WARNING)
        except Exception:
            pass

        if not _DB_PATH.exists():
            log.info(f"RAG DB path missing — disabled: {_DB_PATH}")
            return None

        try:
            client = chromadb.PersistentClient(path=str(_DB_PATH))
            _collection = client.get_collection(_COLLECTION)
            log.info(f"RAG enabled: {_COLLECTION} ({_collection.count()} chunks)")
            return _collection
        except Exception as e:
            log.warning(f"RAG init failed ({type(e).__name__}: {e}) — disabled")
            return None


def _ensure_refs_collection():
    """Open the optional external-reference collection (OWASP / WSTG /
    PayloadsAllTheThings, etc.). Returns the collection or None — refs are
    a supplement, so absence is fine and must never disable the teach path."""
    global _refs_collection, _refs_attempted
    with _lock:
        if _refs_collection is not None:
            return _refs_collection
        if _refs_attempted:
            return None
        _refs_attempted = True
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(_DB_PATH))
            _refs_collection = client.get_collection(_REFS_COLLECTION)
            log.info(f"RAG refs enabled: {_REFS_COLLECTION} ({_refs_collection.count()} chunks)")
            return _refs_collection
        except Exception as e:
            log.info(f"RAG refs not available ({type(e).__name__}) — teach-only")
            return None


def _format_chunks(chunks: list[dict], header_label: str = "Reference Material") -> str:
    """Turn raw retrieved chunks into a single text block ready to paste
    into a system prompt.

    Each chunk already has a self-identifying header (e.g.
    "## Rubeus — opsec notes") from the ingest pipeline, so we just join
    them with separators and wrap the whole block."""
    if not chunks:
        return ""
    body = "\n\n— — —\n\n".join(c["text"] for c in chunks)
    return f"### {header_label} (from ERR0RS RAG)\n\n{body}"


def _registry_fallback(tool_name: str) -> Optional[str]:
    """Deterministic grounding straight from the unified tool registry, used
    when the chunked collection has no chunks for this tool (or RAG is off).
    Guarantees the model gets ground truth for any registry-known tool."""
    try:
        from src.ai.registry_rag import ground_for_tool
        return ground_for_tool(tool_name)
    except Exception:
        return None


def retrieve_for_tool(tool_name: str, n: int = 2) -> Optional[str]:
    """Retrieve teach content for a specific tool that just ran.

    Prefers the chunked RAG collection (exact tool-name metadata match); if
    that has nothing — or RAG isn't available — falls back to the deterministic
    tool_registry ground truth so every known tool still grounds the model.
    Returns a formatted prompt block, or None."""
    if not tool_name:
        return None
    coll = _ensure_collection()
    if coll is None:
        return _registry_fallback(tool_name)

    try:
        # Pull all chunks for this tool. The metadata filter is exact;
        # ChromaDB returns them ranked by relevance to the query text
        # but constrained to chunks matching the tool.
        # We don't pass query_texts (no semantic search needed — we
        # want THIS tool's chunks) so we use .get() with where filter.
        result = coll.get(
            where={"tool": tool_name.lower().strip()},
            limit=10,  # most tools have 5-10 chunks; cap to avoid runaways
        )
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []
        if not docs:
            return _registry_fallback(tool_name)

        # Order: intro chunk first, then the rest. The intro is small
        # and ALWAYS gives the model "what is this tool" context.
        chunks = list(zip(docs, metas))
        chunks.sort(key=lambda x: (x[1].get("section") != "intro", x[1].get("section", "")))
        selected = chunks[:n]
        return _format_chunks(
            [{"text": d} for d, _ in selected],
            header_label=f"ERR0RS teach: {tool_name}",
        )
    except Exception as e:
        log.warning(f"retrieve_for_tool({tool_name}) failed: {e}")
        return _registry_fallback(tool_name)


def retrieve_for_query(query: str, n: int = 2) -> Optional[str]:
    """Retrieve teach content by semantic similarity to a query string.

    Use this when the user mentioned something but didn't name a specific
    tool — "how do I avoid being caught when running Kerberoasting?"
    will return the Rubeus opsec chunk by similarity, not by tool-name
    lookup.

    Returns formatted prompt block, or None."""
    if not query or not query.strip():
        return None
    coll = _ensure_collection()
    if coll is None:
        return None

    merged = []  # (distance, doc) across teach + refs (same embedder => comparable)
    try:
        result = coll.query(query_texts=[query], n_results=n)
        docs = (result.get("documents") or [[]])[0]
        dists = (result.get("distances") or [[]])[0] or [0.0] * len(docs)
        merged += list(zip(dists, docs))
    except Exception as e:
        log.warning(f"retrieve_for_query teach failed: {e}")
    refs = _ensure_refs_collection()
    if refs is not None:
        try:
            rr = refs.query(query_texts=[query], n_results=n)
            rdocs = (rr.get("documents") or [[]])[0]
            rdists = (rr.get("distances") or [[]])[0] or [0.0] * len(rdocs)
            merged += list(zip(rdists, rdocs))
        except Exception as e:
            log.warning(f"retrieve_for_query refs failed: {e}")
    if not merged:
        return None
    merged.sort(key=lambda x: x[0])
    top = [d for _, d in merged[: n + 2]]
    return _format_chunks([{"text": d} for d in top], header_label="ERR0RS RAG context")


def is_available() -> bool:
    """True if the chunked RAG is loaded and queryable. The conversation
    engine doesn't need this — None-handling on the retrieve_* functions
    is the right pattern — but it's useful for diagnostics and the
    preflight check.

    Touches the collection (lazy-loads it). Safe to call any time."""
    return _ensure_collection() is not None


def chunk_count() -> int:
    """How many chunks are in the loaded collection. Zero if RAG isn't
    available."""
    coll = _ensure_collection()
    if coll is None:
        return 0
    try:
        return coll.count()
    except Exception:
        return 0


# ── Test helpers ─────────────────────────────────────────────────────────

def _reset_for_testing():
    """Clear singleton state. Used by tests; not for production callers."""
    global _collection, _init_attempted
    with _lock:
        _collection = None
        _init_attempted = False
