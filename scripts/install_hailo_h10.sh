#!/bin/bash
# ╔═════════════════════════════════════════════════════════════════╗
# ║  ERR0RS — Hailo-10H PCIe Driver Install                        ║
# ║  For Kali Linux on Raspberry Pi 5 + M.2 HAT+                  ║
# ║  Kernel 6.12.75+rpt-rpi-2712 (and future kernels via DKMS)    ║
# ║  Run: sudo bash scripts/install_hailo_h10.sh                   ║
# ╚═════════════════════════════════════════════════════════════════╝
set -e
GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; NC='\033[0m'
KERN=$(uname -r)

echo -e "${CYAN}"
echo "  ██╗  ██╗ █████╗ ██╗██╗      ██████╗"
echo "  ██║  ██║██╔══██╗██║██║     ██╔═══██╗"
echo "  ███████║███████║██║██║     ██║   ██║"
echo "  ██╔══██║██╔══██║██║██║     ██║   ██║"
echo "  ██║  ██║██║  ██║██║███████╗╚██████╔╝"
echo -e "  Hailo-10H NPU Driver Install${NC}"
echo ""
echo -e "  Kernel : ${KERN}"
echo -e "  PCI    : $(lspci | grep -i hailo 2>/dev/null || echo 'not detected yet')"
echo ""

# ── 1. Kernel headers ────────────────────────────────────────────────────────
echo -e "${CYAN}[1/4] Installing kernel headers...${NC}"
apt-get install -y "linux-headers-${KERN}" linux-headers-rpi-2712 build-essential dkms 2>/dev/null \
    && echo -e "  ${GREEN}✓ Headers ready${NC}"

# ── 2. Install h10-hailort-pcie-driver ──────────────────────────────────────
echo -e "${CYAN}[2/4] Installing h10-hailort-pcie-driver...${NC}"
# Remove old conflicting package if present
apt-get remove -y hailort-pcie-driver 2>/dev/null || true
apt-get install -y h10-hailort-pcie-driver \
    && echo -e "  ${GREEN}✓ Package installed${NC}"

# ── 3. DKMS build for current kernel ─────────────────────────────────────────
echo -e "${CYAN}[3/4] Building DKMS module for ${KERN}...${NC}"
DKMS_INFO=$(dkms status 2>/dev/null | grep -i "hailo\|h10" | head -1 || true)

if [ -n "$DKMS_INFO" ]; then
    # Parse: "modulename/version, kernelver, arch: installed/built/..."
    MOD=$(echo "$DKMS_INFO" | awk -F',' '{print $1}' | tr -d ' ')
    NAME=$(echo "$MOD" | cut -d'/' -f1)
    VER=$(echo "$MOD"  | cut -d'/' -f2)
    echo -e "  Module: ${NAME} v${VER}"

    # Remove any stale install for this kernel then rebuild
    dkms remove "${NAME}/${VER}" -k "${KERN}" --all 2>/dev/null || true
    dkms build   "${NAME}/${VER}" -k "${KERN}" \
        && dkms install "${NAME}/${VER}" -k "${KERN}" \
        && echo -e "  ${GREEN}✓ DKMS build + install OK${NC}"
else
    echo -e "  ${YELLOW}! DKMS module not registered — trying manual search...${NC}"
    # The package may have put source in /usr/src/hailo* or /usr/src/h10*
    DKMS_SRC=$(find /usr/src -maxdepth 1 -name "hailo*" -o -name "h10*" 2>/dev/null | head -1)
    if [ -z "$DKMS_SRC" ]; then
        echo -e "  ${RED}✗ No DKMS source found. The package may not have extracted correctly.${NC}"
        echo -e "  Try: sudo apt-get install --reinstall h10-hailort-pcie-driver"
        exit 1
    fi
    BASE=$(basename "$DKMS_SRC")
    NAME=${BASE%-*}
    VER=${BASE##*-}
    dkms add "$DKMS_SRC"           2>/dev/null || true
    dkms build   "${NAME}/${VER}" -k "${KERN}" \
        && dkms install "${NAME}/${VER}" -k "${KERN}" \
        && echo -e "  ${GREEN}✓ DKMS build + install OK${NC}"
fi

# ── 4. Load module and verify ─────────────────────────────────────────────────
echo -e "${CYAN}[4/4] Loading driver and verifying...${NC}"
sleep 1

MOD_LOADED=false
for MOD_NAME in hailo1x_pci hailo_pci; do
    if modprobe "$MOD_NAME" 2>/dev/null; then
        echo -e "  ${GREEN}✓ Loaded: ${MOD_NAME}${NC}"
        MOD_LOADED=true
        # Persist across boots
        if ! grep -q "$MOD_NAME" /etc/modules 2>/dev/null; then
            echo "$MOD_NAME" >> /etc/modules
            echo -e "  ${GREEN}✓ Added ${MOD_NAME} to /etc/modules (auto-load at boot)${NC}"
        fi
        break
    fi
done

if [ "$MOD_LOADED" = false ]; then
    echo -e "  ${YELLOW}! modprobe failed. Checking for module file...${NC}"
    find /lib/modules/"${KERN}" -name "*hailo*" 2>/dev/null
    echo -e "  ${YELLOW}A reboot may be required.${NC}"
fi

# ── Check /dev/hailo ─────────────────────────────────────────────────────────
sleep 1
if ls /dev/hailo* &>/dev/null; then
    echo -e "  ${GREEN}✓ /dev/hailo* present${NC}"
    ls -la /dev/hailo*
else
    echo -e "  ${YELLOW}! /dev/hailo* not present — reboot may be needed${NC}"
fi

# ── hailortcli identify ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}[*] Running: hailortcli fw-control identify${NC}"
if hailortcli fw-control identify; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  Hailo-10H NPU — ONLINE AND VERIFIED ✓  ║${NC}"
    echo -e "${GREEN}║  ERR0RS NPU light should now be GREEN   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
else
    echo ""
    echo -e "${YELLOW}╔══════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  hailortcli returned non-zero            ║${NC}"
    echo -e "${YELLOW}║  Action required:                        ║${NC}"
    echo -e "${YELLOW}║    sudo reboot                           ║${NC}"
    echo -e "${YELLOW}║  Then: hailortcli fw-control identify    ║${NC}"
    echo -e "${YELLOW}╚══════════════════════════════════════════╝${NC}"
fi
