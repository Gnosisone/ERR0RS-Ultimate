"""
ERR0RS ULTIMATE - Workflow Orchestrator
==========================================
This is the brain that chains tools together automatically.

WHAT IT DOES:
-------------
When you start a pentest, you don't just run one tool. You run
a SEQUENCE. Nmap finds ports → Gobuster scans web services →
SQLMap tests for injection → Metasploit exploits what's found.

The orchestrator manages that entire chain. It:
1. Decides which tools to run based on the phase
2. Passes output from one tool as input to the next
3. Tracks state so nothing runs twice
4. Handles failures gracefully (one tool failing doesn't stop the rest)
5. Attaches education at each step

TEACHING NOTE:
--------------
This is exactly how professional red teams operate. They don't
manually run each tool one by one. They have playbooks — predefined
sequences of actions. This orchestrator IS the playbook engine.

The phases map to the standard PTES (Penetration Testing Execution Standard):
  Recon → Scanning → Enumeration → Exploitation → Post-Exploitation
"""

import sys
import os
import time
import subprocess
from datetime import datetime
from typing import List, Dict, Optional, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.models import (
    EngagementSession, ScanResult, Finding,
    Severity, PentestPhase, ToolStatus
)


class ToolResult:
    """Simple container for what a tool returns after execution."""
    def __init__(self, tool_name: str, target: str, phase: PentestPhase,
                 raw_output: str = "", findings: List[Finding] = None,
                 success: bool = True, error: str = "", duration: float = 0.0,
                 command: str = ""):
        self.tool_name = tool_name
        self.target = target
        self.phase = phase
        self.raw_output = raw_output
        self.findings = findings or []
        self.success = success
        self.error = error
        self.duration = duration
        self.command = command

    def to_scan_result(self) -> ScanResult:
        """Convert to the standard ScanResult model."""
        return ScanResult(
            tool_name=self.tool_name,
            status=ToolStatus.SUCCESS if self.success else ToolStatus.FAILED,
            phase=self.phase,
            target=self.target,
            command=self.command,
            findings=self.findings,
            raw_output=self.raw_output,
            duration=self.duration,
            error_msg=self.error if not self.success else None,
        )


# =============================================================================
# WORKFLOW DEFINITIONS — Predefined pentest playbooks
# =============================================================================
# Each workflow is a list of steps. Each step defines: which tool to run,
# what phase it belongs to, and optionally what previous output it needs.
# =============================================================================

WORKFLOW_RECON = [
    {"tool": "nmap",         "phase": PentestPhase.RECONNAISSANCE, "description": "Full port scan with service detection"},
    {"tool": "gobuster",     "phase": PentestPhase.SCANNING,       "description": "Web directory discovery on open HTTP ports",
     "requires_phase": PentestPhase.RECONNAISSANCE},  # Only runs after recon finds HTTP
]

WORKFLOW_WEB_ASSESSMENT = [
    {"tool": "nmap",         "phase": PentestPhase.RECONNAISSANCE, "description": "Identify web services and versions"},
    {"tool": "gobuster",     "phase": PentestPhase.SCANNING,       "description": "Discover endpoints and hidden paths",
     "requires_phase": PentestPhase.RECONNAISSANCE},
    {"tool": "nikto",        "phase": PentestPhase.SCANNING,       "description": "Web server vulnerability scan",
     "requires_phase": PentestPhase.RECONNAISSANCE},
    {"tool": "sqlmap",       "phase": PentestPhase.EXPLOITATION,   "description": "Test for SQL injection vulnerabilities",
     "requires_phase": PentestPhase.SCANNING},
]

WORKFLOW_FULL_PENTEST = [
    # Phase 1: Recon
    {"tool": "nmap",            "phase": PentestPhase.RECONNAISSANCE, "description": "Comprehensive network scan"},
    {"tool": "theharvester",    "phase": PentestPhase.RECONNAISSANCE, "description": "OSINT and email harvesting"},
    # Phase 2: Scanning
    {"tool": "gobuster",        "phase": PentestPhase.SCANNING,       "description": "Web content discovery",
     "requires_phase": PentestPhase.RECONNAISSANCE},
    {"tool": "nikto",           "phase": PentestPhase.SCANNING,       "description": "Web vulnerability scanning",
     "requires_phase": PentestPhase.RECONNAISSANCE},
    # Phase 3: Exploitation
    {"tool": "sqlmap",          "phase": PentestPhase.EXPLOITATION,   "description": "SQL injection testing",
     "requires_phase": PentestPhase.SCANNING},
    {"tool": "hydra",           "phase": PentestPhase.EXPLOITATION,   "description": "Credential brute-forcing",
     "requires_phase": PentestPhase.SCANNING},
    {"tool": "metasploit",      "phase": PentestPhase.EXPLOITATION,   "description": "Exploitation framework",
     "requires_phase": PentestPhase.SCANNING},
    # Phase 4: Post-Exploitation
    {"tool": "linpeas",         "phase": PentestPhase.POST_EXPLOIT,   "description": "Linux privilege escalation check",
     "requires_phase": PentestPhase.EXPLOITATION},
]

AVAILABLE_WORKFLOWS = {
    "recon":            {"name": "Reconnaissance Only",     "steps": WORKFLOW_RECON},
    "web_assessment":   {"name": "Web Application Test",    "steps": WORKFLOW_WEB_ASSESSMENT},
    "full_pentest":     {"name": "Full Penetration Test",   "steps": WORKFLOW_FULL_PENTEST},
}


# =============================================================================
# ORCHESTRATOR CLASS — The execution engine
# =============================================================================

class Orchestrator:
    """
    Runs a workflow against a target. Manages tool execution,
    dependency checking, output passing, and session building.

    Usage:
        orchestrator = Orchestrator()
        session = orchestrator.run_workflow("full_pentest", targets=["192.168.1.100"])
        # session now contains all scan results and findings
    """

    def __init__(self):
        self.tool_registry: Dict[str, Callable] = {}   # tool_name -> execution function
        self.session: Optional[EngagementSession] = None
        self.completed_phases: List[PentestPhase] = []
        self.phase_outputs: Dict[PentestPhase, List[ToolResult]] = {}
        self.logs: List[str] = []

    def register_tool(self, name: str, executor: Callable):
        """
        Register a tool execution function.
        The executor must accept (target: str, context: dict) and return ToolResult.
        """
        self.tool_registry[name] = executor
        self._log(f"Tool registered: {name}")

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(log_entry)  # Also print to console for real-time feedback

    def run_workflow(self, workflow_name: str, targets: List[str],
                     session_name: str = "ERR0RS Assessment",
                     client_name: str = "", tester_name: str = "") -> EngagementSession:
        """
        Main entry point. Runs an entire workflow end-to-end.
        Returns the completed EngagementSession with all results.
        """
        if workflow_name not in AVAILABLE_WORKFLOWS:
            raise ValueError(f"Unknown workflow: {workflow_name}. "
                             f"Available: {list(AVAILABLE_WORKFLOWS.keys())}")

        workflow = AVAILABLE_WORKFLOWS[workflow_name]
        self._log(f"Starting workflow: {workflow['name']}")
        self._log(f"Targets: {targets}")
        self._log(f"Steps planned: {len(workflow['steps'])}")

        # Create the engagement session
        self.session = EngagementSession(
            name=session_name,
            client_name=client_name,
            tester_name=tester_name,
            targets=targets,
            status="active",
        )
        self.completed_phases = []
        self.phase_outputs = {}

        # Execute each step
        for i, step in enumerate(workflow["steps"], 1):
            self._log(f"\n--- Step {i}/{len(workflow['steps'])}: {step['tool']} ({step['phase'].value}) ---")
            self._log(f"  {step.get('description', 'No description')}")

            # Check dependency: does this step require a previous phase to complete?
            required_phase = step.get("requires_phase")
            if required_phase and required_phase not in self.completed_phases:
                self._log(f"  ⏭️  Skipped — requires {required_phase.value} to complete first")
                continue

            # Run against each target
            for target in targets:
                result = self._execute_tool(step["tool"], target, step["phase"])
                if result:
                    self.session.scan_results.append(result.to_scan_result())
                    # Track phase completion
                    if result.success and step["phase"] not in self.completed_phases:
                        self.completed_phases.append(step["phase"])
                        self.phase_outputs.setdefault(step["phase"], []).append(result)

        # Mark session complete
        self.session.ended_at = datetime.now()
        self.session.status = "completed"
        self._log(f"\n✅ Workflow complete. Total findings: {len(self.session.all_findings)}")
        return self.session

    # -----------------------------------------------------------------------
    # TOOL EXECUTION
    # -----------------------------------------------------------------------

    def _execute_tool(self, tool_name: str, target: str, phase: PentestPhase) -> Optional[ToolResult]:
        """
        Execute a single tool. Handles:
        - Registry lookup (is the tool registered?)
        - Timeout protection (60s default)
        - Error handling (tool crashes don't crash the orchestrator)
        - Context passing (previous phase outputs available)
        """
        if tool_name not in self.tool_registry:
            self._log(f"  ⚠️  Tool '{tool_name}' not registered. Skipping.")
            return ToolResult(
                tool_name=tool_name, target=target, phase=phase,
                success=False, error=f"Tool '{tool_name}' not registered in tool registry."
            )

        executor = self.tool_registry[tool_name]

        # Build context — previous phase outputs the tool can use
        context = {
            "phase": phase,
            "previous_phases": self.completed_phases,
            "phase_outputs": self.phase_outputs,
            "session": self.session,
        }

        start_time = time.time()
        try:
            self._log(f"  🔄 Executing {tool_name} against {target}...")
            result = executor(target=target, context=context)
            result.duration = time.time() - start_time

            if result.success:
                self._log(f"  ✅ {tool_name} completed. Findings: {len(result.findings)}")
            else:
                self._log(f"  ❌ {tool_name} failed: {result.error}")

            return result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self._log(f"  ⏰ {tool_name} timed out after {duration:.1f}s")
            return ToolResult(
                tool_name=tool_name, target=target, phase=phase,
                success=False, error="Tool execution timed out (60s limit)",
                duration=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            self._log(f"  💥 {tool_name} crashed: {str(e)}")
            return ToolResult(
                tool_name=tool_name, target=target, phase=phase,
                success=False, error=str(e), duration=duration,
            )

    def get_logs(self) -> List[str]:
        """Return all orchestrator logs."""
        return self.logs

    def get_available_workflows(self) -> Dict[str, str]:
        """Return workflow names and descriptions for UI display."""
        return {k: v["name"] for k, v in AVAILABLE_WORKFLOWS.items()}
