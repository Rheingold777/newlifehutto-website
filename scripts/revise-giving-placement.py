"""Apply the authorized local Giving placement revision without rebuilding pages."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NAV = '''<nav class="site-menu" id="site-menu" aria-label="Main navigation"><a href="/about/">About us</a><a href="/visit/">Your first visit</a><a href="/contact/">Contact</a><a href="/visit/" class="button button-navy nav-visit">Plan your visit <span aria-hidden="true">↗</span></a></nav>
<div class="header-actions"><a href="/give/" class="button header-give">Give</a><button class="menu-toggle" type="button" aria-label="Open navigation" aria-expanded="false" aria-controls="site-menu"><span></span><span></span></button></div>'''

GIVING_ACTION = '''<div class="give-opening-action"><a href="https://newlifehutto.breezechms.com/give/online" class="button button-gold" target="_blank" rel="noopener noreferrer">Give Online <span aria-hidden="true">↗</span></a><p class="giving-provider-note">Secure giving powered by Breeze ChMS</p><p class="giving-guest-note">If you're visiting for the first time, please know that you are absolutely not expected to give.</p></div>'''

def revise(text, giving=False):
    if 'class="header-actions"' not in text:
        text, count = re.subn(r'<button class="menu-toggle".*?</button>\s*<nav class="site-menu".*?</nav>', NAV, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Expected one shared header')
    if giving and 'class="give-opening-action"' not in text:
        text = text.replace('<section class="page-header">', '<section class="page-header give-page-header">', 1)
        anchor = '<p>Partner with us in reaching our community</p>'
        if anchor not in text:
            raise ValueError('Giving heading not found')
        text = text.replace(anchor, anchor + '\n            ' + GIVING_ACTION, 1)
    text = text.replace("Use our optional connection card to introduce yourself or share a question with the church. You're also welcome to simply come to a service.", "Use our optional connection card to introduce yourself. Have a question? <a class=\"connection-contact\" href=\"/contact/\">Contact the church</a>. You're also welcome to simply come to a service.")
    text = text.replace("Prefer to write it down? Our connection card goes straight to Pastor Bernhard. Let us know you're coming, ask a question, or share what's on your heart. We read and respond to every single one.", "Use our connection card to introduce yourself or let us know you're coming. For questions, please use the email or phone listed above.")
    # Bernhard is leaving Breeze; use the church's existing contact path meanwhile.
    text = text.replace("If you'd like to introduce yourself before you arrive, our optional connection card is below.", "If you'd like to introduce yourself before you arrive, you can email or call us.")
    text = text.replace("Use our optional connection card to introduce yourself. Have a question? <a class=\"connection-contact\" href=\"/contact/\">Contact the church</a>. You're also welcome to simply come to a service.", "Have a question or want to say hello before Sunday? We'd love to hear from you. You're also welcome to simply come to a service.")
    text = text.replace('<a class="button button-gold" href="https://newlifehutto.breezechms.com/form/letsconnect" target="_blank" rel="noopener noreferrer">Let us know you\'re coming ↗</a>', '<a class="button button-gold" href="/contact/#say-hello">Contact the church <span aria-hidden="true">→</span></a>')
    text = text.replace('Opens our connection card in a new tab.', 'Email or call us. No registration needed.')
    text = text.replace('<!-- Connection Form -->\n    <section class="section">', '<!-- Direct contact -->\n    <section class="section" id="say-hello">')
    text = text.replace('<h2>Fill Out a Connection Card</h2>', '<h2>Say Hello Before You Visit</h2>')
    text = text.replace("Use our connection card to introduce yourself or let us know you're coming. For questions, please use the email or phone listed above.", "Have a question, or want to let us know you're coming? Email or call us. We'd be glad to help you plan your visit.")
    text = text.replace('<a href="https://newlifehutto.breezechms.com/form/letsconnect" class="btn btn-primary" target="_blank" rel="noopener noreferrer" style="margin-top: var(--space-sm);">Connect With Us</a>', '<div class="button-row" style="justify-content: center; margin-top: var(--space-sm);"><a href="mailto:office@newlifehutto.com" class="btn btn-primary">Email the Church</a><a href="tel:+15128297402" class="btn btn-outline">Call (512) 829-7402</a></div>\n                <p style="margin-top: var(--space-sm);"><a href="mailto:office@newlifehutto.com">office@newlifehutto.com</a></p>')
    return text

if __name__ == '__main__':
    changed = []
    for path in (ROOT / 'site').rglob('*.html'):
        before = path.read_text(encoding='utf-8')
        after = revise(before, path == ROOT / 'site/give/index.html')
        if before != after:
            path.write_text(after, encoding='utf-8')
            changed.append(str(path.relative_to(ROOT)))
    print('\n'.join(changed) or 'Already applied')
