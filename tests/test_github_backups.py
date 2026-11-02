"""Backup API na rzeczywistym SQLite, w tym WAL i awarie zestawu kopii."""
import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch
from app import config,github_changes as changes,github_backups as journals,maintenance
from app.db import connect
from app.network import ToolError
from test_native import DataCase

class GithubBackupTests(DataCase):
    def add(self,state='prepared',did=None):
        did=did or str(uuid4())
        data={'repository':changes.WRITE_REPOSITORY,'title':'README','body':'Description','base':'main','head':'a'*40,'files':[{'path':'README.md','content':'# Test\n','mode':'100644','diff':'+Test'}]}
        result=json.dumps({'branch':'kripai/'+did,'url':'https://github.com/'+changes.WRITE_REPOSITORY+'/pull/1'}) if state=='published' else None
        with changes.store() as conn:conn.execute('INSERT INTO drafts VALUES (?,?,?,?,?)',(did,self.user(),json.dumps(data),state,result))
        return did

    def test_backup_live_wal_and_merge_does_not_roll_back_published_or_newer_rows(self):
        did=self.add()
        live=sqlite3.connect(config.DATA/'github-changes.sqlite3')
        try:
            live.execute('PRAGMA journal_mode=WAL');live.execute("UPDATE drafts SET state='publishing' WHERE id=?",(did,));live.commit()
            self.assertTrue(Path(str(config.DATA/'github-changes.sqlite3')+'-wal').exists())
            archive=maintenance.backup();self.assertEqual(journals.load(archive)[0][3],'publishing')
            standalone=sqlite3.connect(journals.companion(archive))
            try:self.assertEqual(standalone.execute('PRAGMA journal_mode').fetchone()[0],'delete')
            finally:standalone.close()
            self.assertFalse(list(config.BACKUPS.glob('*.partial*')))
            result=json.dumps({'branch':'kripai/'+did,'url':'https://github.com/'+changes.WRITE_REPOSITORY+'/pull/1'})
            live.execute("UPDATE drafts SET state='published',result=? WHERE id=?",(result,did));live.commit()
        finally:live.close()
        newer=self.add()
        maintenance.restore(archive)
        rows={r['id']:r for r in changes.list_drafts(self.user())}
        self.assertEqual(rows[did]['state'],'published');self.assertEqual(rows[newer]['state'],'prepared')

    def test_lost_journal_restores_without_permission_to_replay_writes(self):
        did=self.add();published=self.add('published');archive=maintenance.backup()
        (config.DATA/'github-changes.sqlite3').unlink()  # Kompletna kopia już istnieje.
        maintenance.restore(archive)
        rows={r['id']:r for r in changes.list_drafts(self.user())}
        self.assertEqual(rows[did]['state'],'outcome_unknown');self.assertEqual(rows[published]['state'],'published')
        with patch.object(changes,'api',side_effect=AssertionError('no network')):
            with self.assertRaises(ToolError):changes.publish(did,self.user())

    def test_legacy_backup_keeps_current_journal(self):
        archive=maintenance.backup();did=self.add()
        self.assertEqual(journals.load(archive),[])
        maintenance.restore(archive)
        self.assertEqual(changes.list_drafts(self.user())[0]['id'],did)

    def test_corrupt_or_incomplete_companion_does_not_replace_main(self):
        self.add();archive=maintenance.backup();cid=self.conversation()
        companion=journals.companion(archive);companion.write_bytes(companion.read_bytes()+b'broken')
        with self.assertRaises(ValueError):maintenance.restore(archive)
        with connect() as conn:self.assertTrue(conn.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone())
        journals.checksum(archive).unlink()
        with self.assertRaises(ValueError):maintenance.restore(archive)

    def test_schema_and_unsafe_repository_rejected_even_with_matching_checksum(self):
        did=self.add();archive=maintenance.backup();file=journals.companion(archive)
        conn=sqlite3.connect(file)
        try:
            conn.execute("CREATE TRIGGER unexpected AFTER INSERT ON drafts BEGIN DELETE FROM drafts; END");conn.commit()
        finally:conn.close()
        journals.checksum(archive).write_text(hashlib.sha256(file.read_bytes()).hexdigest())
        with self.assertRaises(ValueError):journals.load(archive)
        with changes.store() as conn:
            row=conn.execute('SELECT data FROM drafts WHERE id=?',(did,)).fetchone();data=json.loads(row['data']);data['repository']='other/repo';conn.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(data),did))
        before=set(config.BACKUPS.glob('kripai-*.sqlite3'))
        with self.assertRaises(ValueError):maintenance.backup()
        self.assertEqual(set(config.BACKUPS.glob('kripai-*.sqlite3')),before)
        self.assertFalse(list(config.BACKUPS.glob('*.partial')))

    def test_checksum_disk_failure_does_not_publish_incomplete_main_backup(self):
        self.add();write=Path.write_text
        def fail(path,*args,**kwargs):
            if str(path).endswith('.github.sha256'):raise OSError('disk full')
            return write(path,*args,**kwargs)
        with patch.object(Path,'write_text',fail):
            with self.assertRaises(OSError):maintenance.backup()
        self.assertEqual(list(config.BACKUPS.glob('*')),[])
        self.assertEqual(len(changes.list_drafts(self.user())),1)

    def test_conflicting_draft_rolls_back_merge_and_preserves_main(self):
        did=self.add();archive=maintenance.backup();cid=self.conversation()
        with changes.store() as conn:
            row=conn.execute('SELECT data FROM drafts WHERE id=?',(did,)).fetchone();data=json.loads(row['data']);data['title']='Newer proposal';conn.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(data),did))
        with self.assertRaises(ValueError):maintenance.restore(archive)
        with connect() as conn:self.assertTrue(conn.execute('SELECT 1 FROM conversations WHERE id=?',(cid,)).fetchone())
        self.assertFalse((config.DATA/'restore.partial').exists())

    def test_retention_removes_only_matching_companions(self):
        self.add();config.BACKUPS.mkdir(exist_ok=True);foreign=config.BACKUPS/'foreign.github';foreign.write_text('keep')
        for _ in range(16):maintenance.backup()
        self.assertEqual(len(list(config.BACKUPS.glob('kripai-*.sqlite3'))),14)
        self.assertEqual(len(list(config.BACKUPS.glob('*.sqlite3.github'))),14)
        self.assertEqual(len(list(config.BACKUPS.glob('*.sqlite3.github.sha256'))),14)
        self.assertEqual(foreign.read_text(),'keep')

    def test_size_limit_is_checked_before_reading_snapshot_into_memory(self):
        self.add();archive=maintenance.backup()
        with patch.object(journals,'MAX_JOURNAL',1),patch.object(Path,'read_bytes',side_effect=AssertionError('must not read oversized file')):
            with self.assertRaises(ValueError):journals.load(archive)

    def test_snapshot_timeout_does_not_leave_a_completed_backup(self):
        self.add()
        with patch.object(journals.time,'monotonic',side_effect=[0,21]):
            with self.assertRaises(TimeoutError):maintenance.backup()
        self.assertEqual(list(config.BACKUPS.glob('*')),[])

    def test_published_proof_from_backup_dominates_rolled_back_prepared_state(self):
        did=self.add('published');archive=maintenance.backup()
        with changes.store() as conn:conn.execute("UPDATE drafts SET state='prepared',result=NULL WHERE id=?",(did,))
        maintenance.restore(archive)
        self.assertEqual(changes.list_drafts(self.user())[0]['state'],'published')
        with patch.object(changes,'api',side_effect=AssertionError('no duplicate write')):
            self.assertTrue(changes.publish(did,self.user())['url'].endswith('/pull/1'))
