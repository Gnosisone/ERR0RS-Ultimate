import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from src.tools.flipper.flipper_evolution import (
    run_flipper_evolution, FlipperEvolution, EVOLUTION_LEVELS
)

print("[ERR0RS] Flipper Evolution Engine Self-Test")
print("=" * 56)

# Status test (no hardware needed)
r = run_flipper_evolution("status")
print(r["stdout"])
print()

# Detection test
r = run_flipper_evolution("detect")
print(r["stdout"])
print()

# Dry-run evolution (no SD card = local output mode)
print("[ERR0RS] Dry-run evolution (local output mode)...")
r2 = run_flipper_evolution("evolve")
print(r2["stdout"][:1200])
print()
print(f"Status : {r2['status']}")
print(f"Level  : {r2.get('level', '?')} — {r2.get('stdout', '')[:40]}")
print(f"XP     : {r2.get('xp', 0)}")
print(f"Happy  : {r2.get('happy', False)}")
print("\n[ERR0RS] Flipper Evolution Engine OK")
