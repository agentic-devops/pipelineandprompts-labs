# AI in the Stack - Code Labs

Hands-on code examples from the [AI in the Stack](https://pipelineandprompts.com/series/ai-in-the-stack/) series.

## Labs

| # | Lab | Status |
|---|---|---|
| 1 | [AI Tooling Evaluation Framework](01-ai-tooling-evaluation/) | Coming soon |
| 2 | [RAG Runbook Assistant](02-rag-runbook-assistant/) | Full walkthrough |
| 3 | [MCP Server for Kubernetes](03-mcp-for-kubernetes/) | Full walkthrough |
| 4 | [Prompt Versioning CI for OpenShift](04-prompt-versioning-ci/) | Full walkthrough |
| 5 | [Swapping LLM Providers](05-swapping-llm-provider/) | Reference only |
| 6 | [n8n Agentic Incident Triage](06-n8n-agentic-workflows/) | Full walkthrough |

## Prerequisites

- Python 3.11+
- Docker (labs 02, 06)
- Kubernetes / OpenShift cluster (labs 03, 04; optional for others)
- OpenAI API key (lab 02)

## Transport note (labs 03 ↔ 06)

Lab 03 speaks **SSE**. Lab 06's demo MCP speaks **Streamable HTTP**. See each lab README before wiring them together.
