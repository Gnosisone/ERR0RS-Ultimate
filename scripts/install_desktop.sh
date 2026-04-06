#!/usr/bin/env bash
# ============================================================
# ERR0RS Ultimate — Desktop & App Menu Integration Installer
# Run once with: sudo bash scripts/install_desktop.sh
# ============================================================
set -e

REPO="/home/kali/ERR0RS-Ultimate"
ICON_SRC="$REPO/src/ui/web/errz-icon.svg"
DESKTOP_SRC="$REPO/err0rs-ultimate.desktop"
ICON_NAME="err0rs"
APP_NAME="ERR0RS Ultimate"

echo ""
echo "  ███████╗██████╗ ██████╗  ██████╗ ██████╗ ███████╗"
echo "  ██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗██╔════╝"
echo "  █████╗  ██████╔╝██████╔╝██║   ██║██████╔╝███████╗"
echo "  ██╔══╝  ██╔══██╗██╔══██╗██║   ██║██╔══██╗╚════██║"
echo "  ███████╗██║  ██║██║  ██║╚██████╔╝██║  ██║███████║"
echo "  ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝"
echo "        Desktop & App Menu Integration Installer"
echo ""

# ── 1. Install SVG icon ─────────────────────────────────────
echo "[1/5] Installing SVG icon..."
mkdir -p /usr/share/icons/hicolor/scalable/apps
cp "$ICON_SRC" /usr/share/icons/hicolor/scalable/apps/${ICON_NAME}.svg
echo "  ✓ /usr/share/icons/hicolor/scalable/apps/${ICON_NAME}.svg"

# ── 2. Convert to PNG sizes ─────────────────────────────────
echo "[2/5] Converting to PNG icon sizes..."
if command -v rsvg-convert &>/dev/null; then
  CONVERTER="rsvg"
elif command -v convert &>/dev/null; then
  CONVERTER="imagemagick"
else
  echo "  ⚠ No SVG converter found. Installing librsvg2-bin..."
  apt-get install -y librsvg2-bin -qq
  CONVERTER="rsvg"
fi

for sz in 16 32 48 64 128 256; do
  mkdir -p /usr/share/icons/hicolor/${sz}x${sz}/apps
  if [ "$CONVERTER" = "rsvg" ]; then
    rsvg-convert -w $sz -h $sz "$ICON_SRC" \
      > /usr/share/icons/hicolor/${sz}x${sz}/apps/${ICON_NAME}.png
  else
    convert -background none -resize ${sz}x${sz} "$ICON_SRC" \
      /usr/share/icons/hicolor/${sz}x${sz}/apps/${ICON_NAME}.png 2>/dev/null
  fi
  echo "  ✓ ${sz}x${sz}"
done

# ── 3. Refresh icon cache ────────────────────────────────────
echo "[3/5] Refreshing icon cache..."
gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null || true
xdg-icon-resource forceupdate 2>/dev/null || true
echo "  ✓ Icon cache updated"

# ── 4. Install .desktop to system app menu ──────────────────
echo "[4/5] Installing to application menu..."
cp "$DESKTOP_SRC" /usr/share/applications/err0rs-ultimate.desktop
chmod 644 /usr/share/applications/err0rs-ultimate.desktop
update-desktop-database /usr/share/applications/ 2>/dev/null || true
echo "  ✓ /usr/share/applications/err0rs-ultimate.desktop"

# ── 5. Desktop shortcut for kali user ───────────────────────
echo "[5/5] Creating desktop shortcut..."
DESKTOP_DIR="/home/kali/Desktop"
mkdir -p "$DESKTOP_DIR"
cp "$DESKTOP_SRC" "$DESKTOP_DIR/err0rs-ultimate.desktop"
chmod +x "$DESKTOP_DIR/err0rs-ultimate.desktop"
chown kali:kali "$DESKTOP_DIR/err0rs-ultimate.desktop"

# XFCE: mark as trusted so it shows the icon (not a text file)
if command -v gio &>/dev/null; then
  sudo -u kali gio set "$DESKTOP_DIR/err0rs-ultimate.desktop" \
    metadata::trusted true 2>/dev/null || true
fi
echo "  ✓ $DESKTOP_DIR/err0rs-ultimate.desktop"

echo ""
echo "  ✅ ERR0RS Ultimate is now in your app menu and on the desktop!"
echo "  ↳ If the desktop icon shows a text file, right-click → Allow Launching"
echo "  ↳ App menu: Applications → Kali → Hacking Tools → ERR0RS Ultimate"
echo ""
