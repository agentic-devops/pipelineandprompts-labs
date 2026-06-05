#!/usr/bin/env bash
# smoke-test.sh — health check for a waybill blue/green slot
#
# Usage: bash scripts/smoke-test.sh <server-ip> <slot>
# Example: bash scripts/smoke-test.sh localhost blue
#          bash scripts/smoke-test.sh localhost green
#
# Override ports without editing this file:
#   BLUE_PORT=8080 bash scripts/smoke-test.sh localhost blue
#   GREEN_PORT=9091 bash scripts/smoke-test.sh localhost green

set -uo pipefail

# ── Arguments ─────────────────────────────────────────────────────────────────
if [ -z "${1:-}" ] || [ -z "${2:-}" ]; then
  echo "Usage: $0 <server-ip> <slot>"
  exit 1
fi

SERVER="$1"
SLOT="$2"

# ── Port mapping ──────────────────────────────────────────────────────────────
BLUE_PORT="${BLUE_PORT:-7070}"
GREEN_PORT="${GREEN_PORT:-9091}"

if [ "$SLOT" = "blue" ]; then
  PORT="$BLUE_PORT"
elif [ "$SLOT" = "green" ]; then
  PORT="$GREEN_PORT"
else
  echo "[smoke] ❌ Unknown slot '$SLOT' — must be 'blue' or 'green'"
  exit 1
fi

BASE="http://${SERVER}:${PORT}"
echo "[smoke] Testing $SLOT slot at $BASE"

# ── 1. HTTP 200 from /health ──────────────────────────────────────────────────
HTTP_CODE=$(curl -s -o /tmp/smoke-body.txt -w "%{http_code}" \
  --max-time 5 "$BASE/health" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" != "200" ]; then
  echo "[smoke] ❌ /health returned HTTP $HTTP_CODE"
  cat /tmp/smoke-body.txt
  exit 1
fi
echo "[smoke] ✅ /health → 200"

# ── 2. DB connected ───────────────────────────────────────────────────────────
DB_STATUS=$(python3 -c "
import json, sys
try:
    d = json.load(open('/tmp/smoke-body.txt'))
    print(d.get('db', 'unknown'))
except Exception:
    print('parse-error')
")

if [ "$DB_STATUS" != "connected" ]; then
  echo "[smoke] ❌ Database not connected — got: $DB_STATUS"
  exit 1
fi
echo "[smoke] ✅ DB connected"

# ── 3. Correct slot reporting ─────────────────────────────────────────────────
REPORTED_SLOT=$(python3 -c "
import json, sys
try:
    d = json.load(open('/tmp/smoke-body.txt'))
    print(d.get('slot', 'unknown'))
except Exception:
    print('parse-error')
")

if [ "$REPORTED_SLOT" != "$SLOT" ]; then
  echo "[smoke] ❌ Wrong slot: expected $SLOT, got $REPORTED_SLOT"
  exit 1
fi
echo "[smoke] ✅ Slot: $REPORTED_SLOT"

# ── 4. Response time ──────────────────────────────────────────────────────────
RESPONSE_MS=$(curl -s -o /dev/null -w "%{time_total}" \
  --max-time 5 "$BASE/health" 2>/dev/null \
  | awk '{printf "%d", $1 * 1000}')

if [ -z "$RESPONSE_MS" ]; then
  echo "[smoke] ❌ Could not measure response time"
  exit 1
fi

if [ "$RESPONSE_MS" -gt 2000 ]; then
  echo "[smoke] ❌ Slow response: ${RESPONSE_MS}ms (threshold: 2000ms)"
  exit 1
fi
echo "[smoke] ✅ Response time: ${RESPONSE_MS}ms"

# ── 5. API reachable ──────────────────────────────────────────────────────────
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 5 "$BASE/shipments" 2>/dev/null || echo "000")

if [ "$API_CODE" != "200" ]; then
  echo "[smoke] ❌ /shipments returned HTTP $API_CODE"
  exit 1
fi
echo "[smoke] ✅ /shipments → 200"

echo "[smoke] ✅ All checks passed for $SLOT slot"
