#!/usr/bin/env python3
"""Export "The Ethical Operator" (Eros-authored book) into an instruction-tuning
dataset for the ERR0RS LoRA — SAME chat format as export_finetune_data.py:
  {"messages":[{"role":"user","content":...},{"role":"assistant","content":...}]}

Turns the book's sections and callout boxes (TECHNIQUE UP CLOSE / THREE TOOLS /
FORENSIC LENS / CONCEPT / LEGAL / DETECTION / CLEANUP / HANDS-ON), its glossary,
and its troubleshooting index into voice-rich user->assistant pairs. The goal is
VOICE (purple-team teaching style), not fact memorization — RAG handles facts.

  python3 tools/export_book_finetune_data.py --preview   # sample, write nothing
  python3 tools/export_book_finetune_data.py             # write the dataset

Author: Gary Holden Schneider (Eros) | ERR0RS-Ultimate
"""
from __future__ import annotations
import json, re, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "ethical_operator_book.md"
OUT  = ROOT / "data/finetune/err0rs_book_lessons.jsonl"

MAX_ANS = 3000          # cap answer length (trim at paragraph boundary)
MIN_ANS = 120

# title-based question templates (these box titles are clean noun-phrases)
TITLE_BOX = {
    "TECHNIQUE UP CLOSE": "Walk me through {t}.",
    "THREE TOOLS":        "What tools should I use for {t}, and when should I reach for each?",
}
# topic-based templates (these box titles are often full sentences -> use the section topic)
TOPIC_BOX = {
    "FORENSIC LENS": "From a defender's perspective, how is {topic} detected and investigated?",
    "CONCEPT":       "Explain the key concept behind {topic}.",
    "LEGAL":         "What are the legal and ethical considerations around {topic}?",
    "DETECTION":     "How is {topic} detected?",
    "CLEANUP":       "How do I clean up properly after working with {topic}?",
    "HANDS-ON":      "Give me a hands-on exercise for {topic}.",
}
ALL_LABELS = set(TITLE_BOX) | set(TOPIC_BOX)
SECTION_Q = [
    "Teach me about {t} in penetration testing.",
    "Explain {t}.",
    "I'm learning about {t} — break it down for me.",
    "Help me understand {t}.",
]


def _trim(text: str, cap: int = MAX_ANS) -> str:
    text = text.strip()
    if len(text) <= cap:
        return text
    cut = text.rfind("\n\n", 0, cap)
    if cut < cap * 0.5:
        cut = text.rfind(". ", 0, cap)
        cut = cut + 1 if cut != -1 else cap
    return text[:cut].strip()


def _clean_topic(sec: str) -> str:
    t = re.sub(r"^\d+(\.\d+)*\s+", "", sec).strip()      # drop "6.2 "
    t = t.split(":")[0].strip() if ":" in t and len(t.split(":")[0]) > 8 else t
    return t.rstrip(".")


def _strip_md(s: str) -> str:
    s = re.sub(r"(?m)^#{1,6}\s*", "", s)                 # heading marks
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def parse_box(block: str):
    """block: one callout (blockquote) with '>' already stripped.
    Returns (label, title, body) or None."""
    m = re.match(r"\s*\*\*(.+?)\*\*\s*(.*)", block, re.S)
    if not m:
        return None
    header, body = m.group(1).strip(), m.group(2).strip()
    # header looks like: "🎯 TECHNIQUE UP CLOSE — how Kerberoasting works..."
    parts = re.split(r"\s+[—–-]\s+", header, maxsplit=1)
    label_raw = parts[0]
    title = parts[1].strip() if len(parts) > 1 else ""
    label = re.sub(r"[^A-Z\- ]", "", label_raw).strip()  # strip emoji -> "TECHNIQUE UP CLOSE"
    label = re.sub(r"\s+", " ", label).strip()
    for key in ALL_LABELS:
        if key in label:
            return key, title, body
    return None


def iter_units(md: str):
    """Yield ('section', vol, chap, sec, prose) and ('box', vol, chap, sec, block)."""
    lines = md.split("\n")
    in_fence = False
    vol = chap = sec = ""
    prose, box = [], []

    def flush_box():
        if box:
            yield_val = ("box", vol, chap, sec, "\n".join(box).strip())
            box.clear()
            return yield_val
        return None

    pending = []
    def emit_prose():
        if prose:
            txt = _strip_md("\n".join(prose)).strip()
            prose.clear()
            if txt:
                pending.append(("section", vol, chap, sec, txt))

    for line in lines:
        st = line.lstrip()
        if st.startswith("```") or st.startswith("~~~"):
            in_fence = not in_fence
            prose.append(line); continue
        if not in_fence:
            if re.match(r"^# VOLUME", line):
                if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip())); box.clear()
                emit_prose(); vol = re.sub(r"^#\s*", "", line).strip(); chap=""; sec=""
                yield from pending; pending.clear(); continue
            if re.match(r"^# Chapter", line):
                if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip())); box.clear()
                emit_prose(); chap = re.sub(r"^#\s*", "", line).strip(); sec=""
                yield from pending; pending.clear(); continue
            if re.match(r"^# Appendix", line):
                if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip())); box.clear()
                emit_prose(); vol="Appendices"; chap = re.sub(r"^#\s*", "", line).strip(); sec=""
                yield from pending; pending.clear(); continue
            if re.match(r"^##\s", line):
                if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip())); box.clear()
                emit_prose(); sec = re.sub(r"^#+\s*", "", line).strip()
                yield from pending; pending.clear(); continue
            if line.lstrip().startswith(">"):
                # blockquote line -> part of a callout box
                emit_prose()
                box.append(re.sub(r"^\s*>\s?", "", line))
                continue
            else:
                if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip())); box.clear()
        prose.append(line)
    emit_prose()
    if box: pending.append(("box", vol, chap, sec, "\n".join(box).strip()))
    yield from pending


def build(md: str):
    examples = []
    glossary_chap = ""
    for kind, vol, chap, sec, content in iter_units(md):
        is_appendix = (vol == "Appendices")
        # ---- glossary: parse **Term** — definition into Q/A ----
        if is_appendix and "Glossary" in chap:
            for para in re.split(r"\n\s*\n", content):
                gm = re.match(r"\*\*(.+?)\*\*\s*[—–-]\s*(.+)", para.strip(), re.S)
                if gm:
                    term, dfn = gm.group(1).strip(), _trim(gm.group(2).strip(), 700)
                    if len(dfn) >= 40:
                        examples.append((f"What does \"{term}\" mean in security?", dfn))
            continue
        # ---- troubleshooting: leave to RAG (terse table rows) ----
        if is_appendix and "Troubleshooting" in chap:
            continue
        # ---- cheat sheet: skip (terse, fact-y -> RAG's job) ----
        if is_appendix and "Cheat Sheet" in chap:
            continue

        if kind == "box":
            parsed = parse_box(content)
            if not parsed:
                continue
            label, title, body = parsed
            body = _trim(body)
            if len(body) < MIN_ANS:
                continue
            topic = _clean_topic(sec) if sec else _clean_topic(chap)
            if not topic:
                continue
            if label in TITLE_BOX and title and len(title) <= 80:
                tt = title.rstrip(".")
                q = TITLE_BOX[label].format(t=tt[0].lower() + tt[1:])
            elif label in TITLE_BOX:
                q = ("Walk me through how {topic} works." if label == "TECHNIQUE UP CLOSE"
                     else "What tools should I use for {topic}, and when should I reach for each?"
                     ).format(topic=topic)
            else:
                q = TOPIC_BOX[label].format(topic=topic)
            if not q.endswith((".", "?")):
                q += "."
            examples.append((q, body))
        else:  # section prose
            topic = _clean_topic(sec) if sec else _clean_topic(chap)
            if not topic or len(content) < MIN_ANS:
                continue
            qi = int(hashlib.md5((vol + chap + sec).encode()).hexdigest(), 16) % len(SECTION_Q)
            examples.append((SECTION_Q[qi].format(t=topic), _trim(content)))

    # dedupe + to messages format
    seen, rows = set(), []
    for q, a in examples:
        key = hashlib.md5((q + "||" + a[:120]).encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        rows.append({"messages": [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]})
    return rows


def main():
    if not BOOK.exists():
        print(f"book not found: {BOOK}"); return 1
    md = BOOK.read_text(encoding="utf-8", errors="replace")
    rows = build(md)
    print(f"  book examples: {len(rows)}")
    if "--preview" in sys.argv:
        import random
        for ex in random.sample(rows, min(4, len(rows))):
            print("\n  USER:", ex["messages"][0]["content"])
            print("  ASSISTANT:", ex["messages"][1]["content"][:240].replace("\n", " "), "...")
        print("\n  PREVIEW — nothing written.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for ex in rows:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"  ok wrote {len(rows)} examples -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
