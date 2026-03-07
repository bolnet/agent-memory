"""Configuration loading and defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


DEFAULT_CONFIG = {
    "default_token_budget": 2000,
    "min_results": 3,
    "pg_connection_string": "postgresql://memwright:memwright@localhost:5432/memwright",
    "neo4j_uri": "bolt://localhost:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "memwright",
    "neo4j_database": "neo4j",
}


@dataclass
class MemoryConfig:
    default_token_budget: int = 2000
    min_results: int = 3
    pg_connection_string: str = "postgresql://memwright:memwright@localhost:5432/memwright"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "memwright"
    neo4j_database: str = "neo4j"

    def __post_init__(self):
        """Apply environment variable overrides.

        Precedence: env vars > config.json > defaults.
        Env vars always win when set, so users can override without editing config.json.
        """
        env_pg = os.environ.get("PG_CONNECTION_STRING")
        if env_pg:
            self.pg_connection_string = env_pg

        env_neo4j_password = os.environ.get("NEO4J_PASSWORD")
        if env_neo4j_password:
            self.neo4j_password = env_neo4j_password

        if os.environ.get("NEO4J_URI"):
            self.neo4j_uri = os.environ["NEO4J_URI"]
        if os.environ.get("NEO4J_USER"):
            self.neo4j_user = os.environ["NEO4J_USER"]
        if os.environ.get("NEO4J_DATABASE"):
            self.neo4j_database = os.environ["NEO4J_DATABASE"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryConfig:
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "default_token_budget": self.default_token_budget,
            "min_results": self.min_results,
            "pg_connection_string": self.pg_connection_string,
            "neo4j_uri": self.neo4j_uri,
            "neo4j_user": self.neo4j_user,
            "neo4j_password": self.neo4j_password,
            "neo4j_database": self.neo4j_database,
        }


def load_config(path: Path) -> MemoryConfig:
    """Load config from a JSON file, falling back to defaults."""
    config_file = path / "config.json"
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
        return MemoryConfig.from_dict(data)
    return MemoryConfig()


def save_config(path: Path, config: MemoryConfig) -> None:
    """Save config to a JSON file."""
    config_file = path / "config.json"
    with open(config_file, "w") as f:
        json.dump(config.to_dict(), f, indent=2)
