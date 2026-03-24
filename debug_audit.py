"""ERR0RS Bug Audit Script — finds all 5 known bugs and reports line numbers."""
import sys, os

ROOT = r"H:\ERR0RS-Ultimate"

def scan(path, markers):
    """Return list of (line_num, line_text) for any line containing a marker."""
    hits = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            for m in markers:
                if m in line:
                    hits.append((i, m, line.rstrip()))
                    break
    return hits

print("=" * 65)
print(" ERR0RS BUG AUDIT")
print("=" * 65)

# Bug 1 — classify_command duplicate body in language_layer.py
path1 = os.path.join(ROOT, "src", "core", "language_layer.py")
hits1 = scan(path1, ["def classify_command", "return 'unknown'", 'return "unknown"'])
print(f"\n[Bug 1] language_layer.py — classify_command occurrences:")
for ln, m, txt in hits1:
    print(f"  L{ln:4d}: {txt[:80]}")

# Bug 2 — flipper guard in errorz_launcher.py
path2 = os.path.join(ROOT, "src", "ui", "errorz_launcher.py")
hits2 = scan(path2, ["/api/flipper", "run_flipper_evolution", "FLIPPER_ENGINE"])
print(f"\n[Bug 2] errorz_launcher.py — flipper handler:")
for ln, m, txt in hits2:
    print(f"  L{ln:4d}: {txt[:80]}")

# Bug 3 — src/__init__.py race condition check
path3 = os.path.join(ROOT, "src", "__init__.py")
hits3 = scan(path3, ["src.education", "exec_module", "education_new"])
print(f"\n[Bug 3] src/__init__.py — education redirect:")
for ln, m, txt in hits3:
    print(f"  L{ln:4d}: {txt[:80]}")

# Bug 4 — requirements.txt missing chromadb/sentence-transformers
path4 = os.path.join(ROOT, "requirements.txt")
path4k = os.path.join(ROOT, "requirements-kali.txt")
for p in [path4, path4k]:
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    missing = [pkg for pkg in ["chromadb", "sentence-transformers"] if pkg not in content]
    print(f"\n[Bug 4] {os.path.basename(p)} — missing: {missing or 'NONE (already present)'}")

# Bug 5 — agents/__init__.py VulnChainAgent import guard
path5 = os.path.join(ROOT, "src", "ai", "agents", "__init__.py")
hits5 = scan(path5, ["VulnChainAgent", "try:", "except"])
print(f"\n[Bug 5] agents/__init__.py — VulnChainAgent import:")
for ln, m, txt in hits5:
    print(f"  L{ln:4d}: {txt[:80]}")

print("\n" + "=" * 65)
print(" AUDIT COMPLETE")
print("=" * 65)
