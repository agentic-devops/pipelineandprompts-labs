from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.auth import verify_api_key
from app.ingest import chroma_client, ingest_runbooks
from app.query import query_runbooks

app = FastAPI(
    title="Runbook RAG API",
    description="Operational troubleshooting grounded in your actual runbooks",
    version="1.0.0",
)


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    try:
        chroma_client.heartbeat()
        return {"status": "healthy", "vector_store": "reachable"}
    except Exception:
        raise HTTPException(status_code=503, detail="Vector store unreachable")


@app.post("/ingest", dependencies=[Depends(verify_api_key)])
def ingest():
    try:
        return ingest_runbooks()
    except Exception:
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.post("/query", dependencies=[Depends(verify_api_key)])
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(request.question) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Question exceeds maximum length of 2000 characters",
        )
    try:
        return query_runbooks(request.question)
    except Exception:
        raise HTTPException(status_code=500, detail="Query failed")
