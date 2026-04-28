#!/usr/bin/env bash
# Clones upstream submodules listed in .gitmodules
set -e
cd "$(dirname "$(realpath "$0")")/.."
echo "[*] Initializing submodules (this will take a while)..."
git submodule update --init --recursive --depth=1
echo "[*] Stripping copyrighted media + huge files..."
find knowledge -type f \( -name "*.wav" -o -name "*.mp3" -o -name "*.mp4" -o -name "*.flac" -o -name "*.m4a" \) -delete 2>/dev/null || true
find knowledge -type f -size +50M -delete 2>/dev/null || true
echo "[+] Knowledge ready."
