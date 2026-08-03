-- mark-migration-applied.sql
--
-- Run once, after a batch loop (V003 or V004) has finished — i.e.
-- after it has returned 0 in the same run. Not run per-batch, since
-- schema_migrations is bookkeeping about the migration as a whole,
-- not about any individual batch.
--
-- Called with -v version='V003' -v phase='backfill' (etc).
SET search_path TO app, public;

INSERT INTO schema_migrations (version, phase)
VALUES (:'version', :'phase')
ON CONFLICT (version) DO NOTHING;
