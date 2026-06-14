#!/usr/bin/env python3
"""Ingest MITRE ATT&CK (enterprise) techniques as TEXT into err0rs_refs.
Parses the STIX bundle -> one text doc per live technique (id, name, tactics,
cleaned description). ATT&CK is free to use with attribution (tagged in metadata).
Re-runnable: purges prior attack:: chunks first."""
import json, re, sys, argparse
from pathlib import Path
ROOT = Path("/home/kali/ERR0RS-clean")

def _clean(d): return re.sub(r"\(Citation:[^)]*\)", "", d or "").strip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stix", default="/home/kali/err0rs_refs_src/enterprise-attack.json")
    ap.add_argument("--db", default=str(ROOT / "errors_knowledge_db"))
    ap.add_argument("--collection", default="err0rs_refs")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    b = json.load(open(a.stix))
    ids, docs, metas = [], [], []
    for o in b.get("objects", []):
        if o.get("type") != "attack-pattern" or o.get("revoked") or o.get("x_mitre_deprecated"):
            continue
        tid = next((r.get("external_id") for r in o.get("external_references", [])
                    if r.get("source_name") == "mitre-attack"), None)
        if not tid:
            continue
        name = o.get("name", "")
        tactics = ", ".join(p.get("phase_name", "") for p in o.get("kill_chain_phases", [])
                            if p.get("kill_chain_name") == "mitre-attack")
        desc = _clean(o.get("description", ""))
        head = f"## ATT&CK {tid}: {name}\nTactics: {tactics}\n"
        full = head + "\n" + desc
        if len(full) <= 2000:
            parts = [full]
        else:
            parts, cur, n = [], head, len(head)
            for p in re.split(r"\n\s*\n", desc):
                if n + len(p) > 2000 and cur.strip() != head.strip():
                    parts.append(cur); cur, n = head + "(cont)\n", len(head) + 7
                cur += "\n" + p; n += len(p)
            if cur.strip():
                parts.append(cur)
        for i, pt in enumerate(parts):
            ids.append(f"attack::{tid}::{i}"); docs.append(pt)
            metas.append({"source": "mitre-attack/enterprise-attack",
                          "license": "ATT&CK Terms of Use", "tech_id": tid,
                          "name": name, "kind": "ref"})
    print(f"  {len(set(m['tech_id'] for m in metas))} techniques -> {len(ids)} chunks")
    if a.dry_run:
        print("  sample:\n   " + docs[0][:240].replace("\n", "\n   ")); print("  DRY RUN"); return 0
    import chromadb
    col = chromadb.PersistentClient(path=a.db).get_or_create_collection(a.collection)
    try:
        ex = col.get(); stale = [i for i in ex["ids"] if i.startswith("attack::")]
        if stale: col.delete(ids=stale); print(f"  purged {len(stale)} stale attack chunks")
    except Exception as e:
        print("  purge skip:", e)
    B = 256
    for s in range(0, len(ids), B):
        col.upsert(ids=ids[s:s+B], documents=docs[s:s+B], metadatas=metas[s:s+B])
        print(f"  ...{min(s+B, len(ids))}/{len(ids)}")
    print(f"  ok {a.collection} now {col.count()} chunks")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
