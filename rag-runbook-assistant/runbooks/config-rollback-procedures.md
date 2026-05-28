# Configuration Rollback Procedures

## Overview

This runbook covers safe rollback procedures for configuration changes in production environments, including Kubernetes ConfigMaps, Secrets, environment variables, and application configuration files.

## When to Rollback

Rollback immediately if:
- Application is in CrashLoopBackOff after config change
- Error rates spike above 5% after deployment
- Critical functionality is broken
- Data corruption is detected
- Security vulnerability is introduced

Do NOT rollback if:
- Issue is isolated to non-critical features
- Forward fix is faster and safer
- Rollback would cause data loss
- Multiple changes were deployed (coordinate first)

## Pre-Rollback Checklist

Before rolling back any configuration:

1. **Verify the problem is configuration-related:**
   ```bash
   # Compare current vs previous config
   kubectl diff -f <config-file>
   
   # Check application logs for config errors
   kubectl logs <pod-name> -n <namespace> | grep -i "config\|environment\|missing"
   ```

2. **Document current state:**
   ```bash
   # Save current configuration
   kubectl get configmap <name> -n <namespace> -o yaml > current-config-backup.yaml
   kubectl get secret <name> -n <namespace> -o yaml > current-secret-backup.yaml
   ```

3. **Notify stakeholders:**
   - Post in #incidents Slack channel
   - Alert team that deployed the change
   - Update status page if customer-facing

4. **Identify rollback target:**
   ```bash
   # View configuration history
   kubectl rollout history deployment/<name> -n <namespace>
   
   # View specific revision
   kubectl rollout history deployment/<name> -n <namespace> --revision=<n>
   ```

## Rollback Procedures by Type

### Kubernetes Deployment Rollback

**Use when:** Configuration is embedded in deployment spec (env vars, volume mounts)

```bash
# View rollout history
kubectl rollout history deployment/<deployment-name> -n <namespace>

# Rollback to previous revision
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# Rollback to specific revision
kubectl rollout undo deployment/<deployment-name> -n <namespace> --to-revision=<n>

# Monitor rollback progress
kubectl rollout status deployment/<deployment-name> -n <namespace>

# Verify pods are healthy
kubectl get pods -n <namespace> -l app=<app-label>
kubectl logs <pod-name> -n <namespace> --tail=50
```

**Verification:**
```bash
# Check application health endpoint
kubectl exec <pod-name> -n <namespace> -- curl localhost:8080/health

# Verify error rates returned to normal
# Check monitoring dashboard or:
kubectl top pods -n <namespace>
```

### ConfigMap Rollback

**Use when:** Application reads from Kubernetes ConfigMap

**Important:** ConfigMap changes don't automatically restart pods. You must trigger a rollout.

```bash
# Get previous ConfigMap version from git or backup
git show HEAD~1:k8s/configmap.yaml > previous-config.yaml

# Apply previous version
kubectl apply -f previous-config.yaml

# Force pod restart to pick up config
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# Monitor restart
kubectl rollout status deployment/<deployment-name> -n <namespace>

# Verify config was applied
kubectl exec <pod-name> -n <namespace> -- cat /etc/config/<key>
```

**Alternative - Manual Edit:**
```bash
# Edit ConfigMap directly (use with caution)
kubectl edit configmap <name> -n <namespace>

# Restart pods
kubectl rollout restart deployment/<deployment-name> -n <namespace>
```

### Secret Rollback

**Use when:** Credentials, certificates, or sensitive config changed

```bash
# Retrieve previous secret from backup or vault
# Secrets should be stored in a secret manager (Vault, AWS Secrets Manager)

# Update secret
kubectl apply -f previous-secret.yaml

# Or update specific key
kubectl create secret generic <name> \
  --from-literal=<key>=<value> \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart deployment
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# Verify (be careful not to expose secrets in logs)
kubectl get secret <name> -n <namespace> -o jsonpath='{.data}' | jq 'keys'
```

**Security Note:** Never log secret values. Verify by checking application behavior, not secret contents.

### Environment Variable Rollback

**Use when:** Config is passed as environment variables in deployment

```bash
# View current environment
kubectl get deployment <name> -n <namespace> -o jsonpath='{.spec.template.spec.containers[0].env}' | jq

# Edit deployment
kubectl edit deployment <name> -n <namespace>
# Manually change env values back to previous state

# Or use patch for specific env var
kubectl patch deployment <name> -n <namespace> -p '
{
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "<container-name>",
            "env": [
              {
                "name": "<ENV_VAR>",
                "value": "<previous-value>"
              }
            ]
          }
        ]
      }
    }
  }
}'

# Kubernetes will automatically trigger rollout
kubectl rollout status deployment/<name> -n <namespace>
```

### Application Config File Rollback

**Use when:** Configuration files are baked into container image or mounted from external source

**Option 1 - Rollback to previous image:**
```bash
# Find previous working image
kubectl rollout history deployment/<name> -n <namespace> --revision=<previous>

# Update to previous image tag
kubectl set image deployment/<name> <container-name>=<image>:<previous-tag> -n <namespace>

# Monitor
kubectl rollout status deployment/<name> -n <namespace>
```

**Option 2 - Mount corrected config:**
```bash
# Update ConfigMap with corrected config file
kubectl create configmap <name> --from-file=config.yaml=<previous-config.yaml> --dry-run=client -o yaml | kubectl apply -f -

# Restart to pick up change
kubectl rollout restart deployment/<name> -n <namespace>
```

## Post-Rollback Steps

1. **Verify service health:**
   ```bash
   # Check pod status
   kubectl get pods -n <namespace>
   
   # Check logs for errors
   kubectl logs -l app=<app-label> -n <namespace> --tail=100
   
   # Test critical endpoints
   curl https://<service-url>/health
   curl https://<service-url>/api/critical-endpoint
   ```

2. **Monitor metrics:**
   - Error rates should return to baseline
   - Latency should stabilize
   - Resource usage should be normal
   - Check Grafana/Datadog dashboards

3. **Verify data integrity:**
   - Run smoke tests
   - Check recent transactions
   - Verify no data corruption occurred

4. **Document the incident:**
   ```markdown
   ## Incident Summary
   - **Time:** [timestamp]
   - **Issue:** [description]
   - **Root Cause:** [config change that caused issue]
   - **Resolution:** Rolled back [component] to revision [n]
   - **Impact:** [duration, affected users]
   - **Prevention:** [what to do differently next time]
   ```

5. **Update configuration management:**
   - Commit working configuration to git
   - Update configuration documentation
   - Tag the working version

6. **Close the incident:**
   - Update status page
   - Notify stakeholders in #incidents
   - Schedule post-mortem if needed

## Rollback Failure Recovery

If rollback itself fails:

1. **Don't panic - you have options:**
   ```bash
   # Check why rollback failed
   kubectl get events -n <namespace> --sort-by='.lastTimestamp'
   
   # Check pod status
   kubectl describe pod <pod-name> -n <namespace>
   ```

2. **Common rollback failures:**

   **ImagePullError on old image:**
   ```bash
   # Image may have been deleted from registry
   # Deploy last known-good config with current image
   kubectl set image deployment/<name> <container>=<current-working-image>
   kubectl apply -f <last-known-good-config.yaml>
   ```

   **Resource conflict:**
   ```bash
   # Another change was applied during rollback
   # Get current state
   kubectl get deployment <name> -n <namespace> -o yaml > current.yaml
   # Manually merge with desired state and reapply
   ```

   **Rollback stuck:**
   ```bash
   # Force new rollout
   kubectl patch deployment <name> -n <namespace> -p "{\"spec\":{\"template\":{\"metadata\":{\"annotations\":{\"force-restart\":\"$(date +%s)\"}}}}}"
   ```

3. **Nuclear option - full redeploy:**
   ```bash
   # Scale down
   kubectl scale deployment <name> --replicas=0 -n <namespace>
   
   # Delete deployment
   kubectl delete deployment <name> -n <namespace>
   
   # Reapply from known-good config
   kubectl apply -f <known-good-deployment.yaml>
   ```

## Prevention Best Practices

1. **Always test config changes in staging first**
2. **Use GitOps - version control all configs**
3. **Implement gradual rollouts:**
   ```yaml
   strategy:
     type: RollingUpdate
     rollingUpdate:
       maxSurge: 1
       maxUnavailable: 0
   ```
4. **Use config validation:**
   ```bash
   kubectl apply --dry-run=client -f config.yaml
   kubectl diff -f config.yaml
   ```
5. **Monitor during deployments:**
   - Watch error rates for 10 minutes after change
   - Set up alerts for config-related errors
   - Have rollback plan ready before deploying

6. **Version your ConfigMaps and Secrets:**
   ```yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: app-config-v2  # Include version in name
   ```

7. **Automate rollback triggers:**
   - Set up automatic rollback on high error rates
   - Use Argo Rollouts or Flagger for progressive delivery

## Related Runbooks

- `kubernetes-crashloop-troubleshooting.md` - Diagnosing pod crashes
- `deployment-best-practices.md` - How to deploy safely
- `incident-response-playbook.md` - General incident handling

## Emergency Contacts

- **Platform Team:** #platform-support Slack
- **On-call Engineer:** PagerDuty escalation
- **Security Issues:** security@company.com
