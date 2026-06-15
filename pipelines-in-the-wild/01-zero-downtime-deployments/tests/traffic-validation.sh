#!/bin/bash
# Traffic validation test
# Sends multiple requests to the live Route and reports
# the distribution of blue vs green responses
#
# Useful for manually validating that HAProxy weight splitting
# is working as expected at each canary stage
#
# Usage:
#   ./tests/traffic-validation.sh          # 50 requests
#   ./tests/traffic-validation.sh 100      # 100 requests
#
# Required: ROUTE_URL set or oc access to retrieve it

set -euo pipefail

NAMESPACE="zero-downtime-demo"
REQUEST_COUNT="${1:-50}"
ROUTE_URL="${ROUTE_URL:-}"

if [ -z "${ROUTE_URL}" ]; then
  ROUTE_URL=$(oc get route nodejs-zero-downtime \
    --namespace "${NAMESPACE}" \
    -o jsonpath='{.spec.host}' 2>/dev/null || echo "")

  if [ -z "${ROUTE_URL}" ]; then
    echo "ERROR: Could not retrieve Route URL."
    echo "       Set: export ROUTE_URL=<your-route-hostname>"
    exit 1
  fi
fi

BASE_URL="https://${ROUTE_URL}"
BLUE_COUNT=0
GREEN_COUNT=0
ERROR_COUNT=0

echo "==> Traffic validation"
echo "    Route: ${BASE_URL}"
echo "    Requests: ${REQUEST_COUNT}"
echo ""

# Get current weight configuration
BLUE_WEIGHT=$(oc get route nodejs-zero-downtime \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.to.weight}' 2>/dev/null || echo "unknown")
GREEN_WEIGHT=$(oc get route nodejs-zero-downtime \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.alternateBackends[0].weight}' \
  2>/dev/null || echo "unknown")

echo "    Configured weights — Blue: ${BLUE_WEIGHT} Green: ${GREEN_WEIGHT}"
echo ""
echo "    Sending requests..."

for i in $(seq 1 "${REQUEST_COUNT}"); do
  RESPONSE=$(curl -sk \
    --max-time 5 \
    "${BASE_URL}/version" 2>/dev/null || echo '{"colour":"error"}')

  COLOUR=$(echo "${RESPONSE}" \
    | grep -o '"colour":"[^"]*"' \
    | cut -d'"' -f4 || echo "error")

  case "${COLOUR}" in
    blue)
      ((BLUE_COUNT++))
      printf "b"
      ;;
    green)
      ((GREEN_COUNT++))
      printf "g"
      ;;
    *)
      ((ERROR_COUNT++))
      printf "e"
      ;;
  esac

  # Print newline every 50 requests for readability
  if [ $((i % 50)) -eq 0 ]; then
    echo ""
  fi
done

echo ""
echo ""

# Calculate percentages
TOTAL=$((BLUE_COUNT + GREEN_COUNT + ERROR_COUNT))
BLUE_PCT=0
GREEN_PCT=0

if [ "${TOTAL}" -gt 0 ]; then
  BLUE_PCT=$(echo "scale=1; ${BLUE_COUNT} * 100 / ${TOTAL}" | bc)
  GREEN_PCT=$(echo "scale=1; ${GREEN_COUNT} * 100 / ${TOTAL}" | bc)
fi

echo "==> Results"
echo "    Total requests:  ${TOTAL}"
echo "    Blue responses:  ${BLUE_COUNT} (${BLUE_PCT}%)"
echo "    Green responses: ${GREEN_COUNT} (${GREEN_PCT}%)"
echo "    Errors:          ${ERROR_COUNT}"
echo ""
echo "    Configured — Blue: ${BLUE_WEIGHT}% Green: ${GREEN_WEIGHT}%"
echo "    Observed   — Blue: ${BLUE_PCT}% Green: ${GREEN_PCT}%"
echo ""

# Note on HAProxy weight accuracy
if [ "${TOTAL}" -lt 50 ]; then
  echo "    NOTE: At low request counts HAProxy weight splitting"
  echo "    may not match configured weights precisely."
  echo "    Run with 100+ requests for more accurate distribution."
fi

if [ "${ERROR_COUNT}" -gt 0 ]; then
  echo "    WARNING: ${ERROR_COUNT} requests returned errors."
  echo "    Check pod health:"
  echo "    oc get pods -n ${NAMESPACE}"
fi
