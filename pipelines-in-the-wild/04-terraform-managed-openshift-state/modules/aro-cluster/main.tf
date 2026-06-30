variable "cluster_name" {
  description = "ARO cluster name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Customer-managed resource group for ARO cluster infrastructure"
  type        = string
}

variable "openshift_version" {
  description = "OpenShift version"
  type        = string
}

variable "pod_cidr" {
  description = "Pod CIDR block"
  type        = string
  default     = "10.128.0.0/14"
}

variable "service_cidr" {
  description = "Service CIDR block"
  type        = string
  default     = "172.30.0.0/16"
}

variable "tags" {
  description = "Tags applied to Azure resources"
  type        = map(string)
  default     = {}
}

# Reference configuration — ARO creates a managed resource group and app registration
# that may survive terraform destroy. See scripts/recovery/aro-orphan-cleanup.sh.
#
# resource "azurerm_redhat_openshift_cluster" "this" {
#   name                = var.cluster_name
#   location            = var.location
#   resource_group_name = var.resource_group_name
#
#   cluster_profile {
#     domain       = "${var.cluster_name}.example.com"
#     version      = var.openshift_version
#     fips_enabled = false
#   }
#
#   network_profile {
#     pod_cidr     = var.pod_cidr
#     service_cidr = var.service_cidr
#   }
#
#   tags = var.tags
# }

output "cluster_id" {
  description = "ARO cluster resource ID"
  value       = null
}

output "managed_resource_group" {
  description = "ARO-managed resource group name (check for orphans after destroy)"
  value       = null
}
