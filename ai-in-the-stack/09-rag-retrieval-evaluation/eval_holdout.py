"""
Today I Ran, Entry 22: does the 12B re-ranker's gain hold on questions it has never
seen, and what changes once one original question gets a second acceptable article?

Sets:
  original  eval_questions_v2.json  (Entry 18's 12 questions; Q7 now lists AI in the
            Stack 07 as also acceptable, decided by reading before this run)
  holdout   eval_questions_holdout.json (10 new questions written from article
            content, plus one no-answer control)

For each set: embedding only vs gemma3:12b re-ranking the top 20 with the chosen
Entry 21 variant (A = 0-10, B = 0-100, C = 0-10 + probability tie-break).
Strict = expected only; lenient = expected or also_acceptable.

    ~/mcp-env/bin/python3 eval_holdout.py C
"""

import json
import sys
from pathlib import Path

from eval_cap_sweep import CAPS, summarize
from eval_rerank import PROMPT as PROMPT_10, evaluate_set, label, parse_score
from eval_rerank_v2 import PROMPT_100, by_cap, call, expected_first_digit, order, parse_score_100

CHROMA_PATH = "./chroma_db"
COLLECTION = "today_i_ran_notes"
SCORER = "gemma3:12b"
TOP_N = 20
SETS = {"original": "eval_questions_v2.json", "holdout": "eval_questions_holdout.json"}


def score(question, docs, variant):
    prim, sec = [], []
    for d in docs:
        if variant == "B":
            r, _ = call(SCORER, PROMPT_100.format(question=question, passage=d), 8)
            s = parse_score_100(r["response"])
            prim.append(s if s is not None else 0)
            sec.append(0.0)
        else:
            r, _ = call(SCORER, PROMPT_10.format(question=question, passage=d), 6, logprobs=(variant == "C"))
            s = parse_score(r["response"])
            prim.append(s if s is not None else 0)
            sec.append(expected_first_digit(r) if variant == "C" else 0.0)
    return prim, sec


def main():
    import chromadb
    import ollama

    variant = sys.argv[1] if len(sys.argv) > 1 else "C"
    assert variant in "ABC"
    col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION)
    total = col.count()
    print(f"Collection size: {total}; scorer {SCORER} variant {variant}")
    indexed = {m["source"] for m in col.get(include=["metadatas"])["metadatas"]}
    saved = {"variant": variant, "collection": total, "sets": {}}

    only = sys.argv[2] if len(sys.argv) > 2 else None
    for set_name, path in SETS.items():
        if only and set_name != only:
            continue
        qs = json.loads(Path(path).read_text())
        rows = {(s, v): {c: [] for c in CAPS} for s in ("embedding only", "12B") for v in ("strict", "lenient")}
        per_q = []
        for n, q in enumerate(qs, 1):
            emb = ollama.embeddings(model="nomic-embed-text", prompt=q["question"])["embedding"]
            res = col.query(query_embeddings=[emb], n_results=total)
            src, docs, dist = [m["source"] for m in res["metadatas"][0]], res["documents"][0], res["distances"][0]
            print(f"{set_name} Q{n}", flush=True)
            prim, sec = score(q["question"], docs[:TOP_N], variant)
            idx = order(prim, sec)
            rec = {"question": q["question"], "expected": q["expected"],
                   "also": q.get("also_acceptable", []),
                   "embed_top3": list(zip(src[:3], [round(x, 1) for x in dist[:3]])),
                   "rerank_top3": [(src[i], prim[i]) for i in idx[:3]],
                   "max_score": max(prim)}
            if q["expected"] is None:
                per_q.append(rec)
                continue
            missing = {q["expected"], *rec["also"]} - indexed
            if missing:
                rec["problem"] = f"not indexed: {sorted(missing)}"
                per_q.append(rec)
                continue
            strict, lenient = {q["expected"]}, {q["expected"], *rec["also"]}
            for setting, ordering in (("embedding only", None), ("12B", idx)):
                caps = by_cap(src, ordering)
                for v, acc in (("strict", strict), ("lenient", lenient)):
                    for c in CAPS:
                        rows[(setting, v)][c].append(evaluate_set(caps[c], acc))
                rec[f"pos_{setting}"] = {v: evaluate_set(caps[None], acc)["position"]
                                         for v, acc in (("strict", strict), ("lenient", lenient))}
            per_q.append(rec)

        print(f"\n=== {set_name} ({path}) ===")
        print(f"{'#':<4}{'embed strict':>13}{'embed len.':>11}{'12B strict':>11}{'12B len.':>9}  expected")
        for n, r in enumerate(per_q, 1):
            if "pos_12B" in r:
                e, m = r["pos_embedding only"], r["pos_12B"]
                print(f"{n:<4}{e['strict']:>13}{e['lenient']:>11}{m['strict']:>11}{m['lenient']:>9}  {r['expected']}")
            else:
                print(f"{n:<4}{'-':>13}{'':>11}{'':>11}{'':>9}  {r.get('problem', 'control (no answer)')}")
        print(f"\n{'setting':<16}{'labels':<9}{'cap':<6}{'hit@1':>7}{'hit@3':>7}{'hit@5':>7}{'mrr':>7}{'exp_chunks_top5':>17}")
        summ = {}
        for (s, v), by in rows.items():
            for c in (None, 1):
                if not by[c]:
                    continue
                x = summarize(by[c])
                summ[f"{s}|{v}|{label(c)}"] = x
                print(f"{s:<16}{v:<9}{label(c):<6}{x['hit@1']:>7.2f}{x['hit@3']:>7.2f}{x['hit@5']:>7.2f}"
                      f"{x['mrr']:>7.2f}{x['exp_chunks_top5']:>17.2f}")
        print("\nTop 3 (embedding distance / 12B score) for misses and controls")
        for n, r in enumerate(per_q, 1):
            if "pos_12B" not in r or r["pos_12B"]["strict"] > 1 or r["pos_embedding only"]["strict"] > 1:
                print(f"Q{n} {r['question'][:70]}")
                print("   embed:", r["embed_top3"])
                print("   12B:  ", r["rerank_top3"])
        print("\nHighest 12B score per question:", [r["max_score"] for r in per_q])
        saved["sets"][set_name] = {"per_question": per_q, "summary": summ}

    Path(f"eval_holdout_results_{variant}{'_' + only if only else ''}.json").write_text(json.dumps(saved, indent=2, default=str))
    print(f"\nSaved eval_holdout_results_{variant}.json")


if __name__ == "__main__":
    main()
