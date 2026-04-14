#!/usr/bin/env python3
"""
ERR0RS — BadUSB Payload Ingestor
Scans knowledge/badusb/* for DuckyScript .txt files, parses REM metadata,
and upserts everything into the 'badusb_payloads' ChromaDB collection.

Usage:
    python3 scripts/ingest_badusb_payloads.py
    python3 scripts/ingest_badusb_payloads.py --reset   # wipe & re-ingest
    python3 scripts/ingest_badusb_payloads.py --dry-run # count only
"""

import re, sys, hashlib, argparse
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parents[1]
BADUSB_DIR = ROOT / "knowledge" / "badusb"
CHROMA_DIR = ROOT / "errors_knowledge_db"
COLLECTION = "badusb_payloads"

sys.path.insert(0, str(ROOT))

# ── DuckyScript detection ─────────────────────────────────────────────────────
DUCKY_RE = re.compile(
    r'^\s*(REM|DELAY|STRING|STRINGLN|GUI|ENTER|TAB|ALT|CTRL|SHIFT|WINDOWS|'
    r'DEFAULT_DELAY|ATTACKMODE|ID|REPEAT|WAIT_FOR_BUTTON_PRESS|'
    r'UPARROW|DOWNARROW|LEFTARROW|RIGHTARROW|ESCAPE|BACKSPACE|'
    r'F\d{1,2}|CAPS|NUMLOCK|SCROLLOCK|PRINTSCREEN|SPACE|HOME|END|'
    r'PAGEUP|PAGEDOWN|INSERT|DELETE|LED)\b',
    re.MULTILINE
)

# ── Metadata parser ──────────────────────────────────────────────────────────
REM_FIELD_RE = re.compile(
    r'^\s*REM\s+(Title|Author|Description|Target|Category|Version|Requirements?|'
    r'Tags?|Platform|OS|Date)\s*[:\-]?\s*(.+)',
    re.IGNORECASE
)

def infer_platform(path: Path, content: str) -> str:
    """Infer target OS from path and content."""
    parts = str(path).lower()
    text  = content.lower()
    if any(x in parts for x in ["windows", "win"]):       return "windows"
    if any(x in parts for x in ["macos", "mac", "osx"]):  return "macos"
    if any(x in parts for x in ["linux", "unix"]):        return "linux"
    if any(x in parts for x in ["android"]):              return "android"
    if any(x in parts for x in ["ios", "iphone"]):        return "ios"
    if any(x in text   for x in ["gui r\n", "win+r", "powershell", "cmd.exe", "regedit"]): return "windows"
    if any(x in text   for x in ["gui space\n", "terminal\n", "launchd", "brew"]):          return "macos"
    if any(x in text   for x in ["bash -i", "/dev/tcp", "sudo", "apt-get"]):                return "linux"
    return "cross"

def infer_category(path: Path, content: str, meta: dict) -> str:
    """Infer category from path, content, and parsed metadata."""
    parts = str(path).lower()
    text  = content.lower()
    cat   = (meta.get("category") or meta.get("tags") or "").lower()

    # From REM metadata first
    if any(x in cat for x in ["exfil", "exfiltrate", "loot"]):     return "exfil"
    if any(x in cat for x in ["persist", "backdoor", "startup"]):   return "persistence"
    if any(x in cat for x in ["recon", "enum", "info"]):            return "recon"
    if any(x in cat for x in ["shell", "reverse", "bind"]):         return "shell"
    if any(x in cat for x in ["prank", "fun", "troll"]):            return "prank"
    if any(x in cat for x in ["cred", "password", "hash"]):        return "credentials"
    if any(x in cat for x in ["privesc", "escalat", "admin"]):      return "privesc"
    if any(x in cat for x in ["evasion", "bypass", "av", "amsi"]): return "evasion"

    # From path
    for chunk in parts.split("/"):
        if "exfil"    in chunk: return "exfil"
        if "persist"  in chunk: return "persistence"
        if "recon"    in chunk: return "recon"
        if "shell"    in chunk: return "shell"
        if "prank"    in chunk: return "prank"
        if "cred"     in chunk: return "credentials"
        if "privesc"  in chunk: return "privesc"
        if "evasion"  in chunk: return "evasion"
        if "keylog"   in chunk: return "surveillance"
        if "screencap" in chunk: return "surveillance"

    # From content
    if re.search(r'discord.*webhook|dropbox|curl.*http|exfil', text): return "exfil"
    if re.search(r'reg add.*run|schtasks|startup|cron|persist',  text): return "persistence"
    if re.search(r'reverse.*shell|bash.*tcp|nc.*lvnp',           text): return "shell"
    if re.search(r'whoami|ipconfig|systeminfo|netstat|ifconfig',  text): return "recon"
    if re.search(r'keylog|screenshot|webcam|screen.cap',          text): return "surveillance"
    if re.search(r'password|hash|sam|lsass|mimikatz|cred',        text): return "credentials"
    if re.search(r'rickroll|prank|troll|fun|joke',                text): return "prank"
    return "utility"

def parse_payload(filepath: Path, repo: str) -> dict | None:
    """Parse a single DuckyScript file into a chunk dict."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None

    if not DUCKY_RE.search(content):
        return None   # not a DuckyScript file

    # Parse REM metadata header fields
    meta_parsed: dict[str, str] = {}
    for line in content.split("\n")[:30]:   # headers are always near the top
        m = REM_FIELD_RE.match(line)
        if m:
            key = m.group(1).lower().rstrip("s")  # normalise plural
            val = m.group(2).strip()
            meta_parsed[key] = val

    title       = meta_parsed.get("title", "")
    author      = meta_parsed.get("author", "")
    description = meta_parsed.get("description", "")
    target_raw  = meta_parsed.get("target", "")
    platform    = infer_platform(filepath, content)
    category    = infer_category(filepath, content, meta_parsed)

    # Build human-readable title from filename if REM Title missing
    if not title:
        title = filepath.stem.replace("_", " ").replace("-", " ").title()

    # Relative path for display & dedup
    rel = str(filepath.relative_to(ROOT))

    # Document text — structured for embedding + display
    doc_lines = [
        f"[BadUSB Payload: {repo}/{filepath.stem}]",
        f"Title: {title}",
    ]
    if author:      doc_lines.append(f"Author: {author}")
    if description: doc_lines.append(f"Description: {description}")
    if target_raw:  doc_lines.append(f"Target: {target_raw}")
    doc_lines.append(f"Platform: {platform}  Category: {category}")
    doc_lines.append("")
    doc_lines.append(content[:3000])   # cap at 3k chars for embedding quality

    doc = "\n".join(doc_lines)

    # Stable unique ID from relative path
    uid = "badusb_" + hashlib.md5(rel.encode()).hexdigest()[:16]

    return {
        "id":       uid,
        "document": doc,
        "metadata": {
            "source":      f"badusb/{repo}",
            "repo":        repo,
            "path":        rel,
            "title":       title,
            "author":      author,
            "description": description[:200],
            "platform":    platform,
            "category":    category,
            "target":      target_raw[:100],
            "filename":    filepath.name,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="ERR0RS BadUSB Payload Ingestor")
    parser.add_argument("--reset",   action="store_true", help="Wipe collection and re-ingest")
    parser.add_argument("--dry-run", action="store_true", help="Count files only, no DB write")
    parser.add_argument("--repo",    default=None,        help="Only ingest a specific repo")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  ERR0RS BadUSB Payload Ingestor")
    print(f"  Source : {BADUSB_DIR}")
    print(f"  Target : {COLLECTION}")
    print(f"{'='*60}\n")

    if not BADUSB_DIR.exists():
        print(f"❌ {BADUSB_DIR} not found")
        sys.exit(1)

    # Collect all DuckyScript files
    chunks = []
    skipped = 0
    repos = sorted(BADUSB_DIR.iterdir()) if not args.repo else [BADUSB_DIR / args.repo]

    for repo_dir in repos:
        if not repo_dir.is_dir():
            continue
        repo_name = repo_dir.name
        repo_chunks = []

        for txt_file in sorted(repo_dir.rglob("*.txt")):
            chunk = parse_payload(txt_file, repo_name)
            if chunk:
                repo_chunks.append(chunk)
            else:
                skipped += 1

        print(f"  {repo_name:35} {len(repo_chunks):4d} payloads")
        chunks.extend(repo_chunks)

    print(f"\n  Total DuckyScript payloads : {len(chunks)}")
    print(f"  Non-DuckyScript skipped   : {skipped}")

    if args.dry_run:
        print("\n  [DRY RUN] No database changes made.")

        # Show category breakdown
        from collections import Counter
        cats = Counter(c["metadata"]["category"] for c in chunks)
        plats = Counter(c["metadata"]["platform"] for c in chunks)
        print("\n  Categories:")
        for cat, n in cats.most_common():
            print(f"    {n:4d}  {cat}")
        print("\n  Platforms:")
        for plat, n in plats.most_common():
            print(f"    {n:4d}  {plat}")
        return

    # Load into ChromaDB
    print(f"\n  Loading into ChromaDB '{COLLECTION}'...")
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))

        if args.reset:
            try:
                client.delete_collection(COLLECTION)
                print(f"  [RESET] Deleted existing '{COLLECTION}'")
            except Exception:
                pass

        col = client.get_or_create_collection(
            name=COLLECTION,
            metadata={"description": "ERR0RS BadUSB DuckyScript payload library"}
        )

        before = col.count()

        # Deduplicate against existing
        all_ids = [c["id"] for c in chunks]
        try:
            existing = set(col.get(ids=all_ids)["ids"])
        except Exception:
            existing = set()

        new_chunks = [c for c in chunks if c["id"] not in existing]
        print(f"  Already in DB : {len(existing)}")
        print(f"  New to add    : {len(new_chunks)}")

        if not new_chunks:
            print("  ✅ All payloads already in DB — nothing to do.")
        else:
            BATCH = 200
            for i in range(0, len(new_chunks), BATCH):
                batch = new_chunks[i:i+BATCH]
                col.add(
                    ids       =[c["id"]       for c in batch],
                    documents =[c["document"] for c in batch],
                    metadatas =[c["metadata"] for c in batch],
                )
                done = min(i+BATCH, len(new_chunks))
                print(f"  ✓ {done:4d}/{len(new_chunks)} chunks ingested...")

        after = col.count()
        print(f"\n  ✅ Done — collection now has {after} documents (+{after-before} new)")

    except ImportError:
        print("❌ chromadb not installed: pip3 install chromadb --break-system-packages")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
