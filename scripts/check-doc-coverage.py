"""Warn when a code path changes without a matching documentation change.

datadef warn-not-fail rule: CI detects proxies for outdatedness, not
outdatedness itself, and a hard fail invites token edits. This check only
warns (::warning output); it exits 0 whenever it ran successfully.

The warning points at ANTIDRIFT.md's code-changes rule so the fix is
mechanical: bump the influenced docs in the same commit.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Paths whose edits count as "code" for coverage purposes.
_CODE_PATHS = (
    "src/",
    "tests/",
    "scripts/",
    ".githooks/",
    ".github/",
    "pyproject.toml",
    "uv.lock",
)

_DOC_SUFFIX = ".md"


def changed_files(base: str, head: str) -> list[str]:
    """Names of files changed between *base* and *head* (merge-base aware)."""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"git diff failed: {detail}")
    return [line for line in result.stdout.splitlines() if line]


def doc_coverage_warnings(changed: list[str]) -> list[str]:
    """Warn once when code changed but no markdown doc did."""
    code_changed = [path for path in changed if path.startswith(_CODE_PATHS)]
    docs_changed = [path for path in changed if path.endswith(_DOC_SUFFIX)]
    if not code_changed or docs_changed:
        return []
    listed = ", ".join(code_changed)
    return [
        f"code changed without a matching docs change: {listed}"
        " — bump the influenced docs in the same commit (ANTIDRIFT.md code-changes rule)"
    ]


def _default_base() -> str:
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/master"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return "origin/master" if probe.returncode == 0 else "HEAD^"


def _parse_args(argv: list[str]) -> tuple[str, str]:
    """Parse optional --base/--head; defaults derive from local git state."""
    base: str | None = None
    head: str | None = None
    index = 0
    while index < len(argv):
        if argv[index] == "--base" and index + 1 < len(argv):
            base = argv[index + 1]
            index += 2
        elif argv[index] == "--head" and index + 1 < len(argv):
            head = argv[index + 1]
            index += 2
        else:
            raise ValueError(f"unexpected argument: {argv[index]}")
    return base or _default_base(), head or "HEAD"


def main(argv: list[str] | None = None) -> int:
    """Warn-only doc coverage check; always exits 0 once it has run."""
    args = list(argv) if argv is not None else []
    try:
        base, head = _parse_args(args)
    except ValueError as exc:
        print(f"check-doc-coverage: usage error: {exc}", file=sys.stderr)
        return 1
    try:
        changed = changed_files(base, head)
    except RuntimeError as exc:
        print(f"check-doc-coverage: {exc}", file=sys.stderr)
        return 1
    for warning in doc_coverage_warnings(changed):
        print(f"::warning::{warning}")
    print(f"check-doc-coverage: {len(changed)} changed file(s), 0 blocking findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())