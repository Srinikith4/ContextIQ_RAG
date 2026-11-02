import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
DATABASE_URL = DATABASE_URL.replace(
    "postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL)


def check_connection():
    with engine.connect() as conn:
        return conn.execute(text("SELECT version()")).scalar()
