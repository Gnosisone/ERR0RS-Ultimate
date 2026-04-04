"""
ERR0RS ULTIMATE - Main Entry Point
=====================================
Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone

Usage:
    python main.py                  # Interactive terminal mode
    python main.py --api            # Start FastAPI server
    python main.py --agent blue_team  # Start with specific agent
    python main.py --backend anthropic  # Use Claude API
    python main.py --query "How do I enumerate SMB?"  # Single query
"""

import argparse
import os
import sys
import logging

# ── Load .env BEFORE anything reads env vars ──────────────────────────────────
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_env_path, override=False)  # CLI args / existing env take precedence
except ImportError:
    pass  # python-dotenv optional; set vars manually if needed

logging.basicConfig(level=logging.WARNING, format="%(asctime)s [ERR0RS] %(message)s")

BANNER = r"""
  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
   ULTIMATE — AI-Powered Penetration Testing Framework
   Built by Gary Holden Schneider | GitHub: Gnosisone
"""

def interactive_mode(ai, agent_type: str = "red_team"):
    from src.ai.agents import list_agents
    print(BANNER)
    print(f"  Active agent : {agent_type}")
    print(f"  LLM backend  : {ai.llm.backend} ({ai.llm.model})")
    print(f"  Knowledge RAG: {'✅ Active' if ai._kb_available else '⚠️  Keyword fallback'}")
    print(f"  Agents       : {', '.join(list_agents())}")
    print("\n  Commands: 'agent <n>' to switch | 'status' | 'exit'")
    print("  ─────────────────────────────────────────────────────\n")

    current_agent = agent_type
    while True:
        try:
            user_input = input(f"ERR0RS [{current_agent}]> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                print("ERR0RS shutting down. Stay ethical out there. 🔥")
                break
            if user_input.lower() == "status":
                import json
                print(json.dumps(ai.status(), indent=2))
                continue
            if user_input.lower().startswith("agent "):
                current_agent = user_input.split(None, 1)[1].strip()
                print(f"  Switched to: {current_agent}\n")
                continue
            result = ai.ask_with_context(user_input, agent=current_agent)
            print(f"\n{result['answer']}\n")
            if result["sources"]:
                print(f"  📚 Sources: {', '.join(result['sources'][:3])}\n")
        except KeyboardInterrupt:
            print("\nERR0RS shutting down.")
            break


def start_api(ai, host: str = "0.0.0.0", port: int = 8000):
    try:
        from fastapi import FastAPI
        import uvicorn
        app = FastAPI(title="ERR0RS ULTIMATE API", version="1.0.0")

        @app.get("/")
        def root():
            return {"name": "ERR0RS ULTIMATE", "status": "running", "ai": ai.status()}

        @app.post("/ask")
        def ask(question: str, agent: str = "red_team"):
            return ai.ask_with_context(question, agent=agent)

        @app.get("/agents")
        def agents():
            from src.ai.agents import list_agents
            return {"agents": list_agents()}

        @app.get("/knowledge/search")
        def search(q: str, n: int = 4):
            return {"query": q, "results": ai.search_knowledge(q, n)}

        # ── Flipper Zero integration ──────────────
        try:
            from src.tools.flipper.flipper_agent import register_flipper_routes
            rag_store = getattr(ai, "_collection", None) or getattr(ai, "collection", None)
            register_flipper_routes(app, rag_store=rag_store)
        except Exception as _fe:
            print(f"  [Flipper] Module load skipped: {_fe}")

        print(BANNER)
        print(f"  API running at http://{host}:{port}")
        print(f"  Docs at http://{host}:{port}/docs\n")
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        print("FastAPI/uvicorn not installed.")
        print("pip install fastapi uvicorn --break-system-packages")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ERR0RS ULTIMATE")
    parser.add_argument("--backend", default=None,         help="LLM backend: ollama or anthropic")
    parser.add_argument("--model",   default=None,         help="Model override")
    parser.add_argument("--agent",   default="red_team",   help="Default agent type")
    parser.add_argument("--api",     action="store_true",  help="Start FastAPI server")
    parser.add_argument("--query",   default=None,         help="Single query mode")
    parser.add_argument("--port",    type=int, default=8000, help="API port (default 8000)")
    args = parser.parse_args()

    from src.ai import ERR0RSAI
    ai = ERR0RSAI(backend=args.backend, model=args.model)

    if args.query:
        result = ai.ask_with_context(args.query, agent=args.agent)
        print(f"\n{result['answer']}\n")
        if result["sources"]:
            print(f"Sources: {', '.join(result['sources'])}")
    elif args.api:
        start_api(ai, port=args.port)
    else:
        interactive_mode(ai, agent_type=args.agent)
