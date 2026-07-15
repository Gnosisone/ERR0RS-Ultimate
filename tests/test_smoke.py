"""
Import + wiring smoke test.

Catches import-time regressions across the whole session's work (a broken
import in any wired module fails here fast) and asserts the public entry
points still exist. Cheap, fast, no network — the kind of guard that would
have caught the dependency drifts early.

Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
"""

import importlib

import pytest


SESSION_MODULES = [
    "main",
    "src.security.purple_team",
    "src.core.command_anatomy",
    "src.core.output_interpreter",
    "src.core.output_anatomy",
    "src.core.tool_registry",
    "src.core.help_parser",
    "src.education_new.roadmap",
    "src.education_new.cheatsheets",
    "src.ai.registry_rag",
    "src.ui.knowledge_api",
]


@pytest.mark.parametrize("mod", SESSION_MODULES)
def test_module_imports(mod):
    assert importlib.import_module(mod) is not None


def test_public_entry_points_exist():
    from src.core import command_anatomy, output_interpreter, output_anatomy
    from src.core import tool_registry, help_parser
    from src.security import purple_team
    from src.education_new import roadmap, cheatsheets
    from src.ai import registry_rag

    for fn in ("explain_command", "format_anatomy", "anatomy_json"):
        assert callable(getattr(command_anatomy, fn))
    assert callable(output_interpreter.interpret)
    assert callable(output_anatomy.format_output_lesson)
    assert callable(tool_registry.get_tool) and callable(tool_registry.to_rag_documents)
    assert callable(help_parser.flag_help)
    assert callable(purple_team.technique_to_finding)
    assert callable(roadmap.get_roadmap) and callable(cheatsheets.get_cheats)
    assert callable(registry_rag.ingest_registry) and callable(registry_rag.ground_for_tool)


def test_knowledge_router_registers_expected_paths():
    from src.ui.knowledge_api import knowledge_router
    paths = {r.path for r in knowledge_router.routes}
    expected = {"/purple", "/purple/{technique}", "/anatomy", "/interpret",
                "/roadmap", "/cheat", "/tools", "/tool/{name}",
                "/results/{tool}", "/rag/tools", "/rag/ingest"}
    assert expected <= paths, f"missing routes: {expected - paths}"
