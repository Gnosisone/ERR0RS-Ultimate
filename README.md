<div align="center">

```
  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
                        U L T I M A T E
```

**The open-source AI security platform built for everyone who can't afford the enterprise tools.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Kali%20%7C%20Parrot%20%7C%20Pi5-557C94?style=flat-square&logo=linux&logoColor=white)](https://kali.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v3.7.0-7c3aed?style=flat-square)](CHANGELOG.md)
[![Tool Registry](https://img.shields.io/badge/Tool%20Registry-5036%20tools%20%7C%2067%20fully%20taught-0ea5e9?style=flat-square)](src/tools/tool_registry.v3.json)
[![Arsenal](https://img.shields.io/badge/Phoenix%20Arsenal-2172%20Tools-ff6b00?style=flat-square)]()
[![Backends](https://img.shields.io/badge/LLM-Claude%20%E2%86%92%20DeepSeek%20%E2%86%92%20Ollama-f97316?style=flat-square)](docs/BACKEND_STRATEGY.md)
[![Pi5](https://img.shields.io/badge/Hardware-Pi%205%20%2B%20Hailo--10H-c51a4a?style=flat-square&logo=raspberry-pi&logoColor=white)]()
[![Stars](https://img.shields.io/github/stars/Gnosisone/ERR0RS-Ultimate?style=flat-square&color=7c3aed)](https://github.com/Gnosisone/ERR0RS-Ultimate/stargazers)
[![Juice Shop Coverage](https://img.shields.io/badge/Juice%20Shop-54%2F111%20(48.6%25)-22c55e?style=flat-square)](https://github.com/Gnosisone/juice-shop-portfolio)
[![Contributors Welcome](https://img.shields.io/badge/Contributors-Welcome-ec4899?style=flat-square)](#-help-build-this-call-for-contributors)

*Runtime is 100% local · zero data leaves the machine · built for red teams, blue teams, and students who are becoming both*

**[Install](#-installation) · [Quick Start](#-quick-start) · [Backends](#-llm-backends) · [Architecture](docs/ARCHITECTURE.md) · [Philosophy](#-philosophy) · [Research](RESEARCH.md) · [Portfolio](https://github.com/Gnosisone/juice-shop-portfolio) · [Contribute](#-help-build-this-call-for-contributors)**

</div>

---

## What is ERR0RS?

ERR0RS-Ultimate is an AI-powered security platform that wraps a 5,036-tool registry — with 67 tools fully taught at operator depth — in a conversational teaching interface, coaches operators from their first nmap scan to full kill-chain engagements, and integrates with a 2,172-tool offensive arsenal — all while keeping runtime fully local.

**It's not another wrapper script.** It's a senior red teamer who happens to be a wise and patient teacher. It sits next to you: running the tools, explaining every decision, analyzing every output, asking the clarifying questions a good mentor asks, and writing the report at the end.

For a student who can't afford a $10,000/year enterprise platform, it's the equalizer.

> *"Cobalt Strike is $3,500/year. Core Impact is $15,000/year. ERR0RS is free, runs on a $80 Raspberry Pi, and teaches you more than either of them."*

---

## Why This Exists

The security industry has an access problem.

Commercial AI security platforms cost $10,000–$50,000+ annually. Meanwhile, criminal ecosystems offer AI-powered attack tools for $200/month. The asymmetry is getting worse every year. Students at community colleges, self-taught practitioners, security teams at small nonprofits — they're being priced out of the tools they need to compete and protect.

ERR0RS closes that gap. It is built on a simple belief: **security knowledge belongs to everyone who needs it to protect systems and people.** Not just to organizations with enterprise budgets.

Every technique in ERR0RS is paired with its defensive countermeasure. Every command is explained before it runs. Every finding is analyzed and contextualized. The platform is designed to produce security professionals, not just tool operators.

---

## What's New in v3.7.0 — "SOC Mentor"

This release lands the **operator-progression layer** that turns ERR0RS from a tool dictionary into a guided learning environment. The headline feature: every lesson now teaches the *strategic* and *OPSEC* dimensions of a tool, not just its flags.

- **🥷 SOC Mentor lesson layer — 23/23 topics covered.** Every `teach <topic>` now ends with a noise-rated coaching block: TL;DR strategic value, 🟢/🟡/🔴 noise level with explanation, ordered next-best-steps (quietest first), and 4 concrete OPSEC tips per tool. The constitution this implements: *"ERR0RS is the ultimate SOC mentor. He should teach his SOC apprentice how to be as stealthy and quiet as possible, as to not expose the test until the operator is ready for the client to know that they are in."* Lives in `src/core/soc_mentor.py`.
- **Persistent server-authoritative mission state.** `~/.err0rs/mission_state.json` is the single source of truth. Survives reboots, browser refreshes, and tab close. Auto-clears on completion with a one-shot `just_completed` flag so the celebration card fires exactly once.
- **Mission 01: Your First Recon — fully playable.** 3-step nmap → nikto → gobuster walkthrough against OWASP Juice Shop. Each step has rich coaching fields (instruction, what_it_does, what_to_look_for, xp_reward). ▶ RUN STEP button fires the command verbatim, bypassing the intent parser so the mission's exact args reach the tool.
- **Mission 02: SQL Injection Fundamentals — shipped.** 4 steps, +175 XP. Manual curl → classic `' OR 1=1--` payload → JWT decode → sqlmap automation. Teaches the SOC-mentor approach: harvest server error messages before guessing payloads; prefer offline cracking over online brute.
- **Per-launch ethics gate.** Every launcher boot re-fires the 5-clause ethical use agreement (red-bordered fullscreen modal, checkbox + I AGREE). PID-based invalidation: relaunch = new PID = gate re-fires. No bypasses.
- **Operator Profile panel.** Extends the existing skill panel with three new sections: OPERATOR (name, skill, sessions, achievements), MODES (Teach Mode / Auto-Coach / Mentor Context toggles), ACTIONS (Continue Lessons, Restart Mission, Reset Profile). Reset is two-click with automatic backup of `~/.err0rs/` before wipe.
- **Welcome-back greeting card** on every launch after ethics-gate, with tone calibrated to skill level (`Welcome back, NAME.` for guided / `NAME.` for pro), and a "next action" button — Continue Mission if active, Next Lesson if not, just a greeting if both are clear.
- **XP awards on EVERY tool execution path.** Brain `_run_tool`, LiveProcess terminal-box runs, and AutoKillChain phase loops all now fire `award_xp('run_<tool>')` and `found_vuln` events. Skill domains and achievements finally populate from real activity.
- **Lesson completion tracking.** Each `teach <topic>` automatically marks the topic completed, awards 30 XP via `complete_lesson` event, and advances the lesson counter on the skill panel. Continue Lessons now actually progresses through all 23 topics instead of re-serving the first one.
- **Architectural xterm typing fix.** `xset r off` disables X11 keyboard auto-repeat during synthetic typing so the X server can't emit stuck-key repeats, then `xset r on` restores in a `finally` block. Combined with a goldilocks 50ms delay, gobuster commands type as `wordlists` (correctly) instead of `worrrrdllllists` or `wordlist`.
- **Phoenix Arsenal page linked** in the topbar. `arsenal.html` (789-line tool grid, 92 curated + 2000+ BlackArch) is now reachable via a cyan 🔱 ARSENAL pill — was previously a finished feature with zero links to it from anywhere.
- **Payload Studio: ATTACKER_IP auto-substitution.** When listener spins up, backend resolves the Pi's outbound interface IP via UDP-socket trick (no nmap needed), and the editor replaces `ATTACKER_IP` placeholders with the real value. Snippet library (21 BadUSB/BadKB payloads across 4 platforms) restored after fixing same string-literal truncation bug class as v3.6.

### v3.7.0 field-hardening (post-launch, live-repo fixes)

After the first cohort of students started running ERR0RS live, a round of field fixes hardened the lesson path end to end:

- **Verbatim command honoring.** Typed commands now run exactly as entered. Previously `nmap -sV -p 80,443,3000,8080 localhost` was silently rewritten to `nmap -O localhost` — the intent parser re-derived its own flags and a substring bug matched `os` inside `localhost`. The parser now passes operator-supplied flags through untouched for every tool, and tool/flag matching is whole-word so short aliases never fire inside ordinary words.
- **SOC-mentor target-down coaching.** When a tool can't reach its target (lab not started, wrong port), ERR0RS recognizes the connection failure, tells the student *why* and *how to fix it* (with a one-click `start_lab.sh` suggestion), and skips the expensive LLM next-step call instead of freezing. Teach the recovery, don't dump a raw error.
- **Arsenal RUN / INFO buttons + rich usage cards.** Tool cards in the Phoenix Arsenal are now click-reliable (index-based handlers replaced fragile JSON-in-attribute markup), and the INFO panel renders a real usage card per tool: summary, 2–4 example invocations with plain-English explanations, and OPSEC tips. Clicking an example loads it into the args box. Backed by `src/core/tool_usage.py`.
- **Resilient operator terminal.** Every `xdotool` call in the synthetic-typing path is individually timeout-guarded so one slow X11 call on a loaded Pi can never abort the whole command (the cause of "RUN STEP errored and typed nothing").
- **Lab + hardware reliability.** `start_lab.sh` detects the docker-group permission gap and falls back to sudo or guides the one-time fix; `pyserial` is pinned in requirements and installed in the venv so the Flipper Evolution Engine loads cleanly.

See [CHANGELOG.md](CHANGELOG.md) for the complete commit-by-commit changelist.

---

## What's New in v3.6.0 — "Teach Knowledge Drop"

This release lands the first major payload of operator-grade teach content into the canonical registry and ships the infrastructure that made it sustainable to produce.

- **67 tools fully taught at operator depth** — every one now carries 6 opsec notes (current to 2025–2026 EDR/AMSI/ETW-TI tradecraft), 2 sample command outputs (beginner + advanced operator scenario), 3 legal notes (CFAA / ROE / cloud automated-response considerations), 5 false-positive traps, and full MITRE ATT&CK technique mappings. Total: **1,328 distinct pieces of red-team teach content** across the registry.
- **RAG knowledge base online** — `tools/ingest_teach_to_rag.py` embeds all 67 teach cards into a local ChromaDB collection (`err0rs_teach_v1`) using `all-MiniLM-L6-v2`. Semantic queries like "kerberoasting active directory" surface the right card (Rubeus) every time. Pi 5 CPU-resident, no GPU needed.
- **`err0rs-qwen` model baked** — the ERR0RS soul (`src/ai/system_prompt.md`) is now embedded directly into a customized `qwen2.5-coder:7b` via Modelfile. Tertiary-tier offline inference inherits the teacher voice without prompt-injection.
- **Build-time teach generator hardened** — `tools/generate_teach.py` cost-tracking rewrite: real per-million-token billing from `msg.usage` (not flat per-call guesses), per-model rate overrides (Sonnet vs Opus vs Haiku), and a cap loop that fires on actual spend. Projection accuracy improved from −56% to −7%.
- **Human-in-the-loop merge tool** — `tools/merge_generated.py` with interactive per-card review (approve/skip/edit/diff/quit), atomic writes, git tags + backup files + session logs, and a non-interactive `--from-decisions` batch path for trusted bulk merges.
- **Quality gates** — `tools/quality_gates.py` runs 12 categorical checks (schema completeness, character ranges, MITRE format, duplicate detection, JSON safety, command-binary cross-references) before merge to catch generator misfires.

See [CHANGELOG.md](CHANGELOG.md) for the complete changelist.

---

## Previously in v3.5.0

This release reshaped ERR0RS around a teacher-first identity and laid the infrastructure for that voice to speak through any LLM backend.

- **The ERR0RS soul** — `src/ai/system_prompt.md` is the canonical statement of who ERR0RS *is* when it speaks to a student. Loaded by every LLM backend, on every call. Switch backends and the voice stays the same.
- **Multi-backend strategy** — Claude (primary) → DeepSeek (secondary) → Ollama (tertiary). Strategy doc at [docs/BACKEND_STRATEGY.md](docs/BACKEND_STRATEGY.md).
- **Socratic teach mode** — after every tool run, ERR0RS asks the student a probing question or fires a short quiz. Wired into the `Operator` (`_socratic_question`, `_quiz`).
- **"WHY THIS?" buttons** — every suggestion card has a button that streams ERR0RS's reasoning for *why* that's the right next move in the attack chain.
- **Schema-validated tool registry** — tools live in `src/tools/tool_registry.v3.json` with 8.6 average flags per tool, full output-reading patterns, and the teach fields v3.6.0 has now begun to fill.
- **Phase 3 teach generator** — `tools/generate_teach.py` produces opsec notes, sample outputs, legal notes, false positives, and MITRE ATT&CK technique IDs for every tool. Build-time, runtime stays offline.
- **Preflight checks** — startup health checks for Python deps, Ollama, security tools on PATH. `python3 main.py --no-preflight` skips them for faster boot.
- **First-run setup wizard** — `python3 main.py --setup` walks new users through `.env` config.
- **Install.sh full tool universe** — 35+ net new tools across apt, Go, pip, and GitHub paths. `--with-c2`, `--with-knowledge-repos`, `--with-submodules` flags for optional heavy installs.

---

## Core Capabilities

### 🧠 The ERR0RS Soul — A Teacher, Not a Tool

ERR0RS isn't ChatGPT with a hacking persona. The file [`src/ai/system_prompt.md`](src/ai/system_prompt.md) defines who ERR0RS *is* — wise, compassionate, patient; honest about uncertainty; fluent across the entire purple-team curriculum from recon through post-exploitation, defense, and modern 2025-2026 tradecraft. Every LLM call across every backend prepends this prompt. The model is the substrate; the prompt is the soul.

Ask it anything:

```
» explain CIS Control 6
» walk me through a Kerberoasting attack
» what should I look for in this nmap output
» what's the difference between SSRF and CSRF
» coach me through this SQL injection
» I need to test a domain controller — what should I check first?
```

The conversation engine injects **live operator state** into every response — your active target, your recent tool runs (with severity-iconed findings), and an auto-loaded lesson for whatever tool you just ran. Mention any tool by name in chat and ERR0RS pulls its lesson on-demand. Multi-turn conversation remembers context across 20 turns.

### 🎓 The Auto Coach + Socratic Teach Mode

When any tool finishes, ERR0RS automatically analyzes the output and fires a coaching block:

```
🔴 ERR0RS ANALYSIS: SMB EXPOSED — Check for EternalBlue
────────────────────────────────────────────────────────
📋 WHAT THIS MEANS:
Port 445 is Windows SMB (file sharing). This is the port EternalBlue
(MS17-010) uses — the exploit behind WannaCry. Even on patched systems,
SMB exposes authentication hashes via NTLM relay attacks.

⚡ NEXT STEPS — click any command to paste:
  1. [Check EternalBlue]
     $ nmap --script smb-vuln-ms17-010 -p 445 192.168.1.100
  2. [Enumerate users, shares, policies]
     $ enum4linux -a 192.168.1.100

🛡️ DEFENSIVE COUNTERMEASURE:
  Disable SMBv1. Block 445 at the perimeter. Require SMB signing.
```

**Teach Mode** (toggleable in the UI with the 📚 button) layers Socratic questioning on top: after every tool run, ERR0RS asks you a probing question about what you just saw. Run the same tool three times and it pops a short quiz to make sure you've internalized the pattern.

Every suggestion card has a **"WHY THIS?"** button that streams ERR0RS's reasoning for why that tool is the right next step given your current target, findings, and where you are in the kill chain.

### 📊 Operator Progression System

Every action earns XP. Every tool run, every finding, every question asked. Six levels from Script Kiddie to Elite, tracked across 8 skill domains. The UI shows your level badge, XP bar, and per-domain skill progress in a live sidebar panel.

This is not gamification for its own sake. It's a feedback loop. When a student can see their Active Directory domain rising, it tells them where to focus next.

### 🎓 Guided Onboarding for Every Skill Level

First-time users get a 4-screen wizard: who ERR0RS is, an ethical use agreement (required, not optional), a skill self-assessment that sets the mode, and a guided first mission against OWASP Juice Shop with step-by-step coaching. Experienced operators can skip straight to expert mode via `python3 main.py --setup`.

### ⚔️ 2,172-Tool Phoenix Arsenal

When [Phoenix-OS](https://github.com/Gnosisone/Phoenix-OS) is installed, ERR0RS unlocks the full BlackArch tool arsenal. Natural language search across all 2,172 tools — "find tools for LDAP enumeration" returns the right ones. One click to execute, live terminal output, automatic coaching.

### 📚 Schema-Validated Tool Registry

[`src/tools/tool_registry.v3.json`](src/tools/tool_registry.v3.json) is the canonical knowledge base — **5,036 tools** indexed, with **67 currently taught at operator depth** (full opsec notes, sample outputs, legal notes, false positives, and MITRE ATT&CK mappings). Every tool carries flag-level teach data, output-reading patterns, and related-tool cross-references. Validated against [`tool_registry.schema.json`](src/tools/tool_registry.schema.json).

```
teach me nmap        → flags, reading output, next steps, MITRE mappings
explain OWASP        → all 10 categories with attack + defense
what is MITRE ATT&CK → all 14 tactics mapped
teach me bloodhound  → AD attack paths explained
what is CIS          → all 18 controls with implementation groups
teach me responder   → LLMNR poisoning start to finish
```

Works offline. No internet. No API keys at runtime. RAG retrieval is local ChromaDB on CPU — no GPU required.

### 🔌 Hardware Integration

Native support for the field operator's stack:

| Hardware | Capability |
|---|---|
| **Flipper Zero** | Full studio + Evolution Engine (10-level XP) + auto-detect |
| **WiFi Pineapple Nano** | PineAP engine, recon modules, client capture |
| **Alfa AWUS036ACM** | Monitor mode, packet injection, 5GHz coverage |
| **USB Rubber Ducky** | Payload library browser, DuckyScript editor |
| **Bash Bunny** | Multi-stage payload management |
| **Hailo-10H NPU** | On-device AI inference on Raspberry Pi 5 (see [docs/HAILO_PHASE3_STATUS.md](docs/HAILO_PHASE3_STATUS.md) for current acceleration status) |

### 📄 Professional Report Generation

End-of-engagement HTML reports with CVSS scoring, MITRE ATT&CK technique mapping, severity-ranked findings, and remediation recommendations. Client-ready with one command: `report`.

---

## 🤖 LLM Backends

ERR0RS's backend strategy isn't just technical — it's philosophical. Read the full reasoning in [docs/BACKEND_STRATEGY.md](docs/BACKEND_STRATEGY.md). The short version:

```
PRIMARY:    Claude (Anthropic API)
            ↓ if unavailable
SECONDARY:  DeepSeek API
            ↓ if no internet
TERTIARY:   Local Ollama
            ↓ last resort
FALLBACK:   Hand-curated registry data only (no LLM)
```

| Backend | Why it's in this position |
|---|---|
| **Claude (primary)** | Best fit for pedagogy — engages seriously with authorized security education, calibrated against fabricating MITRE IDs / CVE numbers, structured output reliable for JSON workflows |
| **DeepSeek (secondary)** | 5–10× cheaper than Claude, open weights mean DeepSeek could one day run locally on Pi 5 + Hailo NPU. Earns its slot through cost-accessibility + future-local potential |
| **Ollama (tertiary)** | True offline operation for engagements where cloud calls aren't OK. Honest caveats: slower on Pi 5 CPU (~13 min/tool for 7B), no Hailo acceleration yet |

**At runtime, ERR0RS itself ships and runs fully offline.** API keys are only needed at build time when generating teach data, or when you explicitly opt into cloud-augmented chat. The generated JSON ships with the repo.

Configure backends in `.env` (copy `.env.example` first):

```bash
ANTHROPIC_API_KEY=sk-ant-...           # primary
DEEPSEEK_API_KEY=sk-...                # secondary (optional)
LLM_BACKEND=auto                       # walks the fallback chain
LLM_FALLBACK_CHAIN=claude,deepseek,ollama
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ERR0RS WEB UI                        │
│         http://localhost:8765  ·  ws://localhost:8766   │
│  ┌──────────┐ ┌──────────────┐ ┌────────┐ ┌─────────┐  │
│  │ Terminal │ │ Intel Feed   │ │ Tools  │ │ Skills  │  │
│  │ +WHY/📚  │ │ + Phases     │ │  Grid  │ │  Panel  │  │
│  └──────────┘ └──────────────┘ └────────┘ └─────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket
┌────────────────────────▼────────────────────────────────┐
│              errorz_launcher.py (HTTP + WS server)      │
│  /api/operator/teach_mode  ·  /api/explain/suggestion   │
│  route_command() → intent_parser → smart_wizard         │
│  conversation_engine.chat_stream() → token broadcast    │
│  LiveProcess(tool) → stdout_buffer → auto_coach         │
└──┬──────────────┬──────────────┬──────────────┬─────────┘
   │              │              │              │
┌──▼─────────┐ ┌──▼─────────┐ ┌─▼─────────┐ ┌──▼──────────┐
│ LLM Router │ │ Phoenix    │ │  Tool     │ │ Progression │
│ Claude→DS  │ │  Bridge    │ │ Executor  │ │  + XP +     │
│ →Ollama    │ │ 2172 tools │ │ + Socratic│ │ teach_mode  │
│ + soul     │ │            │ │ + Quiz    │ │             │
└──┬─────────┘ └────────────┘ └─────┬─────┘ └─────────────┘
   │                                │
   ▼                                ▼
src/ai/                       ┌─────────────┐
system_prompt.md              │ Auto Coach  │
(ERR0RS soul)                 │  Analysis   │
                              └─────────────┘
```

**Stack:** Python 3.10+ · WebSockets · Ollama / Anthropic SDK / OpenAI SDK · ChromaDB RAG · nomic-embed-text · FastAPI (internal) · Vanilla JS + CSS (no framework)

**Design principles:**
- Runtime fully local — no cloud calls required for ERR0RS to operate
- Offline-first — every core feature works without internet
- Purple team — every offensive technique paired with defensive countermeasure
- Teach by default — never run a command without explaining why
- Honest about uncertainty — never fabricate CVE numbers, MITRE IDs, or detection signatures

---

## Installation

### Prerequisites

| Requirement | Notes |
|---|---|
| **Kali Linux, Parrot OS, or Ubuntu/Debian** | x86_64 or ARM64 |
| **Python 3.10+** | `python3 --version` to verify |
| **git** | `sudo apt install git` |
| **Ollama** | Installed automatically by `install.sh` |
| **~4 GB disk free** | For Ollama model + Python deps |

> 💡 **Phoenix Arsenal users:** Install [Phoenix-OS](https://github.com/Gnosisone/Phoenix-OS) **before** ERR0RS to unlock the 2,172-tool grid. ERR0RS auto-detects Phoenix at `/home/kali/Phoenix-OS`. ERR0RS works fully without Phoenix.

---

### Kali Linux / Parrot OS (recommended)

```bash
# 1. Clone
git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate

# 2. Install (handles deps, Ollama, .env, desktop icon, 35+ tools)
sudo bash install.sh

# 3. (optional) Add API keys for Claude / DeepSeek
nano .env

# 4. Launch
bash start_err0rs.sh
# Web UI opens at http://127.0.0.1:8765
```

**Install.sh flags:**

| Flag | What it does |
|---|---|
| (none) | Default: apt + Go + pip + GitHub-clone tools, Ollama, venv, desktop icon |
| `--with-c2` | Adds Sliver, Mythic, Empire, Covenant, Merlin, PoshC2 (multi-GB) |
| `--with-knowledge-repos` | Clones GTFOBins, LOLBAS, PowerSploit, PayloadsAllTheThings, HackTricks for RAG indexing |
| `--with-submodules` | Pulls all 75 knowledge submodules (10-30 min, multi-GB) |
| `--skip-go-tools` / `--skip-pip-tools` / `--skip-github-tools` / `--skip-ollama` | Skip individual install phases for minimal/offline installs |

> ✅ `install.sh` creates `.env` automatically with a generated secret key from [`.env.example`](.env.example).

---

### Raspberry Pi 5 (field deployment)

```bash
# Pi 5 first-boot setup (sets up ARM64 deps, GPU memory split)
sudo bash scripts/pi5_first_boot.sh

# Optional: Hailo-10H NPU driver (if you have the AI HAT+)
sudo bash scripts/install_hailo_h10.sh

# Standard install
sudo bash install.sh
```

> ⚠️ **Hailo + Ollama:** The Hailo-10H NPU is online and identifies via `hailortcli`, but Ollama doesn't yet use it for LLM acceleration. See [docs/HAILO_PHASE3_STATUS.md](docs/HAILO_PHASE3_STATUS.md) for current status and the four paths forward.

---

### First-Run Setup Wizard

For interactive `.env` setup:

```bash
python3 main.py --setup
```

Walks you through: backend selection, model choice, web UI bind/port, security key generation, engagement defaults, and teach mode default.

---

### Manual / Advanced Install

```bash
pip install -r requirements-kali.txt --break-system-packages

# Copy the env template and fill in your values
cp .env.example .env
nano .env
```

---

## Quick Start

Once running at `http://127.0.0.1:8765`, try these in the terminal:

```bash
# Recon
nmap -sV 192.168.1.1
scan 10.0.0.5

# Ask ERR0RS anything (engages teach mode by default)
explain sql injection
walk me through kerberoasting
what is CIS Control 6
how do I read this nmap output

# Education
teach me nmap
teach me bloodhound
what is OWASP

# Operations
target http://localhost:3000
autopilot http://localhost:3000

# Juice Shop lab
juice-shop solve all
```

Toggle teach mode in the UI with the **📚 TEACH ON/OFF** button. Click **WHY THIS?** on any suggestion card to stream ERR0RS's reasoning for why that's the right next move.

---

## Tool Registry & Teach Generator

The repo ships with a schema-validated tool registry, a build-time teach data generator, a human-in-the-loop merge tool, and automated quality gates.

```
src/tools/
├── tool_registry.schema.json       # JSON Schema (draft-2020-12)
├── tool_registry.v3.json           # 5,036 tools — canonical knowledge base
├── tool_registry.generated.json    # Sonnet-generated teach drafts (review before merge)
├── concepts.v2.json                # 7 frameworks (CIA, OWASP, MITRE, etc.)
└── tool_registry.json              # Legacy registry (preserved for compat)

tools/
├── README.md                       # Maintenance scripts guide
├── migrate_registry.py             # legacy → v3 migration (idempotent)
├── validate_registry.py            # CI-grade schema validation
├── generate_teach.py               # LLM teach generator (Claude/DeepSeek/Ollama)
├── quality_gates.py                # 12 categorical checks on generated cards
├── merge_generated.py              # Interactive review + batch apply
└── ingest_teach_to_rag.py          # Embed teach cards into local ChromaDB
```

**The full pipeline** (build-time; runtime stays offline):

```bash
# 1. Generate teach drafts (Sonnet/DeepSeek/local)
python3 tools/generate_teach.py --all --limit-cost 5.00

# 2. Pre-merge quality gates — flag any cards that need review
python3 tools/quality_gates.py

# 3. Review + merge (interactive per-card, or batched via decisions file)
python3 tools/merge_generated.py --resume
python3 tools/merge_generated.py --from-decisions /tmp/decisions.json

# 4. Embed merged cards into local RAG for runtime retrieval
python3 tools/ingest_teach_to_rag.py
```

Every merge creates a `pre-merge-*` git tag and a timestamped backup file so any merge can be rolled back instantly. Session logs land in `docs/MERGE_SESSIONS/` for auditability.

**Validate registry integrity:**
```bash
python3 tools/validate_registry.py
```

---

## Demo Mode

No lab setup needed. ERR0RS includes a built-in demonstration mode that showcases its capabilities against safe local targets:

```bash
python3 src/ui/errorz_launcher.py --demo
```

Demo mode runs against `localhost` and `127.0.0.1` only. It demonstrates tool execution with live streaming output, Auto Coach analysis blocks, conversation AI coaching with the ERR0RS soul, the progression XP system, and report generation.

---

## Validation: OWASP Juice Shop Portfolio

ERR0RS is benchmarked against [OWASP Juice Shop](https://owasp.org/www-project-juice-shop/) — the OWASP Foundation's flagship intentionally-vulnerable web application and the de-facto practical exam for application-security skills.

| Coverage tier | Status |
|---|---|
| **Manual operator coverage** *(Eros, working through challenges with ERR0RS as coach)* | **54 / 111 (48.6%)** — 2 categories complete |
| **ERR0RS autonomous coverage** *(no human in the loop)* | **18 / 111 (16%)** — 100% reliability on the 18 covered |
| **Roadmap target** | **111 / 111** by Q4 2026 |

The full breakdown — including per-challenge attack plans for the 57 unsolved challenges and the engineering roadmap to reach 111/111 autonomous coverage — lives in the dedicated portfolio repo:

> 🎯 **[github.com/Gnosisone/juice-shop-portfolio](https://github.com/Gnosisone/juice-shop-portfolio)**

Notable autonomous solves currently in the suite include SQL injection (Login Admin, User Credentials), DOM XSS, directory traversal (Forgotten Sales Backup, Confidential Document), Poison Null Byte bypass, hidden-route discovery (Score Board), and authorization-flow abuse (Admin Registration, Repetitive Registration). All run on a Raspberry Pi 5 cyberdeck running Kali ARM64 — runtime fully local, no client data ever leaves the device.

---

## Philosophy

ERR0RS is built on a belief that the security field has an access problem — and that education is the only real solution.

Every $50,000 enterprise security tool represents knowledge that exists somewhere. ERR0RS makes that knowledge accessible. Not watered-down. Not simplified to uselessness. The real thing: the same techniques, the same frameworks, the same methodologies that professional red teams use — paired with the explanations that commercial tools leave out.

The purple team philosophy is not a feature. It's the core of what this is:
- Every attack technique comes with its detection signature
- Every exploit comes with its patch
- Every credential dump comes with its hardening recommendation

Security is not a red team problem or a blue team problem. It's a shared understanding problem. ERR0RS is built to close that gap.

> *"We learn from our errors. The name isn't ironic. It's a statement of belief."*

---

## Hardware Stack (Cyberdeck Build)

The reference implementation runs on a Raspberry Pi 5 Cyberdeck:

| Component | Spec |
|---|---|
| **SBC** | Raspberry Pi 5 8GB or 16GB |
| **AI Accelerator** | Hailo-10H NPU (26 TOPS) via AI HAT+ |
| **Storage** | NVMe SSD (Geekworm X1004) |
| **WiFi Adapters** | Alfa AWUS036ACM (5GHz) + built-in Pi WiFi |
| **RF Tools** | Flipper Zero (RogueMaster) + CC1101 |
| **Wireless Attack** | WiFi Pineapple Nano |
| **HID Attack** | ESP32 with Marauder firmware |
| **Total Cost** | ~$400-500 USD |

Running Kali Linux ARM64. Full ERR0RS deployment with Phoenix Arsenal, local LLM inference, and hardware control — field-portable in a 3D-printed case.

---

## Documentation

Strategic and operational documentation for ERR0RS contributors and users:

| Document | What's in it |
|---|---|
| [`docs/BACKEND_STRATEGY.md`](docs/BACKEND_STRATEGY.md) | Why Claude is primary, DeepSeek secondary, Ollama tertiary — the philosophical reasoning behind the LLM fallback chain |
| [`docs/HAILO_PHASE3_STATUS.md`](docs/HAILO_PHASE3_STATUS.md) | Current state of Hailo NPU integration with Ollama, four viable paths forward, honest hardware reality check |
| [`docs/NEXT_SESSION.md`](docs/NEXT_SESSION.md) | Strategic handoff brief — current sprint state, open items, immediate next steps |
| [`src/ai/system_prompt.md`](src/ai/system_prompt.md) | **The ERR0RS soul** — the canonical statement of who ERR0RS is when it speaks to a student |
| [`tools/README.md`](tools/README.md) | Maintenance scripts (migration, validation, teach generation) |
| [`CHANGELOG.md`](CHANGELOG.md) | Full release history |
| [`RESEARCH.md`](RESEARCH.md) | Academic abstract |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to contribute |
| [`SECURITY.md`](SECURITY.md) | Responsible disclosure |

---

## Academic Context

ERR0RS-Ultimate began as a semester research project at Oklahoma State University's cybersecurity program, conceived to address the tools access gap in security education. The platform has been donated to OSU's cybersecurity program for educational use and is being submitted to the Kali Linux community repository.

**Citation (BibTeX):**
```bibtex
@software{schneider2026err0rs,
  author    = {Schneider, Gary Holden},
  title     = {{ERR0RS-Ultimate}: A Fully Local, AI-Powered Penetration Testing Platform},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/Gnosisone/ERR0RS-Ultimate},
  version   = {3.6.0}
}
```

Full abstract: [RESEARCH.md](RESEARCH.md)

---

## 🤝 Help Build This — Call for Contributors

**ERR0RS is built by one person right now. It shouldn't be.**

This project exists because the security industry has an access problem — and no single student can solve that alone. The codebase, the curriculum, the tool coverage, the language support, the hardware integrations — all of it gets better when more people care. If you read this far and any part of the mission resonated, there's a contribution shape for you.

### Where help is most needed

**1. Teach the next 4,969 tools.** The canonical registry has 5,036 tools indexed. 67 are taught at operator depth. That leaves nearly 5,000 tools that have flag schemas but no opsec notes, no sample outputs, no false-positive traps. The `generate_teach.py` → `quality_gates.py` → `merge_generated.py` pipeline is built and proven — adding tools is now a matter of running it, reviewing the output, and merging. Tier 2 BlackArch tools are the next priority.

**2. Command breakdowns** *(new in the roadmap, planned for v3.7.0)*. Right now `sample_outputs` shows what to run and what it does. We want a `command_breakdown` field that decomposes every command flag-by-flag — what each switch does, what happens if you change it, when to use the alternative. This is the missing layer for visual learners and self-taught operators. Schema design and Sonnet prompt-engineering both welcome.

**3. ARM64 / Raspberry Pi optimization.** The reference cyberdeck is a Pi 5 with a Hailo-10H NPU. Ollama doesn't yet use the Hailo for inference — fixing that path (or building a direct HailoRT backend) would let a $400 cyberdeck run local LLM teach without thermal throttling. Details in [docs/HAILO_PHASE3_STATUS.md](docs/HAILO_PHASE3_STATUS.md).

**4. OWASP Juice Shop autonomous coverage.** We're at 18/111 autonomously solved. The roadmap target is 111/111 by Q4 2026. The unsolved 93 are documented with attack plans in the [portfolio repo](https://github.com/Gnosisone/juice-shop-portfolio). Pick one, write a solver, send the PR.

**5. UI for the teach mode.** The teach engine is wired into the conversation engine. The "WHY THIS?" buttons exist. What we don't have yet is a polished UI for browsing the 67 teach cards as a study reference — students should be able to flip through opsec notes like flashcards before an engagement. Vanilla JS, no framework. Designers very welcome.

**6. Lessons for adjacent disciplines.** ERR0RS is currently red-team-heavy. Blue team workflows (SOC analyst Day 1, incident response playbooks, threat hunting with Sysmon/Splunk/ELK), DFIR (memory forensics with Volatility, disk imaging with FTK), cloud security (AWS/Azure/GCP misconfigurations), and AppSec (secure code review, SAST/DAST integration) all have stubs in the registry but no taught content. If your strength is one of these, the schema is ready.

**7. Translation.** Most security education content in the world is in English. ERR0RS's mission to democratize access means translating the soul, the lessons, and the curriculum into other languages. Spanish and Portuguese are highest priority based on contributor interest signals so far.

**8. Documentation, testing, and accessibility.** The README is long, the architecture doc is a stub, the test suite has gaps, and the UI hasn't been audited for screen-reader compatibility. None of these are glamorous. All of them matter.

### What we're not looking for

- "Add ChatGPT support" — the backend strategy is intentional, documented in [docs/BACKEND_STRATEGY.md](docs/BACKEND_STRATEGY.md), and not up for debate via PR
- Features that require runtime cloud calls by default — runtime stays local, period
- Anything that softens or strips the ethical guardrails in `src/ai/system_prompt.md`
- Adversarial / criminal use case enablement (ransomware kits, stalkerware, anything targeting infrastructure without authorization)

### How to start

| If you have... | Start here |
|---|---|
| 30 minutes | Add a tool to `src/tools/tool_registry.v3.json`, validate with `python3 tools/validate_registry.py`, send the PR |
| An afternoon | Write an autonomous Juice Shop solver for one of the 93 unsolved challenges in the [portfolio repo](https://github.com/Gnosisone/juice-shop-portfolio) |
| A weekend | Pick a category in the registry (say, `forensics` or `cloud`) and run the teach pipeline against its tools, review the cards, send the merge |
| Strong feelings about voice | Edit `src/ai/system_prompt.md` — treat it like editing the words of a person you respect. PRs welcome, especially ones that improve calibration on uncertainty |
| Hardware in the loop | Try the Pi 5 + Hailo build, document what breaks, send issues with reproduction steps |

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. Read [`src/ai/system_prompt.md`](src/ai/system_prompt.md) before touching the soul. Read [SECURITY.md](SECURITY.md) before reporting anything sensitive.

**Open an issue and say hi if you want to talk through what to take on. Solo development is fine. Solo development is also lonely.**

> *"We learn from our errors. The name isn't ironic. It's a statement of belief. We learn from each other's errors too."*

---

## Roadmap

| Phase | Status | What ships |
|---|---|---|
| v3.5.0 — Teacher Identity | ✅ Released | ERR0RS soul, multi-backend strategy, socratic mode, "WHY THIS?" buttons |
| v3.6.0 — Teach Knowledge Drop | ✅ **Released** | 67 tools fully taught, RAG online, merge pipeline, cost-accurate generator |
| v3.7.0 — Command Breakdowns | 🔨 Planning | `command_breakdown` schema field, flag-by-flag explanations, visual-learner UI |
| v3.8.0 — Tier-2 Expansion | 📋 Queued | Teach pipeline run across next 200 BlackArch tools |
| v3.9.0 — Hailo Native | 🔬 Research | Direct HailoRT inference backend so Pi 5 NPU runs the teach generator natively |
| v4.0.0 — Juice Shop 111/111 | 🎯 Q4 2026 | Autonomous full-coverage on OWASP Juice Shop |

---

## Security & Ethics

ERR0RS-Ultimate is for **authorized security testing, CTF competitions, and education only.**

Using these techniques against systems you do not own or have explicit written authorization to test is a federal crime under the CFAA (US), Computer Misuse Act (UK), and equivalent laws worldwide.

The platform includes an ethical use agreement that must be accepted on first run. This is not performative compliance — it reflects the belief that the security community's credibility depends on operating within legal and ethical boundaries.

The ERR0RS system prompt is explicit about this: ERR0RS engages with the full offensive curriculum for authorized students, but won't help target real people for harm, won't build mass-impact weapons, and stops students about to make a mistake (scanning out of scope, running payloads they don't understand, attacking infrastructure without authorization). A compassionate mentor is one who tells you the truth — including when the truth is "I won't walk you through this."

**Responsible disclosure:** See [SECURITY.md](SECURITY.md)

---

## License

MIT License — see [LICENSE](LICENSE)

Copyright © 2026 Gary Holden Schneider (Eros)

---

<div align="center">

**Built by a security student, for security students, because the tools should belong to everyone.**

*If ERR0RS helped you learn something, teach it to someone else.*

[![GitHub](https://img.shields.io/badge/GitHub-Gnosisone-7c3aed?style=flat-square&logo=github)](https://github.com/Gnosisone)

</div>
