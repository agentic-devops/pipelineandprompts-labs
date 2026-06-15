# mcp-for-kubernetes

Companion repository for **AI in the Stack #03 — MCP Server Architecture for Platform Teams**.

> Read the article: https://pipelineandprompts.dev  <!-- AUTHOR: update URL -->

## What's in this repo

| Directory | Contents |
|---|---|
| `src/` | Python MCP server source |
| `k8s/` | Kubernetes/OpenShift manifests |
| `helm/platform-mcp/` | Helm chart for deployment |
| `.github/workflows/` | Build, push, and lint pipelines |

## Quick start

### Local (stdio transport)

```bash
pip install -r requirements.txt
export MCP_API_KEY=your-local-dev-key
cd src && python main.py
```

### Cluster deployment

```bash
# 1. Create namespace and RBAC
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/rbac.yaml

# 2. Create secret (replace value)
kubectl create secret generic platform-mcp-secrets \
  --from-literal=api-key=YOUR_KEY \
  -n platform-tools

# 3. Deploy
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/networkpolicy.yaml
kubectl apply -f k8s/poddisruptionbudget.yaml

# 4. OpenShift: expose via Route
oc apply -f k8s/route.yaml

# 5. Kubernetes: expose via Ingress (edit host first)
# kubectl apply -f k8s/ingress.yaml
```

### Helm

```bash
helm install platform-mcp helm/platform-mcp \
  --namespace platform-tools \
  --create-namespace
```

## Open items before production use

See `OPEN_ITEMS.md` for the full checklist from the article review.

## Security

- All Kubernetes tools are read-only by RBAC design
- API key authentication on all endpoints
- Audit log emitted for every tool call
- NetworkPolicy restricts egress to API server and monitoring namespace

## Extensions (coming in this repo)

- [ ] Prometheus / PromQL tool handler
- [ ] PagerDuty active incidents tool
- [ ] Write operations with human approval gate (Article 05 pattern)
- [ ] Redis-backed rate limiter for multi-replica deployments
