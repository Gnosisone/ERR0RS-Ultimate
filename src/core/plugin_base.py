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

    # ── Streaming command execution ────────────────────────────────────────

    def stream(
        self,
        cmd,
        tool_name: Optional[str] = None,
        timeout:   int = 300,
        target:    Optional[str] = None,
    ) -> PluginResult:
        """
        Run a command and stream its output **line-by-line** onto the
        shared event bus as it arrives.  Subscribers (the CLI renderer
        and the dashboard SocketIO relay) see live activity instead of
        waiting for the process to finish.

        Events emitted:
            tool.start   {tool, command, target}
            tool.output  {tool, line}        — one per stdout line
            tool.stderr  {tool, line}        — one per stderr line
            tool.end     {tool, status, exit_code, execution_time}

        Args:
            cmd       : list[str]  → executed without a shell (preferred,
                        safe from injection)
                        str        → executed via the shell
            tool_name : label used in events (defaults to argv[0])
            timeout   : hard deadline in seconds (watchdog kills the PID)
            target    : optional target string for the tool.start event

        Returns a PluginResult — same shape as shell(), so existing
        callers keep working.
        """
        import subprocess
        import threading
        import time as _time

        if isinstance(cmd, (list, tuple)):
            cmd_list, cmd_str, use_shell = list(cmd), " ".join(cmd), False
            default_name = cmd_list[0] if cmd_list else "cmd"
        else:
            cmd_list, cmd_str, use_shell = cmd, str(cmd), True
            default_name = str(cmd).split()[0] if str(cmd).strip() else "cmd"
        tool_name = tool_name or default_name

        self.emit("tool.start", {
            "tool": tool_name, "command": cmd_str, "target": target,
        })

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        rc          : int       = -1
        status                  = "completed"
        proc                    = None
        start                   = _time.time()

        try:
            proc = subprocess.Popen(
                cmd_list, shell=use_shell,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1,
            )

            def _kill_on_timeout():
                if proc.poll() is None:
                    try:
                        proc.kill()
                    except Exception:
                        pass

            watchdog = threading.Timer(timeout, _kill_on_timeout)
            watchdog.daemon = True
            watchdog.start()
            try:
                for raw in iter(proc.stdout.readline, ""):
                    line = raw.rstrip("\n")
                    stdout_lines.append(line)
                    self.emit("tool.output", {"tool": tool_name, "line": line})

                err = proc.stderr.read() or ""
                if err:
                    stderr_lines.append(err)
                    for el in err.splitlines():
                        self.emit("tool.stderr", {"tool": tool_name, "line": el})

                proc.wait(timeout=2)
            finally:
                watchdog.cancel()

            rc = proc.returncode if proc.returncode is not None else -1
            if rc in (-9, 137):
                status = "timeout"
            elif rc != 0:
                status = "failed"

        except FileNotFoundError:
            status = "failed"
            stderr_lines.append(f"{tool_name} not found in PATH")
        except Exception as e:
            status = "failed"
            stderr_lines.append(str(e))
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

        output  = "\n".join(stdout_lines)
        errout  = "\n".join(stderr_lines)
        elapsed = round(_time.time() - start, 2)

        self.emit("tool.end", {
            "tool": tool_name, "status": status,
            "exit_code": rc, "execution_time": elapsed,
        })

        return PluginResult(
            output   = output if output else errout,
            success  = (status == "completed"),
            command  = cmd_str,
            metadata = {"returncode": rc, "status": status,
                        "stderr": errout, "execution_time": elapsed},
        )

    # ── Safe shell execution helper ────────────────────────────────────────

    def shell(self, cmd: str, timeout: int = 60) -> PluginResult:
        """
        Run a shell command and return a PluginResult.
        Now streams output live via stream() — every plugin using this
        helper gets real-time CLI/dashboard output for free.
        Prefer this (or stream() with a list) over raw subprocess calls.
        """
        return self.stream(cmd, timeout=timeout)

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
