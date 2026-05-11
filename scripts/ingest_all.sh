#!/usr/bin/env bash
# ERR0RS — Master Ingestion Script
# Runs all ingesters in the correct order
# Usage: bash scripts/ingest_all.sh
#        bash scripts/ingest_all.sh --dry-run

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY="${1:-}"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ERR0RS — Master Knowledge Base Ingester             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd "$REPO"
source venv/bin/activate 2>/dev/null || true

run() {
    echo "┌─ $1"
    python3 "$2" $DRY
    echo "└─ Done"
    echo ""
}

# 1. PayloadsAllTheThings (web app attacks)
run "PayloadsAllTheThings → payloads_all_things" \
    "scripts/ingest_payloads_all_things.py"

# 2. lanjelot personal KB (operator notes)
run "lanjelot/kb → lanjelot_kb" \
    "scripts/ingest_lanjelot_kb.py"

# 3. BadUSB payload libraries
run "BadUSB Payloads → badusb_payloads" \
    "scripts/ingest_badusb_payloads.py"

# 4. All remaining submodules (batch)
run "All knowledge/ submodules → kb_submodules" \
    "scripts/ingest_all_submodules.py"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  INGESTION COMPLETE — ChromaDB Summary               ║"
echo "╚══════════════════════════════════════════════════════╝"
python3 - << 'PYEOF'
import chromadb
from pathlib import Path
client = chromadb.PersistentClient(path=str(Path("errors_knowledge_db")))
cols   = client.list_collections()
total  = 0
for c in cols:
    col = client.get_collection(c.name)
    n   = col.count()
    total += n
    print(f"  {c.name:<30} {n:>6} chunks")
print(f"  {'─'*38}")
print(f"  TOTAL{'':<25} {total:>6} chunks")
PYEOF
echo ""
