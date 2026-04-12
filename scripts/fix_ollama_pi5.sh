#!/usr/bin/env bash
# ERR0RS — Pi 5 Ollama Setup & Fix Script
# Builds a Pi-optimized ERR0RS model and creates swap
# Run: bash scripts/fix_ollama_pi5.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELFILE="$REPO_ROOT/configs/Modelfile.pi5"
MODEL_NAME="err0rs-pi5"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ERR0RS — Ollama Pi 5 Fix & Optimization Script     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── 1. Swap ───────────────────────────────────────────────────────────────────
echo "[1/4] Checking swap..."
if swapon --show | grep -q swapfile; then
    echo "  ✅ Swap already active: $(free -h | awk '/Swap/{print $2}')"
else
    echo "  Creating 8GB swapfile on NVMe (fast I/O)..."
    fallocate -l 8G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "  ✅ Swap active: $(free -h | awk '/Swap/{print $2}')"

    # Make permanent across reboots
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        echo "  ✅ Added to /etc/fstab (survives reboot)"
    fi
fi

# ── 2. Swappiness tuning ──────────────────────────────────────────────────────
echo ""
echo "[2/4] Tuning kernel swap behavior..."
# swappiness=10 = only swap under heavy pressure (good for inference)
sysctl -w vm.swappiness=10 > /dev/null
if ! grep -q 'vm.swappiness' /etc/sysctl.conf; then
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi
# vfs_cache_pressure=50 = keep file cache longer (benefits Ollama model loads)
sysctl -w vm.vfs_cache_pressure=50 > /dev/null
if ! grep -q 'vfs_cache_pressure' /etc/sysctl.conf; then
    echo 'vm.vfs_cache_pressure=50' >> /etc/sysctl.conf
fi
echo "  ✅ swappiness=10, vfs_cache_pressure=50"

# ── 3. Build Pi-optimized ERR0RS model ───────────────────────────────────────
echo ""
echo "[3/4] Building Pi 5-optimized ERR0RS model..."
echo "  Base: qwen2.5-coder:7b"
echo "  Tuning: num_ctx=2048, num_predict=1024, num_thread=4"
echo ""

if ollama list | grep -q "^${MODEL_NAME}"; then
    echo "  Removing old ${MODEL_NAME}..."
    ollama rm "$MODEL_NAME" 2>/dev/null || true
fi

ollama create "$MODEL_NAME" -f "$MODELFILE"
echo "  ✅ Model '${MODEL_NAME}' created"

# ── 4. Update ERR0RS .env ─────────────────────────────────────────────────────
echo ""
echo "[4/4] Updating ERR0RS config..."
ENV_FILE="$REPO_ROOT/.env"

# Update OLLAMA_MODEL to use our optimized variant
if grep -q '^OLLAMA_MODEL=' "$ENV_FILE"; then
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=${MODEL_NAME}|" "$ENV_FILE"
else
    echo "OLLAMA_MODEL=${MODEL_NAME}" >> "$ENV_FILE"
fi

# Set context window explicitly
if grep -q '^OLLAMA_NUM_CTX=' "$ENV_FILE"; then
    sed -i "s|^OLLAMA_NUM_CTX=.*|OLLAMA_NUM_CTX=2048|" "$ENV_FILE"
else
    echo "OLLAMA_NUM_CTX=2048" >> "$ENV_FILE"
fi

echo "  ✅ .env updated: OLLAMA_MODEL=${MODEL_NAME}"

# ── Smoke test ────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Running smoke test...                               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

RESPONSE=$(curl -s http://localhost:11434/api/generate \
    -d "{\"model\":\"${MODEL_NAME}\",\"prompt\":\"Reply with: ERR0RS ONLINE\",\"stream\":false,\"options\":{\"num_predict\":10}}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','ERROR'))" 2>&1)

if echo "$RESPONSE" | grep -qi "ERR0RS\|online\|error" ; then
    echo "  ✅ Smoke test passed: $RESPONSE"
else
    echo "  ⚠️  Unexpected response: $RESPONSE"
fi

echo ""
free -h
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  ALL DONE — ERR0RS Ollama Pi 5 fix complete          ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Model   : ${MODEL_NAME}                    "
echo "║  Swap    : 8GB (NVMe — fast)                        ║"
echo "║  Context : 2048 tokens (saves ~800MB RAM)           ║"
echo "║  Threads : 4 (Pi 5 physical cores)                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
