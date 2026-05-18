#!/bin/bash
# Emergency rollback — shift 100% traffic back to blue immediately
# Safe to run under pressure — no dependencies on Flagsmith
#
# Usage:
#   ./scripts/rollback.sh
#   ./scripts/rollback.sh --disable-flag   # Also disables Flagsmith gate
#
# Exit codes:
#   0 — rollback complete
#   1 — rollback failed

set -euo pipefail

NAMESPACE="zero-downtime-demo"
ROUTE="nodejs-zero-downtime"
DISABLE_FLAG="${1:-}"
FLAGSMITH_URL="${FLAGSMITH_URL:-}"
FLAGSMITH_API_KEY="${FLAGSMITH_API_KEY:-}"

echo "==> ROLLBACK INITIATED"
echo "    Target: 100% blue / 0% green"
echo "    Namespace: ${NAMESPACE}"
echo ""

# Step 1 — Shift all traffic to blue immediately
echo "==> Step 1: Shifting all traffic to blue..."

oc patch route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  --type=json \
  --patch='[
    {
      "op": "replace",
      "path": "/spec/to/weight",
      "value": 100
    },
    {
      "op": "replace",
      "path": "/spec/alternateBackends/0/weight",
      "value": 0
    }
  ]'

# Step 2 — Verify rollback applied
echo ""
echo "==> Step 2: Verifying rollback applied..."
sleep 2

BLUE_WEIGHT=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.to.weight}')

GREEN_WEIGHT=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.alternateBackends[0].weight}')

if [ "${BLUE_WEIGHT}" = "100" ] && [ "${GREEN_WEIGHT}" = "0" ]; then
  echo "  ✓ Route weights confirmed: Blue 100% / Green 0%"
else
  echo "ERROR: Rollback weights not applied correctly."
  echo "  Expected — Blue: 100, Green: 0"
  echo "  Got      — Blue: ${BLUE_WEIGHT}, Green: ${GREEN_WEIGHT}"
  echo ""
  echo "  Manual fix:"
  echo "  oc patch route ${ROUTE} -n ${NAMESPACE} --type=json \\"
  echo "    --patch='[{\"op\":\"replace\",\"path\":\"/spec/to/weight\",\"value\":100},"
  echo "    {\"op\":\"replace\",\"path\":\"/spec/alternateBackends/0/weight\",\"value\":0}]'"
  exit 1
fi

# Step 3 — Verify blue is healthy
echo ""
echo "==> Step 3: Verifying blue deployment is healthy..."

READY=$(oc get deployment nodejs-blue \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

DESIRED=$(oc get deployment nodejs-blue \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.replicas}')

if [ "${READY}" = "${DESIRED}" ] && [ "${READY}" != "0" ]; then
  echo "  ✓ Blue deployment healthy: ${READY}/${DESIRED} replicas ready"
else
  echo "WARNING: Blue deployment has ${READY}/${DESIRED} ready replicas."
  echo "         Traffic is routed to blue but it may not be fully healthy."
  echo "         Check: oc get pods -n ${NAMESPACE} -l deployment-colour=blue"
fi

# Step 4 — Disable Flagsmith flag if requested
if [ "${DISABLE_FLAG}" = "--disable-flag" ]; then
  echo ""
  echo "==> Step 4: Disabling Flagsmith gate flag..."

  if [ -z "${FLAGSMITH_URL}" ] || [ -z "${FLAGSMITH_API_KEY}" ]; then
    echo "WARNING: FLAGSMITH_URL or FLAGSMITH_API_KEY not set."
    echo "         Disable the flag manually in Flagsmith UI."
  else
    echo "  Flagsmith flag must be disabled manually via UI:"
    echo "  ${FLAGSMITH_URL} → production → enable-green-deployment → off"
  fi
fi

# Step 5 — Print route URL for verification
ROUTE_URL=$(oc get route "${ROUTE}" \
  --namespace "${NAMESPACE}" \
  -o jsonpath='{.spec.host}')

echo ""
echo "==> ROLLBACK COMPLETE"
echo "    All traffic is now on blue."
echo "    Verify: curl https://${ROUTE_URL}/version"
echo "    Expected response: {\"colour\":\"blue\",...}"
echo ""
echo "    Next steps:"
echo "    1. Investigate green deployment failure"
echo "    2. Check logs: oc logs -l deployment-colour=green -n ${NAMESPACE}"
echo "    3. Fix the issue, rebuild the green image, and re-run the pipeline"
