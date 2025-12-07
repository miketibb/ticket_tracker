from src.db.models import Event, PriceSnapshot, UserInterest
from typing import Dict, Any
from datetime import datetime, timezone


class DataCollector:
    def __init__(self, api_client, database):
        self.api_client = api_client
        self.database = database

    def store_event(self, event_data: Dict[str, Any]) -> str:
        """
        Store event and its price snapshot in the database

        TODO: Add status field to distinguish between sold_out,
        unavailable (TBA), and error states. See GitHub issue #X
        """
        event_id = event_data["id"]

        with self.database.get_session() as session:
            # Check if event already exists
            event = session.query(Event).filter_by(id=event_id).first()

            # Add new PriceSnapshot
            snapshot = PriceSnapshot(
                event_id=event_id,
                min_price=event_data.get("min_price"),
                max_price=event_data.get("max_price"),
                currency=event_data.get("currency", "USD"),
            )
            session.add(snapshot)

            if not event:
                # Create new Event
                event = Event(
                    id=event_id,
                    name=event_data["name"],
                    event_type=event_data.get("event_type"),
                    start_date=event_data.get("start_date"),
                    venue_name=event_data.get("venue_name"),
                    city=event_data.get("city"),
                    state=event_data.get("state"),
                    url=event_data.get("url"),
                )
                session.add(event)
                return "created"

            else:
                return "updated"

    def _collect_tracked_events(self) -> Dict:
        """Collect fresh data for tracked events only"""

        # TODO: Add --email filter to only collect specific user's tracked events
        # TODO: Track consecutive failures and mark inactive after X attempts

        # 1. Query UserInterest for active events
        with self.database.get_session() as session:
            # 1. Query UserInterest for active events
            tracked = session.query(UserInterest).filter_by(is_active=True).all()

            # Get event IDs for tracked interests
            event_ids = [interest.event_id for interest in tracked]

            # Query events to check dates
            events = session.query(Event).filter(Event.id.in_(event_ids)).all()

            # Build map of event_id -> event for date checking
            event_map = {event.id: event for event in events}

            # 2. Filter out past events and deactivate them
            now = datetime.now()
            skipped = 0
            active_event_ids = []

            for interest in tracked:
                event = event_map.get(interest.event_id)

                if event and event.start_date and event.start_date < now:
                    # Event is in the past, mark as inactive
                    interest.is_active = False
                    skipped += 1
                else:
                    # Store just the ID, not the whole object
                    active_event_ids.append(interest.event_id)

            # Session commits automatically when exiting with block

        # 3. Collect data for active events (outside session is fine)
        fetched = len(active_event_ids)
        updated = 0
        errors = []

        for event_id in active_event_ids:
            try:
                # 3. Fetch from API
                api_event = self.api_client.get_event_details(event_id)

                if not api_event:
                    errors.append({"event_id": event_id, "error": "Not found in API"})
                    continue

                # 4. Parse and store (creates new PriceSnapshot)
                parsed = self.api_client.parse_event_data(api_event)
                result = self.store_event(parsed)

                if result == "updated":
                    updated += 1

            except Exception as e:
                errors.append({"event_id": event_id, "error": str(e)})

        return {
            "fetched": fetched,
            "created": 0,  # Never creates new events in tracked mode
            "updated": updated,
            "errors": errors,
        }

    def collect_events(self, **search_params) -> Dict:
        """Fetch events from API and store them"""

        if search_params.get("tracked_only"):
            return self._collect_tracked_events()

        # Call API and count results
        events = self.api_client.search_events(**search_params)
        fetched = len(events)

        # Initialize counters
        created = 0
        updated = 0
        errors = []

        # Loop through events
        for event in events:
            try:
                # Parse and store
                parsed = self.api_client.parse_event_data(event)
                result = self.store_event(parsed)

                if result == "created":
                    created += 1
                elif result == "updated":
                    updated += 1

            except Exception as e:
                errors.append(
                    {
                        "event_id": event.get("id", "unknown"),
                        "event_name": event.get("name", "Unknown"),
                        "error": str(e),
                    }
                )

        return {
            "fetched": fetched,
            "created": created,
            "updated": updated,
            "errors": errors,
        }
