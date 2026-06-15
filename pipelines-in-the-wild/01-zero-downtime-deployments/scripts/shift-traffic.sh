#!/bin/bash
# Shift HAProxy Route traffic between blue and green
# Used by the pipeline at each canary stage
#
# Usage:
#   ./scripts/shift-traffic.sh 10    # 10% green, 90% blue
#   ./scripts/shift-traffic.sh 50    # 50% green, 50% blue
#   ./scripts/shift-traffic.sh 100   # 100% green, 0% blue
#   ./scripts/shift-traffic.sh 0     # 0% green, 100% blue (rollback)
#
# Exit codes:
#   0 — traffic shift applied and verified
#   1 — traffic shift failed

set -euo pipefail

NAMESPACE="zero-downtime-demo"
ROUTE="nodejs-zero-downtime"
GREEN_WEIGHT="${1:-}"

if [ -z "${GREEN_WEIGHT}" ]; then
  echo "ERROR: No weight provided."
  echo "Usage: $0 [0|10|50|100]"
  exit 1
fi

# Validate input is a number between 0 and 100
if ! [[ "${GREEN_WEIGHT}" =~ ^[0-9]+$ ]] || \
   [ "${GREEN_WEIGHT}" -lt 0 ] || \
   [ "${GREEN_WEIGHT}" -gt 100 ]; then
  echo "ERROR: Weight must be a number between 0 and 100."
  exit 1
fi

BLUE_WEIGHT=$((100 - GREEN_WEIGHT))

echo "==> Shifting traffic..."
echo "    Blue:  ${BLUE_WEIGHT}%"
echo "    Green: ${GREEN_WEIGHT}%"

# Patch the Route
# .spec.to.weight controls blue (primary backend)
# .spec.alternateBackends[0].weight controls green
oc patch route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  --type=json \
  --patch="[
    {
      \"op\": \"replace\",
      \"path\": \"/spec/to/weight\",
      \"value\": ${BLUE_WEIGHT}
    },
    {
      \"op\": \"replace\",
      \"path\": \"/spec/alternateBackends/0/weight\",
      \"value\": ${GREEN_WEIGHT}
    }
  ]"

# Verify the patch was applied
echo ""
echo "==> Verifying route weights applied..."
sleep 2

APPLIED_BLUE=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.to.weight}')

APPLIED_GREEN=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.alternateBackends[0].weight}')

if [ "${APPLIED_BLUE}" = "${BLUE_WEIGHT}" ] && \
   [ "${APPLIED_GREEN}" = "${GREEN_WEIGHT}" ]; then
  echo "  ✓ Route weights confirmed:"
  echo "    Blue:  ${APPLIED_BLUE}%"
  echo "    Green: ${APPLIED_GREEN}%"
else
  echo "ERROR: Route weights not applied correctly."
  echo "  Expected — Blue: ${BLUE_WEIGHT}, Green: ${GREEN_WEIGHT}"
  echo "  Got      — Blue: ${APPLIED_BLUE}, Green: ${APPLIED_GREEN}"
  exit 1
fi

echo ""
echo "==> Traffic shift complete."

# Print current route URL for manual verification
ROUTE_URL=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.host}')
echo "    Route: https://${ROUTE_URL}/version"
echo "    Run: curl https://${ROUTE_URL}/version"
echo "    to confirm which deployment is serving requests."
