variable "resource_group_name" {
  description = "Resource group for Terraform state storage"
  type        = string
  default     = "rg-terraform-state"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "uksouth"
}

variable "storage_account_name" {
  description = "Globally unique storage account name (lowercase, no hyphens)"
  type        = string
  default     = "myorgterraformstate"
}

variable "container_name" {
  description = "Blob container for state files"
  type        = string
  default     = "tfstate"
}
