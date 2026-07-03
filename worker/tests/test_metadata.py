from document_worker.parsing import metadata


def test_compute_metadata_counts_words_and_characters():
    blocks = [
        {"type": "paragraph", "text": "one two three", "level": None, "page": None},
        {"type": "paragraph", "text": "four five", "level": None, "page": None},
        {"type": "image", "text": "[Image]", "level": None, "page": None},
    ]

    result = metadata.compute_metadata(blocks, page_count=3)

    assert result["word_count"] == 5
    assert result["raw_text"] == "one two three\n\nfour five"
    assert result["character_count"] == len("one two three\n\nfour five")
    assert result["page_count"] == 3
    assert result["reading_time_seconds"] >= 1


def test_detect_language_identifies_english():
    text = "The quick brown fox jumps over the lazy dog near the riverbank."

    assert metadata.detect_language(text) == "en"


def test_detect_language_returns_none_for_empty_text():
    assert metadata.detect_language("") is None


def test_compute_metadata_zero_words_gives_zero_reading_time():
    result = metadata.compute_metadata([], page_count=None)

    assert result["word_count"] == 0
    assert result["reading_time_seconds"] == 0
    assert result["language"] is None
