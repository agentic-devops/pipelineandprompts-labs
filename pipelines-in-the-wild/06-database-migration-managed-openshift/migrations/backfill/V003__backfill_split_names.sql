-- BACKFILL / DML — split customer_name into first/last.
-- Intentionally no ALTER/DROP. Run as db_dml.
--
-- BATCHED, not a single table-wide UPDATE. This is the actual lesson
-- from the incident this lab is built around: an unbatched UPDATE
-- across every row takes an exclusive lock proportional to table
-- size and holds it for the whole statement. On a small demo table
-- that's invisible. On a high-traffic production table it's exactly
-- what caused the original outage.
--
-- This single execution updates AT MOST :batch_size rows and reports
-- how many it touched. scripts/run-phase.sh calls this repeatedly in
-- a loop (see openshift/jobs/backfill-job.yaml.tpl) until it returns 0,
-- with a short pause between batches so the lock is held briefly and
-- released, not held for the duration of the whole backfill.
SET search_path TO app, public;

WITH batch AS (
  SELECT id
  FROM orders
  WHERE customer_first_name IS NULL OR customer_last_name IS NULL
  ORDER BY id
  LIMIT :batch_size
),
updated AS (
  UPDATE orders o
  SET
    customer_first_name = COALESCE(
      o.customer_first_name,
      NULLIF(split_part(trim(o.customer_name), ' ', 1), '')
    ),
    customer_last_name = COALESCE(
      o.customer_last_name,
      NULLIF(
        CASE
          WHEN position(' ' IN trim(o.customer_name)) = 0 THEN ''
          ELSE substring(trim(o.customer_name) FROM position(' ' IN trim(o.customer_name)) + 1)
        END,
        ''
      )
    )
  FROM batch
  WHERE o.id = batch.id
  RETURNING o.id
)
SELECT count(*) FROM updated;
-- Intentionally nothing else in this file. The batch loop in
-- openshift/jobs/backfill-job.yaml.tpl runs this file repeatedly via
-- `psql -tAc`, reads the printed count back into the shell, and stops
-- when it hits 0. The one-time schema_migrations bookkeeping row for
-- V003 is inserted once by that same job, after the loop completes —
-- see scripts/mark-migration-applied.sql.
