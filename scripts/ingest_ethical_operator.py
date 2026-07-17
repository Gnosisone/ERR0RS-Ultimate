#!/usr/bin/env python3
"""
The Ethical Operator (textbook) -> ChromaDB RAG Ingester
═══════════════════════════════════════════════════════════════════
Chunks "The Ethical Operator" along its Volume -> Chapter -> Section
structure and loads it into ERR0RS's ChromaDB knowledge base, into the
SAME collection the conversation engine's retrieve_for_query() already
reads ('err0rs_refs'), using the SAME default ONNX embedder. So once
ingested, ERR0RS will pull book passages by semantic similarity with no
other wiring needed.

Matches the conventions of scripts/ingest_payloads_all_things.py:
  - PersistentClient(errors_knowledge_db)
  - default Chroma embedding function (no explicit EF) == retrieval side
  - self-identifying chunk header, sha256 id, dedupe-by-id, batch add

Usage:
    python3 scripts/ingest_ethical_operator.py                 # ingest
    python3 scripts/ingest_ethical_operator.py --dry-run       # preview
    python3 scripts/ingest_ethical_operator.py --reset         # wipe this book's chunks, re-add
    python3 scripts/ingest_ethical_operator.py --query "how does kerberoasting work"

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os
import re
import sys
import hashlib
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Paths / target (match the rest of ERR0RS exactly) ───────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
CHROMA_PATH = REPO_ROOT / "errors_knowledge_db"
BOOK_PATH   = REPO_ROOT / "ethical_operator_book.md"   # put the corpus here
COLLECTION  = "err0rs_refs"      # the engine's retrieve_for_query() reads this
SOURCE      = "The Ethical Operator"
AUTHOR      = "Gary Holden Schneider"

# ─── Chunking ────────────────────────────────────────────────────────────────
MAX_CHARS = 1200      # ~300 tokens — comfortable for the default MiniLM embedder
OVERLAP   = 200
MIN_CHARS = 90
BATCH     = 100


def _clean_heading(line: str) -> str:
    t = re.sub(r"^#+\s*", "", line).strip()
    return t.replace("**", "").replace("*", "").replace("`", "").strip()


def _split_long(text: str, max_chars: int, overlap: int):
    if len(text) <= max_chars:
        return [text]
    paras = re.split(r"\n\s*\n", text)
    out, cur = [], ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if cur and len(cur) + len(p) + 2 > max_chars:
            out.append(cur.strip())
            tail = cur[-overlap:]
            cut = tail.find("\n")
            cur = (tail[cut + 1:] if cut != -1 else tail).strip()
            cur = (cur + "\n\n" + p) if cur else p
        else:
            cur = (cur + "\n\n" + p) if cur else p
        while len(cur) > max_chars:
            out.append(cur[:max_chars].strip())
            cur = cur[max_chars - overlap:].strip()
    if cur.strip():
        out.append(cur.strip())
    return out


def chunk_book(md: str):
    """Walk the markdown tracking Volume/Chapter/Section (fence-aware) and
    return ERR0RS-style chunk dicts: {id, document, metadata}."""
    lines = md.split("\n")
    in_fence = False
    vol, chap, sec = "Front Matter", "", ""
    buf, chunks = [], []

    def path():
        return " > ".join(x for x in (vol, chap, sec) if x)

    def flush():
        text = "\n".join(buf).strip()
        buf.clear()
        if not text:
            return
        p = path()
        for piece in _split_long(text, MAX_CHARS, OVERLAP):
            piece = piece.strip()
            if len(piece) < MIN_CHARS:
                continue
            doc = f"[{SOURCE}] {p}\n\n{piece}" if p else f"[{SOURCE}]\n\n{piece}"
            uid = hashlib.sha256(f"{SOURCE}::{p}::{piece}".encode()).hexdigest()[:16]
            chunks.append({
                "id": uid,
                "document": doc,
                "metadata": {
                    "source":  SOURCE,
                    "author":  AUTHOR,
                    "volume":  vol,
                    "chapter": chap or "(none)",
                    "section": sec or "(intro)",
                    "path":    p,
                },
            })

    for line in lines:
        st = line.lstrip()
        if st.startswith("```") or st.startswith("~~~"):
            in_fence = not in_fence
            buf.append(line)
            continue
        if not in_fence:
            if re.match(r"^# VOLUME", line):
                flush(); vol = _clean_heading(line); chap = ""; sec = ""; continue
            if re.match(r"^# Chapter", line):
                flush(); chap = _clean_heading(line); sec = ""; continue
            if re.match(r"^# Appendix", line):
                flush(); vol = "Appendices"; chap = _clean_heading(line); sec = ""; continue
            if re.match(r"^##\s", line):
                flush(); sec = _clean_heading(line); continue
            if re.match(r"^#\s", line):
                flush(); sec = _clean_heading(line); continue
        buf.append(line)
    flush()
    return chunks


def _open_collection():
    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed. Run: pip install chromadb --break-system-packages")
        sys.exit(1)
    try:
        import onnxruntime
        onnxruntime.set_default_logger_severity(3)   # hide the harmless GPU-probe WARNING
    except Exception:
        pass
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    # NO embedding_function -> default ONNX MiniLM, identical to the retrieval side
    return client, client.get_or_create_collection(
        name=COLLECTION,
        metadata={"description": "ERR0RS external reference corpora (OWASP / PaTT / books)"},
    )


def do_query(q: str, n: int = 5):
    _, col = _open_collection()
    res = col.query(query_texts=[q], n_results=n)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0] or [0.0] * len(docs)
    print(f"\nTop {len(docs)} for {q!r}\n" + "=" * 60)
    for i, (d, m, dist) in enumerate(zip(docs, metas, dists), 1):
        loc = m.get("path", m.get("source", "?"))
        snip = re.sub(r"\s+", " ", d).strip()[:240]
        print(f"\n[{i}] ({1 - dist:.3f}) {loc}\n    {snip}…")
    print()


def main():
    ap = argparse.ArgumentParser(description="Ingest The Ethical Operator into ERR0RS ChromaDB")
    ap.add_argument("--book", default=str(BOOK_PATH))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reset", action="store_true", help="delete this book's existing chunks first")
    ap.add_argument("--query", default=None)
    args = ap.parse_args()

    if args.query:
        do_query(args.query)
        return

    book = Path(args.book)
    if not book.exists():
        log.error(f"Corpus not found: {book}")
        log.error("Place 'ethical_operator_book.md' there, then re-run.")
        sys.exit(1)

    md = book.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_book(md)
    log.info(f"Parsed {len(chunks)} chunks from {book.name}")

    if args.dry_run:
        log.info("[DRY RUN] not writing")
        for c in chunks[:5]:
            print(f"\n--- {c['metadata']['path']} ---\n{c['document'][:300]}")
        return

    client, col = _open_collection()

    if args.reset:
        try:
            ex = col.get(where={"source": SOURCE})
            if ex.get("ids"):
                col.delete(ids=ex["ids"])
                log.info(f"[RESET] removed {len(ex['ids'])} existing '{SOURCE}' chunks")
        except Exception as e:
            log.warning(f"reset skipped: {e}")

    ids   = [c["id"] for c in chunks]
    docs  = [c["document"] for c in chunks]
    metas = [c["metadata"] for c in chunks]

    # collapse any byte-identical chunks (same id) before talking to Chroma
    seen = set(); _i, _d, _m = [], [], []
    for k, did in enumerate(ids):
        if did in seen:
            continue
        seen.add(did); _i.append(did); _d.append(docs[k]); _m.append(metas[k])
    if len(_i) != len(ids):
        log.info(f"collapsed {len(ids) - len(_i)} identical chunk(s)")
    ids, docs, metas = _i, _d, _m

    existing = set(col.get(ids=ids).get("ids", []))
    nids, ndocs, nmetas = [], [], []
    for i, did in enumerate(ids):
        if did not in existing:
            nids.append(did); ndocs.append(docs[i]); nmetas.append(metas[i])

    if not nids:
        log.info("All chunks already present — nothing to add.")
    else:
        for s in range(0, len(nids), BATCH):
            col.add(ids=nids[s:s+BATCH], documents=ndocs[s:s+BATCH], metadatas=nmetas[s:s+BATCH])
            log.info(f"  added {min(s+BATCH, len(nids))}/{len(nids)}")
        log.info(f"✅ {len(nids)} new chunks added to '{COLLECTION}'")

    log.info(f"Collection '{COLLECTION}' total docs: {col.count()}")
    log.info(f"Verify: python3 scripts/ingest_ethical_operator.py --query \"how do reverse shells work\"")


if __name__ == "__main__":
    main()
