# src/core/workflow/engine.py
# ERR0RS-Ultimate — Workflow Engine (top-level runner)
# Ties WorkflowLoader + WorkflowExecutor together. This is the single
# entry point the CLI, dashboard, and API all call.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import os
from typing import Dict, List, Optional

from .loader   import WorkflowLoader
from .executor import WorkflowExecutor

logger = logging.getLogger("WorkflowEngine")


class WorkflowEngine:
    """
    High-level workflow runner.

    Usage
    -----
    engine = WorkflowEngine(plugin_manager, interpreter, memory,
                            event_bus=event_bus, learn_mode=True)
    results = engine.run("webapp", "192.168.1.10")
    available = engine.list()
    """

    def __init__(
        self,
        plugin_manager,
        interpreter,
        memory,
        event_bus=None,
        learn_mode:   bool = False,
        safe_mode:    bool = False,
        workflow_dir: str  = None,
    ):
        if workflow_dir is None:
            # Default: <repo_root>/workflows/
            workflow_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", "workflows"
            )
        self.loader   = WorkflowLoader(workflow_dir=workflow_dir)
        self.executor = WorkflowExecutor(
            plugin_manager = plugin_manager,
            interpreter    = interpreter,
            memory         = memory,
            event_bus      = event_bus,
            learn_mode     = learn_mode,
            safe_mode      = safe_mode,
        )

    def run(self, workflow_name: str, target: str) -> Dict:
        """
        Load and execute a workflow by name.
        Returns a summary dict with results list and metadata.
        """
        try:
            workflow = self.loader.load(workflow_name)
        except FileNotFoundError as e:
            logger.error(str(e))
            return {"error": str(e), "workflow": workflow_name, "target": target}
        except ValueError as e:
            logger.error(f"Invalid workflow '{workflow_name}': {e}")
            return {"error": str(e), "workflow": workflow_name, "target": target}

        print(f"\n  \033[92m🚀 Workflow:\033[0m {workflow['name']}  →  {target}")
        print("  " + "─" * 56)

        results = self.executor.execute(workflow, target)

        summary = {
            "workflow": workflow["name"],
            "id":       workflow.get("id", workflow_name),
            "target":   target,
            "steps":    len(results),
            "complete": sum(1 for r in results if r.get("status") == "complete"),
            "skipped":  sum(1 for r in results if r.get("status") == "skipped"),
            "errors":   sum(1 for r in results if r.get("status") == "error"),
            "results":  results,
        }

        logger.info(
            f"Workflow '{workflow_name}' done — "
            f"{summary['complete']} complete, "
            f"{summary['skipped']} skipped, "
            f"{summary['errors']} errors."
        )
        return summary

    def list(self) -> List[str]:
        """Return names of all available workflows."""
        return self.loader.list_available()

    def describe(self, workflow_name: str) -> Optional[Dict]:
        """Load and return the raw workflow dict without executing it."""
        try:
            return self.loader.load(workflow_name)
        except (FileNotFoundError, ValueError):
            return None
