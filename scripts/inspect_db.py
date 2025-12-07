# scripts/inspect_db.py
#!/usr/bin/env python3
"""Inspect database contents"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.db.database import Database
from src.db.models import Event, PriceSnapshot, UserInterest


def main():
    Config.validate()
    db = Database()

    with db.get_session() as session:
        # Count records
        event_count = session.query(Event).count()
        snapshot_count = session.query(PriceSnapshot).count()
        interest_count = session.query(UserInterest).count()

        print("Database Contents:")
        print(f"  Events: {event_count}")
        print(f"  Price Snapshots: {snapshot_count}")
        print(f"  User Interests: {interest_count}")
        print()

        # Show events
        print("=" * 80)
        print("EVENTS:")
        print("=" * 80)
        events = session.query(Event).all()
        for event in events:
            print(f"\n{event.id}")
            print(f"  Name: {event.name}")
            print(f"  Date: {event.start_date}")
            print(f"  Venue: {event.venue_name}, {event.city}, {event.state}")

            # Count snapshots for this event
            snap_count = (
                session.query(PriceSnapshot).filter_by(event_id=event.id).count()
            )
            print(f"  Price Snapshots: {snap_count}")

        # Show tracked events
        print("\n" + "=" * 80)
        print("TRACKED EVENTS:")
        print("=" * 80)
        interests = session.query(UserInterest).all()
        for interest in interests:
            event = session.query(Event).filter_by(id=interest.event_id).first()
            status = "✓ Active" if interest.is_active else "✗ Inactive"
            print(f"\n{status} - {event.name if event else interest.event_id}")
            print(f"  User: {interest.user_email}")
            print(
                f"  Target Price: ${interest.target_price}"
                if interest.target_price
                else "  No target price"
            )
            print(f"  Tracking since: {interest.created_at}")

        # Show price history for tracked events
        print("\n" + "=" * 80)
        print("PRICE HISTORY (Tracked Events):")
        print("=" * 80)
        for interest in interests:
            if not interest.is_active:
                continue

            event = session.query(Event).filter_by(id=interest.event_id).first()
            snapshots = (
                session.query(PriceSnapshot)
                .filter_by(event_id=interest.event_id)
                .order_by(PriceSnapshot.snapshot_time)
                .all()
            )

            print(f"\n{event.name if event else interest.event_id}")
            print(f"  Price History ({len(snapshots)} snapshots):")
            for snap in snapshots:
                price_str = (
                    f"${snap.min_price}-${snap.max_price}"
                    if snap.min_price
                    else "No price"
                )
                print(f"    {snap.snapshot_time}: {price_str}")


if __name__ == "__main__":
    main()


# # Count tracked events
# python -c "
# from src.db.database import Database
# from src.db.models import UserInterest
# db = Database()
# with db.get_session() as session:
#     count = session.query(UserInterest).count()
#     print(f'Tracked events: {count}')
# "

# # List event IDs in database
# python -c "
# from src.db.database import Database
# from src.db.models import Event
# db = Database()
# with db.get_session() as session:
#     events = session.query(Event).all()
#     for e in events:
#         print(f'{e.id} - {e.name}')
# "

# # Show price history for one event
# python -c "
# from src.db.database import Database
# from src.db.models import PriceSnapshot
# db = Database()
# event_id = 'Z7r9jZ1A7_O4b'
# with db.get_session() as session:
#     snaps = session.query(PriceSnapshot).filter_by(event_id=event_id).all()
#     for s in snaps:
#         print(f'{s.snapshot_time}: \${s.min_price}-\${s.max_price}')
# "
