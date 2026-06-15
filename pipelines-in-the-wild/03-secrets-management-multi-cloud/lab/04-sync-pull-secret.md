# Step 4 — Sync Pull Secret

**Time:** ~20 minutes  
**Goal:** Replace the manually created pull secret with an ESO-managed `ExternalSecret`.

## Remove the Manual Secret

Delete both the manual secret and any previous ExternalSecret to avoid owner conflicts:

```bash
oc delete externalsecret registry-pull-secret -n dev --ignore-not-found
oc delete secret registry-pull-secret -n dev --ignore-not-found
```

Wait a moment for deletion to complete:

```bash
sleep 2
oc get secret registry-pull-secret -n dev 2>&1 || true
```

## Apply ExternalSecret

**Fake provider (lab path):**

```bash
oc apply -f manifests/lab/dev-pull-secret-fake.yaml
```

**AWS / Azure / Vault:**

Update `manifests/externalsecret/dev-pull-secret-external.yaml` with your provider's remote secret path and field names, then:

```bash
oc apply -f manifests/externalsecret/dev-pull-secret-external.yaml
```

## Verify Sync

```bash
oc get externalsecret registry-pull-secret -n dev
```

Expected:

```
NAME                   STORE              REFRESH INTERVAL   STATUS         READY
registry-pull-secret   dev-secretstore    1h                 SecretSynced   True
```

Confirm the Kubernetes secret was created:

```bash
oc get secret registry-pull-secret -n dev
oc get secret registry-pull-secret -n dev -o jsonpath='{.type}'
# Expected: kubernetes.io/dockerconfigjson
```

Verify structure without printing credential values:

```bash
oc get secret registry-pull-secret -n dev \
  -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq 'keys'
# Expected: ["auths"]
```

## Troubleshooting

```bash
oc describe externalsecret registry-pull-secret -n dev
oc logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=50
```

Common failures:

| Error | Cause | Fix |
|---|---|---|
| `SecretSyncedError` — wrong path/field | `remoteRef.key` or `property` mismatch | Check provider secret path and field names |
| `SecretSyncedError` — already exists | Manual secret not fully deleted before apply | Delete both ExternalSecret and Secret, wait, re-apply |
| Auth failure | SA annotation missing or wrong | Verify IAM/MI/Vault role binding |
| SecretStore not ready | Provider unreachable | Check network policies and vault URL |
| `no matches for kind SecretStore in version v1` | API version mismatch | Use `external-secrets.io/v1beta1` with ESO 0.10.x |

## Next

→ [05-apply-rbac.md](05-apply-rbac.md)
