CREATE TABLE message_images (
 message_id TEXT PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
 attachment_id TEXT REFERENCES attachments(id) ON DELETE SET NULL,
 session_id TEXT REFERENCES sessions(id) ON DELETE SET NULL
);
CREATE INDEX message_images_attachment ON message_images(attachment_id);
