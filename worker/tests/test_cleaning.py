from document_worker.parsing import cleaning


def test_normalize_text_handles_smart_quotes_dashes_and_whitespace():
    text = 'He said “hello”—then\t\tpaused.\n\n\n\nMore text.'

    result = cleaning.normalize_text(text)

    assert result == 'He said "hello"-then paused.\n\nMore text.'


def test_clean_blocks_removes_repeated_headers_and_page_numbers():
    blocks = [
        {"type": "paragraph", "text": "Company Confidential", "level": None, "page": 1},
        {"type": "paragraph", "text": "Artificial", "level": None, "page": 1},
        {
            "type": "paragraph",
            "text": "Intelligence is transforming the world.",
            "level": None,
            "page": 1,
        },
        {"type": "paragraph", "text": "18", "level": None, "page": 1},
        {"type": "paragraph", "text": "Company Confidential", "level": None, "page": 2},
        {"type": "paragraph", "text": "Company Confidential", "level": None, "page": 3},
    ]

    cleaned = cleaning.clean_blocks(blocks)

    assert [b["text"] for b in cleaned] == ["Artificial", "Intelligence is transforming the world."]


def test_clean_blocks_never_touches_table_code_or_image_blocks():
    blocks = [
        {"type": "code", "text": "  x = 1   ", "level": None, "page": None},
        {"type": "table", "text": "a | b", "level": None, "page": None},
        {"type": "image", "text": "[Image]", "level": None, "page": None},
    ]

    cleaned = cleaning.clean_blocks(blocks)

    assert cleaned == blocks


def test_clean_blocks_drops_empty_prose_blocks():
    blocks = [
        {"type": "paragraph", "text": "   ", "level": None, "page": None},
        {"type": "paragraph", "text": "Real content.", "level": None, "page": None},
    ]

    cleaned = cleaning.clean_blocks(blocks)

    assert len(cleaned) == 1
    assert cleaned[0]["text"] == "Real content."
