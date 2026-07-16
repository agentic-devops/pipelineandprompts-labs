"""
Demo RAG service standing in for the Article 02 runbook retrieval pipeline.

Returns a canned runbook answer and source list for any question, so the
n8n workflow's RAG Query node has something real to call over HTTP while
you're validating the workflow shape locally.
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="demo-rag-service")


class QueryRequest(BaseModel):
    question: str


CANNED_ANSWER = (
    "CrashLoopBackOff on payment-api is most commonly caused by a failing "
    "readiness probe during startup. Check that the downstream dependency "
    "(payment-db) is reachable before the app's health check window expires. "
    "Runbook step 1: `oc logs <pod> --previous`. Runbook step 2: verify the "
    "DB connection secret hasn't rotated. Runbook step 3: if restarts exceed "
    "5 in 10 minutes, escalate to the payments on-call rotation."
)

CANNED_SOURCES = ["runbooks/payment-api-crashloop.md", "sops/db-connection-rotation.md"]


@app.post("/query")
def query(req: QueryRequest) -> dict:
    return {
        "question": req.question,
        "answer": CANNED_ANSWER,
        "sources": CANNED_SOURCES,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
