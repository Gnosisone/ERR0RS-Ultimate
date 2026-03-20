<div align="center">

```
 ██████╗ ██████╗ ██████╗  ██████╗ ██████╗ ███████╗
██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝
█████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗
██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║
███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
```

### **AI-Powered Penetration Testing Assistant & Teaching Platform**
*The Clippy of Kali Linux — on steroids.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Kali%20%7C%20Parrot%20%7C%20Pi5-557C94?style=flat-square&logo=linux&logoColor=white)](https://kali.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Gnosisone/ERR0RS-Ultimate?style=flat-square&color=yellow)](https://github.com/Gnosisone/ERR0RS-Ultimate/stargazers)
[![Status](https://img.shields.io/badge/Status-Active%20Dev-blueviolet?style=flat-square)]()

**100% Local · Zero Data Leaves the OS · Built for Kali Linux & Parrot OS**

</div>

---

## 🤖 What is ERR0RS?

ERR0RS is a fully local, AI-powered virtual assistant that lives inside Kali Linux and Parrot OS.
It wraps 120+ security tools in a conversational interface, guides operators through engagements
step-by-step, teaches offensive and defensive techniques in real time, and generates professional
reports — all without sending a single byte of client data to the cloud.

Think of it as having a senior red teamer sitting next to you, pressing the buttons, explaining
what every command does, and writing the report at the end.

> *"We didn't build another tool. We built the operator behind the tools."*

---

## 🎯 Core Pillars

| | Feature | Description |
|---|---|---|
| 🧠 | **AI Brain** | Local LLM via Ollama or cloud (Anthropic/OpenAI) — your choice |
| 🧙 | **Smart Wizard** | Click a tool, ERR0RS presents guided options — no syntax memorization |
| 📚 | **Teach Mode** | Every command explained inline — learn while you hack |
| ⚡ | **Payload Studio** | AI-assisted DuckyScript generator for Flipper Zero, Pico Ducky, USB Rubber Ducky |
| 🟣 | **Purple Team Mode** | Red, Blue, and Purple operator modes — one platform, three perspectives |
| 📊 | **Auto Reporting** | Professional HTML/PDF engagement reports generated automatically |


---

## ⚡ Quick Install

```bash
# Clone the repo
git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate

# Run the installer (Kali / Parrot / Debian / Ubuntu)
sudo bash install.sh

# Launch
python3 src/ui/errorz_launcher.py
```

> **Web UI opens at:** `http://127.0.0.1:8765`

> **Optional — pull the full knowledge base** (~10-30 min first time):
> ```bash
> git submodule update --init --recursive
> ```

---

## 🛠️ Tool Coverage

120+ tools across every phase of an engagement:

| Phase | Tools |
|-------|-------|
| **Recon** | nmap, amass, subfinder, theHarvester, shodan, web-check |
| **Web** | sqlmap, nikto, gobuster, ffuf, nuclei, ZAP, wfuzz |
| **Exploitation** | metasploit, searchsploit, msfvenom |
| **Credentials** | hydra, hashcat, john, LaZagne, SharpChromium |
| **Windows/AD** | WinPwn, BloodHound, CrackMapExec, impacket, enum4linux |
| **Wireless** | aircrack-ng, ESP32Marauder, WiFi Pineapple Nano |
| **BadUSB/HID** | Flipper Zero, USB Rubber Ducky, pico-ducky, USBArmyKnife |
| **Post-Exploit** | mimikatz, SharpHound, PowerSharpPack |
| **Mobile** | frida, MobSF, libimobiledevice, ios-resources |
| **Reporting** | Auto HTML/PDF report generation, MITRE ATT&CK mapping |

---

## 🧙 Smart Wizard — No Syntax Required

Type a vague command like *"scan for open ports"* or click a tool button — ERR0RS presents
a guided option menu with descriptions and teaches what each flag does.

```
┌─────────────────────────────────────────────────────┐
│  ERR0RS // NMAP WIZARD                              │
│                                                     │
│  [1] Quick Scan      — nmap -F {target}             │
│  [2] Version Scan    — nmap -sV {target}            │
│  [3] Full + Scripts  — nmap -sV -sC -p- {target}    │
│  [4] Stealth SYN     — nmap -sS {target}            │
│  [5] UDP Scan        — nmap -sU --top-ports 100     │
│                                                     │
│  💡 -sV probes open ports to determine              │
│     service/version info. Slower but more intel.    │
└─────────────────────────────────────────────────────┘
  Target: [___________________] [ ⚡ RUN ]
```

Wizards available for: nmap · sqlmap · hydra · gobuster · hashcat · metasploit ·
nikto · nuclei · aircrack-ng · subfinder · enum4linux


---

## 🟣 Team Modes

| Mode | Color | Focus |
|------|-------|-------|
| 🔴 **Red Team** | Red | Offensive — exploitation, evasion, C2 |
| 🔵 **Blue Team** | Blue | Defensive — detection, hardening, monitoring |
| 🟣 **Purple Team** | Purple | Both sides simultaneously — instructor mode |

Switch modes in the UI — the tool grid highlights and ERR0RS's guidance adapts to each role.

---

## ⚡ Payload Studio

AI-assisted BadUSB payload generator with real-time DuckyScript suggestions,
line-by-line explanations, platform detection, and an indexed snippet library.

**Supported platforms:** Windows · macOS · Linux · Android · iOS
**Supported devices:** Flipper Zero · USB Rubber Ducky · pico-ducky · USBArmyKnife

Access via the **⚡ PAYLOAD STUDIO** button in the top bar → `http://127.0.0.1:8765/payload_studio.html`

---

## 🏗️ Architecture

```
ERR0RS-Ultimate/
├── src/
│   ├── ai/                     ← LLM router, Ollama/Anthropic/OpenAI backends
│   │   └── agents/             ← Red team, vuln chain, recon, social eng agents
│   ├── core/
│   │   ├── language_layer.py   ← Centralized NLP triggers (all tools)
│   │   ├── smart_wizard.py     ← Guided option menus for 11+ tools
│   │   └── live_terminal.py    ← WebSocket streaming terminal
│   ├── tools/
│   │   ├── payload_studio/     ← DuckyScript AI engine + payload indexer
│   │   ├── badusb_studio/      ← Flipper Zero / HID tool suite
│   │   ├── wireless/           ← WiFi Pineapple + aircrack integration
│   │   └── ...120+ more
│   ├── education/
│   │   └── teach_engine.py     ← Inline teaching system
│   ├── reporting/              ← HTML/PDF report generation
│   └── ui/
│       └── web/
│           ├── index.html          ← Main UI (Zoom-call style)
│           ├── payload_studio.html ← BadUSB payload generator
│           └── purple_team.html    ← Purple team operator view
├── knowledge/                  ← Git submodules (50+ curated security repos)
│   ├── evasion/    ├── windows/    ├── credentials/  ├── hardware/
│   ├── badusb/     ├── mobile/     ├── threat-intel/ ├── redteam/
│   ├── osint/      ├── rocketgod/  ├── social-engineering/ └── ai-security/
└── configs/
    ├── config.template.env     ← Copy to .env and configure
    └── tools.conf              ← Default flags per tool
```

---

## 🍓 Hardware Stack (Pi 5 Deployment)

ERR0RS runs as a portable field unit on Raspberry Pi 5:

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 (16GB RAM) | Main compute |
| Geekworm X1004 dual NVMe HAT | Storage |
| Raspberry Pi AI HAT+ (Hailo-10H, 40 TOPS) | Local AI inference |
| WiFi Pineapple Nano | 2.4GHz wireless attacks |
| Alfa AWUS036ACM | 5GHz wireless coverage |
| Flipper Zero | Sub-GHz, NFC, BadUSB, IR |


---

## 🧠 AI Backends

| Backend | Privacy | Cost | Best For |
|---------|---------|------|----------|
| **Ollama** (default) | 🟢 100% local | Free | Client work, air-gapped |
| **Anthropic Claude** | 🟡 API calls | Paid | Highest quality responses |
| **OpenAI GPT** | 🟡 API calls | Paid | Alternative cloud option |

Configure in `.env`:
```bash
LLM_BACKEND=ollama       # fully offline (recommended)
LLM_BACKEND=anthropic    # Claude via API
LLM_BACKEND=openai       # GPT via API
```

---

## 📚 Knowledge Base

50+ curated security repos as Git submodules — a RAG-ready research library powering
ERR0RS's domain knowledge, payload suggestions, and teaching content.

| Category | Notable Repos |
|----------|--------------|
| `evasion/` | vxunderground MalwareSourceCode, VX-API, VXUG-Papers, Singularity rootkit |
| `windows/` | WinPwn, PowerSharpPack, Priv2Admin |
| `credentials/` | LaZagne, SharpChromium, KittyLitter, redsnarf, hate_crack |
| `hardware/` | ESP32Marauder, pico-ducky, USBArmyKnife, Flipper Zero Unleashed |
| `badusb/` | Flipper BadUSB scripts, USB Rubber Ducky payloads, I-Am-Jakoby collection |
| `mobile/` | ios-resources, iphone_backup_decrypt, EvilOSX, Bella |
| `redteam/` | commando-vm, OSCE3 guide, Cheatsheet-God, 90DaysOfCyberSecurity |
| `threat-intel/` | APT campaign collections, open source CTI tools |
| `osint/` | web-check |
| `rocketgod/` | Full RF/Flipper/HackRF/SubGHz toolkit collection |
| `social-engineering/` | SET, malicious-pdf |
| `ai-security/` | ML for cybersecurity, prompt injection taxonomy |

---

## 🔌 API Reference

Local REST API at `http://127.0.0.1:8765`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a command or question to ERR0RS |
| `POST` | `/api/run` | Execute a tool with target and params |
| `POST` | `/api/wizard` | Get guided option menu for a tool |
| `POST` | `/api/wizard/run` | Execute a wizard option with target |
| `GET`  | `/api/payload_studio/snippets` | All indexed payload snippets |
| `POST` | `/api/payload_studio/explain` | Explain a DuckyScript line |
| `POST` | `/api/payload_studio/suggest` | AI suggestions for next DuckyScript line |
| `POST` | `/api/payload_studio/validate` | Validate a complete DuckyScript payload |
| `POST` | `/api/teach` | Query the teaching engine |
| `WS`   | `/ws/terminal` | Live streaming WebSocket terminal |

---

## 📋 Requirements

- **OS:** Kali Linux, Parrot OS, Ubuntu 22.04+, Debian 12+
- **Python:** 3.10+
- **RAM:** 4GB minimum · 8GB+ recommended · 16GB for Pi 5 with Hailo NPU
- **Disk:** 10GB free (more for knowledge base submodules)
- **Optional:** Ollama for fully offline AI — auto-installed by `install.sh`


---

## 🤝 Contributing

Pull requests are welcome for:
- New tool integrations under `src/tools/`
- Additional wizard flows in `src/core/smart_wizard.py`
- New language triggers in `src/core/language_layer.py`
- Knowledge base submodule additions
- Bug fixes and improvements

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting.

---

## 🎖️ Credits

ERR0RS Ultimate is built on the shoulders of the open-source security community.
Every tool, library, and research repo is credited in full in [CREDITS.md](CREDITS.md).

**Knowledge base contributors:**
vxunderground · RocketGod · djhohnstein · S3cur3Th1sSh1t · trustedsec · nccgroup ·
mandiant · AlessandroZ · justcallmekoko · DarkFlippers · hak5 · i-am-shodan ·
BushidoUK · CyberMonitor · Lissy93 · JoasASantos · Marten4n6 · and many more.

> *"The best way to thank open source developers is to build something great with their work,
> give full credit, and pay it forward by open-sourcing your own."*

---

## ⚖️ Legal & Ethics

ERR0RS Ultimate is built for **authorized penetration testing, security education, and research only.**

- Only use against systems you own or have **explicit written permission** to test
- The author assumes no liability for misuse
- See [SECURITY.md](SECURITY.md) for the full security policy

---

<div align="center">

**Built by [Gary "Eros" Holden Schneider](https://github.com/Gnosisone)**
*Cybersecurity Student · Network Administrator · Offensive Security Practitioner*
*Oklahoma City, OK*

⭐ If ERR0RS helps you, star the repos of every author in [CREDITS.md](CREDITS.md).
That's the real currency.

</div>
