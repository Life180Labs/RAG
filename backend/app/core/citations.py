"""Citation Engine (docs/05-task.md Phase 14; docs/02-architecture.md
section 80).

Each citation stores Document / Page / Section / Chunk ID / Confidence,
one per `ContextEntry` the Context Window Builder decided to include —
citation index (`source_label`, e.g. "Source 1") matches the `[Source N]`
marker `context_window.build_context_window` writes into the assembled
context text, so a downstream LLM instructed to cite "Source N" can be
mapped straight back to this list.

`confidence` is a best-effort proxy, not a calibrated probability: it is
whichever relevance signal ordered the retrieval (`rerank_score` when
reranking ran, else `score`), clamped into `[0.0, 1.0]`. Cosine
similarity and cross-encoder scores are not the same scale as a true
"P(this chunk supports the answer)" estimate — clamping means a
dot-product/euclidean score or a negative cross-encoder logit can floor
to 0.0. This is documented rather than hidden behind a fabricated
calibration model, matching this codebase's "real, not invented" values
convention (see `worker/retrieval_worker/reranking/` provider docstrings).
"""

from app.core.context_window import ContextEntry


def build_citations(entries: list[ContextEntry], *, document_filename: str) -> list[dict]:
    return [
        {
            "source_label": f"Source {i}",
            "document_id": entry.document_id,
            "document_filename": document_filename,
            "page": entry.page,
            "section": entry.heading,
            "chunk_id": entry.chunk_id,
            "confidence": entry.confidence,
        }
        for i, entry in enumerate(entries, start=1)
    ]
