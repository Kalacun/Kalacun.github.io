"""Checks for the content/publication boundary, not presentation snapshots."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
import re
import hashlib
import build


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((build.ROOT / 'content.json').read_text())
        # Draft validation uses an explicit fixture, independently of the live site.
        self.data['draft'] = True
        self.data['profile']['cv_is_draft'] = True

    def test_public_site_preserves_research_descriptions_and_custom_domain(self):
        data = copy.deepcopy(self.data)
        data['draft'] = False
        data['profile']['cv_is_draft'] = False
        build.validate(data, True)
        rendered = build.build(data)
        for paper in data['research']:
            self.assertIn(build.esc(paper['summary']), rendered)
        self.assertIn('href="https://kalacun.com/"', rendered)
        self.assertNotIn('noindex', rendered)
        self.assertNotIn('data-photo-input', rendered)
        self.assertNotIn('to add</span>', rendered)
        self.assertNotIn(' · Updated ', rendered)

    def public_content(self):
        data = copy.deepcopy(self.data)
        data['draft'] = False
        data['profile']['cv_is_draft'] = False
        data['profile']['cv_label'] = 'CV (PDF)'
        # Keep one complete, CV-derived project; omit unfinished sections.
        for key in build.GROUPS:
            data[key] = []
        project = copy.deepcopy(self.data['projects'][0])
        project['details'] = ''
        data['projects'] = [project]
        return data

    def test_misplaced_link_and_missing_fields_have_clear_locations(self):
        self.data['research'].insert(1, {'label': 'Paper', 'url': 'assets/paper.pdf'})
        with self.assertRaisesRegex(ValueError, r'research\[1\].*document link.*"links"'):
            build.validate(self.data, False)
        self.data['research'].pop(1)
        del self.data['research'][0]['authors']
        with self.assertRaisesRegex(ValueError, r'research\[0\].*"authors"'):
            build.validate(self.data, False)

    def test_check_only_reports_edit_errors_without_rewriting_files(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            shutil.copytree(build.ROOT / 'tools', site / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
            data = self.public_content()
            data['projects'] = []
            data['profile'].update(cv='', photo='', cv_source='')
            data['research'] = [{'label': 'Paper', 'url': 'assets/paper.pdf'}]
            content = site / 'content.json'
            content.write_text(json.dumps(data))
            page = site / 'index.html'
            page.write_text('Existing preview must remain unchanged.')
            command = [sys.executable, str(site / 'tools/build.py'), '--check']
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 1)
            self.assertIn('research[0] is a document link', failed.stderr)
            self.assertNotIn('Traceback', failed.stderr)
            data['research'] = []
            content.write_text(json.dumps(data))
            passed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertEqual(page.read_text(), 'Existing preview must remain unchanged.')
            self.assertFalse((site / '_site').exists())

    def test_drafts_and_draft_cvs_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, 'still a draft'):
            build.validate(self.data, True)
        self.data['draft'] = False
        with self.assertRaisesRegex(ValueError, 'draft CV'):
            build.validate(self.data, True)

    def test_unfinished_real_records_cannot_be_published(self):
        self.data['draft'] = False
        self.data['profile']['cv_is_draft'] = False
        self.data['research'][0]['contribution'] = '[Add your individual contribution]'
        with self.assertRaisesRegex(ValueError, 'placeholder'):
            build.validate(self.data, True)

    def test_samples_and_empty_sections_disappear(self):
        data = self.public_content()
        sample = copy.deepcopy(self.data['research'][0])
        sample['example'] = True
        data['research'] = [sample]
        build.validate(data, True)
        rendered = build.build(data)
        self.assertNotIn(sample['title'], rendered)
        self.assertNotIn('href="#research"', rendered)
        self.assertNotIn('writing-note', rendered)
        self.assertNotIn('compare.html', rendered)
        self.assertNotIn('Optional portrait', rendered)
        self.assertIn('Syntherra', rendered)

    def test_public_output_includes_only_referenced_assets(self):
        root = build.ROOT
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            shutil.copytree(root / 'tools', site / 'tools', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(root / 'assets', site / 'assets')
            for filename in ('styles.css', 'script.js', '404.html', '.nojekyll'):
                shutil.copy2(root / filename, site / filename)
            (site / 'assets/unlinked-draft.txt').write_text('Must not ship')
            (site / 'compare.html').write_text('Must not ship')
            (site / 'content.json').write_text(json.dumps(self.public_content()))
            result = subprocess.run([sys.executable, str(site / 'tools/build.py'), '--publish'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = site / '_site'
            self.assertTrue((output / self.data['profile']['cv']).is_file())
            self.assertTrue((output / 'assets/favicon.svg').is_file())
            self.assertFalse((output / 'assets/unlinked-draft.txt').exists())
            self.assertFalse((output / 'compare.html').exists())
            self.assertFalse((output / 'content.json').exists())
            self.assertIn('Syntherra', (output / 'index.html').read_text())

    def test_local_documents_and_links_are_checked(self):
        for bad_url in ('javascript:alert(1)', '//example.com/test', '../README.md', 'assets/missing.pdf'):
            with self.subTest(url=bad_url), self.assertRaises(ValueError):
                build.validate_url(bad_url)
        build.validate_url(self.data['profile']['cv'])

    def test_content_does_not_become_executable_html(self):
        self.data['profile']['name'] = '<script>alert("name")</script>'
        rendered = build.build(self.data)
        self.assertNotIn('<script>alert', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_ids_statuses_and_boolean_flags_are_validated(self):
        original = copy.deepcopy(self.data)
        self.data['research'][1]['id'] = self.data['research'][0]['id']
        with self.assertRaisesRegex(ValueError, 'unique'):
            build.validate(self.data, False)
        self.data = copy.deepcopy(original)
        self.data['research'][0]['status'] = 'in press maybe'
        with self.assertRaisesRegex(ValueError, 'Unknown research status'):
            build.validate(self.data, False)
        self.data = self.public_content()
        self.data['projects'][0]['example'] = 'false'
        with self.assertRaisesRegex(ValueError, 'example must'):
            build.validate(self.data, False)

    def test_selected_site_order_and_removed_content(self):
        class Structure(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sections, self.details = [], []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'section':
                    self.sections.append(attrs.get('id'))
                if tag == 'details':
                    self.details.append(attrs)

        rendered = build.build(self.data)
        structure = Structure()
        structure.feed(rendered)
        self.assertEqual(structure.sections[:7], ['overview', 'research', 'current-research',
            'experience', 'education', 'earlier-research', 'projects'])
        self.assertIn('misc', structure.sections)
        self.assertNotIn('community', structure.sections)
        self.assertEqual(sum('open' not in attrs for attrs in structure.details),
                         len(self.data['research']) + len(self.data['earlier_research']) + 2)
        self.assertEqual(rendered.count('<summary>Summary (expand)'),
                         len(self.data['research']) + len(self.data['earlier_research']))
        for text in ('compare.html', 'previews/', 'versions/', 'On this page',
                     'Teaching &amp; community', 'Scientific computing lecture',
                     'BSc student · Junior researcher · University of Maribor · Slovenia'):
            self.assertNotIn(text, rendered)
        removed_ids = ['additional-project-1', 'additional-project-2', 'additional-project-3',
                       'additional-project-4', 'additional-project-7']
        for entry_id in removed_ids:
            self.assertNotIn(f'id="{entry_id}"', rendered)
        self.assertIn('<h4>Coach and board member</h4>', rendered)
        self.assertIn('<h4>Player</h4>', rendered)
        other = rendered.split('<section id="misc"')[1].split('</section>')[0]
        self.assertIn('<h3 id="languages-title">Languages</h3>', other)
        self.assertIn('<h3 id="ultimate-frisbee-title">Ultimate frisbee</h3>', other)
        self.assertNotIn('languages', structure.sections)
        self.assertIn('How Many Fractions Are There?', rendered)
        self.assertIn('Around 35 teams', rendered)
        self.assertIn('28 advanced to the first round', rendered)
        self.assertIn('eight reached the final', rendered)

    def test_current_abstract_is_inside_collapsed_summary(self):
        self.data['research'][1]['status'] = 'submitted'
        self.data['research'][1]['abstract'] = 'First paragraph with <control>.\n\nSecond paragraph.'
        rendered = build.build(self.data)
        paper = re.search(r'<article class="research-entry" id="tropical-rl".*?</article>', rendered, re.S).group()
        self.assertIn('<h4>Abstract</h4><p>First paragraph with &lt;control&gt;.</p><p>Second paragraph.</p>', paper)
        self.assertIn('<details><summary>Summary (expand)', paper)
        self.assertLess(paper.index('<details>'), paper.index('<h4>Abstract</h4>'))
        self.assertLess(paper.index('<h4>Abstract</h4>'), paper.index('</details>'))
        self.assertIn('Submitted · not yet accepted', paper)

    def test_published_abstracts_and_secondary_lists_start_collapsed(self):
        self.data['research'][0]['abstract'] = 'A full abstract with <control>.\n\nAnother paragraph.'
        rendered = build.build(self.data)
        paper = re.search(r'<article class="research-entry" id="self-rewriting-de".*?</article>', rendered, re.S).group()
        self.assertIn('<details><summary>Summary (expand)', paper)
        self.assertIn('<h4>Abstract</h4><p>A full abstract with &lt;control&gt;.</p><p>Another paragraph.</p>', paper)
        self.assertNotIn('full-abstract', paper)
        self.assertLess(paper.index('<details>'), paper.index('<h4>Abstract</h4>'))
        self.assertLess(paper.index('<h4>Abstract</h4>'), paper.index('</details>'))
        self.assertIn('<details class="more-entries">', rendered)
        self.assertIn('<details class="certificate-list">', rendered)
        certificates = rendered.split('<section id="certificates"')[1].split('</section>')[0]
        self.assertEqual(certificates.count('<article'), len(self.data['certificates']))
        earlier = copy.deepcopy(self.data['earlier_research'][-1])
        earlier['abstract'] = 'Earlier publication abstract.'
        self.assertIn('<details><summary>Summary (expand)', build.compact_entry(earlier, True, publication=True))
        earlier['abstract'] = ''
        earlier['research_summary'] = ''
        empty = build.compact_entry(earlier, True, publication=True)
        self.assertIn('<details><summary>Summary (expand)', empty)
        self.assertIn('Abstract to be added.', empty)

    def test_certificate_originals_and_translations_are_linked_and_intact(self):
        sources = json.loads((build.ROOT / 'tools/certificate-sources.json').read_text())['originals']
        linked = {link['url'] for key in build.GROUPS for item in self.data.get(key, [])
                  for link in item.get('links', []) if link.get('url')}
        self.assertEqual(len(sources), 16)
        for source in sources:
            with self.subTest(source=source['public']):
                original = build.ROOT / source['public']
                self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), source['sha256'])
                self.assertIn(source['public'], linked)
                if not source['english_in_original']:
                    translation = source.get('translation') or ('assets/documents/certificates/translations/' + original.stem + '-en.pdf')
                    self.assertIn(translation, linked)
                    self.assertTrue((build.ROOT / translation).is_file())
        self.assertEqual(sum(not source['english_in_original'] for source in sources), 10)

    def test_language_and_award_documents_stay_out_of_training_section(self):
        rendered = build.build(self.data)
        training = rendered.split('<section id="certificates"')[1].split('</section>')[0]
        other = rendered.split('<section id="misc"')[1].split('</section>')[0]
        awards = rendered.split('<section id="awards"')[1].split('</section>')[0]
        self.assertIn('german-b1-b2.pdf', other)
        self.assertIn('ielts.pdf', other)
        self.assertIn('B1/B2', other)
        self.assertIn('gamejam-first-place.pdf', awards)
        self.assertIn('hackathon-2025.pdf', awards)
        for filename in ('ielts.pdf', 'german-b1-b2.pdf', 'gamejam-first-place.pdf', 'hackathon-2025.pdf'):
            self.assertNotIn(filename, training)
        self.assertNotIn('<iframe', rendered)
        self.assertNotIn('<embed', rendered)


if __name__ == '__main__':
    unittest.main()
