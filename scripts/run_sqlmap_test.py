#!/usr/bin/env python3
import urllib.request, json, time, socket
socket.setdefaulttimeout(800)

def send(msg, timeout=700):
    req = urllib.request.Request(
        "http://localhost:8765/api/operator/receive",
        data=json.dumps({"msg":msg}).encode(),
        headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

LOG = "/tmp/sqlmap_via_operator.log"
open(LOG,"w").close()
def log(m):
    with open(LOG,"a") as f: f.write(m+"\n"); f.flush()
    print(m, flush=True)

log(f"[{time.strftime('%H:%M:%S')}] sqlmap via operator — full flags passthrough test")

t0 = time.time()
r = send("sqlmap -u http://localhost:3000/rest/products/search?q=1 --batch --random-agent --level=2 --risk=1 --time-sec=3 --timeout=15")
elapsed = time.time() - t0

log(f"\ntotal elapsed: {elapsed:.1f}s")
log(f"reported dur: {r.get('duration',0):.1f}s")
log(f"rc: {r.get('returncode','?')}")
log(f"findings: {len(r.get('findings',[]))}")
for f in r.get('findings',[]):
    log(f"  [{f['severity']:8s}] {f['kind']:12s} {f['value'][:80]}")
log(f"\nsuggestions: {len(r.get('suggestions',[]))}")
for s in r.get('suggestions',[])[:3]:
    log(f"  ➡ {s['tool']:10s} ({int(s['confidence']*100)}%) {s['reason'][:55]}")
