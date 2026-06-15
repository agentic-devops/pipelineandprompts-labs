#!/usr/bin/env bash
# Idempotent Vault Kubernetes auth backend setup for OpenShift/Kubernetes clusters.
# Safe to re-run — existing configuration is updated, not duplicated.
#
# Prerequisites:
#   - vault CLI authenticated with sufficient privileges
#   - VAULT_ADDR and VAULT_TOKEN set (or logged in via OIDC)
#
# Usage:
#   export VAULT_ADDR="https://vault.internal:8200"
#   export OPENSHIFT_API_SERVER="https://api.cluster.example.com:6443"
#   export VAULT_K8S_AUTH_ROLE="prod-secret-reader"
#   export VAULT_K8S_AUTH_SA="prod-workload-sa"
#   export VAULT_K8S_AUTH_NAMESPACE="prod"
#   export VAULT_POLICY="prod-secrets-policy"
#   ./kubernetes-auth-setup.sh

set -euo pipefail

: "${VAULT_ADDR:?Set VAULT_ADDR}"
: "${OPENSHIFT_API_SERVER:?Set OPENSHIFT_API_SERVER}"
: "${VAULT_K8S_AUTH_ROLE:=prod-secret-reader}"
: "${VAULT_K8S_AUTH_SA:=prod-workload-sa}"
: "${VAULT_K8S_AUTH_NAMESPACE:=prod}"
: "${VAULT_POLICY:=prod-secrets-policy}"
: "${VAULT_K8S_AUTH_MOUNT:=kubernetes}"

echo "==> Ensuring Kubernetes auth mount exists at auth/${VAULT_K8S_AUTH_MOUNT}"
if ! vault auth list -format=json | jq -e ".[\"${VAULT_K8S_AUTH_MOUNT}/\"]" >/dev/null 2>&1; then
  vault auth enable -path="${VAULT_K8S_AUTH_MOUNT}" kubernetes
else
  echo "    Mount already enabled — updating config"
fi

echo "==> Configuring Kubernetes auth backend"
vault write "auth/${VAULT_K8S_AUTH_MOUNT}/config" \
  kubernetes_host="${OPENSHIFT_API_SERVER}" \
  disable_iss_validation=true

echo "==> Ensuring policy ${VAULT_POLICY} exists"
if [ -f "$(dirname "$0")/prod-secrets-policy.hcl" ]; then
  vault policy write "${VAULT_POLICY}" "$(dirname "$0")/prod-secrets-policy.hcl"
else
  echo "    WARNING: prod-secrets-policy.hcl not found — skipping policy write"
fi

echo "==> Configuring role ${VAULT_K8S_AUTH_ROLE}"
vault write "auth/${VAULT_K8S_AUTH_MOUNT}/role/${VAULT_K8S_AUTH_ROLE}" \
  bound_service_account_names="${VAULT_K8S_AUTH_SA}" \
  bound_service_account_namespaces="${VAULT_K8S_AUTH_NAMESPACE}" \
  policies="${VAULT_POLICY}" \
  ttl=1h

echo "==> Kubernetes auth setup complete"
vault read "auth/${VAULT_K8S_AUTH_MOUNT}/role/${VAULT_K8S_AUTH_ROLE}"
