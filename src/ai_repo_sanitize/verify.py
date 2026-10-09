"""Post-rewrite verification: prove the rewrite touched messages and nothing else.

The two invariants the whole tool is built around — the rewritten tip still
points at the same tree as the original, and no attribution remains in any
message — live here so every mode reuses the same checks.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from .git_utils import commit_messages, current_tree
from .patterns import has_attribution

__all__ = ["CheckResult", "check_attribution", "residual_commits", "tree_unchanged"]


@dataclasses.dataclass(frozen=True)
class CheckResult:
    """Result of a whole-repository attribution scan."""

    total: int
    offending: list[tuple[str, bytes]]

    @property
    def clean(self) -> bool:
        return not self.offending


def residual_commits(work: Path) -> list[tuple[str, bytes]]:
    """Return ``(sha, raw_message)`` pairs that still contain attribution."""
    return [(sha, message) for sha, message in commit_messages(work) if has_attribution(message)]


def check_attribution(work: Path) -> CheckResult:
    """Scan every commit in *work*; messages are read byte-exact via git."""
    commits = commit_messages(work)
    offending = [pair for pair in commits if has_attribution(pair[1])]
    return CheckResult(total=len(commits), offending=offending)


def tree_unchanged(work: Path, branch: str, before: str) -> bool:
    """True when *branch* still points at the tree recorded in *before*."""
    return current_tree(work, branch) == before