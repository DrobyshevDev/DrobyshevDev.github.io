#!/usr/bin/env python3
"""Hold the figures on the front page to the repositories they describe.

The page states four numbers under "Numbers with the conditions they were
measured under". Three of them were typed by hand and nothing recomputed them,
and by September 2026 two had gone stale: decisionrl had grown to 32 algorithms
across 24 environments while the page still said 31 and 22, and line coverage
read 86% when CI measured 84%. An organisation whose stated rule is that a
published number is measured on the run that describes it cannot have its own
front page be the exception.

Each figure here names its source and is checked against it:

  algorithms / environments  decisionrl's CITATION.cff, which decisionrl's own
                             test suite pins to the package it ships
  required dependencies      glia's pyproject.toml, read directly
  line coverage              Codecov, the run that produced it

recall@5 is not checked yet: praxis states it in prose, with nothing pinning it
to an eval run. That is a gap in praxis, not something to paper over here, so
the figure is reported as unverified rather than quietly passed.

Standard library only. Needs network, which is why this runs in its own weekly
workflow rather than in the required CI check.

Usage:
    python scripts/check_figures.py [site_root]
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAW = "https://raw.githubusercontent.com/DrobyshevDev"
CODECOV = "https://api.codecov.io/api/v2/github/DrobyshevDev/repos/decisionrl/"

PAGES = ("index.html", "ru/index.html")


def fetch(url: str) -> str | None:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "drobyshevdev-figures"})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None


def figures_on(page: str) -> dict[str, str]:
    """The <dt>/<dd> pairs of the figures list, as {label: value}."""
    block = re.search(r'<dl class="figures">(.*?)</dl>', page, re.DOTALL)
    if not block:
        return {}
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)<span", block.group(1), re.DOTALL)
    return {label.strip(): value.strip() for label, value in pairs}


def source_counts() -> tuple[int, int, int] | None:
    """Algorithms, environments and applied environments, from decisionrl."""
    citation = fetch(f"{RAW}/decisionrl/main/CITATION.cff")
    if citation is None:
        return None
    match = re.search(r"(\d+) algorithms and (\d+) environments, (\d+) of them applied", citation)
    return tuple(int(g) for g in match.groups()) if match else None


def source_glia_dependencies() -> int | None:
    pyproject = fetch(f"{RAW}/glia/master/pyproject.toml")
    if pyproject is None:
        return None
    match = re.search(r"^dependencies\s*=\s*\[(.*?)\]", pyproject, re.DOTALL | re.MULTILINE)
    if not match:
        return None
    return len([item for item in match.group(1).split(",") if item.strip()])


def source_coverage() -> float | None:
    body = fetch(CODECOV)
    if body is None:
        return None
    try:
        totals = json.loads(body).get("totals") or {}
    except json.JSONDecodeError:
        return None
    coverage = totals.get("coverage")
    return float(coverage) if coverage is not None else None


def main(root: Path) -> int:
    pages = {}
    for name in PAGES:
        path = root / name
        if not path.exists():
            print(f"  {name}: not found", file=sys.stderr)
            return 2
        pages[name] = figures_on(path.read_text(encoding="utf-8"))

    problems: list[str] = []
    unchecked: list[str] = []

    counts = source_counts()
    if counts is None:
        unchecked.append("algorithms/environments — decisionrl's CITATION.cff could not be read")
    else:
        algorithms, environments, applied = counts
        for name, figures in pages.items():
            stated = next((v for k, v in figures.items() if k in ("Algorithms", "Алгоритмов")), None)
            if stated is None:
                problems.append(f"{name}: no algorithms figure")
            elif stated != str(algorithms):
                problems.append(f"{name}: algorithms says {stated}, decisionrl ships {algorithms}")
        words = {9: ("nine", "девять")}
        for name, page in ((n, (root / n).read_text(encoding="utf-8")) for n in PAGES):
            for quoted in re.findall(r"(?:across|на) (\d+) (?:environments|средах)", page):
                if int(quoted) != environments:
                    problems.append(f"{name}: says {quoted} environments, decisionrl ships {environments}")
            # The applied count is spelled out in words beside it, which is how
            # it escaped every check that looked for digits.
            spelled = words.get(applied)
            if spelled and not any(word in page for word in spelled):
                problems.append(
                    f"{name}: does not say {spelled[0]}/{spelled[1]} applied environments, "
                    f"but decisionrl ships {applied}"
                )

    dependencies = source_glia_dependencies()
    if dependencies is None:
        unchecked.append("required dependencies — glia's pyproject.toml could not be read")
    elif dependencies != 0:
        problems.append(f"glia now has {dependencies} required dependencies; the page claims none")

    coverage = source_coverage()
    if coverage is None:
        unchecked.append("line coverage — Codecov has no figure for decisionrl yet")
    else:
        for name, figures in pages.items():
            stated = next((v for k, v in figures.items() if k in ("Line coverage", "Покрытие строк")), None)
            if stated is None:
                problems.append(f"{name}: no coverage figure")
            elif abs(int(stated.rstrip("%")) - coverage) >= 1:
                problems.append(
                    f"{name}: coverage says {stated}, Codecov measures {coverage:.1f}%"
                )

    unchecked.append("recall@5 — praxis states it in prose, with no eval run pinning it")

    for problem in problems:
        print(f"  DRIFTED  {problem}")
    for note in unchecked:
        print(f"  unchecked  {note}")
    if not problems:
        print("\n  Every figure that can be checked matches its source.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
