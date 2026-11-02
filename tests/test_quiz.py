from app.quiz import clean_questions

GOOD = {
    "question": "How many days to reply?",
    "options": ["10", "30", "45", "60"],
    "answer_index": 1,
    "explanation": "Section 7 says 30 days.",
    "page": 11,
}


def test_good_question_is_kept():
    assert clean_questions([GOOD]) == [GOOD]


def test_accepts_questions_wrapped_in_a_dict():
    assert clean_questions({"questions": [GOOD]}) == [GOOD]


def test_wrong_number_of_options_is_dropped():
    bad = {**GOOD, "options": ["10", "30", "45"]}
    assert clean_questions([bad]) == []


def test_answer_index_out_of_range_is_dropped():
    bad = {**GOOD, "answer_index": 4}
    assert clean_questions([bad]) == []


def test_missing_question_is_dropped():
    bad = {**GOOD, "question": ""}
    assert clean_questions([bad]) == []


def test_bad_page_becomes_none():
    item = {**GOOD, "page": "eleven"}
    assert clean_questions([item])[0]["page"] is None


def test_only_good_items_survive_a_mixed_list():
    bad = {**GOOD, "answer_index": "B"}
    assert clean_questions([GOOD, bad, "junk"]) == [GOOD]
