#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# Memwright Startup Script
# Starts all required services and runs health check.
# Usage: ./start.sh [memory-store-path]
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STORE_PATH="${1:-$HOME/.agent-memory/default}"
VENV="$SCRIPT_DIR/.venv"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}[memwright]${NC} $1"; }
ok()    { echo -e "${GREEN}[memwright]${NC} $1"; }
warn()  { echo -e "${YELLOW}[memwright]${NC} $1"; }
fail()  { echo -e "${RED}[memwright]${NC} $1"; }

# ── 1. Check Python venv ──
info "Checking Python environment..."
if [ ! -f "$VENV/bin/python" ]; then
    fail "No .venv found. Run: python -m venv .venv && pip install -e '.[all]'"
    exit 1
fi
ok "Python venv: $VENV"

# ── 2. Load .env ──
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
    ok "Loaded .env"
else
    warn "No .env file found at $ENV_FILE"
fi

# ── 3. Check Docker ──
info "Checking Docker..."
if ! command -v docker &>/dev/null; then
    fail "Docker not installed. Install Docker Desktop."
    exit 1
fi

if ! docker info &>/dev/null; then
    fail "Docker daemon not running. Starting Docker Desktop..."
    open -a Docker 2>/dev/null || true
    info "Waiting for Docker daemon..."
    for i in $(seq 1 30); do
        if docker info &>/dev/null; then
            break
        fi
        sleep 2
        echo -n "."
    done
    echo
    if ! docker info &>/dev/null; then
        fail "Docker failed to start after 60s. Start Docker Desktop manually."
        exit 1
    fi
fi
ok "Docker daemon running"

# ── 4. Start containers ──
info "Starting PostgreSQL + Neo4j containers..."
cd "$SCRIPT_DIR"
docker compose up -d

# ── 5. Wait for PostgreSQL ──
info "Waiting for PostgreSQL to be healthy..."
for i in $(seq 1 30); do
    if docker exec memwright-postgres pg_isready -U memwright -d memwright &>/dev/null; then
        break
    fi
    sleep 1
    echo -n "."
done
echo
if docker exec memwright-postgres pg_isready -U memwright -d memwright &>/dev/null; then
    ok "PostgreSQL ready"
else
    fail "PostgreSQL not ready after 30s"
fi

# ── 6. Wait for Neo4j ──
info "Waiting for Neo4j to be healthy..."
for i in $(seq 1 60); do
    if docker exec memwright-neo4j neo4j status 2>/dev/null | grep -q "running"; then
        break
    fi
    sleep 1
    echo -n "."
done
echo
if docker exec memwright-neo4j neo4j status 2>/dev/null | grep -q "running"; then
    ok "Neo4j ready"
else
    warn "Neo4j may still be starting (slow first boot is normal)"
fi

# ── 7. Check API keys ──
if [ -z "${OPENROUTER_API_KEY:-}" ] && [ -z "${OPENAI_API_KEY:-}" ]; then
    warn "No embedding API key set. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env"
else
    ok "Embedding API key configured"
fi

# ── 8. Initialize memory store ──
info "Initializing memory store at $STORE_PATH..."
"$VENV/bin/python" -m agent_memory.cli init "$STORE_PATH" 2>/dev/null || true

# ── 9. Run full health check ──
echo
echo "═══════════════════════════════════════════════════"
"$VENV/bin/python" -m agent_memory.cli doctor "$STORE_PATH" --env-file "$ENV_FILE"

# ── 10. Print MCP config ──
echo "═══════════════════════════════════════════════════"
info "MCP config for Claude Code:"
echo
"$VENV/bin/python" -m agent_memory.cli setup-claude-code "$STORE_PATH"

echo
ok "Memwright is ready."
