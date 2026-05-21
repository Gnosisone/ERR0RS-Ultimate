#!/usr/bin/env bash
#
# restore_all_submodules.sh — Restore all 75 submodules in ERR0RS-clean
#
# Phase 1: git submodule update on the 6 already-tracked
# Phase 2: git submodule add on the 69 missing entries
# Phase 3: Final accounting
#
# Failures are logged but DO NOT abort the run.
#

set -uo pipefail

REPO=/home/kali/ERR0RS-clean
LOG=/tmp/err0rs_clean_submodule_restore.log
MISSING=/tmp/missing_submodules.txt
START=$(date +%s)

cd "$REPO" || { echo "FATAL: cannot cd to $REPO"; exit 1; }

{
  echo "==============================================================="
  echo " ERR0RS-clean submodule restoration"
  echo " Started: $(date)"
  echo "==============================================================="
  echo ""
} > "$LOG"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

# ── PHASE 1 ────────────────────────────────────────────────────────────────
log "PHASE 1: Pulling 6 already-tracked submodules (parallel jobs=4)"
log ""

if git submodule update --init --recursive --jobs=4 >> "$LOG" 2>&1; then
  log "PHASE 1: OK submodule update succeeded"
else
  log "PHASE 1: WARN submodule update returned non-zero (some may have failed - continuing)"
fi
log ""

# ── PHASE 2 ────────────────────────────────────────────────────────────────
log "PHASE 2: Adding 69 missing submodules sequentially"
log ""

added=0
failed=0
skipped=0
total=$(wc -l < "$MISSING")
i=0

while IFS=$'\t' read -r path url; do
  i=$((i+1))
  log "[$i/$total] $path"

  if [[ -d "$path" ]] && [[ -n "$(ls -A "$path" 2>/dev/null)" ]]; then
    log "          -> SKIP (directory already populated)"
    skipped=$((skipped+1))
    continue
  fi

  rm -rf "$path" 2>/dev/null

  if git submodule add --force "$url" "$path" >> "$LOG" 2>&1; then
    log "          -> OK added"
    added=$((added+1))
  else
    log "          -> FAILED (see log)"
    failed=$((failed+1))
  fi

done < "$MISSING"

log ""
log "PHASE 2 complete: added=$added skipped=$skipped failed=$failed"
log ""

# ── PHASE 3 ────────────────────────────────────────────────────────────────
log "PHASE 3: Final accounting"
log ""

tracked_now=$(git ls-files --stage | grep -c '^160000' || echo 0)
populated_now=$(find knowledge -mindepth 2 -maxdepth 4 -type d ! -empty 2>/dev/null | grep -E "knowledge/(badusb|rocketgod)/" | wc -l || echo 0)

log "Submodules tracked as gitlinks: $tracked_now (was 6)"
log "Populated badusb/rocketgod dirs: $populated_now"
log ""

ELAPSED=$(($(date +%s) - START))
log "Total runtime: $((ELAPSED/60))m $((ELAPSED%60))s"
log "==============================================================="
log " DONE"
log "==============================================================="

touch /tmp/err0rs_clean_submodule_restore.DONE
