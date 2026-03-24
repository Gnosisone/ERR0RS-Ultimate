import subprocess, sys
r = subprocess.run(
    ["git", "push", "origin", "main"],
    cwd="H:/ERR0RS-Ultimate",
    capture_output=True, text=True,
    timeout=60
)
print("STDOUT:", r.stdout)
print("STDERR:", r.stderr)
print("RETURNCODE:", r.returncode)
