# Step 5 — Apply RBAC

**Time:** ~15 minutes  
**Goal:** Lock down namespace secret access and verify the gap from Step 1 is closed.

## Remove Permissive Lab Binding

If you created the permissive Role in Step 1a:

```bash
oc delete rolebinding lab-permissive-probe-binding -n dev --ignore-not-found
oc delete role lab-permissive-secret-reader -n dev --ignore-not-found
```

## Apply Scoped RBAC

If not already applied in Step 3:

```bash
oc apply -f manifests/rbac/dev-secret-rbac.yaml
```

This creates a `Role` scoped to `registry-pull-secret` only, bound to `dev-workload-sa`.

## Verify the Gap is Closed

`oc auth can-i` returns exit code 1 when the answer is `no` — append `|| true` to avoid script failures.

```bash
echo -n "probe-sa can get registry-pull-secret: "
oc auth can-i get secret/registry-pull-secret \
  --as=system:serviceaccount:dev:probe-sa -n dev || true
# Expected: no

echo -n "workload-sa can get registry-pull-secret: "
oc auth can-i get secret/registry-pull-secret \
  --as=system:serviceaccount:dev:dev-workload-sa -n dev || true
# Expected: yes

echo -n "workload-sa can list all secrets: "
oc auth can-i list secrets \
  --as=system:serviceaccount:dev:dev-workload-sa -n dev || true
# Expected: no
```

## Cleanup

```bash
oc delete pod secret-probe -n dev --ignore-not-found
oc delete serviceaccount probe-sa -n dev --ignore-not-found
```

## Key Takeaway

> RBAC scopes access to named secrets. The workload SA gets only what it needs. Everything else gets denied.

## Next

→ [06-trigger-rotation.md](06-trigger-rotation.md)
