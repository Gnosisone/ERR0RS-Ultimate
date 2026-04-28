#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║   ERR0RS Phoenix OS — Pi 5 First Boot Setup                   ║
# ║   Runs once on first login to complete ERR0RS installation    ║
# ║   Called by: /etc/profile.d/errz_firstboot.sh                ║
# ╚═══════════════════════════════════════════════════════════════╝

STAMP="$HOME/.errz_firstboot_done"
REPO="/opt/ERR0RS-Ultimate"
LOG="$HOME/errz_firstboot.log"

# Only run once
[ -f "$STAMP" ] && exit 0

RED='\033[0;31m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'; NC='\033[0m'

echo -e "${RED}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   ERR0RS ULTIMATE — FIRST BOOT SETUP            ║"
echo "  ║   Pi 5 Cyberdeck | Phoenix OS                   ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo "Setting up ERR0RS... this takes ~5 minutes on first boot."
echo "Log: $LOG"
echo ""

{
    echo "[$(date)] ERR0RS First Boot Setup"

    # ── Pull latest code ───────────────────────────────────────────
    echo "[*] Pulling latest ERR0RS from GitHub..."
    cd "$REPO"
    git pull origin main 2>&1 || echo "[!] git pull failed — using bundled version"

    # ── Python venv ────────────────────────────────────────────────
    echo "[*] Setting up Python venv..."
    python3 -m venv "$REPO/venv"
    source "$REPO/venv/bin/activate"
    pip install --upgrade pip -q
    pip install -r "$REPO/requirements.txt" -q || \
    pip install fastapi uvicorn websockets aiohttp \
        anthropic chromadb sentence-transformers \
        python-dotenv rich click psutil -q

    # ── Ollama ─────────────────────────────────────────────────────
    echo "[*] Checking Ollama..."
    if ! command -v ollama &>/dev/null; then
        echo "[*] Installing Ollama..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    systemctl enable ollama 2>/dev/null || true
    systemctl start ollama 2>/dev/null || (ollama serve &)
    sleep 3

    echo "[*] Pulling qwen2.5-coder:7b model (background)..."
    nohup ollama pull qwen2.5-coder:7b > "$HOME/errz_ollama_pull.log" 2>&1 &
    echo "  Model pull running in background — check ~/errz_ollama_pull.log"

    # ── Desktop icon ───────────────────────────────────────────────
    echo "[*] Installing desktop icon..."
    bash "$REPO/scripts/install_desktop_icon.sh" 2>/dev/null || true

    # ── .env config ────────────────────────────────────────────────
    echo "[*] Creating .env..."
    cat > "$REPO/.env" << ENV
UI_HOST=127.0.0.1
UI_PORT=8765
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_HOST=http://localhost:11434
HAILO_ENABLED=true
PI5_MODE=true
ANTHROPIC_API_KEY=
ENV

    echo "[$(date)] First boot setup complete!" >> "$LOG"

} 2>&1 | tee -a "$LOG"

# Mark as done
touch "$STAMP"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ERR0RS SETUP COMPLETE ✓                        ║${NC}"
echo -e "${GREEN}║   Double-click the desktop icon to launch        ║${NC}"
echo -e "${GREEN}║   Or type: errorz                                ║${NC}"
echo -e "${GREEN}║   Web UI: http://127.0.0.1:8765                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
