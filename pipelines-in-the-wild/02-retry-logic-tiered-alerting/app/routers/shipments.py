from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.shipment import Shipment, TrackingEvent, ShipmentStatus
from app.schemas.shipment import (
    ShipmentCreate, ShipmentUpdate, ShipmentOut, ShipmentSummary,
    TrackingEventCreate, TrackingEventOut,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])


# ── Shipments ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Shipment).where(Shipment.waybill_no == payload.waybill_no)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Waybill {payload.waybill_no} already exists",
        )

    shipment = Shipment(**payload.model_dump())
    db.add(shipment)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.get("", response_model=list[ShipmentSummary])
def list_shipments(
    status_filter: ShipmentStatus | None = Query(None, alias="status"),
    carrier:       str | None            = Query(None),
    limit:         int                   = Query(50, ge=1, le=200),
    offset:        int                   = Query(0, ge=0),
    db:            Session               = Depends(get_db),
):
    q = select(Shipment)
    if status_filter:
        q = q.where(Shipment.status == status_filter)
    if carrier:
        q = q.where(Shipment.carrier == carrier)
    q = q.order_by(Shipment.updated_at.desc()).limit(limit).offset(offset)
    return db.execute(q).scalars().all()


@router.get("/{waybill_no}", response_model=ShipmentOut)
def get_shipment(waybill_no: str, db: Session = Depends(get_db)):
    shipment = db.execute(
        select(Shipment).where(Shipment.waybill_no == waybill_no)
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Waybill {waybill_no} not found")
    return shipment


@router.patch("/{waybill_no}", response_model=ShipmentOut)
def update_shipment_status(
    waybill_no: str,
    payload: ShipmentUpdate,
    db: Session = Depends(get_db),
):
    shipment = db.execute(
        select(Shipment).where(Shipment.waybill_no == waybill_no)
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Waybill {waybill_no} not found")

    shipment.status     = payload.status
    shipment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(shipment)
    return shipment


@router.delete("/{waybill_no}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shipment(waybill_no: str, db: Session = Depends(get_db)):
    shipment = db.execute(
        select(Shipment).where(Shipment.waybill_no == waybill_no)
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Waybill {waybill_no} not found")
    db.delete(shipment)
    db.commit()


# ── Tracking events ────────────────────────────────────────────────────────────

@router.post("/{waybill_no}/events", response_model=TrackingEventOut,
             status_code=status.HTTP_201_CREATED)
def add_tracking_event(
    waybill_no: str,
    payload: TrackingEventCreate,
    db: Session = Depends(get_db),
):
    shipment = db.execute(
        select(Shipment).where(Shipment.waybill_no == waybill_no)
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Waybill {waybill_no} not found")

    event = TrackingEvent(
        shipment_id = shipment.id,
        location    = payload.location,
        status      = payload.status,
        note        = payload.note,
        occurred_at = payload.occurred_at or datetime.now(timezone.utc),
    )
    # Keep shipment status in sync with latest event
    shipment.status     = payload.status
    shipment.updated_at = datetime.now(timezone.utc)

    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/{waybill_no}/events", response_model=list[TrackingEventOut])
def get_tracking_events(waybill_no: str, db: Session = Depends(get_db)):
    shipment = db.execute(
        select(Shipment).where(Shipment.waybill_no == waybill_no)
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Waybill {waybill_no} not found")
    return shipment.events
