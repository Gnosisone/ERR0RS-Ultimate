#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# pi_thermal_watch — continuous Pi 5 thermal + throttle monitor
# ──────────────────────────────────────────────────────────────────────────────
# Logs CPU temp, throttle state, load avg, and Ollama runner activity every
# 5 seconds. Color-coded alerts:
#   GREEN   <70°C    Comfortable, no concern
#   YELLOW  70-80°C  Warm but safe — sustainable for hours
#   RED     >80°C    Throttle territory — slow down or improve cooling
#   PURPLE  >85°C    Soft thermal limit — Pi WILL cap frequency
#
# Usage:
#   bash scripts/pi_thermal_watch.sh                 # watch indefinitely
#   bash scripts/pi_thermal_watch.sh 600             # watch for 10 minutes
#   bash scripts/pi_thermal_watch.sh 600 /tmp/x.log  # also log to file
# ──────────────────────────────────────────────────────────────────────────────

DURATION="${1:-0}"           # 0 = forever
LOGFILE="${2:-}"             # optional log to disk
INTERVAL=5

G='\033[92m'; Y='\033[93m'; R='\033[91m'; P='\033[95m'; C='\033[96m'; B='\033[1m'; N='\033[0m'

START=$(date +%s)
echo -e "${B}${C}=== ERR0RS Pi Thermal Watch ===${N}"
echo    "  Started: $(date)"
echo    "  Interval: ${INTERVAL}s"
[ "$DURATION" -gt 0 ] && echo "  Duration: ${DURATION}s" || echo "  Duration: forever (Ctrl-C to stop)"
[ -n "$LOGFILE" ] && echo "  Logfile: $LOGFILE"
echo ""
printf "  %-8s  %-7s  %-15s  %-15s  %-15s  %s\n" "Elapsed" "Temp" "Throttle (now)" "Load avg" "Ollama %CPU" "Status"
printf "  %s\n" "$(printf -- '-%.0s' {1..90})"

while true; do
    NOW=$(date +%s)
    ELAPSED=$(( NOW - START ))
    [ "$DURATION" -gt 0 ] && [ $ELAPSED -ge "$DURATION" ] && break

    TEMP_MILLI=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)
    TEMP=$(awk -v t="$TEMP_MILLI" 'BEGIN { printf "%.1f", t/1000 }')
    THROTTLED=$(vcgencmd get_throttled 2>/dev/null | sed 's/throttled=//')
    NOW_FLAGS=$(( $THROTTLED & 0xffff ))
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | sed 's/^ *//')
    OLLAMA_CPU=$(ps -C ollama -o pcpu= 2>/dev/null | awk '{s+=$1} END {printf "%.0f%%", s}')
    [ -z "$OLLAMA_CPU" ] && OLLAMA_CPU="0%"

    # Color-code the temp
    TEMP_INT=${TEMP%.*}
    if   [ $TEMP_INT -lt 70 ]; then COLOR=$G; STATUS="cool"
    elif [ $TEMP_INT -lt 80 ]; then COLOR=$Y; STATUS="warm"
    elif [ $TEMP_INT -lt 85 ]; then COLOR=$R; STATUS="HOT — throttle risk"
    else                            COLOR=$P; STATUS="SOFT LIMIT — throttling now"
    fi

    THROTTLE_LABEL=""
    [ $NOW_FLAGS -eq 0 ] && THROTTLE_LABEL="${G}ok${N}" || THROTTLE_LABEL="${R}0x$(printf '%x' $NOW_FLAGS)${N}"

    LINE=$(printf "  %-8s  ${COLOR}%-7s${N}  %-25s  %-15s  %-11s  ${COLOR}%s${N}" \
        "${ELAPSED}s" "${TEMP}°C" "$THROTTLE_LABEL" "$LOAD" "$OLLAMA_CPU" "$STATUS")
    echo -e "$LINE"

    if [ -n "$LOGFILE" ]; then
        printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
            "$(date '+%F %T')" "$ELAPSED" "$TEMP" "0x$(printf '%x' $NOW_FLAGS)" "$OLLAMA_CPU" "$STATUS" \
            >> "$LOGFILE"
    fi

    sleep "$INTERVAL"
done

echo ""
echo -e "${B}${C}=== Final state ===${N}"
echo "  Total time: ${ELAPSED}s"
vcgencmd get_throttled 2>&1 | sed 's/^/  /'
echo ""
echo "  Sticky 'since-boot' flags:"
SINCE_BOOT=$(( $THROTTLED >> 16 ))
[ $((SINCE_BOOT & 0x1)) -ne 0 ] && echo -e "    ${Y}⚠ Under-voltage occurred${N}"
[ $((SINCE_BOOT & 0x2)) -ne 0 ] && echo -e "    ${Y}⚠ Arm frequency cap occurred${N}"
[ $((SINCE_BOOT & 0x4)) -ne 0 ] && echo -e "    ${Y}⚠ Throttling occurred${N}"
[ $((SINCE_BOOT & 0x8)) -ne 0 ] && echo -e "    ${Y}⚠ Soft temperature limit reached${N}"
[ $SINCE_BOOT -eq 0 ] && echo -e "    ${G}✓ Clean run — no throttling occurred${N}"
