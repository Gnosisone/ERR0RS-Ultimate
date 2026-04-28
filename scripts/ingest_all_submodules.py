#!/usr/bin/env python3
"""
ERR0RS — Batch Knowledge Base Submodule Ingester
=================================================
Walks all git submodules in the knowledge/ directory and ingests
each one into ChromaDB using the local filesystem (no API calls needed
since they're already cloned).

This is faster than the GitHub API ingester for repos already on disk.

Usage:
    python3 scripts/ingest_all_submodules.py
    python3 scripts/ingest_all_submodules.py --dry-run
    python3 scripts/ingest_all_submodules.py --collection kb_submodules

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os, sys, re, hashlib, argparse, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT   = Path(__file__).resolve().parent.parent
KNOWLEDGE   = REPO_ROOT / "knowledge"
CHROMA_PATH = REPO_ROOT / "errors_knowledge_db"
COLLECTION  = "kb_submodules"

# File types to ingest
INGEST_EXTS = {
    ".md", ".txt", ".rst", ".py", ".sh", ".bash", ".zsh",
    ".rb", ".pl", ".ps1", ".yaml", ".yml", ".conf", ".cfg",
    ".ini", ".c", ".h", ".go", ".rs", ".js", ".ts", ".php",
    ".lua", ".yar", ".yara", ".sigma", ".nse", ".cs",
}

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".github",
             "vendor", "dist", "build", "venv", ".venv"}

MAX_FILE_BYTES = 100_000  # 100KB cap

# Repos to skip — too large, binary-heavy, or already ingested separately
SKIP_REPOS = {
    "UberGuidoZ-Flipper",       # 34k+ chunks — mostly binary .sub files
    "Flipper_Zero",             # 34k+ chunks — RocketGod's signal library
    "PayloadsAllTheThings",     # already in payloads_all_things collection
    "lanjelot-kb",              # already in lanjelot_kb collection
    "nocomp-hack5-payloads",    # already in badusb_payloads collection
    "Flipper-Zero-BadUSB",      # already in badusb_payloads collection
}

# Max chunks per repo to keep ingestion bounded
MAX_CHUNKS_PER_REPO = 500

# Per-category MITRE tags
CATEGORY_MITRE = {
    "advanced_tradecraft": "T1595",
    "badusb":              "T1200",
    "c2":                  "T1071",
    "credentials":         "T1552",
    "enumeration":         "T1046",
    "evasion":             "T1027",
    "exploitation":        "T1190",
    "intel":               "T1591",
    "mobile":              "T1404",
    "recon":               "T1592",
    "redteam":             "T1595",
    "rocketgod":           "T1200",
    "social-engineering":  "T1566",
    "surveillance":        "T1125",
    "threat-intelligence": "T1591",
    "windows":             "T1059",
    "wireless":            "T1040",
}


def chunk_file(filepath: Path, category: str, repo_name: str) -> list[dict]:
    """Chunk a single file into RAG documents."""
    try:
        if filepath.stat().st_size > MAX_FILE_BYTES:
            return []
        text = filepath.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return []

    if len(text) < 40:
        return []

    ext  = filepath.suffix.lower()
    mitre = CATEGORY_MITRE.get(category, "T1595")
    chunks = []

    # Markdown — split on headings
    if ext in (".md", ".rst", ".txt"):
        sections = re.split(r"(?m)^(#{1,3} .+)$", text)
        heading  = f"{filepath.name} — Overview"
        body     = ""

        def flush(h, b):
            b = b.strip()
            if len(b) < 40:
                return
            uid = hashlib.sha256(
                f"{repo_name}::{filepath.name}::{h}::{b[:60]}".encode()
            ).hexdigest()[:16]
            chunks.append({
                "id": uid,
                "document": f"[{category}/{repo_name}: {filepath.name}]\n## {h}\n\n{b}",
                "metadata": {
                    "source":      f"kb/{category}/{repo_name}",
                    "category":    category,
                    "repo":        repo_name,
                    "file":        filepath.name,
                    "section":     h,
                    "ext":         ext,
                    "mitre":       mitre,
                    "attack_type": category,
                }
            })

        for part in sections:
            if re.match(r"^#{1,3} ", part):
                flush(heading, body)
                heading = part.strip("# ").strip()
                body    = ""
            else:
                body += part
        flush(heading, body)

    # Code / scripts — paragraph chunks
    else:
        paras = re.split(r"\n{2,}", text)
        buf   = []
        CHUNK = 10

        for i, para in enumerate(paras):
            para = para.strip()
            if para:
                buf.append(para)
            if len(buf) >= CHUNK or (i == len(paras) - 1 and buf):
                body = "\n\n".join(buf)
                uid  = hashlib.sha256(
                    f"{repo_name}::{filepath.name}::c{len(chunks)}::{body[:60]}".encode()
                ).hexdigest()[:16]
                chunks.append({
                    "id": uid,
                    "document": f"[{category}/{repo_name}: {filepath.name}]\n\n{body}",
                    "metadata": {
                        "source":      f"kb/{category}/{repo_name}",
                        "category":    category,
                        "repo":        repo_name,
                        "file":        filepath.name,
                        "section":     f"chunk_{len(chunks)}",
                        "ext":         ext,
                        "mitre":       mitre,
                        "attack_type": category,
                    }
                })
                buf = []

    return chunks


def walk_submodule(submodule_path: Path, category: str) -> list[dict]:
    """Walk a submodule directory and chunk all ingestable files."""
    all_chunks = []
    repo_name  = submodule_path.name

    for filepath in sorted(submodule_path.rglob("*")):
        # Skip directories and hidden/build paths
        if not filepath.is_file():
            continue
        if any(part in SKIP_DIRS for part in filepath.parts):
            continue
        if filepath.suffix.lower() not in INGEST_EXTS:
            continue

        chunks = chunk_file(filepath, category, repo_name)
        all_chunks.extend(chunks)

    return all_chunks


def collect_all_chunks() -> list[dict]:
    """Walk all knowledge/ submodule dirs and chunk content."""
    all_chunks = []
    stats = {}

    # Walk category directories
    for cat_dir in sorted(KNOWLEDGE.iterdir()):
        if not cat_dir.is_dir() or cat_dir.name.startswith("."):
            continue
        category = cat_dir.name

        # Walk repo subdirectories within category
        for repo_dir in sorted(cat_dir.iterdir()):
            if not repo_dir.is_dir() or repo_dir.name.startswith("."):
                continue
            # Must be a git repo (has .git) or have content files
            has_git     = (repo_dir / ".git").exists()
            has_content = any(repo_dir.rglob("*.md")) or any(repo_dir.rglob("*.txt"))
            if not has_git and not has_content:
                continue
            if repo_dir.name in SKIP_REPOS:
                log.info(f"  ⏭  Skipping {category}/{repo_dir.name} (excluded)")
                continue

            chunks = walk_submodule(repo_dir, category)

            # Cap per-repo to keep total manageable
            if len(chunks) > MAX_CHUNKS_PER_REPO:
                log.info(f"  ⚠️  {repo_dir.name}: {len(chunks)} chunks — capping at {MAX_CHUNKS_PER_REPO}")
                chunks = chunks[:MAX_CHUNKS_PER_REPO]

            if chunks:
                all_chunks.extend(chunks)
                stats[f"{category}/{repo_dir.name}"] = len(chunks)
                log.info(f"  ✓ {category:<22}/{repo_dir.name:<35} {len(chunks):>4} chunks")

    log.info(f"\n  Repos ingested: {len(stats)}")
    return all_chunks


def load_to_chroma(chunks: list[dict], collection_name: str,
                   reset: bool = False) -> int:
    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed.")
        return 0

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

    col = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "ERR0RS KB — all knowledge/ submodules"}
    )

    ids   = [c["id"]       for c in chunks]
    docs  = [c["document"] for c in chunks]
    metas = [c["metadata"] for c in chunks]

    try:
        existing = set(col.get(ids=ids)["ids"])
    except Exception:
        existing = set()

    new_ids, new_docs, new_metas = [], [], []
    for i, did in enumerate(ids):
        if did not in existing:
            new_ids.append(did)
            new_docs.append(docs[i])
            new_metas.append(metas[i])

    if not new_ids:
        log.info("All chunks already in ChromaDB.")
        return 0

    BATCH = 100
    # Process in groups of 500 — re-check existing after each group
    # so if the process dies, re-running picks up where it left off
    SESSION_MAX = 500
    processed = 0

    for start in range(0, len(new_ids), BATCH):
        col.add(
            ids=new_ids[start:start+BATCH],
            documents=new_docs[start:start+BATCH],
            metadatas=new_metas[start:start+BATCH],
        )
        processed += min(BATCH, len(new_ids) - start)
        done = min(start + BATCH, len(new_ids))
        log.info(f"  Upserted {done}/{len(new_ids)}")

        if processed >= SESSION_MAX:
            log.info(f"  ⏸  Session cap reached ({SESSION_MAX}) — re-run to continue")
            break

    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Batch-ingest all knowledge/ submodules into ChromaDB"
    )
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--reset",      action="store_true")
    parser.add_argument("--collection", default=COLLECTION)
    args = parser.parse_args()

    log.info(f"🔍 Scanning {KNOWLEDGE} ...")
    chunks = collect_all_chunks()
    log.info(f"\n📦 Total chunks: {len(chunks)}")

    if args.dry_run:
        log.info("[DRY RUN] — not writing to ChromaDB")
        return

    log.info(f"\n💾 Loading into '{args.collection}'...")
    new = load_to_chroma(chunks, args.collection, reset=args.reset)
    log.info(f"\n✅ {new} new chunks added to '{args.collection}'")


if __name__ == "__main__":
    main()
