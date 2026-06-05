# Waybill API

A shipment tracking and waybill management API for logistics operations.
Built with FastAPI + PostgreSQL. Used as the demo application in:

> **Pipelines in the Wild #02 — "Your Pipeline Will Break. Here's How to Make It Fix Itself."**
> pipelineandprompts.dev/pipelines-in-the-wild/02

---

## What it does

Waybill tracks shipments from origin to destination. Each shipment has a waybill number (the document that travels with the consignment), a status, and a timeline of tracking events appended as it moves through the network.

```
POST /shipments                          Create a new shipment
GET  /shipments?status=in_transit        List shipments, filter by status or carrier
GET  /shipments/{waybill_no}             Get full shipment with tracking history
PATCH /shipments/{waybill_no}            Update status
POST /shipments/{waybill_no}/events      Append a tracking event
GET  /shipments/{waybill_no}/events      Get tracking timeline
DELETE /shipments/{waybill_no}           Remove a shipment

GET  /health                             Health check (includes DB status + slot)
GET  /docs                               OpenAPI docs
```

The `/health` endpoint returns the deployment slot (`blue` or `green`) and DB connection state — which makes it meaningful for the blue/green smoke tests in the pipeline.

---

## Quick start (local)

```bash
# Clone and enter
git clone https://github.com/pipelineandprompts-labs/waybill
cd waybill

# Start Postgres
docker compose up postgres -d

# Install deps
pip install -r requirements.txt

# Run migrations
DATABASE_URL=postgresql://waybill:changeme@localhost:5433/waybill alembic upgrade head

# Start the API
DATABASE_URL=postgresql://waybill:changeme@localhost:5433/waybill \
  SLOT=blue APP_VERSION=dev \
  uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API.

---

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD to something other than "changeme"

docker build -t waybill:local .
IMAGE_NAME=waybill BLUE_TAG=local GREEN_TAG=local docker compose up
```

> **Note:** The compose file uses ports `7070` (blue), `9091` (green), and `5433` (postgres host port)
> to avoid conflicts with common local dev tools. See [Port Reference](#port-reference) below.

Both slots start automatically. Blue is at `http://localhost:7070`, green at `http://localhost:9091`.

---

## Run tests

```bash
pip install pytest httpx
pytest tests/ -v
```

12 tests covering create, read, update, delete, tracking events, duplicate detection, and the health endpoint.

---

## Run smoke tests

```bash
# Test blue slot
BLUE_PORT=7070 bash scripts/smoke-test.sh localhost blue

# Test green slot
bash scripts/smoke-test.sh localhost green
```

The smoke test script checks `/health` (HTTP 200, DB connected, correct slot) and `/shipments` (HTTP 200) for the target slot.

---

## Port reference

| Service         | Host port | Container port | Notes                              |
|-----------------|-----------|----------------|------------------------------------|
| waybill-blue    | 7070      | 8000           | Avoids conflict with pgweb (8080)  |
| waybill-green   | 9091      | 8000           | Avoids conflict with pgweb (8081)  |
| waybill-postgres| 5433      | 5432           | Avoids conflict with local Postgres|

These defaults work on a typical Mac dev machine running pgweb and a local Postgres instance.
Override via env vars if your setup differs:

```bash
BLUE_PORT=8080 GREEN_PORT=8081 bash scripts/smoke-test.sh localhost blue
```

---

## Database migrations

Alembic is used for schema management. Migrations run automatically on container start via the `CMD` in the Dockerfile.

To generate a new migration after model changes:

```bash
docker exec waybill-blue alembic revision --autogenerate -m "describe your change"
docker exec waybill-blue alembic upgrade head
```

---

## Repo structure

```
app/
  main.py              FastAPI app + /health endpoint
  db/session.py        SQLAlchemy engine, session, DB health check
  models/shipment.py   Shipment + TrackingEvent ORM models
  routers/shipments.py All shipment endpoints
  schemas/shipment.py  Pydantic request/response schemas

alembic/               Database migrations
tests/                 pytest integration tests (SQLite, no Docker needed)
scripts/
  smoke-test.sh        Blue/green health check (used by CI pipeline)
Dockerfile             Non-root, multi-layer build
docker-compose.yml     Blue + green slots + PostgreSQL
.env.example           Environment variable reference — copy to .env to start
```

---

## Shipment statuses

`pending` → `in_transit` → `at_hub` → `out_for_delivery` → `delivered`

`exception` at any stage (held at customs, damaged, address query).

---

## Example requests

```bash
# Create a shipment
curl -X POST http://localhost:7070/shipments \
  -H "Content-Type: application/json" \
  -d '{
    "waybill_no": "WB-2024-001",
    "origin": "Manchester Warehouse",
    "destination": "London Distribution Centre",
    "carrier": "FastFreight UK",
    "weight_kg": 125.5
  }'

# Add a tracking event
curl -X POST http://localhost:7070/shipments/WB-2024-001/events \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Birmingham Hub",
    "status": "in_transit",
    "note": "Departed sorting facility at 14:32"
  }'

# Get full tracking history
curl http://localhost:7070/shipments/WB-2024-001
```

---

*Part of [pipelineandprompts-labs](https://github.com/pipelineandprompts-labs)*
