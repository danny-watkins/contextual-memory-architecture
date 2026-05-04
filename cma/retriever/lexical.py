"""BM25 lexical search over MemoryRecord bodies."""

import re

from rank_bm25 import BM25L

from cma.schemas.memory_record import MemoryRecord

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenizer. Drops punctuation and whitespace."""
    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


class BM25Index:
    """In-memory BM25 index over a list of MemoryRecords.

    The corpus is each record's body plus its title (title is repeated three
    times to give it a stronger signal in the BM25 score).
    """

    def __init__(self, records: list[MemoryRecord]):
        self.records = records
        self.doc_ids: list[str] = [r.record_id for r in records]
        self._tokenized: list[list[str]] = [
            tokenize((r.title + " ") * 3 + r.body) for r in records
        ]
        self._bm25 = BM25L(self._tokenized) if self._tokenized else None

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Return the top_k (record_id, score) pairs for a query.

        Scores are normalized to [0, 1] by dividing by the max raw score across
        all docs for this query (so a doc that perfectly matches gets ~1.0).
        Returns an empty list if the corpus is empty or the query produces all
        zero scores.
        """
        if self._bm25 is None or not self.doc_ids:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        raw = self._bm25.get_scores(tokens)
        max_raw = float(raw.max()) if len(raw) else 0.0
        if max_raw <= 0.0:
            return []
        normed = raw / max_raw
        ranked = sorted(
            zip(self.doc_ids, normed.tolist()),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return ranked[:top_k]
