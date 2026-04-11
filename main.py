"""
ERR0RS ULTIMATE - Main Entry Point
=====================================
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

Usage:
    python main.py                          # Interactive terminal mode
    python main.py --api                    # Start FastAPI server
    python main.py --dashboard              # Start live dashboard (Flask+SocketIO)
    python main.py --dashboard --port 5000  # Dashboard on custom port
    python main.py --agent blue_team        # Start with specific agent
    python main.py --backend anthropic      # Use Claude API
    python main.py --query "enum SMB"       # Single query mode
    python main.py --workflow webapp 10.0.0.1   # Run a workflow directly
    python main.py --report 10.0.0.1        # Generate a report
    python main.py --learn                  # Enable education mode globally
    python main.py --safe                   # Enable safe mode (no real hardware)
"""

import argparse
import os
import sys
import logging

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                override=False)
except ImportError:
    pass

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [ERR0RS] %(levelname)s %(name)s — %(message)s",
)
_log = logging.getLogger("ERR0RS")

ROOT = os.path.dirname(os.path.abspath(__file__))

# ═════════════════════════════════════════════════════════════════════════════
# BANNER
# ═════════════════════════════════════════════════════════════════════════════

BANNER = r"""
  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
   ULTIMATE — AI-Powered Penetration Testing Platform
   Gary Holden Schneider (Eros) | github.com/Gnosisone
"""

# ═════════════════════════════════════════════════════════════════════════════
# BOOT HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _boot_plugin_system(config: dict = None):
    """SharedContext + PluginManager. Returns (ctx, pm)."""
    try:
        from src.core.context      import SharedContext
        from src.core.plugin_manager import PluginManager

        ctx = SharedContext(config=config or {})

        # Live event logging
        ctx.event_bus.on("finding.added",
            lambda e, d: _log.info(f"[FIND] {d.get('severity','?').upper()} — {d.get('title', d.get('type','?'))}"))
        ctx.event_bus.on("hardware.connected",
            lambda e, d: _log.info(f"[HW] {d.get('name','?')} online"))
        ctx.event_bus.on("scan.complete",
            lambda e, d: _log.info(f"[SCAN] {d.get('target','?')} complete"))

        pm = PluginManager(
            plugin_dir=os.path.join(ROOT, "src", "plugins"),
            context=ctx,
        )
        pm.load_plugins()
        loaded = [p["name"] for p in pm.list_plugins()]
        if loaded:
            _log.warning(f"Plugins: {', '.join(loaded)}")
        return ctx, pm
    except Exception as e:
        _log.error(f"Plugin boot failed: {e}")
        return None, None


def _boot_hardware(ctx, safe_mode: bool = False):
    """HardwareManager wired to SharedContext event bus."""
    try:
        from src.core.hardware import HardwareManager
        hm = HardwareManager(
            event_bus=ctx.event_bus if ctx else None,
            safe_mode=safe_mode,
            config={
                "flipper_port": os.environ.get("FLIPPER_PORT", "/dev/ttyACM0"),
            },
        )
        _log.warning(f"Hardware: {[d['name'] for d in hm.list_devices()]}")
        return hm
    except Exception as e:
        _log.error(f"Hardware boot failed: {e}")
        return None


def _boot_workflow(pm, interpreter, ctx, event_bus=None,
                   learn_mode=False, safe_mode=False):
    """WorkflowEngine ready to run YAML workflows."""
    try:
        from src.core.workflow import WorkflowEngine
        return WorkflowEngine(
            plugin_manager = pm,
            interpreter    = interpreter,
            memory         = ctx,
            event_bus      = event_bus,
            learn_mode     = learn_mode,
            safe_mode      = safe_mode,
            workflow_dir   = os.path.join(ROOT, "workflows"),
        )
    except Exception as e:
        _log.error(f"Workflow engine boot failed: {e}")
        return None


def _boot_reports(ctx, report_dir=None):
    """ReportGenerator pointed at shared context memory."""
    try:
        from src.reporting.report_generator import ReportGenerator
        return ReportGenerator(
            memory     = ctx,
            report_dir = report_dir or os.path.join(ROOT, "reports"),
        )
    except Exception as e:
        _log.error(f"Report generator boot failed: {e}")
        return None

# ═════════════════════════════════════════════════════════════════════════════
# MODES
# ═════════════════════════════════════════════════════════════════════════════

def interactive_mode(ai, agent_type="red_team", ctx=None, pm=None,
                     workflow_engine=None, hardware_manager=None,
                     report_generator=None, learn_mode=False):
    """Full interactive terminal session with all subsystems."""
    try:
        from src.ai.agents import list_agents
        agents_list = list_agents()
    except Exception:
        agents_list = []

    print(BANNER)
    print(f"  Agent        : {agent_type}")
    print(f"  LLM          : {getattr(getattr(ai,'llm',None),'backend','?')} "
          f"({getattr(getattr(ai,'llm',None),'model','?')})")
    print(f"  RAG          : {'✅' if getattr(ai,'_kb_available',False) else '⚠️  keyword fallback'}")
    if pm:
        cmds = []
        for p in pm.list_plugins():
            cmds.extend(p.get("commands", []))
        print(f"  Plugins      : {len(pm.list_plugins())} | cmds: {', '.join(cmds) or 'none'}")
    if workflow_engine:
        print(f"  Workflows    : {', '.join(workflow_engine.list())}")
    if hardware_manager:
        devs = hardware_manager.list_devices()
        print(f"  Hardware     : {len(devs)} device(s) registered")
    if learn_mode:
        print("  \033[94m📘 Learn mode ON\033[0m")
    print("\n  Commands: target | run | workflow | autopilot | report | devices | deploy")
    print("            explain | learn | agent | plugins | status | exit")
    print("  ─────────────────────────────────────────────────────────────\n")

    current_agent = agent_type

    while True:
        try:
            raw = input(f"\033[92mERR0RS\033[0m [{current_agent}]> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Shutting down. Stay ethical. 🔥")
            break

        if not raw:
            continue
        parts = raw.split()
        cmd   = parts[0].lower()

        # ── Exit ──────────────────────────────────────────────────
        if cmd in ("exit", "quit", "q"):
            print("  Shutting down. Stay ethical. 🔥")
            break

        # ── Status ────────────────────────────────────────────────
        elif cmd == "status":
            import json
            data = {}
            if ctx:
                data["session"] = ctx.summary()
            data["ai"] = ai.status() if hasattr(ai, "status") else {}
            print(json.dumps(data, indent=2, default=str))

        # ── Agent switch ──────────────────────────────────────────
        elif cmd == "agent" and len(parts) > 1:
            current_agent = parts[1]
            print(f"  Switched to: {current_agent}")

        # ── Target ────────────────────────────────────────────────
        elif cmd == "target" and len(parts) > 1 and ctx:
            ctx.set_active_target(parts[1])
            print(f"  Target → {parts[1]}")

        # ── Plugins ───────────────────────────────────────────────
        elif cmd == "plugins" and pm:
            import json as _j
            print(_j.dumps(pm.list_plugins(), indent=2))

        # ── Run plugin command ────────────────────────────────────
        elif cmd == "run" and pm:
            if len(parts) < 2:
                print("  Usage: run <command> [target]")
                continue
            pcmd   = parts[1]
            target = parts[2] if len(parts) > 2 else (ctx.get_active_target() if ctx else None)
            if ctx and target:
                ctx.set_active_target(target)
            result = pm.execute(pcmd, {"target": target})
            print(f"\n{result}\n")

        # ── Workflow ──────────────────────────────────────────────
        elif cmd == "workflow" and workflow_engine:
            if len(parts) < 3:
                print(f"  Usage: workflow <name> <target>")
                print(f"  Available: {', '.join(workflow_engine.list())}")
                continue
            wf_name = parts[1]
            target  = parts[2]
            if ctx:
                ctx.set_active_target(target)
            workflow_engine.executor.learn_mode = learn_mode
            workflow_engine.run(wf_name, target)

        # ── Autopilot ─────────────────────────────────────────────
        elif cmd == "autopilot":
            if len(parts) < 2:
                print("  Usage: autopilot <target>")
                continue
            target = parts[1]
            try:
                from src.core.autopilot    import AutoPilot
                from src.core.interpreter  import Interpreter
                from src.core.command_router import CommandRouter
                interp = Interpreter()
                router = CommandRouter(
                    ai_brain=ai, plugin_manager=pm,
                    interpreter=interp, context=ctx,
                )
                ap = AutoPilot(router=router, ctx=ctx)
                ap.run(target)
            except Exception as e:
                print(f"  Autopilot error: {e}")

        # ── Explain / Learn ───────────────────────────────────────
        elif cmd in ("explain", "learn") and len(parts) > 1:
            topic = " ".join(parts[1:])
            try:
                from src.education_new.teach_engine import TeachEngine
                te  = TeachEngine()
                out = te.get_lesson(topic)
                print(f"\n{out}\n")
            except Exception as e:
                result = ai.ask_with_context(f"Explain {topic} for a penetration tester.", agent="red_team")
                print(f"\n{result.get('answer','')}\n")

        # ── Hardware devices ──────────────────────────────────────
        elif cmd == "devices" and hardware_manager:
            for d in hardware_manager.list_devices():
                state = "\033[92mONLINE\033[0m" if d["connected"] else "\033[91mOFFLINE\033[0m"
                print(f"  {d['name']:16} {state}  payloads: {', '.join(d['payloads'][:5])}")

        # ── Deploy payload ────────────────────────────────────────
        elif cmd == "deploy" and hardware_manager:
            # deploy <device> <payload>
            if len(parts) < 3:
                print("  Usage: deploy <device> <payload>")
                continue
            result = hardware_manager.execute(parts[1], parts[2])
            print(f"\n{result}\n")

        # ── Report ────────────────────────────────────────────────
        elif cmd == "report" and report_generator:
            target = parts[1] if len(parts) > 1 else (ctx.get_active_target() if ctx else "")
            report = report_generator.generate(target=target, enhance_ai=False)
            base   = f"report_{target.replace('.','_') or 'latest'}"
            md     = report_generator.save_markdown(report, f"{base}.md")
            html   = report_generator.save_html(report, f"{base}.html")
            print(f"\n  \033[92m📄 Report saved\033[0m")
            print(f"     Markdown : {md}")
            print(f"     HTML     : {html}")
            print(f"     Findings : {report['stats']['critical']}C "
                  f"{report['stats']['high']}H {report['stats']['medium']}M\n")

        # ── Toggle learn mode ─────────────────────────────────────
        elif cmd == "learn" and len(parts) == 1:
            learn_mode = not learn_mode
            if workflow_engine:
                workflow_engine.executor.learn_mode = learn_mode
            state = "\033[94mON\033[0m" if learn_mode else "OFF"
            print(f"  📘 Learn mode: {state}")

        # ── AI query ──────────────────────────────────────────────
        else:
            result = ai.ask_with_context(raw, agent=current_agent)
            print(f"\n{result.get('answer', result)}\n")
            sources = result.get("sources", []) if isinstance(result, dict) else []
            if sources:
                print(f"  📚 {', '.join(sources[:3])}\n")


def start_api(ai, host="0.0.0.0", port=8000, ctx=None, pm=None,
              hardware_manager=None, workflow_engine=None, report_generator=None):
    """FastAPI REST server (existing + new routes)."""
    try:
        from fastapi import FastAPI
        import uvicorn
    except ImportError:
        print("pip install fastapi uvicorn --break-system-packages")
        sys.exit(1)

    app = FastAPI(title="ERR0RS ULTIMATE API", version="2.0.0")

    @app.get("/")
    def root():
        return {"name": "ERR0RS ULTIMATE", "status": "running",
                "ai": ai.status() if hasattr(ai, "status") else {}}

    @app.post("/ask")
    def ask(question: str, agent: str = "red_team"):
        return ai.ask_with_context(question, agent=agent)

    @app.get("/knowledge/search")
    def search(q: str, n: int = 4):
        return {"query": q, "results": ai.search_knowledge(q, n)}

    if pm and ctx:
        @app.get("/plugins")
        def list_plugins():
            return {"plugins": pm.list_plugins()}

        @app.post("/plugins/run")
        def run_plugin(command: str, target: str = None):
            if target:
                ctx.set_active_target(target)
            result = pm.execute(command, {"target": target or ctx.get_active_target()})
            return {"command": command, "result": str(result)}

        @app.get("/session")
        def session():
            return ctx.summary()

    if hardware_manager:
        @app.get("/devices")
        def devices():
            return {"devices": hardware_manager.list_devices()}

        @app.post("/devices/deploy")
        def deploy(device: str, payload: str):
            result = hardware_manager.execute(device, payload)
            return result.to_dict()

    if workflow_engine:
        @app.get("/workflows")
        def workflows():
            return {"workflows": workflow_engine.list()}

        @app.post("/workflows/run")
        def run_workflow(name: str, target: str):
            return workflow_engine.run(name, target)

    if report_generator:
        @app.post("/report")
        def generate_report(target: str = "", session_id: str = ""):
            report = report_generator.generate(target=target, session_id=session_id)
            md     = report_generator.save_markdown(report, f"report_{session_id or 'api'}.md")
            html   = report_generator.save_html(report, f"report_{session_id or 'api'}.html")
            return {"stats": report["stats"], "md": md, "html": html}

    try:
        from src.tools.flipper.flipper_agent import register_flipper_routes
        register_flipper_routes(app, rag_store=getattr(ai, "_collection", None))
    except Exception as _fe:
        _log.debug(f"Flipper routes skipped: {_fe}")

    print(BANNER)
    print(f"  API  → http://{host}:{port}")
    print(f"  Docs → http://{host}:{port}/docs\n")
    uvicorn.run(app, host=host, port=port)


def start_dashboard(ai, host="127.0.0.1", port=5000, ctx=None, pm=None,
                    hardware_manager=None, workflow_engine=None,
                    report_generator=None, debug=False):
    """Flask + SocketIO live dashboard."""
    try:
        from src.ui.dashboard.app import run_dashboard
        run_dashboard(
            plugin_manager   = pm,
            hardware_manager = hardware_manager,
            report_generator = report_generator,
            workflow_engine  = workflow_engine,
            ctx              = ctx,
            host             = host,
            port             = port,
            debug            = debug,
        )
    except ImportError as e:
        print(f"Dashboard dependencies missing: {e}")
        print("pip install flask flask-socketio --break-system-packages")
        sys.exit(1)


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ERR0RS ULTIMATE",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--backend",   default=None,       help="LLM: ollama | anthropic")
    parser.add_argument("--model",     default=None,       help="Model override")
    parser.add_argument("--agent",     default="red_team", help="Default agent")
    parser.add_argument("--api",       action="store_true",help="FastAPI REST server")
    parser.add_argument("--dashboard", action="store_true",help="Flask live dashboard")
    parser.add_argument("--query",     default=None,       help="Single query and exit")
    parser.add_argument("--workflow",  nargs=2,            metavar=("NAME","TARGET"),
                        help="Run workflow directly: --workflow webapp 10.0.0.1")
    parser.add_argument("--report",    default=None,       metavar="TARGET",
                        help="Generate report for target and exit")
    parser.add_argument("--port",      type=int,default=None, help="Server port")
    parser.add_argument("--host",      default=None,       help="Bind host")
    parser.add_argument("--learn",     action="store_true",help="Enable learn mode")
    parser.add_argument("--safe",      action="store_true",help="Safe mode (no hardware)")
    parser.add_argument("--debug",     action="store_true",help="Debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # ── AI ────────────────────────────────────────────────────────────────
    from src.ai import ERR0RSAI
    ai = ERR0RSAI(backend=args.backend, model=args.model)

    # ── Plugin + Context ──────────────────────────────────────────────────
    plugin_config = {
        "flipper_port": os.environ.get("FLIPPER_PORT", "/dev/ttyACM0"),
        "output_dir":   os.path.join(ROOT, "output"),
        "safe_mode":    args.safe,
    }
    ctx, pm = _boot_plugin_system(config=plugin_config)

    # ── Interpreter + Router ──────────────────────────────────────────────
    from src.core.interpreter    import Interpreter
    from src.core.command_router import CommandRouter
    interpreter = Interpreter()
    router = CommandRouter(
        ai_brain=ai, plugin_manager=pm,
        interpreter=interpreter, context=ctx,
    )

    # ── New subsystems ────────────────────────────────────────────────────
    hardware_manager = _boot_hardware(ctx, safe_mode=args.safe)
    workflow_engine  = _boot_workflow(
        pm, interpreter, ctx,
        event_bus  = ctx.event_bus if ctx else None,
        learn_mode = args.learn,
        safe_mode  = args.safe,
    )
    report_generator = _boot_reports(ctx, report_dir=os.path.join(ROOT, "reports"))

    # ── Dispatch ──────────────────────────────────────────────────────────
    if args.query:
        result = ai.ask_with_context(args.query, agent=args.agent)
        print(f"\n{result.get('answer', result)}\n")
        if isinstance(result, dict) and result.get("sources"):
            print(f"Sources: {', '.join(result['sources'])}")

    elif args.workflow:
        wf_name, target = args.workflow
        if ctx:
            ctx.set_active_target(target)
        if workflow_engine:
            workflow_engine.run(wf_name, target)
        else:
            print("Workflow engine unavailable.")
            sys.exit(1)

    elif args.report:
        if report_generator:
            report = report_generator.generate(target=args.report, enhance_ai=False)
            md   = report_generator.save_markdown(report, "report_cli.md")
            html = report_generator.save_html(report, "report_cli.html")
            print(f"\n  📄 Markdown : {md}")
            print(f"     HTML     : {html}")
            print(f"     Findings : C={report['stats']['critical']} "
                  f"H={report['stats']['high']} M={report['stats']['medium']}\n")
        else:
            print("Report generator unavailable.")
            sys.exit(1)

    elif args.api:
        start_api(
            ai, host=args.host or "0.0.0.0", port=args.port or 8000,
            ctx=ctx, pm=pm, hardware_manager=hardware_manager,
            workflow_engine=workflow_engine, report_generator=report_generator,
        )

    elif args.dashboard:
        start_dashboard(
            ai, host=args.host or "127.0.0.1", port=args.port or 5000,
            ctx=ctx, pm=pm, hardware_manager=hardware_manager,
            workflow_engine=workflow_engine, report_generator=report_generator,
            debug=args.debug,
        )

    else:
        # Default: interactive terminal
        try:
            from src.ui.cli import start_cli
            start_cli(router=router, ctx=ctx, pm=pm, agent=args.agent)
        except (ImportError, AttributeError):
            # Fall back to built-in interactive mode
            interactive_mode(
                ai=ai, agent_type=args.agent, ctx=ctx, pm=pm,
                workflow_engine=workflow_engine,
                hardware_manager=hardware_manager,
                report_generator=report_generator,
                learn_mode=args.learn,
            )
