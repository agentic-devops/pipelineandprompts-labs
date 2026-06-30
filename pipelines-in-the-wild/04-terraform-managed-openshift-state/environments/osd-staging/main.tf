terraform {
  required_version = ">= 1.7"

  backend "gcs" {
    bucket = "my-org-terraform-state"
    prefix = "osd/staging"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "osd_cluster" {
  source = "../../modules/osd-cluster"

  cluster_name      = var.cluster_name
  region            = var.region
  project_id        = var.project_id
  openshift_version = var.openshift_version
  node_count        = 2
  labels            = var.labels
}
