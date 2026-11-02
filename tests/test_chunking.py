from app.chunking import chunk_pages


def test_short_page_is_one_chunk():
    pages = [{"page": 1, "text": "Hello world"}]
    assert chunk_pages(pages) == [{"page": 1, "text": "Hello world"}]


def test_long_page_is_split_with_overlap():
    # 2000 characters: 0123456789...
    text = "".join(str(i % 10) for i in range(2000))
    chunks = chunk_pages([{"page": 3, "text": text}],
                         chunk_size=1500, overlap=300)

    assert len(chunks) == 2
    # first chunk: characters 0 to 1499
    assert chunks[0]["text"] == text[:1500]
    # second starts 300 back, at 1200
    assert chunks[1]["text"] == text[1200:]
    # the 300-character overlap
    assert chunks[0]["text"][-300:] == chunks[1]["text"][:300]
    # page number is kept
    assert all(c["page"] == 3 for c in chunks)


def test_empty_page_gives_no_chunks():
    assert chunk_pages([{"page": 1, "text": "   "}]) == []
