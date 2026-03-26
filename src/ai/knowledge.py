"""
ERR0RS ULTIMATE - RAG Knowledge Base
=======================================
ChromaDB vector database powered by the "From Zero to Secure" book.
Falls back to keyword search if ChromaDB is not installed.

Install dependencies:
    pip install chromadb sentence-transformers --break-system-packages

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import os
import json
import hashlib
import logging
from pathlib import Path

log = logging.getLogger("errors.ai.knowledge")

# Import all chunks from the education knowledge base
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.education.knowledge_base import KNOWLEDGE_BASE
from src.ai.darkcodersc_kb import build_darkcodersc_chunks, DARKCODERSC_TRIGGERS


def _kb_to_chunks() -> list:
    """Convert KNOWLEDGE_BASE dict into flat chunk list for embedding."""
    chunks = []
    for key, edu in KNOWLEDGE_BASE.items():
        chunks.append({
            "id":       key,
            "category": "security",
            "title":    edu.topic,
            "content":  f"{edu.what}\n\n{edu.how}\n\n{edu.defend}",
            "tags":     [key],
        })
    return chunks


class ERR0RSKnowledgeBase:
    """
    RAG knowledge base using ChromaDB + sentence-transformers.
    Auto-falls back to keyword search if ChromaDB not installed.
    """

    def __init__(self, persist_dir: str = "./errors_knowledge_db"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection  = None
        self._use_chroma = self._try_init_chroma()

    def _try_init_chroma(self) -> bool:
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            self.collection = client.get_or_create_collection(
                name="errors_knowledge", embedding_function=ef
            )
            log.info(f"ChromaDB ready — {self.collection.count()} docs")
            return True
        except ImportError:
            return False
        except Exception as e:
            log.error(f"ChromaDB init error: {e}")
            return False

    def ingest(self, force: bool = False) -> int:
        chunks = _kb_to_chunks()
        # ── Merge in DarkCoderSc knowledge base ──────────────────────────────
        try:
            dcs_chunks = build_darkcodersc_chunks()
            chunks.extend(dcs_chunks)
            log.info(f"Merged {len(dcs_chunks)} DarkCoderSc chunks into RAG")
        except Exception as e:
            log.warning(f"DarkCoderSc KB merge failed (non-fatal): {e}")
        if self._use_chroma:
            if self.collection.count() > 0 and not force:
                return self.collection.count()
            ids, docs, metas = [], [], []
            for c in chunks:
                uid = f"{c['id']}_{hashlib.md5(c['content'].encode()).hexdigest()[:8]}"
                ids.append(uid)
                docs.append(f"{c['title']}\n\n{c['content']}")
                metas.append({"id": c["id"], "title": c["title"]})
            self.collection.upsert(ids=ids, documents=docs, metadatas=metas)
            log.info(f"Ingested {len(ids)} chunks into ChromaDB")
            return len(ids)
        else:
            kb_path = self.persist_dir / "knowledge.json"
            with open(kb_path, "w") as f:
                json.dump(chunks, f, indent=2)
            log.info(f"Saved {len(chunks)} chunks (keyword mode)")
            return len(chunks)

    def search(self, query: str, n_results: int = 4) -> list:
        # Check DarkCoderSc fast-path triggers first
        q_lower = query.lower()
        for trigger, chunk_id in DARKCODERSC_TRIGGERS.items():
            if trigger in q_lower:
                log.debug(f"DarkCoderSc trigger match: '{trigger}' → {chunk_id}")
                break
        if self._use_chroma:
            return self._search_chroma(query, n_results)
        return self._search_keyword(query, n_results)

    def _search_chroma(self, query: str, n: int) -> list:
        try:
            res = self.collection.query(
                query_texts=[query],
                n_results=min(n, max(1, self.collection.count()))
            )
            return [
                {"content": doc, "metadata": meta}
                for doc, meta in zip(res["documents"][0], res["metadatas"][0])
            ]
        except Exception as e:
            log.error(f"ChromaDB search error: {e}")
            return []

    def _search_keyword(self, query: str, n: int) -> list:
        kb_path = self.persist_dir / "knowledge.json"
        if not kb_path.exists():
            self.ingest()
        with open(kb_path) as f:
            chunks = json.load(f)
        words = set(query.lower().split())
        scored = []
        for c in chunks:
            text  = f"{c['title']} {c['content']}".lower()
            score = sum(1 for w in words if w in text)
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"content": f"{c['title']}\n\n{c['content']}", "metadata": c}
            for _, c in scored[:n]
        ]
