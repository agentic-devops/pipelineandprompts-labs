# n8n Agentic Workflows — Incident Triage Demo

Companion repo for **AI in the Stack #6: Building n8n Workflows for Platform Engineering Automation**.

This repo lets you run the full incident-triage workflow from the article on your own machine — webhook trigger → parallel RAG + MCP lookups → LLM analysis → conditional Slack notification — using lightweight demo services, so you don't need a live OpenShift cluster or GCP project just to see the shape of the thing work.

Once the demo runs end-to-end, swap the demo RAG and MCP services for the real ones (Article 02's RAG pipeline and [openshift-mcp-sre-tools](https://github.com/nedoshi/openshift-mcp-sre-tools)) and point the LLM node at Vertex AI, exactly as described in the article.

## What's in here

```
06-n8n-agentic-workflows/
├── workflows/
│   └── incident-triage.json      # importable n8n workflow
├── demo-services/
│   ├── demo-rag-service/         # stands in for Article 02's RAG pipeline
│   └── demo-mcp-server/          # stands in for openshift-mcp-sre-tools, real MCP over Streamable HTTP
├── samples/
│   ├── sample-alert.json         # Alertmanager-shaped payload
│   └── trigger-workflow.sh       # curl script to fire the webhook
├── config/
│   ├── alertmanager.yml.example  # production webhook_configs block (untested against live Alertmanager)
│   └── error-workflow.json       # minimal n8n error workflow (posts to Slack on failure)
├── docker-compose.yml            # n8n + both demo services
└── .env.example
```

## Prerequisites

- Docker and Docker Compose
- An n8n instance — the `docker-compose.yml` here spins one up for you, so a separate install isn't required
- A Slack workspace with an incoming webhook or bot token (for the final notification step)
- Optional, for the real (non-demo) path: a GCP project with Vertex AI enabled, and access to a real OpenShift/ROSA/ARO cluster running `openshift-mcp-sre-tools`

**Important:** this workflow's MCP nodes use the community package **[n8n-nodes-mcp](https://www.npmjs.com/package/n8n-nodes-mcp)**, not n8n's built-in MCP Client Tool node. The built-in node only works as a sub-node attached to an AI Agent's tool input — it can't be wired into a Merge step the way this workflow needs, because this workflow calls MCP tools deterministically rather than letting an agent decide when to call them. You'll install the community package as part of the quickstart below (step 3).

## Quickstart (demo services, ~10 minutes)

1. **Clone and configure**

   This lives inside the `pipelineandprompts-labs` monorepo, not as its own repo — clone the whole thing, then work from this subfolder:

   ```bash
   git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
   cd pipelineandprompts-labs/ai-in-the-stack/06-n8n-agentic-workflows
   cp .env.example .env
   ```

   Edit `.env` and set at minimum `SLACK_WEBHOOK_URL` (or bot token — see below). Everything else has a working default for the demo path.

2. **Start everything**

   ```bash
   docker compose up -d
   ```

   This brings up three containers:
   - `n8n` — the workflow engine, at `http://localhost:5678`
   - `demo-rag-service` — a canned runbook-answer API at `http://demo-rag-service:8080/query`
   - `demo-mcp-server` — a real MCP server over Streamable HTTP at `http://demo-mcp-server:8080/mcp`, returning canned cluster diagnostics

3. **Install the MCP community node**

   Open `http://localhost:5678`, create your owner account on first run, then go to **Settings → Community Nodes → Install**, and enter package name `n8n-nodes-mcp`. Confirm the risk warning and install. This is a one-time step per n8n instance — it persists in the `n8n_data` volume.

4. **Create the MCP Streamable HTTP credential**

   In n8n's **Credentials** panel, create a new credential of type **MCP Client (Streamable HTTP) API** (added by the package you just installed — the credential form also offers an SSE option, but Streamable HTTP is what this demo server speaks). Set:
   - **HTTP Streamable URL:** `http://demo-mcp-server:8080/mcp`

   Name it something you'll recognize (the imported workflow expects a credential named `Demo MCP Server (Streamable HTTP)`, but you can rename the reference after import if you use a different name).

   *Why Streamable HTTP and not SSE:* the MCP spec deprecated the HTTP+SSE transport in its 2025-03-26 revision in favor of Streamable HTTP, and client support for SSE has been narrowing since. `demo-mcp-server` in this repo only serves Streamable HTTP (`mcp.run(transport="streamable-http")`) — if you're pointing this workflow at an older MCP server that only speaks SSE, select the SSE option in the credential instead and use its `/sse` path.

5. **Import the workflow**

   Go to **Workflows → Import from File** and select `workflows/incident-triage.json`.

6. **Add credentials**

   The imported workflow references three credentials you'll need to create or select in n8n's **Credentials** panel:
   - **MCP Client (Streamable HTTP) API** — the one you just created in step 4, selected on both `MCP Get Failing Pods` and `MCP Get Events`
   - **Slack** — incoming webhook or bot token, used by the `Slack Post` and `Slack Light Notify` nodes
   - **Vertex AI (Google Cloud)** — used by the `Analyze (Vertex AI)` node. For the demo quickstart you can swap this node's credential for any chat model you already have configured in n8n (OpenAI, Anthropic, Ollama) — the node just needs *a* model to reason over the merged RAG + MCP output. See "Swapping the LLM provider" below.

   Open each node showing a red exclamation mark and select or create the credential.

7. **Trigger it**

   ```bash
   ./samples/trigger-workflow.sh
   ```

   This POSTs `samples/sample-alert.json` to the webhook. Watch the execution in n8n's UI — you'll see the RAG and MCP branches fire in parallel, merge into the analysis step, hit the conditional, and post to Slack.

8. **Check Slack.** You should see a message combining the demo runbook guidance with the demo cluster diagnostics — the same payoff described in the article, just with canned data standing in for a live cluster.

## Swapping in the real services

Once the demo path works, replace pieces one at a time:

| Demo component | Real replacement | Where it's covered |
|---|---|---|
| `demo-rag-service` | Article 02's RAG runbook pipeline | AI in the Stack #2 |
| `demo-mcp-server` | [openshift-mcp-sre-tools](https://github.com/nedoshi/openshift-mcp-sre-tools) against a real ARO/ROSA/OSD cluster — **verify which transport that repo currently uses before swapping.** This demo speaks Streamable HTTP only; if `openshift-mcp-sre-tools` still runs the deprecated SSE transport, either update it to Streamable HTTP or set the n8n credential's connection type to SSE instead. | AI in the Stack #3 |
| Chat model credential | Vertex AI via GCP service account | This article, Step 2 |
| Manual `curl` trigger | Alertmanager webhook (see `config/alertmanager.yml.example`) | This article, Step 3 — **note: this block was not tested against a live Alertmanager** |

Update the **HTTP Streamable URL** in your `Demo MCP Server (Streamable HTTP)` credential from `http://demo-mcp-server:8080/mcp` to your real MCP server's address (this is a credential field, not something set on the `MCP Get Failing Pods` / `MCP Get Events` nodes directly — both nodes share the one credential, so updating it once covers both). Update the **RAG Query** HTTP Request node's URL from `http://demo-rag-service:8080/query` to your real RAG service.

### Swapping the LLM provider

The `Analyze (Vertex AI)` node is a standard n8n AI chat model node. To use a different provider for local testing, delete it and drag in whichever chat model node matches credentials you already have (OpenAI, Anthropic, Ollama) — the rest of the workflow doesn't care which model produced the analysis, only that the node returns text. This mirrors the provider-abstraction pattern from Article 05.

## What changed after review

A second AI tool reviewed this repo and suggested several production-hardening additions. Three were in scope for a tutorial demo and are now built in:

- **Tool schemas** — `demo-mcp-server/server.py`'s tools declare explicit, validated parameter schemas (`limit` bounded 1–100, `pod_name` required and non-empty, namespace pattern-checked). The MCP server rejects an out-of-range or missing parameter before the handler ever runs — try `get_events` with `limit: 500` and you'll get a validation error, not a silently clamped value. This is what "tool schemas prevent the agent from inventing parameters" looks like enforced, not just described.
- **Parallel MCP calls** — the workflow no longer routes both MCP lookups through one combined node. `MCP Get Failing Pods` and `MCP Get Events` are separate nodes that both fire directly off `Parse Alert`, alongside `RAG Query` — three branches running concurrently instead of the agent calling tools one at a time. They rejoin at a 3-input `Merge` node before analysis.
- **Per-node latency timing** — small `Mark * Latency` code nodes stamp `Date.now()` as each branch completes. `Log Execution` at the end computes how long the RAG query, each MCP call, and the LLM analysis step actually took, in milliseconds. n8n's canvas doesn't show per-node runtime by default, so this is what makes the "30-minute run" problem from the article actually measurable in your own executions instead of just visible in hindsight.

Suggestions that weren't adopted, and why:
- **Planning loops / multi-agent orchestration** — this would have the agent decide its own tool-call sequence, which runs against the article's core argument: bound the agent to one step inside a deterministic pipeline, don't let it plan freely. Fits a different article, not this one.
- **MCP connection pooling / rate limiting** — a real production concern, but not something a single-user local tutorial demo needs. Worth a line in your own production notes, not new code here.

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
- **MCP Get Failing Pods / MCP Get Events can't connect** — first confirm `demo-mcp-server` is healthy: `docker compose logs demo-mcp-server`. Then check the `Demo MCP Server (Streamable HTTP)` credential's HTTP Streamable URL is exactly `http://demo-mcp-server:8080/mcp` (from inside the Docker network, not `localhost` — that's the container name n8n resolves internally, and it only works because both containers share the compose network).
- **"Unrecognized node type: n8n-nodes-mcp.mcpClient"** — the community package isn't installed yet, or wasn't installed before the workflow was imported. Go to Settings → Community Nodes → Install → `n8n-nodes-mcp`, then re-open the workflow.
- **MCP node rejects a call with a validation error** — that's the tool schema working as intended, not a bug. Check the parameter against the bounds in `demo-mcp-server/server.py` (e.g. `limit` must be 1–100).
- **Slack node fails** — double check `SLACK_WEBHOOK_URL` in `.env` and that `docker compose up -d` was re-run after editing it (`docker compose up -d --force-recreate n8n`).
- **Workflow runs but never posts to Slack** — check the IF node's condition; the demo MCP server's canned "no failing pods" response may be routing you down the light-notify branch. Edit `demo-services/demo-mcp-server/server.py` to return a failing pod if you want to force the full-alert branch.

## License

MIT — see `LICENSE`.
