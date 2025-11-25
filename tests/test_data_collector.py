from datetime import datetime
from src.db.models import Event, PriceSnapshot
from src.data_collector import DataCollector


def test_store_new_event_with_prices(test_db):
    """Test that new event with prices creates both records"""

    # ARRANGE: Prepare test data
    sample_event = {
        "id": "test_event_123",
        "name": "Test Concert",
        "event_type": "Music/Rock",
        "start_date": datetime(2024, 12, 31, 20, 0, 0),
        "venue_name": "Test Venue",
        "city": "Los Angeles",
        "state": "CA",
        "url": "https://example.com",
        "min_price": 50.0,
        "max_price": 150.0,
        "currency": "USD",
    }

    # ARRANGE: Create collector (api_client not needed for this test)
    collector = DataCollector(api_client=None, database=test_db)

    # ACT: Store the event
    result = collector.store_event(sample_event)

    # ASSERT: Check it worked
    assert result is True

    # ASSERT: Check database has Event
    with test_db.get_session() as session:
        event = session.query(Event).filter_by(id="test_event_123").first()
        assert event is not None
        assert event.name == "Test Concert"
        assert event.city == "Los Angeles"

        # ASSERT: Check database has PriceSnapshot
        snapshots = (
            session.query(PriceSnapshot).filter_by(event_id="test_event_123").all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].min_price == 50.0
        assert snapshots[0].max_price == 150.0


def test_store_existing_event_adds_snapshot(test_db):
    """Test that existing event gets new price snapshot"""

    # ARRANGE: Put an event in the database FIRST
    # (Hint: use test_db.get_session() to add an Event)
    first_event = Event(
        id="test_event_123",
        name="Test Concert",
        event_type="Music/Rock",
        start_date=datetime(2024, 12, 31, 20, 0, 0),
        venue_name="Test Venue",
        city="Los Angeles",
        state="CA",
        url="https://example.com",
    )

    first_snapshot = PriceSnapshot(
        event_id="test_event_123",
        min_price=50.0,  # Original price
        max_price=150.0,
        currency="USD",
    )

    with test_db.get_session() as session:
        session.add(first_event)
        session.add(first_snapshot)

    # ARRANGE: Create new price data for same event
    updated_event_data = {
        "id": "test_event_123",  # SAME ID!
        "name": "Test Concert",
        "event_type": "Music/Rock",
        "start_date": datetime(2024, 12, 31, 20, 0, 0),
        "venue_name": "Test Venue",
        "city": "Los Angeles",
        "state": "CA",
        "url": "https://example.com",
        "min_price": 45.0,  # NEW PRICE - dropped $5!
        "max_price": 140.0,  # NEW PRICE
        "currency": "USD",
    }

    # ARRANGE: Create collector
    collector = DataCollector(api_client=None, database=test_db)

    # ACT: Store the event again with new prices
    result = collector.store_event(updated_event_data)

    # ASSERT: Event still exists (only one)
    assert result is True

    # ASSERT: TWO price snapshots exist now
    with test_db.get_session() as session:
        event = session.query(Event).filter_by(id="test_event_123").first()
        assert event is not None

        snapshots = (
            session.query(PriceSnapshot).filter_by(event_id="test_event_123").all()
        )
        assert len(snapshots) == 2  # Now there should be two snapshots

        # Check that one of them has the new prices
        prices = [(snap.min_price, snap.max_price) for snap in snapshots]
        assert (45.0, 140.0) in prices
        assert (50.0, 150.0) in prices
