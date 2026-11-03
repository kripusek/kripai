"""Historia i niezmienne rewizje GitHuba, tylko odczyt ograniczonej porcji."""
import json
import re
from datetime import datetime
from urllib.parse import quote, urlencode
from .network import ToolError
from .github_pulls import sensitive_path

SHA = re.compile(r'(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})')


def read(repo, section, ref, request):
    def invalid():
        raise ToolError('tool_format_denied')

    def get(suffix):
        try:
            return json.loads(request(suffix)['data'])
        except (ValueError, KeyError, TypeError):
            invalid()

    def text(row, key, default=''):
        value = row.get(key, default)
        if value is None:
            return ''
        if not isinstance(value, str):
            invalid()
        return value

    def sha(value):
        if not isinstance(value, str) or not SHA.fullmatch(value):
            invalid()
        return value.lower()

    def metadata(row):
        if not isinstance(row, dict) or not isinstance(row.get('commit'), dict):
            invalid()
        version = sha(row.get('sha'))
        commit = row['commit']
        message = text(commit, 'message')
        author = commit.get('author')
        if author is not None and not isinstance(author, dict):
            invalid()
        author = author or {}
        name = text(author, 'name')
        # Nie przekazujemy pól email, login ani podpisu; nazwa też bywa mailem.
        name = 'autor niedostępny' if not name or '@' in name else name[:100]
        date = text(author, 'date')
        if date:
            try:
                parsed = datetime.fromisoformat(date.replace('Z', '+00:00'))
                if len(date) > 40 or parsed.tzinfo is None:
                    invalid()
            except ValueError:
                invalid()
        return version, message, name, date

    if section == 'commits':
        query = {'per_page': 11}
        if ref:
            query['sha'] = ref
        rows = get('commits?' + urlencode(query))
        if not isinstance(rows, list):
            invalid()
        items = []
        partial = len(rows) > 10
        seen = set()
        for row in rows[:10]:
            version, message, author, date = metadata(row)
            if version in seen:
                invalid()
            seen.add(version)
            title = (message.splitlines() or [''])[0]
            partial |= len(title) > 200
            items.append({'sha': version, 'title': title[:200], 'author': author,
                          'date': date, 'url': 'https://github.com/' + repo + '/commit/' + version})
        value = '\n'.join(item['sha'] + ' · ' + item['title'] for item in items)
        note = 'Pierwsza porcja historii, do 10 commitów; nie jest to pełna historia repozytorium.'
        return {'url': 'https://github.com/' + repo + '/commits/' + quote(ref or 'HEAD', safe=''),
                'title': repo + ' · historia commitów', 'text': value, 'excerpt': value[:1200],
                'content_kind': 'commit_list', 'items': items, 'count': len(items),
                'limit': 10, 'ref': ref, 'truncated': partial, 'scope_note': note}

    if section != 'commit' or not isinstance(ref, str) or not SHA.fullmatch(ref):
        raise ToolError('tool_arguments_invalid')
    data = get('commits/' + ref.lower() + '?per_page=21')
    version, message, author, date = metadata(data)
    if version != ref.lower():
        raise ToolError('github_commit_mismatch')
    parents = data.get('parents')
    stats = data.get('stats')
    files = data.get('files')
    if not isinstance(parents, list) or len(parents) > 100 or not isinstance(stats, dict) or not isinstance(files, list):
        invalid()
    parent_shas = []
    for parent in parents:
        if not isinstance(parent, dict):
            invalid()
        parent_shas.append(sha(parent.get('sha')))
    stats = {key: stats.get(key) for key in ('additions', 'deletions', 'total')}
    if any(type(value) is not int or value < 0 for value in stats.values()):
        invalid()
    partial = len(message) > 4000 or len(files) > 20
    lines = ['Commit SHA: ' + version, 'Autor: ' + author, 'Data: ' + date,
             'Parents: ' + ', '.join(parent_shas),
             'Dodane/usunięte linie: ' + str(stats['additions']) + '/' + str(stats['deletions']),
             'Opis (niezaufana treść):', message[:4000], 'Zmiany (niezaufana treść):']
    omitted = missing = patches = 0
    for row in files[:20]:
        if not isinstance(row, dict):
            invalid()
        name = text(row, 'filename')
        previous = text(row, 'previous_filename')
        state = text(row, 'status')
        if not name or not state or any(c in name + previous for c in '\x00\r\n'):
            invalid()
        partial |= len(name) > 500 or len(previous) > 500 or len(state) > 30
        lines.append('\nFile: ' + name[:500] + ' [' + state[:30] + ']')
        if previous:
            lines.append('Previous filename: ' + previous[:500])
        if sensitive_path(name) or sensitive_path(previous):
            omitted += 1
            partial = True
            lines.append('Diff pominięty: nazwa wskazuje poświadczenia lub prywatne dane.')
            continue
        patch = row.get('patch')
        if patch is None:
            missing += 1
            partial = True
            lines.append('Brak tekstowego diff w API; nie oznacza braku zmian (np. plik binarny).')
            continue
        if not isinstance(patch, str):
            invalid()
        if '\x00' in patch:
            missing += 1
            partial = True
            lines.append('Diff binarny pominięty.')
            continue
        patches += 1
        partial |= len(patch) > 6000
        lines.append(patch[:6000])
    value = '\n'.join(lines)
    partial |= len(value) > 130000
    note = ('Odczyt niezmiennego SHA: pierwsza porcja API, do 20 plików i 6000 znaków patcha. '
            'Całkowita liczba plików jest nieznana; brak patcha nie oznacza braku zmian. '
            'GitHub może ograniczać diff; nie jest to gwarancja pełnego diff. Bez uprawnień edycji.')
    return {'url': 'https://github.com/' + repo + '/commit/' + version,
            'title': repo + ' · commit ' + version[:12], 'sha': version,
            'text': value[:1200], 'document': value[:130000], 'excerpt': value[:1200],
            'content_kind': 'commit', 'parent_shas': parent_shas, 'stats': stats,
            'processed_files': min(20, len(files)), 'total_files': None,
            'text_patch_files': patches, 'missing_patch_files': missing,
            'omitted_sensitive_files': omitted, 'truncated': bool(partial), 'scope_note': note}
