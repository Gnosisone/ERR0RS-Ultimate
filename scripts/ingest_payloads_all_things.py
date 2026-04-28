#!/usr/bin/env python3
"""
PayloadsAllTheThings → ChromaDB RAG Ingester
Walks the PayloadsAllTheThings submodule, chunks every README.md by
section heading, and loads them into ERR0RS's ChromaDB knowledge base.

Usage:
    python3 scripts/ingest_payloads_all_things.py
    python3 scripts/ingest_payloads_all_things.py --dry-run
    python3 scripts/ingest_payloads_all_things.py --reset   # wipe & re-ingest

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os
import sys
import re
import hashlib
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Paths ────────────────────────────────────────────────────────────────────
REPO_ROOT   = Path(__file__).resolve().parent.parent
PAT_ROOT    = REPO_ROOT / "knowledge" / "exploitation" / "PayloadsAllTheThings"
CHROMA_PATH = REPO_ROOT / "errors_knowledge_db"
COLLECTION  = "payloads_all_things"

# ─── MITRE mapping for auto-tagging ──────────────────────────────────────────
CATEGORY_MITRE = {
    "SQL Injection":              "T1190",
    "XSS Injection":              "T1059.007",
    "Command Injection":          "T1059",
    "File Inclusion":             "T1190",
    "Directory Traversal":        "T1083",
    "Server Side Request Forgery":"T1090",
    "Server Side Template Injection": "T1190",
    "Insecure Deserialization":   "T1190",
    "XML External Entity":        "T1190",
    "XXE Injection":              "T1190",
    "LDAP Injection":             "T1190",
    "NoSQL Injection":            "T1190",
    "GraphQL Injection":          "T1190",
    "JSON Web Token":             "T1552",
    "OAuth Misconfiguration":     "T1550",
    "CORS Misconfiguration":      "T1557",
    "Account Takeover":           "T1078",
    "Insecure Direct Object":     "T1078",
    "Open Redirect":              "T1566",
    "Request Smuggling":          "T1190",
    "Race Condition":             "T1499",
    "Prototype Pollution":        "T1059.007",
    "SAML Injection":             "T1550",
    "Dependency Confusion":       "T1195",
    "API Key Leaks":              "T1552",
    "Insecure Source Code":       "T1552",
    "Mass Assignment":            "T1190",
    "Denial of Service":          "T1499",
    "DNS Rebinding":              "T1557",
    "Upload Insecure Files":      "T1190",
    "Clickjacking":               "T1185",
    "CSRF":                       "T1185",
    "Cross-Site Request Forgery": "T1185",
}

# ─── Attack type tagger ───────────────────────────────────────────────────────
def tag_attack_type(category: str, section: str) -> str:
    text = (category + " " + section).lower()
    if any(w in text for w in ["inject", "sqli", "nosql", "ldap", "xpath"]):
        return "injection"
    if any(w in text for w in ["xss", "cross-site script"]):
        return "xss"
    if any(w in text for w in ["ssrf", "request forgery"]):
        return "ssrf"
    if any(w in text for w in ["rce", "command", "execution", "shell"]):
        return "rce"
    if any(w in text for w in ["traversal", "path", "lfi", "rfi", "inclusion"]):
        return "path_traversal"
    if any(w in text for w in ["auth", "token", "jwt", "oauth", "saml", "session"]):
        return "auth_bypass"
    if any(w in text for w in ["deserializ", "xxe", "xml"]):
        return "deserialization"
    if any(w in text for w in ["upload", "file"]):
        return "file_upload"
    if any(w in text for w in ["redirect", "csrf", "clickjack"]):
        return "client_side"
    if any(w in text for w in ["api", "key", "leak", "exposure"]):
        return "info_disclosure"
    return "web_app"


# ─── Chunk a README.md by ## section headings ─────────────────────────────────
def chunk_readme(readme_path: Path, category: str) -> list[dict]:
    """Split README into chunks at every ## heading. Returns list of doc dicts."""
    try:
        text = readme_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.warning(f"Cannot read {readme_path}: {e}")
        return []

    # Split on ## headings (keep heading in chunk)
    sections = re.split(r"(?m)^(#{1,3} .+)$", text)

    chunks = []
    current_heading = f"{category} — Overview"
    current_body = ""

    def flush(heading, body):
        body = body.strip()
        if len(body) < 40:
            return  # skip near-empty sections
        uid = hashlib.sha256(f"{category}::{heading}::{body[:80]}".encode()).hexdigest()[:16]
        mitre = next(
            (v for k, v in CATEGORY_MITRE.items() if k.lower() in category.lower()), "T1190"
        )
        chunks.append({
            "id":       uid,
            "document": f"[{category}] {heading}\n\n{body}",
            "metadata": {
                "source":      "PayloadsAllTheThings",
                "category":    category,
                "section":     heading,
                "mitre":       mitre,
                "attack_type": tag_attack_type(category, heading),
                "path":        str(readme_path.relative_to(REPO_ROOT)),
            }
        })

    for part in sections:
        if re.match(r"^#{1,3} ", part):
            flush(current_heading, current_body)
            current_heading = part.strip("# ").strip()
            current_body = ""
        else:
            current_body += part

    flush(current_heading, current_body)
    return chunks

# ─── Walk all category folders ────────────────────────────────────────────────
def collect_all_chunks() -> list[dict]:
    all_chunks = []
    skipped = []

    # Skip meta/utility folders
    SKIP_DIRS = {"_LEARNING_AND_SOCIALS", "_template_vuln", ".git", ".github", "Intruder", "Images", "Files"}

    for item in sorted(PAT_ROOT.iterdir()):
        if not item.is_dir() or item.name in SKIP_DIRS:
            continue

        category = item.name
        readme = item / "README.md"

        if not readme.exists():
            skipped.append(category)
            continue

        chunks = chunk_readme(readme, category)
        all_chunks.extend(chunks)
        log.info(f"  ✓ {category:<40} {len(chunks):>3} chunks")

    if skipped:
        log.warning(f"Skipped (no README): {', '.join(skipped)}")

    return all_chunks


# ─── ChromaDB loader ──────────────────────────────────────────────────────────
def load_to_chroma(chunks: list[dict], reset: bool = False) -> None:
    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed. Run: pip install chromadb --break-system-packages")
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection(COLLECTION)
            log.info(f"[RESET] Deleted existing collection '{COLLECTION}'")
        except Exception:
            pass

    col = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"description": "PayloadsAllTheThings — web app attack payloads & techniques"}
    )

    # Batch upsert in chunks of 100
    BATCH = 100
    ids    = [c["id"]       for c in chunks]
    docs   = [c["document"] for c in chunks]
    metas  = [c["metadata"] for c in chunks]

    existing = set(col.get(ids=ids)["ids"])
    new_ids, new_docs, new_metas = [], [], []
    for i, did in enumerate(ids):
        if did not in existing:
            new_ids.append(did)
            new_docs.append(docs[i])
            new_metas.append(metas[i])

    if not new_ids:
        log.info("All chunks already in ChromaDB — nothing to add.")
        return

    for start in range(0, len(new_ids), BATCH):
        col.add(
            ids=new_ids[start:start+BATCH],
            documents=new_docs[start:start+BATCH],
            metadatas=new_metas[start:start+BATCH],
        )
        log.info(f"  Upserted batch {start//BATCH + 1} ({min(start+BATCH, len(new_ids))}/{len(new_ids)})")

    log.info(f"\n✅ Done — {len(new_ids)} new chunks in collection '{COLLECTION}'")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ingest PayloadsAllTheThings into ERR0RS ChromaDB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be ingested without writing")
    parser.add_argument("--reset",   action="store_true", help="Delete and recreate the collection first")
    args = parser.parse_args()

    if not PAT_ROOT.exists():
        log.error(f"PayloadsAllTheThings submodule not found at {PAT_ROOT}")
        log.error("Run: git submodule update --init knowledge/exploitation/PayloadsAllTheThings")
        sys.exit(1)

    log.info(f"🔍 Scanning {PAT_ROOT} ...")
    chunks = collect_all_chunks()
    log.info(f"\n📦 Total chunks collected: {len(chunks)}")

    if args.dry_run:
        log.info("[DRY RUN] — not writing to ChromaDB")
        for c in chunks[:5]:
            print(f"\n--- {c['metadata']['category']} / {c['metadata']['section']} ---")
            print(c['document'][:300])
        return

    log.info(f"\n💾 Loading into ChromaDB at {CHROMA_PATH} ...")
    load_to_chroma(chunks, reset=args.reset)


if __name__ == "__main__":
    main()
