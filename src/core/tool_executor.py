#!/usr/bin/env python3
"""
ERR0RS ULTIMATE – Real Tool Execution Engine
Spawns security tools as subprocesses, streams output, parses results.

Design rules:
  • Every tool runs in its own asyncio subprocess – nothing blocks the event loop.
  • stdout is streamed line-by-line so the dashboard / REPL can show progress live.
  • A hard timeout per-tool prevents runaway scans from locking the session.
  • Output is captured into a structured ToolResult so downstream agents &
    the report generator can consume it without re-parsing.
"""

import asyncio
import logging
import shlex
import shutil
import time
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class ToolStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    SUCCESS   = "success"
    FAILED    = "failed"
    TIMEOUT   = "timeout"
    NOT_FOUND = "not_found"


@dataclass
class ToolResult:
    tool_name   : str
    command     : str                        # the full command string that was run
    status      : ToolStatus
    stdout      : str = ""
    stderr      : str = ""
    return_code : int = -1
    duration_ms : int = 0
    findings    : List[Dict[str, Any]] = field(default_factory=list)
    error       : Optional[str] = None


# ---------------------------------------------------------------------------
# Command builders  –  one per tool family
# ---------------------------------------------------------------------------
# Each function returns the *exact* CLI string that will be executed.
# Parameters are validated here so nothing unsanitised reaches the shell.

def _sanitise(value: str) -> str:
    """Strip anything that isn't alphanumeric, dot, dash, colon, slash, or underscore."""
    return re.sub(r'[^\w.\-:/]', '', str(value))


def build_nmap(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    flags = ["-sV", "-sC"]                          # version + default scripts
    if params.get("os_detection"):
        flags.append("-O")
    if params.get("version_detection"):
        flags.append("-sV")                         # already there, but explicit
    ports = params.get("ports", "top-1000")
    if ports == "top-1000":
        flags.append("--top-ports 1000")
    elif ports == "1-65535":
        flags.append("-p-")
    else:
        flags.append(f"-p {_sanitise(ports)}")
    timing = params.get("timing", "3")
    flags.append(f"-T{_sanitise(timing)}")
    flags.append("-oA /tmp/errorz_nmap")            # all output formats
    return "nmap " + " ".join(flags) + " " + t


def build_sqlmap(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    flags = ["--batch", "--level=3", "--risk=2"]
    if params.get("dbs"):
        flags.append("--dbs")
    if params.get("dump"):
        flags.append("--dump")
    return f"sqlmap -u http://{t} " + " ".join(flags)


def build_nikto(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    return f"nikto -h {t} -o /tmp/errorz_nikto.html -format html"


def build_gobuster(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    wordlist = params.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
    wordlist = _sanitise(wordlist)
    threads  = params.get("threads", "50")
    return f"gobuster dir -u http://{t} -w {wordlist} -t {_sanitise(threads)}"


def build_hydra(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    service  = params.get("service", "ssh")
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    user     = params.get("username", "root")
    return f"hydra -l {_sanitise(user)} -P {_sanitise(wordlist)} {t} {_sanitise(service)}"


def build_hashcat(target: str, params: Dict[str, Any]) -> str:
    """target here is the hash string itself."""
    h = _sanitise(target)
    mode     = params.get("hash_mode", "0")         # 0 = MD5 default
    wordlist = params.get("wordlist", "/usr/share/wordlists/rockyou.txt")
    return f"hashcat -m {_sanitise(mode)} -a 0 {h} {_sanitise(wordlist)}"


def build_subfinder(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    return f"subfinder -d {t} -o /tmp/errorz_subfinder.txt -json"


def build_nuclei(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    return f"nuclei -t http://{t} -json -o /tmp/errorz_nuclei.json"


def build_amass(target: str, params: Dict[str, Any]) -> str:
    t = _sanitise(target)
    return f"amass enum -d {t} -o /tmp/errorz_amass.txt -json"


def build_metasploit(target: str, params: Dict[str, Any]) -> str:
    module  = params.get("module", "")
    options = params.get("options", {})
    # Build a resource script that msfconsole will consume
    lines = []
    if module:
        lines.append(f"use {module}")
        lines.append(f"set RHOSTS {_sanitise(target)}")
        for k, v in options.items():
            lines.append(f"set {_sanitise(k)} {_sanitise(str(v))}")
        lines.append("run")
        lines.append("exit")
    else:
        lines.append(f"search type:exploit target:{_sanitise(target)}")
        lines.append("exit")
    resource_path = "/tmp/errorz_msf_resource.rc"
    Path(resource_path).write_text("\n".join(lines))
    return f"msfconsole -r {resource_path} -q"


# ---------------------------------------------------------------------------
# Command builder registry
# ---------------------------------------------------------------------------

COMMAND_BUILDERS: Dict[str, Any] = {
    "nmap"       : build_nmap,
    "sqlmap"     : build_sqlmap,
    "nikto"      : build_nikto,
    "gobuster"   : build_gobuster,
    "hydra"      : build_hydra,
    "hashcat"    : build_hashcat,
    "subfinder"  : build_subfinder,
    "nuclei"     : build_nuclei,
    "amass"      : build_amass,
    "metasploit" : build_metasploit,
}

# Default timeout (seconds) per tool.  Can be overridden in params.
DEFAULT_TIMEOUTS: Dict[str, int] = {
    "nmap": 300, "sqlmap": 600, "nikto": 180, "gobuster": 600,
    "hydra": 600, "hashcat": 1800, "subfinder": 120, "nuclei": 300,
    "amass": 300, "metasploit": 600,
}


# ---------------------------------------------------------------------------
# Generic fallback  –  for tools NOT in the builder registry
# ---------------------------------------------------------------------------

def build_generic(tool_name: str, target: str, params: Dict[str, Any]) -> str:
    """
    Last-resort builder.  Assembles:  <tool> <target> [--extra from params]
    The universal_adapter can feed extra_flags via params["extra_flags"].
    """
    flags = params.get("extra_flags", [])
    flag_str = " ".join(_sanitise(f) for f in flags) if flags else ""
    return f"{_sanitise(tool_name)} {_sanitise(target)} {flag_str}".strip()


# ---------------------------------------------------------------------------
# Output parsers  –  extract structured findings from raw stdout
# ---------------------------------------------------------------------------

def parse_nmap_output(stdout: str) -> List[Dict[str, Any]]:
    findings = []
    for line in stdout.splitlines():
        m = re.match(r"(\d+)/(\w+)\s+(\w+)\s+(.*)", line.strip())
        if m:
            findings.append({
                "port": m.group(1), "protocol": m.group(2),
                "state": m.group(3), "service": m.group(4).strip(),
            })
    return findings


def parse_subfinder_output(stdout: str) -> List[Dict[str, Any]]:
    return [{"subdomain": line.strip()} for line in stdout.splitlines() if line.strip()]


def parse_gobuster_output(stdout: str) -> List[Dict[str, Any]]:
    findings = []
    for line in stdout.splitlines():
        m = re.match(r"Found:\s+(/\S+)\s+\(Status:\s+(\d+)\)", line)
        if m:
            findings.append({"path": m.group(1), "status_code": m.group(2)})
    return findings


def parse_nuclei_output(stdout: str) -> List[Dict[str, Any]]:
    import json as _json
    findings = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = _json.loads(line)
            findings.append({
                "template": obj.get("template-id", "unknown"),
                "severity": obj.get("info", {}).get("severity", "info"),
                "matched" : obj.get("matched-at", ""),
            })
        except _json.JSONDecodeError:
            continue
    return findings


# Generic parser – just keep non-empty lines as raw findings
def parse_generic_output(stdout: str) -> List[Dict[str, Any]]:
    return [{"raw": line} for line in stdout.splitlines() if line.strip()]


OUTPUT_PARSERS: Dict[str, Any] = {
    "nmap"      : parse_nmap_output,
    "subfinder" : parse_subfinder_output,
    "gobuster"  : parse_gobuster_output,
    "nuclei"    : parse_nuclei_output,
}


# ---------------------------------------------------------------------------
# Execution engine
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Async executor.  Usage:

        executor = ToolExecutor()
        result   = await executor.run("nmap", "192.168.1.1", {"timing":"4"})
        print(result.findings)
    """

    def __init__(self, on_line: Optional[Any] = None):
        """
        on_line – optional async callback(tool_name: str, line: str)
                  called for every stdout line (feeds live dashboard).
        """
        self.on_line = on_line

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    async def run(self, tool_name: str, target: str,
                  params: Optional[Dict[str, Any]] = None) -> ToolResult:
        params = params or {}

        # 1. Locate the binary
        binary = tool_name if tool_name != "metasploit" else "msfconsole"
        if not shutil.which(binary):
            return ToolResult(
                tool_name=tool_name, command="", status=ToolStatus.NOT_FOUND,
                error=f"'{binary}' not found in PATH.  Install it or add to PATH."
            )

        # 2. Build the command string
        builder = COMMAND_BUILDERS.get(tool_name)
        if builder:
            cmd_str = builder(target, params)
        else:
            cmd_str = build_generic(tool_name, target, params)

        # 3. Timeout
        timeout = params.get("timeout", DEFAULT_TIMEOUTS.get(tool_name, 120))

        # 4. Execute
        return await self._execute(tool_name, cmd_str, timeout)

    # ------------------------------------------------------------------
    # Subprocess management
    # ------------------------------------------------------------------

    async def _execute(self, tool_name: str, cmd_str: str, timeout: int) -> ToolResult:
        logger.info("ToolExecutor starting: %s", cmd_str)
        start = time.time()
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Stream stdout line by line
            async def _read_stream(stream, collector, is_stdout=False):
                while True:
                    raw = await stream.readline()
                    if not raw:
                        break
                    line = raw.decode("utf-8", errors="replace").rstrip()
                    collector.append(line)
                    if is_stdout and self.on_line:
                        await self.on_line(tool_name, line)

            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(proc.stdout, stdout_lines, is_stdout=True),
                    _read_stream(proc.stderr, stderr_lines),
                ),
                timeout=timeout,
            )
            await proc.wait()
            rc = proc.returncode

        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(
                tool_name=tool_name, command=cmd_str,
                status=ToolStatus.TIMEOUT,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
                duration_ms=int((time.time() - start) * 1000),
                error=f"Tool timed out after {timeout}s",
            )
        except Exception as exc:
            return ToolResult(
                tool_name=tool_name, command=cmd_str,
                status=ToolStatus.FAILED,
                error=str(exc),
                duration_ms=int((time.time() - start) * 1000),
            )

        duration_ms = int((time.time() - start) * 1000)
        full_stdout = "\n".join(stdout_lines)

        # 5. Parse output into findings
        parser = OUTPUT_PARSERS.get(tool_name, parse_generic_output)
        findings = parser(full_stdout)

        status = ToolStatus.SUCCESS if rc == 0 else ToolStatus.FAILED

        return ToolResult(
            tool_name   = tool_name,
            command     = cmd_str,
            status      = status,
            stdout      = full_stdout,
            stderr      = "\n".join(stderr_lines),
            return_code = rc,
            duration_ms = duration_ms,
            findings    = findings,
        )

    # ------------------------------------------------------------------
    # Batch  –  run multiple tools sequentially or in parallel
    # ------------------------------------------------------------------

    async def run_batch(self, tasks: List[Dict[str, Any]],
                        parallel: bool = False) -> List[ToolResult]:
        """
        tasks = [ {"tool": "nmap", "target": "x.x.x.x", "params": {...}}, ... ]
        """
        if parallel:
            coros = [self.run(t["tool"], t["target"], t.get("params")) for t in tasks]
            return await asyncio.gather(*coros)
        else:
            results = []
            for t in tasks:
                results.append(await self.run(t["tool"], t["target"], t.get("params")))
            return results
