"""Context Window Builder (docs/05-task.md Phase 14; docs/02-architecture.md
section 77).

Pipeline: Top Chunks -> Compression -> Deduplication -> Ordering ->
Citation Attachment -> Context Window. "Top Chunks" is the retrieval's
already-ranked `RetrievalResult` rows (selection already happened at
retrieval time via `top_k`/`score_threshold`); this module's job is
picking which of those fit the token budget and in what order to present
them.

Selection happens in *relevance* order (`rank`, ascending — the same
order Phase 9-13 already established as "best first," honoring
whichever of Phase 13's `rerank_score` or the base `score` that pipeline
used to sort). Only after the included subset is fixed does this module
apply the *display* order — this matters because trimming to budget in
display order could silently drop a highly relevant chunk in favor of a
less relevant one that merely sorts earlier for display, which would
violate "highest relevance first" (docs/02-architecture.md section 77).

"Same document continuity" (the section 77 ordering's #2 priority) is
automatically satisfied here rather than needing its own grouping logic:
`Retrieval` is architecturally scoped to a single document
(`backend/app/models/retrieval.py` — every retrieval targets one
`vector_index_id`/`document_id`), so every chunk in one retrieval's
results already belongs to the same document by construction. The only
real ordering choice left is #3, "chronological order (optional)" —
exposed here as `order_by_page`, which re-sorts the *included* subset by
`Chunk.page` ascending for a more linear reading experience; relevance
order (the default) is used when the flag is off.

Compression reuses Phase 12's `RetrievalResult.compressed_text` when
present (a retrieval run with `compress_context=True`) rather than
recomputing anything here — this module has no opinion on compression
strategy, it just prefers the shorter text when available.
"""

from dataclasses import dataclass

from app.core.token_budget import count_tokens
from app.models.chunk import Chunk
from app.models.retrieval import RetrievalResult


@dataclass
class ContextEntry:
    chunk_id: str
    document_id: str
    text: str
    tokens: int
    page: int | None
    heading: str | None
    rank: int
    confidence: float


def _text_for(result: RetrievalResult) -> str:
    return result.compressed_text if result.compressed_text else ""


def _confidence_for(result: RetrievalResult) -> float:
    raw = result.rerank_score if result.rerank_score is not None else result.score
    return round(max(0.0, min(1.0, raw)), 4)


def build_context_window(
    rows: list[tuple[RetrievalResult, Chunk]],
    *,
    document_id: str,
    token_budget: int,
    order_by_page: bool = False,
) -> tuple[str, list[ContextEntry]]:
    """Returns `(context_text, included_entries)`. `included_entries` is
    already in final display order; `context_text` joins their text with
    a `[Source N]` marker per entry, N matching the citation index the
    caller attaches (docs/02-architecture.md section 80)."""

    seen_chunk_ids: set[str] = set()
    candidates: list[ContextEntry] = []
    for result, chunk in sorted(rows, key=lambda pair: pair[0].rank):
        chunk_id = str(chunk.id)
        if chunk_id in seen_chunk_ids:
            continue
        text = _text_for(result) or chunk.text
        if not text:
            continue
        seen_chunk_ids.add(chunk_id)
        candidates.append(
            ContextEntry(
                chunk_id=chunk_id,
                document_id=document_id,
                text=text,
                tokens=count_tokens(text),
                page=chunk.page,
                heading=chunk.heading,
                rank=result.rank,
                confidence=_confidence_for(result),
            )
        )

    included: list[ContextEntry] = []
    remaining = token_budget
    for entry in candidates:
        if entry.tokens > remaining:
            continue
        included.append(entry)
        remaining -= entry.tokens

    display_order = (
        sorted(included, key=lambda e: (e.page is None, e.page or 0))
        if order_by_page
        else sorted(included, key=lambda e: e.rank)
    )

    parts = [f"[Source {i}]\n{entry.text}" for i, entry in enumerate(display_order, start=1)]
    return "\n\n".join(parts), display_order
