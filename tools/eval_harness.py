#!/usr/bin/env python3
"""ERR0RS eval harness — turn model/pipeline changes into a NUMBER.

  lessons: semantic similarity of a model's answers vs the curriculum (runs now)
  xbow:    parse XBOW validation-benchmarks into a manifest (execution = future)

  python3 tools/eval_harness.py lessons --model gemma3:1b --n 12
  python3 tools/eval_harness.py xbow

NOTE: XBOW benchmark data carries canary strings forbidding training inclusion.
It is used ONLY as eval here and is never ingested into the RAG or fine-tune set.
"""
import argparse, json, sys, random, math, importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def _embed(texts):
    from chromadb.utils import embedding_functions
    return embedding_functions.DefaultEmbeddingFunction()(texts)

def _cos(a, b):
    d = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(y*y for y in b))
    return d / (na*nb + 1e-9)

def _ask(model, q, host="http://localhost:11434"):
    import requests
    r = requests.post(f"{host}/api/chat", json={"model": model, "messages": [
        {"role": "system", "content": "You are a concise penetration-testing tutor."},
        {"role": "user", "content": q}], "stream": False, "keep_alive": -1,
        "options": {"temperature": 0.2, "num_predict": 300}}, timeout=120)
    return r.json().get("message", {}).get("content", "")

def eval_lessons(model, n):
    spec = importlib.util.spec_from_file_location("te", ROOT / "src/core/teach_engine.py")
    te = importlib.util.module_from_spec(spec); spec.loader.exec_module(te)
    topics = [t for t in te.list_topics()
              if isinstance(te.LESSONS[t], dict) and te.LESSONS[t].get("summary")]
    random.seed(42); sample = random.sample(topics, min(n, len(topics)))
    refs = [te.LESSONS[t]["summary"] for t in sample]
    qs = [f"Explain {t} and how it is used in penetration testing." for t in sample]
    print(f"  asking {model} {len(sample)} held-out questions...")
    answers = [_ask(model, q) for q in qs]
    embs = _embed(answers + refs); A, R = embs[:len(answers)], embs[len(answers):]
    sims = [_cos(A[i], R[i]) for i in range(len(sample))]
    for t, s in sorted(zip(sample, sims), key=lambda x: x[1]):
        print(f"    {s:.3f}  {t}")
    mean = sum(sims) / len(sims)
    print(f"\n  SCORE (mean answer<->curriculum similarity): {mean:.4f}  [model={model}, n={len(sample)}]")
    out = ROOT / f"data/eval/lessons_{model.replace(':', '_')}.json"; out.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"model": model, "n": len(sample), "mean": mean,
               "per_topic": dict(zip(sample, sims))}, open(out, "w"), indent=2)
    print(f"  saved -> {out.relative_to(ROOT)}   (re-run vs err0rs-tuned to compare)")

def eval_xbow(path):
    base = Path(path) / "benchmarks"
    if not base.exists():
        print(f"  XBOW benchmarks not found at {base} — clone xbow-engineering/validation-benchmarks"); return
    import collections
    rows = []
    for j in sorted(base.glob("*/benchmark.json")):
        try: d = json.loads(j.read_text())
        except Exception: continue
        rows.append({"id": j.parent.name, "name": d.get("name", ""), "level": d.get("level", ""),
                     "win_condition": d.get("win_condition", ""), "tags": d.get("tags", [])})
    by_tag = collections.Counter(t for r in rows for t in r["tags"])
    by_lvl = collections.Counter(r["level"] for r in rows)
    print(f"  parsed {len(rows)} XBOW benchmarks")
    print("  by level:", dict(sorted(by_lvl.items(), key=lambda x: str(x[0]))))
    print("  top tags:", dict(by_tag.most_common(10)))
    out = ROOT / "data/eval/xbow_manifest.json"; out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(out, "w"), indent=2)
    print(f"  saved -> {out.relative_to(ROOT)}")
    print("  TODO execution harness: `docker compose up` per benchmark, point the ERR0RS")
    print("       agent at it, capture the flag, score solved/total.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["lessons", "xbow"])
    ap.add_argument("--model", default="gemma3:1b")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--xbow-path", default="/home/kali/err0rs_refs_src/validation-benchmarks")
    a = ap.parse_args()
    eval_lessons(a.model, a.n) if a.mode == "lessons" else eval_xbow(a.xbow_path)

if __name__ == "__main__":
    sys.exit(main() or 0)
