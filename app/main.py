import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.cleanup import delete_document, delete_expired, delete_session
from app.database import check_connection
from app.ingest import ingest_pdf
from pydantic import BaseModel, Field
from app.quiz import make_quiz
from app.rag import answer_question
from app.search import list_documents, session_documents

logger = logging.getLogger(__name__)

app = FastAPI(title="ContextIQ")

MAX_UPLOADS = 3
MAX_UPLOAD_MB = 10


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")


@app.get("/documents")
def documents():
    return {"documents": list_documents()}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    return {"postgres": check_connection()}


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    document: str | None = None


@app.post("/chat")
def chat(request: ChatRequest):
    try:
        return answer_question(
            request.question, session_id=request.session_id, document=request.document
        )
    except Exception:
        logger.exception("Chat failed")
        raise HTTPException(
            status_code=502,
            detail="Could not get an answer right now. Please try again in a moment.",
        )


class QuizRequest(BaseModel):
    document: str
    session_id: str | None = None
    count: int = Field(default=5, ge=1, le=10)


@app.post("/quiz")
def quiz(request: QuizRequest):
    try:
        questions = make_quiz(request.document, request.session_id, request.count)
    except Exception:
        logger.exception("Quiz failed")
        raise HTTPException(status_code=502, detail="Could not generate a quiz. Please try again.")
    if questions is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not questions:
        raise HTTPException(status_code=502, detail="Could not generate a quiz. Please try again.")
    return {"document": request.document, "questions": questions}


@app.post("/upload")
def upload(file: UploadFile, session_id: str | None = None):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    delete_expired()
    session_id = session_id or str(uuid.uuid4())
    name = os.path.splitext(file.filename)[0]

    existing = session_documents(session_id)
    if name not in existing and len(existing) >= MAX_UPLOADS:
        raise HTTPException(
            status_code=400,
            detail=f"You can have up to {MAX_UPLOADS} PDFs at a time. Remove one to add another.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if os.path.getsize(tmp_path) > MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"That PDF is larger than {MAX_UPLOAD_MB} MB. Try a smaller file.",
            )
        chunk_count = ingest_pdf(tmp_path, name, session_id=session_id)
    finally:
        os.remove(tmp_path)

    if chunk_count == 0:
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in that PDF. Scanned pages that are only images cannot be read.",
        )

    return {"document": name, "chunks": chunk_count, "session_id": session_id}


@app.delete("/session/{session_id}")
def remove_session(session_id: str):
    return {"deleted_chunks": delete_session(session_id)}


@app.delete("/session/{session_id}/documents/{document}")
def remove_document(session_id: str, document: str):
    return {"deleted_chunks": delete_document(session_id, document)}
