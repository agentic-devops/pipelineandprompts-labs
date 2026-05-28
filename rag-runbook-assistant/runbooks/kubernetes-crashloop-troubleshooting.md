# Kubernetes CrashLoopBackOff Troubleshooting

## Overview

CrashLoopBackOff is a Kubernetes state indicating a pod is starting, crashing, and restarting in a loop. This runbook covers diagnosis and common resolution steps.

## Symptoms

- Pod status shows `CrashLoopBackOff`
- Application unavailable or partially degraded
- Recent deployment or configuration change
- Logs show repeated initialization failures

## Common Causes

### 1. Application Configuration Issues

**Symptom:** Pod crashes immediately after config change

**Diagnosis:**
```bash
# Check recent pod logs
kubectl logs <pod-name> -n <namespace> --previous

# Check current config
kubectl describe pod <pod-name> -n <namespace>

# Verify ConfigMap/Secret mounts
kubectl get configmap <name> -n <namespace> -o yaml
kubectl get secret <name> -n <namespace> -o yaml
```

**Resolution:**
- Verify all required environment variables are set
- Check ConfigMap and Secret references are correct
- Ensure mounted volumes exist and have correct permissions
- See `config-rollback-procedures.md` for rollback steps

### 2. Resource Limits

**Symptom:** Pod runs for a few seconds then OOMKilled

**Diagnosis:**
```bash
# Check resource usage and limits
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Limits"

# Check node resources
kubectl top nodes
kubectl top pods -n <namespace>
```

**Resolution:**
```yaml
# Update deployment resource limits
resources:
  limits:
    memory: "512Mi"
    cpu: "500m"
  requests:
    memory: "256Mi"
    cpu: "250m"
```

### 3. Failed Health Checks

**Symptom:** Pod starts but Kubernetes kills it due to failing liveness/readiness probes

**Diagnosis:**
```bash
# Check probe configuration
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A 10 "livenessProbe"

# Check probe endpoints
kubectl exec <pod-name> -n <namespace> -- curl localhost:8080/health
```

**Resolution:**
- Adjust `initialDelaySeconds` if application needs more startup time
- Verify health check endpoint is actually responding
- Check `failureThreshold` and `timeoutSeconds` are reasonable

### 4. Missing Dependencies

**Symptom:** Application crashes when trying to connect to database, cache, or external service

**Diagnosis:**
```bash
# Check logs for connection errors
kubectl logs <pod-name> -n <namespace> --previous | grep -i "connection\|error\|failed"

# Verify service DNS resolution
kubectl exec <pod-name> -n <namespace> -- nslookup <service-name>

# Check service endpoints
kubectl get endpoints <service-name> -n <namespace>
```

**Resolution:**
- Verify dependent services are running
- Check service names and namespaces are correct
- Ensure network policies allow traffic
- Verify credentials/connection strings are correct

### 5. Container Image Issues

**Symptom:** ImagePullBackOff or image runs but immediately crashes

**Diagnosis:**
```bash
# Check image pull status
kubectl describe pod <pod-name> -n <namespace> | grep -A 5 "Events"

# Verify image exists and is accessible
kubectl get pod <pod-name> -n <namespace> -o jsonpath='{.spec.containers[*].image}'

# Check image pull secrets
kubectl get secrets -n <namespace>
```

**Resolution:**
- Verify image tag is correct
- Check image registry credentials
- Pull image locally to test: `docker pull <image>`
- Ensure image architecture matches node (amd64 vs arm64)

## Step-by-Step Diagnosis

1. **Get pod status:**
   ```bash
   kubectl get pods -n <namespace>
   kubectl describe pod <pod-name> -n <namespace>
   ```

2. **Check recent logs:**
   ```bash
   kubectl logs <pod-name> -n <namespace> --previous --tail=100
   ```

3. **Review recent changes:**
   ```bash
   kubectl rollout history deployment/<deployment-name> -n <namespace>
   kubectl diff -f <deployment-file>
   ```

4. **Check events:**
   ```bash
   kubectl get events -n <namespace> --sort-by='.lastTimestamp' | grep <pod-name>
   ```

5. **Verify configuration:**
   ```bash
   kubectl get pod <pod-name> -n <namespace> -o yaml > pod-dump.yaml
   # Review pod-dump.yaml for misconfigurations
   ```

## Quick Fixes

### Immediate Rollback
If the issue appeared after a deployment:
```bash
kubectl rollout undo deployment/<deployment-name> -n <namespace>
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

### Force Pod Restart
If the issue is transient:
```bash
kubectl delete pod <pod-name> -n <namespace>
# Or scale down and up
kubectl scale deployment/<deployment-name> --replicas=0 -n <namespace>
kubectl scale deployment/<deployment-name> --replicas=3 -n <namespace>
```

### Disable Probes Temporarily
For diagnosis only - **never leave this in production:**
```bash
kubectl patch deployment <deployment-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","livenessProbe":null}]}}}}'
```

## Prevention

- Always test configuration changes in staging first
- Use `kubectl apply --dry-run=client` before applying
- Monitor resource usage trends
- Set appropriate resource requests and limits
- Implement gradual rollouts (canary/blue-green)
- Ensure health check endpoints are robust
- Version ConfigMaps and Secrets

## Related Runbooks

- `config-rollback-procedures.md` - How to safely rollback configuration changes
- `resource-quota-management.md` - Managing namespace resource quotas
- `deployment-best-practices.md` - Deployment strategies and testing

## Escalation

If none of these steps resolve the issue:

1. Gather full diagnostics: `kubectl cluster-info dump > cluster-dump.txt`
2. Check #platform-support Slack channel
3. Page on-call platform engineer if production critical
4. Open incident ticket with logs and timeline
