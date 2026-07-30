from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()
    print(f"Number of users in table: {count}")
