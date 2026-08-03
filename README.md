# DrobyshevDev.github.io

The organisation website: <https://drobyshevdev.github.io/>

A static site with no build step and no third-party requests. Fonts are the system stack,
styles and scripts are two local files, and the page is fully readable with JavaScript
disabled — the script only adds the theme toggle, the mobile menu and the copy buttons.

## Layout

```
index.html          English page
ru/index.html       Russian page
assets/site.css     One stylesheet, light and dark
assets/site.js      Progressive enhancement only
assets/mark.svg     Logo mark
assets/favicon.svg  Favicon
404.html            Not-found page
robots.txt          Crawl policy
sitemap.xml         Two URLs with hreflang alternates
.nojekyll           Serve files as-is, no Jekyll pass
```

## Local preview

Any static server works; paths are absolute, so opening `index.html` from the filesystem
will not resolve `/assets/`.

```bash
python -m http.server 8000
```

Then open <http://localhost:8000/>.

## Deployment

GitHub Pages serves the `main` branch from the repository root. Pushing to `main`
publishes. The CI workflow checks that both pages parse, that every internal link
resolves, and that no external stylesheet or script sneaks in.

## Changing the content

Facts on the page (versions, licences, algorithm and test counts, retrieval metrics) are
copied from the project repositories. When a project releases, update both `index.html`
and `ru/index.html` — the two pages are deliberately kept as mirrors rather than generated
from a shared source, because a build step for two pages costs more than it saves.
