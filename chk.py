import ast, sys
f = "src/tools/payload_studio/snippets.py"
try:
    ast.parse(open(f).read())
    print("snippets.py OK")
except SyntaxError as e:
    print(f"ERROR: {e}")
    sys.exit(1)
