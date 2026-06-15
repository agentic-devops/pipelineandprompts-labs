# Step 1 — Expose the Gap

**Time:** ~20 minutes  
**Goal:** Prove that without RBAC, any service account in a namespace can read and decode every secret.

This is the failure mode that audits find immediately. You need to see it to believe it.

## Why This Step Exists

Kubernetes Secrets are base64 encoded — not encrypted. OpenShift 4.x enables etcd encryption at rest by default, but that does not prevent a pod's service account from reading secrets via the API. Without explicit RBAC, the default service account in a namespace can `get` and `list` all secrets.

## Setup — Deploy a Probe Pod

Create a service account with **no** secret-reading Role bound to it:

```bash
oc create serviceaccount probe-sa -n dev
```

Deploy a pod that uses this service account and attempts to read the pull secret:

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
  containers:
    - name: probe
      image: registry.redhat.io/ubi9/ubi-minimal:latest
      command: ["sleep", "300"]
EOF
```

Wait for the pod to be running:

```bash
oc wait --for=condition=Ready pod/secret-probe -n dev --timeout=60s
```

## Attempt 1 — Read the Secret via API

Exec into the probe pod and use the mounted service account token to query the Kubernetes API:

```bash
oc exec -it secret-probe -n dev -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
  CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  APISERVER=https://kubernetes.default.svc

  curl -s --cacert $CACERT \
    -H "Authorization: Bearer $TOKEN" \
    "$APISERVER/api/v1/namespaces/$NAMESPACE/secrets/registry-pull-secret"
'
```

**Expected result without RBAC:** HTTP 200 with the full secret object, including base64-encoded `.dockerconfigjson`.

If you get a 403 Forbidden, your cluster may have a restrictive default RBAC policy (common on hardened OpenShift). Skip to the oc CLI demonstration below — the principle is the same.

## Attempt 2 — Decode the Credential

From your workstation (using your own credentials, which likely have broader access):

```bash
oc get secret registry-pull-secret -n dev -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq .
```

You will see plaintext username and password. This is what any service account with `get` access to secrets receives.

## Attempt 3 — List ALL Secrets in the Namespace

```bash
oc exec -it secret-probe -n dev -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  NAMESPACE=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace)
  CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

  curl -s --cacert $CACERT \
    -H "Authorization: Bearer $TOKEN" \
    "$APISERVER/api/v1/namespaces/$NAMESPACE/secrets" \
    | jq ".items[].metadata.name"
'
```

Without RBAC, this lists every secret name in the namespace — database passwords, API tokens, TLS certs.

## What You Should Observe

| Check | Without RBAC | With RBAC (Step 5) |
|---|---|---|
| Probe SA can `get` registry-pull-secret | Yes | No (403) |
| Probe SA can `list` all secrets | Yes | No (403) |
| Workload SA can `get` registry-pull-secret | Yes (default) | Yes (scoped Role) |
| Workload SA can `get` other secrets | Yes | No |

## The Cross-Namespace Risk

Repeat the list command but target the `prod` namespace (if it exists):

```bash
oc exec -it secret-probe -n dev -- sh -c '
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
  CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

  curl -s -o /dev/null -w "%{http_code}" --cacert $CACERT \
    -H "Authorization: Bearer $TOKEN" \
    "https://kubernetes.default.svc/api/v1/namespaces/prod/secrets"
'
```

A `200` means dev workloads can read prod secrets. Namespace labels alone do not enforce isolation — RBAC does.

## Cleanup (keep the secret for later steps)

```bash
oc delete pod secret-probe -n dev
oc delete serviceaccount probe-sa -n dev
```

Keep `registry-pull-secret` in dev — you'll replace it with ESO in Step 4.

## Key Takeaway

> Base64 is not access control. RBAC must be applied **before** the first secret is created in a namespace, scoped to named resources.

## Next

→ [02-install-eso.md](02-install-eso.md)
