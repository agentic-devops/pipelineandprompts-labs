variable "cluster_name" {
  description = "ARO cluster name"
  type        = string
  default     = "aro-staging"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "uksouth"
}

variable "resource_group_name" {
  description = "Customer-managed resource group for ARO"
  type        = string
}

variable "openshift_version" {
  description = "OpenShift version"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    environment = "staging"
    platform    = "aro"
    managed_by  = "terraform"
  }
}
