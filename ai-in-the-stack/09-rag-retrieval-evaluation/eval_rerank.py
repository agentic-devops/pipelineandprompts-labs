"""
Today I Ran — re-score the top 20 chunks with a local model, then re-run the cap sweep

For each labeled question in eval_questions.json:
  1. Take the 20 chunks the embedding search ranks highest.
  2. Ask a local model to rate each chunk 0-10 for how well it answers the question.
  3. Re-sort those 20 by rating (ties keep their embedding order); chunks 21+ stay
     below them in their original order.
  4. Score the result the same way Entry 19 did, at caps of none, 1, 2 and 3.

Models are tried one at a time (so Ollama isn't swapping them in and out), and every
model is run RUNS times so the script can report whether its ranking changes between
identical runs (Entry 13 saw a 1B model give different answers to the same prompt).

Labels: each question needs "expected". It may also have "also_acceptable": a list of
other files that would count as a right answer. If any question has it, the script
prints strict results (expected only) and lenient results (expected or acceptable)
side by side. Decide those lists by reading the articles, not by which labels raise
the score.

Needs eval_cap_sweep.py in the same folder. Run from the folder that contains
chroma_db (~/Downloads), using the venv's Python:
    ~/mcp-env/bin/python3 eval_rerank.py
"""

import json
import re
import sys
from pathlib import Path

from eval_cap_sweep import CAPS, SERIES_ENTRY, capped_sources, summarize

EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "today_i_ran_notes"
QUESTIONS_FILE = "eval_questions.json"
RESULTS_FILE = "eval_rerank_results.json"

MODELS = ["llama3.2:1b", "llama3.2:3b", "gemma3:12b"]
TOP_N = 20
RUNS = 2
PRINT_CAPS = [None, 1]

PROMPT = (
    "You are judging search results for a technical blog.\n\n"
    "Question: {question}\n\n"
    "Passage:\n{passage}\n\n"
    "How well does this passage help answer the question? Reply with a single "
    "integer from 0 (unrelated) to 10 (directly answers it). Reply with the number only."
)


def label(cap):
    return "none" if cap is None else str(cap)


def parse_score(text):
    """First whole number 0-10 in the model's reply, or None."""
    match = re.search(r"\b(10|[0-9])\b", text)
    return int(match.group(1)) if match else None


def score_passages(generate, model, question, passages):
    """Rate each passage 0-10. Unparseable replies score 0 and are counted."""
    scores, unparsed = [], 0
    for passage in passages:
        reply = generate(
            model=model,
            prompt=PROMPT.format(question=question, passage=passage),
            options={"temperature": 0, "num_predict": 6},
        )
        score = parse_score(reply["response"])
        if score is None:
            unparsed += 1
            score = 0
        scores.append(score)
    return scores, unparsed


def rerank_order(scores):
    """Indices 0..len-1 sorted by score, best first; ties keep embedding order."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))


def lists_by_cap(sources, scores=None):
    """Chunk sources in embedding order -> {cap: capped list}.
    With scores, the first len(scores) chunks are re-sorted by score first."""
    if scores is None:
        full = list(sources)
    else:
        n = len(scores)
        full = [sources[i] for i in rerank_order(scores)] + list(sources[n:])
    return {cap: capped_sources(full, cap) for cap in CAPS}


def evaluate_set(capped, acceptable):
    top5 = capped[:5]
    positions = [i for i, s in enumerate(capped, 1) if s in acceptable]
    return {
        "position": positions[0],
        "expected_in_top5": sum(s in acceptable for s in top5),
        "distinct_in_top5": len(set(top5)),
        "series_in_top5": sum(bool(SERIES_ENTRY.match(s)) for s in top5),
    }


def print_summary(title, table):
    print(f"\n{title}")
    print(f"{'setting':<22}{'cap':<6}{'hit@1':>7}{'hit@3':>7}{'hit@5':>7}{'mrr':>7}{'exp_chunks_top5':>17}")
    for name, by_cap in table.items():
        for cap in PRINT_CAPS:
            s = by_cap[label(cap)]
            print(f"{name:<22}{label(cap):<6}{s['hit@1']:>7.2f}{s['hit@3']:>7.2f}{s['hit@5']:>7.2f}"
                  f"{s['mrr']:>7.2f}{s['exp_chunks_top5']:>17.2f}")


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

    questions = [q for q in json.loads(Path(QUESTIONS_FILE).read_text()) if q["expected"] is not None]
    indexed = {m["source"] for m in collection.get(include=["metadatas"])["metadatas"]}
    problems = []
    items = []
    for q in questions:
        acceptable = {q["expected"], *q.get("also_acceptable", [])}
        missing = acceptable - indexed
        if missing:
            problems.append(f"not in index: {sorted(missing)}")
            continue
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=q["question"])
        res = collection.query(query_embeddings=[emb["embedding"]], n_results=total)
        items.append({
            "question": q["question"],
            "strict": {q["expected"]},
            "lenient": acceptable,
            "sources": [m["source"] for m in res["metadatas"][0]],
            "docs": res["documents"][0],
        })

    has_lenient = any(it["lenient"] != it["strict"] for it in items)
    variants = ["strict", "lenient"] if has_lenient else ["strict"]

    usable = []
    for model in MODELS:
        try:
            ollama.generate(model=model, prompt="Reply with the number 1.", options={"num_predict": 4})
            usable.append(model)
        except Exception as e:
            print(f"SKIP model {model}: {e}")
    if not usable:
        print("No scoring models available.")
        sys.exit(1)

    # tables[variant][setting][cap_label] = summary; positions = per-question, cap none
    tables = {v: {} for v in variants}
    positions = {"embedding only": []}
    top_picks = {}  # model -> list of (question number, top 3 (source, score)) for questions that missed at baseline
    diagnostics = {}
    saved = {"models": {}, "problems": problems}

    for v in variants:
        tables[v]["embedding only"] = {
            label(cap): summarize([evaluate_set(lists_by_cap(it["sources"])[cap], it[v]) for it in items])
            for cap in CAPS
        }
    for it in items:
        positions["embedding only"].append(evaluate_set(lists_by_cap(it["sources"])[None], it["strict"])["position"])

    for model in usable:
        positions[model] = []
        top_picks[model] = []
        unparsed_total, flat, stable = 0, 0, 0
        per_variant_rows = {v: {cap: [] for cap in CAPS} for v in variants}
        saved["models"][model] = []

        for n, it in enumerate(items, 1):
            run_scores, run_top5 = [], []
            for run in range(RUNS):
                print(f"{model}: question {n}/{len(items)}, run {run + 1}/{RUNS}", flush=True)
                scores, unparsed = score_passages(ollama.generate, model, it["question"], it["docs"][:TOP_N])
                unparsed_total += unparsed
                run_scores.append(scores)
                run_top5.append(lists_by_cap(it["sources"], scores)[None][:5])

            scores = run_scores[0]  # run 1 is the one scored; the rest only check stability
            if len(set(scores)) == 1:
                flat += 1
            if RUNS > 1 and all(t == run_top5[0] for t in run_top5):
                stable += 1

            by_cap = lists_by_cap(it["sources"], scores)
            for v in variants:
                for cap in CAPS:
                    per_variant_rows[v][cap].append(evaluate_set(by_cap[cap], it[v]))
            positions[model].append(evaluate_set(by_cap[None], it["strict"])["position"])

            base_pos = positions["embedding only"][n - 1]
            if base_pos > 1 or positions[model][-1] > 1:
                order = rerank_order(scores)[:3]
                top_picks[model].append((n, [(it["sources"][i], scores[i]) for i in order]))

            saved["models"][model].append({
                "question": it["question"],
                "scores": run_scores,
                "top5_none": run_top5[0],
                "position_by_cap": {label(c): evaluate_set(by_cap[c], it["strict"])["position"] for c in CAPS},
            })

        for v in variants:
            tables[v][model] = {label(cap): summarize(per_variant_rows[v][cap]) for cap in CAPS}
        diagnostics[model] = {"unparsed_replies": unparsed_total, "questions_all_same_score": flat,
                              "questions_same_top5_across_runs": stable}

    print("\nPosition of the labeled article, no cap (embedding only vs re-ranked)")
    names = ["embedding only"] + usable
    print("#    " + "".join(f"{name:>16}" for name in names))
    for i in range(len(items)):
        print(f"{i + 1:<5}" + "".join(f"{positions[name][i]:>16}" for name in names))

    print_summary("Strict labels (expected article only)", tables["strict"])
    if has_lenient:
        print_summary("Lenient labels (expected or also_acceptable; widened after Entry 18's results)", tables["lenient"])

    print("\nScorer diagnostics")
    for model, d in diagnostics.items():
        print(f"{model:<14} unparsed replies: {d['unparsed_replies']:<5} "
              f"questions where all 20 chunks got the same score: {d['questions_all_same_score']:<3} "
              f"questions with the same top 5 across {RUNS} runs: {d['questions_same_top5_across_runs']}/{len(items)}")

    print("\nTop 3 after re-ranking, for questions that missed before or after")
    for model, picks in top_picks.items():
        for n, top in picks:
            shown = ", ".join(f"{s} ({score})" for s, score in top)
            print(f"{model:<14} Q{n}: {shown}")

    for p in problems:
        print(f"PROBLEM: {p}")

    saved["tables"] = tables
    saved["diagnostics"] = diagnostics
    Path(RESULTS_FILE).write_text(json.dumps(saved, indent=2))
    print(f"\nSaved {RESULTS_FILE}")


if __name__ == "__main__":
    main()
