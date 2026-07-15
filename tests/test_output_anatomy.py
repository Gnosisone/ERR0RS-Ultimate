"""
Tests for src/core/output_anatomy.py (results literacy) and its wiring into
the teach engine as a lesson FOLLOW-UP.

The load-bearing test is test_lesson_carries_output_followup: a lesson that
teaches how to RUN a tool must now also teach how to READ its output — that
was the gap this layer closes.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.core import output_anatomy as oa
from src.education_new.teach_engine import handle_teach_request


# ── Lookup + aliases ────────────────────────────────────────────────────────

def test_list_and_has():
    tools = oa.list_output_lessons()
    assert {"nmap", "nxc", "hydra", "hashcat", "gobuster", "sqlmap"} <= set(tools)
    assert oa.has_output_lesson("nmap")
    assert not oa.has_output_lesson("not-a-tool")


def test_alias_resolves():
    assert oa.has_output_lesson("netexec")             # → nxc
    assert oa.get_output_lesson("crackmapexec")["tool"] == "nxc (NetExec)"


# ── Content integrity ───────────────────────────────────────────────────────

def test_every_lesson_is_well_formed():
    for tool, lesson in oa.OUTPUT_LESSONS.items():
        assert lesson.get("headline") and lesson.get("sample")
        assert lesson.get("reading"), f"{tool} has no line-by-line reading"
        for r in lesson["reading"]:
            assert r.get("field") and r.get("means") and r.get("do"), \
                f"{tool} reading row missing field/means/do"
        assert lesson.get("misreads"), f"{tool} has no common-misreads"


def test_reading_teaches_meaning_and_action():
    """Each reading row must explain the value AND the decision it drives."""
    nmap = oa.get_output_lesson("nmap")
    fields = {r["field"] for r in nmap["reading"]}
    assert any("filtered" in f for f in fields)   # the classic misread is taught
    assert any("VERSION" in f for f in fields)    # version→CVE pivot is taught


# ── Rendering ───────────────────────────────────────────────────────────────

def test_format_full_and_compact():
    full = oa.format_output_lesson("nmap")
    assert "READING THE RESULTS" in full
    assert "COMMON MISREADS" in full
    assert "port STATES" in full                  # reference table present
    compact = oa.format_output_lesson("nmap", compact=True)
    assert "READING THE RESULTS" in compact
    assert "port STATES" not in compact           # reference trimmed in compact


def test_format_unknown_is_helpful():
    out = oa.format_output_lesson("nope")
    assert "No results-literacy lesson" in out and "Available" in out


# ── Wiring: the follow-up (the whole point) ─────────────────────────────────

def test_lesson_carries_output_followup():
    """A normal tool lesson must now append the results-literacy follow-up."""
    r = handle_teach_request("nmap")
    assert r["source"] == "errz_builtin"
    assert "READING THE RESULTS" in r["stdout"], \
        "the lesson no longer teaches how to read the output"


def test_direct_results_query_routes_to_full_lesson():
    r = handle_teach_request("how do I read nmap output")
    assert r["source"] == "errz_output"
    assert "READING THE RESULTS" in r["stdout"]
    assert "port STATES" in r["stdout"]           # full (not compact)


def test_non_output_lesson_has_no_followup():
    """A tool without an output lesson shouldn't gain a spurious follow-up."""
    r = handle_teach_request("sql injection")     # a concept lesson, no output lesson
    assert "READING THE RESULTS" not in r["stdout"]
