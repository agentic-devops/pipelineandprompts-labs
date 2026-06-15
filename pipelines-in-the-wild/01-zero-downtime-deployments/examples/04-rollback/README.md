# Example 04 — Emergency Rollback: 100% Blue / 0% Green

## What this does

Immediately shifts all traffic back to blue. Use this when
something goes wrong with green at any stage of the canary process.

This manifest applies the same result as `scripts/rollback.sh`
but as a declarative `oc apply` — useful if you prefer applying
manifests directly over running scripts.

## When to use this

- Green pods are crashing or returning errors
- Response times on green are unacceptable
- Smoke test failed after cutover
- Any situation where you need traffic off green immediately

## Apply — fastest path

```bash
# Option 1: Apply manifest directly
oc apply -f examples/04-rollback/haproxy-route-rollback.yaml

# Option 2: Use the rollback script (recommended — includes verification)
./scripts/rollback.sh

# Option 3: Trigger GitHub Actions rollback workflow
# Actions → Rollback — Shift Traffic to Blue → Run workflow
# (requires reason input for audit trail)
```

## Verify rollback complete

```bash
# Check route weights
oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='Blue: {.spec.to.weight}% Green: {.spec.alternateBackends[0].weight}%'

# Expected: Blue: 100% Green: 0%

# Confirm all traffic on blue
ROUTE=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')

curl -sk https://${ROUTE}/version | grep -o '"colour":"[^"]*"'
# Expected: "colour":"blue"
```

## After rollback — next steps

```bash
# 1. Check what went wrong with green
oc logs -l deployment-colour=green \
  -n zero-downtime-demo \
  --tail=100

# 2. Check green pod events
oc describe pods \
  -l deployment-colour=green \
  -n zero-downtime-demo

# 3. Once fixed, rebuild the green image
#    cd app && ./build-and-push.sh

# 4. Disable and re-enable the Flagsmith gate flag
#    to reset the pipeline gate

# 5. Push a fix commit to main to re-trigger the pipeline
```

## Blast radius of this rollback

- Zero downtime — HAProxy switches weights in-flight
- In-flight requests to green complete normally
- New requests route to blue within seconds of applying
- No pod restarts required
- No DNS changes required
