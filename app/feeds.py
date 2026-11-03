"""Publiczne RSS 2.0 / Atom 1.0: ograniczone opisy, bez pobierania artykułów."""
import ipaddress
import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit
from . import network
from .network import ToolError

ATOM = '{http://www.w3.org/2005/Atom}'
XML_BASE = '{http://www.w3.org/XML/1998/namespace}base'
MAX_ENTRIES = 5


def public_link(value, base):
    url = network.canonical(urljoin(base, value.strip()))
    try:
        address = ipaddress.ip_address(urlsplit(url).hostname)
    except ValueError:
        return url
    if not network.public_ip(str(address)):
        raise ToolError('tool_address_denied')
    return url


def parse(result):
    if result.get('kind') not in {'application/rss+xml', 'application/atom+xml', 'application/xml', 'text/xml', 'text/plain'}:
        raise ToolError('feed_format_denied')
    raw = result.get('data')
    if not isinstance(raw, bytes) or len(raw) > network.MAX_BODY or result.get('download_truncated'):
        raise ToolError('tool_response_too_large')
    try:
        source = raw.decode('utf-8-sig')
    except UnicodeError:
        raise ToolError('feed_encoding_denied') from None
    declaration = re.match(r'\s*<\?xml\b[^?]*encoding=[\"\']([^\"\']+)', source, re.I)
    if declaration and declaration[1].lower() not in {'utf-8', 'utf8', 'us-ascii', 'ascii'}:
        raise ToolError('feed_encoding_denied')
    # Nie pozwalamy parserowi rozwijać encji ani odwołań do zewnętrznych zasobów.
    if re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b', source, re.I):
        raise ToolError('feed_xml_denied')
    try:
        root = ET.fromstring(source)
    except (ET.ParseError, ValueError):
        raise ToolError('feed_format_denied') from None
    base_url = network.canonical(result['url'])
    bases = {}
    stack = [(root, 0, base_url)]
    while stack:
        node, depth, base = stack.pop()
        if depth > 20 or len(bases) >= 5000:
            raise ToolError('feed_xml_limit')
        base = urljoin(base, node.get(XML_BASE, ''))
        if len(base) > 2048:
            raise ToolError('feed_xml_limit')
        bases[id(node)] = base
        stack.extend((child, depth + 1, base) for child in node)

    def plain(node):
        if node is None:
            return ''
        def collect(element):
            if element.tag.rsplit('}', 1)[-1].lower() in network.Text.HIDDEN:
                return ''
            return (element.text or '') + ''.join(collect(child) + (child.tail or '') for child in element)
        parser = network.Text()
        try:
            parser.feed(collect(node))
            value, _ = parser.result()
        except ToolError:
            raise ToolError('feed_format_denied') from None
        return re.sub(r'\s+', ' ', value).strip()

    if root.tag == 'rss' and root.get('version') == '2.0':
        channel = root.find('channel')
        if channel is None:
            raise ToolError('feed_format_denied')
        prefix = ''
        entries = channel.findall('item')
        feed_title = plain(channel.find('title'))
        kind = 'rss2'
    elif root.tag == ATOM + 'feed':
        channel = root
        prefix = ATOM
        entries = root.findall(ATOM + 'entry')
        feed_title = plain(root.find(ATOM + 'title'))
        kind = 'atom1'
    else:
        raise ToolError('feed_format_denied')
    if not feed_title:
        raise ToolError('feed_format_denied')
    items = []
    omitted = scanned = 0
    partial = len(feed_title) > 200
    seen = set()
    for entry in entries[:20]:
        scanned += 1
        title = plain(entry.find(prefix + 'title'))
        date = plain(entry.find(prefix + ('published' if prefix else 'pubDate')))
        if prefix and not date:
            date = plain(entry.find(prefix + 'updated'))
        summary_node = entry.find(prefix + ('summary' if prefix else 'description'))
        if summary_node is None and prefix:
            summary_node = entry.find(prefix + 'content')
        summary = plain(summary_node)
        links = entry.findall(prefix + 'link')
        link = next((link for link in links if not prefix or link.get('rel', 'alternate') == 'alternate'), None)
        target = (link.get('href', '') if prefix else link.text or '') if link is not None else ''
        try:
            if not title or not target:
                raise ToolError('feed_entry_invalid')
            url = public_link(target, bases[id(link)])
            if url in seen:
                raise ToolError('feed_entry_invalid')
        except ToolError:
            omitted += 1
            continue
        seen.add(url)
        partial |= len(title) > 200 or len(date) > 80 or len(summary) > 300
        items.append({'title': title[:200], 'url': url, 'date': date[:80], 'excerpt': summary[:300]})
        if len(items) == MAX_ENTRIES:
            break
    partial |= bool(omitted) or scanned < len(entries)
    lines = [feed_title[:200], 'Wpisy w kolejności kanału (nie pełne artykuły):']
    for i, item in enumerate(items, 1):
        lines.extend([str(i) + '. ' + item['title'], item['url'], item['date'], item['excerpt']])
    value = '\n'.join(lines)
    partial |= len(value) > 12000
    return {'url': base_url, 'title': feed_title[:200], 'content_kind': 'syndication_feed',
            'format': kind, 'items': items, 'text': value[:12000], 'excerpt': value[:1200],
            'count': len(items), 'scanned_entries': scanned, 'provided_entries': len(entries),
            'omitted_entries': omitted, 'truncated': bool(partial),
            'scope_note': 'Do 5 wpisów z bieżącego kanału, opis do 300 znaków. To metadane i zajawki, nie odczyt artykułów ani całe archiwum. Kolejność kanału bez gwarancji chronologii.'}


def execute(name, arguments, scope):
    if name != 'feed_read':
        raise ToolError('tool_not_allowed')
    if not scope.get('web'):
        raise ToolError('tool_permission_denied')
    if not isinstance(arguments, dict) or set(arguments) != {'url'}:
        raise ToolError('tool_arguments_invalid')
    url = network.canonical(arguments['url'])
    if url not in scope.get('urls', []):
        raise ToolError('tool_resource_not_authorized')
    return parse(network.fetch(url))
