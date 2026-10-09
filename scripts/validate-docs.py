#!/usr/bin/env python3
"""Drift guard: keep the docs and the validation gates in agreement.

Inspired by the author's py-review-skill validate pattern (CC-BY-4.0 terms of
that repo; logic rewritten here). Enforces a small, verifiable contract:

* Every canonical validation command is listed in README.md and CONTRIBUTING.md.
* Every required documentation file exists (docs inventory never silently
  shrinks).
* Every internal relative link in the markdown docs resolves to a real file.
* Every required doc carries a current `Last reviewed: YYYY-MM-DD` header
  (missing, unparseable, future, or older than the 90-day window fails).
* The CI workflow and the pre-commit hook actually run the canonical commands
  they claim to run.

Exit code 0 = contract holds; 1 = findings (printed with file references).
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DOCS: tuple[str, ...] = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "MAINTENANCE.md",
    "RESEARCH.md",
    "ROADMAP.md",
    "ANTIDRIFT.md",
    "AGENTS.md",
)

#: Canonical commands. README, CONTRIBUTING, ci.yml and .githooks/pre-commit
#: must all reference these exact strings so the docs cannot drift from what
#: CI and local hooks really execute.
VALIDATION_COMMANDS: tuple[str, ...] = (
    "uv run ty check",
    "uv run ruff check .",
    "uv run pytest",
    "uv run python scripts/validate-docs.py",
)

_LINK_RE = re.compile(r"\]\(([^)]+)\)")
_REVIEW_RE = re.compile(r"Last reviewed:\s*(\d{4}-\d{2}-\d{2})")
_REVIEW_WINDOW_DAYS = 90


def findings(
    root: Path = ROOT,
    review_window_days: int = _REVIEW_WINDOW_DAYS,
    today: date | None = None,
) -> list[str]:
    """Return every drift finding; an empty list means docs and gates agree.

    *root* defaults to the repository root. *today* and *review_window_days*
    exist so tests/test_validate_docs.py can be deterministic.
    """
    problems: list[str] = []
    today = today or date.today()
    missing = [name for name in REQUIRED_DOCS if not (root / name).is_file()]
    if missing:
        problems.append("missing required docs: " + ", ".join(missing))

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    contributing = (
        (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        if (root / "CONTRIBUTING.md").is_file()
        else ""
    )
    for command in VALIDATION_COMMANDS:
        if command not in readme:
            problems.append(f"README.md must list the command: {command}")
        if command not in contributing:
            problems.append(f"CONTRIBUTING.md must list the command: {command}")

    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in VALIDATION_COMMANDS:
        # ci.yml runs the canonical commands verbatim (plain "uv run ..."),
        # so a simple substring check holds.
        if command not in ci:
            problems.append(f"ci.yml must run the canonical command: {command}")

    pre_commit = root / ".githooks" / "pre-commit"
    if pre_commit.is_file():
        hook = pre_commit.read_text(encoding="utf-8")
        if "uv run ruff check ." not in hook:
            problems.append(".githooks/pre-commit must run: uv run ruff check .")
        if "validate-docs.py" not in hook:
            problems.append(".githooks/pre-commit must run scripts/validate-docs.py")

    for doc in REQUIRED_DOCS:
        path = root / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for target in _LINK_RE.findall(text):
            href = target.split(" ", 1)[0]
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / href).resolve()
            if not resolved.exists():
                problems.append(f"{doc}: internal link target does not exist: {href}")
        match = _REVIEW_RE.search(text)
        if match is None:
            problems.append(f"{doc}: missing 'Last reviewed: YYYY-MM-DD' header")
            continue
        try:
            reviewed = date.fromisoformat(match.group(1))
        except ValueError:
            problems.append(f"{doc}: unparseable 'Last reviewed' date: {match.group(1)}")
            continue
        age = (today - reviewed).days
        if age < 0:
            problems.append(f"{doc}: 'Last reviewed' date is in the future: {reviewed}")
        elif age > review_window_days:
            problems.append(
                f"{doc}: last reviewed {age} days ago ({reviewed}); window is "
                f"{review_window_days} days"
            )
    return problems


def _parse_args(argv: list[str]) -> tuple[Path, date, int]:
    """--root DIR, --today YYYY-MM-DD, --review-window N; anything else fails.

    The default invocation stays byte-identical to the canonical command
    (`uv run python scripts/validate-docs.py`), so the substring contract in
    ci.yml and .githooks/pre-commit is untouched.
    """
    root, today, window = ROOT, date.today(), _REVIEW_WINDOW_DAYS
    pending = list(argv)
    while pending:
        name, *rest = pending
        if name not in ("--root", "--today", "--review-window"):
            raise ValueError(f"unknown option: {name}")
        if not rest:
            raise ValueError(f"{name} requires a value")
        value, *pending = rest
        if name == "--root":
            root = Path(value).resolve()
        elif name == "--today":
            today = date.fromisoformat(value)
        else:
            window = int(value)
    return root, today, window


def main(argv: list[str] | None = None) -> int:
    try:
        root, today, window = _parse_args(list(sys.argv[1:] if argv is None else argv))
    except ValueError as exc:
        print(f"validate-docs: usage error: {exc}")
        return 1
    problems = findings(root=root, review_window_days=window, today=today)
    if not problems:
        print("validate-docs: PASS - docs and gates agree")
        return 0
    print("validate-docs: FAIL")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())