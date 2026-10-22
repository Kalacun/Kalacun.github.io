# Aleksander Kalacun's academic website

The website at **https://kalacun.com** uses the selected portrait design and is hosted by GitHub Pages. The source repository is **https://github.com/Kalacun/Kalacun.github.io**. Cloudflare manages the domain and DNS.

## Edit the content

**Edit `content.json`.** It is the single source for the page's text, publications, project descriptions, links, certificates, and other achievements. Run `python3 tools/build.py` to refresh the generated `index.html`. Do not edit that HTML directly: the next build replaces it.

- Profile and bio: `profile`.
- Published and current research: `research`. Use `status` to distinguish published, accepted, submitted, preprint, and in-progress work. A planned venue is not an acceptance.
- Early papers: `earlier_research`.
- Projects: `projects`. `featured: false` places an entry under “More projects.”
- Work, education, awards, and courses: `experience`, `education`, `awards`, and `certificates`.
- Other: `languages`, `ultimate_frisbee`, and `misc`.

Duplicate an existing record to add an achievement. Array order controls entry order. Remove a record to remove it from the site. Keep text short; put longer material in `abstract`, `research_summary`, or project `details`. Write plain text, not HTML. Use `\n\n` for paragraph breaks within a JSON string. Keep commas between records; there must be no trailing comma after the last record.

Every paper has a closed “Summary (expand)” panel. Abstract wording is preserved in the corresponding `abstract` field. The full certificates list and “More projects” also start closed. Existing middle-dot separators are literal content; the builder does not add them between project fields or in the footer.

The builder now reproduces the current page's descriptions, headings, and footer, so direct edits and structured data no longer have to be maintained separately. Public builds omit the local photo picker and empty link placeholders. Incomplete course details can be filled in later without inventing content.

## Replace documents or the portrait

Replace `assets/documents/cv/kalacun-cv.pdf` to update the CV. That file is authoritative; a draft in the project root no longer overwrites it. Replace `assets/portrait.jpg` to update the photograph, or set `profile.photo` to another asset path and update `profile.photo_alt`.

Add documents under `assets/documents/` and link them in the relevant record:

```json
{"label": "Paper (PDF)", "url": "assets/documents/papers/my-paper.pdf"}
```

Use exact filenames, including capitalization. An empty URL is omitted from the live page. The build checks that each linked local file exists and deploys only referenced assets, the favicon, and the site's HTML, CSS, and JavaScript. Unlinked notes and input files are not served. Everything committed to this public source repository is still publicly downloadable, so add only files intended for publication.

Certificate originals remain unchanged. Translation text is in `tools/certificate-translations.json` and `tools/additional-document-translations.json`. Optional translation scripts require ReportLab and Arial; ordinary website builds use only Python's standard library. The English PDFs are reference translations, not certified translations. Original hashes are recorded in `tools/certificate-sources.json`.

## Preview locally

Python 3.10 or newer is sufficient. No package installation is needed.

```bash
python3 tools/build.py
python3 -m http.server 8000 --bind 127.0.0.1
```

Open **http://127.0.0.1:8000/**. Stop the server with Ctrl+C. Alternatively, run `make preview`. If a server is already running in this folder, rebuild and refresh its page.

Check changes before committing:

```bash
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/build.py --publish
```

The publish command writes `_site/` without changing the source page. To preview that exact output, use `python3 -m http.server 8001 --bind 127.0.0.1 --directory _site`, then open http://127.0.0.1:8001/. `make publish` runs the checks and publication build together.

## Git development

The local project tracks the GitHub repository through `origin`; `main` is the live branch. Earlier design history is preserved on the local `codex/phd-homepage-v4` branch and is not included in the fresh public repository.

For a small update:

```bash
git switch main
git pull --ff-only
# Edit content.json or replace a document.
python3 tools/build.py
python3 -m unittest discover -s tools -p 'test_*.py'
git add content.json index.html
# Also add any new or replaced documents explicitly.
git commit -m "Update research and CV"
git push
```

For changes you want to review before publishing:

```bash
git switch main
git pull --ff-only
git switch -c codex/update-research
# Edit, build, and check as above.
git add content.json index.html
git commit -m "Update research descriptions"
git push -u origin codex/update-research
gh pr create --base main --fill
```

GitHub checks the pull request without deploying it. Merge it when ready; a push or merge to `main` automatically rebuilds and deploys the site. Pull-request artifacts are downloadable build output, not publicly hosted preview URLs. For quick browser edits, open `content.json` on GitHub and use its pencil button; a commit to `main` deploys automatically, without needing to edit `index.html` there.

Use `styles.css` for appearance and `tools/home.html` for the page shell. Section rendering lives in `tools/build.py`. The responsive CSS supports narrow screens and browser zoom; no framework is required.

## Publishing and the domain

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for the exact GitHub settings, Cloudflare DNS records, domain verification, HTTPS, and troubleshooting. `profile.domain` is `kalacun.com`; the builder creates the canonical URL, `CNAME`, `robots.txt`, and sitemap. GitHub Actions deployments also require the custom domain to be configured in the repository's Pages settings; the `CNAME` file alone does not configure it.

The workflow at `.github/workflows/pages.yml` checks content, JavaScript syntax, and document links, builds `_site/`, and deploys it. Only pushes to `main` deploy. Failed checks stop deployment. Domain registration, DNS, and HTTPS do not need to be repeated for ordinary content updates.

To undo a published change, use `git revert` on its commit and push the revert. Avoid force-pushing `main` or deleting publication history.
