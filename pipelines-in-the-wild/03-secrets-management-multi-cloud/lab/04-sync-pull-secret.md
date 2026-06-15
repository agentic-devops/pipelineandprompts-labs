# Step 4 — Sync Pull Secret

**Time:** ~20 minutes  
**Goal:** Replace the manually created pull secret with an ESO-managed `ExternalSecret`.

## Remove the Manual Secret

```bash
oc delete secret registry-pull-secret -n dev
```

## Apply ExternalSecret

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

Decode and verify structure (not production values in a shared terminal):

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
| `SecretSyncedError` | Wrong remote path or field name | Check `remoteRef.key` and `property` values |
| Auth failure | SA annotation missing or wrong | Verify IAM/MI/Vault role binding |
| SecretStore not ready | Provider unreachable | Check network policies and vault URL |

## Next

→ [05-apply-rbac.md](05-apply-rbac.md)
