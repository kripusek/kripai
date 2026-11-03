"""RSS/Atom: jawne zasoby, ograniczone XML i brak udawania odczytu artykułów."""
import json
import unittest
from unittest.mock import patch
from app import feeds, network, tools, integrations

URL = 'https://example.org/feed.xml'
RSS = '<rss version="2.0"><channel><title>Kanał żółwia</title>{}</channel></rss>'
ITEM = '<item><title>Wpis</title><link>https://example.org/article</link><pubDate>Dzisiaj</pubDate><description>&lt;p&gt;Opis&lt;/p&gt;</description></item>'


class FeedTests(unittest.TestCase):
    def parse(self, xml, **extra):
        return feeds.parse(dict(url=URL, kind='application/rss+xml', data=xml.encode(), **extra))

    def test_rss_metadata_and_summary_do_not_claim_full_article(self):
        result = self.parse(RSS.format(ITEM))
        self.assertEqual(result['title'], 'Kanał żółwia')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['items'][0]['excerpt'], 'Opis')
        self.assertEqual(result['format'], 'rss2')
        self.assertIn('nie odczyt artykułów', result['scope_note'])
        self.assertFalse(result['truncated'])

    def test_atom_namespace_relative_links_xml_base_and_updated(self):
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://news.example.org/base/"><title>Atom</title><entry xml:base="posts/"><title>Tytuł</title><updated>2026-11-03T00:00:00Z</updated><link rel="self" href="self.xml"/><link href="one"/><summary type="html">&lt;b&gt;Podgląd&lt;/b&gt;</summary></entry></feed>'''
        result = self.parse(xml)
        self.assertEqual(result['format'], 'atom1')
        self.assertEqual(result['items'][0]['url'], 'https://news.example.org/base/posts/one')
        self.assertEqual(result['items'][0]['date'], '2026-11-03T00:00:00Z')
        self.assertEqual(result['items'][0]['excerpt'], 'Podgląd')

    def test_xhtml_scripts_and_embedded_remote_content_are_not_executed_or_fetched(self):
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom</title><entry><title>T</title><link href="https://example.org/a"/><content type="xhtml" src="https://outside.invalid/SECRET"><div xmlns="http://www.w3.org/1999/xhtml">Tekst<script>SECRET_SCRIPT</script><p>Dalszy tekst</p></div></content></entry></feed>'''
        with patch.object(network, 'fetch', side_effect=AssertionError('No content fetch')):
            result = self.parse(xml)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertIn('Dalszy tekst', result['items'][0]['excerpt'])

    def test_five_entries_description_caps_and_first_twenty_scan_are_honest(self):
        rows = ''.join(ITEM.replace('/article', '/article/' + str(n)).replace('Opis', 'x' * 500) for n in range(8))
        result = self.parse(RSS.format(rows))
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['provided_entries'], 8)
        self.assertEqual(result['scanned_entries'], 5)
        self.assertTrue(result['truncated'])
        self.assertEqual(len(result['items'][0]['excerpt']), 300)

    def test_bad_links_missing_title_and_duplicates_are_omitted_not_followed(self):
        rows = ITEM + ITEM + ITEM.replace('https://example.org/article', 'file:///secret') + ITEM.replace('https://example.org/article', 'https://127.0.0.1/private') + ITEM.replace('<title>Wpis</title>', '')
        result = self.parse(RSS.format(rows))
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['omitted_entries'], 4)
        self.assertTrue(result['truncated'])
        self.assertNotIn('file:', result['text'])
        self.assertNotIn('127.0.0.1', result['text'])

    def test_empty_valid_feed_is_empty_current_feed_not_full_archive(self):
        result = self.parse(RSS.format(''))
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['provided_entries'], 0)
        self.assertIn('całe archiwum', result['scope_note'])

    def test_doctype_entities_encoding_and_malformed_xml_are_denied(self):
        cases = [('feed_xml_denied', '<!DOCTYPE rss [<!ENTITY a "EXPAND">]>' + RSS.format(ITEM)),
                 ('feed_format_denied', '<html><title>Login</title></html>'),
                 ('feed_format_denied', '<rss version="2.0">'),
                 ('feed_encoding_denied', '<?xml version="1.0" encoding="iso-8859-1"?>' + RSS.format(ITEM)),
                 ('feed_format_denied', '<rss version="2.0"><channel/></rss>')]
        for code, xml in cases:
            with self.subTest(code=code), self.assertRaises(network.ToolError) as error:
                self.parse(xml)
            self.assertEqual(error.exception.code, code)
        with self.assertRaises(network.ToolError) as error:
            feeds.parse({'url': URL, 'kind': 'application/rss+xml', 'data': b'\xff\xfeinvalid'})
        self.assertEqual(error.exception.code, 'feed_encoding_denied')

    def test_xml_depth_node_and_body_limits(self):
        for xml in ['<a>' * 22 + '</a>' * 22, RSS.format('<x/>' * 5000)]:
            with self.assertRaises(network.ToolError) as error:
                self.parse(xml)
            self.assertEqual(error.exception.code, 'feed_xml_limit')
        with self.assertRaises(network.ToolError) as error:
            self.parse(RSS.format(''), download_truncated=True)
        self.assertEqual(error.exception.code, 'tool_response_too_large')

    def test_explicit_permission_resource_and_adapter_status(self):
        scope = network.policy(URL, web=True)
        result = dict(url=URL, kind='application/rss+xml', data=RSS.format(ITEM).encode())
        with patch.object(network, 'fetch', return_value=result) as fetch:
            self.assertEqual(integrations.read('feed_read', {'url': URL}, scope)['count'], 1)
            fetch.assert_called_once_with(URL)
        with patch.object(network, 'fetch', side_effect=AssertionError('No HTTP')):
            for args, permitted in [({'url': URL}, network.policy(URL)), ({'url': 'https://outside.org/feed'}, scope), ({'url': URL, 'command': 'bad'}, scope)]:
                with self.assertRaises(network.ToolError):
                    feeds.execute('feed_read', args, permitted)
        self.assertTrue(integrations.ADAPTERS['feeds'].status()['read_only'])
        self.assertFalse(any(d['function']['name'] == 'feed_read' for d in tools.schemas(network.policy(URL))))

    def test_actual_entry_link_can_be_read_in_second_plan_without_new_permissions(self):
        from test_web_search import Reply
        calls = []
        scope = network.policy(URL, web=True)
        class Client:
            def post(client, path, json):
                if path.endswith('apply-template'):
                    return Reply({'prompt': 'p'})
                if path.endswith('tokenize'):
                    return Reply({'tokens': [1]})
                calls.append(json)
                name, url = ('feed_read', URL) if len(calls) == 1 else ('web_read', 'https://example.org/article')
                return Reply({'choices': [{'message': {'tool_calls': [{'id': str(len(calls)), 'type': 'function', 'function': {'name': name, 'arguments': __import__('json').dumps({'url': url})}}]}}]})
        def read(name, args, current, check):
            if name == 'feed_read':
                return self.parse(RSS.format(ITEM))
            self.assertIn(args['url'], current['urls'])
            self.assertFalse(current['github'])
            return {'url': args['url'], 'title': 'Artykuł', 'text': 'Przeczytany artykuł'}
        with patch.object(tools, 'read', side_effect=read):
            result = tools.plan(Client(), [], scope, lambda: None, lambda *a: None)
        self.assertEqual([row['name'] for row in result], ['feed_read', 'web_read'])
        feedback = next(row for row in calls[1]['messages'] if row['role'] == 'tool')
        self.assertNotIn('items', json.loads(feedback['content']))


class FeedAPITests(unittest.TestCase):
    def setUp(self):
        import test_native
        self.base = test_native.APITests('runTest')
        self.addCleanup(self.base.doCleanups)
        self.base.setUp()

    def test_authenticated_explicit_test_reads_feed_without_model_and_handles_failure(self):
        value = feeds.parse({'url': URL, 'kind': 'application/rss+xml', 'data': RSS.format(ITEM).encode()})
        with patch.object(tools, 'read', return_value=value) as read:
            response = self.base.post('/integrations/feeds/test', {'url': URL})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['available'])
        self.assertEqual(read.call_args.args[0], 'feed_read')
        from app.db import connect
        with connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM runs').fetchone()['n'], 0)
        with patch.object(tools, 'read', side_effect=network.ToolError('feed_format_denied')):
            self.assertEqual(self.base.post('/integrations/feeds/test', {'url': URL}).json()['error'], 'feed_format_denied')

    def test_session_revocation_csrf_and_bad_shape_block_test(self):
        from app.db import connect
        def revoke(name, args, scope, check):
            with connect() as conn:
                conn.execute('UPDATE sessions SET revoked_at=now()')
            check()
        self.assertEqual(self.base.post('/integrations/feeds/test', {'url': URL, 'token': 'not-accepted'}).status_code, 422)
        self.assertEqual(self.base.client.post('/api/v1/integrations/feeds/test', json={'url': URL}, headers={'X-CSRF-Token': 'bad'}).status_code, 403)
        with patch.object(tools, 'read', side_effect=revoke):
            self.assertEqual(self.base.post('/integrations/feeds/test', {'url': URL}).status_code, 401)
        self.base.client.cookies.clear()
        self.assertEqual(self.base.post('/integrations/feeds/test', {'url': URL}).status_code, 401)
