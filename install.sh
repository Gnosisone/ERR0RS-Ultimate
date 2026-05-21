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
    ldap-utils smbclient smbmap \
    zmap beef-xss ropgadget king-phisher cupp python3-pwntools \
    trufflehog scrcpy seclists exploitdb"

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
    "unfurl|github.com/tomnomnom/unfurl@latest"
    "anew|github.com/tomnomnom/anew@latest"
    "qsreplace|github.com/tomnomnom/qsreplace@latest"
    "interactsh-client|github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest"
    "gitleaks|github.com/gitleaks/gitleaks/v8@latest"
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

# ── Step 1c: pip-installed security tools ─────────────────────────────────────
# Tools that ship via pip, not apt or go. Installed system-wide into a dedicated
# pipx-style location so they're on PATH without polluting venvs.
# Uses --break-system-packages on the SYSTEM python (NOT our venv) — these are
# CLI utilities, not Python libraries to import.
install_pip_tools() {
  echo -e "\n${CYAN}[1c/5] Installing pip-based security tools...${NC}"

  # Use pipx if available — it isolates each tool. Fall back to system pip
  # with --break-system-packages (the only legal pip-as-root option on Kali).
  USE_PIPX="false"
  if command -v pipx &>/dev/null; then
    USE_PIPX="true"
    echo -e "  ${GREEN}✓${NC} Using pipx (isolated per-tool venvs)"
  else
    echo -e "  ${CYAN}Installing pipx for isolated CLI tool installs...${NC}"
    apt install -y pipx 2>/dev/null && USE_PIPX="true"
    if [ "$USE_PIPX" = "true" ]; then
      # Ensure pipx bin dir is on PATH for the invoking user
      if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        sudo -u "$SUDO_USER" -H pipx ensurepath 2>/dev/null || true
      fi
    fi
  fi

  # PIP_TOOLS: format "name|spec_type|spec"
  # spec_type: "pypi" = real package on PyPI, install by name
  #            "git"  = github repo; we clone to /opt/<name> and pipx install ./path
  # Why two paths? pipx install git+https://… only works when the repo has a
  # pyproject.toml or setup.py. Many security tools are loose scripts without
  # proper packaging, so we clone-and-symlink them instead.
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
      # Real PyPI package — pipx handles it cleanly.
      # Capture output silently; only show it on failure.
      pipx_out=$(mktemp)
      if [ "$USE_PIPX" = "true" ] && [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        sudo -u "$SUDO_USER" -H pipx install "$spec" > "$pipx_out" 2>&1
        rc=$?
      elif [ "$USE_PIPX" = "true" ]; then
        pipx install "$spec" > "$pipx_out" 2>&1
        rc=$?
      else
        pip3 install --break-system-packages "$spec" > "$pipx_out" 2>&1
        rc=$?
      fi

      # pipx returns nonzero when package is already installed via stderr message,
      # but the tool is still callable. Check the actual binary instead.
      if [ "$rc" -eq 0 ] || command -v "$name" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
      else
        echo -e "  ${YELLOW}~${NC} $name failed (continuing)"
        tail -3 "$pipx_out" | sed 's/^/      /'
      fi
      rm -f "$pipx_out"

    else
      # git source — clone to /opt, install requirements.txt, symlink main script
      target_dir="/opt/$name"
      if [ -d "$target_dir/.git" ]; then
        echo -e "  ${YELLOW}~${NC} $name already cloned at $target_dir — pulling"
        (cd "$target_dir" && git pull --quiet 2>/dev/null) || true
      else
        git clone --quiet --depth 1 "$spec" "$target_dir" 2>&1 | tail -2 || {
          echo -e "  ${YELLOW}~${NC} $name clone failed (continuing)"
          continue
        }
      fi

      # Install requirements.txt if present, inside a per-tool venv at /opt/<name>/.venv
      if [ -f "$target_dir/requirements.txt" ]; then
        python3 -m venv "$target_dir/.venv" 2>/dev/null
        "$target_dir/.venv/bin/pip" install -q -r "$target_dir/requirements.txt" 2>/dev/null || true
      fi

      # Find the main script — common names per tool
      main_script=""
      for candidate in "${name}.py" "main.py" "${name^}.py" "${name^^}.py" "cli.py"; do
        if [ -f "$target_dir/$candidate" ]; then
          main_script="$target_dir/$candidate"; break
        fi
      done

      if [ -n "$main_script" ]; then
        chmod +x "$main_script" 2>/dev/null
        # Wrapper script that activates the per-tool venv (if it exists) then runs
        cat > "/usr/local/bin/$name" << WRAPPER
#!/usr/bin/env bash
# ERR0RS auto-generated wrapper for $name
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

      # Chown back to user
      if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
        chown -R "$SUDO_USER":"$SUDO_USER" "$target_dir" 2>/dev/null || true
      fi
    fi
  done

  echo -e "  ${GREEN}pip tools done${NC}"
}

# ── Step 1d: Github-cloned tools (no package, just scripts) ───────────────────
# Tools that live as a github repo with no pip/apt distribution. We clone to
# /opt/<tool> and symlink the entry script into /usr/local/bin.
install_github_tools() {
  echo -e "\n${CYAN}[1d/5] Installing github-cloned security tools...${NC}"

  mkdir -p /opt
  cd /opt

  # GH_TOOLS: format "name|repo_url|entry_script_relative_path|symlink_name"
  # entry_script is the file in the cloned dir to symlink. symlink_name is
  # what the user types to run it (added to /usr/local/bin).
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
        echo -e "  ${YELLOW}~${NC} $name clone failed — skipping"
        continue
      }
    fi

    # Make the entry script executable + symlink it
    if [ -f "$target_dir/$script" ]; then
      chmod +x "$target_dir/$script" 2>/dev/null || true
      ln -sf "$target_dir/$script" "/usr/local/bin/$symlink"
      echo -e "  ${GREEN}✓${NC} $name → /usr/local/bin/$symlink"
    else
      echo -e "  ${YELLOW}~${NC} $name: entry script $script not found"
    fi

    # Chown to invoking user so they can update later without sudo
    if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
      chown -R "$SUDO_USER":"$SUDO_USER" "$target_dir" 2>/dev/null || true
    fi
  done

  cd - > /dev/null
  echo -e "  ${GREEN}Github tools done${NC}"
}

# ── Step 1e: C2 Frameworks (opt-in via --with-c2) ─────────────────────────────
# Big installs. Sliver, Merlin, PoshC2, etc. Each gets its own /opt dir.
install_c2_frameworks() {
  echo -e "\n${CYAN}[1e/5] Installing C2 frameworks (--with-c2)...${NC}"
  echo -e "  ${YELLOW}This will pull multi-GB of binaries. Be patient.${NC}"

  mkdir -p /opt
  cd /opt

  # ── Sliver ── (Go, official install script)
  if ! command -v sliver-client &>/dev/null; then
    echo -e "  ${CYAN}Installing Sliver C2...${NC}"
    curl -sSL https://sliver.sh/install 2>/dev/null | bash 2>&1 | tail -3 && \
      echo -e "  ${GREEN}✓${NC} sliver installed" || \
      echo -e "  ${YELLOW}~${NC} sliver install failed"
  else
    echo -e "  ${YELLOW}~${NC} sliver already installed"
  fi

  # ── Merlin ── (Go, github releases)
  if [ ! -d /opt/Merlin ]; then
    echo -e "  ${CYAN}Cloning Merlin C2 server...${NC}"
    git clone --quiet --depth 1 https://github.com/Ne0nd0g/merlin.git /opt/Merlin 2>&1 | tail -2 || true
    [ -d /opt/Merlin ] && echo -e "  ${GREEN}✓${NC} merlin → /opt/Merlin" || \
      echo -e "  ${YELLOW}~${NC} merlin clone failed"
  else
    echo -e "  ${YELLOW}~${NC} merlin already at /opt/Merlin"
  fi

  # ── PoshC2 ── (PowerShell C2, official installer)
  if [ ! -d /opt/PoshC2 ]; then
    echo -e "  ${CYAN}Installing PoshC2...${NC}"
    curl -sSL https://raw.githubusercontent.com/nettitude/PoshC2/master/Install.sh 2>/dev/null | bash 2>&1 | tail -3 || true
    [ -d /opt/PoshC2 ] && echo -e "  ${GREEN}✓${NC} poshc2 → /opt/PoshC2" || \
      echo -e "  ${YELLOW}~${NC} poshc2 install failed"
  else
    echo -e "  ${YELLOW}~${NC} poshc2 already at /opt/PoshC2"
  fi

  # ── Empire ── (apt on Kali, fallback to git clone)
  if ! command -v powershell-empire &>/dev/null && [ ! -d /opt/Empire ]; then
    echo -e "  ${CYAN}Installing Empire C2 (via apt)...${NC}"
    apt install -y powershell-empire 2>/dev/null && \
      echo -e "  ${GREEN}✓${NC} empire (apt)" || {
        git clone --quiet --depth 1 https://github.com/BC-SECURITY/Empire.git /opt/Empire 2>&1 | tail -2 || true
        [ -d /opt/Empire ] && echo -e "  ${GREEN}✓${NC} empire → /opt/Empire" || \
          echo -e "  ${YELLOW}~${NC} empire install failed"
      }
  else
    echo -e "  ${YELLOW}~${NC} empire already present"
  fi

  # ── Covenant ── (.NET C2, requires dotnet — clone only, build separately)
  if [ ! -d /opt/Covenant ]; then
    echo -e "  ${CYAN}Cloning Covenant C2 (build with dotnet separately)...${NC}"
    git clone --quiet --recurse-submodules --depth 1 \
      https://github.com/cobbr/Covenant.git /opt/Covenant 2>&1 | tail -2 || true
    [ -d /opt/Covenant ] && echo -e "  ${GREEN}✓${NC} covenant → /opt/Covenant" || \
      echo -e "  ${YELLOW}~${NC} covenant clone failed"
  else
    echo -e "  ${YELLOW}~${NC} covenant already at /opt/Covenant"
  fi

  # ── Mythic ── (Docker-based, just clone the repo; user runs install separately)
  if [ ! -d /opt/Mythic ]; then
    echo -e "  ${CYAN}Cloning Mythic C2 (run ./install_docker_ubuntu.sh separately)...${NC}"
    git clone --quiet --depth 1 https://github.com/its-a-feature/Mythic.git /opt/Mythic 2>&1 | tail -2 || true
    [ -d /opt/Mythic ] && echo -e "  ${GREEN}✓${NC} mythic → /opt/Mythic" || \
      echo -e "  ${YELLOW}~${NC} mythic clone failed"
  else
    echo -e "  ${YELLOW}~${NC} mythic already at /opt/Mythic"
  fi

  # Chown all C2 dirs to invoking user
  if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    for d in Merlin PoshC2 Empire Covenant Mythic; do
      [ -d "/opt/$d" ] && chown -R "$SUDO_USER":"$SUDO_USER" "/opt/$d" 2>/dev/null || true
    done
  fi

  cd - > /dev/null
  echo -e "  ${GREEN}C2 frameworks done${NC}"
  echo -e "  ${YELLOW}Note: most C2s need additional setup (db init, dotnet build,${NC}"
  echo -e "  ${YELLOW}      docker images). See each repo's README for next steps.${NC}"
}

# ── Step 1f: Knowledge-base reference repos (Windows-side tooling) ────────────
# These are NOT installable tools — they're PowerShell scripts, JSON databases,
# or web resources. We clone them to /opt/knowledge so ERR0RS can index them
# in RAG and teach about them, even though they don't "run" on Kali.
init_knowledge_repos() {
  echo -e "\n${CYAN}[1f/5] Cloning reference repos for RAG knowledge base...${NC}"

  if [ "$WITH_KNOWLEDGE_REPOS" != "true" ]; then
    echo -e "  ${YELLOW}~${NC} Skipped — Windows-side reference repos NOT cloned"
    echo -e "    To clone them: ${CYAN}sudo bash install.sh --with-knowledge-repos${NC}"
    return 0
  fi

  KB_DIR="$SCRIPT_DIR/knowledge_repos"
  mkdir -p "$KB_DIR"
  cd "$KB_DIR"

  # KB_REPOS: format "name|repo_url"
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
    name="${entry%%|*}"
    repo="${entry##*|}"
    target="$KB_DIR/$name"

    if [ -d "$target/.git" ]; then
      echo -e "  ${YELLOW}~${NC} $name already cloned — pulling"
      (cd "$target" && git pull --quiet 2>/dev/null) || true
    else
      echo -e "  ${CYAN}Cloning $name...${NC}"
      git clone --quiet --depth 1 "$repo" "$target" 2>&1 | tail -2 && \
        echo -e "  ${GREEN}✓${NC} $name" || \
        echo -e "  ${YELLOW}~${NC} $name clone failed"
    fi
  done

  # Chown back to invoking user
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

  # Choose model. gemma3:1b verified for Pi 5 / ARM by stress test
  # 2026-05-20 (TTFT 28.1s on chunked RAG, no thermal issues). x86 hosts
  # default to the same model for consistency with the LLM router config;
  # users can override via OLLAMA_MODEL=... in .env if they have RAM headroom
  # for a larger model and want better quality.
  if [[ "$ARCH" == "aarch64" ]]; then
    MODEL="gemma3:1b"     # Pi 5 verified — see docs/STRESS_TESTS/FINDINGS_2026-05-20.md
  else
    MODEL="${OLLAMA_MODEL:-gemma3:1b}"
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
  --with-c2              Install C2 frameworks: empire, sliver, covenant,
                         merlin, poshc2, mythic. Heavy install — multi-GB.
                         Off by default.
  --with-knowledge-repos Clone reference repos: GTFOBins, LOLBAS, PowerSploit,
                         windows-exploit-suggester, etc. — for RAG indexing
                         of Windows-side tools that can't run on Kali.
  --skip-go-tools        Skip Go-based tool installation (dalfox, katana,
                         httpx, naabu, gau, waybackurls, etc.). Use this
                         if you have a slow connection or no internet.
  --skip-pip-tools       Skip pip-installed security tools (pwntools, droopescan,
                         corsy, jwt_tool, graphqlmap, etc.)
  --skip-github-tools    Skip github-clone tools (sn1per, autosploit, LinkFinder,
                         SecretFinder, privesccheck)
  --skip-ollama          Skip Ollama install + model pull. Useful if you
                         already have it running, or you're not using local LLM.
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
  echo -e "    Submodules:      ${WITH_SUBMODULES}"
  echo -e "    C2 frameworks:   ${WITH_C2}"
  echo -e "    Knowledge repos: ${WITH_KNOWLEDGE_REPOS}"
  echo -e "    Go tools:        $([ "$SKIP_GO_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Pip tools:       $([ "$SKIP_PIP_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Github tools:    $([ "$SKIP_GITHUB_TOOLS" = "true" ] && echo "skip" || echo "install")"
  echo -e "    Ollama:          $([ "$SKIP_OLLAMA" = "true" ] && echo "skip" || echo "install")"

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
