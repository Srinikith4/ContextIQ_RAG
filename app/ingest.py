from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.chunking import chunk_pages
from app.database import engine
from app.embedder import embed_texts
from app.models import Chunk
from app.pdf_loader import extract_pages


def ingest_pdf(pdf_path, document_name, session_id=None):
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages)
    if not chunks:
        return 0
    vectors = embed_texts([c["text"] for c in chunks])

    with Session(engine) as session:
        same_session = (
            Chunk.session_id.is_(None)
            if session_id is None
            else Chunk.session_id == session_id
        )
        session.execute(
            delete(Chunk).where(Chunk.document == document_name, same_session)
        )
        for chunk, vector in zip(chunks, vectors):
            session.add(
                Chunk(
                    document=document_name,
                    page=chunk["page"],
                    text=chunk["text"],
                    session_id=session_id,
                    embedding=vector,
                )
            )
        session.commit()
        return len(chunks)
