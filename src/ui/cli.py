# src/ui/cli.py
# ERR0RS-Ultimate — Interactive CLI Shell

import json
import os
import shutil


def _divider(char="─"):
    w = shutil.get_terminal_size((80, 20)).columns
    return char * min(w, 80)


BANNER = """
\033[92m  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝\033[0m
  ERR0RS-Ultimate | AI-Powered Penetration Testing
  Type \033[93mhelp\033[0m for commands | \033[93mexit\033[0m to quit
"""

HELP_TEXT = """
  \033[96mBuilt-in commands:\033[0m
  ─────────────────────────────────────────────────────
  target <ip/host>          Set active target
  run <cmd> [target]        Run plugin directly
    cmds: scan portscan stealth udp vuln full
          subghz badusb nfc ir status
  autopilot <target>        Autonomous kill chain mode
  plugins                   List loaded plugins
  findings [plugin]         Show session findings
  summary                   Session summary
  agent <name>              Switch AI agent
  status                    AI + system status
  clear                     Clear screen
  help                      This menu
  exit / quit               Shutdown ERR0RS
  ─────────────────────────────────────────────────────
  \033[96mOr just talk naturally:\033[0m
  "scan 192.168.1.1 for vulnerabilities"
  "run a stealth scan on target.com"
  "check what ports are open on 10.0.0.5"
"""


def start_cli(router, ctx=None, pm=None, agent: str = "red_team"):
    from src.core.autopilot import AutoPilot

    current_agent = agent
    print(BANNER)
    print(_divider())

    while True:
        try:
            # ── Dynamic prompt ────────────────────────────────────
            t_label = ""
            if ctx:
                t = ctx.get_active_target()
                if t:
                    t_label = f"\033[90m@{t}\033[0m"

            prompt = (
                f"\n\033[92mERR0RS\033[0m"
                f"[\033[93m{current_agent}\033[0m]"
                f"{t_label}> "
            )

            user_input = input(prompt).strip()
            if not user_input:
                continue

            low = user_input.lower()

            # ── Built-ins ─────────────────────────────────────────
            if low in ("exit", "quit", "q"):
                print("\n  ERR0RS shutting down. Stay ethical out there. 🔥\n")
                break

            if low == "help":
                print(HELP_TEXT)
                continue

            if low == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue

            if low in ("status", "summary") and ctx:
                print(json.dumps(ctx.summary(), indent=2))
                continue

            if low == "plugins" and pm:
                for p in pm.list_plugins():
                    icon = "✅" if p["enabled"] else "❌"
                    print(f"  {icon} {p['name']} v{p['version']} "
                          f"[{p['category']}] — {', '.join(p['commands'])}")
                continue

            if low.startswith("findings"):
                if ctx:
                    parts    = user_input.split()
                    plugin_f = parts[1] if len(parts) > 1 else None
                    findings = ctx.get_findings(plugin=plugin_f)
                    if findings:
                        for f in findings:
                            print(f"\n  [{f.get('plugin','?')}] "
                                  f"{f.get('type','?')} → {f.get('target','?')}")
                            lines = str(f.get("output","")).strip().splitlines()
                            for line in lines[:20]:
                                print(f"    {line}")
                            if len(lines) > 20:
                                print(f"    ... ({len(lines)-20} more lines)")
                    else:
                        print("  No findings yet.")
                continue

            if low.startswith("target ") and ctx:
                t = user_input.split(None, 1)[1].strip()
                ctx.set_active_target(t)
                print(f"  \033[92m✓\033[0m Target: {t}")
                continue

            if low.startswith("agent "):
                current_agent = user_input.split(None, 1)[1].strip()
                print(f"  \033[92m✓\033[0m Agent: {current_agent}")
                continue

            if low.startswith("run ") and pm:
                parts  = user_input.split(None, 2)
                cmd    = parts[1] if len(parts) > 1 else ""
                target = (parts[2] if len(parts) > 2
                          else (ctx.get_active_target() if ctx else None))
                if not target:
                    print("  ⚠️  No target. Use: run <cmd> <target>")
                    continue
                if ctx:
                    ctx.set_active_target(target)
                result = pm.execute(cmd, {"target": target})
                print(f"\n\033[96m{_divider()}\033[0m")
                print(result)
                print(f"\033[96m{_divider()}\033[0m")
                continue

            if low.startswith("autopilot "):
                target = user_input.split(None, 1)[1].strip()
                ap = AutoPilot(router=router, ctx=ctx, delay=1.0)
                ap.run(target, max_steps=5)
                continue


            # ── Natural language → router ─────────────────────────
            response = router.handle_input(user_input)

            print(f"\n{_divider()}")

            result = response.get("result", "")
            if result:
                print("\n  \033[96m📡 Result:\033[0m")
                lines = str(result).strip().splitlines()
                for line in lines[:40]:
                    print(f"  {line}")
                if len(lines) > 40:
                    print(f"  ... ({len(lines)-40} more lines — use 'findings' to review)")

            reason = response.get("reason", "")
            if reason:
                print(f"\n  \033[93m🧠 Reason:\033[0m\n  {reason}")

            intent = response.get("intent", "")
            target = response.get("target", "")
            if intent and intent != "ai_only":
                icon = "✅" if response.get("plugin_ran") else "⚠️ "
                print(f"\n  {icon} Plugin: \033[92m{intent}\033[0m"
                      + (f" → {target}" if target else ""))

            suggestions = response.get("suggestions", [])
            icons = {1: "🔴", 2: "🟠", 3: "🟡", 4: "⚪"}
            if suggestions:
                print(f"\n  \033[95m⚡ Next steps:\033[0m")
                for s in suggestions[:5]:
                    icon = icons.get(s.get("priority", 4), "→")
                    cmd  = (f"  [run: {s['command']}]"
                            if s.get("command") else "")
                    print(f"  {icon} {s['message']}{cmd}")

            print(f"\n{_divider()}\n")

        except KeyboardInterrupt:
            print("\n\n  ERR0RS shutting down.\n")
            break
        except Exception as e:
            print(f"\n  \033[91m[ERR0RS ERROR]\033[0m {e}\n")
