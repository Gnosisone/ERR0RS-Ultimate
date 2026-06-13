#!/usr/bin/env python3
"""Ingest a local directory's markdown into a Chroma collection (clone-based).
Use when GitHub's recursive-tree API truncates a large repo (e.g. PaTT).

  python3 tools/ingest_local_dir.py /path/to/repo --source owner/repo --license MIT --prefix patt --dry-run
"""
import sys, re, argparse
from pathlib import Path

def chunk_md(text, max_chars=1800):
    blocks = re.split(r'\n(?=#{1,3}\s)', text)
    chunks, cur, n = [], [], 0
    def flush():
        nonlocal cur, n
        if cur: chunks.append("\n\n".join(cur)); cur, n = [], 0
    for b in blocks:
        b = b.strip()
        if not b: continue
        if len(b) > max_chars:
            flush()
            for para in re.split(r'\n\s*\n', b):
                para = para.strip()
                if not para: continue
                if n and n + len(para) > max_chars: flush()
                cur.append(para); n += len(para)
            flush(); continue
        if n and n + len(b) > max_chars: flush()
        cur.append(b); n += len(b)
    flush()
    return [c for c in chunks if len(c.strip()) > 40]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--collection", default="err0rs_refs")
    ap.add_argument("--source", required=True)
    ap.add_argument("--license", default="")
    ap.add_argument("--prefix", default="ref")
    ap.add_argument("--db", default="/home/kali/ERR0RS-clean/errors_knowledge_db")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = Path(a.path)
    ids, docs, metas = [], [], []
    for f in sorted(root.rglob("*.md")):
        if "/.git/" in str(f): continue
        rel = str(f.relative_to(root))
        try: text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for i, ch in enumerate(chunk_md(text)):
            ids.append(f"{a.prefix}::{rel}::{i}")
            docs.append(f"## {a.source}: {rel}\n\n{ch}")
            metas.append({"source": a.source, "license": a.license, "file": rel, "kind": "ref"})
    print(f"  {a.source}: {len(ids)} chunks from markdown")
    if a.dry_run:
        for d in docs[:2]: print("  --", d[:140].replace("\n", " "))
        print("  DRY RUN — nothing written."); return 0
    import chromadb
    col = chromadb.PersistentClient(path=a.db).get_or_create_collection(a.collection)
    # purge stale chunks for this source (both this prefix and any API-ingested ones)
    try:
        existing = col.get()
        stale = [i for i in existing["ids"] if i.startswith(a.prefix + "::") or a.source.split("/")[-1] in i]
        if stale: col.delete(ids=stale); print(f"  purged {len(stale)} stale chunks")
    except Exception as e:
        print("  (purge skipped:", e, ")")
    B = 256
    for s in range(0, len(ids), B):
        col.upsert(ids=ids[s:s+B], documents=docs[s:s+B], metadatas=metas[s:s+B])
        print(f"  ...{min(s+B, len(ids))}/{len(ids)}")
    print(f"  ok {a.collection} now {col.count()} chunks")
    return 0

if __name__ == "__main__":
    sys.exit(main())
