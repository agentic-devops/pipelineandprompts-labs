"""
Today I Ran — Block 1, Item 1: Bulk-embed the real published catalog

What this does, and why it's different from Entries 05-07:
- Chunks every document from the start, not retrofitted after hitting
  a context-length error (that was Entry 05's path).
- Scans a whole directory instead of a hardcoded file list — built for
  bulk-loading AI in the Stack / Pipelines in the Wild, not single
  test files.
- Reports a summary at the end (files, chunks, skips, failures) rather
  than a line-by-line log, since this is bulk work, not a walkthrough.

Before running:
- `ollama pull nomic-embed-text` (if you haven't already)
- `pip3 install ollama chromadb --break-system-packages` (inside your
  venv if you're using one — this does NOT need the mcp package, so
  it can run outside ~/mcp-env if that's simpler)
- Set SOURCE_DIR (env var) to the folder of markdown files to index
- Run from ~/Downloads, same as every prior entry, so it finds the
  existing ./chroma_db

Run with: python3 bulk_embed_catalog.py
"""

import ollama
import chromadb
from pathlib import Path

# --- Edit this to point at your actual published content ---
import os
SOURCE_DIR = os.environ.get("SOURCE_DIR", "./content/posts")  # folder of .md files to index

EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "today_i_ran_notes"

# Same chunk size as Entry 07, applied from the start this time.
CHUNK_SIZE = 1000
OVERLAP = 200


def chunk_text(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    return [
        text[i : i + CHUNK_SIZE]
        for i in range(0, len(text), CHUNK_SIZE - OVERLAP)
    ]


def main():
    source_path = Path(SOURCE_DIR).expanduser()

    if not source_path.exists():
        print(f"SOURCE_DIR does not exist: {source_path}")
        print("Edit SOURCE_DIR at the top of this script and re-run.")
        return

    md_files = sorted(source_path.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {source_path}")
        return

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    before_count = collection.count()

    files_processed = 0
    chunks_embedded = 0
    files_failed = []

    for path in md_files:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"FAIL  — could not read {path.name}: {e}")
            files_failed.append(path.name)
            continue

        if not text.strip():
            print(f"SKIP  — empty file: {path.name}")
            continue

        chunks = chunk_text(text)

        for i, chunk in enumerate(chunks):
            try:
                resp = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)
            except Exception as e:
                print(f"FAIL  — embedding chunk {i} of {path.name}: {e}")
                continue

            # Single-chunk files keep the plain filename as their ID,
            # matching the convention from Entries 05-06. Multi-chunk
            # files get the _chunkN suffix from Entry 07.
            doc_id = path.stem if len(chunks) == 1 else f"{path.stem}_chunk{i}"

            collection.upsert(
                ids=[doc_id],
                embeddings=[resp["embedding"]],
                documents=[chunk],
                metadatas=[{"source": path.name, "chunk_index": i, "total_chunks": len(chunks)}],
            )
            chunks_embedded += 1

        print(f"OK    — {path.name} ({len(chunks)} chunk{'s' if len(chunks) != 1 else ''}, {len(text)} chars)")
        files_processed += 1

    after_count = collection.count()

    print("\n--- Summary ---")
    print(f"Files found:      {len(md_files)}")
    print(f"Files processed:  {files_processed}")
    print(f"Files failed:     {len(files_failed)} {files_failed if files_failed else ''}")
    print(f"Chunks embedded:  {chunks_embedded}")
    print(f"Collection size:  {before_count} -> {after_count}")


if __name__ == "__main__":
    main()
