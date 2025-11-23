import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration settings for the application"""

    TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")
    TICKETMASTER_BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ticket_tracker.db")

    # API rate limiting
    MAX_REQUESTS_PER_MINUTE = 60

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TICKETMASTER_API_KEY:
            raise ValueError("TICKETMASTER_API_KEY must be set in .env file")
