# DrobyshevDev.github.io

The organisation website: <https://drobyshevdev.github.io/>

[![CI](https://github.com/DrobyshevDev/DrobyshevDev.github.io/actions/workflows/ci.yml/badge.svg)](https://github.com/DrobyshevDev/DrobyshevDev.github.io/actions/workflows/ci.yml)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

A static site with no build step and no third-party requests. The type is the system
stack, the styles and the script are two local files, and every page is fully readable
with JavaScript disabled — the script only opens the mobile menu and copies commands.

The self-containment is not a claim in the footer. `scripts/check_site.py` fails the build
if an external stylesheet, script, font or image appears on any page, and CI runs it on
every push.

## Layout

```
index.html                  English page
ru/index.html               Russian page
legal/index.html            Agreement, privacy policy, legal notice (Russian)
404.html                    Not-found page

assets/site.css             One stylesheet, one scheme, dark
assets/site.js              Progressive enhancement only
assets/mark.svg             Logo mark
assets/favicon.svg          Favicon
assets/og.png               Social preview card, 1200x630, generated
assets/apple-touch-icon.png Home-screen icon, generated

scripts/check_site.py       Structure, metadata, links, self-containment
scripts/make_og_image.py    Renders the card and the touch icon

robots.txt                  Crawl policy
sitemap.xml                 Indexed URLs with hreflang alternates
.nojekyll                   Serve files as-is, no Jekyll pass
```

## Local preview

Any static server works; paths are absolute, so opening `index.html` from the filesystem
will not resolve `/assets/`.

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/>.

## Checks

```bash
python scripts/check_site.py .
```

Standard library only, so it needs nothing but a Python interpreter. It verifies that
markup balances, that each page has exactly one `<h1>` and a language, that every internal
link and in-page anchor resolves, that indexed pages carry canonical, hreflang, description
and Open Graph tags, that every JSON-LD block parses, that the social card referenced by
`og:image` is actually in the repository — and that no page reaches out to a third party.

It also checks that the English and Russian pages have not diverged: the two are mirrors
kept by hand, and this is what stops one gaining a section the other lacks.

## The social card

`assets/og.png` is what appears when the site is linked anywhere. It is generated rather
than drawn, so it can be regenerated when the wording or the project list changes:

```bash
pip install "pillow>=10"
python scripts/make_og_image.py
```

The card names the projects the front page leads with. CI runs `--check`, which re-renders
it and fails if the committed file no longer matches — otherwise adding a project to the
page leaves a preview quietly a release behind, and nobody notices, because the person who
shares the link is never the person who edited the page.

Pillow is needed only to regenerate the card. Building and serving the site needs nothing.

## Deployment

Pushing to `main` publishes through the Pages workflow in `.github/workflows/pages.yml`.

## Changing the content

Facts on the page — versions, licences, algorithm and test counts, retrieval metrics — are
copied from the project repositories, and each is printed with the conditions it was
measured under. When a project releases, update `index.html` and `ru/index.html` together;
the two are deliberately kept as mirrors rather than generated from a shared source,
because a build step for two pages costs more than it saves. The checker enforces that they
stay in step.

## Licence

[MIT](LICENSE) — the markup, the stylesheet, the scripts, the workflows. The name, the mark
and the wording of the legal pages identify DrobyshevDev specifically; everything else is
yours to take.
