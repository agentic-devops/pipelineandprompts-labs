#!/bin/bash
# Verify pipeline-deployer service account has correct permissions
# Run after applying RBAC manifests to confirm before setting up
# GitHub Actions secrets
#
# Usage: ./manifests/rbac/verify-rbac.sh

set -euo pipefail

SA="system:serviceaccount:zero-downtime-demo:pipeline-deployer"
NS="zero-downtime-demo"

echo "==> Verifying pipeline-deployer RBAC in namespace: ${NS}"
echo ""

# Function to run the check safely
run_check() {
    local action=$1
    shift
    # Run the oc auth command with arguments passed to the function
    if oc auth can-i "$@" --as="${SA}" >/dev/null 2>&1; then
        echo "yes"
    else
        echo "no"
    fi
}

PASS=0
FAIL=0

# Positive Checks: Array format: "Description|Verb|Resource|Namespace_Flag"
POSITIVE_CHECKS=(
    "patch deployments|patch|deployments|-n ${NS}"
    "patch routes|patch|routes.route.openshift.io|-n ${NS}"
    "get pods|get|pods|-n ${NS}"
    "list services|list|services|-n ${NS}"
)

for item in "${POSITIVE_CHECKS[@]}"; do
    IFS="|" read -r desc verb resource ns_flag <<< "$item"
    
    # Split the namespace flag properly if it exists
    if [ "$verb" = "yes" ]; then true; fi # Dummy to handle strict flags if needed
    
    RESULT=$(oc auth can-i "$verb" "$resource" ${ns_flag} --as="${SA}" 2>&1)
    
    if [ "$RESULT" = "yes" ]; then
        echo " ✓ ${desc}"
        ((PASS++))
    else
        echo " ✗ ${desc} — FAILED"
        ((FAIL++))
    fi
done

echo ""
echo "==> Verifying pipeline-deployer cannot exceed scope..."
echo ""

# Negative Checks: Array format: "Description|Verb|Resource|[Namespace_Flag]"
NEGATIVE_CHECKS=(
    "delete namespaces (cluster-scoped)|delete|namespaces|"
    "create clusterrolebindings|create|clusterrolebindings|"
    "get secrets|get|secrets|-n ${NS}"
)

for item in "${NEGATIVE_CHECKS[@]}"; do
    IFS="|" read -r desc verb resource ns_flag <<< "$item"
    
    # Run command with optional namespace flag
    if [ -n "$ns_flag" ]; then
        RESULT=$(oc auth can-i "$verb" "$resource" ${ns_flag} --as="${SA}" 2>&1)
    else
        RESULT=$(oc auth can-i "$verb" "$resource" --as="${SA}" 2>&1)
    fi

    if [ "$RESULT" = "no" ]; then
        echo " ✓ cannot ${desc}"
        ((PASS++))
    else
        echo " ✗ can ${desc} — UNEXPECTED, review role.yaml"
        ((FAIL++))
    fi
done

echo ""
echo "==> Result: ${PASS} passed, ${FAIL} failed"
echo ""

if [ $FAIL -gt 0 ]; then
    echo " Review manifests/rbac/role.yaml before proceeding."
    exit 1
else
    echo " RBAC verified. Safe to generate pipeline-deployer token."
    echo ""
    echo " Next step — generate token for GitHub Secrets:"
    echo " oc create token pipeline-deployer -n ${NS} --duration=8760h"
fi

