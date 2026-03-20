import ast, sys

files = [
    "src/ui/errorz_launcher.py",
    "src/tools/payload_studio/payload_engine.py",
    "src/tools/payload_studio/snippets.py",
]
all_ok = True
for f in files:
    try:
        src = open(f, encoding="utf-8").read()
        ast.parse(src)
        print(f"OK  {f}")
    except SyntaxError as e:
        print(f"ERR {f}: {e}")
        all_ok = False

if all_ok:
    print("\nAll Python files VALID")
else:
    sys.exit(1)
