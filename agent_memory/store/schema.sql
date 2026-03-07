CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    tags TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    entity TEXT,
    created_at TEXT NOT NULL,
    event_date TEXT,
    valid_from TEXT NOT NULL,
    valid_until TEXT,
    superseded_by TEXT,
    confidence REAL DEFAULT 1.0,
    status TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (superseded_by) REFERENCES memories(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    content,
    tags,
    category,
    entity,
    content='memories',
    content_rowid='rowid'
);

CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_entity ON memories(entity);
CREATE INDEX IF NOT EXISTS idx_memories_valid ON memories(valid_until);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content, tags, category, entity)
    VALUES (new.rowid, new.content, new.tags, new.category, new.entity);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags, category, entity)
    VALUES ('delete', old.rowid, old.content, old.tags, old.category, old.entity);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content, tags, category, entity)
    VALUES ('delete', old.rowid, old.content, old.tags, old.category, old.entity);
    INSERT INTO memories_fts(rowid, content, tags, category, entity)
    VALUES (new.rowid, new.content, new.tags, new.category, new.entity);
END;

