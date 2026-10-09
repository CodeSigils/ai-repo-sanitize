"""GitHub-facing helpers: the contributors snapshot and the cache nudge.

The default-branch toggle is the "flush the sidebar cache" workaround from the
article that this project grew out of: it temporarily flips the default branch
to a scratch branch and flips it back, which nudges GitHub's widget caches to
recompute the contributor list. It is a personal-observation remedy, not a
documented GitHub feature, so it only ever runs when explicitly requested
(``rewrite --nudge-cache``) and never automatically.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .git_utils import git

__all__ = [
    "ContributorsSnapshot",
    "contributors_via_api",
    "gh_available",
    "toggle_default_branch",
]

_REFRESH_BRANCH = "refresh/sidebar-flush"
_GH_BASE = "https://api.github.com"
_GH_API_VERSION = "2022-11-28"


@dataclasses.dataclass(frozen=True)
class ContributorsSnapshot:
    """Logins returned by the public contributors endpoint."""

    owner: str
    repo: str
    logins: tuple[str, ...]


def gh_available() -> bool:
    return shutil.which("gh") is not None


def resolve_token() -> str | None:
    """Return a GitHub token from the environment, if any.

    Never printed or stored; lets CI authenticate via the automatic
    GITHUB_TOKEN. None keeps the caller on the anonymous, rate-limited path.
    """
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    return token or None


def _api_request(url: str, token: str | None) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-repo-sanitize",
        "X-GitHub-Api-Version": _GH_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def _get_json(url: str, token: str | None) -> Any:
    """GET *url* and return the decoded JSON; retry once on transient errors.

    HTTP errors are server decisions and are not retried (they will not
    resolve in a second); network failures get a single retry.
    """
    request = _api_request(url, token)
    attempts = 0
    while True:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            attempts += 1
            if attempts > 1:
                raise


def contributors_via_api(owner: str, repo: str) -> ContributorsSnapshot:
    """Query the public ``/repos/{owner}/{repo}/contributors`` endpoint.

    Uses a token when one is available (CI's GITHUB_TOKEN) and falls back to
    the auth-less, rate-limited path otherwise. Good enough for a post-push
    sanity print. Raises :class:`urllib.error.URLError` on network problems.
    """
    data = _get_json(f"{_GH_BASE}/repos/{owner}/{repo}/contributors", resolve_token())
    logins = tuple(item["login"] for item in data if isinstance(item, dict) and item.get("login"))
    return ContributorsSnapshot(owner=owner, repo=repo, logins=logins)


def _gh_api(args: list[str]) -> None:
    gh = shutil.which("gh")
    if gh is None:
        raise RuntimeError("gh CLI is required for the cache nudge; install it and retry")
    result = subprocess.run([gh, "api", *args], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"gh api {' '.join(args)} failed" + (f": {detail}" if detail else ""))


def toggle_default_branch(
    work: Path,
    owner: str,
    repo: str,
    branch: str,
    sleep_s: int = 90,
) -> None:
    """Push a scratch branch, flip the default to it, sleep, then restore.

    Rollback runs even when the sleep is interrupted (Ctrl-C), so the default
    branch is always restored and the scratch branch always deleted.
    """
    git(work, "push", "origin", f"{branch}:{_REFRESH_BRANCH}")
    _gh_api(["-X", "PATCH", f"/repos/{owner}/{repo}", "-f", f"default_branch={_REFRESH_BRANCH}"])
    try:
        print(f"cache nudge: default branch is {_REFRESH_BRANCH}; waiting {sleep_s}s")
        time.sleep(sleep_s)
    finally:
        _gh_api(["-X", "PATCH", f"/repos/{owner}/{repo}", "-f", f"default_branch={branch}"])
        git(work, "push", "origin", "--delete", _REFRESH_BRANCH)
        print("cache nudge: default branch restored and scratch branch deleted")