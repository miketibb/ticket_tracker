#!/usr/bin/env python3
"""
Track a specific event for price monitoring.

Usage:
    python scripts/track_event.py --event-id "abc123" --email "you@email.com" --target-price 100
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.api.ticketmaster import TicketmasterAPI
from src.db.database import Database
from src.db.models import Event, UserInterest
from src.data_collector import DataCollector


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Track an event for price monitoring")

    # Add arguments
    parser.add_argument(
        "--event-id", type=str, required=True, help="Ticketmaster Event ID to track"
    )
    parser.add_argument(
        "--email", type=str, required=True, help="User email for tracking notifications"
    )
    parser.add_argument(
        "--target-price", type=float, help="Target price for notifications (optional)"
    )

    return parser.parse_args()


def track_event(event_id: str, user_email: str, target_price: float = None):
    """Add an event to the user's tracking list"""

    # 1. Create API client, database, collector
    api_client = TicketmasterAPI()
    database = Database()
    database.create_tables()
    collector = DataCollector(api_client=api_client, database=database)

    with database.get_session() as session:
        # 2. Check if event exists in DB
        event = session.query(Event).filter_by(id=event_id).first()

        # 3. If not, fetch from API and store
        if not event:
            print(f"Event {event_id} not in database. Fetching from API...")

            api_event = api_client.get_event_details(event_id)  # ← Fixed typo

            if not api_event:
                print(f"Error: Event ID {event_id} not found in Ticketmaster API.")
                return False

            parsed = api_client.parse_event_data(api_event)
            result = collector.store_event(parsed)

            if result:
                print(f"✓ Stored event: {parsed['name']}")
                event = session.query(Event).filter_by(id=event_id).first()
            else:
                print("Error: Failed to store event")
                return False

        # Now event definitely exists
        print(f"\nEvent: {event.name}")
        print(f"  Date: {event.start_date}")
        print(f"  Venue: {event.venue_name}, {event.city}, {event.state}\n")

        # 4. Check if already tracking
        existing_interest = (
            session.query(UserInterest)
            .filter_by(event_id=event_id, user_email=user_email)
            .first()
        )

        # 5. Create or update UserInterest
        if existing_interest:
            # Reactivate if inactive
            was_inactive = not existing_interest.is_active
            existing_interest.is_active = True
            existing_interest.target_price = target_price

            if was_inactive:
                print("ℹ Reactivated tracking for this event")
        else:
            # Create new
            new_interest = UserInterest(
                event_id=event_id, user_email=user_email, target_price=target_price
            )
            session.add(new_interest)

        # Session commits automatically on exit from context manager

        # 6. Print confirmation (outside session is fine - we have the data)
        if existing_interest:
            print(f"✓ Updated tracking for {event.name}")
        else:
            print(f"✓ Now tracking {event.name}")

        if target_price:
            print(f"  Target price: ${target_price}")
        else:
            print("  No target price set (tracking only)")

    return True


def main():
    """Main script logic"""
    args = parse_arguments()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Track the event
    success = track_event(
        event_id=args.event_id, user_email=args.email, target_price=args.target_price
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
