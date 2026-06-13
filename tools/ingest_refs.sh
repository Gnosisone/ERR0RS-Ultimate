#!/usr/bin/env bash
# Stage B: legal reference corpora -> err0rs_refs. Re-runnable (dedups by id).
set -u
cd /home/kali/ERR0RS-clean || exit 1
REPOS=( "OWASP/CheatSheetSeries" "OWASP/wstg" "swisskyrepo/PayloadsAllTheThings" )
for r in "${REPOS[@]}"; do
  echo "==== $(date +%H:%M:%S) START $r ===="
  python3 src/tools/rag_ingestor.py "$r" --collection err0rs_refs --no-submodule
  echo "==== $(date +%H:%M:%S) DONE  $r ===="
done
echo "==== ALL REFS INGESTED $(date +%H:%M:%S) ===="
