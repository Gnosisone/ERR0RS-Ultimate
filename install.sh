#!/usr/bin/env bash
# =============================================================================
# ERR0RS ULTIMATE - Universal Installer
# Supports: Kali Linux, Parrot OS, Ubuntu, Debian
# Author: Gary Holden Schneider (Eros) | GitHub: Gnosisone
# Usage: sudo bash install.sh [OPTIONS]
# =============================================================================

set -e
CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
PURPLE='\033[0;35m'; RED='\033[0;31m'; NC='\033[0m'

# Resolve script directory ONCE at the top — used by every function
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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
  SEC_PKGS="nmap hydra hashcat aircrack-ng sqlmap nikto"

  # Optional Kali/Parrot tools — ERR0RS kill chain expects these.
  # Most ship pre-installed on Kali full; not on Kali light or non-Kali distros.
  # Forgiving loop below — '✓' if it installs, '~' if not available.
  OPT_PKGS="gobuster amass nuclei whatweb wpscan ffuf feroxbuster \
    theharvester subfinder dirb wordlists commix xsser \
    crackmapexec enum4linux responder bettercap evil-winrm \
    impacket-scripts dnsenum dnsrecon onesixtyone snmp-check \
    ldap-utils smbclient smbmap \
    zmap beef-xss ropgadget king-phisher cupp python3-pwntools \
    trufflehog scrcpy seclists exploitdb"

  # Metasploit — installed differently on Parrot vs Kali
  if [[ "$DISTRO_ID" == "kali" ]]; then
    MSF_PKG="metasploit-framework"
  elif [[ "$DISTRO_ID" == "parrot" ]] || [[ "$DISTRO_ID" == "parrotsec" ]]; then
    MSF_PKG="metasploit-framework"
  else
    MSF_PKG=""
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
install_go_tools() {
  echo -e "\n${CYAN}[1b/5] Installing Go-based security tools...${NC}"

  if ! command -v go &>/dev/null; then
    echo -e "  ${YELLOW}Go not found — installing golang...${NC}"
    apt install -y golang-go 2>/dev/null || {
      echo -e "  ${YELLOW}~${NC} golang-go install failed — skipping Go tools"
      return 0
    }
  fi
  GOPATH_BIN="$(go env GOPATH 2>/dev/null)/bin"
  [ -z "$GOPATH_BIN" ] && GOPATH_BIN="/root/go/bin"
  echo -e "  ${GREEN}✓${NC} Go: $(go version | awk '{print $3}')"

  GO_TOOLS=(
    "dalfox|github.com/hahwul/dalfox/v2@latest"
    "katana|github.com/projectdiscovery/katana/cmd/katana@latest"
    "httpx|github.com/projectdiscovery/httpx/cmd/httpx@latest"
    "naabu|github.com/projectdiscovery/naabu/v2/cmd/naabu@latest"
    "gau|github.com/lc/gau/v2/cmd/gau@latest"
    "waybackurls|github.com/tomnomnom/waybackurls@latest"
    "assetfinder|github.com/tomnomnom/assetfinder@latest"
    "gf|github.com/tomnomnom/gf@latest"
    "unfurl|github.com/tomnomnom/unfurl@latest"
    "anew|github.com/tomnomnom/anew@latest"
    "qsreplace|github.com/tomnomnom/qsreplace@latest"
    "interactsh-client|github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest"
    "gitleaks|github.com/gitleaks/gitleaks/v8@latest"
  )

  for entry in "${GO_TOOLS[@]}"; do
    bin_name="${entry%%|*}"
    module="${entry##*|}"
    if command -v "$bin_name" &>/dev/null; then
      echo -e "  ${YELLOW}~${NC} $bin_name already present at $(command -v "$bin_name") — skipping"
      continue
    fi
    echo -e "  Installing $bin_name from $module..."
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      sudo -u "$SUDO_USER" -H bash -c "go install $module" 2>&1 | tail -3 || {
        echo -e "  ${YELLOW}~${NC} $bin_name install failed (continuing)"
        continue
      }
      USER_GOBIN="$(getent passwd "$SUDO_USER" | cut -d: -f6)/go/bin"
      if [ -f "$USER_GOBIN/$bin_name" ]; then
        ln -sf "$USER_GOBIN/$bin_name" "/usr/local/bin/$bin_name"
        echo -e "  ${GREEN}✓${NC} $bin_name → /usr/local/bin/$bin_name"
      else
        echo -e "  ${YELLOW}~${NC} $bin_name compiled but not found at $USER_GOBIN"
      fi
    else
      go install "$module" 2>&1 | tail -3 || {
        echo -e "  ${YELLOW}~${NC} $bin_name install failed (continuing)"
        continue
      }
      if [ -f "$GOPATH_BIN/$bin_name" ]; then
        ln -sf "$GOPATH_BIN/$bin_name" "/usr/local/bin/$bin_name"
        echo -e "  ${GREEN}✓${NC} $bin_name → /usr/local/bin/$bin_name"
      else
        echo -e "  ${YELLOW}~${NC} $bin_name not at $GOPATH_BIN"
      fi
    fi
  done
  echo -e "  ${GREEN}Go tools done${NC}"
}

# ── Step 1c: pip-installed security tools ─────────────────────────────────────
install_pip_tools() {
  echo -e "\n${CYAN}[1c/5] Installing pip-based security tools...${NC}"

  USE_PIPX="false"
  if command -v pipx &>/dev/null; then
    USE_PIPX="true"
    echo -e "  ${GREEN}✓${NC} Using pipx (isolated per-tool venvs)"
  else
    echo -e "  ${CYAN}Installing pipx for isolated CLI tool installs...${NC}"
    apt install -y pipx 2>/dev/null && USE_PIPX="true"
    if [ "$USE_PIPX" = "true" ] && [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      sudo -u "$SUDO_USER" -H pipx ensurepath 2>/dev/null || true
    fi
  fi

  PIP_TOOLS=(
    "droopescan|pypi|droopescan"
    "uro|pypi|uro"
    "graphqlmap|pypi|graphqlmap"
    "corsy|git|https://github.com/s0md3v/Corsy.git"
    "jwt_tool|git|https://github.com/ticarpi/jwt_tool.git"
    "graphw00f|git|https://github.com/dolevf/graphw00f.git"
    "ssrfmap|git|https://github.com/swisskyrepo/SSRFmap.git"
    "nosqlmap|git|https://github.com/codingo/NoSQLMap.git"
  )

  for entry in "${PIP_TOOLS[@]}"; do
    IFS='|' read -r name kind spec <<< "$entry"
    if command -v "$name" &>/dev/null; then
      echo -e "  ${YELLOW}~${NC} $name already on PATH — skipping"
      continue
    fi
    if [ "$kind" = "pypi" ]; then
      pipx_out=$(mktemp)
      if [ "$USE_PIPX" = "true" ] && [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        sudo -u "$SUDO_USER" -H pipx install "$spec" > "$pipx_out" 2>&1; rc=$?
      elif [ "$USE_PIPX" = "true" ]; then
        pipx install "$spec" > "$pipx_out" 2>&1; rc=$?
      else
        pip3 install --break-system-packages "$spec" > "$pipx_out" 2>&1; rc=$?
      fi
      if [ "$rc" -eq 0 ] || command -v "$name" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
      else
        echo -e "  ${YELLOW}~${NC} $name failed (continuing)"
        tail -3 "$pipx_out" | sed 's/^/      /'
      fi
      rm -f "$pipx_out"
    else
      target_dir="/opt/$name"
      if [ -d "$target_dir/.git" ]; then
        echo -e "  ${YELLOW}~${NC} $name already cloned — pulling"
        (cd "$target_dir" && git pull --quiet 2>/dev/null) || true
      else
        git clone --quiet --depth 1 "$spec" "$target_dir" 2>&1 | tail -2 || {
          echo -e "  ${YELLOW}~${NC} $name clone failed (continuing)"; continue
        }
      fi
      if [ -f "$target_dir/requirements.txt" ]; then
        python3 -m venv "$target_dir/.venv" 2>/dev/null
        "$target_dir/.venv/bin/pip" install -q -r "$target_dir/requirements.txt" 2>/dev/null || true
      fi
      main_script=""
      for candidate in "${name}.py" "main.py" "${name^}.py" "${name^^}.py" "cli.py"; do
        if [ -f "$target_dir/$candidate" ]; then
          main_script="$target_dir/$candidate"; break
        fi
      done
      if [ -n "$main_script" ]; then
        chmod +x "$main_script" 2>/dev/null
        cat > "/usr/local/bin/$name" << WRAPPER
#!/usr/bin/env bash
TOOL_DIR="$target_dir"
if [ -d "\$TOOL_DIR/.venv" ]; then
  exec "\$TOOL_DIR/.venv/bin/python3" "$main_script" "\$@"
else
  exec python3 "$main_script" "\$@"
fi
WRAPPER
        chmod +x "/usr/local/bin/$name"
        echo -e "  ${GREEN}✓${NC} $name → /usr/local/bin/$name"
      else
        echo -e "  ${YELLOW}~${NC} $name cloned but no main script auto-detected"
      fi
      if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        chown -R "$SUDO_USER":"$SUDO_USER" "$target_dir" 2>/dev/null || true
      fi
    fi
  done
  echo -e "  ${GREEN}pip tools done${NC}"
}

# ── Step 1d: Github-cloned tools ──────────────────────────────────────────────
install_github_tools() {
  echo -e "\n${CYAN}[1d/5] Installing github-cloned security tools...${NC}"
  mkdir -p /opt; cd /opt
  GH_TOOLS=(
    "Sn1per|https://github.com/1N3/Sn1per.git|install.sh|sniper-install"
    "AutoSploit|https://github.com/NullArray/AutoSploit.git|autosploit.py|autosploit"
    "LinkFinder|https://github.com/GerbenJavado/LinkFinder.git|linkfinder.py|linkfinder"
    "SecretFinder|https://github.com/m4ll0k/SecretFinder.git|SecretFinder.py|secretfinder"
  )
  for entry in "${GH_TOOLS[@]}"; do
    IFS='|' read -r name repo script symlink <<< "$entry"
    target_dir="/opt/$name"
    if [ -d "$target_dir/.git" ]; then
      echo -e "  ${YELLOW}~${NC} $name already cloned at $target_dir — pulling latest"
      (cd "$target_dir" && git pull --quiet 2>/dev/null) || true
    else
      echo -e "  ${CYAN}Cloning $name...${NC}"
      git clone --quiet --depth 1 "$repo" "$target_dir" 2>&1 | tail -3 || {
        echo -e "  ${YELLOW}~${NC} $name clone failed — skipping"; continue
      }
    fi
    if [ -f "$target_dir/$script" ]; then
      chmod +x "$target_dir/$script" 2>/dev/null || true
      ln -sf "$target_dir/$script" "/usr/local/bin/$symlink"
      echo -e "  ${GREEN}✓${NC} $name → /usr/local/bin/$symlink"
    else
      echo -e "  ${YELLOW}~${NC} $name: entry script $script not found"
    fi
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      chown -R "$SUDO_USER":"$SUDO_USER" "$target_dir" 2>/dev/null || true
    fi
  done
  cd - > /dev/null
  echo -e "  ${GREEN}Github tools done${NC}"
}

# ── Step 1e: C2 Frameworks (opt-in via --with-c2) ─────────────────────────────
install_c2_frameworks() {
  echo -e "\n${CYAN}[1e/5] Installing C2 frameworks (--with-c2)...${NC}"
  echo -e "  ${YELLOW}This will pull multi-GB of binaries. Be patient.${NC}"
  mkdir -p /opt; cd /opt

  if ! command -v sliver-client &>/dev/null; then
    echo -e "  ${CYAN}Installing Sliver C2...${NC}"
    curl -sSL https://sliver.sh/install 2>/dev/null | bash 2>&1 | tail -3 && \
      echo -e "  ${GREEN}✓${NC} sliver installed" || \
      echo -e "  ${YELLOW}~${NC} sliver install failed"
  else
    echo -e "  ${YELLOW}~${NC} sliver already installed"
  fi

  if [ ! -d /opt/Merlin ]; then
    git clone --quiet --depth 1 https://github.com/Ne0nd0g/merlin.git /opt/Merlin 2>&1 | tail -2 || true
    [ -d /opt/Merlin ] && echo -e "  ${GREEN}✓${NC} merlin → /opt/Merlin" || echo -e "  ${YELLOW}~${NC} merlin clone failed"
  fi

  if [ ! -d /opt/PoshC2 ]; then
    curl -sSL https://raw.githubusercontent.com/nettitude/PoshC2/master/Install.sh 2>/dev/null | bash 2>&1 | tail -3 || true
    [ -d /opt/PoshC2 ] && echo -e "  ${GREEN}✓${NC} poshc2 → /opt/PoshC2" || echo -e "  ${YELLOW}~${NC} poshc2 install failed"
  fi

  if ! command -v powershell-empire &>/dev/null && [ ! -d /opt/Empire ]; then
    apt install -y powershell-empire 2>/dev/null && echo -e "  ${GREEN}✓${NC} empire (apt)" || {
      git clone --quiet --depth 1 https://github.com/BC-SECURITY/Empire.git /opt/Empire 2>&1 | tail -2 || true
      [ -d /opt/Empire ] && echo -e "  ${GREEN}✓${NC} empire → /opt/Empire" || echo -e "  ${YELLOW}~${NC} empire install failed"
    }
  fi

  if [ ! -d /opt/Covenant ]; then
    git clone --quiet --recurse-submodules --depth 1 https://github.com/cobbr/Covenant.git /opt/Covenant 2>&1 | tail -2 || true
    [ -d /opt/Covenant ] && echo -e "  ${GREEN}✓${NC} covenant → /opt/Covenant" || echo -e "  ${YELLOW}~${NC} covenant clone failed"
  fi

  if [ ! -d /opt/Mythic ]; then
    git clone --quiet --depth 1 https://github.com/its-a-feature/Mythic.git /opt/Mythic 2>&1 | tail -2 || true
    [ -d /opt/Mythic ] && echo -e "  ${GREEN}✓${NC} mythic → /opt/Mythic" || echo -e "  ${YELLOW}~${NC} mythic clone failed"
  fi

  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    for d in Merlin PoshC2 Empire Covenant Mythic; do
      [ -d "/opt/$d" ] && chown -R "$SUDO_USER":"$SUDO_USER" "/opt/$d" 2>/dev/null || true
    done
  fi
  cd - > /dev/null
  echo -e "  ${GREEN}C2 frameworks done${NC}"
  echo -e "  ${YELLOW}Note: most C2s need additional setup (db init, dotnet build, docker images). See each repo's README.${NC}"
}

# ── Step 1f: Knowledge-base reference repos ───────────────────────────────────
init_knowledge_repos() {
  echo -e "\n${CYAN}[1f/5] Cloning reference repos for RAG knowledge base...${NC}"

  if [ "$WITH_KNOWLEDGE_REPOS" != "true" ]; then
    echo -e "  ${YELLOW}~${NC} Skipped — Windows-side reference repos NOT cloned"
    echo -e "    To clone them: ${CYAN}sudo bash install.sh --with-knowledge-repos${NC}"
    return 0
  fi

  KB_DIR="$SCRIPT_DIR/knowledge_repos"
  mkdir -p "$KB_DIR"; cd "$KB_DIR"
  KB_REPOS=(
    "GTFOBins|https://github.com/GTFOBins/GTFOBins.github.io.git"
    "LOLBAS|https://github.com/LOLBAS-Project/LOLBAS.git"
    "PowerSploit|https://github.com/PowerShellMafia/PowerSploit.git"
    "Watson|https://github.com/rasta-mouse/Watson.git"
    "Beroot|https://github.com/AlessandroZ/BeRoot.git"
    "windows-exploit-suggester|https://github.com/AonCyberLabs/Windows-Exploit-Suggester.git"
    "PrivescCheck|https://github.com/itm4n/PrivescCheck.git"
    "PayloadsAllTheThings|https://github.com/swisskyrepo/PayloadsAllTheThings.git"
    "HackTricks|https://github.com/HackTricks-wiki/hacktricks.git"
  )
  for entry in "${KB_REPOS[@]}"; do
    name="${entry%%|*}"; repo="${entry##*|}"; target="$KB_DIR/$name"
    if [ -d "$target/.git" ]; then
      echo -e "  ${YELLOW}~${NC} $name already cloned — pulling"
      (cd "$target" && git pull --quiet 2>/dev/null) || true
    else
      echo -e "  ${CYAN}Cloning $name...${NC}"
      git clone --quiet --depth 1 "$repo" "$target" 2>&1 | tail -2 && \
        echo -e "  ${GREEN}✓${NC} $name" || echo -e "  ${YELLOW}~${NC} $name clone failed"
    fi
  done
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" "$KB_DIR" 2>/dev/null || true
  fi
  cd - > /dev/null
  echo -e "  ${GREEN}Knowledge repos ready at $KB_DIR${NC}"
  echo -e "  ${CYAN}Run RAG indexer to make these searchable.${NC}"
}

# ── Step 2: Python Dependencies ───────────────────────────────────────────────
install_python_deps() {
  echo -e "\n${CYAN}[2/5] Installing Python dependencies (venv)...${NC}"
  VENV_DIR="$SCRIPT_DIR/venv"
  if [ ! -d "$VENV_DIR" ]; then
    echo -e "  Creating venv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      chown -R "$SUDO_USER":"$SUDO_USER" "$VENV_DIR"
    fi
  else
    echo -e "  ${YELLOW}~${NC} venv already exists at $VENV_DIR — reusing"
  fi
  PIP="$VENV_DIR/bin/pip"; PY="$VENV_DIR/bin/python3"
  echo -e "  Upgrading pip + wheel inside venv..."
  "$PIP" install -q --upgrade pip wheel setuptools 2>&1 | tail -2 || true
  REQ_FILE=""
  if [ -f "$SCRIPT_DIR/requirements-kali.txt" ]; then
    REQ_FILE="$SCRIPT_DIR/requirements-kali.txt"
  elif [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    REQ_FILE="$SCRIPT_DIR/requirements.txt"
  fi
  if [ -n "$REQ_FILE" ]; then
    echo -e "  Installing from $(basename "$REQ_FILE")..."
    "$PIP" install -r "$REQ_FILE" 2>&1 | tail -5 || \
      echo -e "  ${YELLOW}~${NC} Some packages failed — continuing"
  else
    echo -e "  ${YELLOW}~${NC} No requirements file — installing core deps inline"
    "$PIP" install -q requests fastapi uvicorn pydantic anthropic openai \
      chromadb sentence-transformers psutil python-dotenv rich click 2>&1 | tail -3 || true
  fi
  "$PIP" install pyidevice 2>/dev/null && \
    echo -e "  ${GREEN}✓${NC} pyidevice (optional iOS support)" || true
  echo -e "  ${GREEN}✓${NC} Python deps installed into venv"
  echo -e "  ${CYAN}venv python:${NC} $PY"
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
  if ! pgrep -x "ollama" >/dev/null; then
    ollama serve &>/dev/null & sleep 3
  fi
  if [[ "$ARCH" == "aarch64" ]]; then
    MODEL="llama3.2"
  else
    MODEL="${OLLAMA_MODEL:-llama3.2}"
  fi
  echo -e "  Pulling model: ${CYAN}$MODEL${NC} (this takes a few minutes first time)..."
  ollama pull "$MODEL" && echo -e "  ${GREEN}✓${NC} $MODEL ready" || \
    echo -e "  ${YELLOW}~${NC} Pull failed — start Ollama manually: ollama pull $MODEL"
}

# ── Step 3b: Knowledge-base submodules (opt-in via --with-submodules) ─────────
init_submodules() {
  echo -e "\n${CYAN}[3b/5] Initializing knowledge-base submodules...${NC}"
  if [ "$WITH_SUBMODULES" != "true" ]; then
    echo -e "  ${YELLOW}~${NC} Skipped — 75 knowledge submodules NOT cloned"
    echo -e "    To pull them all: ${CYAN}sudo bash install.sh --with-submodules${NC}"
    echo -e "    Or one-by-one:    ${CYAN}git submodule update --init <path>${NC}"
    return 0
  fi
  cd "$SCRIPT_DIR"
  echo -e "  ${CYAN}Cloning all submodules (this is the slow part — 10-30 min)...${NC}"
  git submodule update --init --recursive --depth 1 2>&1 | \
    grep -E "Submodule|Cloning" | head -20 || true
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$SUDO_USER":"$SUDO_USER" "$SCRIPT_DIR" 2>/dev/null || true
  fi
  echo -e "  ${GREEN}✓${NC} Submodules initialized"
}

# ── Step 4: Environment Config ────────────────────────────────────────────────
setup_env() {
  echo -e "\n${CYAN}[4/5] Creating .env config...${NC}"
  ENV_FILE="$SCRIPT_DIR/.env"
  if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
# ERR0RS ULTIMATE — Environment Config
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
LLM_BACKEND=ollama
OLLAMA_MODEL=$MODEL
OLLAMA_HOST=http://localhost:11434
DB_URL=postgresql://errorz:err0rs_secure@localhost/errorz
REDIS_URL=redis://localhost:6379
UI_HOST=127.0.0.1
UI_PORT=8765
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "changeme_$(date +%s)")
HAILO_ENABLED=false
PI5_MODE=false
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
  if [ -f "$SCRIPT_DIR/scripts/install_desktop_icon.sh" ]; then
    bash "$SCRIPT_DIR/scripts/install_desktop_icon.sh"
  else
    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    mkdir -p "$DESKTOP_DIR"
    ICON_PATH="$SCRIPT_DIR/assets/icons/err0rs.png"
    [ ! -f "$ICON_PATH" ] && ICON_PATH="$SCRIPT_DIR/assets/icons/err0rs.svg"
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

  if ! grep -q "ERR0RS" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# ERR0RS ULTIMATE" >> ~/.bashrc
    echo "alias errorz='cd $SCRIPT_DIR && bash start_err0rs.sh'" >> ~/.bashrc
    echo "alias errorz-cli='cd $SCRIPT_DIR && python3 main.py'" >> ~/.bashrc
    echo "alias err0rs='cd $SCRIPT_DIR && bash start_err0rs.sh'" >> ~/.bashrc
    echo -e "  ${GREEN}✓${NC} Aliases added: errorz | err0rs | errorz-cli"
  fi
}

# ── Smoke Test ────────────────────────────────────────────────────────────────
smoke_test() {
  echo -e "\n${CYAN}Running quick smoke test...${NC}"
  cd "$SCRIPT_DIR"
  PY="python3"
  if [ -x "$SCRIPT_DIR/venv/bin/python3" ]; then
    PY="$SCRIPT_DIR/venv/bin/python3"
    echo -e "  Using venv python: $PY"
  fi
  "$PY" -c "
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
                         atomic-red-team, PyRIT, etc.). Adds 10-30 min.
  --with-c2              Install C2 frameworks: empire, sliver, covenant,
                         merlin, poshc2, mythic. Heavy install — multi-GB.
  --with-knowledge-repos Clone Windows-side reference repos (GTFOBins, LOLBAS,
                         PowerSploit, etc.) for RAG indexing.
  --skip-go-tools        Skip Go-based tool installation.
  --skip-pip-tools       Skip pip-installed security tools.
  --skip-github-tools    Skip github-clone tools.
  --skip-ollama          Skip Ollama install + model pull.
  -h, --help             Show this help and exit.

Examples:
  sudo bash install.sh                            # Default install
  sudo bash install.sh --with-c2                  # + C2 frameworks
  sudo bash install.sh --with-knowledge-repos     # + Windows-side reference repos
  sudo bash install.sh --with-submodules --with-c2 --with-knowledge-repos  # FULL
  sudo bash install.sh --skip-go-tools --skip-ollama                       # MINIMAL
USAGE
}

# ── CLI parser ────────────────────────────────────────────────────────────────
parse_args() {
  WITH_SUBMODULES="false"
  WITH_C2="false"
  WITH_KNOWLEDGE_REPOS="false"
  SKIP_GO_TOOLS="false"
  SKIP_PIP_TOOLS="false"
  SKIP_GITHUB_TOOLS="false"
  SKIP_OLLAMA="false"
  while [ $# -gt 0 ]; do
    case "$1" in
      --with-submodules)      WITH_SUBMODULES="true";       shift ;;
      --with-c2)              WITH_C2="true";               shift ;;
      --with-knowledge-repos) WITH_KNOWLEDGE_REPOS="true";  shift ;;
      --skip-go-tools)        SKIP_GO_TOOLS="true";         shift ;;
      --skip-pip-tools)       SKIP_PIP_TOOLS="true";        shift ;;
      --skip-github-tools)    SKIP_GITHUB_TOOLS="true";     shift ;;
      --skip-ollama)          SKIP_OLLAMA="true";           shift ;;
      -h|--help)              usage; exit 0 ;;
      *)                      echo "Unknown option: $1"; usage; exit 1 ;;
    esac
  done
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
  parse_args "$@"
  detect_distro
  banner

  echo -e "${CYAN}[*] Fixing script permissions...${NC}"
  find "$SCRIPT_DIR" -maxdepth 2 -name "*.sh" -exec chmod +x {} \;
  echo -e "  ${GREEN}✓${NC} All .sh scripts made executable"

  echo -e "${CYAN}[*] Install plan:${NC}"
  echo -e "    Submodules:      ${WITH_SUBMODULES}"
  echo -e "    C2 frameworks:   ${WITH_C2}"
  echo -e "    Knowledge repos: ${WITH_KNOWLEDGE_REPOS}"
  echo -e "    Go tools:        $([ "$SKIP_GO_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Pip tools:       $([ "$SKIP_PIP_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Github tools:    $([ "$SKIP_GITHUB_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Ollama:          $([ "$SKIP_OLLAMA" = "true" ] && echo "skip" || echo "install")"

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
    [ "$SKIP_GO_TOOLS"     != "true" ] && install_go_tools
    [ "$SKIP_PIP_TOOLS"    != "true" ] && install_pip_tools
    [ "$SKIP_GITHUB_TOOLS" != "true" ] && install_github_tools
    [ "$WITH_C2"           = "true"  ] && install_c2_frameworks
    init_knowledge_repos
    install_python_deps
    [ "$SKIP_OLLAMA"       != "true" ] && install_ollama
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
  echo -e "${YELLOW}  NOTE: Knowledge base submodules are NOT cloned by default.${NC}"
  echo -e "  To pull all KB repos (research/tools), re-run with:"
  echo -e "  ${CYAN}sudo bash install.sh --with-submodules${NC}"
  echo -e "  (Warning: some repos are large — allow 10-30 min on first clone)"
  echo ""
}

main "$@"
