ALTER TABLE runs ADD COLUMN allow_web INTEGER NOT NULL DEFAULT 0 CHECK(allow_web IN (0,1));
ALTER TABLE runs ADD COLUMN allow_github INTEGER NOT NULL DEFAULT 0 CHECK(allow_github IN (0,1));
ALTER TABLE runs ADD COLUMN tool_session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL;
CREATE TABLE tool_sources (
 message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
 ordinal INTEGER NOT NULL,
 name TEXT NOT NULL,
 url TEXT NOT NULL,
 title TEXT NOT NULL,
 excerpt TEXT NOT NULL CHECK(length(excerpt)<=1200),
 PRIMARY KEY(message_id,ordinal)
);
