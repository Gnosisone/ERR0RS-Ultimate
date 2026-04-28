"""
ERR0RS Flipper Agent
====================
ReAct tool definitions + FastAPI route registration.
The ERR0RS AI brain uses these to command the Flipper as a
physical sensor/executor during authorized engagements.

Author: ERR0RS Project | Gary Holden Schneider (Eros)
"""

import json
import asyncio
from typing import Optional
from datetime import datetime

from .flipper_bridge import get_bridge, FlipperBridge
from .flipper_ota import maybe_provision


# ─────────────────────────────────────────────
#  Tool definitions (ERR0RS ReAct format)
# ─────────────────────────────────────────────

FLIPPER_TOOLS = [
    {
        "name": "flipper_connect",
        "description": (
            "Connect to the Flipper Zero hardware via USB serial. "
            "Call before any other Flipper tool. Returns device info."
        ),
        "parameters": {
            "port": {"type": "string", "required": False,
                     "description": "e.g. /dev/ttyACM0 or COM3. Omit for auto-detect."}
        }
    },
    {
        "name": "flipper_status",
        "description": "Get Flipper Zero connection status, battery, firmware, storage.",
        "parameters": {}
    },
    {
        "name": "flipper_subghz_capture",
        "description": (
            "Capture SubGHz RF signals on a specified frequency. "
            "Use during authorized physical pentests to identify RF-controlled "
            "access systems, gate controllers, and wireless sensors. "
            "Results are automatically analyzed by ERR0RS."
        ),
        "parameters": {
            "frequency_mhz": {
                "type": "number", "required": True,
                "description": (
                    "Frequency in MHz. Common: "
                    "433.92 (EU/AU keyfobs), 315.0 (US/JP keyfobs), "
                    "868.35 (EU ISM), 915.0 (US ISM)"
                )
            },
            "duration_sec": {"type": "integer", "required": False,
                             "description": "Capture duration seconds (default 10)"},
            "engagement_id": {"type": "string", "required": False}
        }
    },
    {
        "name": "flipper_nfc_dump",
        "description": (
            "Read and dump an NFC card held against the Flipper. "
            "ERR0RS identifies card type and assesses for known vulnerabilities."
        ),
        "parameters": {
            "engagement_id": {"type": "string", "required": False}
        }
    },
    {
        "name": "flipper_push_payload",
        "description": (
            "Push a DuckyScript BadUSB payload to Flipper SD card. "
            "Requires active engagement_id. Physical execution by authorized tester only."
        ),
        "parameters": {
            "payload_name": {"type": "string", "required": True},
            "duckyscript":  {"type": "string", "required": True},
            "engagement_id":{"type": "string", "required": True}
        }
    },
    {
        "name": "flipper_ir_capture",
        "description": (
            "Capture infrared signals. Useful for meeting room A/V, "
            "IR-controlled locks, smart building systems."
        ),
        "parameters": {
            "duration_sec": {"type": "integer", "required": False},
            "engagement_id": {"type": "string", "required": False}
        }
    },
    {
        "name": "flipper_analyze_capture",
        "description": (
            "Send capture data to ERR0RS AI for protocol analysis, "
            "CVE correlation, attack surface assessment, and report findings."
        ),
        "parameters": {
            "capture_data": {"type": "object", "required": True},
            "engagement_context": {"type": "string", "required": False}
        }
    },
]


# ─────────────────────────────────────────────
#  Agent executor
# ─────────────────────────────────────────────

class FlipperAgent:
    """
    Executes Flipper tool calls from the ERR0RS ReAct agent loop.
    Returns structured results that feed back into the reasoning chain.
    """

    def __init__(self, rag_store=None, report_gen=None):
        self.bridge     = get_bridge()
        self.rag_store  = rag_store
        self.report_gen = report_gen

    async def execute(self, tool_name: str, params: dict) -> dict:
        handlers = {
            "flipper_connect":         self._connect,
            "flipper_status":          self._status,
            "flipper_subghz_capture":  self._subghz_capture,
            "flipper_nfc_dump":        self._nfc_dump,
            "flipper_push_payload":    self._push_payload,
            "flipper_ir_capture":      self._ir_capture,
            "flipper_analyze_capture": self._analyze_capture,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}
        try:
            result = await handler(params)
            if self.rag_store and "err0rs_context" in result:
                await self._ingest_to_rag(result)
            return result
        except Exception as e:
            return {"status": "error", "tool": tool_name, "message": str(e)}

    async def _connect(self, params: dict) -> dict:
        port = params.get("port")
        if port:
            self.bridge.port = port
        result = await self.bridge.async_connect()
        # Run OTA provisioning on first connect — pushes assets,
        # patches config, checks firmware. Skips if already done
        # this session. confirm_callback and progress_callback can be
        # injected via FlipperAgent constructor kwargs.
        if result.get("status") in ("connected",):
            ota_result = await maybe_provision(
                self.bridge,
                confirm_callback=getattr(self, "confirm_callback", None),
                progress_callback=getattr(self, "progress_callback", None),
            )
            if ota_result:
                result["ota"] = ota_result
        return result

    async def _status(self, params: dict) -> dict:
        return await asyncio.to_thread(self.bridge.get_status)

    async def _subghz_capture(self, params: dict) -> dict:
        return await self.bridge.async_capture_subghz(
            frequency_mhz=params.get("frequency_mhz", 433.92),
            duration_sec=params.get("duration_sec", 10),
            engagement_id=params.get("engagement_id")
        )

    async def _nfc_dump(self, params: dict) -> dict:
        return await self.bridge.async_dump_nfc(
            engagement_id=params.get("engagement_id")
        )

    async def _push_payload(self, params: dict) -> dict:
        return await self.bridge.async_push_badusb_payload(
            payload_name=params["payload_name"],
            duckyscript=params["duckyscript"],
            engagement_id=params.get("engagement_id")
        )

    async def _ir_capture(self, params: dict) -> dict:
        return await asyncio.to_thread(
            self.bridge.capture_ir,
            duration_sec=params.get("duration_sec", 5),
            engagement_id=params.get("engagement_id")
        )

    async def _analyze_capture(self, params: dict) -> dict:
        capture   = params.get("capture_data", {})
        extra_ctx = params.get("engagement_context", "")
        prompt = f"""You are ERR0RS, an AI penetration testing assistant.
Analyze the following hardware capture from a Flipper Zero
during an authorized security engagement.

CAPTURE DATA:
{json.dumps(capture, indent=2)}

ENGAGEMENT CONTEXT: {extra_ctx}

Provide:
1. Protocol identification and security assessment
2. Known CVEs or published research relevant to this protocol/frequency
3. Attack surface summary
4. Defensive recommendations for the client report
5. Severity rating (Critical/High/Medium/Low/Informational)
"""
        return {
            "status": "ok",
            "analysis_prompt": prompt,
            "capture_summary": capture.get("err0rs_context", ""),
            "timestamp": datetime.now().isoformat(),
        }

    async def _ingest_to_rag(self, result: dict):
        if not self.rag_store:
            return
        try:
            doc_id  = f"flipper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            context = result.get("err0rs_context", "")
            meta    = {
                "source":        "flipper_zero",
                "engagement_id": result.get("engagement_id", ""),
                "timestamp":     datetime.now().isoformat(),
                "type":          "hardware_capture"
            }
            await asyncio.to_thread(
                self.rag_store.add,
                documents=[context],
                ids=[doc_id],
                metadatas=[meta]
            )
        except Exception as e:
            print(f"[FlipperAgent] RAG ingest warning: {e}")


# ─────────────────────────────────────────────
#  FastAPI route registration
# ─────────────────────────────────────────────

def register_flipper_routes(app, rag_store=None, report_gen=None):
    """
    Call from main.py after FastAPI app creation:
        from src.tools.flipper.flipper_agent import register_flipper_routes
        register_flipper_routes(app, rag_store=collection)
    """
    from fastapi import HTTPException
    from pydantic import BaseModel

    agent = FlipperAgent(rag_store=rag_store, report_gen=report_gen)

    class ToolCall(BaseModel):
        tool: str
        params: dict = {}

    @app.post("/flipper/execute")
    async def flipper_execute(call: ToolCall):
        result = await agent.execute(call.tool, call.params)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result["message"])
        return result

    @app.get("/flipper/tools")
    async def flipper_tools():
        return {"tools": FLIPPER_TOOLS}

    @app.get("/flipper/status")
    async def flipper_status():
        return await agent.execute("flipper_status", {})

    print("[ERR0RS] Flipper routes: /flipper/execute | /flipper/tools | /flipper/status")
