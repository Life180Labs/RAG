"""Sentence chunking (docs/02-architecture.md section 32) — splits
prose blocks into sentences, then merges consecutive sentences up to a
token budget. Table/code/image blocks have no sentence structure, so
each is kept as its own unit rather than being sentence-split."""

from chunk_worker.chunking.text_utils import split_sentences

DEFAULT_MAX_TOKENS = 200

_NON_SENTENCE_TYPES = {"image", "table", "code"}


def chunk_sentence(raw_text: str, spans: list[dict], config: dict) -> list[dict]:
    from chunk_worker.chunking.text_utils import merge_units_to_chunks

    max_tokens = config.get("max_tokens", DEFAULT_MAX_TOKENS)
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
            sentence_end = sentence_start + len(sentence)
            units.append((sentence_start, sentence_end))
            search_from = offset + len(sentence)

    return merge_units_to_chunks(raw_text, units, spans, max_tokens)
