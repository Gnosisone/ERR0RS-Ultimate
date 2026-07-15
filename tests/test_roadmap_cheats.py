"""
Tests for the learning roadmap + cheat sheets and their teach-engine routing.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.education_new import roadmap as rm
from src.education_new import cheatsheets as cs
from src.education_new.teach_engine import handle_teach_request


# ── Roadmap ─────────────────────────────────────────────────────────────────

def test_roadmap_is_ordered_and_complete():
    r = rm.get_roadmap()
    assert [s["n"] for s in r] == list(range(1, len(r) + 1))
    for s in r:
        assert s["name"] and s["why"] and s["topics"] and s["gate"]


def test_get_stage_by_number_and_name():
    assert rm.get_stage(5)["name"] == "Active Directory"
    assert rm.get_stage("active directory")["n"] == 5
    assert rm.get_stage("4")["name"] == "Web"


def test_get_stage_bad_ref():
    assert rm.get_stage(99) is None
    assert rm.get_stage("nonsense") is None


def test_next_stage():
    assert rm.next_stage("web")["name"] == "Active Directory"
    assert rm.next_stage(len(rm.get_roadmap())) is None  # summit → None


def test_format_roadmap_highlights_current():
    out = rm.format_roadmap(highlight="web")
    assert "LEARNING ROADMAP" in out
    assert "▶  4. Web" in out          # current
    assert "✓  1. Networking" in out    # completed


def test_format_stage_has_reasoning():
    out = rm.format_stage(rm.get_stage(5))
    assert "WHY HERE" in out and "READY WHEN" in out


# ── Cheat sheets ────────────────────────────────────────────────────────────

def test_every_cheat_has_all_fields():
    for c in cs.CHEATS:
        for k in ("cat", "cmd", "purpose", "ex", "out", "mistake"):
            assert c.get(k), f"{c.get('cmd')} missing {k}"


def test_get_by_category_and_search():
    assert len(cs.get_cheats("Kerberos")) >= 2
    assert cs.get_cheats("NoSuchCat") == []
    hits = cs.search_cheats("hash")
    assert hits and all("hash" in (c["cmd"] + c["purpose"] + c["ex"] + c["mistake"]).lower()
                        for c in hits)


def test_search_empty_returns_all():
    assert len(cs.search_cheats("")) == len(cs.CHEATS)


def test_format_cheats_renders_and_empty():
    assert "CHEAT SHEET" in cs.format_cheats(cs.get_cheats("Nmap"))
    assert "No matching" in cs.format_cheats([])


# ── Teach-engine routing ────────────────────────────────────────────────────

def test_teach_routes_roadmap():
    r = handle_teach_request("show me the roadmap")
    assert r["source"] == "errz_roadmap" and "LEARNING ROADMAP" in r["stdout"]


def test_teach_routes_roadmap_stage():
    r = handle_teach_request("roadmap active directory")
    assert r["source"] == "errz_roadmap" and "ACTIVE DIRECTORY" in r["stdout"].upper()


def test_teach_routes_cheatsheet():
    r = handle_teach_request("kerberos cheatsheet")
    assert r["source"] == "errz_cheats" and "CHEAT SHEET" in r["stdout"]


def test_teach_still_routes_normal_lesson():
    # Ensure roadmap/cheat keywords didn't cannibalise ordinary lessons.
    r = handle_teach_request("nmap")
    assert r["source"] == "errz_builtin"
