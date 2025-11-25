from src.db.models import Event, PriceSnapshot
from typing import Dict, Any


class DataCollector:
    def __init__(self, api_client, database):
        self.api_client = api_client
        self.database = database

    def store_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Store event and its price snapshot in the database

        TODO: Add status field to distinguish between sold_out,
        unavailable (TBA), and error states. See GitHub issue #X
        """
        event_id = event_data["id"]

        with self.database.get_session() as session:
            # Check if event already exists
            event = session.query(Event).filter_by(id=event_id).first()

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

            # Add new PriceSnapshot
            snapshot = PriceSnapshot(
                event_id=event_id,
                min_price=event_data.get("min_price"),
                max_price=event_data.get("max_price"),
                currency=event_data.get("currency", "USD"),
            )
            session.add(snapshot)

        return True
