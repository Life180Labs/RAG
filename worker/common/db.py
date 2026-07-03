"""Sync SQLAlchemy engine shared by every worker task.

Celery's prefork pool executes task bodies synchronously, so workers use
psycopg3's sync driver rather than the backend's asyncpg engine — same
Postgres, different driver for a different execution model.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.config import get_worker_settings

_settings = get_worker_settings()

engine = create_engine(_settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
