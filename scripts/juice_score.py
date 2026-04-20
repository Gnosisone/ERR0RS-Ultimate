#!/usr/bin/env python3
"""Quick Juice Shop challenge score checker."""
import urllib.request, json, sys

try:
    url = "http://localhost:3000/api/Challenges?limit=999"
    with urllib.request.urlopen(url, timeout=5) as r:
        d = json.loads(r.read())
    cs = d.get("data", [])
    solved = [c for c in cs if c.get("solved")]
    total = len(cs)
    s = len(solved)
    pct = round(s / total * 100, 1) if total else 0
    bar = "█" * int(pct / 2) + "░" * (50 - int(pct / 2))
    print(f"\n  \033[38;5;208m\033[1mJuice Shop CTF\033[0m")
    print(f"  [{bar}]")
    print(f"  {s}/{total} challenges solved ({pct}%)\n")
    # Show recent solves
    diff_names = {1:"★",2:"★★",3:"★★★",4:"★★★★",5:"★★★★★",6:"★★★★★★"}
    for c in sorted(solved, key=lambda x: x.get("difficulty",0)):
        stars = diff_names.get(c.get("difficulty",1),"?")
        print(f"  \033[38;5;82m✓\033[0m [{stars:6s}] {c['name']}")
    print()
except Exception as e:
    print(f"  ⚠️  Could not reach Juice Shop: {e}")
    print("  Start it: cd /home/kali/targets/juice-shop && node build/app.js &")
