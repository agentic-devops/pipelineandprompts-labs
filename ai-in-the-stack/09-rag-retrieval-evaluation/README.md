# 09-rag-retrieval-evaluation

> **Status:** Scripts + results

Companion code for [AI in the Stack #9: RAG Retrieval Evaluation: Prove Your Platform Bot Is Right](https://pipelineandprompts.com/posts/ai-in-the-stack-09-rag-retrieval-evaluation/).

A small, local harness for measuring whether a RAG system retrieves the right source: known-answer questions,
two metrics reported side by side, optional LLM re-ranking, and a check for questions the index can't answer.
Everything runs locally with [Ollama](https://ollama.com) and [Chroma](https://www.trychroma.com). No API keys.

The scripts and results here are the ones behind [Today I Ran](https://pipelineandprompts.com/series/today-i-ran/)
Entries 16–22, run against a 741-chunk index of the blog's own articles.

---

## What's here

| File | What it does | Entry |
|---|---|---|
| `bulk_embed_catalog.py` | Chunks (1,000 chars, 200 overlap) and embeds every `.md` file in `SOURCE_DIR` into the `today_i_ran_notes` collection | [16](https://pipelineandprompts.com/posts/16-bulk-embed-real-catalog/) |
| `eval_retrieval.py` | For each labeled question: rank of the right source among chunks and among documents, and right-source chunks in the top 5 | [18](https://pipelineandprompts.com/posts/18-eval-set-retrieval-scores/) |
| `eval_cap_sweep.py` | Same eval with a per-document cap of none/1/2/3 chunks. Also holds shared helpers | [19](https://pipelineandprompts.com/posts/19-cap-sweep-gains-run-out/) |
| `eval_rerank.py` | Re-scores the top 20 chunks 0–10 with `llama3.2:1b`, `llama3.2:3b` and `gemma3:12b`, then repeats the cap sweep | [20](https://pipelineandprompts.com/posts/20-reranking-top-20-local-models/) |
| `eval_rerank_v2.py` | `gemma3:12b` only: 0–10, 0–100, and 0–10 with ties broken by the model's digit probabilities; times every scoring call | 21 |
| `eval_holdout.py` | Embedding-only vs 12B re-ranking on the original and a held-out question set; prints each question's highest scorer score | 22 |
| `eval_questions.json` | 12 labeled questions + 2 no-answer controls | 18 |
| `eval_questions_v2.json` | Same, with one question accepting a second source (decided before the run that used it) | 22 |
| `eval_questions_holdout.json` | 10 new questions + 1 control, written after the original set | 22 |
| `templates/rosa-questions-template.json` | A starting point for a ROSA assistant, with Classic/HCP divergence questions and a near-miss control. Not used by the scripts | article |
| `results/`, `run-logs/` | Output from the runs reported in the article | |

The only change from the versions that ran: `bulk_embed_catalog.py` reads `SOURCE_DIR` from the environment
instead of a hard-coded path.

---

## Prerequisites

- Python 3.11+ (runs used 3.14)
- Ollama running locally, with the models you need:

```bash
ollama pull nomic-embed-text        # embeddings (all scripts)
ollama pull llama3.2:1b             # eval_rerank.py
ollama pull llama3.2:3b             # eval_rerank.py
ollama pull gemma3:12b              # eval_rerank.py, eval_rerank_v2.py, eval_holdout.py (8 GB)
```

---

## Quick start

```bash
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/ai-in-the-stack/09-rag-retrieval-evaluation

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Build the index from a folder of markdown files (creates ./chroma_db)
SOURCE_DIR=/path/to/your/markdown python bulk_embed_catalog.py

# 2. Retrieval eval, then the cap sweep
python eval_retrieval.py
python eval_cap_sweep.py

# 3. Optional: re-ranking (slow; see cost below)
python eval_rerank_v2.py
python eval_holdout.py C            # or: python eval_holdout.py C holdout
```

All scripts read `./chroma_db` and their question files from the current directory. Run them from this folder.
If a script reports an empty collection, you're in the wrong directory.

To evaluate your own content, replace the question files. Each entry needs `question` and `expected`
(a source file name, or `null` for a control). Optional `also_acceptable` lists other files that count as right.
The `expected` names must match the `source` metadata written by `bulk_embed_catalog.py`, which is the file name.

---

## What the runs showed

Measured on the blog's 741-chunk index. Twelve questions means one question is about 8 points.

| Setup | Right source first | Right source in top 5 | Right-source chunks in top 5 |
|---|---|---|---|
| Embedding only | 10 of 12 | 10 of 12 | 3.17 |
| Cap of 1 chunk per document | 10 of 12 | 12 of 12 | 1.00 |
| `gemma3:12b` re-rank, probability tie-break | 11 of 12 | 12 of 12 | 3.50 |
| Held-out set: embedding only vs 12B re-rank | 9 vs 8 of 10 | 9 vs 9 of 10 | 2.70 vs 3.40 |

- **Report both numbers.** A cap always improves "right source in top 5" and always costs depth.
- **Re-ranking didn't generalise.** It helped on the twelve questions it was developed on and lost one on new questions.
- **No-answer signal.** The 12B scorer's highest chunk score was 7–10 for all 22 answerable questions and 0–3 for all 3 controls.
  Embedding distance can't make that split. Three obvious controls is a small sample; test near-miss controls before relying on it.
- **Cost.** Scoring 20 chunks per question took about 95 s with `gemma3:12b`, 13.6 s with `llama3.2:3b` and 4.4 s with
  `llama3.2:1b` on an Apple M4 Mac mini (16 GB).

---

## Not included

The article recommends decay detection: an owner, last-validated date and Classic/HCP applicability stored on every source,
and dependent questions re-run when a source changes or a release lands. That's a design recommendation. It isn't
implemented or measured here.
