# src/core/plugin_base.py
# ERR0RS-Ultimate — Professional Base Plugin Class
# Every tool module inherits from this. All hooks, education, autopilot,
# analysis, and event integration live here so plugins stay clean and thin.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging
import time

logger = logging.getLogger("PluginBase")


class PluginResult:
    """
    Structured return type for plugin.run().
    Carries raw output + structured findings so the rest of the
    system never has to parse free-form strings.
    """
    def __init__(
        self,
        output:   str  = "",
        success:  bool = True,
        command:  str  = "",
        findings: List[Dict] = None,
        metadata: Dict = None,
    ):
        self.output   = output
        self.success  = success
        self.command  = command
        self.findings = findings or []
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def __str__(self):
        return self.output

    def __bool__(self):
        return self.success

    def to_dict(self) -> Dict:
        return {
            "output":    self.output,
            "success":   self.success,
            "command":   self.command,
            "findings":  self.findings,
            "metadata":  self.metadata,
            "timestamp": self.timestamp,
        }


class BasePlugin:
    """
    Base class for all ERR0RS tool plugins.

    Subclass this and implement at minimum:
        run(command, args) -> PluginResult | str

    Optional hooks for autopilot, education, and live analysis:
        conditions(context)  -> bool          # Should autopilot use this now?
        suggest(context)     -> str | None    # What to recommend
        explain()            -> dict          # Teaching card
        analyze(output)      -> List[dict]    # Parse raw tool output into findings
    """

    def __init__(self, context=None):
        self.context  = context
        self.manifest: Dict = {}
        self.enabled:  bool = True
        self._load_time = time.time()

    # ── Core — must implement ─────────────────────────────────────────────

    def run(self, command: str, args: Dict) -> Any:
        """Execute the tool. Return PluginResult or plain string."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement run(command, args)"
        )

    # ── Lifecycle hooks ────────────────────────────────────────────────────

    def on_load(self):
        """Called once after the plugin is loaded and wired up."""
        pass

    def on_unload(self):
        """Called before the plugin is removed from memory."""
        pass

    def validate_args(self, args: Dict) -> bool:
        """
        Pre-flight check before run(). Return False to abort execution.
        Override to enforce required keys, format checks, etc.
        """
        return True

    # ── Autopilot interface ────────────────────────────────────────────────

    def conditions(self, context: Dict) -> bool:
        """
        Should the autopilot invoke this plugin given the current context?

        Context keys (populated by AutoPilot):
            last_output  : str  — raw output of the previous tool
            open_ports   : list — e.g. [22, 80, 443]
            services     : list — e.g. ["ssh", "http", "smb"]
            os_guess     : str  — e.g. "Linux", "Windows"
            active_target: str  — current IP/hostname
            findings     : list — structured findings so far

        Example:
            return "http" in context.get("services", [])
        """
        return False

    def suggest(self, context: Dict) -> Optional[str]:
        """
        Return a human-readable suggestion string when conditions() is True.
        Used by autopilot to explain its next action choice.

        Example:
            return f"Run web vulnerability scan on {context.get('active_target')}"
        """
        return None

    # ── Education interface ────────────────────────────────────────────────

    def explain(self) -> Dict:
        """
        Return a structured teaching card for this tool/technique.
        Rendered by the EducationEngine in reports and --learn mode.

        Required keys: name, description, usage, example
        Optional keys: mitre_id, mitre_tactic, difficulty, references,
                       defend (blue team countermeasure)
        """
        return {
            "name":        self.manifest.get("name", self.__class__.__name__),
            "description": self.manifest.get("description", "No description provided."),
            "usage":       "Override explain() in your plugin to add usage context.",
            "example":     "",
            "mitre_id":    "",
            "mitre_tactic":"",
            "difficulty":  "Intermediate",
            "defend":      "",
            "references":  [],
        }

    # ── Analysis interface ─────────────────────────────────────────────────

    def analyze(self, output: str) -> List[Dict]:
        """
        Parse raw tool output and return a list of structured findings.
        Called by the autopilot and report generator automatically.

        Each finding dict should contain:
            title       : str   — short finding name
            severity    : str   — critical | high | medium | low | info
            description : str   — what was found
            evidence    : str   — raw snippet from output
            recommendation: str — remediation guidance
            priority    : int   — 1 (critical) … 4 (info)

        Return [] if nothing noteworthy was found.
        """
        return []

    # ── Event bus helpers ──────────────────────────────────────────────────

    def emit(self, event: str, data: Any = None):
        """Emit an event on the shared context event bus."""
        if self.context and hasattr(self.context, "event_bus"):
            self.context.event_bus.emit(event, data)

    def emit_finding(self, finding: Dict):
        """Shortcut: emit a finding AND log it to shared context."""
        finding.setdefault("plugin", self.info()["name"])
        self.emit("finding.added", finding)
        if self.context and hasattr(self.context, "add_finding"):
            self.context.add_finding(finding)

    # ── Logging helpers ────────────────────────────────────────────────────

    def log(self, msg: str, level: str = "info"):
        """Log through the shared context logger if available."""
        if self.context and hasattr(self.context, "logger"):
            getattr(self.context.logger, level, self.context.logger.info)(
                f"[{self.info()['name']}] {msg}"
            )
        else:
            getattr(logger, level, logger.info)(f"[{self.info()['name']}] {msg}")

    def log_debug(self, msg: str):
        self.log(msg, "debug")

    def log_warning(self, msg: str):
        self.log(msg, "warning")

    def log_error(self, msg: str):
        self.log(msg, "error")

    # ── Safe shell execution helper ────────────────────────────────────────

    def shell(self, cmd: str, timeout: int = 60) -> PluginResult:
        """
        Run a shell command safely and return a PluginResult.
        Prefer this over raw subprocess calls in plugin implementations.
        """
        import subprocess
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=timeout
            )
            output = proc.stdout + (proc.stderr if proc.returncode != 0 else "")
            return PluginResult(
                output=output.strip(),
                success=proc.returncode == 0,
                command=cmd,
                metadata={"returncode": proc.returncode},
            )
        except subprocess.TimeoutExpired:
            return PluginResult(
                output=f"[TIMEOUT] Command timed out after {timeout}s: {cmd}",
                success=False, command=cmd,
            )
        except Exception as e:
            return PluginResult(
                output=f"[ERROR] Shell execution failed: {e}",
                success=False, command=cmd,
            )

    # ── Introspection ──────────────────────────────────────────────────────

    def info(self) -> Dict:
        """Return plugin identity from its manifest."""
        return {
            "name":        self.manifest.get("name", self.__class__.__name__),
            "description": self.manifest.get("description", "No description"),
            "version":     self.manifest.get("version", "0.0.1"),
            "category":    self.manifest.get("category", "misc"),
            "commands":    self.manifest.get("commands", []),
            "author":      self.manifest.get("author", "Unknown"),
            "enabled":     self.enabled,
            "uptime_s":    round(time.time() - self._load_time, 1),
        }

    def __repr__(self):
        i = self.info()
        return f"<Plugin:{i['name']} v{i['version']} [{i['category']}]>"
