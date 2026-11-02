"""One-time setup for a fresh database.

Does the three things that were first done by hand:
1. enable the pgvector extension in Postgres
2. create the chunks table from models.py
3. load the built-in PDFs (permanent documents, session_id = NULL)

Run from the project folder:  python -m app.setup_db
Safe to run again: ingest_pdf deletes a document's old rows before adding new ones.
"""
from pathlib import Path

from sqlalchemy import text

from app.database import engine
from app.ingest import ingest_pdf
from app.models import Base

PROJECT_DIR = Path(__file__).resolve().parent.parent

# (file inside sample_docs/, name shown as a tab in the app)
BUILT_IN_DOCS = [
    ("RTI-Act_English.pdf", "RTI Act 2005"),
]


def create_tables():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    print("Database ready: pgvector enabled, chunks table created.")


def load_built_in_docs():
    for filename, name in BUILT_IN_DOCS:
        path = PROJECT_DIR / "sample_docs" / filename
        count = ingest_pdf(str(path), name)
        print(f"Loaded {name}: {count} chunks")


if __name__ == "__main__":
    create_tables()
    load_built_in_docs()
