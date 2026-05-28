from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.ingest import ingest_runbooks, chroma_client
from app.query import query_runbooks

app = FastAPI(
    title="Runbook RAG API",
    description="Operational troubleshooting grounded in your actual runbooks",
    version="1.0.0"
)


class QueryRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    try:
        chroma_client.heartbeat()
        return {"status": "healthy", "vector_store": "reachable"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Vector store unreachable: {str(e)}")


@app.post("/ingest")
def ingest():
    try:
        result = ingest_runbooks()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if len(request.question) > 2000:
        raise HTTPException(status_code=400, detail="Question exceeds maximum length of 2000 characters")
    try:
        result = query_runbooks(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
