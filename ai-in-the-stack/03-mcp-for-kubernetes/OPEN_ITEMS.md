# Open items — platform MCP server

Checklist before running this near production. Treat every unchecked item as a known gap, not a surprise.

## Must fix

- [ ] Pin image digests in Helm/`k8s/deployment.yaml` (no floating `:latest` / `:local` in prod)
- [ ] Confirm API server port in NetworkPolicy (default `6443` — verify for your cluster)
- [ ] Replace placeholder registry / ingress host values under `helm/platform-mcp/values.yaml`
- [ ] Store `MCP_API_KEY` in a real secret manager; rotate on a schedule
- [ ] Wire `X-Session-Id` (or equivalent) from your MCP client so audit + rate limits are per session

## Should fix

- [ ] Add field/label selectors on cluster-wide `list_failing_pods` for large clusters
- [ ] Ship Redis (or similar) rate limiting if you run >1 replica
- [ ] Decide SSE vs Streamable HTTP for your clients (see README transport note)
- [ ] Alert on audit-log volume / denied tool calls

## Nice to have

- [ ] Prometheus / PromQL tools
- [ ] PagerDuty active-incident tools
- [ ] Write operations behind an explicit human-approval gate
