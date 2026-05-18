# Flagsmith Setup Guide

Detailed setup guide for self-hosted Flagsmith on ROSA HCP.
Follow this after deploying the Flagsmith manifests in
`flagsmith/`.

---

## Step 1 — Update secrets before deploying

### Generate a real Django secret key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copy the output. Edit `flagsmith/deployment/flagsmith-secret.yaml`:

```yaml
stringData:
  DJANGO_SECRET_KEY: "<paste generated key here>"
  DATABASE_URL: "postgresql://flagsmith:<your-password>@flagsmith-postgres:5432/flagsmith"
```

Edit `flagsmith/postgres/postgres-secret.yaml`:

```yaml
stringData:
  POSTGRES_PASSWORD: "<your-password>"
  DATABASE_URL: "postgresql://flagsmith:<your-password>@flagsmith-postgres:5432/flagsmith"
```

The password in both files must match exactly.

> ⚠️ Do not commit real secrets to Git. These files are in
> `.gitignore` — verify before pushing:
> `git status flagsmith/`

---

## Step 2 — Deploy in order

```bash
# PostgreSQL first
oc apply -f flagsmith/postgres/postgres-secret.yaml
oc apply -f flagsmith/postgres/postgres-pvc.yaml
oc apply -f flagsmith/postgres/postgres-deployment.yaml
oc apply -f flagsmith/postgres/postgres-service.yaml

# Wait for PostgreSQL
oc rollout status deployment/flagsmith-postgres \
  -n zero-downtime-demo --timeout=120s

# Flagsmith second
oc apply -f flagsmith/deployment/flagsmith-secret.yaml
oc apply -f flagsmith/deployment/flagsmith-deployment.yaml
oc apply -f flagsmith/deployment/flagsmith-service.yaml
oc apply -f flagsmith/deployment/flagsmith-route.yaml

# Wait for Flagsmith
oc rollout status deployment/flagsmith \
  -n zero-downtime-demo --timeout=180s
```

---

## Step 3 — Get Flagsmith URL

```bash
FLAGSMITH_HOST=$(oc get route flagsmith \
  -n zero-downtime-demo \
  -o jsonpath='{.spec.host}')

echo "Flagsmith UI: https://${FLAGSMITH_HOST}"
echo "Flagsmith API: https://${FLAGSMITH_HOST}/api/v1"
```

---

## Step 4 — Initial Flagsmith configuration

Open `https://<flagsmith-host>` in your browser.

### Create admin account

1. Click **Create Account**
2. Enter email and password
3. This becomes the admin account — use a real email
4. Click **Create Account**

### Create organisation

1. Organisation name: `pipelineandprompts`
2. Click **Create**

### Create project

1. Click **Create Project**
2. Name: `pipelineandprompts`
3. Click **Create Project**

### Create environments

Flagsmith creates a `Development` environment by default.
Create a `Production` environment:

1. Click **Environments** → **Create Environment**
2. Name: `production`
3. Click **Create**

### Create the deployment gate flag

1. Go to the **production** environment
2. Click **Features** → **Create Feature**
3. Configure:
   - Name: `enable-green-deployment`
   - Description: `Gates traffic shifting to green deployment`
   - Type: **Feature flag** (boolean)
   - Default state: **Disabled** (toggle off)
4. Click **Create Feature**

---

## Step 5 — Get the API key

1. Go to production environment
2. Click **Settings** → **Keys**
3. Copy the **Client-side environment key**
   (starts with `ser.` or similar)

This key goes into GitHub Secrets as `FLAGSMITH_API_KEY`.

The API URL goes into GitHub Secrets as `FLAGSMITH_URL`:
