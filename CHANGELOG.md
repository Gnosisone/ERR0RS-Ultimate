# Changelog

All notable changes to ERR0RS ULTIMATE are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) · Versioning: [SemVer](https://semver.org)

---

## [3.2.0] - 2026-04-26 — The Education Release

### Added

#### Operator Progression System (`src/core/progression.py`)
- 6-level XP system: SCRIPT KIDDIE → APPRENTICE → PRACTITIONER → SPECIALIST → OPERATOR → ELITE
- XP awarded for every tool run, finding, question asked, and operation completed
- 8 skill domain bars: Web App, Network, Active Directory, Wireless, Hardware, Forensics, Social Engineering, Defense
- Achievement system: First Blood, Recon Master, AD Pwner, Web Hunter, Elite Operator, and more
- Persistent profile at `~/.err0rs/progression.json` — survives restarts
- Level-up notifications with contextual messages ("💀 OPERATOR — You ARE the threat model")

#### First-Run Onboarding Wizard (`src/core/onboarding.py`)
- 4-screen guided wizard on first launch: Welcome → Ethics Agreement → Skill Assessment → First Mission
- Ethical use agreement required before any tool access — not a checkbox, a gate
- Skill self-assessment sets `guided` vs `standard` vs `expert` mode automatically
- First Mission: guided nmap → nikto → gobuster walkthrough with coaching at every step
- Preferences saved to `~/.err0rs/preferences.json`

#### Streaming Conversation Engine (`src/core/conversation_engine.py`)
- Full ERR0RS AI persona with deep security expertise: CIS Controls v8, OWASP Top 10, MITRE ATT&CK, NIST CSF
- Streaming Ollama HTTP API — tokens appear as they generate, not after 120s wait
- Auto model selection: prefers `llama3.2:3b` (faster) over `qwen2.5-coder:7b`
- Per-session conversation history (20 turns, thread-safe)
- Operator state injection — ERR0RS knows active target and findings when answering
- Model warm-up at boot — first query is fast, subsequent queries near-instant
- `is_conversational()` classifier routes chat to LLM, commands to executor (no confusion)

#### Auto Coach Engine (`src/core/auto_coach.py`)
- After every tool completes, ERR0RS analyzes output and fires a coaching block
- Covers: SMB/EternalBlue, RDP, FTP, Redis, VULNERABLE state, missing headers, admin panels,
  exposed .git/.env, SQL injection confirmed, credentials cracked, nuclei critical/high
- Each coaching block: severity color, plain-English explanation, clickable next-step commands, defensive countermeasure
- Works 100% offline — deterministic rules, zero LLM dependency
- XP awarded automatically on significant findings

#### Expanded Teach Engine (`src/core/teach_engine.py`)
- 23 topics vs 8 previously (3× expansion)
- Tools (15): nmap, nikto, gobuster, sqlmap, hydra, nuclei, whatweb, enum4linux, crackmapexec,
  ffuf, metasploit, bloodhound, hashcat, responder, linpeas, netcat
- Concepts (8): CIS Controls v8 (all 18 mapped), OWASP Top 10 2021, MITRE ATT&CK (all 14 tactics),
  Cyber Kill Chain, CIA Triad, Incident Response (NIST phases), Threat Modeling (STRIDE)
- Each lesson: flags reference, reading output, next steps, caution
- Works offline: `teach me nmap`, `explain OWASP`, `what is MITRE ATT&CK`, `tell me about CIS`

#### Lab Startup Script (`scripts/start_lab.sh`)
- One command boots the full environment: Ollama + Juice Shop + ERR0RS
- Handles Docker, Node.js, and gzip wordlist cases with color-coded status
- Extracts rockyou.txt automatically from .gz if needed

#### Web UI Improvements (`src/ui/web/`)
- **Skill Panel** (slide-out right sidebar): level badge, XP bar, domain skill bars, stats
- **Onboarding Overlay**: 4-screen wizard with smooth screen transitions
- **Mission Coach Footer**: appears post-onboarding to guide first steps
- **XP Toast Notifications**: bottom-right, non-intrusive, fires on tool completion and chat
- **Coach Blocks**: rich UI cards after tool completion with severity color coding, clickable commands
- **Guided/Expert Mode Toggle** in terminal header (🔰 GUIDED ↔ ⚡ EXPERT)
- All 13 tool card label mismatches fixed (FAILED LOGIN→TCPDUMP, PROC AUDIT→VOLATILITY, etc.)
- Tool card `onclick` now opens correct panels (OPEN PORTS→netstat not duplicate nmap, etc.)

#### Infrastructure
- `llama3.2:3b` pulled as primary chat model (2.0GB, 2× faster than qwen on ARM)
- ChromaDB `google.rpc` import error patched
- `rockyou.txt` extracted to `~/.err0rs/wordlists/` with auto-fallback in all commands
- `/api/progression` GET endpoint — full operator profile JSON
- `/api/onboarding` GET + POST — first-run wizard data and completion
- `/api/progression/award` POST — manual XP award from frontend events
- `_stdout_buffer` in LiveProcess — rolling 500-line buffer feeds auto-coach
- Teach route upgraded: core engine checked first, education engine as fallback

---

## [3.1.0] - 2026-04-22 — Juice Shop CTF Solver (18/18)

### Added
- **Juice Shop CTF Solver** (`src/core/juice_shop_solver.py`) — fully automated solver
  - Admin login via SQL injection (`' OR 1=1--`)
  - JWT algorithm confusion attack (`alg: none` → forge admin token)
  - Bjoern's password reset via YAML source code analysis
  - Five-star feedback bypass via CAPTCHA solver + admin JWT
  - Score board discovery and tracking
  - Confidential document exfiltration
  - DOM XSS via `<iframe src="javascript:alert(...)">` 
  - Basket manipulation via direct API parameter tampering
  - SQLi database dump via `/rest/products/search` endpoint
  - 10 additional challenges across authentication, access control, injection
  - 18/18 challenges solved at 100% in final v3.1.0 run

### Fixed
- Terminal geometry: fixed column width causing wrapped output
- Flag passthrough: challenge flags now display correctly in UI
- sqlmap output analyzer: improved parsing of injection type lines

---

## [3.0.0] - 2026-04-19 — Phoenix Arsenal + Boot Sequence

### Added
- **Phoenix-OS Bridge** (`src/core/phoenix_bridge.py`) — connects to 2,172-tool Phoenix Arsenal
  - Auto-detects Phoenix at `/home/kali/Phoenix-OS`
  - 92 tools loaded into ERR0RS registry on boot
  - Full NLP search across all 2,172 BlackArch tools
  - One-click execution from ERR0RS terminal
- **Dynamic Boot Sequence** — live hardware detection cards on startup
- **Desktop Icon** — XDG `.desktop` installer with SVG purple cat mascot
- **ERR0RS Brain** — local AI inference with 5 operator modes

### Changed
- Boot sequence now shows all 25+ module load states with green checkmarks
- Web UI layout: 4-pane grid (phases | terminal | intel | tools)

---

## [2.5.0] - 2026-03-15 — Kali 2026.1 Integration

### Added
- MetasploitMCP bridge integration
- AdaptixC2 framework support
- Atomic-Operator integration for atomic red team tests
- Fluxion wireless attack integration
- SSTImap template injection scanner
- WPProbe WordPress scanner
- XSStrike advanced XSS detection
- GEF (GDB Enhanced Features) for exploit development

---

## [2.0.0] - 2026-02-01 — v1.0.0 Milestone

### Added
- 25/25 modules routed and tested
- 28/28 unit tests passing
- Clean boot sequence verified
- `PRODUCTION_READY.md` and `RESEARCH.md` academic abstract
- BibTeX citation block for academic use
- v1.0.0 release tagged

---

## [1.5.0] - 2026-01-15 — Hardware & Payloads

### Added
- **Flipper Zero Evolution Engine** — 10-level XP system, auto-detect, background watcher daemon
- **BadUSB Studio** — Hak5-style visual payload editor, 2,165 DuckyScript payloads ingested
- **Payload Studio UI** — visual payload builder
- **Purple Team Module** — offensive + defensive pairing on every technique
- **Social Engineering Engine** — phishing, pretexting, vishing frameworks
- **Campaign Manager** — multi-target engagement coordination
- **Auto Kill Chain** — 6-phase automated attack sequences
- **Credential Engine** — credential harvesting, cracking, stuffing automation
- **Professional HTML Report Generator** — CVSS-scored, MITRE-linked, client-ready

---

## [1.0.0] - 2025-11-01 — Foundation

### Added
- FastAPI backend with ReAct agent loop
- Ollama LLM integration (Mistral 7B, qwen2.5-coder:7b)
- ChromaDB RAG with nomic-embed-text embeddings
- 41 inline security lessons covering AD, Kerberos, Mimikatz, BloodHound, web shells
- MITRE ATT&CK-aligned BAS engine
- Compliance Mapper (CIS, NIST, PCI-DSS, HIPAA, SOC 2, ISO 27001)
- Blue Team engine with auto-hardening and PCAP analysis
- Natural language expansion layer (500+ operator phrasings, typo correction)
- Smart Wizard with 11 tool wizards and 120+ trigger phrases
- Initial hardware support: Flipper Zero, WiFi Pineapple Nano, Alfa AWUS036ACM

---

*Full commit history: `git log --oneline`*
