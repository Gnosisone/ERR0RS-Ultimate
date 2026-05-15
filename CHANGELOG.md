# Changelog

All notable changes to ERR0RS ULTIMATE are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) · Versioning: [SemVer](https://semver.org)

---

## [3.5.0] - 2026-05-15 — The Teacher Release

The release that gave ERR0RS its voice. Adds the canonical system prompt
("the soul"), wires it into every LLM backend, ships a multi-backend
strategy (Claude / DeepSeek / Ollama), and lights up Socratic teach mode +
"WHY THIS?" reasoning buttons across the runtime.

### Added

#### The ERR0RS Soul — `src/ai/system_prompt.md`
- Canonical statement of who ERR0RS *is* when speaking to a student:
  wise, compassionate, patient teacher; honest about uncertainty; never
  fabricates CVE numbers, MITRE IDs, or detection signatures
- 216 lines covering character, scope of knowledge, how to teach, where
  to draw lines, voice rules — read by every LLM backend on every call
- Identity layer that survives across model swaps — switch backends and
  the voice stays the same

#### Multi-Backend LLM Strategy
- **Primary: Claude (Anthropic)** — best fit for pedagogy + careful structured output
- **Secondary: DeepSeek** — 5–10× cheaper, open weights, future local path on Pi 5 + Hailo
- **Tertiary: Ollama** — true offline operation when cloud calls aren't OK
- `LLM_FALLBACK_CHAIN=claude,deepseek,ollama` walks the chain automatically
- `AnthropicBackend`, `DeepSeekBackend`, `OllamaBackend` classes all load
  `system_prompt.md` and inject ERR0RS persona via system message
- Strategy doc: `docs/BACKEND_STRATEGY.md`

#### Socratic Teach Mode (`src/core/operator.py`)
- `OperatorState.teach_mode` field — toggleable from UI's 📚 button
- `_socratic_question()` — probes student with leading question after each
  tool run instead of just narrating findings
- `_quiz()` — short quiz mode tied to recently-run tool; fires when student
  has used the same tool 3+ times to confirm internalization
- `tool_use_counts` field tracks repeated tool usage for quiz triggering
- Streaming chat via WebSocket broadcast (blocking chat path preserved as fallback)

#### Chat Brain (`src/core/conversation_engine.py`)
- `build_system_prompt(operator_state, user_msg)` now injects:
  - Active target + operator mode
  - Last 3 tool runs with severity-iconed findings (🔴 🟡 🟢)
  - Auto-loaded teach_engine lesson for the most-recent tool
  - On-demand lesson when student mentions any tool by name in chat
- `inject_tool_context()` — kill-chain-aware coaching after each tool run

#### New API Endpoints (`src/ui/errorz_launcher.py`)
- `POST /api/operator/teach_mode` — toggle/set teach mode from UI; syncs
  every 3 seconds back to web frontend
- `POST /api/explain/suggestion` — streams ERR0RS's reasoning for WHY a
  given suggestion is the right next step; pulls operator state +
  registry data + kill-chain context

#### Web UI (`src/ui/web/index.html`)
- **"WHY THIS?" button** on every suggestion card — calls
  `/api/explain/suggestion` and streams the response inline
- **"Explain this output" hover button** on terminal output lines —
  click to ask ERR0RS what that specific line means
- **📚 TEACH ON/OFF toggle** in terminal header — async, syncs with backend
- CSS for the new purple-themed explain/why buttons
- Streaming-mode-aware reply handling (only shows `data.reply` in
  non-streaming fallback path)

#### Schema-Validated Tool Registry (Phase 2)
- `src/tools/tool_registry.schema.json` — JSON Schema draft-2020-12 spec
- `src/tools/tool_registry.v2.json` — 49 tools (47 migrated + 2 absorbed
  from teach_engine LESSONS: whatweb, netcat); avg 8.6 flags/tool, max
  30 on sqlmap; every tool has non-empty teach_intro
- `src/tools/concepts.v2.json` — 7 frameworks extracted as first-class
  concepts: CIA triad, OWASP Top 10, CIS Controls v8, MITRE ATT&CK, kill
  chain, incident response, threat modeling
- `tools/migrate_registry.py` — idempotent legacy → v2 migration
- `tools/validate_registry.py` — schema validator with jsonschema +
  hand-rolled fallback; CI-grade
- `tools/README.md` — maintenance scripts workflow guide

#### LLM Teach Generator (Phase 3)
- `tools/generate_teach.py` — 722 lines, fills the 5 stub fields per tool
  (`opsec_notes`, `sample_outputs`, `legal_notes`, `false_positives`,
  `mitre_attack`) via build-time LLM call
- Backends: Ollama (local, free), Anthropic Claude, DeepSeek — all
  injecting `system_prompt.md` as system message
- Streams `/api/generate` with `format=json`, 120s stall-guard, resume
  support, output to `tool_registry.generated.json` (never auto-merged
  into v2 — human review required)
- Prompt tuned for ERR0RS pedagogy: 4-6 opsec notes mixing beginner +
  bleeding-edge 2025-2026, two sample outputs (beginner + advanced
  chain), real MITRE IDs only (sub-techniques preferred), no fabricated
  CVEs
- Status: **gated on real NPU acceleration**. See
  `docs/HAILO_PHASE3_STATUS.md` for the four paths forward; recommended
  build-time path is Anthropic API (~$0.25 for 49-tool sweep)

#### Startup Preflight (`src/core/preflight.py`)
- 181-line health-check module that runs before anything else
- Checks: critical Python deps, SECRET_KEY not default placeholder,
  Ollama reachability (5s blocking timeout), core security tools on PATH
- `main.py --no-preflight` flag for faster boot
- Returns True only if everything critical passed; misconfig caught before
  user drops into a broken session

#### Interactive Setup Wizard (`main.py --setup`)
- 4-step `.env` builder for first-run users
- Prompts: backend selection (Claude/DeepSeek/Ollama), model choice,
  web UI bind/port, security key generation, engagement defaults
- Integrated into `interactive_mode` so first-run users aren't dropped
  into a cold prompt with no API key set

#### Install.sh Full Tool Universe (Phase 1)
- 312 → 936 lines, **35+ net new tools installed by default**
- New: `--with-c2` flag (Sliver, Mythic, Empire, Covenant, Merlin, PoshC2 — multi-GB)
- New: `--with-knowledge-repos` flag (GTFOBins, LOLBAS, PowerSploit, Watson,
  Beroot, windows-exploit-suggester, PrivescCheck, PayloadsAllTheThings,
  HackTricks for RAG indexing)
- New: `--skip-go-tools`, `--skip-pip-tools`, `--skip-github-tools`,
  `--skip-ollama` flags for minimal/offline installs
- Apt: 10 added (zmap, beef-xss, ropgadget, king-phisher, cupp,
  python3-pwntools, trufflehog, scrcpy, seclists, exploitdb)
- Go: 13 new tools via `go install` + symlink to `/usr/local/bin`
  (dalfox, katana, httpx, naabu, gau, waybackurls, assetfinder, gf,
  unfurl, anew, qsreplace, interactsh-client, gitleaks)
- Pip: 8 tools via pipx (droopescan, uro, graphqlmap) + git-clone wrapper
  pattern for tools without PyPI packages (corsy, jwt_tool, graphw00f,
  ssrfmap, nosqlmap)
- GitHub-clone: 4 tools to `/opt` (Sn1per, AutoSploit, LinkFinder,
  SecretFinder) with auto-symlinked entry scripts
- Install plan summary now shows all 7 flag states upfront
- Updated `--help` with FULL and MINIMAL install examples

#### Documentation
- `docs/BACKEND_STRATEGY.md` — philosophical reasoning for Claude /
  DeepSeek / Ollama ordering
- `docs/HAILO_PHASE3_STATUS.md` — honest hardware reality check; documents
  that Ollama doesn't yet use the Hailo NPU and lays out four viable
  paths forward (custom HailoBackend, GPU box, cloud API, wait)
- `docs/NEXT_SESSION.md` — strategic handoff brief for continuing work
- `docs/SAMPLE_qwen7b_nmap_OUTPUT.json` — cautionary evidence of
  small-model hallucination (qwen-7B confidently invented MITRE IDs +
  wrong defender artifacts for nmap)
- `.env.example` — full template with all backend keys + LLM_FALLBACK_CHAIN
- `.gitignore` updated to negate `.env.example` (track template, ignore
  real `.env`)

### Fixed (Install.sh)
- `main()` was defined but never invoked at EOF — script exited
  immediately on fresh clones. Now properly calls `main "$@"`.
- `SCRIPT_DIR` used in `main()` but never resolved there. Now resolved
  once at top of file.
- pip-vs-apt managed package conflict on Kali rolling. Now uses a venv at
  `$SCRIPT_DIR/venv` with `requirements-kali.txt`.
- pipx `git+https://` URLs silently failed (claimed success when they
  didn't install). Now splits PyPI vs git paths with clone-and-wrap for git.
- Pipeline exit-code bug: `cmd | tail -2 && ✓` always claimed success
  because `tail` exits 0. Fixed with proper `$?` capture.
- PrivescCheck moved from `install_github_tools` to `init_knowledge_repos`
  where it actually belongs (Windows-side reference, not a Linux binary).

### Changed
- Replaced background Ollama health-check thread (`_bg_health`) with the
  new `preflight.run()` synchronous check — same job, cleaner UX,
  fail-fast on misconfig
- README updated end-to-end for the v3.5.0 surface area
- Repo URL corrected throughout from `ERR0RS-clean` (local dir name) to
  `ERR0RS-Ultimate` (actual GitHub repo)

### Documentation Updates
- README sections added: "What's New in v3.5.0", "LLM Backends", "Tool
  Registry & Teach Generator"
- Architecture diagram updated to show multi-backend LLM Router with soul
  injection and new endpoints
- Install section now documents the full flag matrix
- Security & Ethics section now explicit about where ERR0RS draws lines
  (engages with authorized offensive curriculum; won't help target real
  people for harm or build mass-impact weapons)

---

## [3.4.0] - 2026-05-03 — Sprint 04: Professor Mode

The release that made ERR0RS into a coach. Adds the `ProfessorEngine`
real-time AI security coaching layer, `UserProfile` for per-student
skill tracking, and wires Professor Mode into the kill chain end-to-end.

### Added

#### Professor Engine (`src/core/professor_engine.py`)
- Real-time AI security coaching that activates during any tool run
- Pulls operator state + recent findings + RAG context, then delivers
  in-flight commentary as the kill chain advances
- Triggered from kill chain integration points: post-recon, mid-exploit,
  during persistence, on credential dump
- Outputs structured `CoachMessage` records that the UI renders as
  amber/purple sidebar cards

#### UserProfile (`src/core/user_profile.py`)
- Per-student skill model that tracks: tools used, tool proficiency
  (beginner → expert), concepts covered, recent stuck-points
- Persists at `~/.err0rs/user_profile.json`
- Professor Engine reads UserProfile to calibrate coaching depth
  (beginner gets fundamentals; expert gets bleeding-edge nuance)

#### Sprint 04 C+D+E Integration
- Professor Mode wired into `auto_killchain.py` at all 6 phase boundaries
- Kill chain now broadcasts `professor_advice` WebSocket events alongside
  `intel` and `coach` events
- Web UI subscribes and renders Professor cards in the right sidebar

### Changed
- `ConversationEngine` refactored to support ProfessorEngine's streaming
  use case (audit confirmed ConversationEngine was already 90% of
  ProfessorEngine — reused infrastructure, didn't duplicate)

---

## [3.3.0] - 2026-04-29 — Sprint 01–03.5: Web App Killchain Expansion

The release that took ERR0RS from "good web recon" to "complete web app
killchain." Adds JWT manipulation, NoSQL injection, SSTI, and prototype
pollution as native killchain phases with their own engines.

### Added

#### JWT Manipulation Engine (Sprint 01 + 01.5)
- Algorithm confusion attacks (`alg: none`, `RS256→HS256`)
- Key disclosure scanning + auto-forge for known-key cases
- JWT secret cracking against rockyou.txt
- Integrated as a kill-chain phase between auth-recon and post-auth-exploit

#### NoSQL Injection Engine (Sprint 02 + 02.5)
- MongoDB injection (`{"$ne": null}`, regex auth bypass, blind boolean)
- Operator-aware fuzzing for `$where`, `$gt`, `$regex`
- Wired into killchain after web-recon phase

#### SSTI / Prototype Pollution Engine (Sprint 03 + 03.5)
- Server-Side Template Injection detection across Jinja2, Twig, Velocity,
  Freemarker, ERB
- Prototype Pollution payload library for Node.js + Express + Lodash chains
- Auto-detection of vulnerable parser by polyglot probe payloads
- Both wired into killchain post-recon

#### Engagement Orchestrator (Sprint 00 prep)
- Lightweight session scoping wrapper added before JWT engine
- Tracks authorized targets + RoE constraints per engagement
- Prevents accidental out-of-scope scans

### Changed
- Kill chain auto-runner now has 4 new phase modules — JWT, NoSQL, SSTI,
  ProtoPollution
- Updated `juice-shop-portfolio` link in README

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
