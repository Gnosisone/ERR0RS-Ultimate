#!/usr/bin/env python3
"""
ERR0RS — RAG Ingestion (Phase 5a)
═════════════════════════════════
Loads the 67 (or more) Sonnet-generated teach cards from
src/tools/tool_registry.generated.json into a ChromaDB collection so the
runtime conversation engine can retrieve them as few-shot examples.

Why RAG over fine-tuning:
  - 67 examples is too few to fine-tune effectively (LIMA paper needed 1000+
    for noticeable Llama improvement). RAG works with any corpus size.
  - Adding new gold-standard teach cards = re-ingest, no retraining.
  - Qwen-7B at runtime gets to *imitate* Sonnet's style by example, plays
    to its strength (pattern matching) instead of its weakness (factual
    recall on the long tail of MITRE/CVE numbers).
  - Works offline at runtime — RAG database lives in errors_knowledge_db/

Usage:
  python3 tools/ingest_teach_to_rag.py            # ingest from generated.json
  python3 tools/ingest_teach_to_rag.py --query "mimikatz"  # sanity test
  python3 tools/ingest_teach_to_rag.py --stats    # show collection size

The collection name is "err0rs_teach_v1". Runtime code in
src/core/conversation_engine.py will query this collection when building
prompts for the local LLM (qwen / err0rs-qwen / DeepSeek fallback path).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "src" / "tools" / "tool_registry.generated.json"
DB_PATH = ROOT / "errors_knowledge_db"
COLLECTION = "err0rs_teach_v1"


def _get_client():
    """Lazy-import ChromaDB to avoid loading it unless needed."""
    try:
        import chromadb
    except ImportError:
        print("  ✗ chromadb not installed. Install with:", file=sys.stderr)
        print("       pip install chromadb --break-system-packages", file=sys.stderr)
        sys.exit(1)
    DB_PATH.mkdir(exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_PATH))


def _format_teach_card(tool_key: str, teach: dict, source_tool: dict | None = None) -> str:
    """Render a teach card to a single text document for embedding.

    The shape mirrors the prompt template the runtime will use, so
    retrieval-by-similarity returns semantically appropriate examples.
    """
    lines = []
    if source_tool:
        lines.append(f"# {source_tool.get('display_name', tool_key)}")
        lines.append(f"Category: {source_tool.get('category', 'utility')}")
        lines.append(f"Description: {source_tool.get('description', '')}")
        lines.append(f"Teach intro: {source_tool.get('teach_intro', '')}")
        lines.append("")

    if teach.get("opsec_notes"):
        lines.append("## OpSec Notes")
        for note in teach["opsec_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    if teach.get("sample_outputs"):
        lines.append("## Sample Outputs")
        for sample in teach["sample_outputs"]:
            lines.append(f"Scenario: {sample.get('scenario', '')}")
            lines.append(f"Command: {sample.get('command', '')}")
            lines.append(f"Output: {sample.get('output', '')}")
            lines.append(f"Explanation: {sample.get('explanation', '')}")
            lines.append("")

    if teach.get("legal_notes"):
        lines.append("## Legal Notes")
        for note in teach["legal_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    if teach.get("false_positives"):
        lines.append("## False Positives")
        for fp in teach["false_positives"]:
            lines.append(f"- {fp}")
        lines.append("")

    if teach.get("mitre_attack"):
        lines.append("## MITRE ATT&CK Mappings")
        for m in teach["mitre_attack"]:
            lines.append(f"- {m.get('id', '')}: {m.get('name', '')}")
        lines.append("")

    return "\n".join(lines).strip()


def ingest():
    if not GENERATED.exists():
        print(f"  ✗ {GENERATED} not found. Run generate_teach.py first.")
        sys.exit(1)

    gen = json.load(open(GENERATED))
    tools_gen = gen.get("tools", {})
    if not tools_gen:
        print("  ✗ Empty generated file — nothing to ingest")
        sys.exit(1)

    # Pull source v3 metadata so the document includes category/teach_intro
    v3 = json.load(open(ROOT / "src" / "tools" / "tool_registry.v3.json"))
    tools_v3 = v3.get("tools", {})

    client = _get_client()

    # Drop existing collection and rebuild — keeps things idempotent
    try:
        client.delete_collection(COLLECTION)
        print(f"  ⟳ Dropped existing collection: {COLLECTION}")
    except Exception:
        pass

    coll = client.create_collection(
        name=COLLECTION,
        metadata={
            "description": "ERR0RS gold-standard teach cards (Sonnet 4.6 generated)",
            "source": "tool_registry.generated.json",
            "schema_version": "3.0.0",
        },
    )
    print(f"  ✓ Created collection: {COLLECTION}")

    docs, ids, metadatas = [], [], []
    for tool_key, teach in tools_gen.items():
        source = tools_v3.get(tool_key, {})
        doc = _format_teach_card(tool_key, teach, source)
        if not doc:
            continue
        docs.append(doc)
        ids.append(tool_key)
        metadatas.append({
            "tool_key": tool_key,
            "category": source.get("category", "utility"),
            "tier": source.get("tier", 1),
            "n_opsec": len(teach.get("opsec_notes", [])),
            "n_samples": len(teach.get("sample_outputs", [])),
            "n_mitre": len(teach.get("mitre_attack", [])),
        })

    print(f"  ⟳ Embedding {len(docs)} teach cards (this takes ~30-60s on Pi 5)...")
    # ChromaDB uses its default embedder (all-MiniLM-L6-v2, sentence-transformers)
    coll.add(documents=docs, ids=ids, metadatas=metadatas)
    print(f"  ✓ Ingested {len(docs)} teach cards into '{COLLECTION}'")
    print()
    print(f"  Collection stats:")
    print(f"    Path:        {DB_PATH}")
    print(f"    Documents:   {coll.count()}")
    print(f"    Avg doc len: {sum(len(d) for d in docs) // len(docs)} chars")


def query(text: str, n: int = 3):
    client = _get_client()
    try:
        coll = client.get_collection(COLLECTION)
    except Exception as e:
        print(f"  ✗ Collection '{COLLECTION}' not found. Run --ingest first.")
        print(f"    error: {e}")
        sys.exit(1)
    results = coll.query(query_texts=[text], n_results=n)
    print(f"  Top {n} matches for: {text!r}")
    print()
    for i, (doc_id, distance, doc) in enumerate(zip(
            results["ids"][0],
            results["distances"][0],
            results["documents"][0]), 1):
        preview = doc.replace("\n", " ")[:200]
        print(f"  #{i}  {doc_id}  (distance={distance:.3f})")
        print(f"       {preview}...")
        print()


def stats():
    client = _get_client()
    try:
        coll = client.get_collection(COLLECTION)
    except Exception:
        print(f"  ✗ Collection '{COLLECTION}' not yet built. Run without flags to ingest.")
        sys.exit(1)
    print(f"  Collection:  {COLLECTION}")
    print(f"  Path:        {DB_PATH}")
    print(f"  Documents:   {coll.count()}")
    sample = coll.peek(limit=3)
    if sample.get("ids"):
        print(f"  Sample ids:  {sample['ids']}")


def main():
    parser = argparse.ArgumentParser(description="Ingest teach cards into ChromaDB for RAG")
    parser.add_argument("--query", metavar="TEXT", help="Test the collection with a query")
    parser.add_argument("--stats", action="store_true", help="Show collection size")
    parser.add_argument("-n", type=int, default=3, help="Top N results for --query")
    args = parser.parse_args()

    print("=" * 70)
    print(" ERR0RS RAG Ingestion — Phase 5a")
    print("=" * 70)
    print()

    if args.stats:
        stats()
    elif args.query:
        query(args.query, n=args.n)
    else:
        ingest()


if __name__ == "__main__":
    main()
