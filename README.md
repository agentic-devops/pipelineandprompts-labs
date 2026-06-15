# Pipeline & Prompts Labs

Hands-on code examples from [pipelineandprompts.com](https://pipelineandprompts.com)

## Series

### 🤖 [AI in the Stack](./ai-in-the-stack/)
Practical AI integrations for platform engineering. FastAPI, RAG, MCP servers, LLM evaluation.

### 🔄 [Pipelines in the Wild](./pipelines-in-the-wild/)
Production CI/CD patterns. GitHub Actions, zero-downtime deployments, retry logic, secrets management.

### 📚 [DevOps from Zero](./devops-from-zero/)
Foundational DevOps concepts. (Future hands-on labs coming soon)

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

Each lab includes:
- `README.md` - Setup instructions
- Working code
- Tests
- Docker configs (where applicable)

## Contributing

See individual lab READMEs for specific requirements.

## License

MIT
