#!/usr/bin/env python3
"""Structural checks for the static site.

Every check here corresponds to a property the published site must hold, and each
failure names the file, the line and what to do about it. Standard library only,
so CI needs nothing but a Python interpreter.

Usage:
    python scripts/check_site.py [site_root]
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

# Elements that never carry a closing tag, so the balance check must skip them.
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}

# Foreign content: SVG uses self-closing syntax the HTML parser reports as a
# start tag, and its children are irrelevant to document structure.
SKIP_SUBTREES = {"svg"}

PAGES = ["index.html", "ru/index.html", "legal/index.html", "404.html"]
# Pages that must carry full indexing metadata. The legal page is Russian-only
# by design -- a translated legal text is a second legal text that can diverge
# from the first -- so it is checked for structure and links but not for the
# hreflang pair.
INDEXED_PAGES = ["index.html", "ru/index.html"]


@dataclass
class Page:
    """Everything the checks need from one parsed HTML file."""

    path: Path
    rel: str
    lang: str | None = None
    title: str = ""
    unbalanced: list[str] = field(default_factory=list)
    links: list[tuple[str, int]] = field(default_factory=list)
    external_assets: list[tuple[str, int]] = field(default_factory=list)
    images_without_alt: list[int] = field(default_factory=list)
    h1_count: int = 0
    ids: set[str] = field(default_factory=set)
    meta: dict[str, str] = field(default_factory=dict)
    canonical: str | None = None
    hreflang: dict[str, str] = field(default_factory=dict)
    jsonld: list[str] = field(default_factory=list)


class PageParser(HTMLParser):
    def __init__(self, page: Page) -> None:
        super().__init__(convert_charrefs=True)
        self.page = page
        self.stack: list[tuple[str, int]] = []
        self.skip_depth = 0
        self.in_title = False
        self.in_jsonld = False

    # -- structure ---------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        line = self.getpos()[0]

        if self.skip_depth:
            if tag in SKIP_SUBTREES:
                self.skip_depth += 1
            return
        if tag in SKIP_SUBTREES:
            self.skip_depth = 1
            return

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, line))

        if tag == "html":
            self.page.lang = a.get("lang")
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.page.h1_count += 1
        elif tag == "img":
            if "alt" not in a:
                self.page.images_without_alt.append(line)
            self._record_asset(a.get("src", ""), line)
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self.in_jsonld = True
                self.page.jsonld.append("")
            self._record_asset(a.get("src", ""), line)
        elif tag == "link":
            rel = a.get("rel", "").lower()
            href = a.get("href", "")
            if rel == "canonical":
                self.page.canonical = href
            elif rel == "alternate" and a.get("hreflang"):
                self.page.hreflang[a["hreflang"]] = href
            elif rel in {"stylesheet", "icon"}:
                self._record_asset(href, line)
        elif tag == "meta":
            name = a.get("name") or a.get("property")
            if name:
                self.page.meta[name.lower()] = a.get("content", "")
        elif tag == "a":
            href = a.get("href")
            if href:
                self.page.links.append((href, line))

        if a.get("id"):
            self.page.ids.add(a["id"])

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth:
            if tag in SKIP_SUBTREES:
                self.skip_depth -= 1
            return
        if tag == "title":
            self.in_title = False
        if tag == "script":
            self.in_jsonld = False
        if tag in VOID_ELEMENTS:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for orphan, line in self.stack[i + 1:]:
                    self.page.unbalanced.append(f"<{orphan}> opened on line {line} is never closed")
                del self.stack[i:]
                return
        self.page.unbalanced.append(f"</{tag}> on line {self.getpos()[0]} closes nothing")

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.page.title += data
        if self.in_jsonld and self.page.jsonld:
            self.page.jsonld[-1] += data

    # -- helpers -----------------------------------------------------------

    def _record_asset(self, url: str, line: int) -> None:
        if url.startswith(("http://", "https://", "//")):
            self.page.external_assets.append((url, line))
        elif url:
            self.page.links.append((url, line))

    def close(self) -> None:  # type: ignore[override]
        super().close()
        for orphan, line in self.stack:
            self.page.unbalanced.append(f"<{orphan}> opened on line {line} is never closed")


def parse(root: Path, rel: str) -> Page:
    path = root / rel
    page = Page(path=path, rel=rel)
    parser = PageParser(page)
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    page.title = page.title.strip()
    return page


def resolve(root: Path, rel: str, href: str) -> Path:
    """Map a site-relative or document-relative URL to a file on disk."""
    target = unquote(urlparse(href).path)
    base = root if target.startswith("/") else (root / rel).parent
    path = (base / target.lstrip("/")).resolve()
    return path / "index.html" if path.is_dir() else path


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    failures: list[str] = []
    pages = {rel: parse(root, rel) for rel in PAGES}

    def fail(rel: str, message: str) -> None:
        failures.append(f"{rel}: {message}")

    for rel, page in pages.items():
        # Structure.
        for problem in page.unbalanced:
            fail(rel, f"unbalanced markup — {problem}")
        if page.h1_count != 1:
            fail(rel, f"expected exactly one <h1>, found {page.h1_count}")
        if not page.lang:
            fail(rel, "<html> is missing a lang attribute; screen readers need it to pick a voice")
        if not page.title:
            fail(rel, "missing a non-empty <title>")
        for line in page.images_without_alt:
            fail(rel, f"<img> on line {line} has no alt attribute (use alt=\"\" if decorative)")

        # Self-containment: the site must not reach out to a third party.
        for url, line in page.external_assets:
            fail(rel, f"external asset on line {line}: {url} — inline it or vendor it into assets/")

        # Every link resolves: internal files exist, in-page anchors exist.
        for href, line in page.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:", "//")):
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in page.ids:
                    fail(rel, f"line {line}: anchor {href} has no matching id on this page")
                continue
            target = resolve(root, rel, href)
            if not target.exists():
                fail(rel, f"line {line}: {href} does not resolve ({target} is missing)")
            fragment = urlparse(href).fragment
            if fragment:
                target_rel = target.relative_to(root).as_posix()
                if target_rel in pages and fragment not in pages[target_rel].ids:
                    fail(rel, f"line {line}: {href} points at an id that does not exist")

    # Metadata that only the indexed pages need.
    for rel in INDEXED_PAGES:
        page = pages[rel]
        if not page.meta.get("description"):
            fail(rel, "missing <meta name=\"description\">")
        if not page.canonical:
            fail(rel, "missing <link rel=\"canonical\">")
        for tag in ("en", "ru", "x-default"):
            if tag not in page.hreflang:
                fail(rel, f"missing hreflang alternate for '{tag}'")
        for prop in ("og:title", "og:description", "og:url", "og:type", "og:image"):
            if not page.meta.get(prop):
                fail(rel, f"missing Open Graph property {prop}")

        # og:image is an absolute URL, so it never passes through the link
        # resolver above -- and a card that 404s is worse than no card, because
        # every platform caches the miss.
        card = page.meta.get("og:image", "")
        if card:
            path = urlparse(card).path.lstrip("/")
            if not (root / path).exists():
                fail(rel, f"og:image points at {card}, but {path} is not in the repository")
        if page.meta.get("twitter:card") == "summary" and card:
            fail(rel, "twitter:card is 'summary' but a 1200x630 image is set; use 'summary_large_image'")

    # The two language pages must stay mirrors of each other.
    en, ru = pages["index.html"], pages["ru/index.html"]
    if en.lang != "en" or ru.lang != "ru":
        fail("site", f"language mismatch: index.html is '{en.lang}', ru/index.html is '{ru.lang}'")
    sections_en = {i for i in en.ids if i not in {"main", "primary-nav"}}
    sections_ru = {i for i in ru.ids if i not in {"main", "primary-nav"}}
    if sections_en != sections_ru:
        missing = sections_en ^ sections_ru
        fail("site", f"the two language pages have diverged; sections only on one side: {sorted(missing)}")

    # Structured data. A JSON-LD block with a syntax error is silently ignored
    # by every consumer, so the page looks fine and the rich result never
    # appears -- exactly the kind of failure nobody notices.
    for rel, page in pages.items():
        for i, block in enumerate(page.jsonld, 1):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                fail(rel, f"JSON-LD block {i} does not parse: {exc}")
                continue
            for node in data.get("@graph", [data]):
                if not node.get("@type"):
                    fail(rel, f"JSON-LD block {i} has a node without @type")

    # Files the deployment depends on.
    for required in ("robots.txt", "sitemap.xml", ".nojekyll", "assets/site.css", "assets/site.js"):
        if not (root / required).exists():
            fail("site", f"{required} is missing")

    if failures:
        print(f"FAIL — {len(failures)} problem(s):\n", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    checked = ", ".join(PAGES)
    print(f"OK — {checked} pass structure, metadata, link and self-containment checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
