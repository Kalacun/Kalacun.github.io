"""Portrait slot for the selected academic homepage and local editing."""
from html import escape


def portrait(profile, draft, prefix=''):
    src = profile.get('photo', '')
    if not src and not draft:
        return ''
    if src and not src.startswith(('https://', 'http://')):
        src = prefix + src
    alt = profile.get('photo_alt') or 'Portrait of ' + profile['name']
    image = f'<img data-profile-photo src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}" width="176" height="208">' if src else f'<img data-profile-photo alt="{escape(alt, quote=True)}" width="176" height="208" hidden>'
    fallback = f'<div class="photo-fallback"{ " hidden" if src else ""}><span aria-hidden="true">{escape(profile["initials"])}</span><small>Your portrait here</small></div>'
    controls = '''<label class="photo-picker">Preview your photo<input type="file" data-photo-input accept="image/jpeg,image/png,image/webp"></label><p class="photo-status" data-photo-status aria-live="polite">Local preview · nothing is uploaded.</p>''' if draft else ''
    return f'<div class="photo-widget"><div class="photo-frame">{image}{fallback}</div>{controls}</div>'
