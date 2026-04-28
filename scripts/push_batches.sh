#!/usr/bin/env bash
# Push ERR0RS commits to GitHub in batches of 10
# Run this directly in your terminal: bash /home/kali/ERR0RS-Ultimate/scripts/push_batches.sh

set -e
cd /home/kali/ERR0RS-Ultimate

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PURPLE}ERR0RS — Batch Push Script${NC}"
echo "Fetching current remote state..."
git fetch origin 2>/dev/null

COMMITS=$(git log --oneline origin/main..HEAD | tac | awk '{print $1}')
TOTAL=$(echo "$COMMITS" | wc -l)

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${GREEN}Already up to date. Nothing to push.${NC}"
    exit 0
fi

echo -e "${YELLOW}$TOTAL commits to push. Sending in batches of 10...${NC}"
echo ""

BATCH_SIZE=10
BATCH=()
BATCH_NUM=0
PUSHED=0

while IFS= read -r HASH; do
    BATCH+=("$HASH")
    if [ ${#BATCH[@]} -eq $BATCH_SIZE ]; then
        BATCH_NUM=$((BATCH_NUM + 1))
        TARGET="${BATCH[-1]}"
        echo -e "${PURPLE}[Batch $BATCH_NUM]${NC} Pushing up to $TARGET..."
        if git push origin "${TARGET}:refs/heads/main" 2>&1 | grep -v "^remote:" | grep -v "^To "; then
            PUSHED=$((PUSHED + ${#BATCH[@]}))
            echo -e "  ${GREEN}✓ Batch $BATCH_NUM pushed ($PUSHED/$TOTAL)${NC}"
        else
            echo -e "  ${RED}✗ Batch $BATCH_NUM failed. Trying force-with-lease...${NC}"
            git push --force-with-lease origin "${TARGET}:refs/heads/main" 2>&1 | tail -3
        fi
        BATCH=()
        sleep 2
    fi
done <<< "$COMMITS"

# Push any remaining commits
if [ ${#BATCH[@]} -gt 0 ]; then
    BATCH_NUM=$((BATCH_NUM + 1))
    TARGET="${BATCH[-1]}"
    echo -e "${PURPLE}[Batch $BATCH_NUM — final]${NC} Pushing up to $TARGET..."
    git push origin "${TARGET}:refs/heads/main" 2>&1 | tail -3
    PUSHED=$((PUSHED + ${#BATCH[@]}))
    echo -e "  ${GREEN}✓ Final batch pushed${NC}"
fi

echo ""
echo -e "${GREEN}Done! $PUSHED/$TOTAL commits pushed.${NC}"
git log --oneline -3
