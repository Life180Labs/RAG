"""Semantic chunking (docs/02-architecture.md section 35) — uses TF-IDF
cosine similarity between adjacent sentences as its boundary-detection
signal (sentence "embeddings" -> similarity -> boundary detection ->
chunk creation), rather than dense neural embeddings.

This is a deliberate, real technique (the classical approach behind
algorithms like TextTiling), not a stub — but it's a *lighter-weight*
semantic signal than a transformer embedding model. Phase 7 (Embedding
Pipeline) is expected to introduce a second, embedding-model-based
semantic strategy once a provider actually exists; pulling in a full
neural embedding model here, before that phase, would be exactly the
kind of premature, undirected dependency the engineering rules warn
against.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_MAX_TOKENS = 400
DEFAULT_SIMILARITY_THRESHOLD = 0.25
_NON_SENTENCE_TYPES = {"image", "table", "code"}


def _sentence_units(raw_text: str, spans: list[dict]) -> list[tuple[int, int]]:
    from chunk_worker.chunking.text_utils import split_sentences

    units: list[tuple[int, int]] = []
    for span in spans:
        block = span["block"]
        if block["type"] == "image":
            continue
        if block["type"] in _NON_SENTENCE_TYPES:
            units.append((span["start"], span["end"]))
            continue

        block_text = raw_text[span["start"] : span["end"]]
        search_from = 0
        for sentence in split_sentences(block_text):
            offset = block_text.index(sentence, search_from)
            sentence_start = span["start"] + offset
            units.append((sentence_start, sentence_start + len(sentence)))
            search_from = offset + len(sentence)
    return units


def chunk_semantic(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.text_utils import merge_units_to_chunks

    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
    threshold = config.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD)

    units = _sentence_units(raw_text, spans)
    if len(units) < 2:
        return merge_units_to_chunks(raw_text, units, spans, max_tokens)

    sentences = [raw_text[start:end] for start, end in units]
    try:
        matrix = TfidfVectorizer(stop_words="english").fit_transform(sentences)
    except ValueError:
        # Empty vocabulary after stopword removal (e.g. every "sentence"
        # is just punctuation/numbers) — fall back to token-budget-only
        # merging rather than crashing the whole chunking run over it.
        return merge_units_to_chunks(raw_text, units, spans, max_tokens)

    similarities = cosine_similarity(matrix[:-1], matrix[1:]).diagonal()
    force_break_before = {i + 1 for i, sim in enumerate(similarities) if sim < threshold}

    return merge_units_to_chunks(
        raw_text, units, spans, max_tokens, force_break_before=force_break_before
    )
