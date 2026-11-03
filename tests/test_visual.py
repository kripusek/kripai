"""Obrazowy indeks: prawdziwe SQLite/vec0/dekodery; inference jest atrapą."""
from contextlib import contextmanager
import concurrent.futures
import io
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from uuid import uuid4
from PIL import Image
from test_native import DataCase
from test_media import pdf, png
from app import config, media, maintenance, rag, visual, visual_encoder, voice
from app.db import connect, migrate, migration_checksums
from app.visual_encoder import VisualError


def unit(index=0):
    values = [0.0]*768
    values[index] = 1.0
    return struct.pack('<768f', *values)


class FakeVisualEncoder:
    def __init__(self):
        self.images = 0
    def embed_image(self, preview):
        with Image.open(io.BytesIO(preview)) as image:
            assert image.format == 'PNG'
        value = unit(self.images % 2)
        self.images += 1
        return value
    def embed_text(self, query):
        return unit(0 if 'first' in query or 'pierwsz' in query else 1)


@contextmanager
def fake_session(check):
    check()
    yield FakeVisualEncoder()


class VisualDataTests(DataCase):
    def setUp(self):
        super().setUp()
        visual.STOP.clear()
        self.guard = voice.VoiceService()
        self.stack.enter_context(patch.object(media, 'guard', self.guard))
        self.stack.enter_context(patch.object(visual_encoder, 'session', fake_session))
        self.uid, self.sid, self.aid = self.user(), str(uuid4()), str(uuid4())
        self.user_data = {'id': self.uid, 'session_id': self.sid}
        with connect() as conn:
            conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,NULL)',
                         (self.sid, self.uid, b'visual-token', b'visual-csrf', time.time()+600))
            conn.execute('''INSERT INTO attachments(id,owner_id,filename,media_type,original,preview,pages,current_page)
              VALUES (?,?,?,'application/pdf',?,?,2,2)''', (self.aid, self.uid, 'obrazy.pdf', pdf(), b'PNG'))

    def ready(self):
        visual.queue(self.aid, self.user_data)
        self.assertTrue(visual.process_next())
        with connect() as conn:
            state = conn.execute('SELECT * FROM visual_documents WHERE attachment_id=?', (self.aid,)).fetchone()
            self.assertEqual(state['status'], 'ready', state)
        return state

    def counts(self):
        with connect() as conn:
            return [conn.execute('SELECT count(*) AS n FROM '+name).fetchone()['n']
                    for name in ('visual_documents', 'visual_pages', 'visual_vectors')]

    def test_real_pdf_decode_768_space_page_checkpoint_and_preview_unchanged(self):
        state = self.ready()
        self.assertEqual((state['next_page'], state['images'], state['space']), (3, 2, visual.SPACE))
        self.assertEqual(self.counts(), [1, 2, 2])
        with connect() as conn:
            stored = conn.execute('SELECT current_page,preview FROM attachments WHERE id=?', (self.aid,)).fetchone()
            self.assertEqual(stored, {'current_page': 2, 'preview': b'PNG'})
            self.assertEqual(conn.execute('SELECT length(embedding) AS n FROM visual_vectors LIMIT 1').fetchone()['n'], 3072)
            self.assertEqual(conn.execute('SELECT count(DISTINCT preview_sha256) AS n FROM visual_pages').fetchone()['n'], 2)
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM rag_vectors').fetchone()['n'], 0)
        self.assertEqual(visual.queue(self.aid, self.user_data), {'status': 'ready'})
        self.assertFalse(visual.process_next())

    def test_png_and_jpeg_use_real_decoder_and_do_not_need_text_layer(self):
        for kind in ('PNG', 'JPEG'):
            with self.subTest(kind=kind):
                stream = io.BytesIO()
                Image.new('RGB', (30, 10), 'red').save(stream, format=kind)
                with connect() as conn:
                    visual.clear(conn, self.aid, self.uid)
                    conn.execute('''UPDATE attachments SET media_type=?,original=?,pages=1,current_page=1,
                      text_layer='' WHERE id=?''', ('image/png' if kind == 'PNG' else 'image/jpeg', stream.getvalue(), self.aid))
                state = self.ready()
                self.assertEqual((state['images'], state['next_page']), (1, 2))

    def test_acl_selected_ids_and_space_are_inside_actual_knn(self):
        self.ready()
        with connect() as conn:
            first = conn.execute('SELECT id FROM visual_pages WHERE page=1').fetchone()['id']
            value = [.8, .6]+[0.0]*766
            conn.execute('UPDATE visual_vectors SET embedding=? WHERE page_id=?', (struct.pack('<768f', *value), first))
            for index in range(10):
                for pid, owner, aid, space in ((1000+index, 'other', self.aid, visual.SPACE),
                       (2000+index, self.uid, 'not-selected', visual.SPACE),
                       (3000+index, self.uid, self.aid, 'old-space')):
                    conn.execute('INSERT INTO visual_vectors VALUES (?,?,?,?,?)', (pid, owner, aid, space, unit()))
            plan = conn.execute('''EXPLAIN QUERY PLAN SELECT page_id FROM visual_vectors
              WHERE embedding MATCH ? AND k=3 AND owner_id=? AND document_id=? AND space=?''',
              (unit(), self.uid, self.aid, visual.SPACE)).fetchall()
            self.assertTrue(any('VIRTUAL TABLE INDEX' in str(row) for row in plan))
        hits = visual.retrieve([self.aid], self.uid, 'first image', lambda: None)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]['page'], 1)
        self.assertGreater(hits[0]['distance'], 0)
        with self.assertRaises(VisualError) as error:
            visual.retrieve([self.aid], 'other', 'first', lambda: None)
        self.assertEqual(error.exception.status, 404)

    def test_failure_checkpoint_resume_keeps_prior_page_without_duplicates(self):
        visual.queue(self.aid, self.user_data)
        original = media.decode
        def fail(data, page, *args):
            if page == 2:
                raise OSError('synthetic decoder failure')
            return original(data, page, *args)
        with patch.object(media, 'decode', fail):
            visual.process_next()
        with connect() as conn:
            state = conn.execute('SELECT * FROM visual_documents').fetchone()
            self.assertEqual((state['status'], state['next_page'], state['images']), ('failed', 2, 1))
        self.ready()
        self.assertEqual(self.counts(), [1, 2, 2])

    def test_pause_during_inference_never_commits_and_old_generation_cannot_change_new_job(self):
        visual.queue(self.aid, self.user_data)
        class Pausing(FakeVisualEncoder):
            def embed_image(inner, data):
                visual.pause(self.aid, self.uid)
                visual.queue(self.aid, self.user_data)
                return super().embed_image(data)
        @contextmanager
        def session(check):
            yield Pausing()
        with patch.object(visual_encoder, 'session', session):
            visual.process_next()
        self.assertEqual(self.counts(), [1, 0, 0])
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT status FROM visual_documents').fetchone()['status'], 'queued')
        self.assertTrue(visual.process_next())
        self.assertEqual(self.counts(), [1, 2, 2])

    def test_session_and_gaming_checked_in_atomic_write_even_if_outer_check_is_stale(self):
        for change, expected in (("UPDATE sessions SET revoked_at=now()", 'login_required'),
                                 ("UPDATE system_mode SET requested_mode='gaming'", 'gaming_mode')):
            with self.subTest(expected=expected):
                with connect() as conn:
                    conn.execute('UPDATE sessions SET revoked_at=NULL')
                    conn.execute("UPDATE system_mode SET requested_mode='normal'")
                visual.queue(self.aid, self.user_data, rebuild=True)
                class Revoking(FakeVisualEncoder):
                    def embed_image(inner, data):
                        with connect() as conn:
                            conn.execute(change)
                        return super().embed_image(data)
                @contextmanager
                def session(check):
                    yield Revoking()
                with patch.object(visual_encoder, 'session', session), patch.object(visual, 'check_document', return_value=None):
                    visual.process_next()
                self.assertEqual(self.counts(), [1, 0, 0])
                with connect() as conn:
                    state = conn.execute('SELECT status,error_code FROM visual_documents').fetchone()
                    self.assertEqual(state, {'status': 'paused', 'error_code': expected})

    def test_deletion_during_inference_does_not_resurrect_vector(self):
        visual.queue(self.aid, self.user_data)
        class Deleting(FakeVisualEncoder):
            def embed_image(inner, data):
                media.delete(self.aid, self.uid)
                return super().embed_image(data)
        @contextmanager
        def session(check):
            yield Deleting()
        with patch.object(visual_encoder, 'session', session):
            visual.process_next()
        self.assertEqual(self.counts(), [0, 0, 0])
        with connect() as conn:
            self.assertIsNone(conn.execute('SELECT 1 FROM attachments').fetchone())

    def test_cancellation_kills_real_decoder_child(self):
        visual.queue(self.aid, self.user_data)
        folder = config.DATA/'visual-cancel'
        folder.mkdir()
        children = []
        popen = subprocess.Popen
        def launch(argv, **kwargs):
            child = popen(argv, **kwargs)
            children.append(child)
            return child
        def decode(data, page, key, cancelled):
            media.guard.process([sys.executable, '-c', "from pathlib import Path;import time;Path('ready').touch();time.sleep(60)"],
                                folder, key, cancelled, 20)
            raise AssertionError('cancelled child must not finish normally')
        with patch.object(media, 'decode', decode), patch.object(voice.subprocess, 'Popen', launch), concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(visual.process_next)
            for _ in range(150):
                if (folder/'ready').exists():
                    break
                time.sleep(.02)
            self.assertTrue((folder/'ready').exists())
            visual.pause(self.aid, self.uid)
            future.result(5)
        self.assertTrue(children and all(child.poll() is not None for child in children))
        self.assertEqual(self.counts(), [1, 0, 0])

    def test_invalid_packed_vector_and_actual_sql_insert_failure_roll_back_page(self):
        for value in (b'', unit()[:1536], struct.pack('<768f', float('nan'), *([0.0]*767)),
                      struct.pack('<768f', *([0.0]*768)), struct.pack('<768f', 2.0, *([0.0]*767))):
            with self.subTest(size=len(value)), self.assertRaises(VisualError):
                visual.valid_vector(value)
        visual.queue(self.aid, self.user_data)
        # Obchodzimy walidator wyłącznie w teście: rzeczywisty vec0 odrzuca 384d.
        with patch.object(visual, 'valid_vector', return_value=unit()[:1536]):
            visual.process_next()
        self.assertEqual(self.counts(), [1, 0, 0])
        with connect() as conn:
            state = conn.execute('SELECT status,next_page,images FROM visual_documents').fetchone()
            self.assertEqual(state, {'status': 'failed', 'next_page': 1, 'images': 0})

    def test_backup_restore_remove_file_and_backup_failure_preserve_data(self):
        self.ready()
        backup = maintenance.backup()
        with patch.object(maintenance, 'backup', side_effect=OSError('synthetic disk full')):
            with self.assertRaises(OSError):
                visual.remove(self.aid, self.uid)
            with self.assertRaises(OSError):
                visual.queue(self.aid, self.user_data, rebuild=True)
        self.assertEqual(self.counts(), [1, 2, 2])
        visual.remove(self.aid, self.uid)
        self.assertEqual(self.counts(), [0, 0, 0])
        maintenance.restore(backup)
        self.assertEqual(self.counts(), [1, 2, 2])
        media.delete(self.aid, self.uid)
        self.assertEqual(self.counts(), [0, 0, 0])

    def test_corrupt_derived_index_prevents_backup_publication(self):
        self.ready()
        with connect() as conn:
            conn.execute('DELETE FROM visual_vectors WHERE page_id=(SELECT min(id) FROM visual_pages)')
        with self.assertRaises(ValueError):
            maintenance.backup()
        self.assertEqual(list(config.BACKUPS.glob('*.partial')), [])
        self.assertEqual(list(config.BACKUPS.glob('*.sqlite3')), [])

    def test_model_mismatch_requires_explicit_backup_and_rebuild(self):
        self.ready()
        with connect() as conn:
            conn.execute("UPDATE visual_documents SET space='old-model'")
            rows = conn.execute('SELECT page_id,owner_id,document_id,embedding FROM visual_vectors').fetchall()
            # vec0 0.1.6 nie aktualizuje partition key; starsza przestrzeń ma własne rekordy.
            conn.execute('DELETE FROM visual_vectors')
            for row in rows:
                conn.execute('INSERT INTO visual_vectors VALUES (?,?,?,?,?)',
                             (row['page_id'], row['owner_id'], row['document_id'], 'old-model', row['embedding']))
        for action in (lambda: visual.queue(self.aid, self.user_data),
                       lambda: visual.retrieve([self.aid], self.uid, 'first', lambda: None)):
            with self.assertRaises(VisualError) as error:
                action()
            self.assertEqual(error.exception.code, 'visual_model_changed')
        visual.queue(self.aid, self.user_data, rebuild=True)
        self.assertGreater(len(list(config.BACKUPS.glob('*.sqlite3'))), 0)
        self.ready()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT space FROM visual_documents').fetchone()['space'], visual.SPACE)

    def test_selected_limit_query_limits_and_shared_e5_encoder_lock(self):
        self.ready()
        for ids in ([], [str(uuid4()) for _ in range(6)], None):
            with self.subTest(ids=ids), self.assertRaises(VisualError):
                visual.retrieve(ids, self.uid, 'first', lambda: None)
        for query in ('', ' ', 'x'*501, None):
            with self.subTest(query=str(query)[:10]), self.assertRaises(VisualError):
                visual.retrieve([self.aid], self.uid, query, lambda: None)
        with rag.ENCODER_LOCK, self.assertRaises(VisualError) as error:
            visual.retrieve([self.aid], self.uid, 'first', lambda: None)
        self.assertEqual(error.exception.code, 'visual_busy')
        self.assertEqual(len(visual.retrieve([self.aid, self.aid], self.uid, 'first', lambda: None)), 2)

    def test_selection_rechecked_after_encoder_finishes(self):
        self.ready()
        class Removing(FakeVisualEncoder):
            def embed_text(inner, query):
                visual.remove(self.aid, self.uid)
                return unit()
        @contextmanager
        def session(check):
            yield Removing()
        with patch.object(visual_encoder, 'session', session), self.assertRaises(VisualError) as error:
            visual.retrieve([self.aid], self.uid, 'first', lambda: None)
        self.assertEqual(error.exception.status, 404)

    def test_quota_rollback_and_revoked_session_never_starts_encoder(self):
        visual.queue(self.aid, self.user_data)
        with patch.object(visual, 'MAX_IMAGES', 0):
            visual.process_next()
        self.assertEqual(self.counts(), [1, 0, 0])
        visual.queue(self.aid, self.user_data)
        with connect() as conn:
            conn.execute('UPDATE sessions SET revoked_at=now()')
        with patch.object(visual_encoder, 'session', side_effect=AssertionError('must not start')):
            visual.process_next()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT status FROM visual_documents').fetchone()['status'], 'paused')

    def test_restart_resumes_checkpoint_and_list_filters_owner_without_runtime_probe(self):
        visual.queue(self.aid, self.user_data)
        with connect() as conn:
            conn.execute("UPDATE visual_documents SET status='indexing'")
        visual.start()
        try:
            for _ in range(150):
                with connect() as conn:
                    status = conn.execute('SELECT status FROM visual_documents').fetchone()['status']
                if status == 'ready':
                    break
                time.sleep(.03)
            self.assertEqual(status, 'ready')
        finally:
            visual.shutdown()
            visual.STOP.clear()
        with patch.object(visual_encoder, 'session', side_effect=AssertionError('no auto model')):
            result = visual.list_documents(self.uid)
            self.assertEqual((len(result['items']), result['dimensions']), (1, 768))
            self.assertEqual(visual.list_documents('other')['items'], [])

    def test_v7_migration_backup_guard_and_atomic_upgrade(self):
        with connect() as conn:
            for table in ('visual_vectors', 'visual_pages', 'visual_documents'):
                conn.execute('DROP TABLE '+table)
            conn.execute('ALTER TABLE message_images DROP COLUMN page')
            conn.execute('DELETE FROM schema_migrations WHERE version>=8')
        with patch.object(maintenance, 'backup', side_effect=OSError('synthetic disk full')):
            with self.assertRaises(OSError):
                migrate()
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT max(version) AS n FROM schema_migrations').fetchone()['n'], 7)
        migrate()
        self.assertGreater(len(list(config.BACKUPS.glob('*.sqlite3'))), 0)
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT max(version) AS n FROM schema_migrations').fetchone()['n'], len(migration_checksums()))
            self.assertIsNotNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='visual_vectors'").fetchone())
