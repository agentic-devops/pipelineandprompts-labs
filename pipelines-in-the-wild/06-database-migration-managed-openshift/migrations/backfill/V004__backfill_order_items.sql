-- BACKFILL / DML — explode JSONB items into order_items.
--
-- Batched by parent order, not by row, for the same reason V003 is
-- batched: expanding every order's JSONB array in one INSERT...SELECT
-- holds locks across the whole table for however long the full
-- expansion takes. Batching by order id keeps each transaction short.
--
-- Run repeatedly by the loop in openshift/jobs/backfill-job.yaml.tpl
-- until it returns 0. See V003 for the same pattern.
SET search_path TO app, public;

WITH candidate_orders AS (
  SELECT o.id
  FROM orders o
  WHERE jsonb_array_length(o.items) > 0
    AND NOT EXISTS (
      SELECT 1 FROM order_items oi WHERE oi.order_id = o.id
    )
  ORDER BY o.id
  LIMIT :batch_size
),
inserted AS (
  INSERT INTO order_items (order_id, sku, quantity, price_cents)
  SELECT
    o.id,
    elem->>'sku',
    (elem->>'qty')::integer,
    (elem->>'price_cents')::integer
  FROM orders o
  JOIN candidate_orders co ON co.id = o.id
  CROSS JOIN LATERAL jsonb_array_elements(o.items) AS elem
  ON CONFLICT (order_id, sku) DO UPDATE
  SET
    quantity    = EXCLUDED.quantity,
    price_cents = EXCLUDED.price_cents
  RETURNING 1
)
SELECT count(*) FROM inserted;
-- Bookkeeping row for V004 is inserted once, after the loop completes —
-- see scripts/mark-migration-applied.sql.
