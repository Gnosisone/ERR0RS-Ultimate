#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║         ERR0RS LIVE OPERATOR FEED — err0rs_watch.sh             ║
# ║                                                                  ║
# ║  Real-time narrated view of everything ERR0RS is doing.         ║
# ║  Run in any terminal — Thunar, xterm, qterminal, bash, zsh.     ║
# ║                                                                  ║
# ║  Usage:                                                          ║
# ║    bash scripts/err0rs_watch.sh              # watch log file   ║
# ║    bash scripts/err0rs_watch.sh --api        # watch via API    ║
# ║    bash scripts/err0rs_watch.sh --juice      # Juice Shop feed  ║
# ║                                                                  ║
# ║  Author: Gary Holden Schneider (Eros) | github: Gnosisone       ║
# ╚══════════════════════════════════════════════════════════════════╝

# ── Colors ───────────────────────────────────────────────────────────
OR='\033[38;5;208m'   # orange  - ERR0RS actions
CY='\033[38;5;51m'    # cyan    - recon/scan
GR='\033[38;5;82m'    # green   - success/found
RD='\033[38;5;196m'   # red     - exploitation
YL='\033[38;5;226m'   # yellow  - teaching
MA='\033[38;5;135m'   # magenta - post-exploit
DM='\033[38;5;240m'   # dim     - timestamps
BL='\033[1m'          # bold
NC='\033[0m'          # reset

LOG_FILE="/tmp/err0rs_live.log"
API_URL="http://127.0.0.1:8765"
MODE="${1:-}"

# ── Header ────────────────────────────────────────────────────────────
clear
echo -e "${OR}${BL}"
cat << 'BANNER'
  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗
  ██╔════╝██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔════╝
  █████╗  ██████╔╝██████╔╝██║  ███╗██████╔╝███████╗
  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║
  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║
  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
BANNER
echo -e "${NC}${DM}  ─────────────────────────────────────────────────${NC}"
echo -e "  ${OR}${BL}LIVE OPERATOR FEED${NC}  ${DM}│${NC}  ${CY}Real-time narration of every action${NC}"
echo -e "${DM}  ─────────────────────────────────────────────────${NC}"
echo ""

# ── Check ERR0RS is running ───────────────────────────────────────────
check_errz() {
    curl -s --max-time 2 "${API_URL}/api/status" > /dev/null 2>&1
    return $?
}

if ! check_errz; then
    echo -e "  ${RD}${BL}⚠️  ERR0RS not running on port 8765${NC}"
    echo -e "  ${YL}Start it with: cd /home/kali/ERR0RS-Ultimate && python3 src/ui/errorz_launcher.py${NC}"
    echo ""
fi

# ── Mode: API polling ─────────────────────────────────────────────────
if [[ "$MODE" == "--api" ]]; then
    echo -e "  ${CY}Mode: API polling (${API_URL}/api/narrator/feed)${NC}"
    echo -e "  ${DM}Polling every 2s — Ctrl+C to stop${NC}"
    echo -e "${DM}  ─────────────────────────────────────────────────${NC}"
    echo ""
    LAST_COUNT=0
    while true; do
        RESP=$(curl -s --max-time 3 "${API_URL}/api/narrator/feed" 2>/dev/null)
        if [[ -n "$RESP" ]]; then
            TOTAL=$(echo "$RESP" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('total',0))" 2>/dev/null)
            if [[ "$TOTAL" -gt "$LAST_COUNT" ]]; then
                # New lines — print them
                echo "$RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
lines=d.get('lines',[])
start=$LAST_COUNT
new_lines=lines[max(0,start-d.get('total',0)):]
for l in new_lines:
    print(l, end='')
" 2>/dev/null
                LAST_COUNT=$TOTAL
            fi
        fi
        sleep 2
    done
fi

# ── Mode: Juice Shop live solver feed ─────────────────────────────────
if [[ "$MODE" == "--juice" ]]; then
    echo -e "  ${GR}${BL}Mode: Juice Shop CTF Live Solver${NC}"
    echo -e "  ${DM}Shows real-time challenge solving progress${NC}"
    echo -e "${DM}  ─────────────────────────────────────────────────${NC}"
    echo ""

    SOLVED_PREV=0
    while true; do
        RESP=$(curl -s --max-time 3 "http://localhost:3000/api/Challenges?limit=999" 2>/dev/null)
        if [[ -n "$RESP" ]]; then
            echo "$RESP" | python3 -c "
import json,sys
d=json.load(sys.stdin)
cs=d.get('data',[])
solved=[c for c in cs if c.get('solved')]
total=len(cs)
s=len(solved)
pct=round(s/total*100,1) if total else 0
bar='█'*int(pct/2) + '░'*(50-int(pct/2))
print(f'\r  \033[38;5;208m\033[1m[{bar}]\033[0m {s}/{total} ({pct}%)', end='', flush=True)
" 2>/dev/null
        fi
        sleep 5
    done
fi

# ── Default mode: tail the log file ──────────────────────────────────
echo -e "  ${OR}Mode: Live log tail${NC}  ${DM}(${LOG_FILE})${NC}"
echo -e "  ${DM}Press Ctrl+C to stop${NC}"
echo -e "${DM}  ─────────────────────────────────────────────────${NC}"
echo ""

# Create log if it doesn't exist
touch "$LOG_FILE" 2>/dev/null || {
    echo -e "  ${RD}Cannot access ${LOG_FILE}${NC}"
    exit 1
}

# Color-code the tail output based on keywords
tail -f "$LOG_FILE" | while IFS= read -r line; do
    # Phase-based coloring
    if echo "$line" | grep -q "\[ERR0RS:RECON\]"; then
        echo -e "${CY}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:SCANNING\]"; then
        echo -e "${CY}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:EXPLOITATION\]"; then
        echo -e "${RD}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:SUCCESS\]"; then
        echo -e "${GR}${BL}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:WARNING\]"; then
        echo -e "${YL}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:ERROR\]"; then
        echo -e "${RD}${BL}${line}${NC}"
    elif echo "$line" | grep -q "\[ERR0RS:TEACHING\]"; then
        echo -e "${YL}${line}${NC}"
    elif echo "$line" | grep -q "📘 WHY:"; then
        echo -e "${YL}${line}${NC}"
    elif echo "$line" | grep -q "✅ FOUND:"; then
        echo -e "${GR}${BL}${line}${NC}"
    elif echo "$line" | grep -q "──────"; then
        echo -e "${DM}${line}${NC}"
    else
        echo "$line"
    fi
done
