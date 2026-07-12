#!/usr/bin/env bash
# Fires the incident-triage webhook with samples/sample-alert.json.
# Run from the repo root: ./samples/trigger-workflow.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N8N_URL="${N8N_URL:-http://localhost:5678}"

curl -X POST "${N8N_URL}/webhook/incident-triage" \
  -H "Content-Type: application/json" \
  -d @"${SCRIPT_DIR}/sample-alert.json"

echo
echo "Sent. Check the n8n UI (${N8N_URL}) for the execution, and your configured Slack channel for the result."
