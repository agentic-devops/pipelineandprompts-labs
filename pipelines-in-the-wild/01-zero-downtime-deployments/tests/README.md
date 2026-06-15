# Tests

## smoke-test.sh

See `scripts/smoke-test.sh` — tests the live Route endpoint
after deployment. Called by the pipeline automatically.

## traffic-validation.sh

Manual traffic distribution validation. Sends N requests to
the live Route and reports observed blue/green split.

```bash
# 50 requests (default)
./tests/traffic-validation.sh

# 100 requests
./tests/traffic-validation.sh 100
```

Use this to verify HAProxy weight splitting is working as
expected at each canary stage. Legend: `b` = blue, `g` = green,
`e` = error.
