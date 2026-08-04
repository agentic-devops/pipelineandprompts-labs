# Pipeline & Prompts Labs

Hands-on code examples from [pipelineandprompts.com](https://pipelineandprompts.com)

## Series

### [AI in the Stack](./ai-in-the-stack/)
Practical AI integrations for platform engineering. FastAPI, RAG, MCP servers, LLM evaluation.

### [Pipelines in the Wild](./pipelines-in-the-wild/)
Production CI/CD patterns. GitHub Actions, zero-downtime deployments, retry logic, secrets management.

### [DevOps from Zero](./devops-from-zero/)
Foundational DevOps concepts. Hands-on labs coming soon — see that series' README for status.

## Quick Start

```bash
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs

# Fastest local demo (needs OpenAI key)
cd ai-in-the-stack/02-rag-runbook-assistant
cp .env.example .env   # set OPENAI_API_KEY and API_KEY
docker compose up --build
```

Prefer no OpenAI key? Try the n8n incident-triage demo (Slack webhook optional for full path):

```bash
cd ai-in-the-stack/06-n8n-agentic-workflows
cp .env.example .env
docker compose up -d
```

## Lab matrix

| Lab | Status | Local Docker | Cluster | Cloud keys |
|---|---|---|---|---|
| [AI 02 — RAG runbooks](./ai-in-the-stack/02-rag-runbook-assistant/) | Full walkthrough | Yes | Optional | OpenAI |
| [AI 03 — MCP for Kubernetes](./ai-in-the-stack/03-mcp-for-kubernetes/) | Full walkthrough | Partial | Yes | None (kubeconfig) |
| [AI 04 — Prompt versioning CI](./ai-in-the-stack/04-prompt-versioning-ci/) | Full walkthrough | Scripts only | OpenShift sync | OpenShift token |
| [AI 06 — n8n incident triage](./ai-in-the-stack/06-n8n-agentic-workflows/) | Full walkthrough | Yes | Optional | Slack (optional) |
| [Pipelines 01 — Zero-downtime](./pipelines-in-the-wild/01-zero-downtime-deployments/) | Full walkthrough | App only | ROSA/OpenShift | Cluster |
| [Pipelines 02 — Retry / Waybill](./pipelines-in-the-wild/02-retry-logic-tiered-alerting/) | Full walkthrough | Yes | Optional | None |
| [Pipelines 03 — Secrets](./pipelines-in-the-wild/03-secrets-management-multi-cloud/) | Full walkthrough | No | Yes | Cloud / Vault |
| [Pipelines 04 — Terraform state](./pipelines-in-the-wild/04-terraform-managed-openshift-state/) | Full walkthrough | No | Managed OCP | Cloud |
| [Pipelines 06 — DB migration](./pipelines-in-the-wild/06-database-migration-managed-openshift/) | Full walkthrough | Partial | ROSA/ARO | Optional ESO |
| [AI 01 / 05, Pipelines 05](./ai-in-the-stack/) | Reference / Coming soon | — | — | — |

## Structure

```
pipelineandprompts-labs/
├── ai-in-the-stack/          # AI integration examples
├── pipelines-in-the-wild/    # CI/CD patterns
├── devops-from-zero/         # Foundational labs (coming soon)
└── _shared/                  # Shared Docker base images (optional)
```

Each lab's README opens with a status label so you know what to expect before you clone:

- **Full walkthrough** — working code, tests, and a verified end-to-end setup.
- **Reference only** — explains concepts/architecture, no runnable code yet.
- **Coming soon** — placeholder, not yet published.

## A note on lab numbering

Lab numbers are sequential per series but not every number is guaranteed to exist forever —
if a planned lab is retired or merged into another, the series README will say so explicitly
rather than leaving a silent gap.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to submit a lab, report a broken tutorial
step, or suggest a fix.

## License

MIT — see [LICENSE](./LICENSE).
