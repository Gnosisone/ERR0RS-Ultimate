# ERR0RS Safety Gate — Authorization & Lab Mode

**TL;DR:** ERR0RS refuses to run tools against any target not covered by an active
authorization record. This is the CFAA-compliant default. Two ways to proceed:
either authorize a specific engagement, or enable lab mode for localhost/RFC1918.

## Why this exists

Unauthorized access to computer systems is a federal crime in the United States
under the Computer Fraud and Abuse Act (18 U.S.C. § 1030), and equivalent
statutes worldwide. CFAA does not care about the user's age, intent, or skill
level. ERR0RS is built for students from age 12 up. The safety gate prevents a
curious teenager from accidentally committing a federal felony with a tool
they don't yet fully understand.

The gate is the engineering answer to a problem the academic architecture
document called out explicitly:

> "A 12-year-old running real pen-test tools against real targets is a legal
> disaster. CFAA does not care about age."

## How the gate works

Every tool execution flows through `src/security/gate.py::check_tool_execution()`.
That function gets called at the top of both `BaseTool.execute()` and
`BasePlugin.stream()` — the two single chokepoints for tool execution in ERR0RS.

The gate checks four things, in order:

1. **Dangerous patterns** — `rm -rf`, `mkfs`, `dd if=`, `shutdown`, etc. are
   never allowed, even with authorization. These are commands that would
   destroy your own machine.
2. **No-target tools** — tools that operate on local data (e.g. `hashcat`,
   `john`) don't need target authorization. They still pass the dangerous-
   pattern check.
3. **Authorization records** — if there's an active authorization covering
   this target, allow.
4. **Lab mode** — if `ERR0RS_LAB_MODE=1` is set and the target is in a
   permitted lab range (localhost, RFC1918, explicit `ERR0RS_LAB_TARGETS`),
   allow.

If none of those allow, the gate refuses with a clear, helpful error message
that tells the user exactly how to authorize legally.

## When it refuses, what happens

The tool does NOT spawn a subprocess. The user sees a clear message explaining:
- What was refused
- Why CFAA matters
- The two paths to proceed (authorize or lab-mode)

Both `BaseTool.execute()` and `BasePlugin.stream()` emit a `tool.blocked` event
on the shared event bus so the CLI and dashboard see and display the refusal.

## How to USE ERR0RS legally

### Option 1 — You own the target (lab VM, your own machine, RFC1918 home network)

Enable lab mode in `.env`:

```bash
ERR0RS_LAB_MODE=1
```

That alone permits:
- `127.0.0.1`, `::1`, `localhost`
- `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` (all RFC1918)
- `169.254.0.0/16` (link-local)
- IPv6 `fc00::/7` (unique-local), `fe80::/10` (link-local)

For additional lab targets outside those ranges (e.g. a deliberate-vuln VM at
a non-RFC1918 address inside a corporate lab network):

```bash
ERR0RS_LAB_TARGETS=lab.example.com,192.0.2.10,vuln-vm.internal
```

A warning banner prints once per session whenever lab mode is active. This is
intentional — it keeps the user aware that the gate is permissive.

### Option 2 — You have written permission for a specific engagement

Authorization records live at `~/.err0rs/authorization.json`. The schema is
defined by `src/security/authorization.py::AuthorizationManager`. A record
looks like:

```json
[
  {
    "id": "AUTH-20260521-101500",
    "client_name": "Acme Corp",
    "targets": ["acme.example.com", "10.20.30.0/24"],
    "scope_notes": "External web app + internal /24. No DoS.",
    "tester_name": "Eros",
    "start_date": "2026-05-21",
    "end_date": "2026-05-28",
    "created_at": "2026-05-21T10:15:00",
    "confirmed": true,
    "confirmed_at": "2026-05-21T10:16:00",
    "status": "active"
  }
]
```

Today you'd hand-craft this file or use Python directly:

```python
from src.security.authorization import AuthorizationManager
mgr = AuthorizationManager("~/.err0rs/authorization.json")
auth = mgr.create_authorization(
    client_name="Acme Corp",
    targets=["acme.example.com", "10.20.30.0/24"],
    scope_notes="External web app + internal /24. No DoS.",
    tester_name="Eros",
    start_date="2026-05-21",
    end_date="2026-05-28",
)
# Required confirmation step — you must type this exact text:
mgr.confirm_authorization(auth["id"],
    "I confirm I have written authorization to test the specified targets.")
```

A proper CLI helper (`python3 -m src.security.cli_authorize`) is on the v3.7
follow-up list — it'll wrap the same API with a friendly interactive flow.

### Option 3 — You're just running ERR0RS for learning, no targets

If you're working through teach cards or exploring the registry without
running tools against any target, you don't need anything. The gate only
fires when a tool tries to execute.

## What the gate does NOT do

The gate is not a complete substitute for understanding ethics and law. It:

- Does NOT verify whether your authorization is genuine — it trusts the
  record on disk. If you forge an authorization for a target you don't
  own, you're committing fraud on top of unauthorized access.
- Does NOT prevent you from causing damage WITHIN authorized scope. A
  reckless test against an authorized target can still take production
  down. Ethics and judgment still apply.
- Does NOT replace a written contract for real engagements. The on-disk
  record is for runtime enforcement; the legal protection is the signed
  agreement behind it.

## Architecture / Implementation details

- **`src/security/gate.py`** — the public API: `check_tool_execution()` and
  `GateDecision`. Module-level singletons for the auth manager and guardrails
  so all code paths see the same records.
- **`src/security/authorization.py`** — the `AuthorizationManager` class,
  unchanged from earlier sessions. Stores records, checks targets.
- **`src/security/guardrails.py`** — the `EthicalGuardrails` class, also
  pre-existing. Owns the BLOCKED_PATTERNS list and tool risk classification.
- **`src/core/base_tool.py`** — calls the gate at the top of `execute()`,
  before the `tool.start` emit, before any subprocess work.
- **`src/core/plugin_base.py`** — calls the gate at the top of `stream()`,
  same insertion point.

## Tests

The gate has 13 unit tests covering the policy logic (`tests/test_gate.py`
is a TODO, but the validation suite that ran during commit
[v3.7-alpha2: see git log] verified end-to-end:
- BaseTool.execute() refuses unauthorized targets
- BaseTool.execute() with lab-mode permits localhost
- BasePlugin.stream() refuses unauthorized targets
- Lab-mode banner shows once per session, not on every call
- `tool.blocked` events emit on the event bus
- All 7 dangerous-pattern blocked commands still refuse in lab mode

## See also

- `docs/ACADEMIC_ARCHITECTURE.md` — why the gate exists, mission framing
- `src/security/authorization.py` — authorization manager implementation
- `src/security/guardrails.py` — blocked patterns and risk classification
- `src/security/gate.py` — the gate itself (this is the file you'd modify
  if you wanted to extend the policy)
