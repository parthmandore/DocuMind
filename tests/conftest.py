"""Pytest Shared Fixtures for DocuMind Test Suite"""

import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.db.base import Base, get_db
from backend.db.models import Document, DocumentSection, DocumentChunk, ProcessingJob
from backend.api.app import app

TEST_DB_PATH = Path(__file__).resolve().parent / "test_documind.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="session")
def engine():
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

    eng = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    
    # Enable SQLite foreign key cascade
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    
    eng.dispose()
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass

@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(engine, db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
