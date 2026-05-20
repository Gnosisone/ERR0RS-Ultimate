"""
ERR0RS ULTIMATE - Base Tool Module
Foundation class for all security tool integrations

This provides a unified interface for 120+ security tools
"""

import subprocess
import logging
import time
import json
import threading
import re
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level event-bus binding
# ---------------------------------------------------------------------------
# Any subsystem that has a SharedContext can call
#   set_default_event_bus(ctx.event_bus)
# once at startup.  Every BaseTool instance that hasn't been individually
# bound will then publish "tool.output" / "tool.start" / "tool.end" events
# through that bus, which feeds both the CLI subscriber and the dashboard
# SocketIO relay.
_default_event_bus = None


def set_default_event_bus(bus) -> None:
    """Register the global EventBus used by all BaseTool instances."""
    global _default_event_bus
    _default_event_bus = bus


def _get_bus(tool):
    """Resolve the bus for a tool instance (instance override → global)."""
    return getattr(tool, "_event_bus", None) or _default_event_bus


# ---------------------------------------------------------------------------
# Command-line redaction (avoid leaking creds / API keys into logs + events)
# ---------------------------------------------------------------------------
_REDACT_PATTERNS = [
    re.compile(r"(--password[= ])(\S+)", re.IGNORECASE),
    re.compile(r"(-p[= ])(\S+)"),
    re.compile(r"(--token[= ])(\S+)", re.IGNORECASE),
    re.compile(r"(--api[-_]?key[= ])(\S+)", re.IGNORECASE),
    re.compile(r"(Authorization:\s*Bearer\s+)(\S+)", re.IGNORECASE),
]


def _redact(command: str) -> str:
    """Mask common credential flags before logging."""
    out = command
    for pat in _REDACT_PATTERNS:
        out = pat.sub(lambda m: m.group(1) + "***REDACTED***", out)
    return out


class ToolCategory(Enum):
    """Tool categories for organization"""
    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY = "vulnerability"
    EXPLOITATION = "exploitation"
    PASSWORD = "password"
    WIRELESS = "wireless"
    WEB = "web"
    SOCIAL = "social"
    POSTEX = "postexploitation"
    FORENSICS = "forensics"
    MOBILE = "mobile"


class ToolStatus(Enum):
    """Execution status"""
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Standardized tool result"""
    tool_name: str
    status: ToolStatus
    output: str
    errors: str
    execution_time: float
    exit_code: int
    findings: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class BaseTool(ABC):
    """
    Base class for all security tools
    
    Provides:
    - Standardized execution interface
    - Timeout protection
    - Output parsing
    - Error handling
    - Educational content
    - Safety checks
    """
    
    def __init__(
        self,
        tool_name: str,
        category: ToolCategory,
        description: str,
        requires_root: bool = False,
        timeout: int = 60
    ):
        self.tool_name = tool_name
        self.category = category
        self.description = description
        self.requires_root = requires_root
        self.timeout = timeout
        self.status = ToolStatus.READY
        
    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate parameters before execution"""
        pass
    
    @abstractmethod
    def build_command(self, params: Dict[str, Any]) -> str:
        """Build the command to execute"""
        pass
    
    @abstractmethod
    def parse_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse tool output into structured findings"""
        pass    
    # ------------------------------------------------------------------
    # Bus binding (per-instance override; falls back to module default)
    # ------------------------------------------------------------------
    def bind_bus(self, bus) -> None:
        """Attach an EventBus to this specific tool instance."""
        self._event_bus = bus

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.

        Streaming model:
        - Spawn subprocess with line-buffered pipes.
        - Iterate stdout line-by-line so every line is emitted as
          a ``tool.output`` event on the shared EventBus the instant
          it arrives — CLI and dashboard subscribers both see live
          output.
        - Hard deadline enforced by a watchdog thread (Popen.kill on
          timeout) so even a tool that hangs without producing output
          still gets killed.

        Backwards-compatible: returns the same ToolResult shape as
        the previous blocking implementation.
        """
        start_time = time.time()
        bus        = _get_bus(self)

        # Validate parameters
        if not self.validate_params(params):
            return ToolResult(
                tool_name=self.tool_name,
                status=ToolStatus.FAILED,
                output="",
                errors="Invalid parameters",
                execution_time=0,
                exit_code=-1,
                findings=[],
                metadata={}
            )

        # Build command
        command       = self.build_command(params)
        safe_command  = _redact(command)
        logger.info(f"Executing {self.tool_name}: {safe_command}")

        if bus:
            bus.emit("tool.start", {
                "tool":    self.tool_name,
                "command": safe_command,
                "target":  params.get("target"),
            })

        stdout_buf : List[str] = []
        stderr_buf : List[str] = []
        exit_code  : int       = -1
        status                  = ToolStatus.RUNNING
        watchdog   : Optional[threading.Timer] = None
        process    : Optional[subprocess.Popen] = None

        try:
            self.status = ToolStatus.RUNNING

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,           # line-buffered
            )

            # Watchdog: kill the process if it overruns the timeout,
            # even if it's silent on stdout.
            def _kill_on_timeout():
                if process.poll() is None:
                    logger.warning(
                        f"{self.tool_name} timed out after {self.timeout}s — killing PID {process.pid}"
                    )
                    try:
                        process.kill()
                    except Exception:
                        pass

            watchdog = threading.Timer(self.timeout, _kill_on_timeout)
            watchdog.daemon = True
            watchdog.start()

            # Live stdout iteration — every line becomes an event.
            for raw_line in iter(process.stdout.readline, ""):
                line = raw_line.rstrip("\n")
                stdout_buf.append(line)
                if bus:
                    bus.emit("tool.output", {
                        "tool": self.tool_name,
                        "line": line,
                    })

            # stdout EOF — drain stderr (it's usually small)
            try:
                err = process.stderr.read() or ""
            except Exception:
                err = ""
            if err:
                stderr_buf.append(err)
                if bus:
                    for eline in err.splitlines():
                        bus.emit("tool.stderr", {
                            "tool": self.tool_name,
                            "line": eline,
                        })

            process.wait(timeout=2)
            exit_code = process.returncode if process.returncode is not None else -1

            # Distinguish timeout-kill from clean failure.
            # If the watchdog fired, process.returncode is typically -9 on Linux.
            killed_by_watchdog = (
                watchdog is not None
                and not watchdog.is_alive()
                and exit_code in (-9, 137)
            )
            if killed_by_watchdog:
                status = ToolStatus.TIMEOUT
            else:
                status = ToolStatus.COMPLETED if exit_code == 0 else ToolStatus.FAILED

        except Exception as e:
            stderr_buf.append(str(e))
            status = ToolStatus.FAILED
            logger.error(f"{self.tool_name} execution failed: {e}")
            if process is not None and process.poll() is None:
                try:
                    process.kill()
                except Exception:
                    pass
        finally:
            if watchdog is not None:
                watchdog.cancel()

        stdout = "\n".join(stdout_buf)
        stderr = "\n".join(stderr_buf)

        execution_time = time.time() - start_time

        # Parse output into findings
        findings = []
        if stdout and status == ToolStatus.COMPLETED:
            try:
                findings = self.parse_output(stdout)
            except Exception as e:
                logger.error(f"Failed to parse {self.tool_name} output: {e}")
        
        # Create result
        result = ToolResult(
            tool_name=self.tool_name,
            status=status,
            output=stdout,
            errors=stderr,
            execution_time=execution_time,
            exit_code=exit_code,
            findings=findings,
            metadata={
                "category": self.category.value,
                "command": safe_command,
                "params": params
            }
        )

        if bus:
            bus.emit("tool.end", {
                "tool":           self.tool_name,
                "status":         status.value,
                "exit_code":      exit_code,
                "execution_time": execution_time,
                "findings_count": len(findings),
            })

        self.status = status
        return result
    
    def get_educational_content(self) -> Dict[str, str]:
        """Get educational information about this tool"""
        return {
            "what": self.description,
            "when": self._get_when_to_use(),
            "how": self._get_how_to_use(),
            "why": self._get_why_important(),
            "caution": self._get_cautions()
        }
    
    @abstractmethod
    def _get_when_to_use(self) -> str:
        """When to use this tool in a pentest"""
        pass
    
    @abstractmethod
    def _get_how_to_use(self) -> str:
        """How to use this tool effectively"""
        pass
    
    @abstractmethod
    def _get_why_important(self) -> str:
        """Why this tool is important"""
        pass
    
    @abstractmethod
    def _get_cautions(self) -> str:
        """Safety and ethical considerations"""
        pass
