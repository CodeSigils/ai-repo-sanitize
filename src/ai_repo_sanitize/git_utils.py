"""Thin, shell-free wrappers around git subprocess calls.

Every invocation passes an explicit argv list and never a shell, so quoting
bugs and fragile pipelines cannot leak into the tool. Git itself is the only
binary consulted here; the one place shell is used at all is the optional
POSIX commit-msg hook, which lives outside this package on purpose.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .patterns import GIT_GREP_PATTERN

__all__ = [
    "GitError",
    "current_tree",
    "full_messages",
    "git",
    "preview_matches",
]

_RAW_FORMAT = "%H%x00%B%x00"


class GitError(RuntimeError):
    """Raised when a git command fails or git is not available."""


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run ``git -C <cwd> <args>`` and return the CompletedProcess."""
    executable = shutil.which("git")
    if executable is None:
        raise GitError("git executable not found on PATH")
    return subprocess.run(
        [executable, "-C", str(cwd), *args],
        check=check,
        text=True,
        capture_output=True,
    )


def git_bytes(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    """Byte-preserving variant; used where messages may contain non-UTF-8."""
    executable = shutil.which("git")
    if executable is None:
        raise GitError("git executable not found on PATH")
    return subprocess.run(
        [executable, "-C", str(cwd), *args],
        check=check,
        capture_output=True,
    )


def current_tree(work: Path, branch: str) -> str:
    """Return the tree SHA of *branch* in *work* (empty string when absent)."""
    result = git(work, "rev-parse", "-q", "--verify", f"refs/heads/{branch}^{{tree}}", check=False)
    return result.stdout.strip()


def full_messages(work: Path) -> str:
    """Return every commit subject+body, in ``git log`` order (newest first)."""
    return git(work, "log", "--format=%B").stdout


def preview_matches(work: Path) -> list[tuple[str, str]]:
    """List ``(short_sha, subject)`` for commits whose *full message* matches.

    ``--grep`` searches subject and body; ``--format`` only controls what is
    printed. ``-i -E`` are git's own flags and behave identically on Linux
    and macOS, so no external grep binary is involved.
    """
    result = git(
        work,
        "log",
        "--format=%h %s",
        "-i",
        "-E",
        f"--grep={GIT_GREP_PATTERN}",
        check=False,
    )
    if result.returncode != 0:
        # git log --grep exits 0 even with no matches; non-zero means error.
        raise GitError(f"git log failed: {result.stderr.strip() or result.stdout.strip()}")
    matches: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        if line.strip():
            short_sha, _, subject = line.partition(" ")
            matches.append((short_sha, subject))
    return matches


def commit_messages(work: Path) -> list[tuple[str, bytes]]:
    """Return ``(full_sha, raw_message)`` pairs for every commit.

    Parsed from NUL-delimited ``git log`` output; messages cannot contain
    NUL bytes, so the split is unambiguous.
    """
    result = git_bytes(work, "log", f"--format={_RAW_FORMAT}")
    # Every commit contributes two NUL-delimited fields: SHA, then the raw
    # message (a trailing NUL is stripped so the field list stays even).
    fields = result.stdout.rstrip(b"\x00").split(b"\x00")
    pairs: list[tuple[str, bytes]] = []
    for i in range(0, len(fields) - 1, 2):
        pairs.append((fields[i].decode("ascii"), fields[i + 1]))
    return pairs


def branch_exists(work: Path, branch: str) -> bool:
    result = git(work, "rev-parse", "-q", "--verify", f"refs/heads/{branch}", check=False)
    return result.returncode == 0