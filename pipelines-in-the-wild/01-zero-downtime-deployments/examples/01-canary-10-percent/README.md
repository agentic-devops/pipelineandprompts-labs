# Example 01 — Canary 10% Green / 90% Blue

## What this does

Shifts 10% of live traffic to the green deployment while keeping
90% on blue. This is the first traffic shift stage — the lowest
blast radius canary validation step.

At 10%, roughly 1 in 10 requests hits green. Enough to validate
real traffic behaviour without meaningful user impact if something
is wrong.

## When to use this

- First validation after deploying green successfully
- When you want to observe real traffic behaviour before committing
- In regulated environments where any change needs incremental
  validation with documented checkpoints

## Apply

**Recommended approach** (uses script):

```bash
./scripts/shift-traffic.sh 10
```

**Alternative** (direct manifest apply):

```bash
oc apply -f examples/01-canary-10-percent/haproxy-route-10.yaml
```

The script is recommended because it includes verification that the weights were applied correctly.

## Verify weights applied

```bash
oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='Blue: {.spec.to.weight}% Green: {.spec.alternateBackends[0].weight}%'
```

Expected output:
