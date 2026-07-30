from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Get DATABASE_URL from environment (Railway injects this automatically)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is missing")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,          # Set to True to see SQL queries
    pool_pre_ping=True,  # Test connections before using
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
