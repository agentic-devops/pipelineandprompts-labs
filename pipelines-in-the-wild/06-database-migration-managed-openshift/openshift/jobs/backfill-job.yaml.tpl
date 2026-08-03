# Template applied by scripts/run-phase.sh for the backfill phase only.
# Do not apply directly — use ./scripts/run-phase.sh backfill
#
# Unlike expand/contract (single-shot DDL via migrate-job.yaml.tpl),
# backfill runs each SQL file in a loop, in small batches, pausing
# between batches, until each file reports 0 rows touched. This is
# the actual pattern from the incident this lab is built around —
# see migrations/backfill/*.sql for why.
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate-backfill
  namespace: db-migration
  labels:
    app.kubernetes.io/name: db-migrate
    app.kubernetes.io/component: backfill
    migration.phase: backfill
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels:
        app.kubernetes.io/name: db-migrate
        migration.phase: backfill
    spec:
      serviceAccountName: db-migrator
      restartPolicy: Never
      containers:
        - name: psql
          image: postgres:16-alpine
          env:
            - name: PGOPTIONS
              value: "-c search_path=app,public"
            - name: BATCH_SIZE
              value: "500"
            - name: BATCH_PAUSE_SECONDS
              value: "0.25"
          envFrom:
            - secretRef:
                name: SECRET_NAME
          volumeMounts:
            - name: sql
              mountPath: /migrations
              readOnly: true
            - name: scripts
              mountPath: /scripts
              readOnly: true
          command:
            - /bin/sh
            - -ec
            - |
              echo "Phase=backfill user=${PGUSER} host=${PGHOST} batch_size=${BATCH_SIZE}"

              run_batched() {
                # $1 = version (e.g. V003), $2 = phase label, $3 = sql file
                local version="$1" phase="$2" file="$3" total=0 n
                echo "==> $(basename "$file") — batching in groups of ${BATCH_SIZE}"
                while :; do
                  n="$(psql -tA -v batch_size="${BATCH_SIZE}" -f "$file" | tail -n1)"
                  if [ -z "$n" ]; then
                    echo "    got no output from batch query — stopping (check the SQL file)"
                    exit 1
                  fi
                  total=$((total + n))
                  echo "    batch touched ${n} rows (running total: ${total})"
                  if [ "$n" -eq 0 ]; then
                    break
                  fi
                  sleep "${BATCH_PAUSE_SECONDS}"
                done
                echo "    ${file}: done, ${total} rows total"
                psql -v version="${version}" -v phase="${phase}" \
                  -f /scripts/mark-migration-applied.sql
              }

              run_batched "V003" "backfill" /migrations/V003__backfill_split_names.sql
              run_batched "V004" "backfill" /migrations/V004__backfill_order_items.sql

              echo "Backfill complete"
              psql -c "SELECT version, phase, applied_at, applied_by FROM app.schema_migrations ORDER BY applied_at;"
      volumes:
        - name: sql
          configMap:
            name: migration-sql-backfill
        - name: scripts
          configMap:
            name: migration-scripts
