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
[![Version](https://img.shields.io/badge/Version-v3.5.0-7c3aed?style=flat-square)](CHANGELOG.md)
[![Tool Registry](https://img.shields.io/badge/Tool%20Registry-49%20schema--validated-0ea5e9?style=flat-square)](src/tools/tool_registry.v2.json)
[![Arsenal](https://img.shields.io/badge/Phoenix%20Arsenal-2172%20Tools-ff6b00?style=flat-square)]()
[![Backends](https://img.shields.io/badge/LLM-Claude%20%E2%86%92%20DeepSeek%20%E2%86%92%20Ollama-f97316?style=flat-square)](docs/BACKEND_STRATEGY.md)
[![Pi5](https://img.shields.io/badge/Hardware-Pi%205%20%2B%20Hailo--10H-c51a4a?style=flat-square&logo=raspberry-pi&logoColor=white)]()
[![Stars](https://img.shields.io/github/stars/Gnosisone/ERR0RS-Ultimate?style=flat-square&color=7c3aed)](https://github.com/Gnosisone/ERR0RS-Ultimate/stargazers)
[![Juice Shop Coverage](https://img.shields.io/badge/Juice%20Shop-54%2F111%20(48.6%25)-22c55e?style=flat-square)](https://github.com/Gnosisone/juice-shop-portfolio)

*Runtime is 100% local · zero data leaves the machine · built for red teams, blue teams, and students who are becoming both*

**[Install](#-installation) · [Quick Start](#-quick-start) · [Backends](#-llm-backends) · [Architecture](docs/ARCHITECTURE.md) · [Philosophy](#-philosophy) · [Research](RESEARCH.md) · [Portfolio](https://github.com/Gnosisone/juice-shop-portfolio) · [Contribute](CONTRIBUTING.md)**

</div>

---

## What is ERR0RS?

ERR0RS-Ultimate is an AI-powered security platform that wraps 49 schema-validated security tools in a conversational teaching interface, coaches operators from their first nmap scan to full kill-chain engagements, and integrates with a 2,172-tool offensive arsenal — all while keeping runtime fully local.

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

## What's New in v3.5.0

This release reshapes ERR0RS around a teacher-first identity and lays the infrastructure for that voice to speak through any LLM backend.

- **The ERR0RS soul** — `src/ai/system_prompt.md` is now the canonical statement of who ERR0RS *is* when it speaks to a student. Loaded by every LLM backend, on every call. Switch backends and the voice stays the same.
- **Multi-backend strategy** — Claude (primary) → DeepSeek (secondary) → Ollama (tertiary). Strategy doc at [docs/BACKEND_STRATEGY.md](docs/BACKEND_STRATEGY.md).
- **Socratic teach mode** — after every tool run, ERR0RS asks the student a probing question or fires a short quiz. Wired into the `Operator` (`_socratic_question`, `_quiz`).
- **"WHY THIS?" buttons** — every suggestion card now has a button that streams ERR0RS's reasoning for *why* that's the right next move in the attack chain.
- **Schema-validated tool registry** — 49 tools in `src/tools/tool_registry.v2.json` with 8.6 average flags per tool, full output-reading patterns, and stub fields ready for LLM-generated bleeding-edge content.
- **Phase 3 teach generator** — `tools/generate_teach.py` produces opsec notes, sample outputs, legal notes, false positives, and MITRE ATT&CK technique IDs for every tool. Build-time, runtime stays offline.
- **Preflight checks** — startup health checks for Python deps, Ollama, security tools on PATH. `python3 main.py --no-preflight` skips them for faster boot.
- **First-run setup wizard** — `python3 main.py --setup` walks new users through `.env` config (backend, model, web UI, security key, engagement defaults).
- **Install.sh full tool universe** — 35+ net new tools across apt, Go, pip, and GitHub paths. `--with-c2`, `--with-knowledge-repos`, `--with-submodules` flags for optional heavy installs.

See [CHANGELOG.md](CHANGELOG.md) for the complete changelist.

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

[`src/tools/tool_registry.v2.json`](src/tools/tool_registry.v2.json) is the canonical knowledge base — 49 tools with full flag-level teach data, output-reading patterns, related tools, and stub fields for bleeding-edge content (opsec notes, sample outputs, legal notes, false positives, MITRE ATT&CK technique IDs). Validated against [`tool_registry.schema.json`](src/tools/tool_registry.schema.json).

```
teach me nmap        → flags, reading output, next steps, MITRE mappings
explain OWASP        → all 10 categories with attack + defense
what is MITRE ATT&CK → all 14 tactics mapped
teach me bloodhound  → AD attack paths explained
what is CIS          → all 18 controls with implementation groups
teach me responder   → LLMNR poisoning start to finish
```

Works offline. No internet. No API keys at runtime.

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

The repo ships with a schema-validated tool registry and a build-time teach data generator.

```
src/tools/
├── tool_registry.schema.json       # JSON Schema (draft-2020-12)
├── tool_registry.v2.json           # 49 tools — canonical knowledge base
├── concepts.v2.json                # 7 frameworks (CIA, OWASP, MITRE, etc.)
└── tool_registry.json              # Legacy registry (preserved for compat)

tools/
├── README.md                       # Maintenance scripts guide
├── migrate_registry.py             # legacy → v2 migration (idempotent)
├── validate_registry.py            # CI-grade schema validation
└── generate_teach.py               # LLM teach generator (Claude/DeepSeek/Ollama)
```

**Validate registry integrity:**
```bash
python3 tools/validate_registry.py        # 49 tools, schema-clean
```

**Generate teach data** (build-time, fills opsec_notes, sample_outputs, legal_notes, false_positives, mitre_attack stub fields):

```bash
# Sample 3 tools to gauge quality
python3 tools/generate_teach.py --sample nmap sqlmap hydra

# Full sweep (requires ANTHROPIC_API_KEY or DEEPSEEK_API_KEY in .env)
python3 tools/generate_teach.py --all
```

Output goes to `src/tools/tool_registry.generated.json` (separate from canonical v2 — human review before merge). See [`tools/README.md`](tools/README.md) for the full workflow.

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
  version   = {3.5.0}
}
```

Full abstract: [RESEARCH.md](RESEARCH.md)

---

## Contributing

We welcome contributions at every skill level. See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

**Quick paths to contribute:**
- Add a tool to `src/tools/tool_registry.v2.json` (validate with `python3 tools/validate_registry.py`)
- Add a lesson to the teach engine (`src/core/teach_engine.py`)
- Add an auto-coach rule (`src/core/auto_coach.py` — COACHING_RULES list)
- Write tests (`tests/test_errors.py`)
- Improve ERR0RS's voice — edit `src/ai/system_prompt.md` (treat like edits to a person you respect)
- Improve documentation or translate lessons

**Current priorities:**
- Phase 3b — `tools/merge_generated.py` for human-reviewed merging of LLM teach output into v2 registry
- Phase 4b — wire v2 registry teach data into Professor Engine runtime
- Phase 5 — UI Teach button + intent routing
- HailoBackend — direct HailoRT inference path so Pi 5 NPU can run the teach generator natively (currently blocked by Ollama lacking a Hailo backend)
- Burp Suite automation integration
- Windows/AD lab environment setup scripts
- Mobile platform support (NetHunter)
- ARM64 performance optimizations

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
