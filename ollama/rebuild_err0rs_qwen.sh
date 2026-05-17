#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Rebuild the err0rs-qwen Ollama model
# ──────────────────────────────────────────────────────────────────────────────
# Why a script and not just `ollama create -f Modelfile`?
#   The Modelfile template carries SYSTEM_PROMPT_PLACEHOLDER. This script
#   replaces it with the canonical src/ai/system_prompt.md content right
#   before passing the file to ollama. That way the source of truth is the
#   markdown soul file, not a copy-pasted version inside the Modelfile.
#
# Run this whenever:
#   - src/ai/system_prompt.md changes (most common reason)
#   - You want to recreate the local err0rs-qwen model from scratch
#   - You've updated Modelfile.err0rs parameters
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOUL="$ROOT/src/ai/system_prompt.md"
TEMPLATE="$ROOT/ollama/Modelfile.err0rs"
BUILT="$ROOT/ollama/Modelfile.err0rs.built"
MODEL_NAME="${1:-err0rs-qwen}"

if [[ ! -f "$SOUL" ]]; then
    echo "✗ Missing: $SOUL" >&2
    exit 1
fi
if [[ ! -f "$TEMPLATE" ]]; then
    echo "✗ Missing: $TEMPLATE" >&2
    exit 1
fi
if ! command -v ollama >/dev/null 2>&1; then
    echo "✗ ollama command not found on PATH" >&2
    exit 1
fi

echo "  ⟳ Reading system_prompt.md ($(wc -c < "$SOUL") chars, $(wc -l < "$SOUL") lines)..."

# Escape: triple quotes inside the soul would break the SYSTEM """..."""
# block. system_prompt.md uses single backticks for code, not triple quotes,
# so we just sanity-check.
if grep -q '"""' "$SOUL"; then
    echo "✗ system_prompt.md contains triple quotes — would break Modelfile SYSTEM block" >&2
    echo "  Refactor those quotes before rebuilding" >&2
    exit 1
fi

# Python does the substitution (sed can't easily handle multi-line replacements
# with arbitrary content)
python3 - "$TEMPLATE" "$SOUL" "$BUILT" <<'PY_EOF'
import sys
template_path, soul_path, output_path = sys.argv[1:4]
template = open(template_path).read()
soul = open(soul_path).read().rstrip()
out = template.replace("SYSTEM_PROMPT_PLACEHOLDER", soul)
open(output_path, "w").write(out)
print(f"  ✓ Wrote {output_path} ({len(out)} chars)")
PY_EOF

echo "  ⟳ Building $MODEL_NAME (this takes ~30s on Pi 5)..."
ollama create "$MODEL_NAME" -f "$BUILT"

echo ""
echo "  ✓ Built $MODEL_NAME"
ollama list | grep -E "NAME|$MODEL_NAME" | head -3
echo ""
echo "  Try it:"
echo "    ollama run $MODEL_NAME \"explain CIS Control 6\""
