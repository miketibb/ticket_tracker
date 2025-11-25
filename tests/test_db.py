import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.db.models import Base, Event, PriceSnapshot, UserInterest


class TestDatabase:
    # In tests/test_db.py, replace the test_create_tables method with:

    def test_create_tables(self, test_db):
        """Test that tables are created successfully"""
        from sqlalchemy import inspect

        inspector = inspect(test_db.engine)
        table_names = inspector.get_table_names()

        # Tables should exist after initialization
        assert "events" in table_names
        assert "price_snapshots" in table_names
        assert "user_interests" in table_names

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
