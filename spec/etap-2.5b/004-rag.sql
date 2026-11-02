CREATE TABLE IF NOT EXISTS rag_documents (
 attachment_id TEXT PRIMARY KEY REFERENCES attachments(id) ON DELETE CASCADE,
 owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
 space TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','indexing','ready','paused','failed')),
 next_page INTEGER NOT NULL DEFAULT 1,
 chunks INTEGER NOT NULL DEFAULT 0,
 error_code TEXT,
 updated_at REAL NOT NULL DEFAULT(unixepoch())
);
CREATE TABLE IF NOT EXISTS rag_chunks (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 attachment_id TEXT NOT NULL REFERENCES rag_documents(attachment_id) ON DELETE CASCADE,
 page INTEGER NOT NULL CHECK(page>=1),
 ordinal INTEGER NOT NULL,
 text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 1000),
 UNIQUE(attachment_id,page,ordinal)
);
CREATE VIRTUAL TABLE IF NOT EXISTS rag_vectors USING vec0(
 chunk_id INTEGER PRIMARY KEY,
 owner_id TEXT PARTITION KEY,
 document_id TEXT PARTITION KEY,
 embedding FLOAT[384] distance_metric=cosine
);
ALTER TABLE runs ADD COLUMN rag_selection TEXT NOT NULL DEFAULT '[]';
CREATE TABLE IF NOT EXISTS message_sources (
 message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 ordinal INTEGER NOT NULL,
 attachment_id TEXT NOT NULL REFERENCES attachments(id) ON DELETE CASCADE,
 page INTEGER NOT NULL,
 excerpt TEXT NOT NULL CHECK(length(excerpt)<=1000),
 PRIMARY KEY(message_id,ordinal)
);
