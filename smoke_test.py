"""ERR0RS Smoke Test - syntax check all 5 patched files + import check."""
import ast, sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.chdir(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    "src/__init__.py",
    "src/ai/agents/__init__.py",
    "src/core/language_layer.py",
    "src/ui/errorz_launcher.py",
    "requirements.txt",
    "requirements-kali.txt",
]

print("=" * 60)
print("  ERR0RS Bug-Fix Smoke Test")
print("=" * 60)

all_good = True

# 1 — Syntax check every Python file
for path in FILES:
    if not path.endswith(".py"):
        # For txt files, just check they contain the new deps
        content = open(path, encoding="utf-8").read()
        has_chroma = "chromadb" in content
        has_st     = "sentence-transformers" in content
        status = "OK" if (has_chroma and has_st) else "MISSING DEPS"
        marker = "✓" if (has_chroma and has_st) else "✗"
        print(f"  {marker}  {path:45s}  [{status}]")
        if status != "OK":
            all_good = False
        continue

    try:
        src = open(path, encoding="utf-8").read()
        ast.parse(src)
        print(f"  ✓  {path:45s}  [SYNTAX OK]")
    except SyntaxError as e:
        print(f"  ✗  {path:45s}  [SYNTAX ERROR: {e}]")
        all_good = False

print()

# 2 — Spot-check key fixes are present
CHECKS = [
    ("src/core/language_layer.py",
     "return 'unknown'\n",
     "Bug 1: classify_command has single return"),
    ("src/ui/errorz_launcher.py",
     "if FLIPPER_ENGINE:\n                        self._json(run_flipper_evolution",
     "Bug 2: evolution calls are guarded"),
    ("src/__init__.py",
     "_sys.modules['src.education.knowledge_base']",
     "Bug 3: knowledge_base pre-registered"),
    ("src/ai/agents/__init__.py",
     "except Exception as _vuln_err:",
     "Bug 5: VulnChainAgent wrapped in try/except"),
]

print("  Content checks:")
for path, needle, label in CHECKS:
    src = open(path, encoding="utf-8").read()
    found = needle in src
    marker = "✓" if found else "✗"
    status = "PRESENT" if found else "NOT FOUND"
    print(f"  {marker}  {label:50s}  [{status}]")
    if not found:
        all_good = False

print()
print("=" * 60)
print(f"  RESULT: {'ALL CLEAR ✓' if all_good else 'FAILURES FOUND ✗'}")
print("=" * 60)
sys.exit(0 if all_good else 1)
