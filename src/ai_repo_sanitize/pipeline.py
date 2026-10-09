"""End-to-end pipeline: the guarded sequence from the article.

Safety is the product: a mirror backup exists before anything is rewritten,
the rewritten tip must point at the *same* tree as the original, and no
attribution may remain before a push is even considered. A push only happens
when the caller passes ``push=True``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import git_utils, publish, rewrite, verify
from .platform import (
    ContributorsSnapshot,
    contributors_via_api,
    gh_available,
    toggle_default_branch,
)

__all__ = [
    "PipelineError",
    "RewritePlan",
    "RewriteReport",
    "preview_commits",
    "run_check",
    "run_rewrite",
]


class PipelineError(RuntimeError):
    """Raised when a safety invariant fails or a precondition is missing."""


@dataclass(frozen=True)
class RewritePlan:
    """Everything the rewrite pass needs, decided up front."""

    work_dir: Path
    branch: str
    remote_url: str | None = None
    backup_dir: Path | None = None
    push: bool = False
    nudge_cache: bool = False


@dataclass
class RewriteReport:
    """Observable outcome of a rewrite run."""

    plan: RewritePlan
    preview: list[tuple[str, str]] = field(default_factory=list)
    before_tree: str | None = None
    after_tree: str | None = None
    residual: list[tuple[str, bytes]] = field(default_factory=list)
    pushed: bool = False
    contributors: ContributorsSnapshot | None = None


def _require_git_repo(work: Path) -> None:
    result = git_utils.git(work, "rev-parse", "--is-inside-work-tree", check=False)
    if result.returncode != 0 or result.stdout.strip() != "true":
        raise PipelineError(f"not a git repository: {work}")


def _split_remote(url: str) -> tuple[str, str] | None:
    """Best-effort (owner, repo) from a remote URL; None when unparseable.

    Accepts https://host/owner/repo.git, ssh://git@host/owner/repo.git and
    scp-style git@host:owner/repo.git; rejects local paths (a real owner
    never contains a "/").
    """
    stripped = url.removesuffix(".git")
    if "://" in stripped:
        stripped = stripped.split("://", 1)[1]
    if stripped.startswith("git@") and ":" in stripped:
        stripped = stripped.split(":", 1)[1]
    if "/" in stripped:
        stripped = stripped.split("/", 1)[1]
    owner, sep, repo = stripped.rpartition("/")
    if not sep or not owner or not repo or "/" in owner:
        return None
    return owner, repo


def preview_commits(work: Path) -> list[tuple[str, str]]:
    """Return ``(short_sha, subject)`` for commits a rewrite would change."""
    _require_git_repo(work)
    return git_utils.preview_matches(work)


def run_check(work: Path) -> verify.CheckResult:
    """Scan *work* for AI attribution; never modifies anything."""
    _require_git_repo(work)
    return verify.check_attribution(work)


def run_rewrite(plan: RewritePlan) -> RewriteReport:
    """Execute the full guarded sequence; pushes only when ``plan.push``."""
    work = plan.work_dir.resolve()
    _require_git_repo(work)
    report = RewriteReport(plan=plan)

    # Step 0 - mirror backup (the escape hatch). Refuse to overwrite one.
    if plan.backup_dir is not None:
        backup = plan.backup_dir.resolve()
        if backup.exists():
            raise PipelineError(
                f"backup mirror already exists: {backup} "
                "(remove it only after confirming the rewrite is good)"
            )
        if plan.remote_url is None:
            raise PipelineError("--backup-dir requires --remote-url (mirror backup needs a source)")
        backup.parent.mkdir(parents=True, exist_ok=True)
        git_utils.git(work.parent, "clone", "--mirror", plan.remote_url, str(backup))
    elif plan.push or plan.nudge_cache:
        raise PipelineError("rewrite with --push/--nudge-cache requires --backup-dir")

    before = git_utils.current_tree(work, plan.branch)
    if not before:
        raise PipelineError(f"branch {plan.branch!r} does not exist in {work}")
    report.before_tree = before

    # Step 1 - preview: exactly what the rewrite will drop.
    report.preview = git_utils.preview_matches(work)

    # Step 2 - rewrite messages only.
    rewrite.rewrite_messages(work)

    # Step 3 - verify: same tree, no attribution left. Hard gates.
    after = git_utils.current_tree(work, plan.branch)
    report.after_tree = after
    if not verify.tree_unchanged(work, plan.branch, before):
        raise PipelineError(
            f"tree changed during rewrite ({before} -> {after}); refusing to continue"
        )
    report.residual = verify.residual_commits(work)
    if report.residual:
        raise PipelineError(
            f"attribution still present in {len(report.residual)} commit(s); refusing to continue"
        )

    # Step 4 - publish only when asked, via --force-with-lease.
    if plan.push:
        if plan.remote_url is None:
            raise PipelineError("--push requires --remote-url")
        publish.publish(work, plan.remote_url, plan.branch)
        report.pushed = True

    # Step 5 - check the surfaces: contributors widget cache.
    pair = _split_remote(plan.remote_url) if plan.remote_url else None
    if pair is not None:
        owner, repo = pair
        try:
            report.contributors = contributors_via_api(owner, repo)
        except Exception as exc:  # network/rate-limit: informational only
            print(f"warning: contributors check skipped ({exc})")

    # Step 6 - last-resort sidebar-cache nudge, only when explicitly requested.
    if plan.nudge_cache:
        if pair is None:
            raise PipelineError("--nudge-cache requires an SSH-style or full remote URL")
        if not gh_available():
            raise PipelineError("--nudge-cache requires the gh CLI")
        owner, repo = pair
        # Toggle pushes the refresh branch itself and rolls back on Ctrl-C.
        toggle_default_branch(work, owner, repo, plan.branch)

    return report