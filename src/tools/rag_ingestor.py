#!/usr/bin/env python3
"""
ERR0RS — Universal GitHub RAG Ingestor
=======================================
One command to add any GitHub repo to ERR0RS's ChromaDB knowledge base.

Usage (from ERR0RS interactive shell):
    add to rag "https://github.com/user/repo"
    add to rag github.com/user/repo
    add to rag user/repo

Usage (standalone):
    python3 src/tools/rag_ingestor.py https://github.com/user/repo
    python3 src/tools/rag_ingestor.py user/repo --dry-run
    python3 src/tools/rag_ingestor.py user/repo --collection my_collection

What it does:
    1. Resolves the URL → owner/repo format
    2. Fetches repo metadata via GitHub API (stars, description, language)
    3. Walks all files recursively via API (no clone needed)
    4. Chunks text/markdown files by section or paragraph
    5. Auto-tags each chunk with: repo, owner, file, extension, topic
    6. Upserts into ChromaDB collection 'github_rag' (or custom name)
    7. Optionally adds as a git submodule to knowledge/

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os, sys, re, json, time, hashlib, argparse, logging
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("rag_ingestor")

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[2]
CHROMA_PATH = ROOT / "errors_knowledge_db"
KNOWLEDGE   = ROOT / "knowledge"
COLLECTION  = "github_rag"

# ─── File extensions we ingest ────────────────────────────────────────────────
INGEST_EXTS = {
    ".md", ".txt", ".rst", ".py", ".sh", ".bash", ".zsh",
    ".rb", ".pl", ".ps1", ".yaml", ".yml", ".json", ".conf",
    ".cfg", ".ini", ".toml", ".c", ".h", ".cpp", ".java",
    ".go", ".rs", ".js", ".ts", ".php", ".lua", ".asm",
    ".nse", ".yar", ".yara", ".sigma", ".rules",
}

# Extensions to skip entirely
SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".mp4", ".mp3", ".wav", ".zip", ".gz", ".tar", ".7z",
    ".exe", ".dll", ".so", ".bin", ".pdf", ".docx", ".xlsx",
    ".pptx", ".pyc", ".pyo", ".class", ".jar", ".deb", ".rpm",
    ".img", ".iso", ".vmdk", ".ova", ".lock", ".sum",
}

# Skip these paths entirely
SKIP_PATHS = {
    ".git", "node_modules", "__pycache__", ".pytest_cache",
    "vendor", "dist", "build", ".venv", "venv", "env",
    "site-packages", ".github",
}

# Max file size to ingest (bytes)
MAX_FILE_SIZE = 150_000  # 150KB — avoids massive generated files

# ─── GitHub API helpers ───────────────────────────────────────────────────────

def _api_get(url: str, token: str = None) -> dict | list | None:
    """GET GitHub API URL, return parsed JSON or None."""
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "ERR0RS-Ultimate-RAG/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        req  = Request(url, headers=headers)
        resp = urlopen(req, timeout=15)
        return json.loads(resp.read())
    except HTTPError as e:
        if e.code == 403:
            log.warning("GitHub API rate limited. Set GITHUB_TOKEN env var for higher limits.")
        elif e.code == 404:
            log.error(f"Repo not found: {url}")
        else:
            log.error(f"HTTP {e.code}: {url}")
        return None
    except URLError as e:
        log.error(f"Network error: {e}")
        return None


def _raw_get(url: str) -> str | None:
    """GET raw file content, return text or None."""
    try:
        req  = Request(url, headers={"User-Agent": "ERR0RS-Ultimate-RAG/1.0"})
        resp = urlopen(req, timeout=15)
        raw  = resp.read()
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def resolve_repo(url_or_slug: str) -> tuple[str, str]:
    """
    Parse any form of GitHub reference into (owner, repo).
    Accepts:
        https://github.com/user/repo
        github.com/user/repo
        user/repo
    """
    url_or_slug = url_or_slug.strip().strip('"').strip("'")
    # strip protocol
    slug = re.sub(r"^https?://", "", url_or_slug)
    slug = slug.strip("/")
    # strip github.com prefix
    slug = re.sub(r"^(?:www\.)?github\.com/", "", slug)
    # strip trailing .git
    slug = re.sub(r"\.git$", "", slug)
    # strip trailing path (tree/main/...)
    slug = re.sub(r"/tree/.*$", "", slug)
    parts = slug.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse repo from: '{url_or_slug}' → need 'owner/repo'")
    return parts[0], parts[1]


# ─── File tree walker (API-based, no clone needed) ────────────────────────────

def _walk_tree(owner: str, repo: str, sha: str = "HEAD",
               token: str = None, prefix: str = "") -> list[dict]:
    """
    Recursively walk the GitHub tree API.
    Returns list of {path, url, size, type} for blobs (files).
    """
    url  = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{sha}?recursive=1"
    data = _api_get(url, token)
    if not data or "tree" not in data:
        return []

    files = []
    for item in data["tree"]:
        if item["type"] != "blob":
            continue
        path = item["path"]
        # skip by directory
        parts = Path(path).parts
        if any(p in SKIP_PATHS for p in parts):
            continue
        ext = Path(path).suffix.lower()
        if ext in SKIP_EXTS:
            continue
        size = item.get("size", 0)
        if size > MAX_FILE_SIZE:
            log.debug(f"  Skipping large file ({size}B): {path}")
            continue
        files.append({
            "path": path,
            "sha":  item["sha"],
            "size": size,
            "ext":  ext,
        })

    return files


# ─── Content fetcher ──────────────────────────────────────────────────────────

def fetch_file(owner: str, repo: str, path: str,
               branch: str = "main", token: str = None) -> str | None:
    """Fetch raw file content. Tries main then master."""
    for br in [branch, "master", "main", "dev"]:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{path}"
        content = _raw_get(url)
        if content is not None:
            return content
    return None


# ─── Chunking strategy ────────────────────────────────────────────────────────

def chunk_content(content: str, path: str, owner: str, repo: str) -> list[dict]:
    """
    Smart chunking:
      - Markdown (.md, .rst): split on ## headings
      - Code (.py, .sh, .rb etc): split on def/class/function blocks + blank lines
      - Config/YAML/JSON: whole file as one chunk (usually small)
      - Plain text: paragraph-based splitting
    """
    ext  = Path(path).suffix.lower()
    name = Path(path).name
    chunks = []

    if not content or len(content.strip()) < 30:
        return []

    # ── Markdown / RST ────────────────────────────────────────────
    if ext in (".md", ".rst", ".txt"):
        sections = re.split(r"(?m)^(#{1,3} .+)$", content)
        current_heading = f"{name} — Overview"
        current_body    = ""

        def flush_md(heading, body):
            body = body.strip()
            if len(body) < 40:
                return
            uid = hashlib.sha256(
                f"{owner}/{repo}::{path}::{heading}::{body[:60]}".encode()
            ).hexdigest()[:16]
            chunks.append({
                "id":       uid,
                "document": f"[{owner}/{repo}: {path}]\n## {heading}\n\n{body}",
                "metadata": {
                    "source":  f"github/{owner}/{repo}",
                    "owner":   owner,
                    "repo":    repo,
                    "path":    path,
                    "section": heading,
                    "ext":     ext,
                    "type":    "markdown",
                }
            })

        for part in sections:
            if re.match(r"^#{1,3} ", part):
                flush_md(current_heading, current_body)
                current_heading = part.strip("# ").strip()
                current_body    = ""
            else:
                current_body += part
        flush_md(current_heading, current_body)

    # ── Code files ─────────────────────────────────────────────────
    elif ext in (".py", ".rb", ".sh", ".bash", ".zsh", ".pl",
                 ".js", ".ts", ".go", ".rs", ".java", ".c",
                 ".cpp", ".h", ".php", ".lua", ".ps1"):
        # Split on double newlines (logical blocks)
        paras = re.split(r"\n{3,}", content)
        buf   = []
        PARA_CHUNK = 12  # paragraphs per chunk

        for i, para in enumerate(paras):
            para = para.strip()
            if para:
                buf.append(para)
            if len(buf) >= PARA_CHUNK or (i == len(paras) - 1 and buf):
                body = "\n\n".join(buf)
                uid  = hashlib.sha256(
                    f"{owner}/{repo}::{path}::chunk{len(chunks)}::{body[:60]}".encode()
                ).hexdigest()[:16]
                chunks.append({
                    "id":       uid,
                    "document": f"[{owner}/{repo}: {path}]\n\n{body}",
                    "metadata": {
                        "source":  f"github/{owner}/{repo}",
                        "owner":   owner,
                        "repo":    repo,
                        "path":    path,
                        "section": f"chunk_{len(chunks)}",
                        "ext":     ext,
                        "type":    "code",
                    }
                })
                buf = []

    # ── Everything else — whole file as single chunk ───────────────
    else:
        body = content.strip()
        if len(body) >= 40:
            uid = hashlib.sha256(
                f"{owner}/{repo}::{path}::{body[:80]}".encode()
            ).hexdigest()[:16]
            chunks.append({
                "id":       uid,
                "document": f"[{owner}/{repo}: {path}]\n\n{body}",
                "metadata": {
                    "source":  f"github/{owner}/{repo}",
                    "owner":   owner,
                    "repo":    repo,
                    "path":    path,
                    "section": name,
                    "ext":     ext,
                    "type":    "config",
                }
            })

    return chunks

# ─── ChromaDB loader ──────────────────────────────────────────────────────────

def load_to_chroma(chunks: list[dict], collection_name: str = COLLECTION,
                   reset: bool = False) -> int:
    """Upsert chunks into ChromaDB. Returns count of new chunks added."""
    try:
        import chromadb
    except ImportError:
        log.error("chromadb not installed. Run: pip install chromadb --break-system-packages")
        return 0

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection(collection_name)
            log.info(f"[RESET] Deleted collection '{collection_name}'")
        except Exception:
            pass

    col = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "ERR0RS GitHub RAG — auto-ingested repos"}
    )

    ids    = [c["id"]       for c in chunks]
    docs   = [c["document"] for c in chunks]
    metas  = [c["metadata"] for c in chunks]

    # Deduplicate
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
        log.info("  All chunks already in ChromaDB — nothing new to add.")
        return 0

    BATCH = 100
    for start in range(0, len(new_ids), BATCH):
        col.add(
            ids=new_ids[start:start+BATCH],
            documents=new_docs[start:start+BATCH],
            metadatas=new_metas[start:start+BATCH],
        )
        log.info(f"  ✓ Batch {start//BATCH+1}: {min(start+BATCH, len(new_ids))}/{len(new_ids)} chunks")

    return len(new_ids)


# ─── Submodule helper ─────────────────────────────────────────────────────────

def add_submodule(owner: str, repo: str, dest_category: str = "exploitation") -> bool:
    """
    Add repo as a git submodule under knowledge/<category>/<repo>.
    Category is auto-detected from repo topics/description.
    """
    import subprocess
    dest = KNOWLEDGE / dest_category / repo
    if dest.exists():
        log.info(f"  Submodule already exists at {dest}")
        return True
    url = f"https://github.com/{owner}/{repo}.git"
    log.info(f"  Adding submodule: {url} → knowledge/{dest_category}/{repo}")
    result = subprocess.run(
        ["git", "submodule", "add", url, str(dest.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode == 0:
        log.info(f"  ✅ Submodule added")
        return True
    else:
        log.warning(f"  Submodule add failed: {result.stderr.strip()}")
        return False


def _detect_category(description: str, topics: list, language: str) -> str:
    """Guess the best knowledge/ subfolder from repo metadata."""
    combined = (description + " " + " ".join(topics) + " " + (language or "")).lower()
    if any(w in combined for w in ["flipper", "subghz", "rf", "radio", "wireless", "wifi", "bluetooth"]):
        return "wireless"
    if any(w in combined for w in ["recon", "osint", "subdomain", "enum", "discovery", "scan"]):
        return "recon"
    if any(w in combined for w in ["payload", "exploit", "injection", "xss", "sqli", "rce", "lfi", "webshell"]):
        return "exploitation"
    if any(w in combined for w in ["badusb", "rubber ducky", "hid", "keystroke"]):
        return "badusb"
    if any(w in combined for w in ["c2", "command", "control", "rat", "remote access", "cobalt"]):
        return "c2"
    if any(w in combined for w in ["evasion", "bypass", "obfuscat", "av bypass", "amsi", "antivirus"]):
        return "evasion"
    if any(w in combined for w in ["social engineer", "phish", "pretexting", "vishing"]):
        return "social-engineering"
    if any(w in combined for w in ["windows", "active directory", "kerberos", "ldap", "ntlm", "mimikatz"]):
        return "windows"
    if any(w in combined for w in ["mobile", "android", "ios", "apk", "frida"]):
        return "mobile"
    if any(w in combined for w in ["threat intel", "malware", "ioc", "yara", "sigma", "hunt"]):
        return "threat-intelligence"
    if any(w in combined for w in ["credential", "password", "hash", "crack", "brute"]):
        return "enumeration"
    if any(w in combined for w in ["oscp", "ctf", "writeup", "hack the box", "tryhack", "notes", "cheat"]):
        return "advanced_tradecraft"
    return "exploitation"  # default


# ─── Main ingestor function ───────────────────────────────────────────────────

def ingest_github(
    url_or_slug: str,
    collection:   str  = COLLECTION,
    dry_run:      bool = False,
    add_sub:      bool = True,
    token:        str  = None,
    verbose:      bool = True,
) -> dict:
    """
    Full pipeline: parse URL → fetch tree → chunk files → load ChromaDB.
    Returns result dict with stats.

    This is the function called by the ERR0RS command handler.
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    result = {
        "url":        url_or_slug,
        "owner":      None,
        "repo":       None,
        "stars":      0,
        "files_found":0,
        "files_ingested": 0,
        "chunks_total":   0,
        "chunks_new":     0,
        "collection": collection,
        "submodule":  False,
        "error":      None,
    }

    # ── 1. Parse URL ──────────────────────────────────────────────
    try:
        owner, repo = resolve_repo(url_or_slug)
        result["owner"] = owner
        result["repo"]  = repo
    except ValueError as e:
        result["error"] = str(e)
        return result

    log.info(f"\n{'='*58}")
    log.info(f"  ERR0RS RAG INGESTOR — {owner}/{repo}")
    log.info(f"{'='*58}")

    # ── 2. Repo metadata ──────────────────────────────────────────
    meta_url = f"https://api.github.com/repos/{owner}/{repo}"
    meta = _api_get(meta_url, token)
    if not meta:
        result["error"] = f"Cannot reach {owner}/{repo} — check name or network"
        return result

    stars       = meta.get("stargazers_count", 0)
    description = meta.get("description", "") or ""
    language    = meta.get("language", "") or ""
    topics      = meta.get("topics", [])
    branch      = meta.get("default_branch", "main")

    result["stars"] = stars
    log.info(f"  ⭐ {stars:,} stars | {language} | {description[:60]}")
    log.info(f"  Branch: {branch} | Topics: {', '.join(topics[:6]) or 'none'}")

    # ── 3. Walk file tree ─────────────────────────────────────────
    log.info(f"\n  🔍 Walking file tree...")
    files = _walk_tree(owner, repo, sha=branch, token=token)

    # Filter to ingestable extensions
    ingestable = [f for f in files
                  if not f["ext"] or f["ext"] in INGEST_EXTS]
    result["files_found"] = len(files)
    log.info(f"  Found {len(files)} total files, {len(ingestable)} ingestable")

    # ── 4. Fetch + chunk ──────────────────────────────────────────
    all_chunks = []
    ingested   = 0

    for i, file_info in enumerate(ingestable):
        path = file_info["path"]
        if verbose:
            log.info(f"  [{i+1}/{len(ingestable)}] {path}")

        content = fetch_file(owner, repo, path, branch=branch, token=token)
        if not content:
            log.debug(f"    ↳ Could not fetch")
            continue

        chunks = chunk_content(content, path, owner, repo)
        if chunks:
            all_chunks.extend(chunks)
            ingested += 1

        # Be kind to GitHub's servers
        if i % 20 == 0 and i > 0:
            time.sleep(0.5)

    result["files_ingested"] = ingested
    result["chunks_total"]   = len(all_chunks)
    log.info(f"\n  📦 {len(all_chunks)} chunks from {ingested} files")

    if dry_run:
        log.info("  [DRY RUN] — not writing to ChromaDB or adding submodule")
        if all_chunks:
            log.info(f"\n  Sample chunk ({all_chunks[0]['metadata']['path']}):")
            log.info(all_chunks[0]["document"][:300])
        return result

    # ── 5. Load into ChromaDB ─────────────────────────────────────
    if all_chunks:
        log.info(f"\n  💾 Loading into ChromaDB collection '{collection}'...")
        new_count = load_to_chroma(all_chunks, collection_name=collection)
        result["chunks_new"] = new_count
        log.info(f"  ✅ {new_count} new chunks added to '{collection}'")
    else:
        log.warning("  No chunks generated — repo may be empty or binary-only")

    # ── 6. Optional submodule ─────────────────────────────────────
    if add_sub:
        category = _detect_category(description, topics, language)
        result["submodule"] = add_submodule(owner, repo, dest_category=category)

    log.info(f"\n{'='*58}")
    log.info(f"  DONE — {owner}/{repo}")
    log.info(f"  Chunks: {result['chunks_new']} new / {result['chunks_total']} total")
    log.info(f"  Collection: {collection}")
    log.info(f"{'='*58}\n")

    return result


# ─── ERR0RS Command Handler ───────────────────────────────────────────────────

def handle_add_to_rag(command: str, params: dict = None) -> dict:
    """
    Entry point called by ERR0RS module registry.
    Parses: "add to rag <url>" or "add to rag <url> --no-submodule"
    """
    params = params or {}

    # Extract URL from command string
    # Patterns: add to rag "url" | rag add url | ingest url
    url_match = re.search(
        r'(?:add\s+(?:to\s+)?rag|rag\s+add|ingest)\s+"?([^\s"]+)"?',
        command, re.IGNORECASE
    )
    if not url_match:
        # Maybe URL was passed directly in params
        url = params.get("url") or params.get("target", "")
    else:
        url = url_match.group(1).strip()

    if not url:
        return {
            "status": "error",
            "stdout": (
                "Usage: add to rag <github_url>\n"
                "Examples:\n"
                "  add to rag https://github.com/swisskyrepo/PayloadsAllTheThings\n"
                "  add to rag user/repo\n"
                "  add to rag github.com/user/repo"
            )
        }

    dry_run  = params.get("dry_run", False)
    add_sub  = params.get("submodule", True)
    collect  = params.get("collection", COLLECTION)
    token    = params.get("token") or os.environ.get("GITHUB_TOKEN")

    result = ingest_github(
        url_or_slug = url,
        collection  = collect,
        dry_run     = dry_run,
        add_sub     = add_sub,
        token       = token,
        verbose     = True,
    )

    if result["error"]:
        return {"status": "error",   "stdout": f"❌ {result['error']}"}

    stdout = (
        f"\n{'='*54}\n"
        f"  ✅ RAG INGEST COMPLETE\n"
        f"{'='*54}\n"
        f"  Repo       : {result['owner']}/{result['repo']} (⭐{result['stars']:,})\n"
        f"  Files      : {result['files_ingested']} ingested / {result['files_found']} found\n"
        f"  Chunks     : {result['chunks_new']} new / {result['chunks_total']} total\n"
        f"  Collection : {result['collection']}\n"
        f"  Submodule  : {'✅ added' if result['submodule'] else '⚠️  skipped'}\n"
        f"{'='*54}\n"
        f"  ERR0RS now knows: {result['owner']}/{result['repo']}\n"
        f"  Query with: search rag <topic>\n"
    )
    return {"status": "success", "stdout": stdout, "data": result}


# ─── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ERR0RS Universal GitHub RAG Ingestor",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("url",
        help="GitHub URL or owner/repo slug\nExamples:\n"
             "  https://github.com/swisskyrepo/PayloadsAllTheThings\n"
             "  user/repo\n"
             "  github.com/user/repo"
    )
    parser.add_argument("--dry-run",    action="store_true", help="Preview without writing")
    parser.add_argument("--no-submodule", action="store_true", help="Skip adding as git submodule")
    parser.add_argument("--collection", default=COLLECTION, help=f"ChromaDB collection name (default: {COLLECTION})")
    parser.add_argument("--token",      default=None,       help="GitHub API token (or set GITHUB_TOKEN env)")
    parser.add_argument("--reset",      action="store_true", help="Delete collection and re-ingest")
    args = parser.parse_args()

    result = ingest_github(
        url_or_slug = args.url,
        collection  = args.collection,
        dry_run     = args.dry_run,
        add_sub     = not args.no_submodule,
        token       = args.token or os.environ.get("GITHUB_TOKEN"),
        verbose     = True,
    )

    if result["error"]:
        print(f"\n❌ Error: {result['error']}\n")
        sys.exit(1)

    print(f"\n✅ Done!")
    print(f"   Repo      : {result['owner']}/{result['repo']}")
    print(f"   Chunks    : {result['chunks_new']} new / {result['chunks_total']} total")
    print(f"   Collection: {result['collection']}")
    if result["submodule"]:
        print(f"   Submodule : added to knowledge/")


if __name__ == "__main__":
    main()
