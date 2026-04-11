# src/core/workflow/executor.py
# ERR0RS-Ultimate — Workflow Step Executor
# Runs each step in a loaded workflow: evaluates conditions, interpolates
# args, dispatches to plugin_manager, runs analysis, emits events.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger("WorkflowExecutor")

_SAFE_BUILTINS = {"True": True, "False": False, "None": None}


class WorkflowExecutor:
    """
    Executes a validated workflow dict produced by WorkflowLoader.

    Parameters
    ----------
    plugin_manager : PluginManager
        Dispatches plugin commands.
    interpreter : Interpreter
        Analyses raw tool output into structured findings.
    memory : SharedContext | SimpleMemory
        Stores results and findings across steps.
    event_bus : EventBus | None
        Optional; emits real-time events to the dashboard.
    learn_mode : bool
        When True, print educational explanations per step.
    safe_mode : bool
        When True, hardware/deploy steps are blocked.
    """

    def __init__(
        self,
        plugin_manager,
        interpreter,
        memory,
        event_bus=None,
        learn_mode: bool = False,
        safe_mode:  bool = False,
    ):
        self.plugin_manager = plugin_manager
        self.interpreter    = interpreter
        self.memory         = memory
        self.event_bus      = event_bus
        self.learn_mode     = learn_mode
        self.safe_mode      = safe_mode

    # ── Public ────────────────────────────────────────────────────────────

    def execute(self, workflow: dict, target: str) -> List[Dict]:
        """
        Run all steps in the workflow. Returns a list of step result dicts.
        """
        context = self._fresh_context(target)
        results: List[Dict] = []

        self._emit("workflow_start", {"workflow": workflow["name"], "target": target})

        for i, step in enumerate(workflow["steps"]):
            step_num   = i + 1
            step_name  = step.get("name", f"Step {step_num}")
            step_type  = step.get("type", "command")
            timeout    = step.get("timeout", 120)
            should_learn = self.learn_mode or step.get("learn", False)

            print(f"\n  \033[96m[{step_num}/{len(workflow['steps'])}]\033[0m "
                  f"\033[93m{step_name}\033[0m")
            self._emit("workflow_step", {
                "step": step_num, "total": len(workflow["steps"]),
                "name": step_name, "target": target,
            })

            # ── Condition gate ────────────────────────────────────
            condition = step.get("condition")
            if condition:
                if not self._eval_condition(condition, context):
                    print(f"  \033[90m⏭  Skipping — condition not met: {condition}\033[0m")
                    results.append({"step": step_num, "name": step_name,
                                    "status": "skipped", "reason": condition})
                    continue

            # ── Special step types ────────────────────────────────
            if step_type == "analyze":
                result = self._run_analyze(context, step_name)
                results.append(result)
                continue

            # ── Hardware/deploy gate ──────────────────────────────
            command = step.get("command", "")
            if command == "deploy" and self.safe_mode:
                print("  \033[91m🔒 SAFE_MODE — hardware deploy blocked.\033[0m")
                results.append({"step": step_num, "name": step_name,
                                 "status": "blocked", "reason": "safe_mode"})
                continue

            # ── Build args ────────────────────────────────────────
            raw_args = step.get("args", {})
            args = {
                k: v.replace("{target}", target) if isinstance(v, str) else v
                for k, v in raw_args.items()
            }

            # ── Education pre-step ────────────────────────────────
            if should_learn:
                self._print_education(command)

            # ── Execute ───────────────────────────────────────────
            t0 = time.time()
            try:
                raw_result = self.plugin_manager.execute(command, args)
            except Exception as e:
                raw_result = f"[PLUGIN ERROR] {e}"
            elapsed = round(time.time() - t0, 2)

            output = str(raw_result)
            success = not output.startswith("[ERR0RS]") and not output.startswith("[PLUGIN ERROR]")

            # Print a preview
            lines = output.splitlines()
            for line in lines[:12]:
                print(f"    {line}")
            if len(lines) > 12:
                print(f"    ... ({len(lines) - 12} more lines)")

            # ── Save to memory ────────────────────────────────────
            self._save_result(command, output)

            # ── Context update ────────────────────────────────────
            self._update_context(context, output)

            self._emit("command_result", {
                "step": step_num, "command": command,
                "result": output[:2000], "elapsed": elapsed,
            })

            step_result = {
                "step":    step_num,
                "name":    step_name,
                "command": command,
                "args":    args,
                "status":  "complete" if success else "error",
                "output":  output,
                "elapsed": elapsed,
            }
            results.append(step_result)

            if not success:
                print(f"  \033[91m✗ Step error — continuing.\033[0m")

        # ── Workflow done ─────────────────────────────────────────
        self._emit("workflow_complete", {
            "workflow": workflow["name"], "target": target,
            "steps_run": len(results),
        })
        print(f"\n  \033[92m✓ Workflow complete\033[0m — {len(results)} steps")
        return results

    # ── Internals ─────────────────────────────────────────────────────────

    def _fresh_context(self, target: str) -> Dict:
        return {
            "target":        target,
            "services":      [],
            "open_ports":    [],
            "forms_detected": False,
            "os_guess":      "",
            "last_output":   "",
        }

    def _eval_condition(self, condition: str, context: Dict) -> bool:
        try:
            return bool(eval(condition, {"__builtins__": _SAFE_BUILTINS}, context))  # noqa: S307
        except Exception as e:
            logger.warning(f"Condition eval error '{condition}': {e}")
            return False

    def _run_analyze(self, context: Dict, step_name: str) -> Dict:
        """Run the interpreter over the last stored result."""
        last_output = ""
        if hasattr(self.memory, "last_results"):
            results = self.memory.last_results
            if results:
                last_key = list(results.keys())[-1]
                last_output = str(results[last_key])
        elif hasattr(self.memory, "history") and self.memory.history:
            last_output = str(self.memory.history[-1].get("result", ""))

        findings = []
        if last_output and hasattr(self.interpreter, "analyze_output"):
            findings = self.interpreter.analyze_output(last_output)

        # Update context from findings
        import re
        for port_match in re.findall(r"(\d+)/tcp\s+open", last_output):
            port = int(port_match)
            if port not in context["open_ports"]:
                context["open_ports"].append(port)
        for svc in ["http", "https", "ssh", "ftp", "smb", "rdp"]:
            if svc in last_output.lower() and svc not in context["services"]:
                context["services"].append(svc)
        if "form" in last_output.lower() or "input" in last_output.lower():
            context["forms_detected"] = True

        print(f"  \033[95m📊 Analysis:\033[0m "
              f"{len(findings)} finding(s) | "
              f"Services: {context['services']} | "
              f"Ports: {context['open_ports']}")

        self._emit("analysis_complete", {
            "findings": findings,
            "context":  {k: v for k, v in context.items() if k != "last_output"},
        })

        return {"step": step_name, "type": "analyze",
                "status": "complete", "findings": findings}

    def _update_context(self, context: Dict, output: str):
        import re
        context["last_output"] = output
        for port_match in re.findall(r"(\d+)/tcp\s+open", output):
            port = int(port_match)
            if port not in context["open_ports"]:
                context["open_ports"].append(port)
        for svc in ["http", "https", "ssh", "ftp", "smb", "rdp", "mysql"]:
            if svc in output.lower() and svc not in context["services"]:
                context["services"].append(svc)
        if "form" in output.lower() or "input type=" in output.lower():
            context["forms_detected"] = True

    def _save_result(self, command: str, output: str):
        try:
            if hasattr(self.memory, "save_result"):
                self.memory.save_result(command, output)
            elif hasattr(self.memory, "last_results"):
                self.memory.last_results[command] = output
            elif hasattr(self.memory, "log_action"):
                self.memory.log_action("workflow", command, {}, output)
        except Exception as e:
            logger.debug(f"Memory save failed: {e}")

    def _print_education(self, command: str):
        """Print a teaching card for the given command if plugin supports it."""
        try:
            plugin_name = self.plugin_manager.command_index.get(command)
            if not plugin_name:
                return
            instance = self.plugin_manager.plugins[plugin_name]["instance"]
            if not hasattr(instance, "explain"):
                return
            card = instance.explain()
            print(f"\n  \033[94m📘 Learning: {card.get('name', command)}\033[0m")
            print(f"  {card.get('description', '')}")
            if card.get("mitre_id"):
                print(f"  MITRE: {card['mitre_id']} — {card.get('mitre_tactic', '')}")
            if card.get("defend"):
                print(f"  🛡  Defend: {card['defend']}")
            print()
        except Exception as e:
            logger.debug(f"Education print failed: {e}")

    def _emit(self, event: str, data: Any = None):
        if self.event_bus:
            try:
                self.event_bus.emit(event, data)
            except Exception as e:
                logger.debug(f"Event bus emit failed: {e}")
