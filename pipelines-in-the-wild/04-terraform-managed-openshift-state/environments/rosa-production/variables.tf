variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "ROSA cluster name"
  type        = string
  default     = "rosa-production"
}

variable "openshift_version" {
  description = "OpenShift version"
  type        = string
}

variable "compute_machine_type" {
  description = "Worker node instance type — confirm capacity in mandated region"
  type        = string
  default     = "m5.xlarge"
}

variable "account_role_prefix" {
  description = "ROSA account role prefix"
  type        = string
}

variable "operator_role_prefix" {
  description = "ROSA operator role prefix"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default = {
    environment = "production"
    platform    = "rosa"
    managed_by  = "terraform"
  }
}
