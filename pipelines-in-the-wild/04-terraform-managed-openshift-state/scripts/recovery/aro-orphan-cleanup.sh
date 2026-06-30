#!/usr/bin/env bash
# aro-orphan-cleanup.sh — inventory and cleanup for orphaned ARO resources
#
# terraform destroy on ARO can report success while leaving the app registration
# and managed resource group running. There is no error — resources keep billing.
#
# Usage:
#   ./scripts/recovery/aro-orphan-cleanup.sh inventory
#   ./scripts/recovery/aro-orphan-cleanup.sh delete-app <app-id>
#   ./scripts/recovery/aro-orphan-cleanup.sh delete-rg <resource-group-name>

set -euo pipefail

cmd="${1:-inventory}"
prefix="${ARO_PREFIX:-aro-}"

inventory() {
  echo "=== App registrations (prefix: ${prefix}) ==="
  az ad app list \
    --filter "startswith(displayName,'${prefix}')" \
    --query "[].{name:displayName,id:appId}" \
    --output table

  echo "=== Managed resource groups (prefix: ${prefix}) ==="
  az group list --query "[?starts_with(name, '${prefix}')]" --output table
}

delete_app() {
  local app_id="${2:?app ID required}"
  az ad app delete --id "${app_id}"
}

delete_rg() {
  local rg="${2:?resource group name required}"
  echo "This deletes ALL resources in ${rg}. Confirm the group is genuinely orphaned."
  read -r -p "Continue? [y/N] " confirm
  [[ "${confirm}" == [yY] ]] || exit 1
  az group delete --name "${rg}" --yes --no-wait
}

case "${cmd}" in
  inventory) inventory ;;
  delete-app) delete_app "$@" ;;
  delete-rg) delete_rg "$@" ;;
  *)
    echo "Unknown command: ${cmd}"
    echo "Commands: inventory | delete-app | delete-rg"
    exit 1
    ;;
esac
