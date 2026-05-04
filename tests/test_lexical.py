from cma.retriever.lexical import BM25Index, tokenize
from cma.schemas.memory_record import MemoryRecord


def _rec(rid: str, title: str, body: str) -> MemoryRecord:
    return MemoryRecord(record_id=rid, type="note", title=title, path=f"{rid}.md", body=body)


def test_tokenize_lowercases_and_splits():
    assert tokenize("Hello, World! 42 things.") == ["hello", "world", "42", "things"]


def test_tokenize_empty():
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_bm25_returns_relevant_top_match():
    records = [
        _rec("a", "Capital Call ADR", "We process capital calls in the request path."),
        _rec("b", "Cooking Rice", "Add rice to boiling water."),
        _rec("c", "Queue Retry Pattern", "Retry external calls via queue with backoff."),
    ]
    index = BM25Index(records)
    results = index.search("capital call processing", top_k=3)
    assert results
    assert results[0][0] == "a"
    assert results[0][1] == 1.0  # max-normalized


def test_bm25_empty_corpus():
    index = BM25Index([])
    assert index.search("anything") == []


def test_bm25_zero_score_query():
    records = [_rec("a", "Foo", "alpha beta gamma")]
    index = BM25Index(records)
    # Query with no overlapping tokens should return nothing
    assert index.search("zzzz") == []


def test_bm25_title_indexed():
    """Tokens in the title should be searchable even if the body never mentions them."""
    records = [
        _rec("a", "Async Queue Pattern", "Body text talks only about unrelated cooking topics."),
        _rec("b", "Salad Recipe", "Mix lettuce and tomatoes."),
        _rec("c", "Train Schedule", "Departures every hour."),
    ]
    index = BM25Index(records)
    results = index.search("async queue", top_k=3)
    assert results
    assert results[0][0] == "a"


def test_bm25_top_k_limits_results():
    records = [
        _rec(rid, f"Title {rid}", f"shared keyword and unique term {rid}")
        for rid in ["a", "b", "c", "d", "e"]
    ]
    index = BM25Index(records)
    results = index.search("shared", top_k=2)
    assert len(results) <= 2
