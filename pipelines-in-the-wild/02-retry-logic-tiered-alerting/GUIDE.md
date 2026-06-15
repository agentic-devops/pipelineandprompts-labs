# Waybill — Local Dev Setup Guide

A complete walkthrough for getting the Waybill blue/green stack running locally on a Mac,
from zero to both slots passing smoke tests.

Written for beginners. Every command is explained.

---

## What you'll have at the end

- PostgreSQL running in Docker
- Two instances of the Waybill API running side-by-side (blue on port 7070, green on 9091)
- Both slots passing a full smoke test (health, DB, slot identity, response time, API)
- A clear mental model of blue/green deployments

---

## Prerequisites

You need these installed before starting:

| Tool | Why | Install |
|------|-----|---------|
| Docker Desktop | Runs all containers | https://www.docker.com/products/docker-desktop |
| Python 3.11+ | Runs tests locally | https://www.python.org/downloads/ |
| Git | Clones the repo | Pre-installed on Mac; or `brew install git` |

Verify everything works:

```zsh
docker --version      # Docker version 25.x or newer
python3 --version     # Python 3.11 or newer
git --version         # git version 2.x
```

---

## Step 1 — Clone the repo

```zsh
git clone https://github.com/pipelineandprompts-labs/waybill
cd waybill
```

Everything from here on assumes you're inside the `waybill/` directory.

---

## Step 2 — Create your .env file

The `.env` file holds credentials and config. Never commit it — it's in `.gitignore`.
A safe template is provided:

```zsh
cp .env.example .env
```

Open `.env` and review it. For local dev the defaults are fine — `changeme` as the password
is acceptable because the database port (`5433`) is only accessible from your own machine.

> **Production rule:** always set `POSTGRES_PASSWORD` to a strong random value in production.
> Use `openssl rand -hex 32` to generate one.

---

## Step 3 — Understand the port layout

Before starting anything, know which ports are used and why they're not the obvious defaults:

| Service | Host port | Why not the default? |
|---------|-----------|----------------------|
| waybill-blue | **7070** | Port 8080 is used by pgweb on a typical Mac dev setup |
| waybill-green | **9091** | Port 8081 is used by pgweb portfolio instance |
| postgres | **5433** | Port 5432 is used by a local Postgres installation |

Inside Docker, containers talk to each other on standard ports (app on 8000, postgres on 5432).
The host ports above are only used when you access them from your Mac.

Check what's already using a port (useful for debugging):

```zsh
lsof -i :7070      # should return nothing if the port is free
```

---

## Step 4 — Build the image

The `docker-compose.yml` doesn't have a `build:` key — it expects a pre-built image.
Build it manually first:

```zsh
docker build -t waybill:local .
```

This builds from the `Dockerfile` in the current directory and tags the result as `waybill:local`.

> **Why no `build:` in compose?**
> In production, blue and green run different pre-built image versions (e.g. `v1.2.0` and `v1.3.0`).
> Separating build from compose reflects that production pattern.

---

## Step 5 — Start the stack

```zsh
IMAGE_NAME=waybill BLUE_TAG=local GREEN_TAG=local docker compose up
```

Breaking this down:
- `IMAGE_NAME=waybill` — the base image name (becomes `waybill:local`)
- `BLUE_TAG=local` — tag for the blue slot
- `GREEN_TAG=local` — tag for the green slot
- `docker compose up` — starts all services defined in `docker-compose.yml`

You should see:

```
✔ Container waybill-postgres  Healthy
✔ Container waybill-blue      Started
✔ Container waybill-green     Started
```

The postgres healthcheck runs first. Blue and green only start once postgres is healthy
(`depends_on: condition: service_healthy`).

---

## Step 6 — Run the migrations

The Dockerfile's `CMD` runs `alembic upgrade head` on startup, which creates the database
schema automatically. Verify the tables exist:

```zsh
docker exec waybill-postgres psql -U waybill -d waybill -c "\dt"
```

Expected output:

```
           List of relations
 Schema |      Name       | Type  |  Owner
--------+-----------------+-------+---------
 public | shipments       | table | waybill
 public | tracking_events | table | waybill
```

If you see "no relations found", the migration didn't run. Trigger it manually:

```zsh
docker exec waybill-blue alembic upgrade head
```

---

## Step 7 — Run the smoke tests

The smoke test script checks five things for each slot:
1. `/health` returns HTTP 200
2. The DB reports as connected
3. The slot name matches (`blue` or `green`)
4. Response time is under 2000ms
5. `/shipments` returns HTTP 200

Run both slots:

```zsh
bash scripts/smoke-test.sh localhost blue
bash scripts/smoke-test.sh localhost green
```

All green output looks like this:

```
[smoke] Testing blue slot at http://localhost:7070
[smoke] ✅ /health → 200
[smoke] ✅ DB connected
[smoke] ✅ Slot: blue
[smoke] ✅ Response time: 5ms
[smoke] ✅ /shipments → 200
[smoke] ✅ All checks passed for blue slot
```

---

## Step 8 — Run the unit tests

The unit tests use SQLite (no Docker needed) and cover the full CRUD lifecycle:

```zsh
pip install pytest httpx
pytest tests/ -v
```

Expected: 12 tests, all passing.

---

## Step 9 — Try the API

Both slots are live. Blue is on 7070, green on 9091. The API is identical — slot identity
shows in `/health` and nowhere else.

**Interactive docs:**
- Blue: http://localhost:7070/docs
- Green: http://localhost:9091/docs

**Create a shipment:**

```zsh
curl -X POST http://localhost:7070/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "waybill_no": "WB-2024-001",
    "origin": "Manchester Warehouse",
    "destination": "London Distribution Centre",
    "carrier": "FastFreight UK",
    "weight_kg": 125.5
  }'
```

**Add a tracking event:**

```zsh
curl -X POST http://localhost:7070/shipments/WB-2024-001/events \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Birmingham Hub",
    "status": "in_transit",
    "note": "Departed sorting facility at 14:32"
  }'
```

**Get the full tracking history:**

```zsh
curl http://localhost:7070/shipments/WB-2024-001
```

**Verify blue and green share the same database** — create via blue, read via green:

```zsh
curl -s http://localhost:9091/shipments/WB-2024-001 | python3 -m json.tool
```

You'll see the same shipment. Both slots point to the same PostgreSQL database, which is the
foundation of blue/green deployments — traffic can be switched without data loss.

---

## Troubleshooting

### "pull access denied for waybill"

Docker is trying to pull the image from a registry. Build it locally first:

```zsh
docker build -t waybill:local .
```

### "Bind for 0.0.0.0:XXXX failed: port is already allocated"

Something else owns that port. Find it:

```zsh
lsof -i :7070
```

Kill the container holding it, or change the port in `docker-compose.yml`.

See what all your containers are currently using:

```zsh
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### "BASE: unbound variable" in smoke test

You're missing the slot argument. Both arguments are required:

```zsh
bash scripts/smoke-test.sh localhost blue   # ✅
bash scripts/smoke-test.sh localhost        # ❌ missing slot
```

### "relation shipments does not exist"

Migrations haven't run yet. Run them manually:

```zsh
docker exec waybill-blue alembic upgrade head
```

### Smoke test fails with HTTP 404 on /health

Check what port the container is actually on — it may differ from the smoke test default:

```zsh
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

Override the port without editing the script:

```zsh
BLUE_PORT=8080 bash scripts/smoke-test.sh localhost blue
```

### `ss` command not found

`ss` is Linux-only. On macOS use:

```zsh
netstat -an | grep LISTEN    # all listeners
lsof -i :8080                # specific port
```

---

## Stopping the stack

```zsh
docker compose down           # stops containers, keeps the postgres volume
docker compose down -v        # stops containers AND deletes the database volume
```

Use `-v` when you want a completely clean slate.

---

## What's next

Once both slots are green, the natural progression is:

1. **Integration tests** — full CRUD lifecycle: create, update, delete, verify persistence
2. **Slot isolation test** — write via blue, read via green, confirm shared DB
3. **Load test** — `hey -n 1000 -c 50 http://localhost:7070/shipments`
4. **Rollback test** — break green intentionally, cut back to blue, verify zero data loss
5. **CI integration** — wire `smoke-test.sh` into GitHub Actions

---

*Part of [pipelineandprompts-labs](https://github.com/pipelineandprompts-labs)*
