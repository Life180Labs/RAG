"""Metadata filter extraction (docs/05-task.md Phase 11;
docs/02-architecture.md section 55 Metadata Detection).

Scope note: section 55's own example ("Show HR policies after 2024" ->
Department=HR, Year>=2024) extracts filters this system's retrieval
layer cannot actually apply. Phase 9/10 already fixed
`metadata_filter` to exactly three keys — `heading`, `page`,
`language` (see `worker/index_worker/providers/pgvector_provider.py`'s
`_FILTERABLE_CHUNK_COLUMNS`) — because those are the only fields
chunking ever attaches to a chunk row. There is no department or
publication-year column anywhere in the chunk schema, so extracting
one here would produce a filter silently ignored by every provider's
`search()`. Rather than build detection for filters nothing downstream
can use, this module only extracts the three keys real filtering
supports:

- `language`: an explicit language name in the query ("...in French").
- `page`: an explicit page reference ("...on page 5").
- `heading`: a quoted phrase, treated as a candidate exact heading
  match (best-effort/low-recall by nature — it only fires when the
  user quotes the section they mean).
"""

import re

_LANGUAGE_NAMES: dict[str, str] = {
    "english": "en",
    "french": "fr",
    "spanish": "es",
    "german": "de",
    "chinese": "zh",
    "japanese": "ja",
    "portuguese": "pt",
    "italian": "it",
}
_LANGUAGE_PATTERN = re.compile(
    r"\bin (" + "|".join(_LANGUAGE_NAMES) + r")\b", re.IGNORECASE
)
_PAGE_PATTERN = re.compile(r"\bp(?:age)?\.?\s*(\d+)\b", re.IGNORECASE)
_HEADING_PATTERN = re.compile(r'"([^"]{2,100})"')


def extract(query_text: str) -> dict[str, str]:
    filters: dict[str, str] = {}

    language_match = _LANGUAGE_PATTERN.search(query_text)
    if language_match:
        filters["language"] = _LANGUAGE_NAMES[language_match.group(1).lower()]

    page_match = _PAGE_PATTERN.search(query_text)
    if page_match:
        filters["page"] = page_match.group(1)

    heading_match = _HEADING_PATTERN.search(query_text)
    if heading_match:
        filters["heading"] = heading_match.group(1)

    return filters
