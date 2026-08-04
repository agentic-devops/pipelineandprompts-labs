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
# Clone all labs
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs

# Try the RAG runbook assistant
cd ai-in-the-stack/02-rag-runbook-assistant
docker-compose up
```

## Structure

```
pipelineandprompts-labs/
├── ai-in-the-stack/          # AI integration examples
├── pipelines-in-the-wild/    # CI/CD patterns
└── devops-from-zero/         # Foundational labs
```

Each lab's README opens with a status label so you know what to expect before you clone:

- **Full walkthrough** — working code, tests, and a verified end-to-end setup.
- **Reference only** — explains concepts/architecture, no runnable code yet.
- **Coming soon** — placeholder, not yet published.

Labs marked "Full walkthrough" include:
- `README.md` with setup instructions
- Working code
- Tests
- Docker configs (where applicable)

## A note on lab numbering

Lab numbers are sequential per series but not every number is guaranteed to exist forever —
if a planned lab is retired or merged into another, the series README will say so explicitly
rather than leaving a silent gap.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to submit a lab, report a broken tutorial
step, or suggest a fix.

## License

MIT — see [LICENSE](./LICENSE).
