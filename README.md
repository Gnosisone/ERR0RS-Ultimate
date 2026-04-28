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
[![Version](https://img.shields.io/badge/Version-v3.2.0-7c3aed?style=flat-square)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/Tests-28%2F28%20passing-22c55e?style=flat-square)](tests/)
[![Modules](https://img.shields.io/badge/Tool%20Modules-25%2B-0ea5e9?style=flat-square)]()
[![Arsenal](https://img.shields.io/badge/Phoenix%20Arsenal-2172%20Tools-ff6b00?style=flat-square)]()
[![Local](https://img.shields.io/badge/LLM-100%25%20Local-f97316?style=flat-square)](https://ollama.com)
[![Pi5](https://img.shields.io/badge/Hardware-Pi%205%20%2B%20Hailo--10H-c51a4a?style=flat-square&logo=raspberry-pi&logoColor=white)]()
[![Stars](https://img.shields.io/github/stars/Gnosisone/ERR0RS-Ultimate?style=flat-square&color=7c3aed)](https://github.com/Gnosisone/ERR0RS-Ultimate/stargazers)

*100% local · zero data leaves the machine · built for red teams, blue teams, and students who are becoming both*

**[Install](#-installation) · [Quick Start](#-quick-start) · [Demo](#-demo-mode) · [Architecture](docs/ARCHITECTURE.md) · [Philosophy](#-philosophy) · [Research](RESEARCH.md) · [Contribute](CONTRIBUTING.md)**

</div>

---

## What is ERR0RS?

ERR0RS-Ultimate is a fully local, AI-powered security platform that wraps 25+ security modules in a conversational interface, teaches offensive and defensive techniques inline, and coaches operators from their first nmap scan to full kill-chain engagements — without sending a single byte to the cloud.

**It's not another wrapper script.** It's a senior red teamer that sits next to you: running the tools, explaining every decision, analyzing every output, and writing the report at the end. For a student who can't afford a $10,000/year enterprise platform, it's the equalizer.

> *"Cobalt Strike is $3,500/year. Core Impact is $15,000/year. ERR0RS is free, runs on a $80 Raspberry Pi, and teaches you more than either of them."*

---

## Why This Exists

The security industry has an access problem.

Commercial AI security platforms cost $10,000–$50,000+ annually. Meanwhile, criminal ecosystems offer AI-powered attack tools for $200/month. The asymmetry is getting worse every year. Students at community colleges, self-taught practitioners, security teams at small nonprofits — they're being priced out of the tools they need to compete and protect.

ERR0RS closes that gap. It is built on a simple belief: **security knowledge belongs to everyone who needs it to protect systems and people.** Not just to organizations with enterprise budgets.

Every technique in ERR0RS is paired with its defensive countermeasure. Every command is explained before it runs. Every finding is analyzed and contextualized. The platform is designed to produce security professionals, not just tool operators.

---

## Core Capabilities

### 🧠 AI That Actually Understands Security

ERR0RS isn't ChatGPT with a hacking persona. It's a local LLM (Ollama) with a deep, purpose-built security prompt covering CIS Controls v8, OWASP Top 10, MITRE ATT&CK, NIST CSF, and 15+ major offensive tools. Ask it anything:

```
» explain CIS Control 6
» walk me through a Kerberoasting attack
» what should I look for in this nmap output
» what's the difference between SSRF and CSRF
» coach me through this SQL injection
```

Responses stream token-by-token and render as formatted coaching blocks with syntax-highlighted code. Multi-turn conversation remembers context across 20 turns.

### 🎓 The Auto Coach — No Silent Tool Runs

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

Works completely offline. No LLM required for coaching — deterministic rules cover 15+ tools and 20+ finding patterns.

### 📊 Operator Progression System

Every action earns XP. Every tool run, every finding, every question asked. Six levels from Script Kiddie to Elite, tracked across 8 skill domains. The UI shows your level badge, XP bar, and per-domain skill progress in a live sidebar panel.

This is not gamification for its own sake. It's a feedback loop. When a student can see their Active Directory domain rising, it tells them where to focus next.

### 🎓 Guided Onboarding for Every Skill Level

First-time users get a 4-screen wizard: who ERR0RS is, an ethical use agreement (required, not optional), a skill self-assessment that sets the mode, and a guided first mission against OWASP Juice Shop with step-by-step coaching. Experienced operators can skip straight to expert mode.

### ⚔️ 2,172-Tool Phoenix Arsenal

When [Phoenix-OS](https://github.com/Gnosisone/Phoenix-OS) is installed, ERR0RS unlocks the full BlackArch tool arsenal. Natural language search across all 2,172 tools — "find tools for LDAP enumeration" returns the right ones. One click to execute, live terminal output, automatic coaching.

### 📚 23-Topic Offline Curriculum

```
teach me nmap        → flags, reading output, next steps
explain OWASP        → all 10 categories with attack + defense
what is MITRE ATT&CK → all 14 tactics mapped
teach me bloodhound  → AD attack paths explained
what is CIS          → all 18 controls with implementation groups
teach me responder   → LLMNR poisoning start to finish
```

Works offline. No internet. No API keys.

### 🔌 Hardware Integration

Native support for the field operator's stack:

| Hardware | Capability |
|---|---|
| **Flipper Zero** | Full studio + Evolution Engine (10-level XP) + auto-detect |
| **WiFi Pineapple Nano** | PineAP engine, recon modules, client capture |
| **Alfa AWUS036ACM** | Monitor mode, packet injection, 5GHz coverage |
| **USB Rubber Ducky** | Payload library browser, DuckyScript editor |
| **Bash Bunny** | Multi-stage payload management |
| **Hailo-10H NPU** | On-device AI inference on Raspberry Pi 5 |

### 📄 Professional Report Generation

End-of-engagement HTML reports with CVSS scoring, MITRE ATT&CK technique mapping, severity-ranked findings, and remediation recommendations. Client-ready with one command: `report`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ERR0RS WEB UI                        │
│         http://localhost:8765  ·  ws://localhost:8766   │
│  ┌──────────┐ ┌──────────────┐ ┌────────┐ ┌─────────┐  │
│  │ Terminal │ │ Intel Feed   │ │ Tools  │ │ Skills  │  │
│  │ + Coach  │ │ + Phases     │ │  Grid  │ │  Panel  │  │
│  └──────────┘ └──────────────┘ └────────┘ └─────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │ WebSocket
┌────────────────────────▼────────────────────────────────┐
│              errorz_launcher.py (HTTP + WS server)      │
│  route_command() → intent_parser → smart_wizard         │
│  is_conversational() → conversation_engine (streaming)  │
│  LiveProcess(tool) → stdout_buffer → auto_coach         │
└──┬──────────────┬──────────────┬──────────────┬─────────┘
   │              │              │              │
┌──▼──┐    ┌──────▼────┐  ┌─────▼─────┐  ┌────▼────────┐
│Ollama│   │ Phoenix   │  │  Tool     │  │ Progression │
│ LLM │   │  Bridge   │  │ Executor  │  │  + XP       │
│3.2:3b│  │ 2172 tools│  │ nmap,sqlmap│ │  system     │
└─────┘   └───────────┘  │ nikto, etc│  └─────────────┘
                          └─────┬─────┘
                          ┌─────▼─────┐
                          │Auto Coach │
                          │ Analysis  │
                          └───────────┘
```

**Stack:** Python 3.10+ · WebSockets · Ollama · ChromaDB RAG · nomic-embed-text · FastAPI (internal) · Vanilla JS + CSS (no framework)

**Design principles:**
- Zero cloud dependencies — everything runs locally or not at all
- Offline first — every core feature works without internet
- Purple team — every offensive technique paired with defensive countermeasure
- Teach by default — never run a command without explaining why

---

## Installation

### Prerequisites

| Requirement | Notes |
|---|---|
| **Kali Linux, Parrot OS, or Ubuntu/Debian** | x86\_64 or ARM64 |
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

# 2. Install (handles deps, Ollama, .env, desktop icon)
sudo bash install.sh

# 3. Launch
bash start_err0rs.sh
# Web UI opens at http://127.0.0.1:8765
```

> ✅ `install.sh` creates `.env` automatically with a generated secret key.  
> Do **NOT** manually run `cp configs/config.template.env .env` — it overwrites the generated key.

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

---

### Full Lab Environment (Juice Shop + Ollama + ERR0RS)

```bash
bash scripts/start_lab.sh
```

Starts everything: Ollama, OWASP Juice Shop (Docker or Node), wordlist setup, then ERR0RS.

---

### Manual / Advanced Install

```bash
pip install -r requirements-kali.txt --break-system-packages

# Create .env manually ONLY if not using install.sh
cp configs/config.template.env .env
nano .env  # Fill in LLM_BACKEND, model, etc.
```

---

## Quick Start

Once running at `http://127.0.0.1:8765`, try these in the terminal:

```bash
# Recon
nmap -sV 192.168.1.1
scan 10.0.0.5

# Ask ERR0RS anything
explain sql injection
walk me through kerberoasting
what is CIS Control 6
how do I read nmap output

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

---

## Demo Mode

No lab setup needed. ERR0RS includes a built-in demonstration mode that showcases its capabilities against safe local targets:

```bash
python3 src/ui/errorz_launcher.py --demo
```

Demo mode runs against `localhost` and `127.0.0.1` only. It demonstrates:
- Tool execution with live streaming output
- Auto-coach analysis blocks
- Conversation AI coaching
- Progression XP system
- Report generation

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
| **SBC** | Raspberry Pi 5 8GB |
| **AI Accelerator** | Hailo-10H NPU (26 TOPS) via AI HAT+ |
| **Storage** | NVMe SSD (Geekworm X1004) |
| **WiFi Adapters** | Alfa AWUS036ACM (5GHz) + built-in Pi WiFi |
| **RF Tools** | Flipper Zero (RogueMaster) + CC1101 |
| **Wireless Attack** | WiFi Pineapple Nano |
| **HID Attack** | ESP32 with Marauder firmware |
| **Total Cost** | ~$400-500 USD |

Running Kali Linux ARM64. Full ERR0RS deployment with Phoenix Arsenal, local LLM inference, and hardware control — field-portable in a 3D-printed case.

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
  version   = {3.2.0}
}
```

Full abstract: [RESEARCH.md](RESEARCH.md)

---

## Contributing

We welcome contributions at every skill level. See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

**Quick paths to contribute:**
- Add a tool integration (see `src/tools/recon/nmap_tool.py` as template)
- Add a lesson to the teach engine (`src/core/teach_engine.py`)
- Add an auto-coach rule (`src/core/auto_coach.py` — COACHING_RULES list)
- Write tests (`tests/test_errors.py`)
- Improve documentation or translate lessons

**Current priorities:**
- Burp Suite automation integration
- Windows/AD lab environment setup scripts
- Mobile platform support (NetHunter)
- Browser-based agent integration
- ARM64 performance optimizations

---

## Security & Ethics

ERR0RS-Ultimate is for **authorized security testing, CTF competitions, and education only.**

Using these techniques against systems you do not own or have explicit written authorization to test is a federal crime under the CFAA (US), Computer Misuse Act (UK), and equivalent laws worldwide.

The platform includes an ethical use agreement that must be accepted on first run. This is not performative compliance — it reflects the belief that the security community's credibility depends on operating within legal and ethical boundaries.

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
