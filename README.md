<div align="center">

```
 ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
 ██╔════╝██╔══██╗██╔══██╗██╔═════╝██╔══██╗██╔════╝
 █████╗  ██████╔╝██████╔╝██║  ███╗██████╔╝███████╗
 ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║
 ███████╗██║  ██║██║  ██║╚███████╔╝██║  ██║███████║
 ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══════╝ ╚═╝  ╚═╝╚══════╝
```

### **AI-Powered Penetration Testing Assistant, Instructor & Red Team Platform**
*The Clippy of Kali Linux — on steroids. The de facto cybersecurity training curriculum.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Kali%20%7C%20Parrot%20%7C%20Pi5-557C94?style=flat-square&logo=linux&logoColor=white)](https://kali.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Dev-blueviolet?style=flat-square)]()

**100% Local · Zero Data Leaves the OS · Built for Professional Red Teams & Security Education**

</div>

---

## 🤖 What is ERR0RS?

ERR0RS ULTIMATE is a fully local, AI-powered security platform that lives inside Kali Linux
and Parrot OS. It wraps 120+ security tools in a conversational interface, automates complete
penetration testing engagements, teaches offensive and defensive techniques in real time,
generates professional client reports, and delivers enterprise-grade threat intelligence
briefings — all without sending a single byte of client data to the cloud.

Think of it as having a senior red teamer sitting next to you: pressing the buttons,
explaining every command, correlating findings, and writing the report at the end.

> *"Technology cannot be patched. Humans cannot be patched. ERR0RS teaches you to attack and defend both."*

### Why ERR0RS Exists

The cybersecurity training gap is real and growing. AI has democratized sophisticated
attacks — WormGPT, FraudGPT, and AI-powered deepfakes are available to criminals for
$200/month. The defenders must think ahead of the pack. ERR0RS exists to close that gap:
to give security professionals, students, and enterprises the same depth of understanding
that the adversary already has.

---

## 🎯 Core Capabilities

| | Capability | Description |
|---|---|---|
| 🧠 | **AI Brain** | Local LLM (Ollama) or cloud — 5 operator modes, zero cloud dependency option |
| 🧙 | **Smart Wizard** | Guided option menus for 15+ tools — no syntax memorization required |
| 📚 | **Teach Mode** | Every command explained inline with real-time education — learn while operating |
| 🎯 | **Auto Kill Chain** | Full automated pentest: recon → scan → exploit → post → report |
| 📋 | **Campaign Manager** | Full engagement lifecycle — objectives, findings, credentials, timeline |
| 💥 | **BAS Engine** | Breach & Attack Simulation — MITRE ATT&CK-aligned defense validation |
| 🧬 | **Credential Engine** | Auto hash detection, hashcat pipeline, spray automation, pattern analytics |
| 🎭 | **Social Engineering** | Phishing campaign builder, vishing scripts, pretext framework, OSINT tools |
| 🕵️ | **AI Threat Intel** | WormGPT/FraudGPT profiles, deepfake briefings, Fortune 500 board decks |
| ⚡ | **Payload Studio** | AI-assisted DuckyScript for Flipper Zero, Rubber Ducky, pico-ducky |
| 🟣 | **Purple Team Mode** | Red, Blue, and Purple operator modes — attack AND detect simultaneously |
| 📊 | **Pro Reporter** | Executive-grade HTML/PDF reports with CVSS scoring and remediation roadmaps |
| 🌐 | **Language Layer** | 500+ natural language variants — operators speak human, ERR0RS listens |


---

## ⚡ Quick Install

```bash
git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate
sudo bash install.sh
python3 src/ui/errorz_launcher.py
```

> **Web UI:** `http://127.0.0.1:8765`
> **WebSocket Terminal:** `ws://127.0.0.1:8766`

```bash
# Optional — full knowledge base (~50 curated security repos)
git submodule update --init --recursive

# Optional — offline AI (fully local, no API key)
ollama pull llama3.2

# Optional — cloud AI (highest quality)
export ANTHROPIC_API_KEY=your_key_here
```

---

## 🛠️ Tool Coverage — 120+ Tools, Every Phase

| Phase | Tools Integrated |
|-------|-----------------|
| **Recon** | nmap, amass, subfinder, theHarvester, shodan, masscan, dnsrecon |
| **Web** | sqlmap, nikto, gobuster, ffuf, nuclei, wfuzz, feroxbuster, wpscan |
| **Exploitation** | metasploit, msfvenom, armitage, searchsploit, exploitdb |
| **Credentials** | hydra, hashcat, john, LaZagne, mimikatz, secretsdump |
| **Windows/AD** | BloodHound, CrackMapExec, impacket, enum4linux, WinPwn, PowerSharpPack |
| **Post-Exploit** | meterpreter, chisel, proxychains, ligolo, portforward automation |
| **Wireless** | aircrack-ng, airodump-ng, aireplay-ng, hcxdumptool, WiFi Pineapple |
| **BadUSB/HID** | Flipper Zero, USB Rubber Ducky, pico-ducky, USBArmyKnife |
| **Cloud** | AWS/Azure/GCP enumeration, Prowler, IAM auditing |
| **OSINT/SE** | theHarvester, Maltego, Sherlock, GoPhish, SET, Evilginx2 |
| **Mobile** | frida, MobSF, AndroRAT, iOS attack tools |
| **CTF** | Web/PWN/Crypto/Forensics/Reversing solver framework |
| **Reporting** | Auto HTML/PDF generation, CVSS scoring, MITRE mapping |

---

## 🎯 Auto Kill Chain — Full Automated Engagement

ERR0RS runs a complete penetration test autonomously:

```
ERR0RS> auto pentest 10.10.10.0/24

══════════════════════════════════════════════════════════
  ERR0RS AUTO KILL CHAIN — SUPERVISED MODE
  Target: 10.10.10.0/24  |  7 Phases
══════════════════════════════════════════════════════════

Phase 1 — Reconnaissance      [nmap discovery, subfinder, theHarvester]
Phase 2 — Scanning             [nmap deep, nuclei, nikto, gobuster]
Phase 3 — Vulnerability Assess [nuclei CVE, nmap vuln scripts, searchsploit]

⏸  Phase complete. Found 12 findings. Continue? [Y/n]: Y

Phase 4 — Exploitation         [sqlmap, hydra]  ← pauses for authorization
Phase 5 — Post-Exploitation    [local_exploit_suggester, hashdump]
Phase 6 — Lateral Movement     [crackmapexec sweep]
Phase 7 — Report Generation    [pro_reporter → HTML/PDF]

══════════════════════════════════════════════════════════
  COMPLETE: 7 phases | 34 findings | 3 credentials
  🔴 CRITICAL: 2  🟠 HIGH: 8  🟡 MEDIUM: 14  🟢 LOW: 10
══════════════════════════════════════════════════════════
```

**Modes:** `SUPERVISED` (pauses between phases) · `FULL_AUTO` (lab/CTF) · `DRY_RUN` (plan only)

---

## 📋 Campaign Manager — Professional Engagement Tracking

Every engagement tracked from first scan to final report:

```python
# ERR0RS tracks everything automatically
ERR0RS> new campaign "ACME Corp Q2 Assessment" --client "ACME Inc" --scope 10.10.10.0/24

Campaign created: ID=a3f7b2c1
  Objectives:  0/9 achieved
  Findings:    0 total
  Credentials: 0 captured
  Sessions:    0 active

# Findings logged automatically as tools run
# Credentials captured and correlated
# Timeline maintained throughout
# Final report generated on close
```

---

## 💥 BAS Engine — Breach & Attack Simulation

Validate your defenses without sending data outside. Competes with Pentera, SafeBreach, Cymulate:

```
ERR0RS> run bas credential_access

[ERR0RS BAS] Credential Access Simulation
MITRE: T1003, T1558.003, T1110, T1555

  ✅ LSASS Access Check     — Detection: Event ID 4656 should trigger SIEM
  ✅ SAM Database Access     — Detection: Unexpected /etc/shadow read should alert
  ✅ Password Manager Detect — Finding: KeePass running, credential access target

Playbooks: credential_access · lateral_movement · persistence ·
           defense_evasion · ransomware_sim · c2_beacon_sim
```


---

## 🎭 Social Engineering Engine — The Human Variable

The human is the primary attack surface. ERR0RS knows it.

```
ERR0RS> teach me social engineering
ERR0RS> build phishing campaign --company "ACME" --domain acme.com --pretext it_password_reset
ERR0RS> vishing script --pretext it_helpdesk --target "John Smith" --company "ACME"
ERR0RS> pretext recommend --role "CFO" --department "Finance"
```

**Phishing Campaign Builder** — Complete GoPhish campaign configs with:
- 5 production-ready pretext templates (IT password reset, HR benefits, CEO wire, MFA alert, shared document)
- Infrastructure setup guidance (domain aging, SPF/DKIM/DMARC, SSL)
- Per-target tracking, credential capture, redirect-after-capture
- GoPhish step-by-step setup workflow

**Vishing Script Generator** — Populated call scripts:
- IT helpdesk security incident (yes ladder, elicitation, escalation handling)
- HR payroll verification (bracketing technique)
- Corporate security audit (technical intimidation)

**OSINT Human Recon** — theHarvester, Maltego, Sherlock, Hunter.io, LinkedIn, breach data

**Physical SE** — Tailgating techniques, badge cloning (Proxmark3/Flipper Zero),
USB drops, impersonation pretexts, dumpster diving, shoulder surfing

**Defense** — DMARC enforcement, GoPhish simulation programs, FIDO2 MFA,
security awareness training with AI-quality phishing examples

---

## 🕵️ AI Threat Intelligence — What Criminals Are Using Right Now

ERR0RS teaches and briefs on the current criminal AI ecosystem:

```
ERR0RS> teach me wormgpt
ERR0RS> teach me fraudgpt
ERR0RS> teach me deepfake fraud
ERR0RS> teach me prompt injection
ERR0RS> teach me mitre atlas
ERR0RS> corporate briefing --company "Fortune 500 Inc" --industry "Financial Services"
```

**Threat Profiles:**
- **WormGPT** (July 2023) — Uncensored LLM for BEC, phishing at scale, malware assistance
- **FraudGPT** (Aug 2023) — $200/month financial fraud: fake bank portals, vishing scripts
- **AI Voice Cloning** — $30/month, 3-second sample, real-time clone ($25.6M Hong Kong incident)
- **Real-Time Video Deepfakes** — Live video call impersonation, documented enterprise losses
- **Prompt Injection** — MITRE ATLAS AML.T0051, attacking enterprise AI systems

**Corporate Briefing Generator** — Produces executive-ready HTML briefings:
- Financial risk quantification (BEC $125K avg, ransomware $812K avg, deepfake $25.6M)
- SEC 2023 regulatory exposure, board liability
- Prioritized investment recommendations (Immediate/90-day/Strategic)
- Red team demonstration framework for boards

---

## 🧬 Credential Engine — Automated Credential Pipeline

```
ERR0RS> crack all hashes                    # auto-detect type, run hashcat
ERR0RS> spray credentials --service smb    # spray cracked creds across network
ERR0RS> analyze passwords                  # pattern analytics for report
ERR0RS> import hashes secretsdump.txt      # bulk import from secretsdump/hashdump
```

**Auto Hash Detection** — NTLM, MD5, SHA1, SHA256, bcrypt, sha512crypt,
NetNTLMv2, Kerberos TGS, AS-REP, DCC2 — detected automatically

**Crack Pipeline** — Groups by type, builds hashcat commands, parses cracked output

**Spray Automation** — CrackMapExec integration, lockout-aware (configurable delay/rounds)

**Pattern Analytics** — Season+Year, Company+Number, Length<8, No special chars
— generates remediation language for client reports

---

## 📊 Professional Reporter — Client-Grade Output

```
ERR0RS> generate report
ERR0RS> pro report --client "ACME Corp" --operator "Eros"
```

Produces a full HTML engagement report with:
- **Cover page** — client, operator, dates, target count
- **Risk matrix** — Critical/High/Medium/Low/Info with visual risk score
- **Executive summary** — auto-generated from findings data
- **Detailed findings** — CVSS scores, MITRE ATT&CK IDs, per-finding remediation
- **Credential harvest table** — username, domain, type, cracked status
- **Remediation roadmap** — color-coded priority ranking
- **Engagement timeline** — every operator action logged
- **Scope section** — all tested targets documented

---

## 🧠 Natural Language Interface — 500+ Phrasings

ERR0RS understands how operators actually talk:

```
"scan that ip"                → nmap
"poke that machine"           → nmap
"pop the box"                 → metasploit
"crack the wifi"              → aircrack/hashcat
"can mimikatz crack wifi?"    → corrects + teaches right tool
"dump the hashes"             → mimikatz/secretsdump
"loot the machine"            → post-exploitation
"pivot to internal"           → lateral movement
"yo how do i root this"       → privilege escalation
"brief the board on ai threats" → corporate briefing generator
```

**Typo correction** — "mataslpoit" → metasploit (80+ corrections, silent)
**Operator slang** — "pop", "pwn", "da", "loot", "beacon", "pivot", "da"
**Compound intents** — "scan then exploit then escalate then dump creds"
**Tone detection** — beginner/intermediate/expert/operator — adapts explanation depth
**Phase detection** — detects kill chain phase from context, suggests next steps


---

## 🧙 Smart Wizard — Guided Tool Menus

Type a vague command or click a tool — ERR0RS presents guided options:

```
┌─────────────────────────────────────────────────────┐
│  ERR0RS // NMAP WIZARD                              │
│                                                     │
│  [1] Quick Scan      — nmap -F {target}             │
│  [2] Version Scan    — nmap -sV {target}            │
│  [3] Full + Scripts  — nmap -sV -sC -p- {target}    │
│  [4] Stealth SYN     — nmap -sS {target}            │
│  [5] UDP Scan        — nmap -sU --top-ports 100     │
│  [6] Vuln Scripts    — nmap --script vuln {target}  │
│                                                     │
│  💡 -sV probes ports to determine service versions  │
└─────────────────────────────────────────────────────┘
  Target: [___________________] [ ⚡ RUN ]
```

Wizards for: nmap · sqlmap · hydra · gobuster · hashcat · metasploit ·
nikto · nuclei · aircrack-ng · subfinder · enum4linux · msfvenom · mimikatz

---

## 📚 Teaching System — Learn While You Operate

Every tool run can include inline education:

```
ERR0RS> nmap -sV 10.10.10.100 --teach

[ERR0RS TEACHES] Nmap — Network Mapper
====================================================
[TL;DR] The essential reconnaissance tool. Discovers hosts,
open ports, services, versions, and OS information.

HOW IT WORKS:
  Nmap sends carefully crafted packets and analyzes responses
  to determine what's running on remote hosts...

[Running: nmap -sV -sC --top-ports 1000 10.10.10.100]

22/tcp  open  ssh    OpenSSH 8.2p1
  [ERR0RS] Port 22 = SSH. Try: hydra -l root -P rockyou.txt ssh://10.10.10.100

80/tcp  open  http   Apache 2.4.49
  [ERR0RS] Port 80 = HTTP. Apache 2.4.49 → CHECK for CVE-2021-41773 (Path Traversal!)
  [ERR0RS] Run: nuclei -u http://10.10.10.100 -tags cve-2021-41773

445/tcp open  smb
  [ERR0RS] Port 445 = SMB. Check MS17-010 IMMEDIATELY:
  [ERR0RS] nmap -p 445 --script smb-vuln-ms17-010 10.10.10.100
```

**16 built-in offline lessons** (no Ollama needed):
nmap · sqlmap · nikto · gobuster · hydra · metasploit · hashcat · aircrack ·
nuclei · subfinder · xss · sql injection · meterpreter · privilege escalation ·
burp suite · wireshark · mimikatz · wifi cracking · social engineering · ai threats

**24 annotated ports** — every open port triggers contextual attack guidance

---

## 🟣 Purple Team Mode — Attack AND Detect Simultaneously

```
ERR0RS> purple team this
ERR0RS> attack then detect
ERR0RS> simulate and build detection rule

[ERR0RS PURPLE] Running attack AND detection simultaneously.
I'll execute the offensive action, then show what a defender sees:

OFFENSIVE: Running credential access simulation...
  → LSASS memory access attempted

DEFENSIVE: What the SOC should see:
  → Sysmon Event 10: Process accessing lsass.exe
  → Windows Event 4656: Handle to LSASS requested
  → EDR Alert: Suspicious memory read on protected process

SIGMA RULE GENERATED:
  title: Suspicious LSASS Access
  detection:
    selection:
      EventID: 10
      TargetImage|contains: 'lsass.exe'
  condition: selection

MITRE ATT&CK: T1003.001 — OS Credential Dumping: LSASS Memory
```

---

## 🏗️ Architecture

```
ERR0RS-Ultimate/
├── main.py                          ← CLI entry (--api / --query / interactive)
├── src/
│   ├── ui/
│   │   ├── errorz_launcher.py       ← Main HTTP+WebSocket server (port 8765/8766)
│   │   └── web/                     ← Browser UI (index.html, payload_studio.html)
│   ├── ai/
│   │   ├── __init__.py              ← ERR0RSAI class (LLM + RAG + agents)
│   │   ├── llm_router.py            ← Ollama / Anthropic / OpenAI routing
│   │   ├── errz_brain.py            ← 5-mode native AI brain (no cloud required)
│   │   └── agents/                  ← Red/Blue/Purple/Bug Bounty agents
│   ├── core/
│   │   ├── language_layer.py        ← Central NLP — all triggers, classify_command()
│   │   ├── language_expansion_v2.py ← 500+ phrasings, typos, slang, compound intents
│   │   ├── smart_wizard.py          ← Guided tool menus
│   │   ├── live_terminal.py         ← WebSocket PTY streaming
│   │   └── tool_executor.py         ← Async subprocess engine
│   ├── orchestration/
│   │   ├── campaign_manager.py      ← Engagement lifecycle management
│   │   ├── auto_killchain.py        ← Automated 7-phase kill chain
│   │   └── execution_modes.py       ← INTERACTIVE / YOLO / SUPERVISED
│   ├── education/
│   │   └── teach_engine.py          ← Bridge to education_new
│   ├── education_new/
│   │   └── teach_engine.py          ← Full offline lesson library (16+ topics)
│   ├── reporting/
│   │   └── pro_reporter.py          ← Executive HTML report generator
│   ├── tools/
│   │   ├── credentials/
│   │   │   └── credential_engine.py ← Hash detect, crack, spray, analytics
│   │   ├── se_engine/
│   │   │   └── se_engine.py         ← Phishing builder, vishing scripts, OSINT
│   │   ├── threat/
│   │   │   └── ai_threat_engine.py  ← AI criminal tool intel + board briefings
│   │   ├── breach/
│   │   │   └── bas_engine.py        ← Breach & Attack Simulation (6 playbooks)
│   │   ├── postex/                  ← Post-exploitation, privesc, lateral movement
│   │   ├── wireless/                ← WiFi attack automation
│   │   ├── social/                  ← SE automation wrapper
│   │   ├── cloud/                   ← AWS/Azure/GCP security
│   │   ├── ctf/                     ← CTF solver modes
│   │   ├── opsec/                   ← OPSEC checklists and tradecraft
│   │   ├── badusb_studio/           ← Flipper Zero / HID suite
│   │   └── payload_studio/          ← DuckyScript AI engine
│   ├── memory/
│   │   └── engagement_memory.py     ← Knowledge graph — learns from every job
│   └── security/
│       ├── blue_team.py             ← Hardening, audit, PCAP analysis
│       └── guardrails.py            ← Ethical controls
├── knowledge/                       ← RAG knowledge base
│   ├── social-engineering/HUMAN_VARIABLE/  ← SE deep knowledge
│   ├── threat-intelligence/ai-powered-threats/ ← WormGPT/FraudGPT intel
│   ├── wireless/                    ← WiFi attack reference
│   ├── windows/ credentials/ evasion/ exploitation/ mobile/ recon/
│   └── [50+ curated security repos as git submodules]
├── knowledge.json                   ← RAG-ready entries (~45 topics)
└── docs/
    └── Metasploit_Armitage_RedTeam_Book.md  ← 2,182-line reference book
```


---

## 🔌 Complete API Reference

**HTTP API** at `http://127.0.0.1:8765` | **WebSocket** at `ws://127.0.0.1:8766`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Full system status — all engine flags |
| `POST` | `/api/command` | Route any natural language command |
| `POST` | `/api/tool` | Execute specific tool with target + params |
| `POST` | `/api/shell` | Raw shell execution |
| `POST` | `/api/teach` | Query teaching engine |
| `POST` | `/api/wizard` | Get guided option menu for a tool |
| `POST` | `/api/wizard/run` | Execute wizard option with target |
| `POST` | `/api/brain` | ERR0RS native AI brain (5 modes) |
| `POST` | `/api/bas` | Breach & Attack Simulation playbooks |
| `POST` | `/api/campaign` | Campaign manager — create/status/findings |
| `POST` | `/api/killchain` | Automated kill chain — specify target + mode |
| `POST` | `/api/pro_report` | Generate professional HTML report |
| `POST` | `/api/credentials` | Credential engine — add/crack/spray/analyze |
| `POST` | `/api/se` | Social engineering engine commands |
| `POST` | `/api/ai_threat` | AI threat intelligence queries + briefings |
| `POST` | `/api/blue_team` | Blue team — harden/audit/report |
| `POST` | `/api/harden` | Auto-hardening for a specific finding |
| `POST` | `/api/report` | Security audit PDF report |
| `POST` | `/api/soc` | SOC actions — failed logins, open ports, logs |
| `POST` | `/api/compliance` | Compliance mapping — MITRE/CIS/NIST |
| `POST` | `/api/ollama` | Direct Ollama AI query |
| `POST` | `/api/flipper` | Flipper Zero Studio commands |
| `POST` | `/api/badusb` | BadUSB/DuckyScript generation |
| `POST` | `/api/rocketgod` | RF/HackRF/SubGHz tools |
| `GET` | `/api/payload_studio/snippets` | Full indexed payload library |
| `POST` | `/api/payload_studio/explain` | Explain a DuckyScript line |
| `POST` | `/api/payload_studio/suggest` | Next-line suggestions |
| `POST` | `/api/payload_studio/validate` | Validate a complete payload |
| `WS` | `/ws/terminal` | Live streaming PTY terminal |

---

## 🍓 Hardware Stack — Pi 5 Field Deployment

ERR0RS runs as a portable, self-contained pentest unit:

| Component | Purpose |
|-----------|---------|
| Raspberry Pi 5 (16GB RAM) | Main compute |
| Geekworm X1004 v1.1 dual NVMe HAT | Fast SSD storage |
| Raspberry Pi AI HAT+ 2 (Hailo-10H, 40 TOPS) | Local AI inference (needs Debian Trixie) |
| Waveshare PCIe TO 2-CH PCIe HAT | PCIe lane splitting |
| PiSquare RP2040+ESP-12E | Wireless GPIO bridge |
| WiFi Pineapple Nano (AR9331/AR9271) | 2.4GHz wireless attacks |
| Alfa AWUS036ACM (MT7612U) | 5GHz wireless, monitor mode + injection |
| Flipper Zero | Sub-GHz RF, NFC, RFID, BadUSB, IR |

---

## 🧠 AI Backends

| Backend | Privacy | Cost | Best For |
|---------|---------|------|----------|
| **Ollama** (default) | 🟢 100% local | Free | Client work, air-gapped, Pi 5 |
| **Anthropic Claude** | 🟡 API | Paid | Highest quality responses |
| **OpenAI GPT** | 🟡 API | Paid | Alternative cloud option |

```bash
LLM_BACKEND=ollama       # fully offline — recommended for client work
LLM_BACKEND=anthropic    # Claude API
LLM_BACKEND=openai       # GPT API
ANTHROPIC_API_KEY=sk-...
```

---

## 📚 Knowledge Base — 50+ Curated Security Repos + RAG

**`knowledge.json`** — 45+ RAG-ready entries covering:
CIA Triad · OSI Model · Pentesting Methodology · Nmap · SQLMap · Nikto · Gobuster ·
Hydra · Metasploit · Hashcat · Aircrack · Nuclei · Subfinder · XSS · SQL Injection ·
Privilege Escalation (Linux + Windows) · Active Directory · Post-Exploitation ·
Mimikatz · WiFi Cracking · Wireless Tool Selection · Social Engineering ·
Phishing · Vishing · Physical SE · SE Defense · WormGPT · FraudGPT ·
Deepfake Fraud · Prompt Injection · MITRE ATLAS · Corporate AI Briefing

**Git submodules** — Knowledge categories:

| Category | Notable Sources |
|----------|----------------|
| `evasion/` | AMSI bypass, OffensiveVBA, PowerShell evasion |
| `windows/` | WinPwn, PowerSharpPack |
| `credentials/` | hate_crack, SharpChromium, SharpWeb |
| `exploitation/` | Singularity |
| `mobile/` | AndroRAT, beerus-android, house-frida |
| `badusb/` | Flipper BadUSB, MacOS DuckyScripts, PowerShell-for-Hackers |
| `c2/` | CS-Situational-Awareness-BOF |
| `redteam/` | SteppingStones |
| `rocketgod/` | HackRF Treasure Chest, WiGLE Vault, SubGHz Toolkit, ProtoPirate |
| `social-engineering/` | SET, HUMAN_VARIABLE field guide |
| `threat-intelligence/` | AI criminal tool profiles, field guides |
| `wireless/` | WiFi attack reference, tool selection guide |

---

## 📖 Documentation

| Document | Contents |
|----------|----------|
| `docs/Metasploit_Armitage_RedTeam_Book.md` | 2,182-line complete guide: msfconsole, msfvenom, Armitage, kill chain playbooks |
| `docs/ERR0RS_Deep_Reference.md` | Every function in the framework documented |
| `knowledge/social-engineering/HUMAN_VARIABLE/HUMAN_VARIABLE_FIELD_GUIDE.md` | SE field guide: psychology, phishing, vishing, physical, defense |
| `knowledge/threat-intelligence/ai-powered-threats/AI_THREAT_FIELD_GUIDE.md` | WormGPT, FraudGPT, deepfakes, enterprise defense roadmap |
| `knowledge/wireless/WIRELESS_KNOWLEDGE.md` | WiFi attack reference + Mimikatz vs aircrack disambiguation |

---

## ⚙️ Requirements

- **OS:** Kali Linux · Parrot OS · Ubuntu 22.04+ · Debian 12+ · Raspberry Pi OS (Trixie for AI HAT)
- **Python:** 3.10+
- **RAM:** 4GB minimum · 8GB+ recommended · 16GB for Pi 5 + Hailo NPU
- **Storage:** 10GB free minimum (50GB+ with all knowledge submodules)
- **Optional:** Ollama (local AI) · ANTHROPIC_API_KEY (cloud AI)

---

## 🤝 Contributing

PRs welcome for:
- New tool integrations in `src/tools/`
- Wizard flows in `src/core/smart_wizard.py`
- Language triggers in `src/core/language_layer.py` or `language_expansion_v2.py`
- Knowledge base entries in `knowledge.json`
- Teaching lessons in `src/education_new/teach_engine.py`
- Bug fixes verified with the test suite

---

## 🎖️ Credits

Built on the shoulders of the open-source security community.
Full credits in [CREDITS.md](CREDITS.md).

Notable contributors: vxunderground · RocketGod · djhohnstein · S3cur3Th1sSh1t ·
trustedsec · nccgroup · mandiant · AlessandroZ · justcallmekoko · DarkFlippers ·
hak5 · i-am-shodan · BushidoUK · CyberMonitor · Lissy93 · and many more.

---

## ⚖️ Legal & Ethics

**For authorized penetration testing, security education, and research ONLY.**

- Only use against systems you own or have **explicit written permission** to test
- All social engineering modules require written client authorization
- The author assumes no liability for misuse
- See [SECURITY.md](SECURITY.md) for the full security policy

Every technique in ERR0RS has an equal defensive component.
Understanding the attack is the foundation of building the defense.

---

<div align="center">

**Built by [Gary "Eros" Holden Schneider](https://github.com/Gnosisone)**
*Cybersecurity Student · Network Administrator · Offensive Security Practitioner*
*CompTIA Tech+ · Microsoft Certified · Oklahoma City, OK*

*"Technology cannot be patched. Humans cannot be patched.*
*ERR0RS teaches you to attack and defend both."*

⭐ Star this repo. Star the repos in [CREDITS.md](CREDITS.md). Pay it forward.

</div>
