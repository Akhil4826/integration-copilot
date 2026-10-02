"""Pytest configuration and fixtures for Unit, Integration, and Agent tests."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force testing environment settings
os.environ["APP_ENV"] = "testing"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.config import get_settings
from app.core.security import reset_rate_limits
from app.db.database import Base, get_db
from app.llm.mock_provider import MockLLMProvider
from app.main import app
from scripts.seed_db import generate_seed_data

# In-memory SQLite engine for tests
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create in-memory database schema and seed baseline deterministic data."""
    from app.db.database import SessionLocal as AppSessionLocal

    AppSessionLocal.configure(bind=test_engine)

    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    generate_seed_data(session)
    session.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a database session within an isolated transaction that rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency and reset rate limiter."""
    reset_rate_limits()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_rate_limits()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Standard authenticated headers with Bearer token."""
    settings = get_settings()
    return {"Authorization": f"Bearer {settings.api_auth_token}"}


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Admin authenticated headers with Bearer token."""
    settings = get_settings()
    return {"Authorization": f"Bearer {settings.admin_auth_token}"}


@pytest.fixture
def mock_llm() -> MockLLMProvider:
    return MockLLMProvider()
