"""Fixed-size and sliding-window chunking (docs/02-architecture.md
section 33). Both are the same character-window algorithm; "sliding
window" is just "fixed size" with a non-zero `overlap` — registered as a
separate strategy name (with a different default config) because
that's a real, named deliverable in docs/05-task.md Phase 6, not because
the underlying code differs."""

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_OVERLAP = 0


def chunk_fixed(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.text_utils import make_chunk

    chunk_size = config.get("chunk_size", DEFAULT_CHUNK_SIZE)
    overlap = config.get("overlap", DEFAULT_OVERLAP)
    step = max(1, chunk_size - overlap)

    chunks: list[dict] = []
    n = len(raw_text)
    start = 0
    while start < n:
        end = min(start + chunk_size, n)
        chunk = make_chunk(raw_text, start, end, spans)
        if chunk["text"]:
            chunks.append(chunk)
        if end >= n:
            break
        start += step

    return chunks
