"""Tests for the pgvector store (mocked — no real PostgreSQL connection).

These tests verify the VectorStore interface and SQL generation
without requiring a running PostgreSQL instance.
"""

from unittest.mock import MagicMock, patch, call

import pytest


class TestVectorStoreInterface:
    """Test VectorStore methods with mocked psycopg connection."""

    def _make_store(self):
        """Create a VectorStore with a mocked connection."""
        with patch("psycopg.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            from agent_memory.store.vector_store import VectorStore

            store = VectorStore.__new__(VectorStore)
            store.connection_string = "postgresql://test"
            store._conn = mock_conn
            return store, mock_conn

    def test_add(self):
        store, mock_conn = self._make_store()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        embedding = [0.1] * 1536
        store.add("mem123", "test content", embedding)

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO memory_vectors" in sql

    def test_delete(self):
        store, mock_conn = self._make_store()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = store.delete("mem123")

        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "DELETE FROM memory_vectors" in sql
        assert result is True

    def test_search(self):
        store, mock_conn = self._make_store()
        mock_cursor = MagicMock()
        mock_cursor.description = [("memory_id",), ("content",), ("distance",)]
        mock_cursor.fetchall.return_value = [
            ("mem1", "content1", 0.5),
            ("mem2", "content2", 0.8),
        ]
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        embedding = [0.1] * 1536
        results = store.search(embedding, limit=10)

        assert len(results) == 2
        assert results[0]["memory_id"] == "mem1"
        assert results[0]["distance"] == 0.5
        assert results[1]["memory_id"] == "mem2"

    def test_count(self):
        store, mock_conn = self._make_store()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        result = store.count()
        assert result == 42

    def test_close(self):
        store, mock_conn = self._make_store()
        store.close()
        mock_conn.close.assert_called_once()
