#!/bin/bash
# Verify a deployment is healthy before shifting traffic
# Used by the pipeline before each traffic shift step
#
# Usage:
#   ./scripts/verify-deployment.sh blue
#   ./scripts/verify-deployment.sh green
#   ./scripts/verify-deployment.sh route-weights
#
# Exit codes:
#   0 — verification passed
#   1 — verification failed

set -euo pipefail

NAMESPACE="zero-downtime-demo"
COLOUR="${1:-}"
MAX_RETRIES=12
RETRY_INTERVAL=10

if [ -z "$COLOUR" ]; then
  echo "ERROR: No argument provided."
  echo "Usage: $0 [blue|green|route-weights]"
  exit 1
fi

# -------------------------------------------------------
# Helper: check deployment rollout status
# -------------------------------------------------------
check_deployment() {
  local DEPLOYMENT="nodejs-${1}"
  echo "==> Checking rollout status: ${DEPLOYMENT}"

  if ! oc rollout status deployment/"${DEPLOYMENT}" \
    --namespace "${NAMESPACE}" \
    --timeout=120s; then
    echo "ERROR: Deployment ${DEPLOYMENT} did not complete rollout."
    exit 1
  fi

  # Verify expected replica count
  READY=$(oc get deployment "${DEPLOYMENT}" \
    --namespace "${NAMESPACE}" \
    -o jsonpath='{.status.readyReplicas}')
  DESIRED=$(oc get deployment "${DEPLOYMENT}" \
    --namespace "${NAMESPACE}" \
    -o jsonpath='{.spec.replicas}')

  if [ "${READY}" != "${DESIRED}" ]; then
    echo "ERROR: ${DEPLOYMENT} has ${READY}/${DESIRED} ready replicas."
    exit 1
  fi

  echo "  ✓ ${DEPLOYMENT}: ${READY}/${DESIRED} replicas ready"
}

# -------------------------------------------------------
# Helper: health check against deployment pods directly
# Bypasses the Route — tests the deployment in isolation
# before any traffic is shifted
# -------------------------------------------------------
check_health_direct() {
  local COLOUR="${1}"
  echo "==> Running direct health check against ${COLOUR} pods..."

  # Get a pod name for the target colour
  POD=$(oc get pods \
    --namespace "${NAMESPACE}" \
    --selector="app=nodejs-zero-downtime,deployment-colour=${COLOUR}" \
    --field-selector=status.phase=Running \
    -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

  if [ -z "${POD}" ]; then
    echo "ERROR: No running pods found for deployment-colour=${COLOUR}"
    exit 1
  fi

  echo "  Using pod: ${POD}"

  RETRIES=0
  until [ $RETRIES -ge $MAX_RETRIES ]; do
    RESPONSE=$(oc exec "${POD}" \
      --namespace "${NAMESPACE}" \
      -- curl -s -o /dev/null -w "%{http_code}" \
      http://localhost:8080/health 2>/dev/null || echo "000")

    if [ "${RESPONSE}" = "200" ]; then
      echo "  ✓ Health check passed (HTTP ${RESPONSE})"

      # Also verify colour matches expected
      COLOUR_RESPONSE=$(oc exec "${POD}" \
        --namespace "${NAMESPACE}" \
        -- curl -s http://localhost:8080/version 2>/dev/null \
        | grep -o '"colour":"[^"]*"' \
        | cut -d'"' -f4)

      if [ "${COLOUR_RESPONSE}" = "${COLOUR}" ]; then
        echo "  ✓ Colour verified: ${COLOUR_RESPONSE}"
      else
        echo "ERROR: Expected colour ${COLOUR}, got ${COLOUR_RESPONSE}"
        exit 1
      fi
      return 0
    fi

    echo "  Health check returned HTTP ${RESPONSE}, retrying in ${RETRY_INTERVAL}s... (${RETRIES}/${MAX_RETRIES})"
    ((RETRIES++))
    sleep $RETRY_INTERVAL
  done

  echo "ERROR: Health check failed after ${MAX_RETRIES} retries."
  exit 1
}

# -------------------------------------------------------
# Helper: verify HAProxy Route weights
# -------------------------------------------------------
check_route_weights() {
  echo "==> Verifying HAProxy Route weights..."

  BLUE_WEIGHT=$(oc get route nodejs-zero-downtime \
    --namespace "${NAMESPACE}" \
    -o jsonpath='{.spec.to.weight}')

  GREEN_WEIGHT=$(oc get route nodejs-zero-downtime \
    --namespace "${NAMESPACE}" \
    -o jsonpath='{.spec.alternateBackends[0].weight}')

  echo "  Blue weight:  ${BLUE_WEIGHT}"
  echo "  Green weight: ${GREEN_WEIGHT}"

  TOTAL=$((BLUE_WEIGHT + GREEN_WEIGHT))
  if [ "${TOTAL}" != "100" ]; then
    echo "ERROR: Route weights do not add up to 100 (got ${TOTAL})"
    exit 1
  fi

  echo "  ✓ Route weights valid (total: ${TOTAL})"
}

# -------------------------------------------------------
# Main
# -------------------------------------------------------
case "${COLOUR}" in
  blue)
    check_deployment "blue"
    check_health_direct "blue"
    ;;
  green)
    check_deployment "green"
    check_health_direct "green"
    ;;
  route-weights)
    check_route_weights
    ;;
  *)
    echo "ERROR: Unknown argument '${COLOUR}'"
    echo "Usage: $0 [blue|green|route-weights]"
    exit 1
    ;;
esac

echo ""
echo "==> Verification passed for: ${COLOUR}"
