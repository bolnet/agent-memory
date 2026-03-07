"""Tests for the Neo4j graph (mocked — no real Neo4j instance needed)."""

import sys
from unittest.mock import MagicMock, patch

import pytest


# Mock the neo4j module before importing our code
mock_neo4j = MagicMock()
mock_neo4j.GraphDatabase = MagicMock()
sys.modules.setdefault("neo4j", mock_neo4j)

from agent_memory.graph.neo4j_graph import Neo4jGraph, _sanitize_rel_type


class TestSanitizeRelType:
    def test_valid_type(self):
        assert _sanitize_rel_type("uses") == "USES"

    def test_type_with_spaces(self):
        assert _sanitize_rel_type("works at") == "WORKS_AT"

    def test_type_with_special_chars(self):
        assert _sanitize_rel_type("related-to") == "RELATEDTO"

    def test_empty_fallback(self):
        assert _sanitize_rel_type("!!!") == "RELATED_TO"


class TestNeo4jGraphInterface:
    """Test Neo4jGraph methods with mocked Neo4j driver."""

    def _make_graph(self):
        """Create a Neo4jGraph with a fully mocked driver."""
        with patch("agent_memory.graph.neo4j_graph.GraphDatabase") as mock_gdb:
            mock_driver = MagicMock()
            mock_gdb.driver.return_value = mock_driver
            # execute_query returns (records, summary, keys)
            mock_driver.execute_query.return_value = ([], MagicMock(), [])

            graph = Neo4jGraph(
                uri="bolt://localhost:7687",
                auth=("neo4j", "testpass"),
                database="testdb",
            )
            return graph, mock_driver

    def test_init_creates_driver(self):
        graph, mock_driver = self._make_graph()
        mock_driver.verify_connectivity.assert_called_once()
        assert mock_driver.execute_query.call_count >= 1

    def test_add_entity(self):
        graph, mock_driver = self._make_graph()
        mock_driver.execute_query.reset_mock()

        graph.add_entity("Python", "tool", {"version": "3.12"})

        mock_driver.execute_query.assert_called_once()
        query = mock_driver.execute_query.call_args[0][0]
        assert "MERGE" in query
        assert "Entity" in query

    def test_add_relation(self):
        graph, mock_driver = self._make_graph()
        mock_driver.execute_query.reset_mock()

        graph.add_relation("Alice", "Python", "uses", {"since": "2024"})

        # 2 MERGE calls for auto-creating nodes + 1 for the relation
        assert mock_driver.execute_query.call_count == 3
        last_query = mock_driver.execute_query.call_args_list[-1][0][0]
        assert "USES" in last_query

    def test_get_related(self):
        graph, mock_driver = self._make_graph()
        mock_record1 = {"name": "Python"}
        mock_record2 = {"name": "Django"}
        mock_driver.execute_query.return_value = (
            [mock_record1, mock_record2],
            MagicMock(),
            [],
        )

        result = graph.get_related("Alice", depth=2)
        assert "Python" in result
        assert "Django" in result

    def test_get_related_empty(self):
        graph, mock_driver = self._make_graph()
        mock_driver.execute_query.return_value = ([], MagicMock(), [])

        result = graph.get_related("NonExistent")
        assert result == []

    def test_get_subgraph(self):
        graph, mock_driver = self._make_graph()
        mock_record = {
            "nodes": [
                {"name": "Alice", "type": "person"},
                {"name": "Python", "type": "tool"},
            ],
            "edges": [
                {"source": "alice", "target": "python", "type": "USES"},
            ],
        }
        mock_driver.execute_query.return_value = ([mock_record], MagicMock(), [])

        result = graph.get_subgraph("Alice")
        assert result["entity"] == "Alice"
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_get_subgraph_empty(self):
        graph, mock_driver = self._make_graph()
        mock_driver.execute_query.return_value = ([], MagicMock(), [])

        result = graph.get_subgraph("NonExistent")
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_get_entities(self):
        graph, mock_driver = self._make_graph()
        mock_records = [
            {"entity": {"name": "python", "entity_type": "tool", "key": "python"}},
            {"entity": {"name": "react", "entity_type": "tool", "key": "react"}},
        ]
        mock_driver.execute_query.return_value = (mock_records, MagicMock(), [])

        result = graph.get_entities(entity_type="tool")
        assert len(result) == 2

    def test_stats(self):
        graph, mock_driver = self._make_graph()

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.execute_read.return_value = {
            "nodes": 5,
            "edges": 3,
            "types": {"tool": 2, "person": 3},
        }

        result = graph.stats()
        assert result["nodes"] == 5

    def test_save_is_noop(self):
        graph, mock_driver = self._make_graph()
        graph.save()
        graph.save("/some/path")

    def test_close(self):
        graph, mock_driver = self._make_graph()
        graph.close()
        mock_driver.close.assert_called_once()
