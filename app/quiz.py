import random

from app.llm import generate_json
from app.search import get_document_chunks

QUIZ_PROMPT = """Write {count} multiple-choice questions that test understanding of the text below.
Rules:
- Use ONLY facts stated in the text.
- Each question has exactly 4 options and exactly one correct answer.
- Mix easy and harder questions, and cover different parts of the text.
- Write each question so it stands alone. Do not say "the text" or "the passage".
- Return a JSON list. Each item has these keys:
  "question" (string), "options" (list of 4 strings), "answer_index" (0 to 3),
  "explanation" (one short sentence), "page" (the page number where the answer is).

Text:
{context}"""


def pick_chunks(chunks, max_chunks=8):
    if len(chunks) <= max_chunks:
        return chunks
    return sorted(random.sample(chunks, max_chunks), key=lambda c: c["page"])


def clean_questions(raw):
    if isinstance(raw, dict):
        raw = raw.get("questions", [])
    cleaned = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        question = item.get("question")
        options = item.get("options")
        answer = item.get("answer_index")
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(options, list) or len(options) != 4:
            continue
        if not all(isinstance(o, str) and o.strip() for o in options):
            continue
        if not isinstance(answer, int) or isinstance(answer, bool) or not 0 <= answer <= 3:
            continue
        page = item.get("page")
        cleaned.append(
            {
                "question": question.strip(),
                "options": [o.strip() for o in options],
                "answer_index": answer,
                "explanation": str(item.get("explanation", "")).strip(),
                "page": page if isinstance(page, int) else None,
            }
        )
    return cleaned


def make_quiz(document, session_id=None, count=5):
    chunks = get_document_chunks(document, session_id)
    if not chunks:
        return None
    picked = pick_chunks(chunks)
    context = "\n\n".join(f"[page {c['page']}]\n{c['text']}" for c in picked)
    raw = generate_json(QUIZ_PROMPT.format(count=count, context=context))
    return clean_questions(raw)[:count]
