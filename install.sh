#!/usr/bin/env bash
# =============================================================================
# ERR0RS ULTIMATE - Universal Installer
# Supports: Kali Linux, Parrot OS, Ubuntu, Debian
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
# Usage: sudo bash install.sh
# =============================================================================

set -e
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
PURPLE='\033[0;35m'; RED='\033[0;31m'; NC='\033[0m'

# ── Detect Distro ─────────────────────────────────────────────────────────────
detect_distro() {
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="${ID,,}"
    DISTRO_NAME="$NAME"
  else
    DISTRO_ID="unknown"
    DISTRO_NAME="Unknown Linux"
  fi
}

# ── Banner ────────────────────────────────────────────────────────────────────
banner() {
  echo -e "${PURPLE}"
  echo "  ██████╗ ██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
  echo "  ██╔════╝██╔══██╗██╔══██╗██╔═████╗██╔══██╗██╔════╝"
  echo "  █████╗  ██████╔╝██████╔╝██║██╔██║██████╔╝███████╗"
  echo "  ██╔══╝  ██╔══██╗██╔══██╗████╔╝██║██╔══██╗╚════██║"
  echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
  echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
  echo -e "${NC}  Universal Installer | Kali • Parrot • Debian • Ubuntu"
  echo -e "  Detected: ${CYAN}$DISTRO_NAME${NC} (${DISTRO_ID})\n"
}

ARCH=$(uname -m)

# ── Step 1: System Packages ───────────────────────────────────────────────────
install_system_deps() {
  echo -e "\n${CYAN}[1/5] Installing system packages for $DISTRO_NAME...${NC}"
  apt update -qq

  # Core packages — same on all Debian-based distros
  CORE_PKGS="python3 python3-pip python3-venv python3-dev git curl wget \
    libssl-dev libffi-dev build-essential xdg-utils"

  # Security tools — available on both Kali and Parrot
  # Parrot uses same package names as Kali for most tools
  SEC_PKGS="nmap hydra hashcat aircrack-ng sqlmap nikto"

  # These may or may not be pre-installed (Parrot Security has most already)
  OPT_PKGS="gobuster amass nuclei"

  # Metasploit — installed differently on Parrot vs Kali
  if [[ "$DISTRO_ID" == "kali" ]]; then
    MSF_PKG="metasploit-framework"
  elif [[ "$DISTRO_ID" == "parrot" ]] || [[ "$DISTRO_ID" == "parrotsec" ]]; then
    MSF_PKG="metasploit-framework"   # Parrot also has it in repos
  else
    MSF_PKG=""   # Will install via script below if missing
  fi

  apt install -y $CORE_PKGS $SEC_PKGS 2>/dev/null || true

  # Install optional tools — don't fail if not available in this repo
  for pkg in $OPT_PKGS $MSF_PKG; do
    apt install -y "$pkg" 2>/dev/null && \
      echo -e "  ${GREEN}✓${NC} $pkg" || \
      echo -e "  ${YELLOW}~${NC} $pkg not in repos — skipping (install manually if needed)"
  done

  # Install libimobiledevice for iOS attacks
  apt install -y libimobiledevice-utils libimobiledevice-dev \
    usbmuxd ifuse 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} libimobiledevice (iOS support)" || \
    echo -e "  ${YELLOW}~${NC} libimobiledevice optional — install for iOS attacks"

  # PostgreSQL + Redis (optional, for engagement memory)
  apt install -y postgresql postgresql-contrib redis-server 2>/dev/null || true

  echo -e "  ${GREEN}System packages done${NC}"
}

# ── Step 2: Python Dependencies ───────────────────────────────────────────────
install_python_deps() {
  echo -e "\n${CYAN}[2/5] Installing Python dependencies...${NC}"

  # Parrot and Kali both need --break-system-packages on newer Python
  PIP_FLAGS="--break-system-packages -q"

  pip3 install requests fastapi uvicorn pydantic $PIP_FLAGS
  pip3 install anthropic openai $PIP_FLAGS
  pip3 install chromadb sentence-transformers $PIP_FLAGS
  pip3 install psutil python-dotenv rich click $PIP_FLAGS

  # iOS/macOS tools
  pip3 install pyidevice 2>/dev/null || true

  echo -e "  ${GREEN}Python deps done${NC}"
}

# ── Step 3: Ollama (Local LLM) ────────────────────────────────────────────────
install_ollama() {
  echo -e "\n${CYAN}[3/5] Setting up Ollama (local AI)...${NC}"
  if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    echo -e "  ${GREEN}✓${NC} Ollama installed"
  else
    echo -e "  ${YELLOW}~${NC} Ollama already installed"
  fi

  # Start Ollama if not running
  if ! pgrep -x "ollama" >/dev/null; then
    ollama serve &>/dev/null & sleep 3
  fi

  # Choose model based on arch
  if [[ "$ARCH" == "aarch64" ]]; then
    MODEL="llama3.2"      # Optimized for ARM (Pi 5)
  else
    MODEL="${OLLAMA_MODEL:-llama3.2}"
  fi

  echo -e "  Pulling model: ${CYAN}$MODEL${NC} (this takes a few minutes first time)..."
  ollama pull "$MODEL" && echo -e "  ${GREEN}✓${NC} $MODEL ready" || \
    echo -e "  ${YELLOW}~${NC} Pull failed — start Ollama manually: ollama pull $MODEL"
}

# ── Step 4: Environment Config ────────────────────────────────────────────────
setup_env() {
  echo -e "\n${CYAN}[4/5] Creating .env config...${NC}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ENV_FILE="$SCRIPT_DIR/.env"

  if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
# ERR0RS ULTIMATE — Environment Config
# All API keys are optional — ERR0RS works 100% offline with Ollama

# AI Providers (leave blank to use Ollama only)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# LLM Backend: ollama | anthropic | openai
LLM_BACKEND=ollama
OLLAMA_MODEL=$MODEL
OLLAMA_HOST=http://localhost:11434

# Database (optional — for engagement memory)
DB_URL=postgresql://errorz:err0rs_secure@localhost/errorz
REDIS_URL=redis://localhost:6379

# Web UI
UI_HOST=127.0.0.1
UI_PORT=8765

# Security
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "changeme_$(date +%s)")

# Hardware flags (auto-detected at runtime)
HAILO_ENABLED=false
PI5_MODE=false

# Distro
DISTRO=$DISTRO_ID
EOF
    echo -e "  ${GREEN}✓${NC} .env created at $ENV_FILE"
  else
    echo -e "  ${YELLOW}~${NC} .env already exists — skipping"
  fi
}

# ── Step 5: Desktop Integration ───────────────────────────────────────────────
setup_desktop() {
  echo -e "\n${CYAN}[5/5] Setting up desktop integration...${NC}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  # Create desktop launcher
  DESKTOP_DIR="$HOME/Desktop"
  mkdir -p "$DESKTOP_DIR" 2>/dev/null || true

  cat > "$DESKTOP_DIR/ERR0RS.desktop" << EOF
[Desktop Entry]
Type=Application
Name=3RR0RZ Virtual Assistant
Comment=AI-Powered Penetration Testing Assistant
Exec=bash -c "cd $SCRIPT_DIR && python3 src/ui/errorz_launcher.py"
Terminal=false
Categories=Security;Network;
EOF
  chmod +x "$DESKTOP_DIR/ERR0RS.desktop" 2>/dev/null || true

  # System-wide app entry
  cat > /usr/share/applications/errorz.desktop << EOF
[Desktop Entry]
Type=Application
Name=3RR0RZ Virtual Assistant
Comment=AI-Powered Red Team Assistant — ERR0RS ULTIMATE
Exec=bash -c "cd $SCRIPT_DIR && python3 src/ui/errorz_launcher.py"
Terminal=false
Categories=Security;Network;
EOF
  echo -e "  ${GREEN}✓${NC} Desktop shortcuts created"

  # Add to PATH
  if ! grep -q "ERR0RS" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# ERR0RS ULTIMATE" >> ~/.bashrc
    echo "alias errorz='cd $SCRIPT_DIR && python3 src/ui/errorz_launcher.py'" >> ~/.bashrc
    echo "alias errorz-cli='cd $SCRIPT_DIR && python3 main.py'" >> ~/.bashrc
    echo -e "  ${GREEN}✓${NC} Aliases added to .bashrc → type 'errorz' to launch"
  fi
}

# ── Smoke Test ────────────────────────────────────────────────────────────────
smoke_test() {
  echo -e "\n${CYAN}Running quick smoke test...${NC}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$SCRIPT_DIR"
  python3 -c "
import sys; sys.path.insert(0, 'src')
tests = [
  ('src.ai.providers',         'LLMRouter'),
  ('src.ai.agents',            'RedTeamAgent'),
  ('src.ai.agents.vuln_chain', 'VulnChainAgent'),
  ('src.tools.apple.apple_attack', 'macOSAttackModule'),
  ('src.tools.apple.ios_attack',   'iOSAttackModule'),
  ('src.tools.web.web_advanced',   'GraphQLAttacker'),
]
passed = 0
for mod, cls in tests:
  try:
    m = __import__(mod, fromlist=[cls])
    getattr(m, cls)
    print(f'  [+] {cls}')
    passed += 1
  except Exception as e:
    print(f'  [!] {cls}: {e}')
print(f'  Passed: {passed}/{len(tests)}')
" && echo -e "  ${GREEN}Smoke test complete${NC}" || \
  echo -e "  ${YELLOW}Some imports failed — check requirements${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  detect_distro
  banner

  # Check if running as root for system installs
  if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Not running as root — skipping system package install${NC}"
    echo -e "    For full install run: ${CYAN}sudo bash install.sh${NC}\n"
    install_python_deps
    setup_env
    setup_desktop
    smoke_test
  else
    install_system_deps
    install_python_deps
    install_ollama
    setup_env
    setup_desktop
    smoke_test
  fi

  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║   3RR0RZ INSTALLED ON $DISTRO_NAME  ✓   ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}Launch Web UI:${NC}  python3 src/ui/errorz_launcher.py"
  echo -e "  ${CYAN}Launch CLI:${NC}     python3 main.py"
  echo -e "  ${CYAN}Or just type:${NC}   errorz   (after reloading shell)"
  echo ""
  echo -e "  Web UI will open at: ${CYAN}http://127.0.0.1:8765${NC}"
  echo ""
  echo -e "${YELLOW}  NOTE: Knowledge base submodules are NOT cloned by default.${NC}"
  echo -e "  To pull all KB repos (research/tools), run:"
  echo -e "  ${CYAN}git submodule update --init --recursive${NC}"
  echo -e "  (Warning: some repos are large — allow 10-30 min on first clone)"
  echo ""
}
