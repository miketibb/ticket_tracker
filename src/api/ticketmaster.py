import requests
from typing import Dict, List, Optional
from datetime import datetime
from src.config import Config


class TicketmasterAPI:
    """Client for interacting with Ticketmaster Discovery API"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or Config.TICKETMASTER_API_KEY
        self.base_url = Config.TICKETMASTER_BASE_URL

        if not self.api_key:
            raise ValueError("Ticketmaster API key is required")

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """Make a request to the Ticketmaster API"""
        url = f"{self.base_url}/{endpoint}"
        params["apikey"] = self.api_key

        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def search_events(
        self,
        keyword: str = None,
        city: str = None,
        state_code: str = None,
        classification_name: str = None,
        start_date: str = None,
        size: int = 20,
    ) -> List[Dict]:
        """
        Search for events

        Args:
            keyword: Search keyword (artist, team, venue, etc.)
            city: City name
            state_code: State code (e.g., 'CA', 'NY')
            classification_name: Type of event (e.g., 'Music', 'Sports')
            start_date: Start date in format YYYY-MM-DDTHH:mm:ssZ
            size: Number of results (max 200)

        Returns:
            List of event dictionaries
        """
        params = {"size": size}

        if keyword:
            params["keyword"] = keyword
        if city:
            params["city"] = city
        if state_code:
            params["stateCode"] = state_code
        if classification_name:
            params["classificationName"] = classification_name
        if start_date:
            params["startDateTime"] = start_date

        response = self._make_request("events.json", params)

        # Extract events from response
        if "_embedded" in response and "events" in response["_embedded"]:
            return response["_embedded"]["events"]

        return []

    def get_event_details(self, event_id: str) -> Optional[Dict]:
        """Get detailed information about a specific event"""
        try:
            response = self._make_request(f"events/{event_id}.json", {})
            return response
        except requests.exceptions.HTTPError:
            return None

    def parse_event_data(self, event: Dict) -> Dict:
        """Parse raw event data into a structured format"""
        # Extract price range
        price_ranges = event.get("priceRanges", [])
        min_price = None
        max_price = None
        currency = "USD"

        if price_ranges:
            min_price = price_ranges[0].get("min")
            max_price = price_ranges[0].get("max")
            currency = price_ranges[0].get("currency", "USD")

        # Extract venue information
        venues = event.get("_embedded", {}).get("venues", [])
        venue_name = venues[0].get("name") if venues else None
        city = venues[0].get("city", {}).get("name") if venues else None
        state = venues[0].get("state", {}).get("stateCode") if venues else None

        # Extract dates
        dates = event.get("dates", {})
        start_date_str = dates.get("start", {}).get("dateTime")
        start_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(
                    start_date_str.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Extract classifications
        classifications = event.get("classifications", [])
        event_type = None
        if classifications:
            segment = classifications[0].get("segment", {}).get("name")
            genre = classifications[0].get("genre", {}).get("name")
            event_type = f"{segment}/{genre}" if segment and genre else segment or genre

        return {
            "id": event["id"],
            "name": event["name"],
            "event_type": event_type,
            "start_date": start_date,
            "venue_name": venue_name,
            "city": city,
            "state": state,
            "url": event.get("url"),
            "min_price": min_price,
            "max_price": max_price,
            "currency": currency,
        }


# Example usage script
if __name__ == "__main__":
    """
    To run this:
    1. Sign up for Ticketmaster API key at https://developer.ticketmaster.com/
    2. Create a .env file with: TICKETMASTER_API_KEY=your_key_here
    3. Run: python3 -m src.api.ticketmaster
    """

    # Validate configuration
    Config.validate()

    # Initialize API client
    api = TicketmasterAPI()

    # Search for concerts in Los Angeles (next 30 days to get more recent events with pricing)
    from datetime import datetime, timedelta

    start_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    print("Searching for upcoming concerts in Los Angeles (next 30 days)...")
    events = api.search_events(
        city="Atlanta", state_code="GA", classification_name="Music", size=20
    )

    print(f"\nFound {len(events)} total events")

    # Filter events with pricing information
    events_with_prices = []
    events_without_prices = []

    for event in events:
        parsed = api.parse_event_data(event)
        if parsed["min_price"] is not None and parsed["max_price"] is not None:
            events_with_prices.append(parsed)
        else:
            events_without_prices.append(parsed)

    print(f"  - {len(events_with_prices)} with pricing information")
    print(
        f"  - {len(events_without_prices)} without pricing (TBA, presale, or sold out)\n"
    )

    # Display events with prices
    if events_with_prices:
        print("=" * 80)
        print("EVENTS WITH PRICING:")
        print("=" * 80)
        for parsed in events_with_prices:
            print(f"\nEvent: {parsed['name']}")
            print(f"  Type: {parsed['event_type']}")
            print(f"  Date: {parsed['start_date']}")
            print(
                f"  Venue: {parsed['venue_name']}, {parsed['city']}, {parsed['state']}"
            )
            print(
                f"  Price Range: ${parsed['min_price']:.2f} - ${parsed['max_price']:.2f} {parsed['currency']}"
            )
            print(f"  URL: {parsed['url']}")

    # Display some events without prices (for awareness)
    if events_without_prices:
        print("\n" + "=" * 80)
        print("SAMPLE EVENTS WITHOUT PRICING (first 3):")
        print("=" * 80)
        for parsed in events_without_prices[:3]:
            print(f"\nEvent: {parsed['name']}")
            print(f"  Date: {parsed['start_date']}")
            print(f"  Venue: {parsed['venue_name']}")
            print(f"  Price: Not yet available")
            print(f"  URL: {parsed['url']}")

    print("\n" + "=" * 80)
    print(f"Total events suitable for price tracking: {len(events_with_prices)}")
    print("=" * 80)
