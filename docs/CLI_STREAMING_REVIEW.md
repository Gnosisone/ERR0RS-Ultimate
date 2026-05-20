# ERR0RS-clean — Functional Review & CLI Streaming Plan

**Reviewer:** Claude KaliForge
**Date:** 2026-05-19
**Scope:** `/home/kali/ERR0RS-clean/` (application code only; `venv/` and `knowledge/` skipped)
**Focus order:** (1) live CLI tool-output streaming, (2) OpSec / feature gaps, (3) perf, (4) code quality

---

## TL;DR

The dashboard sees live tool output because it subscribes to a real event bus (`SharedContext.event_bus` → SocketIO). The CLI never subscribes to that bus, so it only sees a final `result` string. There are also two competing execution paths — the **good** async streaming `ToolExecutor` (`src/core/tool_executor.py`) and a **bad** blocking `BaseTool.execute()` (`src/core/base_tool.py`) — and several tools still go through the blocking one. Fix is three coordinated changes plus a handful of cleanups.

---

## 1. Streaming architecture — confirmed findings

### What works
- `src/core/tool_executor.py:319` — uses `asyncio.create_subprocess_shell` and an `on_line` callback that fires for every stdout line. This is the right primitive.
- `src/orchestration/execution_modes.py:77` — `ExecutionEngine` wires `ToolExecutor(on_line=self._on_tool_line)` and `_on_tool_line` prints `[tool] line`. Good.
- `src/ui/dashboard/app.py:93-110` — `_wire_event_bus()` relays a defined list of events (`workflow_step`, `command_result`, `device.action`, etc.) to SocketIO. The dashboard "sees everything" because of this.

### What's broken
- **`src/core/base_tool.py:132`** — `subprocess.Popen(...)` + `process.communicate(timeout=...)`. Fully blocking. Captures stdout/stderr into a single string and returns it only after the tool exits. Any tool subclassing `BaseTool` *cannot* stream, no matter what the executor layer does.
- **`src/tools/tool_integration.py:118`** — second blocking `Popen` path, no streaming, no timeout in some branches.
- **`src/ui/cli.py:71`** — REPL is sync `input()`; **`:154`** — `router.handle_input()` returns a final dict, no callbacks. CLI never receives `event_bus` events even when the dashboard does.
- **`src/orchestration/execution_modes.py:84-86`** — `@staticmethod async def _on_tool_line` is correct under the asyncio loop but is invisible to the CLI because the CLI doesn't run inside that loop or subscribe to the bus.
- **`src/security/guardrails.py:62-99`** — `EthicalGuardrails.check_execution()` exists but is **not called** before `ToolExecutor.run()` or `BaseTool.execute()`. So guardrails are effectively dead code.
- **`src/core/tool_executor.py:382`** — bare `except: pass` on the XP award branch (silent failure).

---

## 2. Fix design — CLI live streaming in 4 moves

### Move 1 — Make `BaseTool.execute()` non-blocking + emit events

Replace the `Popen.communicate()` in `src/core/base_tool.py` with a line-iteration loop and an optional `on_line` hook. Diff sketch (keep the public API the same, add streaming as opt-in so existing callers don't break):

```python
# src/core/base_tool.py — replace lines 128-158

self.status = ToolStatus.RUNNING
stdout_buf, stderr_buf = [], []

process = subprocess.Popen(
    command, shell=True,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1,  # line-buffered
)

start_deadline = time.time() + self.timeout
try:
    # Drain stdout live
    for line in iter(process.stdout.readline, ""):
        line = line.rstrip("\n")
        stdout_buf.append(line)
        # Publish to event bus if available (set by BaseTool.bind_bus())
        bus = getattr(self, "_event_bus", None)
        if bus:
            bus.emit("tool.output", {"tool": self.tool_name, "line": line})
        # Hard timeout check
        if time.time() > start_deadline:
            process.kill()
            status = ToolStatus.TIMEOUT
            break
    process.wait(timeout=2)
    # Drain stderr in one go (it's small)
    stderr_buf.append(process.stderr.read() or "")
    exit_code = process.returncode
    status = ToolStatus.COMPLETED if exit_code == 0 else ToolStatus.FAILED
except Exception as e:
    process.kill()
    stderr_buf.append(str(e))
    exit_code, status = -1, ToolStatus.FAILED

stdout = "\n".join(stdout_buf)
stderr = "\n".join(stderr_buf)
```

And add a one-line binder so the orchestrator/CLI can attach a bus:

```python
def bind_bus(self, bus): self._event_bus = bus
```

### Move 2 — Have `ToolExecutor.on_line` publish to the bus too

`src/core/tool_executor.py` already has `on_line`. Replace the bare `print()` in `ExecutionEngine._on_tool_line` with a bus emit so **both** sinks (CLI + dashboard) get the same event:

```python
# src/orchestration/execution_modes.py
def __init__(self, event_bus=None):
    self.event_bus = event_bus
    self.executor  = ToolExecutor(on_line=self._on_tool_line)
    ...

async def _on_tool_line(self, tool_name: str, line: str):
    if self.event_bus:
        self.event_bus.emit("tool.output", {"tool": tool_name, "line": line})
    else:                       # fallback for stand-alone runs
        print(f"   │ [{tool_name}] {line}")
```

Add `"tool.output"` to the dashboard's `RELAY_EVENTS` list in `src/ui/dashboard/app.py:95-100`.

### Move 3 — Subscribe the CLI to the bus

This is the change you actually feel. Inside `start_cli()` in `src/ui/cli.py`, register a handler before the REPL loop:

```python
def start_cli(router, ctx=None, pm=None, agent: str = "red_team"):
    ...
    # ── Live tool-output subscription ──────────────────────────
    if ctx and getattr(ctx, "event_bus", None):
        def _print_tool_line(_evt, data):
            tool = data.get("tool", "?")
            line = data.get("line", "")
            # \r + clear-line so we don't clobber the prompt mid-typing
            print(f"\r\033[2K   │ \033[90m[{tool}]\033[0m {line}")

        def _print_step(_evt, data):
            step = data.get("step") or data.get("description", "")
            print(f"\r\033[2K\033[96m▸\033[0m {step}")

        ctx.event_bus.on("tool.output",    _print_tool_line)
        ctx.event_bus.on("workflow_step",  _print_step)
        ctx.event_bus.on("finding.added",  _print_step)
```

If your `EventBus.on()` dispatches synchronously (most simple buses do), this Just Works inside the sync REPL — every `bus.emit()` from another thread prints to the terminal immediately. If it dispatches asynchronously, wrap the handlers with `threading.Lock` around `sys.stdout` to avoid prompt collisions.

### Move 4 — (Polish) prompt-toolkit `patch_stdout` so the prompt survives streaming

Right now `print()` mid-input will mangle the active prompt. Replace `input()` with `prompt_toolkit.prompt(...)` and wrap the REPL with `patch_stdout()`:

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

session = PromptSession()
with patch_stdout():
    while True:
        user_input = session.prompt(prompt_text).strip()
```

Now tool lines stream above the prompt while the user keeps typing. This is the "Clippy on steroids" feel you described.

---

## 3. Punch list — prioritized

### P0 — Do these first (functional / safety)
| # | File:Line | Issue | Fix |
|---|---|---|---|
| 1 | `src/core/base_tool.py:132-149` | Blocking `Popen.communicate()` swallows live output | Move 1 above |
| 2 | `src/ui/cli.py:start_cli` | No event-bus subscription | Move 3 above |
| 3 | `src/security/guardrails.py:62-99` | `check_execution()` never called before run | Call it from `ToolExecutor.run()` *and* `BaseTool.execute()` before subprocess launch; deny on high-risk + no auth |
| 4 | `src/security/authorization.py:36-82` | Authorizations loaded but not checked | Gate `BaseTool.execute()` on `AuthorizationManager.is_authorized(target)` — fail closed |
| 5 | `src/tools/tool_integration.py:118` | Second blocking Popen path, no timeout | Either delete it and route everything through `ToolExecutor`, or apply Move 1 |

### P1 — OpSec / hygiene
| # | File:Line | Issue | Fix |
|---|---|---|---|
| 6 | `src/core/tool_executor.py:382` | Bare `except: pass` on XP award | Log at DEBUG: `logger.debug("XP award failed: %s", exc)` |
| 7 | `src/core/base_tool.py:126` | Command logged verbatim, may include creds/keys | Add a `redact(command)` helper that masks `--password`, `-p `, tokens, API keys before logging |
| 8 | `src/orchestration/execution_modes.py:85` | `print()` direct to stdout — no journal | Persist every tool.output line to `~/.err0rs/logs/<engagement>/<tool>.log` (rotated, gzip after run) |
| 9 | `src/ui/cli.py:71` | `input()` history not persistent | Use `prompt_toolkit` `FileHistory` so red-team operators get up-arrow recall across sessions |
| 10 | global | No engagement-ID tag on events | Add `engagement_id` to every `event_bus.emit(...)` payload — makes logs filterable per client |

### P2 — Code quality / architecture
| # | File:Line | Issue | Fix |
|---|---|---|---|
| 11 | `src/education/` + `src/education_new/` | Parallel implementations, both imported | Decide one canonical, delete the other; add a `from src.education import *` shim if external code references either |
| 12 | `src/tools/badusb/` vs `src/tools/badusb_studio/` | Old wrapper unused | Delete `src/tools/badusb/` once nothing in `main.py` imports from it (currently `badusb_studio` is the active path, main.py:248-250) |
| 13 | Two `orchestrator.py` (ai/agents/ + orchestration/) | Different roles but same filename — confusing | Rename `src/ai/agents/orchestrator.py` → `agent_coordinator.py` to clarify |
| 14 | `src/core/tool_executor.py:272` | `on_line: Optional[Any]` | Type as `Optional[Callable[[str, str], Awaitable[None]]]` |
| 15 | `src/core/demo_mode.py:259,279,294` | `time.sleep()` in code that may run inside asyncio | Replace with `await asyncio.sleep()` (or guard with `if not asyncio.get_event_loop().is_running()`) |
| 16 | global | No `requirements.txt` or `pyproject.toml` lock | Add `pyproject.toml` + `pip-compile` lockfile so the venv is reproducible across rolling-release Kali |

### P3 — Performance
| # | Where | Idea |
|---|---|---|
| 17 | `ToolExecutor.run_batch(parallel=True)` | Add a `max_concurrency` semaphore so 50 parallel nmaps don't melt the box |
| 18 | `src/ai/rag_ingest_2026.py` (RAG ingest) | If using chromadb, batch upserts of 256 docs vs single-shot |
| 19 | `tool.output` event spam | Throttle UI emit to every 50ms or coalesce 10 lines per event — saves SocketIO chatter on huge nmap scans |
| 20 | `src/tools/tool_integration.py` | Move LOLBin lookups to a cached dict (lru_cache) instead of disk lookup per call |

---

## 4. Feature gaps worth filling

These map cleanly onto MITRE ATT&CK coverage you'll want for a "Clippy on steroids" red-team copilot:

- **Recon (TA0043):** `amass intel` integration is missing. Add to `src/tools/network/sentinel.py` as a passive-DNS pivot.
- **Initial Access (TA0001):** No `evilginx2` or `gophish` bridge. Phishing infra orchestration is a glaring hole given you have `phish_hunter.py`.
- **Execution (TA0002):** `sliver` mentioned in your charter — no client wrapper found. Consider `src/tools/c2/sliver_client.py`.
- **Persistence (TA0003):** No registry/cron persistence templates in `postex_module.py`.
- **Credential Access (TA0006):** `credential_engine.py` exists but doesn't wrap `kerbrute` / `impacket-GetUserSPNs` (Kerberoasting). Big gap for AD work.
- **Lateral Movement (TA0008):** `CrackMapExec` is listed in your charter but I don't see an integration. `nxc` (the modern fork) is what Kali ships now.
- **Defense Evasion (TA0005):** `evasion_lab.py` exists — verify it covers AMSI/ETW patches and donut shellcode generation. If not, those are quick wins.
- **Reporting:** `pro_reporter.py` is solid — but no Markdown→DOCX bridge for client deliverables. Add a `--format=docx` flag using `python-docx`.

---

## 5. Suggested test plan after the streaming patch

1. **Smoke test** — run `python main.py` (default CLI), then `run scan 127.0.0.1`. You should see `[nmap] Starting Nmap 7.x ...` appear *line by line* in the terminal, not all at once at the end.
2. **Dashboard parity** — same scan, with `--dashboard` open in another window. Both terminals get the same stream simultaneously.
3. **Long-running tool** — `run vuln 192.168.56.100` with `nuclei` and confirm the prompt stays clean (no overwrite glitches) — verifies `patch_stdout`.
4. **Guardrails active** — try a target you haven't authorized. Should fail closed with a clear "no written authorization on file" message.
5. **Ctrl-C** — interrupts during a streaming nmap should kill the child cleanly and unwind to the prompt (test the new `process.kill()` path in `base_tool.py`).

---

## 6. What I did *not* touch

- I didn't modify any source files. Every diff in this doc is a sketch — you should review and apply.
- I did not run the venv to verify imports — the shell sandbox was unavailable. Worth a manual `python -c "from src.core.tool_executor import ToolExecutor"` after the patches.
- I didn't audit the `knowledge/` tree (vendored third-party).
- I didn't review the FastAPI surface in detail — same streaming fix likely applies if you want `/api` clients to subscribe via SSE.

---

## OpSec note (always)

All of the above assumes you're testing in a lab or on systems with **explicit written authorization**. The auth gate fix in P0 (#3, #4) isn't paranoia — it's the difference between a tool and a liability. Get it wired before this ships to anyone else.

— Claude KaliForge
