# Step 6 — Trigger Rotation

**Time:** ~30 minutes  
**Goal:** Rotate a credential in the central store, observe the sync lag, prove the running pod still uses the stale value, then restart and confirm the new credential is active.

This is the rotation failure mode that documentation does not cover.

## Background

When a secret rotates in the central vault:

1. ESO reconciles the namespace-level Kubernetes `Secret` within `refreshInterval`
2. The running pod **does not** automatically pick up the new value
3. The pod uses whatever was mounted at startup until it is restarted

The vault shows rotation succeeded. The pod disagrees.

## Setup — Deploy a Workload Using the Pull Secret

If you don't already have a deployment referencing the synced secret:

```bash
cat <<'EOF' | oc apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: registry-consumer
  namespace: dev
  labels:
    lab: trigger-rotation
spec:
  replicas: 1
  selector:
    matchLabels:
      app: registry-consumer
  template:
    metadata:
      labels:
        app: registry-consumer
    spec:
      serviceAccountName: dev-workload-sa
      imagePullSecrets:
        - name: registry-pull-secret
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: registry.redhat.io/ubi9/ubi-minimal:latest
          command: ["sleep", "infinity"]
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            runAsNonRoot: true
EOF

oc rollout status deployment/registry-consumer -n dev
```

Record the current pod name and start time:

```bash
POD=$(oc get pod -n dev -l app=registry-consumer -o jsonpath='{.items[0].metadata.name}')
echo "Pod: $POD"
oc get pod $POD -n dev -o jsonpath='{.status.startTime}'
```

## Step 1 — Record the Current Credential

Decode the Kubernetes secret as it exists right now:

```bash
echo "=== K8s Secret (current) ==="
oc get secret registry-pull-secret -n dev \
  -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq .

echo "=== ExternalSecret status ==="
oc get externalsecret registry-pull-secret -n dev
```

Note the `refreshInterval` — this is your maximum sync lag:

```bash
oc get externalsecret registry-pull-secret -n dev \
  -o jsonpath='{.spec.refreshInterval}'
```

## Step 2 — Rotate in the Central Store

### Fake provider (lab path)

The fake SecretStore ships with `v1` and `v2` credential versions. Patch the ExternalSecret to `v2`:

```bash
oc patch externalsecret registry-pull-secret -n dev --type=json -p='[
  {"op":"replace","path":"/spec/dataFrom/0/extract/version","value":"v2"}
]'
```

### AWS Secrets Manager

Docs: [Rotate a secret](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)

```bash
aws secretsmanager update-secret \
  --secret-id dev/registry/pull-secret \
  --secret-string '{"host":"registry.internal","username":"rotated-user","password":"NEW-PASSWORD-HERE"}'
```

### Azure Key Vault

Docs: [Add a secret version](https://learn.microsoft.com/en-us/azure/key-vault/secrets/about-secrets#secret-versions)

```bash
az keyvault secret set \
  --vault-name YOUR-KEYVAULT-NAME \
  --name dev-registry-pull-secret \
  --value '{"host":"registry.internal","username":"rotated-user","password":"NEW-PASSWORD-HERE"}'
```

### HashiCorp Vault

Docs: [KV v2 — update version](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2#versioned-kv-secrets-engine)

```bash
vault kv put secret/dev/registry/pull-secret \
  host=registry.internal \
  username=rotated-user \
  password=NEW-PASSWORD-HERE
```

**Timestamp the rotation:**

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

## Step 3 — Watch ESO Sync (Observe the Lag)

Force an immediate reconcile instead of waiting for `refreshInterval`:

```bash
# Annotate to trigger immediate sync
oc annotate externalsecret registry-pull-secret -n dev \
  force-sync=$(date +%s) --overwrite
```

Watch status:

```bash
oc get externalsecret registry-pull-secret -n dev -w
```

Wait until `STATUS=SecretSynced` and `READY=True`. Note how long this took.

Verify the K8s secret now has the new credential:

```bash
echo "=== K8s Secret (after sync) ==="
oc get secret registry-pull-secret -n dev \
  -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq .
```

Confirm `username` is now `rotated-user`.

## Step 4 — Prove the Pod Still Has the OLD Credential

The pod has **not** been restarted. Check what's actually mounted inside it:

```bash
# The pod's imagePullSecret is resolved at scheduling time
# Check the pod's age — it predates the rotation
oc get pod $POD -n dev -o jsonpath='{.status.startTime}{"\n"}{.metadata.creationTimestamp}{"\n"}'

# Describe events — no new pull attempt
oc describe pod $POD -n dev | grep -A10 "Events:"
```

If your registry enforces credential validation on pull, you can demonstrate stale creds by pushing a new image tag and observing the pod does not re-pull (it uses the cached image layer). The credential mismatch only surfaces on the **next** pull attempt — which happens after restart.

**The proof:** K8s secret has `rotated-user`. Pod started before rotation. Pod will not use `rotated-user` until restarted.

## Step 5 — Restart and Confirm

```bash
# Confirm sync completed BEFORE restarting
oc get externalsecret registry-pull-secret -n dev

# Restart the deployment
oc rollout restart deployment/registry-consumer -n dev
oc rollout status deployment/registry-consumer -n dev

# New pod should have started after rotation
NEW_POD=$(oc get pod -n dev -l app=registry-consumer -o jsonpath='{.items[0].metadata.name}')
echo "New pod: $NEW_POD"
oc get pod $NEW_POD -n dev -o jsonpath='{.status.startTime}'
```

Verify the new pod pulled successfully (no ImagePullBackOff):

```bash
oc get pod $NEW_POD -n dev
oc describe pod $NEW_POD -n dev | grep -A5 "Events:"
```

## Step 6 — Simulate a Bad Rotation (Optional)

Rotate to an intentionally wrong password, sync, restart, and observe ImagePullBackOff:

```bash
# Set bad password in central store (provider-specific)
# Force sync
oc annotate externalsecret registry-pull-secret -n dev \
  force-sync=$(date +%s) --overwrite

# Restart
oc rollout restart deployment/registry-consumer -n dev

# Observe failure
oc get pods -n dev -l app=registry-consumer
# Expected: ImagePullBackOff or ErrImagePull
```

Rollback procedure:

```bash
# 1. Undo deployment — buys time but does NOT fix the secret
oc rollout undo deployment/registry-consumer -n dev

# 2. Restore correct password in central store
# 3. Force ESO re-sync
# 4. Restart again
```

> `oc rollout undo` rolls back deployment config, not the secret value.

## What You Should Observe

| Event | K8s Secret value | Pod credential | Pod status |
|---|---|---|---|
| Before rotation | `lab-user` | `lab-user` (mounted at start) | Running |
| After vault rotation, before sync | `lab-user` | `lab-user` | Running |
| After ESO sync | `rotated-user` | `lab-user` (stale) | Running |
| After rollout restart | `rotated-user` | `rotated-user` | Running |
| Bad rotation + restart | `bad-password` | `bad-password` | ImagePullBackOff |

## Key Takeaway

> Rotation in the vault ≠ rotation in the running workload. An explicit rollout restart after confirmed ESO sync is required. This must be a named step in your runbook — not a footnote.

## Next

→ [07-rotation-runbook-exercise.md](07-rotation-runbook-exercise.md)
