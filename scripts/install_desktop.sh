#!/usr/bin/env bash
# ============================================================
# ERR0RS Ultimate — Desktop & App Menu Integration Installer
# Run with: sudo bash scripts/install_desktop.sh
# ============================================================

REPO="/home/kali/ERR0RS-Ultimate"
ICON_DIR="$REPO/assets/icons"
DESKTOP_FILE="$REPO/err0rs-ultimate.desktop"

echo ""
echo "  [ERR0RS] Desktop Integration Installer"
echo ""

# ── 1. Install PNG icons into hicolor theme ──────────────────
echo "[1/4] Installing icons..."
for sz in 16 32 48 64 128 256; do
  DEST="/usr/share/icons/hicolor/${sz}x${sz}/apps"
  mkdir -p "$DEST"
  cp "$ICON_DIR/err0rs-${sz}.png" "$DEST/err0rs.png"
  echo "  ✓ ${sz}x${sz}"
done

# Install SVG too
mkdir -p /usr/share/icons/hicolor/scalable/apps
cp "$REPO/src/ui/web/errz-icon.svg" /usr/share/icons/hicolor/scalable/apps/err0rs.svg
echo "  ✓ scalable SVG"

# ── 2. Refresh icon cache ─────────────────────────────────────
echo "[2/4] Refreshing icon cache..."
gtk-update-icon-cache -f -t /usr/share/icons/hicolor/ 2>/dev/null && echo "  ✓ gtk cache" || echo "  (gtk-update-icon-cache not found, skipping)"
xdg-icon-resource forceupdate 2>/dev/null || true

# ── 3. Register in app menu ───────────────────────────────────
echo "[3/4] Registering in application menu..."
cp "$DESKTOP_FILE" /usr/share/applications/err0rs-ultimate.desktop
chmod 644 /usr/share/applications/err0rs-ultimate.desktop
update-desktop-database /usr/share/applications/ 2>/dev/null && echo "  ✓ app menu registered" || echo "  ✓ copied (update-desktop-database not found)"

# ── 4. Desktop shortcut ───────────────────────────────────────
echo "[4/4] Adding desktop shortcut..."
DESK="/home/kali/Desktop"
mkdir -p "$DESK"
cp "$DESKTOP_FILE" "$DESK/err0rs-ultimate.desktop"
chmod +x "$DESK/err0rs-ultimate.desktop"
chown kali:kali "$DESK/err0rs-ultimate.desktop"
# Mark trusted for XFCE so it renders as icon, not text file
sudo -u kali gio set "$DESK/err0rs-ultimate.desktop" metadata::trusted true 2>/dev/null || \
  sudo -u kali dbus-launch gio set "$DESK/err0rs-ultimate.desktop" metadata::trusted true 2>/dev/null || true
echo "  ✓ $DESK/err0rs-ultimate.desktop"

echo ""
echo "  ✅ Done! ERR0RS Ultimate is now in your app menu + desktop."
echo "  ↳ App menu: Applications → Usual Applications → Network"
echo "  ↳ Desktop: double-click the ERR0RS icon to launch"
echo "  ↳ If desktop shows a text file: right-click → Allow Launching"
echo ""
