from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:yourpassword@localhost/learnhub")

# Railway uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
