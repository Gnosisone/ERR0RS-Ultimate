import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
with open('src/ui/errorz_launcher.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if '/api/' in line and ('POST' in line or 'path ==' in line or 'path.startswith' in line):
        print(f"Line {i}: {line.rstrip()}")
