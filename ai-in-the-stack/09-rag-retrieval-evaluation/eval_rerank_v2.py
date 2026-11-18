"""
Today I Ran, Entry 21: do the re-ranker's ties go away with a finer scale or a
smarter tie-break, and what does re-ranking cost in time?

Variants (all re-score the top 20 chunks per question, same strict labels):
  A  gemma3:12b, 0-10 integer, ties keep embedding order. Same as Entry 20;
     should reproduce its numbers.
  B  gemma3:12b, 0-100 integer, ties keep embedding order.
  C  gemma3:12b, same integer scores as A, but ties are broken by the expected
     score from the model's probabilities over the first digit of its reply
     (higher first), then embedding order. C can only reorder tied chunks.

Timing: every scoring call is wall-clocked. A separate single plain pass (0-10,
no logprobs) is timed for 1B, 3B and 12B so the cost numbers are comparable.

Decided before running: the tie-break rule for C, the 0-100 prompt for B, and
that A must reproduce Entry 20 or the run is reported as a mismatch.

Run from ~/Downloads with the venv's Python:
    ~/mcp-env/bin/python3 eval_rerank_v2.py
"""

import json
import math
import re
import sys
import time
from pathlib import Path

from eval_cap_sweep import CAPS, capped_sources, summarize
from eval_rerank import PROMPT as PROMPT_10, evaluate_set, label, parse_score

EMBED_MODEL = "nomic-embed-text"
CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "today_i_ran_notes"
QUESTIONS_FILE = "eval_questions.json"
RESULTS_FILE = "eval_rerank_v2_results.json"

SCORER = "gemma3:12b"
TIMING_MODELS = ["llama3.2:1b", "llama3.2:3b", "gemma3:12b"]
TOP_N = 20
RUNS = 2
PRINT_CAPS = [None, 1]

PROMPT_100 = PROMPT_10.replace(
    "a single integer from 0 (unrelated) to 10 (directly answers it)",
    "a single integer from 0 (unrelated) to 100 (directly answers it)",
)
assert PROMPT_100 != PROMPT_10


def parse_score_100(text):
    match = re.search(r"\b(100|[1-9]?[0-9])\b", text)
    return int(match.group(1)) if match else None


def expected_first_digit(reply):
    """Expected value over digit tokens at the first digit position of the reply."""
    for pos in reply.get("logprobs") or []:
        if pos["token"].strip().isdigit():
            mass, total = 0.0, 0.0
            for alt in pos.get("top_logprobs") or []:
                tok = alt["token"].strip()
                if len(tok) == 1 and tok.isdigit():
                    p = math.exp(alt["logprob"])
                    mass += p * int(tok)
                    total += p
            return mass / total if total else 0.0
    return 0.0


def call(model, prompt, num_predict, logprobs=False):
    import ollama
    kwargs = {"logprobs": True, "top_logprobs": 10} if logprobs else {}
    t = time.perf_counter()
    r = ollama.generate(model=model, prompt=prompt,
                        options={"temperature": 0, "num_predict": num_predict}, **kwargs)
    return r, time.perf_counter() - t


def order(primary, secondary=None):
    n = len(primary)
    sec = secondary or [0.0] * n
    return sorted(range(n), key=lambda i: (-primary[i], -sec[i], i))


def by_cap(sources, idx_order=None):
    if idx_order is None:
        full = list(sources)
    else:
        full = [sources[i] for i in idx_order] + list(sources[len(idx_order):])
    return {cap: capped_sources(full, cap) for cap in CAPS}


def top_tie(scores, sources):
    """How many chunks share the top score, and how many distinct articles they span."""
    best = max(scores)
    tied = [sources[i] for i, s in enumerate(scores) if s == best]
    return len(tied), len(set(tied))


def main():
    import chromadb
    import ollama

    if not Path(CHROMA_PATH).exists():
        sys.exit(f"No chroma_db in {Path.cwd()}; run from ~/Downloads")
    col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION_NAME)
    total = col.count()
    print(f"Collection size: {total}")
    if total == 0:
        sys.exit("Empty collection")

    qs = [q for q in json.loads(Path(QUESTIONS_FILE).read_text()) if q["expected"]]
    items = []
    for q in qs:
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=q["question"])["embedding"]
        res = col.query(query_embeddings=[emb], n_results=total)
        items.append({"q": q["question"], "exp": {q["expected"]},
                      "sources": [m["source"] for m in res["metadatas"][0]],
                      "docs": res["documents"][0]})

    saved = {"collection": total, "questions": len(items), "variants": {}, "timing": {}}
    rows = {k: {cap: [] for cap in CAPS} for k in ["embedding only", "A 0-10", "B 0-100", "C 0-10 + prob tie-break"]}
    pos = {k: [] for k in rows}
    ties = {k: [] for k in ["A 0-10", "B 0-100"]}
    stable = {"A": 0, "B": 0}
    unparsed = {"A": 0, "B": 0}
    times = {"A+C (logprobs)": [], "B": []}

    ollama.generate(model=SCORER, prompt="Reply with 1.", options={"num_predict": 2})

    for n, it in enumerate(items, 1):
        docs, src = it["docs"][:TOP_N], it["sources"]
        base = by_cap(src)
        for cap in CAPS:
            rows["embedding only"][cap].append(evaluate_set(base[cap], it["exp"]))
        pos["embedding only"].append(evaluate_set(base[None], it["exp"])["position"])

        # A and C: 0-10 with logprobs
        runs_a, runs_e = [], []
        for run in range(RUNS):
            print(f"A/C Q{n} run {run + 1}", flush=True)
            sc, ev = [], []
            for d in docs:
                r, dt = call(SCORER, PROMPT_10.format(question=it["q"], passage=d), 6, logprobs=True)
                times["A+C (logprobs)"].append(dt)
                s = parse_score(r["response"])
                if s is None:
                    unparsed["A"] += 1
                    s = 0
                sc.append(s)
                ev.append(expected_first_digit(r))
            runs_a.append(sc)
            runs_e.append(ev)
        if runs_a[0] == runs_a[1]:
            stable["A"] += 1

        # B: 0-100
        runs_b = []
        for run in range(RUNS):
            print(f"B Q{n} run {run + 1}", flush=True)
            sc = []
            for d in docs:
                r, dt = call(SCORER, PROMPT_100.format(question=it["q"], passage=d), 8)
                times["B"].append(dt)
                s = parse_score_100(r["response"])
                if s is None:
                    unparsed["B"] += 1
                    s = 0
                sc.append(s)
            runs_b.append(sc)
        if runs_b[0] == runs_b[1]:
            stable["B"] += 1

        a, e, b = runs_a[0], runs_e[0], runs_b[0]
        for key, idx in [("A 0-10", order(a)), ("B 0-100", order(b)), ("C 0-10 + prob tie-break", order(a, e))]:
            caps = by_cap(src, idx)
            for cap in CAPS:
                rows[key][cap].append(evaluate_set(caps[cap], it["exp"]))
            pos[key].append(evaluate_set(caps[None], it["exp"])["position"])
        ties["A 0-10"].append(top_tie(a, src[:TOP_N]))
        ties["B 0-100"].append(top_tie(b, src[:TOP_N]))

        saved["variants"][f"Q{n}"] = {
            "question": it["q"], "scores_a": runs_a, "expected_digit": runs_e, "scores_b": runs_b,
            "top3": {k: [(src[i], (a if k != "B" else b)[i]) for i in idx[:3]]
                     for k, idx in [("A", order(a)), ("B", order(b)), ("C", order(a, e))]},
        }

    # timing pass: one plain 0-10 run per model, no logprobs
    for m in TIMING_MODELS:
        ollama.generate(model=m, prompt="Reply with 1.", options={"num_predict": 2})
        per_q = []
        for n, it in enumerate(items, 1):
            print(f"timing {m} Q{n}", flush=True)
            t0 = time.perf_counter()
            for d in it["docs"][:TOP_N]:
                call(m, PROMPT_10.format(question=it["q"], passage=d), 6)
            per_q.append(time.perf_counter() - t0)
        saved["timing"][m] = {"per_question_s": per_q}

    # ---- report ----
    names = list(rows)
    print("\nPosition of labeled article, no cap")
    print("#   " + "".join(f"{k[:14]:>16}" for k in names))
    for i in range(len(items)):
        print(f"{i + 1:<4}" + "".join(f"{pos[k][i]:>16}" for k in names))

    print(f"\n{'setting':<26}{'cap':<6}{'hit@1':>7}{'hit@3':>7}{'hit@5':>7}{'mrr':>7}{'exp_chunks_top5':>17}")
    summ = {}
    for k in names:
        summ[k] = {}
        for cap in CAPS:
            s = summarize(rows[k][cap])
            summ[k][label(cap)] = s
            if cap in PRINT_CAPS:
                print(f"{k:<26}{label(cap):<6}{s['hit@1']:>7.2f}{s['hit@3']:>7.2f}{s['hit@5']:>7.2f}"
                      f"{s['mrr']:>7.2f}{s['exp_chunks_top5']:>17.2f}")

    print("\nTop-score ties (chunks sharing the top score / distinct articles among them)")
    for k, lst in ties.items():
        multi = sum(1 for c, d in lst if d > 1)
        print(f"{k:<10} mean tied chunks {sum(c for c, _ in lst) / len(lst):.2f}; "
              f"questions where the top score spans >1 article: {multi}/{len(lst)}")
        print("   per question: " + " ".join(f"{c}/{d}" for c, d in lst))

    print(f"\nUnparsed replies: A {unparsed['A']}, B {unparsed['B']}")
    print(f"Identical scores across {RUNS} runs: A {stable['A']}/{len(items)}, B {stable['B']}/{len(items)}")

    print("\nTop 3 for questions 6, 7, 10, 12")
    for n in (6, 7, 10, 12):
        for k, top in saved["variants"][f"Q{n}"]["top3"].items():
            print(f"Q{n} {k}: " + ", ".join(f"{s} ({v})" for s, v in top))

    print("\nTiming (seconds)")
    for k, t in times.items():
        print(f"12B {k:<16} per call mean {sum(t) / len(t):.2f}  per question (20 calls) {20 * sum(t) / len(t):.1f}")
    for m, d in saved["timing"].items():
        pq = d["per_question_s"]
        print(f"plain pass {m:<14} per question mean {sum(pq) / len(pq):.1f}  min {min(pq):.1f}  max {max(pq):.1f}  "
              f"total {sum(pq):.0f}")

    saved.update({"summary": summ, "positions": pos, "ties": ties, "stable": stable,
                  "unparsed": unparsed, "call_times": times})
    Path(RESULTS_FILE).write_text(json.dumps(saved, indent=2, default=str))
    print(f"\nSaved {RESULTS_FILE}")


if __name__ == "__main__":
    main()
