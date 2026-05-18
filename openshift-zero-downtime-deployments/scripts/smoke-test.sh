#!/bin/bash
# Post-deploy smoke test
# Tests the live Route endpoint after full cutover to green
# Also used to validate blue is serving correctly on initial setup
#
# Usage:
#   ./scripts/smoke-test.sh blue
#   ./scripts/smoke-test.sh green
#
# Required environment variables:
#   ROUTE_URL — the Route hostname (without https://)
#               e.g. nodejs-zero-downtime-zero-downtime-demo.apps.<cluster>
#
# Exit codes:
#   0 — smoke test passed
#   1 — smoke test failed

set -euo pipefail

EXPECTED_COLOUR="${1:-}"
ROUTE_URL="${ROUTE_URL:-}"
MAX_RETRIES=5
RETRY_INTERVAL=10

if [ -z "${EXPECTED_COLOUR}" ]; then
  echo "ERROR: No colour argument provided."
  echo "Usage: $0 [blue|green]"
  exit 1
fi

if [ -z "${ROUTE_URL}" ]; then
  # Try to get it from oc if not set
  ROUTE_URL=$(oc get route nodejs-zero-downtime \
    --namespace zero-downtime-demo \
    -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

  if [ -z "${ROUTE_URL}" ]; then
    echo "ERROR: ROUTE_URL not set and could not retrieve from cluster."
    echo "       Set: export ROUTE_URL=<your-route-hostname>"
    exit 1
  fi
fi

BASE_URL="https://${ROUTE_URL}"
echo "==> Running smoke test against: ${BASE_URL}"
echo "    Expected colour: ${EXPECTED_COLOUR}"
echo ""

PASS=0
FAIL=0

# -------------------------------------------------------
# Test 1: Root endpoint returns 200
# -------------------------------------------------------
echo "--- Test 1: Root endpoint (/) returns HTTP 200"
RETRIES=0
until [ $RETRIES -ge $MAX_RETRIES ]; do
  STATUS=$(curl -sk -o /dev/null -w "%{http_code}" "${BASE_URL}/")
  if [ "${STATUS}" = "200" ]; then
    echo "  ✓ HTTP ${STATUS}"
    ((PASS++))
    break
  fi
  echo "  HTTP ${STATUS}, retrying... (${RETRIES}/${MAX_RETRIES})"
  ((RETRIES++))
  sleep $RETRY_INTERVAL
done
[ $RETRIES -ge $MAX_RETRIES ] && echo "  ✗ FAILED" && ((FAIL++))

# -------------------------------------------------------
# Test 2: Health endpoint returns healthy
# -------------------------------------------------------
echo "--- Test 2: /health returns status: healthy"
HEALTH=$(curl -sk "${BASE_URL}/health" 2>/dev/null || echo "{}")
if echo "${HEALTH}" | grep -q '"status":"healthy"'; then
  echo "  ✓ Health check passed"
  ((PASS++))
else
  echo "  ✗ Health check failed. Response: ${HEALTH}"
  ((FAIL++))
fi

# -------------------------------------------------------
# Test 3: Version endpoint returns expected colour
# -------------------------------------------------------
echo "--- Test 3: /version returns colour: ${EXPECTED_COLOUR}"
VERSION=$(curl -sk "${BASE_URL}/version" 2>/dev/null || echo "{}")
ACTUAL_COLOUR=$(echo "${VERSION}" \
  | grep -o '"colour":"[^"]*"' \
  | cut -d'"' -f4 || echo "unknown")

if [ "${ACTUAL_COLOUR}" = "${EXPECTED_COLOUR}" ]; then
  echo "  ✓ Colour confirmed: ${ACTUAL_COLOUR}"
  ((PASS++))
else
  echo "  ✗ Expected colour '${EXPECTED_COLOUR}', got '${ACTUAL_COLOUR}'"
  echo "    Full response: ${VERSION}"
  ((FAIL++))
fi

# -------------------------------------------------------
# Results
# -------------------------------------------------------
echo ""
echo "==> Smoke test results: ${PASS} passed, ${FAIL} failed"

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "    SMOKE TEST FAILED — do not proceed with traffic shift"
  echo "    Check logs: oc logs -l deployment-colour=${EXPECTED_COLOUR}"
  echo "                -n zero-downtime-demo"
  exit 1
else
  echo ""
  echo "    SMOKE TEST PASSED — safe to proceed"
fi
