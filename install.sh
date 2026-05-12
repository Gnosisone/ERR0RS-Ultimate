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
    libssl-dev libffi-dev build-essential xdg-utils jq unzip"

  # Security tools — available on both Kali and Parrot
  # Parrot uses same package names as Kali for most tools
  SEC_PKGS="nmap hydra hashcat aircrack-ng sqlmap nikto"

  # Optional Kali/Parrot tools — ERR0RS kill chain expects these.
  # Most ship pre-installed on Kali full; not on Kali light or non-Kali distros.
  # Forgiving loop below — '✓' if it installs, '~' if not available.
  OPT_PKGS="gobuster amass nuclei whatweb wpscan ffuf feroxbuster \
    theharvester subfinder dirb wordlists commix xsser \
    crackmapexec enum4linux responder bettercap evil-winrm \
    impacket-scripts dnsenum dnsrecon onesixtyone snmp-check \
    ldap-utils smbclient smbmap"

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

# ── Step 1b: Go-based security tools ──────────────────────────────────────────
# Several tools the ERR0RS kill chain expects (dalfox, katana, httpx, etc.)
# are Go binaries not packaged in Kali/Parrot apt. We install Go, then
# `go install` each tool, then symlink into /usr/local/bin so they're on PATH
# for all users (including non-root callers via the kill chain).
install_go_tools() {
  echo -e "\n${CYAN}[1b/5] Installing Go-based security tools...${NC}"

  # Install golang-go if missing. We don't need a bleeding-edge Go;
  # the apt version is fine for `go install` against modern modules.
  if ! command -v go &>/dev/null; then
    echo -e "  ${CYAN}Installing golang-go via apt...${NC}"
    apt install -y golang-go 2>/dev/null || {
      echo -e "  ${RED}✗${NC} Failed to install golang-go — skipping Go tools"
      echo -e "  ${YELLOW}~${NC} dalfox, katana, httpx will be unavailable"
      return 0
    }
  fi

  echo -e "  ${GREEN}✓${NC} Go: $(go version 2>&1 | awk '{print $3}')"

  # Tools to install via `go install`. Format: "binary_name|module@version"
  # @latest is fine for most; pinning would be future-proofing for OSU delivery.
  GO_TOOLS=(
    "dalfox|github.com/hahwul/dalfox/v2@latest"
    "katana|github.com/projectdiscovery/katana/cmd/katana@latest"
    "httpx|github.com/projectdiscovery/httpx/cmd/httpx@latest"
    "naabu|github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    "gau|github.com/lc/gau/v2/cmd/gau@latest"
    "waybackurls|github.com/tomnomnom/waybackurls@latest"
    "assetfinder|github.com/tomnomnom/assetfinder@latest"
    "gf|github.com/tomnomnom/gf@latest"
  )

  # Determine where `go install` writes binaries. When running under sudo,
  # GOPATH defaults to /root/go/bin. We want them in $SUDO_USER's GOPATH
  # so they're owned by the user, then symlinked to /usr/local/bin.
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    USER_GOBIN="$USER_HOME/go/bin"
    mkdir -p "$USER_GOBIN"
    chown -R "$SUDO_USER":"$SUDO_USER" "$USER_HOME/go"
  else
    USER_GOBIN="${HOME}/go/bin"
    mkdir -p "$USER_GOBIN"
  fi

  for entry in "${GO_TOOLS[@]}"; do
    bin_name="${entry%%|*}"
    module="${entry##*|}"

    # If a binary by this name is already on PATH AND it isn't one of our
    # previous symlinks (which point into the user's go/bin), skip — likely
    # an apt-installed version we shouldn't override.
    existing=$(command -v "$bin_name" 2>/dev/null || true)
    if [ -n "$existing" ] && [ ! -L "$existing" ]; then
      echo -e "  ${YELLOW}~${NC} $bin_name already present at $existing — skipping"
      continue
    fi

    echo -e "  ${CYAN}Installing $bin_name from $module...${NC}"

    # `go install` as the invoking user so module cache + binaries land in
    # their $HOME, not /root. This avoids root-owned ~/go/pkg/mod issues.
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      sudo -u "$SUDO_USER" -H bash -c "go install '$module'" 2>&1 | tail -3
    else
      go install "$module" 2>&1 | tail -3
    fi

    # Symlink user's go binary into /usr/local/bin (root-readable, on default PATH)
    if [ -f "$USER_GOBIN/$bin_name" ]; then
      ln -sf "$USER_GOBIN/$bin_name" "/usr/local/bin/$bin_name"
      echo -e "  ${GREEN}✓${NC} $bin_name → /usr/local/bin/$bin_name"
    else
      echo -e "  ${YELLOW}~${NC} $bin_name install failed — check $USER_GOBIN"
    fi
  done

  echo -e "  ${GREEN}Go tools done${NC}"
}

# ── Step 2: Python Dependencies ───────────────────────────────────────────────
install_python_deps() {
  echo -e "\n${CYAN}[2/5] Installing Python dependencies (venv)...${NC}"

  # ── Modern Kali/Parrot ship PEP 668 EXTERNALLY-MANAGED Python.
  # ── We use a project-local venv at $SCRIPT_DIR/venv to avoid clobbering
  # ── system packages (e.g., python3-starlette) that apt manages.
  # ── start_err0rs.sh also expects $SCRIPT_DIR/venv — same path, no surprises.

  VENV_DIR="$SCRIPT_DIR/venv"

  # Pick the right requirements file: prefer the lean Kali/Parrot list
  # on those distros (no GUI / build deps), full list elsewhere.
  if [[ "$DISTRO_ID" == "kali" ]] || [[ "$DISTRO_ID" == "parrot" ]] || [[ "$DISTRO_ID" == "parrotsec" ]]; then
    REQ_FILE="$SCRIPT_DIR/requirements-kali.txt"
  else
    REQ_FILE="$SCRIPT_DIR/requirements.txt"
  fi

  if [ ! -f "$REQ_FILE" ]; then
    echo -e "  ${RED}✗${NC} Missing $REQ_FILE — aborting Python install"
    return 1
  fi

  # Create venv if missing. We use --system-site-packages OFF so the venv
  # is fully isolated — no inheriting apt's broken-record packages.
  if [ ! -d "$VENV_DIR" ]; then
    echo -e "  ${CYAN}Creating venv at $VENV_DIR${NC}"
    python3 -m venv "$VENV_DIR" || {
      echo -e "  ${RED}✗${NC} Failed to create venv. Is python3-venv installed?"
      return 1
    }
  else
    echo -e "  ${YELLOW}~${NC} venv already exists at $VENV_DIR — reusing"
  fi

  # Fix ownership — when running under sudo, venv is created root-owned,
  # which breaks the user's later pip installs. Chown back to the invoking user.
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" "$VENV_DIR"
  fi

  VENV_PIP="$VENV_DIR/bin/pip"
  VENV_PY="$VENV_DIR/bin/python3"

  # Upgrade pip + wheel inside venv — old pip has dependency-resolver bugs.
  echo -e "  ${CYAN}Upgrading pip + wheel inside venv...${NC}"
  "$VENV_PY" -m pip install --upgrade pip wheel setuptools -q || {
    echo -e "  ${RED}✗${NC} pip upgrade failed"
    return 1
  }

  echo -e "  ${CYAN}Installing from $(basename "$REQ_FILE")...${NC}"
  "$VENV_PIP" install -r "$REQ_FILE" || {
    echo -e "  ${RED}✗${NC} pip install failed — see error above"
    return 1
  }

  # Optional iOS/macOS tools — don't fail the install if these don't build
  "$VENV_PIP" install pyidevice 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} pyidevice (optional iOS support)" || \
    echo -e "  ${YELLOW}~${NC} pyidevice skipped (optional)"

  # Re-fix ownership after pip writes new files as root
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" "$VENV_DIR"
  fi

  echo -e "  ${GREEN}✓${NC} Python deps installed into venv"
  echo -e "  ${CYAN}venv python:${NC} $VENV_PY"
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

# ── Step 3b: Knowledge-base submodules (opt-in via --with-submodules) ─────────
# ERR0RS ships with 75 knowledge submodules (BadUSB scripts, RF research,
# atomic-red-team, PyRIT, etc.) for the RAG knowledge base. By default we
# DO NOT clone them — they're large (multi-GB) and not all users need them.
# Pass --with-submodules to install.sh to pull them all.
init_submodules() {
  echo -e "\n${CYAN}[3b/5] Initializing knowledge-base submodules...${NC}"

  if [ "$WITH_SUBMODULES" != "true" ]; then
    DECLARED=$(grep -c "^\[submodule" "$SCRIPT_DIR/.gitmodules" 2>/dev/null || echo 0)
    echo -e "  ${YELLOW}~${NC} Skipped — ${DECLARED} knowledge submodules NOT cloned"
    echo -e "    To pull them all: ${CYAN}sudo bash install.sh --with-submodules${NC}"
    echo -e "    Or one-by-one:    ${CYAN}git submodule update --init <path>${NC}"
    return 0
  fi

  if [ ! -f "$SCRIPT_DIR/.gitmodules" ]; then
    echo -e "  ${YELLOW}~${NC} No .gitmodules file — skipping"
    return 0
  fi

  DECLARED=$(grep -c "^\[submodule" "$SCRIPT_DIR/.gitmodules")
  echo -e "  ${CYAN}Cloning $DECLARED knowledge submodules — this can take 10-30 min...${NC}"
  echo -e "  ${YELLOW}Network: $(du -sh ~/.cache 2>/dev/null | cut -f1) cache, expect multi-GB download${NC}"

  # Run as the invoking user so submodule clones land in their git config,
  # not /root's. Otherwise file ownership inside knowledge/ will be broken.
  cd "$SCRIPT_DIR"
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    sudo -u "$SUDO_USER" -H git submodule update --init --recursive --jobs 4 2>&1 | \
      grep -E "Cloning into|Submodule path|error|fatal" || true
  else
    git submodule update --init --recursive --jobs 4 2>&1 | \
      grep -E "Cloning into|Submodule path|error|fatal" || true
  fi

  # Quick verification — count what we actually got
  POPULATED=$(find "$SCRIPT_DIR/knowledge" -mindepth 2 -maxdepth 4 -type d -name ".git" 2>/dev/null | wc -l)
  echo -e "  ${GREEN}✓${NC} Submodules: $POPULATED/$DECLARED populated"

  if [ "$POPULATED" -lt "$DECLARED" ]; then
    MISSING=$((DECLARED - POPULATED))
    echo -e "  ${YELLOW}~${NC} $MISSING submodules failed to clone — likely network or repo issues"
    echo -e "    Retry later: ${CYAN}git submodule update --init --recursive${NC}"
  fi
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

  # Run dedicated desktop icon installer
  if [ -f "$SCRIPT_DIR/scripts/install_desktop_icon.sh" ]; then
    bash "$SCRIPT_DIR/scripts/install_desktop_icon.sh"
  else
    # Fallback if script not found
    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    mkdir -p "$DESKTOP_DIR"
    ICON_PATH="$SCRIPT_DIR/assets/icons/err0rs.png"
    [ ! -f "$ICON_PATH" ] && ICON_PATH="$SCRIPT_DIR/assets/icons/err0rs.svg"

    # Main ERR0RS launcher
    cat > "$DESKTOP_DIR/ERR0RS-Ultimate.desktop" << DEOF
[Desktop Entry]
Version=1.1
Type=Application
Name=ERR0RS Ultimate
GenericName=AI Penetration Testing Platform
Comment=AI-powered pentesting — MetasploitMCP | Kali 2026.1 | Local LLM
Exec=bash -c "cd $SCRIPT_DIR && bash start_err0rs.sh"
Icon=$ICON_PATH
Terminal=true
StartupNotify=true
Categories=Security;Network;System;
Keywords=pentest;hacking;metasploit;kali;offensive;ai;
DEOF
    chmod +x "$DESKTOP_DIR/ERR0RS-Ultimate.desktop"
    gio set "$DESKTOP_DIR/ERR0RS-Ultimate.desktop" metadata::trusted true 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Desktop shortcut created"

    # Prompt Manual launcher
    cat > "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop" << DEOF
[Desktop Entry]
Version=1.1
Type=Application
Name=ERR0RS Prompt Manual
GenericName=ERR0RS Prompting Guide
Comment=Interactive prompt instruction manual for ERR0RS-Ultimate
Exec=bash -c "cd $SCRIPT_DIR && bash open_manual.sh"
Icon=$ICON_PATH
Terminal=false
StartupNotify=true
Categories=Security;Documentation;
Keywords=pentest;prompting;manual;guide;err0rs;
DEOF
    chmod +x "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop"
    gio set "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop" metadata::trusted true 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Manual desktop icon created"
  fi

  # Add shell aliases
  if ! grep -q "ERR0RS" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# ERR0RS ULTIMATE" >> ~/.bashrc
    echo "alias errorz='cd $SCRIPT_DIR && bash start_err0rs.sh'" >> ~/.bashrc
    echo "alias errorz-cli='cd $SCRIPT_DIR && \"$SCRIPT_DIR/venv/bin/python3\" main.py'" >> ~/.bashrc
    echo "alias err0rs='cd $SCRIPT_DIR && bash start_err0rs.sh'" >> ~/.bashrc
    echo -e "  ${GREEN}✓${NC} Aliases added: errorz | err0rs | errorz-cli"
  fi
}

# ── Smoke Test ────────────────────────────────────────────────────────────────
smoke_test() {
  echo -e "\n${CYAN}Running quick smoke test...${NC}"
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$SCRIPT_DIR"

  # Prefer venv python if it exists; fall back to system python only if not
  VENV_PY="$SCRIPT_DIR/venv/bin/python3"
  if [ -x "$VENV_PY" ]; then
    PYBIN="$VENV_PY"
    echo -e "  ${CYAN}Using venv python: $PYBIN${NC}"
  else
    PYBIN="python3"
    echo -e "  ${YELLOW}~${NC} venv not found — falling back to system python3"
  fi

  "$PYBIN" -c "
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

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
  cat << USAGE
ERR0RS Ultimate Installer

Usage:
  sudo bash install.sh [OPTIONS]

Options:
  --with-submodules      Clone all 75 knowledge-base submodules (badusb,
                         atomic-red-team, PyRIT, etc.). Adds 10-30 min and
                         multi-GB of disk. Off by default.
  --skip-go-tools        Skip Go-based tool installation (dalfox, katana,
                         httpx, naabu, gau, waybackurls, etc.). Use this
                         if you have a slow connection or no internet.
  --skip-ollama          Skip Ollama install + model pull. Useful if you
                         already have it running, or you're not using local LLM.
  -h, --help             Show this help and exit.

Examples:
  sudo bash install.sh
  sudo bash install.sh --with-submodules
  sudo bash install.sh --skip-go-tools --skip-ollama
USAGE
}

# ── CLI parser ────────────────────────────────────────────────────────────────
parse_args() {
  WITH_SUBMODULES="false"
  SKIP_GO_TOOLS="false"
  SKIP_OLLAMA="false"

  while [ $# -gt 0 ]; do
    case "$1" in
      --with-submodules)  WITH_SUBMODULES="true";  shift ;;
      --skip-go-tools)    SKIP_GO_TOOLS="true";    shift ;;
      --skip-ollama)      SKIP_OLLAMA="true";      shift ;;
      -h|--help)          usage; exit 0 ;;
      *)                  echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  # Parse CLI args first so flags are set before anything else runs.
  parse_args "$@"

  # Resolve script directory once at top level — used by find, setup_env, setup_desktop
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  detect_distro
  banner

  # Ensure all shell scripts are executable after Windows clone (CRLF strip)
  echo -e "${CYAN}[*] Fixing script permissions...${NC}"
  find "$SCRIPT_DIR" -maxdepth 2 -name "*.sh" -exec chmod +x {} \;
  echo -e "  ${GREEN}✓${NC} All .sh scripts made executable"

  # Show what we're going to do
  echo -e "${CYAN}[*] Install plan:${NC}"
  echo -e "    Submodules:  ${WITH_SUBMODULES}"
  echo -e "    Go tools:    $([ "$SKIP_GO_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Ollama:      $([ "$SKIP_OLLAMA" = "true" ] && echo "skip" || echo "install")"

  # Check if running as root for system installs
  if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}[!] Not running as root — skipping system package install${NC}"
    echo -e "    For full install run: ${CYAN}sudo bash install.sh${NC}\n"
    install_python_deps
    init_submodules
    setup_env
    setup_desktop
    smoke_test
  else
    install_system_deps
    [ "$SKIP_GO_TOOLS" != "true" ] && install_go_tools
    install_python_deps
    [ "$SKIP_OLLAMA" != "true" ] && install_ollama
    init_submodules
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
  if [ "$WITH_SUBMODULES" != "true" ]; then
    echo -e "${YELLOW}  NOTE: Knowledge base submodules are NOT cloned by default.${NC}"
    echo -e "  To pull all KB repos (research/tools), re-run with:"
    echo -e "  ${CYAN}sudo bash install.sh --with-submodules${NC}"
    echo -e "  (Warning: some repos are large — allow 10-30 min on first clone)"
    echo ""
  fi
}

# ── Entry Point ───────────────────────────────────────────────────────────────
main "$@"
