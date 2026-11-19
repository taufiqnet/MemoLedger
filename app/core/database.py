import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Determine active database engine
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    # Graceful fallback to SQLite for local tests/development
    logger.warning(f"Could not connect to {db_url}: {e}. Falling back to SQLite local database.")
    db_url = "sqlite:///./memoledger.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        connect_args=connect_args,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Read-only database engine for guarded Text-to-SQL
readonly_engine = engine
ReadonlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_readonly_db() -> Generator[Session, None, None]:
    db = ReadonlySessionLocal()
    try:
        yield db
    finally:
        db.close()
