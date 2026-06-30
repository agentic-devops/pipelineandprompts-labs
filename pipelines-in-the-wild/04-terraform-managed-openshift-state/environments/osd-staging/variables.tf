variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "OSD cluster name"
  type        = string
  default     = "osd-staging"
}

variable "openshift_version" {
  description = "OpenShift version"
  type        = string
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default = {
    environment = "staging"
    platform    = "osd"
    managed_by  = "terraform"
  }
}
