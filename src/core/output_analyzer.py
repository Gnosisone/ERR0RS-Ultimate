"""
ERR0RS Output Analyzer
══════════════════════
Parses each tool's stdout into structured Finding objects.

Finding kinds: open_port, service, vuln, creds, endpoint, technology, cve,
               header, os, database, info, misc, status
Severity:      info | low | medium | high | critical
"""
import re, logging
from typing import List
log = logging.getLogger("err0rs.analyzer")


def _make_finding(tool, kind, value, detail=None, severity="info"):
    from src.core.operator import Finding
    return Finding(tool=tool, kind=kind, value=value,
                   detail=detail or {}, severity=severity)


CRIT_PORTS = {"445","3389","23","1433","3306","5432","6379","27017","21"}
HIGH_PORTS = {"22","80","443","8080","8443","139","135","25","143","110"}


def _parse_nmap(stdout, target):
    out = []
    for m in re.finditer(r"^(\d+)/(tcp|udp)\s+(open|open\|filtered)\s+(\S+)\s*(.*)$",
                         stdout, re.MULTILINE):
        port, proto, state, svc, ver = m.groups()
        sev = "critical" if port in CRIT_PORTS else "high" if port in HIGH_PORTS else "medium"
        out.append(_make_finding("nmap","open_port",
                   f"{port}/{proto} {svc} {ver}".strip(),
                   detail={"port":port,"proto":proto,"service":svc,
                           "version":ver.strip(),"state":state,"target":target},
                   severity=sev))
    for m in re.finditer(r"OS details?:\s*(.+)$", stdout, re.MULTILINE):
        out.append(_make_finding("nmap","os",m.group(1).strip(),severity="info"))
    for m in re.finditer(r"(CVE-\d{4}-\d+)", stdout):
        out.append(_make_finding("nmap","cve",m.group(1),severity="high"))
    if "VULNERABLE" in stdout:
        out.append(_make_finding("nmap","vuln",
                   "NSE script reported VULNERABLE state",severity="critical"))
    return out


def _parse_whatweb(stdout, target):
    out = []
    clean = re.sub(r"\x1b\[[0-9;]*[mGK]", "", stdout)
    for m in re.finditer(r"([A-Za-z][\w-]*)\[([^\]]+)\]", clean):
        name, val = m.group(1), m.group(2)
        if name in {"HTTPServer","Apache","nginx","IIS","X-Powered-By","PHP",
                    "JQuery","Bootstrap","WordPress","Drupal","Joomla",
                    "HTML5","Script","Title","Meta-Refresh","Country","IP",
                    "UncommonHeaders","X-Frame-Options"}:
            out.append(_make_finding("whatweb","technology",
                       f"{name}: {val}",detail={"name":name,"value":val}))
    m = re.search(r"\[(\d{3})\s+\w+\]", clean)
    if m: out.append(_make_finding("whatweb","status",f"HTTP {m.group(1)}"))
    return out


def _parse_nikto(stdout, target):
    out = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("+"): continue
        content = line.lstrip("+ ").strip()
        low = content.lower()
        if any(k in low for k in ("start time","end time","target ip",
               "target hostname","target port","platform",
               "your nikto installation","host(s) tested","scan terminated")):
            continue
        sev = "medium"
        if "cve-" in low or "rce" in low or "sql injection" in low: sev = "high"
        if "critical" in low or "eternalblue" in low:              sev = "critical"
        if "header missing" in low or "uncommon header" in low:    sev = "low"
        out.append(_make_finding("nikto",
                   "vuln" if sev in ("high","critical") else "misc",
                   content[:180], severity=sev))
    return out


def _parse_gobuster(stdout, target):
    out = []
    for m in re.finditer(r"^(/\S+)\s+\(Status:\s*(\d+)\)", stdout, re.MULTILINE):
        path, status = m.group(1), m.group(2)
        sev = "high" if path.lower() in ("/admin","/phpmyadmin",
               "/wp-admin","/api","/.git") else "medium"
        out.append(_make_finding("gobuster","endpoint",
                   f"{path} [{status}]",
                   detail={"path":path,"status":status,"target":target},
                   severity=sev))
    return out


def _parse_nuclei(stdout, target):
    out = []
    for m in re.finditer(r"\[([^\]]+)\]\s*\[(http|tcp|dns|file)\]\s*\[(\w+)\]\s*(\S+)",
                         stdout):
        tmpl, proto, sev, url = m.groups()
        severity = sev.lower()
        if severity not in ("critical","high","medium","low","info"):
            severity = "medium"
        out.append(_make_finding("nuclei","vuln",
                   f"{tmpl} → {url}",
                   detail={"template":tmpl,"protocol":proto,
                           "severity":severity,"url":url},
                   severity=severity))
    return out


def _parse_sqlmap(stdout, target):
    out = []
    clean = re.sub(r"\x1b\[[0-9;]*[mGK]", "", stdout)
    low = clean.lower()

    # Confirmed injection patterns (fresh scan or resumed from cache)
    confirmed = ("is vulnerable" in low
                 or ("parameter" in low and "injectable" in low and "not injectable" not in low)
                 or "sqlmap identified the following injection point" in low
                 or "sqlmap resumed the following injection point" in low)

    # Heuristic / early-stop patterns
    heuristic = ("appears to be" in low and "injectable" in low) or \
                ("might be injectable" in low)

    if confirmed:
        # Extract parameter name + injection type from structured block
        param = ""
        inj_type = ""
        m = re.search(r"parameter:\s*(\w+)", clean, re.I)
        if m: param = f" (param: {m.group(1)})"
        m = re.search(r"type:\s*([^\n]+)", clean, re.I)
        if m: inj_type = f" — {m.group(1).strip()}"
        out.append(_make_finding("sqlmap","vuln",
                   f"SQL Injection confirmed{param}{inj_type}",
                   severity="critical"))
        # Also extract the payload for the report
        m = re.search(r"payload:\s*(.+)", clean, re.I)
        if m:
            out.append(_make_finding("sqlmap","vuln",
                       f"Working payload: {m.group(1).strip()[:120]}",
                       severity="critical"))
    elif heuristic:
        m = re.search(r"parameter\s+['\"]?(\w+)['\"]?\s+appears", clean, re.I)
        param = f" (param: {m.group(1)})" if m else ""
        out.append(_make_finding("sqlmap","vuln",
                   f"SQL Injection likely — heuristic hit{param}", severity="high"))

    # DBMS detection — check both "is" and "could be" variants
    m = re.search(r"back-end DBMS(?:\s*is\s*|\s*could be\s*|:\s*)['\"]?(\w[\w\s]*?)['\"]?[\n.]", clean, re.I)
    if m:
        dbms = m.group(1).strip()
        if dbms and len(dbms) < 50:
            out.append(_make_finding("sqlmap","technology",
                       f"DBMS: {dbms}", severity="info"))

    # Dumped DBs
    for m in re.finditer(r"available databases \[(\d+)\]:\s*\n((?:\[\*\]\s+\S+\n?)+)",
                         clean):
        dbs = re.findall(r"\[\*\]\s+(\S+)", m.group(2))
        for db in dbs:
            out.append(_make_finding("sqlmap","database",f"DB: {db}",
                       detail={"database":db}, severity="high"))

    # Dumped table data
    if "table" in low and "entries" in low and "dumped" in low:
        out.append(_make_finding("sqlmap","database",
                   "Table data dumped — check sqlmap output dir", severity="critical"))

    # WAF
    if "waf/ips" in low or "protected by some kind of waf" in low:
        out.append(_make_finding("sqlmap","info",
                   "WAF/IPS detected — may need --tamper", severity="medium"))
    return out


def _parse_dalfox(stdout, target):
    out = []
    for line in stdout.splitlines():
        clean = re.sub(r"\x1b\[[0-9;]*[mGK]", "", line)
        if "[POC]" in clean or "[VERIF]" in clean:
            out.append(_make_finding("dalfox","vuln",
                       f"XSS: {clean.strip()[:160]}", severity="high"))
        elif "[VULN]" in clean:
            out.append(_make_finding("dalfox","vuln",
                       f"XSS: {clean.strip()[:160]}", severity="critical"))
    return out


def _parse_hydra(stdout, target):
    out = []
    for m in re.finditer(
        r"\[\w+\]\s+host:\s*(\S+)\s+login:\s*(\S+)\s+password:\s*(\S+)", stdout):
        host, login, pw = m.groups()
        out.append(_make_finding("hydra","creds",
                   f"{login}:{pw}@{host}",
                   detail={"host":host,"user":login,"pass":pw},
                   severity="critical"))
    return out


PARSERS = {
    "nmap":     _parse_nmap,
    "whatweb":  _parse_whatweb,
    "nikto":    _parse_nikto,
    "gobuster": _parse_gobuster,
    "nuclei":   _parse_nuclei,
    "sqlmap":   _parse_sqlmap,
    "dalfox":   _parse_dalfox,
    "hydra":    _parse_hydra,
}


def analyze(tool, stdout, target=""):
    if not stdout: return []
    parser = PARSERS.get(tool)
    if not parser: return []
    try:
        return parser(stdout, target)
    except Exception as e:
        log.warning(f"Analyzer failed for {tool}: {e}")
        return []
