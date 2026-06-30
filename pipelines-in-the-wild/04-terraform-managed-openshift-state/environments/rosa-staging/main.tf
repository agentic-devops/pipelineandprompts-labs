terraform {
  required_version = ">= 1.7"

  backend "s3" {
    bucket         = "my-org-terraform-state"
    key            = "rosa/staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    rhcs = {
      source  = "terraform-redhat/rhcs"
      version = "~> 1.6"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "rosa_cluster" {
  source = "../../modules/rosa-cluster"

  cluster_name         = var.cluster_name
  aws_region           = var.aws_region
  openshift_version    = var.openshift_version
  compute_machine_type = var.compute_machine_type
  account_role_prefix  = var.account_role_prefix
  operator_role_prefix = var.operator_role_prefix
  replicas             = 2
  multi_az             = false
  tags                 = var.tags
}
