"""Layer 2: FTS5 BM25 full-text search."""

from __future__ import annotations

from typing import List

from agent_memory.models import Memory, RetrievalResult
from agent_memory.store.sqlite_store import SQLiteStore


def fts_search(store: SQLiteStore, query: str, limit: int = 50) -> List[RetrievalResult]:
    """Perform FTS5 BM25 search and return scored results."""
    raw_results = store.fts_search(query, limit=limit)
    if not raw_results:
        return []

    # BM25 returns negative scores (lower = better match)
    # Normalize relative to the best score in this result set
    best_rank = abs(raw_results[0]["rank"]) if raw_results else 1.0
    results = []
    for item in raw_results:
        raw_rank = abs(item["rank"])
        # Relative normalization: best match gets 1.0, worst gets ~0.1
        if best_rank > 0:
            score = min(raw_rank / best_rank, 1.0)
        else:
            score = 0.5
        results.append(
            RetrievalResult(
                memory=item["memory"],
                score=score,
                match_source="fts",
            )
        )
    return results
