import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
with open('src/core/smart_wizard.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'WIZARDS' in line and '=' in line and 'def' not in line:
        print(f"Line {i}: {line.rstrip()}")
    if 'WIZARD_TRIGGERS' in line and '=' in line and 'def' not in line:
        print(f"Line {i}: {line.rstrip()}")
