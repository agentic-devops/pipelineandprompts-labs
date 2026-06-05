# ai-stack-02-rag-runbooks

A FastAPI service that makes internal runbooks semantically searchable using RAG (Retrieval-Augmented Generation). Engineers ask questions in natural language and get answers grounded in your actual documentation, with source citations.

![Architecture](docs/rag-pipeline-internal-runbooks-architecture.png)

---

## Architecture Overview

Two data flows. The ingest path runs once and on every runbook update: markdown files are chunked with `RecursiveCharacterTextSplitter`, embedded via OpenAI `text-embedding-3-small`, and stored in a local Chroma vector store. The query path runs at incident time: the question is embedded, Chroma returns the top-K matching chunks, those chunks are assembled into a prompt, and `gpt-4o-mini` returns a grounded answer with source citations.

OpenAI is the only external dependency. Chroma runs locally against the filesystem.

---

## Use Cases

- On-call engineer asks "why is my pod stuck in CrashLoopBackOff after a config change?" and gets a cited answer from your Kubernetes runbooks in under two seconds
- Junior team member queries the service instead of paging a senior at 2am for a known issue that is documented but hard to find
- Slack bot integration that surfaces the relevant runbook section when an alert fires, before a human even opens a terminal
- Post-incident review tooling that queries your runbook corpus to identify whether the failure mode was documented
- Bootstrapping new team members with a queryable knowledge base during their first on-call rotation

---

## Prerequisites

- Python 3.11+
- Docker (for containerised deployment)
- OpenAI API key with access to `text-embedding-3-small` and `gpt-4o-mini`
- For OpenShift/Kubernetes deployment: a namespace with permission to create Deployments, Services, and Secrets

---

## Quick Start

```bash
# Clone and enter the directory
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/ai-stack-02-rag-runbooks

# Install dependencies
pip install fastapi uvicorn openai chromadb langchain-text-splitters pydantic-settings python-dotenv

# Configure environment
cp .env.example .env
# Edit .env — add OPENAI_API_KEY and set API_KEY to a secret value

# Add your runbook markdown files
cp your-runbooks/*.md runbooks/

# Start the service
uvicorn app.main:app --reload --port 8080

# Ingest runbooks
curl -X POST http://localhost:8080/ingest \
  -H "X-API-Key: your-secret-key-here"

# Query
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{"question": "why is my pod stuck in CrashLoopBackOff after a config change?"}'
```

---

## Project Structure

```
ai-stack-02-rag-runbooks/
├── app/
│   ├── main.py           # FastAPI app — routes and endpoint definitions
│   ├── ingest.py         # Document loading, chunking, embedding, Chroma upsert
│   ├── query.py          # Vector search, prompt assembly, LLM call
│   ├── auth.py           # APIKeyHeader dependency for endpoint protection
│   └── config.py         # Pydantic Settings — reads from .env
├── runbooks/
│   └── *.md              # Markdown runbook files (not committed — add your own)
├── chroma_db/            # Chroma vector store — auto-created on first ingest
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

## Configuration

All settings are read from `.env` via `pydantic-settings`. Copy `.env.example` and fill in values before running.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | required | OpenAI API key |
| `API_KEY` | required | Secret key for `X-API-Key` header authentication |
| `CHROMA_PATH` | `./chroma_db` | Path to the Chroma persistent store |
| `RUNBOOKS_PATH` | `./runbooks` | Directory containing markdown runbook files |
| `CHUNK_SIZE` | `500` | Token chunk size for text splitting |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks |
| `TOP_K_RESULTS` | `4` | Number of chunks returned per query |

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Confirms service is reachable and Chroma is responding |
| `POST` | `/ingest` | `X-API-Key` | Loads, chunks, embeds, and upserts all runbooks in `RUNBOOKS_PATH` |
| `POST` | `/query` | `X-API-Key` | Accepts a natural language question, returns answer and source citations |

`/query` request body:
```json
{ "question": "string — max 2000 characters" }
```

`/query` response:
```json
{
  "answer": "string",
  "sources": ["runbook-filename.md", "..."]
}
```

---

## Docker

```bash
# Build
docker build -t runbook-rag:latest .

# Run (development — baked runbooks)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e API_KEY=$API_KEY \
  -v $(pwd)/chroma_db:/app/chroma_db \
  runbook-rag:latest

# Run (production — mounted runbooks)
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e API_KEY=$API_KEY \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/runbooks:/app/runbooks \
  runbook-rag:latest
```

---

## OpenShift / Kubernetes Deployment

Store both keys as a Secret:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: runbook-rag-secret
  namespace: your-namespace
type: Opaque
stringData:
  API_KEY: your-secret-key-here
  OPENAI_API_KEY: sk-...
```

Reference in your Deployment:

```yaml
envFrom:
  - secretRef:
      name: runbook-rag-secret
```

Mount the Chroma store as a PersistentVolumeClaim to survive pod restarts. Without a PVC, every pod restart loses the vector store and requires a fresh ingest.

---

## Security Notes

**Authentication.** `POST /ingest` and `POST /query` require a valid `X-API-Key` header. The key is validated against `settings.api_key` in `app/auth.py`. Do not expose these endpoints without this middleware or an equivalent auth layer in front.

**Prompt injection.** The system prompt in `app/query.py` explicitly instructs the model to treat all context as data only. This is a partial mitigation. Review runbooks sourced from external systems (wiki syncs, CI pipelines) before ingestion.

**Secret management.** Never commit `.env` — it is in `.gitignore`. In production, use your platform's secrets store (Vault, OpenShift Secrets, AWS Secrets Manager). The `.env` pattern is for local development only.

**Blast radius.** This service makes outbound calls to the OpenAI API for every ingest and every query. A misconfigured loop or an unauthenticated `/ingest` endpoint can generate significant API spend. Monitor your OpenAI usage dashboard after deployment.

---

## Known Limitations

- Chroma runs as a local file-backed store — not suitable for multi-replica deployments without a shared PVC or migration to a hosted vector database
- Runbook ingest is synchronous and single-threaded — large corpora (500+ documents) will take time and should be triggered off-hours
- No ingest webhook is included — re-ingestion must be triggered manually or via an external cron/event
- The service loads only `.md` files from `RUNBOOKS_PATH` — PDF or HTML runbooks require a conversion step before ingest
- Token limit on OpenAI context window means very large top-K values with large chunks may exceed the model's context, causing silent truncation

---

## Roadmap

- Webhook endpoint to trigger re-ingest on Git push or wiki update
- Support for PDF and HTML runbook formats via document conversion pipeline
- Swap OpenAI for Ollama (covered in AI in the Stack #06) for air-gapped or cost-sensitive environments
- Chroma → hosted vector database migration guide (Pinecone, Weaviate, pgvector)
- Slack bot integration example that queries the service when a PagerDuty alert fires

---

## GitHub Topics

`rag` `retrieval-augmented-generation` `platform-engineering` `fastapi` `chromadb` `openai` `kubernetes` `devops` `python` `ai-in-the-stack`

---

## Linked Article

For full implementation walkthrough:
**Build a RAG Pipeline for Internal Runbooks with FastAPI and Chroma** — pipelineandprompts.com/posts/rag-pipeline-internal-runbooks-platform-engineering/
