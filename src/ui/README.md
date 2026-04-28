# ERR0RS UI v2.0 — Web Dashboard

## Overview
Fully local web-based assistant dashboard featuring the ERR0RS mascot.
**No data leaves the machine.** Runs on `127.0.0.1:8765` via Python's built-in HTTP server.

## Structure
```
src/ui/
├── errorz_launcher.py   ← Python server + framework bridge
├── web/
│   └── index.html       ← Full dashboard UI (single file, no CDN deps)
├── errorz/
│   └── errorz_core.py   ← Legacy PyGame/PyQt5 sprite engine
└── kat/
    └── kat_core.py      ← Legacy K.A.T. assistant core
```

## Launch
```bash
python3 src/ui/errorz_launcher.py
```
Opens `http://127.0.0.1:8765` in your default browser automatically.

## Features
- 🐱 **ERR0RS Mascot** — animated SVG cat character with glowing eyes, hoodie, BAPE pants
- 💬 **Speech bubble** — cycles contextual hacker quotes, updates on tool launch
- 📊 **Stat bars** — live-animated NPU load, RAM, network I/O
- 🖥️ **Terminal** — interactive command input, routes to ERR0RS framework when available
- 🔧 **Tool Grid** — 16 quick-launch buttons (Nmap, Metasploit, Hydra, Pineapple, Flipper, etc.)
- 📋 **Pentest Phases** — visual phase tracker (Recon → Report)
- 📡 **Intel Feed** — live event log in the right panel
- 🔌 **REST API** — `/api/status`, `/api/command`, `/api/tool` endpoints

## API Endpoints
| Method | Endpoint       | Body                          | Returns           |
|--------|---------------|-------------------------------|-------------------|
| GET    | /api/status   | —                             | System info JSON  |
| GET    | /api/phases   | —                             | Phase list JSON   |
| POST   | /api/command  | `{"command": "scan 10.0.0.1"}`| Output from NLI   |
| POST   | /api/tool     | `{"tool":"nmap","args":[...]}`| Tool launch result|

## Next Steps
- [ ] WebSocket integration for real-time tool output streaming
- [ ] Sprite animation upgrade using Canvas API
- [ ] Voice command input (local Whisper model via Hailo NPU)
- [ ] Report viewer panel (inline HTML report rendering)
