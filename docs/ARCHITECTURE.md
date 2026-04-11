# ERR0RS-Ultimate — Architecture Reference

> **Platform:** Kali Linux / Parrot OS (ARM64 + x86_64)  
> **Primary target hardware:** Raspberry Pi 5 8GB Cyberdeck  
> **Author:** Gary Holden Schneider (Eros) | [github.com/Gnosisone](https://github.com/Gnosisone)

---

## Overview

ERR0RS-Ultimate is a fully local, AI-powered penetration testing platform. Every component runs on-device — no data leaves the machine. It pairs offensive automation with inline defensive education, making it equally useful for red team operators and cybersecurity students.

```
User ──► CLI / Dashboard ──► CommandRouter ──► PluginManager ──► Kali Tools
                                    │
                                    ▼
                               AI Brain (Ollama / Anthropic)
                                    │
                              ┌─────┴──────┐
                          RAG (ChromaDB)   ReAct Agent Loop
```

---

## Directory structure

```
ERR0RS-Ultimate/
├── main.py                   # Entry point — all modes boot from here
├── src/
│   ├── ai/                   # LLM routing, RAG, agents
│   │   ├── errz_brain.py     # Core AI orchestrator
│   │   ├── llm_router.py     # Ollama / Anthropic / OpenAI switching
│   │   ├── rag_ingest_2026.py
│   │   └── agents/           # RedTeam, BlueTeam, BugBounty, MalwareAnalyst
│   ├── core/
│   │   ├── plugin_base.py    # BasePlugin — all tools inherit this
│   │   ├── plugin_manager.py # Load / execute / index plugins
│   │   ├── autopilot.py      # Autonomous kill-chain runner
│   │   ├── command_router.py # NLI → plugin dispatch
│   │   ├── interpreter.py    # Raw output → structured findings
│   │   ├── context.py        # SharedContext + EventBus
│   │   ├── db.py             # SQLite — users, sessions, findings, audit
│   │   ├── workflow/         # YAML-driven multi-step workflows
│   │   │   ├── loader.py
│   │   │   ├── executor.py
│   │   │   └── engine.py
│   │   └── hardware/         # Physical attack device layer
│   │       ├── device_base.py
│   │       ├── flipper.py    # Flipper Zero (wraps flipper_bridge)
│   │       ├── hak5.py       # Ducky / BashBunny / Pineapple / SharkJack
│   │       └── manager.py
│   ├── tools/                # 25+ Kali tool wrappers (plugin format)
│   │   ├── recon/            # nmap, masscan, shodan
│   │   ├── web/              # nikto, sqlmap, dirb, gobuster
│   │   ├── wireless/         # aircrack, hashcat, hostapd
│   │   ├── exploitation/     # metasploit bridge, searchsploit
│   │   ├── credentials/      # hashcat, john, hydra
│   │   ├── flipper/          # flipper_bridge, flipper_agent, evolution
│   │   └── ...
│   ├── education/            # Teach engine, knowledge base
│   │   └── teach_engine.py   # 41 offline lessons, MITRE ATT&CK map
│   ├── orchestration/        # Campaign manager, kill chain, auto runner
│   ├── reporting/            # Markdown / HTML / JSON report generator
│   ├── ui/
│   │   ├── cli.py            # Interactive terminal
│   │   └── dashboard/        # Flask + SocketIO live dashboard
│   │       ├── app.py        # App factory
│   │       ├── auth.py       # Login, register, session guard
│   │       ├── routes/api.py # 14 REST endpoints
│   │       └── routes/pages.py
│   └── plugins/              # Manifested plugins (manifest.json format)
├── workflows/                # YAML kill-chain definitions
│   ├── webapp.yaml
│   └── network.yaml
├── knowledge/                # 50+ git submodules — RAG source material
├── configs/
│   ├── config.template.env   # Copy to .env and configure
│   └── tools.conf
├── docs/                     # Reference documentation
├── scripts/                  # Install, deploy, Pi setup scripts
└── tests/
    └── test_errors.py
```

---

## Core subsystems

### Plugin system

Every tool is a plugin — a directory with `manifest.json` + a `Plugin(BasePlugin)` class.

```python
class Plugin(BasePlugin):
    def run(self, command, args) -> PluginResult: ...
    def conditions(self, context) -> bool: ...   # autopilot gate
    def suggest(self, context) -> str: ...       # autopilot hint
    def explain(self) -> dict: ...               # education card
    def analyze(self, output) -> list: ...       # finding extraction
```

### Autopilot

Autonomous kill-chain runner. On each step it:
1. Executes the current plugin
2. Calls `interpreter.analyze_output()` for fast-path findings
3. Sweeps all loaded plugins' `conditions()` for suggestions
4. Sends context + output to the LLM for a structured JSON next-action decision
5. Escalates to the next stage or stops

### Workflow engine

YAML-defined multi-step workflows. Built-ins: `webapp`, `network`, `hardware_attack`, `quick`.

```bash
python main.py --workflow webapp 192.168.1.10
errors> workflow network 10.0.0.1 --learn
```

### Hardware layer

`HardwareManager` is a single registry over `DeviceBase` subclasses:

| Device | Class | Backend |
|--------|-------|---------|
| Flipper Zero | `FlipperDevice` | `flipper_bridge.py` serial |
| USB Rubber Ducky | `Hak5Device(ducky)` | DuckyScript staging |
| Bash Bunny | `Hak5Device(bashbunny)` | Bash payload |
| WiFi Pineapple Nano | `Hak5Device(pineapple)` | REST API |
| Shark Jack | `Hak5Device(sharkjack)` | SSH |

`safe_mode=True` blocks all hardware execution globally.

### Dashboard

Flask + SocketIO real-time dashboard at `http://127.0.0.1:5000`:

- Live activity feed (WebSocket event stream)
- Device status panel
- Workflow launcher
- Payload deployer
- Report generator
- REST API at `/api/` (14 endpoints)

```bash
python main.py --dashboard
python main.py --dashboard --port 8080 --host 0.0.0.0
```

### Auth

- bcrypt password hashing (sha256 fallback if bcrypt unavailable)
- First registered user → admin role
- `login_required` / `role_required` decorators
- Full audit log in SQLite

---

## Hardware stack (field Cyberdeck)

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 8GB | Main compute |
| Hailo-10H NPU (40 TOPS) | Local AI inference |
| NVMe via Geekworm X1004 | Fast storage |
| WiFi Pineapple Nano | 2.4GHz wireless attacks |
| Alfa AWUS036ACM | 5GHz wireless coverage |
| Flipper Zero (RogueMaster) | Sub-GHz, NFC, BadUSB, IR |
| ESP32 (Marauder) | WiFi / Bluetooth probing |
| CC1101 | Sub-GHz RF |

---

## LLM backends

| Backend | Privacy | Cost | Recommended for |
|---------|---------|------|-----------------|
| Ollama (default) | 100% local | Free | All client work, air-gapped |
| Anthropic Claude | API calls | Paid | Highest quality reasoning |
| OpenAI GPT | API calls | Paid | Alternative cloud option |

Set in `.env`: `LLM_BACKEND=ollama` (default model: `qwen2.5-coder:7b`)

---

## Launch modes

```bash
python main.py                          # Interactive terminal
python main.py --dashboard              # Live web dashboard
python main.py --api                    # FastAPI REST server
python main.py --workflow webapp TARGET # Run workflow directly
python main.py --report TARGET          # Generate report and exit
python main.py --query "enum SMB"       # Single query mode
python main.py --learn                  # Enable education mode
python main.py --safe                   # Safe mode (no real hardware)
```

---

*ERR0RS-Ultimate is a purple team research platform — every offensive technique is paired with defensive countermeasures. Authorized use only.*
