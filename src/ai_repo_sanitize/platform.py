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
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from .git_utils import git

__all__ = [
    "ContributorsSnapshot",
    "contributors_via_api",
    "gh_available",
    "toggle_default_branch",
]

_REFRESH_BRANCH = "refresh/sidebar-flush"
_GH_BASE = "https://api.github.com"


@dataclasses.dataclass(frozen=True)
class ContributorsSnapshot:
    """Logins returned by the public contributors endpoint."""

    owner: str
    repo: str
    logins: tuple[str, ...]


def gh_available() -> bool:
    return shutil.which("gh") is not None


def contributors_via_api(owner: str, repo: str) -> ContributorsSnapshot:
    """Query the public ``/repos/{owner}/{repo}/contributors`` endpoint.

    Auth-less and therefore rate-limited; good enough for a post-push sanity
    print. Raises :class:`urllib.error.URLError` on network problems.
    """
    url = f"{_GH_BASE}/repos/{owner}/{repo}/contributors"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "ai-repo-sanitize"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
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