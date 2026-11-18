"""
Today I Ran — Block 1: sweep the per-article cap on the same eval set

Entry 18 compared "no cap" with "cap of 1 per article". This runs the same
questions at cap = none, 1, 2 and 3, and reports for each setting:

  hit@1/3/5      : is the labeled article's first chunk in the top 1/3/5 of the
                   capped list?
  mrr            : mean of 1 / (position of that first chunk)
  exp_chunks_top5: chunks from the labeled article in the top 5 (depth)
  distinct_top5  : different articles in the top 5 (variety)
  series_top5    : chunks from "Today I Ran" entries (01-..., 18-...) in the top 5

Labels come from eval_questions.json, unchanged from Entry 18. Questions with
"expected": null are controls and are skipped here.

Built-in check against Entry 18: the "none" row should show hit@1/3/5 of
0.83 / 0.83 / 0.83 and exp_chunks_top5 of 3.17, and the "1" row should show
hit@3 0.92, hit@5 1.00, mrr 0.88 and exp_chunks_top5 1.00. If they don't, the
collection or the questions changed since that run.

Run from the folder that contains chroma_db (~/Downloads):
    python3 eval_cap_sweep.py
"""

import json
import re
import sys
from pathlib import Path

EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "today_i_ran_notes"
QUESTIONS_FILE = "eval_questions.json"
RESULTS_FILE = "eval_cap_sweep_results.json"
CAPS = [None, 1, 2, 3]

SERIES_ENTRY = re.compile(r"^\d{2}-")


def capped_sources(sources, cap):
    """Keep at most `cap` chunks per article, preserving rank order.
    cap=None keeps everything."""
    if cap is None:
        return list(sources)
    counts, out = {}, []
    for source in sources:
        seen = counts.get(source, 0)
        if seen < cap:
            out.append(source)
            counts[source] = seen + 1
    return out


def evaluate(capped, expected):
    top5 = capped[:5]
    return {
        "position": capped.index(expected) + 1,
        "expected_in_top5": top5.count(expected),
        "distinct_in_top5": len(set(top5)),
        "series_in_top5": sum(bool(SERIES_ENTRY.match(s)) for s in top5),
    }


def summarize(rows):
    n = len(rows)
    if n == 0:
        return {}
    summary = {}
    for k in (1, 3, 5):
        summary[f"hit@{k}"] = sum(r["position"] <= k for r in rows) / n
    summary["mrr"] = sum(1 / r["position"] for r in rows) / n
    summary["exp_chunks_top5"] = sum(r["expected_in_top5"] for r in rows) / n
    summary["distinct_top5"] = sum(r["distinct_in_top5"] for r in rows) / n
    summary["series_top5"] = sum(r["series_in_top5"] for r in rows) / n
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

    per_question = []  # (question, {cap: metrics})
    problems = []

    for item in questions:
        expected = item["expected"]
        if expected is None:
            continue
        if expected not in indexed_sources:
            problems.append(f"expected file not in index: {expected}")
            continue
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=item["question"])
        res = collection.query(query_embeddings=[emb["embedding"]], n_results=total)
        sources = [m["source"] for m in res["metadatas"][0]]
        per_question.append((item["question"], {cap: evaluate(capped_sources(sources, cap), expected) for cap in CAPS}))

    label = lambda cap: "none" if cap is None else str(cap)

    print("\nPer question  (position of labeled article | its chunks in top 5)")
    print("#    " + "  ".join(f"{label(c):>5}" for c in CAPS) + "   |   " + "  ".join(f"{label(c):>5}" for c in CAPS))
    for i, (_, by_cap) in enumerate(per_question, 1):
        pos = "  ".join(f"{by_cap[c]['position']:>5}" for c in CAPS)
        dep = "  ".join(f"{by_cap[c]['expected_in_top5']:>5}" for c in CAPS)
        print(f"{i:<4} {pos}   |   {dep}")

    print("\nSummary by cap")
    header = f"{'cap':<6}{'hit@1':>7}{'hit@3':>7}{'hit@5':>7}{'mrr':>7}{'exp_chunks_top5':>17}{'distinct_top5':>15}{'series_top5':>13}"
    print(header)
    results = {}
    for cap in CAPS:
        s = summarize([by_cap[cap] for _, by_cap in per_question])
        results[label(cap)] = s
        print(f"{label(cap):<6}{s['hit@1']:>7.2f}{s['hit@3']:>7.2f}{s['hit@5']:>7.2f}{s['mrr']:>7.2f}"
              f"{s['exp_chunks_top5']:>17.2f}{s['distinct_top5']:>15.2f}{s['series_top5']:>13.2f}")

    for p in problems:
        print(f"PROBLEM: {p}")

    Path(RESULTS_FILE).write_text(json.dumps(
        {"summary_by_cap": results,
         "per_question": [{"question": q, "by_cap": {label(c): v for c, v in by_cap.items()}}
                          for q, by_cap in per_question],
         "problems": problems}, indent=2))
    print(f"\nSaved {RESULTS_FILE}")


if __name__ == "__main__":
    main()
