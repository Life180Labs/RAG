"""Markdown parser (markdown-it-py). Images are found via a raw regex
pass over the source rather than the token stream, since `![alt](url)`
tokens are nested inline children rather than top-level block tokens."""

import re

from markdown_it import MarkdownIt

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")


def parse(content: bytes) -> tuple[list[dict], int | None]:
    text = content.decode("utf-8", errors="replace")
    md = MarkdownIt()
    tokens = md.parse(text)

    blocks: list[dict] = []
    title_assigned = False
    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            level = int(token.tag[1])
            inline = tokens[i + 1]
            block_type = "heading" if title_assigned else "title"
            title_assigned = True
            blocks.append(
                {
                    "type": block_type,
                    "text": inline.content,
                    "level": level if block_type == "heading" else None,
                    "page": None,
                }
            )
            i += 3
            continue

        if token.type == "paragraph_open":
            inline = tokens[i + 1]
            content = inline.content.strip()
            # A paragraph that's *only* an image (`![alt](url)`) is picked up
            # by the image regex pass below instead — otherwise it'd be
            # double-counted as both a paragraph and an image block.
            if content and not _IMAGE_RE.fullmatch(content):
                blocks.append(
                    {"type": "paragraph", "text": inline.content, "level": None, "page": None}
                )
            i += 3
            continue

        if token.type in ("bullet_list_open", "ordered_list_open"):
            depth = 1
            i += 1
            items = []
            while i < len(tokens) and depth > 0:
                nested = tokens[i]
                if nested.type in ("bullet_list_open", "ordered_list_open"):
                    depth += 1
                elif nested.type in ("bullet_list_close", "ordered_list_close"):
                    depth -= 1
                elif nested.type == "inline":
                    items.append(nested.content)
                i += 1
            if items:
                blocks.append(
                    {"type": "list", "text": "\n".join(items), "level": None, "page": None}
                )
            continue

        if token.type == "fence":
            blocks.append({"type": "code", "text": token.content, "level": None, "page": None})
            i += 1
            continue

        if token.type == "table_open":
            depth = 1
            i += 1
            cells = []
            while i < len(tokens) and depth > 0:
                nested = tokens[i]
                if nested.type == "table_open":
                    depth += 1
                elif nested.type == "table_close":
                    depth -= 1
                elif nested.type == "inline":
                    cells.append(nested.content)
                i += 1
            if cells:
                blocks.append(
                    {"type": "table", "text": "\n".join(cells), "level": None, "page": None}
                )
            continue

        i += 1

    for match in _IMAGE_RE.finditer(text):
        alt = match.group(1) or "[Image]"
        blocks.append({"type": "image", "text": alt, "level": None, "page": None})

    return blocks, None
