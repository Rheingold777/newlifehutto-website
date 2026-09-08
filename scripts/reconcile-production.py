"""Reconcile the private design with the verified September 8 production v4.

This helper is intentionally offline and does not write files on import or run.
Call revise(html_text, relative_path) after prior design/location helpers. The
frozen public content and verification provenance live in config/production-v4-baseline.json.
It does not replace the preview header, footer, contact path, or hero design.
"""
from pathlib import Path
import html
import json
import re
from urllib.parse import unquote_plus, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/production-v4-baseline.json').read_text(encoding='utf-8'))


def official_address(text):
    """Use the building address; preserve separate Suite 1800 arrival guidance."""
    return re.sub(
        r'\b623\s+(?:West|W)\s+Front\s+(?:Street|St)\s*,?\s*(?:<br\s*/?>\s*)?Suite\s+1800\b',
        CONFIG['street_address'], text, flags=re.I,
    )


def _schema(value):
    if isinstance(value, dict):
        updated = {key: _schema(item) for key, item in value.items()}
        if str(value.get('streetAddress', '')).startswith('623 '):
            updated.update(streetAddress=CONFIG['street_address'], addressLocality='Hutto',
                           addressRegion='TX', postalCode='78634')
        # Only repair existing GeoCoordinates; the preview deliberately removed
        # unverified objects earlier, so do not add coordinates where none exist.
        types = value.get('@type', [])
        if isinstance(types, str):
            types = [types]
        if 'GeoCoordinates' in types and 'latitude' in value and 'longitude' in value:
            updated.update(CONFIG['geo'])
        return updated
    if isinstance(value, list):
        return [_schema(item) for item in value]
    return official_address(value) if isinstance(value, str) else value


def _map_tag(match):
    tag = match.group(0)
    attr = 'href' if match.group('tag').lower() == 'a' else 'src'
    pattern = re.compile(r'\b' + attr + r'\s*=\s*(["\x27])(.*?)\1', re.S | re.I)
    current = pattern.search(tag)
    if not current:
        return tag
    url = html.unescape(current.group(2))
    parsed = urlsplit(url)
    if parsed.hostname not in {'maps.google.com', 'www.google.com', 'google.com'}:
        return tag
    decoded = unquote_plus(url).lower()
    if not any(marker in decoded for marker in (
        '623 w front st', '623 west front street',
        '0x8644dba769c3acab:0x7ae230f7237dd6d8',
    )):
        # Google review/business links are distinct from the approved building.
        return tag
    key = 'building_directions_url' if attr == 'href' else 'building_embed_url'
    new_attribute = attr + '="' + html.escape(CONFIG[key], quote=True) + '"'
    return tag[:current.start()] + new_attribute + tag[current.end():]


def _giving(text):
    start = re.search(r'<section\s+class="page-header\b[^\"]*">', text, re.I)
    footer = re.search(r'<footer\b[^>]*class="site-footer"', text, re.I)
    if not start or not footer or start.start() >= footer.start():
        raise ValueError('Expected preview Giving page header and shared footer')
    text = text[:start.start()] + CONFIG['giving_main_html'] + '\n\n    ' + text[footer.start():]
    text, count = re.subn(
        r'(<meta\s+name="description"\s+content=")[^\"]*(")',
        lambda m: m.group(1) + html.escape(CONFIG['giving_description'], quote=True) + m.group(2),
        text, count=1, flags=re.I,
    )
    if count != 1:
        raise ValueError('Expected one Giving meta description')
    return text


def _announcement(text):
    new = CONFIG['homepage_announcement_html']
    previous = re.compile(r'<section\s+class="giving-announcement"[^>]*>.*?</section>', re.S)
    if previous.search(text):
        return previous.sub(lambda _: new, text, count=1)
    anchor = re.search(r'<section\s+class="welcome-note"[^>]*>.*?</section>', text, re.S)
    if not anchor:
        raise ValueError('Expected homepage welcome-note anchor for giving announcement')
    return text[:anchor.end()] + '\n' + new + text[anchor.end():]


def revise(text, relative_path):
    """Return reconciled HTML; relative_path is e.g. 'index.html' or 'give/index.html'."""
    relative_path = str(relative_path).replace('\\', '/').lstrip('/')
    if relative_path.startswith('site/'):
        relative_path = relative_path[5:]
    if relative_path == 'give/index.html':
        text = _giving(text)
    if relative_path == 'index.html':
        text = _announcement(text)
    parts = re.split(
        r'(<script\b[^>]*type=["\x27]application/ld\+json["\x27][^>]*>.*?</script>)',
        text, flags=re.S | re.I,
    )
    for index, part in enumerate(parts):
        if index % 2:
            match = re.fullmatch(r'(<script\b[^>]*>)(.*?)(</script>)', part, flags=re.S | re.I)
            data = _schema(json.loads(match.group(2)))
            parts[index] = match.group(1) + '\n' + json.dumps(data, indent=2, ensure_ascii=False) + '\n' + match.group(3)
        else:
            parts[index] = official_address(part)
    text = ''.join(parts)
    return re.sub(r'<(?P<tag>a|iframe)\b[^>]*>', _map_tag, text, flags=re.I | re.S)


if __name__ == '__main__':
    raise SystemExit('Offline helper only: import revise(text, relative_path); no files were written.')
