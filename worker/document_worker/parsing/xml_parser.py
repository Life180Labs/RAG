"""XML parser (lxml). Unlike JSON, XML documents are often prose-bearing
(e.g. DocBook, RSS), so each leaf element's text becomes its own
"paragraph" block rather than one opaque code blob."""

from lxml import etree


def parse(content: bytes) -> tuple[list[dict], int | None]:
    try:
        root = etree.fromstring(content)
    except etree.XMLSyntaxError:
        text = content.decode("utf-8", errors="replace")
        if not text.strip():
            return [], None
        return [{"type": "code", "text": text, "level": None, "page": None}], None

    blocks: list[dict] = []
    for element in root.iter():
        text = (element.text or "").strip()
        if text and len(list(element)) == 0:
            blocks.append({"type": "paragraph", "text": text, "level": None, "page": None})

    return blocks, None
