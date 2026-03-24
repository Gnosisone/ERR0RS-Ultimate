import ast, sys
with open('src/ui/errorz_launcher.py', 'r', encoding='utf-8', errors='replace') as f:
    src = f.read()
tree = ast.parse(src)
for n in ast.walk(tree):
    if isinstance(n, ast.ImportFrom) and n.module:
        mod = n.module or ''
        if any(x in mod for x in ['postex','wireless','social_module','social.social']):
            names = [a.name for a in n.names]
            print(f"Line {n.lineno}: from {mod} import {names}")
