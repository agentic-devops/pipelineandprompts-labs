variable "cluster_name" {
  description = "OSD cluster name"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "openshift_version" {
  description = "OpenShift version"
  type        = string
}

variable "machine_type" {
  description = "Compute Engine machine type for worker nodes"
  type        = string
  default     = "n2-standard-4"
}

variable "node_count" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "labels" {
  description = "Labels applied to GCP resources"
  type        = map(string)
  default     = {}
}

# Reference configuration — OSD on GCP creates persistent disks, load balancers,
# Cloud NAT, and IAM service accounts that may outlive namespace deletion.
# See scripts/recovery/osd-orphan-cleanup.sh.
#
# OSD cluster provisioning typically uses the OCM API or rhcs provider with GCP.
# Confirm import resource address for your provider version before importing orphans.

output "cluster_id" {
  description = "OSD cluster ID"
  value       = null
}
