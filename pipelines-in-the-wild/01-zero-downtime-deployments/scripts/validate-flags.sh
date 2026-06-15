#!/bin/bash
# Validate Flagsmith flag state before shifting traffic
# Pipeline aborts if the gate flag is not enabled
#
# Usage:
#   ./scripts/validate-flags.sh
#
# Required environment variables:
#   FLAGSMITH_API_KEY  — Flagsmith environment API key
#   FLAGSMITH_URL      — Flagsmith API URL
#                        e.g. https://flagsmith.<route>/api/v1
#
# Exit codes:
#   0 — flag is enabled, pipeline can proceed
#   1 — flag is disabled or unreachable, pipeline should abort

set -euo pipefail

FLAG_NAME="enable-green-deployment"
FLAGSMITH_URL="${FLAGSMITH_URL:-}"
FLAGSMITH_API_KEY="${FLAGSMITH_API_KEY:-}"

if [ -z "${FLAGSMITH_URL}" ]; then
  echo "ERROR: FLAGSMITH_URL environment variable not set."
  exit 1
fi

if [ -z "${FLAGSMITH_API_KEY}" ]; then
  echo "ERROR: FLAGSMITH_API_KEY environment variable not set."
  exit 1
fi

echo "==> Checking Flagsmith flag: ${FLAG_NAME}"
echo "    Flagsmith URL: ${FLAGSMITH_URL}"

# Query Flagsmith API for flag state
RESPONSE=$(curl -sf \
  --max-time 10 \
  -H "X-Environment-Key: ${FLAGSMITH_API_KEY}" \
  "${FLAGSMITH_URL}/flags/" 2>/dev/null) || {
  echo "ERROR: Could not reach Flagsmith API at ${FLAGSMITH_URL}"
  echo "       Check FLAGSMITH_URL and confirm Flagsmith is running:"
  echo "       oc get pods -n zero-downtime-demo -l app=flagsmith"
  exit 1
}

# Extract flag enabled state
FLAG_ENABLED=$(echo "${RESPONSE}" \
  | grep -o "\"feature\":{\"id\":[^}]*\"name\":\"${FLAG_NAME}\"[^}]*}[^}]*\"enabled\":[^,}]*" \
  | grep -o "\"enabled\":[^,}]*" \
  | grep -o "[^:]*$" \
  | tr -d ' "' 2>/dev/null || echo "not_found")

if [ "${FLAG_ENABLED}" = "not_found" ] || [ -z "${FLAG_ENABLED}" ]; then
  echo "ERROR: Flag '${FLAG_NAME}' not found in Flagsmith."
  echo "       Create the flag in Flagsmith UI before running the pipeline."
  echo "       See docs/flagsmith-setup.md for setup steps."
  exit 1
fi

if [ "${FLAG_ENABLED}" = "true" ]; then
  echo "  ✓ Flag '${FLAG_NAME}' is ENABLED — pipeline can proceed"
  exit 0
else
  echo "  ✗ Flag '${FLAG_NAME}' is DISABLED — pipeline will not shift traffic"
  echo ""
  echo "  To enable: Flagsmith UI → production environment →"
  echo "  enable-green-deployment → toggle on"
  exit 1
fi
