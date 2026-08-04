# Security

This monorepo backs tutorials on [pipelineandprompts.com](https://pipelineandprompts.com).

## Reporting a vulnerability

Open a private security advisory on GitHub if the issue involves credential leakage or remote code execution in a lab. For broken tutorial steps (wrong paths, missing env vars), use the [Broken tutorial](.github/ISSUE_TEMPLATE/broken-tutorial.md) issue template instead.

## Lab-specific notes

- **RAG (AI 02):** `X-API-Key` required on `/ingest` and `/query`. See `ai-in-the-stack/02-rag-runbook-assistant/docs/SECURITY.md`.
- **MCP (AI 03):** read-only RBAC by design; API key on non-health routes. See that lab's `OPEN_ITEMS.md` before production use.
- **n8n (AI 06):** keep real MCP servers read-only; protect webhooks before pointing Alertmanager at them.
- **Never commit** `.env`, cloud tokens, or kubeconfigs. Each runnable lab ships `.env.example` where secrets are required.
