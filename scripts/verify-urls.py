#!/usr/bin/env python3
"""Verify that every external URL referenced by the docs is reachable.

Deliberately run only from the weekly CI schedule / manual dispatch, not on
every push: URL checks are slow and flaky, and blocking PRs on them creates
noise. Uses the stdlib only. HEAD requests by default, with a GET fallback
for servers that reject HEAD (405/501), a single retry for transient network
errors, and a small thread pool. Duplicate URLs across docs are checked once
but reported for every document that references them.

Exit code 0 = all URLs reachable; 1 = at least one failure (listed).
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_URL_RE = re.compile(r"https?://[^\s)\]}>]+")
_UA = {"User-Agent": "ai-repo-sanitize-url-check"}
_MAX_WORKERS = 8
_MAX_ATTEMPTS = 2


def collect_urls() -> tuple[dict[str, list[str]], list[str]]:
    """Map unique external URLs to the docs referencing them, plus unreadable docs."""
    per_url: dict[str, list[str]] = {}
    unreadable: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{path.relative_to(ROOT)} ({exc.__class__.__name__})")
            continue
        doc = str(path.relative_to(ROOT))
        for url in _URL_RE.findall(text):
            # A closing markdown code-span backtick is never part of the URL.
            clean = url.rstrip(".,;:!?`")
            per_url.setdefault(clean, []).append(doc)
    for docs in per_url.values():
        docs.sort()
    return per_url, unreadable


def _request(url: str, method: str) -> urllib.request.Request:
    return urllib.request.Request(url, method=method, headers=_UA)


def check(url: str) -> bool:
    """Return True when *url* answers with a 2xx/3xx status.

    HEAD by default; a 405/501 (the server rejects HEAD) falls back to GET.
    Transient network errors are retried up to _MAX_ATTEMPTS. An HTTPError
    means the server answered, so it is not retried: a server-side decision
    will not resolve in one second.
    """
    for attempt in range(_MAX_ATTEMPTS):
        try:
            # trusted: docs URLs, reachability-only check
            with urllib.request.urlopen(_request(url, method="HEAD"), timeout=15) as response:
                return 200 <= response.status < 400
        except urllib.error.HTTPError as exc:
            if exc.code not in (405, 501):
                print(f"  - unreachable: {url} (HTTP {exc.code})")
                return False
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt + 1 >= _MAX_ATTEMPTS:
                print(f"  - unreachable: {url} ({exc.__class__.__name__})")
                return False
    try:
        # trusted: docs URLs, reachability-only check
        with urllib.request.urlopen(_request(url, method="GET"), timeout=15) as response:
            return 200 <= response.status < 400
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        if isinstance(exc, urllib.error.HTTPError):
            detail = f"(HTTP {exc.code})"
        else:
            detail = f"({exc.__class__.__name__})"
        print(f"  - unreachable: {url} {detail}")
        return False


def main() -> int:
    per_url, unreadable = collect_urls()
    urls = sorted(per_url)
    ok_by_url = dict(
        zip(urls, ThreadPoolExecutor(max_workers=_MAX_WORKERS).map(check, urls), strict=True)
    )
    failures = 0
    lines = 0
    for url in urls:
        for doc in per_url[url]:
            lines += 1
            ok = ok_by_url[url]
            if not ok:
                failures += 1
            print(f"  [{'ok' if ok else 'FAIL'}] {doc}: {url}")
    for entry in unreadable:
        lines += 1
        failures += 1
        print(f"  [FAIL] unreadable doc: {entry}")
    if failures:
        print(f"verify-urls: FAIL ({failures} of {lines} references unreachable)")
        return 1
    print(f"verify-urls: PASS ({len(urls)} unique URLs reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())