# Open Items — AI in the Stack #03

Unresolved items from the Stage 5 article review. Resolve before publishing.

## Blocking

- [ ] **Health endpoint** — `/health` is now implemented in `src/main.py`.
      Confirm it returns HTTP 200 before building the container image.

## Validate before publishing

- [ ] MCP Python SDK package name and version: confirm `mcp>=1.0.0` is
      available on PyPI and that `SseServerTransport` / `connect_sse` match
      the installed version interface.

- [ ] `session_id` propagation: replace `"default"` in `src/tools.py` with
      real session identity from your request context.

- [ ] OpenShift SCC version: if using `restricted` SCC (pre-4.11), remove
      `seccompProfile` from `k8s/deployment.yaml` and
      `helm/platform-mcp/templates/deployment.yaml`.

- [ ] `list_pod_for_all_namespaces` performance: add caching or namespace
      scoping if running on clusters with hundreds of namespaces.

- [ ] Replace `your-registry/platform-mcp:latest` with your actual registry
      path and pin to a digest or semver tag.

- [ ] Confirm `https://github.com/pipelineandprompts-labs/mcp-for-kubernetes`
      is the correct repo slug before publishing the article.

## Unverified

- [ ] NetworkPolicy egress ports: confirm Kubernetes/OpenShift API server port
      for your cluster (443, 6443, or 8443). Update `k8s/networkpolicy.yaml`
      and `helm/platform-mcp/values.yaml`.

- [ ] `SseServerTransport` class name and `/messages` path argument: verify
      against installed SDK version with a local `python main.py` run.
