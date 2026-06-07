from sqlalchemy import Column, String, Float, DateTime, Enum as PgEnum, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import enum
import uuid

from app.db.session import Base


class ShipmentStatus(str, enum.Enum):
    PENDING    = "pending"
    IN_TRANSIT = "in_transit"
    AT_HUB     = "at_hub"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED  = "delivered"
    EXCEPTION  = "exception"


class Shipment(Base):
    __tablename__ = "shipments"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    waybill_no  = Column(String(20), unique=True, nullable=False, index=True)
    origin      = Column(String(100), nullable=False)
    destination = Column(String(100), nullable=False)
    carrier     = Column(String(50), nullable=False)
    weight_kg   = Column(Float, nullable=False)
    status      = Column(PgEnum(ShipmentStatus), nullable=False, default=ShipmentStatus.PENDING)
    created_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at  = Column(DateTime(timezone=True),
                         default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    events = relationship("TrackingEvent", back_populates="shipment",
                          cascade="all, delete-orphan", order_by="TrackingEvent.occurred_at")


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False, index=True)
    location    = Column(String(100), nullable=False)
    status      = Column(PgEnum(ShipmentStatus), nullable=False)
    note        = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shipment = relationship("Shipment", back_populates="events")
