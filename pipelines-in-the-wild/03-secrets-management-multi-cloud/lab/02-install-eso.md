# Step 2 — Install External Secrets Operator

**Time:** ~15 minutes  
**Goal:** Install ESO via Helm and verify all operator pods are healthy.

## Install

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

helm install external-secrets \
  external-secrets/external-secrets \
  --namespace external-secrets \
  --create-namespace \
  -f manifests/operator/eso-install-values.yaml \
  --version 0.10.0
```

## Verify

```bash
oc get pods -n external-secrets
oc get crd | grep external-secrets
```

Expected CRDs:

- `secretstores.external-secrets.io`
- `externalsecrets.external-secrets.io`
- `clustersecretstores.external-secrets.io`

All pods in `external-secrets` namespace should be `Running`.

## Troubleshooting

```bash
oc logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=50
oc describe pod -n external-secrets -l app.kubernetes.io/name=external-secrets
```

## Next

→ [03-configure-secretstore.md](03-configure-secretstore.md)
