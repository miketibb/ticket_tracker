import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.api.ticketmaster import TicketmasterAPI


@pytest.fixture
def sample_event_response():
    """Sample event data from Ticketmaster API"""
    return {
        "id": "vvG1YZKS9rStch",
        "name": "Taylor Swift | The Eras Tour",
        "url": "https://www.ticketmaster.com/event/123",
        "dates": {"start": {"dateTime": "2024-08-08T19:00:00Z"}},
        "classifications": [{"segment": {"name": "Music"}, "genre": {"name": "Pop"}}],
        "priceRanges": [{"min": 49.50, "max": 449.50, "currency": "USD"}],
        "_embedded": {
            "venues": [
                {
                    "name": "SoFi Stadium",
                    "city": {"name": "Inglewood"},
                    "state": {"stateCode": "CA"},
                }
            ]
        },
    }


@pytest.fixture
def api_client():
    """Create API client with test key"""
    return TicketmasterAPI(api_key="test_key")


class TestTicketmasterAPI:
    def test_init_without_api_key(self):
        """Test that initialization fails without API key"""
        with patch("src.api.ticketmaster.Config.TICKETMASTER_API_KEY", None):
            with pytest.raises(ValueError, match="API key is required"):
                TicketmasterAPI()

    def test_init_with_api_key(self):
        """Test successful initialization with API key"""
        api = TicketmasterAPI(api_key="test_key")
        assert api.api_key == "test_key"
        assert api.base_url == "https://app.ticketmaster.com/discovery/v2"

    @patch("src.api.ticketmaster.requests.get")
    def test_search_events_success(self, mock_get, api_client, sample_event_response):
        """Test successful event search"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "_embedded": {"events": [sample_event_response]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        events = api_client.search_events(keyword="Taylor Swift")

        assert len(events) == 1
        assert events[0]["id"] == "vvG1YZKS9rStch"
        assert mock_get.called

    @patch("src.api.ticketmaster.requests.get")
    def test_search_events_no_results(self, mock_get, api_client):
        """Test event search with no results"""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        events = api_client.search_events(keyword="NonexistentArtist123")

        assert len(events) == 0

    def test_parse_event_data(self, api_client, sample_event_response):
        """Test parsing of event data"""
        parsed = api_client.parse_event_data(sample_event_response)

        assert parsed["id"] == "vvG1YZKS9rStch"
        assert parsed["name"] == "Taylor Swift | The Eras Tour"
        assert parsed["event_type"] == "Music/Pop"
        assert parsed["venue_name"] == "SoFi Stadium"
        assert parsed["city"] == "Inglewood"
        assert parsed["state"] == "CA"
        assert parsed["min_price"] == 49.50
        assert parsed["max_price"] == 449.50
        assert parsed["currency"] == "USD"
        assert isinstance(parsed["start_date"], datetime)

    def test_parse_event_data_missing_fields(self, api_client):
        """Test parsing event with missing optional fields"""
        minimal_event = {"id": "test123", "name": "Test Event"}

        parsed = api_client.parse_event_data(minimal_event)

        assert parsed["id"] == "test123"
        assert parsed["name"] == "Test Event"
        assert parsed["min_price"] is None
        assert parsed["max_price"] is None
        assert parsed["venue_name"] is None
