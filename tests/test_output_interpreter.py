"""
Tests for src/core/output_interpreter.py — the loop-closing interpreter.

Covers tool detection, each parser, the meaning layer, and the decorated
next-step recommendations (anatomy + opsec + detection). Deterministic and
offline — these tests must never touch the network (the interpreter uses
next_step_engine's rule halves, never its Ollama fallback).

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.core import output_interpreter as oi


NMAP = """Nmap scan report for 10.0.0.10
Host is up (0.0011s latency).
PORT     STATE SERVICE       VERSION
22/tcp   open  ssh           OpenSSH 8.2
445/tcp  open  microsoft-ds  Samba smbd 4.6.2
139/tcp  closed netbios-ssn
88/tcp   open  kerberos-sec  Microsoft Windows Kerberos"""

NXC_ADMIN = r"SMB   10.0.0.15   445   DC01   [+] corp.local\jdoe:Autumn2025! (Pwn3d!)"
NXC_FAIL  = r"SMB   10.0.0.16   445   WS02   [-] corp.local\jdoe:wrongpass STATUS_LOGON_FAILURE"
NXC_HASH  = r"SMB   10.0.0.17   445   WS03   [+] corp.local\adm:aad3b435b51404eeaad3b435b51404ee (Pwn3d!)"
HYDRA     = "[22][ssh] host: 10.0.0.5   login: admin   password: hunter2"
HASHCAT   = "9f4e1b7c0a2d3e4f5061728394a5b6c7:Summer2024!"
GOBUSTER  = "/admin                (Status: 301) [Size: 312]\n/login.php            (Status: 200) [Size: 1240]"


# ── Detection ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,tool", [
    (NMAP, "nmap"), (NXC_ADMIN, "nxc"), (HYDRA, "hydra"),
    (GOBUSTER, "gobuster"),
])
def test_detect_tool(text, tool):
    assert oi.detect_tool(text) == tool


def test_detect_unknown():
    assert oi.detect_tool("just some random text") is None


# ── Parsers ─────────────────────────────────────────────────────────────────

def test_parse_nmap_open_only():
    fs = oi.parse_nmap(NMAP)
    ports = {f.detail["port"] for f in fs}
    assert ports == {"22", "445", "88"}      # 139 was closed → excluded
    assert all(f.kind == "open_port" for f in fs)


def test_parse_nxc_success_only_and_admin():
    assert oi.parse_nxc(NXC_FAIL) == []      # '[-]' ignored
    fs = oi.parse_nxc(NXC_ADMIN)
    assert len(fs) == 1
    d = fs[0].detail
    assert d["admin"] is True and d["user"] == r"corp.local\jdoe"
    assert d["secret"] == "Autumn2025!" and d["is_hash"] is False


def test_parse_nxc_detects_hash():
    d = oi.parse_nxc(NXC_HASH)[0].detail
    assert d["is_hash"] is True


def test_parse_hydra_and_hashcat_and_gobuster():
    assert oi.parse_hydra(HYDRA)[0].detail["secret"] == "hunter2"
    assert oi.parse_hashcat(HASHCAT)[0].detail["secret"] == "Summer2024!"
    paths = {f.value for f in oi.parse_gobuster(GOBUSTER)}
    assert paths == {"/admin", "/login.php"}


# ── Meaning layer ───────────────────────────────────────────────────────────

def test_meaning_maps_services():
    d = oi.interpret(NMAP)
    by_port = {f["detail"]["port"]: f["meaning"] for f in d["findings"]}
    assert "Domain Controller" in by_port["88"]
    assert "SMB" in by_port["445"]


# ── Recommendations: reuse + decorate ───────────────────────────────────────

def test_nmap_recommends_with_anatomy_and_opsec():
    d = oi.interpret(NMAP)
    assert d["next_steps"], "should recommend follow-ups for open ports"
    step = d["next_steps"][0]
    assert step["command"] and step["why"]
    assert step["anatomy"].get("tool")            # anatomy attached
    # at least one step carries an OPSEC tip from soc_mentor
    assert any(s.get("opsec") for s in d["next_steps"])


def test_cred_admin_triggers_secretsdump_and_detection():
    d = oi.interpret(NXC_ADMIN)
    cmds = " ".join(s["command"] for s in d["next_steps"])
    assert "secretsdump" in cmds and "bloodhound-python" in cmds
    assert any(s.get("detection") for s in d["next_steps"])


def test_cred_hash_uses_H_flag():
    d = oi.interpret(NXC_HASH)
    share_step = next(s for s in d["next_steps"] if "--shares" in s["command"])
    assert "-H " in share_step["command"]         # pass-the-hash, not -p


# ── Safety / edge cases ─────────────────────────────────────────────────────

def test_empty_and_unknown_are_safe():
    d = oi.interpret("")
    assert d["tool"] is None and d["findings"] == []
    d2 = oi.interpret("random noise with no tool signature")
    assert "Could not identify" in d2["summary"]


def test_format_renders_full_briefing():
    out = oi.format_interpretation(NMAP)
    assert "ERR0RS READS THE OUTPUT" in out
    assert "WHAT I SEE" in out and "DO THIS NEXT" in out


def test_explicit_tool_hint_overrides_detection():
    # Give raw creds text but force the nxc parser via hint.
    d = oi.interpret(NXC_ADMIN, tool="nxc")
    assert d["tool"] == "nxc" and d["findings"]
