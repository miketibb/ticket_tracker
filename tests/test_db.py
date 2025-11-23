import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Event, PriceSnapshot, UserInterest
from src.db.database import Database


@pytest.fixture
def test_db():
    """Create a test database in memory"""
    db = Database("sqlite:///:memory:")
    db.create_tables()
    return db


@pytest.fixture
def sample_event():
    """Sample event for testing"""
    return Event(
        id="test_event_123",
        name="Test Concert",
        event_type="Music/Rock",
        start_date=datetime(2024, 12, 31, 20, 0, 0),
        venue_name="Test Venue",
        city="Los Angeles",
        state="CA",
        url="https://example.com/event",
    )


class TestDatabase:
    def test_create_tables(self, test_db):
        """Test that tables are created successfully"""
        # Tables should exist after initialization
        assert test_db.engine.has_table("events")
        assert test_db.engine.has_table("price_snapshots")
        assert test_db.engine.has_table("user_interests")

    def test_add_event(self, test_db, sample_event):
        """Test adding an event to database"""
        with test_db.get_session() as session:
            session.add(sample_event)

        with test_db.get_session() as session:
            event = session.query(Event).filter_by(id="test_event_123").first()
            assert event is not None
            assert event.name == "Test Concert"
            assert event.city == "Los Angeles"

    def test_add_price_snapshot(self, test_db, sample_event):
        """Test adding price snapshots to an event"""
        with test_db.get_session() as session:
            session.add(sample_event)

            snapshot = PriceSnapshot(
                event_id=sample_event.id,
                min_price=50.0,
                max_price=150.0,
                currency="USD",
            )
            session.add(snapshot)

        with test_db.get_session() as session:
            event = session.query(Event).filter_by(id="test_event_123").first()
            assert len(event.price_snapshots) == 1
            assert event.price_snapshots[0].min_price == 50.0

    def test_multiple_price_snapshots(self, test_db, sample_event):
        """Test adding multiple price snapshots over time"""
        with test_db.get_session() as session:
            session.add(sample_event)

            snapshot1 = PriceSnapshot(
                event_id=sample_event.id,
                min_price=50.0,
                max_price=150.0,
                snapshot_time=datetime(2024, 1, 1, 12, 0, 0),
            )
            snapshot2 = PriceSnapshot(
                event_id=sample_event.id,
                min_price=45.0,
                max_price=140.0,
                snapshot_time=datetime(2024, 1, 2, 12, 0, 0),
            )
            session.add_all([snapshot1, snapshot2])

        with test_db.get_session() as session:
            event = session.query(Event).filter_by(id="test_event_123").first()
            assert len(event.price_snapshots) == 2

            # Check that prices changed
            snapshots = sorted(event.price_snapshots, key=lambda s: s.snapshot_time)
            assert snapshots[0].min_price == 50.0
            assert snapshots[1].min_price == 45.0  # Price dropped

    def test_user_interest(self, test_db, sample_event):
        """Test tracking user interest in an event"""
        with test_db.get_session() as session:
            session.add(sample_event)

            interest = UserInterest(
                event_id=sample_event.id,
                user_email="test@example.com",
                target_price=100.0,
            )
            session.add(interest)

        with test_db.get_session() as session:
            interest = (
                session.query(UserInterest).filter_by(event_id="test_event_123").first()
            )
            assert interest is not None
            assert interest.user_email == "test@example.com"
            assert interest.target_price == 100.0

    def test_cascade_delete(self, test_db, sample_event):
        """Test that price snapshots are deleted when event is deleted"""
        with test_db.get_session() as session:
            session.add(sample_event)
            snapshot = PriceSnapshot(
                event_id=sample_event.id, min_price=50.0, max_price=150.0
            )
            session.add(snapshot)

        with test_db.get_session() as session:
            event = session.query(Event).filter_by(id="test_event_123").first()
            session.delete(event)

        with test_db.get_session() as session:
            # Event should be deleted
            event = session.query(Event).filter_by(id="test_event_123").first()
            assert event is None

            # Price snapshots should also be deleted (cascade)
            snapshots = (
                session.query(PriceSnapshot).filter_by(event_id="test_event_123").all()
            )
            assert len(snapshots) == 0
