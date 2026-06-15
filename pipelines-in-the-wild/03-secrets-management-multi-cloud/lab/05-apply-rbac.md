# Step 5 — Apply RBAC

**Time:** ~15 minutes  
**Goal:** Lock down namespace secret access and verify the gap from Step 1 is closed.

## Apply RBAC

If not already applied in Step 3:

```bash
oc apply -f manifests/rbac/dev-secret-rbac.yaml
```

This creates a `Role` scoped to `registry-pull-secret` only, bound to `dev-workload-sa`.

## Verify the Gap is Closed

Re-run the probe from Step 1:

```bash
oc create serviceaccount probe-sa -n dev

cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-probe
  namespace: dev
spec:
  serviceAccountName: probe-sa
  restartPolicy: Never
  containers:
    - name: probe
      image: registry.redhat.io/ubi9/ubi-minimal:latest
      command: ["sleep", "120"]
EOF

oc wait --for=condition=Ready pod/secret-probe -n dev --timeout=60s
```

Attempt to read the secret:

```bash
oc exec secret-probe -n dev -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
  CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

  curl -s -o /dev/null -w "%{http_code}" --cacert $CACERT \
    -H "Authorization: Bearer $TOKEN" \
    "https://kubernetes.default.svc/api/v1/namespaces/$NAMESPACE/secrets/registry-pull-secret"
'
```

**Expected:** `403`

## Verify Workload SA Still Works

```bash
oc auth can-i get secret/registry-pull-secret \
  --as=system:serviceaccount:dev:dev-workload-sa -n dev
# Expected: yes
```

## Cleanup

```bash
oc delete pod secret-probe -n dev
oc delete serviceaccount probe-sa -n dev
```

## Key Takeaway

> RBAC scopes access to named secrets. The workload SA gets only what it needs. Everything else gets 403.

## Next

→ [06-trigger-rotation.md](06-trigger-rotation.md)
