# AI in the Stack #7 — mcp-sre-tools

This folder is a reference pointer, not a fork or a copy. The working implementation lives in its own repository:

**[agentic-devops/mcp-sre-tools](https://github.com/agentic-devops/mcp-sre-tools)**

## What it is

A read-only MCP (Model Context Protocol) server exposing 9 diagnostic tools for OpenShift and Kubernetes cluster inspection — `get_cluster_health`, `get_failing_pods`, `diagnose_crashloop`, `get_cluster_operators`, and others. Supports ARO, ROSA HCP, OSD-GCP, and generic OpenShift/Kubernetes clusters. `READ_ONLY_MODE` is enabled by default; there is no write, patch, or remediation tool in the codebase.

## Why it's referenced here

This repo is the working implementation behind **AI in the Stack #7 — Agentic AI Infrastructure: What It Takes to Do It Safely**, which covers:

- The as-built read-only architecture (this repo)
- A proposed — and deliberately never implemented — maturity-gated remediation flow (Observe → Suggest → Approval → Automatic), designed in response to real platform engineering objections about write access
- What went wrong in private, unpublished testing of write-capable variants (not in this repo), including a failure where the agent correctly diagnosed a problem but recommended a fix built on deprecated OpenShift Logging API knowledge

## Honesty note

The write/patch/upgrade-capable testing discussed in the article was done privately and is **not** part of this public repo. What's here is exactly what shipped: read-only diagnostics, namespace-scoped RBAC, NetworkPolicy-restricted egress. If you're building on this for another article or project, that boundary is the point — don't assume write capability exists just because the article discusses it.

## Linked article

AI in the Stack #7 — Agentic AI Infrastructure: What It Takes to Do It Safely
`pipelineandprompts.com/posts/ai-in-the-stack-07-agentic-ai-infrastructure/` *(slug pending final SEO pass)*

## For future reference by other articles

If you're pulling this repo into a different article's context, note:
- 9 tools, all read-only — verify against `src/mcp/tools.js` directly rather than assuming scope
- `mcp-for-kubernetes` (listed separately in `REPO_INDEX.md`, linked to AI in the Stack #2) is a **different project** — do not conflate the two despite the similar naming
