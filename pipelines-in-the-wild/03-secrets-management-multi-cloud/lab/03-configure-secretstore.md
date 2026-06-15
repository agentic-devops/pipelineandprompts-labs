# Step 3 — Configure SecretStore

**Time:** ~25 minutes  
**Goal:** Connect ESO to your central secrets manager for the `dev` namespace.

Pick your provider and follow the matching section.

> ESO 0.10.x uses `apiVersion: external-secrets.io/v1beta1` — all manifests in this repo match that version.

## Common Setup

Create the workload service account and scoped RBAC:

```bash
oc apply -f manifests/rbac/dev-secret-rbac.yaml
```

## Option A — Fake Provider (lab / demo clusters)

Use when you do not have AWS, Azure, or Vault available. Validates the full ESO sync and rotation flow without external dependencies.

```bash
oc apply -f manifests/lab/dev-secretstore-fake.yaml
```

Verify:

```bash
oc get secretstore dev-secretstore -n dev
# READY column should be True
```

Then skip to [04-sync-pull-secret.md](04-sync-pull-secret.md) and use the fake ExternalSecret manifest.

Docs: [ESO fake provider](https://external-secrets.io/v0.10.0/provider/fake/)

## Option B — AWS Secrets Manager

Official references:
- [ESO AWS Secrets Manager provider](https://external-secrets.io/v0.10.0/provider/aws-secrets-manager/)
- [AWS Secrets Manager user guide](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)
- [IAM roles for service accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [ROSA: Assuming an AWS IAM role for a service account](https://docs.openshift.com/rosa/authentication/assuming-an-aws-iam-role-for-a-service-account.html) (OpenShift on AWS)

1. Create IAM role with trust policy scoped to cluster OIDC and `secretsmanager:GetSecretValue` on specific ARNs
2. Annotate the service account:

```bash
oc annotate serviceaccount dev-workload-sa -n dev \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT_ID:role/dev-secrets-reader
```

3. Apply SecretStore:

```bash
oc apply -f manifests/secretstore/dev-secretstore-aws.yaml
```

4. Verify:

```bash
oc get secretstore dev-secretstore -n dev
oc describe secretstore dev-secretstore -n dev
```

## Option C — Azure Key Vault

Official references:
- [ESO Azure Key Vault provider](https://external-secrets.io/v0.10.0/provider/azure-key-vault/)
- [Azure Key Vault overview](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)
- [AKS Workload Identity overview](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Key Vault Secrets User built-in role](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles#key-vault-secrets-user)

1. Assign `Key Vault Secrets User` to managed identity scoped to your vault
2. Annotate the service account:

```bash
oc annotate serviceaccount dev-workload-sa -n dev \
  azure.workload.identity/client-id=MANAGED_IDENTITY_CLIENT_ID
```

3. Apply SecretStore:

```bash
oc apply -f manifests/secretstore/dev-secretstore-azure.yaml
```

4. Verify:

```bash
oc get secretstore dev-secretstore -n dev
oc describe secretstore dev-secretstore -n dev
```

## Option D — HashiCorp Vault

Official references:
- [ESO HashiCorp Vault provider](https://external-secrets.io/v0.10.0/provider/hashicorp-vault/)
- [Vault Kubernetes auth method](https://developer.hashicorp.com/vault/docs/auth/kubernetes)
- [Vault KV secrets engine v2](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2)
- [Vault on Kubernetes](https://developer.hashicorp.com/vault/docs/platform/k8s)

1. Run the auth setup script:

```bash
export VAULT_ADDR="https://vault.internal:8200"
export OPENSHIFT_API_SERVER="https://$(oc whoami --show-server | sed 's|https://api.|https://|')"
export VAULT_K8S_AUTH_ROLE="dev-secret-reader"
export VAULT_K8S_AUTH_SA="dev-workload-sa"
export VAULT_K8S_AUTH_NAMESPACE="dev"
export VAULT_POLICY="prod-secrets-policy"

chmod +x vault/kubernetes-auth-setup.sh
./vault/kubernetes-auth-setup.sh
```

2. Apply SecretStore:

```bash
oc apply -f manifests/secretstore/dev-secretstore-vault.yaml
```

3. Verify:

```bash
oc get secretstore dev-secretstore -n dev
oc describe secretstore dev-secretstore -n dev
```

## Validation

SecretStore status should show `Ready=True`. If not, check ESO logs:

```bash
oc logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=50
```

## Next

→ [04-sync-pull-secret.md](04-sync-pull-secret.md)
