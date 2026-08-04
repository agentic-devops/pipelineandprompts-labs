# Database Migration on ROSA / ARO

> **Status:** Full walkthrough

Online schema change demo using **Expand/Contract**, **DDL/DML role split**, **External Secrets Operator (ESO)**, and a **dedicated migrator ServiceAccount**.

Primary target: **ROSA HCP** (in-cluster Postgres for the lab; swap host for RDS when ready). ARO path uses the same Jobs — only the ESO `SecretStore` changes (Azure Key Vault).

## Sample scenario

Legacy `orders` table stores a single `customer_name` and packs line items in a JSONB column. We migrate to first/last name columns and a normalized `order_items` table **without downtime**.

| Phase | Who | What |
|-------|-----|------|
| **Expand** | DDL role | Add nullable columns + `order_items` table |
| **Backfill** | DML role | Split names, explode JSONB → rows |
| **App cutover** | App (dual-write) | Read/write new shape; keep legacy warm |
| **Contract** | DDL role | Drop `customer_name` + `items` after apps stop using them |

Full narrative: [docs/scenario.md](docs/scenario.md) · Architecture: [docs/architecture.md](docs/architecture.md) · Runbook: [docs/runbook.md](docs/runbook.md) · What actually broke: [docs/anti-pattern-what-not-to-do.sql](docs/anti-pattern-what-not-to-do.sql) (read-only — do not run)

## Security model (interview talking points)

1. **Expand/Contract** — never rewrite columns in place under traffic; add → backfill → switch → drop.
2. **DDL ≠ DML** — expand/contract Jobs use `db_ddl`; backfill uses `db_dml` (no `ALTER`/`DROP`).
3. **ESO** — credentials never live in Git; synced into the namespace as Secrets.
4. **Dedicated SA** — `db-migrator` runs Jobs; app Deployment uses `order-api` with DML-only (or tighter) grants.

## Prerequisites

- ROSA HCP (or ARO) with `oc` logged in
- Cluster ability to create projects / deploy workloads
- Optional: External Secrets Operator + cloud secret store for the ESO path

## Quick Start

```bash
git clone https://github.com/agentic-devops/pipelineandprompts-labs.git
cd pipelineandprompts-labs/pipelines-in-the-wild/06-database-migration-managed-openshift
# Follow docs/runbook.md for phase-by-phase apply order
```

## Linked Article

https://pipelineandprompts.com/posts/ — companion to the Pipelines in the Wild series (expand/contract migrations on managed OpenShift).
