variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Default GCP region for provider"
  type        = string
  default     = "us-central1"
}

variable "state_bucket_name" {
  description = "GCS bucket name for Terraform state"
  type        = string
  default     = "my-org-terraform-state"
}

variable "location" {
  description = "GCS bucket location (multi-region or region)"
  type        = string
  default     = "US"
}
