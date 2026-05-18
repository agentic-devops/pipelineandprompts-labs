# Architecture — Zero-Downtime Blue/Green Deployments

## Design Goal

Deploy new application versions to production on ROSA HCP with zero
downtime, a human-controlled traffic gate, and an instant rollback
path that does not require a new deployment.

## Core Design Decisions

### Why HAProxy Route weight splitting over other approaches

Several approaches exist for gradual traffic shifting on OpenShift.
This implementation uses HAProxy Route weight splitting because:

- It requires no additional infrastructure — the OpenShift router
  is already present on every cluster
- It works on ROSA HCP without any router-level configuration
  access — all control is via Route annotations and spec
- Weight changes apply in-flight — no pod restarts, no DNS TTL
  wait, no load balancer reprovisioning
- It is reversible in seconds — a single `oc patch` command
  shifts all traffic back to blue

Alternatives considered and why they were not chosen:

**Ingress NGINX canary annotations**
Not available on OpenShift by default. Requires installing a
separate Ingress controller alongside the OpenShift router.
Additional operational complexity for no gain on OpenShift.

**Service Mesh (Istio/OpenShift Service Mesh)**
More precise traffic control but significant operational overhead.
Requires sidecar injection, mTLS configuration, and VirtualService
resources. Appropriate for microservices environments with many
services — disproportionate for a single-service deployment pattern.

**DNS-based switching**
Long TTL propagation means traffic shift is not instant.
Rollback requires waiting for DNS to propagate. Not suitable for
zero-downtime requirements.

### Why Flagsmith as the deployment gate

The pipeline does not shift traffic automatically after green
is deployed and health-checked. It checks a Flagsmith feature
flag first.

This design decision exists because:

- A passing smoke test does not mean the deployment is safe to
  promote — a human or automated monitor may have additional
  context the pipeline cannot see
- The flag can be disabled at any point to halt the pipeline
  before a traffic shift, without cancelling the GitHub Actions
  run itself
- Every flag change in Flagsmith is logged with user, timestamp,
  and environment — this is your deployment audit trail
- In regulated environments, a deployment gate with an audit log
  satisfies change management requirements that a CI/CD pipeline
  alone cannot

### Why blue stays running after full cutover

Blue is never deleted immediately after green takes 100% traffic.

This is the most important operational safety decision in this
architecture. The reasons:

- Rollback from 100% green to 100% blue takes under 30 seconds
  with no pod startup time required — blue is already running
- Issues that only surface under full production load may not
  appear until minutes or hours after cutover
- The cost of running an idle blue deployment is negligible
  compared to the cost of a deployment that requires rebuilding
  from scratch to rollback

Blue is replaced at the next deployment cycle when a new green
version is validated and promoted.

---

## Control Plane and Data Plane

**Control plane**
- GitHub Actions — orchestrates the pipeline steps
- Flagsmith — holds deployment gate state
- `oc` CLI — applies manifest changes to the cluster
- RBAC — bounds what the pipeline can touch

**Data plane**
- HAProxy Router — distributes live traffic between blue and green
- Blue Deployment — current stable version, baseline traffic
- Green Deployment — new version, receives traffic after validation
- ClusterIP Services — stable endpoints for each deployment
- Internal Image Registry — stores container images (or external registry for production)

**Trust boundary**
The pipeline service account (`pipeline-deployer`) can patch
Routes and Deployments in `zero-downtime-demo` only. It cannot
read Secrets, modify cluster-scoped resources, or touch other
namespaces. This bounds the blast radius of a compromised
pipeline token to the demo namespace.

---

## Blast Radius Analysis

**If the pipeline misbehaves:**
- Worst case: 100% traffic shifted to green prematurely
- Mitigation: `scripts/rollback.sh` restores blue in under 30s
- Second mitigation: Flagsmith gate — disabling the flag stops
  any further traffic shifts immediately

**If the Flagsmith deployment fails:**
- Pipeline aborts at the gate check step
- No traffic is shifted
- Blue continues serving 100% of traffic
- Green is deployed but receives no traffic

**If the GitHub Actions runner loses connectivity mid-shift:**
- HAProxy Route retains whatever weight was last applied
- Traffic does not automatically revert
- Manual rollback required:
  `oc apply -f examples/04-rollback/haproxy-route-rollback.yaml`

**If green pods crash after receiving traffic:**
- HAProxy stops routing to green pods that fail health checks
- Weight setting remains but unhealthy pods are bypassed
- Manual rollback still recommended to explicitly set weights
- Blue pods absorb the traffic HAProxy was sending to green

---

## Sequence Diagram
