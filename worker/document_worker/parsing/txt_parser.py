"""Plain-text parser. TXT has no structural markup, so the only
structure inferred is: the first short line is treated as a "title", and
the rest is split into "paragraph" blocks on blank-line boundaries."""

_TITLE_MAX_CHARS = 100


def parse(content: bytes) -> tuple[list[dict], int | None]:
    text = content.decode("utf-8", errors="replace")
    paragraphs = [p.strip() for p in text.split("\n\n")]
    paragraphs = [p for p in paragraphs if p]

    blocks: list[dict] = []
    for index, paragraph in enumerate(paragraphs):
        if index == 0 and len(paragraph) <= _TITLE_MAX_CHARS and "\n" not in paragraph:
            blocks.append({"type": "title", "text": paragraph, "level": None, "page": None})
        else:
            blocks.append({"type": "paragraph", "text": paragraph, "level": None, "page": None})

    return blocks, None
