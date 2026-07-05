"""Unit tests for metadata filter extraction (docs/05-task.md Phase 11;
docs/02-architecture.md section 55). Scoped to the three keys the
retrieval layer actually supports — see filter_extractor.py's docstring
for why department/date-range filters aren't extracted."""

from retrieval_worker.query_understanding.filter_extractor import extract


def test_extracts_language():
    assert extract("Show me this document in French") == {"language": "fr"}


def test_extracts_page():
    assert extract("What does it say on page 42?") == {"page": "42"}


def test_extracts_heading_from_quoted_phrase():
    assert extract('What does the "Termination Clause" section say?') == {
        "heading": "Termination Clause"
    }


def test_extracts_multiple_keys_at_once():
    result = extract('On page 3, in French, under "Overview" what is stated?')
    assert result == {"language": "fr", "page": "3", "heading": "Overview"}


def test_returns_empty_dict_when_nothing_detected():
    assert extract("What is the leave policy for contractors?") == {}
