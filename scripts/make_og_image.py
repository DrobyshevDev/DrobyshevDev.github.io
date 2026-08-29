#!/usr/bin/env python3
"""Render the social preview card that appears when the site is linked.

The card is generated rather than drawn by hand so it can be regenerated when
the wording or the project list changes.

The output is not byte-reproducible across machines: it is drawn with whatever
fonts are installed, and a Linux runner has neither Georgia nor Calibri.
Vendoring those is not an option their licences allow, so --check verifies the
card still says the right things rather than that it renders to the same bytes.

    python scripts/make_og_image.py            # writes assets/og.png
    python scripts/make_og_image.py --check    # fails if the card no longer
                                               # matches what the page claims

Pillow is the only dependency and is not needed to build or serve the site --
the card is committed, so a reader never regenerates it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 1200x630 is what every platform crops to. Anything else gets letterboxed.
W, H = 1200, 630
MARK_PATH = Path(__file__).resolve().parent.parent / "assets" / "mark.png"

INK = (10, 11, 14)
INK_RAISED = (18, 20, 26)
LINE = (34, 38, 48)
PAPER = (248, 249, 251)
PAPER_DIM = (154, 161, 173)
PAPER_FAINT = (124, 134, 151)
ACCENT = (165, 176, 255)
GOLD = (216, 182, 120)

TITLE = "Frameworks and tooling for"
TITLE2 = "machine learning and LLM agents"
TAGLINE = "Open source \u00b7 typed \u00b7 tested on Linux, macOS and Windows"
DOMAIN = "drobyshevdev.github.io"

# The projects the front page leads with, in the order it lists them. Adding one
# to the site without adding it here makes the card quietly wrong, which --check
# in CI is there to catch.
PROJECTS = ["praxis", "mlango", "glia", "decisionrl", "stadion"]

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")]
SERIF = ["georgiab.ttf", "Georgia_Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]
SANS = ["calibri.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
MONO = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"]


def load_font(candidates, size):
    """First font that exists, falling back to Pillow's built-in.

    The card is committed to the repository, so a machine without these fonts
    never renders it in anger -- but --check would flag a mismatch, which is
    why the fallback is silent rather than fatal.
    """
    for directory in FONT_DIRS:
        if not directory.exists():
            continue
        for name in candidates:
            for path in directory.rglob(name):
                try:
                    return ImageFont.truetype(str(path), size)
                except OSError:
                    continue
    return ImageFont.load_default()


def paste_mark(img, x, y, size):
    """Paste the organisation mark, the same file the site and GitHub both show.

    It is a raster rather than something drawn here on purpose: the mark has a
    rim glow and scanlines that a dozen lines of Pillow would only approximate,
    and a card that shows a near-miss of the logo is worse than one that shows
    the logo.
    """
    mark = Image.open(MARK_PATH).convert("RGB").resize((size, size), Image.LANCZOS)
    img.paste(mark, (int(x), int(y)))


def render() -> Image.Image:
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # A soft wash in the top-left, the same gradient idea as the site hero.
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    for i in range(60, 0, -1):
        r = i * 12
        t = i / 60
        colour = tuple(int(INK[c] + (ACCENT[c] - INK[c]) * 0.10 * (1 - t)) for c in range(3))
        gd.ellipse([-r + 120, -r + 40, r + 120, r + 40], fill=colour)
    img = Image.blend(img, glow, 0.9)
    d = ImageDraw.Draw(img)

    f_title = load_font(SERIF, 62)
    f_tag = load_font(SANS, 27)
    f_mono = load_font(MONO, 24)
    f_brand = load_font(SANS, 34)
    f_domain = load_font(MONO, 26)

    pad = 84
    paste_mark(img, pad, 74, 56)
    d = ImageDraw.Draw(img)
    d.text((pad + 76, 82), "DrobyshevDev", font=f_brand, fill=PAPER)

    d.text((pad, 196), TITLE, font=f_title, fill=PAPER)
    d.text((pad, 268), TITLE2, font=f_title, fill=PAPER)

    d.text((pad, 366), TAGLINE, font=f_tag, fill=PAPER_DIM)

    # Project row, mono, separated by faint dots.
    x = pad
    for i, name in enumerate(PROJECTS):
        if i:
            d.text((x, 446), "\u00b7", font=f_mono, fill=PAPER_FAINT)
            x += d.textlength("\u00b7", font=f_mono) + 18
        d.text((x, 446), name, font=f_mono, fill=ACCENT)
        x += d.textlength(name, font=f_mono) + 18

    d.line([(pad, 516), (W - pad, 516)], fill=LINE, width=1)
    d.text((pad, 542), DOMAIN, font=f_domain, fill=PAPER)

    right = "MIT \u00b7 Apache-2.0"
    d.text((W - pad - d.textlength(right, font=f_mono), 546), right, font=f_mono, fill=GOLD)
    return img


def page_projects(index: Path) -> list[str]:
    """The projects the front page leads with, in the order it lists them."""
    html = index.read_text(encoding="utf-8")
    start = html.find('id="projects"')
    end = html.find("</section>", start)
    section = html[start:end] if start >= 0 else ""
    return re.findall(
        r'<h3><a href="https://github\.com/DrobyshevDev/([\w.-]+)"', section)


def check(out: Path) -> int:
    """Is the committed card still telling the truth?

    Deliberately not a byte comparison against a fresh render. The card is
    drawn with whatever fonts the machine has, and a CI runner has neither
    Georgia nor Calibri -- so identical bytes would need the fonts vendored
    into the repository, which their licences do not allow.

    What actually goes stale is the project list: someone adds a project to the
    page and the preview keeps advertising the old set. That is what this
    checks, plus that the file exists and has the dimensions every platform
    crops to.
    """
    problems = []
    root = out.parent.parent

    if not out.exists():
        print(f"FAIL - {out.name} is missing; run scripts/make_og_image.py")
        return 1

    with Image.open(out) as img:
        if img.size != (W, H):
            problems.append(f"{out.name} is {img.size[0]}x{img.size[1]}, expected {W}x{H}")

    icon = out.parent / "apple-touch-icon.png"
    if not icon.exists():
        problems.append(f"{icon.name} is missing; run scripts/make_og_image.py")

    listed = page_projects(root / "index.html")
    if not listed:
        problems.append("could not read the project list out of index.html; has the markup changed?")
    elif listed != PROJECTS:
        problems.append(
            f"the card names {PROJECTS} but the page leads with {listed}; "
            f"update PROJECTS in this script and re-run it")

    if problems:
        print("FAIL - " + "\n       ".join(problems))
        return 1
    print(f"OK - card is {W}x{H} and names the same projects as the page: {', '.join(PROJECTS)}")
    return 0


def main(argv) -> int:
    out = Path(__file__).resolve().parent.parent / "assets" / "og.png"

    if "--check" in argv:
        return check(out)

    img = render()
    img.save(out, optimize=True)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")

    # The touch icon reuses the mark, which is the same shape the favicon uses.
    icon = Image.new("RGB", (180, 180), (5, 4, 27))
    paste_mark(icon, 0, 0, 180)
    icon_path = out.parent / "apple-touch-icon.png"
    icon.save(icon_path, optimize=True)
    print(f"wrote {icon_path} ({icon_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
