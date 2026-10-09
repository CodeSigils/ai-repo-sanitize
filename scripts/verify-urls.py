#!/usr/bin/env python3
"""Verify that every external URL referenced by the docs is reachable.

Deliberately run only from the weekly CI schedule / manual dispatch, not on
every push: URL checks are slow and flaky, and blocking PRs on them creates
noise. Uses HEAD requests and the stdlib only.

Exit code 0 = all URLs reachable; 1 = at least one failure (listed).
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_URL_RE = re.compile(r"https?://[^\s)\]}>]+")
_UA = {"User-Agent": "ai-repo-sanitize-url-check"}


def collect_urls() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in sorted(ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for url in _URL_RE.findall(text):
            clean = url.rstrip(".,;:!?")
            found.append((str(path.relative_to(ROOT)), clean))
    return found


def check(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD", headers=_UA)
    try:
        # trusted: docs URLs, reachability-only check
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 400
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
        print(f"  - unreachable: {url} ({exc.__class__.__name__})")
        return False


def main() -> int:
    urls = collect_urls()
    failures = 0
    for doc, url in urls:
        ok = check(url)
        if not ok:
            failures += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {doc}: {url}")
    if failures:
        print(f"verify-urls: FAIL ({failures} of {len(urls)} unreachable)")
        return 1
    print(f"verify-urls: PASS ({len(urls)} URLs reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())