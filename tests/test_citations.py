from app.rag import cited_pages


def test_greeting_has_no_pages():
    assert cited_pages("Hello! How can I help you?") == set()


def test_not_found_has_no_pages():
    assert cited_pages(
        "I could not find it in the uploaded documents.") == set()


def test_single_citation():
    assert cited_pages("Reply within 30 days (RTI Act 2005, page 11).") == {11}


def test_several_citations():
    answer = "See (RTI Act 2005, pages 11 and 13) and (RTI Act 2005, page 20)."
    assert cited_pages(answer) == {11, 13, 20}


def test_list_of_pages():
    assert cited_pages("Pages 4, 5 & 7 explain this.") == {4, 5, 7}
