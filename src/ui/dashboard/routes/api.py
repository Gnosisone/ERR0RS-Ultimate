# src/ui/dashboard/routes/api.py
# ERR0RS-Ultimate — REST API blueprint
# All JSON endpoints the dashboard JS and external callers hit.
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import os
from flask import Blueprint, current_app, jsonify, request, abort

api_bp = Blueprint("api", __name__)


def _pm():
    return current_app.config.get("PLUGIN_MANAGER")

def _hm():
    return current_app.config.get("HARDWARE_MANAGER")

def _rg():
    return current_app.config.get("REPORT_GENERATOR")

def _we():
    return current_app.config.get("WORKFLOW_ENGINE")

def _ctx():
    return current_app.config.get("SHARED_CTX")


# ── Health ────────────────────────────────────────────────────────────────────

@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "ERR0RS-Ultimate"})


# ── Session ───────────────────────────────────────────────────────────────────

@api_bp.route("/session")
def session_summary():
    ctx = _ctx()
    if not ctx:
        return jsonify({"error": "No active session"}), 503
    return jsonify(ctx.summary())


# ── Plugins ───────────────────────────────────────────────────────────────────

@api_bp.route("/plugins")
def list_plugins():
    pm = _pm()
    if not pm:
        return jsonify([])
    return jsonify(pm.list_plugins())


@api_bp.route("/plugins/commands")
def plugin_commands():
    pm = _pm()
    if not pm:
        return jsonify({})
    return jsonify(pm.get_available_commands())


@api_bp.route("/plugins/run", methods=["POST"])
def run_plugin():
    """
    Body: {"command": "scan", "target": "192.168.1.1", "args": {...}}
    """
    pm   = _pm()
    ctx  = _ctx()
    data = request.get_json(silent=True) or {}

    command = data.get("command", "")
    target  = data.get("target", "")
    args    = data.get("args", {})

    if not pm or not command:
        return jsonify({"error": "Missing plugin_manager or command"}), 400

    if target:
        args.setdefault("target", target)
        if ctx:
            ctx.set_active_target(target)

    result = pm.execute(command, args)
    return jsonify({"command": command, "target": target, "result": str(result)})


@api_bp.route("/findings")
def get_findings():
    ctx = _ctx()
    if not ctx or not hasattr(ctx, "get_findings"):
        return jsonify([])
    plugin = request.args.get("plugin")
    ftype  = request.args.get("type")
    return jsonify(ctx.get_findings(plugin=plugin, finding_type=ftype))


# ── Hardware ──────────────────────────────────────────────────────────────────

@api_bp.route("/devices")
def list_devices():
    hm = _hm()
    if not hm:
        return jsonify([])
    return jsonify(hm.list_devices())


@api_bp.route("/devices/status")
def devices_status():
    hm = _hm()
    if not hm:
        return jsonify({})
    return jsonify(hm.status_all())


@api_bp.route("/devices/probe")
def probe_devices():
    hm = _hm()
    if not hm:
        return jsonify({})
    return jsonify(hm.probe_all())


@api_bp.route("/devices/deploy", methods=["POST"])
def deploy_payload():
    """
    Body: {"device": "flipper", "payload": "rfid_read", "args": {...}}
    """
    hm   = _hm()
    data = request.get_json(silent=True) or {}

    device  = data.get("device", "")
    payload = data.get("payload", "")
    args    = data.get("args", {})

    if not hm or not device or not payload:
        return jsonify({"error": "Missing device or payload"}), 400

    result = hm.execute(device, payload, args)
    return jsonify(result.to_dict())


@api_bp.route("/devices/safe_mode", methods=["POST"])
def set_safe_mode():
    hm      = _hm()
    data    = request.get_json(silent=True) or {}
    enabled = bool(data.get("enabled", True))
    if hm:
        hm.set_safe_mode(enabled)
    return jsonify({"safe_mode": enabled})


# ── Workflows ─────────────────────────────────────────────────────────────────

@api_bp.route("/workflows")
def list_workflows():
    we = _we()
    if not we:
        return jsonify([])
    return jsonify(we.list())


@api_bp.route("/workflows/describe/<name>")
def describe_workflow(name: str):
    we = _we()
    if not we:
        return jsonify({"error": "Workflow engine unavailable"}), 503
    wf = we.describe(name)
    if not wf:
        return jsonify({"error": f"Workflow '{name}' not found"}), 404
    return jsonify(wf)


@api_bp.route("/workflows/run", methods=["POST"])
def run_workflow():
    """
    Body: {"workflow": "webapp", "target": "192.168.1.1"}
    Runs synchronously — use SocketIO run_workflow event for async.
    """
    we   = _we()
    data = request.get_json(silent=True) or {}
    name = data.get("workflow", "quick")
    tgt  = data.get("target", "")
    if not we or not tgt:
        return jsonify({"error": "Missing workflow_engine or target"}), 400
    summary = we.run(name, tgt)
    return jsonify(summary)


# ── Reports ───────────────────────────────────────────────────────────────────

@api_bp.route("/reports")
def list_reports():
    rg = _rg()
    report_dir = getattr(rg, "report_dir", "reports") if rg else "reports"
    if not os.path.isdir(report_dir):
        return jsonify([])
    files = sorted(
        f for f in os.listdir(report_dir)
        if f.endswith((".md", ".html", ".json"))
    )
    return jsonify(files)


@api_bp.route("/reports/generate", methods=["POST"])
def generate_report():
    """
    Body: {"target": "192.168.1.1", "session_id": "AB12",
           "formats": ["md","html","json"], "enhance_ai": false}
    """
    rg   = _rg()
    data = request.get_json(silent=True) or {}

    if not rg:
        return jsonify({"error": "Report generator unavailable"}), 503

    target      = data.get("target", "")
    session_id  = data.get("session_id", "")
    formats     = data.get("formats", ["md", "html"])
    enhance_ai  = bool(data.get("enhance_ai", False))

    report = rg.generate(target=target, session_id=session_id, enhance_ai=enhance_ai)

    saved = {}
    base  = f"report_{session_id or 'latest'}"
    if "md"   in formats:
        saved["md"]   = rg.save_markdown(report, f"{base}.md")
    if "html" in formats:
        saved["html"] = rg.save_html(report, f"{base}.html")
    if "json" in formats:
        saved["json"] = rg.save_json(report, f"{base}.json")

    return jsonify({"saved": saved, "stats": report["stats"]})
