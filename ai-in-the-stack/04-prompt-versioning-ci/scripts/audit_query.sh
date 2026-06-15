#!/bin/bash
# Path: prompt-versioning-ci-openshift/scripts/audit_query.sh
# Purpose: Query OpenShift audit logs for ConfigMap access in ai-workflows namespace
# Article: https://pipelineandprompts.com/posts/prompt-versioning-ci-openshift/
#
# Usage: ./audit_query.sh 2026-06-11T14:00:00Z 2026-06-11T15:00:00Z

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "Usage: $0 <START_TIME> <END_TIME>" >&2
  echo "Example: $0 2026-06-11T14:00:00Z 2026-06-11T15:00:00Z" >&2
  exit 1
fi

START_TIME="$1"
END_TIME="$2"

# Check if oc is installed
if ! command -v oc &> /dev/null; then
  echo "Error: oc CLI not found. Install from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/" >&2
  exit 1
fi

# Check if logged in
if ! oc whoami &> /dev/null; then
  echo "Error: Not logged in to OpenShift. Run 'oc login' first." >&2
  exit 1
fi

echo "Querying audit logs for ConfigMap access in ai-workflows namespace"
echo "Time range: $START_TIME to $END_TIME"
echo ""
echo "TIMESTAMP                  | USER                           | VERB | RESOURCE   | CODE"
echo "---------------------------|--------------------------------|------|------------|-----"

oc adm audit log \
  --namespace=ai-workflows \
  --resource=configmaps \
  --verb=get \
  --after="$START_TIME" \
  --before="$END_TIME" \
  --output=json 2>/dev/null | \
jq -r '.items[] |
  [
    .requestReceivedTimestamp,
    .user.username,
    .verb,
    .objectRef.resource,
    (.responseStatus.code // "N/A")
  ] |
  @tsv' | \
awk -F'\t' '{printf "%-26s | %-30s | %-4s | %-10s | %s\n", $1, $2, $3, $4, $5}'

echo ""
echo "Query complete"
