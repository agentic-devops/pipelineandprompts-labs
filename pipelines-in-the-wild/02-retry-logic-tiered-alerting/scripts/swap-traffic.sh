#!/usr/bin/env bash
# swap-traffic.sh — atomically swap nginx traffic to the new blue/green slot
#
# Usage: bash scripts/swap-traffic.sh <server-ip> <target-slot>
# Example: bash scripts/swap-traffic.sh 10.0.0.42 green
#
# What it does:
#   1. Writes the new active slot to /etc/deploy/active-slot
#   2. Updates the nginx upstream config to point at the new slot's port
#   3. Reloads nginx (zero-downtime — existing connections complete)
#   4. Verifies the slot file was updated before declaring success
#
# Requires on the deploy server:
#   - deploy user with sudo permission to write /etc/deploy/active-slot
#   - deploy user with sudo permission to run: nginx -s reload
#   - nginx upstream config at /etc/nginx/conf.d/waybill-upstream.conf
#   - Port mapping: blue=7070, green=9091 (matches docker-compose.yml)
#
# Run bootstrap-server.sh once to set up these permissions.

set -euo pipefail

if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  echo "Usage: $0 <server-ip> <target-slot>"
  exit 1
fi

SERVER="$1"
TARGET="$2"

if [ "$TARGET" != "blue" ] && [ "$TARGET" != "green" ]; then
  echo "❌ Invalid slot '$TARGET' — must be 'blue' or 'green'"
  exit 1
fi

# Port mapping must match docker-compose.yml
BLUE_PORT=7070
GREEN_PORT=9091

if [ "$TARGET" = "blue" ]; then
  PORT=$BLUE_PORT
else
  PORT=$GREEN_PORT
fi

echo "[swap] Swapping traffic to $TARGET slot (port $PORT) on $SERVER"

ssh "deploy@${SERVER}" bash << EOF
  set -euo pipefail

  # Write new active slot
  echo "$TARGET" | sudo tee /etc/deploy/active-slot > /dev/null

  # Update nginx upstream to point at new slot
  sudo tee /etc/nginx/conf.d/waybill-upstream.conf > /dev/null << NGINX
upstream waybill {
    server 127.0.0.1:${PORT};
}
NGINX

  # Reload nginx — zero-downtime, existing connections complete gracefully
  sudo nginx -s reload

  # Verify the slot file updated correctly
  WRITTEN=\$(cat /etc/deploy/active-slot)
  if [ "\$WRITTEN" != "$TARGET" ]; then
    echo "❌ Slot file verification failed: expected $TARGET, got \$WRITTEN"
    exit 1
  fi

  echo "✅ Traffic swapped to $TARGET (port $PORT)"
  echo "✅ Active slot confirmed: \$WRITTEN"
EOF

echo "[swap] ✅ Swap complete — $TARGET is now live"
