#!/usr/bin/env bash
# rosa-orphan-cleanup.sh — inventory and cleanup for orphaned ROSA resources
#
# OIDC providers, operator roles, and account roles survive partial applies
# and failed destroys. Run inventory first; delete only confirmed orphans.
#
# Usage:
#   ./scripts/recovery/rosa-orphan-cleanup.sh inventory
#   ./scripts/recovery/rosa-orphan-cleanup.sh delete-cluster <cluster-name>
#   ./scripts/recovery/rosa-orphan-cleanup.sh delete-oidc <cluster-name>
#   ./scripts/recovery/rosa-orphan-cleanup.sh delete-operator-roles <cluster-name>
#
# Account roles are shared across clusters — only delete if no other clusters use them.

set -euo pipefail

cmd="${1:-inventory}"

inventory() {
  echo "=== ROSA clusters ==="
  if ! command -v rosa >/dev/null 2>&1; then
    echo "ERROR: rosa CLI not found — install from https://docs.openshift.com/rosa/rosa_install_access_delete_clusters/rosa_getting_started_iam.html"
    return 1
  fi
  rosa list-clusters --output json | \
    jq '.clusters[] | {id: .id, name: .name, state: .state}'

  echo "=== OIDC providers ==="
  aws iam list-open-id-connect-providers | \
    jq -r '.OpenIDConnectProviderList[].Arn'
}

delete_cluster() {
  local cluster="${2:?cluster name required}"
  rosa delete cluster --cluster="${cluster}" --yes
  echo "Cluster deletion initiated. Run delete-oidc and delete-operator-roles after cluster is gone."
}

delete_oidc() {
  local cluster="${2:?cluster name required}"
  rosa delete oidc-provider -c "${cluster}" --yes
}

delete_operator_roles() {
  local cluster="${2:?cluster name required}"
  rosa delete operator-roles -c "${cluster}" --yes
}

delete_account_roles() {
  local prefix="${2:?prefix required}"
  echo "WARNING: account roles may be shared. Confirm no other clusters use prefix '${prefix}'."
  read -r -p "Continue? [y/N] " confirm
  [[ "${confirm}" == [yY] ]] || exit 1
  rosa delete account-roles --prefix "${prefix}" --yes
}

case "${cmd}" in
  inventory) inventory ;;
  delete-cluster) delete_cluster "$@" ;;
  delete-oidc) delete_oidc "$@" ;;
  delete-operator-roles) delete_operator_roles "$@" ;;
  delete-account-roles) delete_account_roles "$@" ;;
  *)
    echo "Unknown command: ${cmd}"
    echo "Commands: inventory | delete-cluster | delete-oidc | delete-operator-roles | delete-account-roles"
    exit 1
    ;;
esac
