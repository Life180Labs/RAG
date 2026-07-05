"""Context compression (docs/05-task.md Phase 12; docs/02-architecture.md
section 75 Context Compression).

Lexical (token-overlap) sentence scoring, not embedding-based — the
same "real but deliberately bounded" scope choice Phase 10 made for
BM25: scoring every candidate chunk's individual sentences against the
query via a fresh embedding call at retrieval time would add real
latency and cost this phase doesn't need to pay for a working
compression step. Keeps every sentence that shares at least one token
with the query; if none do (a purely semantic match with no lexical
overlap at all), falls back to the single sentence with the highest
raw overlap count rather than ever returning empty text.
"""

import re

from common.text_utils import split_sentences

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# A fixed English stopword list, not a full NLP library — without
# filtering these, almost every sentence in ordinary prose shares
# "the"/"is"/"a" with almost every query, making token-overlap scoring
# nearly useless in practice (every sentence "overlaps").
_STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
        "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was",
        "were", "what", "when", "where", "which", "who", "will", "with",
    }
)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(text.lower())) - _STOPWORDS


def compress(chunk_text: str, query_text: str) -> str:
    query_tokens = _tokenize(query_text)
    sentences = split_sentences(chunk_text)
    if not query_tokens or not sentences:
        return chunk_text

    scored = [(sentence, len(_tokenize(sentence) & query_tokens)) for sentence in sentences]
    kept = [sentence for sentence, overlap in scored if overlap > 0]
    if not kept:
        kept = [max(scored, key=lambda pair: pair[1])[0]]
    return " ".join(kept)
