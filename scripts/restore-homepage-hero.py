"""Preserve the user-selected live landing design in the private homepage."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def revise(text):
    hero = (ROOT / 'templates/homepage-hero.html').read_text(encoding='utf-8').strip()
    revised, count = re.subn(r'<section class="(?:welcome-section|hero live-hero)">.*?</section>', lambda _: hero, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Expected exactly one homepage landing section')
    return revised

if __name__ == '__main__':
    path = ROOT / 'site/index.html'
    before = path.read_text(encoding='utf-8')
    after = revise(before)
    if after != before:
        path.write_text(after, encoding='utf-8')
    print('Live homepage landing section retained.')
