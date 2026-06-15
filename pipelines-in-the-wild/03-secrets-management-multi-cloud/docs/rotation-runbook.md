# Rotation Runbook — Secrets Management Multi-Cloud

> Fill in the `[OWNER]` and `[CONTACT]` placeholders for your environment before storing this in your team's runbook system.

## Credential: Registry Pull Secret

| Field | Value |
|---|---|
| Secret name (K8s) | `registry-pull-secret` |
| ExternalSecret | `registry-pull-secret` |
| Central store path | `prod/registry/pull-secret` |
| Namespaces affected | `prod` |
| Workloads affected | `[LIST DEPLOYMENTS USING imagePullSecrets]` |

---

## Rotation Approval

| Role | Name | Contact | Authority |
|---|---|---|---|
| Rotation approver (prod) | `[OWNER]` | `[CONTACT]` | Approves credential change in central store |
| Platform engineer on-call | `[OWNER]` | `[CONTACT]` | Executes rollout restart after confirmed sync |
| Application owner | `[OWNER]` | `[CONTACT]` | Confirms application health post-restart |
| Security liaison | `[OWNER]` | `[CONTACT]` | Reviews audit logs for anomalous access |

**Approval required before rotation?** `[YES/NO — if YES, link to change management ticket template]`

---

## Pre-Rotation Checklist

- [ ] Change ticket approved (if required)
- [ ] New credential tested in dev namespace
- [ ] ESO operator healthy (`oc get pods -n external-secrets`)
- [ ] ExternalSecret status `SecretSynced` in target namespace
- [ ] On-call engineer available for rollout restart
- [ ] Rollback plan documented (see below)

---

## Rotation Procedure

### Step 1 — Rotate in central store

Rotate the credential in your provider:

- **AWS Secrets Manager:** Update secret value via console or CLI
- **Azure Key Vault:** Create new secret version
- **HashiCorp Vault:** Write new version to KV path

**Executed by:** `[OWNER]`  
**Timestamp:** `_______________`

### Step 2 — Confirm ESO sync

```bash
# Watch ExternalSecret status until SecretSynced
oc get externalsecret registry-pull-secret -n prod -w

# Verify READY=True and STATUS=SecretSynced
oc get externalsecret registry-pull-secret -n prod

# Check ESO operator logs if sync fails
oc logs -n external-secrets \
  -l app.kubernetes.io/name=external-secrets --tail=50
```

**Maximum sync lag:** `refreshInterval` on ExternalSecret (default: 1h — reduce for time-sensitive credentials)

**Sync confirmed by:** `[OWNER]`  
**Timestamp:** `_______________`

### Step 3 — Restart affected workloads

> Pods use credentials mounted at startup. Sync alone does not update running pods.

```bash
# Restart each affected deployment
oc rollout restart deployment/<APP_NAME> -n prod

# Wait for rollout to complete
oc rollout status deployment/<APP_NAME> -n prod
```

**Restart executed by:** `[OWNER]`  
**Timestamp:** `_______________`

### Step 4 — Confirm health

```bash
# Verify pods are running
oc get pods -n prod -l app=<APP_LABEL>

# Verify image pull succeeded (no ImagePullBackOff)
oc describe pod -l app=<APP_LABEL> -n prod | grep -A5 "Events:"

# Application health check
curl -f https://<APP_HEALTH_ENDPOINT>/health
```

**Health confirmed by:** `[OWNER]`  
**Timestamp:** `_______________`

---

## Rollback Procedure

If rotation introduces a bad credential:

```bash
# 1. Roll back deployment first — buys time
oc rollout undo deployment/<APP_NAME> -n prod
oc rollout status deployment/<APP_NAME> -n prod

# 2. Restore previous credential value in central store
#    (provider-specific — see provider docs)

# 3. Wait for ESO re-sync
oc get externalsecret registry-pull-secret -n prod -w

# 4. Trigger new rollout with corrected credential
oc rollout restart deployment/<APP_NAME> -n prod
```

> `oc rollout undo` rolls back deployment config, not the secret value. If the vault value is wrong, fix the vault first.

---

## Escalation Path

| Severity | Condition | Escalate to | Response time |
|---|---|---|---|
| P3 | Sync lag > refreshInterval | Platform on-call | 30 min |
| P2 | ExternalSecret `SecretSyncedError` | Platform lead + Security | 15 min |
| P1 | Production ImagePullBackOff after rotation | Incident commander + all owners | Immediate |

**Incident bridge:** `[SLACK CHANNEL / PAGERDUTY SERVICE / TEAMS CHANNEL]`

**After-hours contact tree:**

1. Platform on-call → `[CONTACT]`
2. Application owner → `[CONTACT]`
3. Security liaison → `[CONTACT]`
4. Engineering manager → `[CONTACT]`

---

## Post-Rotation

- [ ] Audit log reviewed for anomalous reads during rotation window
- [ ] Change ticket closed with rotation timestamp
- [ ] Runbook updated if procedure deviated
- [ ] Lessons learned captured (if incident occurred)

---

## Monitoring

Wire these alerts before relying on this runbook:

| Signal | Source | Threshold |
|---|---|---|
| `externalsecret_sync_calls_error` | ESO metrics | > 0 for 5 min |
| ExternalSecret not Ready | `oc get externalsecret` | READY=False for 10 min |
| ImagePullBackOff | Pod events | Any pod in prod namespace |
