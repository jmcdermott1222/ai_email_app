"""Sanity checks for database session and models."""

import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import User


def test_create_user_roundtrip() -> None:
    database_url = os.getenv("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        user = User(email="test@example.com", google_sub="sub-123")
        session.add(user)
        session.commit()

        result = session.execute(select(User).where(User.email == "test@example.com"))
        fetched = result.scalar_one()

    assert fetched.email == "test@example.com"
