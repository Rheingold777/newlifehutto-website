"""Apply Bernhard's exact September 7 website location wording."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ADDRESS = '623 W Front St, Suite 1800, Hutto, TX 78634'
MAP_ADDRESS = '623+W+Front+St%2C+Suite+1800%2C+Hutto%2C+TX+78634'

def wording(text):
    text = re.sub(r'623\+(?:West|W)\+Front\+(?:Street|St)(?:(?:%2C)?\+Suite\+1800)?(?:%2C)?\+Hutto(?:%2C)?\+TX\+78634', MAP_ADDRESS, text, flags=re.I)
    text = re.sub(r'623\s+(?:West|W)\s+Front\s+(?:Street|St)\b(?:\s*(?:,\s*|<br\s*/?>\s*)?Suite\s*1800)?(?:\s*(?:,\s*|<br\s*/?>\s*)Hutto,?\s+TX(?:\s+78634)?)?', ADDRESS, text)
    text = text.replace('Look for our sign at Suite 1800.', 'Look for the New Life Hutto sign at Suite 1800.')
    text = text.replace('Look for the New Life Hutto sign.', 'Look for the New Life Hutto sign at Suite 1800.')
    text = text.replace('Find Suite 1800 and come through the door.', 'Look for the New Life Hutto sign at Suite 1800 and come through the door.')
    text = text.replace('Look for the New Life Hutto sign and come through the door.', 'Look for the New Life Hutto sign at Suite 1800 and come through the door.')
    text = text.replace('<dd>Suite 1800</dd>', '<dd>' + ADDRESS + '</dd>')
    text = text.replace('Downtown Hutto, near the water tower', 'Suite 1800 — look for the New Life Hutto sign')
    text = text.replace("We're in downtown Hutto, right off Front Street near the Hutto water tower.", 'Look for Suite 1800 and the New Life Hutto sign.')
    text = text.replace(', right in downtown Hutto near the water tower.', '. Look for Suite 1800 and the New Life Hutto sign.')
    text = text.replace(' in historic downtown Hutto, right off Front Street.', '. Look for Suite 1800 and the New Life Hutto sign.')
    parking = 'Free parking is available in front of the building at ' + ADDRESS + '. Look for the New Life Hutto sign at Suite 1800.'
    text = text.replace('Free parking is available directly in front of the building at ' + ADDRESS + ', and along Front Street in downtown Hutto.', parking)
    text = text.replace('Free parking is right in front of the building at ' + ADDRESS + ", and along Front Street. It's downtown Hutto — parking is never a problem. If you see the Hutto water tower, you're close.", parking)
    text = text.replace(', in historic downtown Hutto.', '.').replace(', in downtown Hutto.', '.')
    text = text.replace('</strong> in downtown Hutto.', '</strong>.')
    text = text.replace('right in the heart of downtown Hutto', 'in Hutto')
    text = text.replace('in the heart of downtown Hutto', 'in Hutto')
    text = text.replace('in historic downtown Hutto', 'in Hutto').replace('in downtown Hutto', 'in Hutto')
    return text.replace('on West Front Street.', 'on W Front St.')

def schema_value(value):
    if isinstance(value, dict):
        result = {key: schema_value(item) for key, item in value.items()}
        if 'streetAddress' in value and str(value['streetAddress']).startswith('623 '):
            result.update(streetAddress='623 W Front St, Suite 1800', addressLocality='Hutto', addressRegion='TX', postalCode='78634')
        return result
    if isinstance(value, list):
        return [schema_value(item) for item in value]
    return wording(value) if isinstance(value, str) else value

def revise(text):
    pattern = r'(<script\b[^>]*type=["\x27]application/ld\+json["\x27][^>]*>.*?</script>)'
    parts = re.split(pattern, text, flags=re.S | re.I)
    for index, part in enumerate(parts):
        if index % 2:
            match = re.fullmatch(r'(<script\b[^>]*>)(.*?)(</script>)', part, flags=re.S | re.I)
            data = schema_value(json.loads(match.group(2)))
            parts[index] = match.group(1) + '\n' + json.dumps(data, indent=2, ensure_ascii=False) + '\n' + match.group(3)
        else:
            parts[index] = wording(part)
    return ''.join(parts)

if __name__ == '__main__':
    for path in (ROOT / 'site').rglob('*.html'):
        before = path.read_text(encoding='utf-8')
        after = revise(before)
        if before != after:
            path.write_text(after, encoding='utf-8')
            print(path.relative_to(ROOT))
