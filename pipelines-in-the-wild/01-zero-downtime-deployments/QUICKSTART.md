# Quick Start Guide — Zero-Downtime Deployments

This guide shows exactly what commands to run for a working deployment on ROSA HCP using the OpenShift internal registry. Takes ~10 minutes.

## Prerequisites

- ROSA HCP cluster running
- `oc` CLI installed
- Logged into cluster: `oc whoami` should show your username

## Step 1: Create Namespace and RBAC

```bash
# Create namespace
oc apply -f manifests/namespace/namespace.yaml

# Apply RBAC (service account for pipeline)
oc apply -f manifests/rbac/service-account.yaml
oc apply -f manifests/rbac/role.yaml
oc apply -f manifests/rbac/role-binding.yaml

# Verify RBAC is correct
chmod +x manifests/rbac/verify-rbac.sh
./manifests/rbac/verify-rbac.sh
```

Expected output: All checks pass, no failures.

---

## Step 2: Build Container Images

Using OpenShift's built-in build system (no external registry required):

```bash
# Create ImageStream
oc create imagestream nodejs-zero-downtime -n zero-downtime-demo

# Create build configuration
oc new-build --name=nodejs-zero-downtime \
  --binary --strategy=docker \
  --to=nodejs-zero-downtime:latest \
  -n zero-downtime-demo

# Build image from app directory
oc start-build nodejs-zero-downtime \
  --from-dir=./app --follow \
  -n zero-downtime-demo
```

Wait for build to complete (takes ~2 minutes).

```bash
# Tag image for blue and green
oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:blue -n zero-downtime-demo

oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:green -n zero-downtime-demo

# Verify tags exist
oc get imagestream nodejs-zero-downtime -n zero-downtime-demo
```

Expected output: Shows `blue`, `green`, and `latest` tags.

---

## Step 3: Deploy Blue Baseline

```bash
# Apply blue deployment and service
oc apply -f manifests/blue/deployment.yaml
oc apply -f manifests/blue/service.yaml

# Wait for rollout
oc rollout status deployment/nodejs-blue -n zero-downtime-demo --timeout=120s
```

Expected output: `deployment "nodejs-blue" successfully rolled out`

```bash
# Verify blue pods are running
oc get pods -n zero-downtime-demo -l deployment-colour=blue
```

Expected: 2 pods in `Running` state.

---

## Step 4: Create HAProxy Route

```bash
# Apply route manifest (starts at 100% blue, 0% green)
oc apply -f manifests/route/haproxy-route.yaml

# Get route URL
ROUTE_URL=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo -o jsonpath='{.spec.host}')

echo "Route URL: https://${ROUTE_URL}"
```

---

## Step 5: Test Blue is Working

```bash
# Test version endpoint
curl -k https://${ROUTE_URL}/version

# Expected output:
# {"colour":"blue","version":"1.0.0","hostname":"nodejs-blue-...","timestamp":"..."}

# Test health endpoint
curl -k https://${ROUTE_URL}/health

# Expected output:
# {"status":"healthy","colour":"blue","version":"1.0.0","timestamp":"..."}
```

If you see `"colour":"blue"`, blue deployment is working! ✅

---

## Step 6: Deploy Green

```bash
# Apply green deployment and service
oc apply -f manifests/green/deployment.yaml
oc apply -f manifests/green/service.yaml

# Wait for rollout
oc rollout status deployment/nodejs-green -n zero-downtime-demo --timeout=120s
```

Expected output: `deployment "nodejs-green" successfully rolled out`

```bash
# Verify green pods are running
oc get pods -n zero-downtime-demo -l deployment-colour=green
```

Expected: 2 pods in `Running` state.

**Important**: Green is deployed but receives NO traffic yet. Route is still 100% blue.

---

## Step 7: Test Green Pods Directly

```bash
# Get a green pod name
POD=$(oc get pods -n zero-downtime-demo \
  -l deployment-colour=green \
  --field-selector=status.phase=Running \
  -o jsonpath='{.items[0].metadata.name}')

# Test health directly on pod (bypasses route)
oc exec ${POD} -n zero-downtime-demo -- \
  curl -s http://localhost:8080/health | jq '.'

# Expected output:
# {
#   "status": "healthy",
#   "colour": "green",
#   "version": "2.0.0",
#   "timestamp": "..."
# }
```

If you see `"colour":"green"` and `"version":"2.0.0"`, green is healthy! ✅

---

## Step 8: Gradual Traffic Shift

Now we'll shift traffic from blue to green in stages.

### Stage 1: 10% Canary

```bash
chmod +x scripts/shift-traffic.sh
./scripts/shift-traffic.sh 10
```

Expected output: `Route weights confirmed: Blue: 90% Green: 10%`

```bash
# Validate traffic distribution
chmod +x tests/traffic-validation.sh
./tests/traffic-validation.sh 50
```

Expected: ~90% blue responses, ~10% green responses.

**Observe for issues**: Check logs, metrics, error rates. In production, wait 5-15 minutes at this stage.

---

### Stage 2: 50% Split

```bash
./scripts/shift-traffic.sh 50
```

Expected output: `Route weights confirmed: Blue: 50% Green: 50%`

```bash
# Validate traffic distribution
./tests/traffic-validation.sh 50
```

Expected: ~50% blue responses, ~50% green responses.

---

### Stage 3: 100% Cutover

```bash
./scripts/shift-traffic.sh 100
```

Expected output: `Route weights confirmed: Blue: 0% Green: 100%`

```bash
# Validate all traffic on green
./tests/traffic-validation.sh 50
```

Expected: 100% green responses, 0% blue responses.

```bash
# Verify via route
curl -k https://${ROUTE_URL}/version
# Expected: {"colour":"green","version":"2.0.0",...}
```

**Green is now serving all production traffic!** ✅

---

## Step 9: Test Rollback

This is the critical safety feature — instant rollback to blue.

```bash
chmod +x scripts/rollback.sh
./scripts/rollback.sh --skip-flag-disable
```

Expected output: `ROLLBACK COMPLETE - All traffic is now on blue.`

```bash
# Verify rollback
./tests/traffic-validation.sh 20
```

Expected: 100% blue responses, 0% green responses.

```bash
# Verify via route
curl -k https://${ROUTE_URL}/version
# Expected: {"colour":"blue","version":"1.0.0",...}
```

**Rollback complete in under 30 seconds!** ✅

---

## Step 10: Check Both Deployments

```bash
# Both blue AND green should still be running
oc get deployments -n zero-downtime-demo -l app=nodejs-zero-downtime
```

Expected output:
```
NAME           READY   UP-TO-DATE   AVAILABLE   AGE
nodejs-blue    2/2     2            2           15m
nodejs-green   2/2     2            2           10m
```

**This is the key safety feature**: Both deployments stay running so you can rollback instantly without waiting for pods to start.

---

## Verification Checklist

✅ Blue deployment running (2/2 replicas)  
✅ Green deployment running (2/2 replicas)  
✅ Route created and accessible  
✅ Traffic shifting works: 10% → 50% → 100%  
✅ Traffic distribution matches configured weights  
✅ Rollback to blue works in < 30 seconds  
✅ Both deployments stay running after cutover  
✅ Zero errors during traffic shifts  

---

## What You Just Built

You now have a production-ready zero-downtime deployment system that:

- **Deploys new versions with zero downtime**
- **Gradually shifts traffic through canary stages**
- **Can rollback instantly** (< 30 seconds, no pod startup wait)
- **Works on ROSA HCP out-of-the-box** (no additional infrastructure)
- **Uses built-in HAProxy route weights** (no Istio, no Ingress NGINX needed)

---

## Next Steps

### For Production Use

1. **Set up external registry**: See [Prerequisites](docs/prerequisites.md) Section 2 Option B
2. **Deploy Flagsmith**: See [Flagsmith Setup](docs/flagsmith-setup.md) for deployment gate
3. **Configure GitHub Actions**: See [Prerequisites](docs/prerequisites.md) Section 4
4. **Add monitoring**: Integrate Prometheus queries between traffic stages
5. **Add image scanning**: Use Trivy or Clair in pipeline

### Learn More

- **[Architecture](docs/architecture.md)** — Why these design decisions?
- **[Rollback Runbook](docs/rollback-runbook.md)** — 2am emergency procedures
- **[Prerequisites Full Guide](docs/prerequisites.md)** — Complete production setup

### Clean Up (Optional)

```bash
# Delete everything
oc delete namespace zero-downtime-demo

# Or delete just the deployments but keep namespace
oc delete deployment,service,route,imagestream --all -n zero-downtime-demo
```

---

## Troubleshooting

### ImagePullBackOff on pods

```bash
# Check imagestream exists
oc get imagestream nodejs-zero-downtime -n zero-downtime-demo

# Check image tags
oc describe imagestream nodejs-zero-downtime -n zero-downtime-demo

# Force deployment to use correct image
oc set image deployment/nodejs-blue \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:blue \
  -n zero-downtime-demo
```

### Route returns 503 errors

```bash
# Check services have endpoints
oc get endpoints nodejs-blue nodejs-green -n zero-downtime-demo

# Check pods are ready
oc get pods -n zero-downtime-demo -l app=nodejs-zero-downtime

# Check route configuration
oc describe route nodejs-zero-downtime -n zero-downtime-demo
```

### Traffic not splitting correctly

```bash
# Check route weights
oc get route nodejs-zero-downtime -n zero-downtime-demo -o yaml | grep weight

# Re-apply weight change
./scripts/shift-traffic.sh <desired-percentage>
```

---

**Questions?** Check the [main README](README.md) or open an issue.
