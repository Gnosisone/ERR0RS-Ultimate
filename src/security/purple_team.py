#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — PURPLE TEAM PLAYGROUND                   ║
║              src/security/purple_team.py                          ║
║                                                                  ║
║  The missing seam between the two existing halves of ERR0RS:     ║
║    • soc_mentor.py  → offensive OPSEC (how loud is a technique)   ║
║    • blue_team.py   → defensive remediation (how to harden)      ║
║  This module maps a RED technique to its BLUE detection          ║
║  artifacts — MITRE, Sysmon, Windows events, Sigma, Splunk,       ║
║  Elastic, Sentinel, Defender — so an operator learns both sides  ║
║  of the same action. Red fires it; blue catches it; you learn    ║
║  the fingerprint it leaves.                                      ║
║                                                                  ║
║  Constitution (Eros / KIS): teach the operator what the SOC      ║
║  will see, so they operate with full awareness — knowledge,      ║
║  integrity, security.                                            ║
║                                                                  ║
║  Zero heavy deps (stdlib only), 100% local, gracefully degrades. ║
║  Bridges into ReportGenerator via technique_to_finding().        ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import textwrap
from typing import Dict, List, Optional

# Detection "surfaces" a technique can be seen on. Order = render order.
# Kept as a tuple so callers can validate a requested section against it.
DETECTION_SURFACES = (
    "sysmon",
    "windows_events",
    "sigma",
    "splunk",
    "elastic",
    "sentinel",
    "defender",
)

# Human labels for the surfaces (terminal + frontend share these).
SURFACE_LABELS = {
    "sysmon":         "Sysmon",
    "windows_events": "Windows Events",
    "sigma":          "Sigma",
    "splunk":         "Splunk SPL",
    "elastic":        "Elastic",
    "sentinel":       "Microsoft Sentinel",
    "defender":       "Microsoft Defender",
}

# Aliases → canonical technique key. Lets an operator type what they know.
_ALIASES = {
    "pth":             "pass-the-hash",
    "passthehash":     "pass-the-hash",
    "pass the hash":   "pass-the-hash",
    "kerberoast":      "kerberoasting",
    "kerberoasting":   "kerberoasting",
    "asrep":           "asrep-roasting",
    "asreproast":      "asrep-roasting",
    "as-rep roasting": "asrep-roasting",
}


# ═══════════════════════════════════════════════════════════════════════════
# TECHNIQUE LIBRARY
# Each entry is a self-contained purple-team lesson. Extend by adding keys —
# the API and renderers are fully data-driven, so no code changes are needed
# to grow the library.
# ═══════════════════════════════════════════════════════════════════════════

TECHNIQUES: Dict[str, Dict] = {

    "pass-the-hash": {
        "name":       "Pass-the-Hash",
        "aka":        ["PtH", "NTLM hash reuse"],
        "tactic":     "Lateral Movement",
        "severity":   "high",          # feeds technique_to_finding()
        "opsec_ref":  "pass-the-hash", # cross-links to soc_mentor.MENTOR if present
        "mitre": [
            {"id": "T1550.002", "name": "Use Alternate Authentication Material: Pass the Hash"},
            {"id": "T1003.001", "name": "OS Credential Dumping: LSASS Memory (hash source)"},
        ],
        "attack": {
            "summary": (
                "NTLM proves knowledge of a password by proving possession of its "
                "hash — so the plaintext is optional. Steal the NT hash once and "
                "authenticate with it anywhere it is valid."
            ),
            "why": (
                "Windows NTLM hashes the password client-side; the server never "
                "needs the plaintext, so neither does the attacker. The hash IS "
                "the credential."
            ),
            "steps": [
                {"cmd": "nxc smb 10.0.0.0/24 -u administrator -H <nthash> --local-auth",
                 "note": "Spray the hash across the subnet; '-H' takes the hash where '-p' takes a password."},
                {"cmd": "nxc smb 10.0.0.15 -u administrator -H <nthash> -x whoami --local-auth",
                 "note": "Where it says 'Pwn3d!', execute — the hash is admin on that host."},
                {"cmd": "impacket-psexec administrator@10.0.0.15 -hashes :<nthash>",
                 "note": "Interactive SYSTEM shell; leading ':' means NT-only (no LM hash)."},
            ],
        },
        "detections": {
            "sysmon": {
                "summary": (
                    "Before a hash is passed it is usually stolen from LSASS. "
                    "Sysmon sees the theft as a process opening lsass.exe with "
                    "credential-dumping access rights."
                ),
                "events": ["Event ID 10 (ProcessAccess)", "Event ID 1 (ProcessCreate)", "Event ID 3 (NetworkConnect)"],
                "content": (
                    "Event ID 10 (ProcessAccess)\n"
                    "  TargetImage: C:\\Windows\\System32\\lsass.exe\n"
                    "  GrantedAccess: 0x1010 / 0x1410 / 0x1438  (classic Mimikatz masks)\n"
                    "  SourceImage: anything not a known AV/EDR agent\n"
                    "Event ID 1 (ProcessCreate)  — the tool that injects the credential\n"
                    "Event ID 3 (NetworkConnect) — the outbound 445/tcp lateral hop"
                ),
            },
            "windows_events": {
                "summary": (
                    "On the target, PtH appears as an NTLM-backed network logon. "
                    "The Mimikatz sekurlsa::pth signature is a Logon Type 9 with "
                    "the 'seclogo' process and 'Negotiate' package — a combination "
                    "legitimate apps almost never produce."
                ),
                "events": ["4624 (Logon Type 9 / 3)", "4776 (NTLM validation on DC)", "4672 (admin logon)"],
                "content": (
                    "4624  An account was successfully logged on\n"
                    "      Logon Type: 9 (NewCredentials)   <- sekurlsa::pth tell\n"
                    "      Logon Process: seclogo\n"
                    "      Authentication Package: Negotiate\n"
                    "      (network PtH instead shows Type 3 + package 'NTLM')\n"
                    "4776  DC validated NTLM credentials\n"
                    "The clincher: a 4624 NTLM logon with NO matching 4768/4769\n"
                    "(Kerberos). Real domain users get Kerberos; NTLM-only lateral\n"
                    "auth is suspicious by default."
                ),
            },
            "sigma": {
                "summary": "Vendor-neutral rule. Write once, convert to any SIEM with 'sigma convert'.",
                "content": (
                    "title: Pass the Hash Activity (Logon Type 9 / seclogo)\n"
                    "id: e1c9a1f2-5b7a-4a11-9c2d-pth00000001\n"
                    "status: stable\n"
                    "logsource:\n"
                    "  product: windows\n"
                    "  service: security\n"
                    "detection:\n"
                    "  selection:\n"
                    "    EventID: 4624\n"
                    "    LogonType: 9\n"
                    "    LogonProcessName: 'seclogo'\n"
                    "    AuthenticationPackageName: 'Negotiate'\n"
                    "  filter:\n"
                    "    SubjectUserSid: 'S-1-0-0'\n"
                    "  condition: selection and not filter\n"
                    "falsepositives:\n"
                    "  - Some legitimate runas /netonly usage\n"
                    "level: high\n"
                    "tags:\n"
                    "  - attack.lateral_movement\n"
                    "  - attack.t1550.002"
                ),
            },
            "splunk": {
                "summary": "Roll up by host+account so one attacker's lateral movement collapses into one row.",
                "content": (
                    "index=windows source=\"WinEventLog:Security\" EventCode=4624\n"
                    "  LogonType=9 Logon_Process=seclogo Authentication_Package=Negotiate\n"
                    "| where Security_ID!=\"S-1-0-0\"\n"
                    "| stats count min(_time) as first max(_time) as last\n"
                    "        by host, Account_Name, Source_Network_Address\n"
                    "| convert ctime(first) ctime(last)\n"
                    "| sort - count"
                ),
            },
            "elastic": {
                "summary": "KQL detection plus an EQL sequence tying the LSASS read to the lateral hop.",
                "content": (
                    "event.code : \"4624\"\n"
                    "  and winlog.event_data.LogonType : \"9\"\n"
                    "  and winlog.event_data.LogonProcessName : \"seclogo\"\n"
                    "  and winlog.event_data.AuthenticationPackageName : \"Negotiate\"\n"
                    "  and not winlog.event_data.SubjectUserSid : \"S-1-0-0\"\n"
                    "\n"
                    "sequence by host.name with maxspan=1m\n"
                    "  [ process where event.code==\"10\"\n"
                    "      and winlog.event_data.TargetImage : \"*lsass.exe\" ]\n"
                    "  [ network where destination.port==445 ]"
                ),
            },
            "sentinel": {
                "summary": "Endpoint 4624 event; pair with Defender for Identity's DC-side PtH alert.",
                "content": (
                    "SecurityEvent\n"
                    "| where EventID == 4624\n"
                    "| where LogonType == 9\n"
                    "| where LogonProcessName =~ \"seclogo\"\n"
                    "| where AuthenticationPackageName =~ \"Negotiate\"\n"
                    "| where SubjectUserSid != \"S-1-0-0\"\n"
                    "| project TimeGenerated, Computer, TargetAccount, IpAddress\n"
                    "| summarize Hits=count(), Hosts=make_set(Computer)\n"
                    "          by TargetAccount, IpAddress"
                ),
            },
            "defender": {
                "summary": "MDE flags LSASS access + anomalous NTLM chains; MDI flags a hash from a new source.",
                "content": (
                    "MDE alerts: 'Suspicious authentication activity',\n"
                    "            'Possible Pass-the-Hash attack'\n"
                    "MDI alert:  'Suspected identity theft (pass-the-hash)'\n"
                    "\n"
                    "Advanced Hunting (KQL over the MDE schema):\n"
                    "DeviceLogonEvents\n"
                    "| where LogonType == \"Network\" and Protocol == \"NTLM\"\n"
                    "| join kind=leftanti (\n"
                    "    IdentityLogonEvents | where Protocol == \"Kerberos\"\n"
                    "  ) on AccountName\n"
                    "| project Timestamp, DeviceName, AccountName, RemoteIP"
                ),
            },
        },
        "remediation": (
            "Enforce SMB signing; disable NTLM where feasible; enable LSA "
            "Protection (RunAsPPL) and Credential Guard to stop the LSASS dump; "
            "restrict local-admin reuse with LAPS."
        ),
        "learning": (
            "Pass-the-Hash works because NTLM authenticates with the hash, not the "
            "plaintext. The defensive tell is an NTLM network logon (Event 4624, "
            "Logon Type 9, seclogo/Negotiate) with no matching Kerberos ticket. "
            "Kill the hash source (Credential Guard) and the technique dies."
        ),
    },

    "kerberoasting": {
        "name":       "Kerberoasting",
        "aka":        ["SPN roasting"],
        "tactic":     "Credential Access",
        "severity":   "high",
        "opsec_ref":  "bloodhound",
        "mitre": [
            {"id": "T1558.003", "name": "Steal or Forge Kerberos Tickets: Kerberoasting"},
        ],
        "attack": {
            "summary": (
                "Any authenticated domain user can request a service ticket (TGS) "
                "for an account that has an SPN. The ticket is encrypted with the "
                "service account's password hash — crack it offline, no lockouts."
            ),
            "why": (
                "The KDC hands a TGS to anyone with a valid TGT. If the service "
                "account uses RC4 and a weak password, the ticket cracks fast and "
                "silently on the attacker's own hardware."
            ),
            "steps": [
                {"cmd": "impacket-GetUserSPNs corp.local/jdoe:Pass123 -dc-ip 10.0.0.10 -request",
                 "note": "Enumerate SPN accounts and request their TGS tickets in one shot."},
                {"cmd": "hashcat -m 13100 kerb.hash rockyou.txt -r best64.rule",
                 "note": "Crack the $krb5tgs$ hash offline — invisible to the target."},
            ],
        },
        "detections": {
            "windows_events": {
                "summary": (
                    "A burst of TGS requests (4769) using weak RC4 encryption for "
                    "many SPNs from one account is the classic signature."
                ),
                "events": ["4769 (TGS requested)"],
                "content": (
                    "4769  A Kerberos service ticket was requested\n"
                    "      Ticket Encryption Type: 0x17 (RC4-HMAC)  <- weak, roastable\n"
                    "      Ticket Options: 0x40810000\n"
                    "      Service Name: the SPN being roasted\n"
                    "Signal: one account requesting many distinct SPNs with RC4 in a\n"
                    "short window. AES (0x12) tickets are far less roastable."
                ),
            },
            "sigma": {
                "summary": "Detect RC4 TGS requests, excluding machine accounts.",
                "content": (
                    "title: Potential Kerberoasting via RC4 TGS Requests\n"
                    "id: b2d9c4a1-11ce-4f6d-9a8e-krb00000003\n"
                    "logsource:\n"
                    "  product: windows\n"
                    "  service: security\n"
                    "detection:\n"
                    "  selection:\n"
                    "    EventID: 4769\n"
                    "    TicketEncryptionType: '0x17'\n"
                    "    TicketOptions: '0x40810000'\n"
                    "  filter_computer:\n"
                    "    ServiceName|endswith: '$'\n"
                    "  condition: selection and not filter_computer\n"
                    "level: medium\n"
                    "tags:\n"
                    "  - attack.credential_access\n"
                    "  - attack.t1558.003"
                ),
            },
            "splunk": {
                "summary": "Flag accounts requesting an abnormal number of distinct RC4 SPNs.",
                "content": (
                    "index=windows EventCode=4769 Ticket_Encryption_Type=0x17\n"
                    "| where NOT match(Service_Name, \"\\$$\")\n"
                    "| stats dc(Service_Name) as spn_count values(Service_Name) as spns\n"
                    "        by Account_Name\n"
                    "| where spn_count > 5"
                ),
            },
            "sentinel": {
                "summary": "Same RC4-TGS burst logic in KQL.",
                "content": (
                    "SecurityEvent\n"
                    "| where EventID == 4769 and TicketEncryptionType == \"0x17\"\n"
                    "| where ServiceName !endswith \"$\"\n"
                    "| summarize SPNs=dcount(ServiceName) by Account, bin(TimeGenerated, 1h)\n"
                    "| where SPNs > 5"
                ),
            },
            "defender": {
                "summary": "Defender for Identity ships a native Kerberoasting alert.",
                "content": (
                    "MDI alert: 'Suspected Kerberoasting attempt'\n"
                    "Fires on anomalous TGS request volume + weak encryption from a\n"
                    "single principal. Tune out known service scanners."
                ),
            },
        },
        "remediation": (
            "Use 25+ char random passwords or gMSAs for service accounts; enforce "
            "AES-only Kerberos; remove unnecessary SPNs; alert on RC4 TGS bursts."
        ),
        "learning": (
            "Kerberoasting turns 'any valid user' into 'service-account cracker' "
            "because the KDC encrypts the TGS with the service account's own hash. "
            "The fix is entropy: a long random password makes the offline crack "
            "computationally hopeless, and gMSAs automate that."
        ),
    },

    "asrep-roasting": {
        "name":       "AS-REP Roasting",
        "aka":        ["AS-REP roast"],
        "tactic":     "Credential Access",
        "severity":   "high",
        "opsec_ref":  "kerberos",
        "mitre": [
            {"id": "T1558.004", "name": "Steal or Forge Kerberos Tickets: AS-REP Roasting"},
        ],
        "attack": {
            "summary": (
                "Accounts with 'Do not require Kerberos preauthentication' set will "
                "return an AS-REP encrypted with the user's password hash to ANY "
                "requester — crackable offline with zero authentication attempts."
            ),
            "why": (
                "Preauth is what normally proves you know the password before the "
                "KDC replies. Disable it and the KDC hands out a crackable blob to "
                "an unauthenticated attacker."
            ),
            "steps": [
                {"cmd": "impacket-GetNPUsers corp.local/ -usersfile users.txt -no-pass -dc-ip 10.0.0.10",
                 "note": "Request AS-REPs for preauth-disabled accounts with no credentials."},
                {"cmd": "hashcat -m 18200 asrep.hash rockyou.txt",
                 "note": "Crack the $krb5asrep$ hash offline."},
            ],
        },
        "detections": {
            "windows_events": {
                "summary": "AS-REQ (4768) with preauth not required and RC4 encryption.",
                "events": ["4768 (AS-REQ / TGT requested)"],
                "content": (
                    "4768  A Kerberos authentication ticket (TGT) was requested\n"
                    "      Pre-Authentication Type: 0    <- preauth NOT required\n"
                    "      Ticket Encryption Type: 0x17  (RC4-HMAC)\n"
                    "Signal: TGT requests with preauth type 0 are rare and roastable;\n"
                    "a spike from one source IP across many users is enumeration."
                ),
            },
            "sigma": {
                "summary": "Detect TGT requests where preauthentication is disabled.",
                "content": (
                    "title: AS-REP Roasting (Preauth Not Required)\n"
                    "id: f3a71b90-24de-4c8a-9b1c-krb00000004\n"
                    "logsource:\n"
                    "  product: windows\n"
                    "  service: security\n"
                    "detection:\n"
                    "  selection:\n"
                    "    EventID: 4768\n"
                    "    PreAuthType: '0'\n"
                    "    TicketEncryptionType: '0x17'\n"
                    "  condition: selection\n"
                    "level: high\n"
                    "tags:\n"
                    "  - attack.credential_access\n"
                    "  - attack.t1558.004"
                ),
            },
            "splunk": {
                "summary": "Surface preauth-disabled TGT requests, especially in bursts.",
                "content": (
                    "index=windows EventCode=4768 Pre_Authentication_Type=0\n"
                    "| stats count values(Account_Name) as accounts\n"
                    "        by Client_Address\n"
                    "| where count > 3"
                ),
            },
            "sentinel": {
                "summary": "KQL equivalent for the AS-REP roast pattern.",
                "content": (
                    "SecurityEvent\n"
                    "| where EventID == 4768 and PreAuthType == \"0\"\n"
                    "| summarize Accounts=dcount(TargetAccount) by IpAddress,\n"
                    "            bin(TimeGenerated, 1h)\n"
                    "| where Accounts > 3"
                ),
            },
            "defender": {
                "summary": "MDI raises an AS-REP roasting alert on the same pattern.",
                "content": (
                    "MDI alert: 'Suspected AS-REP Roasting attempt'\n"
                    "Also audit accounts with DONT_REQ_PREAUTH set — that flag is the\n"
                    "root cause and should be near-zero in a healthy domain."
                ),
            },
        },
        "remediation": (
            "Remove 'Do not require Kerberos preauthentication' from all accounts; "
            "audit userAccountControl for DONT_REQ_PREAUTH; enforce strong passwords."
        ),
        "learning": (
            "AS-REP roasting is Kerberoasting's unauthenticated cousin: it needs no "
            "creds, only a username list, because preauth was disabled. Re-enabling "
            "preauth removes the free crackable ticket entirely."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API  (data-driven — never hard-codes a technique name)
# ═══════════════════════════════════════════════════════════════════════════

def _canon(name: str) -> str:
    """Normalise an operator-supplied name to a canonical technique key.

    Handles case, surrounding whitespace, spaces-vs-hyphens, and the alias
    table (e.g. 'PtH' or 'pass the hash' → 'pass-the-hash'). Returns the
    canonical key even if it is not present in TECHNIQUES, so the caller can
    distinguish 'unknown alias' from 'known-but-missing'.
    """
    if not name:
        return ""
    key = name.strip().lower()
    if key in _ALIASES:
        return _ALIASES[key]
    # Try the alias table again with hyphens collapsed to spaces and vice-versa.
    spaced = key.replace("-", " ")
    if spaced in _ALIASES:
        return _ALIASES[spaced]
    return key.replace(" ", "-")


def get_technique(name: str) -> Optional[Dict]:
    """Return the technique block for a name/alias, or None if unknown."""
    return TECHNIQUES.get(_canon(name))


def list_techniques() -> List[Dict]:
    """Return a lightweight catalogue for menus/UIs, sorted by name.

    Each item: {key, name, tactic, mitre} — enough to render a picker without
    shipping the whole (heavy) detection payload.
    """
    catalogue = []
    for key, t in TECHNIQUES.items():
        catalogue.append({
            "key":    key,
            "name":   t.get("name", key),
            "tactic": t.get("tactic", ""),
            "mitre":  [m["id"] for m in t.get("mitre", [])],
        })
    return sorted(catalogue, key=lambda x: x["name"].lower())


def get_detections_json(name: str, surface: Optional[str] = None) -> Dict:
    """Return detection artifacts as JSON-ready data for the frontend.

    With no `surface`, returns every detection surface for the technique.
    With a valid `surface` (e.g. 'sigma'), returns just that one. Unknown
    technique → {}. Unknown surface → {} (caller can check DETECTION_SURFACES).
    """
    t = get_technique(name)
    if not t:
        return {}
    detections = t.get("detections", {})
    if surface is None:
        return detections
    surface = surface.lower()
    if surface not in detections:
        return {}
    return {surface: detections[surface]}


def _opsec_footer(technique: Dict) -> List[str]:
    """Best-effort cross-link into soc_mentor's OPSEC layer for this technique.

    Lazy, guarded import keeps purple_team decoupled from soc_mentor: if the
    mentor module or the referenced topic is missing, we simply skip the
    footer rather than failing the whole render.
    """
    ref = technique.get("opsec_ref")
    if not ref:
        return []
    try:
        from src.core import soc_mentor
    except Exception:
        return []
    steps = soc_mentor.get_next_steps_json(ref)
    if not steps:
        return []
    lines = ["", "  🥷 OPSEC (via SOC mentor — quietest first):"]
    for step in steps[:3]:
        noise = str(step.get("noise", "?")).upper()
        lines.append(f"    [{noise:<6}] {step.get('tool', '?')}")
    return lines


def format_purple_block(name: str, surfaces: Optional[List[str]] = None) -> str:
    """Render a technique as a terminal-friendly purple-team lesson.

    `surfaces` optionally filters which detection surfaces to show (defaults to
    all, in DETECTION_SURFACES order). Returns a helpful message if the
    technique is unknown, so the CLI never prints an empty string.
    """
    t = get_technique(name)
    if not t:
        available = ", ".join(x["key"] for x in list_techniques())
        return (f"  No purple-team data for '{name}'.\n"
                f"  Available techniques: {available}")

    # Which surfaces to render, validated against what the technique actually has.
    have = t.get("detections", {})
    if surfaces:
        wanted = [s.lower() for s in surfaces if s.lower() in have]
    else:
        wanted = [s for s in DETECTION_SURFACES if s in have]

    out: List[str] = []
    bar = "═" * 62
    out.append(bar)
    out.append(f"  🟣 PURPLE TEAM — {t.get('name', name)}  [{t.get('tactic', '')}]")
    out.append(bar)

    mitre = t.get("mitre", [])
    if mitre:
        out.append("  MITRE ATT&CK: " + ", ".join(f"{m['id']} ({m['name']})" for m in mitre))

    atk = t.get("attack", {})
    if atk.get("summary"):
        out.append("")
        out.append("  ◤ RED — OFFENSE")
        for line in textwrap.wrap(atk["summary"], width=58):
            out.append(f"    {line}")
        for step in atk.get("steps", []):
            out.append(f"    $ {step['cmd']}")
            for line in textwrap.wrap(step.get("note", ""), width=54):
                out.append(f"        {line}")

    out.append("")
    out.append("  BLUE — DETECTION ◥")
    for surface in wanted:
        block = have[surface]
        out.append("")
        out.append(f"  ── {SURFACE_LABELS.get(surface, surface)} ──")
        if block.get("summary"):
            for line in textwrap.wrap(block["summary"], width=58):
                out.append(f"    {line}")
        content = block.get("content", "")
        for line in content.splitlines():
            out.append(f"      {line}")

    if t.get("remediation"):
        out.append("")
        out.append("  🛡  REMEDIATION")
        for line in textwrap.wrap(t["remediation"], width=58):
            out.append(f"    {line}")

    out.extend(_opsec_footer(t))
    out.append(bar)
    return "\n".join(out)


def technique_to_finding(name: str, target: str = "", evidence: str = "") -> Optional[Dict]:
    """Bridge a purple-team technique into a ReportGenerator-compatible finding.

    Emits a dict whose keys match reporting.report_generator.Finding so the
    technique can be dropped straight into a report (carrying its MITRE id,
    tactic, remediation, and the educational 'learning' note). Returns None
    for an unknown technique so the caller can skip it cleanly.
    """
    t = get_technique(name)
    if not t:
        return None
    mitre = t.get("mitre", [])
    primary = mitre[0] if mitre else {"id": "", "name": ""}
    atk = t.get("attack", {})
    return {
        "title":          f"{t.get('name', name)} exposure",
        "severity":       t.get("severity", "medium"),
        "description":    atk.get("summary", ""),
        "evidence":       evidence or (f"Technique validated against {target}." if target else
                                       "Validated in purple-team exercise; see detection artifacts."),
        "recommendation": t.get("remediation", ""),
        "plugin":         "purple_team",
        "mitre_id":       primary["id"],
        "mitre_tactic":   t.get("tactic", ""),
        "learning":       t.get("learning", ""),
    }
