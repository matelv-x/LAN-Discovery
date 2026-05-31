#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/pi/sg1_v4}"

fail() { echo "ERROR: $1" >&2; exit 1; }

[ -d "$APP_DIR" ] || fail "App folder not found: $APP_DIR"

if ! sudo -n true 2>/dev/null; then
  echo "This restore needs sudo because stargate files may be owned by root."
  sudo true
fi

restore_latest() {
  local rel="$1"
  local pattern="$APP_DIR/$rel.bak-langate-*"
  local backup
  backup="$(ls -t $pattern 2>/dev/null | head -n 1 || true)"
  if [ -n "$backup" ] && [ -f "$backup" ]; then
    sudo rm -f "$APP_DIR/$rel"
    sudo cp -a "$backup" "$APP_DIR/$rel"
    echo "Restored: $rel"
  else
    echo "Skipped, no backup found: $rel"
  fi
}

echo "Restoring LAN Gates backups in:"
echo "  $APP_DIR"

sudo systemctl stop stargate.service || true

restore_latest "classes/stargate_address_book.py"
restore_latest "classes/stargate_address_manager.py"
restore_latest "classes/web_server.py"
restore_latest "web/js/address_book.js"
restore_latest "web/main.css"
restore_latest "config/milkyway-addresses.json"

sudo find "$APP_DIR/classes" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
sudo chown -R pi:pi "$APP_DIR"
sudo systemctl start stargate.service

echo "=== LAN GATES RESTORE COMPLETE ==="
