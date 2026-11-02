# ContextIQ

**Ask questions about a PDF and get answers that name the exact page they came from. Or turn the same document into a quiz.**

ContextIQ is a retrieval-augmented generation (RAG) application built with FastAPI, PostgreSQL with pgvector, local embeddings and Google Gemini. It answers only from the document you choose, cites the page for every fact, and says so plainly when the answer is not in the document.

**Live demo:** [https://contextiq-rag-cwr0.onrender.com](https://contextiq-rag-cwr0.onrender.com) (hosted on Render's free tier, so after a period of inactivity the first load may take up to a minute to wake up).

![ContextIQ answering a question about the RTI Act, with the source page shown beside the answer](docs/ask.png)

## Coming in the next version

ContextIQ is under active development. The next release is planned to add:

- **More built-in documents.** Additional public documents, each with its own tab, ready to question and quiz without uploading anything.
- **Live, real-time data.** Answers that go beyond a fixed document by calling open, free APIs for things like news, weather, sports and currency rates, so a question about today gets today's information.
- **Visual answers.** Responses that explain with images and charts, not only text, where a picture makes the answer clearer.
- **Accounts and saved history.** Sign-in, so conversations and quiz results are kept between visits.
- **Follow-up questions.** Remembering the last few messages, so "and what about the penalty?" is understood in context.

More features are planned beyond these, and this section will be updated as they ship.

---

## Contents

- [Coming in the next version](#coming-in-the-next-version)
- [Why I built this](#why-i-built-this)
- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Design decisions](#design-decisions)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [API](#api)
- [Running it locally](#running-it-locally)
- [Tests](#tests)
- [Limitations and next steps](#limitations-and-next-steps)

---

## Why I built this

This project started as a simple chatbot that matched questions to canned answers using TF-IDF. It worked for small talk, but it could not answer anything that was not already in its dataset, and it had no idea where an answer came from.

I wanted to build something closer to how real document assistants work: give it a long, dense document such as an Act of Parliament, ask a question in plain English, and get an answer you can verify. The key word is *verify*. A language model on its own will happily invent a plausible answer. ContextIQ is built around the opposite idea: every answer has to point back to a page in the source, and if the source does not contain the answer, the app should say that instead of guessing.

The built-in document is the **Right to Information Act, 2005**, a 27-page Indian law that is public, practical and full of specific numbers (deadlines, fees, penalties) that make wrong answers easy to spot.

### Hosting history

The first version of this project was deployed on an **AWS EC2 free-tier Linux instance**. I chose EC2 deliberately, to learn what it takes to run an application on a real Linux server rather than on a managed platform. Once the free-tier limits were reached, I moved the public demo of the current version to **Render**, which offers a free tier suited to showing the project publicly. The live link is temporary and is listed at the top of this README when the demo is running.

---

## What it does

**Ask questions with page citations.** Type a question in your own words. The answer appears beside a large page number showing where in the document it came from, with any other supporting pages listed underneath. Greetings and questions the document cannot answer show no page number, because no page was used.

**Generate a quiz from the document.** Choose 3, 5 or 10 questions. Gemini writes multiple-choice questions from the text, the server validates them, and the app walks you through one at a time, with an explanation and the page reference after each answer. A review screen at the end lists every question, the correct answer and where to read about it.

![A quiz question generated from the RTI Act](docs/quiz.png)

**Upload your own PDFs.** Add up to three PDFs (10 MB each). Each one opens in its own tab and supports both asking and quizzing. Uploads are private to your browser session and are deleted automatically one hour after they are added.

**Built for people who have never seen it before.** Folder-style tabs for each document, a short "How it works" panel, keyboard shortcuts in the quiz (1 to 4 to answer, Enter to continue), clear error messages, light and dark themes, and a layout that works on phones.

![Quiz results with the correct answer for each question](docs/quiz-result.png)

---

## How it works

There are two pipelines: one that prepares a document, and one that answers a question.

```mermaid
flowchart LR
    subgraph Ingestion
        A[PDF] --> B[Extract text per page<br/>pypdf]
        B --> C[Split into overlapping chunks<br/>1500 chars, 300 overlap]
        C --> D[Embed each chunk<br/>bge-small-en-v1.5, 384 dims]
        D --> E[(PostgreSQL + pgvector)]
    end

    subgraph Answering
        Q[Question] --> R[Rewrite as a passage<br/>HyDE, Gemini]
        Q --> S[Vector search<br/>cosine distance, top 10]
        R --> S
        E --> S
        S --> T[Merge, deduplicate, rank]
        T --> U[Grounded prompt<br/>Gemini]
        U --> V[Keep only the pages<br/>the answer cites]
        V --> W[Answer + page numbers]
    end
```

### Preparing a document

1. **Extract.** `pypdf` reads the PDF page by page, so every piece of text keeps its page number.
2. **Chunk.** Each page is split into chunks of 1,500 characters, with 300 characters of overlap between neighbours. The overlap means a sentence that falls on a boundary still appears whole in at least one chunk. The RTI Act becomes 69 chunks.
3. **Embed.** Each chunk is turned into a 384-number vector using the `BAAI/bge-small-en-v1.5` model, run locally through `fastembed`. Chunks with similar meaning end up with vectors that point in similar directions.
4. **Store.** The text, page number and vector go into a single `chunks` table in PostgreSQL, using the `pgvector` extension for the vector column. Built-in documents have no session ID. Uploaded documents carry the session ID of the browser that uploaded them.

### Answering a question

1. **Rewrite the question (HyDE).** Gemini is asked to write a short passage, in the style of the source document, that would answer the question. This is called Hypothetical Document Embeddings. It helps because a question ("How many days does the officer have?") is worded very differently from the law that answers it ("shall, as expeditiously as possible, and in any case within thirty days...").
2. **Search.** Both the original question and the rewritten passage are embedded and searched against the selected document using cosine distance. The top 10 results from each search are merged, duplicates are removed, and the rest are ranked by distance.
3. **Generate a grounded answer.** The retrieved chunks are passed to Gemini, each labelled with its document and page. The prompt tells the model to answer only from this context, cite the page for each fact, and say clearly when the answer is not there.
4. **Check the citations.** The server reads the page numbers the answer actually cites and returns only those pages, and only if they were among the retrieved chunks. This is why a greeting shows no page number, and why the app never displays a page the model made up.

### Generating a quiz

The server samples up to eight chunks from the document, asks Gemini for multiple-choice questions in JSON mode, and then validates every question before sending it to the browser: exactly four non-empty options, a valid answer index from 0 to 3, a real question string, and a numeric page. Anything malformed is dropped rather than shown.

---

## Design decisions

**Building the pipeline directly instead of using LangChain.** Every step (chunking, embedding, search, prompting, citation checking) is a small, readable function. That made retrieval problems easy to find and fix, and it means I can explain exactly what happens to a question at each stage.

**pgvector instead of a separate vector database.** The documents, their metadata and their vectors live in one PostgreSQL table. Filtering by document or session is an ordinary `WHERE` clause, and there is one less service to run, pay for and keep in sync.

**Local embeddings.** `fastembed` runs the embedding model on the server, so indexing a document costs nothing per call, works without a second API key, and keeps document text away from another third party. Gemini is used only for the rewrite, the answer and the quiz.

**HyDE, based on a real retrieval failure.** While testing, the question "How many days does the officer have to reply?" kept missing the section that sets the 30-day limit. Larger chunks did not fix it, and a plain keyword-style rewrite pulled in unrelated sections. Rewriting the question as a passage in the style of the Act did: the correct chunk entered the results, which is also why the search keeps the top 10 rather than the top 3.

**Citations are verified, not trusted.** The model is asked to cite pages, but the server only displays pages that the answer cites and that were actually retrieved. This removed a confusing behaviour where small talk such as "hi" showed a page number.

**Temporary, isolated uploads.** Uploaded chunks are tagged with a random session ID, so one visitor can never search another visitor's file. Each session is limited to three PDFs of 10 MB. Expired uploads are removed whenever a new upload arrives, which keeps the database small without needing a background job.

**Model output is validated.** Quiz questions come back as JSON, but the server still checks every field before using it, because language models occasionally return three options, an answer written as a letter, or a page number written as words.

**A frontend with no framework.** The interface is a single HTML file with plain JavaScript, served by FastAPI. All model output is escaped before it is displayed. Chat history lives in the browser only (see [Limitations](#limitations-and-next-steps)).

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL on Neon, pgvector, SQLAlchemy 2, psycopg 3 |
| PDF parsing | pypdf |
| Embeddings | fastembed with `BAAI/bge-small-en-v1.5` (384 dimensions, runs locally) |
| Language model | Google Gemini via the `google-genai` SDK (model set in `.env`) |
| Frontend | HTML, CSS and vanilla JavaScript |
| Testing | pytest, FastAPI TestClient, monkeypatch |

---

## Project structure

```
.
├── app/
│   ├── main.py          FastAPI app: routes, upload rules, error handling
│   ├── rag.py           Question answering: HyDE rewrite, search, grounded prompt, citation check
│   ├── quiz.py          Quiz generation and validation of model output
│   ├── search.py        Vector search and document listing queries
│   ├── ingest.py        PDF to chunks to embeddings to database
│   ├── pdf_loader.py    Text extraction, one entry per page
│   ├── chunking.py      Overlapping character chunks
│   ├── embedder.py      Local embedding model
│   ├── llm.py           Gemini client (plain text and JSON responses)
│   ├── cleanup.py       Deleting expired uploads, one document, or a whole session
│   ├── models.py        The chunks table (SQLAlchemy model with a vector column)
│   ├── database.py      Database connection
│   └── setup_db.py      One-command setup for a fresh database
├── static/
│   └── index.html       The whole user interface
├── tests/               21 unit tests
├── sample_docs/         RTI Act 2005 (built in) and a fictional cafe FAQ for testing uploads
├── docs/                Screenshots used in this README
├── requirements.txt     Pinned runtime dependencies
├── requirements-dev.txt Adds pytest for development
└── .env.example         The settings the app needs
```

---

## API

Interactive documentation is available at `/docs` (Swagger UI) when the server is running.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | The web interface |
| `GET` | `/documents` | Names of the built-in documents |
| `POST` | `/chat` | Answer a question. Body: `question`, optional `document` and `session_id` |
| `POST` | `/quiz` | Generate a quiz. Body: `document`, optional `session_id`, `count` from 1 to 10 |
| `POST` | `/upload` | Upload a PDF (multipart). Optional `session_id` query parameter |
| `DELETE` | `/session/{session_id}/documents/{document}` | Remove one uploaded PDF |
| `DELETE` | `/session/{session_id}` | Remove every upload in a session |
| `GET` | `/health` | Liveness check |
| `GET` | `/db-check` | Confirms the database connection |

Example response from `/chat`:

```json
{
  "answer": "The Public Information Officer must provide the information or reject the request within thirty days of receiving it (RTI Act 2005, page 11). If the information concerns the life or liberty of a person, it must be provided within forty-eight hours (RTI Act 2005, page 11).",
  "rewritten_query": "The Public Information Officer shall, as expeditiously as possible, and in any case within thirty days of the receipt of the request, provide the information...",
  "sources": [
    { "document": "RTI Act 2005", "page": 11, "distance": 0.162 }
  ]
}
```

Upload errors return clear messages: `400` for a file that is not a PDF or a fourth upload, `413` for a file over 10 MB, and `422` for a PDF with no readable text (for example a scanned image). If Gemini is unavailable, `/chat` and `/quiz` return `502` with a message the interface can show, and the full error is logged on the server.

---

## Running it locally

### Requirements

- Python 3.10 or newer (developed on 3.14)
- A PostgreSQL database with the pgvector extension available. A free [Neon](https://neon.tech) project works out of the box.
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com)

### Setup

```bash
git clone https://github.com/Srinikith4/ContextIQ_RAG.git
cd ContextIQ_RAG

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own values:

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Prepare the database. This enables pgvector, creates the table and loads the RTI Act. It is safe to run more than once.

```bash
python -m app.setup_db
```

```
Database ready: pgvector enabled, chunks table created.
Loaded RTI Act 2005: 69 chunks
```

Start the server:

```bash
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. To try uploads, use `sample_docs/BrewAndBloom_Cafe_FAQ.pdf`, a short fictional document written for testing.

The first start downloads the embedding model once and caches it, so later starts are quick.

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

The 21 tests run offline, in about three seconds, without touching the database or Gemini.

| File | What it covers |
|---|---|
| `test_chunking.py` | Short pages, splitting with the exact 300-character overlap, empty pages |
| `test_citations.py` | Reading cited pages from answers, and returning none for greetings or "not found" |
| `test_quiz.py` | Keeping valid questions and dropping malformed ones from model output |
| `test_upload.py` | Upload rules (non-PDF, size limit, three-file limit, unreadable PDF, session handling), using FastAPI's TestClient with the database calls replaced by fakes |

---

## Limitations and next steps

These are known and deliberate trade-offs for the current version.

- **Chat history is not saved.** There is no sign-in yet, so conversations live in the browser and clear on reload. The interface says this openly. The next step is user accounts and a conversations table.
- **Each question is answered on its own.** The server is stateless, so a follow-up like "and what about the penalty?" does not see the previous question. Passing recent messages to the model would fix this.
- **One search per document.** You cannot yet ask a single question across all your documents at once.
- **Expired uploads are cleaned up lazily**, when the next upload arrives, rather than on a timer.
- **Quiz page numbers come from the model** and are not yet checked against the retrieved chunks, the way answer citations are.
- **No vector index yet.** At this size an exact search is fast. For thousands of documents I would add an HNSW index in pgvector.
- **Uploaded documents are untrusted input.** A PDF could contain instructions aimed at the model. The prompt restricts the model to answering from context, but prompt injection is not fully solved here.

---

## Sample documents

- `sample_docs/RTI-Act_English.pdf`: The Right to Information Act, 2005, published by the Government of India.
- `sample_docs/BrewAndBloom_Cafe_FAQ.pdf`: A fictional cafe FAQ written for this project to test uploads. The cafe does not exist.

---

## Author

**J.V. Sri Nikith**

Built as a hands-on project to learn retrieval-augmented generation properly, from PDF parsing and vector search to prompt design, output validation and testing.
