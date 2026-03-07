"""SQLite + FTS5 storage implementation."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_memory.models import Memory

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class SQLiteStore:
    """Low-level SQLite storage for memories."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        schema_sql = _SCHEMA_PATH.read_text()
        self._conn.executescript(schema_sql)

    def close(self) -> None:
        self._conn.close()

    # ── Memory CRUD ──

    def insert(self, memory: Memory) -> Memory:
        self._conn.execute(
            """INSERT INTO memories
               (id, content, tags, category, entity, created_at, event_date,
                valid_from, valid_until, superseded_by,
                confidence, status, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                memory.id,
                memory.content,
                memory.tags_json(),
                memory.category,
                memory.entity,
                memory.created_at,
                memory.event_date,
                memory.valid_from,
                memory.valid_until,
                memory.superseded_by,
                memory.confidence,
                memory.status,
                memory.metadata_json(),
            ),
        )
        self._conn.commit()
        return memory

    def get(self, memory_id: str) -> Optional[Memory]:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row is None:
            return None
        return Memory.from_row(dict(row))

    def update(self, memory: Memory) -> Memory:
        self._conn.execute(
            """UPDATE memories SET
               content=?, tags=?, category=?, entity=?, event_date=?,
               valid_from=?, valid_until=?, superseded_by=?,
               confidence=?, status=?, metadata=?
               WHERE id=?""",
            (
                memory.content,
                memory.tags_json(),
                memory.category,
                memory.entity,
                memory.event_date,
                memory.valid_from,
                memory.valid_until,
                memory.superseded_by,
                memory.confidence,
                memory.status,
                memory.metadata_json(),
                memory.id,
            ),
        )
        self._conn.commit()
        return memory

    def delete(self, memory_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def list_memories(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        entity: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 100,
    ) -> List[Memory]:
        conditions = []
        params: List[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if entity:
            conditions.append("entity = ?")
            params.append(entity)
        if after:
            conditions.append("created_at >= ?")
            params.append(after)
        if before:
            conditions.append("created_at <= ?")
            params.append(before)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [Memory.from_row(dict(r)) for r in rows]

    # ── FTS5 Search ──

    def fts_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Full-text search using FTS5 BM25 ranking.

        Returns dicts with 'memory' and 'rank' keys.
        """
        # Escape FTS5 special characters
        safe_query = self._escape_fts_query(query)
        if not safe_query:
            return []

        rows = self._conn.execute(
            """SELECT m.*, bm25(memories_fts) as rank
               FROM memories_fts fts
               JOIN memories m ON m.rowid = fts.rowid
               WHERE memories_fts MATCH ?
               AND m.status = 'active'
               ORDER BY rank
               LIMIT ?""",
            (safe_query, limit),
        ).fetchall()

        results = []
        for row in rows:
            row_dict = dict(row)
            rank = row_dict.pop("rank")
            results.append({"memory": Memory.from_row(row_dict), "rank": rank})
        return results

    _FTS_STOP_WORDS = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "about", "like",
        "through", "after", "over", "between", "out", "against", "during",
        "without", "before", "under", "around", "among", "what", "which",
        "who", "whom", "this", "that", "these", "those", "am", "or", "and",
        "but", "if", "than", "too", "very", "just", "how", "where", "when",
        "why", "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "such", "no", "not", "only", "own", "same", "so", "then",
        "up", "down", "my", "your", "his", "her", "its", "our", "their",
        "me", "him", "us", "them", "i", "you", "he", "she", "it", "we", "they",
    })

    def _escape_fts_query(self, query: str) -> str:
        """Convert a natural language query to an FTS5 query.

        Strips possessives, filters stop words, joins content words with OR.
        """
        words = []
        for word in query.split():
            # Strip possessives: "Caroline's" → "Caroline"
            parts = word.replace("\u2019", "'").split("'")
            for part in parts:
                cleaned = "".join(c for c in part if c.isalnum() or c == "_")
                if cleaned and cleaned.lower() not in self._FTS_STOP_WORDS and len(cleaned) >= 2:
                    words.append(f'"{cleaned}"')
        if not words:
            for word in query.split():
                parts = word.replace("\u2019", "'").split("'")
                for part in parts:
                    cleaned = "".join(c for c in part if c.isalnum() or c == "_")
                    if cleaned:
                        words.append(f'"{cleaned}"')
        return " OR ".join(words)

    # ── Tag Search ──

    def tag_search(
        self,
        tags: List[str],
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Memory]:
        """Find active memories matching any of the given tags."""
        conditions = ["status = 'active'", "valid_until IS NULL"]
        params: List[Any] = []

        tag_conditions = []
        for tag in tags:
            tag_conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if tag_conditions:
            conditions.append(f"({' OR '.join(tag_conditions)})")

        if category:
            conditions.append("category = ?")
            params.append(category)

        where = " AND ".join(conditions)
        query = f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [Memory.from_row(dict(r)) for r in rows]

    # ── Stats ──

    def stats(self) -> Dict[str, Any]:
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        by_status = {}
        for row in self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM memories GROUP BY status"
        ).fetchall():
            by_status[row["status"]] = row["cnt"]
        by_category = {}
        for row in self._conn.execute(
            "SELECT category, COUNT(*) as cnt FROM memories GROUP BY category"
        ).fetchall():
            by_category[row["category"]] = row["cnt"]

        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        return {
            "total_memories": total,
            "by_status": by_status,
            "by_category": by_category,
            "db_size_bytes": db_size,
        }

    # ── Raw SQL ──

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        cursor = self._conn.execute(sql, params or [])
        if cursor.description is None:
            self._conn.commit()
            return []
        return [dict(row) for row in cursor.fetchall()]

    # ── Bulk operations ──

    def archive_before(self, date: str) -> int:
        cursor = self._conn.execute(
            "UPDATE memories SET status='archived' WHERE created_at < ? AND status='active'",
            (date,),
        )
        self._conn.commit()
        return cursor.rowcount

    def compact(self) -> int:
        cursor = self._conn.execute(
            "DELETE FROM memories WHERE status='archived'"
        )
        self._conn.commit()
        self._conn.execute("VACUUM")
        return cursor.rowcount
