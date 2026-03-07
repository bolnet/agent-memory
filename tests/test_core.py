"""Tests for AgentMemory core class."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from agent_memory import AgentMemory, Memory

# mem_dir, mem, and test_config fixtures come from conftest.py


class TestInit:
    def test_creates_directory(self, mem_dir, test_config):
        path = os.path.join(mem_dir, "subdir", "nested")
        m = AgentMemory(path, config=test_config)
        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "memory.db"))
        assert os.path.isfile(os.path.join(path, "config.json"))
        m.close()

    def test_context_manager(self, mem_dir, test_config):
        with AgentMemory(mem_dir, config=test_config) as m:
            m.add("test")
        # Should not raise

    def test_custom_config(self, mem_dir, test_config):
        test_config["default_token_budget"] = 500
        m = AgentMemory(mem_dir, config=test_config)
        assert m.config.default_token_budget == 500
        m.close()


class TestCRUD:
    def test_add_and_get(self, mem):
        m = mem.add("User likes Python", tags=["preference"], category="preference")
        assert m.id
        assert m.content == "User likes Python"
        assert m.tags == ["preference"]
        assert m.status == "active"

        retrieved = mem.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "User likes Python"

    def test_get_nonexistent(self, mem):
        assert mem.get("nonexistent") is None

    def test_add_with_all_fields(self, mem):
        m = mem.add(
            content="Works at SoFi",
            tags=["career", "sofi"],
            category="career",
            entity="SoFi",
            event_date="2025-01-15T00:00:00Z",
            confidence=0.9,
            metadata={"source": "conversation"},
        )
        retrieved = mem.get(m.id)
        assert retrieved.entity == "SoFi"
        assert retrieved.category == "career"
        assert retrieved.confidence == 0.9
        assert retrieved.metadata == {"source": "conversation"}

    def test_forget(self, mem):
        m = mem.add("temp fact")
        assert mem.forget(m.id)
        retrieved = mem.get(m.id)
        assert retrieved.status == "archived"

    def test_forget_nonexistent(self, mem):
        assert not mem.forget("nonexistent")

    def test_forget_before(self, mem):
        mem.add("old fact")
        count = mem.forget_before("2099-01-01")
        assert count >= 1

    def test_compact(self, mem):
        m = mem.add("to remove")
        mem.forget(m.id)
        removed = mem.compact()
        assert removed == 1
        assert mem.get(m.id) is None


class TestSearch:
    def test_search_by_category(self, mem):
        mem.add("Python is great", tags=["tech"], category="preference")
        mem.add("Works at Google", tags=["career"], category="career")
        results = mem.search(category="preference")
        assert len(results) >= 1
        assert all(r.category == "preference" for r in results)

    def test_search_by_entity(self, mem):
        mem.add("CEO of SoFi", tags=["career"], category="career", entity="SoFi")
        mem.add("Uses React", tags=["tech"], category="tech", entity="React")
        results = mem.search(entity="SoFi")
        assert len(results) >= 1

    def test_search_with_query(self, mem):
        mem.add("User prefers dark mode", tags=["preference"], category="preference")
        mem.add("User works remotely", tags=["career"], category="career")
        results = mem.search(query="dark mode")
        assert len(results) >= 1

    def test_list_all(self, mem):
        mem.add("fact 1")
        mem.add("fact 2")
        results = mem.search(limit=100)
        assert len(results) >= 2


class TestStats:
    def test_stats(self, mem):
        mem.add("fact 1", category="career")
        mem.add("fact 2", category="preference")
        s = mem.stats()
        assert s["total_memories"] == 2
        assert s["by_status"]["active"] == 2
        assert s["by_category"]["career"] == 1
        assert s["db_size_bytes"] > 0


class TestExportImport:
    def test_export_import_roundtrip(self, mem, mem_dir, test_config):
        mem.add("fact 1", tags=["a"], category="career", entity="X")
        mem.add("fact 2", tags=["b"], category="preference")

        export_path = os.path.join(mem_dir, "export.json")
        mem.export_json(export_path)

        # Verify export file
        with open(export_path) as f:
            data = json.load(f)
        assert len(data) == 2

        # Import into new store
        new_dir = os.path.join(mem_dir, "new_store")
        with AgentMemory(new_dir, config=test_config) as new_mem:
            count = new_mem.import_json(export_path)
            assert count == 2
            assert new_mem.stats()["total_memories"] == 2


class TestRawSQL:
    def test_execute(self, mem):
        mem.add("test fact", category="test_cat")
        rows = mem.execute(
            "SELECT * FROM memories WHERE category = ?", ["test_cat"]
        )
        assert len(rows) == 1
        assert rows[0]["content"] == "test fact"
