#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║        ERR0RS ULTIMATE — KNOWLEDGE API ROUTER                    ║
║              src/ui/knowledge_api.py                             ║
║                                                                  ║
║  The read-only knowledge endpoints (purple team, command         ║
║  anatomy, output interpreter, roadmap, cheat sheets, unified     ║
║  tool registry, results literacy, RAG). Extracted from           ║
║  main.start_api into an APIRouter so they are defined ONCE and   ║
║  are testable in isolation (mount on a bare app, drive via       ║
║  httpx.ASGITransport) without the version-fragile TestClient.    ║
║                                                                  ║
║  These routes are self-contained (lazy imports, no server        ║
║  state), which is exactly why they belong in a router.           ║
║                                                                  ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone        ║
╚══════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

from fastapi import APIRouter, Body

knowledge_router = APIRouter()


# ── Purple team: red technique → blue detection artifacts ─────────────────
@knowledge_router.get("/purple")
def purple_list():
    from src.security import purple_team as _pt
    return {"techniques": _pt.list_techniques(),
            "surfaces":   list(_pt.DETECTION_SURFACES)}


@knowledge_router.get("/purple/{technique}")
def purple_technique(technique: str, surface: str = None):
    from src.security import purple_team as _pt
    t = _pt.get_technique(technique)
    if not t:
        return {"error":     f"unknown technique '{technique}'",
                "available": [x["key"] for x in _pt.list_techniques()]}
    return {
        "name":        t["name"],
        "tactic":      t.get("tactic", ""),
        "mitre":       t.get("mitre", []),
        "attack":      t.get("attack", {}),
        "detections":  _pt.get_detections_json(technique, surface),
        "remediation": t.get("remediation", ""),
        "learning":    t.get("learning", ""),
    }


# ── Command anatomy: break a command into explained parts ─────────────────
@knowledge_router.get("/anatomy")
def anatomy(cmd: str):
    from src.core.command_anatomy import anatomy_json
    return anatomy_json(cmd)


# ── Output interpreter: raw tool output → findings + taught next steps ─────
@knowledge_router.post("/interpret")
def interpret_output(payload: dict = Body(...)):
    from src.core.output_interpreter import interpret
    return interpret(payload.get("output", ""),
                     tool=payload.get("tool"),
                     target=payload.get("target"))


# ── Learning roadmap ──────────────────────────────────────────────────────
@knowledge_router.get("/roadmap")
def roadmap(stage: str = None):
    from src.education_new import roadmap as _rm
    s = _rm.get_stage(stage) if stage else None
    return s if s else {"roadmap": _rm.get_roadmap()}


# ── Cheat sheets ──────────────────────────────────────────────────────────
@knowledge_router.get("/cheat")
def cheat(q: str = None):
    from src.education_new import cheatsheets as _cs
    if q:
        return {"query": q, "results": _cs.get_cheats(q) or _cs.search_cheats(q)}
    return {"categories": _cs.list_categories(), "results": _cs.get_cheats()}


# ── Unified tool knowledge registry ───────────────────────────────────────
@knowledge_router.get("/tools")
def tools_list():
    from src.core import tool_registry as _tr
    return {"tools": _tr.list_tools(), "drift": _tr.find_drift()["num_duplicated_flags"]}


@knowledge_router.get("/tool/{name}")
def tool_dossier(name: str):
    from src.core import tool_registry as _tr
    tj = _tr.tool_json(name)
    return tj if tj else {"error": f"no knowledge for '{name}'"}


# ── Results literacy: how to read a tool's output ─────────────────────────
@knowledge_router.get("/results/{tool}")
def results_literacy(tool: str):
    from src.core import output_anatomy as _oa
    lesson = _oa.get_output_lesson(tool)
    return lesson if lesson else {"error": f"no results lesson for '{tool}'",
                                  "available": _oa.list_output_lessons()}


# ── RAG: ground-truth corpus + (re)ingest ─────────────────────────────────
@knowledge_router.get("/rag/tools")
def rag_tool_docs():
    """Ground-truth tool knowledge as RAG documents (deterministic corpus)."""
    from src.core import tool_registry as _tr
    return {"documents": _tr.to_rag_documents()}


@knowledge_router.post("/rag/ingest")
def rag_ingest(payload: dict = Body(default={})):
    """(Re)ingest the unified tool registry into the err0rs_refs collection."""
    from src.ai.registry_rag import ingest_registry
    return ingest_registry(reset=bool(payload.get("reset", False)))
