import sys
import os

# Add backend directory to sys.path to allow importing app
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

from sqlalchemy import text
from app.database.connection import get_engine

def add_column():
    engine = get_engine()
    with engine.connect() as conn:
        try:
            # check if column exists first to avoid error if re-running
            result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'country_code'"))
            if result.fetchone():
                print("'country_code' column already exists.")
                return

            conn.execute(text("ALTER TABLE users ADD COLUMN country_code VARCHAR(10) DEFAULT 'KRW' COMMENT 'Currency Code for Budget'"))
            conn.commit()
            print("Successfully added 'country_code' column to 'users' table.")
        except Exception as e:
            print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_column()
