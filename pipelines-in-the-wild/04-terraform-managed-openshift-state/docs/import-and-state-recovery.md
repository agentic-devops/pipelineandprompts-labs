# Importing Orphaned Resources Back Into Terraform State

Use these commands when a resource survived a partial apply and should continue to be managed by Terraform.

**Always run `terraform plan` after import.** There will be diffs in optional attributes — review each one before applying.

## ROSA (AWS)

```bash
cd environments/rosa-production

# Confirm provider version and resource type in modules/rosa-cluster/main.tf
terraform import \
  rhcs_cluster_rosa_classic.production \
  my-rosa-cluster-id   # use cluster ID, not name
```

## ARO (Azure)

```bash
cd environments/aro-production

terraform import \
  azurerm_resource_group.aro_cluster \
  /subscriptions/<subscription-id>/resourceGroups/<resource-group-name>
```

## OSD (GCP)

Confirm import resource address for your OSD provider version before running import.

```bash
cd environments/osd-production

# Example — replace resource address and ID with values from your configuration
# terraform import <resource_address> <cluster_id>
```

## State Recovery from Versioned Backend

If an apply corrupted the current state file, restore a previous version:

**S3:**
```bash
aws s3api list-object-versions \
  --bucket my-org-terraform-state \
  --prefix rosa/production/terraform.tfstate

aws s3api get-object \
  --bucket my-org-terraform-state \
  --key rosa/production/terraform.tfstate \
  --version-id <version-id> \
  terraform.tfstate.restored
```

**Azure Blob:** use portal or `az storage blob list` with `--include versions`.

**GCS:**
```bash
gsutil ls -a gs://my-org-terraform-state/osd/production/
gsutil cp gs://my-org-terraform-state/osd/production/default.tfstate#<generation> ./restored.tfstate
```
