#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║              ERR0RS ULTIMATE — LAB STARTUP SCRIPT                  ║
# ║                    scripts/start_lab.sh                             ║
# ║                                                                      ║
# ║  Starts the full ERR0RS practice environment:                       ║
# ║    • OWASP Juice Shop (web app target)                              ║
# ║    • ERR0RS web UI + WebSocket server                               ║
# ║    • Ollama LLM (if not already running)                            ║
# ║    • Metasploitable 2 VM (if VirtualBox available)                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

set -e
GREEN='\033[0;32m'; PURPLE='\033[0;35m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
BOLD='\033[1m'

echo -e "${PURPLE}${BOLD}"
echo "  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
echo "                 LAB ENVIRONMENT STARTUP"
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ── 1. Ollama ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Checking Ollama...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "  Starting Ollama..."
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Ollama started${NC}"
    else
        echo -e "  ${RED}✗ Ollama failed to start — check /tmp/ollama.log${NC}"
    fi
else
    echo -e "  ${GREEN}✓ Ollama already running${NC}"
fi

# ── 2. Juice Shop ──────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/4] Starting OWASP Juice Shop...${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200\|302\|301"; then
    echo -e "  ${GREEN}✓ Juice Shop already running at http://localhost:3000${NC}"
else
    # Try Docker
    if command -v docker &> /dev/null; then
        # Detect docker permission problem up front — on a fresh Kali the
        # user often isn't in the docker group, so every docker call needs
        # sudo. Pick the right invocation (or tell the user how to fix it)
        # instead of silently failing with a permission-denied.
        DOCKER="docker"
        if ! docker info > /dev/null 2>&1; then
            if sudo -n docker info > /dev/null 2>&1; then
                DOCKER="sudo docker"
            else
                echo -e "  ${YELLOW}⚠ Docker needs elevated permissions.${NC}"
                echo -e "     One-time fix (then re-run this script):"
                echo -e "       ${BOLD}sudo usermod -aG docker \$USER${NC}  then log out/in"
                echo -e "     Or start Juice Shop now with:"
                echo -e "       ${BOLD}sudo docker run -d -p 3000:3000 --name juice-shop bkimminich/juice-shop${NC}"
                DOCKER=""
            fi
        fi
        if [ -n "$DOCKER" ]; then
            EXISTING=$($DOCKER ps -aq --filter name=juice-shop 2>/dev/null)
            if [ -n "$EXISTING" ]; then
                $DOCKER start juice-shop > /dev/null 2>&1 && echo -e "  ${GREEN}✓ Juice Shop container restarted${NC}"
            else
                $DOCKER run -d -p 3000:3000 --name juice-shop bkimminich/juice-shop > /dev/null 2>&1 && \
                    echo -e "  ${GREEN}✓ Juice Shop container started — waiting for startup...${NC}" && \
                sleep 8
            fi
        fi
    # Try Node.js install
    elif command -v node &> /dev/null && [ -d "$HOME/juice-shop" ]; then
        cd "$HOME/juice-shop" && node app.js > /tmp/juice-shop.log 2>&1 &
        echo -e "  ${GREEN}✓ Juice Shop started via Node.js${NC}"
    else
        echo -e "  ${RED}✗ Juice Shop not available. Install with:${NC}"
        echo -e "     docker pull bkimminich/juice-shop"
        echo -e "     OR: git clone https://github.com/juice-shop/juice-shop && cd juice-shop && npm install && node app.js"
    fi

    # Verify it's up
    sleep 3
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null | grep -q "200\|302\|301"; then
        echo -e "  ${GREEN}✓ Juice Shop online at http://localhost:3000${NC}"
    else
        echo -e "  ${YELLOW}⚠ Juice Shop may still be starting — try in 30 seconds${NC}"
    fi
fi

# ── 3. Wordlists ───────────────────────────────────────────────────────────
echo -e "${YELLOW}[3/4] Checking wordlists...${NC}"
ROCKYOU="/usr/share/wordlists/rockyou.txt"
LOCAL_RW="$HOME/.err0rs/wordlists/rockyou.txt"

if [ -f "$ROCKYOU" ]; then
    echo -e "  ${GREEN}✓ rockyou.txt found at $ROCKYOU${NC}"
elif [ -f "$LOCAL_RW" ]; then
    echo -e "  ${GREEN}✓ rockyou.txt found at $LOCAL_RW${NC}"
elif [ -f "/usr/share/wordlists/rockyou.txt.gz" ]; then
    echo -e "  Extracting rockyou.txt.gz..."
    mkdir -p "$HOME/.err0rs/wordlists"
    cp /usr/share/wordlists/rockyou.txt.gz /tmp/rockyou.txt.gz
    gzip -d /tmp/rockyou.txt.gz
    cp /tmp/rockyou.txt "$LOCAL_RW"
    echo -e "  ${GREEN}✓ rockyou.txt extracted to $LOCAL_RW${NC}"
else
    echo -e "  ${RED}✗ rockyou.txt not found. Install: sudo apt install wordlists${NC}"
fi

# ── 4. ERR0RS ──────────────────────────────────────────────────────────────
echo -e "${YELLOW}[4/4] Starting ERR0RS...${NC}"
cd "$PROJECT_DIR"
echo ""
echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  LAB ENVIRONMENT READY${NC}"
echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${YELLOW}ERR0RS UI:   ${GREEN}http://localhost:8765${NC}"
echo -e "  ${YELLOW}Juice Shop:  ${GREEN}http://localhost:3000${NC}"
echo -e "  ${YELLOW}Ollama:      ${GREEN}http://localhost:11434${NC}"
echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
python3 src/ui/errorz_launcher.py
