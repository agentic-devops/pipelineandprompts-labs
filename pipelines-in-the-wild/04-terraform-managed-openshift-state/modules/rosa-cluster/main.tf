terraform {
  required_providers {
    rhcs = {
      source  = "terraform-redhat/rhcs"
      version = "~> 1.6"
    }
  }
}

variable "cluster_name" {
  description = "ROSA cluster name"
  type        = string
}

variable "aws_region" {
  description = "AWS region for the cluster"
  type        = string
}

variable "openshift_version" {
  description = "OpenShift version (e.g. 4.14.24)"
  type        = string
}

variable "compute_machine_type" {
  description = "EC2 instance type for worker nodes"
  type        = string
  default     = "m5.xlarge"
}

variable "multi_az" {
  description = "Deploy across multiple availability zones"
  type        = bool
  default     = true
}

variable "replicas" {
  description = "Number of worker nodes"
  type        = number
  default     = 3
}

variable "account_role_prefix" {
  description = "Prefix for ROSA account roles (shared across clusters)"
  type        = string
}

variable "operator_role_prefix" {
  description = "Prefix for ROSA operator roles"
  type        = string
}

variable "tags" {
  description = "Tags applied to AWS resources"
  type        = map(string)
  default     = {}
}

# Reference configuration — uncomment and configure after governance approval.
# Confirm provider version and resource type before import/apply.
#
# resource "rhcs_cluster_rosa_classic" "this" {
#   cluster_name           = var.cluster_name
#   aws_region             = var.aws_region
#   openshift_version      = var.openshift_version
#   compute_machine_type   = var.compute_machine_type
#   multi_az               = var.multi_az
#   replicas               = var.replicas
#   account_role_prefix    = var.account_role_prefix
#   operator_role_prefix   = var.operator_role_prefix
#   tags                   = var.tags
# }

output "cluster_id" {
  description = "ROSA cluster ID (for import and cleanup scripts)"
  value       = null # replace with rhcs_cluster_rosa_classic.this.id when enabled
}
