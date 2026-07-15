"""
Tests for src/core/command_anatomy.py — the command-breakdown engine.

Covers: the flagship msfconsole -x recursion, flag resolution + honest
fallback, argument classification, is_command gating, malformed input
safety, and the JSON shape. Pure-stdlib module — no network/deps.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.core import command_anatomy as ca


# ── The flagship: msfconsole -x recursion ───────────────────────────────────

MSF_CMD = ('msfconsole -q -x "use exploit/windows/smb/ms17_010_eternalblue; '
           'set RHOSTS 10.0.0.5; set LHOST tun0; run"')


def test_msf_breaks_into_flags_and_payload():
    d = ca.explain_command(MSF_CMD)
    assert d["tool"] == "msfconsole"
    tokens = [p["token"] for p in d["parts"]]
    assert "-q" in tokens and "-x" in tokens
    xpart = next(p for p in d["parts"] if p["token"] == "-x")
    assert "sub" in xpart and len(xpart["sub"]) == 4  # use, set, set, run


def test_msf_use_explains_local_namespace_walk():
    d = ca.explain_command(MSF_CMD)
    xpart = next(p for p in d["parts"] if p["token"] == "-x")
    use = xpart["sub"][0]
    assert use["verb"] == "use"
    # The teaching point: loading is local, target untouched.
    assert "YOUR OWN" in use["operand_note"] or "arms Metasploit" in use["operand_note"]


def test_msf_rhosts_is_target_lhost_is_callback():
    d = ca.explain_command(MSF_CMD)
    sub = next(p for p in d["parts"] if p["token"] == "-x")["sub"]
    rhosts = next(s for s in sub if s.get("operand", "").upper().startswith("RHOSTS"))
    lhost  = next(s for s in sub if s.get("operand", "").upper().startswith("LHOST"))
    assert "TARGET" in rhosts["operand_note"].upper()
    assert "call" in lhost["operand_note"].lower() or "you" in lhost["operand_note"].lower()


def test_msf_plain_english_reflects_this_command():
    d = ca.explain_command(MSF_CMD)
    pe = d["plain_english"]
    assert "ms17_010_eternalblue" in pe
    assert "10.0.0.5" in pe
    assert "tun0" in pe


# ── Flag resolution + honesty ───────────────────────────────────────────────

def test_known_flag_has_what_and_why():
    d = ca.explain_command("nmap -sS -p- 10.0.0.5")
    ss = next(p for p in d["parts"] if p["token"] == "-sS")
    assert ss["what"] and ss["why"]
    assert "SYN" in ss["what"] or "SYN" in ss["why"]


def test_unknown_flag_is_not_faked():
    d = ca.explain_command("nmap -zZ 10.0.0.5")
    zz = next(p for p in d["parts"] if p["token"] == "-zZ")
    assert "not in the local knowledge base" in zz["what"]
    assert "--help" in zz["why"] or "man " in zz["why"]


def test_value_taking_flag_consumes_next_token():
    d = ca.explain_command("hydra -l admin -P rockyou.txt ssh://10.0.0.5")
    lflag = next(p for p in d["parts"] if p["token"] == "-l")
    assert lflag.get("value") == "admin"
    # -P value is a wordlist → classified in value_note
    pflag = next(p for p in d["parts"] if p["token"] == "-P")
    assert "wordlist" in (pflag.get("value_note") or "").lower()


# ── Argument classification ─────────────────────────────────────────────────

@pytest.mark.parametrize("token,role", [
    ("10.0.0.5", "target-host"),
    ("10.0.0.0/24", "target-range"),
    ("http://site/app", "target-url"),
    ("wlan0", "interface"),
    ("rockyou.txt", "wordlist"),
])
def test_arg_classifier(token, role):
    assert ca._classify_arg(token)["role"] == role


# ── Subcommands (gobuster dir/dns) ──────────────────────────────────────────

def test_subcommand_recognised():
    d = ca.explain_command("gobuster dir -u http://x -w list.txt")
    first = d["parts"][0]
    assert first["role"] == "subcommand" and first["token"] == "dir"


# ── is_command gating ───────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("nmap", False),                    # bare tool → lesson, not anatomy
    ("nmap -sV 10.0.0.5", True),
    ("teach me sql injection", False),
    ("msfconsole -q -x 'run'", True),
    ("", False),
])
def test_is_command(text, expected):
    assert ca.is_command(text) is expected


# ── Safety ──────────────────────────────────────────────────────────────────

def test_malformed_quotes_do_not_raise():
    d = ca.explain_command('curl -H "unterminated')
    assert d["tool"] == "curl"  # falls back to naive split, still works


def test_empty_is_safe():
    d = ca.explain_command("")
    assert d["tool"] == "" and d["parts"] == []


def test_format_anatomy_renders():
    out = ca.format_anatomy(MSF_CMD)
    assert "COMMAND ANATOMY" in out
    assert "ms17_010_eternalblue" in out
    assert "In plain English" in out


def test_anatomy_json_shape():
    d = ca.anatomy_json("nmap -sV 10.0.0.5")
    assert set(d) >= {"command", "tool", "tool_summary", "parts", "plain_english"}
