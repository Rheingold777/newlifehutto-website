"""Apply Bernhard's September 8 baptism-photo selection without rebuilding pages."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def revise(text):
    section = (ROOT / 'templates/homepage-baptism.html').read_text(encoding='utf-8').strip()
    result, count = re.subn(r'<section class="story-section(?: baptism-section)? section-space"[^>]*>.*?</section>', lambda _: section, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Expected one homepage story section')
    return result

if __name__ == '__main__':
    path = ROOT / 'site/index.html'
    path.write_text(revise(path.read_text(encoding='utf-8')), encoding='utf-8')
