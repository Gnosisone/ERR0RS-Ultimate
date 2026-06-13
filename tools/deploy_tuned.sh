#!/usr/bin/env bash
# Convert a merged HF model -> GGUF -> quantize -> register with Ollama as err0rs-tuned.
# Needs a built llama.cpp (set LLAMA_CPP=/path/to/llama.cpp). Can run on the Pi.
set -euo pipefail
MERGED="${1:-err0rs-merged}"
LLAMA="${LLAMA_CPP:-$HOME/llama.cpp}"
GGUF="err0rs.gguf"; Q="err0rs-Q4_K_M.gguf"
python3 "$LLAMA/convert_hf_to_gguf.py" "$MERGED" --outfile "$GGUF"
"$LLAMA/llama-quantize" "$GGUF" "$Q" Q4_K_M
cat > Modelfile <<MF
FROM ./$Q
PARAMETER temperature 0.3
PARAMETER num_ctx 4096
SYSTEM "You are ERR0RS, a local offensive-security mentor. Teach clearly and insist on authorized, ethical, legal testing only."
MF
ollama create err0rs-tuned -f Modelfile
echo "done -> ollama run err0rs-tuned"
