# ERR0RS-Ultimate — Quick Start

> Full documentation: [README.md](README.md) · [Architecture](docs/ARCHITECTURE.md)

---

## 1 — Clone

```bash
git clone --recurse-submodules https://github.com/Gnosisone/ERR0RS-Ultimate.git
cd ERR0RS-Ultimate
```

## 2 — Install

```bash
# Kali Linux / Parrot OS
chmod +x install.sh && ./install.sh

# Raspberry Pi 5 (first time)
chmod +x scripts/pi5_first_boot.sh && ./scripts/pi5_first_boot.sh
./install.sh
```

## 3 — Configure

```bash
cp configs/config.template.env .env
nano .env
```

Minimum required settings:

```bash
LLM_BACKEND=ollama            # or: anthropic / openai
OLLAMA_MODEL=qwen2.5-coder:7b
```

## 4 — Start Ollama (if using local LLM)

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

## 5 — Launch

```bash
# Interactive terminal (default)
python main.py

# Live dashboard at http://127.0.0.1:5000
python main.py --dashboard

# FastAPI server at http://0.0.0.0:8000/docs
python main.py --api

# Run a workflow directly
python main.py --workflow webapp 192.168.1.10

# Generate a report
python main.py --report 192.168.1.10

# Safe mode (no hardware execution)
python main.py --safe
```

## First commands

```
ERR0RS [red_team]> target 192.168.1.10    # Set your target
ERR0RS [red_team]> run scan 192.168.1.10  # Port scan
ERR0RS [red_team]> workflow webapp ...    # Full web assessment
ERR0RS [red_team]> autopilot 192.168.1.10 # Hands-free kill chain
ERR0RS [red_team]> explain nmap           # Learn about a tool
ERR0RS [red_team]> report 192.168.1.10   # Generate report
ERR0RS [red_team]> devices               # Hardware status
ERR0RS [red_team]> exit                  # Shutdown
```

---

*Authorized use only. Stay ethical.*
