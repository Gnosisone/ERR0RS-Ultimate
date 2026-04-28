#!/bin/bash
# ERR0RS — Hailo-10H NPU Setup Script for Kali Linux ARM64
# Raspberry Pi 5 + Raspberry Pi AI HAT+ 2
# Usage: sudo bash scripts/install_hailo.sh

set -e
RED='\033[0;31m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; PURPLE='\033[0;35m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

print_banner() {
  echo -e "${PURPLE}"
  echo "  ╔══════════════════════════════════════════════════╗"
  echo "  ║   ERR0RS — Hailo-10H NPU Setup                  ║"
  echo "  ║   Pi 5 AI HAT+ 2 | Kali Linux ARM64             ║"
  echo "  ╚══════════════════════════════════════════════════╝"
  echo -e "${NC}"
}

check_pi() {
  if ! grep -q "Raspberry Pi 5" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}[!] Not detected as Pi 5 — some steps may not apply${NC}"
  else
    echo -e "  ${GREEN}✓ Raspberry Pi 5 confirmed${NC}"
  fi
}

fix_pcie_config() {
  echo -e "${CYAN}[1/7] Configuring PCIe for Hailo-10H...${NC}"
  CONFIG="/boot/firmware/config.txt"
  [ ! -f "$CONFIG" ] && CONFIG="/boot/config.txt"
  grep -q "dtparam=pciex1$" "$CONFIG" || echo "dtparam=pciex1" >> "$CONFIG"
  grep -q "dtparam=pciex1_gen=3" "$CONFIG" || echo "dtparam=pciex1_gen=3" >> "$CONFIG"
  echo -e "  ${GREEN}✓ PCIe Gen3 enabled in $CONFIG${NC}"
}

remove_hailo8_driver() {
  echo -e "${CYAN}[2/7] Removing conflicting Hailo-8 driver (hailo_pci)...${NC}"
  modprobe -r hailo_pci 2>/dev/null || true
  KM="/lib/modules/$(uname -r)/updates/dkms/hailo_pci.ko"
  if [ -f "$KM" ]; then
    rm -f "$KM"; depmod -a
    echo -e "  ${GREEN}✓ Removed hailo_pci.ko${NC}"
  else
    echo -e "  ${GREEN}✓ hailo_pci not present (clean)${NC}"
  fi
}

fix_gcc() {
  echo -e "${CYAN}[3/7] Fixing GCC version for DKMS kernel module build...${NC}"
  # Kali ships gcc-14, Raspberry Pi kernel was built with gcc-12
  apt install -y gcc-12 g++-12 2>/dev/null || true
  update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 120 \
    --slave /usr/bin/g++ g++ /usr/bin/g++-12 2>/dev/null || true
  echo -e "  ${GREEN}✓ gcc-12 set as default for DKMS${NC}"
}


add_rpi_repo() {
  echo -e "${CYAN}[4/7] Adding Raspberry Pi apt repository...${NC}"
  mkdir -p /etc/apt/keyrings
  if [ ! -f "/etc/apt/keyrings/raspberrypi-archive-keyring.gpg" ]; then
    curl -fsSL https://archive.raspberrypi.com/debian/raspberrypi.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/raspberrypi-archive-keyring.gpg
  fi
  cat > /etc/apt/sources.list.d/raspberrypi.list << 'REPO'
deb [arch=arm64 signed-by=/etc/apt/keyrings/raspberrypi-archive-keyring.gpg] http://archive.raspberrypi.com/debian trixie main
REPO
  # Pin Hailo packages high, everything else low
  cat > /etc/apt/preferences.d/raspberrypi-hailo-pin << 'PIN'
Package: *
Pin: origin archive.raspberrypi.com
Pin-Priority: 1

Package: h10-hailort-pcie-driver h10-hailort hailort hailort-* libhailort* hailo*
Pin: origin archive.raspberrypi.com
Pin-Priority: 1001
PIN
  apt update -qq
  echo -e "  ${GREEN}✓ RPi repo added, Hailo packages pinned${NC}"
}

install_hailo_driver() {
  echo -e "${CYAN}[5/7] Installing Hailo-10H driver + HailoRT runtime...${NC}"
  apt install -y dkms linux-headers-rpi-2712 2>/dev/null || apt install -y dkms 2>/dev/null || true
  apt install -y h10-hailort-pcie-driver h10-hailort
  # Install Python bindings
  pip install hailort --break-system-packages -q 2>/dev/null || \
  pip3 install hailort --break-system-packages -q 2>/dev/null || \
    echo -e "  ${YELLOW}~ pip install hailort failed — download from hailo.ai Developer Zone${NC}"
  echo -e "  ${GREEN}✓ hailo1x_pci driver + HailoRT installed${NC}"
}

install_hailo_apps() {
  echo -e "${CYAN}[6/7] Installing hailo-apps (hailo-ollama GenAI server)...${NC}"
  apt install -y git python3-venv 2>/dev/null || true
  if [ ! -d "/opt/hailo-apps" ]; then
    git clone --depth=1 https://github.com/hailo-ai/hailo-apps.git /opt/hailo-apps
  else
    cd /opt/hailo-apps && git pull origin main 2>/dev/null || true
  fi

  # Set up venv for hailo-apps
  python3 -m venv /opt/hailo-apps/venv
  /opt/hailo-apps/venv/bin/pip install -e /opt/hailo-apps -q 2>/dev/null || true

  # Install GenAI model zoo package
  apt install -y hailo-gen-ai-model-zoo 2>/dev/null && \
    echo -e "  ${GREEN}✓ Hailo GenAI model zoo installed${NC}" || \
    echo -e "  ${YELLOW}~ Model zoo not in apt — models may be bundled in hailo-apps${NC}"

  echo -e "  ${GREEN}✓ hailo-apps installed at /opt/hailo-apps${NC}"
}

create_hailo_ollama_service() {
  echo -e "${CYAN}[7/7] Creating hailo-ollama systemd service...${NC}"
  cat > /etc/systemd/system/hailo-ollama.service << 'SERVICE'
[Unit]
Description=Hailo-10H NPU LLM Server (Ollama-compatible REST API on :8000)
After=network.target

[Service]
Type=simple
User=kali
WorkingDirectory=/opt/hailo-apps
ExecStart=/opt/hailo-apps/venv/bin/python -m hailo_apps.gen_ai_apps.hailo_ollama.server --port 8000
Restart=on-failure
RestartSec=5
Environment=HAILO_OLLAMA_PORT=8000

[Install]
WantedBy=multi-user.target
SERVICE

  systemctl daemon-reload
  systemctl enable hailo-ollama.service
  echo -e "  ${GREEN}✓ hailo-ollama.service enabled (starts on boot)${NC}"
}

print_summary() {
  echo ""
  echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║   HAILO-10H SETUP COMPLETE ✓                         ║${NC}"
  echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
  echo -e "${GREEN}║   REBOOT REQUIRED to load hailo1x_pci driver         ║${NC}"
  echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
  echo -e "${GREEN}║   After reboot, verify with:                         ║${NC}"
  echo -e "${GREEN}║     lspci | grep -i hailo                            ║${NC}"
  echo -e "${GREEN}║     lsmod | grep hailo                               ║${NC}"
  echo -e "${GREEN}║     hailortcli fw-control identify                   ║${NC}"
  echo -e "${GREEN}║     ls -la /dev/hailo0                               ║${NC}"
  echo -e "${GREEN}║                                                      ║${NC}"
  echo -e "${GREEN}║   Start the NPU LLM server:                          ║${NC}"
  echo -e "${GREEN}║     sudo systemctl start hailo-ollama                ║${NC}"
  echo -e "${GREEN}║                                                      ║${NC}"
  echo -e "${GREEN}║   Test inference:                                    ║${NC}"
  echo -e "${GREEN}║     curl http://localhost:8000/api/tags              ║${NC}"
  echo -e "${GREEN}║                                                      ║${NC}"
  echo -e "${GREEN}║   ERR0RS will auto-detect the NPU at startup         ║${NC}"
  echo -e "${GREEN}║   Check: http://127.0.0.1:8765/api/hailo?action=diagnose ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Main ─────────────────────────────────────────────────────────
[ "$EUID" -ne 0 ] && { echo "Run as root: sudo bash scripts/install_hailo.sh"; exit 1; }

print_banner
check_pi
fix_pcie_config
remove_hailo8_driver
fix_gcc
add_rpi_repo
install_hailo_driver
install_hailo_apps
create_hailo_ollama_service
print_summary

read -p "Reboot now to load hailo1x_pci driver? [Y/n]: " -n 1 -r
echo
[[ $REPLY =~ ^[Yy]$|^$ ]] && reboot || echo "Reboot when ready: sudo reboot"
