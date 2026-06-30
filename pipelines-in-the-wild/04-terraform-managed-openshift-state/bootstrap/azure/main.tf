# bootstrap/azure — Azure Blob storage account for Terraform state
# Run once manually before the first ARO deployment.
#
# Note: in private ARO environments with no public egress, configure a private
# endpoint for the storage account so the Terraform runner can reach it.
# Public endpoint access can be disabled at the storage account level once
# the private endpoint is confirmed working.

resource "azurerm_resource_group" "terraform_state" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_storage_account" "terraform_state" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.terraform_state.name
  location                 = azurerm_resource_group.terraform_state.location
  account_tier             = "Standard"
  account_replication_type = "GRS"

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "tfstate" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.terraform_state.name
  container_access_type = "private"
}

output "storage_account_name" {
  value = azurerm_storage_account.terraform_state.name
}

output "container_name" {
  value = azurerm_storage_container.tfstate.name
}

output "resource_group_name" {
  value = azurerm_resource_group.terraform_state.name
}
