# terraform-managed-openshift-state

> **Status:** Full walkthrough

Working Terraform configurations for ROSA, ARO, and OSD state management — bootstrap modules, per-environment remote backends, drift detection workflows, and orphan recovery scripts from production engagements.

Supports the article:
**The State File Is Gone. Now What?** — Pipelines in the Wild #4
https://pipelineandprompts.com/posts/terraform-managed-openshift-state/

## What This Repo Does

Managed OpenShift deployments create resources across multiple ownership boundaries. When Terraform apply fails mid-way — and in governed enterprise environments, it will — orphaned infrastructure accumulates: OIDC providers on AWS, app registrations on Azure, persistent disks on GCP.

This repo provides:

1. **Remote state bootstrap** — S3+DynamoDB (ROSA), Azure Blob (ARO), GCS (OSD) with versioning enabled
2. **State isolation by platform and environment** — separate state files prevent blast radius
3. **Scheduled drift detection** — daily `terraform plan -detailed-exitcode` across production environments
4. **Orphan recovery scripts** — inventory and cleanup for platform-specific residue

## Architecture

```
bootstrap/          # Run once manually per cloud — state backend infrastructure
environments/       # One state file per platform × environment
modules/            # rosa-cluster, aro-cluster, osd-cluster
scripts/            # Drift alerts + orphan recovery
.github/workflows/  # Scheduled drift detection
```

Each platform has its own remote backend, orphaned resource profile, and governance surface. The drift detection layer is platform-agnostic.

| Platform | Cloud | State backend | Orphans on partial apply |
|----------|-------|---------------|--------------------------|
| ROSA | AWS | S3 + DynamoDB | OIDC providers, operator roles, account roles |
| ARO | Azure | Azure Blob Storage | App registration, managed resource group |
| OSD | GCP | GCS bucket | Persistent disks, load balancers, IAM service accounts |

## Directory Structure

```
.
├── bootstrap/
│   ├── aws/         # S3 bucket + DynamoDB — run once manually
│   ├── azure/       # Azure Blob storage account — run once manually
│   └── gcp/         # GCS bucket — run once manually
├── environments/
│   ├── rosa-production/
│   ├── rosa-staging/
│   ├── aro-production/
│   ├── aro-staging/
│   ├── osd-production/
│   └── osd-staging/
├── modules/
│   ├── rosa-cluster/
│   ├── aro-cluster/
│   └── osd-cluster/
├── scripts/
│   ├── alert.py
│   └── recovery/
├── docs/
│   ├── governance-checklist.md
│   └── import-and-state-recovery.md
└── .github/workflows/
    └── drift-detection.yml
```

## Quick Start

### 1. Bootstrap remote state (before any cluster resources)

Pick your platform and run bootstrap once:

```bash
# ROSA — AWS
cd bootstrap/aws
terraform init && terraform apply

# ARO — Azure
cd bootstrap/azure
terraform init && terraform apply

# OSD — GCP
cd bootstrap/gcp
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

Confirm versioning is enabled on the bucket before proceeding.

### 2. Configure an environment

```bash
cd environments/rosa-production
# Edit variables.tf or provide a terraform.tfvars
terraform init
terraform plan -out=tfplan   # review before apply
```

Cluster resource blocks in `modules/` are commented out by default — uncomment after governance approval and provider credentials are configured.

### 3. Enable drift detection

Set GitHub Actions secrets:

| Secret | Used by |
|--------|---------|
| `AWS_PLAN_ROLE_ARN` | rosa-production |
| `AZURE_CREDENTIALS` | aro-production |
| `GCP_CREDENTIALS` | osd-production |
| `SLACK_WEBHOOK_URL` | drift alerts |

The workflow runs daily at 06:00 UTC and on manual dispatch.

### 4. Recover orphans

```bash
# Inventory only — safe to run anytime
./scripts/recovery/rosa-orphan-cleanup.sh inventory
./scripts/recovery/aro-orphan-cleanup.sh inventory
./scripts/recovery/osd-orphan-cleanup.sh inventory
```

See [docs/import-and-state-recovery.md](docs/import-and-state-recovery.md) for import commands when resources should remain Terraform-managed.

## Prerequisites

- Terraform >= 1.7 (workflow uses `~1.7`; local 1.5.x will fail version checks)
- Cloud CLI tools: `aws`, `az`, `gcloud`, `rosa` (as needed)
- GitHub Actions enabled (for drift detection)
- Governance prerequisites completed — see [docs/governance-checklist.md](docs/governance-checklist.md)

## Validate Locally

No cloud credentials required:

```bash
./scripts/validate-local.sh
```

Checks shell syntax, `alert.py`, workflow YAML, `terraform fmt`, and `terraform validate` across bootstrap, modules, and all environments. Downloads Terraform 1.7.5 to `.cache/` automatically if your installed version is too old.

Optional — run recovery inventory against live accounts (requires CLIs + credentials):

```bash
./scripts/validate-local.sh --with-cloud
```

## Key Design Decisions

- **Remote state before the first resource block** — not a day-two task
- **Separate state per environment** — a broken `rosa-staging` state does not affect `aro-production`
- **Read-only plan role for drift detection** — separate from the apply role
- **Versioned backends** — every previous state is restorable if an apply corrupts the current one
- **`-detailed-exitcode`** — exit code 2 means drift detected; exit code 0 means no changes

## What This Repo Does Not Do

Drift detection surfaces the problem. It does not resolve it. There is no reliable cleanup sequence for a partial managed OpenShift install that leaves the account clean with confidence — see recovery scripts and use judgment.

The governance relationship is the critical path. Remote state and drift detection are irrelevant if the governance team denies the permissions required for the cluster to function.

---

*Part of [pipelineandprompts-labs](https://github.com/agentic-devops/pipelineandprompts-labs)*
