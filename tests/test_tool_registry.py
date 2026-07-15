"""
Tests for src/core/tool_registry.py — the unified tool knowledge graph.

The load-bearing test is test_duplicated_flags_resolve_to_single_owner: it
enforces that any flag defined in more than one source resolves — through the
registry — to exactly ONE canonical definition. That's what makes "defined
once" a guarantee instead of a hope, and it will fail loudly if a future edit
introduces a divergent duplicate.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import pytest

from src.core import tool_registry as tr


# ── Aggregation ─────────────────────────────────────────────────────────────

def test_get_tool_aggregates_sources():
    nmap = tr.get_tool("nmap")
    assert nmap is not None
    # nmap has data in lessons, mentor, flag_kb, cheats, summaries
    assert {"lessons", "mentor", "flag_kb"} <= set(nmap.sources)
    assert nmap.summary and nmap.flags and nmap.opsec


def test_unknown_tool_is_none():
    assert tr.get_tool("definitely-not-a-tool") is None
    assert tr.get_tool("") is None


# ── Alias resolution (centralised) ──────────────────────────────────────────

@pytest.mark.parametrize("alias,canon", [
    ("netexec", "nxc"), ("crackmapexec", "nxc"), ("cme", "nxc"),
    ("bloodhound-python", "bloodhound"), ("impacket-secretsdump", "secretsdump"),
])
def test_alias_resolution(alias, canon):
    assert tr._canon(alias) == canon


def test_alias_get_tool():
    assert tr.get_tool("netexec").name == "nxc"


# ── The single-source-of-truth guarantee ────────────────────────────────────

def test_duplicated_flags_resolve_to_single_owner():
    """For EVERY flag defined in both LESSONS and FLAG_KB, the registry must
    resolve it to the canonical (flag_kb) definition — one answer, not two."""
    drift = tr.find_drift()
    assert drift["duplicated_flags"], "expected known duplication to be present"
    for tool, flags in drift["duplicated_flags"].items():
        tk = tr.get_tool(tool)
        for f in flags:
            assert tk.flags[f]["source"] == "flag_kb", \
                f"{tool} {f} did not resolve to the canonical owner"
            # canonical owner must be complete (non-empty what + why)
            assert tk.flags[f]["what"] and tk.flags[f]["why"]


def test_find_drift_shape():
    d = tr.find_drift()
    assert set(d) == {"duplicated_flags", "num_duplicated_flags",
                      "coverage", "total_entries"}
    assert d["num_duplicated_flags"] == sum(len(v) for v in d["duplicated_flags"].values())
    assert d["total_entries"] == len(d["coverage"])


# ── Catalogue ───────────────────────────────────────────────────────────────

def test_list_tools_covers_union():
    tools = set(tr.list_tools())
    from src.education_new.teach_engine import LESSONS
    from src.core.command_anatomy import FLAG_KB
    assert set(FLAG_KB) <= tools           # every FLAG_KB tool present
    assert "nmap" in tools and "nxc" in tools


# ── RAG serialisation (the #3 hook) ─────────────────────────────────────────

def test_to_rag_documents():
    docs = tr.to_rag_documents()
    assert docs and all({"id", "tool", "text", "sources"} <= set(d) for d in docs)
    nmap = next(d for d in docs if d["tool"] == "nmap")
    assert nmap["id"] == "tool:nmap"
    assert "Flags:" in nmap["text"] and "OpSec:" in nmap["text"]
    # ground-truth text must carry real syntax, e.g. a known nmap flag
    assert "-sV" in nmap["text"]


# ── Render ──────────────────────────────────────────────────────────────────

def test_format_tool():
    out = tr.format_tool("nmap")
    assert "TOOL DOSSIER" in out and "FLAGS:" in out
    assert "No knowledge" in tr.format_tool("bogus-xyz")


def test_tool_json_roundtrip():
    j = tr.tool_json("nxc")
    assert j["name"] == "nxc" and isinstance(j["flags"], dict)
