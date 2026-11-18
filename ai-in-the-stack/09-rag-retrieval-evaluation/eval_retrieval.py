"""
Today I Ran — Block 1, Item 3: score retrieval against known right answers

For each question in eval_questions.json that has an "expected" source file,
this finds where that document lands in the ranking, two ways:

  chunk rank : position of its best chunk among ALL chunks (what an uncapped
               query returns)
  doc rank   : position among distinct documents (what a per-document cap of 1
               returns)

It also counts how many of the top 5 chunks come from the expected document.
That column matters because doc-level hit rates can only improve under a cap
(the cap removes chunks that sat above the right document). What a cap costs
is extra chunks of the right document, which only shows up in that count.

Questions with "expected": null are controls (no right answer in the corpus).
They are printed but excluded from the scores.

Run from the folder that contains chroma_db (~/Downloads, as in earlier entries):
    python3 eval_retrieval.py
"""

import json
import re
import sys
from pathlib import Path

EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "today_i_ran_notes"
QUESTIONS_FILE = "eval_questions.json"
RESULTS_FILE = "eval_results.json"

# "Today I Ran" entries are named 01-..., 15-...; other posts are not.
SERIES_ENTRY = re.compile(r"^\d{2}-")


def rank_sources(sources):
    """sources: source names ordered best to worst, one per chunk.
    Returns {source: (best_chunk_rank, doc_rank)}, both 1-based."""
    first_chunk = {}
    for position, source in enumerate(sources, 1):
        first_chunk.setdefault(source, position)
    doc_order = sorted(first_chunk, key=first_chunk.get)
    return {s: (first_chunk[s], d) for d, s in enumerate(doc_order, 1)}


def summarize(rows):
    """rows: list of dicts with chunk_rank, doc_rank, expected_in_top5, top1_is_series."""
    n = len(rows)
    if n == 0:
        return {}
    summary = {"questions": n}
    for k in (1, 3, 5):
        summary[f"chunk_hit@{k}"] = sum(r["chunk_rank"] <= k for r in rows) / n
        summary[f"doc_hit@{k}"] = sum(r["doc_rank"] <= k for r in rows) / n
    summary["doc_mrr"] = sum(1 / r["doc_rank"] for r in rows) / n
    summary["avg_expected_chunks_in_top5"] = sum(r["expected_in_top5"] for r in rows) / n
    summary["top1_is_series_entry"] = sum(r["top1_is_series"] for r in rows)
    return summary


def main():
    import chromadb
    import ollama

    chroma_dir = Path(CHROMA_PATH)
    if not chroma_dir.exists():
        print(f"No chroma_db folder in {Path.cwd()}")
        print("Run this from the folder that contains it (~/Downloads).")
        sys.exit(1)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    total = collection.count()
    print(f"Chroma path:     {chroma_dir.resolve()}")
    print(f"Collection size: {total}")
    if total == 0:
        print("Collection is empty. Wrong directory?")
        sys.exit(1)

    questions = json.loads(Path(QUESTIONS_FILE).read_text())
    indexed_sources = {m["source"] for m in collection.get(include=["metadatas"])["metadatas"]}

    scored, controls, problems = [], [], []

    for item in questions:
        question, expected = item["question"], item["expected"]
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=question)
        res = collection.query(query_embeddings=[emb["embedding"]], n_results=total)
        sources = [m["source"] for m in res["metadatas"][0]]
        dists = res["distances"][0]
        top1, top1_dist = sources[0], dists[0]

        if expected is None:
            controls.append({"question": question, "top1": top1, "top1_distance": round(top1_dist, 1)})
            continue

        if expected not in indexed_sources:
            problems.append(f"expected file not in index: {expected}")
            continue

        chunk_rank, doc_rank = rank_sources(sources)[expected]
        scored.append({
            "question": question,
            "expected": expected,
            "chunk_rank": chunk_rank,
            "doc_rank": doc_rank,
            "expected_in_top5": sum(s == expected for s in sources[:5]),
            "top1": top1,
            "top1_distance": round(top1_dist, 1),
            "top1_is_series": bool(SERIES_ENTRY.match(top1)),
        })

    print("\n#   doc_rank  chunk_rank  exp_in_top5  top1")
    for i, r in enumerate(scored, 1):
        flag = "  <- series entry" if r["top1_is_series"] else ""
        print(f"{i:<3} {r['doc_rank']:<9} {r['chunk_rank']:<11} {r['expected_in_top5']:<12} {r['top1']}{flag}")

    print("\nControls (no right answer expected):")
    for c in controls:
        print(f"  {c['top1_distance']:>6}  {c['top1']}   <- {c['question']}")

    for p in problems:
        print(f"PROBLEM: {p}")

    summary = summarize(scored)
    print("\n--- Summary ---")
    for key, value in summary.items():
        print(f"{key:<30} {value:.2f}" if isinstance(value, float) else f"{key:<30} {value}")

    Path(RESULTS_FILE).write_text(json.dumps(
        {"summary": summary, "scored": scored, "controls": controls, "problems": problems}, indent=2))
    print(f"\nSaved {RESULTS_FILE}")


if __name__ == "__main__":
    main()
