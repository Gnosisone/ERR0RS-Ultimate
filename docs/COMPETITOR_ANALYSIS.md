# ERR0RS — Autonomous Pentest Framework: Competitor Architecture Review

**Purpose.** A grounded look at how other autonomous / agentic pentest systems
structure their kill chain, and what ERR0RS can adopt. Findings are scoped to
what is *verifiable*: open-source repos were read directly; closed commercial
products are described from public material only and are clearly marked.

**Scope of review.** Open-source (code read on-device): PentestGPT, VulnBot,
PentAGI, KaliGPT. Closed (public info only, **no source available**, not
reviewed): XBOW, NodeZero (Horizon3.ai), Pentera, RidgeBot, Mindgard.

---

## Open-source frameworks (code reviewed)

### PentestGPT  (GreyDGL/PentestGPT — license: see repo; ~13.7k stars)
- **Core idea:** three separated modules — **reasoning / generation / parsing**
  — that maintain an explicit **Pentesting Task Tree (PTT)** as the run's source
  of truth.
- **Standout pattern:** the reasoning model is decoupled from the parsing model
  (`--reasoning-model` vs `--parsing-model`): a strong model plans, a cheap model
  condenses tool output. Current package is event-driven
  (pipeline / controller / session / events).

### VulnBot  (KHenryAegis/VulnBot — published multi-agent framework; ~175 stars)
- **Core idea:** role-specialized agents — **Collector -> Scanner -> Exploiter**
  — each a `Role` with its own goal, tool set, and prompt, driven by a `Planner`
  that writes and walks a task tree.
- **Standout patterns:**
  - **LLM success-gating:** a `check_success` step judges whether a task
    succeeded before the planner advances.
  - **Separate planning vs execution context** (`plan_chat_id` / `react_chat_id`)
    so raw tool output never pollutes the planning transcript.
  - **Cross-phase summary** (`PlannerSummary`) — a compressed handoff between
    phases instead of carrying full history.
  - **DB-backed, session-resumable** runs.

### PentAGI  (vxcontrol/pentagi — Apache-adjacent; ~17.7k stars)
- **Core idea:** a Go **flow** abstraction (a first-class, resumable run) over a
  multi-agent system, with containerized tool execution (20+ tools).
- **Standout patterns:** **versioned prompts + full observability** (Langfuse
  tracing of every agent call), a **knowledge-graph memory** (Graphiti) for
  structured run memory, and sandboxed/reproducible tool execution.

### KaliGPT  (SudoHopeX/KaliGPT — ~520 stars)
- **Core idea:** an agentic Kali CLI helper — multi-provider LLM, tool-calling,
  slash commands (`/list-tools`), a guidance mode.
- **Read:** closest peer in *spirit* but architecturally shallow (a tool-calling
  chat assistant, not a deep autonomous chain). Useful UX cues, little loop depth.

---

## Patterns worth adopting (ranked by fit to ERR0RS on the Pi / gemma3:1b)

1. **Split reasoning from parsing** (PentestGPT). Use gemma3:1b as the cheap
   parser/condenser (tool output -> structured findings) and route heavier
   reasoning to a larger model when one is available. Best fit for the TTFT /
   context budget.
2. **Separate plan-context from exec-context** (VulnBot). Keep raw tool output
   out of the planning transcript — large win on a small context window.
3. **Compress across phases** (VulnBot PlannerSummary). A short phase summary
   instead of full history before the next phase.
4. **Explicit, persisted task tree with per-task status** (PentestGPT, VulnBot).
   Makes the chain resumable and lets the narrator show real progress.
5. **LLM success-gating before advancing** (VulnBot). Wire into the existing
   next_step engine.
6. **Role-specialized prompts + tool subsets per phase** (VulnBot) over one
   monolithic agent prompt.
7. **Versioned prompts + decision logging / observability** (PentAGI). Treat
   prompts as versioned artifacts; log agent decisions for debugging and as a
   research/credibility artifact.
8. **Structured run memory** (PentAGI knowledge graph). A "what we've learned
   about this target" store beyond flat RAG (advanced; later).
9. **Sandboxed tool execution** (PentAGI). The production-grade safety pattern;
   heavy for a Pi but worth a containerized profile for x86 deployment.

## Where ERR0RS already differentiates
- Fully local / airgapped by design (most peers assume cloud LLMs).
- Education-first: a 83-lesson teach engine + RAG that no competitor pairs with
  the autonomous loop.
- CFAA-aware safety gate and tiered operator attestation.

## Honest gaps vs the field
- No explicit, persisted task-tree object yet (missions are more linear).
- Single-model loop; no reasoning/parsing split.
- No per-run decision log / prompt versioning.
- Tool execution is direct, not sandboxed.

## Suggested next steps
1. Introduce a first-class, persisted **Plan/Task-tree** object with status.
2. Add a **parser pass** (gemma3:1b) that condenses tool output into structured
   findings before the reasoning step sees it.
3. Separate **plan vs exec** conversation contexts.
4. Add a lightweight **decision log** per run.
5. (Closed-competitor parity) wire **XBOW's open validation-benchmarks** as an
   eval harness to measure ERR0RS objectively.

*Closed products (XBOW, NodeZero, Pentera, RidgeBot, Mindgard) were not
code-reviewed — no public source. Capability comparison from public material
can be added separately and should be labelled as such.*

---

## Addendum — PentAGI deep read (Go source + prompt templates)

The prompt-template roster (`backend/pkg/templates/prompts/`) reveals a much
finer-grained multi-agent system than the first pass suggested. It runs a
**primary orchestrator** over a roster of **specialist agents**, each with its
own prompt:

- Operators: **pentester**, **coder**, **searcher**, **installer**, **adviser**, **reporter**
- Planning: **subtasks_generator**, **subtasks_refiner**, **task_planner**, **task_descriptor**
- Oversight: **reflector** (self-critique), **execution_monitor**
- Context mgmt: **summarizer**, **enricher**, **memorist**, short/full execution-context builders
- Robustness: **toolcall_fixer** / **input_toolcall_fixer** — agents that repair
  malformed tool calls before they fail
- Routing: a parallel set of **`question_*`** prompts (question_pentester,
  question_coder, …) that cheaply decide *whether/which* specialist should act

The flow engine (`controller/flow.go`) is a DB-persisted `flowWorker` with
concurrency control (mutexes/waitgroups/cancellation), Langfuse tracing, and
multiple concurrent "assistant workers."

### New high-value patterns for ERR0RS (beyond the first list)

10. **toolcall_fixer / format-repair pass.** Small models (gemma3:1b) routinely
    emit malformed JSON / tool calls. A dedicated repair pass that salvages a bad
    call instead of failing the step is the natural sibling of our reasoning/parsing
    split — cheap, and a big reliability win on the Pi.
11. **`question_*` gating before invoking a specialist.** A one-token "should the
    pentester act now?" check avoids running every agent each turn — efficient
    routing on limited compute.
12. **Dedicated context-management agents** (summarizer / enricher / memorist).
    Formalizes the cross-phase compression we already flagged, as first-class roles.
13. **Reflector / execution_monitor loops.** Explicit self-critique and execution
    oversight, separate from the acting agent.

These reinforce the direction: on a small local model, ERR0RS wins by *decomposing*
into cheap specialized passes (parse, fix, gate, summarize) around a thin reasoning
core — not by asking one prompt to do everything.
