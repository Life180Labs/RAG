"""Chunker factory — maps a strategy name to its chunking function.

Every entry has the signature `(raw_text: str, spans: list[dict],
config: dict) -> list[dict]`. "adaptive" is deliberately not registered
here: it has a different signature (it also reports which concrete
strategy it picked), so callers that want it use
`chunk_worker.chunking.adaptive.chunk_adaptive` directly rather than
going through this uniform registry.
"""

from collections.abc import Callable

from chunk_worker.chunking.basic import chunk_fixed
from chunk_worker.chunking.hierarchy import chunk_hierarchical, chunk_parent_child
from chunk_worker.chunking.paragraph import chunk_paragraph
from chunk_worker.chunking.recursive import chunk_recursive
from chunk_worker.chunking.semantic import chunk_semantic
from chunk_worker.chunking.sentence import chunk_sentence
from chunk_worker.chunking.structural import chunk_structural

ChunkFn = Callable[[str, list[dict], dict], list[dict]]

_CHUNKERS: dict[str, ChunkFn] = {
    "fixed": chunk_fixed,
    "sliding_window": chunk_fixed,
    "recursive": chunk_recursive,
    "paragraph": chunk_paragraph,
    "sentence": chunk_sentence,
    "structural": chunk_structural,
    "markdown": chunk_structural,
    "html": chunk_structural,
    "semantic": chunk_semantic,
    "parent_child": chunk_parent_child,
    "hierarchical": chunk_hierarchical,
}

DEFAULT_CONFIG: dict[str, dict] = {
    "fixed": {"chunk_size": 1000, "overlap": 0},
    "sliding_window": {"chunk_size": 1000, "overlap": 200},
    "recursive": {"max_tokens": 400},
    "paragraph": {"max_tokens": 400},
    "sentence": {"max_tokens": 200},
    "structural": {"max_tokens": 400},
    "markdown": {"max_tokens": 400},
    "html": {"max_tokens": 400},
    "semantic": {"max_tokens": 400, "similarity_threshold": 0.25},
    "parent_child": {"parent_max_tokens": 1200, "child_max_tokens": 300},
    "hierarchical": {"max_depth": 3},
}


class UnknownChunkStrategyError(ValueError):
    pass


def get_chunker(strategy: str) -> ChunkFn:
    chunker = _CHUNKERS.get(strategy)
    if chunker is None:
        raise UnknownChunkStrategyError(f"No chunker registered for strategy '{strategy}'.")
    return chunker


def default_config(strategy: str) -> dict:
    return dict(DEFAULT_CONFIG.get(strategy, {}))
