# Step 1 — Expose the Gap

**Time:** ~20 minutes  
**Goal:** Prove that without scoped RBAC, service accounts in a namespace can read and decode secrets.

This is the failure mode that audits find immediately. You need to see it to believe it.

## Why This Step Exists

Kubernetes Secrets are base64 encoded — not encrypted. OpenShift 4.x enables etcd encryption at rest by default, but that does not prevent a pod's service account from reading secrets via the API. Without explicit RBAC scoped to named secrets, any service account with broad `get`/`list` on secrets can retrieve every credential in the namespace.

## OpenShift Note

OpenShift ships with restrictive default RBAC — a new service account **cannot** read secrets until granted permission. To demonstrate the gap this lab is about, Step 1a creates a deliberately permissive Role that simulates ad-hoc environments where secrets were created without scoped access controls.

## Step 1a — Simulate Permissive Access (OpenShift / hardened clusters)

```bash
oc create serviceaccount probe-sa -n dev

cat <<'EOF' | oc apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: lab-permissive-secret-reader
  namespace: dev
rules:
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: lab-permissive-probe-binding
  namespace: dev
subjects:
  - kind: ServiceAccount
    name: probe-sa
    namespace: dev
roleRef:
  kind: Role
  name: lab-permissive-secret-reader
  apiGroup: rbac.authorization.k8s.io
EOF
```

> Remove this permissive binding in Step 5 when you apply scoped RBAC.

## Setup — Deploy a Probe Pod

```bash
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: secret-probe
  namespace: dev
  labels:
    lab: expose-the-gap
spec:
  serviceAccountName: probe-sa
  restartPolicy: Never
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: probe
      image: registry.redhat.io/ubi9/ubi-minimal:latest
      command: ["sleep", "300"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: ["ALL"]
        runAsNonRoot: true
EOF

oc wait --for=condition=Ready pod/secret-probe -n dev --timeout=120s
```

## Attempt 1 — Check RBAC with oc auth can-i

`oc auth can-i` returns `no` with exit code 1 — that is expected when access is denied.

```bash
echo -n "probe-sa can get registry-pull-secret: "
oc auth can-i get secret/registry-pull-secret \
  --as=system:serviceaccount:dev:probe-sa -n dev || true

echo -n "probe-sa can list all secrets: "
oc auth can-i list secrets \
  --as=system:serviceaccount:dev:probe-sa -n dev || true
```

**Expected with permissive Role (Step 1a):** both return `yes`.

## Attempt 2 — Decode the Credential

From your workstation (using your own credentials, which likely have broader access):

```bash
oc get secret registry-pull-secret -n dev -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq .
```

You will see plaintext username and password. This is what any service account with `get` access to secrets receives.

## Attempt 3 — List ALL Secrets in the Namespace

```bash
echo -n "probe-sa can list secrets: "
oc auth can-i list secrets \
  --as=system:serviceaccount:dev:probe-sa -n dev || true

# Show secret names visible to your own credentials
oc get secrets -n dev -o name
```

Without scoped RBAC, the permissive Role grants access to every secret in the namespace — database passwords, API tokens, TLS certs.

## What You Should Observe

| Check | Permissive RBAC (Step 1) | Scoped RBAC (Step 5) |
|---|---|---|
| Probe SA can `get` registry-pull-secret | yes | no |
| Probe SA can `list` all secrets | yes | no |
| Workload SA can `get` registry-pull-secret | no (not bound yet) | yes (scoped Role) |
| Workload SA can `get` other secrets | no | no |

## The Cross-Namespace Risk

```bash
echo -n "probe-sa can list prod secrets: "
oc auth can-i list secrets \
  --as=system:serviceaccount:dev:probe-sa -n prod || true
```

A `yes` means dev workloads can read prod secrets. Namespace labels alone do not enforce isolation — RBAC does.

## Cleanup (keep the secret for later steps)

```bash
oc delete pod secret-probe -n dev
# Keep probe-sa and permissive binding until Step 5
```

Keep `registry-pull-secret` in dev — you'll replace it with ESO in Step 4.

## Key Takeaway

> Base64 is not access control. RBAC must be applied **before** the first secret is created in a namespace, scoped to named resources.

## Next

→ [02-install-eso.md](02-install-eso.md)
