import subprocess, os, time, sys

os.chdir('H:/ERR0RS-Ultimate')

# Kill any lingering git processes
subprocess.run(['taskkill', '/F', '/IM', 'git.exe'], capture_output=True)
time.sleep(1)

# Remove stale lock file
lock = 'H:/ERR0RS-Ultimate/.git/index.lock'
try:
    os.remove(lock)
    print(f'Removed lock: {lock}')
except FileNotFoundError:
    print('No lock file found')
except Exception as e:
    print(f'Lock removal error: {e}')

time.sleep(1)

# Stage all
r = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
print('git add:', r.returncode, r.stderr[:200] if r.stderr else 'OK')

# Commit
r = subprocess.run(
    ['git', 'commit', '-F', '.git/COMMIT_MSG_S4.txt'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print('git commit stdout:', r.stdout[:500])
print('git commit stderr:', r.stderr[:300] if r.stderr else '')
print('Return code:', r.returncode)
