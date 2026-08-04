# mcp-for-kubernetes

> **Status:** Full walkthrough

Companion repository for **AI in the Stack #03 — MCP Server Architecture for Platform Teams**.

> Read the article: https://pipelineandprompts.com/posts/mcp-server-architecture-platform-engineering-kubernetes/

## Transport note (read before wiring to lab 06)

This lab serves **HTTP+SSE** (`/sse`) — the transport many desktop MCP clients (Cursor, Claude Desktop) still use for remote servers.

Lab 06's n8n demo speaks **Streamable HTTP** (`/mcp`) via a separate canned `demo-mcp-server`. Do **not** point the lab 06 workflow at this SSE server without changing the n8n credential connection type to SSE (and the URL to `/sse`), or upgrading this server to Streamable HTTP.

| Lab | Transport | Typical client |
|---|---|---|
| 03 (this repo) | SSE (`/sse`) | Cursor / Claude Desktop / kubectl-side agents |
| 06 demo MCP | Streamable HTTP (`/mcp`) | n8n `n8n-nodes-mcp` |

## What's in this repo

| Directory | Contents |
|---|---|
| `src/` | Python MCP server source |
| `k8s/` | Kubernetes/OpenShift manifests |
| `helm/platform-mcp/` | Helm chart for deployment |
| `.github/workflows/` | Build, push, and lint pipelines |

## Quick start

### Local (HTTP/SSE)

```bash
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/ai-in-the-stack/03-mcp-for-kubernetes

pip install -r requirements.txt
export MCP_API_KEY=your-local-dev-key
cd src && python main.py
```

Clients connect to `http://localhost:8080/sse` with header `X-API-Key: your-local-dev-key`.
Optional: send `X-Session-Id` so rate limiting and audit logs are per-client instead of a shared bucket.

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

See [OPEN_ITEMS.md](./OPEN_ITEMS.md) for the checklist from the article review.

## Security

- All Kubernetes tools are read-only by RBAC design
- API key authentication on all endpoints (except `/health`)
- Audit log emitted for every tool call (includes `X-Session-Id` when provided)
- NetworkPolicy restricts egress to API server and monitoring namespace

## Extensions (coming in this repo)

- [ ] Prometheus / PromQL tool handler
- [ ] PagerDuty active incidents tool
- [ ] Write operations with human approval gate
- [ ] Redis-backed rate limiter for multi-replica deployments
- [ ] Streamable HTTP transport option alongside SSE
