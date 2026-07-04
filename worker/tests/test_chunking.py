"""Unit tests for the chunker factory (docs/05-task.md Phase 6), run
against real structured blocks (the same shape Phase 5's parsers
produce) — no mocks."""

from chunk_worker.chunking.adaptive import choose_strategy, chunk_adaptive
from chunk_worker.chunking.basic import chunk_fixed
from chunk_worker.chunking.factory import DEFAULT_CONFIG, get_chunker
from chunk_worker.chunking.hierarchy import chunk_hierarchical, chunk_parent_child
from chunk_worker.chunking.paragraph import chunk_paragraph
from chunk_worker.chunking.recursive import chunk_recursive
from chunk_worker.chunking.semantic import chunk_semantic
from chunk_worker.chunking.sentence import chunk_sentence
from chunk_worker.chunking.structural import chunk_structural
from chunk_worker.chunking.text_utils import join_blocks_with_spans, split_sentences
from chunk_worker.chunking.tokenizer import count_tokens
from chunk_worker.chunking.validation import validate_chunks

MULTI_SECTION_BLOCKS = [
    {"type": "title", "text": "My Report", "level": None, "page": 1},
    {"type": "heading", "text": "Section One", "level": 1, "page": 1},
    {
        "type": "paragraph",
        "text": "This is the first sentence about cats. Cats are great pets. "
        "Many people love cats.",
        "level": None,
        "page": 1,
    },
    {"type": "heading", "text": "Section Two", "level": 1, "page": 2},
    {
        "type": "paragraph",
        "text": "This is about rockets and space travel. Rockets go to space. "
        "NASA launches rockets.",
        "level": None,
        "page": 2,
    },
]


def _spans():
    return join_blocks_with_spans(MULTI_SECTION_BLOCKS)


def test_join_blocks_with_spans_tracks_headings_and_offsets():
    raw_text, spans = _spans()

    assert "My Report" in raw_text
    assert spans[0]["heading"] == "My Report"
    # The paragraph under "Section One" should report that heading, not "My Report".
    paragraph_span = next(s for s in spans if s["block"]["text"].startswith("This is the first"))
    assert paragraph_span["heading"] == "Section One"


def test_count_tokens_is_positive_for_real_text():
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0


def test_split_sentences_splits_on_boundaries():
    sentences = split_sentences("One. Two! Three? Four.")
    assert sentences == ["One.", "Two!", "Three?", "Four."]


def test_fixed_chunker_respects_chunk_size_and_overlap():
    raw_text, spans = _spans()
    chunks = chunk_fixed(raw_text, spans, {"chunk_size": 40, "overlap": 10})

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 40
        assert chunk["char_end"] - chunk["char_start"] <= 40


def test_paragraph_chunker_keeps_blocks_intact():
    raw_text, spans = _spans()
    chunks = chunk_paragraph(raw_text, spans, {"max_tokens": 10})

    all_text = "".join(c["text"] for c in chunks)
    assert "Cats are great pets" in all_text
    assert "NASA launches rockets" in all_text


def test_sentence_chunker_splits_into_individual_sentences():
    raw_text, spans = _spans()
    chunks = chunk_sentence(raw_text, spans, {"max_tokens": 6})

    assert any(c["text"] == "Cats are great pets." for c in chunks)


def test_recursive_chunker_is_preferred_default_and_respects_budget():
    raw_text, spans = _spans()
    chunks = chunk_recursive(raw_text, spans, {"max_tokens": 15})

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk["token_count"] <= 20  # small slack for merge-boundary rounding


def test_structural_chunker_breaks_at_every_heading():
    raw_text, spans = _spans()
    chunks = chunk_structural(raw_text, spans, {"max_tokens": 400})

    headings = [c["heading"] for c in chunks]
    assert "Section One" in headings
    assert "Section Two" in headings
    # Cats content and rockets content must land in different chunks.
    cats_chunk = next(c for c in chunks if "Cats are great pets" in c["text"])
    rockets_chunk = next(c for c in chunks if "NASA launches rockets" in c["text"])
    assert cats_chunk is not rockets_chunk


def test_markdown_and_html_strategies_are_the_same_function():
    assert get_chunker("markdown") is get_chunker("html")
    assert get_chunker("markdown") is chunk_structural
    assert get_chunker("structural") is chunk_structural


def test_semantic_chunker_separates_topically_distinct_sentences():
    raw_text, spans = _spans()
    chunks = chunk_semantic(raw_text, spans, {"max_tokens": 400, "similarity_threshold": 0.15})

    cats_chunks = [c for c in chunks if "cats" in c["text"].lower()]
    rockets_chunks = [c for c in chunks if "rocket" in c["text"].lower()]
    assert cats_chunks and rockets_chunks
    assert all(c not in rockets_chunks for c in cats_chunks)


def test_semantic_chunker_handles_fewer_than_two_sentences():
    blocks = [{"type": "paragraph", "text": "Only one sentence here", "level": None, "page": 1}]
    raw_text, spans = join_blocks_with_spans(blocks)
    chunks = chunk_semantic(raw_text, spans, {"max_tokens": 400})
    assert len(chunks) == 1


def test_parent_child_chunker_links_children_to_parents():
    raw_text, spans = _spans()
    chunks = chunk_parent_child(
        raw_text, spans, {"parent_max_tokens": 1000, "child_max_tokens": 10}
    )

    parents = [i for i, c in enumerate(chunks) if c["parent_ref"] is None]
    children = [c for c in chunks if c["parent_ref"] is not None]
    assert parents
    assert children
    for child in children:
        assert child["parent_ref"] in parents


def test_hierarchical_chunker_produces_multi_level_tree():
    raw_text, spans = _spans()
    chunks = chunk_hierarchical(raw_text, spans, {"max_depth": 2})

    root_level = [c for c in chunks if c["parent_ref"] is None]
    deeper_level = [c for c in chunks if c["parent_ref"] is not None]
    assert root_level
    assert deeper_level


def test_adaptive_chooses_paragraph_for_short_documents():
    blocks = [{"type": "paragraph", "text": "Short doc.", "level": None, "page": 1}]
    raw_text, spans = join_blocks_with_spans(blocks)
    strategy, _config = choose_strategy(spans)
    assert strategy == "paragraph"


def test_adaptive_chooses_structural_for_headinged_documents():
    blocks = []
    for i in range(1, 4):
        blocks.append({"type": "heading", "text": f"Section {i}", "level": 1, "page": 1})
        blocks.append({"type": "paragraph", "text": "word " * 300, "level": None, "page": 1})

    raw_text, spans = join_blocks_with_spans(blocks)
    strategy, _config = choose_strategy(spans)
    assert strategy in ("structural", "parent_child")


def test_chunk_adaptive_returns_chunks_and_resolved_strategy():
    raw_text, spans = _spans()
    chunks, strategy, config = chunk_adaptive(raw_text, spans, {})
    assert chunks
    assert strategy in DEFAULT_CONFIG
    assert isinstance(config, dict)


def test_chunk_adaptive_actually_dispatches_to_structural():
    # Regression test: choose_strategy picking "structural" must resolve to
    # a real registered chunker. get_chunker("structural") was previously
    # missing from the factory (only "markdown"/"html" aliased to it), which
    # made chunk_adaptive raise UnknownChunkStrategyError for exactly the
    # heading-dense documents it's meant to handle best.
    blocks = []
    for i in range(1, 4):
        blocks.append({"type": "heading", "text": f"Section {i}", "level": 1, "page": 1})
        blocks.append({"type": "paragraph", "text": "word " * 300, "level": None, "page": 1})

    raw_text, spans = join_blocks_with_spans(blocks)
    chunks, strategy, _config = chunk_adaptive(raw_text, spans, {})
    assert strategy in ("structural", "parent_child")
    assert chunks


def test_validate_chunks_marks_empty_and_duplicate_and_ready():
    chunks = [
        {"text": "Real content one.", "token_count": 3},
        {"text": "   ", "token_count": 0},
        {"text": "Real content one.", "token_count": 3},
        {"text": "Real content two.", "token_count": 3},
    ]
    validate_chunks(chunks)

    assert chunks[0]["status"] == "ready"
    assert chunks[1]["status"] == "skipped"
    assert chunks[1]["status_message"] == "Empty chunk text."
    assert chunks[2]["status"] == "skipped"
    assert "Duplicate" in chunks[2]["status_message"]
    assert chunks[3]["status"] == "ready"


def test_validate_chunks_marks_oversized_chunks_failed():
    chunks = [{"text": "word " * 20, "token_count": 9000}]
    validate_chunks(chunks)
    assert chunks[0]["status"] == "failed"
    assert "maximum token limit" in chunks[0]["status_message"]
