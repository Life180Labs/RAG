"""Chunk validation (docs/02-architecture.md section 39). Every chunk
ends up READY, FAILED, or SKIPPED — never silently dropped, so
exclusion from later phases (embedding) stays visible and auditable.
"""

import hashlib

MIN_TOKENS = 1
HARD_MAX_TOKENS = 8000
REPLACEMENT_CHAR = "�"
MAX_REPLACEMENT_RATIO = 0.05


def _content_hash(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def validate_chunks(chunks: list[dict]) -> list[dict]:
    """Annotates each chunk dict in place with `status`/`status_message`
    and returns the same list (order preserved, nothing removed)."""
    seen_hashes: set[str] = set()

    for chunk in chunks:
        text = chunk.get("text", "")

        if not text.strip():
            chunk["status"] = "skipped"
            chunk["status_message"] = "Empty chunk text."
            continue

        if chunk.get("token_count", 0) < MIN_TOKENS:
            chunk["status"] = "skipped"
            chunk["status_message"] = "Below minimum token count."
            continue

        replacement_count = text.count(REPLACEMENT_CHAR)
        if replacement_count and replacement_count / len(text) > MAX_REPLACEMENT_RATIO:
            chunk["status"] = "failed"
            chunk["status_message"] = "Text contains excessive invalid-encoding characters."
            continue

        if chunk.get("token_count", 0) > HARD_MAX_TOKENS:
            chunk["status"] = "failed"
            chunk["status_message"] = f"Chunk exceeds the maximum token limit ({HARD_MAX_TOKENS})."
            continue

        content_hash = _content_hash(text)
        if content_hash in seen_hashes:
            chunk["status"] = "skipped"
            chunk["status_message"] = "Duplicate content within this chunk set."
            continue
        seen_hashes.add(content_hash)

        chunk["status"] = "ready"
        chunk["status_message"] = None

    return chunks
