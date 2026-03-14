"""
Pytest configuration: provides a tmp_db fixture that initializes
an in-memory SQLite database for each test.
"""
import pytest
from readwise.db.database import Database


@pytest.fixture
def tmp_db(tmp_path):
    """Initialize a fresh SQLite database in a temp directory for each test."""
    db_path = tmp_path / "test.db"
    db = Database.init(db_path)
    yield db
    db.close()
    Database._instance = None
