#!/usr/bin/env python3
"""Fix README.md install instructions and Quick Start section."""
import re

with open('/home/kali/ERR0RS-Ultimate/README.md', 'r') as f:
    content = f.read()

changed = 0

# ── Fix 1: Quick Start section ─────────────────────────────────────────────
OLD_QS = (
    "## Quick Start\n\n"
    "```bash\n"
    "# Clone with submodules\n"
    "git clone --recurse-submodules https://github.com/Gnosisone/ERR0RS-Ultimate.git\n"
    "cd ERR0RS-Ultimate\n\n"
    "# Install (Kali / Parrot)\n"
    "chmod +x install.sh && ./install.sh\n\n"
    "# Configure\n"
    "cp configs/config.template.env .env\n"
    "nano .env   # Set LLM_BACKEND, FLIPPER_PORT, etc.\n\n"
    "# Launch\n"
    "python main.py              # Interactive terminal\n"
    "python main.py --dashboard  # Live web dashboard \u2192 http://127.0.0.1:5000\n"
    "python main.py --api        # REST API \u2192 http://0.0.0.0:8000/docs\n"
    "```"
)

NEW_QS = (
    "## Quick Start\n\n"
    "```bash\n"
    "# 1. Clone the repo\n"
    "git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git\n"
    "cd ERR0RS-Ultimate\n\n"
    "# 2. Run the installer (handles Python deps, Ollama, .env creation, desktop icon)\n"
    "sudo bash install.sh\n\n"
    "# 3. .env is created automatically — just edit to customize\n"
    "nano .env   # Set LLM_BACKEND, OLLAMA_MODEL, API keys, etc.\n\n"
    "# 4. Launch\n"
    "bash start_err0rs.sh                 # Recommended \u2014 web UI at http://127.0.0.1:8765\n"
    "python3 src/ui/errorz_launcher.py    # Direct launcher (same result)\n"
    "python3 main.py                      # CLI-only mode\n"
    "```\n\n"
    "> \u26a0\ufe0f **Do NOT run `cp configs/config.template.env .env` manually** \u2014 "
    "`install.sh` creates `.env` with a generated secret key. "
    "Running the `cp` afterwards overwrites that key with the placeholder template. "
    "Only use `config.template.env` as a reference."
)

if OLD_QS in content:
    content = content.replace(OLD_QS, NEW_QS, 1)
    changed += 1
    print("OK  Quick Start section updated")
else:
    print("MISS Quick Start section not found exactly -- skipping")

# ── Fix 2: Installation section ────────────────────────────────────────────
OLD_INST = (
    "## Installation\n\n"
    "### Kali Linux / Parrot OS (recommended)\n\n"
    "```bash\n"
    "git clone --recurse-submodules https://github.com/Gnosisone/ERR0RS-Ultimate.git\n"
    "cd ERR0RS-Ultimate\n"
    "chmod +x install.sh && ./install.sh\n"
    "cp configs/config.template.env .env\n"
    "```\n\n"
    "### Raspberry Pi 5 (field deployment)\n\n"
    "```bash\n"
    "# Run the Pi 5 first-boot setup script\n"
    "chmod +x scripts/pi5_first_boot.sh && ./scripts/pi5_first_boot.sh\n\n"
    "# Install Hailo-10H NPU driver\n"
    "chmod +x scripts/install_hailo_h10.sh && ./scripts/install_hailo_h10.sh\n\n"
    "# Then standard install\n"
    "./install.sh\n"
    "```\n\n"
    "### Manual dependency install\n\n"
    "```bash\n"
    "pip install -r requirements-kali.txt --break-system-packages\n\n"
    "# Optional: Flask dashboard\n"
    "pip install flask flask-socketio --break-system-packages\n\n"
    "# Optional: bcrypt auth\n"
    "pip install bcrypt --break-system-packages\n"
    "```"
)

NEW_INST = (
    "## Installation\n\n"
    "### Prerequisites\n\n"
    "| Requirement | Notes |\n"
    "|---|---|\n"
    "| **Kali Linux, Parrot OS, or Ubuntu/Debian** | x86\\_64 or ARM64 |\n"
    "| **Python 3.10+** | `python3 --version` to check |\n"
    "| **git** | `sudo apt install git` |\n"
    "| **Ollama** | Installed automatically by `install.sh` |\n"
    "| **~4 GB disk free** | For Ollama model + Python deps |\n\n"
    "> \U0001f4a1 **Phoenix Arsenal users:** Install "
    "[Phoenix-OS](https://github.com/Gnosisone/Phoenix-OS) **before** ERR0RS-Ultimate "
    "if you want the full 2,172-tool arsenal. ERR0RS auto-detects Phoenix at "
    "`/home/kali/Phoenix-OS` and enables the Phoenix Bridge. "
    "ERR0RS works fully without Phoenix \u2014 Phoenix just unlocks the extended tool grid.\n\n"
    "---\n\n"
    "### Kali Linux / Parrot OS (recommended)\n\n"
    "```bash\n"
    "# 1. Clone the repo\n"
    "git clone https://github.com/Gnosisone/ERR0RS-Ultimate.git\n"
    "cd ERR0RS-Ultimate\n\n"
    "# 2. Run installer as root (handles system deps, Ollama, .env, desktop icon)\n"
    "sudo bash install.sh\n\n"
    "# 3. Launch\n"
    "bash start_err0rs.sh\n"
    "# Web UI opens at http://127.0.0.1:8765\n"
    "```\n\n"
    "> \u2705 **The installer creates `.env` automatically.** "
    "Do NOT manually `cp configs/config.template.env .env` \u2014 "
    "it will overwrite your auto-generated secret key. "
    "Only use `config.template.env` as a reference for adding custom keys.\n\n"
    "---\n\n"
    "### Raspberry Pi 5 (field deployment)\n\n"
    "```bash\n"
    "# Run the Pi 5 first-boot setup script\n"
    "sudo bash scripts/pi5_first_boot.sh\n\n"
    "# Optional: Install Hailo-10H NPU driver\n"
    "sudo bash scripts/install_hailo_h10.sh\n\n"
    "# Then standard install\n"
    "sudo bash install.sh\n"
    "```\n\n"
    "---\n\n"
    "### Manual dependency install (no sudo / advanced users)\n\n"
    "```bash\n"
    "pip install -r requirements-kali.txt --break-system-packages\n\n"
    "# Optional: Flask dashboard\n"
    "pip install flask flask-socketio --break-system-packages\n\n"
    "# Optional: bcrypt auth\n"
    "pip install bcrypt --break-system-packages\n\n"
    "# Create .env manually (only when NOT using install.sh)\n"
    "cp configs/config.template.env .env\n"
    "nano .env   # Fill in LLM_BACKEND, model, API keys\n"
    "```"
)

if OLD_INST in content:
    content = content.replace(OLD_INST, NEW_INST, 1)
    changed += 1
    print("OK  Installation section updated")
else:
    print("MISS Installation section not found exactly -- skipping")

with open('/home/kali/ERR0RS-Ultimate/README.md', 'w') as f:
    f.write(content)

print(f"\nDone -- {changed}/2 sections updated")
