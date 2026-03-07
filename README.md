<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo.svg">
    <source media="(prefers-color-scheme: light)" srcset="docs/logo-dark.svg">
    <img alt="Memwright" src="docs/logo.svg" width="400">
  </picture>
</p>

<p align="center">
  <em>Embedded memory for AI agents. Sub-5ms retrieval. Works with Claude Code.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/memwright/"><img src="https://img.shields.io/pypi/v/memwright?color=C15F3C&style=flat-square" alt="PyPI"></a>
  <a href="https://pypi.org/project/memwright/"><img src="https://img.shields.io/pypi/pyversions/memwright?style=flat-square" alt="Python"></a>
  <a href="https://github.com/bolnet/agent-memory/blob/main/LICENSE"><img src="https://img.shields.io/github/license/bolnet/agent-memory?style=flat-square" alt="License"></a>
  <a href="https://registry.modelcontextprotocol.io/servers/io.github.bolnet/memwright"><img src="https://img.shields.io/badge/MCP-Registry-C15F3C?style=flat-square" alt="MCP Registry"></a>
</p>

---

## Why Memwright?

AI agents forget everything between conversations. The typical fix is a managed vector database or cloud memory service. Memwright takes a different approach:

- **Local-first** — A SQLite file with FTS5 full-text search. Your data stays on your machine.
- **Fast** — 4-layer retrieval cascade returns results in under 5ms.
- **Token efficient** — 300-500 tokens per recall vs 15,000+ for full history replay.

Works as a **Claude Code MCP server**, a **Cursor MCP server**, or a **Python library**.

## Install

```bash
pip install memwright[all]      # Recommended — includes pgvector, Neo4j, MCP
pip install memwright           # Core only (SQLite + FTS5)
pip install memwright[vectors]  # + pgvector semantic search
pip install memwright[neo4j]    # + Neo4j graph database
pip install memwright[mcp]      # + MCP server for Claude Code / Cursor
```

**Requirements:** Docker (for PostgreSQL + Neo4j) and an embedding API key (`OPENROUTER_API_KEY` or `OPENAI_API_KEY`).

## Quick Start — MCP Server (Claude Code / Cursor)

```bash
# 1. Initialize (starts Docker containers, generates .env)
agent-memory init ~/.agent-memory/my-project

# 2. Get MCP config
agent-memory setup-claude-code ~/.agent-memory/my-project
```

Add the output to your `.mcp.json`:

```json
{
  "agent-memory": {
    "command": "agent-memory",
    "args": ["serve", "~/.agent-memory/my-project"]
  }
}
```

Claude now has 7 memory tools: `memory_add`, `memory_get`, `memory_recall`, `memory_search`, `memory_forget`, `memory_timeline`, `memory_stats`.

Add to your `CLAUDE.md`:

```markdown
## Memory
Use `memory_recall` at the start of each conversation with the user's first message.
Use `memory_add` to store preferences, decisions, and project context.
```

## Quick Start — Python API

```python
from agent_memory import AgentMemory

mem = AgentMemory("./my-agent")

# Store facts
mem.add("User prefers Python over Java",
        tags=["preference", "coding"], category="preference")
mem.add("User works at SoFi as Staff SWE",
        tags=["career"], category="career", entity="SoFi")

# Recall relevant memories
results = mem.recall("what language does the user prefer?")
for r in results:
    print(f"[{r.match_source}:{r.score:.2f}] {r.content}")

# Get formatted context string for prompt injection
context = mem.recall_as_context("user background", budget=500)

# Contradiction handling — old facts get auto-superseded
mem.add("User works at Google as Principal Eng",
        tags=["career"], category="career", entity="SoFi")
# ^ The SoFi memory is now superseded automatically
```

## How Retrieval Works

Multi-layer cascade with Reciprocal Rank Fusion:

```mermaid
graph TD
    Q["Query"] --> T["1. Tag Match<br/><small>&lt;1ms · SQL index</small>"]
    Q --> F["2. FTS5 BM25<br/><small>1-3ms · Full-text</small>"]
    Q --> G["3. Graph Expansion<br/><small>&lt;1ms · Neo4j multi-hop</small>"]
    Q --> V["4. Vector Similarity<br/><small>5-10ms · pgvector cosine</small>"]
    T --> R["RRF Fusion + Ranking"]
    F --> R
    G --> R
    V --> R
    R --> O["Ranked Results<br/><small>within token budget</small>"]

    style Q fill:#C15F3C,stroke:#C15F3C,color:#fff
    style R fill:#C15F3C,stroke:#C15F3C,color:#fff
    style O fill:#161b22,stroke:#C15F3C,color:#F4F3EE
    style T fill:#161b22,stroke:#30363d,color:#F4F3EE
    style F fill:#161b22,stroke:#30363d,color:#F4F3EE
    style G fill:#161b22,stroke:#30363d,color:#F4F3EE
    style V fill:#161b22,stroke:#30363d,color:#F4F3EE
```

When the graph is enabled, entity relationships are traversed to find related memories (e.g., querying "Python" also finds memories about "FastAPI" if they're connected). Graph relationship triples are injected as synthetic context for multi-hop reasoning.

## CLI

```bash
agent-memory init ./store              # Initialize store + Docker + .env
agent-memory add ./store "text" ...    # Add a memory
agent-memory recall ./store "query"    # Multi-layer recall
agent-memory search ./store "text"     # FTS5 search
agent-memory list ./store              # List memories
agent-memory timeline ./store          # Entity timeline
agent-memory stats ./store             # Store statistics
agent-memory doctor ./store            # Health check
agent-memory serve ./store             # Start MCP server
agent-memory export ./store -o bak.json
agent-memory import ./store bak.json
```

## Architecture

```
AgentMemory
├── SQLite + FTS5    — Core keyword search, always on
├── pgvector         — Semantic vector search (PostgreSQL)
├── Neo4j            — Entity graph, multi-hop traversal
├── Retrieval        — 4-layer cascade with RRF fusion
├── Temporal         — Contradiction detection, supersession
├── Extraction       — Rule-based + optional LLM
├── MCP Server       — Claude Code / Cursor integration
└── CLI + Doctor     — Health check for all components
```

## Configuration

AgentMemory stores `config.json` in the memory store directory:

```json
{
  "default_token_budget": 2000,
  "min_results": 3,
  "pg_connection_string": "postgresql://memwright:memwright@localhost:5432/memwright",
  "neo4j_uri": "bolt://localhost:7687",
  "neo4j_password": "memwright"
}
```

Environment variables override config: `PG_CONNECTION_STRING`, `NEO4J_PASSWORD`, `OPENROUTER_API_KEY` / `OPENAI_API_KEY`.

## License

Apache 2.0

---

<sub>mcp-name: io.github.bolnet/memwright</sub>
