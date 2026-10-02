"""Reset database script: drops all tables and re-seeds from scratch."""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.db.database import Base, SessionLocal, engine
from scripts.seed_db import generate_seed_data


def reset_database():
    """Drop all tables, recreate them, and seed deterministic data."""
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating fresh database schema...")
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        print("Populating database with deterministic seed data...")
        generate_seed_data(session)
        print("Database successfully reset and re-seeded.")
    finally:
        session.close()


if __name__ == "__main__":
    reset_database()
