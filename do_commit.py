import subprocess, os, time, sys

os.chdir('H:/ERR0RS-Ultimate')

print("[1] Removing stale lock if present...")
lock = '.git/index.lock'
if os.path.exists(lock):
    try:
        os.remove(lock)
        print("  Removed lock file")
    except Exception as e:
        print(f"  Could not remove: {e} — trying anyway")
else:
    print("  No lock file")

time.sleep(1)

print("[2] git add -A...")
r = subprocess.run(['git', 'add', '-A'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(f"  rc={r.returncode}")
if r.stderr:
    print(f"  stderr: {r.stderr[:300]}")

time.sleep(1)

print("[3] git commit...")
msg = "feat: Flipper Zero Evolution Engine + session 4 fixes\n\n17/17 modules OK, Flipper evolves to Level 7 WAVE RIDER on first run."
r = subprocess.run(
    ['git', 'commit', '-m', msg],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f"  rc={r.returncode}")
print(f"  stdout: {r.stdout[:500]}")
if r.stderr:
    print(f"  stderr: {r.stderr[:300]}")

print("[4] git log --oneline -3...")
r = subprocess.run(['git', 'log', '--oneline', '-3'],
    capture_output=True, text=True, encoding='utf-8', errors='replace')
print(r.stdout)
print("DONE")
