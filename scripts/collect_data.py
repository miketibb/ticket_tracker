#!/usr/bin/env python3
"""
Collect event data from Ticketmaster API and store in database.

Usage:
    python scripts/collect_data.py --city "Los Angeles" --type "Music"
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.api.ticketmaster import TicketmasterAPI
from src.db.database import Database
from src.data_collector import DataCollector


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Collect event data from Ticketmaster")

    # TODO: Add arguments
    # Hint: parser.add_argument('--city', type=str, help='City name')
    parser.add_argument("--city", type=str, help="City name")
    parser.add_argument("--state", type=str, help="State code (e.g., CA)")
    parser.add_argument("--type", type=str, help="Event classification (e.g., Music)")
    parser.add_argument(
        "--keyword", type=str, help="Search keyword (artist, team, venue)"
    )
    parser.add_argument(
        "--size", type=int, default=20, help="Number of events to fetch"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Days from today to search for events"
    )

    return parser.parse_args()


def main():
    """Main script logic"""
    # Parse arguments
    args = parse_arguments()
    if not any([args.keyword, args.city, args.state, args.type]):
        print("Error: Please provide at least one search parameter")
        print(
            "Example: python scripts/collect_data.py --city 'Los Angeles' --type 'Music'"
        )
        sys.exit(1)

    # TODO: Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Make sure your .env file has the TICKETMASTER_API_KEY set.")
        sys.exit(1)

    params_str = ", ".join(
        [
            f"{k}={v}"
            for k, v in [
                ("city", args.city),
                ("state", args.state),
                ("type", args.type),
                ("keyword", args.keyword),
            ]
            if v is not None
        ]
    )
    print(f"  Parameters: {params_str}")
    print()

    # Create API client and database
    api_client = TicketmasterAPI()
    database = Database()
    database.create_tables()

    # Create DataCollector
    collector = DataCollector(api_client=api_client, database=database)

    # Build search parameters from args
    search_params = {
        "keyword": args.keyword,
        "city": args.city,
        "state_code": args.state,
        "classification_name": args.type,
        "size": args.size,
    }

    # Call collect_events()
    print(f"Collecting events...")
    results = collector.collect_events(**search_params)
    print()

    # Print results
    print(f"Found {results['fetched']} events from API")
    print()
    print("Storing in database...")
    print(f"  Created: {results['created']} new events")
    print(f"  Updated: {results['updated']} existing events")
    print(f"  Errors: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrors encountered:")
        for error in results["errors"]:
            print(f"  - {error['event_name']} ({error['event_id']}): {error['error']}")

    print("\nDone!")


if __name__ == "__main__":
    main()
