from cma.retriever.fragments import (
    deduplicate_fragments,
    score_paragraph,
    select_fragments,
    split_paragraphs,
)


def test_split_paragraphs_basic():
    body = "First paragraph.\n\nSecond paragraph.\n\nThird."
    assert split_paragraphs(body) == ["First paragraph.", "Second paragraph.", "Third."]


def test_split_paragraphs_handles_extra_whitespace():
    body = "A\n\n\n   \n\nB"
    paragraphs = split_paragraphs(body)
    assert paragraphs == ["A", "B"]


def test_split_paragraphs_empty():
    assert split_paragraphs("") == []
    assert split_paragraphs("   \n\n  ") == []


def test_score_paragraph_overlap():
    score = score_paragraph(
        "Capital call processing is slow.", {"capital", "call", "processing"}
    )
    assert score == 1.0


def test_score_paragraph_partial_overlap():
    score = score_paragraph("Only one match here", {"only", "two", "tokens", "missing"})
    assert score == 0.25


def test_score_paragraph_empty_query():
    assert score_paragraph("anything", set()) == 0.0


def test_select_fragments_picks_top():
    body = (
        "Cooking rice in water.\n\n"
        "Capital call processing is the topic.\n\n"
        "Random unrelated paragraph about cats."
    )
    picks = select_fragments(body, "capital call processing", max_fragments=2)
    assert len(picks) <= 2
    assert "Capital call" in picks[0][0]


def test_select_fragments_fallback_returns_first_paragraph():
    body = "Just one paragraph here.\n\nAnother one."
    picks = select_fragments(body, "completely unrelated", max_fragments=3)
    # No tokens overlap, but fallback should still return at least one fragment
    assert len(picks) >= 1


def test_select_fragments_empty_body():
    assert select_fragments("", "query") == []


def test_deduplicate_keeps_higher_score():
    fragments = [
        ("a", "Capital call processing is the topic.", 0.9),
        ("b", "Capital call processing is the topic.", 0.4),
        ("c", "Different unrelated paragraph here.", 0.7),
    ]
    deduped = deduplicate_fragments(fragments)
    sources = {src for src, _, _ in deduped}
    assert "a" in sources
    assert "b" not in sources  # duplicate of a, lower score
    assert "c" in sources
