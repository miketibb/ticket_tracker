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
    assert result == "created"

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
    assert result == "updated"

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


def test_store_event_without_prices(test_db):
    """Test that event without prices still creates records"""
    # Event data with no prices
    no_price_event_data = {
        "id": "test_event_456",
        "name": "Free Concert",
        "event_type": "Music/Pop",
        "start_date": datetime(2024, 11, 15, 18, 0, 0),
        "venue_name": "Open Park",
        "city": "San Francisco",
        "state": "CA",
        "url": "https://example.com/free-concert",
        "min_price": None,  # ← No price data
        "max_price": None,
        "currency": "USD",
    }

    # ARRANGE: Create collector
    collector = DataCollector(api_client=None, database=test_db)

    # ACT: Store the event
    result = collector.store_event(no_price_event_data)

    # ASSERT: Check it worked
    assert result == "created"

    # Assert snapshot exists with None prices
    with test_db.get_session() as session:
        event = session.query(Event).filter_by(id="test_event_456").first()
        assert event is not None
        assert event.name == "Free Concert"

        snapshots = (
            session.query(PriceSnapshot).filter_by(event_id="test_event_456").all()
        )
        assert len(snapshots) == 1
        assert snapshots[0].min_price is None
        assert snapshots[0].max_price is None
        assert snapshots[0].currency == "USD"


def test_collect_events_success(test_db, sample_raw_event):
    """Test successfully collecting and storing events"""
    from unittest.mock import Mock

    # ARRANGE: Create fake API responses
    fake_raw_events = [
        sample_raw_event(
            event_id="event_1", name="Concert 1", min_price=50.0, max_price=150.0
        ),
        sample_raw_event(
            event_id="event_2",
            name="Concert 2",
            min_price=60.0,
            max_price=160.0,
        ),
    ]

    fake_parsed_event_1 = {
        "id": "event_1",
        "name": "Concert 1",
        "min_price": 50.0,
        "max_price": 150.0,
        "event_type": "concert",
        "start_date": datetime(2024, 12, 31, 20, 0, 0),
        "venue_name": "Venue 1",
        "city": "Los Angeles",
        "state": "CA",
        "url": "https://example1.com",
        "currency": "USD",
    }

    fake_parsed_event_2 = {
        "id": "event_2",
        "name": "Concert 2",
        "min_price": 60.0,
        "max_price": 160.0,
        "event_type": "concert",
        "start_date": datetime(2025, 1, 15, 20, 0, 0),
        "venue_name": "Venue 2",
        "city": "Los Angeles",
        "state": "CA",
        "url": "https://example2.com",
        "currency": "USD",
    }

    # ARRANGE: Create mock API client
    mock_api = Mock()
    mock_api.search_events.return_value = fake_raw_events

    # Problem: parse_event_data gets called twice (once per event)
    # How do we return different values each time?
    mock_api.parse_event_data.side_effect = [fake_parsed_event_1, fake_parsed_event_2]

    # ARRANGE: Create collector with mock API
    collector = DataCollector(api_client=mock_api, database=test_db)

    # ACT: Collect events
    result = collector.collect_events(city="Los Angeles")

    # ASSERT: Check summary
    assert result["fetched"] == 2
    assert result["created"] == 2
    assert result["updated"] == 0
    assert len(result["errors"]) == 0

    # ASSERT: Check database
    with test_db.get_session() as session:
        event1 = session.query(Event).filter_by(id="event_1").first()
        event2 = session.query(Event).filter_by(id="event_2").first()

        assert event1 is not None
        assert event1.name == "Concert 1"
        assert event2 is not None
        assert event2.name == "Concert 2"

        # Check price snapshots
        snapshots1 = session.query(PriceSnapshot).filter_by(event_id="event_1").all()
        snapshots2 = session.query(PriceSnapshot).filter_by(event_id="event_2").all()

        assert len(snapshots1) == 1
        assert snapshots1[0].min_price == 50.0
        assert len(snapshots2) == 1
        assert snapshots2[0].min_price == 60.0
