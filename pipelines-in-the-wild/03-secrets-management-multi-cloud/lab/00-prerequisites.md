# Step 0 — Prerequisites

Before starting the lab, verify you have everything needed.

## Tool Versions

| Tool | Minimum version | Verify |
|---|---|---|
| `oc` or `kubectl` | OpenShift 4.12+ / K8s 1.26+ | `oc version` |
| Helm | 3.x | `helm version` |
| `jq` | any recent | `jq --version` |
| `base64` | system default | `base64 --version` |

## Cluster Access

- Cluster-admin or sufficient privileges to:
  - Create namespaces
  - Install Helm charts in `external-secrets` namespace
  - Create `SecretStore` and `ExternalSecret` CRDs
  - Create `Role` and `RoleBinding` resources

```bash
oc whoami
oc auth can-i create secretstore --all-namespaces
```

## Provider Account

Choose one provider and confirm access:

### AWS Secrets Manager

- IAM role with `secretsmanager:GetSecretValue` scoped to specific secret ARNs
- Cluster OIDC provider configured for IRSA
- Secret created at path matching `dev/registry/pull-secret` with fields: `host`, `username`, `password`

Docs: [ESO AWS provider](https://external-secrets.io/v0.10.0/provider/aws-secrets-manager/) · [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html) · [IRSA](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)

### Azure Key Vault

- Key Vault with a secret at matching path
- Managed identity with `Key Vault Secrets User` role on the vault
- Workload Identity configured on the cluster

Docs: [ESO Azure provider](https://external-secrets.io/v0.10.0/provider/azure-key-vault/) · [Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/overview) · [Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)

### HashiCorp Vault

- Vault server reachable from the cluster
- `vault` CLI authenticated
- KV v2 secrets engine enabled at `secret/`
- Secret at `secret/data/dev/registry/pull-secret`

Docs: [ESO Vault provider](https://external-secrets.io/v0.10.0/provider/hashicorp-vault/) · [Kubernetes auth](https://developer.hashicorp.com/vault/docs/auth/kubernetes) · [KV v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)

## Lab Namespace

This lab uses the `dev` namespace. Create it now:

```bash
oc apply -f manifests/namespace/dev-namespace.yaml
```

## Registry Pull Secret (Manual — for Step 1 only)

Step 1 deliberately uses a manually created secret to demonstrate the RBAC gap. Create a throwaway secret:

```bash
oc create secret docker-registry registry-pull-secret \
  --docker-server=registry.internal \
  --docker-username=lab-user \
  --docker-password=lab-password-change-me \
  -n dev
```

> This secret will be replaced by ESO in later steps. Use fake credentials — never real production values in a lab.

## Next

→ [01-expose-the-gap.md](01-expose-the-gap.md)
