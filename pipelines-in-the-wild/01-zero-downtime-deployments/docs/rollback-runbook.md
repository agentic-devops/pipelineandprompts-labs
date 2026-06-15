# Rollback Runbook — Zero-Downtime Blue/Green

This runbook is written for 2am incidents. Short sentences.
No assumed context. Every command is copy-pasteable.

---

## Situation: Something is wrong with green. Shift all traffic to blue.

### Option A — GitHub Actions (preferred, audit trail)

1. Go to your GitHub repository
2. Click **Actions**
3. Click **Rollback — Shift Traffic to Blue**
4. Click **Run workflow**
5. Enter a reason (required — this is your audit trail)
6. Select **Disable Flagsmith flag: true**
7. Click **Run workflow**
8. Watch the workflow — it completes in under 2 minutes

Verify:
```bash
ROUTE=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')
curl -sk https://${ROUTE}/version | grep colour
# Expected: "colour":"blue"
```

---

### Option B — Script (fastest, no GitHub required)

```bash
# From the repo root
./scripts/rollback.sh

# To also disable the Flagsmith gate flag
./scripts/rollback.sh --disable-flag
```

Completes in under 30 seconds.

---

### Option C — Direct manifest apply (no scripts, no GitHub)

```bash
oc apply \
  -f examples/04-rollback/haproxy-route-rollback.yaml \
  -n zero-downtime-demo
```

---

### Option D — Manual oc patch (absolute minimum, nothing else available)

```bash
oc patch route nodejs-zero-downtime \
  -n zero-downtime-demo \
  --type=json \
  --patch='[
    {"op":"replace","path":"/spec/to/weight","value":100},
    {"op":"replace","path":"/spec/alternateBackends/0/weight","value":0}
  ]'
```

---

## Verify rollback complete (all options)

```bash
# Check route weights
oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='Blue: {.spec.to.weight} Green: {.spec.alternateBackends[0].weight}'
# Expected: Blue: 100 Green: 0

# Check blue pods are healthy
oc get pods -n zero-downtime-demo \
  -l deployment-colour=blue

# Hit the live endpoint
ROUTE=$(oc get route nodejs-zero-downtime \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')
curl -sk https://${ROUTE}/version
# Expected: {"colour":"blue",...}
```

---

## After rollback — investigate green

```bash
# Check green pod logs
oc logs \
  -l deployment-colour=green \
  -n zero-downtime-demo \
  --tail=100

# Check green pod events
oc describe pods \
  -l deployment-colour=green \
  -n zero-downtime-demo

# Check green pod resource usage
oc top pods \
  -n zero-downtime-demo \
  -l deployment-colour=green

# Check recent events in namespace
oc get events \
  -n zero-downtime-demo \
  --sort-by='.lastTimestamp' \
  | tail -20
```

---

## Disable Flagsmith gate manually

If you did not use `--disable-flag` during rollback:

1. Open Flagsmith UI:
```bash
   oc get route flagsmith \
     -n zero-downtime-demo \
     -o jsonpath='{.spec.host}'
```
2. Go to: production environment
3. Find: `enable-green-deployment`
4. Toggle: **OFF**

This prevents the pipeline from attempting another traffic
shift if it is re-triggered before the green issue is resolved.

---

## Re-enable after fix

Once green is fixed and a new image is pushed:

1. Enable `enable-green-deployment` flag in Flagsmith
2. Push a commit to `main` to re-trigger the pipeline
3. Pipeline will deploy the new green and begin canary process

---

## Escalation

If rollback does not resolve the issue and blue is also
behaving unexpectedly:

```bash
# Check cluster nodes
oc get nodes

# Check namespace resource quotas
oc describe resourcequota -n zero-downtime-demo

# Check recent cluster events
oc get events -A \
  --sort-by='.lastTimestamp' \
  | tail -30
```

Contact your ROSA support channel if cluster-level issues
are suspected.
