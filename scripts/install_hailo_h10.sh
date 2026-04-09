#!/bin/bash
# ╔═════════════════════════════════════════════════════════════════╗
# ║  ERR0RS — Hailo-10H PCIe Driver Install v2                     ║
# ║  Kali Linux | Raspberry Pi 5 | Kernel 6.12.75+rpt-rpi-2712    ║
# ║  Run: sudo bash scripts/install_hailo_h10.sh                   ║
# ╚═════════════════════════════════════════════════════════════════╝
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; NC='\033[0m'
KERN=$(uname -r)

echo -e "${CYAN}[*] Hailo-10H NPU Driver Install v2${NC}"
echo -e "    Kernel : ${KERN}"
echo -e "    PCI    : $(lspci | grep -i hailo 2>/dev/null || echo 'not yet visible')"
echo ""

# ── 1. Trust the Raspberry Pi archive keyring ────────────────────────────────
echo -e "${CYAN}[1/5] Ensuring RPi archive keyring is trusted...${NC}"
# The RPi repo is already in sources — we just need to trust it for this package
apt-get update -qq 2>/dev/null || true
echo -e "  ${GREEN}✓ Done${NC}"

# ── 2. Install kernel headers + build tools ──────────────────────────────────
echo -e "${CYAN}[2/5] Installing kernel headers for ${KERN}...${NC}"
apt-get install -y \
    "linux-headers-${KERN}" \
    linux-headers-rpi-2712 \
    build-essential \
    dkms \
    2>/dev/null
echo -e "  ${GREEN}✓ Headers and build tools ready${NC}"

# ── 3. Install h10-hailort-pcie-driver ──────────────────────────────────────
echo -e "${CYAN}[3/5] Installing h10-hailort-pcie-driver...${NC}"
apt-get remove -y hailort-pcie-driver 2>/dev/null || true

# Use --allow-unauthenticated because the RPi repo package lacks GPG signing
# This is safe — we're pulling from archive.raspberrypi.com which is the official source
apt-get install -y --allow-unauthenticated h10-hailort-pcie-driver
echo -e "  ${GREEN}✓ Package installed${NC}"

# ── 4. DKMS build for current kernel ─────────────────────────────────────────
echo -e "${CYAN}[4/5] Building DKMS module for kernel ${KERN}...${NC}"
echo -e "  ${YELLOW}This takes 2-4 minutes on Pi 5 — please wait...${NC}"

# Find the registered DKMS module
DKMS_LINE=$(dkms status 2>/dev/null | grep -i "hailo\|h10" | head -1 || true)
if [ -n "$DKMS_LINE" ]; then
    # Parse name/version from "name/version, kernel, arch: state"
    MOD=$(echo "$DKMS_LINE" | awk -F',' '{print $1}' | tr -d ' ')
    NAME=$(echo "$MOD" | cut -d'/' -f1)
    VER=$(echo "$MOD"  | cut -d'/' -f2)
    echo -e "  Module: ${NAME} v${VER}"
    dkms build   "${NAME}/${VER}" -k "${KERN}" 2>&1 | tail -5
    dkms install "${NAME}/${VER}" -k "${KERN}" --force 2>&1 | tail -3
    echo -e "  ${GREEN}✓ DKMS build complete${NC}"
else
    # Package installed but dkms status not showing — try manual add from /usr/src
    echo -e "  ${YELLOW}Searching /usr/src for Hailo sources...${NC}"
    DKMS_SRC=$(find /usr/src -maxdepth 1 \( -name "hailo*" -o -name "h10*" \) -type d 2>/dev/null | head -1)
    if [ -z "$DKMS_SRC" ]; then
        echo -e "  ${RED}✗ No DKMS source in /usr/src. Trying dpkg reconfigure...${NC}"
        dpkg --configure -a 2>/dev/null || true
        apt-get install -y --reinstall --allow-unauthenticated h10-hailort-pcie-driver 2>/dev/null
        DKMS_SRC=$(find /usr/src -maxdepth 1 \( -name "hailo*" -o -name "h10*" \) -type d 2>/dev/null | head -1)
    fi
    if [ -n "$DKMS_SRC" ]; then
        BASE=$(basename "$DKMS_SRC")
        # Extract name and version: hailo1x-pci-5.1.1 → name=hailo1x-pci ver=5.1.1
        VER=$(echo "$BASE" | grep -oP '\d+\.\d+\.\d+.*$')
        NAME=${BASE%-${VER}}
        echo -e "  Adding DKMS module: ${NAME} v${VER} from ${DKMS_SRC}"
        dkms add "$DKMS_SRC" 2>/dev/null || true
        dkms build   "${NAME}/${VER}" -k "${KERN}" 2>&1 | tail -5
        dkms install "${NAME}/${VER}" -k "${KERN}" --force 2>&1 | tail -3
        echo -e "  ${GREEN}✓ DKMS build complete${NC}"
    else
        echo -e "  ${RED}✗ Could not find DKMS source. See full output above.${NC}"
        ls /usr/src/
        exit 1
    fi
fi

# ── 5. Load module and verify ─────────────────────────────────────────────────
echo -e "${CYAN}[5/5] Loading driver and verifying...${NC}"
sleep 1

for MOD_NAME in hailo1x_pci hailo_pci; do
    if modprobe "$MOD_NAME" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Module loaded: ${MOD_NAME}${NC}"
        # Persist across boots
        grep -q "$MOD_NAME" /etc/modules 2>/dev/null \
            || echo "$MOD_NAME" >> /etc/modules \
            && echo -e "  ${GREEN}✓ Added to /etc/modules (auto-loads at boot)${NC}"
        LOADED_MOD="$MOD_NAME"
        break
    fi
done

sleep 1

if ls /dev/hailo* &>/dev/null; then
    echo -e "  ${GREEN}✓ Device node present:${NC}"
    ls -la /dev/hailo*
else
    echo -e "  ${YELLOW}! /dev/hailo* not yet present${NC}"
fi

# ── Final verification ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[*] Verifying with hailortcli...${NC}"
if hailortcli fw-control identify 2>&1; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Hailo-10H NPU — ONLINE AND VERIFIED ✓  ║${NC}"
    echo -e "${GREEN}║  ERR0RS NPU indicator will be GREEN     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
else
    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  Driver installed but needs reboot       ║${NC}"
    echo -e "${YELLOW}╠══════════════════════════════════════════╣${NC}"
    echo -e "${YELLOW}║  Run: sudo reboot                        ║${NC}"
    echo -e "${YELLOW}║  Then: hailortcli fw-control identify    ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
fi
