#!/bin/bash
# =============================================================================
# ERR0RS ULTIMATE — Phoenix-OS Image Builder v2.0
# Pi 5 + Hailo-10H + ERR0RS
# Self-healing: auto-detects latest Kali ARM64, validates before extract
# Usage: sudo bash scripts/build_pi_image.sh
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$HOME/Phoenix-OS/build"
MOUNT_DIR="/tmp/phoenix_pi_mount"
OUTPUT_IMG="$REPO_DIR/ERR0RS-Phoenix-Pi5.img"
IMG_SIZE_GB=16
KALI_ARM_INDEX="https://kali.download/arm-images/"

RED='\033[0;31m'; GREEN='\033[0;32m'; PURPLE='\033[0;35m'
CYAN='\033[0;36m'; YELLOW='\033[1;33m'; ORANGE='\033[0;33m'; NC='\033[0m'

log()     { echo -e "${GREEN}[+]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
err()     { echo -e "${RED}[-]${NC} $1"; exit 1; }
info()    { echo -e "${CYAN}[*]${NC} $1"; }
section() { echo -e "\n${ORANGE}╔══ $1 ══╗${NC}"; }

print_banner() {
  echo -e "${ORANGE}"
  cat << 'BANNER'
 ██████╗ ██╗  ██╗ ██████╗ ███████╗███╗   ██╗██╗██╗  ██╗
 ██╔══██╗██║  ██║██╔═══██╗██╔════╝████╗  ██║██║╚██╗██╔╝
 ██████╔╝███████║██║   ██║█████╗  ██╔██╗ ██║██║ ╚███╔╝
 ██╔═══╝ ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║██║ ██╔██╗
 ██║     ██║  ██║╚██████╔╝███████╗██║ ╚████║██║██╔╝ ██╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═╝
BANNER
  echo -e "${CYAN}  Image Builder v2.0 | Pi 5 + Hailo-10H + ERR0RS${NC}"
  echo -e "${YELLOW}  Self-Healing Kali ARM Downloader${NC}\n"
}


# =============================================================================
# STEP 0 — Preflight checks
# =============================================================================
check_root() {
  [ "$EUID" -eq 0 ] || err "Run as root: sudo bash scripts/build_pi_image.sh"
}

install_build_deps() {
  section "CHECK] Verifying build dependencies"
  apt install -y \
    qemu-user-static binfmt-support \
    kpartx parted dosfstools e2fsprogs \
    rsync wget curl xz-utils xxd \
    2>/dev/null || true
  update-binfmts --enable qemu-aarch64 2>/dev/null || true
  log "Dependencies OK"
}

# =============================================================================
# STEP 1 — Self-Healing Kali ARM64 Downloader
# =============================================================================
detect_latest_kali_version() {
  info "Probing Kali ARM index for latest Pi5 image..."
  LATEST_VER=$(curl -s --max-time 15 "$KALI_ARM_INDEX" \
    | grep -oP 'kali-\d{4}\.\d+' \
    | sort -V \
    | tail -1)
  [ -z "$LATEST_VER" ] && err "Could not detect Kali version from index. Check internet."
  log "Latest detected version: $LATEST_VER"
  echo "$LATEST_VER"
}

build_image_url() {
  local ver="$1"
  local ver_num="${ver#kali-}"
  echo "${KALI_ARM_INDEX}${ver}/kali-linux-${ver_num}-raspberry-pi5-arm64.img.xz"
}

validate_xz() {
  local filepath="$1"
  local magic
  magic=$(xxd -p -l 6 "$filepath" 2>/dev/null || echo "")
  [ "$magic" = "fd377a585a00" ] && return 0 || return 1
}


download_base_image() {
  section "1/6] Downloading Kali ARM64 base image"
  mkdir -p "$BUILD_DIR"

  local KALI_VER IMG_URL IMG_PATH EXTRACTED
  KALI_VER=$(detect_latest_kali_version)
  IMG_URL=$(build_image_url "$KALI_VER")
  IMG_PATH="$BUILD_DIR/kali-base.img.xz"

  info "Target URL: $IMG_URL"

  # Cache validation — nuke corrupt/empty files
  if [ -f "$IMG_PATH" ]; then
    local filesize
    filesize=$(stat -c%s "$IMG_PATH" 2>/dev/null || echo 0)
    if [ "$filesize" -lt 1000000 ]; then
      warn "Cached file too small (${filesize} bytes) — corrupt. Removing..."
      rm -f "$IMG_PATH"
    elif ! validate_xz "$IMG_PATH"; then
      warn "Failed XZ magic byte check — not a valid archive. Removing..."
      rm -f "$IMG_PATH"
    else
      log "Base image already downloaded and verified ✓"
    fi
  fi

  # Download if still missing
  if [ ! -f "$IMG_PATH" ]; then
    log "Downloading Kali ARM64 Pi5 (~1.2GB)..."
    wget --show-progress --tries=3 --timeout=60 -O "$IMG_PATH" "$IMG_URL"
    if ! validate_xz "$IMG_PATH"; then
      rm -f "$IMG_PATH"
      err "Downloaded file failed XZ validation — URL may be wrong or download incomplete."
    fi
    log "Download verified ✓"
  fi

  EXTRACTED="${IMG_PATH%.xz}"
  if [ ! -f "$EXTRACTED" ]; then
    log "Extracting..."
    xz -dk "$IMG_PATH"
    log "Extraction complete ✓"
  else
    log "Extracted image present — skipping decompression"
  fi

  echo "$EXTRACTED"
}


# =============================================================================
# STEP 2 — Expand image
# =============================================================================
expand_image() {
  local img="$1"
  section "2/6] Expanding image to ${IMG_SIZE_GB}GB"
  cp "$img" "$OUTPUT_IMG"
  truncate -s "${IMG_SIZE_GB}G" "$OUTPUT_IMG"
  parted "$OUTPUT_IMG" resizepart 2 100% 2>/dev/null || true
  log "Image expanded: $OUTPUT_IMG"
}

# =============================================================================
# STEP 3 — Mount
# =============================================================================
mount_image() {
  section "3/6] Mounting image partitions"
  mkdir -p "$MOUNT_DIR/boot" "$MOUNT_DIR/root"
  LOOP=$(losetup -f --show -P "$OUTPUT_IMG")
  log "Loop device: $LOOP"
  sleep 1
  mount "${LOOP}p1" "$MOUNT_DIR/boot"
  mount "${LOOP}p2" "$MOUNT_DIR/root"
  cp /usr/bin/qemu-aarch64-static "$MOUNT_DIR/root/usr/bin/"
  echo "$LOOP"
}

# =============================================================================
# STEP 4 — Chroot setup
# =============================================================================
chroot_setup() {
  local loop="$1"
  section "4/6] Chroot: baking ERR0RS into image"

  log "Syncing ERR0RS-Ultimate repo into image..."
  rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$REPO_DIR/" "$MOUNT_DIR/root/opt/ERR0RS-Ultimate/"

  cat > "$MOUNT_DIR/root/tmp/setup_errorz.sh" <<'CHROOT'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[ERR0RS] Updating packages..."
apt update -qq

echo "[ERR0RS] Installing dependencies..."
apt install -y \
  python3 python3-pip python3-venv python3-dev git curl wget \
  nmap hydra hashcat aircrack-ng sqlmap nikto gobuster \
  postgresql redis-server \
  python3-pyqt5 libssl-dev libffi-dev build-essential \
  i2c-tools spi-tools xxd

# Hailo-10H NPU — PCIe config
echo "[ERR0RS] Configuring Hailo-10H NPU PCIe..."
echo "dtparam=pciex1" >> /boot/firmware/config.txt
echo "dtparam=pciex1_gen=3" >> /boot/firmware/config.txt
echo "dtoverlay=pciex1-compat-pi5,no-mip" >> /boot/firmware/config.txt

echo "[ERR0RS] Setting up Python venv..."
cd /opt/ERR0RS-Ultimate
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install websockets aiohttp --quiet


echo "[ERR0RS] Installing systemd service..."
cat > /etc/systemd/system/errorz.service <<SERVICE
[Unit]
Description=ERR0RS AI Pentest Assistant — Phoenix OS
After=network.target graphical.target

[Service]
Type=simple
User=kali
WorkingDirectory=/opt/ERR0RS-Ultimate
ExecStart=/opt/ERR0RS-Ultimate/venv/bin/python3 src/ui/errorz_launcher.py
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=graphical.target
SERVICE

systemctl enable errorz.service

echo "[ERR0RS] Writing .env..."
cat > /opt/ERR0RS-Ultimate/.env <<ENV
UI_HOST=127.0.0.1
UI_PORT=8765
DB_URL=postgresql://errorz:err0rs_secure@localhost/errorz
REDIS_URL=redis://localhost:6379
HAILO_ENABLED=true
PI5_MODE=true
OLLAMA_MODEL=qwen2.5-coder:7b
ENV

echo "phoenix" > /etc/hostname
sed -i 's/kali/phoenix/g' /etc/hosts
echo "kali:err0rs" | chpasswd
chown -R kali:kali /opt/ERR0RS-Ultimate

echo "[ERR0RS] Chroot setup complete ✓"
CHROOT

  chmod +x "$MOUNT_DIR/root/tmp/setup_errorz.sh"
  log "Running chroot (takes a few minutes)..."
  chroot "$MOUNT_DIR/root" /tmp/setup_errorz.sh 2>&1
  rm -f "$MOUNT_DIR/root/tmp/setup_errorz.sh"
  log "Chroot complete ✓"
}


# =============================================================================
# STEP 5 — Unmount & finalize
# =============================================================================
unmount_image() {
  local loop="$1"
  section "5/6] Finalizing image"
  rm -f "$MOUNT_DIR/root/usr/bin/qemu-aarch64-static"
  sync
  umount "$MOUNT_DIR/boot" 2>/dev/null || true
  umount "$MOUNT_DIR/root" 2>/dev/null || true
  losetup -d "$loop" 2>/dev/null || true
  log "Image finalized ✓"
}

# =============================================================================
# STEP 6 — Flash instructions
# =============================================================================
print_complete() {
  echo ""
  echo -e "${PURPLE}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${PURPLE}║    ERR0RS PHOENIX OS — BUILD COMPLETE  ✓                 ║${NC}"
  echo -e "${PURPLE}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${CYAN}Image:${NC}  $OUTPUT_IMG"
  echo -e "${CYAN}Size:${NC}   ${IMG_SIZE_GB}GB"
  echo ""
  echo -e "${YELLOW}── FLASH TO NVME ──────────────────────────────────────────${NC}"
  echo "  Option A — Raspberry Pi Imager (Windows):"
  echo "    Choose OS → Use Custom → ERR0RS-Phoenix-Pi5.img"
  echo ""
  echo "  Option B — CLI (replace /dev/sdX):"
  echo -e "    ${GREEN}sudo dd if=$OUTPUT_IMG of=/dev/sdX bs=4M status=progress conv=fsync${NC}"
  echo ""
  echo -e "${YELLOW}── FIRST BOOT ─────────────────────────────────────────────${NC}"
  echo "    Hostname: phoenix"
  echo "    User:     kali  |  Pass: err0rs"
  echo "    ERR0RS:   http://localhost:8765"
  echo ""
  echo -e "${CYAN}Knowledge, Integrity, Security.${NC}\n"
}

# =============================================================================
# MAIN
# =============================================================================
main() {
  print_banner
  check_root
  install_build_deps
  BASE=$(download_base_image)
  expand_image "$BASE"
  LOOP=$(mount_image)
  chroot_setup "$LOOP"
  unmount_image "$LOOP"
  print_complete
}

main
