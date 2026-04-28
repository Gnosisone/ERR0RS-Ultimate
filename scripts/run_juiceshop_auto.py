#!/usr/bin/env python3
import urllib.request, json, time, socket
socket.setdefaulttimeout(800)

def send(msg, timeout=800):
    req = urllib.request.Request(
        "http://localhost:8765/api/operator/receive",
        data=json.dumps({"msg":msg}).encode(),
        headers={"Content-Type":"application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        data["_elapsed"] = time.time()-t0
    except Exception as e:
        data = {"status":"error","error":str(e)}
    return data

LOG = "/tmp/juiceshop_auto.log"
def log(m):
    with open(LOG,"a") as f: f.write(m+"\n"); f.flush()

open(LOG,"w").close()
log(f"[{time.strftime('%H:%M:%S')}] JUICE SHOP AUTO-CHAIN v3")

r = send("target is http://localhost:3000")
log(f"set_target: {r.get('reply','?')}")

for step, cmd in [
    ("whatweb",  "whatweb"),
    ("gobuster", "gobuster"),
    ("nikto",    "nikto"),
    ("sqlmap",   "sqlmap -u http://localhost:3000/rest/products/search?q=1 --batch --random-agent --level=2 --risk=1 --time-sec=3 --timeout=15"),
    ("dalfox",   "dalfox url http://localhost:3000/rest/products/search?q=apple"),
]:
    log(f"\n=== {step} ===")
    r = send(cmd)
    if "error" in r:
        log(f"  ❌ error: {r['error']}")
        continue
    log(f"  rc={r.get('returncode','?')} dur={r.get('duration',0):.1f}s findings={len(r.get('findings',[]))}")
    for f in r.get('findings',[])[:12]:
        log(f"    [{f['severity']:7s}] {f['kind']:12s} {f['value'][:70]}")

log("\n=== report ===")
r = send("report", timeout=20)
log(f"  {r.get('reply','?')}")

r = send("status")
s = r.get('state',{})
log(f"\n🏁 FINAL: tools_run={s.get('tools_run')} findings={s.get('findings')}")
