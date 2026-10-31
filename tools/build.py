#!/usr/bin/env python3
"""Build the academic homepage with Python's standard library. No dependencies."""
import argparse
import datetime
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from string import Template
from urllib.parse import unquote, urlsplit
from portraits import portrait

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {
    "published": ("Published", "published"),
    "accepted": ("Accepted · to appear", "published"),
    "submitted": ("Submitted · not yet accepted", "unpublished"),
    "preprint": ("Preprint · not peer reviewed", "unpublished"),
    "unpublished": ("Unpublished manuscript", "unpublished"),
    "in-progress": ("Work in progress", "ongoing"),
}
GROUPS = ("research", "projects", "education", "experience", "awards", "certificates", "languages", "earlier_research", "ultimate_frisbee", "misc")


def esc(value):
    return html.escape(str(value), quote=True)


def paragraphs(value):
    return ''.join(f'<p>{esc(part.strip())}</p>' for part in re.split(r'\n\s*\n', value) if part.strip())


def asset_path(url):
    """Return a local document path, or None for an external URL/fragment."""
    parts = urlsplit(url)
    if parts.scheme or parts.netloc or url.startswith("#"):
        return None
    path = (ROOT / unquote(parts.path)).resolve()
    if not path.is_relative_to(ROOT / "assets"):
        raise ValueError(f"Local links must point inside assets/: {url}")
    return path


def validate_url(url):
    if not url:
        return
    if url != url.strip() or "\\" in url or any(ord(c) < 32 for c in url):
        raise ValueError(f"Invalid link: {url!r}")
    parts = urlsplit(url)
    if parts.scheme:
        if parts.scheme not in ("https", "http") or not parts.netloc:
            raise ValueError(f"Use a complete HTTPS link or an assets/ path: {url}")
    elif parts.netloc:
        raise ValueError(f"Use https:// instead of a protocol-relative link: {url}")
    else:
        path = asset_path(url)
        if path and not path.is_file():
            raise ValueError(f"Document or image does not exist: {url}")


def records(data, key):
    return [item for item in data.get(key, []) if data["draft"] or not item.get("example", False)]


def link_list(items, draft, class_name="resource-links"):
    links = []
    for item in items:
        label, url = item["label"], item.get("url", "")
        if url:
            accessible = f' aria-label="{esc(item["aria_label"])}"' if item.get('aria_label') else ''
            links.append(f'<a href="{esc(url)}"{accessible}>{esc(label)} <span aria-hidden="true">↗</span></a>')
        elif draft:
            links.append(f'<span class="pending">{esc(label)} <span class="pending-note">to add</span></span>')
    return f'<div class="{class_name}">{"".join(links)}</div>' if links else ""


def detail(label, fields, title, opened=True):
    body = "".join(f'<div><h4>{esc(heading)}</h4>{paragraphs(value)}</div>' for heading, value in fields if value)
    return (f'<details{" open" if opened else ""}><summary>{label}<span class="sr-only"> for {esc(title)}</span></summary>'
            f'<div class="detail-body">{body}</div></details>') if body else ""


def publication_summary(item):
    fields = [('Abstract', item.get('abstract')), ('Research summary', item.get('research_summary')),
              ('Evaluation & limitations', item.get('evaluation')), ('Next steps', item.get('next'))]
    if not any(value for _, value in fields):
        fields = [('Research summary', item.get('summary'))]
    panel = detail('Summary (expand)', fields, item['title'], opened=False)
    return panel or (f'<details><summary>Summary (expand)<span class="sr-only"> for {esc(item["title"])}</span></summary>'
                     '<div class="detail-body"><p class="pending">Abstract to be added.</p></div></details>')


def research_entry(item, draft, name):
    status, category = STATUSES[item["status"]]
    authors = esc(item['authors']).replace(esc(name), f'<strong>{esc(name)}</strong>')
    example = ' <span class="example-label">example</span>' if item.get("example") else ""
    updated = f'<span>Updated {esc(item["updated"])}</span>' if item.get("updated") else ""
    return f'''<article class="research-entry" id="{esc(item['id'])}" data-category="{category}">
      <div class="entry-year">{esc(item['year'])}</div><div class="entry-content">
      <div class="status-line"><span class="status {category}">{esc(status)}</span>{example}</div>
      <h3>{esc(item['title'])}</h3><p class="metadata">{authors}</p>
      <p class="venue">{esc(item.get('venue', ''))}</p>{f'<p>{esc(item["summary"])}</p>' if item.get('summary') else ''}
      {f'<p class="contribution"><strong>My contribution.</strong> {esc(item["contribution"])}</p>' if item.get('contribution') else ''}
      {link_list(item.get('links', []), draft)}
      {publication_summary(item)}
      <div class="entry-updated">{updated}</div></div></article>'''


def project_entry(item, draft):
    metadata = ', '.join(esc(item.get(key, '')) for key in ('context', 'tools') if item.get(key))
    return f'''<article class="project-entry" id="{esc(item['id'])}">
      <div class="entry-heading"><h3>{esc(item['title'])}</h3><span class="entry-year">{esc(item['year'])}</span></div>
      <p class="metadata">{metadata}</p>
      {f'<p>{esc(item["summary"])}</p>' if item.get('summary') else ''}
      {f'<p class="contribution"><strong>My contribution.</strong> {esc(item["contribution"])}</p>' if item.get('contribution') else ''}
      {link_list(item.get('links', []), draft)}
      {detail('Project details', [('Further details', item.get('details'))], item['title'])}</article>'''


def compact_entry(item, draft, heading_level=3, publication=False):
    courses = item.get("courses", [])
    course_details = (f'<details open><summary>Selected coursework<span class="sr-only"> for {esc(item["title"])}</span></summary>'
                      '<ul class="course-list">' + "".join(f'<li>{esc(c)}</li>' for c in courses) + '</ul></details>') if courses else ""
    return f'''<article class="compact-entry"><div class="entry-heading"><h{heading_level}>{esc(item['title'])}</h{heading_level}>
      <span class="entry-year">{esc(item.get('dates', ''))}</span></div>
      <p class="metadata">{esc(item.get('organization', ''))}</p><p>{esc(item.get('description', ''))}</p>
      {course_details}{link_list(item.get('links', []), draft)}
      {publication_summary(item) if publication else ''}</article>'''


def section(section_id, title, content):
    if not content:
        return ''
    return f'<section id="{section_id}" aria-labelledby="{section_id}-title"><h2 id="{section_id}-title">{title}</h2>{content}</section>'


def profile_resources(profile):
    items = [{'label': label, 'url': profile.get(key, '')} for key, label in [
        ('cv', profile.get('cv_label', 'CV (PDF)')), ('github', 'GitHub'),
        ('codeberg', 'Codeberg'), ('scholar', 'Google Scholar'), ('orcid', 'ORCID')]
        if profile.get(key)]
    email = f'<a href="mailto:{esc(profile["email"])}">Email ↗</a>' if profile.get('email') else ''
    return '<div class="profile-links">' + email + link_list(items, False) + '</div>'


def build(data):
    draft, profile = data['draft'], data['profile']
    entries = []
    research = records(data, 'research')
    published = [item for item in research if item['status'] in ('published', 'accepted')]
    current = [item for item in research if item['status'] not in ('published', 'accepted')]
    for key, title, items in [('research', 'Published research', published), ('current-research', 'Current research', current)]:
        if items:
            entries.append((key, title, ''.join(research_entry(item, draft, profile['name']) for item in items)))
    for key, title in [('experience', 'Research experience'), ('education', 'Education')]:
        items = records(data, key)
        if items:
            entries.append((key, title, ''.join(compact_entry(item, draft) for item in items)))
    earlier = ''.join(compact_entry(item, draft, publication=True) for item in records(data, 'earlier_research'))
    if earlier:
        entries.append(('earlier-research', 'Earlier research', '<details open><summary>Research before university</summary>' + earlier + '</details>'))
    projects = records(data, 'projects')
    if projects:
        content = ''.join(project_entry(item, draft) for item in projects if item.get('featured', True))
        more = [item for item in projects if not item.get('featured', True)]
        if more:
            content += f'<details class="more-entries"><summary>More projects ({len(more)})</summary>' + ''.join(project_entry(item, draft) for item in more) + '</details>'
        entries.append(('projects', 'Other projects', content))
    for key, title in [('awards', 'Honors and awards'), ('certificates', 'Courses and certificates')]:
        items = records(data, key)
        if items:
            content = ''.join(compact_entry(item, draft) for item in items)
            if key == 'certificates':
                content = f'<details class="certificate-list"><summary>View all certificates ({len(items)})</summary>{content}</details>'
            entries.append((key, title, content))
    other = ''
    for key, title in [('languages', 'Languages'), ('ultimate_frisbee', 'Ultimate frisbee')]:
        items = records(data, key)
        if items:
            group_id = key.replace('_', '-')
            group_content = ''.join(compact_entry(item, draft, heading_level=4) for item in items)
            if key == 'languages':
                group_content = f'<div class="language-list">{group_content}</div>'
            other += (f'<div class="misc-group" id="{group_id}" aria-labelledby="{group_id}-title">'
                      f'<h3 id="{group_id}-title">{title}</h3>'
                      + group_content + '</div>')
    other += ''.join(compact_entry(item, draft) for item in records(data, 'misc'))
    if other:
        entries.append(('misc', 'Other', other))
    nav_titles = {'research': 'Published research', 'current-research': 'Current research',
        'experience': 'Research experience', 'education': 'Education', 'earlier-research': 'Earlier research',
        'projects': 'Other projects', 'certificates': 'Certificates', 'misc': 'Other'}
    nav = '<a href="#overview">Overview</a>'
    nav += ''.join(f'<a href="#{key}">{nav_titles[key]}</a>' for key, _, _ in entries if key in nav_titles)
    nav += '<a href="#contact">Contact & CV</a>'
    glance = []
    if research:
        counts = []
        if published:
            counts.append(f'{len(published)} published ' + ('paper' if len(published) == 1 else 'papers'))
        if current:
            counts.append(f'{len(current)} submitted or ongoing ' + ('manuscript' if len(current) == 1 else 'manuscripts'))
        research_anchor = 'research' if published else 'current-research'
        glance.append(f'<div><dt><a href="#{research_anchor}">Research</a></dt><dd>{" · ".join(counts)}</dd></div>')
    if records(data, 'education'):
        glance.append(f'<div><dt><a href="#education">Education</a></dt><dd>{esc(records(data, "education")[0]["title"])}</dd></div>')
    if projects:
        glance.append('<div><dt><a href="#projects">Applied work</a></dt><dd>' + ' · '.join(esc(item['title']) for item in projects if item.get('featured', True)) + '</dd></div>')
    glance_html = '<h2 class="overview-title">At a glance</h2><dl class="overview-list">' + ''.join(glance) + '</dl>' if glance and profile.get('show_glance', True) else ''
    interest_html = '<h2 class="overview-title">Research interests</h2><p class="interests">' + ' / '.join(esc(item) for item in profile.get('interests', [])) + '</p>' if profile.get('interests') else ''
    resources = profile_resources(profile)
    contact = f'<p><a href="mailto:{esc(profile["email"])}">{esc(profile["email"])}</a></p>' if profile.get('email') else ''
    entries.append(('contact', 'Contact & CV', contact + resources))
    tokens = dict(name=esc(profile['name']),
        description=esc('Research, publications, projects, and academic background of ' + profile['name'] + '.'),
        robots='<meta name="robots" content="noindex, nofollow">' if draft else '',
        canonical=f'<link rel="canonical" href="https://{esc(profile["domain"])}/">' if profile.get('domain') else '',
        portrait=portrait(profile, draft), nav=nav, resources=resources,
        bio=''.join(f'<p class="bio">{esc(item)}</p>' for item in profile['bio']),
        interests=interest_html, glance=glance_html,
        sections='\n'.join(section(key, title, content) for key, title, content in entries),
        updated=datetime.date.fromisoformat(profile['updated']).strftime('%B %Y'))
    rendered = Template((ROOT / 'tools/home.html').read_text()).substitute(tokens)
    return '\n'.join(line.rstrip() for line in rendered.splitlines()) + '\n'


def validate_entries(data):
    """Report content-editing mistakes with their JSON location before rendering."""
    for group in GROUPS:
        items = data.get(group, [])
        if not isinstance(items, list):
            raise ValueError(f'{group} must be a list of entries.')
        for index, item in enumerate(items):
            location = f'{group}[{index}]'
            if not isinstance(item, dict):
                raise ValueError(f'{location} must be an entry object.')
            if 'label' in item and 'url' in item and 'title' not in item:
                raise ValueError(
                    f'{location} is a document link, not a complete entry. '
                    'Move this {label, url} object into the existing publication or project\'s "links" list.')
            required = ('id', 'title', 'authors', 'year', 'status') if group == 'research' else (
                ('id', 'title', 'year') if group == 'projects' else ('title',))
            for key in required:
                if key not in item:
                    raise ValueError(f'{location} is missing required field "{key}". Copy a complete entry from the same section.')
                if not isinstance(item[key], str):
                    raise ValueError(f'{location}.{key} must be text.')
            links = item.get('links', [])
            if not isinstance(links, list):
                raise ValueError(f'{location}.links must be a list of {{label, url}} objects.')
            for link_index, link in enumerate(links):
                link_location = f'{location}.links[{link_index}]'
                if not isinstance(link, dict) or not isinstance(link.get('label'), str):
                    raise ValueError(f'{link_location} must be an object with a text "label" and "url".')
                if not isinstance(link.get('url', ''), str):
                    raise ValueError(f'{link_location}.url must be text.')


def validate(data, publish):
    if type(data.get('draft')) is not bool:
        raise ValueError('draft must be true or false.')
    if publish and data['draft']:
        raise ValueError('This is still a draft. Fill in content.json, remove examples, then set draft to false before publishing.')
    validate_entries(data)
    profile = data['profile']
    domain = profile.get('domain', '')
    if domain and (len(domain) > 253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', domain)):
        raise ValueError('profile.domain must be a lowercase domain such as example.com, without https:// or a path.')
    if publish and profile.get('cv_is_draft'):
        raise ValueError('Replace the draft CV, then set profile.cv_is_draft to false.')
    for key in ('name', 'initials', 'bio', 'updated'):
        if not profile.get(key):
            raise ValueError(f'profile.{key} is required.')
    datetime.date.fromisoformat(profile['updated'])
    ids = {'overview', 'research', 'current-research', 'experience', 'education', 'earlier-research', 'projects', 'awards', 'certificates', 'languages', 'ultimate-frisbee', 'languages-title', 'ultimate-frisbee-title', 'misc', 'contact', 'main-content', 'page-title'}
    urls = [profile.get(key, '') for key in ('cv', 'github', 'codeberg', 'scholar', 'orcid', 'photo')]
    if profile.get('email') and not re.fullmatch(r'[^\s@?<>]+@[^\s@?<>]+\.[^\s@?<>]+', profile['email']):
        raise ValueError('profile.email should contain an email address only.')
    for group in GROUPS:
        for item in data.get(group, []):
            for flag in ('example', 'featured'):
                if flag in item and type(item[flag]) is not bool:
                    raise ValueError(f'{flag} must be true or false.')
        for item in records(data, group):
            if group == 'research' and item['status'] not in STATUSES:
                raise ValueError(f'Unknown research status: {item["status"]}')
            if group in ('research', 'projects'):
                entry_id = item['id']
                if not re.fullmatch(r'[a-z][a-z0-9-]*', entry_id) or entry_id in ids:
                    raise ValueError(f'Use a unique lowercase, hyphenated id: {entry_id}')
                ids.add(entry_id)
            urls.extend(link.get('url', '') for link in item.get('links', []))
    for url in urls:
        validate_url(url)
    if not data['draft']:
        public_data = {'profile': profile, **{key: records(data, key) for key in GROUPS}}
        content = json.dumps(public_data, ensure_ascii=False)
        if re.search(r'\[[^\[\]]+\]|Your Name|your-username|you@example\.com', content):
            # Check string values separately so JSON array brackets do not count.
            def placeholder(value):
                if isinstance(value, str):
                    return bool(re.search(r'\[[^\[\]]+\]|Your Name|your-username|you@example\.com', value))
                if isinstance(value, list):
                    return any(placeholder(v) for v in value)
                if isinstance(value, dict):
                    return any(placeholder(v) for v in value.values())
                return False
            if placeholder(public_data):
                raise ValueError('Visible placeholder text remains. Replace bracketed prompts or remove their entries.')
    return [asset_path(url) for url in urls if url and asset_path(url)]


class LinkCheck(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.fragments = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if attrs.get('href', '').startswith('#'):
            self.fragments.append(attrs['href'][1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--publish', action='store_true', help='Require real content and build only public files into _site/.')
    mode.add_argument('--check', action='store_true', help='Validate content and document paths without writing files.')
    args = parser.parse_args()
    try:
        data = json.loads((ROOT / 'content.json').read_text())
        if args.check:
            validate(data, not data.get('draft', True))
            print('Content and document links are valid. No files were changed.')
            return
        source = data['profile'].get('cv_source', '')
        if source:
            source_path = (ROOT / source).resolve()
            if not source_path.is_relative_to(ROOT) or source_path.suffix.lower() != '.pdf':
                raise ValueError('cv_source must be a PDF inside this project.')
            if source_path.is_file():
                target = asset_path(data['profile']['cv'])
                if target is None:
                    raise ValueError('cv_source requires a local assets/ CV path.')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target)
        assets = validate(data, args.publish)
        rendered = build(data)
        checker = LinkCheck()
        checker.feed(rendered)
        if len(checker.ids) != len(set(checker.ids)):
            raise ValueError('Duplicate HTML IDs.')
        if set(checker.fragments) - set(checker.ids):
            raise ValueError('A content link points to a missing page section.')
        if args.publish:
            output = ROOT / '_site'
            if output.is_symlink():
                raise ValueError('_site must not be a symlink.')
            if output.exists():
                shutil.rmtree(output)
            output.mkdir()
            for filename in ('styles.css', 'script.js', '.nojekyll', '404.html'):
                shutil.copy2(ROOT / filename, output / filename)
            for asset in set(assets + [ROOT / 'assets/favicon.svg']):
                dest = output / asset.relative_to(ROOT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(asset, dest)
        else:
            output = ROOT
        (output / 'index.html').write_text(rendered)
        if data['profile'].get('domain'):
            domain = data['profile']['domain']
            (output / 'CNAME').write_text(domain + '\n')
            if args.publish:
                (output / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: https://{domain}/sitemap.xml\n')
                (output / 'sitemap.xml').write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                    f'<url><loc>https://{domain}/</loc></url></urlset>\n')
        print(f'Built {output / "index.html"} ({"draft preview" if data["draft"] else "public content"}).')
    except (KeyError, TypeError, ValueError) as error:
        parser.exit(1, f'Content error: {error}\n')


if __name__ == '__main__':
    main()
