"""
Integration tests for the Waybill API.
Run: pytest tests/ -v
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite:///./test_waybill.db"
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_shipment(client):
    r = client.post("/shipments", json={
        "waybill_no": "WB-2024-001", "origin": "Manchester Warehouse",
        "destination": "London Distribution Centre",
        "carrier": "FastFreight UK", "weight_kg": 125.5,
    })
    assert r.status_code == 201
    return r.json()

def test_health_ok(client):
    with patch("app.main.check_db_connection", return_value=True):
        r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert "slot" in data

def test_health_db_unreachable(client):
    with patch("app.main.check_db_connection", return_value=False):
        r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "degraded"

def test_create_shipment(client):
    r = client.post("/shipments", json={
        "waybill_no": "WB-2024-002", "origin": "Birmingham Hub",
        "destination": "Edinburgh Depot", "carrier": "NorthStar Logistics", "weight_kg": 42.0,
    })
    assert r.status_code == 201
    assert r.json()["status"] == "pending"

def test_duplicate_409(client, sample_shipment):
    r = client.post("/shipments", json={
        "waybill_no": "WB-2024-001", "origin": "Leeds", "destination": "Bristol",
        "carrier": "AnyCarrier", "weight_kg": 10.0,
    })
    assert r.status_code == 409

def test_invalid_waybill_no_422(client):
    r = client.post("/shipments", json={
        "waybill_no": "wb 2024 001",  # spaces not allowed
        "origin": "Manchester", "destination": "London",
        "carrier": "FastFreight", "weight_kg": 10.0,
    })
    assert r.status_code == 422

def test_get_shipment(client, sample_shipment):
    r = client.get("/shipments/WB-2024-001")
    assert r.status_code == 200
    assert r.json()["origin"] == "Manchester Warehouse"

def test_get_404(client):
    assert client.get("/shipments/WB-NOTEXIST").status_code == 404

def test_list_and_filter(client, sample_shipment):
    assert len(client.get("/shipments").json()) == 1
    assert len(client.get("/shipments?status=pending").json()) == 1
    assert len(client.get("/shipments?status=delivered").json()) == 0

def test_update_status(client, sample_shipment):
    r = client.patch("/shipments/WB-2024-001", json={"status": "in_transit"})
    assert r.status_code == 200
    assert r.json()["status"] == "in_transit"

def test_tracking_event(client, sample_shipment):
    r = client.post("/shipments/WB-2024-001/events", json={
        "location": "Birmingham Hub", "status": "in_transit",
        "note": "Departed sorting facility at 14:32",
    })
    assert r.status_code == 201
    assert client.get("/shipments/WB-2024-001").json()["status"] == "in_transit"

def test_get_events(client, sample_shipment):
    client.post("/shipments/WB-2024-001/events", json={"location": "Hub A", "status": "in_transit"})
    client.post("/shipments/WB-2024-001/events", json={"location": "Hub B", "status": "at_hub"})
    assert len(client.get("/shipments/WB-2024-001/events").json()) == 2

def test_delete(client, sample_shipment):
    assert client.delete("/shipments/WB-2024-001").status_code == 204
    assert client.get("/shipments/WB-2024-001").status_code == 404
