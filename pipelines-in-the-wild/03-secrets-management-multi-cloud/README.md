# secrets-management-multi-cloud

Production-ready External Secrets Operator manifests, RBAC templates, and rotation runbook for managing secrets across AWS, Azure, and HashiCorp Vault in OpenShift and Kubernetes environments.

This repository supports the article:
**Secrets Management Across Multi-Cloud Pipelines** — Pipelines in the Wild #3
https://pipelineandprompts.com/posts/secrets-management-multi-cloud-pipelines/

## What This Repo Does

Centralizes registry pull secrets (and the pattern for any credential) in a cloud-native secrets manager, syncs them into Kubernetes namespaces via External Secrets Operator (ESO), and locks down access with namespace-scoped RBAC.

Three problems solved:

1. **Secrets sprawl** — one canonical value per credential in a central store, not ad hoc copies per namespace
2. **RBAC gap** — base64 encoding is not access control; named-secret Roles prevent cross-workload reads
3. **Rotation lag** — explicit runbook for sync confirmation + rollout restart after every rotation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 — Central Secrets Store                                │
│  AWS Secrets Manager │ Azure Key Vault │ HashiCorp Vault          │
│  Canonical credential values, provider-scoped identity            │
└────────────────────────────┬────────────────────────────────────┘
                             │ provider API (read-only for workloads)
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 2 — Sync Operator (External Secrets Operator)          │
│  Watches central store → reconciles namespace K8s Secrets       │
│  Failure mode: sync lag between vault rotation and K8s Secret   │
└────────────────────────────┬────────────────────────────────────┘
                             │ creates/updates Secret objects
┌────────────────────────────▼────────────────────────────────────┐
│  Layer 3 — Namespace Isolation + RBAC                           │
│  prod namespace │ dev namespace                                   │
│  SecretStore (per ns) │ ExternalSecret │ Role (named secrets)   │
│  Workload pods mount secrets at startup — restart required      │
└─────────────────────────────────────────────────────────────────┘
```

See [diagrams/secrets-management-architecture.png](diagrams/secrets-management-architecture.png) for the full diagram.

## Provider Support

| Provider | Auth method | Manifest | Official docs |
|---|---|---|---|
| AWS Secrets Manager | IRSA via STS (JWT) | `manifests/secretstore/*-aws.yaml` | [ESO AWS provider](https://external-secrets.io/v0.10.0/provider/aws-secrets-manager/) · [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) · [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) |
| Azure Key Vault | Workload Identity | `manifests/secretstore/*-azure.yaml` | [ESO Azure KV provider](https://external-secrets.io/v0.10.0/provider/azure-key-vault/) · [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/overview) · [Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview) |
| HashiCorp Vault | Kubernetes auth | `manifests/secretstore/*-vault.yaml` | [ESO Vault provider](https://external-secrets.io/v0.10.0/provider/hashicorp-vault/) · [Vault Kubernetes auth](https://developer.hashicorp.com/vault/docs/auth/kubernetes) · [KV secrets engine v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2) |

Each provider has prod and dev variants. Apply **one** SecretStore per namespace — never share across environments.

OpenShift on AWS (ROSA): see [Assuming an AWS IAM role for a service account](https://docs.openshift.com/rosa/authentication/assuming-an-aws-iam-role-for-a-service-account.html) for OIDC/STS setup that pairs with the AWS SecretStore manifests.

## Prerequisites

- OpenShift 4.12+ or Kubernetes 1.26+
- Helm 3.x
- Cluster-admin access to install ESO and configure RBAC
- A central secrets manager account **or** use the fake provider manifests in `manifests/lab/` for demo clusters
- `oc` or `kubectl` CLI

> Manifests use `external-secrets.io/v1beta1` — compatible with ESO 0.10.x pinned in `manifests/operator/eso-install-values.yaml`.

## Quick Start

```bash
# 1. Create namespaces (before anything else)
oc apply -f manifests/namespace/

# 2. Install External Secrets Operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets --create-namespace \
  -f manifests/operator/eso-install-values.yaml \
  --version 0.10.0

# 3. Apply RBAC for your target namespace
oc apply -f manifests/rbac/dev-secret-rbac.yaml

# 4. Configure provider identity on the service account (see lab/03)
# 5. Apply SecretStore for your provider
oc apply -f manifests/secretstore/dev-secretstore-aws.yaml   # or azure/vault

# 6. Sync the pull secret
oc apply -f manifests/externalsecret/dev-pull-secret-external.yaml

# 7. Verify
oc get externalsecret registry-pull-secret -n dev
oc get secret registry-pull-secret -n dev
```

For the full guided exercise, start with [LAB.md](LAB.md).

## Manifest Reference

| Path | Purpose |
|---|---|
| `manifests/namespace/` | Namespace + ResourceQuota — apply first |
| `manifests/rbac/` | Named-secret Role + RoleBinding per environment |
| `manifests/operator/eso-install-values.yaml` | Pinned Helm values for ESO |
| `manifests/secretstore/` | Provider-specific SecretStore (prod + dev) |
| `manifests/externalsecret/` | ExternalSecret with dockerconfigjson template |
| `vault/kubernetes-auth-setup.sh` | Idempotent Vault K8s auth configuration |
| `vault/prod-secrets-policy.hcl` | Minimal Vault policy — no wildcards |

All manifests contain `# AUTHOR TO VALIDATE` comments for environment-specific values. Replace placeholders before applying to production.

## Validate Locally

No cluster required:

```bash
chmod +x scripts/validate-local.sh
./scripts/validate-local.sh
```

With a logged-in `oc` or `kubectl` session:

```bash
./scripts/validate-local.sh --with-cluster
```

The script uses Ruby (built into macOS) for YAML parsing and downloads kubeconform to `.cache/` if not installed.

Cluster walkthrough on OpenShift without AWS/Azure/Vault: use the fake provider path in `lab/03` and `manifests/lab/`.

## Lab Exercise

The `lab/` directory is a sequenced hands-on exercise — not a flat examples folder. The order matters:

1. **Expose the gap** — prove any SA can read secrets without RBAC
2. **Install ESO** — operator health check
3. **Configure SecretStore** — connect to your provider
4. **Sync pull secret** — ExternalSecret reconciliation
5. **Apply RBAC** — close the gap
6. **Trigger rotation** — observe sync lag, restart pods
7. **Write the runbook** — name the people for 2 AM rotations

→ [LAB.md](LAB.md) for the full index with time estimates.

## Rotation Runbook

The runbook that most teams don't have until after their first incident:

→ [docs/rotation-runbook.md](docs/rotation-runbook.md)

Covers: who approves, who restarts, who confirms health, escalation path, rollback procedure.

## Known Limitations

- **Sync lag** — `refreshInterval` (default 1h) means up to 60 minutes before K8s Secret reflects a vault change. Reduce for time-sensitive credentials (minimum recommended: 15m).
- **No automatic pod restart** — ESO syncs the Secret object; pods must be restarted explicitly after confirmed sync.
- **creationPolicy: Owner** — deleting an ExternalSecret deletes the managed Secret. Document this before granting delete access.
- **Placeholder values** — manifests ship with `AUTHOR TO VALIDATE` comments. CI fails if unresolved placeholders remain. Fill in your environment values before production use.
- **Single SecretStore per namespace** — ClusterSecretStore variant is on the roadmap for centrally managed stores.

## Roadmap

1. **ClusterSecretStore variant** — centrally managed stores with security tradeoff notes
2. **Rotation event webhook** — auto-restart affected deployments after confirmed ESO sync
3. **ROSA-specific variant** — Terraform + STS OIDC for AWS Secrets Manager on ROSA
4. **Secret scanning pre-commit hook** — `detect-secrets` or `gitleaks` integration
5. **Multi-cluster SecretStore federation** — single secrets manager, per-cluster identity bindings

## Linked Article

**Secrets Management Across Multi-Cloud Pipelines** — Pipelines in the Wild #3

https://pipelineandprompts.com/posts/secrets-management-multi-cloud-pipelines/

---

*Part of [pipelineandprompts-labs](https://github.com/agentic-devops/pipelineandprompts-labs)*
