from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import engine
from app.embedder import embed_texts
from app.models import Chunk


def search_chunk(question, top_k=3, session_id=None, document=None):
    query_vector = embed_texts([question])[0]
    distance = Chunk.embedding.cosine_distance(query_vector)
    visible = Chunk.session_id.is_(None)
    if session_id is not None:
        visible = or_(visible, Chunk.session_id == session_id)
    stmt = select(Chunk, distance).where(visible)
    if document is not None:
        stmt = stmt.where(Chunk.document == document)
    stmt = stmt.order_by(distance).limit(top_k)

    with Session(engine) as session:
        rows = session.execute(stmt).all()
        return [
            {
                "document": chunk.document,
                "page": chunk.page,
                "text": chunk.text,
                "distance": float(dist),
            }
            for chunk, dist in rows
        ]


def get_document_chunks(document, session_id=None):
    visible = Chunk.session_id.is_(None)
    if session_id is not None:
        visible = or_(visible, Chunk.session_id == session_id)
    stmt = (
        select(Chunk)
        .where(visible, Chunk.document == document)
        .order_by(Chunk.page, Chunk.id)
    )
    with Session(engine) as session:
        return [
            {"page": chunk.page, "text": chunk.text}
            for chunk in session.scalars(stmt).all()
        ]


def list_documents():
    stmt = (
        select(Chunk.document)
        .where(Chunk.session_id.is_(None))
        .distinct()
        .order_by(Chunk.document)
    )
    with Session(engine) as session:
        return list(session.scalars(stmt).all())


def session_documents(session_id):
    stmt = (
        select(Chunk.document)
        .where(Chunk.session_id == session_id)
        .distinct()
    )
    with Session(engine) as session:
        return list(session.scalars(stmt).all())
