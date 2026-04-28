# src/ui/dashboard/app.py
# ERR0RS-Ultimate — Flask + SocketIO Live Dashboard
# Real-time pentest operations dashboard with WebSocket event streaming.
# Serves: live activity feed, device status, report list, plugin runner.
#
# Start: python -m src.ui.dashboard.app
# or via main.py --dashboard
#
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

from __future__ import annotations
import logging
import os
import sys

logger = logging.getLogger("Dashboard")


def create_app(
    plugin_manager=None,
    hardware_manager=None,
    report_generator=None,
    workflow_engine=None,
    ctx=None,
    secret_key: str = None,
    debug: bool = False,
):
    """
    Flask application factory.
    All ERR0RS subsystems are injected so the app never imports them globally
    (avoids circular imports and makes unit testing trivial).
    """
    try:
        from flask import Flask
        from flask_socketio import SocketIO
    except ImportError:
        logger.error(
            "Flask/Flask-SocketIO not installed.\n"
            "pip install flask flask-socketio --break-system-packages"
        )
        return None, None

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.secret_key = (
        secret_key
        or os.environ.get("ERR0RS_SECRET", "err0rs-dev-secret-change-in-prod")
    )

    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=False,
        engineio_logger=False,
    )

    # ── Attach subsystems to app context ──────────────────────────────────
    app.config["PLUGIN_MANAGER"]   = plugin_manager
    app.config["HARDWARE_MANAGER"] = hardware_manager
    app.config["REPORT_GENERATOR"] = report_generator
    app.config["WORKFLOW_ENGINE"]  = workflow_engine
    app.config["SHARED_CTX"]       = ctx

    # Ensure DB schema exists
    try:
        from src.core.db import init_db
        init_db()
    except Exception as _dbe:
        logger.warning(f"DB init warning: {_dbe}")

    # ── Wire event bus → SocketIO ─────────────────────────────────────────
    if ctx and hasattr(ctx, "event_bus"):
        _wire_event_bus(ctx.event_bus, socketio)

    # ── Register blueprints ───────────────────────────────────────────────
    from .routes.pages import pages_bp
    from .routes.api   import api_bp
    from .auth         import auth_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp)

    # ── SocketIO event handlers ───────────────────────────────────────────
    _register_socket_handlers(socketio, app)

    return app, socketio


def _wire_event_bus(event_bus, socketio):
    """Bridge SharedContext EventBus → SocketIO so dashboard gets live events."""
    RELAY_EVENTS = [
        "workflow_start", "workflow_step", "workflow_complete",
        "command_result", "ai_decision", "device.action",
        "device.success", "device.error", "finding.added",
        "analysis_complete", "scan.complete",
    ]
    for evt in RELAY_EVENTS:
        # Closure capture
        def make_handler(event_name):
            def handler(_, data):
                try:
                    socketio.emit(event_name, data or {})
                except Exception as e:
                    logger.debug(f"SocketIO relay error on '{event_name}': {e}")
            return handler
        event_bus.on(evt, make_handler(evt))


def _register_socket_handlers(socketio, app):
    from flask_socketio import emit as sio_emit

    @socketio.on("connect")
    def handle_connect():
        ctx = app.config.get("SHARED_CTX")
        if ctx:
            sio_emit("session_summary", ctx.summary())
        logger.debug("Dashboard client connected.")

    @socketio.on("disconnect")
    def handle_disconnect():
        logger.debug("Dashboard client disconnected.")

    @socketio.on("run_scan")
    def handle_run_scan(data):
        """Client requests an immediate scan."""
        pm     = app.config.get("PLUGIN_MANAGER")
        target = data.get("target", "")
        if not pm or not target:
            sio_emit("error", {"message": "Missing plugin_manager or target."})
            return
        result = pm.execute("scan", {"target": target})
        sio_emit("command_result", {"command": "scan", "result": str(result)})

    @socketio.on("run_workflow")
    def handle_run_workflow(data):
        """Client requests a workflow run."""
        import threading
        we     = app.config.get("WORKFLOW_ENGINE")
        name   = data.get("workflow", "quick")
        target = data.get("target", "")
        if not we or not target:
            sio_emit("error", {"message": "Missing workflow_engine or target."})
            return
        # Run in background thread so socket doesn't block
        t = threading.Thread(
            target=we.run, args=(name, target), daemon=True
        )
        t.start()
        sio_emit("workflow_queued", {"workflow": name, "target": target})

    @socketio.on("deploy_payload")
    def handle_deploy(data):
        """Client requests hardware payload deployment."""
        hm      = app.config.get("HARDWARE_MANAGER")
        device  = data.get("device", "")
        payload = data.get("payload", "")
        if not hm or not device or not payload:
            sio_emit("error", {"message": "Missing hardware_manager, device, or payload."})
            return
        result = hm.execute(device, payload)
        sio_emit("device.action", result.to_dict())


def run_dashboard(
    plugin_manager=None,
    hardware_manager=None,
    report_generator=None,
    workflow_engine=None,
    ctx=None,
    host: str  = "127.0.0.1",
    port: int  = 5000,
    debug: bool = False,
):
    """Convenience runner — creates and starts the dashboard app."""
    app, socketio = create_app(
        plugin_manager   = plugin_manager,
        hardware_manager = hardware_manager,
        report_generator = report_generator,
        workflow_engine  = workflow_engine,
        ctx              = ctx,
        debug            = debug,
    )
    if not app:
        return
    print(f"\n  \033[92m🌐 ERR0RS Dashboard\033[0m → http://{host}:{port}")
    print(f"  API:  http://{host}:{port}/api/")
    print(f"  Docs: http://{host}:{port}/api/docs\n")
    socketio.run(app, host=host, port=port, debug=debug,
                 use_reloader=False, allow_unsafe_werkzeug=True)
