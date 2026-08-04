from pathlib import Path

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI

from app.config import settings

client = OpenAI(api_key=settings.openai_api_key)
chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
collection = chroma_client.get_or_create_collection(name="runbooks")

# OpenAI embedding batch size — keep under API limits while cutting round-trips
EMBED_BATCH_SIZE = 100


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed one or more texts in a single API call when possible."""
    if not texts:
        return []

    embeddings: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        response = client.embeddings.create(
            input=batch,
            model="text-embedding-3-small",
        )
        # API returns data sorted by index
        ordered = sorted(response.data, key=lambda item: item.index)
        embeddings.extend(item.embedding for item in ordered)
    return embeddings


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def load_and_chunk_runbooks() -> list[dict]:
    runbooks_path = Path(settings.runbooks_path)
    if not runbooks_path.is_dir():
        return []

    files = [
        filepath
        for filepath in sorted(runbooks_path.glob("*.md"))
        # Skip the directory README — it is setup docs, not a runbook
        if filepath.name.lower() != "readme.md"
    ]
    if not files:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks: list[dict] = []
    for filepath in files:
        content = filepath.read_text(encoding="utf-8")
        doc_chunks = splitter.split_text(content)

        for i, chunk in enumerate(doc_chunks):
            chunks.append(
                {
                    "id": f"{filepath.stem}-chunk-{i}",
                    "text": chunk,
                    "source": filepath.name,
                }
            )

    return chunks


def ingest_runbooks() -> dict:
    chunks = load_and_chunk_runbooks()

    if not chunks:
        return {
            "status": "no runbooks found",
            "chunks_ingested": 0,
            "hint": (
                f"Place .md runbooks in {settings.runbooks_path} "
                "(sample files ship in this lab's runbooks/ directory)"
            ),
        }

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embed_texts(texts)

    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": chunk["source"]} for chunk in chunks],
    )

    return {
        "status": "ingested",
        "chunks_ingested": len(chunks),
        "runbooks_processed": len({chunk["source"] for chunk in chunks}),
    }
