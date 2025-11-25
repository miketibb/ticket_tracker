import pytest
import os
from src.db.database import Database


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ["TICKETMASTER_API_KEY"] = "test_key"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    yield
    if "TICKETMASTER_API_KEY" in os.environ:
        del os.environ["TICKETMASTER_API_KEY"]
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture
def test_db():
    """Create a test database in memory"""
    db = Database("sqlite:///:memory:")
    db.create_tables()
    return db
