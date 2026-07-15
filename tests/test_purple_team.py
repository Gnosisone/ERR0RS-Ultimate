"""
Tests for src/security/purple_team.py — the Purple Team Playground.

Covers: name/alias normalisation, catalogue integrity, detection-surface
retrieval, terminal rendering, the ReportGenerator finding-bridge, and the
guarded soc_mentor OPSEC cross-link. Pure-stdlib module, so no network or
heavy deps are required to run these.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.security import purple_team as pt


# ── Normalisation / lookup ──────────────────────────────────────────────────

@pytest.mark.parametrize("alias,expected", [
    ("PtH", "pass-the-hash"),
    ("pass the hash", "pass-the-hash"),
    ("pass-the-hash", "pass-the-hash"),
    ("Kerberoast", "kerberoasting"),
    ("asrep", "asrep-roasting"),
    ("AS-REP Roasting", "asrep-roasting"),
])
def test_canon_resolves_aliases(alias, expected):
    assert pt._canon(alias) == expected


def test_canon_empty_is_safe():
    assert pt._canon("") == ""
    assert pt._canon(None) == ""  # type: ignore[arg-type]


def test_get_technique_known_and_unknown():
    assert pt.get_technique("pth")["name"] == "Pass-the-Hash"
    assert pt.get_technique("does-not-exist") is None


# ── Catalogue integrity ─────────────────────────────────────────────────────

def test_catalogue_is_sorted_and_complete():
    cat = pt.list_techniques()
    assert [c["key"] for c in cat] == sorted(TECH_KEYS)
    for c in cat:
        assert c["name"] and c["tactic"] and c["mitre"]


def test_every_technique_has_required_fields():
    for key, t in pt.TECHNIQUES.items():
        assert t.get("name"), f"{key} missing name"
        assert t.get("severity") in {"critical", "high", "medium", "low", "info"}
        assert t.get("mitre"), f"{key} missing mitre"
        assert t.get("detections"), f"{key} missing detections"
        # Every declared detection surface must be a known surface.
        for surface in t["detections"]:
            assert surface in pt.DETECTION_SURFACES, f"{key}: bad surface {surface}"


TECH_KEYS = ["pass-the-hash", "kerberoasting", "asrep-roasting"]


# ── Detection retrieval ─────────────────────────────────────────────────────

def test_detections_all_and_single():
    alld = pt.get_detections_json("pth")
    assert set(alld) <= set(pt.DETECTION_SURFACES)
    assert "sigma" in alld
    one = pt.get_detections_json("pth", "sigma")
    assert list(one) == ["sigma"]
    assert one["sigma"]["content"].strip().startswith("title:")


def test_detections_bogus_surface_and_technique():
    assert pt.get_detections_json("pth", "bogus") == {}
    assert pt.get_detections_json("nope") == {}


# ── Terminal rendering ──────────────────────────────────────────────────────

def test_format_block_known():
    out = pt.format_purple_block("pass-the-hash")
    assert "PURPLE TEAM" in out
    assert "T1550.002" in out
    assert "Sigma" in out and "Splunk" in out
    assert "RED — OFFENSE" in out and "BLUE — DETECTION" in out


def test_format_block_unknown_is_helpful():
    out = pt.format_purple_block("totally-fake")
    assert "No purple-team data" in out
    assert "Available techniques" in out


def test_format_block_surface_filter():
    out = pt.format_purple_block("pth", surfaces=["sigma"])
    assert "Sigma" in out
    assert "Splunk SPL" not in out  # filtered out


# ── ReportGenerator bridge ──────────────────────────────────────────────────

def test_technique_to_finding_schema():
    f = pt.technique_to_finding("pth", target="10.0.0.15")
    for key in ("title", "severity", "description", "evidence",
                "recommendation", "plugin", "mitre_id", "mitre_tactic", "learning"):
        assert key in f
    assert f["mitre_id"] == "T1550.002"
    assert f["plugin"] == "purple_team"
    assert f["severity"] == "high"


def test_technique_to_finding_unknown_is_none():
    assert pt.technique_to_finding("nope") is None


def test_finding_bridges_into_real_reportgenerator():
    """The bridge dict must construct a valid ReportGenerator Finding and
    survive full Markdown generation with MITRE + learning intact."""
    from src.reporting.report_generator import ReportGenerator

    class MockMem:
        def get_findings(self):
            return [pt.technique_to_finding("pass-the-hash", target="10.0.0.15"),
                    pt.technique_to_finding("asrep-roasting", target="dc01")]
        targets = ["10.0.0.15", "dc01"]

    rg = ReportGenerator(memory=MockMem(), report_dir="/tmp/pt_test")
    report = rg.generate(target="10.0.0.15")
    assert report["stats"]["high"] == 2
    md = rg._format_markdown(report)
    assert "Pass-the-Hash exposure" in md
    assert "attack.mitre.org" in md      # MITRE link rendered
    assert "Learn:" in md                # learning note rendered


# ── OPSEC cross-link (guarded) ──────────────────────────────────────────────

def test_opsec_footer_present_when_ref_exists():
    """kerberoasting.opsec_ref='bloodhound' exists in soc_mentor.MENTOR."""
    out = pt.format_purple_block("kerberoasting")
    assert "OPSEC" in out
