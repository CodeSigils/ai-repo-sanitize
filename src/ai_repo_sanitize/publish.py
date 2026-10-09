"""Publishing the rewritten history: restore origin, fetch, force-with-lease.

``git filter-repo`` deletes the ``origin`` remote on purpose (it wants the
operator to stop and re-read the docs), so publishing is a distinct step that
re-adds it after the rewrite. The plain ``git fetch origin <branch>`` form is
used deliberately: in current git it recreates ``refs/remotes/origin/<branch>``,
which is exactly the tracking ref ``--force-with-lease`` compares against
before it overwrites the remote.
"""

from __future__ import annotations

from pathlib import Path

from .git_utils import git

__all__ = ["add_origin", "fetch_branch", "force_push", "publish"]


def add_origin(work: Path, remote_url: str) -> None:
    """Re-add origin unless a remote named origin already exists."""
    existing = git(work, "remote", "get-url", "origin", check=False)
    if existing.returncode == 0:
        return
    git(work, "remote", "add", "origin", remote_url)


def fetch_branch(work: Path, branch: str) -> None:
    git(work, "fetch", "origin", branch)


def force_push(work: Path, branch: str) -> None:
    git(work, "push", "--force-with-lease", "origin", branch)


def publish(work: Path, remote_url: str, branch: str) -> None:
    """Re-add origin, fetch the branch, then push with force-with-lease."""
    add_origin(work, remote_url)
    fetch_branch(work, branch)
    force_push(work, branch)