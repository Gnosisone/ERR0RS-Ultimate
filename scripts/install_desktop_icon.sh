#!/bin/bash
# ╔═══════════════════════════════════════════════════════════════╗
# ║       ERR0RS-Ultimate :: Desktop Icon Installer               ║
# ║                                                               ║
# ║  Creates desktop icons and app menu entries for all users.   ║
# ║  Supports: Kali Linux, Parrot OS, Ubuntu, Debian              ║
# ║  Desktop envs: XFCE, GNOME, KDE, LXDE, MATE                  ║
# ║                                                               ║
# ║  Usage:                                                        ║
# ║    sudo bash scripts/install_desktop_icon.sh  (all users)     ║
# ║    bash scripts/install_desktop_icon.sh       (current user)  ║
# ╚═══════════════════════════════════════════════════════════════╝

set -e
RED='\033[0;31m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ICON_DIR="$SCRIPT_DIR/assets/icons"
ICON_PNG="$ICON_DIR/err0rs.png"
ICON_SVG="$ICON_DIR/err0rs.svg"

echo -e "${RED}"
echo "  ██████╗ ██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
echo -e "${NC}  Desktop Icon Installer\n"

echo -e "${CYAN}[*] Desktop: ${NC}${XDG_CURRENT_DESKTOP:-unknown}"
echo -e "${CYAN}[*] Install dir: ${NC}$SCRIPT_DIR"
echo -e "${CYAN}[*] Running as: ${NC}$(whoami)\n"

# ── Generate PNG icons from SVG if not present ──────────────────
generate_icons() {
    mkdir -p "$ICON_DIR"
    echo -e "${CYAN}[*] Setting up icons...${NC}"

    # Repo already ships hyphenated PNG icons: err0rs-{16,32,48,64,128,256}.png
    # Use those directly; only fall back to SVG conversion if missing.
    # This avoids depending on cairosvg/ImageMagick/rsvg-convert at install time.

    # If we already have a usable icon, just point ICON_PNG at it.
    for cand in err0rs.png err0rs-256.png err0rs-128.png err0rs-64.png; do
        if [ -f "$ICON_DIR/$cand" ] && [ -s "$ICON_DIR/$cand" ]; then
            if [ "$cand" != "err0rs.png" ]; then
                cp "$ICON_DIR/$cand" "$ICON_PNG"
            fi
            echo -e "  ${GREEN}✓${NC} Using existing icon: $cand"
            echo -e "  ${GREEN}✓${NC} Main icon ready at $ICON_PNG"
            return 0
        fi
    done

    # No pre-built PNG found — fall back to SVG conversion.
    # Only proceed if SVG is a non-trivial file (>100 bytes — empty stubs are common).
    if [ ! -f "$ICON_SVG" ] || [ "$(stat -c%s "$ICON_SVG" 2>/dev/null || echo 0)" -lt 100 ]; then
        echo -e "  ${YELLOW}~${NC} No valid icon source found (SVG missing or stub)"
        echo -e "  ${YELLOW}~${NC} Desktop entries will use missing-icon fallback"
        return 0
    fi

    if python3 -c "import cairosvg" 2>/dev/null; then
        python3 - << PYEOF || true
import cairosvg, shutil, os
svg = open("$ICON_SVG").read()
for size in [16,24,32,48,64,128,256,512]:
    cairosvg.svg2png(bytestring=svg.encode(),
                     write_to=f"$ICON_DIR/err0rs-{size}.png",
                     output_width=size, output_height=size)
if os.path.exists(f"$ICON_DIR/err0rs-256.png"):
    shutil.copy("$ICON_DIR/err0rs-256.png", "$ICON_PNG")
print("PNGs generated via cairosvg")
PYEOF
    elif command -v convert &>/dev/null; then
        for size in 16 24 32 48 64 128 256 512; do
            convert "$ICON_SVG" -resize ${size}x${size} \
                "$ICON_DIR/err0rs-${size}.png" 2>/dev/null || true
        done
        [ -f "$ICON_DIR/err0rs-256.png" ] && cp "$ICON_DIR/err0rs-256.png" "$ICON_PNG"
        echo -e "  ${GREEN}✓ PNGs generated via ImageMagick${NC}"
    elif command -v rsvg-convert &>/dev/null; then
        for size in 16 24 32 48 64 128 256 512; do
            rsvg-convert -w $size -h $size "$ICON_SVG" \
                -o "$ICON_DIR/err0rs-${size}.png" 2>/dev/null || true
        done
        [ -f "$ICON_DIR/err0rs-256.png" ] && cp "$ICON_DIR/err0rs-256.png" "$ICON_PNG"
        echo -e "  ${GREEN}✓ PNGs generated via rsvg-convert${NC}"
    else
        cp "$ICON_SVG" "$ICON_PNG" 2>/dev/null || true
        echo -e "  ${YELLOW}~ No PNG converter found — using SVG as icon${NC}"
    fi
    echo -e "  ${GREEN}✓${NC} Icons ready in $ICON_DIR"
}

# ── Build .desktop file — main ERR0RS launcher ───────────────────
desktop_entry() {
    cat << EOF
[Desktop Entry]
Version=1.1
Type=Application
Name=ERR0RS Ultimate
GenericName=AI Penetration Testing Platform
Comment=AI-powered pentesting — MetasploitMCP | Kali 2026.1 | Local LLM
Exec=bash -c "cd $SCRIPT_DIR && bash start_err0rs.sh"
Icon=$ICON_PNG
Terminal=true
StartupNotify=true
Categories=Security;Network;System;
Keywords=pentest;hacking;metasploit;kali;offensive;recon;exploit;ai;mcp;
StartupWMClass=ERR0RS
X-GNOME-UsesNotifications=true
EOF
}

# ── Build .desktop file — Prompt Manual ──────────────────────────
manual_desktop_entry() {
    cat << EOF
[Desktop Entry]
Version=1.1
Type=Application
Name=ERR0RS Prompt Manual
GenericName=ERR0RS Prompting Guide
Comment=Interactive prompt instruction manual for ERR0RS-Ultimate
Exec=bash -c "cd $SCRIPT_DIR && bash open_manual.sh"
Icon=$ICON_PNG
Terminal=false
StartupNotify=true
Categories=Security;Documentation;
Keywords=pentest;hacking;prompting;manual;guide;err0rs;ai;
StartupWMClass=ERR0RS-Manual
EOF
}

# ── Install for current user ─────────────────────────────────────
install_user() {
    echo -e "${CYAN}[1/3] Installing for current user: $(whoami)${NC}"

    USER_APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    mkdir -p "$USER_APPS"
    desktop_entry > "$USER_APPS/err0rs-ultimate.desktop"
    chmod +x "$USER_APPS/err0rs-ultimate.desktop"
    echo -e "  ${GREEN}✓ App menu: $USER_APPS/err0rs-ultimate.desktop${NC}"

    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    mkdir -p "$DESKTOP_DIR"

    # Main ERR0RS launcher
    desktop_entry > "$DESKTOP_DIR/ERR0RS-Ultimate.desktop"
    chmod +x "$DESKTOP_DIR/ERR0RS-Ultimate.desktop"
    gio set "$DESKTOP_DIR/ERR0RS-Ultimate.desktop" \
        metadata::trusted true 2>/dev/null || true
    echo -e "  ${GREEN}✓ Desktop icon: $DESKTOP_DIR/ERR0RS-Ultimate.desktop${NC}"

    # Prompt Manual launcher
    manual_desktop_entry > "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop"
    chmod +x "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop"
    gio set "$DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop" \
        metadata::trusted true 2>/dev/null || true
    echo -e "  ${GREEN}✓ Manual icon: $DESKTOP_DIR/ERR0RS-Prompt-Manual.desktop${NC}"

    # Also add manual to app menu
    manual_desktop_entry > "$USER_APPS/err0rs-prompt-manual.desktop"
    chmod +x "$USER_APPS/err0rs-prompt-manual.desktop"

    update-desktop-database "$USER_APPS" 2>/dev/null || true
}

# ── Install system-wide (all users) — requires root ──────────────
install_system_wide() {
    echo -e "${CYAN}[2/3] Installing system-wide for all users...${NC}"

    # Install icon into hicolor theme (standard XDG)
    # Repo ships hyphenated filenames: err0rs-{16,32,48,64,128,256}.png
    for SIZE in 16 24 32 48 64 128 256 512; do
        HICOLOR_DIR="/usr/share/icons/hicolor/${SIZE}x${SIZE}/apps"
        mkdir -p "$HICOLOR_DIR"
        if [ -f "$ICON_DIR/err0rs-${SIZE}.png" ]; then
            cp "$ICON_DIR/err0rs-${SIZE}.png" \
               "$HICOLOR_DIR/err0rs-ultimate.png"
        fi
    done

    # Scalable SVG
    mkdir -p "/usr/share/icons/hicolor/scalable/apps"
    [ -f "$ICON_SVG" ] && \
        cp "$ICON_SVG" "/usr/share/icons/hicolor/scalable/apps/err0rs-ultimate.svg"

    echo -e "  ${GREEN}✓ Icons → /usr/share/icons/hicolor/${NC}"

    # System .desktop entry — main app
    desktop_entry > /usr/share/applications/err0rs-ultimate.desktop
    chmod 644 /usr/share/applications/err0rs-ultimate.desktop
    echo -e "  ${GREEN}✓ System app entry → /usr/share/applications/${NC}"

    # System .desktop entry — manual
    manual_desktop_entry > /usr/share/applications/err0rs-prompt-manual.desktop
    chmod 644 /usr/share/applications/err0rs-prompt-manual.desktop
    echo -e "  ${GREEN}✓ Manual app entry → /usr/share/applications/${NC}"

    # Desktop icon for every existing user
    echo -e "${CYAN}[3/3] Adding icons to all existing user desktops...${NC}"
    for USER_HOME in /home/*/; do
        USERNAME=$(basename "$USER_HOME")
        USER_DESKTOP="$USER_HOME/Desktop"
        mkdir -p "$USER_DESKTOP"

        # Main launcher
        desktop_entry > "$USER_DESKTOP/ERR0RS-Ultimate.desktop"
        chmod +x "$USER_DESKTOP/ERR0RS-Ultimate.desktop"
        chown "${USERNAME}:${USERNAME}" \
            "$USER_DESKTOP/ERR0RS-Ultimate.desktop" 2>/dev/null || true
        sudo -u "$USERNAME" gio set \
            "$USER_DESKTOP/ERR0RS-Ultimate.desktop" \
            metadata::trusted true 2>/dev/null || true

        # Manual launcher
        manual_desktop_entry > "$USER_DESKTOP/ERR0RS-Prompt-Manual.desktop"
        chmod +x "$USER_DESKTOP/ERR0RS-Prompt-Manual.desktop"
        chown "${USERNAME}:${USERNAME}" \
            "$USER_DESKTOP/ERR0RS-Prompt-Manual.desktop" 2>/dev/null || true
        sudo -u "$USERNAME" gio set \
            "$USER_DESKTOP/ERR0RS-Prompt-Manual.desktop" \
            metadata::trusted true 2>/dev/null || true

        # Also add both to their local app menus
        USER_APPS_DIR="$USER_HOME/.local/share/applications"
        mkdir -p "$USER_APPS_DIR"
        desktop_entry > "$USER_APPS_DIR/err0rs-ultimate.desktop"
        manual_desktop_entry > "$USER_APPS_DIR/err0rs-prompt-manual.desktop"
        chmod +x "$USER_APPS_DIR/err0rs-ultimate.desktop"
        chmod +x "$USER_APPS_DIR/err0rs-prompt-manual.desktop"
        chown -R "${USERNAME}:${USERNAME}" "$USER_APPS_DIR" 2>/dev/null || true

        echo -e "  ${GREEN}✓${NC} $USERNAME"
    done

    # /etc/skel — future new users get both icons automatically
    mkdir -p "/etc/skel/Desktop"
    desktop_entry > "/etc/skel/Desktop/ERR0RS-Ultimate.desktop"
    manual_desktop_entry > "/etc/skel/Desktop/ERR0RS-Prompt-Manual.desktop"
    chmod +x "/etc/skel/Desktop/ERR0RS-Ultimate.desktop"
    chmod +x "/etc/skel/Desktop/ERR0RS-Prompt-Manual.desktop"
    echo -e "  ${GREEN}✓ /etc/skel — new users get both icons automatically${NC}"

    # Refresh caches
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
    echo -e "  ${GREEN}✓ Icon cache refreshed${NC}"
}

# ── XFCE desktop reload ──────────────────────────────────────────
refresh_xfce() {
    if pgrep -x "xfdesktop" >/dev/null 2>&1; then
        xfdesktop --reload 2>/dev/null || true
        echo -e "  ${GREEN}✓ XFCE desktop refreshed${NC}"
    fi
}

# ── Summary ──────────────────────────────────────────────────────
summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ERR0RS DESKTOP ICONS INSTALLED ✓                 ║${NC}"
    echo -e "${GREEN}╠════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║   ERR0RS-Ultimate.desktop    → launch the AI       ║${NC}"
    echo -e "${GREEN}║   ERR0RS-Prompt-Manual.desktop → open the manual   ║${NC}"
    echo -e "${GREEN}║   Menu: Applications → Security → ERR0RS           ║${NC}"
    if [ "$EUID" -eq 0 ]; then
    echo -e "${GREEN}║   System: /usr/share/applications/                 ║${NC}"
    echo -e "${GREEN}║   New users get both icons automatically            ║${NC}"
    fi
    echo -e "${GREEN}╠════════════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║   Double-click ERR0RS-Prompt-Manual to read guide  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}  Tip: Run with sudo for ALL users:${NC}"
        echo -e "       sudo bash $SCRIPT_DIR/scripts/install_desktop_icon.sh"
        echo ""
    fi
}

# ── Main ─────────────────────────────────────────────────────────
generate_icons

if [ "$EUID" -eq 0 ]; then
    install_system_wide
fi

install_user
refresh_xfce
summary
