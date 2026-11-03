CREATE TABLE upload_sessions (
 id TEXT PRIMARY KEY,
 generation TEXT NOT NULL DEFAULT (lower(hex(randomblob(16)))) CHECK(length(generation)=32),
 owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL,
 filename TEXT NOT NULL CHECK(length(filename) BETWEEN 1 AND 180),
 size INTEGER NOT NULL CHECK(size BETWEEN 1 AND 8388608),
 sha256 TEXT NOT NULL CHECK(length(sha256)=64),
 received INTEGER NOT NULL DEFAULT 0 CHECK(received BETWEEN 0 AND size),
 data BLOB NOT NULL DEFAULT X'',
 status TEXT NOT NULL DEFAULT 'uploading' CHECK(status IN ('uploading','completed')),
 attachment_id TEXT REFERENCES attachments(id) ON DELETE SET NULL,
 created_at REAL NOT NULL DEFAULT (unixepoch()),
 expires_at REAL NOT NULL,
 CHECK((status='uploading' AND length(data)=received AND attachment_id IS NULL) OR (status='completed' AND length(data)=0 AND received=size))
);
CREATE INDEX upload_sessions_owner ON upload_sessions(owner_id,expires_at);
