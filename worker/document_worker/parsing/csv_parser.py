"""CSV parser (pandas, per docs/02-architecture.md section 25). A CSV is
tabular by definition, so the whole file becomes a single "table" block
rather than being split into paragraphs."""

import io

import pandas as pd


def parse(content: bytes) -> tuple[list[dict], int | None]:
    dataframe = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False)
    rows = [" | ".join(dataframe.columns)]
    rows.extend(" | ".join(row) for row in dataframe.itertuples(index=False, name=None))
    text = "\n".join(rows)
    if not text.strip():
        return [], None
    return [{"type": "table", "text": text, "level": None, "page": None}], None
