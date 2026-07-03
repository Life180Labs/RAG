"""JSON parser (native `json` module). JSON is a data format, not prose —
the whole document becomes a single pretty-printed "code" block."""

import json


def parse(content: bytes) -> tuple[list[dict], int | None]:
    text = content.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        pretty = text

    if not pretty.strip():
        return [], None
    return [{"type": "code", "text": pretty, "level": None, "page": None}], None
