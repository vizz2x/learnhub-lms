from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

DATABASE_URL = os.environ.get("DATABASE_URL")

print("=" * 60)
print("DATABASE_URL exists:", "DATABASE_URL" in os.environ)
print("DATABASE_URL value:", repr(DATABASE_URL))
print("=" * 60)

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL is missing!")

if DATABASE_URL == "":
    raise RuntimeError("DATABASE_URL is an empty string!")

# Railway uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
with engine.connect() as conn:
    print("Connected to Postgres:", conn.execute("SELECT version();").fetchone())


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
