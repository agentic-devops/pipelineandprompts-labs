# Swapping LLM Providers Without Rewriting Your Stack

> **Status:** Reference only

Concept notes from **AI in the Stack #5**. No runnable LiteLLM / OpenShift manifests ship in this folder yet — use the article for the full walkthrough until the companion code lands.

## Quick Recap

- Design the control plane before the first prompt — context injection, gateway routing, and post-generation validation catch errors that trial-and-error model switching cannot
- Knowledge gaps are a context problem, not a model problem — inject verified platform context into cheap models instead of paying for expensive models that still guess
- Validate every generated manifest with `oc apply --dry-run=server` before applying — the cluster’s API server catches structural errors that prompt engineering alone will not

## Linked Article

https://pipelineandprompts.com/posts/swapping-llm-providers-without-rewriting-stack/

When this lab graduates to **Full walkthrough**, expect: LiteLLM proxy manifests, ConfigMap-driven model routing, and dry-run validation scripts.
