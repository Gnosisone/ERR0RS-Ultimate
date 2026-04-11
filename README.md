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

**AI-Powered Penetration Testing Platform · Purple Team · Cybersecurity Education**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Kali%20%7C%20Parrot%20%7C%20Pi5-557C94?style=flat-square&logo=linux&logoColor=white)](https://kali.org)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/badge/Release-v1.0.0-7c3aed?style=flat-square)](https://github.com/Gnosisone/ERR0RS-Ultimate/releases)
[![Modules](https://img.shields.io/badge/Tool%20Modules-25%2B-0ea5e9?style=flat-square)]()
[![Local](https://img.shields.io/badge/LLM-100%25%20Local-f97316?style=flat-square)](https://ollama.com)
[![Pi5](https://img.shields.io/badge/Hardware-Pi%205%20%2B%20Hailo--10H-c51a4a?style=flat-square&logo=raspberry-pi&logoColor=white)]()

*100% local · zero data leaves the OS · built for professional red teams and security education*

[Installation](#-installation) · [Quick Start](#-quick-start) · [Architecture](docs/ARCHITECTURE.md) · [Philosophy](PHILOSOPHY.md) · [Research](RESEARCH.md)

</div>

---

## What is ERR0RS?

ERR0RS-Ultimate is a fully local, AI-powered security platform that runs inside Kali Linux and Parrot OS. It wraps 25+ security tool modules in a conversational interface, autonomously executes kill-chain workflows, teaches offensive and defensive techniques inline, and generates professional pentest reports — all without sending a single byte of client data to the cloud.

Think of it as a senior red teamer sitting next to you: running the tools, explaining every decision, correlating findings across the engagement, and writing the report at the end.

> *"Technology cannot be patched. Humans cannot be patched. ERR0RS teaches you to attack and defend both."*

---

## Core Capabilities

| | Capability | Detail |
|---|---|---|
| 🧠 | **AI Brain** | Local Ollama LLM with ReAct agent loop · 5 operator modes · cloud optional |
| 🚀 | **Autopilot** | Autonomous kill-chain runner · scan → enumerate → exploit → report |
| 📋 | **Workflow Engine** | YAML-defined multi-step engagements · `webapp`, `network`, `hardware_attack` |
| 📚 | **Teach Mode** | Every command explained inline · 41 offline lessons · MITRE ATT&CK mapped |
| 🔌 | **Hardware Control** | Flipper Zero · USB Rubber Ducky · Bash Bunny · WiFi Pineapple · Shark Jack |
| 🌐 | **Live Dashboard** | Flask + SocketIO real-time web UI · device status · live event feed |
| 📄 | **Report Generator** | Professional Markdown + HTML + JSON · severity ranked · MITRE linked |
| 🔐 | **Auth + Audit** | bcrypt auth · SQLite session store · full audit log |
| 🧬 | **Knowledge Base** | 50+ curated security repos as RAG-indexed submodules |
| 🛡️ | **Purple Team** | Every offensive technique paired with defensive countermeasures |

---

## Quick Start

```bash
# Clone with submodules
git clone --recurse-submodules https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate

# Install (Kali / Parrot)
chmod +x install.sh && ./install.sh

# Configure
cp configs/config.template.env .env
nano .env   # Set LLM_BACKEND, FLIPPER_PORT, etc.

# Launch
python main.py              # Interactive terminal
python main.py --dashboard  # Live web dashboard → http://127.0.0.1:5000
python main.py --api        # REST API → http://0.0.0.0:8000/docs
```

---

## Launch Modes

```bash
python main.py                              # Interactive terminal (default)
python main.py --dashboard                  # Flask + SocketIO live dashboard
python main.py --api                        # FastAPI REST server + Swagger docs
python main.py --workflow webapp 10.0.0.1   # Run a workflow directly
python main.py --report 10.0.0.1            # Generate report and exit
python main.py --query "enum SMB shares"    # Single query mode
python main.py --learn                      # Enable inline education mode
python main.py --safe                       # Safe mode — no real hardware execution
python main.py --agent blue_team            # Start in blue team analyst mode
```

---

## Terminal Commands

Once inside the interactive shell:

```
ERR0RS [red_team]> target 192.168.1.10        # Set active target
ERR0RS [red_team]> run scan 192.168.1.10      # Execute a plugin command
ERR0RS [red_team]> workflow webapp 10.0.0.1   # Run full web app assessment
ERR0RS [red_team]> autopilot 10.0.0.1         # Autonomous kill chain
ERR0RS [red_team]> devices                    # List connected hardware
ERR0RS [red_team]> deploy flipper rfid_read   # Deploy hardware payload
ERR0RS [red_team]> explain sql injection      # Teach engine — any topic
ERR0RS [red_team]> report 10.0.0.1            # Generate pentest report
ERR0RS [red_team]> agent blue_team            # Switch operator mode
ERR0RS [red_team]> learn                      # Toggle education mode on/off
```

---

## Architecture

```
User Input (CLI / Dashboard / API)
         │
         ▼
   CommandRouter ──── NLI / Language Layer
         │
    ┌────┴────┐
    │         │
PluginManager  AI Brain (Ollama / Claude / GPT)
    │         │
    │    ┌────┴────────────────┐
    │    │  ReAct Agent Loop   │
    │    │  ChromaDB RAG       │
    │    │  Knowledge Base     │
    │    └────────────────────-┘
    │
    ▼
Kali Tools (nmap · sqlmap · metasploit · aircrack · hydra · 25+ more)
    │
    ▼
Interpreter → Findings → Report Generator
    │
    ▼
EventBus → SocketIO Dashboard (real-time)
```

**Key subsystems:**

- `src/core/plugin_base.py` — Every tool is a `BasePlugin` subclass with `conditions()`, `suggest()`, `explain()`, `analyze()` hooks wired into autopilot and education
- `src/core/autopilot.py` — Autonomous kill-chain: sweeps plugin conditions, calls LLM for structured JSON next-action, escalates through stages
- `src/core/workflow/` — YAML-driven multi-step workflows with condition evaluation, safe_mode gate, and per-step education
- `src/core/hardware/` — `HardwareManager` registry over `DeviceBase` subclasses for Flipper Zero, Hak5, and more
- `src/ui/dashboard/` — Flask + SocketIO live dashboard with 14 REST endpoints and bcrypt-authenticated sessions
- `src/reporting/` — `Finding` dataclass, heuristic output parser, MITRE ATT&CK links, Markdown + HTML + JSON export

Full technical reference: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Hardware Stack

ERR0RS runs as a portable field unit on Raspberry Pi 5 (Cyberdeck build):

| Component | Purpose |
|---|---|
| Raspberry Pi 5 8GB | Main compute |
| Hailo-10H NPU (40 TOPS) | Local AI inference acceleration |
| Geekworm X1004 NVMe HAT | Fast storage |
| WiFi Pineapple Nano | 2.4GHz wireless attacks |
| Alfa AWUS036ACM | 5GHz wireless coverage |
| Flipper Zero (RogueMaster) | Sub-GHz · NFC · BadUSB · IR |
| ESP32 w/ Marauder | WiFi / Bluetooth probing |
| CC1101 | Sub-GHz RF |

Also runs on any standard x86_64 Kali / Parrot installation.

---

## Plugin System

Every tool is a plugin — a directory with `manifest.json` + a `Plugin(BasePlugin)` class.

```python
class Plugin(BasePlugin):
    def run(self, command, args) -> PluginResult:
        # Execute the tool
        return self.shell(f"nmap -sV {args['target']}")

    def conditions(self, context) -> bool:
        # When should autopilot invoke this?
        return len(context.get("open_ports", [])) > 0

    def suggest(self, context) -> str:
        # What to recommend in autopilot output
        return f"Run service version scan on {context['active_target']}"

    def explain(self) -> dict:
        # Teaching card rendered in --learn mode and reports
        return {
            "name": "Nmap",
            "description": "Network mapper — port scanning and service detection",
            "mitre_id": "T1046",
            "mitre_tactic": "Discovery",
            "defend": "Monitor for SYN flood patterns; deploy honeypots on unused ports",
        }

    def analyze(self, output) -> list:
        # Extract structured findings from raw tool output
        findings = []
        if "22/tcp open" in output:
            findings.append({"title": "SSH Exposed", "severity": "medium", ...})
        return findings
```

---

## Workflow Engine

Define multi-step engagements in YAML:

```yaml
id: webapp
name: Web Application Assessment

steps:
  - name: Port & Service Recon
    command: scan
    args: { target: "{target}" }
    learn: true

  - name: Analyse Services
    type: analyze

  - name: Web Vulnerability Scan
    command: web_scan
    args: { target: "{target}" }
    condition: '"http" in services or "https" in services'
    learn: true

  - name: SQL Injection Test
    command: sqlmap
    args: { target: "{target}" }
    condition: 'forms_detected == True'
```

```bash
# Run from CLI
python main.py --workflow webapp 192.168.1.10

# Or interactively
ERR0RS [red_team]> workflow webapp 192.168.1.10

# Built-in workflows: webapp · network · hardware_attack · quick
```

---

## LLM Backends

| Backend | Privacy | Cost | Best For |
|---|---|---|---|
| **Ollama** (default) | 🟢 100% local | Free | All client work · air-gapped ops |
| **Anthropic Claude** | 🟡 API calls | Paid | Highest quality reasoning |
| **OpenAI GPT** | 🟡 API calls | Paid | Alternative cloud option |

```bash
# .env configuration
LLM_BACKEND=ollama          # default — fully offline
LLM_BACKEND=anthropic       # Claude via API key
LLM_BACKEND=openai          # GPT via API key

# Default local model
OLLAMA_MODEL=qwen2.5-coder:7b   # runs well on Pi 5 with Hailo-10H
```

---

## Installation

### Kali Linux / Parrot OS (recommended)

```bash
git clone --recurse-submodules https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate
chmod +x install.sh && ./install.sh
cp configs/config.template.env .env
```

### Raspberry Pi 5 (field deployment)

```bash
# Run the Pi 5 first-boot setup script
chmod +x scripts/pi5_first_boot.sh && ./scripts/pi5_first_boot.sh

# Install Hailo-10H NPU driver
chmod +x scripts/install_hailo_h10.sh && ./scripts/install_hailo_h10.sh

# Then standard install
./install.sh
```

### Manual dependency install

```bash
pip install -r requirements-kali.txt --break-system-packages

# Optional: Flask dashboard
pip install flask flask-socketio --break-system-packages

# Optional: bcrypt auth
pip install bcrypt --break-system-packages
```

### Required environment variables (`configs/config.template.env`)

```bash
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_HOST=http://localhost:11434

# Optional: cloud LLM
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Hardware
FLIPPER_PORT=/dev/ttyACM0
ERR0RS_SAFE_MODE=false

# Dashboard
ERR0RS_SECRET=change-me-in-production
ERR0RS_DB=errors.db
```

---

## REST API

Start with `python main.py --api` — Swagger UI at `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check + AI status |
| `POST` | `/ask` | Natural language query |
| `GET` | `/plugins` | List loaded plugins |
| `POST` | `/plugins/run` | Execute plugin command |
| `GET` | `/session` | Current session summary |
| `GET` | `/devices` | Hardware device list |
| `POST` | `/devices/deploy` | Deploy hardware payload |
| `GET` | `/workflows` | Available workflows |
| `POST` | `/workflows/run` | Run a workflow |
| `POST` | `/report` | Generate pentest report |

Dashboard API (port 5000): `GET /api/health` · `POST /api/reports/generate` · `POST /api/devices/safe_mode` · and 10 more.

---

## Knowledge Base

50+ curated security researcher repositories indexed as RAG-ready git submodules:

```
knowledge/
├── evasion/         # AV/EDR bypass techniques
├── windows/         # Windows exploitation (PowerSharpPack, WinPwn)
├── credentials/     # Credential harvesting and cracking
├── badusb/          # BadUSB payloads (rocketgod collection)
├── threat-intel/    # CTI frameworks and datasets
├── osint/           # OSINT tools and techniques
├── social-engineering/  # SET and SE frameworks
├── mobile/          # iOS/Android security research
├── ai-security/     # AI/ML attack and defense research
└── ...
```

Powered by ChromaDB vector search — every lesson, suggest, and AI response is grounded in curated research.

---

## Research & Citation

ERR0RS-Ultimate is a published academic research artifact. Full paper: [`RESEARCH.md`](RESEARCH.md)

```bibtex
@software{schneider2025err0rs,
  author    = {Schneider, Gary Holden},
  title     = {{ERR0RS-Ultimate}: An AI-Powered Purple Team Security Platform},
  year      = {2025},
  url       = {https://github.com/Gnosisone/ERR0RS-Ultimate},
  note      = {Penetration testing automation with inline cybersecurity education}
}
```

---

## Philosophy

ERR0RS is built on three pillars:

**1. Purple team by default.** Every offensive technique surfaces its defensive countermeasure. Attackers and defenders train on the same platform.

**2. Sovereignty over data.** Client data never leaves the machine. Local LLM, local RAG, local database. Air-gap deployable.

**3. Education at every step.** The platform teaches while it operates. Every scan result, every finding, every payload is explained in plain language. The goal is an operator who understands their tools — not one who just runs them.

Full manifesto: [`PHILOSOPHY.md`](PHILOSOPHY.md)

---

## Project Structure

```
ERR0RS-Ultimate/
├── main.py                   # Single entry point — all modes
├── src/
│   ├── ai/                   # LLM routing, RAG, ReAct agents
│   ├── core/
│   │   ├── plugin_base.py    # BasePlugin + PluginResult
│   │   ├── autopilot.py      # Autonomous kill-chain runner
│   │   ├── workflow/         # YAML workflow engine
│   │   ├── hardware/         # Flipper Zero, Hak5, device registry
│   │   ├── context.py        # SharedContext + EventBus
│   │   └── db.py             # SQLite — auth, sessions, findings, audit
│   ├── tools/                # 25+ Kali tool plugin wrappers
│   ├── education_new/        # Teach engine · 41 offline lessons
│   ├── reporting/            # MD / HTML / JSON report generator
│   └── ui/
│       ├── cli.py            # Interactive terminal
│       └── dashboard/        # Flask + SocketIO live dashboard
├── workflows/                # YAML kill-chain definitions
├── knowledge/                # 50+ security repos (git submodules)
├── docs/                     # ARCHITECTURE.md + reference docs
├── scripts/                  # Install + Pi setup scripts
├── configs/                  # config.template.env · tools.conf
└── tests/                    # Test suite
```

---

## Contributing

Pull requests welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

**High-value contributions:**
- New tool plugins (any `BasePlugin` subclass with `manifest.json`)
- Additional YAML workflows
- Education content (new lessons for `teach_engine.py`)
- Report template improvements
- Hardware device adapters (`DeviceBase` subclasses)

**Before submitting:** run `python tests/test_errors.py` — all tests must pass.

---

## Credits & Shoutouts

Built by **Gary Holden Schneider (Eros)** | [github.com/Gnosisone](https://github.com/Gnosisone)

Standing on the shoulders of the security community. Full credits: [`CREDITS.md`](CREDITS.md) · [`SHOUTOUTS.md`](SHOUTOUTS.md)

Special recognition: [@rocketgod-git](https://github.com/rocketgod-git) · [@justcallmekoko](https://github.com/justcallmekoko) · [@UNC0V3R3D](https://github.com/UNC0V3R3D) · [@xssnick](https://github.com/xssnick) · and the entire Flipper Zero + Hak5 open source community.

---

## Legal

ERR0RS-Ultimate is designed exclusively for **authorized penetration testing, security research, and cybersecurity education**.

- Only use against systems you own or have explicit written permission to test
- The authors accept no liability for unauthorized or illegal use
- See [`SECURITY.md`](SECURITY.md) for responsible disclosure policy

---

<div align="center">

**Built in Oklahoma City · Runs on a Raspberry Pi · Ships on a Cyberdeck**

*"Stay ethical out there."*

[![GitHub](https://img.shields.io/badge/GitHub-Gnosisone-181717?style=flat-square&logo=github)](https://github.com/Gnosisone/ERR0RS-Ultimate)

</div>
