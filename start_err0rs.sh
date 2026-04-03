#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║       ERR0RS-Ultimate :: Full Stack Launcher v2.0             ║
# ║       Kali 2026.1 | Pi 5 + Hailo-10H | Phoenix-OS            ║
# ╚═══════════════════════════════════════════════════════════════╝
# Usage: bash start_err0rs.sh [--no-msf] [--no-ollama] [--cli]
# Services: Ollama → MetasploitMCP (optional) → ERR0RS Web UI

set -e
RED='\033[0;31m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; PURPLE='\033[0;35m'; NC='\033[0m'

# ── Resolve absolute repo root (works from any working dir) ──────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Detect Pi vs Desktop ─────────────────────────────────────────
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    PI_MODE=true
    OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"
    UI_PORT="${UI_PORT:-8765}"
else
    PI_MODE=false
    OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:32b}"
    UI_PORT="${UI_PORT:-8765}"
fi

MSF_PASS="${MSF_PASSWORD:-err0rs_local}"
MSF_MCP_PORT="${MSF_MCP_PORT:-8085}"
PAYLOAD_DIR="${PAYLOAD_SAVE_DIR:-$HOME/err0rs_payloads}"
LOG_DIR="$HOME/err0rs_logs"
mkdir -p "$PAYLOAD_DIR" "$LOG_DIR"


# ── Banner ────────────────────────────────────────────────────────
echo -e "${RED}"
echo "  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
echo -e "${NC}  ULTIMATE — $([ "$PI_MODE" = true ] && echo "Pi 5 Cyberdeck Mode 🍓" || echo "Kali 2026.1 Desktop Mode")"
echo ""

# ── Check venv / Python deps ─────────────────────────────────────
echo -e "${CYAN}[*] Checking Python environment...${NC}"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo -e "  ${YELLOW}No venv found — creating...${NC}"
    python3 -m venv "$SCRIPT_DIR/venv"
fi
source "$SCRIPT_DIR/venv/bin/activate" 2>/dev/null || true

# Quick check: websockets installed?
python3 -c "import websockets" 2>/dev/null || {
    echo -e "  ${YELLOW}Installing missing deps...${NC}"
    pip install -r "$SCRIPT_DIR/requirements.txt" -q \
        2>/dev/null || pip install websockets aiohttp -q
}
echo -e "  ${GREEN}✓ Python environment ready${NC}"

# ── Kali 2026.1 tool check (non-blocking) ────────────────────────
echo -e "${CYAN}[*] Checking available tools...${NC}"
TOOLS_OK=0; TOOLS_MISSING=0
for tool in nmap sqlmap nikto gobuster hydra hashcat; do
    if command -v $tool &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $tool"
        TOOLS_OK=$((TOOLS_OK+1))
    else
        echo -e "  ${YELLOW}~${NC} $tool (not installed)"
        TOOLS_MISSING=$((TOOLS_MISSING+1))
    fi
done
echo -e "  Tools: ${GREEN}$TOOLS_OK available${NC} | ${YELLOW}$TOOLS_MISSING missing${NC}"


# ── Metasploit RPC (optional, skip on Pi or if --no-msf) ─────────
if [[ "$*" != *"--no-msf"* ]] && [ "$PI_MODE" = false ]; then
    echo -e "${CYAN}[*] Starting Metasploit RPC...${NC}"
    if command -v msfrpcd &>/dev/null; then
        if ! pgrep -x msfrpcd > /dev/null; then
            msfrpcd -P "$MSF_PASS" -S -a 127.0.0.1 -p 55553 \
                > "$LOG_DIR/msfrpcd.log" 2>&1 &
            sleep 5
        fi
        echo -e "  ${GREEN}✓ msfrpcd on 127.0.0.1:55553${NC}"
        # MetasploitMCP
        MSF_SCRIPT=$(find /usr/share /opt -name "MetasploitMCP.py" 2>/dev/null | head -1)
        if [[ -n "$MSF_SCRIPT" ]]; then
            MSF_PASSWORD="$MSF_PASS" MSF_SERVER=127.0.0.1 MSF_PORT=55553 \
            MSF_SSL=false PAYLOAD_SAVE_DIR="$PAYLOAD_DIR" \
            python3 "$MSF_SCRIPT" --transport http \
                --host 127.0.0.1 --port "$MSF_MCP_PORT" \
                > "$LOG_DIR/metasploitmcp.log" 2>&1 &
            sleep 2
            echo -e "  ${GREEN}✓ MetasploitMCP on 127.0.0.1:${MSF_MCP_PORT}${NC}"
        else
            echo -e "  ${YELLOW}~ MetasploitMCP.py not found (sudo apt install metasploit-mcp)${NC}"
        fi
    else
        echo -e "  ${YELLOW}~ Metasploit not found — skipping RPC${NC}"
    fi
fi

# ── Ollama ────────────────────────────────────────────────────────
if [[ "$*" != *"--no-ollama"* ]]; then
    echo -e "${CYAN}[*] Starting Ollama (model: $OLLAMA_MODEL)...${NC}"
    if ! command -v ollama &>/dev/null; then
        echo -e "  ${YELLOW}~ Ollama not installed — installing now...${NC}"
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    if ! pgrep -x ollama > /dev/null; then
        ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
        sleep 4
    fi
    # Pull model if not already pulled
    if ! ollama list 2>/dev/null | grep -q "${OLLAMA_MODEL%%:*}"; then
        echo -e "  ${YELLOW}Pulling $OLLAMA_MODEL (first time — takes a few minutes)...${NC}"
        ollama pull "$OLLAMA_MODEL" &
    fi
    echo -e "  ${GREEN}✓ Ollama ready | $OLLAMA_MODEL${NC}"
fi

# ── RAG first-run ingest ──────────────────────────────────────────
if [[ ! -d "$HOME/err0rs_chromadb" ]]; then
    echo -e "${CYAN}[*] First run — ingesting knowledge base (background)...${NC}"
    python3 "$SCRIPT_DIR/src/ai/rag_ingest_2026.py" \
        --source kali2026 > "$LOG_DIR/rag.log" 2>&1 &
    echo -e "  ${GREEN}✓ RAG ingest running in background${NC}"
fi


# ── Status Summary ────────────────────────────────────────────────
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   ERR0RS ULTIMATE — ALL SYSTEMS GO               ║${NC}"
echo -e "${PURPLE}╠══════════════════════════════════════════════════╣${NC}"
if [[ "$*" != *"--no-msf"* ]] && [ "$PI_MODE" = false ]; then
echo -e "${PURPLE}║   Metasploit RPC : 127.0.0.1:55553              ║${NC}"
echo -e "${PURPLE}║   MetasploitMCP  : 127.0.0.1:${MSF_MCP_PORT}           ║${NC}"
fi
echo -e "${PURPLE}║   Ollama         : 127.0.0.1:11434              ║${NC}"
echo -e "${PURPLE}║   ERR0RS UI      : http://127.0.0.1:${UI_PORT}      ║${NC}"
echo -e "${PURPLE}║   WebSocket      : ws://127.0.0.1:8766           ║${NC}"
echo -e "${PURPLE}║   Model          : $OLLAMA_MODEL$([ "$PI_MODE" = true ] && echo " [Pi]" || echo "")           ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════╝${NC}"
echo -e "${RED}  [!] FOR AUTHORIZED TESTING ONLY — 100% LOCAL${NC}\n"

# ── Write .env if missing ─────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cat > "$SCRIPT_DIR/.env" << ENV
UI_HOST=127.0.0.1
UI_PORT=$UI_PORT
LLM_BACKEND=ollama
OLLAMA_MODEL=$OLLAMA_MODEL
OLLAMA_HOST=http://localhost:11434
HAILO_ENABLED=$([ "$PI_MODE" = true ] && echo "true" || echo "false")
PI5_MODE=$PI_MODE
ANTHROPIC_API_KEY=
ENV
    echo -e "  ${GREEN}✓ .env created${NC}"
fi

# ── Launch ERR0RS ─────────────────────────────────────────────────
echo -e "${CYAN}[*] Launching ERR0RS...${NC}"

if [[ "$*" == *"--cli"* ]]; then
    # CLI mode
    python3 "$SCRIPT_DIR/main.py"
else
    # Web UI mode — this is the correct launcher (NOT uvicorn main:app)
    ERRZ_PORT="$UI_PORT" python3 "$SCRIPT_DIR/src/ui/errorz_launcher.py"
fi
