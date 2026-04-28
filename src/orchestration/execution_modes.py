#!/usr/bin/env python3
"""
ERR0RS ULTIMATE - Execution Modes  (REAL – calls ToolExecutor)
Interactive, YOLO, and Supervised execution modes.

Modes:
  INTERACTIVE  – confirm every step before it runs   (safest)
  YOLO         – fire everything automatically       (lab / CTF)
  SUPERVISED   – run step, show output, ask to continue
"""

import logging
import sys
import os
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio

# ---------------------------------------------------------------------------
# Path fix so "from src.core…" works regardless of CWD
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.core.tool_executor import ToolExecutor, ToolResult, ToolStatus  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ExecutionMode(Enum):
    INTERACTIVE = "interactive"
    YOLO        = "yolo"
    SUPERVISED  = "supervised"


@dataclass
class ExecutionStep:
    step_number          : int
    tool_name            : str
    target               : str
    parameters           : Dict[str, Any]
    description          : str
    estimated_time       : int   # seconds (rough estimate)
    requires_confirmation: bool = True


@dataclass
class ExecutionPlan:
    mode                : ExecutionMode
    steps               : List[ExecutionStep]
    total_steps         : int
    estimated_total_time: int
    target              : str
    intent              : str


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ExecutionEngine:
    """
    Manages execution flow.  Each mode shares the same _execute_step()
    which delegates to the real ToolExecutor subprocess runner.
    """

    def __init__(self):
        self.current_mode   = ExecutionMode.INTERACTIVE
        self.current_plan   : Optional[ExecutionPlan] = None
        self.executed_steps : List[ExecutionStep]     = []
        self.executor       = ToolExecutor(on_line=self._on_tool_line)
        self.paused         = False

    # ------------------------------------------------------------------
    # Live-output callback  (prints each line as it arrives)
    # ------------------------------------------------------------------

    @staticmethod
    async def _on_tool_line(tool_name: str, line: str):
        print(f"   │ [{tool_name}] {line}")

    # ------------------------------------------------------------------
    # Mode setter
    # ------------------------------------------------------------------

    def set_mode(self, mode: ExecutionMode):
        self.current_mode = mode

    # ------------------------------------------------------------------
    # Plan builder
    # ------------------------------------------------------------------

    def create_plan(self, tools: List[str], target: str,
                    parameters: Dict[str, Any], intent: str) -> ExecutionPlan:
        steps      = []
        total_time = 0
        for idx, tool_name in enumerate(tools, 1):
            est = self._estimate_tool_time(tool_name, parameters)
            total_time += est
            steps.append(ExecutionStep(
                step_number=idx, tool_name=tool_name, target=target,
                parameters=parameters.copy(),
                description=f"Run {tool_name} against {target}",
                estimated_time=est,
                requires_confirmation=(self.current_mode == ExecutionMode.INTERACTIVE),
            ))
        plan = ExecutionPlan(
            mode=self.current_mode, steps=steps, total_steps=len(steps),
            estimated_total_time=total_time, target=target, intent=intent,
        )
        self.current_plan = plan
        return plan

    @staticmethod
    def _estimate_tool_time(tool_name: str, params: Dict) -> int:
        BASE = {"nmap":60,"sqlmap":120,"nikto":90,"gobuster":180,
                "hydra":300,"hashcat":600,"metasploit":180,
                "subfinder":30,"nuclei":120,"amass":60}
        base = BASE.get(tool_name, 60)
        t = params.get("timing", "3")
        if t == "1":   base *= 3
        elif t == "4": base = int(base * 0.5)
        return base

    # ==================================================================
    # INTERACTIVE MODE
    # ==================================================================

    async def execute_interactive(self, plan: ExecutionPlan) -> Dict[str, Any]:
        results = {"mode":"interactive","steps_completed":0,"steps_skipped":0,"results":[]}
        print("\n" + "="*60)
        print("🎯 INTERACTIVE MODE – you control every step")
        print("="*60)
        print(f"\n📋 Plan: {plan.total_steps} steps  |  🎯 {plan.target}  "
              f"|  ⏱  ~{plan.estimated_total_time//60}m {plan.estimated_total_time%60}s\n")

        for step in plan.steps:
            print(f"\n📍 Step {step.step_number}/{plan.total_steps}")
            print(f"   Tool     : {step.tool_name}")
            print(f"   Target   : {step.target}")
            print(f"   Est time : {step.estimated_time}s")
            if step.parameters:
                print(f"   Params   : {step.parameters}")

            resp = input("\n   Execute? [Y / n / skip / stop]: ").strip().lower()

            if resp in ("stop","quit","exit","q"):
                print("\n⏹  Stopped by user"); break
            if resp == "skip":
                print("   ⏭  Skipped"); results["steps_skipped"] += 1; continue
            if resp not in ("","y","yes"):
                print("   ⏭  Skipped"); results["steps_skipped"] += 1; continue

            print(f"\n   ▶  Running {step.tool_name} …")
            step_result = await self._execute_step(step)
            results["results"].append(step_result)
            results["steps_completed"] += 1
            self._print_step_summary(step_result)

        print("\n" + "="*60)
        print(f"✅ Interactive complete  |  done={results['steps_completed']}  "
              f"skipped={results['steps_skipped']}")
        print("="*60)
        return results

    # ==================================================================
    # YOLO MODE
    # ==================================================================

    async def execute_yolo(self, plan: ExecutionPlan) -> Dict[str, Any]:
        results = {"mode":"yolo","steps_completed":0,"results":[]}
        print("\n" + "="*60)
        print("🚀 YOLO MODE – full auto, no questions")
        print("⚠️  Make sure your target is authorised!")
        print("="*60)
        print(f"\n📋 {plan.total_steps} steps  |  🎯 {plan.target}")
        print("\n🔥 Launching in 3 seconds …  (Ctrl-C to abort)")
        await asyncio.sleep(3)

        for step in plan.steps:
            if self.paused:
                print("\n⏸  Paused"); return results
            print(f"\n▶  [{step.step_number}/{plan.total_steps}] {step.tool_name} → {step.target}")
            step_result = await self._execute_step(step)
            results["results"].append(step_result)
            results["steps_completed"] += 1
            emoji = "✅" if step_result["status"] == "success" else "❌"
            print(f"   {emoji} {step.tool_name}: {step_result['status']}  "
                  f"({step_result.get('findings_count',0)} findings, "
                  f"{step_result.get('duration_ms',0)}ms)")

        print("\n" + "="*60)
        print(f"🎉 YOLO complete  |  {results['steps_completed']} steps done")
        print("="*60)
        return results

    # ==================================================================
    # SUPERVISED MODE
    # ==================================================================

    async def execute_supervised(self, plan: ExecutionPlan) -> Dict[str, Any]:
        results = {"mode":"supervised","steps_completed":0,"results":[]}
        print("\n" + "="*60)
        print("👀 SUPERVISED MODE – run → review → continue")
        print("="*60)
        print(f"\n📋 {plan.total_steps} steps  |  🎯 {plan.target}\n")

        for step in plan.steps:
            print(f"\n▶  [{step.step_number}/{plan.total_steps}] Running {step.tool_name} …")
            step_result = await self._execute_step(step)
            results["results"].append(step_result)
            results["steps_completed"] += 1

            # Show findings preview
            print(f"\n📊 {step.tool_name} results  (status={step_result['status']}):")
            for f in step_result.get("findings_preview", []):
                print(f"     • {f}")
            if not step_result.get("findings_preview"):
                print("     (no structured findings – see raw output above)")

            if step.step_number < plan.total_steps:
                resp = input("\n   Continue? [Y / n]: ").strip().lower()
                if resp in ("n","no","stop"):
                    print("\n⏹  Stopped"); break

        print("\n" + "="*60)
        print(f"✅ Supervised complete  |  {results['steps_completed']}/{plan.total_steps} steps")
        print("="*60)
        return results

    # ==================================================================
    # Shared: real subprocess execution via ToolExecutor
    # ==================================================================

    async def _execute_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Delegate to the real ToolExecutor and normalise the result."""
        try:
            tool_result: ToolResult = await self.executor.run(
                step.tool_name, step.target, step.parameters
            )
            self.executed_steps.append(step)

            # Normalise to a plain dict the rest of the pipeline can use
            findings_preview = []
            for f in tool_result.findings[:5]:           # first 5 for display
                findings_preview.append(str(f))

            return {
                "tool"            : step.tool_name,
                "target"          : step.target,
                "status"          : tool_result.status.value,
                "findings"        : tool_result.findings,
                "findings_count"  : len(tool_result.findings),
                "findings_preview": findings_preview,
                "duration_ms"     : tool_result.duration_ms,
                "return_code"     : tool_result.return_code,
                "stdout"          : tool_result.stdout,
                "stderr"          : tool_result.stderr,
                "command"         : tool_result.command,
                "error"           : tool_result.error,
            }
        except Exception as exc:
            logger.exception("Step execution error")
            return {
                "tool": step.tool_name, "target": step.target,
                "status": "failed", "error": str(exc),
                "findings": [], "findings_count": 0,
                "findings_preview": [], "duration_ms": 0,
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _print_step_summary(sr: Dict[str, Any]):
        emoji = "✅" if sr["status"] == "success" else "❌"
        print(f"\n   {emoji} {sr['tool']}  |  status={sr['status']}  "
              f"|  findings={sr.get('findings_count',0)}  "
              f"|  time={sr.get('duration_ms',0)}ms")
        if sr.get("error"):
            print(f"   ⚠  {sr['error']}")

    def pause(self):  self.paused = True
    def resume(self): self.paused = False

    def get_progress(self) -> Dict[str, Any]:
        if not self.current_plan:
            return {"status": "no_active_plan"}
        total = self.current_plan.total_steps or 1
        done  = len(self.executed_steps)
        return {
            "mode": self.current_mode.value,
            "total_steps": total, "completed_steps": done,
            "progress_percent": round(done / total * 100, 1),
            "paused": self.paused,
        }
