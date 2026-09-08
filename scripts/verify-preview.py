"""Bounded read-only acceptance checks against the loopback preview only."""
import datetime
import http.client
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

BASE = Path(__file__).resolve().parents[1]
CONFIG = json.loads((BASE / 'routes.json').read_text(encoding='utf-8'))
ORIGIN = CONFIG['origin']
EXPECTED = set(CONFIG['routes'])
LOCAL = 'http://127.0.0.1:8770'
checks = []


def check(name, condition, detail=None):
    checks.append({'check': name, 'passed': bool(condition), 'detail': detail})


def fetch(target, method='GET'):
    connection = http.client.HTTPConnection('127.0.0.1', 8770, timeout=15)
    connection.request(method, target)
    response = connection.getresponse()
    result = (response.status, dict((k.lower(), v) for k, v in response.getheaders()), response.read())
    connection.close()
    return result


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.og = []
        self.descriptions = []
        self.h1 = 0
        self.title = ''
        self.is_title = False
        self.links = []
        self.assets = []
        self.schemas = []
        self.schema_buffer = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link':
            if attrs.get('rel') == 'canonical': self.canonicals.append(attrs.get('href'))
            if attrs.get('rel') in ('stylesheet', 'icon', 'apple-touch-icon'): self.assets.append(attrs.get('href', ''))
        if tag == 'meta':
            if attrs.get('property') == 'og:url': self.og.append(attrs.get('content'))
            if attrs.get('name') == 'description': self.descriptions.append(attrs.get('content'))
        if tag == 'h1': self.h1 += 1
        if tag == 'title': self.is_title = True
        if tag == 'a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag in ('img', 'script', 'source', 'video'):
            if attrs.get('src'): self.assets.append(attrs['src'])
            if attrs.get('poster'): self.assets.append(attrs['poster'])
        if tag == 'script' and attrs.get('type') == 'application/ld+json': self.schema_buffer = ''

    def handle_data(self, data):
        if self.is_title: self.title += data
        if self.schema_buffer is not None: self.schema_buffer += data

    def handle_endtag(self, tag):
        if tag == 'title': self.is_title = False
        if tag == 'script' and self.schema_buffer is not None:
            self.schemas.append(json.loads(self.schema_buffer))
            self.schema_buffer = None


def internal_url(value, route):
    parsed = urlsplit(urljoin(LOCAL + route, value))
    if parsed.hostname not in ('127.0.0.1', 'newlifehutto.com', 'www.newlifehutto.com'): return None
    return parsed.path + (('?' + parsed.query) if parsed.query else '')


def schema_strings(value):
    if isinstance(value, str): yield value
    elif isinstance(value, dict):
        for item in value.values(): yield from schema_strings(item)
    elif isinstance(value, list):
        for item in value: yield from schema_strings(item)


pages = {}
assets = set()
for route in CONFIG['routes']:
    status, headers, body = fetch(route)
    check(f'{route} direct HTTP 200', status == 200, status)
    check(f'{route} preview indexing blocked', 'noindex' in headers.get('x-robots-tag', ''))
    text = body.decode('utf-8')
    check(f'{route} analytics removed from response', not re.search(r'googletagmanager\.com|google-analytics\.com|\bgtag\s*\(|\bdataLayer\b', text))
    page = Page()
    try:
        page.feed(text)
        check(f'{route} JSON-LD parses', bool(page.schemas), len(page.schemas))
    except json.JSONDecodeError as error:
        check(f'{route} JSON-LD parses', False, str(error))
    pages[route] = page
    check(f'{route} one self-canonical', page.canonicals == [ORIGIN + route], page.canonicals)
    check(f'{route} matching Open Graph URL', page.og == [ORIGIN + route], page.og)
    check(f'{route} title, description, single H1', bool(page.title.strip()) and len(page.descriptions) == 1 and bool(page.descriptions[0]) and page.h1 == 1)
    bad_schema_urls = []
    for value in schema_strings(page.schemas):
        parsed = urlsplit(value)
        if parsed.hostname in ('newlifehutto.com', 'www.newlifehutto.com'):
            candidate = (parsed.path.rstrip('/') + '/') if parsed.path else '/'
            if candidate in EXPECTED and (parsed.scheme != 'https' or parsed.hostname != 'newlifehutto.com' or parsed.path != candidate): bad_schema_urls.append(value)
    check(f'{route} schema page URLs normalized', not bad_schema_urls, bad_schema_urls)
    for asset in page.assets:
        local = internal_url(asset, route)
        if local: assets.add(local)
    status_head, head_headers, head_body = fetch(route, 'HEAD')
    check(f'{route} HEAD has no body and correct length', status_head == 200 and not head_body and head_headers.get('content-length') == str(len(body)))
    variants = ['/index.html'] if route == '/' else [route.rstrip('/'), route + 'index.html']
    for variant in variants:
        target = variant + '?source=preview&value=one%20two'
        s, h, _ = fetch(target)
        check(f'{variant} single permanent redirect preserves query', s == 301 and h.get('location') == route + '?source=preview&value=one%20two', {'status': s, 'location': h.get('location')})

status, headers, body = fetch('/sitemap.xml')
check('Sitemap direct 200', status == 200)
locs = [node.text for node in ET.fromstring(body).findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
check('Sitemap exactly matches 14 canonical pages', len(locs) == 14 and set(locs) == {ORIGIN + route for route in EXPECTED}, locs)

link_failures = []
route_links = {}
for route, page in pages.items():
    route_links[route] = set()
    for link in page.links:
        local = internal_url(link, route)
        if not local: continue
        path = urlsplit(local).path
        if path in EXPECTED: route_links[route].add(path)
        status, _, _ = fetch(local)
        if status != 200: link_failures.append({'page': route, 'href': link, 'status': status})
check('Internal links point directly to working pages/assets', not link_failures, link_failures)
reached = set()
queue = ['/']
while queue:
    route = queue.pop()
    if route in reached: continue
    reached.add(route)
    queue.extend(route_links.get(route, set()) - reached)
check('Homepage crawl reaches all 14 intended pages', reached == EXPECTED, {'reached': sorted(reached), 'missing': sorted(EXPECTED - reached)})

asset_failures = []
pending = list(assets)
while pending:
    target = pending.pop()
    status, headers, body = fetch(target)
    if status != 200 or not body: asset_failures.append({'asset': target, 'status': status})
    if 'text/css' in headers.get('content-type', ''):
        for match in re.findall(r'url\(\s*[\"\']?([^\)\"\']+)[\"\']?\s*\)', body.decode('utf-8')):
            if match.startswith('data:'): continue
            local = internal_url(match, target)
            if local and local not in assets:
                assets.add(local)
                pending.append(local)
check('Referenced local assets resolve', not asset_failures, {'count': len(assets), 'failures': asset_failures})

for legacy, destination in CONFIG['legacyRedirects'].items():
    for variant in (legacy, legacy + '/'):
        status, headers, _ = fetch(variant + '?from=old')
        check(f'{variant} correct legacy successor', status == 301 and headers.get('location') == destination + '?from=old')
for missing in ['/missing-preview-20260907', '/kids', '/youth', '/upcoming-events', '/your-salvation-matters', '/es/', '/sermons/', '/blog/', '/assets/missing.jpg']:
    status, headers, body = fetch(missing)
    check(f'{missing} real helpful 404', status == 404 and b'/visit/' in body and 'noindex' in headers.get('x-robots-tag', ''))
status, _, body = fetch('/robots.txt')
check('Preview robots disallows all', status == 200 and body == b'User-agent: *\nDisallow: /\n')
status, _, _ = fetch('/', 'POST')
check('Preview rejects writes', status == 405)
for invalid in ['/../routes.json', '/%2e%2e/routes.json', '/assets/%2e%2e/%2e%2e/routes.json', '/assets\\..\\routes.json', '/.git/config']:
    status, _, _ = fetch(invalid)
    check(f'Path safety {invalid}', status == 400, status)

result = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'base_url': LOCAL, 'scope': 'Local preview only. Public host redirects, deployment, live indexing and provider submissions not tested.', 'passed': sum(item['passed'] for item in checks), 'failed': sum(not item['passed'] for item in checks), 'checks': checks}
(BASE / 'output').mkdir(exist_ok=True)
(BASE / 'output' / 'verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, indent=2))
for item in checks:
    if not item['passed']: print('FAIL:', item['check'], json.dumps(item['detail']))
sys.exit(1 if result['failed'] else 0)
