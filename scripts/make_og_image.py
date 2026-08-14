#!/usr/bin/env python3
"""Render the social preview card that appears when the site is linked.

The card is generated rather than drawn by hand so it can be regenerated when
the wording or the project list changes, and so the file in the repository is
reproducible: same script, same output, byte for byte.

    python scripts/make_og_image.py            # writes assets/og.png
    python scripts/make_og_image.py --check    # fails if the file is stale

Pillow is the only dependency and is not needed to build or serve the site --
the card is committed, so a reader never regenerates it.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 1200x630 is what every platform crops to. Anything else gets letterboxed.
W, H = 1200, 630

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


MARK_BG = (79, 70, 229)


def rounded_mark(draw, x, y, size):
    """The organisation mark: three stacked bars, same as assets/mark.svg."""
    draw.rounded_rectangle([x, y, x + size, y + size], radius=size * 0.25, fill=MARK_BG)
    unit = size / 32
    bars = [(7, 8, 18, 0.95), (7, 14.3, 12.6, 0.78), (7, 20.6, 7.4, 0.58)]
    for bx, by, bw, alpha in bars:
        # White at the given opacity over the indigo ground, composited per
        # channel: averaging one number across all three turns it grey.
        shade = tuple(round(255 * alpha + MARK_BG[c] * (1 - alpha)) for c in range(3))
        draw.rounded_rectangle(
            [x + bx * unit, y + by * unit, x + (bx + bw) * unit, y + (by + 3.4) * unit],
            radius=1.7 * unit, fill=shade)


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
    rounded_mark(d, pad, 74, 56)
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


def main(argv) -> int:
    out = Path(__file__).resolve().parent.parent / "assets" / "og.png"
    img = render()

    if "--check" in argv:
        if not out.exists():
            print(f"FAIL - {out.name} is missing; run scripts/make_og_image.py")
            return 1
        fresh = out.with_suffix(".check.png")
        img.save(fresh, optimize=True)
        same = hashlib.sha256(out.read_bytes()).digest() == hashlib.sha256(fresh.read_bytes()).digest()
        fresh.unlink()
        print("OK - social card matches the generator" if same else
              "FAIL - assets/og.png is stale; run scripts/make_og_image.py")
        return 0 if same else 1

    img.save(out, optimize=True)
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")

    # The touch icon reuses the mark, which is the same shape the favicon uses.
    icon = Image.new("RGB", (180, 180), (79, 70, 229))
    rounded_mark(ImageDraw.Draw(icon), 0, 0, 180)
    icon_path = out.parent / "apple-touch-icon.png"
    icon.save(icon_path, optimize=True)
    print(f"wrote {icon_path} ({icon_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
