# ERR0RS-clean — Session Handoff

**Topic:** CLI live tool-output streaming + functional review
**Date:** 2026-05-19
**Project root:** `/home/kali/ERR0RS-clean/`
**Status:** Streaming patch applied across 6 files. Awaiting a clean re-test of `run portscan`.

---

## How to resume in a new chat

Paste this whole file in. The one-line summary: *"We made ERR0RS stream tool output live to the CLN via the EventBus. Patch is applied; I need to verify it and continue the punch-list in `docs/CLI_STREAMING_REVIEW.md`."*

---

## What the goal was

When ERR0RS runs an external tool (nmap, etc.), the live output only appeared in the
dashboard UI — the CLI saw nothing until the tool finished. Goal: make the CLI mirror
the dashboard with real-time, line-by-line stdout/stderr passthrough.

**Root cause found:** The dashboard subscribes to a shared `EventBus`
(`SharedContext.event_bus`) and relays events to SocketIO. The CLI never subscribed.
Separately, tools were run with blocking calls (`subprocess.run(capture_output=True)`,
`Popen.communicate()`) that return one big string only after the process exits.

---

## Files changed (all applied, all on disk)

### 1. `src/core/base_tool.py`
- Added module-level `set_default_event_bus(bus)` + `_get_bus(tool)` + per-instance `bind_bus(bus)`.
- Added `_redact()` — masks `--password`, `-p`, `--token`, `--api-key`, `Bearer` tokens before logging/emitting.
- Rewrote `BaseTool.execute()` — now `Popen` line-buffered, iterates `stdout.readline`, emits `tool.start` / `tool.output` / `tool.stderr` / `tool.end` per line. Watchdog `threading.Timer` enforces timeout (kills PID even if tool is silent).

### 2. `src/orchestration/execution_modes.py`
- `ExecutionEngine.__init__` now takes optional `event_bus`.
- `_on_tool_line` no longer `@staticmethod`; publishes `tool.output` to the bus, falls back to `print()` if no bus. (Note: `ExecutionEngine` is exported but not instantiated anywhere yet — change is forward-looking.)

### 3. `src/ui/dashboard/app.py`
- Added `tool.start`, `tool.output`, `tool.stderr`, `tool.end` to `RELAY_EVENTS` so the dashboard mirrors the CLI stream.

### 4. `src/ui/cli.py`
- Added `_stream_print()` (thread-safe, clears input line with `\r\033[2K`).
- Added handlers `_on_tool_start/_output/_stderr/_end`, `_on_workflow_step`, `_on_finding` and `_attach_cli_to_bus(bus)`.
- `start_cli()` now subscribes the CLI to `ctx.event_bus` AND calls `set_default_event_bus(ctx.event_bus)`. Prints `● Live tool streaming ENABLED`.

### 5. `src/core/plugin_base.py`  ← **the fix that actually mattered**
- Added `BasePlugin.stream(cmd, tool_name, timeout, target)` — runs `Popen` line-buffered, emits `tool.*` events per line, watchdog timeout, returns a `PluginResult`.
- Rewrote `BasePlugin.shell()` to delegate to `stream()` — so **every plugin using `self.shell(...)` now streams for free**.

### 6. `src/plugins/recon/nmap_plugin/plugin.py`
- `run()` now calls `self.stream(cmd, tool_name="nmap", ...)` instead of `subprocess.run`.
- Removed unused `import subprocess`.
- Added `-v` to every `SCAN_PROFILES` entry (+ `--stats-every` on long scans) — **required** because nmap is silent without `-v` and there's nothing to stream until the end.

---

## EventBus reference (so future patches stay consistent)

`src/core/context.py` — `class EventBus`:
- `bus.on(event: str, callback)` — callback signature is `cb(event_name, data)`
- `bus.emit(event: str, data=None)` — **synchronous**, fires all listeners in the calling thread, thread-safe (internal lock)
- Lives at `SharedContext.event_bus`; plugins get it via `self.context.event_bus`, and `BasePlugin.emit()` already wraps it.

Standard event payloads now in use:
- `tool.start`  → `{tool, command, target}`
- `tool.output` → `{tool, line}`
- `tool.stderr` → `{tool, line}`
- `tool.end`    → `{tool, status, exit_code, execution_time}`

---

## THE BLOCKER — sandbox / verification

The Cowork isolated Linux sandbox failed to start this whole session
("Workspace unavailable. The isolated Linux environment failed to start."),
so **none of the patches were compile-checked or run by the assistant**.
The user ran the earlier round manually on the Raspberry Pi Kali host and it worked.

### What still needs to be verified (run on the Kali host, not the sandbox)

```bash
cd ~/ERR0RS-clean
python -m py_compile src/core/base_tool.py \
                     src/orchestration/execution_modes.py \
                     src/ui/dashboard/app.py \
                     src/ui/cli.py \
                     src/core/plugin_base.py \
                     src/plugins/recon/nmap_plugin/plugin.py
```

Then the real test:

```bash
python main.py
# inside the REPL:
target 127.0.0.1
run portscan 127.0.0.1     # use portscan, NOT scan — scan on localhost is 0.5s, too fast to see streaming
```

**Expected:** `▸ nmap → 127.0.0.1`, then `│ [nmap] ...` lines appearing live during
the scan (including `Discovered open port` and `Stats:` progress lines), then
`└─ nmap completed (rc=0, Ns, N findings)`.

**If it does NOT stream live:** likely cause is nmap block-buffering its stdout when
not attached to a TTY. Fix = prefix the command with `stdbuf -oL -eL`. In
`plugin_base.py` `stream()`, when `use_shell` is False you can prepend
`["stdbuf", "-oL", "-eL"]` to `cmd_list` (coreutils `stdbuf` ships on Kali/Parrot).

### Sandbox issue itself
The sandbox failing is a Cowork-environment problem, not an ERR0RS bug. Nothing in
the repo needs changing for it. If a fresh chat also has a dead sandbox, just keep
using direct file tools (Read/Write/Edit) — that's what worked this session — and
run all Python verification on the Kali host manually.

---

## Remaining work (priority order)

From `docs/CLI_STREAMING_REVIEW.md` — full detail there. Top items:

1. **Verify the streaming patch** with the test above. (Blocking everything else.)
2. **Sweep remaining plugins** for blocking `subprocess.run` / `Popen.communicate` —
   swap each to `self.stream(...)` or `self.shell(...)`. Known offender:
   `src/tools/tool_integration.py:118`. Check `src/plugins/hardware/flipper_plugin/plugin.py` too.
3. **P0 — wire guardrails:** `src/security/guardrails.py` `check_execution()` and
   `src/security/authorization.py` are defined but **never called** before a tool runs.
   Add an authorization/guardrail gate at the top of `BasePlugin.stream()` and
   `BaseTool.execute()` — fail closed if the target isn't authorized.
4. **P1 OpSec:** persist every `tool.output` line to a per-engagement log file
   (`~/.err0rs/logs/<engagement>/<tool>.log`); tag events with an `engagement_id`.
5. **P2 cleanup:** dedupe `src/education/` vs `src/education_new/`,
   `src/tools/badusb/` vs `src/tools/badusb_studio/`; rename one of the two
   `orchestrator.py` files.
6. **Polish:** swap CLI `input()` for `prompt_toolkit` + `patch_stdout()` so the
   prompt survives mid-stream output cleanly, plus persistent command history.

---

## Key reference docs in the repo

- `docs/CLI_STREAMING_REVIEW.md` — full prioritized review (P0–P3 punch list, feature gaps, MITRE coverage, test plan).
- `docs/HANDOFF_CLI_STREAMING.md` — this file.

---

## Environment notes

- Host: Kali on Raspberry Pi (`kali@kali-raspberrypi`), rolling release.
- venv at `~/ERR0RS-clean/venv`, Python 3.13.
- nmap 7.99 installed; Ollama running (`err0rs-qwen`, `llama3.2:3b`, `err0rs-pi5`, `qwen2.5-coder:7b`).
- `/dev/ttyACM0` absent → flipper plugin logs a harmless serial-connect warning at boot. Not a bug.
- Default `python main.py` launches the interactive CLI (`src/ui/cli.py:start_cli`).
- All authorized-testing / OpSec rules from the project charter still apply.
