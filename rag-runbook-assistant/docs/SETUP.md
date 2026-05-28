# Detailed Setup Guide

This guide walks through setting up the RAG pipeline for internal runbooks in different environments.

## Table of Contents

- [Local Development Setup](#local-development-setup)
- [Docker Setup](#docker-setup)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Production Configuration](#production-configuration)
- [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- OpenAI API key with access to embeddings and GPT models
- 500MB free disk space
- Git (for cloning the repository)

### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/pipeline-and-prompts-labs/ai-stack-02-rag-runbooks.git
   cd ai-stack-02-rag-runbooks
   ```

2. **Create and activate virtual environment:**
   ```bash
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   
   # On Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

5. **Add your runbooks:**
   - Place markdown files in the `runbooks/` directory
   - Or use the provided sample runbooks to test

6. **Start the service:**
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```
   
   You should see:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
   INFO:     Started reloader process
   INFO:     Started server process
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

7. **Ingest runbooks:**
   ```bash
   curl -X POST http://localhost:8080/ingest
   ```
   
   Expected response:
   ```json
   {
     "status": "ingested",
     "chunks_ingested": 42,
     "runbooks_processed": 5
   }
   ```

8. **Test a query:**
   ```bash
   curl -X POST http://localhost:8080/query \
     -H "Content-Type: application/json" \
     -d '{"question": "how do I troubleshoot a pod in CrashLoopBackOff?"}'
   ```

## Docker Setup

### Build and Run Locally

1. **Build the image:**
   ```bash
   docker build -t runbook-rag:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name runbook-rag \
     -p 8080:8080 \
     -e OPENAI_API_KEY=$OPENAI_API_KEY \
     -v $(pwd)/chroma_db:/app/chroma_db \
     -v $(pwd)/runbooks:/app/runbooks \
     runbook-rag:latest
   ```

3. **Check logs:**
   ```bash
   docker logs -f runbook-rag
   ```

4. **Ingest and query:**
   ```bash
   curl -X POST http://localhost:8080/ingest
   curl -X POST http://localhost:8080/query \
     -H "Content-Type: application/json" \
     -d '{"question": "your question here"}'
   ```

### Using Docker Compose

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f
   ```

3. **Stop services:**
   ```bash
   docker-compose down
   ```

## Kubernetes Deployment

### Basic Deployment

1. **Create namespace:**
   ```bash
   kubectl create namespace runbook-rag
   ```

2. **Create secret for OpenAI API key:**
   ```bash
   kubectl create secret generic openai-credentials \
     --from-literal=api-key=$OPENAI_API_KEY \
     -n runbook-rag
   ```

3. **Create deployment:**
   ```yaml
   # deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: runbook-rag
     namespace: runbook-rag
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: runbook-rag
     template:
       metadata:
         labels:
           app: runbook-rag
       spec:
         containers:
         - name: runbook-rag
           image: runbook-rag:latest
           ports:
           - containerPort: 8080
           env:
           - name: OPENAI_API_KEY
             valueFrom:
               secretKeyRef:
                 name: openai-credentials
                 key: api-key
           - name: CHROMA_PATH
             value: "/data/chroma_db"
           volumeMounts:
           - name: vector-store
             mountPath: /data/chroma_db
           - name: runbooks
             mountPath: /app/runbooks
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
           livenessProbe:
             httpGet:
               path: /health
               port: 8080
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /health
               port: 8080
             initialDelaySeconds: 5
             periodSeconds: 5
         volumes:
         - name: vector-store
           persistentVolumeClaim:
             claimName: runbook-rag-pvc
         - name: runbooks
           configMap:
             name: runbooks-config
   ```

4. **Create PVC for vector store:**
   ```yaml
   # pvc.yaml
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: runbook-rag-pvc
     namespace: runbook-rag
   spec:
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 5Gi
   ```

5. **Create ConfigMap for runbooks:**
   ```bash
   kubectl create configmap runbooks-config \
     --from-file=runbooks/ \
     -n runbook-rag
   ```

6. **Create service:**
   ```yaml
   # service.yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: runbook-rag-service
     namespace: runbook-rag
   spec:
     selector:
       app: runbook-rag
     ports:
     - port: 80
       targetPort: 8080
     type: ClusterIP
   ```

7. **Apply all resources:**
   ```bash
   kubectl apply -f pvc.yaml
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   ```

8. **Trigger initial ingest:**
   ```bash
   kubectl exec -n runbook-rag deployment/runbook-rag -- \
     curl -X POST http://localhost:8080/ingest
   ```

## Production Configuration

### Environment Variables

For production, configure via your platform's secrets manager:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `CHROMA_PATH` | No | `./chroma_db` | Vector store path |
| `RUNBOOKS_PATH` | No | `./runbooks` | Runbooks directory |
| `CHUNK_SIZE` | No | `500` | Tokens per chunk |
| `CHUNK_OVERLAP` | No | `50` | Overlap between chunks |
| `TOP_K_RESULTS` | No | `4` | Chunks to retrieve |

### Authentication

⚠️ **Critical:** Add authentication before production deployment.

Example with FastAPI API key:

```python
# app/auth.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# app/main.py
from app.auth import verify_api_key

@app.post("/query", dependencies=[Depends(verify_api_key)])
def query(request: QueryRequest):
    # ... existing code
```

### Automatic Re-Ingestion

Set up a CronJob to re-ingest when runbooks change:

```yaml
# cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: runbook-reingest
  namespace: runbook-rag
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: reingest
            image: curlimages/curl:latest
            command:
            - curl
            - -X
            - POST
            - http://runbook-rag-service/ingest
          restartPolicy: OnFailure
```

### Monitoring

Add metrics and alerting:

```python
# app/main.py
from prometheus_client import Counter, Histogram
import time

query_counter = Counter('queries_total', 'Total queries')
query_duration = Histogram('query_duration_seconds', 'Query duration')

@app.post("/query")
def query(request: QueryRequest):
    query_counter.inc()
    start = time.time()
    try:
        result = query_runbooks(request.question)
        return result
    finally:
        query_duration.observe(time.time() - start)
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"

**Cause:** Not running from project root or virtual environment not activated.

**Fix:**
```bash
cd /path/to/ai-stack-02-rag-runbooks
source venv/bin/activate
uvicorn app.main:app --reload
```

### "Vector store unreachable"

**Cause:** Chroma DB not initialized.

**Fix:**
```bash
# Run ingest first
curl -X POST http://localhost:8080/ingest
```

### "OpenAI API error: 401 Unauthorized"

**Cause:** Invalid or missing API key.

**Fix:**
1. Verify key in `.env` file
2. Check key is active at https://platform.openai.com/api-keys
3. Restart the service after updating `.env`

### "No relevant runbooks found"

**Cause:** No runbooks ingested or question too specific.

**Fix:**
1. Check runbooks exist: `ls runbooks/`
2. Re-run ingest: `curl -X POST http://localhost:8080/ingest`
3. Try rephrasing question to be more general

### High memory usage

**Cause:** Large vector store or many concurrent queries.

**Fix:**
1. Reduce `TOP_K_RESULTS` in `.env`
2. Reduce `CHUNK_SIZE` to create smaller chunks
3. Increase container memory limits

### Slow query responses

**Cause:** Large document corpus or network latency to OpenAI.

**Fix:**
1. Reduce `TOP_K_RESULTS` to retrieve fewer chunks
2. Use a smaller embedding model (if available)
3. Cache common queries
4. Consider local LLM deployment (Ollama)

## Next Steps

- See [SECURITY.md](SECURITY.md) for security hardening
- Read the main [README.md](../README.md) for usage examples
- Check the article for architecture details
