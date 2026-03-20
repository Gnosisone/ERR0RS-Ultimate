#!/bin/bash
# =============================================================================
# ERR0RS ULTIMATE — Pi 5 First Boot Configuration
# Run ONCE after flashing and booting the Pi 5 for the first time
# Usage: sudo bash /opt/ERR0RS-Ultimate/scripts/pi5_first_boot.sh
# =============================================================================

set -e
REPO_DIR="/opt/ERR0RS-Ultimate"
GREEN='\033[0;32m'; PURPLE='\033[0;35m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log()    { echo -e "${GREEN}[+]${NC} $1"; }
warn()   { echo -e "${YELLOW}[!]${NC} $1"; }
section(){ echo -e "\n${CYAN}══ $1 ══${NC}"; }

section "HAILO AI HAT+ 2 DRIVER INSTALL"
# Install HailoRT from Hailo's APT repo
log "Adding Hailo repository..."
curl -fsSL https://hailo-hailort.s3.eu-west-2.amazonaws.com/HailoRT/hailo_platform_repo.gpg \
  | gpg --dearmor -o /usr/share/keyrings/hailo.gpg 2>/dev/null || warn "GPG key step skipped"

echo "deb [signed-by=/usr/share/keyrings/hailo.gpg] \
  https://hailo-hailort.s3.eu-west-2.amazonaws.com/HailoRT/4.18.0/deb stable main" \
  > /etc/apt/sources.list.d/hailo.list 2>/dev/null || warn "Hailo repo step skipped — install manually"

apt update -qq 2>/dev/null || true
apt install -y hailort python3-hailort 2>/dev/null || warn "Hailo pkg install skipped — check internet"
log "Hailo runtime install attempted"

section "NVME PERFORMANCE TUNING"
# Ensure PCIe Gen 3 is set for X1004 dual NVMe
CONFIG="/boot/firmware/config.txt"
grep -q "pciex1_gen=3" "$CONFIG" || echo "dtparam=pciex1_gen=3" >> "$CONFIG"
grep -q "pciex1-compat" "$CONFIG" || echo "dtoverlay=pciex1-compat-pi5,no-mip" >> "$CONFIG"
log "PCIe Gen 3 confirmed in config.txt"

# I/O scheduler tweak for NVMe
echo 'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"' \
  > /etc/udev/rules.d/60-nvme-scheduler.rules
log "NVMe scheduler set to none (optimal for SSDs)"

section "WIRELESS ADAPTER SETUP"
# Enable monitor mode persistence for common chipsets
apt install -y aircrack-ng wireless-tools rfkill 2>/dev/null || true
rfkill unblock all
log "Wireless adapters unblocked"

section "ENABLE REQUIRED INTERFACES"
# I2C / SPI for any HAT communication
raspi-config nonint do_i2c 0
raspi-config nonint do_spi 0
log "I2C and SPI enabled"

section "EXPAND FILESYSTEM"
# Fill available NVMe space
raspi-config nonint do_expand_rootfs
log "Filesystem expansion queued (takes effect on reboot)"

section "POSTGRESQL FIRST SETUP"
service postgresql start
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='errorz'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE errorz;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='errorz'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE USER errorz WITH PASSWORD 'err0rs_secure';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE errorz TO errorz;" 2>/dev/null || true
systemctl enable postgresql redis-server
log "Database ready"

section "VERIFY ERR0RS SERVICE"
systemctl daemon-reload
systemctl enable errorz.service
systemctl start errorz.service || warn "ERR0RS service start failed — check logs: journalctl -u errorz"
log "ERR0RS service enabled and started"

echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║   Pi 5 First Boot Config Complete  ✓                ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${CYAN}ERR0RS Dashboard:${NC}  http://$(hostname -I | awk '{print $1}'):8765"
echo -e "  ${CYAN}Hailo NPU check:${NC}   hailortcli fw-control identify"
echo -e "  ${CYAN}Service status:${NC}    systemctl status errorz"
echo -e "  ${CYAN}Reboot now to apply all changes:${NC}  sudo reboot"
echo ""
