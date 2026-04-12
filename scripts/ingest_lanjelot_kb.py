#!/usr/bin/env python3
"""
lanjelot/kb → ChromaDB RAG Ingester
Ingests flat text operator notes from lanjelot's personal infosec KB.
Each file is one topic — chunked by blank-line-separated paragraphs.

Usage:
    python3 scripts/ingest_lanjelot_kb.py
    python3 scripts/ingest_lanjelot_kb.py --dry-run
    python3 scripts/ingest_lanjelot_kb.py --reset

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""

import os, sys, re, hashlib, argparse, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT   = Path(__file__).resolve().parent.parent
KB_ROOT     = REPO_ROOT / "knowledge" / "advanced_tradecraft" / "lanjelot-kb"
CHROMA_PATH = REPO_ROOT / "errors_knowledge_db"
COLLECTION  = "lanjelot_kb"

# Skip non-note files
SKIP_FILES = {".git", "README", "LICENSE", ".gitignore", ".DS_Store"}

# Map filenames → MITRE tags + attack categories
FILE_META = {
    "sqli":           {"mitre": "T1190", "attack_type": "injection",       "category": "Web App"},
    "xss":            {"mitre": "T1059.007", "attack_type": "xss",          "category": "Web App"},
    "ssrf":           {"mitre": "T1090", "attack_type": "ssrf",             "category": "Web App"},
    "ssti":           {"mitre": "T1190", "attack_type": "injection",        "category": "Web App"},
    "xxe":            {"mitre": "T1190", "attack_type": "injection",        "category": "Web App"},
    "lfi":            {"mitre": "T1190", "attack_type": "path_traversal",   "category": "Web App"},
    "csrf":           {"mitre": "T1185", "attack_type": "client_side",      "category": "Web App"},
    "graphql":        {"mitre": "T1190", "attack_type": "injection",        "category": "Web App"},
    "jwt":            {"mitre": "T1552", "attack_type": "auth_bypass",      "category": "Web App"},
    "oauth":          {"mitre": "T1550", "attack_type": "auth_bypass",      "category": "Web App"},
    "saml":           {"mitre": "T1550", "attack_type": "auth_bypass",      "category": "Web App"},
    "waf":            {"mitre": "T1562", "attack_type": "evasion",          "category": "Evasion"},
    "evasion":        {"mitre": "T1562", "attack_type": "evasion",          "category": "Evasion"},
    "bypass_av":      {"mitre": "T1027", "attack_type": "evasion",          "category": "Evasion"},
    "privesc":        {"mitre": "T1068", "attack_type": "privesc",          "category": "Privilege Escalation"},
    "sudo":           {"mitre": "T1548", "attack_type": "privesc",          "category": "Privilege Escalation"},
    "mimikatz":       {"mitre": "T1003", "attack_type": "credential_dump",  "category": "Credentials"},
    "pass-the-hash":  {"mitre": "T1550.002", "attack_type": "lateral",      "category": "Lateral Movement"},
    "dpapi":          {"mitre": "T1555", "attack_type": "credential_dump",  "category": "Credentials"},
    "password":       {"mitre": "T1110", "attack_type": "brute_force",      "category": "Credentials"},
    "john":           {"mitre": "T1110", "attack_type": "brute_force",      "category": "Credentials"},
    "rainbow_tables": {"mitre": "T1110", "attack_type": "brute_force",      "category": "Credentials"},
    "keepass":        {"mitre": "T1555", "attack_type": "credential_dump",  "category": "Credentials"},
    "reverse-shells": {"mitre": "T1059", "attack_type": "rce",              "category": "Exploitation"},
    "exploitation":   {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "exploits":       {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "webshells":      {"mitre": "T1505.003", "attack_type": "persistence",  "category": "Persistence"},
    "backdoors":      {"mitre": "T1505", "attack_type": "persistence",      "category": "Persistence"},
    "nmap":           {"mitre": "T1046", "attack_type": "enumeration",      "category": "Recon"},
    "recon":          {"mitre": "T1592", "attack_type": "enumeration",      "category": "Recon"},
    "dns":            {"mitre": "T1018", "attack_type": "enumeration",      "category": "Recon"},
    "googlehacking":  {"mitre": "T1593", "attack_type": "osint",            "category": "Recon"},
    "ldap":           {"mitre": "T1087", "attack_type": "enumeration",      "category": "Recon"},
    "snmp":           {"mitre": "T1040", "attack_type": "enumeration",      "category": "Recon"},
    "smbrelay":       {"mitre": "T1557", "attack_type": "mitm",             "category": "Lateral Movement"},
    "mitm":           {"mitre": "T1557", "attack_type": "mitm",             "category": "Lateral Movement"},
    "ssh":            {"mitre": "T1021.004", "attack_type": "lateral",      "category": "Lateral Movement"},
    "metasploit":     {"mitre": "T1190", "attack_type": "exploitation",     "category": "Exploitation"},
    "mssql":          {"mitre": "T1190", "attack_type": "injection",        "category": "Exploitation"},
    "mysql":          {"mitre": "T1190", "attack_type": "injection",        "category": "Exploitation"},
    "oracle":         {"mitre": "T1190", "attack_type": "injection",        "category": "Exploitation"},
    "postgres":       {"mitre": "T1190", "attack_type": "injection",        "category": "Exploitation"},
    "redis":          {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "jenkins":        {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "jboss":          {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "tomcat":         {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "weblogic":       {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "struts":         {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "spring":         {"mitre": "T1190", "attack_type": "rce",              "category": "Exploitation"},
    "wordpress":      {"mitre": "T1190", "attack_type": "rce",              "category": "Web App"},
    "drupal":         {"mitre": "T1190", "attack_type": "rce",              "category": "Web App"},
    "phishing":       {"mitre": "T1566", "attack_type": "social_eng",       "category": "Social Engineering"},
    "keylogger":      {"mitre": "T1056", "attack_type": "collection",       "category": "Collection"},
    "forensic":       {"mitre": "T1005", "attack_type": "dfir",             "category": "DFIR"},
    "malware":        {"mitre": "T1204", "attack_type": "malware",          "category": "Malware"},
    "crypto":         {"mitre": "T1552", "attack_type": "crypto",           "category": "Crypto"},
    "wifi":           {"mitre": "T1040", "attack_type": "wireless",         "category": "Wireless"},
    "scada":          {"mitre": "T0800", "attack_type": "ics",              "category": "ICS/SCADA"},
    "linux":          {"mitre": "T1059.004", "attack_type": "enumeration",  "category": "Linux"},
    "windows":        {"mitre": "T1059.001", "attack_type": "enumeration",  "category": "Windows"},
    "powershell":     {"mitre": "T1059.001", "attack_type": "execution",    "category": "Windows"},
    "python":         {"mitre": "T1059.006", "attack_type": "scripting",    "category": "Scripting"},
    "php":            {"mitre": "T1059", "attack_type": "webdev",           "category": "Web App"},
    "cloud":          {"mitre": "T1078.004", "attack_type": "cloud",        "category": "Cloud"},
    "containers":     {"mitre": "T1610", "attack_type": "container",        "category": "Cloud"},
    "methodo-webapp": {"mitre": "T1190", "attack_type": "methodology",      "category": "Methodology"},
    "pentest":        {"mitre": "T1595", "attack_type": "methodology",      "category": "Methodology"},
    "fuzz":           {"mitre": "T1190", "attack_type": "fuzzing",          "category": "Web App"},
    "burp":           {"mitre": "T1190", "attack_type": "proxy",            "category": "Tools"},
    "sqlmap":         {"mitre": "T1190", "attack_type": "injection",        "category": "Tools"},
    "medusa":         {"mitre": "T1110", "attack_type": "brute_force",      "category": "Tools"},
}

DEFAULT_META = {"mitre": "T1595", "attack_type": "general", "category": "General"}

def chunk_kb_file(filepath: Path) -> list[dict]:
    """
    Chunk a flat lanjelot KB file into RAG documents.
    Strategy: split on double newlines (paragraphs) + ## headings.
    Each chunk gets the filename as topic + paragraph number.
    """
    topic = filepath.name
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace").strip()
    except Exception as e:
        log.warning(f"Cannot read {filepath}: {e}")
        return []

    if len(text) < 20:
        return []

    meta = FILE_META.get(topic, DEFAULT_META)

    # Split on double newlines — paragraph-level chunks
    raw_paragraphs = re.split(r"\n{2,}", text)

    chunks = []
    buffer = []
    CHUNK_SIZE = 8   # paragraphs per chunk (keeps context local)

    for i, para in enumerate(raw_paragraphs):
        para = para.strip()
        if not para:
            continue
        buffer.append(para)

        # Flush at CHUNK_SIZE or on ## section headers (new topic)
        if len(buffer) >= CHUNK_SIZE or (para.startswith("##") and len(buffer) > 1):
            content = "\n\n".join(buffer)
            uid = hashlib.sha256(f"{topic}::{i}::{content[:60]}".encode()).hexdigest()[:16]
            chunks.append({
                "id": uid,
                "document": f"[lanjelot/kb: {topic}]\n\n{content}",
                "metadata": {
                    "source":      "lanjelot-kb",
                    "topic":       topic,
                    "mitre":       meta["mitre"],
                    "attack_type": meta["attack_type"],
                    "category":    meta["category"],
                    "chunk":       len(chunks),
                }
            })
            buffer = []

    # Flush remaining
    if buffer:
        content = "\n\n".join(buffer)
        if len(content) > 30:
            uid = hashlib.sha256(f"{topic}::final::{content[:60]}".encode()).hexdigest()[:16]
            chunks.append({
                "id": uid,
                "document": f"[lanjelot/kb: {topic}]\n\n{content}",
                "metadata": {
                    "source":      "lanjelot-kb",
                    "topic":       topic,
                    "mitre":       meta["mitre"],
                    "attack_type": meta["attack_type"],
                    "category":    meta["category"],
                    "chunk":       len(chunks),
                }
            })

    return chunks


def collect_all_chunks() -> list[dict]:
    all_chunks = []
    files = sorted([f for f in KB_ROOT.iterdir()
                    if f.is_file() and f.name not in SKIP_FILES
                    and not f.name.startswith(".")])

    for filepath in files:
        chunks = chunk_kb_file(filepath)
        if chunks:
            all_chunks.extend(chunks)
            log.info(f"  ✓ {filepath.name:<35}  {len(chunks):>3} chunks")
        else:
            log.debug(f"  - {filepath.name} (skipped — too short)")

    return all_chunks


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
        metadata={"description": "lanjelot personal infosec KB — years of real-world pentest notes"}
    )

    BATCH = 100
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
            new_ids.append(did); new_docs.append(docs[i]); new_metas.append(metas[i])

    if not new_ids:
        log.info("All chunks already in ChromaDB — nothing to add.")
        return

    for start in range(0, len(new_ids), BATCH):
        col.add(
            ids=new_ids[start:start+BATCH],
            documents=new_docs[start:start+BATCH],
            metadatas=new_metas[start:start+BATCH],
        )
        log.info(f"  Upserted batch {start//BATCH+1} ({min(start+BATCH, len(new_ids))}/{len(new_ids)})")

    log.info(f"\n✅ Done — {len(new_ids)} new chunks in collection '{COLLECTION}'")


def main():
    parser = argparse.ArgumentParser(description="Ingest lanjelot/kb into ERR0RS ChromaDB")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset",   action="store_true")
    args = parser.parse_args()

    if not KB_ROOT.exists():
        log.error(f"lanjelot-kb not found at {KB_ROOT}")
        log.error("Run: git submodule update --init knowledge/advanced_tradecraft/lanjelot-kb")
        sys.exit(1)

    log.info(f"🔍 Scanning {KB_ROOT} ...")
    chunks = collect_all_chunks()
    log.info(f"\n📦 Total chunks: {len(chunks)} from {len(set(c['metadata']['topic'] for c in chunks))} topics")

    if args.dry_run:
        log.info("[DRY RUN] — not writing to ChromaDB")
        for c in chunks[:3]:
            print(f"\n--- {c['metadata']['topic']} ---")
            print(c["document"][:300])
        return

    log.info(f"\n💾 Loading into ChromaDB at {CHROMA_PATH} ...")
    load_to_chroma(chunks, reset=args.reset)


if __name__ == "__main__":
    main()
