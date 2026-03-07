"""Scoring, deduplication, temporal boost, entity boost, token budget assembly."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from agent_memory.models import RetrievalResult
from agent_memory.utils.tokens import estimate_tokens


def deduplicate(results: List[RetrievalResult]) -> List[RetrievalResult]:
    """Remove duplicate memories, keeping the highest-scored entry."""
    seen: dict[str, RetrievalResult] = {}
    for r in results:
        mid = r.memory.id
        if mid not in seen or r.score > seen[mid].score:
            seen[mid] = r
    return list(seen.values())


def temporal_boost(
    results: List[RetrievalResult],
    decay_days: int = 90,
    enabled: bool = True,
) -> List[RetrievalResult]:
    """Boost scores for more recent memories.

    Can be disabled for benchmark data spanning long time periods.
    """
    if not enabled:
        return results
    now = datetime.now(timezone.utc)
    for r in results:
        try:
            created = datetime.fromisoformat(r.memory.created_at)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (now - created).days
            # Linear decay: full boost at 0 days, no boost after decay_days
            boost = max(0.0, 1.0 - (age_days / decay_days)) * 0.2
            r.score += boost
        except (ValueError, TypeError):
            pass
    return results


def entity_boost(
    results: List[RetrievalResult], query_entities: Optional[List[str]] = None
) -> List[RetrievalResult]:
    """Boost score if memory entity or content matches query entities.

    Checks both the entity field (strong match) and content substring (weaker match).
    """
    if not query_entities:
        return results
    query_entities_lower = {e.lower() for e in query_entities}
    for r in results:
        # Strong boost: entity field exact match
        if r.memory.entity and r.memory.entity.lower() in query_entities_lower:
            r.score += 0.3
        # Weaker boost: entity name appears in content
        else:
            content_lower = r.memory.content.lower()
            for ent in query_entities_lower:
                if len(ent) >= 3 and ent in content_lower:
                    r.score += 0.15
                    break
    return results


def fit_to_budget(
    results: List[RetrievalResult], token_budget: int
) -> List[RetrievalResult]:
    """Select highest-scored results that fit within token budget."""
    # Sort by score descending
    sorted_results = sorted(results, key=lambda r: r.score, reverse=True)
    selected = []
    tokens_used = 0
    for r in sorted_results:
        t = estimate_tokens(r.memory.content)
        if tokens_used + t <= token_budget:
            selected.append(r)
            tokens_used += t
        elif not selected:
            # Always include at least one result
            selected.append(r)
            break
    return selected
