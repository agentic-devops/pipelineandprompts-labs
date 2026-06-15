# Example 03 — Full Cutover: 100% Green / 0% Blue

## What this does

Shifts all traffic to green. Blue receives zero traffic but
remains running — it is your instant rollback path.

Do not scale down or delete the blue deployment after cutover.
Blue stays running until the next deployment cycle confirms
green is stable in production.

## When to use this

- After green has passed both the 10% and 50% canary stages
- When smoke tests confirm green is healthy
- When the Flagsmith gate flag is enabled and the pipeline
  has completed validation

## Apply

```bash
oc apply -f examples/03-full-cutover/haproxy-route-100.yaml
```

## Verify full cutover

```bash
# Verify route weights
oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='Blue: {.spec.to.weight}% Green: {.spec.alternateBackends[0].weight}%'

# Expected: Blue: 0% Green: 100%

# Confirm all requests hit green
ROUTE=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')

for i in $(seq 1 10); do
  curl -sk https://${ROUTE}/version \
    | grep -o '"colour":"[^"]*"'
done

# Expected: "colour":"green" every time
```

## Run full smoke test

```bash
export ROUTE_URL=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')

./scripts/smoke-test.sh green
```

## After cutover — what to do with blue

Blue keeps running. Do not delete it. At the next deployment cycle:

1. The pipeline deploys a new green image
2. Green passes validation
3. Traffic shifts to new green
4. Old blue (now the previous green) gets replaced

This is the natural rotation. Blue is always the previous stable
version — your rollback safety net.

## Rollback from full cutover

Even at 100% green, rollback to blue takes under 30 seconds:

```bash
./scripts/rollback.sh
```

Or trigger the rollback workflow in GitHub Actions:
Actions → Rollback — Shift Traffic to Blue → Run workflow
