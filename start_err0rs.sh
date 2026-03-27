#!/bin/bash
# ╔═══════════════════════════════════════════════════════════╗
# ║       ERR0RS-Ultimate :: Full Stack Launcher              ║
# ║       Kali 2026.1 Edition                                 ║
# ╚═══════════════════════════════════════════════════════════╝
# Usage: bash start_err0rs.sh [--no-msf] [--no-ollama]
# Services: msfrpcd → MetasploitMCP → Ollama → ERR0RS FastAPI

set -e
RED='\033[0;31m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'; NC='\033[0m'

MSF_PASS="${MSF_PASSWORD:-err0rs_local}"
MSF_MCP_PORT="${MSF_MCP_PORT:-8085}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:32b}"
PAYLOAD_DIR="${PAYLOAD_SAVE_DIR:-$HOME/err0rs_payloads}"
LOG_DIR="$HOME/err0rs_logs"
mkdir -p "$PAYLOAD_DIR" "$LOG_DIR"

echo -e "${RED}"
echo "  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
echo "  ULTIMATE — Kali 2026.1 — Airgapped Mode"
echo -e "${NC}"

# ── Check Kali 2026.1 tools ──
echo -e "${CYAN}[*] Checking Kali 2026.1 tools...${NC}"
for tool in metasploit-mcp adaptixc2 atomic-operator fluxion sstimap wpprobe xsstrike; do
  dpkg -l $tool &>/dev/null 2>&1 && echo -e "  ${GREEN}✓${NC} $tool" || \
    echo -e "  ${RED}✗${NC} $tool → sudo apt install $tool"
done

# ── msfrpcd ──
if [[ "$*" != *"--no-msf"* ]]; then
  echo -e "\n${CYAN}[*] Starting Metasploit RPC...${NC}"
  if ! pgrep -x msfrpcd > /dev/null; then
    msfrpcd -P "$MSF_PASS" -S -a 127.0.0.1 -p 55553 > "$LOG_DIR/msfrpcd.log" 2>&1 &
    sleep 6
  fi
  echo -e "  ${GREEN}✓ msfrpcd on 127.0.0.1:55553${NC}"

  # ── MetasploitMCP ──
  echo -e "${CYAN}[*] Starting MetasploitMCP server...${NC}"
  MSF_SCRIPT=$(find /usr/share /opt -name "MetasploitMCP.py" 2>/dev/null | head -1)
  if [[ -n "$MSF_SCRIPT" ]]; then
    MSF_PASSWORD="$MSF_PASS" MSF_SERVER=127.0.0.1 MSF_PORT=55553 \
    MSF_SSL=false PAYLOAD_SAVE_DIR="$PAYLOAD_DIR" \
    python "$MSF_SCRIPT" --transport http --host 127.0.0.1 --port "$MSF_MCP_PORT" \
      > "$LOG_DIR/metasploitmcp.log" 2>&1 &
    sleep 3
    echo -e "  ${GREEN}✓ MetasploitMCP on 127.0.0.1:${MSF_MCP_PORT}${NC}"
  else
    echo -e "  ${RED}✗ MetasploitMCP.py not found — sudo apt install metasploit-mcp${NC}"
  fi
fi

# ── Ollama ──
if [[ "$*" != *"--no-ollama"* ]]; then
  echo -e "${CYAN}[*] Starting Ollama...${NC}"
  pgrep -x ollama > /dev/null || (ollama serve > "$LOG_DIR/ollama.log" 2>&1 & sleep 3)
  echo -e "  ${GREEN}✓ Ollama ready | Model: $OLLAMA_MODEL${NC}"
  echo -e "  Pull if needed: ollama pull $OLLAMA_MODEL"
fi

# ── RAG first-run ingest ──
if [[ ! -d "$HOME/err0rs_chromadb" ]]; then
  echo -e "${CYAN}[*] First run — ingesting knowledge base...${NC}"
  cd "$(dirname "$0")" && python src/ai/rag_ingest_2026.py --source kali2026
  python src/ai/rag_ingest_2026.py --source chains
  echo -e "  ${GREEN}✓ RAG knowledge base ready${NC}"
fi

# ── Status Summary ──
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ERR0RS ULTIMATE — ALL SYSTEMS GO        ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Metasploit RPC  : 127.0.0.1:55553      ║${NC}"
echo -e "${GREEN}║  MetasploitMCP   : 127.0.0.1:${MSF_MCP_PORT}       ║${NC}"
echo -e "${GREEN}║  Ollama          : 127.0.0.1:11434      ║${NC}"
echo -e "${GREEN}║  ERR0RS API      : 127.0.0.1:8000       ║${NC}"
echo -e "${GREEN}║  Dashboard       : 127.0.0.1:8000/ui    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo -e "${RED}  [!] AUTHORIZED TESTING ONLY — AIRGAPPED${NC}\n"

# ── Launch ERR0RS ──
cd "$(dirname "$0")" && uvicorn main:app --host 127.0.0.1 --port 8000 --reload
