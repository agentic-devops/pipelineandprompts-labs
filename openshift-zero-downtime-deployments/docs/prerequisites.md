# Prerequisites — Full Setup Guide

Complete this guide before running the pipeline for the first time.
Work through each section in order.

---

## 1. ROSA HCP Cluster Access

Confirm you have access to your ROSA HCP cluster:

```bash
# Log in via the OpenShift console token
oc login --token=<your-token> \
  --server=https://api.<cluster>.<region>.openshiftapps.com:6443

# Confirm cluster version
oc version

# Confirm you have project creation rights
oc auth can-i create namespaces
```

Minimum OpenShift version: **4.14**

---

## 2. Container Image Registry Setup

You have two options for storing container images. **Option A** (internal registry) is recommended for demos and testing. **Option B** (external registry) is recommended for production.

---

### Option A: OpenShift Internal Registry (Recommended for Demo/Testing)

Build images directly on the cluster using the internal OpenShift registry. No external registry account required.

```bash
# Create ImageStream
oc create imagestream nodejs-zero-downtime -n zero-downtime-demo

# Create build configuration for binary builds
oc new-build --name=nodejs-zero-downtime \
  --binary --strategy=docker \
  --to=nodejs-zero-downtime:latest \
  -n zero-downtime-demo

# Build image from local app directory
oc start-build nodejs-zero-downtime \
  --from-dir=./app --follow \
  -n zero-downtime-demo

# Tag the image for blue and green deployments
oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:blue -n zero-downtime-demo

oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:green -n zero-downtime-demo

# Verify images are tagged
oc get imagestream nodejs-zero-downtime -n zero-downtime-demo
```

After building, update the deployments to use the internal registry:

```bash
# Update blue deployment
oc set image deployment/nodejs-blue \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:blue \
  -n zero-downtime-demo

# Update green deployment  
oc set image deployment/nodejs-green \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:green \
  -n zero-downtime-demo
```

**Pros:**
- No external registry account needed
- Images stay within your cluster
- Faster builds (no push over internet)
- Free for demo/testing

**Cons:**
- Images not accessible outside cluster
- Loses images if namespace is deleted
- Not suitable for multi-cluster deployments

---

### Option B: External Registry (Recommended for Production)

Use quay.io, Docker Hub, or your organization's registry for production deployments.

**Using Quay.io:**

1. Create account at https://quay.io
2. Create repository: `nodejs-zero-downtime`
3. Set visibility: **Public** (or create pull secret for private)

```bash
# Log into quay.io
podman login quay.io

# Build and push both images
cd app
chmod +x build-and-push.sh

# Edit REGISTRY variable in build-and-push.sh first:
# REGISTRY="quay.io/YOUR-USERNAME"

./build-and-push.sh
```

**For private registries**, create a pull secret:

```bash
# Create pull secret for quay.io
oc create secret docker-registry quay-pull-secret \
  --docker-server=quay.io \
  --docker-username=YOUR-USERNAME \
  --docker-password=YOUR-TOKEN \
  --namespace=zero-downtime-demo

# Link to default service account
oc secrets link default quay-pull-secret \
  --for=pull \
  --namespace=zero-downtime-demo
```

Update manifests to reference your registry:

```yaml
# manifests/blue/deployment.yaml
spec:
  template:
    spec:
      containers:
        - name: nodejs
          image: quay.io/YOUR-USERNAME/nodejs-zero-downtime:blue
```

**Pros:**
- Images accessible from multiple clusters
- Persistent storage outside cluster
- Better for CI/CD pipelines
- Supports image scanning/security

**Cons:**
- Requires external account
- Internet upload time for large images
- May have cost for private repos

---

Verify images are available:

```bash
# For internal registry:
oc get imagestream nodejs-zero-downtime -n zero-downtime-demo

# For external registry:
# Visit: https://quay.io/repository/YOUR-USERNAME/nodejs-zero-downtime
# Both `blue` and `green` tags should be visible
```

---

## 3. Namespace and RBAC

```bash
# Create namespace
oc apply -f manifests/namespace/namespace.yaml

# Apply RBAC
oc apply -f manifests/rbac/service-account.yaml
oc apply -f manifests/rbac/role.yaml
oc apply -f manifests/rbac/role-binding.yaml

# Verify RBAC is correct
chmod +x manifests/rbac/verify-rbac.sh
./manifests/rbac/verify-rbac.sh
```

Expected output: all checks pass, no failures.

---

## 4. GitHub Actions Authentication to ROSA HCP

ROSA HCP uses AWS STS. The pipeline authenticates using a
Kubernetes service account token. This is a long-lived token
suitable for CI/CD use.

### Step 1 — Generate the pipeline token

```bash
# Generate token valid for 1 year
oc create token pipeline-deployer \
  --namespace zero-downtime-demo \
  --duration=8760h
```

Copy the full token output — you will not see it again.

### Step 2 — Get your cluster API URL

```bash
oc whoami --show-server
# Returns: https://api.<cluster-name>.<region>.openshiftapps.com:6443
```

### Step 3 — Add GitHub Secrets

In your GitHub repository:
Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret name | Value |
|-------------|-------|
| `OPENSHIFT_SERVER` | Output of `oc whoami --show-server` |
| `OPENSHIFT_TOKEN` | Token from Step 1 |
| `OPENSHIFT_NAMESPACE` | `zero-downtime-demo` |

### Step 4 — Verify GitHub Actions can authenticate

Push a small change to a branch and check the validate-manifests
workflow runs without authentication errors. If you see
`Unauthorized` errors, regenerate the token and update the secret.

### Token rotation

The token generated above is valid for 1 year. Set a calendar
reminder to rotate it before expiry:

```bash
# Rotate token
oc create token pipeline-deployer \
  --namespace zero-downtime-demo \
  --duration=8760h

# Update OPENSHIFT_TOKEN secret in GitHub
# Settings → Secrets → OPENSHIFT_TOKEN → Update secret
```

---

## 5. Deploy Blue (Baseline)

Before running the pipeline, deploy blue manually as the baseline:

```bash
# Deploy blue deployment and service
oc apply -f manifests/blue/deployment.yaml
oc apply -f manifests/blue/service.yaml

# Apply the HAProxy Route (starts at 100% blue)
oc apply -f manifests/route/haproxy-route.yaml

# Wait for blue to be ready
oc rollout status deployment/nodejs-blue \
  --namespace zero-downtime-demo \
  --timeout=120s

# Get the Route URL
oc get route nodejs-zero-downtime \
  --namespace zero-downtime-demo \
  -o jsonpath='{.spec.host}'

# Test blue is serving traffic
curl https://<route-url>/version
# Expected: {"colour":"blue","version":"1.0.0",...}
```

---

## 6. Deploy Flagsmith

Follow the deploy order in `flagsmith/README.md`.

After Flagsmith is running:

```bash
# Get Flagsmith URL
oc get route flagsmith \
  --namespace zero-downtime-demo \
  -o jsonpath='{.spec.host}'
```

### Configure the deployment gate flag

1. Open Flagsmith UI at `https://<flagsmith-route>`
2. Create admin account (first user becomes admin)
3. Create organisation: `pipelineandprompts`
4. Create project: `pipelineandprompts`
5. Create environment: `production`
6. Create feature flag:
   - Name: `enable-green-deployment`
   - Type: Feature flag (boolean)
   - Default state: **Disabled**
7. Go to: production environment → API Keys
8. Copy the **Client-side environment key**

### Add Flagsmith secrets to GitHub

| Secret name | Value |
|-------------|-------|
| `FLAGSMITH_URL` | `https://<flagsmith-route>/api/v1` |
| `FLAGSMITH_API_KEY` | Client-side environment key from Step 8 |

---

## 7. Final Verification Checklist

Before triggering the pipeline for the first time, confirm:

```bash
# Namespace exists
oc get namespace zero-downtime-demo

# Blue deployment is running
oc get deployment nodejs-blue -n zero-downtime-demo

# Route exists and points to blue
oc get route nodejs-zero-downtime -n zero-downtime-demo

# Flagsmith is running
oc get deployment flagsmith -n zero-downtime-demo

# Pipeline service account exists
oc get serviceaccount pipeline-deployer -n zero-downtime-demo

# Images exist in quay.io
# Check: https://quay.io/repository/flyers22/nodejs-zero-downtime
```

GitHub Secrets checklist:
- [ ] `OPENSHIFT_SERVER`
- [ ] `OPENSHIFT_TOKEN`
- [ ] `OPENSHIFT_NAMESPACE`
- [ ] `FLAGSMITH_URL`
- [ ] `FLAGSMITH_API_KEY`

Flagsmith checklist:
- [ ] Project created: `pipelineandprompts`
- [ ] Environment created: `production`
- [ ] Flag created: `enable-green-deployment` (default: disabled)
- [ ] API key copied to GitHub Secrets

Once all items are checked, push a commit to `main` to trigger
the pipeline.
