"""Shared test fixtures — ensures tests use test databases, not production."""

import tempfile

import pytest

from agent_memory import AgentMemory


# Test databases (separate from production)
TEST_CONFIG = {
    "pg_connection_string": "postgresql://memwright:memwright@localhost:5432/memwright_test",
    "neo4j_uri": "bolt://localhost:7688",
    "neo4j_user": "neo4j",
    "neo4j_password": "memwright",
    "neo4j_database": "neo4j",
}


@pytest.fixture
def test_config():
    """Config dict pointing to test databases."""
    return dict(TEST_CONFIG)


@pytest.fixture
def mem_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mem(mem_dir):
    m = AgentMemory(mem_dir, config=TEST_CONFIG)
    yield m
    m.close()
