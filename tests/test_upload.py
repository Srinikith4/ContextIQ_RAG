import pytest
from fastapi.testclient import TestClient

import app.main as main

client = TestClient(main.app)

PDF = ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")


@pytest.fixture(autouse=True)
def fake_database(monkeypatch):
    """Swap the database and ingest steps for fakes, so these tests never touch Neon."""
    monkeypatch.setattr(main, "delete_expired", lambda: 0)
    monkeypatch.setattr(main, "session_documents", lambda session_id: [])
    monkeypatch.setattr(main, "ingest_pdf", lambda path,
                        name, session_id=None: 4)


def test_rejects_non_pdf():
    r = client.post(
        "/upload", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_accepts_pdf_and_returns_session():
    r = client.post("/upload", files={"file": PDF})
    assert r.status_code == 200
    body = r.json()
    assert body["document"] == "notes"
    assert body["chunks"] == 4
    assert body["session_id"]          # a new session id was created


def test_keeps_the_same_session_when_given():
    r = client.post("/upload?session_id=abc", files={"file": PDF})
    assert r.json()["session_id"] == "abc"


def test_blocks_a_fourth_pdf(monkeypatch):
    monkeypatch.setattr(main, "session_documents",
                        lambda session_id: ["a", "b", "c"])
    r = client.post("/upload?session_id=abc", files={"file": PDF})
    assert r.status_code == 400
    assert "up to 3" in r.json()["detail"]


def test_rejects_file_over_size_limit(monkeypatch):
    # limit 0 MB, so any file is "too big"
    monkeypatch.setattr(main, "MAX_UPLOAD_MB", 0)
    r = client.post("/upload", files={"file": PDF})
    assert r.status_code == 413


def test_rejects_pdf_with_no_text(monkeypatch):
    monkeypatch.setattr(main, "ingest_pdf", lambda path,
                        name, session_id=None: 0)
    r = client.post("/upload", files={"file": PDF})
    assert r.status_code == 422
