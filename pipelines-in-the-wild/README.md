# Pipelines in the Wild - Code Labs

Hands-on code examples from the [Pipelines in the Wild](https://pipelineandprompts.com/series/pipelines-in-the-wild/) series.

## Labs

| # | Lab | Status |
|---|---|---|
| 1 | [Zero-Downtime Deployments on OpenShift](01-zero-downtime-deployments/) | Full walkthrough |
| 2 | [Retry Logic & Tiered Alerting](02-retry-logic-tiered-alerting/) | Full walkthrough |
| 3 | [Secrets Management in Multi-Cloud Pipelines](03-secrets-management-multi-cloud/) | Full walkthrough |
| 4 | [Terraform State Management for Managed OpenShift](04-terraform-managed-openshift-state/) | Full walkthrough |
| 5 | [Stop Managing Kubernetes](05-stop-managing-k8/) | Reference only |
| 6 | [Database Migration on Managed OpenShift](06-database-migration-managed-openshift/) | Full walkthrough |

## Prerequisites

- GitHub account with Actions enabled
- OpenShift cluster (ROSA HCP recommended) or Kubernetes cluster (labs 01, 03, 06)
- `oc` CLI or `kubectl`
- Docker (for local testing — labs 01 app, 02)
- Terraform (lab 04)

## What You'll Learn

- **Zero-downtime deployments**: HAProxy-based blue/green with canary progression
- **Pipeline resilience**: Automatic retry logic with exponential backoff
- **Alert optimization**: Tiered alerting to reduce noise and improve signal
- **Secrets management**: Vault / cloud secret stores, rotation strategies, RBAC
- **Terraform state management**: Remote backends, drift detection, and orphan recovery
- **Online schema changes**: Expand/contract migrations with role-split Jobs

## Quick Start

```bash
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/pipelines-in-the-wild

# Fastest local path — Waybill API + retry demo
cd 02-retry-logic-tiered-alerting
cp .env.example .env
docker compose up --build
```

For OpenShift blue/green, see [01-zero-downtime-deployments/QUICKSTART.md](01-zero-downtime-deployments/QUICKSTART.md).

---

*Part of [pipelineandprompts-labs](https://github.com/agentic-devops/pipelineandprompts-labs)*
