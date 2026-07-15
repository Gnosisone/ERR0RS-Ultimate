#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — UNIFIED TOOL KNOWLEDGE REGISTRY         ║
║              src/core/tool_registry.py                            ║
║                                                                  ║
║  One place to ask "what do we know about <tool>?" — aggregating  ║
║  the five deterministic knowledge sources that grew up           ║
║  separately:                                                     ║
║    • teach_engine.LESSONS      → what / how / commands / tips    ║
║    • soc_mentor.MENTOR         → opsec / noise / next-steps      ║
║    • command_anatomy.FLAG_KB   → flags (what / why / takes-arg)  ║
║    • cheatsheets.CHEATS        → quick reference rows            ║
║    • purple_team.TECHNIQUES    → related detection techniques    ║
║                                                                  ║
║  This does NOT duplicate those sources — it assigns each FIELD   ║
║  a single canonical OWNER and merges. Where two sources overlap  ║
║  (flags live in both FLAG_KB and LESSONS), FLAG_KB wins because  ║
║  it is richer, so every read resolves to one definition. The     ║
║  drift detector (find_drift) makes any remaining duplication     ║
║  visible and testable, so "defined once" is enforced, not just   ║
║  hoped for. to_rag_documents() serialises the whole graph as     ║
║  ground truth for the RAG layer.                                 ║
║                                                                  ║
║  Lazy + guarded: a missing source degrades a field, never the    ║
║  whole registry. Pure stdlib.                                    ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

# One place for tool-name aliases (previously scattered across modules).
ALIASES = {
    "netexec": "nxc", "crackmapexec": "nxc", "cme": "nxc",
    "bloodhound-python": "bloodhound", "bloodhound.py": "bloodhound",
    "impacket-secretsdump": "secretsdump", "impacket-getnpusers": "getnpusers",
    "impacket-getuserspns": "getuserspns", "impacket-psexec": "psexec",
    "john the ripper": "john",
}

# Cheat-sheet category → canonical tool name, so cheats attach to the right tool.
_CHEAT_CAT_TO_TOOL = {
    "nmap": "nmap", "netexec": "nxc", "metasploit": "metasploit",
    "hashcat": "hashcat", "hydra": "hydra", "kerberos": "kerberos",
    "ldap": "ldap", "ad": "active directory", "sqlmap": "sqlmap",
    "wireshark": "wireshark", "powershell": "powershell", "linux": "linux",
    "windows": "windows", "docker": "docker", "kubernetes": "kubernetes",
}


def _canon(name: str) -> str:
    """Normalise a tool name: strip path, lowercase, resolve aliases."""
    if not name:
        return ""
    n = name.split("/")[-1].strip().lower()
    return ALIASES.get(n, n)


# ── Guarded source loaders (each returns {} / None on failure) ──────────────

def _lessons() -> Dict:
    try:
        from src.education_new.teach_engine import LESSONS
        return LESSONS
    except Exception:
        return {}


def _mentor(name: str) -> Optional[Dict]:
    try:
        from src.core import soc_mentor
        return soc_mentor.get_mentor(name)
    except Exception:
        return None


def _flag_kb() -> Dict:
    try:
        from src.core.command_anatomy import FLAG_KB
        return FLAG_KB
    except Exception:
        return {}


def _tool_summaries() -> Dict:
    try:
        from src.core.command_anatomy import TOOL_SUMMARIES
        return TOOL_SUMMARIES
    except Exception:
        return {}


def _cheats_for(name: str) -> List[Dict]:
    try:
        from src.education_new import cheatsheets
    except Exception:
        return []
    # Map any cheat category that canonicalises to this tool.
    out = []
    for cat, tool in _CHEAT_CAT_TO_TOOL.items():
        if tool == name:
            out.extend(cheatsheets.get_cheats(cat))
    return out


def _related_techniques(name: str) -> List[str]:
    """Purple techniques whose name/alias matches this tool/topic (best effort)."""
    try:
        from src.security import purple_team
    except Exception:
        return []
    if purple_team.get_technique(name):
        return [purple_team.get_technique(name)["name"]]
    return []


def _has_output_lesson(name: str) -> bool:
    """True if output_anatomy has a results-literacy lesson for this tool."""
    try:
        from src.core import output_anatomy
        return output_anatomy.has_output_lesson(name)
    except Exception:
        return False


def _output_rag_text(name: str) -> str:
    """Compact 'how to read the output' text, for RAG grounding on results."""
    try:
        from src.core import output_anatomy
        lesson = output_anatomy.get_output_lesson(name)
    except Exception:
        lesson = None
    if not lesson:
        return ""
    bits = [lesson.get("headline", "")]
    for r in lesson.get("reading", [])[:6]:
        bits.append(f"{r['field']} means {r['means']} Do: {r['do']}")
    for m in lesson.get("misreads", []):
        bits.append("Misread: " + m)
    return " ".join(b for b in bits if b)


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED VIEW
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolKnowledge:
    name: str
    summary: str = ""
    what: str = ""
    how: str = ""
    flags: Dict[str, Dict] = field(default_factory=dict)   # flag -> {what,why,arg,source}
    commands: Dict[str, str] = field(default_factory=dict)
    tips: List[str] = field(default_factory=list)
    opsec: List[str] = field(default_factory=list)
    noise: str = ""
    next_steps: List[Dict] = field(default_factory=list)
    cheats: List[Dict] = field(default_factory=list)
    related_techniques: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)


def _merge_flags(name: str, lesson: Dict) -> Dict[str, Dict]:
    """Merge flag knowledge with a single canonical resolution per flag:
    LESSONS flags first (shallow), then FLAG_KB overrides (rich) — so any flag
    defined in both resolves to exactly ONE definition (FLAG_KB's)."""
    flags: Dict[str, Dict] = {}
    for f, desc in (lesson.get("flags") or {}).items():
        flags[f] = {"what": desc, "why": "", "arg": False, "source": "lessons"}
    for f, info in (_flag_kb().get(name) or {}).items():
        flags[f] = {"what": info.get("what", ""), "why": info.get("why", ""),
                    "arg": info.get("arg", False), "source": "flag_kb"}
    return flags


def get_tool(name: str) -> Optional[ToolKnowledge]:
    """Unified knowledge for a tool, or None if NO source knows it."""
    name = _canon(name)
    if not name:
        return None
    lessons = _lessons()
    lesson = lessons.get(name, {})
    mentor = _mentor(name) or {}
    summaries = _tool_summaries()
    cheats = _cheats_for(name)
    techniques = _related_techniques(name)

    sources = []
    if lesson:            sources.append("lessons")
    if mentor:            sources.append("mentor")
    if name in _flag_kb(): sources.append("flag_kb")
    if cheats:            sources.append("cheats")
    if name in summaries: sources.append("summaries")
    if techniques:        sources.append("purple")

    if not sources:
        return None

    summary = (summaries.get(name)
               or lesson.get("tldr")
               or mentor.get("tldr")
               or lesson.get("title", name))

    return ToolKnowledge(
        name=name,
        summary=summary,
        what=lesson.get("what", ""),
        how=lesson.get("how", ""),
        flags=_merge_flags(name, lesson),
        commands=lesson.get("commands", {}) or {},
        tips=lesson.get("tips", []) or [],
        opsec=mentor.get("opsec_tips", []) or [],
        noise=mentor.get("noise_level", ""),
        next_steps=mentor.get("logical_next", []) or [],
        cheats=cheats,
        related_techniques=techniques,
        sources=sources,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CATALOGUE + RENDER + DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

def list_tools() -> List[str]:
    """Every knowledge key across all sources (canonicalised, de-duped, sorted).

    Includes topics/tactics as well as tools — the registry is a knowledge
    graph, not only a tool list; callers can filter on `.sources` if needed.
    """
    keys = set()
    keys |= set(_lessons())
    keys |= set(_flag_kb())
    keys |= set(_tool_summaries())
    try:
        from src.core import soc_mentor
        keys |= set(soc_mentor.MENTOR)
    except Exception:
        pass
    # Canonicalise INSIDE the set so aliases (netexec/crackmapexec → nxc,
    # bloodhound-python → bloodhound) collapse to one entry — otherwise
    # distinct raw keys yield duplicate canon names (and duplicate RAG ids).
    return sorted({_canon(k) for k in keys})


def tool_json(name: str) -> Optional[Dict]:
    """Unified knowledge as a plain dict (API / serialisation)."""
    tk = get_tool(name)
    return asdict(tk) if tk else None


def format_tool(name: str) -> str:
    """Render the unified knowledge for a tool as a terminal card."""
    tk = get_tool(name)
    if not tk:
        return f"  No knowledge on record for '{name}'."
    bar = "═" * 60
    out = [bar, f"  🧩 TOOL DOSSIER — {tk.name}", bar,
           f"  {tk.summary}"]
    if tk.noise:
        out.append(f"  Noise level: {tk.noise}")
    out.append(f"  Sources: {', '.join(tk.sources)}")
    if tk.what:
        out += ["", "  WHAT IT IS:", "    " + tk.what]
    if tk.flags:
        out += ["", "  FLAGS:"]
        for f, d in tk.flags.items():
            why = f"  — {d['why']}" if d.get("why") else ""
            out.append(f"    {f:<14} {d['what']}{why}")
    if tk.commands:
        out += ["", "  KEY COMMANDS:"]
        for label, cmd in list(tk.commands.items())[:8]:
            out.append(f"    [{label}] {cmd}")
    if tk.opsec:
        out += ["", "  🥷 OPSEC:"]
        out += [f"    • {t}" for t in tk.opsec[:4]]
    if tk.next_steps:
        out += ["", "  → NEXT STEPS:"]
        for s in tk.next_steps[:4]:
            out.append(f"    [{str(s.get('noise','?')).upper():<6}] {s.get('tool','?')} — {s.get('why','')}")
    if tk.cheats:
        out += ["", "  📇 CHEATS:"]
        for c in tk.cheats[:4]:
            out.append(f"    {c['cmd']} — {c['purpose']}")
    if tk.related_techniques:
        out.append("")
        out.append("  🟣 Related purple techniques: " + ", ".join(tk.related_techniques))
    if _has_output_lesson(tk.name):
        out.append("")
        out.append(f"  📖 Reading its output: run `results {tk.name}`")
    out += [bar, "  `anatomy <cmd>` for a breakdown · `purple <tech>` for detections."]
    return "\n".join(out)


def find_drift() -> Dict:
    """Diagnostic: where the same knowledge is defined in more than one place.

    The registry resolves every duplicated flag to FLAG_KB (the richer owner),
    but this surfaces the duplication so LESSONS can be thinned over time and a
    test can gate against NEW divergence. Returns duplicated flags per tool +
    per-tool source coverage.
    """
    lessons = _lessons()
    flagkb = _flag_kb()
    duplicated = {}
    for t in set(lessons) & set(flagkb):
        both = sorted(set((lessons[t].get("flags") or {})) & set(flagkb[t]))
        if both:
            duplicated[t] = both
    coverage = {}
    for t in list_tools():
        tk = get_tool(t)
        coverage[t] = tk.sources if tk else []
    return {
        "duplicated_flags":     duplicated,
        "num_duplicated_flags": sum(len(v) for v in duplicated.values()),
        "coverage":             coverage,
        "total_entries":        len(coverage),
    }


def to_rag_documents() -> List[Dict]:
    """Serialise the whole knowledge graph as ground-truth documents for RAG.

    One document per tool, flattening every field into text. Feeding these into
    the vector store gives the LLM deterministic, non-hallucinated grounding for
    tool syntax/opsec — the registry becomes the single source the model reads.
    Returns [{id, tool, text, sources}].
    """
    docs = []
    for t in list_tools():
        tk = get_tool(t)
        if not tk:
            continue
        parts = [f"TOOL: {tk.name}", f"Summary: {tk.summary}"]
        if tk.what:
            parts.append(f"What it is: {tk.what}")
        if tk.how:
            parts.append(f"How it works: {tk.how}")
        if tk.flags:
            parts.append("Flags: " + "; ".join(
                f"{f} = {d['what']} {d['why']}".strip() for f, d in tk.flags.items()))
        if tk.commands:
            parts.append("Commands: " + "; ".join(f"{k}: {v}" for k, v in tk.commands.items()))
        if tk.opsec:
            parts.append("OpSec: " + " ".join(tk.opsec))
        if tk.cheats:
            parts.append("Cheat sheet: " + "; ".join(
                f"{c['cmd']} ({c['purpose']})" for c in tk.cheats))
        if tk.related_techniques:
            parts.append("Related detection techniques: " + ", ".join(tk.related_techniques))
        out_text = _output_rag_text(tk.name)
        if out_text:
            parts.append("How to read its output: " + out_text)
        docs.append({"id": f"tool:{tk.name}", "tool": tk.name,
                     "text": "\n".join(parts), "sources": tk.sources})
    return docs
