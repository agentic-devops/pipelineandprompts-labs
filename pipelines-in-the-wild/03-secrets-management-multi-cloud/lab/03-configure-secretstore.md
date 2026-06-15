# Step 3 — Configure SecretStore

**Time:** ~25 minutes  
**Goal:** Connect ESO to your central secrets manager for the `dev` namespace.

Pick your provider and follow the matching section.

## Common Setup

Create the workload service account:

```bash
oc apply -f manifests/rbac/dev-secret-rbac.yaml
```

## AWS Secrets Manager

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

## Azure Key Vault

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

## HashiCorp Vault

1. Run the auth setup script:

```bash
export VAULT_ADDR="https://vault.internal:8200"
export OPENSHIFT_API_SERVER="https://$(oc whoami --show-server)"
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
