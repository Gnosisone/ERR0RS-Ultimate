#!/usr/bin/env python3
"""Full Juice Shop auto-chain — final verification."""
import urllib.request, json, time, socket
socket.setdefaulttimeout(800)

def send(msg, timeout=700):
    req = urllib.request.Request(
        "http://localhost:8765/api/operator/receive",
        data=json.dumps({"msg":msg}).encode(),
        headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error":str(e)}

LOG = "/tmp/full_chain.log"
open(LOG,"w").close()
def log(m):
    with open(LOG,"a") as f: f.write(m+"\n"); f.flush()

log(f"[{time.strftime('%H:%M:%S')}] FULL CHAIN v4 — verification run")
log(f"set_target: {send('target is http://localhost:3000').get('reply','?')}")

steps = [
    ("whatweb",  "whatweb",                                                                                         120),
    ("gobuster", "gobuster",                                                                                        180),
    ("nikto",    "nikto",                                                                                           200),
    ("sqlmap",   "sqlmap -u http://localhost:3000/rest/products/search?q=1 --batch --random-agent --level=2 --risk=1 --time-sec=3 --timeout=15", 700),
    ("dalfox",   "dalfox url http://localhost:3000/rest/products/search?q=apple",                                   150),
]

totals = {"findings":0, "critical":0, "high":0}
for step, cmd, to in steps:
    log(f"\n=== {step} ===")
    r = send(cmd, timeout=to)
    if "error" in r:
        log(f"  ❌ {r['error']}")
        continue
    findings = r.get('findings',[])
    totals["findings"] += len(findings)
    log(f"  rc={r.get('returncode','?')} dur={r.get('duration',0):.1f}s findings={len(findings)}")
    for f in findings[:12]:
        totals[f['severity']] = totals.get(f['severity'], 0) + 1
        log(f"    [{f['severity']:8s}] {f['kind']:12s} {f['value'][:70]}")
    sugs = r.get('suggestions',[])
    for s in sugs[:2]:
        log(f"    ➡ next: {s['tool']:10s} ({int(s['confidence']*100)}%) {s['reason'][:55]}")

log("\n=== report ===")
r = send("report", timeout=20)
log(f"  {r.get('reply','?')}")
path = r.get('report_path','')

log(f"\n{'='*60}")
log(f"🏁 TOTALS: {totals['findings']} findings "
    f"({totals.get('critical',0)} crit, {totals.get('high',0)} high, "
    f"{totals.get('medium',0)} med, {totals.get('low',0)} low, {totals.get('info',0)} info)")
log(f"📄 Report: {path}")
