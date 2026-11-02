import re

from app.llm import generate_answer
from app.search import search_chunk

REWRITE_PROMPT = """Write a one or two sentence passage, in the style of the official document that would contain the answer (for example a law, a policy, a manual or an FAQ), that directly answers this question.
It is only used for searching, so a best guess is fine. Return only the passage.

Question: {question}"""

PROMPT = """You are an assistant that answers questions using ONLY the context below.
Cite the document and page for each fact like (RTI Act 2005, page 11).
If the answer is not in the context, say you could not find it in the uploaded documents.
If the question is a greeting or small talk, reply briefly and do not cite anything.
If the user asks what they can ask or what the document is about, briefly list the main topics covered in the context and suggest two or three example questions, without citations.

Context:
{context}

Question: {question}

Answer:"""


def cited_pages(answer):
    """Page numbers the answer actually cites, e.g. "(RTI Act 2005, page 11)" or "pages 11 and 13"."""
    pages = set()
    for match in re.finditer(r"pages?\s+(\d+(?:\s*(?:,|and|&|-)\s*\d+)*)", answer, re.IGNORECASE):
        pages.update(int(n) for n in re.findall(r"\d+", match.group(1)))
    return pages


def answer_question(question, session_id=None, document=None, top_k=10):
    rewritten = generate_answer(
        REWRITE_PROMPT.format(question=question)).strip()

    best = {}
    for query in (question, rewritten):
        for hit in search_chunk(query, top_k=top_k, session_id=session_id, document=document):
            old = best.get(hit["text"])
            if old is None or hit["distance"] < old["distance"]:
                best[hit["text"]] = hit
    hits = sorted(best.values(), key=lambda h: h["distance"])

    context = "\n\n".join(
        f"[{h['document']}, page {h['page']}]\n{h['text']}" for h in hits
    )
    answer = generate_answer(PROMPT.format(context=context, question=question))

    # Only return pages the answer really used, so a greeting or "not found" shows no page.
    used = cited_pages(answer)
    sources, seen = [], set()
    for h in hits:
        key = (h["document"], h["page"])
        if h["page"] in used and key not in seen:
            seen.add(key)
            sources.append({
                "document": h["document"],
                "page": h["page"],
                "distance": round(h["distance"], 3),
            })
    return {"answer": answer, "rewritten_query": rewritten, "sources": sources}
