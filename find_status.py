import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
with open('src/ui/errorz_launcher.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'def ' in line and ('status' in line.lower() or '_status' in line.lower()):
        print(f"Line {i}: {line.rstrip()}")
