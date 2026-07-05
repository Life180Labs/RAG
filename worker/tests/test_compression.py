"""Unit tests for context compression (docs/05-task.md Phase 12;
docs/02-architecture.md section 75)."""

from retrieval_worker.compression import compress


def test_keeps_only_sentences_overlapping_the_query():
    chunk_text = (
        "The company was founded in 1998. Vacation policy grants twenty days per year. "
        "The office is located downtown."
    )
    result = compress(chunk_text, "what is the vacation policy")
    assert "Vacation policy grants twenty days per year." in result
    assert "The company was founded in 1998." not in result
    assert "The office is located downtown." not in result


def test_falls_back_to_best_sentence_when_no_lexical_overlap():
    chunk_text = "Alpha beta gamma. Delta epsilon zeta."
    result = compress(chunk_text, "zzz nonexistent tokens")
    assert result in ("Alpha beta gamma.", "Delta epsilon zeta.")


def test_returns_original_text_for_blank_query():
    chunk_text = "Some chunk text here."
    assert compress(chunk_text, "   ") == chunk_text


def test_returns_original_text_for_empty_chunk():
    assert compress("", "some query") == ""
