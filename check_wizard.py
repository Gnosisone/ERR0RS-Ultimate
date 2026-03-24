import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')
import src.core.smart_wizard as m
exports = [x for x in dir(m) if not x.startswith('_')]
print("smart_wizard exports:", exports)
