from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Chunk


def delete_session(session_id):
    with Session(engine) as session:
        result = session.execute(delete(Chunk).where(
            Chunk.session_id == session_id))
        session.commit()
        return result.rowcount


def delete_expired(max_age_minutes=60):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    with Session(engine) as session:
        result = session.execute(
            delete(Chunk).where(
                Chunk.session_id.is_not(None), Chunk.created_at < cutoff
            )
        )
        session.commit()
        return result.rowcount


def delete_document(session_id, document):
    with Session(engine) as session:
        result = session.execute(
            delete(Chunk).where(
                Chunk.session_id == session_id, Chunk.document == document
            )
        )
        session.commit()
        return result.rowcount
