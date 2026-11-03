"""Regresja odczytu historii i patchy: sieć kontrolowana, bez zapisu GitHuba."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import config, network, tools
from app.github_commits import read


class CommitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        context = patch.object(config, 'DATA', Path(temp.name))
        context.start()
        self.addCleanup(context.stop)
        self.sha = 'a' * 40
        self.scope = network.policy('owner/repo', github=True)
        self.row = {'sha': self.sha, 'commit': {'message': 'Naprawa żółwia\n\nOpis',
                    'author': {'name': 'Autor', 'email': 'PRIVATE_EMAIL', 'date': '2026-11-03T00:00:00Z'}},
                    'parents': [{'sha': 'b' * 40}], 'stats': {'additions': 1, 'deletions': 0, 'total': 1},
                    'files': [{'filename': 'app/main.py', 'status': 'modified', 'patch': '+print(1)'}],
                    'html_url': 'file:///PRIVATE_URL', 'author': {'login': 'PRIVATE_LOGIN'}}

    def wrap(self, data):
        return {'data': json.dumps(data).encode()}

    def execute(self, **args):
        values = dict(repository='owner/repo', section='commit', ref=self.sha)
        values.update(args)
        return network.execute('github_read', values, self.scope)

    def test_list_is_bounded_canonical_and_ref_encoded_without_full_history_claim(self):
        rows = [dict(self.row, sha=f'{n:040x}') for n in range(11)]
        with patch.object(network, 'fetch', return_value=self.wrap(rows)) as fetch:
            result = self.execute(section='commits', ref='feature/a')
        self.assertEqual(fetch.call_args.args[0], 'https://api.github.com/repos/owner/repo/commits?per_page=11&sha=feature%2Fa')
        self.assertEqual(result['count'], 10)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['url'], 'https://github.com/owner/repo/commits/feature%2Fa')
        self.assertEqual(result['items'][0]['title'], 'Naprawa żółwia')
        self.assertIn('pełna historia', result['scope_note'])
        for forbidden in ('PRIVATE_EMAIL', 'PRIVATE_LOGIN', 'PRIVATE_URL'):
            self.assertNotIn(forbidden, json.dumps(result))

    def test_empty_list_and_short_history_do_not_invent_totals(self):
        for rows in ([], [self.row]):
            with patch.object(network, 'fetch', return_value=self.wrap(rows)):
                result = self.execute(section='commits', ref='')
            self.assertEqual(result['count'], len(rows))
            self.assertFalse(result['truncated'])
            self.assertNotIn('total_count', result)

    def test_commit_immutable_sha_metadata_and_patch_without_edit_permissions(self):
        with patch.object(network, 'fetch', return_value=self.wrap(self.row)) as fetch:
            result = self.execute(ref=self.sha.upper())
        self.assertEqual(fetch.call_count, 1)
        self.assertTrue(fetch.call_args.args[0].endswith('/commits/' + self.sha + '?per_page=21'))
        self.assertEqual(result['url'], 'https://github.com/owner/repo/commit/' + self.sha)
        self.assertIn('+print(1)', result['document'])
        self.assertEqual(result['parent_shas'], ['b' * 40])
        self.assertIsNone(result['total_files'])
        self.assertEqual(result['processed_files'], 1)
        self.assertFalse(result['truncated'])
        self.assertNotIn('editable', result)
        self.assertNotIn('PRIVATE_', json.dumps(result))

    def test_full_sha64_supported_but_mismatched_sha_rejected(self):
        row = dict(self.row, sha='c' * 64)
        with patch.object(network, 'fetch', return_value=self.wrap(row)):
            self.assertEqual(self.execute(ref='c' * 64)['sha'], 'c' * 64)
            with self.assertRaises(network.ToolError) as error:
                self.execute()
            self.assertEqual(error.exception.code, 'github_commit_mismatch')

    def test_permissions_ref_shape_path_and_number_fail_before_fetch(self):
        cases = [({'repository': 'outside/repo'}, 'tool_resource_not_authorized'),
                 ({'ref': 'main'}, 'github_commit_sha_required'),
                 ({'ref': ''}, 'github_commit_sha_required'),
                 ({'path': 'app/main.py'}, 'tool_arguments_invalid'),
                 ({'number': 1}, 'tool_arguments_invalid'),
                 ({'ref': '../main'}, 'tool_arguments_invalid')]
        with patch.object(network, 'fetch', side_effect=AssertionError('No HTTP')):
            for args, code in cases:
                with self.subTest(args=args), self.assertRaises(network.ToolError) as error:
                    self.execute(**args)
                self.assertEqual(error.exception.code, code)
            with self.assertRaises(network.ToolError):
                network.execute('github_read', {'repository': 'owner/repo', 'section': 'commits'}, network.policy('owner/repo'))

    def test_sensitive_renamed_and_current_paths_skip_patch(self):
        row = copy.deepcopy(self.row)
        row['files'] = [{'filename': '.env', 'status': 'modified', 'patch': 'SECRET_PATCH'},
                        {'filename': 'public.txt', 'previous_filename': '.git-credentials', 'status': 'renamed', 'patch': 'SECRET_PATCH'}]
        with patch.object(network, 'fetch', return_value=self.wrap(row)):
            result = self.execute()
        self.assertEqual(result['omitted_sensitive_files'], 2)
        self.assertEqual(result['text_patch_files'], 0)
        self.assertNotIn('SECRET_PATCH', result['document'])
        self.assertTrue(result['truncated'])

    def test_missing_binary_and_limits_are_explicit(self):
        row = copy.deepcopy(self.row)
        row['commit']['message'] = 'm' * 5000
        row['files'] = [{'filename': str(n) + '.txt', 'status': 'modified', 'patch': 'x' * 7000} for n in range(21)]
        row['files'][0].pop('patch')
        row['files'][1]['patch'] = '\x00binary'
        with patch.object(network, 'fetch', return_value=self.wrap(row)):
            result = self.execute()
        self.assertEqual(result['processed_files'], 20)
        self.assertEqual(result['missing_patch_files'], 2)
        self.assertEqual(result['text_patch_files'], 18)
        self.assertTrue(result['truncated'])
        self.assertNotIn('x' * 6001, result['document'])
        self.assertNotIn('m' * 4001, result['document'])
        self.assertIn('nie oznacza braku zmian', result['document'])

    def test_malformed_metadata_files_and_json_do_not_become_empty_success(self):
        invalid = [None, [], dict(self.row, sha='wrong'), dict(self.row, parents=[{}]),
                   dict(self.row, stats={'additions': True, 'deletions': 0, 'total': 1}),
                   dict(self.row, files=[{'filename': 'a', 'status': 'modified', 'patch': {}}]),
                   dict(self.row, files=[{'filename': 'a', 'previous_filename': {}, 'status': 'modified'}])]
        for row in invalid:
            with self.subTest(row=row), patch.object(network, 'fetch', return_value=self.wrap(row)), self.assertRaises(network.ToolError):
                self.execute()
        row = copy.deepcopy(self.row)
        row['commit']['author']['date'] = 'not-a-date'
        with patch.object(network, 'fetch', return_value=self.wrap(row)), self.assertRaises(network.ToolError):
            self.execute()
        with patch.object(network, 'fetch', return_value={'data': b'invalid JSON'}), self.assertRaises(network.ToolError):
            self.execute()

    def test_duplicate_list_shas_bad_date_and_remote_denial_fail(self):
        with patch.object(network, 'fetch', return_value=self.wrap([self.row, self.row])), self.assertRaises(network.ToolError):
            self.execute(section='commits', ref='')
        with patch.object(network, 'fetch', side_effect=network.ToolError('tool_remote_denied')), self.assertRaises(network.ToolError) as error:
            self.execute()
        self.assertEqual(error.exception.code, 'tool_remote_denied')

    def test_tool_schema_exposes_commit_sections_only_with_consent(self):
        definition = next(item for item in tools.schemas(self.scope) if item['function']['name'] == 'github_read')
        choices = definition['function']['parameters']['properties']['section']['enum']
        self.assertIn('commits', choices)
        self.assertIn('commit', choices)
        self.assertFalse(any(item['function']['name'] == 'github_read' for item in tools.schemas(network.policy('owner/repo'))))

    def test_email_like_author_name_is_not_structured_output(self):
        row = copy.deepcopy(self.row)
        row['commit']['author']['name'] = 'private@example.org'
        with patch.object(network, 'fetch', return_value=self.wrap(row)):
            result = self.execute()
        self.assertNotIn('private@example.org', result['document'])
        self.assertIn('autor niedostępny', result['document'])

    def test_commit_read_does_not_authorize_draft_and_feedback_is_honest(self):
        from app import github_changes
        from test_web_search import Reply
        scope = network.policy('kripusek/kripusek-autoexec', github=True)
        scope['owner'] = 'fixture-owner'
        calls = []
        class Client:
            def post(client, path, json):
                if path.endswith('apply-template'):
                    return Reply({'prompt': 'p'})
                if path.endswith('tokenize'):
                    return Reply({'tokens': [1]})
                calls.append(json)
                if len(calls) == 1:
                    name, args = 'github_read', {'repository': 'kripusek/kripusek-autoexec', 'section': 'commits'}
                else:
                    feedback = __import__('json').loads(json['messages'][-1]['content'])
                    self.assertTrue(feedback['feedback_text_truncated'])
                    self.assertNotIn('items', feedback)
                    name, args = 'github_draft', {'repository': 'kripusek/kripusek-autoexec', 'title': 'Proposal', 'body': '', 'files': [{'path': 'README.md', 'content': 'Changed'}]}
                return Reply({'choices': [{'message': {'tool_calls': [{'id': str(len(calls)), 'type': 'function', 'function': {'name': name, 'arguments': __import__('json').dumps(args)}}]}}]})
        def tool_read(name, args, current, check):
            if name == 'github_draft':
                return github_changes.draft(args, current)
            return {'url': 'https://github.com/kripusek/kripusek-autoexec/commits/HEAD', 'title': 'Commits', 'text': 'x' * 2000, 'items': [{'sha': self.sha}], 'sha': self.sha, 'content_kind': 'commit_list', 'truncated': False}
        with patch.object(tools, 'read', side_effect=tool_read):
            results = tools.plan(Client(), [], scope, lambda: None, lambda *a: None)
        self.assertNotIn('editable', results[0])
        self.assertEqual(results[-1]['error'], 'github_read_file_first')
