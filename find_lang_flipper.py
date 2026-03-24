import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
with open('src/core/language_layer.py', 'r', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if 'BADUSB' in line or 'FLIPPER' in line or 'badusb' in line.lower():
        print(f"Line {i}: {line.rstrip()}")
