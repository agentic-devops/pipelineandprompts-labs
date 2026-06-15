# Zero-Downtime Blue/Green Deployments on OpenShift

Production-ready blue/green deployment system for ROSA HCP (Red Hat OpenShift Service on AWS) with gradual traffic shifting, instant rollback, and human-controlled deployment gates.

## What This Is

A complete implementation of zero-downtime deployments using OpenShift HAProxy Routes with weight-based traffic splitting. Deploy new application versions through controlled canary stages (10% → 50% → 100%) with the ability to rollback to the previous version in under 30 seconds.

**Key Features:**
- ✅ **Zero downtime** — HAProxy shifts traffic in-flight with no pod restarts
- ✅ **Gradual rollout** — 10% → 50% → 100% canary progression with observation windows
- ✅ **Instant rollback** — Both blue and green stay running for sub-30s rollback
- ✅ **Human-controlled gates** — Optional Flagsmith integration for deployment approval
- ✅ **No additional infrastructure** — Uses built-in OpenShift router, works OOTB on ROSA HCP
- ✅ **Complete automation** — GitHub Actions pipeline handles entire deployment flow

## Verified Working

This system has been tested and verified on ROSA HCP with:
- OpenShift 4.21.9
- Kubernetes 1.34.6
- Internal OpenShift image registry
- HAProxy route weight splitting
- Zero errors during traffic shifts

## Quick Start

### Prerequisites

- ROSA HCP cluster (OpenShift 4.14+)
- `oc` CLI installed and logged in
- `podman` or `docker` for building images (optional - can build on cluster)
- GitHub account (for CI/CD pipeline)

### 1. Clone and Deploy

```bash
# Create namespace
oc apply -f manifests/namespace/namespace.yaml

# Apply RBAC
oc apply -f manifests/rbac/service-account.yaml
oc apply -f manifests/rbac/role.yaml
oc apply -f manifests/rbac/role-binding.yaml

# Build application images on cluster
oc new-build --name=nodejs-zero-downtime \
  --binary --strategy=docker \
  --to=nodejs-zero-downtime:latest \
  -n zero-downtime-demo

oc start-build nodejs-zero-downtime \
  --from-dir=./app --follow \
  -n zero-downtime-demo

# Tag images for blue and green
oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:blue -n zero-downtime-demo
oc tag zero-downtime-demo/nodejs-zero-downtime:latest \
  zero-downtime-demo/nodejs-zero-downtime:green -n zero-downtime-demo
```

### 2. Deploy Blue Baseline

```bash
# Deploy blue deployment and service
oc apply -f manifests/blue/deployment.yaml
oc apply -f manifests/blue/service.yaml

# Update to use internal registry
oc set image deployment/nodejs-blue \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:blue \
  -n zero-downtime-demo

# Wait for rollout
oc rollout status deployment/nodejs-blue -n zero-downtime-demo

# Create HAProxy route (starts at 100% blue)
oc apply -f manifests/route/haproxy-route.yaml
```

### 3. Test Blue is Working

```bash
ROUTE_URL=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo -o jsonpath='{.spec.host}')

curl -k https://${ROUTE_URL}/version
# Expected: {"colour":"blue","version":"1.0.0",...}
```

### 4. Deploy Green

```bash
# Deploy green deployment and service
oc apply -f manifests/green/deployment.yaml
oc apply -f manifests/green/service.yaml

# Update to use internal registry
oc set image deployment/nodejs-green \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:green \
  -n zero-downtime-demo

# Wait for rollout
oc rollout status deployment/nodejs-green -n zero-downtime-demo
```

### 5. Test Traffic Shifting

```bash
# Stage 1: 10% canary
./scripts/shift-traffic.sh 10
./tests/traffic-validation.sh 50

# Stage 2: 50% split
./scripts/shift-traffic.sh 50
./tests/traffic-validation.sh 50

# Stage 3: 100% cutover
./scripts/shift-traffic.sh 100
./tests/traffic-validation.sh 50

# Rollback to blue
./scripts/rollback.sh --skip-flag-disable
```

## Documentation

- **[Architecture](docs/architecture.md)** — Design decisions, blast radius analysis, alternatives considered
- **[Prerequisites](docs/prerequisites.md)** — Complete setup guide for first-time deployment
- **[Rollback Runbook](docs/rollback-runbook.md)** — 2am-friendly emergency rollback procedures
- **[Flagsmith Setup](docs/flagsmith-setup.md)** — Optional deployment gate configuration

## Repository Structure

```
.
├── app/                          # Node.js application
│   ├── Dockerfile               # Container build definition
│   ├── server.js                # Simple Express app
│   └── build-and-push.sh        # Image build script
├── manifests/
│   ├── namespace/               # Namespace definition
│   ├── rbac/                    # Service account and permissions
│   ├── blue/                    # Blue deployment + service
│   ├── green/                   # Green deployment + service
│   └── route/                   # HAProxy route with weight splitting
├── scripts/
│   ├── shift-traffic.sh         # Traffic shifting script (used by pipeline)
│   ├── rollback.sh              # Emergency rollback script
│   ├── verify-deployment.sh     # Health check verification
│   └── smoke-test.sh            # Endpoint validation
├── tests/
│   └── traffic-validation.sh    # Manual traffic distribution testing
├── examples/                     # Example route manifests for each stage
│   ├── 01-canary-10-percent/   # 10% green / 90% blue
│   ├── 02-canary-50-percent/   # 50% green / 50% blue
│   ├── 03-full-cutover/        # 100% green / 0% blue
│   └── 04-rollback/            # Emergency rollback to 100% blue
├── .github/workflows/
│   ├── blue-green-deploy.yml   # Main deployment pipeline
│   ├── rollback.yml            # Emergency rollback workflow
│   └── validate-manifests.yml  # Pre-deployment validation
└── docs/                        # Detailed documentation
```

## GitHub Actions Pipeline

The automated pipeline handles:

1. **Validation** — Dry-run manifests, verify RBAC
2. **Deploy Green** — Deploy new version with zero traffic
3. **Health Check** — Verify green pods are healthy
4. **Flagsmith Gate** — Check deployment approval flag (optional)
5. **Gradual Shift** — 10% → 50% → 100% with observation windows
6. **Verification** — Health checks between each stage

See [Prerequisites](docs/prerequisites.md) for GitHub Actions setup.

## Traffic Shifting Mechanics

HAProxy Route weights control traffic distribution:

```yaml
spec:
  to:
    kind: Service
    name: nodejs-blue
    weight: 90              # Blue gets 90% of traffic
  alternateBackends:
    - kind: Service
      name: nodejs-green
      weight: 10            # Green gets 10% of traffic
```

Weight changes apply **in-flight** — no DNS propagation, no pod restarts, no load balancer reprovisioning.

## Rollback Strategy

**Critical design decision**: Blue is never deleted after green takes 100% traffic.

**Why?**
- Rollback from 100% green → 100% blue takes under 30 seconds
- No pod startup time — blue is already running
- Issues may surface minutes/hours after cutover under full load
- Cost of running idle blue << cost of emergency redeployment

**How to rollback:**

```bash
# Option 1: Script (fastest)
./scripts/rollback.sh

# Option 2: Direct manifest
oc apply -f examples/04-rollback/haproxy-route-rollback.yaml

# Option 3: GitHub Actions workflow
# Actions → Rollback workflow → Run (requires reason for audit)

# Option 4: Direct oc patch
oc patch route nodejs-zero-downtime -n zero-downtime-demo \
  --type=json --patch='[
    {"op":"replace","path":"/spec/to/weight","value":100},
    {"op":"replace","path":"/spec/alternateBackends/0/weight","value":0}
  ]'
```

## Production Considerations

### Using External Registry (quay.io, Docker Hub, etc.)

For production, use an external registry instead of the internal OpenShift registry:

1. Build and push images:
   ```bash
   cd app
   # Edit build-and-push.sh with your registry
   ./build-and-push.sh
   ```

2. Update manifests to reference your registry:
   ```yaml
   image: quay.io/your-org/nodejs-zero-downtime:blue
   ```

See [Prerequisites](docs/prerequisites.md) Section 2 for detailed registry setup.

### Adding Flagsmith Deployment Gate

Deploy Flagsmith for human-controlled deployment gates:

```bash
# See flagsmith/README.md for deployment
oc apply -f flagsmith/postgres/
oc apply -f flagsmith/deployment/
```

Then add Flagsmith secrets to GitHub Actions. See [Flagsmith Setup](docs/flagsmith-setup.md).

### Monitoring Integration

Add observability checks between traffic stages:

- Query Prometheus for error rate thresholds
- Check application metrics before proceeding
- Integrate with PagerDuty/DataDog/Dynatrace

Example in `.github/workflows/blue-green-deploy.yml`:
```yaml
- name: Check error rate at 10%
  run: |
    # Query your metrics platform
    # Abort if error rate > threshold
```

## Testing

```bash
# Manual traffic distribution test
./tests/traffic-validation.sh 100

# Verify deployment health
./scripts/verify-deployment.sh blue
./scripts/verify-deployment.sh green

# Smoke test against live route
export ROUTE_URL=$(oc get route nodejs-zero-downtime -n zero-downtime-demo -o jsonpath='{.spec.host}')
./scripts/smoke-test.sh blue
```

## Troubleshooting

### ImagePullBackOff errors

If pods show `ImagePullBackOff`:

```bash
# Check image exists in registry
oc get imagestream nodejs-zero-downtime -n zero-downtime-demo

# Verify image tags
oc get is nodejs-zero-downtime -n zero-downtime-demo -o yaml

# Update deployment to use correct image
oc set image deployment/nodejs-blue \
  nodejs=image-registry.openshift-image-registry.svc:5000/zero-downtime-demo/nodejs-zero-downtime:blue \
  -n zero-downtime-demo
```

### Route not distributing traffic

```bash
# Check route configuration
oc get route nodejs-zero-downtime -n zero-downtime-demo -o yaml

# Verify both services exist
oc get svc nodejs-blue nodejs-green -n zero-downtime-demo

# Check service endpoints
oc get endpoints nodejs-blue nodejs-green -n zero-downtime-demo
```

### Pipeline fails at Flagsmith gate

```bash
# Skip Flagsmith check for testing
./scripts/shift-traffic.sh 10  # Manual shifting
./scripts/rollback.sh --skip-flag-disable  # Skip flag disable
```

## Contributing

This is a reference implementation. Adapt to your needs:

- Add multi-region support
- Integrate with Argo CD / Flux
- Add automated rollback on error threshold
- Implement progressive delivery with feature flags

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Review [Architecture](docs/architecture.md) for design decisions
- Check [Rollback Runbook](docs/rollback-runbook.md) for emergency procedures
- Open an issue on GitHub
