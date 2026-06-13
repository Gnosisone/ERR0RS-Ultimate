#!/usr/bin/env python3
"""Export the OWNED teach corpus (src/core/teach_engine.py LESSONS) into an
instruction-tuning dataset for fine-tuning a small open base model.

Only Eros-authored content is used (lessons you own outright) — no third-party
RAG corpora — so the resulting weights carry no external license obligations.

Output: data/finetune/err0rs_lessons.jsonl   (chat format, one example/line)
  {"messages":[{"role":"user","content":...},{"role":"assistant","content":...}]}

  python3 tools/export_finetune_data.py            # write the dataset
  python3 tools/export_finetune_data.py --preview  # show a sample, write nothing
"""
from __future__ import annotations
import json, sys, importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data/finetune/err0rs_lessons.jsonl"
_spec = importlib.util.spec_from_file_location("teach_engine", ROOT / "src/core/teach_engine.py")
_te = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_te)
LESSONS, render_lesson, list_topics = _te.LESSONS, _te.format_lesson, _te.list_topics


def clean(topic: str) -> str:
    t = render_lesson(topic)
    for m in ("[[LESSON_CONTROLS", "\U0001f4ac Questions", "\u23ed"):
        i = t.find(m)
        if i != -1:
            t = t[:i]
    return t.strip()


def pairs_for(topic: str):
    L = LESSONS[topic]
    L = L if isinstance(L, dict) else {}
    out = []
    # 1) primary: full lesson — teaches the model ERR0RS's teaching voice
    out.append((f"Teach me about {topic} for penetration testing.", clean(topic)))
    # 2) crisp definition
    if L.get("summary"):
        out.append((f"What is {topic}?", L["summary"]))
    # 3) code lessons -> code generation
    if L.get("code"):
        subj = topic.replace("python-", "")
        out.append((f"Show me example Python code for {subj} in an offensive-security context.",
                    L["code"].strip()))
    # 4) tool lessons -> usage
    if L.get("typical") or L.get("flags"):
        usage = (L.get("typical", "") + "\n").strip()
        flags = L.get("flags") or {}
        if isinstance(flags, dict) and flags:
            usage += "\n" + "\n".join(f"{k}  —  {v}" for k, v in list(flags.items())[:8])
        if usage.strip():
            out.append((f"How do I use {topic} and what are its key options?", usage.strip()))
    return [(q, a) for q, a in out if a and a.strip()]


def main():
    preview = "--preview" in sys.argv
    examples = []
    for topic in list_topics():
        if topic in LESSONS:
            for q, a in pairs_for(topic):
                examples.append({"messages": [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ]})
    print(f"  lessons: {len(list_topics())} | training examples: {len(examples)}")
    if preview:
        import random
        for ex in random.sample(examples, min(2, len(examples))):
            print("\n  USER:", ex["messages"][0]["content"])
            print("  ASSISTANT:", ex["messages"][1]["content"][:200].replace("\n", " "), "...")
        print("\n  PREVIEW — nothing written.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    kb = OUT.stat().st_size / 1024
    print(f"  ok wrote {len(examples)} examples -> {OUT.relative_to(ROOT)} ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
