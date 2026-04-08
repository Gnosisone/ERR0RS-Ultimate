#!/usr/bin/env bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║  ERR0RS-Ultimate :: Prompt Manual Launcher                    ║
# ║                                                               ║
# ║  Opens err0rs_prompt_manual.html in the default browser.      ║
# ║  Falls back through: xdg-open → firefox → chromium → python3 ║
# ╚═══════════════════════════════════════════════════════════════╝

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANUAL="$SCRIPT_DIR/docs/err0rs_prompt_manual.html"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

if [ ! -f "$MANUAL" ]; then
  echo -e "${RED}[!] Manual not found at: $MANUAL${NC}"
  echo -e "${CYAN}[*] Make sure you cloned the full repo including docs/${NC}"
  exit 1
fi

echo -e "${GREEN}[+] Opening ERR0RS Prompt Manual...${NC}"
echo -e "${CYAN}    $MANUAL${NC}"

# Try openers in order of preference
if command -v xdg-open &>/dev/null; then
  xdg-open "$MANUAL" &
elif command -v firefox &>/dev/null; then
  firefox "$MANUAL" &
elif command -v chromium &>/dev/null; then
  chromium "$MANUAL" &
elif command -v chromium-browser &>/dev/null; then
  chromium-browser "$MANUAL" &
elif command -v python3 &>/dev/null; then
  python3 -m webbrowser "file://$MANUAL" &
else
  echo -e "${RED}[!] No browser found. Open manually:${NC}"
  echo -e "    file://$MANUAL"
  exit 1
fi

echo -e "${GREEN}[+] Manual launched.${NC}"
