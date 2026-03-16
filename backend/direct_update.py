import sqlalchemy as sa
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Build connection string
# We need to manually add details JSON column since Alembic is fundamentally out of sync on this user's DB
DB_USER = os.getenv("MYSQL_USER")
DB_PASS = os.getenv("MYSQL_PASSWORD")
DB_HOST = "localhost"
DB_PORT = "3307"
DB_NAME = os.getenv("MYSQL_DATABASE")

database_url = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(database_url)

with engine.begin() as conn:
    try:
        conn.execute(sa.text("ALTER TABLE reservation_list ADD COLUMN details JSON NULL;"))
        print("Column details added to reservation_list successfully!")
    except Exception as e:
        print(f"Error or column already exists: {e}")
