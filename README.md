# Memwright

mcp-name: io.github.bolnet/memwright

Embedded memory for AI agents. SQLite + pgvector + Neo4j.

`pip install memwright` — Python import: `from agent_memory import AgentMemory`

## Why

AI agents forget everything between conversations. The typical fix is a managed vector database or cloud memory service. AgentMemory takes a different approach: a local SQLite file with FTS5 full-text search, zero external dependencies, and sub-5ms retrieval.

**Works great as a Claude Code MCP server** — give Claude persistent memory.

## Install

```bash
pip install memwright[all]      # Recommended — includes pgvector, Neo4j, MCP
pip install memwright           # Core only (SQLite + FTS5)
pip install memwright[vectors]  # + pgvector semantic search
pip install memwright[neo4j]    # + Neo4j graph database
pip install memwright[mcp]      # + MCP server for Claude Code
```

**Requirements:**
- Docker (for PostgreSQL + Neo4j): `docker compose up -d`
- Embedding API key: `OPENROUTER_API_KEY` or `OPENAI_API_KEY`

## Quick Start — Claude Code MCP Server

```bash
# 1. Initialize a memory store
agent-memory init ~/.agent-memory/my-project

# 2. Get the MCP config
agent-memory setup-claude-code ~/.agent-memory/my-project
```

Add the output to your project's `.mcp.json`:

```json
{
  "agent-memory": {
    "command": "agent-memory",
    "args": ["serve", "/Users/you/.agent-memory/my-project", "--mcp"]
  }
}
```

Claude now has 6 memory tools: `memory_add`, `memory_recall`, `memory_search`, `memory_forget`, `memory_timeline`, `memory_stats`.

Add instructions to your `CLAUDE.md` (see `examples/CLAUDE.md.example`):

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

# Recall relevant memories (multi-layer cascade: tags, FTS5, optional vectors + graph)
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

## CLI

```bash
agent-memory init ./store
agent-memory add ./store "User prefers dark mode" --tags preference --category preference
agent-memory recall ./store "what theme?"
agent-memory search ./store "Python" --category preference
agent-memory list ./store --status active
agent-memory timeline ./store --entity SoFi
agent-memory stats ./store
agent-memory export ./store -o backup.json
agent-memory import ./store backup.json
agent-memory forget ./store <memory-id>
agent-memory compact ./store
agent-memory inspect ./store
agent-memory serve ./store --mcp
```

## How Retrieval Works

Multi-layer cascade with Reciprocal Rank Fusion:

| Layer | Method | Speed | Always On |
|-------|--------|-------|-----------|
| 1. Tag match | SQL index lookup | <1ms | Yes |
| 2. FTS5 BM25 | SQLite full-text search | 1-3ms | Yes |
| 3. Graph expansion | Neo4j multi-hop entity traversal | <1ms | Yes |
| 4. Vector similarity | pgvector cosine similarity | 5-10ms | Yes |

Results from all layers are fused using Reciprocal Rank Fusion (RRF), boosted by recency and entity relevance, deduplicated, then assembled within a token budget.

When the graph is enabled, entity relationships are traversed to find related memories (e.g., querying "Python" also finds memories about "FastAPI" if they're connected in the graph). Graph relationship triples are injected as synthetic context for multi-hop reasoning.

## Configuration

AgentMemory stores a `config.json` in the memory store directory. Options:

```json
{
  "default_token_budget": 2000,
  "min_results": 3,
  "pg_connection_string": "postgresql://memwright:memwright@localhost:5432/memwright",
  "neo4j_uri": "bolt://localhost:7687",
  "neo4j_user": "neo4j",
  "neo4j_password": "memwright",
  "neo4j_database": "neo4j"
}
```

## Key Features

- **Sub-5ms retrieval** — Fast multi-layer cascade with RRF fusion.
- **Token efficient** — 300-500 tokens per recall vs 15,000+ for full history replay.
- **Automatic contradiction handling** — New facts supersede old ones (same entity + category).
- **Graph-enhanced** — Neo4j entity graph enables multi-hop reasoning.
- **Semantic search** — pgvector cosine similarity over OpenAI embeddings.
- **Inspectable** — `sqlite3 memory.db` and see exactly what the agent remembers.
- **MCP server** — First-class Claude Code / Claude Desktop integration.
- **Health check** — `agent-memory doctor` verifies all components.

## Architecture

```
AgentMemory
├── SQLite + FTS5 store (core keyword search)
├── pgvector (semantic vector search)
├── Neo4j (entity graph, multi-hop traversal)
├── Multi-layer retrieval (tag → BM25 → graph → vector) with RRF fusion
├── Temporal logic (contradiction detection, supersession, timeline)
├── Extraction pipeline (rule-based default, optional LLM)
├── MCP server (for Claude Code)
└── CLI + Health check
```

## License

Apache 2.0
