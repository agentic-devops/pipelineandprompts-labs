# Runbooks Directory

Place your operational runbooks in this directory as markdown (`.md`) files.

## Format Requirements

- **File format:** Markdown (`.md`)
- **Encoding:** UTF-8
- **Structure:** Any markdown structure works - headers, lists, code blocks, etc.

## Naming Conventions

Use descriptive, lowercase filenames with hyphens:
- ✅ `kubernetes-crashloop-troubleshooting.md`
- ✅ `database-migration-rollback.md`
- ✅ `config-deployment-procedures.md`
- ❌ `doc1.md`
- ❌ `Troubleshooting.md`

## Content Guidelines

Write runbooks as you normally would. The RAG system will:
- Chunk your content automatically (500 tokens per chunk with 50 token overlap)
- Index it semantically (not just keyword matching)
- Surface relevant sections based on natural language queries

### What Makes a Good Runbook for RAG

1. **Clear problem descriptions** - Engineers will search using symptoms
2. **Step-by-step procedures** - Specific actions are easier to retrieve
3. **Context and examples** - Helps semantic matching
4. **Consistent terminology** - Use the same terms your team uses

### Example Structure

```markdown
# Service Restart Procedure

## Symptoms
- Service unresponsive
- Health check failures
- Timeout errors in logs

## Diagnosis Steps
1. Check service logs: `kubectl logs -n prod <pod-name>`
2. Verify resource limits: `kubectl describe pod <pod-name>`
3. Check recent deployments: `kubectl rollout history deployment/<name>`

## Resolution
...
```

## Updating Runbooks

After adding or modifying runbooks:

```bash
# Re-ingest to update the vector store
curl -X POST http://localhost:8080/ingest
```

The system uses `upsert`, so re-ingesting won't create duplicates.

## Sample Runbooks

This directory includes sample runbooks to demonstrate the system:
- `kubernetes-crashloop-troubleshooting.md` - Pod restart debugging
- `config-rollback-procedures.md` - Configuration rollback steps

Replace these with your actual runbooks.
