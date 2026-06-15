# Flagsmith Setup — zero-downtime-demo

This directory contains manifests for self-hosted Flagsmith running
on ROSA HCP. This is a demo-grade setup using in-cluster PostgreSQL.

> ⚠️ Not for production. In-cluster PostgreSQL has no automated
> backups or high availability. For production use Amazon RDS.
> See docs/flagsmith-setup.md for the RDS migration path.

## Deploy order

Always deploy in this order:

```bash
# 1. Apply PostgreSQL secret — edit password first
oc apply -f flagsmith/postgres/postgres-secret.yaml

# 2. Apply PVC
oc apply -f flagsmith/postgres/postgres-pvc.yaml

# 3. Deploy PostgreSQL
oc apply -f flagsmith/postgres/postgres-deployment.yaml
oc apply -f flagsmith/postgres/postgres-service.yaml

# 4. Wait for PostgreSQL to be ready
oc rollout status deployment/flagsmith-postgres \
  -n zero-downtime-demo

# 5. Apply Flagsmith secret — edit DJANGO_SECRET_KEY first
oc apply -f flagsmith/deployment/flagsmith-secret.yaml

# 6. Deploy Flagsmith
oc apply -f flagsmith/deployment/flagsmith-deployment.yaml
oc apply -f flagsmith/deployment/flagsmith-service.yaml
oc apply -f flagsmith/deployment/flagsmith-route.yaml

# 7. Wait for Flagsmith to be ready
oc rollout status deployment/flagsmith -n zero-downtime-demo

# 8. Get Flagsmith URL
oc get route flagsmith -n zero-downtime-demo
```

## Before applying secrets

Edit these values in the secret files before applying:

**flagsmith/postgres/postgres-secret.yaml**
- `POSTGRES_PASSWORD` — set a real password
- `DATABASE_URL` — update with same password

**flagsmith/deployment/flagsmith-secret.yaml**
- `DJANGO_SECRET_KEY` — generate with:
  `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `DATABASE_URL` — must match postgres-secret password

## After deployment

1. Open Flagsmith UI at the Route URL
2. Create admin account
3. Create project: `pipelineandprompts`
4. Create environment: `production`
5. Create flag: `enable-green-deployment` (default: disabled)
6. Copy environment API key
7. Add to GitHub Secrets as `FLAGSMITH_API_KEY`

See docs/flagsmith-setup.md for detailed screenshots and steps.
