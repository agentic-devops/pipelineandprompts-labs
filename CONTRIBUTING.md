# Contributing

Thanks for your interest in improving these labs. This repo backs the tutorials on
[pipelineandprompts.com](https://pipelineandprompts.com), so the bar for any change is:
**a reader following the blog post should be able to clone, run, and succeed.**

## Before opening a PR

- Run the lab yourself from a clean clone. If a command in the README doesn't work
  verbatim, the README is wrong — fix the README, not just your local setup.
- Check that any `git clone` / `cd` path in your README matches the actual folder name.
- If your lab has tests, run them and include the command in the README.
- If your lab has no working code yet (concepts-only), label it clearly at the top of
  the README (see "Lab maturity labels" below) instead of leaving it ambiguous.

## Lab maturity labels

Every lab README should open with one of these labels directly under the title:

- `Status: Full walkthrough` — working code, tests, and a verified end-to-end setup.
- `Status: Reference only` — explains concepts/architecture, no runnable code yet.
- `Status: Coming soon` — placeholder, not yet published.

## Adding a new lab

1. Create a numbered folder under the right series (`ai-in-the-stack/`,
   `pipelines-in-the-wild/`, or `devops-from-zero/`). Use the next sequential number —
   don't leave gaps; if a planned lab is cut, renumber the ones after it.
2. Include a `README.md` with: a one-line description, the maturity label, prerequisites,
   and a Quick Start block that has been copy-pasted and run from a clean clone.
3. Link the new lab from the series' `README.md` list.
4. If the lab needs secrets or API keys, provide a `.env.example` — never commit real keys.

## Style

- No emoji in headings or bullet lists — keep feature lists in plain bold-lead-in bullets.
- Prefer short, verified command blocks over prose descriptions of what to run.
- Internal process notes (changelogs, "what we updated" summaries) belong in commit
  messages or a `CHANGELOG.md`, not as standalone files like `DOCUMENTATION_UPDATES.md`.

## Reporting a broken tutorial step

Open an issue with: the lab name, the exact command that failed, and the error output.
That's the fastest path to a fix and a blog post correction.
