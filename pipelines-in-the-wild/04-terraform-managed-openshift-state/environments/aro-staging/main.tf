terraform {
  required_version = ">= 1.7"

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "myorgterraformstate"
    container_name       = "tfstate"
    key                  = "aro/staging/terraform.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

module "aro_cluster" {
  source = "../../modules/aro-cluster"

  cluster_name        = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  openshift_version   = var.openshift_version
  tags                = var.tags
}
