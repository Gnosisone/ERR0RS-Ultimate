#!/usr/bin/env python3
"""
gen_lesson.py - offline teach-lesson generator for ERR0RS.

Captures a tool's real --help, asks a local security LLM (Foundation-Sec-8B,
run offline / build-time) to write a lesson GROUNDED ONLY in that help text,
validates the schema, and emits a LESSONS-ready entry for teach_engine.py.

Usage:
    python3 tools/gen_lesson.py nmap sqlmap        # print paste-ready blocks
    python3 tools/gen_lesson.py wpprobe --write    # insert into teach_engine.py
    ERR0RS_LESSON_MODEL=foundation-sec-8b python3 tools/gen_lesson.py nmap

Model: set ERR0RS_LESSON_MODEL to your ollama tag. Foundation-Sec-8B is the
intended build-time model; it is too slow on the Pi 5 at runtime, so run this on
capable hardware and commit the generated lessons (offline content-baking).
"""
import json, os, re, subprocess, sys, urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL  = os.environ.get("ERR0RS_LESSON_MODEL", "foundation-sec-8b")
KEYS   = ("summary", "typical", "flags", "read", "next", "caution", "cia")
ANSI   = re.compile(r"\x1b\[[0-9;]*[mGKH]")

SYS_PROMPT = (
    "You are a senior offensive-security instructor writing a concise lesson for a "
    "purple-team learning platform. You are given a tool name and its real --help "
    "output. Write a lesson GROUNDED STRICTLY in that help text - never invent flags "
    "or behavior it does not support. Output ONLY a JSON object (no prose) with EXACTLY "
    "these keys: summary (string), typical (string: one example command + short # comment), "
    "flags (object mapping real flag/subcommand -> plain-English explanation), "
    "read (array of strings: how to read output / gotchas), "
    "next (array of strings shaped 'tool (why)'), "
    "caution (string: authorization + blast-radius warning), "
    "cia (array of strings: CONFIDENTIALITY/INTEGRITY/AVAILABILITY placement, one line each). "
    "Keep it tight, practical, authorization-only framing in caution."
)

def get_help(tool):
    for args in (["--help"], ["-h"], ["help"]):
        try:
            r = subprocess.run([tool, *args], capture_output=True, text=True, timeout=20)
            out = ANSI.sub("", (r.stdout or "") + "\n" + (r.stderr or "")).strip()
            if len(out) > 40:
                return out[:6000]
        except Exception:
            continue
    return None

def gen(tool, help_text):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {"role": "user", "content": "TOOL: %s\n\n--help output:\n%s" % (tool, help_text)},
        ],
        "stream": False, "format": "json",
        "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 1500},
    }
    req = urllib.request.Request(OLLAMA + "/api/chat",
                                data=json.dumps(payload).encode(),
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    if data.get("done_reason") not in (None, "stop"):
        print("  [!] %s: stopped early (%s) - may be truncated" % (tool, data.get("done_reason")), file=sys.stderr)
    return json.loads(data["message"]["content"])

def validate(d):
    miss = [k for k in KEYS if k not in d]
    if miss: return "missing keys: %s" % miss
    if not isinstance(d["flags"], dict) or not d["flags"]: return "flags must be a non-empty object"
    for k in ("read", "next", "cia"):
        if not isinstance(d[k], list) or not d[k]: return "%s must be a non-empty array" % k
    return None

def to_block(tool, d):
    e = lambda s: str(s).replace("\\", "\\\\").replace('"', '\\"')
    L = ['    "%s": {' % e(tool),
         '        "summary": "%s",' % e(d["summary"]),
         '        "typical": "%s",' % e(d["typical"]),
         '        "flags": {']
    for k, v in d["flags"].items():
        L.append('            "%s": "%s",' % (e(k), e(v)))
    L.append("        },")
    L.append('        "read": [')
    for it in d["read"]:
        L.append('            "%s",' % e(it))
    L.append("        ],")
    L.append('        "next": [%s],' % ", ".join('"%s"' % e(x) for x in d["next"]))
    L.append('        "caution": "%s",' % e(d["caution"]))
    L.append('        "cia": [')
    for it in d["cia"]:
        L.append('            "%s",' % e(it))
    L.append("        ],")
    L.append("    },")
    return "\n".join(L)

def insert(block):
    import shutil, ast
    p = "src/core/teach_engine.py"
    s = open(p, encoding="utf-8").read()
    anchor = "LESSONS = {\n"
    assert s.count(anchor) == 1, "LESSONS anchor not unique"
    shutil.copy(p, "/tmp/teach_engine.py.bak.gen")
    s2 = s.replace(anchor, anchor + block + "\n", 1)
    ast.parse(s2)
    open(p, "w", encoding="utf-8").write(s2)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    write = "--write" in sys.argv
    if not args:
        print(__doc__); return
    print("[*] model=%s ollama=%s\n" % (MODEL, OLLAMA), file=sys.stderr)
    for tool in args:
        h = get_help(tool)
        if not h:
            print("  [skip] %s: no --help captured (installed? on PATH?)" % tool, file=sys.stderr); continue
        try:
            d = gen(tool, h)
        except Exception as ex:
            print("  [fail] %s: model/parse error: %s" % (tool, ex), file=sys.stderr); continue
        err = validate(d)
        if err:
            print("  [fail] %s: invalid lesson (%s)" % (tool, err), file=sys.stderr); continue
        block = to_block(tool, d)
        if write:
            insert(block); print("  [ok] %s: inserted (backup /tmp/teach_engine.py.bak.gen)" % tool, file=sys.stderr)
        else:
            print(block)

if __name__ == "__main__":
    main()
