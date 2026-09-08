"""Normalize known church page URLs in the private site copy. Never contact production.

Defaults to a dry run; use --write after visual edits finish. Asset URLs, unknown
routes, external destinations, query strings, fragments and provider URLs stay intact.
"""
import argparse
import html
import json
import posixpath
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

BASE = Path(__file__).resolve().parents[1]
CONFIG = json.loads((BASE / 'routes.json').read_text(encoding='utf-8'))
ORIGIN = CONFIG['origin']
ROUTES = set(CONFIG['routes'])
KNOWN = {route.rstrip('/') or '/': route for route in ROUTES}
HOSTS = {'newlifehutto.com', 'www.newlifehutto.com'}


def normalized(value, current_route, only_absolute=False):
    if not value or value.startswith(('#', '?')):
        return value
    parts = urlsplit(value)
    if parts.scheme and parts.scheme not in ('http', 'https'):
        return value
    if parts.netloc and (parts.hostname or '').lower() not in HOSTS:
        return value
    absolute = bool(parts.netloc)
    if only_absolute and not absolute:
        return value
    resolved = urlsplit(urljoin(ORIGIN + current_route, value))
    key = posixpath.normpath(resolved.path).rstrip('/') or '/'
    if key.endswith('/index.html'):
        key = key[:-11].rstrip('/') or '/'
    elif key == '/index.html':
        key = '/'
    if key not in KNOWN:
        return value
    new_path = KNOWN[key]
    if absolute:
        return urlunsplit(('https', 'newlifehutto.com', new_path, parts.query, parts.fragment))
    return urlunsplit(('', '', new_path, parts.query, parts.fragment))


def normalize_html(raw, route):
    # Attribute matching retains each original quote and all surrounding formatting.
    attribute = re.compile(r'(\b(?:href|src|content)\s*=\s*)([\"\'])(.*?)\2', re.I | re.S)
    raw = attribute.sub(lambda m: m[1] + m[2] + normalized(m[3], route) + m[2], raw)
    # Structured-data URLs and plain absolute own-site URLs. Assets do not match
    # a known page path and therefore remain byte-for-byte unchanged.
    own_url = re.compile(r'https?://(?:www\.)?newlifehutto\.com[^\s\"\'<>\\]*', re.I)
    raw = own_url.sub(lambda m: normalized(m[0], route, only_absolute=True), raw)
    # Restore already-public email destinations from Cloudflare's XOR encoding.
    # This removes the preview's dependency on a production-only decode endpoint.
    def decode(encoded):
        try:
            data = bytes.fromhex(encoded)
            decoded = bytes(value ^ data[0] for value in data[1:]).decode('utf-8')
            if not re.fullmatch(r'[A-Za-z0-9.!#$%&*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', decoded):
                raise ValueError('not an email address')
            return decoded
        except (ValueError, IndexError, UnicodeError) as error:
            raise ValueError(f'Invalid public email encoding on {route}: {error}') from error
    raw = re.sub(r'(href\s*=\s*)([\"\'])/cdn-cgi/l/email-protection#([a-f0-9]+)\2',
                 lambda m: m[1] + m[2] + 'mailto:' + html.escape(decode(m[3]), quote=True) + m[2], raw, flags=re.I)
    raw = re.sub(r'<span\b[^>]*\bdata-cfemail\s*=\s*[\"\']([a-f0-9]+)[\"\'][^>]*>.*?</span>',
                 lambda m: html.escape(decode(m[1])), raw, flags=re.I | re.S)
    raw = re.sub(r'<script\b[^>]*\bsrc\s*=\s*[\"\']/cdn-cgi/[^\"\']*email-decode\.min\.js[\"\'][^>]*>\s*</script>', '', raw, flags=re.I)
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    changed = []
    for route in CONFIG['routes']:
        page = BASE / 'site' / route.lstrip('/') / 'index.html'
        if not page.is_file():
            raise SystemExit(f'Missing expected page: {page}')
        old = page.read_text(encoding='utf-8-sig')
        new = normalize_html(old, route)
        if new != old:
            changed.append(str(page.relative_to(BASE)))
            if args.write:
                page.write_text(new, encoding='utf-8', newline='\n')
    sitemap = BASE / 'site' / 'sitemap.xml'
    old = sitemap.read_text(encoding='utf-8-sig')
    new = re.sub(r'(<loc>)(.*?)(</loc>)', lambda m: m[1] + normalized(m[2], '/') + m[3], old)
    if new != old:
        changed.append('site/sitemap.xml')
        if args.write:
            sitemap.write_text(new, encoding='utf-8', newline='\n')
    print(json.dumps({'mode': 'write' if args.write else 'dry-run', 'changed': changed}, indent=2))


if __name__ == '__main__':
    main()
