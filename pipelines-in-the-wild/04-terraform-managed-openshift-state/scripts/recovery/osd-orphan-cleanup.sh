#!/usr/bin/env bash
# osd-orphan-cleanup.sh — inventory and cleanup for orphaned OSD/GCP resources
#
# OSD namespace deletion does not always trigger cleanup of underlying GCP resources.
# Persistent disks, load balancers, Cloud NAT, and IAM service accounts may survive.
#
# Usage:
#   ./scripts/recovery/osd-orphan-cleanup.sh inventory
#   ./scripts/recovery/osd-orphan-cleanup.sh delete-disk <disk-name> <zone>
#   ./scripts/recovery/osd-orphan-cleanup.sh disable-sa <service-account-email>
#   ./scripts/recovery/osd-orphan-cleanup.sh delete-sa <service-account-email>

set -euo pipefail

cmd="${1:-inventory}"
osd_filter="${OSD_FILTER:-osd}"

inventory() {
  echo "=== Unattached persistent disks ==="
  gcloud compute disks list \
    --filter="NOT users:*" \
    --format="table(name,zone,sizeGb,status)"

  echo "=== Load balancers (filter: description~${osd_filter}) ==="
  gcloud compute forwarding-rules list \
    --filter="description~${osd_filter}" \
    --format="table(name,region,IPAddress)"

  echo "=== Service accounts (filter: email~${osd_filter}) ==="
  gcloud iam service-accounts list \
    --filter="email~${osd_filter}" \
    --format="table(email,displayName,disabled)"
}

delete_disk() {
  local disk="${2:?disk name required}"
  local zone="${3:?zone required}"
  gcloud compute disks delete "${disk}" --zone="${zone}" --quiet
}

disable_sa() {
  local email="${2:?service account email required}"
  gcloud iam service-accounts disable "${email}"
}

delete_sa() {
  local email="${2:?service account email required}"
  gcloud iam service-accounts delete "${email}" --quiet
}

case "${cmd}" in
  inventory) inventory ;;
  delete-disk) delete_disk "$@" ;;
  disable-sa) disable_sa "$@" ;;
  delete-sa) delete_sa "$@" ;;
  *)
    echo "Unknown command: ${cmd}"
    echo "Commands: inventory | delete-disk | disable-sa | delete-sa"
    exit 1
    ;;
esac
