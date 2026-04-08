#!/bin/bash
# =============================================================================
# ERR0RS ULTIMATE — VM Deployment Script
# Supports: Kali Linux, Parrot OS Security, Parrot Home, Debian, Ubuntu
# Run this INSIDE your VM after cloning the repo
# Usage: sudo bash scripts/deploy_kali_vm.sh
# =============================================================================

# Detect distro
if [ -f /etc/os-release ]; then
  . /etc/os-release
  DISTRO_ID="${ID,,}"
  DISTRO_NAME="$NAME"
else
  DISTRO_ID="unknown"; DISTRO_NAME="Linux"
fi

set -e  # Exit on any error

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_DIR/venv"
LOG="$REPO_DIR/deploy.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; PURPLE='\033[0;35m'
CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

banner() {
  echo -e "${PURPLE}"
  echo "  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
  echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
  echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
  echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
  echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
  echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
  echo -e "  ${CYAN}Kali VM Deployment Script v2.0${NC}"
  echo ""
}

log() { echo -e "${GREEN}[+]${NC} $1" | tee -a "$LOG"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG"; }
err() { echo -e "${RED}[-]${NC} $1" | tee -a "$LOG"; }
section() { echo -e "\n${CYAN}══ $1 ══${NC}" | tee -a "$LOG"; }

check_root() {
  if [ "$EUID" -ne 0 ]; then
    err "Run as root: sudo bash scripts/deploy_kali_vm.sh"
    exit 1
  fi
}

step1_system_deps() {
  section "STEP 1 — System Dependencies"
  echo -e "  ${CYAN}Deploying on: $DISTRO_NAME${NC}"
  apt update -qq 2>&1 | tee -a "$LOG"

  # Core packages identical on Kali + Parrot + Debian/Ubuntu
  apt install -y \
    python3 python3-pip python3-venv python3-dev git curl wget \
    nmap hydra hashcat aircrack-ng sqlmap nikto \
    postgresql postgresql-contrib redis-server \
    libssl-dev libffi-dev build-essential \
    libimobiledevice-utils usbmuxd \
    xdg-utils 2>&1 | tee -a "$LOG"

  # Parrot Security Edition already ships with most tools
  # Try metasploit — available on both Kali and Parrot Security
  apt install -y metasploit-framework 2>/dev/null | tee -a "$LOG" || \
    warn "Metasploit not in repos — install manually if needed"

  # Optional tools — gobuster, amass, nuclei
  for tool in gobuster amass nuclei; do
    apt install -y "$tool" 2>/dev/null && log "$tool installed" || \
      warn "$tool not found in repos — may need manual install"
  done

  log "System dependencies installed on $DISTRO_NAME"
}

step2_venv() {
  section "STEP 2 — Python Virtual Environment"
  cd "$REPO_DIR"
  python3 -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG"
  pip install -r requirements.txt 2>&1 | tee -a "$LOG"
  # Extra UI deps
  pip install websockets aiohttp 2>&1 | tee -a "$LOG"
  log "Virtual environment ready at $VENV_DIR"
}

step3_database() {
  section "STEP 3 — PostgreSQL + Redis"
  service postgresql start
  service redis-server start
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='errorz'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE errorz;"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='errorz'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER errorz WITH PASSWORD 'err0rs_secure';"
  sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE errorz TO errorz;" 2>/dev/null || true
  log "Database configured"
}

step4_env() {
  section "STEP 4 — Environment Config"
  if [ ! -f "$REPO_DIR/.env" ]; then
    cat > "$REPO_DIR/.env" <<EOF
# ERR0RS ULTIMATE — Environment Config
# AI Providers (all optional — ERR0RS works fully offline)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Database
DB_URL=postgresql://errorz:err0rs_secure@localhost/errorz
REDIS_URL=redis://localhost:6379

# UI Server
UI_HOST=127.0.0.1
UI_PORT=8765

# Security
SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=http://127.0.0.1:8765

# Hardware
HAILO_ENABLED=false
PI5_MODE=false
EOF
    log ".env created — add API keys if desired (optional)"
  else
    warn ".env already exists — skipping"
  fi
}

step5_autostart() {
  section "STEP 5 — Desktop Autostart Entry"
  mkdir -p /etc/xdg/autostart
  cat > /etc/xdg/autostart/errorz.desktop <<EOF
[Desktop Entry]
Type=Application
Name=ERR0RS Assistant
Comment=AI Penetration Testing Assistant
Exec=bash -c "cd $REPO_DIR && source venv/bin/activate && python3 src/ui/errorz_launcher.py"
Icon=$REPO_DIR/docs/errorz_icon.png
Terminal=false
Categories=Security;
EOF
  # Also create app launcher shortcut
  cat > /usr/share/applications/errorz.desktop <<EOF
[Desktop Entry]
Type=Application
Name=ERR0RS Assistant v2.0
Comment=AI-Powered Pentest Assistant
Exec=bash -c "cd $REPO_DIR && source venv/bin/activate && python3 src/ui/errorz_launcher.py"
Terminal=false
Categories=Security;Network;
EOF
  log "Desktop entries created"
}

step6_run_test() {
  section "STEP 6 — Smoke Test"
  cd "$REPO_DIR"
  source "$VENV_DIR/bin/activate"
  python3 -c "
import sys
sys.path.insert(0, 'src')
print('[+] Python path OK')
try:
    from core.tool_executor import ToolExecutor
    print('[+] ToolExecutor import OK')
except Exception as e:
    print(f'[!] ToolExecutor: {e}')
try:
    from ui.errorz_launcher import HOST, PORT
    print(f'[+] UI launcher OK — will serve on {HOST}:{PORT}')
except Exception as e:
    print(f'[!] UI launcher: {e}')
print('[+] Smoke test complete')
"
}

main() {
  banner
  check_root
  log "Starting deployment — log at $LOG"
  step1_system_deps
  step2_venv
  step3_database
  step4_env
  step5_autostart
  step6_run_test
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  ERR0RS DEPLOYED SUCCESSFULLY ON KALI VM  ✓     ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${CYAN}To launch ERR0RS:${NC}"
  echo "  cd $REPO_DIR"
  echo "  source venv/bin/activate"
  echo "  python3 src/ui/errorz_launcher.py"
  echo ""
  echo -e "  ${CYAN}Next step → run build_iso.sh to create Pi 5 image${NC}"
}

main
