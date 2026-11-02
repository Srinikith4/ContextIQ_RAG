def chunk_pages(pages, chunk_size=1500, overlap=300):
    chunks = []
    for page in pages:
        text = page["text"].strip()
        start = 0
        while start < len(text):
            end = start + chunk_size
            piece = text[start:end]
            if piece.strip():
                chunks.append({"page": page["page"], "text": piece})
            if end >= len(text):
                break
            start = end - overlap
    return chunks
