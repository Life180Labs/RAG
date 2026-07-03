"""HTML parser (BeautifulSoup + lxml)."""

from bs4 import BeautifulSoup

_BLOCK_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "table", "img"]


def parse(content: bytes) -> tuple[list[dict], int | None]:
    soup = BeautifulSoup(content, "lxml")
    blocks: list[dict] = []
    title_assigned = False

    for element in soup.find_all(_BLOCK_TAGS):
        # Skip elements nested inside another already-visited block element
        # (e.g. <li> inside a <table>, or <p> inside a <li>) to avoid
        # double-counting the same text as two blocks.
        if element.find_parent(_BLOCK_TAGS) is not None:
            continue

        if element.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = element.get_text(strip=True)
            if not text:
                continue
            level = int(element.name[1])
            block_type = "heading" if title_assigned else "title"
            title_assigned = True
            blocks.append(
                {
                    "type": block_type,
                    "text": text,
                    "level": level if block_type == "heading" else None,
                    "page": None,
                }
            )
        elif element.name == "p":
            text = element.get_text(strip=True)
            if text:
                blocks.append({"type": "paragraph", "text": text, "level": None, "page": None})
        elif element.name == "li":
            text = element.get_text(strip=True)
            if text:
                blocks.append({"type": "list", "text": text, "level": None, "page": None})
        elif element.name == "pre":
            text = element.get_text()
            if text.strip():
                blocks.append({"type": "code", "text": text, "level": None, "page": None})
        elif element.name == "table":
            rows = []
            for tr in element.find_all("tr"):
                cells = [cell.get_text(strip=True) for cell in tr.find_all(["td", "th"])]
                rows.append(" | ".join(cells))
            text = "\n".join(rows)
            if text.strip():
                blocks.append({"type": "table", "text": text, "level": None, "page": None})
        elif element.name == "img":
            alt = element.get("alt") or "[Image]"
            blocks.append({"type": "image", "text": alt, "level": None, "page": None})

    return blocks, None
