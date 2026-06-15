# Pipelines in the Wild - Code Labs

Hands-on code examples from the [Pipelines in the Wild](https://pipelineandprompts.com/series/pipelines-in-the-wild/) series.

## Labs

1. [Zero-Downtime Deployments on OpenShift](01-zero-downtime-deployments/) - Blue/green deployments with gradual traffic shifting on ROSA HCP
2. [Retry Logic & Tiered Alerting](02-retry-logic-tiered-alerting/) - Self-healing pipelines with intelligent retry and alert escalation
3. [Secrets Management in Multi-Cloud Pipelines](03-secrets-management-multi-cloud/) - External Secrets Operator manifests, RBAC templates, and rotation runbook for AWS, Azure, and Vault

## Prerequisites

- GitHub account with Actions enabled
- OpenShift cluster (ROSA HCP recommended) or Kubernetes cluster
- `oc` CLI or `kubectl`
- Docker (for local testing)
- Terraform (for lab 3)

## What You'll Learn

These labs demonstrate production CI/CD patterns used in real-world platform engineering:

- **Zero-downtime deployments**: HAProxy-based blue/green with canary progression
- **Pipeline resilience**: Automatic retry logic with exponential backoff
- **Alert optimization**: Tiered alerting to reduce noise and improve signal
- **Secrets management**: Vault integration, rotation strategies, and compliance

Each lab includes working code, GitHub Actions workflows, and step-by-step setup instructions.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/pipelines-in-the-wild

# Try the zero-downtime deployment demo
cd 01-zero-downtime-deployments
# Follow the README for OpenShift setup
```

---

*Part of [pipelineandprompts-labs](https://github.com/agentic-devops/pipelineandprompts-labs)*
