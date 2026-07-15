#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — OUTPUT INTERPRETER                       ║
║              src/core/output_interpreter.py                       ║
║                                                                  ║
║  The keystone that closes the loop. You paste real tool output   ║
║  (nmap, NetExec, hydra, hashcat, gobuster, sqlmap); ERR0RS:      ║
║    1. detects which tool produced it,                            ║
║    2. PARSES it into Finding objects (the missing utility),      ║
║    3. EXPLAINS what each finding MEANS (SOC-analyst voice),      ║
║    4. RECOMMENDS the next move — reusing next_step_engine's      ║
║       rules — with a command_anatomy breakdown attached, plus    ║
║       soc_mentor OPSEC and purple_team detection cross-links.    ║
║                                                                  ║
║  This is deliberately deterministic (regex + the existing rule   ║
║  engine): no LLM call, so it's instant, offline, and never       ║
║  hallucinates a port or a command. It is the ground truth the    ║
║  RAG/LLM layer should lean on, not the other way around.         ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.core.operator import Finding


# ═══════════════════════════════════════════════════════════════════════════
# TOOL DETECTION — fingerprint the source tool from its output shape
# ═══════════════════════════════════════════════════════════════════════════

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """NetExec/CME/hashcat colourise output; strip codes before parsing."""
    return _ANSI.sub("", text or "")


# (compiled signature, tool-name). First match wins; order = specificity.
_SIGNATURES = [
    (re.compile(r"Nmap scan report|Starting Nmap|PORT\s+STATE\s+SERVICE", re.I), "nmap"),
    (re.compile(r"^\s*(SMB|LDAP|WINRM|MSSQL|RDP|FTP|SSH)\s+\S+\s+\d+\s+\S+\s+\[[+\-*]\]", re.M), "nxc"),
    (re.compile(r"\]\[\w+\]\s+host:\s+\S+\s+login:", re.I), "hydra"),
    (re.compile(r"\(Status:\s*\d+\)\s*\[Size", re.I), "gobuster"),
    (re.compile(r"available databases \[\d+\]|is vulnerable|back-end DBMS", re.I), "sqlmap"),
    (re.compile(r"Session\.\.+:|Recovered\.\.+:|\$krb5|Status\.\.+: Cracked", re.I), "hashcat"),
]


def detect_tool(output: str) -> Optional[str]:
    """Best-effort identification of the tool that produced this output."""
    text = _strip_ansi(output)
    for rx, tool in _SIGNATURES:
        if rx.search(text):
            return tool
    return None


# ═══════════════════════════════════════════════════════════════════════════
# MEANING LAYER — what a finding actually enables (the teaching part)
# Keyed by service token / port; used to explain WHY a finding matters.
# ═══════════════════════════════════════════════════════════════════════════

SERVICE_MEANING = {
    "445":  ("SMB — file sharing and the backbone of Windows/AD.",
             "Richest low-effort surface: null-session enumeration, share access, "
             "user lists, and the EternalBlue check all start here."),
    "139":  ("NetBIOS — legacy SMB session service.",
             "Usually rides alongside 445; enum4linux dumps users/shares/policy."),
    "88":   ("Kerberos — this host is a Domain Controller.",
             "Enables username validation without a password, AS-REP roasting, and "
             "marks the heart of the domain."),
    "389":  ("LDAP — the directory itself.",
             "Anonymous bind often leaks users, groups, and SPNs; check description "
             "fields for hidden passwords."),
    "636":  ("LDAPS — LDAP over TLS.",
             "Same directory data as 389 but encrypted on the wire."),
    "22":   ("SSH — encrypted remote shell.",
             "Targets: weak passwords (careful brute), reused keys, and known-CVE banners."),
    "21":   ("FTP — file transfer.",
             "Test anonymous login first; often world-readable or writable."),
    "80":   ("HTTP — a web application.",
             "The biggest attack surface: fingerprint the stack, then fuzz paths and "
             "test the OWASP Top 10."),
    "443":  ("HTTPS — a web application over TLS.",
             "Same as 80 with -k on tools; check the cert for internal hostnames."),
    "3389": ("RDP — remote desktop.",
             "Check BlueKeep (CVE-2019-0708); careful credential attacks after enum."),
    "3306": ("MySQL — a database service.",
             "Test empty/default creds; a hit often means direct data access."),
    "1433": ("MSSQL — a database service.",
             "Empty 'sa' password and xp_cmdshell are classic footholds."),
    "5985": ("WinRM — Windows Remote Management.",
             "Valid creds here often mean an interactive shell via evil-winrm."),
    "5432": ("PostgreSQL — a database service.",
             "Try postgres/postgres; can lead to code execution via COPY/plpython."),
    "53":   ("DNS — name resolution.",
             "Attempt a zone transfer (AXFR); if allowed it dumps every hostname."),
    "6379": ("Redis — in-memory data store.",
             "Frequently unauthenticated; KEYS * may hand you sessions or a write primitive."),
}

# Service-name (from -sV) → representative port, so name-only lines still map.
_SERVICE_ALIAS = {
    "microsoft-ds": "445", "netbios-ssn": "139", "kerberos-sec": "88",
    "ldap": "389", "ldapssl": "636", "ssh": "22", "ftp": "21",
    "http": "80", "https": "443", "ms-wbt-server": "3389", "mysql": "3306",
    "ms-sql-s": "1433", "wsman": "5985", "postgresql": "5432", "domain": "53",
    "redis": "6379",
}


# ═══════════════════════════════════════════════════════════════════════════
# PARSERS — raw tool output → List[Finding]
# Kinds are chosen to match what next_step_engine already consumes:
#   open_port (detail.port/service) · endpoint (detail.path) · technology
#   plus creds / vuln for the credential + web-vuln paths.
# ═══════════════════════════════════════════════════════════════════════════

_RE_NMAP_HOST = re.compile(r"Nmap scan report for\s+([^\s(]+)")
_RE_NMAP_PORT = re.compile(
    r"^(\d{1,5})/(tcp|udp)\s+(open|filtered|open\|filtered)\s+(\S+)(?:\s+(.*))?$", re.M)


def parse_nmap(text: str) -> List[Finding]:
    findings: List[Finding] = []
    for m in _RE_NMAP_PORT.finditer(text):
        port, proto, state, service, version = m.groups()
        if "open" not in state:
            continue
        findings.append(Finding(
            tool="nmap", kind="open_port",
            value=f"{port}/{proto} {service}".strip(),
            detail={"port": port, "proto": proto, "service": service,
                    "version": (version or "").strip()},
            severity="info",
        ))
    return findings


_RE_NXC = re.compile(
    r"^\s*(SMB|LDAP|WINRM|MSSQL|RDP|FTP|SSH)\s+(\S+)\s+\d+\s+(\S+)\s+"
    r"\[([+\-*])\]\s+(.*)$", re.M)
_RE_NXC_CRED = re.compile(r"([^\s:\\]+(?:\\[^\s:]+)?):(\S+)")


def parse_nxc(text: str) -> List[Finding]:
    """Parse NetExec / CrackMapExec lines. '[+]' = success; '(Pwn3d!)' = admin."""
    findings: List[Finding] = []
    for m in _RE_NXC.finditer(_strip_ansi(text)):
        proto, host, hostname, marker, rest = m.groups()
        if marker != "+":
            continue  # only act on successes
        pwned = "Pwn3d!" in rest or "(Pwn3d" in rest
        cred = _RE_NXC_CRED.search(rest)
        user = cred.group(1) if cred else ""
        secret = cred.group(2) if cred else ""
        findings.append(Finding(
            tool="nxc", kind="creds",
            value=f"{user} on {host} ({proto}){' [ADMIN]' if pwned else ''}".strip(),
            detail={"host": host, "hostname": hostname, "proto": proto.lower(),
                    "user": user, "secret": secret, "admin": pwned,
                    "is_hash": bool(re.fullmatch(r"[0-9a-fA-F]{32}", secret or ""))},
            severity="high" if pwned else "medium",
        ))
    return findings


_RE_HYDRA = re.compile(
    r"\[(\d+)\]\[(\w+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)", re.I)


def parse_hydra(text: str) -> List[Finding]:
    findings: List[Finding] = []
    for m in _RE_HYDRA.finditer(text):
        port, service, host, login, password = m.groups()
        findings.append(Finding(
            tool="hydra", kind="creds",
            value=f"{login}:{password} on {host} ({service})",
            detail={"host": host, "proto": service.lower(), "port": port,
                    "user": login, "secret": password, "admin": False, "is_hash": False},
            severity="high",
        ))
    return findings


_RE_HASHCAT = re.compile(r"^([0-9a-fA-F]{16,}|\$[\w$*.\-/+=]+?)\:(.+)$", re.M)


def parse_hashcat(text: str) -> List[Finding]:
    """Parse cracked hashes (potfile / --show format: hash:plaintext)."""
    findings: List[Finding] = []
    for m in _RE_HASHCAT.finditer(_strip_ansi(text)):
        h, plain = m.groups()
        if plain.strip().lower() in ("", "cracked"):
            continue
        findings.append(Finding(
            tool="hashcat", kind="creds",
            value=f"cracked → {plain.strip()}",
            detail={"hash": h, "secret": plain.strip(), "user": "", "admin": False,
                    "is_hash": False},
            severity="high",
        ))
    return findings


_RE_GOBUSTER = re.compile(r"^(\/\S*)\s+\(Status:\s*(\d+)\)", re.M)


def parse_gobuster(text: str) -> List[Finding]:
    findings: List[Finding] = []
    for m in _RE_GOBUSTER.finditer(_strip_ansi(text)):
        path, status = m.groups()
        findings.append(Finding(
            tool="gobuster", kind="endpoint",
            value=path,
            detail={"path": path, "status": status},
            severity="info",
        ))
    return findings


def parse_sqlmap(text: str) -> List[Finding]:
    findings: List[Finding] = []
    if re.search(r"is vulnerable|Parameter:.*(GET|POST).*", text, re.I) or "sqlmap identified" in text.lower():
        findings.append(Finding(
            tool="sqlmap", kind="vuln", value="sql injection confirmed",
            detail={"type": "sqli"}, severity="critical"))
    dbs = re.search(r"available databases \[\d+\]:\s*((?:\s*\[\*\]\s*\S+)+)", text)
    if dbs:
        names = re.findall(r"\[\*\]\s*(\S+)", dbs.group(1))
        findings.append(Finding(
            tool="sqlmap", kind="database", value=f"{len(names)} databases",
            detail={"databases": names}, severity="high"))
    return findings


PARSERS = {
    "nmap":     parse_nmap,
    "nxc":      parse_nxc,
    "hydra":    parse_hydra,
    "hashcat":  parse_hashcat,
    "gobuster": parse_gobuster,
    "sqlmap":   parse_sqlmap,
}


def _extract_target(text: str, findings: List[Finding]) -> str:
    """Best-effort target: nmap host line, or a host from a finding's detail."""
    m = _RE_NMAP_HOST.search(text)
    if m:
        return m.group(1)
    for f in findings:
        host = f.detail.get("host")
        if host:
            return host
    return ""


# ═══════════════════════════════════════════════════════════════════════════
# MEANING + RECOMMENDATION (reuse next_step_engine; decorate with anatomy)
# ═══════════════════════════════════════════════════════════════════════════

def _finding_meaning(f: Finding) -> str:
    """One-line 'why this matters' for a finding — the teaching layer."""
    if f.kind == "open_port":
        port = f.detail.get("port", "")
        svc = f.detail.get("service", "")
        key = port if port in SERVICE_MEANING else _SERVICE_ALIAS.get(svc, "")
        if key in SERVICE_MEANING:
            what, why = SERVICE_MEANING[key]
            return f"{what} {why}"
        return f"Service '{svc or 'unknown'}' is exposed — enumerate its version for known CVEs."
    if f.kind == "creds":
        if f.detail.get("admin"):
            return "ADMIN access — you can dump secrets (SAM/LSA) and pivot from here."
        if f.detail.get("is_hash"):
            return "You hold an NT hash — reuse it directly via Pass-the-Hash, no cracking needed."
        return "Valid credentials — authenticate and enumerate the domain as this user."
    if f.kind == "endpoint":
        status = f.detail.get("status", "")
        note = {"200": "live page", "301": "redirect", "302": "redirect",
                "401": "auth-protected — interesting", "403": "forbidden — often bypassable",
                "500": "server error — may be injectable"}.get(status, "discovered")
        return f"Hidden path ({status} {note}) — inspect it for functionality and flaws."
    if f.kind == "vuln":
        return "Confirmed vulnerability — move to controlled exploitation."
    if f.kind == "database":
        return "Database schema enumerated — pick a table and dump it."
    return "Noted."


def _mentor_opsec(tool: str) -> str:
    """Best-effort OPSEC tip from soc_mentor for a recommended tool."""
    try:
        from src.core import soc_mentor
    except Exception:
        return ""
    for candidate in (tool, tool.replace("impacket-", ""), tool.replace("-python", "")):
        m = soc_mentor.get_mentor(candidate)
        if m and m.get("opsec_tips"):
            return m["opsec_tips"][0]
    return ""


def _decorate(tool: str, args: List[str], reason: str, detection: str = "") -> Dict:
    """Turn a (tool, args, reason) suggestion into a fully-taught next step:
    the command, WHY, a command_anatomy breakdown, OPSEC, and detection note."""
    command = (tool + " " + " ".join(args)).strip()
    anatomy = {}
    try:
        from src.core import command_anatomy
        anatomy = command_anatomy.explain_command(command)
    except Exception:
        pass
    return {
        "command":   command,
        "why":       reason,
        "anatomy":   anatomy,
        "opsec":     _mentor_opsec(tool),
        "detection": detection,
    }


def _cred_followups(f: Finding, target: str) -> List[Dict]:
    """AD-foothold continuation for a credential finding (our own rules,
    matching the flowchart in soc_mentor). Cross-links purple pass-the-hash."""
    d = f.detail
    user = d.get("user") or "user"
    secret = d.get("secret") or "PASSWORD"
    host = d.get("host") or target or "TARGET"
    domain = user.split("\\")[0] if "\\" in user else "DOMAIN"
    bare_user = user.split("\\")[-1]
    auth = f"-u {bare_user} " + (f"-H {secret}" if d.get("is_hash") else f"-p {secret}")

    # What the blue team sees if this cred gets reused as a hash.
    pth_detection = ""
    if d.get("is_hash"):
        try:
            from src.security import purple_team
            det = purple_team.get_detections_json("pass-the-hash", "windows_events")
            pth_detection = det.get("windows_events", {}).get("summary", "")
        except Exception:
            pth_detection = ""

    steps = [
        _decorate("nxc", ["smb", host, *auth.split(), "--shares"],
                  "Confirm access and list shares as this account — proves the foothold and reveals reachable data.",
                  detection=pth_detection),
        _decorate("bloodhound-python",
                  ["-u", bare_user, "-p" if not d.get("is_hash") else "--hashes", secret,
                   "-d", domain, "-ns", host, "-c", "All"],
                  "Map the domain from this account and compute the shortest path to Domain Admin."),
    ]
    if d.get("admin"):
        steps.insert(1, _decorate(
            "impacket-secretsdump",
            [f"{domain}/{bare_user}:{secret}@{host}"],
            "You're admin here — dump SAM/LSA/cached hashes to fuel lateral movement.",
            detection=pth_detection or "Dumping LSASS/SAM triggers Sysmon EID 10 (lsass access) — see the Purple Team module."))
    return steps


def _recommend(findings: List[Finding], target: str) -> List[Dict]:
    """Reuse next_step_engine's deterministic rules for ports/endpoints/tech,
    add our credential rules, decorate everything, and de-duplicate."""
    recs: List[Dict] = []

    # Reuse the existing rule engine (deterministic halves only — NO LLM call).
    try:
        from src.core import next_step_engine as nse
        suggestions = (nse._apply_port_followups(findings, target)
                       + nse._apply_finding_rules(findings, target))
        for s in suggestions:
            recs.append(_decorate(s.tool, s.args, s.reason))
    except Exception:
        pass

    for f in findings:
        if f.kind == "creds":
            recs.extend(_cred_followups(f, target))

    seen, out = set(), []
    for r in recs:
        if r["command"] in seen:
            continue
        seen.add(r["command"])
        out.append(r)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def interpret(output: str, tool: Optional[str] = None, target: Optional[str] = None) -> Dict:
    """Interpret raw tool output into findings + meanings + taught next steps.

    Returns {tool, target, findings:[{...,meaning}], next_steps:[{command,why,
    anatomy,opsec,detection}], summary}. Never raises on odd input.
    """
    output = output or ""
    tool = tool or detect_tool(output)
    parser = PARSERS.get(tool or "")
    findings = parser(output) if parser else []
    target = target or _extract_target(output, findings)

    findings_out = [{
        "kind": f.kind, "value": f.value, "severity": f.severity,
        "detail": f.detail, "meaning": _finding_meaning(f),
    } for f in findings]

    next_steps = _recommend(findings, target)

    if not tool:
        summary = "Could not identify the tool from this output. Try `interpret <tool> <output>`."
    elif not findings:
        summary = f"Recognised {tool} output but found nothing actionable in it."
    else:
        summary = (f"{tool}: {len(findings)} finding(s), "
                   f"{len(next_steps)} recommended next step(s).")

    return {"tool": tool, "target": target, "findings": findings_out,
            "next_steps": next_steps, "summary": summary}


def format_interpretation(output: str, tool: Optional[str] = None,
                          target: Optional[str] = None) -> str:
    """Render an interpretation as a terminal-friendly briefing."""
    data = interpret(output, tool=tool, target=target)
    bar = "═" * 60
    out = [bar, "  🧠 ERR0RS READS THE OUTPUT", bar,
           f"  Tool: {data['tool'] or 'unknown'}"
           + (f"   Target: {data['target']}" if data['target'] else ""),
           f"  {data['summary']}"]

    if data["findings"]:
        out += ["", "  ── WHAT I SEE ──"]
        for f in data["findings"]:
            out.append(f"  • [{f['severity'].upper()}] {f['value']}")
            out.append(f"      → {f['meaning']}")

    if data["next_steps"]:
        out += ["", "  ── DO THIS NEXT ──"]
        for i, s in enumerate(data["next_steps"], 1):
            out.append(f"  {i}. $ {s['command']}")
            out.append(f"       WHY: {s['why']}")
            anat = s.get("anatomy") or {}
            if anat.get("plain_english"):
                out.append(f"       {anat['plain_english']}")
            if s.get("opsec"):
                out.append(f"       🥷 OPSEC: {s['opsec']}")
            if s.get("detection"):
                out.append(f"       🔵 SOC SEES: {s['detection']}")
    out += [bar, "  Tip: run `anatomy <command>` on any step for the full breakdown."]
    return "\n".join(out)
