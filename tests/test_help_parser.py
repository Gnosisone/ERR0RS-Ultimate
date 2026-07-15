"""
Tests for src/core/help_parser.py — the --help/man long-tail fallback.

The parser is tested purely (sample help text, no subprocess). The safety
gate and a single real-tool integration are tested against the environment,
skipping gracefully when the tool isn't installed.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import shutil
import pytest

from src.core import help_parser as hp


# ── Pure parser across the three common help layouts ────────────────────────

NMAP_STYLE = """
  -iL <inputfilename>: Input from list of hosts/networks
  -sn: Ping Scan - disable port scan
  --min-rate <number>: Send packets no slower than <number> per second
"""

GOBUSTER_STYLE = """
   --url value, -u value        The target URL
   --wordlist value, -w value   Path to the wordlist
   --follow-redirect, -r        Follow redirects (default: false)
"""

CURL_STYLE = """
 -d, --data <data>            HTTP POST data
 -H, --header <header/@file>  Pass custom header(s) to server
 -k, --insecure               Allow insecure server connections
"""


def test_parse_nmap_style():
    f = hp.parse_help_text(NMAP_STYLE)
    assert f["-iL"] == "Input from list of hosts/networks"
    assert f["-sn"].startswith("Ping Scan")
    assert "--min-rate" in f


def test_parse_gobuster_style_shares_desc_across_flags():
    f = hp.parse_help_text(GOBUSTER_STYLE)
    assert f["--url"] == "The target URL" and f["-u"] == "The target URL"
    assert f["-r"].startswith("Follow redirects")   # default clause trimmed


def test_parse_curl_style_short_and_long():
    f = hp.parse_help_text(CURL_STYLE)
    assert f["-d"] == "HTTP POST data" and f["--data"] == "HTTP POST data"
    assert f["-k"].startswith("Allow insecure")


def test_parse_ignores_non_flag_lines():
    f = hp.parse_help_text("Usage: tool [options]\nDescription here\n\n  -v: verbose")
    assert list(f) == ["-v"]


def test_long_description_is_capped():
    long = "  --x: " + "word " * 60
    f = hp.parse_help_text(long)
    assert len(f["--x"]) <= 141 and f["--x"].endswith("…")


# ── Safety gate ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("bad", [
    "nmap; rm -rf /", "../../bin/sh", "tool with spaces", "a|b", "$(evil)", "",
])
def test_unsafe_tool_names_never_run(bad):
    hp._reset_cache()
    assert hp._run_help(bad) == ""


def test_nonexistent_tool_returns_empty():
    hp._reset_cache()
    assert hp._run_help("definitely-not-installed-xyz123") == ""


# ── Caching ─────────────────────────────────────────────────────────────────

def test_flag_map_is_cached(monkeypatch):
    calls = {"n": 0}
    def fake_run(tool):
        calls["n"] += 1
        return NMAP_STYLE
    hp._reset_cache()
    monkeypatch.setattr(hp, "_run_help", fake_run)
    hp._flag_map("faketool")
    hp._flag_map("faketool")
    assert calls["n"] == 1   # second call served from cache


# ── Real-tool integration (skips if the tool isn't installed) ───────────────

@pytest.mark.skipif(not shutil.which("nmap"), reason="nmap not installed")
def test_real_nmap_help_resolves_a_long_tail_flag():
    hp._reset_cache()
    assert hp.flag_help("nmap", "-iL")   # a real flag not in the hand-curated KB


@pytest.mark.skipif(not shutil.which("nmap"), reason="nmap not installed")
def test_command_anatomy_use_help_integration():
    from src.core import command_anatomy as ca
    d = ca.explain_command("nmap -iL hosts.txt 10.0.0.5", use_help=True)
    il = next(p for p in d["parts"] if p["token"] == "-iL")
    assert "list" in il["what"].lower() and "--help" in il["why"]
    # default (no use_help) must stay pure/unknown
    d2 = ca.explain_command("nmap -iL hosts.txt 10.0.0.5")
    il2 = next(p for p in d2["parts"] if p["token"] == "-iL")
    assert "not in the local knowledge base" in il2["what"]
