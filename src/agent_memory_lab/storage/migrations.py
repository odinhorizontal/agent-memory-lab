"""Initial SQLite schema and FTS synchronization."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memory_versions (
    row_id INTEGER PRIMARY KEY,
    id TEXT NOT NULL REFERENCES memory_keys(id),
    version INTEGER NOT NULL CHECK (version >= 1),
    session_id TEXT NOT NULL,
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    memory_type TEXT NOT NULL CHECK (memory_type IN
        ('semantic','episodic','procedural','preference')),
    entity TEXT, attribute TEXT, value TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    valid_from TEXT, valid_to TEXT,
    status TEXT NOT NULL CHECK (status IN ('active','superseded','deleted')),
    confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    scope TEXT NOT NULL,
    pending_conflict INTEGER NOT NULL CHECK (pending_conflict IN (0,1)),
    visible INTEGER NOT NULL CHECK (visible IN (0,1)),
    terms TEXT NOT NULL,
    UNIQUE(id, version),
    CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_from < valid_to),
    CHECK ((entity IS NULL AND attribute IS NULL AND value IS NULL) OR
           (entity IS NOT NULL AND attribute IS NOT NULL AND value IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS memory_events (
    id INTEGER PRIMARY KEY,
    memory_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    operation TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    details TEXT NOT NULL,
    FOREIGN KEY(memory_id, version) REFERENCES memory_versions(id, version)
);
CREATE TABLE IF NOT EXISTS memory_relations (
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    target_id TEXT NOT NULL,
    target_version INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('supersedes','consolidates')),
    PRIMARY KEY(source_id, source_version, target_id, target_version, kind),
    FOREIGN KEY(source_id, source_version) REFERENCES memory_versions(id, version),
    FOREIGN KEY(target_id, target_version) REFERENCES memory_versions(id, version)
);
CREATE INDEX IF NOT EXISTS idx_tenant ON memory_keys(user_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_fact_slots ON memory_versions(scope, memory_type, entity, attribute)
    WHERE visible = 1;
CREATE INDEX IF NOT EXISTS idx_effective ON memory_versions(visible, status, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_events_memory ON memory_events(memory_id, id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON memory_relations(target_id, target_version);
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    terms, content='memory_versions', content_rowid='row_id'
);
CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_versions BEGIN
    INSERT INTO memory_fts(rowid, terms) VALUES (new.row_id, new.terms);
END;
CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory_versions BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, terms) VALUES ('delete', old.row_id, old.terms);
END;
CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE OF terms ON memory_versions BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, terms) VALUES ('delete', old.row_id, old.terms);
    INSERT INTO memory_fts(rowid, terms) VALUES (new.row_id, new.terms);
END;
"""


def migrate(db) -> None:
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if version == 0:
        db.executescript("BEGIN IMMEDIATE;\n" + SCHEMA + "\nPRAGMA user_version=1;\nCOMMIT;")
    elif version != 1:
        raise RuntimeError(f"Unsupported SQLite schema version: {version}")
