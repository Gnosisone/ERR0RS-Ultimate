import subprocess, os
os.chdir('H:/ERR0RS-Ultimate')
r = subprocess.run(
    ['git', 'add', 'requirements.txt', 'requirements-kali.txt'],
    capture_output=True, text=True
)
print('add:', r.returncode, r.stderr[:100] if r.stderr else 'OK')
r = subprocess.run(
    ['git', 'commit', '-m', 'fix: remove pygame, add requirements-kali.txt for headless Kali/Pi'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print('commit:', r.returncode)
print(r.stdout[:300])
