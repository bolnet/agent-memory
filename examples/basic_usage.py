"""Basic usage of AgentMemory."""

from agent_memory import AgentMemory

# Initialize — just a path
mem = AgentMemory("./my-agent-memory")

# Store some facts
mem.add(
    "User prefers Python over Java",
    tags=["preference", "coding"],
    category="preference",
)

mem.add(
    "User works at SoFi as Staff SWE AI",
    tags=["career", "sofi"],
    category="career",
    entity="SoFi",
)

mem.add(
    "Project uses FastAPI + PostgreSQL",
    tags=["project", "tech-stack"],
    category="project",
    entity="my-project",
)

# Recall relevant memories
results = mem.recall("what programming language does the user prefer?")
for r in results:
    print(f"[{r.match_source}:{r.score:.2f}] {r.content}")

# Get formatted context for prompt injection
context = mem.recall_as_context("tell me about the user's background")
print("\n--- Context for system prompt ---")
print(context)

# Search with filters
career_facts = mem.search(category="career", status="active")
print(f"\nCareer facts: {len(career_facts)}")
for m in career_facts:
    print(f"  - {m.content}")

# Stats
stats = mem.stats()
print(f"\nTotal memories: {stats['total_memories']}")

mem.close()
