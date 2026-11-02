"""Odtworzenie starszego schematu w testach migracji, bez pozostałości nowych kolumn."""
def drop_tools(conn):
    conn.execute('DROP TABLE IF EXISTS tool_sources')
    columns={row['name'] for row in conn.execute('PRAGMA table_info(runs)')}
    for column in ('allow_web','allow_github','tool_session_id','allow_mcp'):
        if column in columns:conn.execute('ALTER TABLE runs DROP COLUMN '+column)
    conn.execute('DELETE FROM schema_migrations WHERE version>=5')
