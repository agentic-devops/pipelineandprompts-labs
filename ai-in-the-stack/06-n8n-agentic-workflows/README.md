# n8n Agentic Workflows — Incident Triage Demo

Companion repo for **AI in the Stack #6: Building n8n Workflows for Platform Engineering Automation**.

This repo lets you run the full incident-triage workflow from the article on your own machine — webhook trigger → parallel RAG + MCP lookups → LLM analysis → conditional Slack notification — using lightweight mock services, so you don't need a live OpenShift cluster or GCP project just to see the shape of the thing work.

Once the demo runs end-to-end, swap the mock RAG and MCP services for the real ones (Article 02's RAG pipeline and [openshift-mcp-sre-tools](https://github.com/nedoshi/openshift-mcp-sre-tools)) and point the LLM node at Vertex AI, exactly as described in the article.

## What's in here

```
n8n-agentic-workflows/
├── workflows/
│   └── incident-triage.json      # importable n8n workflow
├── mock-services/
│   ├── mock-rag-service/         # stands in for Article 02's RAG pipeline
│   └── mock-mcp-server/          # stands in for openshift-mcp-sre-tools, real MCP-over-SSE
├── samples/
│   ├── sample-alert.json         # Alertmanager-shaped payload
│   └── trigger-workflow.sh       # curl script to fire the webhook
├── config/
│   ├── alertmanager.yml.example  # production webhook_configs block (untested against live Alertmanager)
│   └── error-workflow.json       # minimal n8n error workflow (posts to Slack on failure)
├── docker-compose.yml            # n8n + both mock services
└── .env.example
```

## Prerequisites

- Docker and Docker Compose
- An n8n instance — the `docker-compose.yml` here spins one up for you, so a separate install isn't required
- A Slack workspace with an incoming webhook or bot token (for the final notification step)
- Optional, for the real (non-mock) path: a GCP project with Vertex AI enabled, and access to a real OpenShift/ROSA/ARO cluster running `openshift-mcp-sre-tools`

## Quickstart (mock services, ~10 minutes)

1. **Clone and configure**

   ```bash
   git clone https://github.com/pipelineandprompts-labs/n8n-agentic-workflows.git
   cd n8n-agentic-workflows
   cp .env.example .env
   ```

   Edit `.env` and set at minimum `SLACK_WEBHOOK_URL` (or bot token — see below). Everything else has a working default for the mock path.

2. **Start everything**

   ```bash
   docker compose up -d
   ```

   This brings up three containers:
   - `n8n` — the workflow engine, at `http://localhost:5678`
   - `mock-rag-service` — a canned runbook-answer API at `http://mock-rag-service:8080/query`
   - `mock-mcp-server` — a real MCP server over SSE at `http://mock-mcp-server:8080/sse`, returning canned cluster diagnostics

3. **Import the workflow**

   Open `http://localhost:5678`, create your owner account on first run, then go to **Workflows → Import from File** and select `workflows/incident-triage.json`.

4. **Add credentials**

   The imported workflow references two credentials you'll need to create in n8n's **Credentials** panel:
   - **Slack** — incoming webhook or bot token, used by the `Slack Post` and `Slack Light Notify` nodes
   - **Vertex AI (Google Cloud)** — used by the `Analyze (Vertex AI)` node. For the mock quickstart you can swap this node's credential for any chat model you already have configured in n8n (OpenAI, Anthropic, Ollama) — the node just needs *a* model to reason over the merged RAG + MCP output. See "Swapping the LLM provider" below.

   Open each node showing a red exclamation mark and select or create the credential.

5. **Trigger it**

   ```bash
   ./samples/trigger-workflow.sh
   ```

   This POSTs `samples/sample-alert.json` to the webhook. Watch the execution in n8n's UI — you'll see the RAG and MCP branches fire in parallel, merge into the analysis step, hit the conditional, and post to Slack.

6. **Check Slack.** You should see a message combining the mock runbook guidance with the mock cluster diagnostics — the same payoff described in the article, just with canned data standing in for a live cluster.

## Swapping in the real services

Once the mock path works, replace pieces one at a time:

| Mock component | Real replacement | Where it's covered |
|---|---|---|
| `mock-rag-service` | Article 02's RAG runbook pipeline | AI in the Stack #2 |
| `mock-mcp-server` | [openshift-mcp-sre-tools](https://github.com/nedoshi/openshift-mcp-sre-tools) against a real ARO/ROSA/OSD cluster | AI in the Stack #3 |
| Chat model credential | Vertex AI via GCP service account | This article, Step 2 |
| Manual `curl` trigger | Alertmanager webhook (see `config/alertmanager.yml.example`) | This article, Step 3 — **note: this block was not tested against a live Alertmanager** |

Update the **MCP Client** node's URL from `http://mock-mcp-server:8080/sse` to your real MCP server's address, and the **RAG Query** HTTP Request node's URL from `http://mock-rag-service:8080/query` to your real RAG service.

### Swapping the LLM provider

The `Analyze (Vertex AI)` node is a standard n8n AI chat model node. To use a different provider for local testing, delete it and drag in whichever chat model node matches credentials you already have (OpenAI, Anthropic, Ollama) — the rest of the workflow doesn't care which model produced the analysis, only that the node returns text. This mirrors the provider-abstraction pattern from Article 05.

## Execution limits (do this before your first real test run)

The article's central warning: an LLM agent node makes execution non-deterministic. This workflow ships with the guardrails already configured, but verify them after import:

1. **Workflow Settings → Timeout** — set to 5 minutes to start.
2. **HTTP Request nodes → Retry on Fail** — enabled, Max Tries: 3, Wait Between Tries: 2000ms. Already set on `RAG Query` in the imported JSON; confirm it survived the import.
3. **Workflow Settings → Error Workflow** — import `config/error-workflow.json` first, then select it as the Error Workflow for `incident-triage`. It posts failures to a `#automation-errors` Slack channel (configure the channel in its Slack node).

Do not point this workflow at a production Alertmanager until all three are confirmed.

## Security notes (read before pointing this at a real cluster)

- Keep the real MCP server **read-only**. `openshift-mcp-sre-tools` defaults to read-only diagnostic tools — don't add write capability without approval gates and rollback, per the article's guidance.
- Protect GCP credentials stored in n8n with a NetworkPolicy restricting access to the n8n UI/API if running on-cluster.
- If exposing the webhook to a real Alertmanager, terminate TLS on the OpenShift Route and enable Alertmanager's basic auth on the webhook config — don't leave the endpoint open to arbitrary POSTs.

Full detail on all of the above is in the article itself.

## Troubleshooting

- **Nodes show a red exclamation mark on import** — credentials don't transfer between n8n instances. Recreate them per step 4 above.
- **MCP Client node can't connect** — confirm `mock-mcp-server` is healthy: `docker compose logs mock-mcp-server`. The SSE endpoint is `http://mock-mcp-server:8080/sse` from inside the Docker network, not `localhost`.
- **Slack node fails** — double check `SLACK_WEBHOOK_URL` in `.env` and that `docker compose up -d` was re-run after editing it (`docker compose up -d --force-recreate n8n`).
- **Workflow runs but never posts to Slack** — check the IF node's condition; the mock MCP server's canned "no failing pods" response may be routing you down the light-notify branch. Edit `mock-services/mock-mcp-server/server.py` to return a failing pod if you want to force the full-alert branch.

## License

MIT — see `LICENSE`.
