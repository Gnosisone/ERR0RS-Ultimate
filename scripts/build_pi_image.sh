#!/bin/bash
# =============================================================================
# ERR0RS ULTIMATE — Step 2: Raspberry Pi 5 ISO/Image Builder
# Run this on your Kali VM AFTER deploy_kali_vm.sh succeeds
# Builds a flashable .img for the Pi 5 with ERR0RS pre-installed
# Usage: sudo bash scripts/build_pi_image.sh
# =============================================================================

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="/tmp/errorz_pi_build"
MOUNT_DIR="/tmp/errorz_pi_mount"
OUTPUT_IMG="$REPO_DIR/ERR0RS-Phoenix-Pi5.img"
IMG_SIZE_GB=16   # Set to match your NVMe partition target
BASE_URL="https://downloads.raspberrypi.com/raspios_lite_arm64/images"

RED='\033[0;31m'; GREEN='\033[0;32m'; PURPLE='\033[0;35m'
CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

log()    { echo -e "${GREEN}[+]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
err()    { echo -e "${RED}[-]${NC} $1"; exit 1; }
section(){ echo -e "\n${CYAN}══ $1 ══${NC}"; }

check_root() {
  [ "$EUID" -eq 0 ] || err "Run as root: sudo bash scripts/build_pi_image.sh"
}

install_build_deps() {
  section "Installing build tools"
  apt install -y \
    qemu-user-static binfmt-support \
    kpartx parted dosfstools e2fsprogs \
    rsync wget curl xz-utils \
    2>/dev/null || true
  update-binfmts --enable qemu-aarch64 2>/dev/null || true
  log "Build tools ready"
}

download_base_image() {
  section "Downloading Raspberry Pi OS Lite (ARM64)"
  mkdir -p "$BUILD_DIR"
  # Use Kali ARM64 for Pi instead if preferred — change URL here
  LATEST_IMG="2024-11-19-raspios-bookworm-arm64-lite.img.xz"
  IMG_PATH="$BUILD_DIR/$LATEST_IMG"
  if [ ! -f "$IMG_PATH" ]; then
    log "Downloading base image (~500MB)..."
    wget -q --show-progress \
      "$BASE_URL/raspios_lite_arm64-2024-11-19/$LATEST_IMG" \
      -O "$IMG_PATH"
  else
    warn "Base image already cached — skipping download"
  fi
  log "Decompressing..."
  xz -dk "$IMG_PATH"
  BASE_IMG="${IMG_PATH%.xz}"
  echo "$BASE_IMG"
}

expand_image() {
  local img="$1"
  section "Expanding image to ${IMG_SIZE_GB}GB"
  cp "$img" "$OUTPUT_IMG"
  truncate -s "${IMG_SIZE_GB}G" "$OUTPUT_IMG"
  # Expand the last partition to fill the space
  parted "$OUTPUT_IMG" resizepart 2 100% 2>/dev/null || true
  log "Image expanded: $OUTPUT_IMG"
}

mount_image() {
  section "Mounting image partitions"
  mkdir -p "$MOUNT_DIR/boot" "$MOUNT_DIR/root"
  LOOP=$(losetup -f --show -P "$OUTPUT_IMG")
  log "Loop device: $LOOP"
  sleep 1
  mount "${LOOP}p1" "$MOUNT_DIR/boot"
  mount "${LOOP}p2" "$MOUNT_DIR/root"
  # Enable QEMU ARM64 chroot
  cp /usr/bin/qemu-aarch64-static "$MOUNT_DIR/root/usr/bin/"
  echo "$LOOP"
}

chroot_setup() {
  local loop="$1"
  section "Chroot: installing ERR0RS inside image"

  # Copy repo into image
  log "Copying ERR0RS-Ultimate repo..."
  rsync -a --exclude='.git' --exclude='venv' --exclude='__pycache__' \
    "$REPO_DIR/" "$MOUNT_DIR/root/opt/ERR0RS-Ultimate/"

  # Write the chroot setup script
  cat > "$MOUNT_DIR/root/tmp/setup_errorz.sh" <<'CHROOT'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive

echo "[ERR0RS] Updating package lists..."
apt update -qq

echo "[ERR0RS] Installing core packages..."
apt install -y \
  python3 python3-pip python3-venv python3-dev git curl wget \
  nmap hydra hashcat aircrack-ng sqlmap nikto gobuster \
  postgresql redis-server chromium-browser \
  python3-pyqt5 libssl-dev libffi-dev build-essential \
  i2c-tools spi-tools

# Hailo AI HAT+ 2 support
echo "[ERR0RS] Adding Hailo PCIe support..."
echo "dtparam=pciex1" >> /boot/firmware/config.txt
echo "dtparam=pciex1_gen=3" >> /boot/firmware/config.txt

# PCIe splitter — enable both slots
echo "dtoverlay=pciex1-compat-pi5,no-mip" >> /boot/firmware/config.txt

echo "[ERR0RS] Setting up Python venv..."
cd /opt/ERR0RS-Ultimate
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install websockets aiohttp --quiet

echo "[ERR0RS] Configuring autostart..."
mkdir -p /etc/systemd/system
cat > /etc/systemd/system/errorz.service <<SERVICE
[Unit]
Description=ERR0RS AI Pentest Assistant
After=network.target graphical.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/ERR0RS-Ultimate
ExecStart=/opt/ERR0RS-Ultimate/venv/bin/python3 src/ui/errorz_launcher.py
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=graphical.target
SERVICE

systemctl enable errorz.service

echo "[ERR0RS] Creating .env..."
cat > /opt/ERR0RS-Ultimate/.env <<ENV
UI_HOST=127.0.0.1
UI_PORT=8765
DB_URL=postgresql://errorz:err0rs_secure@localhost/errorz
REDIS_URL=redis://localhost:6379
HAILO_ENABLED=true
PI5_MODE=true
ENV

# Set hostname
echo "phoenix" > /etc/hostname
sed -i 's/raspberrypi/phoenix/g' /etc/hosts

# Default user setup
useradd -m -s /bin/bash -G sudo,video,audio,plugdev,netdev pi 2>/dev/null || true
echo "pi:err0rs" | chpasswd
chown -R pi:pi /opt/ERR0RS-Ultimate

echo "[ERR0RS] Chroot setup complete ✓"
CHROOT

  chmod +x "$MOUNT_DIR/root/tmp/setup_errorz.sh"
  log "Running chroot setup (this takes a few minutes)..."
  chroot "$MOUNT_DIR/root" /tmp/setup_errorz.sh 2>&1
  rm "$MOUNT_DIR/root/tmp/setup_errorz.sh"
  log "Chroot setup complete"
}

unmount_image() {
  local loop="$1"
  section "Unmounting and finalizing"
  rm -f "$MOUNT_DIR/root/usr/bin/qemu-aarch64-static"
  umount "$MOUNT_DIR/boot" 2>/dev/null || true
  umount "$MOUNT_DIR/root" 2>/dev/null || true
  losetup -d "$loop" 2>/dev/null || true
  log "Image finalized: $OUTPUT_IMG"
}

print_flash_instructions() {
  echo ""
  echo -e "${PURPLE}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${PURPLE}║     ERR0RS Phoenix OS IMAGE BUILT SUCCESSFULLY  ✓       ║${NC}"
  echo -e "${PURPLE}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${CYAN}Image location:${NC} $OUTPUT_IMG"
  echo -e "${CYAN}Image size:${NC}     ${IMG_SIZE_GB}GB"
  echo ""
  echo -e "${YELLOW}── FLASH TO NVME/SD ──────────────────────────────────────${NC}"
  echo "  Option A (Raspberry Pi Imager):"
  echo "    1. Open Raspberry Pi Imager"
  echo "    2. Choose OS → Use Custom → select ERR0RS-Phoenix-Pi5.img"
  echo "    3. Choose your NVMe/SD card target"
  echo "    4. Click Write"
  echo ""
  echo "  Option B (command line — replace /dev/sdX with your device):"
  echo -e "    ${GREEN}sudo dd if=$OUTPUT_IMG of=/dev/sdX bs=4M status=progress conv=fsync${NC}"
  echo ""
  echo -e "${YELLOW}── FIRST BOOT ────────────────────────────────────────────${NC}"
  echo "    Default user: pi"
  echo "    Default pass: err0rs"
  echo "    ERR0RS UI:    http://localhost:8765"
  echo ""
  echo -e "${CYAN}Next step → Transfer .img to Windows via shared folder/USB${NC}"
  echo "  then flash with Raspberry Pi Imager on Windows"
}

main() {
  check_root
  install_build_deps
  BASE=$(download_base_image)
  expand_image "$BASE"
  LOOP=$(mount_image)
  chroot_setup "$LOOP"
  unmount_image "$LOOP"
  print_flash_instructions
}

main
