#!/usr/bin/env python3
"""
ERR0RS — BadUSB Payload Library RAG Ingester
=============================================
Ingests Flipper Zero / Rubber Ducky / BadUSB payload collections
into ChromaDB for semantic search and teach engine augmentation.

Handles the nocomp/Flipper_Zero_Badusb_hack5_payloads structure
and any similarly organized BadUSB repo.

Usage:
    python3 scripts/ingest_badusb_payloads.py
    python3 scripts/ingest_badusb_payloads.py --dry-run
    python3 scripts/ingest_badusb_payloads.py --reset

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os, sys, re, hashlib, argparse, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT   = Path(__file__).resolve().parent.parent
BADUSB_ROOT = REPO_ROOT / "knowledge" / "badusb"
CHROMA_PATH = REPO_ROOT / "errors_knowledge_db"
COLLECTION  = "badusb_payloads"

# Repo-specific ingestion configs
# Maps repo dir name → (category_detection_mode, description)
REPO_CONFIGS = {
    "nocomp-hack5-payloads":      "category_dirs",   # credentials/execution/etc at root
    "I-Am-Jakoby-FlipperBadUSB": "payloads_dir",    # Payloads/Flip-*/
    "Flipper-Zero-BadUSB":        "payloads_dir",    # same author, same structure
    "aleff-flipper-shits":        "flat_payloads",   # payload dirs at root
    "bad_ducky":                  "flat_payloads",   # demo_scripts/ at root
    "WHID-injector":              "flat_payloads",   # Payloads/ + misc dirs
    "WHID-31337":                 "flat_payloads",   # RF/HID attack dirs at root
}

# Category → MITRE mapping
CATEGORY_MITRE = {
    "credentials":       "T1056",    # Input Capture / Credential Harvesting
    "execution":         "T1059",    # Command & Scripting Interpreter
    "exfiltration":      "T1041",    # Exfiltration Over C2 Channel
    "remote_access":     "T1021.006",# Remote Services — WinRM
    "recon":             "T1082",    # System Information Discovery
    "general":           "T1200",    # Hardware Additions
    "incident_response": "T1200",    # Hardware Additions
    "mobile":            "T1200",    # Hardware Additions
    "prank":             "T1200",    # Hardware Additions
}

# Target OS detection
def detect_os(content: str) -> str:
    c = content.lower()
    if any(w in c for w in ["powershell", "cmd", "winrm", "net user", "reg add", "windows"]):
        return "windows"
    if any(w in c for w in ["sudo", "bash", "linux", "apt", "chmod"]):
        return "linux"
    if any(w in c for w in ["android", "adb", "mobile"]):
        return "android"
    if any(w in c for w in ["ios", "iphone", "imessage"]):
        return "ios"
    return "multi"


def parse_payload_header(content: str) -> dict:
    """Extract REM header metadata from DuckyScript payload."""
    meta = {"title": "", "author": "", "description": "", "category": "", "target": "", "version": ""}
    for line in content.split("\n")[:25]:
        line = line.strip()
        stripped = re.sub(r"^REM\s*#?\s*", "", line, flags=re.IGNORECASE).strip()
        for field in ["title", "author", "description", "category", "target", "version"]:
            m = re.match(rf"^{field}\s*[:\-]\s*(.+)", stripped, re.IGNORECASE)
            if m:
                meta[field] = m.group(1).strip()
    return meta


def chunk_badusb_repo(repo_path: Path, repo_name: str) -> list[dict]:
    """Walk a BadUSB payload repo and create RAG chunks."""
    chunks = []

    # Walk category directories
    for category_dir in sorted(repo_path.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        category = category_dir.name.lower()
        mitre    = CATEGORY_MITRE.get(category, "T1200")

        # Walk payload subdirectories
        for payload_dir in sorted(category_dir.iterdir()):
            if not payload_dir.is_dir():
                continue

            payload_name = payload_dir.name
            payload_text = ""
            readme_text  = ""
            header_meta  = {}

            # Collect all text files in this payload dir
            for f in sorted(payload_dir.iterdir()):
                if not f.is_file():
                    continue

                ext = f.suffix.lower()
                if ext in (".txt",):
                    try:
                        content = f.read_text(encoding="utf-8", errors="replace")
                        if not header_meta:
                            header_meta = parse_payload_header(content)
                        payload_text += f"\n\n=== {f.name} ===\n{content}"
                    except Exception:
                        pass

                elif ext in (".md",):
                    try:
                        readme_text = f.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass

                elif ext in (".ps1", ".sh", ".py"):
                    try:
                        code = f.read_text(encoding="utf-8", errors="replace")
                        payload_text += f"\n\n=== {f.name} (script) ===\n{code}"
                    except Exception:
                        pass

            if not payload_text and not readme_text:
                continue

            # Build combined document
            title = header_meta.get("title") or payload_name
            author = header_meta.get("author", "unknown")
            desc   = header_meta.get("description", "")
            target = header_meta.get("target", detect_os(payload_text))

            doc_parts = [f"[BadUSB Payload: {repo_name}/{category}/{payload_name}]"]
            doc_parts.append(f"Title: {title}")
            doc_parts.append(f"Author: {author}")
            doc_parts.append(f"Category: {category}")
            doc_parts.append(f"Target: {target}")
            if desc:
                doc_parts.append(f"Description: {desc}")
            if readme_text:
                # First 800 chars of README
                doc_parts.append(f"\nREADME:\n{readme_text[:800]}")
            if payload_text:
                doc_parts.append(f"\nPAYLOAD:\n{payload_text[:1200]}")

            document = "\n".join(doc_parts)
            uid = hashlib.sha256(
                f"{repo_name}::{category}::{payload_name}".encode()
            ).hexdigest()[:16]

            chunks.append({
                "id": uid,
                "document": document,
                "metadata": {
                    "source":       f"badusb/{repo_name}",
                    "repo":         repo_name,
                    "category":     category,
                    "payload":      payload_name,
                    "title":        title,
                    "author":       author,
                    "target_os":    target,
                    "mitre":        mitre,
                    "attack_type":  "badusb",
                }
            })

        log.info(f"  ✓ {repo_name}/{category:<30} → {len([c for c in chunks if c['metadata']['category']==category])} payloads")

    return chunks


def _ingest_flat_dirs(root, repo_name):
    chunks = []
    SKIP = {".git",".github","node_modules","__pycache__","Assets","Images","images","README"}
    for item in sorted(root.iterdir()):
        if not item.is_dir() or item.name.startswith(".") or item.name in SKIP:
            continue
        payload_text = readme_text = ""
        header_meta  = {}
        for f in sorted(item.rglob("*")):
            if not f.is_file() or ".git" in str(f): continue
            ext = f.suffix.lower()
            if ext in (".txt",".ps1",".sh",".py",".rb",".bat"):
                try:
                    c = f.read_text(encoding="utf-8",errors="replace")
                    if not header_meta and ext==".txt": header_meta=parse_payload_header(c)
                    payload_text += f"\n\n=== {f.name} ===\n{c[:800]}"
                except: pass
            elif ext==".md":
                try: readme_text=f.read_text(encoding="utf-8",errors="replace")[:600]
                except: pass
        if not payload_text and not readme_text: continue
        title  = header_meta.get("title") or item.name
        author = header_meta.get("author","unknown")
        desc   = header_meta.get("description","")
        target = header_meta.get("target", detect_os(payload_text))
        lower  = (payload_text+readme_text+desc).lower()
        mitre  = "T1200"
        if any(w in lower for w in ["winrm","psremoting"]): mitre="T1021.006"
        elif any(w in lower for w in ["reverse shell","netcat","ncat"]): mitre="T1059"
        elif any(w in lower for w in ["password","credential","hash"]): mitre="T1552"
        elif any(w in lower for w in ["wifi","ssid","wpa"]): mitre="T1040"
        elif any(w in lower for w in ["exfil","webhook","discord"]): mitre="T1041"
        elif any(w in lower for w in ["defender","amsi","antivirus"]): mitre="T1562"
        uid = hashlib.sha256(f"{repo_name}::{item.name}".encode()).hexdigest()[:16]
        chunks.append({"id":uid,
            "document":"\n".join(filter(None,[
                f"[BadUSB: {repo_name}/{item.name}]",
                f"Title: {title}", f"Author: {author}", f"Target: {target}",
                f"Description: {desc}" if desc else "",
                f"\nREADME:\n{readme_text}" if readme_text else "",
                f"\nPAYLOAD:\n{payload_text}" if payload_text else "",
            ])),
            "metadata":{"source":f"badusb/{repo_name}","repo":repo_name,
                "category":"badusb","payload":item.name,"title":title,
                "author":author,"target_os":target,"mitre":mitre,"attack_type":"badusb"}
        })
    return chunks


def collect_all_chunks():
    all_chunks = []
    CATEGORY_REPOS = {"nocomp-hack5-payloads"}
    PAYLOADS_DIR_REPOS = {"I-Am-Jakoby-FlipperBadUSB","Flipper-Zero-BadUSB"}

    for repo_dir in sorted(BADUSB_ROOT.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."): continue
        name = repo_dir.name
        log.info(f"\n  📂 {name}...")
        if name in CATEGORY_REPOS:
            chunks = chunk_badusb_repo(repo_dir, name)
        elif name in PAYLOADS_DIR_REPOS:
            pd = repo_dir/"Payloads"
            chunks = _ingest_flat_dirs(pd if pd.exists() else repo_dir, name)
        else:
            chunks = _ingest_flat_dirs(repo_dir, name)
        if chunks:
            all_chunks.extend(chunks)
            log.info(f"  ✓ {name:<40} {len(chunks):>4} chunks")
    return all_chunks


def load_to_chroma(chunks: list[dict], reset: bool = False) -> int:
    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed.")
        return 0

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection(COLLECTION)
            log.info(f"[RESET] Deleted '{COLLECTION}'")
        except Exception:
            pass

    col = client.get_or_create_collection(
        name=COLLECTION,
        metadata={"description": "BadUSB/DuckyScript payload library — Flipper Zero + Rubber Ducky"}
    )

    ids   = [c["id"] for c in chunks]
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

    BATCH = 50
    for start in range(0, len(new_ids), BATCH):
        col.add(
            ids=new_ids[start:start+BATCH],
            documents=new_docs[start:start+BATCH],
            metadatas=new_metas[start:start+BATCH],
        )
        log.info(f"  Upserted {min(start+BATCH, len(new_ids))}/{len(new_ids)}")

    return len(new_ids)


def main():
    parser = argparse.ArgumentParser(description="Ingest BadUSB payloads into ERR0RS ChromaDB")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset",   action="store_true")
    args = parser.parse_args()

    log.info(f"🔍 Scanning BadUSB knowledge base at {BADUSB_ROOT}...")
    chunks = collect_all_chunks()
    log.info(f"\n📦 Total payload chunks: {len(chunks)}")

    if args.dry_run:
        log.info("[DRY RUN] — not writing to ChromaDB")
        if chunks:
            c = chunks[0]
            log.info(f"\nSample — {c['metadata']['title']}:")
            print(c["document"][:500])
        return

    log.info(f"\n💾 Loading into ChromaDB collection '{COLLECTION}'...")
    new = load_to_chroma(chunks, reset=args.reset)
    log.info(f"\n✅ {new} new chunks added to '{COLLECTION}'")


if __name__ == "__main__":
    main()
