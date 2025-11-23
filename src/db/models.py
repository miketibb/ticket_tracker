from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

Base = declarative_base()


class Event(Base):
    """Event information from Ticketmaster"""

    __tablename__ = "events"

    id = Column(String, primary_key=True)  # Ticketmaster event ID
    name = Column(String, nullable=False)
    event_type = Column(String)  # concert, sports, etc.
    start_date = Column(DateTime)
    venue_name = Column(String)
    city = Column(String)
    state = Column(String)
    url = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    price_snapshots = relationship(
        "PriceSnapshot", back_populates="event", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Event(id={self.id}, name={self.name}, date={self.start_date})>"


class PriceSnapshot(Base):
    """Price information at a specific point in time"""

    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    min_price = Column(Float)
    max_price = Column(Float)
    currency = Column(String, default="USD")
    snapshot_time = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    event = relationship("Event", back_populates="price_snapshots")

    # Ensure we don't duplicate snapshots
    __table_args__ = (
        UniqueConstraint("event_id", "snapshot_time", name="uix_event_snapshot"),
    )

    def __repr__(self):
        return f"<PriceSnapshot(event_id={self.event_id}, min={self.min_price}, max={self.max_price}, time={self.snapshot_time})>"


class UserInterest(Base):
    """Track which events users are interested in monitoring"""

    __tablename__ = "user_interests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    user_email = Column(String, nullable=False)
    target_price = Column(Float)  # Optional: alert when price drops below this
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<UserInterest(event_id={self.event_id}, email={self.user_email})>"
