ALTER TABLE system_mode ADD COLUMN requested_profile TEXT NOT NULL DEFAULT 'text' CHECK(requested_profile IN ('text','vision'));
ALTER TABLE system_mode ADD COLUMN loaded_profile TEXT NOT NULL DEFAULT 'none' CHECK(loaded_profile IN ('none','text','vision'));
CREATE TABLE attachments (
 id TEXT PRIMARY KEY,
 owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 filename TEXT NOT NULL CHECK(length(filename) BETWEEN 1 AND 180),
 media_type TEXT NOT NULL CHECK(media_type IN ('image/png','image/jpeg','application/pdf')),
 original BLOB NOT NULL CHECK(length(original) BETWEEN 1 AND 8388608),
 preview BLOB NOT NULL CHECK(length(preview) BETWEEN 1 AND 4194304),
 pages INTEGER NOT NULL CHECK(pages BETWEEN 1 AND 50),
 current_page INTEGER NOT NULL CHECK(current_page BETWEEN 1 AND pages),
 text_layer TEXT NOT NULL DEFAULT '' CHECK(length(text_layer)<=12000),
 analysis TEXT NOT NULL DEFAULT '' CHECK(length(analysis)<=12000),
 created_at REAL NOT NULL DEFAULT(unixepoch())
);
CREATE INDEX attachments_owner ON attachments(owner_id,created_at);
