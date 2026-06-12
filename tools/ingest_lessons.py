#!/usr/bin/env python3
"""Bridge the hand-authored teach LESSONS into the chunked RAG collection.

ingest_chunked.py ingests the generated tool_registry cards. This companion
ingests the rich, hand-authored lessons from src/core/teach_engine.py (the
Python track, blue-team, RE, etc.) into the SAME err0rs_teach_v1_chunked
collection, under a separate '__lesson__' id namespace so the two never
collide. Re-runnable (upsert).

  python3 tools/ingest_lessons.py --dry-run     # build chunks, no write
  python3 tools/ingest_lessons.py               # embed + upsert
  python3 tools/ingest_lessons.py --query "port scanner"
"""
from __future__ import annotations
import argparse, re, sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "errors_knowledge_db"
COLLECTION_NAME = "err0rs_teach_v1_chunked"
TARGET = 1800   # soft chunk ceiling in chars

_spec = importlib.util.spec_from_file_location("teach_engine", ROOT / "src/core/teach_engine.py")
_te = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_te)
LESSONS, render_lesson, list_topics = _te.LESSONS, _te.format_lesson, _te.list_topics


def render_clean(topic: str) -> str:
    txt = render_lesson(topic)
    marks = ("[[LESSON_CONTROLS", "\U0001f4ac Questions", "\u23ed")
    cuts = [c for c in (txt.find(m) for m in marks) if c != -1]
    if cuts:
        txt = txt[:min(cuts)]
    return txt.strip()


def chunks_for(topic: str) -> list[dict]:
    display = (LESSONS[topic].get("display") or topic) if isinstance(LESSONS[topic], dict) else topic
    blocks = [b.strip() for b in re.split(r"\n\s*\n", render_clean(topic)) if b.strip()]
    out, cur, n = [], [], 0

    def flush():
        nonlocal cur, n
        if not cur:
            return
        idx = len(out)
        out.append({
            "id": f"{topic}__lesson__{idx}",
            "text": f"## {display} - {topic} (lesson, part {idx+1})\n\n" + "\n\n".join(cur),
            "metadata": {"tool": topic, "topic": topic, "section": "lesson",
                         "sub_idx": idx, "source": "err0rs-handauthored", "kind": "lesson"},
        })
        cur, n = [], 0

    for b in blocks:
        if n and n + len(b) > TARGET:
            flush()
        cur.append(b); n += len(b) + 2
    flush()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--query")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()

    topics = [t for t in (args.only or list_topics()) if t in LESSONS]
    all_chunks = []
    for t in topics:
        all_chunks.extend(chunks_for(t))
    sizes = sorted(len(c["text"]) for c in all_chunks)
    print(f"  lessons: {len(topics)} | chunks: {len(all_chunks)}")
    if sizes:
        print(f"  chunk size min/median/max: {sizes[0]}/{sizes[len(sizes)//2]}/{sizes[-1]} chars")
        print(f"  avg chunks/lesson: {len(all_chunks)/len(topics):.1f}")

    if args.query:
        import chromadb
        col = chromadb.PersistentClient(path=str(DB_PATH)).get_collection(COLLECTION_NAME)
        res = col.query(query_texts=[args.query], n_results=4, where={"kind": "lesson"})
        for i, (d, m, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], res["distances"][0]), 1):
            print(f"  #{i} dist={dist:.3f} [{m['topic']}] {d[:88].strip()}...")
        return 0

    if args.dry_run:
        for c in all_chunks[:3]:
            print(f"\n  --- {c['id']} ({len(c['text'])} chars) ---")
            print("  " + c["text"][:260].replace("\n", "\n  "))
        print("\n  DRY RUN - nothing written.")
        return 0

    import chromadb
    col = chromadb.PersistentClient(path=str(DB_PATH)).get_or_create_collection(COLLECTION_NAME)
    col.upsert(ids=[c["id"] for c in all_chunks],
               documents=[c["text"] for c in all_chunks],
               metadatas=[c["metadata"] for c in all_chunks])
    print(f"  ok upserted {len(all_chunks)} lesson chunks -> {COLLECTION_NAME} (now {col.count()} total)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
