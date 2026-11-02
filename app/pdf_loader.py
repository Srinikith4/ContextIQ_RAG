from pypdf import PdfReader


def extract_pages(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": number, "text": text})
    return pages
