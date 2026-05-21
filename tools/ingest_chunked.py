#!/usr/bin/env python3
"""
ERR0RS — Chunked Teach Ingestion (v3.7 Phase 2)
═══════════════════════════════════════════════════════════════════

Splits each teach card into retrieval-sized chunks and embeds them into a
new ChromaDB collection alongside the existing whole-card collection.

WHY THIS EXISTS:
  The original RAG approach embeds each teach card whole (~12k chars each).
  When retrieved and stuffed into gemma3:1b's prompt on a Pi 5, it takes
  145+ seconds to even start generating (validated 2026-05-20). Below the
  4K-char threshold, TTFT drops to ~34s — interactive territory. Chunking
  is the only way to hit interactive latency on the hardware we target.

CHUNKING STRATEGY (Approach C — section-level with sub-splits):
  Per tool, we generate:

    1. ONE intro chunk per tool:
         display_name + description + category + tier + risk
         + MITRE technique list (the tiny mitre_attack section folds in here)
       Always retrieved alongside the content match so the model knows
       "what is this tool" even if the matched chunk is deep in a section.

    2. PER-SECTION chunks for the four narrative sections:
         opsec_notes, sample_outputs, legal_notes, false_positives

       If a section's rendered text ≤ 2500 chars: one chunk for the whole section.
       If > 2500 chars: split on natural break points (one item per chunk if
       it's a list-of-strings; preserve dict-shaped sample_outputs as whole
       items) and group items until we approach 2000 chars. This keeps chunks
       semantically coherent — each chunk is one or more complete thoughts,
       never half a sentence.

  Each chunk gets stable, deterministic ID:    {tool}__{section}__{sub_idx}
  Each chunk carries metadata:                 {tool, section, sub_idx, category, tier}
  Each chunk's text starts with a header:      "## {display_name} — {section}\n"
                                                so retrieval results are
                                                self-identifying when stuffed
                                                back into a prompt.

OUTPUT:
  - New collection: err0rs_teach_v1_chunked
  - The existing err0rs_teach_v1 (whole-card) collection is untouched —
    backward compatible. Old call sites keep working until they're migrated.

USAGE:
  python3 tools/ingest_chunked.py                 # full ingest, all 67 tools
  python3 tools/ingest_chunked.py --only rubeus crackmapexec   # subset
  python3 tools/ingest_chunked.py --query "kerberoasting"      # test retrieval
  python3 tools/ingest_chunked.py --stats                      # show collection stats
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "src" / "tools" / "tool_registry.v3.json"
DB_PATH  = ROOT / "errors_knowledge_db"

COLLECTION_NAME = "err0rs_teach_v1_chunked"

# Target chunk size — empirically chosen so a top-2 retrieval (intro + content)
# stays under ~4500 chars total, well within gemma3:1b's interactive prompt
# budget on Pi 5.
TARGET_CHUNK_CHARS = 2000
HARD_CHUNK_CEILING = 2500

# Sections we chunk. mitre_attack is intentionally NOT here — those items
# are too small individually (~30-50 chars each) to be useful retrievals;
# they fold into the intro chunk instead.
CHUNKED_SECTIONS = ("opsec_notes", "sample_outputs", "legal_notes", "false_positives")


# ── Chunking helpers ─────────────────────────────────────────────────────

def render_mitre(mitre: list) -> str:
    """Render the mitre_attack list as compact text for the intro chunk."""
    if not mitre:
        return ""
    parts = []
    for m in mitre:
        if isinstance(m, dict):
            mid = m.get("id", "")
            name = m.get("name", "")
            if mid and name:
                parts.append(f"  - {mid}: {name}")
    return "MITRE ATT&CK techniques:\n" + "\n".join(parts) if parts else ""


def build_intro_chunk(tool_key: str, card: dict) -> dict:
    """The intro chunk — always retrieved as context companion. Carries
    the 'what is this tool' info so the model isn't operating in the dark
    when the content match is deep in a specific section."""
    display = card.get("display_name", tool_key)
    desc = (card.get("description") or "").strip()
    category = card.get("category", "")
    tier = card.get("tier", "")
    risk = card.get("risk", "")

    header = f"## {display}\n"
    body_parts = []

    meta_line = []
    if category: meta_line.append(f"category={category}")
    if tier: meta_line.append(f"tier={tier}")
    if risk: meta_line.append(f"risk={risk}")
    if meta_line:
        body_parts.append(" · ".join(meta_line))

    if desc:
        # Cap description at 800 chars — anything longer means the tool author
        # was writing a teach card in the description; the body sections cover that.
        if len(desc) > 800:
            desc = desc[:797] + "..."
        body_parts.append(desc)

    mitre_text = render_mitre(card.get("mitre_attack", []))
    if mitre_text:
        body_parts.append(mitre_text)

    text = header + "\n".join(body_parts)
    return {
        "id":   f"{tool_key}__intro",
        "text": text,
        "metadata": {
            "tool": tool_key,
            "section": "intro",
            "sub_idx": 0,
            "category": str(category),
            "tier": str(tier),
        },
    }


def render_section_items(section: str, items: list) -> list[str]:
    """Render a section's items as a list of self-contained text fragments.

    For list-of-strings (opsec_notes, legal_notes, false_positives) each
    string IS one item — return as-is.

    For sample_outputs (list-of-dicts with scenario/command/output/explanation),
    each dict becomes one rich fragment with markdown structure preserved."""
    rendered = []
    for it in items:
        if isinstance(it, str):
            rendered.append(it.strip())
        elif isinstance(it, dict):
            # sample_outputs shape: {scenario, command, output, explanation}
            parts = []
            if it.get("scenario"):
                parts.append(f"**Scenario:** {it['scenario']}")
            if it.get("command"):
                parts.append(f"```\n{it['command']}\n```")
            if it.get("output"):
                parts.append(f"**Output:**\n```\n{it['output']}\n```")
            if it.get("explanation"):
                parts.append(f"**Explanation:** {it['explanation']}")
            if parts:
                rendered.append("\n\n".join(parts))
    return rendered


def chunk_section(tool_key: str, display: str, section: str,
                  items: list) -> Iterator[dict]:
    """Yield one or more chunk dicts for this section.

    Algorithm:
      1. Render items into self-contained fragments (one per item)
      2. If everything fits in one chunk (≤ HARD_CHUNK_CEILING), emit one chunk
      3. Otherwise, group fragments greedily — start a new chunk when adding
         the next fragment would exceed TARGET_CHUNK_CHARS

    Why greedy grouping (not fixed splits):
      Fixed splits cut mid-sentence; greedy grouping preserves the integrity
      of each opsec note / sample / legal point. Worst case: one chunk per
      item if an item is itself > TARGET. Acceptable.
    """
    fragments = render_section_items(section, items)
    if not fragments:
        return

    header = f"## {display} — {section.replace('_', ' ')}\n\n"
    joined_full = header + "\n\n---\n\n".join(fragments)

    # Fast path: whole section fits in one chunk
    if len(joined_full) <= HARD_CHUNK_CEILING:
        yield {
            "id":   f"{tool_key}__{section}__0",
            "text": joined_full,
            "metadata": {
                "tool": tool_key, "section": section, "sub_idx": 0,
            },
        }
        return

    # Slow path: greedy group fragments into sub-chunks
    sub_idx = 0
    current_buf: list[str] = []
    current_len = len(header)  # header counts against budget

    def flush():
        nonlocal sub_idx, current_buf, current_len
        if not current_buf:
            return None
        body = "\n\n---\n\n".join(current_buf)
        text = header + body
        chunk = {
            "id":   f"{tool_key}__{section}__{sub_idx}",
            "text": text,
            "metadata": {
                "tool": tool_key, "section": section, "sub_idx": sub_idx,
            },
        }
        sub_idx += 1
        current_buf = []
        current_len = len(header)
        return chunk

    for frag in fragments:
        frag_with_sep = ("\n\n---\n\n" if current_buf else "") + frag
        # If adding this fragment overflows AND we already have content,
        # flush the current chunk and start a new one with this fragment.
        if current_len + len(frag_with_sep) > TARGET_CHUNK_CHARS and current_buf:
            yielded = flush()
            if yielded:
                yield yielded
            # Now start fresh with this fragment
            current_buf = [frag]
            current_len = len(header) + len(frag)
        else:
            current_buf.append(frag)
            current_len += len(frag_with_sep)

    # Tail
    yielded = flush()
    if yielded:
        yield yielded


def chunks_for_tool(tool_key: str, card: dict) -> list[dict]:
    """Return all chunks for one teach card: 1 intro + N section chunks."""
    chunks = [build_intro_chunk(tool_key, card)]
    display = card.get("display_name", tool_key)
    for section in CHUNKED_SECTIONS:
        items = card.get(section) or []
        if not items:
            continue
        for ch in chunk_section(tool_key, display, section, items):
            chunks.append(ch)
    return chunks


# ── Ingest / Query / Stats ───────────────────────────────────────────────

def get_collection(create: bool = False):
    import chromadb
    client = chromadb.PersistentClient(path=str(DB_PATH))
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        return client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "ERR0RS teach cards chunked for fast RAG retrieval"},
        )
    return client.get_collection(COLLECTION_NAME)


def load_taught_tools(only: list[str] | None = None) -> dict[str, dict]:
    """Load tools that have any teach content. Filter to --only if given."""
    v3 = json.loads(REGISTRY.read_text())
    out = {}
    for k, t in v3.get("tools", {}).items():
        if only and k not in only:
            continue
        if any(t.get(s) for s in CHUNKED_SECTIONS):
            out[k] = t
    return out


def cmd_ingest(args):
    tools = load_taught_tools(args.only)
    if not tools:
        print("  ! no taught tools matched the filter")
        return 1

    print(f"=== Chunked teach ingestion ===")
    print(f"  source:     {REGISTRY.relative_to(ROOT)}")
    print(f"  collection: {COLLECTION_NAME}")
    print(f"  tools:      {len(tools)} ({'filtered' if args.only else 'all taught'})")

    # Build all chunks first (cheap, no embedding yet)
    all_chunks: list[dict] = []
    size_buckets = {"<500": 0, "500-1500": 0, "1500-2500": 0, ">2500": 0}
    for tool_key, card in tools.items():
        chunks = chunks_for_tool(tool_key, card)
        all_chunks.extend(chunks)
        for ch in chunks:
            n = len(ch["text"])
            if n < 500: size_buckets["<500"] += 1
            elif n < 1500: size_buckets["500-1500"] += 1
            elif n < 2500: size_buckets["1500-2500"] += 1
            else: size_buckets[">2500"] += 1

    print(f"\n  chunks built:      {len(all_chunks)}")
    print(f"  avg chunks/tool:   {len(all_chunks)/len(tools):.1f}")
    print(f"  size distribution: {size_buckets}")

    if args.dry_run:
        print(f"\n  DRY RUN — no embedding performed. Sample chunks:")
        for ch in all_chunks[:3]:
            print(f"\n  --- {ch['id']} ({len(ch['text'])} chars) ---")
            print("  " + ch["text"][:300].replace("\n", "\n  "))
            if len(ch["text"]) > 300:
                print("  ...")
        return 0

    # Embed + persist
    print(f"\n  embedding {len(all_chunks)} chunks (CPU, all-MiniLM-L6-v2)...")
    collection = get_collection(create=True)
    collection.add(
        ids=[c["id"] for c in all_chunks],
        documents=[c["text"] for c in all_chunks],
        metadatas=[c["metadata"] for c in all_chunks],
    )
    print(f"  ✓ ingested {collection.count()} chunks into '{COLLECTION_NAME}'")
    print(f"  ✓ persisted to {DB_PATH.relative_to(ROOT)}")
    return 0


def cmd_query(args):
    collection = get_collection(create=False)
    print(f"=== Query: {args.query!r} (n={args.n_results}) ===\n")
    res = collection.query(query_texts=[args.query], n_results=args.n_results)
    docs = res["documents"][0] if res.get("documents") else []
    metas = res["metadatas"][0] if res.get("metadatas") else []
    dists = res["distances"][0] if res.get("distances") else []
    if not docs:
        print("  (no results)")
        return 1
    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists), 1):
        tool = meta.get("tool", "?")
        section = meta.get("section", "?")
        sub = meta.get("sub_idx", 0)
        print(f"  #{i}  distance={dist:.4f}  {tool}__{section}__{sub}  ({len(doc)} chars)")
        # Print first 200 chars of doc for sanity check
        preview = doc[:200].replace("\n", " ")
        print(f"      preview: {preview}{'...' if len(doc) > 200 else ''}")
        print()
    return 0


def cmd_stats(args):
    try:
        collection = get_collection(create=False)
    except Exception as e:
        print(f"  ! collection not found: {e}")
        return 1
    count = collection.count()
    print(f"=== Collection stats: {COLLECTION_NAME} ===")
    print(f"  total chunks: {count}")
    if count == 0:
        return 0
    # Sample some chunks to compute size + section distribution
    sample = collection.get(limit=min(count, 1000), include=["documents", "metadatas"])
    sizes = [len(d) for d in sample["documents"]]
    sections: dict[str, int] = {}
    tools: set[str] = set()
    for m in sample["metadatas"]:
        sec = m.get("section", "?")
        sections[sec] = sections.get(sec, 0) + 1
        tools.add(m.get("tool", "?"))
    sizes.sort()
    print(f"  unique tools:    {len(tools)}")
    print(f"  chunks/tool avg: {count/len(tools):.1f}")
    print(f"  size median:     {sizes[len(sizes)//2]} chars")
    print(f"  size min/max:    {sizes[0]} / {sizes[-1]} chars")
    print(f"  sections:        {sections}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", nargs="*", help="Only ingest these tool keys")
    p.add_argument("--dry-run", action="store_true", help="Build chunks but don't embed")
    p.add_argument("--query", help="Test retrieval with this query (skips ingest)")
    p.add_argument("--n-results", type=int, default=3, help="For --query: how many results")
    p.add_argument("--stats", action="store_true", help="Show collection stats (skips ingest)")
    args = p.parse_args()

    if args.stats:
        return cmd_stats(args)
    if args.query:
        return cmd_query(args)
    return cmd_ingest(args)


if __name__ == "__main__":
    sys.exit(main())
