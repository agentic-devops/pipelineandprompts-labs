import os
from pathlib import Path
from openai import OpenAI
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)
chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
collection = chroma_client.get_or_create_collection(name="runbooks")


def embed_text(text: str) -> list[float]:
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def load_and_chunk_runbooks() -> list[dict]:
    runbooks_path = Path(settings.runbooks_path)
    chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap
    )

    for filepath in runbooks_path.glob("*.md"):
        content = filepath.read_text(encoding="utf-8")
        doc_chunks = splitter.split_text(content)

        for i, chunk in enumerate(doc_chunks):
            chunks.append({
                "id": f"{filepath.stem}-chunk-{i}",
                "text": chunk,
                "source": filepath.name
            })

    return chunks


def ingest_runbooks() -> dict:
    chunks = load_and_chunk_runbooks()

    if not chunks:
        return {"status": "no runbooks found", "chunks_ingested": 0}

    for chunk in chunks:
        embedding = embed_text(chunk["text"])
        collection.upsert(
            ids=[chunk["id"]],
            embeddings=[embedding],
            documents=[chunk["text"]],
            metadatas=[{"source": chunk["source"]}]
        )

    return {
        "status": "ingested",
        "chunks_ingested": len(chunks),
        "runbooks_processed": len(set(c["source"] for c in chunks))
    }
