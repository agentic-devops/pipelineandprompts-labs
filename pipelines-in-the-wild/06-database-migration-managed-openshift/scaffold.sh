#!/usr/bin/env bash
# Recreate the database-migration folder tree (empty placeholders).
# Prefer the checked-in content; this exists so you can bootstrap a *new*
# sibling repo with the same layout.
set -euo pipefail

TARGET="${1:-.}"
BASE="${TARGET%/}/database-migration"

mkdir -p \
  "${BASE}/docs" \
  "${BASE}/sql" \
  "${BASE}/migrations/expand" \
  "${BASE}/migrations/backfill" \
  "${BASE}/migrations/contract" \
  "${BASE}/openshift/jobs" \
  "${BASE}/openshift/secrets" \
  "${BASE}/scripts" \
  "${BASE}/apps/order-api"

touch \
  "${BASE}/docs/.gitkeep" \
  "${BASE}/sql/.gitkeep" \
  "${BASE}/migrations/expand/.gitkeep" \
  "${BASE}/migrations/backfill/.gitkeep" \
  "${BASE}/migrations/contract/.gitkeep" \
  "${BASE}/openshift/jobs/.gitkeep" \
  "${BASE}/openshift/secrets/.gitkeep" \
  "${BASE}/scripts/.gitkeep" \
  "${BASE}/apps/order-api/.gitkeep"

cat > "${BASE}/README.md" <<'EOF'
# Database Migration (scaffold)

This is an empty directory tree only. Populate it with:

- `sql/` baseline + roles
- `migrations/{expand,backfill,contract}/`
- `openshift/` SA, Jobs, ESO
- `scripts/deploy.sh` / `run-phase.sh`

For a fully working reference implementation, see the populated version
of this lab at:
pipelineandprompts-labs/pipelines-in-the-wild/06-database-migration-managed-openshift
EOF

echo "Scaffolded ${BASE}"
find "${BASE}" -type d | sort
