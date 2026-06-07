from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.shipment import ShipmentStatus


# ── Tracking events ───────────────────────────────────────────────────────────

class TrackingEventCreate(BaseModel):
    location:   str             = Field(..., min_length=2, max_length=100)
    status:     ShipmentStatus
    note:       Optional[str]   = Field(None, max_length=500)
    occurred_at: Optional[datetime] = None


class TrackingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          UUID
    location:    str
    status:      ShipmentStatus
    note:        Optional[str]
    occurred_at: datetime


# ── Shipments ─────────────────────────────────────────────────────────────────

class ShipmentCreate(BaseModel):
    waybill_no:  str   = Field(..., min_length=6, max_length=20,
                               pattern=r"^[A-Z0-9\-]+$",
                               description="Uppercase alphanumeric, e.g. WB-2024-001")
    origin:      str   = Field(..., min_length=2, max_length=100)
    destination: str   = Field(..., min_length=2, max_length=100)
    carrier:     str   = Field(..., min_length=2, max_length=50)
    weight_kg:   float = Field(..., gt=0, le=10000)


class ShipmentUpdate(BaseModel):
    status: ShipmentStatus


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:          UUID
    waybill_no:  str
    origin:      str
    destination: str
    carrier:     str
    weight_kg:   float
    status:      ShipmentStatus
    created_at:  datetime
    updated_at:  datetime
    events:      list[TrackingEventOut] = []


class ShipmentSummary(BaseModel):
    """Lightweight list response — no events."""
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    waybill_no: str
    origin:     str
    destination: str
    status:     ShipmentStatus
    updated_at: datetime


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:   str
    slot:     str
    version:  str
    db:       str
