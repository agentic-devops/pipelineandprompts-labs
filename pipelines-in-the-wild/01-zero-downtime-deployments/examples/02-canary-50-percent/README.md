# Example 02 — Canary 50% Green / 50% Blue

## What this does

Equal traffic split between blue and green. This is the mid-point
confidence check — green is handling real production load at scale
before full cutover is committed.

At 50/50, any performance difference between blue and green becomes
clearly visible. This is the stage where latency regressions,
memory leaks, or connection pool issues surface under real load.

## When to use this

- After green has passed the 10% validation stage
- Before committing to full cutover
- When you want a direct performance comparison between
  blue and green under identical load conditions

## Apply

```bash
oc apply -f examples/02-canary-50-percent/haproxy-route-50.yaml
```

## Verify weights applied

```bash
oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='Blue: {.spec.to.weight}% Green: {.spec.alternateBackends[0].weight}%'
```

Expected output:
