#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/home/pi/sg1_v4}"

fail() { echo "ERROR: $1" >&2; exit 1; }

[ -d "$APP_DIR" ] || fail "App folder not found: $APP_DIR"

if ! sudo -n true 2>/dev/null; then
  echo "This restore needs sudo because stargate files may be owned by root."
  sudo true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Surgically removing LAN Discovery code in:"
echo "  $APP_DIR"

if [ "${STARGATE_ADDON_NO_RESTART:-0}" != "1" ]; then
  sudo systemctl stop stargate.service || true
fi

sudo python3 "$SCRIPT_DIR/surgical_restore.py" "$APP_DIR" "$SCRIPT_DIR/langate.sh"
sudo python3 -m py_compile \
  "$APP_DIR/classes/stargate_address_book.py" \
  "$APP_DIR/classes/stargate_address_manager.py" \
  "$APP_DIR/classes/web_server.py"

sudo find "$APP_DIR/classes" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
sudo chown -R pi:pi "$APP_DIR"
if [ "${STARGATE_ADDON_NO_RESTART:-0}" != "1" ]; then
  sudo systemctl start stargate.service
else
  echo "Stargate restart deferred by add-on manager."
fi

echo "=== LAN GATES RESTORE COMPLETE ==="
