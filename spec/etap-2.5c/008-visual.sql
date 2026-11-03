CREATE TABLE visual_documents (
 attachment_id TEXT PRIMARY KEY REFERENCES attachments(id) ON DELETE CASCADE,
 owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
 generation TEXT NOT NULL CHECK(length(generation)=32),
 space TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','indexing','ready','paused','failed')),
 next_page INTEGER NOT NULL DEFAULT 1 CHECK(next_page>=1),
 images INTEGER NOT NULL DEFAULT 0 CHECK(images>=0),
 error_code TEXT,
 updated_at REAL NOT NULL DEFAULT(unixepoch())
);
CREATE TABLE visual_pages (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 attachment_id TEXT NOT NULL REFERENCES visual_documents(attachment_id) ON DELETE CASCADE,
 page INTEGER NOT NULL CHECK(page>=1),
 preview_sha256 TEXT NOT NULL CHECK(length(preview_sha256)=64),
 UNIQUE(attachment_id,page)
);
CREATE VIRTUAL TABLE visual_vectors USING vec0(
 page_id INTEGER PRIMARY KEY,
 owner_id TEXT PARTITION KEY,
 document_id TEXT PARTITION KEY,
 space TEXT PARTITION KEY,
 embedding FLOAT[768] distance_metric=cosine
);
